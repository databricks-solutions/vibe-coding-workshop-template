# Pre-req: MCP AppKit setup (admin)

> **Audience:** Workspace admins preparing **Apps Lakebase Genie** workshops that use **MCP AppKit** tools (`mcp-appkit-skill`).
>
> **Outcome:** One shared Databricks App exposing the AppKit MCP endpoint, plus a **service principal** and **`v2v-gc-agent`** secret scope so participants can authenticate with OAuth M2M from notebooks.
>
> **Participant follow-up:** After you finish this guide, attendees run **[`apps_lakebase/prompts/mcp-setup-gc.md`](apps_lakebase/prompts/mcp-setup-gc.md)** Step 1 (connectivity) and Step 2 (grant the MCP service principal read access to the workshop repo folder).

**Related workspace checklist:** Foundation items (UC, warehouse, compute, Apps, Lakebase) live in **[`PRE-REQUISITES.md`](PRE-REQUISITES.md)** §1–§5. Complete those first.

---

## 1. When this applies

| Delivery | Action |
|----------|--------|
| **Apps Lakebase Genie + MCP** | Complete **§2** (deploy app) then **§3** (SP + secrets). |
| **Data Product Accelerator Genie only** | **Skip** this document — DPA medallion prompts are SDK-first and do not require `mcp-appkit-skill`. |

---

## 2. Deploy the `mcp-appkit-skill` Databricks App

The MCP server is a **Databricks App** whose HTTP endpoint ends with **`/mcp`**. Deploy it **once** per workshop workspace; all participants share it.

**Source layout in this monorepo:** `mcp-appkit-skill/` at the repository root (next to `apps_lakebase/`). It contains `app.yaml`, `requirements.txt`, `server/main.py`, and a ready-made deploy notebook.

### 2.1 Recommended: run `deploy_mcp_app` from the workspace

1. Ensure the workshop template is available in the workspace (same tree as Genie **`REPO_ROOT`**, e.g. under `/Workspace/Users/<you>/.../vibe-coding-workshop-template` or your Shared mirror).
2. In the workspace UI, open the notebook **`mcp-appkit-skill/deploy_mcp_app`** (path: `{REPO_ROOT}/mcp-appkit-skill/deploy_mcp_app` — Databricks stores it without `.py`).
3. Review **`WORKSPACE_TARGET`** and **`APP_NAME`** in the configuration cell (defaults: `/Workspace/Shared/mcp-appkit-skill` and `mcp-appkit-skill`).
4. **Run all cells** as a user with permission to create Apps and write to `WORKSPACE_TARGET`.

The notebook copies the packaged files from the notebook’s directory into `WORKSPACE_TARGET`, creates the app if missing, deploys, and polls until compute is **ACTIVE**.

### 2.2 Alternative: deploy from an admin notebook (SDK only)

Use this if you cannot open the bundled notebook but can run Python in a notebook with the same file tree available under a known path.

Set `REPO_ROOT` to your workspace checkout of this template (match **`REPO_ROOT`** in [`data_product_accelerator/gc-prompt-conversion/workshop-variables.md`](data_product_accelerator/gc-prompt-conversion/workshop-variables.md)), then:

```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.workspace import ImportFormat
from databricks.sdk.service.apps import App, AppDeployment
import time

w = WorkspaceClient()

APP_NAME = "mcp-appkit-skill"
REPO_ROOT = "/Workspace/Users/YOUR_EMAIL/v2v-in-geniecode/vibe-coding-workshop-template"  # <-- set to your checkout
SRC = f"{REPO_ROOT}/mcp-appkit-skill"
WORKSPACE_TARGET = "/Workspace/Shared/mcp-appkit-skill"

FILES = [
    "app.yaml",
    "requirements.txt",
    "server/__init__.py",
    "server/main.py",
]

w.workspace.mkdirs(WORKSPACE_TARGET + "/server")
for rel in FILES:
    src_path = f"{SRC}/{rel}"
    dst_path = f"{WORKSPACE_TARGET}/{rel}"
    exported = w.workspace.export(path=src_path, format=ImportFormat.AUTO)
    w.workspace.import_(
        path=dst_path,
        content=exported.content,
        format=ImportFormat.AUTO,
        overwrite=True,
    )
    print(f"  ✓ {rel}")

try:
    app_info = w.apps.get(name=APP_NAME)
    print(f"App already exists: {app_info.url}")
except Exception:
    app_info = w.apps.create_and_wait(
        app=App(name=APP_NAME, description="MCP server with 11 AppKit tools")
    )
    print(f"App created: {app_info.url}")

w.apps.deploy(app_name=APP_NAME, app_deployment=AppDeployment(source_code_path=WORKSPACE_TARGET))
print("Deploying...")

for _ in range(60):
    app_info = w.apps.get(name=APP_NAME)
    state = app_info.compute_status.state.name
    if state == "ACTIVE":
        break
    time.sleep(10)

print(f"✓ App is {app_info.compute_status.state.name}: {app_info.url}")
print(f"  MCP endpoint: {app_info.url}/mcp")
```

> **Upstreams:** If your organization maintains a fork, replace `REPO_ROOT` / paths with the folder that contains the same four files. External reference repo pattern: `https://github.com/<YOUR_ORG>/mcp-appkit-skill` (sync those files into `WORKSPACE_TARGET` using Repos or workspace copy, then run from **create app** onward).

### 2.3 Verify the app

```python
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
app_info = w.apps.get(name="mcp-appkit-skill")
assert app_info.compute_status.state.name == "ACTIVE", (
    f"App not active: {app_info.compute_status.state.name}"
)
print(f"✓ MCP AppKit Skill running at {app_info.url}/mcp")
```

**Record the MCP URL** (`https://…/mcp`) — you need it for **`apps_lakebase/prompts/mcp-setup-gc.md`** Step 1a (`MCP_URL`) and any workspace-specific tables in that file.

---

## 3. Service principal, OAuth secret, and `v2v-gc-agent` scope

The MCP server authenticates callers via **OAuth M2M**. Participants read **`client_id`** and **`client_secret`** from a shared **secret scope** (`v2v-gc-agent`) at runtime.

Everything below runs in a **Databricks notebook** (workspace admin).

### 3a. Create a service principal

```python
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
SP_NAME = "v2v-workshop-mcp-sp"

existing = [sp for sp in w.service_principals.list() if sp.display_name == SP_NAME]
if existing:
    sp = existing[0]
    print(f"SP already exists: {sp.display_name}, id={sp.id}, application_id={sp.application_id}")
else:
    sp = w.service_principals.create(display_name=SP_NAME)
    print(f"SP created: {sp.display_name}, id={sp.id}, application_id={sp.application_id}")

SP_ID = sp.id
SP_APP_ID = sp.application_id
print(f"\nSP numeric id: {SP_ID}")
print(f"SP application_id (client_id UUID): {SP_APP_ID}")
```

**UI alternative:** **Settings → Identity and access → Service principals → Add service principal**. The **`application_id`** on the SP page is the **`client_id`**.

### 3b. Generate an OAuth client secret

```python
secret_response = w.service_principal_secrets_proxy.create(service_principal_id=SP_ID)
CLIENT_ID = SP_APP_ID
CLIENT_SECRET = secret_response.secret
print(f"client_id:     {CLIENT_ID}")
print(f"client_secret: {CLIENT_SECRET[:8]}...  (SAVE FULL VALUE — shown only once)")
```

**UI alternative:** Open the SP → **Secrets** → **Generate secret** — copy immediately.

### 3c. Grant the SP `CAN_USE` on the MCP app

```python
from databricks.sdk.service.apps import AppAccessControlRequest, AppPermissionLevel

w.apps.update_permissions(
    app_name="mcp-appkit-skill",
    access_control_list=[
        AppAccessControlRequest(
            service_principal_name=SP_APP_ID,
            permission_level=AppPermissionLevel.CAN_USE,
        )
    ],
)
print(f"✓ Granted CAN_USE on mcp-appkit-skill to {SP_NAME}")
```

### 3d. Create secret scope and store credentials

```python
SCOPE = "v2v-gc-agent"
try:
    w.secrets.create_scope(scope=SCOPE)
    print(f"Scope '{SCOPE}' created.")
except Exception as e:
    if "RESOURCE_ALREADY_EXISTS" in str(e):
        print(f"Scope '{SCOPE}' already exists.")
    else:
        raise

w.secrets.put_secret(scope=SCOPE, key="client_id", string_value=CLIENT_ID)
w.secrets.put_secret(scope=SCOPE, key="client_secret", string_value=CLIENT_SECRET)
print(f"✓ Stored client_id and client_secret in '{SCOPE}'")
```

### 3e. Grant participants read access to the scope

```python
w.secrets.put_acl(scope=SCOPE, principal="users", permission="READ")
print(f"✓ Granted READ on '{SCOPE}' to all users")

# --- OR: grant to a specific AD group ---
# w.secrets.put_acl(
#     scope=SCOPE,
#     principal="workshop-participants",
#     permission="READ",
# )
```

> **Without READ on the scope**, participants see **permission denied** when resolving secrets for MCP.

### 3f. Verify end-to-end (notebook)

Run as a normal user (or admin) in a notebook attached to a cluster or serverless where **`dbutils.secrets`** is available:

```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.catalog import SecurableType

w = WorkspaceClient()
SCOPE = "v2v-gc-agent"

secrets = w.secrets.list_secrets(scope=SCOPE)
keys = [s.key for s in secrets]
assert "client_id" in keys and "client_secret" in keys, f"Missing keys: {keys}"
print(f"✓ Secret scope '{SCOPE}' verified: {keys}")

for acl in w.secrets.list_acls(scope=SCOPE):
    print(f"  {acl.principal}: {acl.permission}")

test_cid = dbutils.secrets.get(scope=SCOPE, key="client_id")
test_csec = dbutils.secrets.get(scope=SCOPE, key="client_secret")
sp_client = WorkspaceClient(
    host=w.config.host,
    client_id=test_cid,
    client_secret=test_csec,
)
me = sp_client.current_user.me()
print(f"✓ OAuth M2M auth works — authenticated as: {me.display_name}")
```

**Expected (example):**

```
✓ Secret scope 'v2v-gc-agent' verified: ['client_id', 'client_secret']
  users: READ
✓ OAuth M2M auth works — authenticated as: v2v-workshop-mcp-sp
```

---

## 4. Why this architecture

The **`mcp-appkit-skill`** app hosts **11 tools** (scaffold, deploy, validate, plugins, Lakebase helpers, etc.). Tool calls use **OAuth M2M**. Storing one SP’s credentials in **`v2v-gc-agent`** avoids per-participant SP provisioning; participants only confirm connectivity at session start (**`mcp-setup-gc.md`**).

---

## 5. Troubleshooting

| Symptom | What to check |
|---------|----------------|
| **`SECRET_DOES_NOT_EXIST`** | Run **§3d**; confirm scope name **`v2v-gc-agent`**. |
| **MCP `401 Unauthorized`** | Regenerate secret (**§3b**), update **`client_secret`** in scope (**§3d**). |
| **MCP `403 Forbidden`** | Re-run **§3c**; confirm SP **`CAN_USE`** on **`mcp-appkit-skill`**. |
| **App not found / not ACTIVE** | Re-run **§2**; confirm Apps enabled (**[`PRE-REQUISITES.md`](PRE-REQUISITES.md)** §5). |
| **Deploy notebook cannot read source files** | Confirm **`REPO_ROOT`** checkout includes **`mcp-appkit-skill/`** or use **§2.2** with correct paths. |

---

## 6. Admin checklist

- [ ] **`mcp-appkit-skill`** app exists and compute is **ACTIVE**; MCP URL recorded (**§2**).
- [ ] Service principal created (**§3a**); OAuth secret saved once (**§3b**).
- [ ] SP granted **`CAN_USE`** on **`mcp-appkit-skill`** (**§3c**).
- [ ] Scope **`v2v-gc-agent`** holds **`client_id`** and **`client_secret`** (**§3d**).
- [ ] Participants (or **`users`**) have **READ** on the scope (**§3e**).
- [ ] **§3f** verification succeeds from a notebook.

Then send participants to **`apps_lakebase/prompts/mcp-setup-gc.md`**.
