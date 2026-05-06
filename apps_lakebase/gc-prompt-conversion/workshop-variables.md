# Workshop Variables — apps_lakebase Standard Setup

**Read this BEFORE following any prompt in `apps_lakebase/prompts/`.** This file defines the standard variables, file-writing helper, and four AppKit-aware SDK helpers that every Genie Code prompt depends on.

> **Companion:** Read `@apps_lakebase/gc-prompt-conversion/gc-prompt-header.md` first for environment constraints and error-handling protocol.

---

## Three-Cell Bootstrap

Every prompt must run these three cells (in separate cells) before doing anything else:

```python
# Cell 1 — install packages (own cell, run first)
%pip install databricks-mcp --upgrade databricks-sdk -q
```

```python
# Cell 2 — restart the kernel (required: databricks-mcp pulls a newer pydantic/typing_extensions)
dbutils.library.restartPython()
```

```python
# Cell 3 — re-derive variables AND helpers AFTER restart (Python state was wiped)
# Paste the entire block below into Cell 3.

import base64
import time
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.workspace import ImportFormat
from databricks.sdk.service.apps import App, AppDeployment

w = WorkspaceClient()

email = spark.sql("SELECT current_user()").collect()[0][0]
prefix = email.split("@")[0].replace(".", "-")
parts = prefix.split("-")
APP_NAME = f"{parts[0]}-{parts[-1][0]}-booking-app"[:26]
DB_SCHEMA = APP_NAME.replace("-", "_")
REPO_ROOT = f"/Workspace/Users/{email}/v2v-in-geniecode/vibe-coding-workshop-template"
APP_BASE = f"{REPO_ROOT}/apps_lakebase/{APP_NAME}"

def write_file(path, content):
    """Write a plain text file (TypeScript, JSON, YAML, markdown) to the workspace.
    Creates parent dirs automatically. Encodes content to base64 for the SDK."""
    parent = "/".join(path.split("/")[:-1])
    w.workspace.mkdirs(parent)
    w.workspace.import_(
        path=path,
        content=base64.b64encode(content.encode()).decode(),
        format=ImportFormat.AUTO,
        overwrite=True,
    )
    print(f"\u2713 Wrote {path.split('/')[-1]}")

def setup_mcp_client(secret_scope="v2v-gc-agent",
                     client_id_key="client_id",
                     client_secret_key="client_secret",
                     mcp_app_slug="mcp-appkit-skill"):
    """One-shot MCP + WorkspaceClient bootstrap.

    Pulls v2v-gc-agent OAuth secrets, derives MCP_URL from the workspace host,
    instantiates DatabricksMCPClient with M2M auth, asserts the 11 core
    AppKit tools exist. Returns (w, mcp_client).

    Replaces the 30-50 line Session Recovery block currently duplicated
    across `setup_lakebase_gc.md`, `wire_ui_to_lakebase_gc.md`,
    `deploy_and_test_gc.md`, and `one-ui-design-local.md`.

    PREREQUISITE: cells 1 (pip install) and 2 (restartPython) above MUST
    have run first. This helper does NOT install packages or restart the
    kernel.

    Args:
        secret_scope: Databricks secret scope holding the OAuth client_id/secret
                      (default: "v2v-gc-agent" — set up by the workshop admin).
        client_id_key: secret key for the OAuth client_id.
        client_secret_key: secret key for the OAuth client_secret.
        mcp_app_slug: slug of the MCP AppKit Skill App (default: "mcp-appkit-skill").

    Returns:
        (w, mcp_client) — both ready to use.
    """
    import nest_asyncio
    from databricks.sdk import WorkspaceClient as _WC
    from databricks_mcp import DatabricksMCPClient

    nest_asyncio.apply()

    w_local = _WC()
    cid = w_local.dbutils.secrets.get(scope=secret_scope, key=client_id_key)
    csecret = w_local.dbutils.secrets.get(scope=secret_scope, key=client_secret_key)
    host = spark.conf.get("spark.databricks.workspaceUrl")

    w_oauth = _WC(
        host=f"https://{host}",
        client_id=cid,
        client_secret=csecret,
    )

    app_obj = w_local.apps.get(name=mcp_app_slug)
    mcp_url = f"{app_obj.url.rstrip('/')}/mcp"
    mcp_client = DatabricksMCPClient(server_url=mcp_url, workspace_client=w_oauth)

    tools = mcp_client.list_tools()
    tool_names = [t.name for t in tools]
    print(f"MCP OK. {len(tools)} tools: {tool_names}")

    core = ["appkit_scaffold_app", "appkit_deploy", "appkit_validate", "appkit_add_lakebase", "appkit_list_apps"]
    missing = [t for t in core if t not in tool_names]
    if missing:
        raise RuntimeError(f"MCP missing core tools: {missing}. Run mcp-setup-gc.md.")
    print("All core tools verified. Ready to go!")

    return w_local, mcp_client

def ensure_app_active(app_name, max_wait_minutes=10):
    """Start the app if STOPPED, poll compute_status until ACTIVE.

    Uses .state.name (returns "ACTIVE") — NEVER str(state) (returns
    "ComputeState.ACTIVE") which never matches and infinite-loops.

    Returns the final compute state string.

    Replaces the ~12-line ensure-active block duplicated in
    `one-ui-design-local.md` and `deploy_and_test_gc.md`.
    """
    app = w.apps.get(app_name)
    compute = app.compute_status.state.name if app.compute_status and app.compute_status.state else "UNKNOWN"
    if compute == "ACTIVE":
        return compute

    print(f"App compute is {compute}, starting...")
    w.apps.start(app_name)
    iters = max(1, int((max_wait_minutes * 60) / 15))
    for i in range(iters):
        time.sleep(15)
        app = w.apps.get(app_name)
        compute = app.compute_status.state.name if app.compute_status and app.compute_status.state else "UNKNOWN"
        print(f"  [{i:2d}] {compute}")
        if compute == "ACTIVE":
            return compute
        if compute in ("STOPPED", "ERROR"):
            w.apps.start(app_name)
    return compute

def validate_and_deploy(app_name, app_base, description="StayFindr -- AppKit booking app"):
    """End-to-end deploy contract for AppKit apps.

    Steps:
      1. mcp_client.call_tool('appkit_validate', ...) and print result
      2. w.apps.get(app_name) or w.apps.create_and_wait(...) if missing
      3. ensure_app_active(app_name)
      4. w.apps.deploy_and_wait(app_name=..., app_deployment=AppDeployment(source_code_path=app_base))
      5. Return (deployment, app_url)

    Collapses the 35-50 line Validate+Create+Activate+Deploy block in
    `one-ui-design-local.md` and `deploy_and_test_gc.md` into a single call.

    REQUIRES: `mcp_client` in scope (call setup_mcp_client() first).
    """
    print(f"Validating {app_name} via MCP appkit_validate...")
    result = mcp_client.call_tool("appkit_validate", {
        "app_name": app_name,
        "source_code_path": app_base,
    })
    print(result.content[0].text if hasattr(result, "content") else result)

    try:
        app = w.apps.get(app_name)
        print(f"App exists: {app_name}")
    except Exception:
        print(f"Creating app {app_name}...")
        app = w.apps.create_and_wait(
            app=App(name=app_name, description=description, default_source_code_path=app_base)
        )
        print(f"\u2713 App created")

    ensure_app_active(app_name)

    print(f"Deploying {app_name}...")
    deployment = w.apps.deploy_and_wait(
        app_name=app_name,
        app_deployment=AppDeployment(source_code_path=app_base),
    )
    state = deployment.status.state.name if deployment.status and deployment.status.state else "UNKNOWN"
    app_url = w.apps.get(app_name).url
    print(f"\u2713 Deploy: {deployment.deployment_id} -- {state}")
    print(f"  URL: {app_url}")
    return deployment, app_url

def verify_postgres_resource(app_name):
    """Print pass/fail for postgres-type resource binding.

    AppKit's lakebase() plugin REQUIRES a postgres-type AppResource.
    A database-type binding causes ConfigurationError at startup -- the
    most common Lakebase wiring failure in the workshop.

    Returns True if a postgres resource is bound, False otherwise.

    Replaces the 10-15 line verification block duplicated in
    `setup_lakebase_gc.md` Step 5 and `deploy_and_test_gc.md` Step 3 + 6b.
    """
    app = w.apps.get(name=app_name)
    has_postgres = False
    for r in (app.resources or []):
        if r.postgres:
            print(f"  \u2713 Resource '{r.name}' \u2192 postgres type, branch={r.postgres.branch}, db={r.postgres.database}")
            has_postgres = True
        elif r.database:
            print(f"  \u2717 Resource '{r.name}' \u2192 database type -- WRONG. AppKit needs postgres type.")
            print(f"    Fix: re-run setup_lakebase_gc.md Step 2c to rebind as AppResourcePostgres")
    if not has_postgres:
        print("  \u2717 No postgres resource found -- app will crash with ConfigurationError. Run setup_lakebase_gc.md Step 2.")
    return has_postgres

print(f"APP_NAME:  {APP_NAME}")
print(f"DB_SCHEMA: {DB_SCHEMA}")
print(f"REPO_ROOT: {REPO_ROOT}")
print(f"APP_BASE:  {APP_BASE}")
```

---

## Helper Quick Reference

| Helper | Purpose | Replaces |
|--------|---------|----------|
| `write_file(path, content)` | Write workspace file (.ts, .json, .yaml, .md) | `databricks workspace import` / `echo > file` |
| `setup_mcp_client()` | Bootstrap M2M MCP + WorkspaceClient, verify 11 core tools | ~30-50 line Session Recovery block (5x duplicate) |
| `ensure_app_active(app_name)` | Start app if STOPPED, poll compute until ACTIVE (uses `.state.name`) | ~12 line activate block (3x duplicate) |
| `validate_and_deploy(app_name, app_base)` | MCP `appkit_validate` + create-if-missing + ensure-ACTIVE + `deploy_and_wait` + URL print | ~35-50 line deploy block (3x duplicate, 13 `deploy_and_wait` callsites) |
| `verify_postgres_resource(app_name)` | Check resource binding is `postgres`-type (not `database`) | ~10-15 line verification block (3x duplicate) |

---

## AppKit Constraints Cheat-Sheet (for `validate_and_deploy` users)

| Rule | Why |
|------|-----|
| Use `.state.name` for compute polling, NEVER `str(state)` | `str(state)` returns `"ComputeState.ACTIVE"`, breaks `== "ACTIVE"` checks |
| Wrap `source_code_path` in `AppDeployment(source_code_path=...)` | `deploy_and_wait()` rejects it as a top-level kwarg |
| `app.yaml` env: `LAKEBASE_ENDPOINT` with `valueFrom: postgres` (NOT `valueFrom: database`) | `lakebase()` plugin requires postgres-type resource binding |
| `app.ts` plugin order: `lakebase()` BEFORE `server()` | `appkit.lakebase` must exist when routes register |
| `app.ts` (Lakebase wired): **`await createApp({... onPluginsReady ...})`** | Without `await`, `tsx` can finish before routes bind — `/api/health` 404 or perpetual **Mock Data**. Do **not** use bare `createApp({...})`. Do **not** use `.then()` chains for this workshop |
| `package.json` build script: `"(npm run typegen || true) && vite build"` | `appkit build` does not exist; typegen failures must not block vite |
| `app.yaml` command: `["./node_modules/.bin/tsx", "app.ts"]` (NOT `npx`) | `npx` not on PATH at runtime |
