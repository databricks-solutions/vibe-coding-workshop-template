# SSE Chunk Format Patterns for Databricks Serving Endpoints

Databricks Model Serving streams responses in **two different SSE chunk formats** depending on how the endpoint was created. Your frontend parser must handle both, or at minimum detect and fail loudly on the wrong one. This reference documents the formats, a dual-format parser, and a pre-deploy `curl` test that tells you which format you are receiving before writing parser code.

> **Read this when:** building a streaming parser, debugging "endpoint returns 200 but UI stays blank", or validating a new endpoint's streaming contract.

---

## The Two Formats

### Format A: Databricks Responses API (Agent Framework)

Produced by endpoints deployed via `databricks.agents.deploy()` wrapping a `ResponsesAgent` / `MCPToolCallingAgent` (i.e., the pattern in `09-simple-agent-scaffold/SKILL.md`).

Each SSE `data:` line is a JSON object with a `type` discriminator:

```
data: {"type":"response.output_text.delta","delta":"Hello"}
data: {"type":"response.output_text.delta","delta":", world"}
data: {"type":"response.completed"}
data: [DONE]
```

Key fields:
- `type: "response.output_text.delta"` — text chunk, content is in `delta` (string)
- `type: "response.output_text.done"` — end of a text output block (no text)
- `type: "response.completed"` — stream complete (may be followed by `[DONE]`)
- Tool-call events (`response.function_call.*`) appear between deltas for tool-using agents

### Format B: OpenAI Chat Completion (Custom Model Serving)

Produced by custom Model Serving endpoints using the OpenAI-compatible chat completion shape (the default when you deploy via MLflow `pyfunc` flavor that returns OpenAI-style payloads, or when using non-agent LLM wrappers).

Each `data:` line is an OpenAI-compatible chunk:

```
data: {"id":"...","object":"chat.completion.chunk","choices":[{"delta":{"content":"Hello"},"index":0}]}
data: {"id":"...","object":"chat.completion.chunk","choices":[{"delta":{"content":", world"},"index":0}]}
data: [DONE]
```

Key path: `chunk.choices[0].delta.content` (string).

---

## Pre-Deploy Format Test (do this BEFORE writing parser code)

Run this `curl` one-liner against the deployed endpoint and inspect the first chunk:

```bash
ENDPOINT_NAME="your-agent-endpoint"
TOKEN=$(databricks auth token --profile "$DATABRICKS_CONFIG_PROFILE" | jq -r .access_token)
HOST=$(databricks auth describe --profile "$DATABRICKS_CONFIG_PROFILE" -o json | jq -r .details.host)

curl -sS -N -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input":[{"role":"user","content":"say hi in 3 words"}],"stream":true}' \
  "$HOST/serving-endpoints/$ENDPOINT_NAME/invocations" | head -c 1000
```

Decide based on the first non-empty `data:` line:

| First chunk contains... | Format | Parser path |
|-------------------------|--------|-------------|
| `"type":"response.output_text.delta"` | Databricks Responses API | `chunk.delta` |
| `"object":"chat.completion.chunk"` or `"choices":[...]` | OpenAI Chat Completion | `chunk.choices[0].delta.content` |
| `400 Bad Request: Model is missing inputs ['input']` | Payload was wrong | Change `input` → `messages` or vice versa; retest — see `custom-proxy-fallback.md` |
| `401` / `403` | Auth issue, not a format issue | Fix SP grants on the endpoint, then retest |

Capture the first ~500 bytes of output; commit the format decision as a comment in the parser so later edits don't regress.

---

## Dual-Format Parser

The safest default is a parser that handles both and logs unknown shapes once. This lets a single frontend component work against either endpoint type without branching by endpoint name.

```typescript
type Chunk = {
  type?: string;
  delta?: string;
  choices?: Array<{ delta?: { content?: string } }>;
};

let warnedUnknown = false;

export function extractDelta(chunk: Chunk): string {
  if (chunk.type === "response.output_text.delta" && typeof chunk.delta === "string") {
    return chunk.delta;
  }
  const openAiDelta = chunk.choices?.[0]?.delta?.content;
  if (typeof openAiDelta === "string") {
    return openAiDelta;
  }
  if (
    !warnedUnknown &&
    chunk.type !== "response.output_text.done" &&
    chunk.type !== "response.completed" &&
    !chunk.type?.startsWith("response.function_call")
  ) {
    console.warn("[sse] unknown chunk shape", chunk);
    warnedUnknown = true;
  }
  return "";
}
```

Call this from the SSE reader per decoded JSON chunk. Skip `[DONE]` sentinels before parsing:

```typescript
for (const line of buffer.split("\n\n")) {
  const data = line.split("\n").find((l) => l.startsWith("data: "))?.slice(6);
  if (!data || data === "[DONE]") continue;
  try {
    const parsed = JSON.parse(data) as Chunk;
    const text = extractDelta(parsed);
    if (text) onDelta(text);
  } catch {
    // Partial / keepalive — ignore
  }
}
```

---

## Gotchas

| Symptom | Root cause | Fix |
|---------|-----------|-----|
| Streaming returns 200, UI stays blank, no errors | Parser only reads `choices[0].delta.content` but endpoint emits Responses API | Use the dual parser; add the `response.output_text.delta` branch |
| Parser throws on `[DONE]` | `JSON.parse("[DONE]")` fails | Skip the `[DONE]` sentinel before `JSON.parse` |
| First chunks parse, then blank output | Tool-call events (`response.function_call.*`) are not handled and the `[DONE]` sentinel is missed | Ignore tool-call types, don't error on them; always `break` on `[DONE]` |
| Random dropped characters | Not decoding multi-byte UTF-8 across chunk boundaries | Use `TextDecoder({ stream: true })` and buffer until `\n\n` |
| Fine in dev, broken in prod | Prod endpoint was redeployed with a different agent class (Responses vs OpenAI) | Rerun the `curl` test against prod; the format can change between deploys |

---

## When NOT to use the dual parser

If you own both ends (the agent deploy script **and** the UI), pick one format and stick with it — it is simpler to document the contract than to keep the dual parser. In that case, set the format in `09-simple-agent-scaffold/SKILL.md` ("Contract for UI Wiring") and write a single-path parser. Use the dual parser only when the UI must support multiple endpoint types (mixed OpenAI + Responses).
