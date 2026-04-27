# App Authorization (Service Principal) — Complete Reference

App authorization is the **default** authentication mode for Databricks Apps. Databricks
automatically creates a service principal (SP) when you create an app. Every user of
the app shares the same SP identity and therefore the same permissions.

Primary sources:

- [Authentication for AI agents](https://docs.databricks.com/aws/en/generative-ai/agent-framework/agent-authentication)
- [App authorization deep dive](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/auth#app-authorization)
- [Add resources to a Databricks app](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/resources)

---

## How it works

1. You create a Databricks App (UI, CLI, or bundle).
2. Databricks **auto-provisions** a workspace-level service principal tied to that app.
3. Code running inside the app authenticates as the SP via **default credential chain**
   (`WorkspaceClient()` with no explicit config).
4. You grant the SP access to the resources the agent needs.

---

## Granting permissions via UI

### Databricks Apps UI (fastest path)

1. Navigate to **Compute → Apps** in the workspace.
2. Click the app name → **Edit app** → **Configure** tab.
3. Under **Resources**, click **Add resource**.
4. Select the resource type (SQL warehouse, Genie space, serving endpoint, etc.).
5. Choose the specific resource and the permission level.
6. Click **Save**. The SP is automatically granted the permission.

### Workspace admin console

1. Navigate to **Admin Settings → Service Principals**.
2. Find the SP named after your app (e.g., `app-my-agent`).
3. Open the SP detail page.
4. Under **Permissions**, add workspace-level entitlements.
5. For UC resources, use SQL GRANT statements instead (see below).

---

## Granting permissions via CLI

### Using Databricks CLI

```bash
# List service principals to find the app SP
databricks service-principals list --output json | \
  jq '.[] | select(.display_name | contains("my-app-name"))'

# Grant SP access to a SQL warehouse
databricks permissions update sql/warehouses/<warehouse-id> \
  --json '{
    "access_control_list": [{
      "service_principal_name": "app-my-agent",
      "permission_level": "CAN_USE"
    }]
  }'

# Grant SP access to a serving endpoint
databricks permissions update serving-endpoints/<endpoint-id> \
  --json '{
    "access_control_list": [{
      "service_principal_name": "app-my-agent",
      "permission_level": "CAN_QUERY"
    }]
  }'

# Grant SP access to an MLflow experiment
databricks permissions update mlflow-experiments/<experiment-id> \
  --json '{
    "access_control_list": [{
      "service_principal_name": "app-my-agent",
      "permission_level": "CAN_EDIT"
    }]
  }'
```

### Using SQL for Unity Catalog resources

```sql
-- Get the SP application_id first (from CLI output above)
-- Grant catalog access
GRANT USE CATALOG ON CATALOG my_catalog TO `<sp-application-id>`;

-- Grant schema access
GRANT USE SCHEMA ON SCHEMA my_catalog.my_schema TO `<sp-application-id>`;

-- Grant table SELECT
GRANT SELECT ON TABLE my_catalog.my_schema.my_table TO `<sp-application-id>`;

-- Grant function execution
GRANT EXECUTE ON FUNCTION my_catalog.my_schema.my_function TO `<sp-application-id>`;

-- Grant volume read
GRANT READ VOLUME ON VOLUME my_catalog.my_schema.my_volume TO `<sp-application-id>`;

-- Prompt Registry: grant CREATE FUNCTION + EXECUTE + MANAGE on schema
GRANT CREATE FUNCTION ON SCHEMA my_catalog.my_schema TO `<sp-application-id>`;
GRANT EXECUTE ON SCHEMA my_catalog.my_schema TO `<sp-application-id>`;
```

---

## `databricks.yml` resource declarations

Declare resources in the bundle so permissions are **applied automatically** on deploy:

```yaml
# databricks.yml
bundle:
  name: my-agent

resources:
  apps:
    my_agent:
      name: my-agent
      description: "Health monitoring agent"
      source_code_path: ../src/my_agent

      resources:
        # SQL Warehouse — CAN USE granted automatically
        - name: sql-warehouse
          description: "SQL warehouse for queries"
          sql_warehouse:
            id: ${var.warehouse_id}
            permission: CAN_USE

        # Serving endpoint — CAN QUERY granted automatically
        - name: llm-endpoint
          description: "LLM serving endpoint"
          serving_endpoint:
            name: ${var.llm_endpoint_name}
            permission: CAN_QUERY

        # MLflow experiment — CAN EDIT granted automatically
        - name: mlflow-experiment
          description: "Tracing experiment"
          mlflow_experiment:
            path: /Shared/experiments/${bundle.target}/my-agent
            permission: CAN_EDIT

        # Genie Space — CAN RUN granted automatically
        - name: genie-space
          description: "Cost analysis Genie space"
          genie_space:
            id: ${var.genie_space_id}
            permission: CAN_RUN

        # Secret scope — CAN READ granted automatically
        - name: secrets
          description: "API keys"
          secret_scope:
            name: my-agent-secrets
            permission: CAN_READ

      # Environment variables injected at runtime
      config:
        command:
          - python
          - -m
          - uvicorn
          - main:app
          - --host=0.0.0.0
          - --port=8000
        env:
          - name: SQL_WAREHOUSE_ID
            value_from:
              resources:
                - sql-warehouse

          - name: LLM_ENDPOINT_NAME
            value_from:
              resources:
                - llm-endpoint
```

---

## SP permission management via Databricks SDK

```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.iam import (
    AccessControlRequest,
    PermissionLevel,
)

w = WorkspaceClient()

# ──────────────────────────────────────────────
# 1. Find the app service principal
# ──────────────────────────────────────────────
sp = None
for s in w.service_principals.list(filter=f'displayName co "my-agent"'):
    sp = s
    break

assert sp, "Service principal not found"
print(f"SP: {sp.display_name} (id={sp.id}, app_id={sp.application_id})")

# ──────────────────────────────────────────────
# 2. Grant SQL warehouse access
# ──────────────────────────────────────────────
w.warehouses.set_permissions(
    warehouse_id="abc123",
    access_control_list=[
        AccessControlRequest(
            service_principal_name=sp.display_name,
            permission_level=PermissionLevel.CAN_USE,
        )
    ],
)

# ──────────────────────────────────────────────
# 3. Grant serving endpoint access
# ──────────────────────────────────────────────
w.serving_endpoints.set_permissions(
    serving_endpoint_id="def456",
    access_control_list=[
        AccessControlRequest(
            service_principal_name=sp.display_name,
            permission_level=PermissionLevel.CAN_QUERY,
        )
    ],
)

# ──────────────────────────────────────────────
# 4. Grant MLflow experiment access
# ──────────────────────────────────────────────
w.experiments.set_permissions(
    experiment_id="789",
    access_control_list=[
        AccessControlRequest(
            service_principal_name=sp.display_name,
            permission_level=PermissionLevel.CAN_EDIT,
        )
    ],
)

# ──────────────────────────────────────────────
# 5. Grant UC resources via SQL (SDK statement execution)
# ──────────────────────────────────────────────
grants = [
    f"GRANT USE CATALOG ON CATALOG main TO `{sp.application_id}`",
    f"GRANT USE SCHEMA ON SCHEMA main.default TO `{sp.application_id}`",
    f"GRANT SELECT ON TABLE main.default.metrics TO `{sp.application_id}`",
]
for sql in grants:
    w.statement_execution.execute_statement(
        warehouse_id="abc123",
        statement=sql,
    )
```

---

## Principle of least privilege patterns

### Pattern 1: Read-only analytics agent

Grant only what the agent reads; never grant MODIFY/WRITE.

```
SP permissions:
  SQL Warehouse     → CAN USE
  Serving endpoint  → CAN QUERY
  MLflow experiment → CAN EDIT  (traces only, not models)
  UC tables         → SELECT only (no INSERT/UPDATE)
  Genie space       → CAN RUN
```

### Pattern 2: Agent with write-back

When the agent writes results (summaries, alerts, recommendations):

```
SP permissions:
  (all read-only grants above)  +
  UC target table   → SELECT, INSERT, MODIFY
  UC volume         → READ and WRITE  (for file outputs)
```

### Pattern 3: Tool-calling agent

When the agent calls UC functions as tools:

```
SP permissions:
  (base grants)  +
  UC functions    → EXECUTE on each function
  UC schema       → USE SCHEMA on the schema containing functions
```

### Pattern 4: Multi-schema agent

For agents spanning multiple catalogs/schemas, grant at the **narrowest** scope:

```sql
-- BAD: too broad
GRANT USE CATALOG ON CATALOG main TO `<sp-app-id>`;
GRANT SELECT ON CATALOG main TO `<sp-app-id>`;

-- GOOD: specific schemas and tables
GRANT USE CATALOG ON CATALOG main TO `<sp-app-id>`;
GRANT USE SCHEMA ON SCHEMA main.billing TO `<sp-app-id>`;
GRANT SELECT ON TABLE main.billing.usage TO `<sp-app-id>`;
GRANT USE SCHEMA ON SCHEMA main.security TO `<sp-app-id>`;
GRANT SELECT ON TABLE main.security.audit_logs TO `<sp-app-id>`;
```

---

## Permission audit and rotation

### Auditing current permissions

```python
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

sp_name = "app-my-agent"

# Audit warehouse permissions
perms = w.warehouses.get_permissions(warehouse_id="abc123")
for acl in perms.access_control_list:
    for p in (acl.all_permissions or []):
        print(f"  {acl.service_principal_name or acl.user_name}: {p.permission_level}")

# Audit UC grants (via SQL)
result = w.statement_execution.execute_statement(
    warehouse_id="abc123",
    statement=f"SHOW GRANTS ON TABLE main.default.metrics",
)
for row in result.result.data_array:
    print(row)
```

### SP credential rotation

Databricks Apps automatically manage SP credentials—you do not need to rotate
PATs or OAuth secrets manually. If you need to force rotation (e.g., after a
security incident):

1. Delete the app and recreate it (new SP, new credentials).
2. Or use the Admin API to reset SP credentials:

```python
# Reset SP OAuth secret (forces new credentials)
w.service_principals.update(
    id=sp.id,
    active=True,  # re-activate if suspended
)
```

### Periodic review checklist

- [ ] Review SP permissions quarterly
- [ ] Remove unused resource grants
- [ ] Verify no `ALL PRIVILEGES` or `MANAGE` grants exist unless justified
- [ ] Check that SP is not a workspace admin (it shouldn't be)
- [ ] Confirm `databricks.yml` resource declarations match actual grants
- [ ] Test with a non-admin user to verify agent works with minimum privileges

---

## Common issues

| Symptom | Cause | Fix |
| --- | --- | --- |
| `PERMISSION_DENIED` on table query | Missing UC GRANT | Add `SELECT` + `USE SCHEMA` + `USE CATALOG` |
| Agent can't create MLflow traces | SP lacks experiment permission | Grant `CAN EDIT` on the MLflow experiment |
| Genie queries fail with "Can View" error | SP lacks Genie + downstream grants | Grant `CAN RUN` on space + `SELECT` on tables + `CAN USE` on warehouse |
| `WorkspaceClient()` returns wrong identity | Code running outside app context | Verify `DATABRICKS_APP_NAME` env var is set |
| Bundle deploy doesn't apply permissions | Resource not declared in `databricks.yml` | Add resource block under `resources:` in app definition |

---

## Related references

- `user-authorization.md` — OBO authentication for per-user access
- `resource-permissions.md` — Full permission matrix for all resource types
- `model-serving-auth-passthrough.md` — Automatic passthrough on Model Serving
