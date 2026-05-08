# MCP Setup — optional facilitator track

> **Not** part of the default Genie prompt path (`workshop-variables.md` + `validate_and_deploy`). For workspace admins running an optional MCP AppKit helper app.

**MCP tool reference:** [`../gc-prompt-conversion/MCP-appkit_tooling.md`](../gc-prompt-conversion/MCP-appkit_tooling.md).

---

## How This File Is Organized

| Section | Who | When |
|---------|-----|------|
| **Admin Pre-Work** (summary) | Workshop admin | Once, days before the workshop |
| **Step 1: Verify MCP Connectivity** | Each participant | Start of every session |
| **Step 2: Grant MCP SP Repo Access** | Each participant | Once per repo folder |

If the `v2v-gc-agent` secret scope already has `client_id` and `client_secret`, **skip straight to Step 1**.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  Admin pre-work (PRE-REQUISITES.md § 6)                          │
│                                                                  │
│   Service Principal ──► OAuth Client ID + Secret                 │
│                              │                                   │
│                              ▼                                   │
│                     Databricks Secret Scope                      │
│                      scope: "v2v-gc-agent"                         │
│                      keys:  client_id, client_secret             │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│  Genie Code uses (at runtime — Step 1 below)                     │
│                                                                  │
│   dbutils.secrets.get("v2v-gc-agent", "client_id")                 │
│   dbutils.secrets.get("v2v-gc-agent", "client_secret")             │
│           │                                                      │
│           ▼                                                      │
│   WorkspaceClient(host, client_id, client_secret)                │
│           │                                                      │
│           ▼                                                      │
│   DatabricksMCPClient  ──►  MCP AppKit Skill App                 │
│                             ├─ Scaffold                          │
│                             │   └─ appkit_scaffold_app           │
│                             ├─ Deploy & Validate                 │
│                             │   ├─ appkit_deploy                 │
│                             │   ├─ appkit_validate               │
│                             │   └─ appkit_list_apps              │
│                             ├─ Plugins                           │
│                             │   ├─ appkit_add_lakebase           │
│                             │   ├─ appkit_add_analytics          │
│                             │   ├─ appkit_add_genie_panel        │
│                             │   └─ appkit_add_files_browser      │
│                             ├─ Infrastructure                    │
│                             │   ├─ appkit_provision_lakebase     │
│                             │   └─ appkit_manage_app_resources   │
│                             ├─ Management                        │
│                             │   ├─ appkit_list_apps              │
│                             │   └─ appkit_get_app_status         │
│                             └─ (11 tools total)                  │
└──────────────────────────────────────────────────────────────────┘
```

> **Note on `appkit_deploy` identity:** The `appkit_deploy` MCP tool runs as the **service principal** behind the MCP server, not the current Genie Code user. The SP needs CAN_MANAGE on both the app and the workspace directory — see `03-appkit-deploy/SKILL.md` Step 2 for the permission grants. If the SP can't be granted access, use the deploy job fallback instead (Step 3 Option B).

---

## Admin Pre-Work (one-time setup)

The full step-by-step instructions for admin setup are in **`PRE-REQUISITES.md` § 6** (items 6a–6e). Here's a summary:

| Sub-step | What | PRE-REQUISITES.md |
|----------|------|-------------------|
| 6a | Create a service principal in Account Console | § 6a |
| 6b | Generate an OAuth client secret (save immediately) | § 6b |
| 6c | Grant SP workspace User role + Can Use on `mcp-appkit-skill` | § 6c |
| 6d | Create `v2v-gc-agent` secret scope, store `client_id` + `client_secret` | § 6d |
| 6e | Verify with `validate-prereqs.py` | § 6e |

> **Already done?** If `validate-prereqs.py` passes all checks, skip to Step 1.

---

## Step 1: Verify MCP Connectivity

> **This is the only step participants run at the start of the workshop.** Admin pre-work (above) must be completed beforehand.

### 1a: Install and Connect

```python
%pip install databricks-mcp
```

> **Kernel restart required.** The `databricks-mcp` package pulls in `pydantic` v2.13+ which needs `typing_extensions` ≥ 4.15 (for `Sentinel`). The serverless runtime ships an older version. After pip install, you **must** restart the Python kernel before importing — otherwise you'll get `ImportError: cannot import name 'Sentinel' from 'typing_extensions'`.

```python
dbutils.library.restartPython()
```

Then in a **new cell** (after the kernel restarts):

```python
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

tools = mcp_client.list_tools()
tool_names = [t.name for t in tools]
print(f"MCP OK. {len(tools)} tools: {tool_names}")

# Verify core tools
for tool in ["appkit_scaffold_app", "appkit_deploy", "appkit_validate", "appkit_add_lakebase", "appkit_list_apps"]:
    assert tool in tool_names, f"Missing: {tool}"
print("All core tools verified. Ready to go!")
```

**Expected output:**

```
Auth type: oauth-m2m
MCP OK. 11 tools: ['appkit_scaffold_app', 'appkit_add_lakebase', ...]
All core tools verified. Ready to go!
```

> **Full validation:** For a comprehensive check (SDK, OAuth token, MCP server, Apps API, Lakebase API), run `apps_lakebase/skills/00-appkit-navigator/scripts/validate-prereqs.py`.

### 1b: If It Fails

| Error | Cause | Fix (admin action) |
|-------|-------|-----|
| `SECRET_DOES_NOT_EXIST` or scope not found | Admin pre-work not completed | Run `PRE-REQUISITES.md` § 6d |
| `401 Unauthorized` on token request | `client_id` or `client_secret` is wrong | Re-generate OAuth secret (§ 6b), update scope (§ 6d) |
| `403 Forbidden` | SP doesn't have workspace access | Complete § 6c |
| `MCP connection failed` | MCP App not running or SP lacks app permissions | Check `mcp-appkit-skill` is ACTIVE; grant SP access (§ 6c) |
| `ModuleNotFoundError: databricks_mcp` | Package not installed | Run `%pip install databricks-mcp -q` then restart kernel |
| `ImportError: cannot import name 'Sentinel'` | Outdated `typing_extensions` | Run `dbutils.library.restartPython()` (see 1a above) |
| `appkit_validate` says `app.yaml not found` but files exist | MCP SP lacks `CAN_READ` on repo folder | Run Step 2 below to grant SP read access |

> **Fallback:** If MCP setup fails entirely, the standard workshop still proceeds with **SDK only** (`workshop-variables.md`, `write_file`, `validate_and_deploy`). This MCP doc is optional.

---

## Step 2: Grant MCP SP Read Access to Your Repo Folder

The MCP tools (`appkit_validate`, `appkit_deploy`) run as the MCP app's service principal. This SP needs `CAN_READ` on your workspace repo folder — without it, `appkit_validate` reports false negatives like `app.yaml not found` even when files exist.

Run this **once** after MCP connectivity is confirmed:

```python
from databricks.sdk.service.iam import AccessControlRequest, PermissionLevel

MCP_APP_NAME = "mcp-appkit-skill"
mcp_app_info = w.apps.get(MCP_APP_NAME)
mcp_sp_app_id = mcp_app_info.service_principal_client_id
print(f"MCP app SP: {mcp_app_info.service_principal_name}  (application_id: {mcp_sp_app_id})")

repo_path = REPO_ROOT  # e.g. /Workspace/Users/{email}/v2v-in-geniecode/vibe-coding-workshop-template
repo_info = w.workspace.get_status(repo_path)

w.permissions.update(
    request_object_type="repos",
    request_object_id=str(repo_info.object_id),
    access_control_list=[
        AccessControlRequest(
            service_principal_name=mcp_sp_app_id,
            permission_level=PermissionLevel.CAN_READ,
        )
    ],
)
print(f"✓ Granted CAN_READ on repo to MCP SP ({mcp_sp_app_id})")
```

> **Why is this needed?** Workspace-level User access does not cascade into Git Repo folders. The SP needs explicit `CAN_READ` on the repo object for `w.workspace.get_status()` calls inside the MCP tools to succeed.

---

## Workspace-Specific Values

These values are hardcoded in the workshop prompts. If adapting for a different workspace, update them:

| Parameter | Value | Where to Find |
|-----------|-------|---------------|
| Workspace Host | `https://adb-4101016551133680.0.azuredatabricks.net` | Workspace URL bar |
| Workspace ID | `4101016551133680` | Last segment of workspace URL |
| MCP Server URL | `https://mcp-appkit-skill-4101016551133680.0.azure.databricksapps.com/mcp` | Compute → Apps → mcp-appkit-skill |
| Secret Scope | `v2v-gc-agent` | Hardcoded in all `_gc.md` prompts |
| Secret Keys | `client_id`, `client_secret` | Hardcoded in all `_gc.md` prompts |

---

## What's Next?

Once Steps 1-2 pass, the MCP client and workspace client are ready. The workshop prompts will be provided to you — paste each one into a new Genie Code conversation in sequence.

> **Troubleshooting:** If errors occur during any workshop step, consult `@apps_lakebase/gc-prompt-conversion/troubleshooting_gc.md` for the error-to-fix lookup tables.
