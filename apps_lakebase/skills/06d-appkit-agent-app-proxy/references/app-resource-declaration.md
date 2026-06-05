# Declaring an Agent App as an `app` Resource

How to bind an Agent App as a backend resource for an AppKit App, both via Databricks Asset Bundles (`databricks.yml`) and via the Databricks Apps UI. This is the **correct** resource type for the 2-Apps pattern — not `serving_endpoint`.

**When to read this:** Reading [../SKILL.md](../SKILL.md) and reached Step 1. Stop and read this file first.

> **Client routing:** the `databricks.yml` / `app.yaml` edits are client-agnostic. On **Genie Code**, run `databricks bundle validate` via `runDatabricksCli` (**omit `--profile`**; if a targetless validate is guardrail-blocked, pass `--target dev`); the Apps-UI form is browser-based and works on both clients. See [`../SKILL.md`](../SKILL.md) routing table and `skills/genie-code-environment`.

---

## Why `app`, Not `serving_endpoint`

The Databricks Apps platform models cross-resource permissions as typed resource bindings. For an Agent App backend, you want:

| What | Value |
|------|-------|
| Resource kind | `app` |
| Permission | `CAN_USE` |
| Inferred env var | `APP_URL_<resource_name_upper_snake>` (platform default) |
| Recommended explicit env var | `AGENT_APP_URL` via `valueFrom: <resource-name>` |

Using `serving_endpoint` instead:

- Targets a Model Serving endpoint URL shape (`/serving-endpoints/:name/invocations`), which the Agent App does not expose.
- Grants `CAN_QUERY`, which has no meaning against an App.
- Injects `SERVING_ENDPOINT=<name>`, not a URL — the plugin must resolve via CLI, which fails at runtime with `Cannot find serving endpoint <name>`.

---

## `databricks.yml` — Canonical Fragment

Inside the AppKit App's bundle file:

```yaml
variables:
  agent_app_name:
    description: Name of the Agent App (deployed per Track A 07-deploy-and-query)
  appkit_app_name:
    description: Name of this AppKit App

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

The **`name: agent-backend`** string is the key — `app.yaml` references it in `valueFrom:` and the platform derives the env var from it.

### Verify the schema supports `app:`

CLI versions older than `0.295.0` may not accept the `app` resource type. Confirm:

```bash
databricks bundle schema | jq '.definitions.AppResource_APP // empty'
```

Expected output is a non-empty JSON object describing `name` and `permission`. If empty, upgrade the CLI:

```bash
# macOS
brew upgrade databricks

# or direct
curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh
```

### Validate before deploy

```bash
databricks bundle validate --profile $PROFILE
```

If you see:

```
Error: unknown field: app
```

…your CLI is too old. Upgrade and re-run.

---

## `app.yaml` — Env Var Mapping

The bundle alone is not enough — the AppKit container needs an env var that points at the Agent App URL.

```yaml
env:
  - name: AGENT_APP_URL
    valueFrom: agent-backend
```

Three things to know about `valueFrom`:

1. It looks up the resource by the `name` you set in `databricks.yml` (here, `agent-backend`).
2. For `app` resources, the resolved value is the **full HTTPS URL** of the App (including `https://` and the subdomain).
3. The platform may append a trailing `/` depending on CLI version. The proxy strips it — see [obo-forwarding.md](obo-forwarding.md).

### If you skip `valueFrom`

The platform injects a default-named env var for every bound resource, roughly `APP_URL_AGENT_BACKEND` (uppercased resource name with underscores). **Do not rely on this** — it changes across CLI versions and is not documented as stable. Always declare `AGENT_APP_URL` explicitly via `valueFrom`.

---

## Apps UI Equivalent (No Bundle)

If the AppKit App is managed via the Apps UI rather than DABs:

1. Navigate to the AppKit App → **Settings → Resources**.
2. Click **Add resource** → **App**.
3. Select the Agent App from the dropdown.
4. Set **Resource name** to `agent-backend` (must match whatever `valueFrom` expects).
5. Set **Permission** to `CAN_USE`.
6. Save.

Then edit **Settings → Environment variables**:

- Name: `AGENT_APP_URL`
- Source: **From resource** → select the `agent-backend` resource.

Deployment must be re-triggered for the resource binding to take effect.

---

## Local Development

For `npm run dev`, the platform is not present. Set `AGENT_APP_URL` in `.env`:

```env
AGENT_APP_URL=https://<agent-app-name>-<workspace-id>.apps.databricks.com
```

Retrieve the URL with:

```bash
databricks apps get "$AGENT_APP_NAME" --profile "$PROFILE" --output json | jq -r '.url'
```

The AppKit proxy uses the same `/invocations` path regardless of environment, so local dev points at the deployed Agent App for end-to-end tests.

---

## Gotchas

| Gotcha | Symptom | Fix |
|--------|---------|-----|
| Used `serving_endpoint` resource type | `AGENT_APP_URL` empty or `SERVING_ENDPOINT` set instead | Switch to `app:` — see above |
| Resource name mismatch between `databricks.yml` and `app.yaml` `valueFrom` | `AGENT_APP_URL` empty at runtime | Both must read `agent-backend` (or whatever name you chose) |
| `CAN_QUERY` on an `app` resource | `bundle validate` fails: `permission "CAN_QUERY" not allowed for resource type "app"` | Use `CAN_USE` |
| CLI rejects `app:` block | `unknown field: app` at validate time | Upgrade CLI to `0.295.0+` |
| Agent App not deployed first | `agent_app_name` resolves to a not-yet-existing App; bundle deploys but env var is empty | Deploy Agent App (Track A Prompt 17) **before** deploying AppKit App |
| Trailing slash on `AGENT_APP_URL` | `POST /invocations/invocations` 404 | Proxy strips it; if you're calling manually in a script, strip before concatenation |

---

## References

- [Databricks Apps resources](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/resources)
- [Databricks Asset Bundles schema](https://docs.databricks.com/aws/en/dev-tools/bundles/resources.html)
- [apps_lakebase/skills/03-appkit-deploy/SKILL.md](../../03-appkit-deploy/SKILL.md)
- [apps_lakebase/skills/04-appkit-plugin-add/references/plugin-serving.md](../../04-appkit-plugin-add/references/plugin-serving.md) — the `serving_endpoint` counterpart, for comparison
