## Context

> **On ANY error:** STOP and read `@apps_lakebase/gc-prompt-conversion/troubleshooting_gc.md`. Match the error message or symptom in the tables. Apply the fix exactly as described. Do NOT improvise a workaround before checking the troubleshooting reference.

You are Genie Code, an AI assistant on the Databricks workspace. You are deploying a Lakebase-wired Databricks App, verifying it starts correctly, and testing connection resilience.

Key requirements:

- **Deploy (primary):** **`deployment, app_url = validate_and_deploy(APP_NAME, APP_BASE)`** from `@apps_lakebase/gc-prompt-conversion/workshop-variables.md` — MCP `appkit_validate` + SDK `create`/`deploy_and_wait` as one contract (**`@apps_lakebase/gc-prompt-conversion/GENIE-CODE-OVERRIDES.md`**). Do **not** hand-roll a different validate+deploy sequence unless troubleshooting directs it.
- **Permissions:** If the MCP service principal cannot read the app source tree, fix **folder and app ACLs** for the MCP SP (`CAN_READ` / `CAN_MANAGE`) — see `@apps_lakebase/gc-prompt-conversion/MCP-appkit_tooling.md`, `.assistant_instructions.md` Deploy Rules, and `@apps_lakebase/gc-prompt-conversion/troubleshooting_gc.md`. **No** deploy Jobs.
- **Validate** (included in `validate_and_deploy`): MCP `appkit_validate` uses `source_code_path`, not `workspace_path`.
- Monitor deployment via SDK: `w.apps.get()`, `w.apps.list_deployments()`
- Fix deployment errors (up to 3 iterations): identify error → fix files → redeploy → re-verify
- **API testing from notebooks is blocked by the Apps auth proxy** — use SDK status checks and browser verification instead
- `@databricks/appkit` is a **CLI tool only** — it has no `build` or `start` commands. Use `vite build` and `tsx app.ts` instead

**Environment:** Genie Code on Databricks workspace (serverless). No CLI, no curl, no psql, no localhost. **`validate_and_deploy()`** uses MCP for **`appkit_validate`** and the SDK for **`deploy_and_wait`**. Browser handles UI verification.

**Prompt sequence:** `one-ui-design-local.md` → `setup_lakebase_gc.md` → `wire_ui_to_lakebase_gc.md` → **this file** (see `@apps_lakebase/prompts/README.md`).

---

### Session Recovery: MCP Setup

> **Skip this section** if `mcp_client` and `w` are still in scope from a previous prompt. Run ONLY if your Genie Code session was reset (kernel recycled, new conversation, or `ModuleNotFoundError`). If packages are missing, re-run the MCP setup prompt first to reinstall them.

<!--
# --- Uncomment this block if session was reset ---

import nest_asyncio
nest_asyncio.apply()

from databricks.sdk import WorkspaceClient
from databricks_mcp import DatabricksMCPClient

w = WorkspaceClient()
client_id = w.dbutils.secrets.get(scope="v2v-gc-agent", key="client_id")
client_secret = w.dbutils.secrets.get(scope="v2v-gc-agent", key="client_secret")
host = spark.conf.get("spark.databricks.workspaceUrl")

w_oauth = WorkspaceClient(
    host=f"https://{host}",
    client_id=client_id,
    client_secret=client_secret,
)

MCP_URL = f"https://mcp-appkit-skill-{host.split('.')[0]}.{host.split('.', 1)[1]}/mcp"
mcp_client = DatabricksMCPClient(server_url=MCP_URL, workspace_client=w_oauth)

tools = mcp_client.list_tools()
print(f"MCP OK. {len(tools)} tools available")

# --- End session recovery block ---
-->

> **Troubleshooting:** See `@apps_lakebase/gc-prompt-conversion/troubleshooting_gc.md` for error resolution.

---

## Your Task

Deploy the Lakebase-wired web application and verify it starts correctly. This is the first deploy with Lakebase code — the Service Principal will create the database schema, tables, and seed data on startup.

**First:** Read `apps_lakebase/{APP_NAME}/.vibecoding-state.md` — it contains variable values and TODO items from prior phases.

**Working directory:** All app files are under `apps_lakebase/{APP_NAME}/` within the repo.

**Prerequisite:** The **Wire Lakebase Backend** step must be complete — `server/server.ts` has DDL, seed data, API routes, and health endpoint using `export async function registerRoutes(appkit)` and `appkit.server.extend((app) => { ... })`, with SQL via `appkit.lakebase.query()`.

---

### Step 1: Derive Variables and Read State

Ensure `APP_NAME`, `DB_SCHEMA`, `REPO_ROOT`, `APP_BASE`, `mcp_client`, and `w` are in scope (paste **`@apps_lakebase/gc-prompt-conversion/workshop-variables.md`** Cell 3 if needed). Then read `.vibecoding-state.md` to confirm values and check for deferred TODO items.

---

### Step 2: Validate App Structure (optional preflight)

**Note:** Step 4 **`validate_and_deploy()`** already runs MCP **`appkit_validate`** first. Use this step only if you want an early read of validation output before touching deploy.

```python
result = mcp_client.call_tool("appkit_validate", {
    "app_name": APP_NAME,
    "source_code_path": APP_BASE,
})
print(result)
```

> **If MCP is unavailable:** See `@apps_lakebase/skills/03-appkit-deploy/SKILL.md` (Genie / validation patterns) and `@apps_lakebase/gc-prompt-conversion/troubleshooting_gc.md` — do not reference removed local-only scripts.

Fix any reported errors before proceeding.

Also manually verify these files:

| File | Must Have |
|------|-----------|
| `app.yaml` | `LAKEBASE_ENDPOINT` with `valueFrom: postgres`, `DB_SCHEMA` with correct value, command using `tsx app.ts` (NOT `npx` or `appkit start`) |
| `app.ts` | `createApp({ plugins: [lakebase(), server()], async onPluginsReady(appkit) { await registerRoutes(appkit); } })` — `lakebase()` before `server()`, no `autoStart`, no `.then()`, no top-level `await` |
| `server/server.ts` | `export async function registerRoutes(appkit)` with `appkit.server.extend((app) => {...})`, DDL with `DB_SCHEMA`, routes returning `{ data, source }`, `/api/health` with wrapped health JSON |
| `package.json` | `@databricks/lakebase` in `dependencies`, build script `"(npm run typegen || true) && vite build"` (NOT `appkit build`) — same as `one-ui-design-local.md` |

Also confirm:
- `server/mock-data.ts` exists with fallback data arrays
- No `databricks.yml` in the app directory (this workflow does not use Databricks Asset Bundles)
- No `appkit.plugins.json` (not needed with `registerRoutes` / `appkit.server.extend` architecture)

Fix any issues before proceeding.

---

### Step 3: Verify Lakebase Instance and Resource Binding

Check the Lakebase instance is `AVAILABLE` before deploying:

```python
inst = w.database.get_database_instance(name=APP_NAME)
print(f"Instance: {inst.name}  State: {inst.state}")
```

**Verify the resource binding is `postgres` type** (not `database` type). AppKit's `lakebase()` plugin requires a `postgres`-type resource — a `database`-type binding causes `ConfigurationError` at startup:

```python
app = w.apps.get(name=APP_NAME)
has_postgres = False
for r in (app.resources or []):
    if r.postgres:
        print(f"  ✓ Resource '{r.name}' → postgres type, branch={r.postgres.branch}")
        has_postgres = True
    elif r.database:
        print(f"  ✗ Resource '{r.name}' → database type — WRONG! AppKit needs postgres type.")
        print(f"    Fix: re-run setup_lakebase_gc.md Step 2 (Step 3d in skill) to rebind as AppResourcePostgres")
if not has_postgres:
    print("  ✗ No postgres resource found — app will crash. Run setup_lakebase_gc.md Step 2.")
```

If the instance is not available, the resource binding is missing, or it's the wrong type, revisit the **Setup Lakebase** step before continuing.

---

### Step 4: Deploy Application

**Primary (required for Genie):** call **`validate_and_deploy(APP_NAME, APP_BASE)`** from `@apps_lakebase/gc-prompt-conversion/workshop-variables.md` (same contract as **`@apps_lakebase/gc-prompt-conversion/GENIE-CODE-OVERRIDES.md`**).

```python
deployment, app_url = validate_and_deploy(APP_NAME, APP_BASE)
print(f"Deployment state: {deployment.status.state.name if deployment.status and deployment.status.state else 'UNKNOWN'}")
print(f"App URL: {app_url}")
```

> **CRITICAL:** `validate_and_deploy` expects `mcp_client` and `w` in scope — run workshop-variables Cell 3 after pip + restart if needed.

> If the MCP SP cannot read the app tree after troubleshooting, **grant** `CAN_READ` on `APP_BASE` and `CAN_MANAGE` on the app and directory for the MCP SP (UUID from `appkit_get_app_status`). Redeploy with **`validate_and_deploy`** only — no Jobs, no `_deploy_app`.

> SP permissions (`CAN_MANAGE` on app + directory) were granted in the UI step (`one-ui-design-local.md`). If you get MCP permission errors, re-run those grants.

**Timing:** First deploys take 3-5 minutes (platform runs `npm install` + `npm run build`). Redeployments take 1-3 minutes.

---

### Step 5: Verify Deployment Success

After the deploy completes, poll until the app is `ACTIVE`:

```python
import time

for i in range(20):
    app = w.apps.get(name=APP_NAME)
    cs = app.compute_status.state.name if app.compute_status and app.compute_status.state else "UNKNOWN"
    print(f"  [{i+1}] compute={cs}")
    if cs == "ACTIVE":
        print(f"\n✓ App is ACTIVE at: {app.url}")
        break
    time.sleep(15)
else:
    print("⚠ App did not reach ACTIVE within 5 minutes")
```

> **CRITICAL:** Use `.state.name` (returns `"ACTIVE"`) not `str(state)` (returns `"ComputeState.ACTIVE"`). The latter never matches `== "ACTIVE"` and causes infinite polling.

Check deployment details:

```python
deployments = list(w.apps.list_deployments(app_name=APP_NAME))
latest = deployments[0] if deployments else None
if latest:
    ds = latest.status.state.name if latest.status and latest.status.state else "?"
    print(f"Latest deployment: {latest.deployment_id}")
    print(f"  Status: {ds}")
    print(f"  Message: {latest.status.message if latest.status else ''}")
```

If the deployment `FAILED`, check app logs:

```python
logs = w.apps.get_logs(app_name=APP_NAME)
if logs and hasattr(logs, 'log_lines'):
    for line in (logs.log_lines or [])[-30:]:
        print(line)
```

---

### Step 6: Browser Verification

> **IMPORTANT:** API testing from notebooks does NOT work — the Databricks Apps auth proxy returns `401 {}` for all programmatic requests. This is by design.

Print the app URL and instruct the user to verify in browser:

1. Home page loads with the React UI (not an error page or JSON)
2. Navigation links work (Search, Agent pages)
3. Click into a listing to verify detail page renders
4. Data source indicator shows "Live Data" if Lakebase is connected
5. Navigate to `{app_url}/api/health` — expected: `{ "data": [{ "status": "connected" }], "source": "live" }`

---

### Step 6b: Post-Deploy Lakebase Verification

After confirming the app is `ACTIVE`, verify that Lakebase is connected and the app is serving live data (not mock fallback):

```python
import time

app = w.apps.get(name=APP_NAME)
cs = app.compute_status.state.name if app.compute_status and app.compute_status.state else "UNKNOWN"

if cs != "ACTIVE":
    print(f"⚠ App is {cs}, not ACTIVE — skip Lakebase verification until app is running")
else:
    print(f"App URL: {app.url}")

    # Verify resource binding is postgres type
    postgres_bound = False
    for r in (app.resources or []):
        if r.postgres:
            print(f"  ✓ Resource '{r.name}' → postgres type")
            postgres_bound = True
        elif r.database:
            print(f"  ✗ Resource '{r.name}' → database type (WRONG — will cause ConfigurationError)")
    if not postgres_bound:
        print("  ✗ No postgres resource — Lakebase pool will fail to initialize")

    # Check Lakebase instance is still available
    try:
        inst = w.database.get_database_instance(name=APP_NAME)
        print(f"  ✓ Lakebase instance: {inst.state}")
    except Exception as e:
        print(f"  ✗ Lakebase instance check failed: {e}")

    # Print verification instructions
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║  POST-DEPLOY VERIFICATION CHECKLIST                         ║
╠══════════════════════════════════════════════════════════════╣
║  Open this URL in your browser:                             ║
║  {app.url}
║                                                              ║
║  1. Home page loads with React UI (not error/JSON)          ║
║  2. Navigation links work (Search, Agent pages)             ║
║  3. Click a listing → detail page renders                   ║
║  4. Go to {{app_url}}/api/health                              ║
║     Expected: {{"data":[{{"status":"connected"}}],"source":"live"}} ║
║  5. Go to {{app_url}}/api/listings                            ║
║     Expected: {{"data":[...],"source":"live"}}                ║
║                                                              ║
║  If "source":"mock" → Lakebase pool failed. Check logs.     ║
║  If app crashes → check resource type (must be postgres).   ║
╚══════════════════════════════════════════════════════════════╝
""")
```

> **If the app crashed immediately after deploy:** Check logs for `ConfigurationError: Missing required resources: postgres:Postgres [lakebase]`. This means the resource was bound as `database` type instead of `postgres` type. Fix by re-running `setup_lakebase_gc.md` Step 2 (specifically Step 3d in the skill) to rebind using `AppResourcePostgres`, then redeploy.

---

### Step 7: Fix Deployment Errors (up to 3 iterations)

If the deploy fails or the app doesn't start, read `@apps_lakebase/skills/03-appkit-deploy/SKILL.md` Step 5 for the full error diagnosis flow.

After fixing, re-validate via MCP `appkit_validate` (`app_name` + `source_code_path`) and redeploy. Common errors:

| Error | Fix |
|-------|-----|
| `error: unknown command 'build'` | Replace `appkit build` with `vite build` in `package.json` |
| `sh: 1: npx: not found` | Replace `npx` with `./node_modules/.bin/<binary>` in `app.yaml` command |
| `ERR_MODULE_NOT_FOUND: @databricks/lakebase` | Add to `package.json` `dependencies`; redeploy |
| `ConfigurationError: Missing required resources: postgres:Postgres` | Resource bound as `database` type instead of `postgres` type. Rebind using `AppResourcePostgres` (see `04-appkit-plugin-add/SKILL.md` Step 3d), then redeploy |
| `error resolving resource postgres` | `app.yaml` has `valueFrom: postgres` but no `postgres`-named resource bound. Run `setup_lakebase_gc.md` Step 2 (Step 3d) |
| `ConfigurationError: Warehouse ID not found` | Remove unconfigured plugins from `app.ts` — use only `lakebase()` + `server()` in that order |
| `role "..." does not exist` | Re-run `w.database.create_database_instance_role()` from setup step |
| `permission denied for schema` / `must be owner` | Drop schema from Lakebase SQL Console; redeploy so SP re-creates |
| `Connection attempt 1/5 failed` | Normal cold start — wait 15s, AppKit retries automatically |
| `Could not resolve entry module "index.html"` | Verify `client/index.html` exists; `root: "client"` in `vite.config.ts` |

Stop after 3 iterations.

---

### Step 8: Idle Connection Test (Optional)

If Lakebase is configured with scale-to-zero, test reconnection resilience:

1. Confirm baseline — health JSON shows `"source": "live"` and `data: [{ "status": "connected" }]` in browser
2. Wait 5 minutes — let Lakebase scale to zero
3. Re-test in browser — navigate to `{app_url}/api/health`
4. Expected: first request may take 5-15 seconds (endpoint waking), then health JSON shows `data: [{ "status": "connected" }]` and `source: "live"`
5. If still `source: "mock"` after 30 seconds — check `server.ts` for proper error handling

---

### If Workspace App Limit Is Reached

Use the Databricks SDK to list apps, find STOPPED ones, and delete one to make room. Read `@apps_lakebase/skills/03-appkit-deploy/SKILL.md` "If the Workspace App Limit Is Reached" section for the code. Only delete STOPPED apps, never RUNNING/ACTIVE. Stop after 3 deletion attempts.

---

### Checklist

- [ ] MCP `appkit_validate` passed (or SDK fallback validation passed)
- [ ] Pre-deploy config validated (all 4 files checked)
- [ ] Lakebase instance state is `AVAILABLE`
- [ ] App resource binding is `postgres` type (NOT `database` type)
- [ ] No `databricks.yml` or `appkit.plugins.json` in the app directory
- [ ] App deployed via **`validate_and_deploy()`** (SDP only) — deployment `SUCCEEDED`
- [ ] App URL printed for browser verification
- [ ] Post-deploy Lakebase verification completed (resource type check, instance check, browser instructions)
- [ ] Browser verification: home page loads, `/api/health` returns `{ "data": [{ "status": "connected" }], "source": "live" }` (or `"source": "mock"` if pool failed)
- [ ] Error fix table provided for common deployment failures
- [ ] `.vibecoding-state.md` updated with: app URL, deploy status, deploy method, Lakebase instance state, any errors and fixes

**Previous step:** `wire_ui_to_lakebase_gc.md` | **Next step:** None — workshop complete!
