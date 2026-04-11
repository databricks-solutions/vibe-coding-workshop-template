---
name: appkit-deploy
description: >
  Deploy a Databricks AppKit application to Databricks Apps. Covers config
  validation, build verification, deployment, UI verification, error diagnosis
  with fix loop, and workspace app limit handling. Use when asked to deploy an
  AppKit app, push to production, ship the app, or troubleshoot a failed deploy.
  Triggers on "deploy app", "push to databricks", "ship app", "deploy appkit",
  "databricks apps deploy", "fix deploy error", "app won't start".
license: Apache-2.0
compatibility: Requires a built AppKit project with Node.js v22+ and Databricks CLI >= 0.295.0
metadata:
  author: prashanth subrahmanyam
  version: "1.0.0"
  domain: apps
  role: deploy
  standalone: true
  last_verified: "2026-04-10"
  volatility: medium
  upstream_sources:
    - https://databricks.github.io/appkit/docs/app-management
    - https://databricks.github.io/appkit/docs/configuration
    - https://github.com/databricks/databricks-agent-skills
---

# Deploy Databricks AppKit Applications

Deploy an AppKit project to Databricks Apps, verify it runs, and fix common errors.

## When to Use

- Deploying an AppKit app to Databricks Apps (first deploy or redeployment)
- Verifying a deployed app loads correctly
- Diagnosing and fixing deploy failures
- Freeing workspace app slots when the limit is reached

**Not for scaffolding.** Use `appkit-scaffold` to create a new project.
**Not for building features.** Use `appkit-build` to implement UI and backend code.

## Prerequisites

Before deploying, ensure:

- The app builds locally (`npm run build` succeeds)
- `$APP_NAME` and `$PROFILE` are set by the calling prompt
- The app directory contains `app.yaml` and `databricks.yml`
- If deploying to a **different workspace** than where the app was scaffolded: update the `host` in `databricks.yml`, update `sql_warehouse_id` for the new workspace, and remove stale bundle state with `rm -rf $APP_NAME/.databricks`

---

## Before You Begin

**The upstream AppKit docs are the source of truth for deploy commands and options.**

- **App management:** https://databricks.github.io/appkit/docs/app-management
- **Configuration:** https://databricks.github.io/appkit/docs/configuration
- **CLI help:** `databricks apps deploy --help`

The bundled reference at [references/app-management.md](references/app-management.md) covers commonly used commands as a fallback when live docs cannot be reached.

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

---

## Step 2: Build

```bash
cd $APP_NAME
npm run build
```

This must complete without errors. A successful build produces the output referenced by `app.yaml`'s command (typically `build/index.mjs` or `dist/server.js`).

Verify the build output exists before deploying:

```bash
# Check for the file that app.yaml's command references
ls dist/server.js 2>/dev/null || ls build/index.mjs 2>/dev/null || echo "WARNING: No build output found — check app.yaml command"
```

If there are TypeScript or build errors, fix them before proceeding.

---

## Step 3: Deploy

```bash
cd $APP_NAME
databricks apps deploy --profile $PROFILE
```

This single command runs the full pipeline:
1. Builds the frontend (`npm run build`)
2. Deploys the bundle to the workspace
3. Starts the app

Wait for completion — typically 1-3 minutes for redeployments, up to 5 minutes for first deploys.

Verify the app is running before proceeding:

```bash
databricks apps get $APP_NAME --output json --profile $PROFILE | jq '{status: .status.state, compute: .compute_status.state}'
```

If `compute` is not `ACTIVE` or `status` is not `RUNNING`, wait 30 seconds and re-check. Use `databricks apps logs $APP_NAME --follow --profile $PROFILE` to stream logs in real-time instead of polling repeatedly.

For faster iteration after the first deploy, use `--skip-build` if the code hasn't changed:

```bash
databricks apps deploy --skip-build --profile $PROFILE
```

---

## Step 4: Verify UI Loads

Get the deployed app URL:

```bash
APP_URL=$(databricks apps get $APP_NAME --output json --profile $PROFILE | jq -r '.url')
echo "App URL: $APP_URL"
```

Open `$APP_URL` in a browser. You should see the React application with your pages and components — not an error page or JSON.

If the page shows an error or doesn't load, proceed to Step 5.

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
   - For config-only changes (e.g., fixing `app.yaml` env vars or `databricks.yml` resources), use `--skip-build` to save 1-2 minutes: `databricks apps deploy --skip-build --profile $PROFILE`
4. Check logs again

If no errors: deployment is successful.

Repeat up to 3 times. If errors persist after 3 attempts, report them for manual investigation.

### Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `Cannot find module 'build/index.mjs'` | Build output missing or `app.yaml` command wrong | Verify `app.yaml` command matches the build output (see Step 1) and `npm run build` succeeds |
| `DATABRICKS_WAREHOUSE_ID is not set` | Analytics plugin can't find the warehouse | Add `valueFrom: sql-warehouse` for `DATABRICKS_WAREHOUSE_ID` in `app.yaml` |
| Connection refused / timeout on SQL queries | SQL warehouse starting up or stopped | Wait 30s and retry; check warehouse is running in the workspace |
| TypeScript / build errors during deploy | Compilation issues in `server/` or `client/` | Run `npm run build` locally, fix errors, redeploy |
| `ERR_MODULE_NOT_FOUND` for `@databricks/appkit` | Dependencies not installed | Verify `package.json` lists `@databricks/appkit` and `@databricks/appkit-ui`; redeploy |

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
| Deploy | `databricks apps deploy --profile $PROFILE` |
| Deploy (skip build) | `databricks apps deploy --skip-build --profile $PROFILE` |
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
