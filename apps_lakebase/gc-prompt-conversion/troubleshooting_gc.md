# Troubleshooting Reference — Genie Code Workshop

**Purpose:** This is the single source of truth for diagnosing and fixing errors across all workshop steps. When any error occurs, consult this file FIRST before improvising a fix.

**How to use:** Match the error message or symptom in the tables below. Apply the fix exactly as described. If the error is not listed, check the step-specific "Pre-Deploy Checklist" to ensure nothing was missed.

---

## Global Directives

These rules apply to EVERY step. Follow them proactively — do not wait for errors.

### SDK File Operations

| Rule | Detail |
|------|--------|
| Always `mkdirs` before writing | Call `w.workspace.mkdirs(parent_path)` before any `w.workspace.import_()`. The SDK does NOT create parent directories automatically. |
| Use base64 encoding for file writes | `content` parameter of `w.workspace.import_()` expects a base64-encoded string: `base64.b64encode(content.encode("utf-8")).decode("utf-8")` |
| Use `w.workspace.export()` to read files | NOT `export_()` (no trailing underscore) |
| Unicode in JSX files | When writing `.tsx` files via Python SDK, use actual Unicode characters (e.g., `·`, `★`, `✓`, `🏠`), NOT escape sequences like `\u00B7`, `\u2605`, `\u{1F3E0}`. Python string literals with `\u` are interpreted by Python, not passed through to TypeScript. |

### MCP Client

| Rule | Detail |
|------|--------|
| Constructor signature | `DatabricksMCPClient(server_url: str, workspace_client: Optional[WorkspaceClient])` — nothing else. Do NOT pass `oauth_client_id`, `oauth_client_secret`, or `oauth_scope`. |
| Separate WorkspaceClient | Create a dedicated `WorkspaceClient` with M2M credentials (`client_id`, `client_secret`) and pass it as `workspace_client`. |
| Session recovery | If `mcp_client` is undefined, run the Session Recovery block in the current prompt. |
| Bootstrap after re-init | Genie **re-initializing** clients or a **new kernel** wipes Python state. Re-run the **three-cell** sequence from `workshop-variables.md` (pip → `restartPython` → Cell 3 with `setup_mcp_client()`) before importing `databricks_mcp`. |

### APP_NAME Derivation

| Rule | Detail |
|------|--------|
| Format | `{firstname}-{last_initial}-booking-app` — single letter for last name, NOT the full last name. Example: `jaiwant.jonathan` → `jaiwant-j-booking-app`, NOT `jaiwant-jonathan-booking-app`. |
| Source of truth | If `.vibecoding-state.md` exists, use the `APP_NAME` from there. It overrides any derivation. |
| Constraints | Max 26 chars, lowercase letters/numbers/hyphens only. No underscores. |

### Deploy

| Rule | Detail |
|------|--------|
| Primary path (Genie) | After MCP SP grants: use `validate_and_deploy(APP_NAME, APP_BASE)` from `workshop-variables.md` — MCP `appkit_validate` + SDK `create_and_wait` / `ensure_app_active` / `deploy_and_wait`. |
| `permission_denied` / validate cannot list files | Grant the **MCP service principal** `CAN_READ` on the app’s workspace folder (`APP_BASE`) and `CAN_MANAGE` on the app and directory as needed. Use the UUID `service_principal_client_id` from `appkit_get_app_status` (not the numeric id). See `.assistant_instructions.md` Deploy Rules and `MCP-appkit_tooling.md` (SDP path — **no** deploy Jobs). |
| Fallback — MCP `appkit_deploy` | Only when SDK path is blocked and job is unavailable; requires same SP grants as validate. |
| Parameter case sensitivity | Deploy job params must be uppercase: `"APP_NAME"` and `"APP_BASE"`. Wrong case = `InvalidParameterValue`. |
| `AppDeployment` wrapper | `source_code_path` must be inside `AppDeployment(source_code_path=...)`, NOT as a direct kwarg to `deploy_and_wait()`. |
| Polling state comparison | Use `.state.name` (returns `"ACTIVE"`) not `str(state)` (returns `"ComputeState.ACTIVE"`). The latter breaks equality checks and causes infinite polling. |
| Deploy job INTERNAL_ERROR | The job can fail but still trigger the deployment. Always poll `w.apps.list_deployments()` to check actual deployment status regardless of job exit code. |

### API Testing

| Rule | Detail |
|------|--------|
| No programmatic API testing | The Databricks Apps auth proxy returns `401 {}` for all programmatic requests from notebooks. This is by design. |
| Browser only | Verify API endpoints (`/api/health`, `/api/listings`, etc.) in the browser. Print the URL for the user. |

---

## Step 1: Scaffold, UI, mock deploy (`one-ui-design-local.md`)

### Pre-deploy checklist (scaffold + first deploy)

- [ ] `w.workspace.mkdirs(APP_BASE)` called before writing any scaffold files
- [ ] `package.json` build script is `"(npm run typegen || true) && vite build"` (NOT `"npm run typegen && vite build"`)
- [ ] `tsx` and `vite` are in `dependencies` (NOT `devDependencies` — platform may skip devDependencies)
- [ ] `app.yaml` command is `["./node_modules/.bin/tsx", "app.ts"]` (NOT `npx tsx app.ts`)
- [ ] `app.ts` (pre-Lakebase) uses `import { createApp, server } from "@databricks/appkit"` + `await createApp({ plugins: [server()] })` — `await` is required, NOT `export default createApp`, NOT `import { server } from "@databricks/appkit/server"` (that subpath crashes). Once Lakebase is wired: **`await createApp({ plugins: [lakebase(), server()], async onPluginsReady(appkit) { ... } })`** — **`await` on `createApp` is required** (same reason as pre-Lakebase); no `.then()`, no `server({ autoStart: false })`
- [ ] `client/index.html` exists with `<div id="root">`
- [ ] `vite.config.ts` has `root: "client"` and `outDir: "dist"` (NOT `"../dist"` — `outDir: "dist"` with `root: "client"` outputs to `client/dist/` where AppKit looks for static files)
- [ ] No `databricks.yml` in the app directory
- [ ] MCP SP has `CAN_MANAGE` on app and workspace directory

### Error Table

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ModuleNotFoundError: No module named 'databricks_mcp'` | Package not installed for this kernel, or `setup_mcp_client()` ran **before** pip + restart after a Genie re-init / new session | Run **Cell 1** alone: `%pip install databricks-mcp --upgrade databricks-sdk -q`. Then **Cell 2**: `dbutils.library.restartPython()`. Then **Cell 3**: paste the full block from `gc-prompt-conversion/workshop-variables.md` (defines helpers) and `w, mcp_client = setup_mcp_client()`. **Genie re-init = new Python** — always repeat cells 1–2–3. See also `MCP-appkit_tooling.md` troubleshooting table. |
| `TypeError: DatabricksMCPClient.__init__() got an unexpected keyword argument 'oauth_client_id'` | Wrong constructor args | Use `DatabricksMCPClient(server_url=MCP_URL, workspace_client=w_oauth)` only. See Global Directives → MCP Client. |
| `The parent folder (...) does not exist` / "parse scaffold files failed" | Missing directory | Call `w.workspace.mkdirs(APP_BASE)` before writing any files. |
| `Error building app` (after deploy) | `typegen` failure blocking `vite build` | Change build script to `"(npm run typegen || true) && vite build"`. |
| `Error building app` — `Could not resolve entry module "index.html"` | Missing HTML entry point | Create `client/index.html`. Verify `vite.config.ts` has `root: "client"`. |
| `sh: 1: npx: not found` | `npx` in app.yaml command | Replace with `["./node_modules/.bin/tsx", "app.ts"]` in `app.yaml`. |
| `error: unknown command 'build'` / `error: unknown command 'start'` | Using `appkit build` or `appkit start` | `@databricks/appkit` has no CLI commands. Use `vite build` (build script) and `tsx app.ts` (start command). |
| `InvalidParameterValue` on deploy job run | Wrong `notebook_params` key case | Keys must be uppercase: `{"APP_NAME": ..., "APP_BASE": ...}`. |
| `Top-level await is currently not supported with the "cjs" output format` | `app.ts` uses `await` at top level with old `tsx` | Upgrade `tsx` to latest (supports top-level await). If still failing, check `tsconfig.json` has `"module": "ESNext"`. |
| Deploy job `INTERNAL_ERROR` but deployment is actually IN_PROGRESS | Job failed but triggered the deploy | Poll `w.apps.list_deployments(app_name=APP_NAME)` to check actual deployment status. |
| Infinite polling — compute never shows ACTIVE | Using `str(state)` instead of `.state.name` | `str(state)` returns `"ComputeState.ACTIVE"` which never equals `"ACTIVE"`. Use `app.compute_status.state.name`. |
| `ConfigurationError: Warehouse ID not found` | Unconfigured plugins in `app.ts` | Remove all plugins except `server()` (mock phase) or `lakebase(), server()` (after Lakebase wiring). |
| `ServerError: server({ autoStart }) has been removed` | Old AppKit pattern — `autoStart` option was removed | Replace `server({ autoStart: false })` with `server()`. Replace `.then(async (appkit) => { ... appkit.server.start() })` with `onPluginsReady: async (appkit) => { ... }`. See **Section 6** in `GENIE-CODE-OVERRIDES.md` for canonical `app.ts`. |
| `tsx` or `vite` not found during platform build | In `devDependencies` instead of `dependencies` | Move `tsx` and `vite` from `devDependencies` to `dependencies` in `package.json`. |
| `AttributeError: 'str' object has no attribute 'value'` during deploy | `AppDeploymentMode.SNAPSHOT` used in `AppDeployment(mode=...)` — in this SDK version the enum is already a string, calling `.value` on it fails | Fix: use `validate_and_deploy(APP_NAME, APP_BASE)` — do NOT import or use `AppDeploymentMode`. |
| `Error: app crashed unexpectedly` — `ERR_MODULE_NOT_FOUND: Package subpath './server' is not defined` | Wrong `app.ts` import — `import { server } from "@databricks/appkit/server"` subpath does not exist | Fix: `import { createApp, server } from "@databricks/appkit"` (single import from main package). |
| `Error: app crashed unexpectedly` — app starts then immediately exits, no server binding | `export default createApp(...)` — tsx exports the Promise but never awaits it | Fix: `await createApp({ plugins: [server()] })` — must use `await`, not `export default`. |
| App deploys SUCCEEDED but all pages return blank / no frontend assets served | `outDir: "../dist"` in `vite.config.ts` — build goes to `<APP_ROOT>/dist/`, AppKit looks in `client/dist/` | Fix: change to `outDir: "dist"` — with `root: "client"`, this outputs to `client/dist/`. |

### Pre-deploy checklist (UI polish)

- [ ] All new/modified `.tsx` files use actual Unicode characters (not `\u` escapes)
- [ ] All file writes use base64 encoding: `base64.b64encode(content.encode("utf-8")).decode("utf-8")`
- [ ] No new imports reference exports that were removed from `mockData.ts`
- [ ] CSS import paths are relative to the importing file (e.g., `./styles/global.css` not `../src/styles/global.css`)

### Error table (polish / components)

| Symptom | Cause | Fix |
|---------|-------|-----|
| `TypeError: Object of type bytes is not JSON serializable` | Raw bytes passed to `w.workspace.import_()` | Use `base64.b64encode(content.encode("utf-8")).decode("utf-8")` for the `content` param. |
| `AttributeError: 'WorkspaceExt' object has no attribute 'export_'` | Typo in SDK method | Use `w.workspace.export()` (no trailing underscore). |
| Build fails with "cannot find module '../src/styles/global.css'" | Wrong CSS import path | Fix import to `./styles/global.css` (relative to the file's location in the build). |
| Build fails with syntax error in `.tsx` file | `\u{1F3E0}` or similar in JSX | Replace all `\uXXXX` and `\u{XXXXX}` escape sequences with actual Unicode characters. Python writes these as literal backslash-u strings. |
| `mockListings is not iterable` / `import_mock_data.X is not iterable` | Mock data export names don't match import names | Check actual export names in `mock-data.ts` (e.g. `MOCK_LISTINGS` vs `mockListings`) — import names must match exactly |
| `Error building app` after adding components | TypeScript import errors | Read the build error. Common: importing a symbol that was renamed or doesn't exist in the target module. |

---

## Step 2: Setup Lakebase (`setup_lakebase_gc.md`)

### Pre-Deploy Checklist

- [ ] `%pip install --upgrade databricks-sdk -q` + `dbutils.library.restartPython()` run before importing `AppResourcePostgres`
- [ ] Lakebase instance created — state `AVAILABLE`
- [ ] Database created with `DB_SCHEMA` name
- [ ] App SP granted `DATABRICKS_SUPERUSER`
- [ ] Resource bound as `postgres` type (via `AppResourcePostgres`), NOT `database` type (via `AppResourceDatabase`)
- [ ] `@databricks/lakebase` in `dependencies` (not `devDependencies`)
- [ ] `app.yaml` has `LAKEBASE_ENDPOINT` with `valueFrom: postgres` (NOT `valueFrom: database`)
- [ ] `app.ts` is UNCHANGED — still `[server()]` only

### Error Table

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ImportError: cannot import name 'AppResourcePostgres'` | Outdated SDK on serverless runtime | Run `%pip install --upgrade databricks-sdk -q` then `dbutils.library.restartPython()`. Verify version ≥ 0.105.0. |
| `AppResourcePostgres` not found, only `AppResourceDatabase` available | Same as above — old SDK | Upgrade SDK. After upgrade, `from databricks.sdk.service.apps import AppResourcePostgres` should succeed. |
| `Identity not found` when creating SP role | Using UUID `service_principal_client_id` instead of numeric `service_principal_id` | The `create_database_instance_role` API needs the **numeric** `service_principal_id`, not the UUID `client_id`. Get it from `app.service_principal_id` after `w.apps.get(APP_NAME)`. |
| `project already exists` during deploy | Lakebase project from a prior run | Either delete the project first (`w.database.delete_database_instance(name=APP_NAME)`) or skip project creation and proceed to resource binding. |
| `LAKEBASE_ENDPOINT is not set` / `PGHOST is not set` at runtime | Missing resource binding or wrong `valueFrom` | Verify `app.yaml` has `valueFrom: postgres` and the app has a `postgres`-type resource bound. |
| `ConfigurationError: Missing required resources: postgres:Postgres [lakebase]` | Resource bound as `database` type | Rebind using `AppResourcePostgres` with `branch` and `database` params (not `AppResourceDatabase`). |
| MCP `appkit_add_lakebase` returns wrong env var name | MCP boilerplate outdated | Ignore MCP suggestion. Always use `LAKEBASE_ENDPOINT` with `valueFrom: postgres`, NOT `DATABRICKS_LAKEBASE_DB` with `valueFrom: database`. |

---

## Step 3: Wire Lakebase Backend (`wire_ui_to_lakebase_gc.md`)

### Pre-Deploy Checklist

- [ ] `app.ts` uses **`await createApp({ plugins: [lakebase(), server()], async onPluginsReady(appkit) { await registerRoutes(appkit) } })`** — `lakebase()` before `server()`; **`await` on `createApp` required** (so `/api/*` routes mount reliably); use `appkit.lakebase.query()` for SQL — not `ctx.lakebase.getPool()`
- [ ] Single `appkit.server.extend((app) => { ... })` call inside `onPluginsReady` via `registerRoutes(appkit)` in `server.ts` — not `server.extend((app, ctx) => ...)` on the `server` import
- [ ] All DDL uses `process.env.DB_SCHEMA` (never hardcoded)
- [ ] DDL is idempotent: `CREATE SCHEMA IF NOT EXISTS`, `CREATE TABLE IF NOT EXISTS`
- [ ] Seed data uses count-check pattern (not `ON CONFLICT`)
- [ ] All API routes return `{ data, source }` with mock fallback on error
- [ ] `/api/health` endpoint exists
- [ ] `server/mock-data.ts` has camelCase fallback data arrays
- [ ] `useLakebaseData` hook created in `client/src/hooks/`
- [ ] `ConnectionStatus` component created
- [ ] All pages updated to use `useLakebaseData` hook instead of direct `mockData` imports
- [ ] No remaining imports of removed exports from `mockData.ts` — check ALL files in `client/src/pages/` and `client/src/components/`
- [ ] All file writes use base64 encoding
- [ ] No `\u` escape sequences in `.tsx` files

### Error Table

| Symptom | Cause | Fix |
|---------|-------|-----|
| `Cannot GET /api/health` / 404 on all API routes (after deploy) | Missing **`await` on `createApp`**, or plugin order wrong, or missing `onPluginsReady` | Use **`await createApp({ plugins: [lakebase(), server()], async onPluginsReady(appkit) { await registerRoutes(appkit) } })`**. `lakebase()` before `server()`. Bare `createApp({...})` without `await` often yields 404 on all `/api/*` after deploy. |
| `import_appkit.server.extend is not a function` | `server.extend()` called on the imported `server` function instead of the AppKit instance | Use `appkit.server.extend()` — `extend()` is on the resolved AppKit instance from `onPluginsReady`, not on the `server` import |
| `Error building app` after wiring | Stale imports from `mockData.ts` | Check all `.tsx` files for imports of removed exports (e.g., `listings` array, `getListingById`). Update to use `useLakebaseData` hook. |
| `Error building app` — syntax error in JSX | Unicode escape sequences | Replace `\u00B7`, `\u2605`, `\u{1F3E0}` etc. with actual characters: `·`, `★`, `🏠`. |
| `TypeError: Object of type bytes is not JSON serializable` | File write without base64 | Use `base64.b64encode(content.encode("utf-8")).decode("utf-8")` before `w.workspace.import_()`. |
| `ctx.lakebase` / `appkit.lakebase` unavailable or wrong access pattern | Plugin order wrong, or using old `ctx` pattern | `lakebase()` must come before `server()` in the plugins array. Use `appkit` from `onPluginsReady` and `appkit.lakebase.query()` (not `ctx.lakebase.getPool()`). |
| Routes registered but return empty data | DDL ran but seed data skipped | Check the count-check pattern: `SELECT COUNT(*) FROM {schema}.{table}` — if count > 0, seeding is skipped. Drop and re-create if needed. |
| `permission denied for sequence` | SP lacks GRANT on sequences for SERIAL columns | Add `GRANT ALL ON ALL SEQUENCES IN SCHEMA {DB_SCHEMA} TO "{sp-id}"` to the DDL block. |

---

## Step 4: Deploy & Test (`deploy_and_test_gc.md`)

### Pre-Deploy Checklist

- [ ] MCP `appkit_validate` passed (or manual checks confirmed)
- [ ] Lakebase instance state is `AVAILABLE`
- [ ] Resource binding is `postgres` type (not `database` type)
- [ ] `app.ts`: **`await createApp({ plugins: [lakebase(), server()], async onPluginsReady(appkit) { await registerRoutes(appkit) } })`** (lakebase first; **`await` required**)
- [ ] `server/server.ts` has `/api/health` endpoint
- [ ] No `databricks.yml` or `appkit.plugins.json` in app directory
- [ ] All file content verified — no `\u` escapes, no stale imports, base64 encoding used

### Post-Deploy Verification (Browser)

Open the app URL and check:

| Check | Expected | If Wrong |
|-------|----------|----------|
| Home page | React UI loads (not error page or JSON) | Check build — likely a build error |
| Navigation | Links work (Search, Agent, Listing Detail) | Check `client/src/index.tsx` router config |
| `/api/health` | `{ "data": [{ "status": "connected" }], "source": "live" }` | See "API returns mock" below |
| `/api/listings` | `{ "data": [...], "source": "live" }` | See "API returns mock" below |
| Data source indicator | Shows "Live Data" | See "API returns mock" below |
| After 5 min idle | Still returns `"source": "live"` | See "Connection lost after idle" below |

### Error Table

| Symptom | Cause | Fix |
|---------|-------|-----|
| `Error building app` | TypeScript compilation failure | Check for: stale mockData imports, unicode escapes in JSX, missing components, CSS import paths. Fix file and redeploy. |
| App crashes immediately — `ConfigurationError: Missing required resources: postgres:Postgres` | Resource bound as `database` type | Rebind using `AppResourcePostgres` (run `setup_lakebase_gc.md` Step 2, specifically Step 3d). |
| App ACTIVE but API returns `"source": "mock"` | Lakebase `SELECT 1` failed in `/api/health` **or** health route never registered | 1) Read `{APP_URL}/logz` — health `catch` must `console.error` (see `wire_ui_to_lakebase_gc.md`). 2) Confirm **`await createApp(...)`** in `app.ts`. 3) Resource is `postgres` type, Lakebase AVAILABLE, SP has `DATABRICKS_SUPERUSER`, plugin order `[lakebase(), server()]`. |
| 404 on all `/api/*` routes | Routes not registered — often **bare `createApp({...})` without `await`** | Fix `app.ts` to **`await createApp({ plugins: [lakebase(), server()], async onPluginsReady(appkit) { await registerRoutes(appkit) } })`**. Then redeploy. |
| Navbar shows **Mock Data** but infra looks correct | Same as above — unawaited `createApp` or swallowed health error | Add **`await`**, redeploy, check `/logz` for `[Lakebase] Health check failed:` lines. |
| "Map view" missing on Search results | `MapPlaceholder` sits **under** a tall `FilterSidebar` (below the fold) | Move `<MapPlaceholder />` **above** `<FilterSidebar />` or make map **sticky** at top of left column — see `@apps_lakebase/gc-prompt-conversion/GENIE-CODE-OVERRIDES.md` (Map / location UI). |
| User expected Google-style interactive map | `MapPlaceholder` is a **stub** by design | Optional: static OSM image from `lat`/`lng`; full Leaflet/Mapbox is out of workshop scope unless you add deps deliberately. |
| `role "..." does not exist` | SP lacks Lakebase role | Re-run `w.database.create_database_instance_role()` from setup step. |
| `permission denied for schema` / `must be owner of schema` | Schema owned by a different identity | Drop schema from Lakebase SQL Console: `DROP SCHEMA {DB_SCHEMA} CASCADE;`. Redeploy — SP will re-create it. |
| `error resolving resource postgres for env LAKEBASE_ENDPOINT` | No `postgres`-named resource bound to app | Run `setup_lakebase_gc.md` Step 2 (Step 3d in skill) to bind `AppResourcePostgres`. |
| `Connection attempt 1/5 failed` | Normal Lakebase cold start | Wait 15-30 seconds. AppKit retries automatically. |
| `token's identity did not match` | OAuth token mismatch | Verify `app.yaml` env vars. Do NOT manually set `PGUSER` or `PGPASSWORD`. |
| Connection lost after idle (returns `"source": "mock"`) | Lakebase scaled to zero, connection didn't recover | Reload page 2-3 times (first request wakes the endpoint). If still mock after 30s, check `server.ts` error handling around `appkit.lakebase.query()`. |
| `ERR_MODULE_NOT_FOUND: @databricks/lakebase` | Package not in dependencies | Add `@databricks/lakebase` to `package.json` `dependencies`. Redeploy. |

---

## Quick Reference: SDK Patterns

### Write a file to workspace

```python
import base64
from databricks.sdk.service.workspace import ImportFormat

content = "file contents here"
content_b64 = base64.b64encode(content.encode("utf-8")).decode("utf-8")
w.workspace.import_(
    path=f"{APP_BASE}/path/to/file.tsx",
    content=content_b64,
    format=ImportFormat.AUTO,
    overwrite=True,
)
```

### Read a file from workspace

```python
import base64
from databricks.sdk.service.workspace import ExportFormat

content_obj = w.workspace.export(path=f"{APP_BASE}/path/to/file.tsx", format=ExportFormat.AUTO)
content = base64.b64decode(content_obj.content).decode("utf-8")
```

### Poll deployment status

```python
import time

for i in range(20):
    app = w.apps.get(name=APP_NAME)
    cs = app.compute_status.state.name if app.compute_status and app.compute_status.state else "UNKNOWN"
    dep = app.pending_deployment or app.active_deployment
    ds = dep.status.state.name if dep and dep.status and dep.status.state else "N/A"
    print(f"  [{i+1}] deploy={ds}  compute={cs}")
    if cs == "ACTIVE" and ds in ("SUCCEEDED", "N/A"):
        break
    time.sleep(15)
```

### Check Lakebase resource binding

```python
app = w.apps.get(name=APP_NAME)
for r in (app.resources or []):
    if r.postgres:
        print(f"  ✓ postgres resource: {r.name}")
    elif r.database:
        print(f"  ✗ database resource (WRONG TYPE): {r.name}")
```
