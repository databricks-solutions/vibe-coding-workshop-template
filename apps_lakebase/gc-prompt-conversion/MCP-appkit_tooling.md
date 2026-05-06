# MCP AppKit Tooling — Complete Tool Reference

> **Prerequisite document for all `_gc.md` prompt files.** Complete the one-time setup in `mcp-setup-gc.md` before using these tools.

---

## Overview

The **`mcp-appkit-skill`** Databricks App exposes **11 MCP tools** for scaffolding, deploying, validating, and extending AppKit applications from within Genie Code notebooks. The tools are accessed via the `DatabricksMCPClient` Python library.

**Source project:** `/Users/Jaiwant.jonathan/DBXApps/appkit-mcp-skill` (deployed as `mcp-appkit-skill` in the workspace).

---

## Tool Hierarchy

MCP AppKit tools are the **primary** interface for scaffold, validate, plugins, and Lakebase helpers. The **Databricks SDK** (`WorkspaceClient` `w`) carries **SDP deployment** (`w.apps.*`) and workspace/database operations:

| Tier | Tools | Auth Required | When to Use |
|------|-------|---------------|-------------|
| **1. MCP AppKit** (via `DatabricksMCPClient`) | All 11 tools below | OAuth M2M (`v2v-gc-agent` scope) | Scaffold, validate, plugins, Lakebase provisioning, status |
| **2. Databricks SDK** (`WorkspaceClient` `w`) | `w.apps.*`, `w.database.*`, `w.workspace.*`, `w.permissions.*` | Notebook / Genie runtime auth | **SDP (SDK deployment path):** `validate_and_deploy()` uses `w.apps.create_and_wait` / `w.apps.deploy_and_wait` after MCP `appkit_validate`. **No Databricks Jobs** for deploy. |

**SDP (SDK deployment path):** The workshop contract is `validate_and_deploy(app_name, app_base)` in `workshop-variables.md`: MCP `appkit_validate`, then **SDK** create/activate/deploy via the session `WorkspaceClient` (`w`). Do not create or run deploy Jobs; do not use `_deploy_app` notebooks.

---

## Architecture

```
Genie Code (serverless compute)
  │
  ├─ DatabricksMCPClient  ← Python SDK wrapper (Primary)
  │    │
  │    ├─ WorkspaceClient(host, client_id, client_secret)  ← OAuth M2M
  │    │
  │    └─ MCP Streamable HTTP  →  mcp-appkit-skill App (FastMCP)
  │                                  │
  │                                  ├── Scaffold & Deploy ──────────────────
  │                                  │   ├─ appkit_scaffold_app   → generates project files
  │                                  │   ├─ appkit_deploy         → creates + deploys app via SDK
  │                                  │   └─ appkit_validate       → pre-deploy checks
  │                                  │
  │                                  ├── Plugin Add-ons ─────────────────────
  │                                  │   ├─ appkit_add_lakebase   → Lakebase boilerplate + .then() pattern
  │                                  │   ├─ appkit_add_analytics  → SQL query + chart component
  │                                  │   ├─ appkit_add_genie_panel → Genie Space chat panel
  │                                  │   └─ appkit_add_files_browser → UC Volumes browser (DirectoryList)
  │                                  │
  │                                  ├── Infrastructure ─────────────────────
  │                                  │   ├─ appkit_provision_lakebase → Create instance + bind postgres
  │                                  │   └─ appkit_manage_app_resources → Add/update app resources
  │                                  │
  │                                  └── Management ─────────────────────────
  │                                      ├─ appkit_list_apps       → list all workspace apps
  │                                      └─ appkit_get_app_status  → detailed app + deployment info
  │
  └─ WorkspaceClient()  ← runtime auth: `w.apps.*` for SDP deploy (`validate_and_deploy`), `w.workspace.*`, `w.database.*`, `w.permissions.*`
```

---

## Setup Code (Copy-Paste Ready)

```python
# --- Cell 1: Install ---
%pip install databricks-mcp
```

If you get `ImportError: cannot import name 'Sentinel' from 'typing_extensions'`:

```python
%pip install typing_extensions --upgrade
dbutils.library.restartPython()
```

```python
# --- Cell 2: Create MCP client ---
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
print(f"Auth type: {w_oauth.config.auth_type}")  # → "oauth-m2m"

MCP_URL = "https://mcp-appkit-skill-4101016551133680.0.azure.databricksapps.com/mcp"
mcp_client = DatabricksMCPClient(server_url=MCP_URL, workspace_client=w_oauth)

# Verify
tools = mcp_client.list_tools()
print(f"MCP OK. {len(tools)} tools:")
for t in tools:
    print(f"  - {t.name}")
```

**Expected output:**

```
Auth type: oauth-m2m
MCP OK. 11 tools:
  - appkit_scaffold_app
  - appkit_add_lakebase
  - appkit_add_genie_panel
  - appkit_deploy
  - appkit_add_analytics
  - appkit_add_files_browser
  - appkit_validate
  - appkit_list_apps
  - appkit_get_app_status
  - appkit_provision_lakebase
  - appkit_manage_app_resources
```

> **Note:** `DatabricksMCPClient` has **synchronous** methods (`call_tool`, `list_tools`) and async variants (`acall_tool`, `alist_tools`). The sync methods internally use `asyncio.run()`, which conflicts with Databricks notebooks' running event loop. Always call `nest_asyncio.apply()` before using the client.

---

## Tool Reference

### Tool 1: `appkit_scaffold_app`

Create a new AppKit app scaffold with `app.ts`, `app.yaml`, `package.json`, and `README.md`. When `lakebase` is in the plugin list, generates `app.ts` with the `.then()` pattern and includes `server/server.ts` with Express routes.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `app_name` | string | Yes | Databricks App name (<=26 chars, lowercase/hyphens) |
| `description` | string | Yes | What the app does — used in the README |
| `plugins` | list[string] | No | Plugins to wire: `analytics`, `genie`, `lakebase`, `files`, `serving`, `vectorSearch`, `server`. Defaults to `["server"]`. |
| `workspace_path` | string | No | If provided, files are uploaded to this workspace path automatically |

**Usage:**

```python
result = mcp_client.call_tool("appkit_scaffold_app", {
    "app_name": "my-booking-app",
    "description": "A vacation rental marketplace with search and booking",
    "plugins": ["lakebase", "server"],
})
scaffold = json.loads(result.content[0].text)
for f in scaffold["files"]:
    print(f"  {f['path']} ({len(f['contents'])} chars)")
```

**When `lakebase` is included, generates:** (MCP output is often outdated — **normalize** to `@apps_lakebase/gc-prompt-conversion/GENIE-CODE-OVERRIDES.md` Section 6 before deploy.)
- `app.ts` — target: **`await createApp({ plugins: [lakebase(), server()], async onPluginsReady(appkit) { await registerRoutes(appkit) } })`** — do **not** use `server({ autoStart: false })` or `.then()` chains
- `server/server.ts` with `registerRoutes(appkit)` using `appkit.lakebase.query()` and `appkit.server.extend()`

> **Warning:** The scaffold generates `app.yaml` and `package.json` that use `npx @databricks/appkit <cmd>`. `npx` is NOT available in the Databricks Apps build environment. You **must** overwrite these with corrected versions — see `01-appkit-scaffold/SKILL.md` Step 2.

> **Note:** Plugins `serving`, `vectorSearch`, and `files` are not included in the MCP scaffold defaults. To add these plugins manually, add them to `app.ts` imports and the plugins array, and configure the corresponding env vars in `app.yaml`. See AppKit docs for details.

---

### Tool 2: `appkit_add_lakebase`

Add Lakebase (managed PostgreSQL) boilerplate code and config snippets to an AppKit app. Uses the correct `onPluginsReady` pattern with `server()` and `appkit.lakebase.query()`.

**Does NOT create Lakebase projects or databases** — use `appkit_provision_lakebase` (Tool 14) or the Databricks SDK for that.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `app_name` | string | Yes | The Databricks App name |
| `lakebase_instance_name` | string | No | Lakebase instance name (defaults to app_name) |

**Returns:**
- `server/server.ts` — Express routes with `registerRoutes(appkit)` using `appkit.lakebase.query()`, health check returning `{ data: [{ status }], source }`
- `app.yaml (patch)` — env entries for `LAKEBASE_ENDPOINT` (`valueFrom: postgres`) and `DB_SCHEMA`
- `app.ts (replace)` — `onPluginsReady` pattern with `lakebase()` + `server()`
- `extra_dependencies` — `@databricks/lakebase`

---

### Tool 3: `appkit_add_genie_panel`

Scaffold an "Ask Genie" conversational analytics panel wired to a Genie Space. Uses `GenieChat` from `@databricks/appkit-ui/react`.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `genie_space_id` | string | Yes | The Genie Space ID to wire the panel to |
| `panel_title` | string | No | Display title for the panel. Default: `"Ask Genie"` |

**Returns:**
- `client/src/components/AskGeniePanel.tsx` — React component using `GenieChat`
- `app.yaml (patch)` — env entry for `DATABRICKS_GENIE_SPACE_ID` with `valueFrom: genie-space`
- `app.ts (patch)` — `genie()` plugin import

---

### Tool 4: `appkit_deploy`

Deploy a Databricks App from a workspace source path. Creates the app if it doesn't exist, then triggers deployment.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `app_name` | string | Yes | Databricks App name (<=26 chars, lowercase/hyphens) |
| `source_code_path` | string | Yes | Workspace path with app source, e.g. `/Workspace/Users/me@co.com/my-app` |

> **Note:** This tool runs as the MCP service principal. If validate or deploy fails with folder / `permission_denied`, **grant the MCP SP** `CAN_READ` (validate) and `CAN_MANAGE` (deploy) on the app’s workspace directory and on the app resource — use `service_principal_client_id` from `appkit_get_app_status` (UUID, not numeric id). See Deploy Rules in `.assistant_instructions.md` and `troubleshooting_gc.md`. **Do not** use a Databricks Job or `_deploy_app` for deploy; the supported path is SDP (`validate_and_deploy` + permissions).

---

### Tool 5: `appkit_add_analytics`

Add a SQL analytics query and matching visualization component.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query_name` | string | Yes | Name for the query (becomes filename and queryKey), e.g. `sales_by_region` |
| `sql` | string | Yes | Databricks SQL query text (Spark SQL dialect) |
| `chart_type` | string | No | `bar`, `line`, `area`, `pie`, `donut`, `scatter`, `heatmap`, or `table`. Default: `bar` |
| `x_key` | string | No | Column name for X axis (auto-detected if omitted) |
| `y_key` | string | No | Column name for Y axis (auto-detected if omitted) |

**Returns:**
- `config/queries/{query_name}.sql` — the SQL file
- `client/src/components/{QueryName}Chart.tsx` — React chart component using `@databricks/appkit-ui/react`
- `app.yaml (patch)` — env entry for `DATABRICKS_WAREHOUSE_ID`
- `app.ts (patch)` — `analytics()` plugin import

---

### Tool 6: `appkit_add_files_browser`

Scaffold a UC Volumes file browser panel using `DirectoryList` from `@databricks/appkit-ui/react`.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| *(none)* | — | — | This tool takes no parameters |

**Returns:**
- `client/src/components/FilesBrowser.tsx` — React component using `DirectoryList` from `@databricks/appkit-ui`
- `app.ts (patch)` — `files()` plugin import

---

### Tool 7: `appkit_validate`

Validate an AppKit app before deployment. Checks that the workspace path contains required files.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `app_name` | string | Yes | Databricks App name |
| `source_code_path` | string | Yes | Workspace path with the app source |

**Checks performed:** `app.yaml` exists, `package.json` exists, `client/` directory exists, `server/` directory exists, `config/` directory exists, app exists in workspace.

---

### Tool 8: `appkit_list_apps`

List all Databricks Apps in the workspace with their status, URLs, and compute state.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| *(none)* | — | — | This tool takes no parameters |

---

### Tool 9: `appkit_get_app_status` (NEW)

Get detailed status of a Databricks App including compute state, active deployment, resources, service principal, and URL. More detailed than `appkit_list_apps`.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `app_name` | string | Yes | Databricks App name |

**Returns:**
- `app_name`, `url`, `compute_state`
- `service_principal_client_id` — the SP's UUID for permission grants
- `resources` — list of bound resources (postgres, sql-warehouse, etc.)
- `recent_deployments` — last 5 deployments with state, message, and source_code_path

---

### Tool 10: `appkit_provision_lakebase` (NEW)

Provision a Lakebase instance for an app and bind it as a postgres resource. Creates the instance if it doesn't exist, discovers the database path, and binds the postgres resource to the app.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `app_name` | string | Yes | Databricks App name (also used as instance name) |
| `db_schema` | string | No | Schema name for app tables. Defaults to app_name with hyphens→underscores |

**Returns:**
- `instance` — creation status message
- `branch_path`, `database_path` — Lakebase paths
- `resource_bound` — whether the postgres resource was bound
- `app_yaml_env` — env var snippet for `LAKEBASE_ENDPOINT` + `DB_SCHEMA`

---

### Tool 11: `appkit_manage_app_resources`

Add or update a resource binding on a Databricks App.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `app_name` | string | Yes | Databricks App name |
| `resource_type` | string | Yes | One of: `postgres`, `secret`, `sql-warehouse`, `serving-endpoint` |
| `resource_name` | string | Yes | Name for the resource binding (used in `valueFrom`) |
| `config` | dict | No | Type-specific config (see below) |

**Config keys by type:**
- `postgres`: `{ branch, database, permission }`
- `secret`: `{ scope, key, permission }`
- `sql-warehouse`: `{ id, permission }`
- `serving-endpoint`: `{ name, permission }`

---

## Tool Categories Summary

| Category | Tools | When to Use |
|----------|-------|-------------|
| **Scaffold** | `appkit_scaffold_app` | Creating a new AppKit project from scratch |
| **Deploy** | `appkit_deploy`, `appkit_validate` | Deploying to Databricks Apps, pre-deploy validation |
| **Lakebase** | `appkit_add_lakebase`, `appkit_provision_lakebase` | Adding Lakebase boilerplate + provisioning instances |
| **Analytics** | `appkit_add_analytics` | Adding SQL queries + chart visualizations |
| **Genie** | `appkit_add_genie_panel` | Adding conversational AI analytics |
| **Files** | `appkit_add_files_browser` | UC Volumes file browsing |
| **Management** | `appkit_list_apps`, `appkit_get_app_status` | Listing, inspecting apps |
| **Infrastructure** | `appkit_manage_app_resources` | Resource binding |

---

## Plugin Registry

Each plugin adds imports, plugin calls, env vars, and extra dependencies:

| Plugin | Import | `app.ts` Call | Required Env Var | Extra Deps |
|--------|--------|---------------|------------------|------------|
| `analytics` | `analytics` | `analytics()` | `DATABRICKS_WAREHOUSE_ID` (`valueFrom: sql-warehouse`) | — |
| `genie` | `genie` | `genie()` | `DATABRICKS_GENIE_SPACE_ID` (`valueFrom: genie-space`) | — |
| `lakebase` | `lakebase` | `lakebase()` | `LAKEBASE_ENDPOINT` (`valueFrom: postgres`) + `DB_SCHEMA` | `@databricks/lakebase` |
| `files` | `files` | `files()` | — | — |
| `server` | `server` | `server()` | — | — |

> **Important:** Plugins that require env vars (`analytics`, `genie`, `lakebase`) will **crash at startup** if the corresponding resource is not configured in `app.yaml`. Start with only `server()` and add plugins as resources are provisioned.

> **Important:** When using `lakebase()` with custom routes, use **`await createApp({..., async onPluginsReady(appkit) { await registerRoutes(appkit) }})`** — see `@apps_lakebase/gc-prompt-conversion/GENIE-CODE-OVERRIDES.md` Section 6. Do **not** use `server({ autoStart: false })` (removed). Do **not** omit **`await`** on `createApp` — routes may not mount and `/api/health` will 404 or return mock.

---

## Authentication Deep Dive

### Why OAuth M2M (not PAT or notebook token)?

The MCP AppKit Skill App enforces **OAuth authentication**:

| Method | Result | Why |
|--------|--------|-----|
| PAT (Personal Access Token) | 401 Unauthorized | MCP server rejects non-OAuth tokens |
| Notebook API token | 401 Unauthorized | Notebook tokens are internal/runtime, not OAuth |
| Default `WorkspaceClient()` | Rejected | Runtime auth type, no OAuth token |
| **SP `client_credentials` grant** | **Works** | Produces a valid OAuth bearer token |

### How `DatabricksMCPClient` handles auth

1. `WorkspaceClient(host, client_id, client_secret)` sets `auth_type = "oauth-m2m"`
2. On first API call, the SDK calls `{host}/oidc/v1/token` with `grant_type=client_credentials`
3. The returned `access_token` (JWT) is passed as `Authorization: Bearer {token}` to the MCP server
4. Token auto-refreshes when it expires (default: 3600s)

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `ModuleNotFoundError: No module named 'databricks_mcp'` | Package not installed | `%pip install databricks-mcp` then restart kernel |
| `ImportError: cannot import name 'Sentinel'` | Outdated `typing_extensions` | `%pip install typing_extensions --upgrade` then restart |
| `MCP connection failed` / `Failed to fetch` | MCP App not running or SP lacks permissions | Check that `mcp-appkit-skill` is ACTIVE in Compute → Apps; grant SP access |
| `401 Unauthorized` on token request | `client_id` or `client_secret` is wrong | Re-generate the OAuth secret and update the `v2v-gc-agent` scope |
| `403 Forbidden` | SP doesn't have workspace access | Grant workspace access to the SP |
| `Unknown plugins: [...]` | Invalid plugin name passed to scaffold | Use only: `analytics`, `genie`, `lakebase`, `files`, `server` |

---

## Workspace-Specific Values

| Parameter | Value |
|-----------|-------|
| Workspace URL | `https://adb-4101016551133680.0.azuredatabricks.net` |
| OIDC Token Endpoint | `https://adb-4101016551133680.0.azuredatabricks.net/oidc/v1/token` |
| MCP Server URL | `https://mcp-appkit-skill-4101016551133680.0.azure.databricksapps.com/mcp` |
| MCP App Name | `mcp-appkit-skill` |
| Secret Scope | `v2v-gc-agent` |
| Secret Keys | `client_id`, `client_secret` |

---

## Version History

| Date | Change |
|------|--------|
| 2025-01 | Initial: async `mcp` SDK + notebook API token (failed — 401) |
| 2025-01 | Switched to async `mcp` SDK + OAuth SP token from `v2v-gc-agent` scope (worked) |
| 2025-01 | `DatabricksMCPClient` + `nest_asyncio` + OAuth SP (simplest, works) |
| 2026-04 | Documented all 11 tools; corrected tool names to `appkit_scaffold_app`/`appkit_deploy` |
| 2026-04 | **Major overhaul:** Replaced tRPC patterns with Express routes (`appkit.server.extend`), fixed Lakebase env (`LAKEBASE_ENDPOINT`/`postgres`), added `.then()` pattern, removed `appkit_add_trpc_route`, updated to correct API patterns |
| 2026-04 | **Trimmed to 11 tools:** Removed `appkit_add_express_route`, `appkit_add_serving_endpoint`, `appkit_add_vector_search`, `appkit_push_files`, `appkit_get_app_logs` (unused by workshop prompts or redundant). Removed `serving`/`vectorSearch` from PLUGIN_REGISTRY. |
| 2026-07 | Added tool hierarchy (MCP primary → native fallback → SDK); fixed import to `databricks_mcp`; added fallback notes per tool; restored `nest_asyncio` requirement |
| 2026-05 | **Jobs removed:** Deploy is SDP-only (`validate_and_deploy` + SDK `w.apps.*` + MCP validate). Dropped `deploy-appkit-app` job and `_deploy_app` notebook; grant MCP SP on workspace path instead. |
