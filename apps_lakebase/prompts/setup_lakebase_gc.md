## Context

> **On ANY error:** STOP and read `@apps_lakebase/gc-prompt-conversion/troubleshooting_gc.md`. Match the error message or symptom in the tables. Apply the fix exactly as described. Do NOT improvise a workaround before checking the troubleshooting reference.

You are Genie Code, an AI assistant on the Databricks workspace. You are adding the Lakebase (PostgreSQL) package to an existing AppKit application and creating a Lakebase database instance. This is a **config-only** step — create the database instance, bind it to the app, add the npm dependency, and configure YAML files, but do NOT modify `server.ts`. Plugin registration happens in the **Wire Lakebase Backend** step.

Key requirements:

- Create a Lakebase database instance via the **Databricks SDK** (`w.database` API)
- Use the MCP `appkit_add_lakebase` tool for boilerplate file snippets (this tool does NOT create Lakebase projects — you must create the project/database first via SDK)
- Grant the app's service principal `DATABRICKS_SUPERUSER` access
- Bind the database as a `postgres`-type resource on the app via `w.apps.update()` (AppKit requires `AppResourcePostgres`, not `AppResourceDatabase`)
- Discover the database path via `w.postgres.list_databases()` for the resource binding
- Add `@databricks/lakebase` to `package.json` dependencies (do NOT register the plugin in `app.ts` yet)
- Configure `app.yaml` with `LAKEBASE_ENDPOINT` (`valueFrom: postgres`) and `DB_SCHEMA` environment variables
- Do NOT deploy in this step — deployment happens in `deploy_and_test_gc.md`
- Do NOT add `lakebase()` to `app.ts` — that happens in `wire_ui_to_lakebase_gc.md`

**Environment:** Genie Code on Databricks workspace (serverless). No CLI, no npm, no Node.js. MCP tools provide boilerplate snippets. Databricks SDK handles Lakebase provisioning and file operations.

**Prompt sequence:** `one-ui-design-local.md` → **this file** → `wire_ui_to_lakebase_gc.md` → `deploy_and_test_gc.md` (see `@apps_lakebase/prompts/README.md`).

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

### Required: Verify Databricks SDK Version

The Lakebase resource binding (Step 2) requires `AppResourcePostgres` from a recent SDK. This was installed in the first workshop prompt. Verify it is available:

```python
from databricks.sdk.service.apps import AppResourcePostgres
print("✓ SDK version OK — AppResourcePostgres available")
```

If this fails with `ImportError`, run:

```python
%pip install --upgrade databricks-sdk -q
dbutils.library.restartPython()
```

---

## Your Task

Create a Lakebase database instance, configure the app to connect to it, and add the npm dependency. Do NOT modify `server.ts` — plugin registration and DDL/seed happen in `wire_ui_to_lakebase_gc.md`.

**First:** Read `apps_lakebase/{APP_NAME}/.vibecoding-state.md` if it exists — it contains resolved issues and variable values from prior phases.

**Working directory:** All app files are under `apps_lakebase/{APP_NAME}/` within the repo.

---

### Step 1: Set Variables

Use `spark.sql("SELECT current_user()")` to get the current user's email. Derive:

| Variable | Derivation | Example |
|----------|-----------|---------|
| `APP_NAME` | `{firstname}-{lastinitial}-booking-app` (max 26 chars) | `jaiwant-j-booking-app` |
| `DB_SCHEMA` | `APP_NAME` with hyphens replaced by underscores | `jaiwant_j_booking_app` |
| `REPO_ROOT` | `/Workspace/Users/{email}/v2v-in-geniecode/vibe-coding-workshop-template` | |
| `APP_BASE` | `{REPO_ROOT}/apps_lakebase/{APP_NAME}` | |

Also set up the `write_file` helper using the Databricks SDK (same as prior steps).

---

### Step 2: Provision Lakebase Infrastructure

Read `@apps_lakebase/skills/04-appkit-plugin-add/SKILL.md` and follow **Steps 3a–3d** to provision the Lakebase infrastructure via SDK:

- **Step 3a** — Create the Lakebase instance (check if it already exists first). Store `read_write_dns` as `LAKEBASE_HOST`.
- **Step 3b** — Create the database catalog with `create_database_if_not_exists=True`. Use `DB_SCHEMA` as the `database_name`.
- **Step 3c** — Grant the app's service principal `DATABRICKS_SUPERUSER` using the proper enum types.
- **Step 3d** — Discover the database path via `w.postgres.list_databases()`, then bind as a `postgres`-type resource named `"postgres"` on the app with `CAN_CONNECT_AND_CREATE` permission.

> **Order matters:** Create instance → Create database → Grant SP role → Bind resource.

---

### Step 3: Get MCP Boilerplate

Call the MCP `appkit_add_lakebase` tool to get file snippets:

```python
result = mcp_client.call_tool("appkit_add_lakebase", {
    "app_name": APP_NAME,
    "lakebase_instance_name": APP_NAME,
})
```

> **Important:** `appkit_add_lakebase` does NOT create Lakebase projects or databases. It only returns file snippets (app.yaml patches, server.ts boilerplate, dependencies) that wire an **already-existing** Lakebase project into your AppKit app. Step 2 above handles project creation via the SDK.

> **Fallback:** If the MCP client is unavailable, apply the patterns from `@apps_lakebase/skills/04-appkit-plugin-add/SKILL.md` Steps 2b–2c directly.

Review the returned snippets. Apply the `package.json` and `app.yaml` changes. Do NOT apply `server.ts` changes yet — those happen in `wire_ui_to_lakebase_gc.md`.

---

### Step 4: Configure `app.yaml` and `package.json`

Ensure `package.json` has `@databricks/lakebase` in `dependencies` (not `devDependencies`).

Update `app.yaml` with Lakebase environment variables — see `@apps_lakebase/skills/04-appkit-plugin-add/SKILL.md` Step 2c for the Lakebase `app.yaml` env pattern (`LAKEBASE_ENDPOINT` with `valueFrom: postgres`, `DB_SCHEMA` with your derived value).

> **CRITICAL:** Use `LAKEBASE_ENDPOINT` with `valueFrom: postgres` — NOT `DATABRICKS_LAKEBASE_DB` with `valueFrom: database`. AppKit's `lakebase()` plugin requires a `postgres`-type resource. Using the wrong type causes `ConfigurationError` at startup.

> **Do NOT set `PGHOST`, `PGPORT`, `PGDATABASE` manually** — the `lakebase()` plugin derives these from the `postgres` resource binding.

If `app.yaml` already has other entries, merge — do not overwrite.

---

### Step 5: Verify All Changes

1. **Read `package.json`** — confirm `@databricks/lakebase` is in `dependencies`
2. **Read `app.yaml`** — confirm `LAKEBASE_ENDPOINT` with `valueFrom: postgres` and `DB_SCHEMA` are set
3. **Read `app.ts`** — confirm it is **unchanged** (still uses `createApp({ plugins: [server()] })`)
4. **Check instance status** — `w.database.get_database_instance(name=APP_NAME)` state is `AVAILABLE`
5. **Check resource binding** — `w.apps.get(name=APP_NAME)` resources includes a `postgres`-type resource:

```python
app = w.apps.get(name=APP_NAME)
for r in (app.resources or []):
    pg = r.postgres
    if pg:
        print(f"  ✓ Resource '{r.name}' → branch={pg.branch}, db={pg.database}")
    else:
        print(f"  ⚠ Resource '{r.name}' is NOT postgres type — AppKit will crash. Re-run Step 3d.")
```

---

### Checklist

- [ ] Lakebase instance created — state `AVAILABLE`
- [ ] Database created — name is `{DB_SCHEMA}`
- [ ] App SP granted `DATABRICKS_SUPERUSER`
- [ ] App resource bound — `postgres`-type resource named `postgres` visible (NOT `database` type)
- [ ] `@databricks/lakebase` added to `package.json` `dependencies`
- [ ] `app.ts` is **unchanged** (still `createApp({ plugins: [server()] })`)
- [ ] `DB_SCHEMA` derived from `APP_NAME` (hyphens to underscores)
- [ ] `app.yaml` has `LAKEBASE_ENDPOINT` (`valueFrom: postgres`) and `DB_SCHEMA`
- [ ] `.vibecoding-state.md` updated with: `DB_SCHEMA`, `LAKEBASE_HOST`, instance state, SP IDs

**Previous step:** `one-ui-design-local.md` | **Next step:** `wire_ui_to_lakebase_gc.md`
