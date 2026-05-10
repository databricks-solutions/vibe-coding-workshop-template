## Context

You are a QA engineer deploying and running end-to-end tests for an AppKit web application with Lakebase. Your goal is to deploy the Lakebase-wired app to Databricks Apps (where the Service Principal creates database objects on first boot), verify Lakebase connectivity and API correctness, and test connection resilience after idle periods.

Key requirements:

- Validate Lakebase config in `app.yaml` before deploying
- Deploy using the `03-appkit-deploy` skill (SP creates schema/tables on first boot)
- Test all backend API endpoints with bearer token authentication
- Check app logs for healthy Lakebase connections
- Fix Lakebase-specific errors (up to 3 iterations)
- Optionally grant local dev permissions for post-deploy local testing
- Run the critical idle connection test (3-5 minutes idle, then re-test)
- Consult the [databricks-agent-skills references](https://github.com/databricks/databricks-agent-skills/tree/main/skills/databricks-apps/references/appkit) for Lakebase patterns, platform constraints, and testing guidance

CLI Best Practices:

- Run from `apps_lakebase/` or use `apps_lakebase/scripts/` for scripts
- Run CLI commands outside the IDE sandbox to avoid SSL/TLS certificate errors

This prompt is returned as-is for direct use in Cursor/Copilot. No LLM processing.

---

## Your Task

Deploy the Lakebase-wired web application to Databricks Apps and run comprehensive end-to-end testing. This is the first deploy with Lakebase code — the Service Principal will create the database schema, tables, and seed data on startup.

**First:** Read `apps_lakebase/$APP_NAME/.vibecoding-state.md` if it exists — it contains resolved issues and variable values from prior phases.

**Workspace:** `https://adb-4101016551133680.0.azuredatabricks.net/`

**Working directory:** All app paths and commands use the `apps_lakebase/` folder. The scaffolded AppKit app lives at `apps_lakebase/$APP_NAME/`.

**Prerequisite:** Complete the **Wire Lakebase Backend** step first. Local testing must pass with mock fallback data before deployment.

---

### Deployment Constraints

- Databricks App names must use only lowercase letters, numbers, and dashes (no underscores). Use hyphens: `my-app-name` not `my_app_name`.
- App names are max 26 characters.

---

### Step 1: Set Variables and Validate Lakebase Config

Derive your app name and auto-detect a CLI profile for the target workspace:

```bash
USER_JSON=$(databricks current-user me --output json)
EMAIL=$(echo "$USER_JSON" | jq -r '.userName')
FIRSTNAME=$(echo "$EMAIL" | cut -d'@' -f1 | cut -d'.' -f1)
LASTINITIAL=$(echo "$EMAIL" | cut -d'@' -f1 | cut -d'.' -f2 | cut -c1)
APP_PREFIX="${FIRSTNAME}-${LASTINITIAL}"
APP_NAME="${APP_PREFIX}-booking-app"

TARGET_HOST="https://adb-4101016551133680.0.azuredatabricks.net/"
PROFILE=$(databricks auth profiles --output json 2>/dev/null \
  | jq -r --arg host "$TARGET_HOST" \
    '[.profiles[] | select(.host == $host)] | .[0].name // empty')

if [ -z "$PROFILE" ]; then
  echo "No profile found for $TARGET_HOST — creating one..."
  databricks auth login --host "$TARGET_HOST"
  PROFILE=$(databricks auth profiles --output json 2>/dev/null \
    | jq -r --arg host "$TARGET_HOST" \
      '[.profiles[] | select(.host == $host)] | .[0].name // empty')
fi

echo "Using profile: $PROFILE"
```

Verify `app.yaml` has the Lakebase-specific environment variables (in addition to the generic checks the deploy skill performs):

```bash
grep "valueFrom.*postgres" apps_lakebase/$APP_NAME/app.yaml && echo "LAKEBASE_ENDPOINT: OK"
grep "postgres_project" apps_lakebase/$APP_NAME/databricks.yml && echo "Bundle resources: OK"
```

Then run the AppKit validator to catch schema or resource binding issues early:

```bash
cd apps_lakebase/$APP_NAME && databricks apps validate --profile $PROFILE
```

Fix any validation errors before deploying.

You should see `valueFrom: postgres` for `LAKEBASE_ENDPOINT` in `app.yaml` and `postgres_projects` in `databricks.yml`. The platform auto-injects `PGHOST`, `PGPORT`, `PGDATABASE`, `PGSSLMODE` from the bundle resource binding — these should NOT appear as static values in `app.yaml`.

> **Do NOT declare `postgres_branches` or `postgres_endpoints`** in `databricks.yml`. Lakebase Autoscaling auto-creates the default `production` branch and `primary` endpoint with the project. Declaring them causes Terraform "already exists" errors.

---

### Step 1b: Complete Lakebase Two-Phase Resource Binding

The **Setup Lakebase** step declared `postgres_projects` in `databricks.yml` (Phase 1). Before deploying, you must complete Phase 2: add the `app.resources.postgres` binding so `valueFrom: postgres` resolves at runtime.

**If this is the first deploy** (project does not exist yet), deploy once to create the project, then discover the database ID:

```bash
cd apps_lakebase/$APP_NAME
databricks apps deploy --profile $PROFILE
# Wait for deploy to complete, then:
DB_ID=$(databricks postgres list-databases projects/$APP_NAME/branches/production \
  --profile $PROFILE --output json | jq -r '.[0].name')
echo "Database ID: $DB_ID"
```

**If the project already exists** (from a prior deploy), just discover the database ID:

```bash
DB_ID=$(databricks postgres list-databases projects/$APP_NAME/branches/production \
  --profile $PROFILE --output json | jq -r '.[0].name')
echo "Database ID: $DB_ID"
```

Then add the `resources` array to your `apps.app` resource in `databricks.yml`:

```yaml
resources:
  apps:
    app:
      name: "<APP_NAME>"
      source_code_path: ./
      resources:
        - name: "postgres"
          postgres:
            branch: "projects/<APP_NAME>/branches/production"
            database: "projects/<APP_NAME>/branches/production/databases/<DB_ID>"
            permission: "CAN_CONNECT_AND_CREATE"
```

Replace `<APP_NAME>` with the actual app name and `<DB_ID>` with the discovered database ID (e.g., `db-jzmj-xj802bpntj`).

> **Why this matters:** `valueFrom: postgres` in `app.yaml` resolves against the **app's resource list** (`apps.app.resources`), not the top-level bundle resources (`postgres_projects`). Without `app.resources.postgres`, the platform cannot inject `LAKEBASE_ENDPOINT` and the app falls back to mock data silently.

For the full schema reference, see `@apps_lakebase/skills/04-appkit-plugin-add/references/plugin-lakebase.md` section "app.resources.postgres Schema Reference".

---

### Step 2: Deploy (SP Creates Database Objects)

Read and follow the `03-appkit-deploy` skill at `@apps_lakebase/skills/03-appkit-deploy/SKILL.md`. Run all skill commands from the `apps_lakebase/` directory.

The skill covers: config validation, build, deploy, UI verification, error diagnosis (3-iteration fix loop), and workspace app limit handling.

This is the first deploy with Lakebase code. The Service Principal runs the DDL in `server.ts` on startup, creating the schema, tables, and seed data. The SP owns all database objects it creates.

> **Deploy-first requirement (from [agent-skills lakebase.md](https://github.com/databricks/databricks-agent-skills/blob/main/skills/databricks-apps/references/appkit/lakebase.md)):** The SP must create the schema to own it. If you ran local dev before deploying, the schema is owned by your personal credentials and the SP cannot access it. In that case, drop the schema from the Lakebase SQL Console and redeploy.

> **SP permissions:** The Service Principal is auto-granted `CONNECT_AND_CREATE` via the `app.resources.postgres` binding (with `permission: CAN_CONNECT_AND_CREATE`). No manual grants are needed. If you see permission errors, verify the `app.resources.postgres` binding is declared in `databricks.yml` (see Step 1b).

**Timing:** First deploys take 3-5 minutes (npm install runs on the platform). Redeployments take 1-3 minutes. Use `databricks apps logs $APP_NAME --follow --profile $PROFILE` to stream logs in real-time instead of polling repeatedly.

**Important:** Always use `databricks apps deploy` — never `databricks apps start` — to push code changes. `databricks apps deploy` runs the full pipeline (build + bundle deploy + start). `apps start` only resumes a stopped app without updating code, and may hang if compute is in STOPPED state.

After the skill completes, verify the app status is RUNNING before testing:

```bash
databricks apps get $APP_NAME --output json --profile $PROFILE | jq '{status: .status.state, compute: .compute_status.state, url: .url}'

APP_URL=$(databricks apps get $APP_NAME --output json --profile $PROFILE | jq -r '.url')
echo "App URL: $APP_URL"
```

The primary readiness signal is `compute_status.state: ACTIVE`. `status.state` may remain `null` in some CLI versions or workspace configurations — this is normal and does not indicate a problem. If `compute` is not `ACTIVE`, wait 30 seconds and re-check.

**Warning:** `databricks bundle deploy` resets the app's resource list to match `databricks.yml`. If no code changes are needed since the **Wire Lakebase Backend** step, you may skip redeployment — the app is already running.

---

### Rule: Before Testing ANY API Endpoint

1. Read `server/server.ts` (or equivalent) to identify all registered routes, HTTP methods, and request body schemas
2. For POST/PUT endpoints, extract exact field names from the INSERT/UPDATE SQL statements
3. Construct test payloads that match the actual code — do NOT guess based on REST conventions
4. Only test routes that actually exist in the code

DO NOT guess request body fields or assume standard REST endpoints exist (e.g., `GET /api/bookings` may not exist even if `POST /api/bookings` does).

> **Smoke test selectors:** If the app includes `tests/smoke.spec.ts` (from AppKit scaffold), update heading and text selectors to match your app's actual content before running `databricks apps validate`. The default template assertions will fail for custom apps. See [testing.md](https://github.com/databricks/databricks-agent-skills/blob/main/skills/databricks-apps/references/testing.md).

---

### Step 3: Test All Backend APIs

Databricks Apps require authentication. Get a bearer token, then test:

```bash
TOKEN=$(databricks auth token --profile $PROFILE | jq -r '.access_token')
AUTH_HEADER="Authorization: Bearer $TOKEN"
```

> **Token expiry:** Databricks Apps bearer tokens can expire quickly. If any `curl` call returns an empty `{}` response, check the HTTP status code — it is likely 401 (expired token). The Databricks Apps proxy returns `{}` instead of a standard 401 body. Refresh the token before each test batch:
>
> ```bash
> TOKEN=$(databricks auth token --profile $PROFILE | jq -r '.access_token')
> ```

```bash
# Health endpoint (align with Genie workshop: GET /api/health)
curl -s -H "$AUTH_HEADER" "$APP_URL/api/health" | jq .

# Test each data endpoint used by your UI pages.
# Replace with your actual API endpoints:
curl -s -H "$AUTH_HEADER" "$APP_URL/api/orders" | jq .
# curl -s -H "$AUTH_HEADER" "$APP_URL/api/bookings" | jq .
# curl -s -H "$AUTH_HEADER" "$APP_URL/api/listings" | jq .
# ... add all endpoints that fetch from Lakebase
```

If `curl` returns HTML (a login page) or 401, the token may have expired. Re-run the `TOKEN=...` line to refresh it.

**Verify each response includes:**

- `"source": "live"` (not `"mock"`) when Lakebase is connected
- Actual data rows from your Lakebase tables
- Health endpoint returns wrapped JSON: `{ "data": [{ "status": "connected" }], "source": "live" }` (same contract as **`wire_ui_to_lakebase_gc.md`**)

If any endpoint returns `"source": "mock"`, there is a Lakebase connection issue — proceed to Step 5.

---

### Step 4: Check Logs for Lakebase Connections

```bash
databricks apps logs $APP_NAME --tail-lines 100 --search lakebase --profile $PROFILE
```

You should see INFO logs showing:

- `ConnectionPool initialised` — the Lakebase plugin started successfully
- Connection attempts to Lakebase (may include retries on first connect after scale-to-zero wake)
- `[Lakebase]` prefixed query logs with row counts for each endpoint

If the `--search` flag is not supported by your CLI version, fall back to:

```bash
databricks apps logs $APP_NAME --tail-lines 100 --profile $PROFILE | grep -i lakebase
```

---

### Step 5: Fix Lakebase Errors (up to 3 iterations)

If Lakebase-specific errors occur (the deploy skill already handles generic AppKit errors), check the logs:

```bash
databricks apps logs $APP_NAME --tail-lines 100 --profile $PROFILE
```

#### Lakebase-Specific Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `ERR_MODULE_NOT_FOUND` for `@databricks/lakebase` | Package not installed | Verify `@databricks/lakebase` is in `package.json` dependencies; redeploy |
| `error resolving resource postgres for env LAKEBASE_ENDPOINT: resource postgres not found` | `app.yaml` uses `valueFrom: postgres` but no `postgres` resource in `databricks.yml`; `bundle deploy` stripped it | Add the `app.resources.postgres` binding to `databricks.yml` (see Step 1b); redeploy |
| `LAKEBASE_ENDPOINT is not set` or `PGHOST is not set` | Missing app resource binding | Verify `valueFrom: postgres` in `app.yaml` and that `apps.app.resources` has a `postgres` entry in `databricks.yml` (see Step 1b); redeploy |
| `role "xxxxxxxx-xxxx-..." does not exist` | Service Principal lacks Lakebase role | Re-deploy the app so the SP re-creates and owns objects. If the SP was just created, grant via SQL (see Step 2 callout) |
| `permission denied for sequence` | SP lacks GRANT on sequences for SERIAL columns | Re-deploy the app so the SP re-creates objects, or grant manually: `GRANT ALL ON ALL SEQUENCES IN SCHEMA <DB_SCHEMA> TO "<sp-id>";` |
| `Connection attempt 1/5 failed` | Normal on first request — Lakebase autoscaling cold start | Wait and retry. The connection pool handles retries automatically |
| `token's identity did not match` | OAuth token mismatch | Verify `app.yaml` has correct static env vars; do NOT set `PGUSER` or `PGPASSWORD` manually |
| `permission denied for schema` / `must be owner of schema` | Schema owned by another identity (e.g., from a prior deploy or local dev) | Drop the schema (`DROP SCHEMA <DB_SCHEMA> CASCADE;`) from the Lakebase SQL Console and redeploy so the SP re-creates it |

> **Note:** If you previously ran an older version of the **Wire Lakebase Backend** step that deployed the app, you may have schema ownership conflicts. Drop the schema from the Lakebase SQL Console and redeploy to let the SP recreate it cleanly.

**Fix cycle:**

1. Identify the error from logs
2. Apply the fix in `apps_lakebase/$APP_NAME/`
3. Redeploy: `cd apps_lakebase/$APP_NAME && databricks apps deploy --profile $PROFILE`
4. Wait for the app to reach RUNNING state (stream logs with `databricks apps logs $APP_NAME --follow --profile $PROFILE`)
5. Re-test endpoints

Repeat up to 3 times. If errors persist after 3 attempts, report them for manual investigation.

---

### Step 6: Idle Connection Test (CRITICAL)

After confirming all endpoints return `"source": "live"`, wait 3-5 minutes without interacting with the app. Lakebase autoscaling instances may scale to zero during idle periods.

After waiting, reload the app in your browser and re-test:

```bash
TOKEN=$(databricks auth token --profile $PROFILE | jq -r '.access_token')
curl -s -H "Authorization: Bearer $TOKEN" "$APP_URL/api/health" | jq .
```

**Expected:** Still returns `"source": "live"`. The AppKit Lakebase plugin handles automatic OAuth token refresh and connection pool recovery.

If it returns `"source": "mock"` or the health check shows `"disconnected"`, check logs for `terminating connection` or `Connection attempt failed` errors:

```bash
databricks apps logs $APP_NAME --tail-lines 50 --profile $PROFILE
```

The connection pool should recover automatically after the autoscaling instance wakes. If it does not recover after 2-3 page reloads, verify pool settings configured in the **Wire Lakebase Backend** step (`lakebase({ pool: { ... } })` in `server.ts`).

---

### Step 7: Grant Local Development Permissions (Optional)

After deployment, you can optionally grant your Databricks identity access to the Lakebase database for local development against live data.

**Option 1: `databricks_superuser` via Lakebase UI (recommended — simpler)**

1. Open the Lakebase Autoscaling UI (Compute > Lakebase Postgres > your project)
2. Navigate to the Branch Overview page for `production`
3. Click **Add role** (or **Edit role** if your OAuth role already exists)
4. Select your Databricks identity as the principal and check the **`databricks_superuser`** system role

This grants full DML access (read/write) to all objects in the branch. `databricks_superuser` has DML access but NOT DDL (create schema/table) — the SP already created objects during deploy. Reference: [AppKit Lakebase docs - Local development](https://databricks.github.io/appkit/docs/plugins/lakebase#local-development)

**Option 2: Fine-grained SQL grants (for schema-level control)**

```sql
CREATE EXTENSION IF NOT EXISTS databricks_auth;

DO $$
DECLARE
  subject TEXT := '<YOUR_EMAIL>';
  schema TEXT := '<DB_SCHEMA>';
BEGIN
  PERFORM databricks_create_role(subject, 'USER');
  EXECUTE format('GRANT CONNECT ON DATABASE "databricks_postgres" TO %I', subject);
  EXECUTE format('GRANT ALL ON SCHEMA %s TO %I', schema, subject);
  EXECUTE format('GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA %s TO %I', schema, subject);
  EXECUTE format('GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA %s TO %I', schema, subject);
  EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA %s GRANT ALL ON TABLES TO %I', schema, subject);
  EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA %s GRANT ALL ON SEQUENCES TO %I', schema, subject);
END $$;
```

**How to run this SQL** — choose one method:

1. **Lakebase SQL Console** — open the Lakebase project in the Databricks UI (Compute > Lakebase Postgres > your project), click the branch, and use the built-in SQL editor.

2. **`psql` with OAuth credentials:**
   ```bash
   # Generate short-lived credentials (endpoint path is a REQUIRED positional argument)
   ENDPOINT="projects/jaiwant-j-booking-app/branches/production/endpoints/primary"
   CREDS=$(databricks postgres generate-database-credential "$ENDPOINT" \
     --profile $PROFILE --output json)
   PGUSER="$(databricks current-user me --output json --profile $PROFILE | jq -r '.userName')"
   PGPASSWORD=$(echo "$CREDS" | jq -r '.token')

   # Connect
   PGPASSWORD=$PGPASSWORD psql -h {LAKEBASE_HOST} -U $PGUSER -d databricks_postgres --set=sslmode=require
   ```

After granting, verify local connectivity:

```bash
cd apps_lakebase/$APP_NAME
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
npm run dev
# In another terminal:
curl -s http://localhost:8000/api/health | jq .
# Expected: { "data": [{ "status": "connected" }], "source": "live" }
```

---

### Summary

Your job is complete when:

- [ ] Databricks App is deployed and running
- [ ] Web UI is accessible at the app URL (React application, not an error page)
- [ ] ConnectionStatus shows "Live Data" (connected to Lakebase)
- [ ] **`GET /api/health`** returns `{ "data": [{ "status": "connected" }], "source": "live" }`
- [ ] All data API endpoints return `"source": "live"` with real data from Lakebase
- [ ] No errors in the app logs
- [ ] Idle connection test passes (still "Live Data" after 3-5 minutes idle)
- [ ] `.vibecoding-state.md` updated (see below)

**Before finishing**, append to `apps_lakebase/$APP_NAME/.vibecoding-state.md` with:
- Step name (`## Deploy and E2E Test`)
- Key variable values (`APP_URL`, test results summary)
- Any resolved issues or workarounds encountered during this phase
