# Trace ID Extraction

How to extract MLflow trace IDs from Databricks serving endpoint responses, enabling
the feedback → MLflow assessment link.

> **Client note (IDE & Genie Code).** This is pure **server-side parser code** — it runs at request time on the deployed app and is identical on both clients. There are no client-specific commands here.

This helper is shared between [07-appkit-chat-history](../../07-appkit-chat-history/SKILL.md)
(which captures `trace_id` during streaming and persists it on `chat.Message`) and
[08-appkit-feedback](../SKILL.md) (which reads it back to log MLflow assessments).

## Where Trace IDs Come From

When a Databricks serving endpoint has tracing enabled (via MLflow), each response
includes trace metadata. The exact location depends on the endpoint type and response
format.

**Important:** tracing is a property of the deployed endpoint, not the client. If
`trace_id` never appears in any chunk, the endpoint was deployed without tracing.
Redeploy with tracing enabled (see [SKILL.md Step 1](../SKILL.md#enabling-mlflow-tracing-on-the-agent-endpoint)).

## Extraction Patterns

### Pattern 1: Databricks Agent Serving (Streaming)

Agents deployed via Databricks Agent Framework include trace info in the
`databricks_output` field of stream chunks:

```json
{
  "databricks_output": {
    "trace": {
      "info": {
        "trace_id": "abc123def456",
        "experiment_id": "12345"
      }
    }
  }
}
```

Extraction:

```typescript
function extractTraceIdFromChunk(chunk: Record<string, unknown>): string | null {
  const dbOutput = chunk?.databricks_output as Record<string, unknown> | undefined;
  if (!dbOutput) return null;

  const trace = dbOutput.trace as Record<string, unknown> | undefined;
  const info = trace?.info as Record<string, unknown> | undefined;
  if (typeof info?.trace_id === "string") return info.trace_id;

  return null;
}
```

### Pattern 2: Databricks Agent Serving (Non-Streaming)

Same structure but in the full response:

```json
{
  "choices": [{ "message": { "content": "Hello!" } }],
  "databricks_output": {
    "trace": {
      "info": { "trace_id": "abc123def456" }
    }
  }
}
```

### Pattern 3: MLflow AgentServer (Local Development)

When running an agent locally via `mlflow.models.serve`:

```json
{
  "trace_id": "abc123def456",
  "choices": [{ "message": { "content": "Hello!" } }]
}
```

Extraction:

```typescript
if (typeof chunk.trace_id === "string") return chunk.trace_id;
```

### Pattern 4: Foundation Model Endpoints

Raw foundation model endpoints (e.g., `databricks-meta-llama-3-1-70b-instruct`)
do **not** include trace IDs by default. To get traces, wrap the endpoint in an agent
that logs to MLflow and redeploy it. There is no client-side flag you can set to make
an already-deployed endpoint start emitting trace IDs — tracing is enabled at deploy
time via the Agent Framework (`databricks.agents.deploy(..., enable_trace=True)` or
the equivalent Mosaic AI Agent Evaluation option).

> **Note on upstream docs:** some older templates used a Vercel AI SDK provider
> option like `providerOptions.databricks.includeTrace`. That option does not exist
> in AppKit's Serving plugin — AppKit streams whatever the endpoint emits. The only
> way to get `trace_id` is for the endpoint itself to produce it.

## Combined Extractor

Use a combined function that handles Patterns 1-3:

```typescript
function extractTraceId(chunk: Record<string, unknown>): string | null {
  // Pattern 1/2: Databricks Agent Serving
  const dbOutput = chunk?.databricks_output as Record<string, unknown> | undefined;
  if (dbOutput) {
    const trace = dbOutput.trace as Record<string, unknown> | undefined;
    const info = trace?.info as Record<string, unknown> | undefined;
    if (typeof info?.trace_id === "string") return info.trace_id;
  }

  // Pattern 3: MLflow AgentServer
  if (typeof chunk?.trace_id === "string") return chunk.trace_id;

  return null;
}
```

This is exactly the helper used in
[07-appkit-chat-history Step 4a](../../07-appkit-chat-history/SKILL.md#step-4-stream--persist-assistant-message-appkit-native).

## When to Extract

Extract the trace ID during streaming and accumulate it. The `for await` loop wraps
`AppKit.serving("agent").asUser(req).stream(...)` — same pattern as
[06-appkit-serving-wiring Step 6b](../../06-appkit-serving-wiring/SKILL.md).

```typescript
let traceId: string | null = null;

for await (const chunk of AppKit.serving("agent").asUser(req).stream({ messages })) {
  // Check every chunk — trace info may appear in any chunk (usually the last)
  const extracted = extractTraceId(chunk as Record<string, unknown>);
  if (extracted) traceId = extracted;

  // Forward chunk to client
  res.write(`data: ${JSON.stringify(chunk)}\n\n`);
}

// After stream completes, save traceId with the assistant message:
await AppKit.lakebase.query(
  `INSERT INTO chat."Message" (id, "chatId", role, parts, "traceId", "createdAt")
   VALUES ($1, $2, 'assistant', $3, $4, CURRENT_TIMESTAMP)`,
  [assistantMsgId, chatId, JSON.stringify([{ type: "text", text: accumulatedText }]), traceId],
);
```

The trace ID usually appears in the last chunk of the stream, but checking every chunk
is safer.

## Sending Trace ID to the Client

After the stream completes, send the trace ID as a metadata event so the client can
associate it with the message it just rendered (needed by `FeedbackButtons` when the
Lakebase lookup is unavailable):

```typescript
res.write(
  `data: ${JSON.stringify({ type: "meta", assistantMessageId, traceId })}\n\n`,
);
res.end();
```

The client stores this on the message object:

```tsx
if (parsed.type === "meta") {
  assistantMessageId = parsed.assistantMessageId;
  traceId = parsed.traceId ?? null;
}
// ...after the stream closes, update the last message with { id, traceId }
```

See [07-appkit-chat-history Step 4c](../../07-appkit-chat-history/SKILL.md#4c-client-side-integration)
for the full client-side SSE parser.

## Debugging Missing Trace IDs

| Symptom | Cause | Fix |
|---------|-------|-----|
| `traceId` is always `null` | Endpoint doesn't return trace info | Redeploy the agent with `databricks.agents.deploy(..., enable_trace=True)` |
| `traceId` appears on some messages | Trace info only on certain response types | Check endpoint config; tool-calling responses sometimes emit trace on a different chunk — but the combined extractor above handles both the `databricks_output` and top-level `trace_id` cases |
| MLflow API returns 404 for trace | Trace not yet flushed to MLflow backend | Add a short delay before logging assessment, or retry once on 404 |
| Feedback logged but no assessment visible in MLflow UI | Wrong experiment ID | Verify `MLFLOW_EXPERIMENT_ID` matches the endpoint's experiment (check the `experiment_id` field from Pattern 1) |
| `traceId` extracted but persists as `null` on the DB row | Forgot to pass the captured `traceId` variable into the `INSERT INTO chat."Message"` call | Review [07-appkit-chat-history Step 4b](../../07-appkit-chat-history/SKILL.md#4b-the-apichat-proxy-route) — the fourth `$4` bind must be the accumulated `traceId` |
