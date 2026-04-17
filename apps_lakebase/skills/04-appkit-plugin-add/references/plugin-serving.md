# Serving Plugin

**Upstream docs (always check for latest):** https://databricks.github.io/appkit/docs/plugins/serving
Also consult the live AppKit docs: `npx @databricks/appkit docs "serving"`
The information below may be outdated. Prefer upstream when available.

Provides an authenticated proxy to Databricks Model Serving endpoints, with invoke and streaming support. Use this plugin to connect to Agent endpoints, LLM serving endpoints, or any Model Serving endpoint.

**Capabilities:** Named endpoint aliases for multiple serving endpoints, non-streaming (`invoke`) and SSE streaming (`stream`) invocation, automatic OpenAPI type generation for request/response schemas, request body filtering based on endpoint schema, on-behalf-of (OBO) user execution.

## Adding to an Existing AppKit Project

### 1. Register the Plugin

In `server/server.ts`:

```typescript
import { createApp, server, serving } from "@databricks/appkit";

await createApp({
  plugins: [
    server(),
    serving(),
  ],
});
```

### 2. Add Serving Endpoint as App Resource

The serving endpoint must be added as a **resource** to your Databricks App before it can be accessed. Do this via the Databricks Apps UI or `app.yaml`:

- **Default resource key:** `serving-endpoint`
- **Required permission:** `CAN_QUERY` (sends inference requests and views metadata)
- **Prerequisite:** The endpoint must be in `READY` state

The endpoint resource grants the app's service principal permission to query it. Without this resource binding, the plugin cannot reach the endpoint.

#### `databricks.yml` resource snippet (DABs deploy)

When provisioning the app via Databricks Asset Bundles, declare the serving endpoint resource in `databricks.yml`:

```yaml
resources:
  apps:
    ${var.app_name}:
      resources:
        - name: serving-endpoint
          description: Agent serving endpoint the AppKit plugin binds to
          serving_endpoint:
            name: ${var.serving_endpoint_name}
            permission: CAN_QUERY
```

> **Field name trap:** the bundle schema uses **`name`** (not `endpoint_name`). Using `endpoint_name` produces:
>
> ```
> Error: unknown field: endpoint_name
> Error: missing required field: name
> ```
>
> ...at `databricks bundle validate` time. The schema changed from earlier docs. When in doubt, run `databricks bundle schema | jq '.definitions."AppResource_SERVING_ENDPOINT"'` to confirm the current field name against your CLI version. See [03-appkit-deploy/SKILL.md](../../03-appkit-deploy/SKILL.md) Common Errors for the recovery step.

### 3. Environment Variables

**For deployment** — add to `app.yaml`:

```yaml
env:
  - name: DATABRICKS_SERVING_ENDPOINT_NAME
    valueFrom: serving-endpoint
```

> **Critical:** The Databricks Apps platform injects `SERVING_ENDPOINT=<name>` via the resource binding, but the AppKit Serving plugin reads `DATABRICKS_SERVING_ENDPOINT_NAME`. You must explicitly declare the env var with that name in `app.yaml` using `valueFrom: serving-endpoint` so the platform value is mapped to the name the plugin expects.

**For local development** — add to `.env`:

```env
DATABRICKS_SERVING_ENDPOINT_NAME=<your-endpoint-name>
```

Local dev also requires Databricks authentication (CLI profile or `DATABRICKS_HOST` + `DATABRICKS_TOKEN`).

### 4. Configuration Options

```typescript
serving({
  endpoints: {
    agent:      { env: "DATABRICKS_SERVING_ENDPOINT_NAME" },
    classifier: { env: "DATABRICKS_SERVING_ENDPOINT_CLASSIFIER" },
  },
  timeout: 120000, // request timeout in ms (default: 120000)
});
```

If `endpoints` is omitted, the plugin reads `DATABRICKS_SERVING_ENDPOINT_NAME` from the environment and registers it under the `default` alias.

To bypass traffic routing and target a specific model within a multi-model endpoint:

```typescript
serving({
  endpoints: {
    agent: { env: "DATABRICKS_SERVING_ENDPOINT_NAME", servedModel: "my-agent-v2" },
  },
});
```

### 5. Frontend — useServingStream (Streaming)

Recommended for Agent endpoints — streaming provides progressive UX feedback for slow responses:

```tsx
import { useServingStream } from "@databricks/appkit-ui/react";

function AgentChat() {
  const { stream, chunks, streaming, error, reset } = useServingStream(
    { messages: [{ role: "user", content: "Hello" }] },
    {
      alias: "agent",
      onComplete: (finalChunks) => {
        console.log("Stream done, got", finalChunks.length, "chunks");
      },
    },
  );

  return (
    <>
      <button onClick={stream} disabled={streaming}>Send</button>
      <button onClick={reset}>Reset</button>
      {chunks.map((chunk, i) => <pre key={i}>{JSON.stringify(chunk)}</pre>)}
      {error && <p>{error}</p>}
    </>
  );
}
```

> **Note:** Unlike Genie's `GenieChat` component, the Serving plugin has no pre-built chat component. `useServingStream` is stateless — the app must manage conversation history. See `06-appkit-serving-wiring/references/chat-ui-patterns.md` for full chat UI patterns.

### 6. Frontend — useServingInvoke (Non-Streaming)

For endpoints with fast, deterministic responses:

```tsx
import { useServingInvoke } from "@databricks/appkit-ui/react";

function AgentQuery() {
  const { invoke, data, loading, error } = useServingInvoke(
    { messages: [{ role: "user", content: "Summarize Q3 sales" }] },
    { alias: "agent" },
  );

  return (
    <>
      <button onClick={invoke} disabled={loading}>Run</button>
      {data && <pre>{JSON.stringify(data, null, 2)}</pre>}
      {error && <p>{error}</p>}
    </>
  );
}
```

Both hooks accept `autoStart: true` to invoke automatically on mount.

## HTTP Endpoints

### Named mode (with `endpoints` config)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/serving/:alias/invoke` | Non-streaming invocation |
| POST | `/api/serving/:alias/stream` | SSE streaming invocation |

### Default mode (no `endpoints` config)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/serving/invoke` | Non-streaming invocation |
| POST | `/api/serving/stream` | SSE streaming invocation |

### Request format

```json
{
  "messages": [
    { "role": "user", "content": "Hello" }
  ]
}
```

> **The plugin normalizes the request body for you.** Databricks Agent endpoints deployed via `databricks.agents.deploy()` expect `{"input": [...]}` at the top level — **not** `{"messages": [...]}`. The plugin transforms the incoming request before forwarding. When building a **custom proxy without the plugin**, you must do the `messages → input` transformation explicitly; see [06-appkit-serving-wiring/references/custom-proxy-fallback.md](../../06-appkit-serving-wiring/references/custom-proxy-fallback.md).

## Programmatic Access (Server-Side)

```typescript
const AppKit = await createApp({
  plugins: [
    server(),
    serving({
      endpoints: { agent: { env: "DATABRICKS_SERVING_ENDPOINT_NAME" } },
    }),
  ],
});

// Non-streaming (service principal context)
const result = await AppKit.serving("agent").invoke({
  messages: [{ role: "user", content: "Hello" }],
});

// Non-streaming (user context — recommended in route handlers)
const result = await AppKit.serving("agent").asUser(req).invoke({
  messages: req.body.messages,
});

// Streaming
for await (const chunk of AppKit.serving("agent").stream({
  messages: [{ role: "user", content: "Hello" }],
})) {
  console.log(chunk);
}
```

All serving routes execute on behalf of the authenticated user (OBO) by default, ensuring per-user `CAN_QUERY` permissions are enforced on the serving endpoint.

## Type Generation

The `appKitServingTypesPlugin()` Vite plugin generates TypeScript types from your serving endpoints' OpenAPI schemas. No manual setup needed — the AppKit dev server includes this plugin automatically.

Generated types provide:
- Alias autocomplete in both backend (`AppKit.serving("alias")`) and frontend hooks
- Typed request/response/chunk per endpoint based on OpenAPI schemas

If an endpoint's OpenAPI schema is unavailable (not deployed, env var not set), the plugin generates generic fallback types. The endpoint is still usable — just without typed request/response.

> **Note:** Endpoints that don't define a streaming response schema in their OpenAPI spec will have `chunk: unknown`. For these endpoints, use `useServingInvoke` instead of `useServingStream` — the `response` type will still be properly typed.

## Combining with Other Plugins

```typescript
import { createApp, server, serving, lakebase, analytics } from "@databricks/appkit";

await createApp({
  plugins: [server(), serving(), lakebase(), analytics()],
});
```
