# Post-Deploy Permissions — OBO-first, with a best-effort system-SP fallback

Loaded by `SKILL.md` Step 5 when you need the full reference for endpoint authentication — the OBO-vs-SP matrix, system-SP discovery, and UC grant realities. For the happy path, follow **Step 3** (dual `auth_policy`) and **Step 5** (OBO query gate) in `SKILL.md`; this doc is the deep dive.

## TL;DR — prefer OBO; the system SP is a fallback

Deploying with a dual `auth_policy` (`SystemAuthPolicy.resources` + `UserAuthPolicy(api_scopes=["mcp.genie","sql"])`) makes the endpoint `EMBEDDED_AND_USER_CREDENTIALS`. The Genie MCP call then runs **On-Behalf-Of the calling user**, so it respects that user's existing UC grants with **zero** post-deploy grants. This is the proven primary path.

The endpoint **system service principal (SP)** only matters as a fallback for true machine-to-machine callers that have no user token (an app's own SP token, a scheduled job). Granting that SP is **best-effort and unreliable** (see "The system-SP grant reality" below) — so design user-facing callers to forward OBO instead.

## What auth passthrough does (system SP)

`databricks.agents.deploy()` creates a system SP per endpoint. When you declare resources in `SystemAuthPolicy.resources` (or legacy `resources=[...]`), passthrough grants that SP:

- `CAN_QUERY` on the LLM serving endpoint (`DatabricksServingEndpoint`),
- `Can Run` on the Genie Space (`DatabricksGenieSpace`),
- `CAN USE` on the SQL warehouse (`DatabricksSQLWarehouse` — mandatory; the Genie Space runs its SQL there).

It does **not** automatically grant the SP Unity Catalog privileges (`USE CATALOG`, `USE SCHEMA`, `SELECT`, `EXECUTE`) on the gold tables/TVFs the Genie Space queries. That gap is the entire reason the SP fallback is fragile.

## Identities you can't see (and may not be able to grant to)

The endpoint system SP is an **invisible platform object**. It is:

- **NOT** in workspace SCIM → `databricks service-principals list` will not return it.
- **NOT verifiable** via `SHOW GRANTS \`<uuid>\` ON SCHEMA …` → that returns **empty** even after a `GRANT … SUCCEEDED`, because the SP is invisible to SCIM. Do not use `SHOW GRANTS` to confirm a system-SP grant.
- **Rotated** across deploys/config updates → a single endpoint can accumulate several distinct system SP UUIDs over time. Any grant targeting an older one is dead.
- **An implicit member** of the `users` group → workspace ACLs on warehouses and Genie Spaces are typically inherited.

This invisibility is the root cause of the most common debug dead ends. The next sections cover discovery and the grant reality.

## Step 1 — Find the SP UUID (via endpoint events, NOT SCIM)

`agents.deploy()` system SPs are not in SCIM, so `databricks service-principals list` will NOT return them. The first `PERMISSION_DENIED: No access to table X` error does NOT contain a UUID for this variant either. The reliable source is the endpoint's event stream.

### Python (via the Databricks SDK)

```python
from databricks.sdk import WorkspaceClient

def discover_endpoint_sps(w: WorkspaceClient, endpoint_name: str) -> list[str]:
    """Return ALL system SP UUIDs ever created for this endpoint (rotation-aware).

    Backticks are stripped to avoid malformed GRANT SQL.
    """
    resp = w.api_client.do(
        "GET",
        f"/api/2.0/serving-endpoints/{endpoint_name}/events",
        query={"limit": 200},
    )
    marker = "System service principal creation with ID "
    sps = [
        e["message"].split(marker, 1)[1].split(" ", 1)[0].strip().strip("`")
        for e in resp.get("events", [])
        if marker in e.get("message", "")
    ]
    return list(dict.fromkeys(sps))  # de-dup, preserve order

SPS = discover_endpoint_sps(WorkspaceClient(), "<your endpoint>")
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

## Step 3 — Best-effort UC grants to the system SP (the fallback reality)

This step is ONLY needed for the M2M fallback path (no user token). For user-facing callers, prefer OBO (Step 5) and skip this entirely.

Grant by UUID — NOT by `service_principal_name = <uuid>` (a workspace-ACL concept that doesn't apply to UC). Discover and grant **all** rotated SPs:

```python
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
for sp in discover_endpoint_sps(w, ENDPOINT_NAME):   # from Step 1
    for stmt in [
        f"GRANT USE CATALOG ON CATALOG `{CATALOG}` TO `{sp}`",
        f"GRANT USE SCHEMA, SELECT, EXECUTE ON SCHEMA `{CATALOG}`.`{GOLD_SCHEMA}` TO `{sp}`",
    ]:
        try:
            w.statement_execution.execute_statement(
                warehouse_id=WAREHOUSE_ID, statement=stmt, wait_timeout="30s"
            )
            print(f"best-effort OK: {stmt}")
        except Exception as e:   # never fail the deploy on the fallback path
            print(f"best-effort SKIP ({type(e).__name__}): {stmt}")
```

`EXECUTE` is required if your Genie Space exposes TVFs as certified answers — without it, TVF calls fail with the same `PERMISSION_DENIED: No access to table X` symptom as a missing `SELECT`.

### The system-SP grant reality (proven by probe)

- The `GRANT … SUCCEEDED` status does **not** prove the grant took: `SHOW GRANTS \`<uuid>\` ON SCHEMA …` returns **empty** for system SPs (they're invisible to SCIM). **`SHOW GRANTS` is not a valid verification** here.
- Because the only check we have (`SHOW GRANTS`) is blind, the SP path is **unverifiable from a notebook** — the only definitive proof is a true M2M call (an SP token with no user context) reaching `/invocations` and Genie returning data.
- Treat these grants as best-effort. Do **not** gate a deploy on them. The gate is the OBO query (Step 5).
- Run as a workspace admin or the catalog/schema owner (`MANAGE` required). If you lack `MANAGE`, ask the owner.

## Step 4 — Verify with the OBO query (the real gate)

A greeting does not exercise the MCP tool-calling path. Query the endpoint with a domain-specific data question via the SDK — the call is forwarded On-Behalf-Of you, exercising the OBO + Genie MCP path. No PAT, no `curl`, no `databricks auth token` (hard-blocked on Genie Code):

```python
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
r = w.serving_endpoints.query(
    name="<your endpoint>",
    inputs={"input": [{"role": "user", "content": "<domain-specific data question>"}]},
)
payload = r.as_dict() if hasattr(r, "as_dict") else r
out = payload.get("output", [])
assert any(o.get("type") == "function_call" for o in out), "no Genie tool call — greeting only"
assert any(o.get("type") == "message" for o in out), "no message with data"
```

PASS = at least one `function_call` followed by a `message` with real numbers. FAIL (greeting only) = the tool wasn't exercised; tighten the system prompt with a domain nudge or verify the Genie Space has content (Step 5a probes in `SKILL.md`).

> **IDE convenience:** a `curl + PAT` POST to `/invocations` works the same way (a PAT call is also forwarded OBO). Not available on Genie Code — use the SDK query.

## Who runs the MCP tool call? (OBO vs SP — corrected matrix)

For an endpoint deployed with a dual `auth_policy` (`EMBEDDED_AND_USER_CREDENTIALS`), the MCP tool runs as **whatever identity reaches `/invocations`**:

| Caller | Identity for `/invocations` | Identity for MCP tool (Genie) |
|---|---|---|
| AI Playground | user OBO | **user (OBO)** |
| SDK `serving_endpoints.query(...)` / `curl + PAT` | user OBO | **user (OBO)** |
| AppKit app → `/invocations` (OBO forwarded) | user OBO | **user (OBO)** |
| AppKit app → `/invocations` (app SP token only) | app SP | endpoint system SP (fallback) |
| Scheduled job / pure M2M (no user token) | system SP | endpoint system SP (fallback) |

So **Playground and SDK/PAT calls ARE an OBO path** — they run Genie as the calling user, not the system SP. The system SP is only used when no user token is forwarded. (A legacy `resources=`-only deploy — no `UserAuthPolicy` — yields `EMBEDDED_CREDENTIALS` and always uses the system SP; prefer the dual `auth_policy`.)

## Common failure modes

| Symptom | Likely cause | Fix |
|---|---|---|
| `PERMISSION_DENIED: No access to table X` on the OBO gate (no UUID) | YOUR own UC grants are missing on the space's tables (the query runs as you), OR `serialized_space` was wiped | Run Step 5a probes first. If the space is healthy, grant yourself `SELECT`/`EXECUTE` on the gold schema. |
| `PERMISSION_DENIED` only for a pure M2M caller (app SP token) | System SP lacks UC grants (best-effort Step 3 didn't take) | Prefer forwarding OBO from the app. If M2M is required, re-run Step 3 for all discovered SPs; accept it is unverifiable. |
| `403 Forbidden` from the MCP endpoint despite OBO wiring | Wrong scope — `dashboards.genie` is the Conversation API; the Managed MCP path needs `mcp.genie` | Set `UserAuthPolicy(api_scopes=["mcp.genie","sql"])` and redeploy. |
| `SHOW GRANTS \`<uuid>\`` returns empty after a `SUCCEEDED` grant | System SPs are invisible to SCIM | Expected — `SHOW GRANTS` is not a valid system-SP check. Verify via the OBO query (Step 4) instead. |
| `200 OK` from `PATCH /permissions/...` but ACL listing shows no entry | You tried to grant a system SP via workspace Permissions API | Expected silent drop. Use UC `GRANT … TO \`<uuid>\`` or `users`-group inheritance. |
| `GRANT ... MANAGE required` when running Step 3 | Caller lacks `MANAGE` on the securable | Ask the catalog/schema owner to run it. |
| OBO returns wrong/empty results for some users | Those users lack UC `SELECT` on the underlying tables | Correct behavior — OBO respects per-user grants. Grant the users (or a group) `SELECT`. |
