# Custom Serving Proxy Fallback

Use this reference when the AppKit `serving()` plugin is **not** exported by your installed AppKit version, or when you need a custom proxy that post-processes agent responses in ways the plugin does not support. It replicates the plugin's HTTP surface (`/api/serving/invoke`, `/api/serving/stream`) using the AppKit SDK's execution context for authentication.

> **Read this only when the Step 1b verification in `04-appkit-plugin-add/SKILL.md` returns `typeof serving === "undefined"`.** If the plugin is available, use `serving()` directly as documented in `06-appkit-serving-wiring/SKILL.md` Step 3 — do not build a custom proxy.

---

## When to Build a Custom Proxy

| Situation | Action |
|-----------|--------|
| `serving` export is `undefined` in the installed AppKit version | Build a custom proxy (this file) |
| `serving` export exists | Use the plugin per `SKILL.md` Step 3 — do not build a proxy |
| Plugin works but you need to post-process responses | Use `server.extend()` on top of `serving()` — see `SKILL.md` Step 6, not this file |

---

## Step 1: Verify the Gap Before Writing Code

```bash
cd apps_lakebase/$APP_NAME
node -e "const m = require('@databricks/appkit'); console.log('serving:', typeof m.serving);"
node -e "console.log('appkit:', require('@databricks/appkit/package.json').version);"
```

If `serving: function`, stop — use the plugin. Only continue if `serving: undefined`.

Check the upstream release notes (`https://github.com/databricks/appkit/releases`) to see which version first published the plugin. If a newer version is already on your npm registry and the platform can reach it, upgrade first:

```bash
npm install @databricks/appkit@latest @databricks/appkit-ui@latest
node -e "console.log(typeof require('@databricks/appkit').serving)"
```

If the plugin was added in a version not yet on your registry, proceed with the proxy below.

> **Critical — do NOT regenerate `package-lock.json` to force the upgrade.** The Databricks Apps platform's `npm install` depends on lockfile stability. See `03-appkit-deploy/references/lockfile-and-recreation.md`.

---

## Step 2: Authentication Pattern

The correct API is `config.authenticate(headers)` — it populates a `Headers` object with the `Authorization` header the SDK resolved (PAT, OAuth M2M, OBO, etc.). There is no `getToken()` method on the AppKit `Config` type.

```typescript
import { getExecutionContext } from "@databricks/appkit";

async function getServingHeaders(): Promise<{ host: string; headers: Record<string, string> }> {
  const ctx = getExecutionContext();
  const config = ctx.client.config;
  await config.ensureResolved();
  const host = (config.host ?? "").replace(/\/$/, "");
  const h = new Headers();
  await config.authenticate(h);
  h.set("Content-Type", "application/json");
  const out: Record<string, string> = {};
  h.forEach((v, k) => { out[k] = v; });
  return { host, headers: out };
}
```

### Anti-patterns that will fail at deploy time

| Wrong | Error | Why |
|-------|-------|-----|
| `config.getToken()` | `TypeError: config.getToken is not a function` | Method does not exist on AppKit's `Config`. Use `authenticate(headers)`. |
| `process.env.DATABRICKS_HOST` directly | `TypeError: Failed to parse URL` | Platform-injected `DATABRICKS_HOST` may not include `https://`. Use `config.host` (pre-resolved with protocol). |
| Stashing `Authorization` header manually from env vars | 401 on the serving endpoint | Misses OBO forwarding and token refresh. Always round-trip through the SDK. |
| `new WorkspaceClient().config.getToken()` | Same as above — method does not exist | Use `getExecutionContext().client.config` so OBO flows through. |

### Read the type declarations before writing

```bash
find node_modules/@databricks/appkit -name "*.d.ts" | xargs grep -l "authenticate\|getExecutionContext" | head -5
```

Open the matching `.d.ts` file and confirm the method name before copy-pasting. Do not guess method names from other Databricks SDKs.

---

## Step 3: Payload Transformation

Databricks Agent endpoints deployed via `databricks.agents.deploy()` with `ResponsesAgent` expect `{"input": [...]}` at the top level — **not** `{"messages": [...]}`. The AppKit `serving()` plugin normalizes this automatically; a custom proxy must do it explicitly.

```typescript
type ChatMessage = { role: string; content: string };

function buildAgentPayload(body: Record<string, unknown>, stream = false) {
  const messages = body.messages as ChatMessage[] | undefined;
  const payload: Record<string, unknown> = {
    input: messages ?? body.input ?? [],
  };
  if (stream) payload.stream = true;
  if (body.context) payload.context = body.context;
  return payload;
}
```

Sending `{"messages": [...]}` directly produces:

```
400 Bad Request
{"error":"Model is missing inputs ['input']. Note that there were extra inputs: ['messages']."}
```

> The frontend (your chat UI) should continue to send `{ messages: [...] }` — that matches the AppKit `useServingStream` shape. Only the **server proxy** transforms `messages` → `input` before forwarding to the endpoint.

---

## Step 4: Route Handlers

Register two routes that mirror the plugin's default URL shape (`/api/serving/invoke` and `/api/serving/stream`) so the frontend `useServingStream` / `useServingInvoke` hooks work unchanged once the plugin becomes available.

```typescript
import { createApp, server, getExecutionContext } from "@databricks/appkit";

const AppKit = await createApp({ plugins: [server({ autoStart: false })] });

AppKit.server.extend((app) => {
  app.post("/api/serving/invoke", async (req, res) => {
    try {
      const endpointName = process.env.DATABRICKS_SERVING_ENDPOINT_NAME;
      if (!endpointName) {
        res.status(500).json({ error: "DATABRICKS_SERVING_ENDPOINT_NAME not set" });
        return;
      }
      const { host, headers } = await getServingHeaders();
      const payload = buildAgentPayload(req.body, false);
      const upstream = await fetch(
        `${host}/serving-endpoints/${endpointName}/invocations`,
        { method: "POST", headers, body: JSON.stringify(payload) },
      );
      const text = await upstream.text();
      res.status(upstream.status).type(upstream.headers.get("content-type") ?? "application/json").send(text);
    } catch (err) {
      console.warn(`[serving proxy] invoke error: ${err}`);
      res.status(500).json({ error: "Serving invoke failed" });
    }
  });

  app.post("/api/serving/stream", async (req, res) => {
    try {
      const endpointName = process.env.DATABRICKS_SERVING_ENDPOINT_NAME;
      if (!endpointName) {
        res.status(500).json({ error: "DATABRICKS_SERVING_ENDPOINT_NAME not set" });
        return;
      }
      const { host, headers } = await getServingHeaders();
      const payload = buildAgentPayload(req.body, true);
      const upstream = await fetch(
        `${host}/serving-endpoints/${endpointName}/invocations`,
        { method: "POST", headers, body: JSON.stringify(payload) },
      );
      if (!upstream.ok || !upstream.body) {
        const text = await upstream.text();
        res.status(upstream.status).send(text);
        return;
      }
      res.setHeader("Content-Type", "text/event-stream");
      res.setHeader("Cache-Control", "no-cache");
      res.setHeader("Connection", "keep-alive");
      const reader = upstream.body.getReader();
      const decoder = new TextDecoder();
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        res.write(decoder.decode(value, { stream: true }));
      }
      res.end();
    } catch (err) {
      console.warn(`[serving proxy] stream error: ${err}`);
      res.write(`data: ${JSON.stringify({ error: String(err) })}\n\n`);
      res.end();
    }
  });
});

await AppKit.server.start();
```

> **`autoStart: false` is required** — `server.extend()` must run before the server begins listening. Same pattern as the Lakebase wiring skill.

---

## Step 5: Frontend Consumption

The proxy above is URL-compatible with the AppKit hooks, so when the plugin eventually ships you can delete the proxy and the frontend keeps working. In the meantime, use raw `fetch` + `ReadableStream` for streaming:

```typescript
async function streamAgent(messages: { role: string; content: string }[], onDelta: (text: string) => void) {
  const res = await fetch("/api/serving/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages }),
  });
  if (!res.ok || !res.body) throw new Error(`stream failed: ${res.status}`);
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split("\n\n");
    buffer = events.pop() ?? "";
    for (const ev of events) {
      const line = ev.split("\n").find((l) => l.startsWith("data: "));
      if (!line) continue;
      const payload = line.slice(6);
      if (payload === "[DONE]") return;
      try {
        const chunk = JSON.parse(payload);
        // Dual-format parser — see references/sse-format-patterns.md
        const delta =
          chunk.type === "response.output_text.delta"
            ? chunk.delta ?? ""
            : chunk.choices?.[0]?.delta?.content ?? "";
        if (delta) onDelta(delta);
      } catch {
        // Partial chunk or non-JSON keepalive — ignore
      }
    }
  }
}
```

For the streaming chunk format details (and why the dual parser is required), read [sse-format-patterns.md](sse-format-patterns.md) before writing the frontend parser.

---

## Gotchas

| Gotcha | Fix |
|--------|-----|
| `TypeError: config.getToken is not a function` | AppKit `Config` has `authenticate(headers)`, not `getToken()`. Use the `getServingHeaders` pattern above. |
| `TypeError: Failed to parse URL` when calling the endpoint | `process.env.DATABRICKS_HOST` may lack `https://`. Use `config.host` (pre-resolved). |
| `400: Model is missing inputs ['input']` | Forwarded `{ messages }` directly. Transform to `{ input }` with `buildAgentPayload`. |
| Streaming returns 200 but UI stays blank | Parser only reads `choices[0].delta.content`. Add the `response.output_text.delta` branch — see `sse-format-patterns.md`. |
| Routes not registered after deploy | `server({ autoStart: false })` missing, or `server.extend()` called after `start()`. Extend first, then start. |
| 401 from the endpoint in production | OBO token not flowing through. Confirm you are calling `getExecutionContext()` inside the request handler (per-request), not at module scope. |
| `serving-endpoint` resource missing | App SP lacks `CAN_QUERY`. Add the resource in `databricks.yml` — see `04-appkit-plugin-add/references/plugin-serving.md`. |

---

## When to Retire This Proxy

Once `serving()` ships in a version of AppKit your platform npm registry can resolve, delete the proxy routes and the `buildAgentPayload` / `getServingHeaders` helpers, and add `serving()` to the plugins array per `SKILL.md` Step 3. The frontend hooks (`useServingStream`, `useServingInvoke`) continue to work without any UI changes because this proxy uses the same URL surface.
