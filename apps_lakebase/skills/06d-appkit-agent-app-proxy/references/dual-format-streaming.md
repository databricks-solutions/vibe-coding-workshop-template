# Dual-Format SSE Streaming

Agent Apps authored per Track A emit SSE events in **two different shapes** depending on which MLflow helper they use. A chat UI parser that handles only one shape will silently render blank output against the other. Use the dual extractor below for compatibility.

The proxy is also **dual** at the request boundary — it accepts two request body shapes from the frontend (Responses-style and Chat-style). See "Request Shape Contract" below.

**When to read this:** Reading [../SKILL.md](../SKILL.md) and reached Step 4 (frontend hook). Stop and read this file first.

---

## Request Shape Contract

The proxy MUST accept and normalize both AppKit-side request body shapes before forwarding to the Agent App's `/invocations` endpoint:

| Shape | Body | Used by |
|-------|------|---------|
| Responses-style | `{ "input": ... }` | `mlflow.genai.agent_server` Responses adapters; `ResponsesAgent`-shaped clients |
| Chat-style | `{ "messages": [{ "role": "user", "content": "..." }, ...] }` | The minimal `useAgentChat` hook in SKILL.md Step 4; OpenAI-compatible chat clients |

Anything else (missing both `input` and `messages`, non-array `messages`, etc.) MUST be rejected with HTTP `400`:

```json
{ "error": "invalid_body_shape", "accepted": ["input", "messages"] }
```

Why this matters: an earlier proxy iteration assumed only `{messages}`. Responses-style callers were dropped silently — the agent received a malformed body, returned an empty stream, and the dual extractor below rendered a blank UI with no error. **A `400 invalid_body_shape` response makes the contract violation observable instead of silent.** Pair the request-shape rejection here with the response-shape extractor below; together they cover both ends of the proxy.

See [../SKILL.md § Request Body Contract](../SKILL.md#request-body-contract-dual-shape-normalized) for the proxy-handler implementation snippet.

---

## SSE Synthesis Debt (`workspace_sse_guardrail`)

The extractor below works against a true streaming source **and** against a synthesized stream produced by the proxy when `endpoint_guardrail_audit[agent_chat].streaming_ok == false`. In the synthesized case the proxy calls `/invocations` with `stream: false`, parses the unary JSON, and emits exactly one `response.output_text.delta` (Shape A below) followed by `response.completed` and `[DONE]`. The frontend cannot tell the difference — and that's the point of the dual extractor.

This synthesis branch is `debt: workspace_sse_guardrail` and must be audited via `vibecoding-state.audit_debts` per [../SKILL.md § SSE Synthesis Debt](../SKILL.md#sse-synthesis-debt-workspace_sse_guardrail).

---

## The Two Shapes

### Shape A — Responses API Events (preferred)

Emitted by `mlflow.genai.agent_server` when the handler yields from `ResponsesAgent`-style streaming:

```json
{"type": "response.output_text.delta", "delta": "Hello"}
{"type": "response.output_text.delta", "delta": " there"}
{"type": "response.completed", "response": {"status": "completed"}}
```

Token text is in `delta` directly. The `type` field distinguishes text deltas from tool call events, completion events, and error events.

### Shape B — OpenAI Chat Completion Chunks

Emitted by agents that wrap an OpenAI-compatible model behind `AgentServer.serve()` without the Responses adapter:

```json
{"choices": [{"delta": {"content": "Hello"}, "index": 0}]}
{"choices": [{"delta": {"content": " there"}, "index": 0}]}
```

Token text is under `choices[0].delta.content`.

### Mix

Some handlers emit a preamble in Shape A (e.g. tool-call progress) and the final text in Shape B, or vice versa. The extractor must ignore events it doesn't know and skip chunks without text deltas.

---

## The Dual Extractor

```typescript
type AgentChunk = Record<string, unknown>;

export function extractDelta(chunk: AgentChunk): string {
  // Shape A — Responses API text delta
  if (chunk.type === "response.output_text.delta") {
    return typeof chunk.delta === "string" ? chunk.delta : "";
  }

  // Shape A — Responses API completion / tool events carry no text delta
  if (typeof chunk.type === "string" && chunk.type.startsWith("response.")) {
    return "";
  }

  // Shape B — OpenAI chat completion chunk
  const choices = chunk.choices as Array<{ delta?: { content?: string } }> | undefined;
  const openaiDelta = choices?.[0]?.delta?.content;
  return typeof openaiDelta === "string" ? openaiDelta : "";
}
```

Properties:

- Never throws on malformed input.
- Returns `""` for non-text events (tool calls, status pings, completion markers).
- Accepts both shapes without configuration — no per-agent branching in the UI.

---

## Full SSE Reader

Pair the extractor with a buffered SSE reader. Important: SSE payloads can span chunk boundaries, so buffer until you see `\n\n`.

```typescript
import { extractDelta } from "./agent-stream-extractor";

export async function streamAgent(
  messages: { role: string; content: string }[],
  onDelta: (text: string) => void,
  onDone?: () => void,
  onError?: (err: string) => void,
): Promise<void> {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages }),
  });
  if (!res.ok || !res.body) {
    onError?.(`stream failed: HTTP ${res.status}`);
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const events = buffer.split("\n\n");
      buffer = events.pop() ?? "";

      for (const ev of events) {
        const dataLine = ev.split("\n").find((l) => l.startsWith("data: "));
        if (!dataLine) continue;
        const payload = dataLine.slice(6).trim();
        if (!payload || payload === "[DONE]") continue;

        try {
          const chunk = JSON.parse(payload);
          if (chunk.error) {
            onError?.(String(chunk.error));
            continue;
          }
          const delta = extractDelta(chunk);
          if (delta) onDelta(delta);
        } catch {
          // Partial JSON or non-JSON keepalive — ignore
        }
      }
    }
    onDone?.();
  } catch (err) {
    onError?.(String(err));
  } finally {
    reader.releaseLock();
  }
}
```

---

## Pre-Deploy `curl` Test

Before wiring the frontend, verify which shape your Agent App actually emits:

```bash
AGENT_URL=$(databricks apps get "$AGENT_APP_NAME" --profile "$PROFILE" --output json | jq -r '.url')
TOKEN=$(databricks auth token --profile "$PROFILE" --output json | jq -r '.access_token')

curl -sN -X POST "${AGENT_URL%/}/invocations" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Say hi in three words"}]}' \
  | head -c 2000
```

Inspect the first few `data: ...` lines:

- Contain `"type":"response.output_text.delta"` → Shape A.
- Contain `"choices":[{"delta":{"content":...`  → Shape B.
- Mix of both → dual extractor is mandatory.

If `curl` hangs with no output, the agent is not emitting SSE — it may be in unary `/invocations` mode. Check the agent's handler: `@agent_server.stream` vs `@agent_server.invoke`.

---

## Event Ordering and Completion Detection

Shape A emits an explicit terminator:

```json
{"type": "response.completed", "response": {...}}
```

Shape B does not; completion is signaled by the TCP close or an `[DONE]` sentinel that some wrappers add.

The reader above treats `[DONE]` as a no-op and relies on `reader.read()` returning `done: true` on close. This works for both shapes. If you need a typed `onComplete` event for your UI (to unlock the input, commit the message to history, etc.), call `onDone` in the `finally` after the loop — which the code above does.

---

## Gotchas

| Gotcha | Symptom | Fix |
|--------|---------|-----|
| Parse only `choices[0].delta.content` | Blank UI against `ResponsesAgent` streams | Use the dual extractor |
| Parse only `response.output_text.delta` | Blank UI against OpenAI-wrapped agents | Use the dual extractor |
| Split buffer on `\n` (single newline) | Events rendered mid-chunk, partial JSON errors | Split on `\n\n` (double newline per SSE spec) |
| `JSON.parse` inside `onDelta` without try/catch | One malformed chunk tears down the whole stream | Wrap in try/catch; treat parse errors as keepalives |
| Reader not released on early return | Memory leak across many chats | `reader.releaseLock()` in `finally` |
| Assumed `[DONE]` is always present | UI "streaming" spinner never clears | Use `done: true` from `reader.read()` as the authoritative terminator |

---

## References

- [SSE spec (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events)
- [OpenAI chat completions streaming format](https://platform.openai.com/docs/api-reference/chat/streaming)
- [apps_lakebase/skills/06-appkit-serving-wiring/references/sse-format-patterns.md](../../06-appkit-serving-wiring/references/sse-format-patterns.md) — the Serving-endpoint counterpart; different URLs and resource model but same dual-shape problem
- [Track A 02-agent-framework](../../../../genai-agents/tracks/A-custom-agent-apps/02-agent-framework/SKILL.md) — where the agent authoring pattern decides which shape it emits
