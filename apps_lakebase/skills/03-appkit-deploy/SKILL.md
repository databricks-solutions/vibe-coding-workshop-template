---
name: 03-appkit-deploy
description: >
  Deploy a Databricks AppKit application to Databricks Apps. Covers config
  validation, build verification, deployment, UI verification, error diagnosis
  with fix loop, and workspace app limit handling. Use when asked to deploy an
  AppKit app, push to production, ship the app, or troubleshoot a failed deploy.
  Triggers on "deploy app", "push to databricks", "ship app", "deploy appkit",
  "databricks apps deploy", "fix deploy error", "app won't start".
license: Apache-2.0
compatibility: Requires a built AppKit project with Node.js v22+ and Databricks CLI >= 0.295.0
allowed-tools: Bash(databricks:*) Bash(npm:*) Bash(curl:*) Bash(node:*) Read
metadata:
  author: prashanth subrahmanyam
  version: "1.1.0"
  domain: apps
  role: deploy
  standalone: true
  last_verified: "2026-04-12"
  volatility: medium
  upstream_sources:
    - https://github.com/databricks/databricks-agent-skills/blob/main/skills/databricks-apps/SKILL.md
    - https://github.com/databricks/databricks-agent-skills/tree/main/skills/databricks-apps/references/appkit
    - https://databricks.github.io/appkit/docs/app-management
    - https://databricks.github.io/appkit/docs/configuration
    - https://databricks.github.io/appkit/docs/development/project-setup
    - https://databricks.github.io/appkit/docs/development/llm-guide
    - https://docs.databricks.com/aws/en/dev-tools/databricks-apps/deploy
    - https://docs.databricks.com/aws/en/dev-tools/databricks-apps/app-runtime
---

# Deploy Databricks AppKit Applications

Deploy an AppKit project to Databricks Apps, verify it runs, and fix common errors.

## When to Use

- Deploying an AppKit app to Databricks Apps (first deploy or redeployment)
- Verifying a deployed app loads correctly
- Diagnosing and fixing deploy failures
- Freeing workspace app slots when the limit is reached

**Not for scaffolding.** Use `01-appkit-scaffold` to create a new project.
**Not for building features.** Use `02-appkit-build` to implement UI and backend code.

## Prerequisites

Before deploying, ensure:

- The app builds locally (`npm run build` succeeds)
- `$APP_NAME` and `$PROFILE` are set by the calling prompt
- The app directory contains `app.yaml` and `databricks.yml`
- If deploying to a **different workspace** than where the app was scaffolded: update the `host` in `databricks.yml`, update `sql_warehouse_id` for the new workspace, and remove stale bundle state with `rm -rf $APP_NAME/.databricks`
- If no CLI profile exists for the target workspace, create one with `databricks auth login --host <workspace-url>` (NOT `databricks configure`, which requires interactive token input and fails in automated/agent contexts)

---

## Before You Begin

**The upstream Databricks agent-skills repo and AppKit docs are the source of truth for deploy commands, platform rules, and options.**

- **Agent Skills (deploy patterns, platform rules):** https://github.com/databricks/databricks-agent-skills/blob/main/skills/databricks-apps/SKILL.md
- **Platform guide (SP permissions, runtime constraints, errors):** https://github.com/databricks/databricks-agent-skills/blob/main/skills/databricks-apps/references/platform-guide.md
- **App management:** https://databricks.github.io/appkit/docs/app-management
- **Configuration:** https://databricks.github.io/appkit/docs/configuration
- **AppKit docs (in-terminal):** `npx @databricks/appkit docs "app-management"`
- **CLI help:** `databricks apps deploy --help`

The bundled reference at [references/app-management.md](references/app-management.md) covers commonly used commands as a fallback when live docs cannot be reached.

> **Do NOT improvise workarounds.** If a deployment fails, check the app logs and match
> the error against the Common Errors table below. Do NOT add npm lifecycle hooks
> (`preinstall`, `postinstall`), platform-detection conditionals, or workarounds that skip
> the platform's build pipeline. These consistently cause cascading failures that are harder
> to diagnose than the original error. When in doubt, consult the authoritative sources above.

---

## Authoritative References

The [databricks-agent-skills](https://github.com/databricks/databricks-agent-skills) repository contains the canonical AppKit deployment patterns. When in doubt, consult these references:

| Topic | Reference |
|-------|-----------|
| AppKit scaffolding, validation, workflow | [databricks-apps SKILL.md](https://github.com/databricks/databricks-agent-skills/blob/main/skills/databricks-apps/SKILL.md) |
| Platform rules (SP permissions, runtime limits, common errors) | [platform-guide.md](https://github.com/databricks/databricks-agent-skills/blob/main/skills/databricks-apps/references/platform-guide.md) |
| AppKit project structure and checklists | [appkit/overview.md](https://github.com/databricks/databricks-agent-skills/blob/main/skills/databricks-apps/references/appkit/overview.md) |
| Lakebase pool, CRUD, schema ownership | [appkit/lakebase.md](https://github.com/databricks/databricks-agent-skills/blob/main/skills/databricks-apps/references/appkit/lakebase.md) |
| Smoke tests and Playwright guidance | [testing.md](https://github.com/databricks/databricks-agent-skills/blob/main/skills/databricks-apps/references/testing.md) |
| AppKit docs (in-terminal) | `npx @databricks/appkit docs "app-management"` |

### Platform Constraints (from platform-guide.md)

These runtime constraints affect deployment and troubleshooting:

- **Startup timeout:** App must start within 10 minutes (including dependency installation)
- **HTTP proxy timeout:** 120 seconds per request (not configurable; use WebSockets for long operations)
- **Max apps per workspace:** 100
- **Max file size:** 10 MB per file in bundle
- **Filesystem:** Ephemeral — no persistent local storage; use UC Volumes or Lakebase
- **No shell in `command`:** `app.yaml` `command` does not run in a shell; env vars outside `app.yaml` are inaccessible
- **Graceful shutdown:** SIGTERM → 15 seconds → SIGKILL
- **Logging:** Only stdout/stderr captured; file-based logs are lost on container recycle
- **Destructive updates:** `bundle run` / `apps update` does full replacement and can wipe OBO scopes

### Platform Build Pipeline

When `databricks apps deploy` pushes code to the platform, the following sequence runs inside the container:

1. **Download source** — workspace files are extracted into `/home/app/`
2. **`npm install`** — installs dependencies from `package.json` / `package-lock.json`. Runs in **production mode** (`NODE_ENV=production`), so `devDependencies` are skipped.
3. **`npm run build`** (if the `build` script exists) — compiles the project. `prebuild` hooks fire automatically before this step.
4. **Run `command`** — executes the `command` from `app.yaml` (e.g., `npm run start`)

**Hard timeout:** The entire sequence (steps 1-4) must complete within **10 minutes**. If npm install or build exceeds this, the deploy fails with `App process did not start within 10 minutes`.

**Critical rules:**

- **NEVER** add `preinstall` or `postinstall` scripts that modify `node_modules`. These create infinite loops or corrupt the install.
- **NEVER** add platform-detection conditionals (e.g., `[ "$HOME" = '/home/app' ]`) to skip build steps.
- **NEVER** modify the scaffold's `package.json` dependency versions, aliases, or overrides. If `rolldown-vite`, `@playwright/test`, or other packages were included by `databricks apps init`, leave them as-is — the scaffold is tested to deploy on the platform.
- **DO** let scaffolded `prebuild` hooks run (`appkit sync`, `appkit generate-types`). Warnings about `@ast-grep/napi` are harmless and guarded by `2>/dev/null; true`.
- **DO** note that `databricks bundle deploy` (and `databricks apps deploy` which calls it internally) uses `.gitignore` patterns for file exclusion — NOT `.databricksignore`.

**Authoritative source:** [Databricks Apps deploy — deployment logic](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/deploy) and [post-deployment behavior](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/app-runtime).

---

## Step 1: Validate Configuration

Verify `app.yaml` has a startup command:

```bash
grep -E "build/index\.mjs|npm.*start" $APP_NAME/app.yaml
```

Accepted patterns:

- `command: ['npm', 'run', 'start']` — AppKit default (scaffold output)
- `command: [node, build/index.mjs]` — legacy / alternative

If using `npm run start`, verify the `start` script in `package.json` points to the correct built output (e.g., `node dist/server.js`).

If no startup command is present, add the default:

```yaml
command:
  - npm
  - run
  - start
```

Check that required environment bindings are present. At minimum, apps using the analytics plugin need:

```bash
grep "DATABRICKS_WAREHOUSE_ID" $APP_NAME/app.yaml
```

You should see `valueFrom: sql-warehouse`. If missing, add it:

```yaml
env:
  - name: DATABRICKS_WAREHOUSE_ID
    valueFrom: sql-warehouse
```

The calling prompt may require additional plugin-specific env vars (e.g., `LAKEBASE_ENDPOINT` for Lakebase). Validate those before proceeding.

Also verify `app.yaml` and `databricks.yml` both reference the correct `$APP_NAME`:

```bash
grep "name:" $APP_NAME/app.yaml
grep "name:" $APP_NAME/databricks.yml | head -1
```

Run the AppKit validator to check `app.yaml` schema, resource bindings, and manifest validity:

```bash
cd $APP_NAME && databricks apps validate --profile $PROFILE
```

Fix any reported errors before proceeding.

**Cross-validate `valueFrom` references against `databricks.yml` resources.** Every `valueFrom:` in `app.yaml` must have a matching resource declaration in `databricks.yml`. If not, `databricks apps deploy` (which runs `bundle deploy` internally) will fail to resolve the resource and the env var will be empty at runtime.

```bash
for ref in $(grep 'valueFrom:' $APP_NAME/app.yaml | awk '{print $2}'); do
  if ! grep -q "$ref" $APP_NAME/databricks.yml 2>/dev/null; then
    echo "ERROR: app.yaml references valueFrom: $ref but no matching resource in databricks.yml"
    echo "  bundle deploy will strip manually-attached resources. Add the resource to databricks.yml."
  fi
done
```

This catches the common failure where Lakebase `postgres` resources were attached via REST API or `databricks apps update` but not declared in `databricks.yml` — `bundle deploy` resets the resource list on every deploy, stripping anything not in the bundle config.

**Check for pre-existing Lakebase projects that conflict with bundle declarations.** If `databricks.yml` declares `postgres_projects` but the project already exists on the platform, `bundle deploy` will fail with a Terraform "already exists" error.

```bash
PROJECT_ID=$(grep -A2 'postgres_projects:' $APP_NAME/databricks.yml | grep 'project_id:' | awk '{print $2}' | tr -d "'" | tr -d '"')
if [ -n "$PROJECT_ID" ]; then
  EXISTS=$(databricks postgres list-projects --profile $PROFILE --output json 2>/dev/null \
    | jq -e --arg pid "$PROJECT_ID" '[.[] | select(.name | contains($pid))] | length > 0' 2>/dev/null)
  if [ "$EXISTS" = "true" ]; then
    echo "WARNING: Lakebase project '$PROJECT_ID' already exists on the platform."
    echo "  Remove postgres_projects (and postgres_branches/postgres_endpoints) from databricks.yml"
    echo "  to avoid 'already exists' Terraform errors. Keep only app.resources.postgres binding."
  fi
fi
```

---

## Step 2: Build

Run `npm run build` locally to catch TypeScript and compilation errors early. The deploy pipeline rebuilds on the platform, but catching errors locally avoids a slow deploy-fail-fix cycle.

```bash
cd $APP_NAME
npm run build
```

This must complete without errors. A successful build produces the output referenced by `app.yaml`'s command (typically `build/index.mjs` or `dist/server.js`).

Verify the build output exists before deploying:

```bash
ls build/index.mjs 2>/dev/null || ls dist/server.js 2>/dev/null || echo "WARNING: No build output found — check app.yaml command"
```

If there are TypeScript or build errors, fix them before proceeding.

---

## Step 3: Deploy

Deploy using the AppKit CLI pipeline — a single command that builds the frontend, syncs code to the workspace via bundle deploy, and starts the app:

```bash
cd $APP_NAME
databricks apps deploy --profile $PROFILE
```

This is equivalent to running `npm run build` + `databricks bundle deploy` + `databricks apps start` in sequence.

For faster iteration after the first deploy, skip the build step:

```bash
databricks apps deploy --skip-build --profile $PROFILE
```

> **Resource-sensitive deploys:** `databricks apps deploy` runs `bundle deploy` internally, which resets the app's resource list to match `databricks.yml`. If resources were added outside the bundle (e.g., via REST API), a bundle deploy removes them. In that case, sync code first with `databricks bundle deploy --profile $PROFILE`, then trigger a run separately with `databricks apps deploy --profile $PROFILE` (which rebuilds from the already-synced workspace source without resetting resources). If no code changes are needed, skip redeployment entirely.

For Lakebase Autoscaling, use `postgres_project`/`postgres_branch`/`postgres_endpoint` resources (CLI v0.287.0+) if you want bundle-managed project lifecycle. For Lakebase Provisioned, use `database_instance` + `app.resources[].database` (CLI v0.265.0+). Do not mix the two models.

Wait for completion — typically 1-3 minutes for redeployments, 3-5 minutes for first deploys. Do not treat longer waits as failures until 7+ minutes have elapsed.

Verify the app is running before proceeding:

```bash
databricks apps get $APP_NAME --output json --profile $PROFILE | jq '{status: .status.state, compute: .compute_status.state}'
```

> **Note:** `status.state` may be `null` for up to 60 seconds after deployment even when the app is healthy. The definitive health signal is `compute_status.state: "ACTIVE"` plus clean logs showing the server is listening. If `compute` is `ACTIVE` but `status` is `null`, the app is running — proceed to Step 4.

If `compute` is not `ACTIVE`, wait 30 seconds and re-check. Use `databricks apps logs $APP_NAME --follow --profile $PROFILE` to stream logs in real-time instead of polling repeatedly.

---

## Step 4: Verify UI Loads

Run `bash scripts/verify-deploy.sh $APP_NAME $PROFILE` to automate status polling, URL retrieval, and health check. Or verify manually:

```bash
APP_URL=$(databricks apps get $APP_NAME --output json --profile $PROFILE | jq -r '.url')
echo "App URL: $APP_URL"
```

Open `$APP_URL` in a browser. You should see the React application with your pages and components — not an error page or JSON.

If the page shows an error or doesn't load, proceed to Step 5.

---

## Testing Deployed App APIs

Databricks Apps require authentication for all API requests. Generate a bearer token before testing:

```bash
TOKEN=$(databricks auth token --profile $PROFILE | jq -r '.access_token')
curl -s -H "Authorization: Bearer $TOKEN" "$APP_URL/api/health" | jq .
```

If `curl` returns HTML (a login page) or 401, the token has expired. Re-run the `TOKEN=...` line to refresh it. Tokens are short-lived (~1 hour).

---

## Step 5: Check Logs and Fix Errors (up to 3 iterations)

Stream the app logs:

```bash
databricks apps logs $APP_NAME --tail-lines 100 --profile $PROFILE
```

If errors exist:

1. Identify the error from the log output
2. Apply the fix in the app directory
3. Redeploy: `databricks apps deploy --profile $PROFILE`
   - For config-only changes (e.g., `app.yaml` or `databricks.yml`): `databricks apps deploy --skip-build --profile $PROFILE`
4. Check logs again

If no errors: deployment is successful.

Repeat up to 3 times. If errors persist after 3 attempts, report them for manual investigation.

> **Before diagnosing errors:** Run `npx @databricks/appkit docs "app-management"` and `databricks apps deploy --help` for the latest CLI options and deployment behavior. These are the source of truth for deploy commands.

### Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `Cannot find module 'build/index.mjs'` | Build output missing or `app.yaml` command wrong | Verify `app.yaml` command matches the build output (see Step 1) and `npm run build` succeeds |
| `DATABRICKS_WAREHOUSE_ID is not set` | Analytics plugin can't find the warehouse | Add `valueFrom: sql-warehouse` for `DATABRICKS_WAREHOUSE_ID` in `app.yaml` |
| Connection refused / timeout on SQL queries | SQL warehouse starting up or stopped | Wait 30s and retry; check warehouse is running in the workspace |
| TypeScript / build errors during deploy | Compilation issues in `server/` or `client/` | Run `npm run build` locally, fix errors, redeploy |
| `ERR_MODULE_NOT_FOUND` for `@databricks/appkit` | Dependencies not installed | Verify `package.json` lists `@databricks/appkit` and `@databricks/appkit-ui`; redeploy |
| `databricks apps restart` -> command not found | `restart` subcommand does not exist | Always redeploy: `databricks apps deploy --profile $PROFILE`. There is no restart command. |
| App loses resources after `stop` then `start` | `stop`/`start` cycle detaches manually-attached resources (e.g., postgres) | Avoid `stop`/`start` for apps with non-bundle resources. Redeploy instead. |
| `databricks api put/patch` with complex JSON silently fails | The CLI `api` subcommand does not reliably handle nested JSON payloads | Use `curl` with bearer token for REST API calls that require complex JSON bodies |
| `error resolving resource postgres for env LAKEBASE_ENDPOINT: resource postgres not found` | `app.yaml` uses `valueFrom: postgres` but no `postgres` resource declared in `databricks.yml`; `bundle deploy` stripped manually-attached resources | Add `postgres_project`/`postgres_branch`/`postgres_endpoint` resources to `databricks.yml` app definition; see `05-appkit-lakebase-wiring` skill prerequisites |
| `app.yaml` syntax / validation error | Invalid YAML or bad `valueFrom` reference | Run `databricks apps validate --profile $PROFILE` to diagnose |
| Env vars not available at startup | `command` does not run in a shell; env vars outside `app.yaml` are inaccessible | Define all needed variables in `app.yaml`'s `env` section |
| `PERMISSION_DENIED` after deploy | SP missing permissions on declared resources | Ensure resources in `databricks.yml` have `permission` field; platform auto-grants on deploy |
| `File is larger than 10485760 bytes` | Bundled file exceeds 10 MB limit | Use `requirements.txt`/`package.json` for deps; do not bundle large artifacts |
| 504 Gateway Timeout | Request exceeded 120s proxy timeout | Use WebSockets for long operations; SSE may be buffered |
| OBO scopes missing after deploy | `apps update` / `bundle run` does full replacement, can wipe scopes | Re-apply OBO scopes after each deploy that modifies resources |

The calling prompt may define additional plugin-specific errors (e.g., Lakebase connection or permission errors). Check those if the errors above don't match.

---

## If the Workspace App Limit Is Reached

If deployment fails because the workspace has hit its app limit, do NOT rename your app. Instead, free up a slot by removing the oldest stopped app:

Find the oldest stopped app:

```bash
OLDEST=$(databricks apps list -o json --profile $PROFILE | jq -r '[.[] | select(.compute_status.state == "STOPPED")] | sort_by(.update_time) | .[0] | .name // empty')
if [ -z "$OLDEST" ]; then
  echo "No stopped apps to delete. Manual workspace cleanup needed."
else
  echo "Deleting oldest stopped app: $OLDEST"
  databricks apps delete "$OLDEST" --profile $PROFILE
  sleep 10
fi
```

Retry the deployment.

If the limit error persists, repeat with the next oldest stopped app — but stop after 3 total attempts (increase the wait to 20s, then 40s between retries). If it still fails after 3 tries, stop and report the issue for manual workspace cleanup. Never delete apps in RUNNING state.

---

## Quick Reference

| Task | Command |
|------|---------|
| Build | `npm run build` |
| Validate config | `databricks apps validate --profile $PROFILE` |
| Deploy (full) | `databricks apps deploy --profile $PROFILE` |
| Deploy (skip build) | `databricks apps deploy --skip-build --profile $PROFILE` |
| Sync code only (no restart) | `databricks bundle deploy --profile $PROFILE` |
| Get app URL | `databricks apps get $APP_NAME --output json --profile $PROFILE \| jq -r '.url'` |
| Stream logs | `databricks apps logs $APP_NAME --tail-lines 100 --profile $PROFILE` |
| Follow logs live | `databricks apps logs $APP_NAME --follow --profile $PROFILE` |
| Search logs | `databricks apps logs $APP_NAME --follow --search ERROR --profile $PROFILE` |
| Stop app | `databricks apps stop $APP_NAME --profile $PROFILE` |
| Start app | `databricks apps start $APP_NAME --profile $PROFILE` |
| Delete app | `databricks apps delete $APP_NAME --profile $PROFILE` |
| List all apps | `databricks apps list --profile $PROFILE` |
| AppKit deploy help | `databricks apps deploy --help` |
| Live docs | `npx @databricks/appkit docs "app-management"` |
