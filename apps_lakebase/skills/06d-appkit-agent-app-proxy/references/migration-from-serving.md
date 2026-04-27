# Migrating from `06-appkit-serving-wiring` to `06d-appkit-agent-app-proxy`

Use this reference when an AppKit app was originally wired against a **Model Serving endpoint** ([`06-appkit-serving-wiring`](../../06-appkit-serving-wiring/SKILL.md)) and the underlying agent has been (or is being) redeployed as a **Databricks App** per [migrate-agent-to-apps](https://docs.databricks.com/aws/en/generative-ai/agent-framework/migrate-agent-to-apps).

**Symptoms that signal a needed migration:**

- `/api/serving/invoke` or `/api/serving/stream` returns `404: Cannot find serving endpoint` after the agent was redeployed.
- The Databricks Apps UI shows the old `serving-endpoint` resource as **unbound** or **deleted**.
- `databricks serving-endpoints get <name>` reports the endpoint is gone.
- You see a "Migrate agent to Apps" banner in the workspace.

---

## Before You Start

Confirm the new Agent App is deployed and healthy:

```bash
databricks apps get "$AGENT_APP_NAME" --profile "$PROFILE" --output json | jq '{state: .status.state, url: .url}'
```

Expect `{"state": "RUNNING", "url": "https://..."}`. If the Agent App doesn't exist yet, complete [Track A 07-deploy-and-query](../../../../genai-agents/tracks/A-custom-agent-apps/07-deploy-and-query/SKILL.md) with `target=databricks_apps` first, then return here.

---

## Migration Steps

### Step 1 — Swap the Bundle Resource

In `databricks.yml`, replace the `serving_endpoint` resource with an `app` resource.

**Before:**

```yaml
resources:
  apps:
    ${var.appkit_app_name}:
      resources:
        - name: serving-endpoint
          description: Agent serving endpoint
          serving_endpoint:
            name: ${var.serving_endpoint_name}
            permission: CAN_QUERY
```

**After:**

```yaml
resources:
  apps:
    ${var.appkit_app_name}:
      resources:
        - name: agent-backend
          description: Agent App this AppKit dashboard proxies to
          app:
            name: ${var.agent_app_name}
            permission: CAN_USE
```

Also rename the variable:

```yaml
variables:
  # remove:
  #   serving_endpoint_name:
  #     description: Agent serving endpoint name
  # add:
  agent_app_name:
    description: Name of the Agent App (deployed per Track A 07-deploy-and-query)
```

Validate:

```bash
databricks bundle validate --profile "$PROFILE"
```

See [`app-resource-declaration.md`](app-resource-declaration.md) for the full rationale and schema-check command.

### Step 2 — Swap the Env Var in `app.yaml`

**Before:**

```yaml
env:
  - name: DATABRICKS_SERVING_ENDPOINT_NAME
    valueFrom: serving-endpoint
```

**After:**

```yaml
env:
  - name: AGENT_APP_URL
    valueFrom: agent-backend
```

If you have a local `.env` for `npm run dev`, update it too:

```env
# remove:
# DATABRICKS_SERVING_ENDPOINT_NAME=old-endpoint-name
# add:
AGENT_APP_URL=https://<agent-app-name>-<workspace-id>.apps.databricks.com
```

### Step 3 — Drop the `serving()` Plugin

In `server/server.ts`, remove the plugin registration. The Agent App doesn't benefit from Serving plugin features (type generation, alias routing, `.asUser(req)`) because the URL shape and auth model differ.

**Before:**

```typescript
import { createApp, server, serving } from "@databricks/appkit";

await createApp({
  plugins: [server(), serving()],
});
```

**After:**

```typescript
import { createApp, server } from "@databricks/appkit";
import { proxyAgentChat } from "./agent-proxy";

const AppKit = await createApp({
  plugins: [server({ autoStart: false })],
});

AppKit.server.extend((app) => {
  app.post("/api/chat", proxyAgentChat);
});

await AppKit.server.start();
```

### Step 4 — Create `server/agent-proxy.ts`

Follow [../SKILL.md](../SKILL.md) Step 2. The handler is the two-layer auth pattern from [`obo-forwarding.md`](obo-forwarding.md).

### Step 5 — Rename Frontend Routes

The Serving plugin registered `/api/serving/invoke` and `/api/serving/stream`. The 06d proxy registers `/api/chat`. Update all frontend fetch calls:

**Before (React):**

```tsx
const { stream } = useServingStream({ messages }, { alias: "agent" });
```

**After:**

```tsx
import { useAgentChat } from "./useAgentChat";
const { messages, send, streaming } = useAgentChat();
```

Full hook source is in [../SKILL.md](../SKILL.md) Step 4a. Delete `useServingStream` / `useServingInvoke` imports from `@databricks/appkit-ui/react` unless other endpoints still use them.

### Step 6 — Update the Dual-Format Parser (if needed)

The Responses-API branch in your parser is still useful — Agent Apps emit the same shape as `ResponsesAgent`-served endpoints. If your parser was already dual-format per [`06/references/sse-format-patterns.md`](../../06-appkit-serving-wiring/references/sse-format-patterns.md), keep it. Otherwise replace it with the extractor in [`dual-format-streaming.md`](dual-format-streaming.md).

### Step 7 — Delete the Old Serving Endpoint (optional)

Once the Agent App path is verified in production, clean up:

```bash
databricks serving-endpoints delete "$OLD_SERVING_ENDPOINT_NAME" --profile "$PROFILE"
```

This is optional — you may want to keep the endpoint as a fallback during rollout. If you keep it, remove it from the bundle so it's not re-applied.

### Step 8 — Re-deploy and Re-approve Resource Bindings

```bash
databricks bundle deploy --profile "$PROFILE"
databricks apps deploy --profile "$PROFILE"
```

The first deploy after swapping to `app` resources may require **resource-binding approval** in the Databricks Apps UI — the AppKit SP needs explicit `CAN_USE` consent on the Agent App. Visit **AppKit App → Resources** and approve pending bindings.

### Step 9 — Verify

Run the 06d end-to-end probes:

```bash
bash apps_lakebase/skills/06d-appkit-agent-app-proxy/scripts/test-agent-app-proxy.sh \
  --appkit-app "$APPKIT_APP_NAME" \
  --agent-app "$AGENT_APP_NAME" \
  --profile "$PROFILE"
```

All three probes (direct Agent App, AppKit SP-only, AppKit with forwarded user token) must pass.

---

## Side-by-Side Summary

| Layer | 06 (Model Serving) | 06d (App Backend) |
|-------|--------------------|---------------------|
| Resource kind in `databricks.yml` | `serving_endpoint` | `app` |
| Resource permission | `CAN_QUERY` | `CAN_USE` |
| Env var | `DATABRICKS_SERVING_ENDPOINT_NAME` (name) | `AGENT_APP_URL` (full URL) |
| AppKit plugin | `serving()` | none (vanilla `server.extend`) |
| Frontend hook | `useServingStream` | custom `useAgentChat` |
| Route | `/api/serving/:alias/stream` | `/api/chat` |
| Upstream URL | `/serving-endpoints/:name/invocations` | `<AGENT_APP_URL>/invocations` |
| End-user auth | Serving plugin's `.asUser(req)` | explicit `x-forwarded-access-token` forward |
| App-to-App auth | Implicit via plugin | explicit `config.authenticate(headers)` |

---

## Rollback

If the migration fails and you need to roll back:

1. Re-add the `serving_endpoint` resource to `databricks.yml`.
2. Restore `DATABRICKS_SERVING_ENDPOINT_NAME` in `app.yaml`.
3. Re-register the `serving()` plugin.
4. Restore frontend `useServingStream` usage.
5. `databricks bundle deploy` + `databricks apps deploy`.

This only works if you did **not** delete the old Serving endpoint in Step 7.

---

## Common Migration Mistakes

| Mistake | Why It Fails | Fix |
|---------|--------------|-----|
| Kept `serving_endpoint` resource alongside new `app` resource | Platform still maps `SERVING_ENDPOINT` env var; proxy ambiguity | Delete the old resource |
| Forgot to drop `serving()` plugin | Auto-registered routes 404 against Agent App | Remove the import + plugin entry |
| Left `/api/serving/stream` in frontend | Hits the Serving plugin auto-route (which now fails) | Rename to `/api/chat` |
| Kept `DATABRICKS_SERVING_ENDPOINT_NAME` in `app.yaml` | Harmless but confusing; looks like the app still needs it | Delete |
| Didn't approve resource binding | `/api/chat` 403 with `App not authorized` | Visit Apps UI → Resources → Approve |
| Kept `serving_endpoint_name` in state files | Breaks state schema consistency with the walkthrough | Rename to `agent_app_url` + `agent_app_name` |

---

## References

- [Migrate an agent to Databricks Apps](https://docs.databricks.com/aws/en/generative-ai/agent-framework/migrate-agent-to-apps) — upstream guide, always take precedence
- [`../SKILL.md`](../SKILL.md) — the target skill for the migrated app
- [`obo-forwarding.md`](obo-forwarding.md) — new auth model
- [`app-resource-declaration.md`](app-resource-declaration.md) — new resource form
- [`dual-format-streaming.md`](dual-format-streaming.md) — SSE parser (often reusable from the old 06 wiring)
- [apps_lakebase/skills/06-appkit-serving-wiring/SKILL.md](../../06-appkit-serving-wiring/SKILL.md) — old wiring, for reference while migrating
