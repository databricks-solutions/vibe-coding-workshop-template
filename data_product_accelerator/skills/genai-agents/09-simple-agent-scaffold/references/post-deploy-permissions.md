# Post-Deploy Service Principal Permissions

Loaded by `SKILL.md` Step 5 when the deployed endpoint SP needs runtime access beyond what auth passthrough covers.

## Why this is needed

`databricks.agents.deploy()` creates a system service principal (SP) for the endpoint. Automatic Auth Passthrough — driven by the `resources=[...]` declarations in `log_model()` — covers the **Genie Space API** (via `DatabricksGenieSpace`) and the **LLM serving endpoint** (via `DatabricksServingEndpoint`).

It does **not** automatically grant:

- `CAN_USE` on the **SQL warehouse** that powers each Genie Space
- `SELECT` / `USE SCHEMA` / `USE CATALOG` on the **Unity Catalog tables** the Genie Space queries

For OBO (on-behalf-of) calls from AI Playground, the caller's identity is used and these grants may not matter. For programmatic calls via API tokens, or when the Genie Space's backing warehouse auth is scoped to the SP, the grants below are required.

## Step 1: Find the SP UUID

Either option works:

- **From the first error.** The first `PERMISSION_DENIED` response from the endpoint contains the SP UUID, e.g.:
  ```
  PERMISSION_DENIED: Service principal 12345678-abcd-... is not authorized to use this SQL Endpoint.
  ```
- **From the Serving UI.** Workspace → Serving → your endpoint → **Events** tab → look for the SP creation event at deploy time.

Export it for the commands below:

```bash
SP_UUID="12345678-abcd-efgh-ijkl-mnopqrstuvwx"
```

## Step 2: Grant `CAN_USE` on the SQL warehouse

The Genie Space backing warehouse must be reachable by the endpoint SP.

```python
import os, requests
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
host  = w.config.host
token = w.config.token or os.environ["DATABRICKS_TOKEN"]

warehouse_id = "<WAREHOUSE_ID>"   # from the Genie Space config
sp_uuid      = os.environ["SP_UUID"]

r = requests.patch(
    f"{host}/api/2.0/permissions/sql/warehouses/{warehouse_id}",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "access_control_list": [
            {"service_principal_name": sp_uuid, "permission_level": "CAN_USE"}
        ]
    },
    timeout=30,
)
r.raise_for_status()
print(r.json())
```

CLI equivalent (uses the same REST endpoint under the hood):

```bash
databricks permissions update sql/warehouses "$WAREHOUSE_ID" \
  --json "{\"access_control_list\":[{\"service_principal_name\":\"$SP_UUID\",\"permission_level\":\"CAN_USE\"}]}" \
  --profile $PROFILE
```

## Step 3: Grant UC privileges on the tables the Genie Space reads

Only needed when the Genie Space reads via the SP's identity (not OBO).

```sql
GRANT USE CATALOG ON CATALOG <catalog>          TO `<SP_UUID>`;
GRANT USE SCHEMA  ON SCHEMA  <catalog>.<schema> TO `<SP_UUID>`;
GRANT SELECT      ON SCHEMA  <catalog>.<schema> TO `<SP_UUID>`;
```

Or per-table if you want narrower access:

```sql
GRANT SELECT ON TABLE <catalog>.<schema>.<table> TO `<SP_UUID>`;
```

Run these from a SQL editor or warehouse the caller owns `MANAGE` on. If you lack `MANAGE`, ask a workspace admin or the catalog owner.

## Step 4: Verify

Re-run the same domain-specific data question that previously returned `PERMISSION_DENIED`:

```bash
databricks serving-endpoints query <endpoint-name> \
  --json '{"input":[{"role":"user","content":"<your data question>"}]}' \
  --profile $PROFILE
```

If the CLI truncates the output (shows only `id` / `object`), fall back to `curl`:

```bash
curl -sS -X POST \
  -H "Authorization: Bearer $DATABRICKS_TOKEN" \
  -H "Content-Type: application/json" \
  "$DATABRICKS_HOST/serving-endpoints/<endpoint-name>/invocations" \
  -d '{"input":[{"role":"user","content":"<your data question>"}]}' | jq
```

## OBO vs SP — quick reference

| Caller path | Auth identity | Needs SP grants? |
|---|---|---|
| AI Playground (user logged in) | OBO — caller's user identity | No (assuming the user has table access) |
| API token from another SP / service | Endpoint SP | **Yes** — grants in Steps 2–3 required |
| API token from the same user as Playground | OBO — user identity | No |

## Common failure modes

| Symptom | Likely cause | Fix |
|---|---|---|
| `PERMISSION_DENIED: ... not authorized to use this SQL Endpoint` | Step 2 not done | Run the PATCH above |
| Genie returns "no permission on table `x`" | Step 3 not done for that catalog/schema | Run the GRANTs above |
| `GRANT ... MANAGE required` when running Step 3 | The caller lacks `MANAGE` on the securable | Ask the catalog/schema owner to run it |
| Grants look correct but query still fails | Caching / stale tokens | Redeploy the endpoint (`agents.deploy(...)` again) or wait ~1 minute |
