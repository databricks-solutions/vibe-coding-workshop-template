# Post-Deploy Service Principal Permissions

Loaded by `SKILL.md` Step 5 when you need the full reference for the endpoint system SP — discovery, UC grants, workspace ACL inheritance, and the OBO-vs-SP matrix. For the happy path, follow **Step 5b** in `SKILL.md`; this doc is the deep dive.

## Why this is needed

`databricks.agents.deploy()` creates a **system service principal (SP)** for every endpoint. Automatic Auth Passthrough — driven by the `resources=[...]` declarations in `log_model()` — covers the **Genie Space API** (via `DatabricksGenieSpace`) and the **LLM serving endpoint** (via `DatabricksServingEndpoint`).

It does **not** automatically grant:

- Unity Catalog privileges (`USE CATALOG`, `USE SCHEMA`, `SELECT`, `EXECUTE`) on the gold tables and TVFs the Genie Space queries.
- Workspace ACLs on the SQL warehouse and Genie Space — these are typically inherited via the `users` group (see Step 2 below).

## Identities you can't see but can grant to

The endpoint system SP is an **invisible platform object**. It is:

- **NOT** in workspace SCIM → `databricks service-principals list` will not return it.
- **IS** enforced by Unity Catalog → `GRANT … TO \`<uuid>\`` works by UUID.
- **IS** an implicit member of the `users` group → workspace ACLs on warehouses and Genie Spaces are typically inherited, no per-SP grant required.

This invisibility is the root cause of the three most common debug dead ends. The next section fixes each one.

## Step 1 — Find the SP UUID (via endpoint events, NOT SCIM)

`agents.deploy()` system SPs are not in SCIM, so `databricks service-principals list` will NOT return them. The first `PERMISSION_DENIED: No access to table X` error does NOT contain a UUID for this variant either. The reliable source is the endpoint's event stream.

### Python (via the Databricks SDK)

```python
from databricks.sdk import WorkspaceClient

def get_endpoint_sp(w: WorkspaceClient, endpoint_name: str) -> str:
    resp = w.api_client.do(
        "GET",
        f"/api/2.0/serving-endpoints/{endpoint_name}/events",
        query={"limit": 200},
    )
    marker = "System service principal creation with ID "
    for e in resp.get("events", []):
        msg = e.get("message", "")
        if marker in msg:
            return msg.split(marker, 1)[1].split(" ", 1)[0]
    raise RuntimeError(
        f"No system SP creation event on {endpoint_name}. "
        f"Endpoint may still be provisioning."
    )

SP_UUID = get_endpoint_sp(WorkspaceClient(), "<your endpoint>")
```

### CLI (bash)

```bash
ENDPOINT="<your agent endpoint>"
SP_UUID=$(databricks api get \
  "/api/2.0/serving-endpoints/$ENDPOINT/events?limit=200" \
  --profile $PROFILE \
  | jq -r '.events[] | select(.message | contains("System service principal creation with ID ")) | .message' \
  | head -1 \
  | sed -E 's/.*System service principal creation with ID ([^ ]+).*/\1/')
echo "Endpoint system SP: $SP_UUID"
```

### Anti-patterns

| What you might try | Why it fails |
|---|---|
| `databricks service-principals list` | System SPs are not in SCIM — this returns user-created SPs only. |
| Grep the `PERMISSION_DENIED` response for a UUID | The `No access to table X` variant does **not** contain a UUID. Only the older `not authorized to use this SQL Endpoint` variant does. |
| Look in the **Events** tab of the Serving UI | The event is there, but the UI truncates long messages. Use the API. |

## Step 2 — Workspace ACLs rely on `users`-group inheritance

System SPs are implicit members of the `users` group. If the `users` group has `CAN_USE` on the warehouse and `CAN_RUN` on the Genie Space (both are workspace defaults on most setups), **NO explicit per-SP grant is needed**.

Verify inheritance:

```bash
WH_ID="<your warehouse id>"
databricks api get /api/2.0/permissions/warehouses/$WH_ID --profile $PROFILE \
  | jq '.access_control_list[] | select(.group_name=="users")'
# Expect: .all_permissions[] with {"permission_level":"CAN_USE","inherited":false}
```

If the `users` entry is missing, grant the **group** ONCE (it's workspace-wide and covers every future `agents.deploy()` endpoint on this workspace):

```bash
databricks api patch /api/2.0/permissions/warehouses/$WH_ID --profile $PROFILE \
  --json '{"access_control_list":[{"group_name":"users","permission_level":"CAN_USE"}]}'
```

### Do NOT try this — it returns `200` but silently drops the entry

```bash
# ❌ BROKEN for system SPs — returns 200 OK but the entry never appears in ACL listing.
databricks api patch /api/2.0/permissions/warehouses/$WH_ID --profile $PROFILE \
  --json "{\"access_control_list\":[{\"service_principal_name\":\"$SP_UUID\",\"permission_level\":\"CAN_USE\"}]}"
```

The Permissions API requires the principal to be in SCIM. System SPs aren't, so the entry is silently discarded. This is the single most misleading call in the agent-deploy permissioning flow — it looks like it worked.

## Step 3 — Grant UC privileges to the SP by UUID

UC is the layer that actually enforces table access for the endpoint's tool calls. Grant by UUID (NOT by `service_principal_name = <uuid>` — that's a workspace-ACL concept that doesn't apply to UC):

```sql
GRANT USE CATALOG ON CATALOG `<catalog>` TO `<SP_UUID>`;
GRANT USE SCHEMA, SELECT, EXECUTE ON SCHEMA `<catalog>`.`<schema>` TO `<SP_UUID>`;
```

Or narrower per-table:

```sql
GRANT SELECT ON TABLE `<catalog>`.`<schema>`.`<table>` TO `<SP_UUID>`;
```

**`EXECUTE` is required** if your Genie Space exposes TVFs (table-valued functions) as certified answers. Without it, TVF calls fail with the same `PERMISSION_DENIED: No access to table X` symptom as a missing `SELECT`. The error does not distinguish between the two.

Idempotent Python variant (preferred, matches Step 5b in `SKILL.md`):

```python
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
for stmt in [
    f"GRANT USE CATALOG ON CATALOG `{CATALOG}` TO `{SP_UUID}`",
    f"GRANT USE SCHEMA, SELECT, EXECUTE ON SCHEMA `{CATALOG}`.`{GOLD_SCHEMA}` TO `{SP_UUID}`",
]:
    w.statement_execution.execute_statement(
        warehouse_id=WAREHOUSE_ID, statement=stmt, wait_timeout="30s"
    )
```

Run as a workspace admin or the catalog/schema owner (`MANAGE` required). If you lack `MANAGE`, ask the owner.

## Step 4 — Verify with a domain-specific data question

A greeting does not exercise the MCP tool-calling path. Use a domain-specific data question via `curl + PAT`:

```bash
ENDPOINT="<your endpoint>"
HOST="$(databricks auth env --profile $PROFILE | jq -r .env.DATABRICKS_HOST)"
TOKEN="$(databricks auth token --profile $PROFILE | jq -r .access_token)"

curl -sS -X POST "$HOST/serving-endpoints/$ENDPOINT/invocations" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"input":[{"role":"user","content":"<domain-specific data question>"}]}' \
  | jq '.output[] | select(.type=="function_call" or .type=="message")'
```

PASS = at least one `function_call` followed by a `message` with real numbers. FAIL (greeting only) = the tool wasn't exercised; tighten the system prompt with a domain nudge or verify the Genie Space has content (Step 5a probes in `SKILL.md`).

## Who runs the MCP tool call? (OBO vs SP — corrected matrix)

| Caller | Identity for `/invocations` | Identity for MCP tool (Genie) |
|---|---|---|
| AI Playground (on `EMBEDDED_CREDENTIALS` endpoint) | user OBO | **endpoint system SP** |
| `curl + PAT` → `/invocations` | user PAT | **endpoint system SP** |
| AppKit app → `/invocations` (app SP token) | app SP | **endpoint system SP** |
| AppKit app → `/invocations` (OBO forwarded) | user OBO | **endpoint system SP** |

For `agents.deploy()` endpoints the MCP identity is **ALWAYS** the endpoint system SP. The `resource_credential_strategy: EMBEDDED_CREDENTIALS` contract that `agents.deploy()` sets is **not user-settable** via any public API. Grant UC to that SP (Step 3 above).

**Playground is therefore NOT an OBO bypass** for MCP tool calls. A Playground greeting that succeeds only tells you the LLM endpoint is live — it does not tell you the system SP can read Genie's tables.

## Common failure modes

| Symptom | Likely cause | Fix |
|---|---|---|
| `PERMISSION_DENIED: ... not authorized to use this SQL Endpoint` | `users`-group `CAN_USE` inheritance missing on the warehouse | Grant the `users` GROUP (not the SP) once via Step 2. |
| `PERMISSION_DENIED: No access to table X` (no UUID in error) | UC grants missing on the endpoint SP, OR `serialized_space` was wiped | Run Step 5a probes in `SKILL.md` first. If space is healthy, apply Step 3 grants by SP UUID. |
| `200 OK` from `PATCH /permissions/...` but ACL listing shows no entry | You tried to grant a system SP via workspace Permissions API | Expected silent drop. Switch to UC `GRANT … TO \`<uuid>\`` or use `users`-group inheritance. |
| `GRANT ... MANAGE required` when running Step 3 | Caller lacks `MANAGE` on the securable | Ask the catalog/schema owner to run it. |
| Grants look correct but query still fails | Caching / stale tokens | Re-run `agents.deploy(...)` or wait ~1 minute for UC to propagate. |
| Playground works but AppKit app fails with `PERMISSION_DENIED` | **Impossible with `EMBEDDED_CREDENTIALS`** — both paths share the system SP. If you see this, Playground is actually failing too; check `curl + PAT` with a domain question. |
