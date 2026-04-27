# Resource Grants and Deployment Configuration

Use this reference when **debugging permission issues** in `app.yaml`, bundle
`databricks.yml`, Unity Catalog, or Model Serving resource bundles.

---

## Two-Layer Permission Model

Agents need **two layers** of permissions to access Databricks resources:

1. **App/bundle resources** — attach workspace capabilities (warehouses,
   endpoints, connections) to the app or serving endpoint.
2. **UC GRANTs** — give the service principal (or OBO user) rights on
   catalogs, schemas, tables, functions, and connections.

Both layers are typically required for MCP-backed tools. Missing either layer
causes runtime permission errors.

---

## Grant Matrix

| Capability / Tool Path | Typical `app.yaml` / Bundle Resources | Unity Catalog (Direct on Objects) | Notes |
|---|---|---|---|
| SQL warehouse queries | `sql_warehouse` → `CAN_USE` | Optional table/schema grants | Warehouse must see tables the SQL uses |
| LLM / chat model | `serving_endpoint` → `CAN_QUERY` | — | Endpoint name must match agent `model` |
| Vector Search index | Vector Search serving endpoint if required | `USE CATALOG`, `USE SCHEMA`, `SELECT` on index (and source tables) | MCP needs UC visibility to backing objects |
| UC Functions MCP | Often same LLM endpoint resource | `USE CATALOG`, `USE SCHEMA`, `EXECUTE` on functions | SP is app identity unless using OBO |
| Databricks SQL MCP | `sql_warehouse` → `CAN_USE` | Grants on tables the generated SQL touches | System auto-selects warehouse if `_meta.warehouse_id` not set |
| External MCP (UC HTTP) | Connection + egress as per workspace | `USE CONNECTION` on the UC connection | Secrets referenced in connection options |
| Genie MCP | Genie / warehouse as per app template | Space + data access per Genie docs | Align with Genie governance model |
| Code interpreter (`python_exec`) | `uc_securable` with `EXECUTE` | `EXECUTE` on `system.ai.python_exec` | Use `uc_securable` resource type in `databricks.yml` |
| UC connections proxy (non-MCP) | Connection | `USE CONNECTION` on the UC connection | For direct REST API calls without MCP |

**Rule of thumb:** App/bundle **resources** attach workspace capabilities
(warehouses, endpoints, connections). **UC GRANTs** give the service principal
(or OBO user) rights on catalogs, schemas, tables, functions, and connections.

---

## `app.yaml` Resource Example

```yaml
resources:
  - name: sql-warehouse
    sql_warehouse:
      permission: CAN_USE

  - name: llm-endpoint
    serving_endpoint:
      name: "databricks-claude-sonnet-4-6"
      permission: CAN_QUERY

  - name: vector-search-endpoint
    serving_endpoint:
      name: "vector-search-endpoint"
      permission: CAN_QUERY

env:
  - name: WAREHOUSE_ID
    valueFrom: sql-warehouse
  - name: LLM_MODEL
    value: "databricks-claude-sonnet-4-6"
```

---

## `databricks.yml` (Bundle) Permissions Example

```yaml
resources:
  apps:
    my_agent_app:
      name: my-agent-app
      source_code_path: .
      resources:
        - name: sql-warehouse
          sql_warehouse:
            permission: CAN_USE
        - name: llm-endpoint
          serving_endpoint:
            name: "databricks-claude-sonnet-4-6"
            permission: CAN_QUERY
```

Mirror the same logical resources in both `app.yaml` and `databricks.yml` so
deployed apps get identical attachments.

---

## UC SQL Grants for MCP-Backed Resources

The app's **service principal** (or the principal your code uses) needs direct
access to underlying UC objects MCP servers expose.

### Vector Search MCP (`prod.docs` example)

```sql
GRANT USE CATALOG ON CATALOG prod TO `<app-sp>`;
GRANT USE SCHEMA ON SCHEMA prod.docs TO `<app-sp>`;
GRANT SELECT ON TABLE prod.docs.knowledge_index TO `<app-sp>`;
```

Vector Search may also need access to **source** tables feeding the index.

### UC Functions MCP (`prod.analytics` example)

```sql
GRANT USE CATALOG ON CATALOG prod TO `<app-sp>`;
GRANT USE SCHEMA ON SCHEMA prod.analytics TO `<app-sp>`;
GRANT EXECUTE ON FUNCTION prod.analytics.* TO `<app-sp>`;
```

### Databricks SQL MCP

The SQL MCP generates SQL dynamically. Grant the agent's identity access to
tables the generated SQL may touch:

```sql
GRANT USE CATALOG ON CATALOG prod TO `<app-sp>`;
GRANT USE SCHEMA ON SCHEMA prod.sales TO `<app-sp>`;
GRANT SELECT ON TABLE prod.sales.transactions TO `<app-sp>`;
GRANT SELECT ON TABLE prod.sales.customers TO `<app-sp>`;
```

If the agent writes data, also grant `INSERT`, `UPDATE`, or `MODIFY` as needed.

### Code Interpreter (`system.ai.python_exec`)

Grant via `databricks.yml` using the `uc_securable` resource type:

```yaml
resources:
  apps:
    my_agent_app:
      resources:
        - name: 'python_exec'
          uc_securable:
            securable_full_name: 'system.ai.python_exec'
            securable_type: 'FUNCTION'
            permission: 'EXECUTE'
```

### External MCP (UC HTTP Connection)

```sql
GRANT USE CONNECTION ON CONNECTION my_external_mcp TO `<app-sp>`;
```

### UC Connections Proxy (Non-MCP REST APIs)

Same grant as external MCP — the proxy uses the UC connection's credentials:

```sql
GRANT USE CONNECTION ON CONNECTION openai_connection TO `<app-sp>`;
```

Replace `` `<app-sp>` `` with your Databricks App / job service principal
identifier.

---

## MLflow Resources Declaration (Model Serving)

When logging an agent for **Model Serving**, declare resource dependencies so
serving can provision a system SP with the correct entitlements:

```python
from mlflow.models.resources import (
    DatabricksServingEndpoint,
    DatabricksVectorSearchIndex,
    DatabricksUCConnection,
    DatabricksFunction,
    DatabricksApp,
    DatabricksGenieSpace,
    DatabricksSQLWarehouse,
)

resources = [
    DatabricksServingEndpoint(endpoint_name="databricks-claude-sonnet-4-6"),
    DatabricksVectorSearchIndex(index_name="prod.docs.knowledge_index"),
    DatabricksUCConnection(connection_name="my_external_mcp"),
    DatabricksFunction("prod.analytics.enrich_customer"),
    DatabricksGenieSpace(genie_space_id="abc123"),
    DatabricksSQLWarehouse(warehouse_id="warehouse123"),
]
```

### Auto-Discovery with `get_databricks_resources()`

Instead of manually listing every resource, let `DatabricksMCPClient`
enumerate them:

```python
from databricks.sdk import WorkspaceClient
from databricks_mcp import DatabricksMCPClient
from mlflow.models.resources import DatabricksServingEndpoint

ws = WorkspaceClient()
host = ws.config.host

MANAGED_MCP_SERVER_URLS = [
    f"{host}/api/2.0/mcp/functions/system/ai",
    f"{host}/api/2.0/mcp/vector-search/prod/docs/knowledge_index",
]

resources = [
    DatabricksServingEndpoint(endpoint_name="databricks-claude-sonnet-4-6"),
]

for mcp_url in MANAGED_MCP_SERVER_URLS:
    mcp_client = DatabricksMCPClient(server_url=mcp_url, workspace_client=ws)
    resources.extend(mcp_client.get_databricks_resources())

mlflow.pyfunc.log_model(
    artifact_path="agent",
    python_model="agent.py",
    resources=resources,
)
```

This is the recommended approach — it eliminates manual resource maintenance
and reduces the risk of missing a dependency.

---

## DO / DON'T

### DO — Grant all downstream dependencies

```sql
GRANT USE CATALOG ON CATALOG prod TO `<sp>`;
GRANT USE SCHEMA ON SCHEMA prod.docs TO `<sp>`;
GRANT SELECT ON TABLE prod.docs.knowledge_index TO `<sp>`;
```

### DON'T — Assume MCP grants propagate without catalog/schema access

```sql
-- WRONG: Only index SELECT; SP cannot resolve catalog/schema path
GRANT SELECT ON TABLE prod.docs.knowledge_index TO `<sp>`;
-- Runtime: "permission denied for catalog prod"
```

### DO — Use `get_databricks_resources()` for Model Serving

```python
for url in MCP_SERVER_URLS:
    resources.extend(DatabricksMCPClient(server_url=url, workspace_client=ws).get_databricks_resources())
```

### DON'T — Log only top-level resources

```python
resources = [DatabricksServingEndpoint(endpoint_name="my-llm")]
# Missing Vector Search, Genie, Functions — serving access errors
```

---

## Common Permission Symptoms

| Symptom | Likely Fix |
|---------|------------|
| `PermissionDenied` on Vector Search | `USE` catalog/schema + `SELECT` on index (and source tables if needed) |
| Function MCP tools fail at runtime | `EXECUTE` on function(s) + `USE SCHEMA` / `USE CATALOG` |
| App cannot reach warehouse | `sql_warehouse` resource with `CAN_USE` + warehouse access to tables |
| External MCP via UC | `USE CONNECTION` + valid secret / token in connection options |
| SQL MCP "no warehouse" | Set `_meta.warehouse_id` or ensure SP can access at least one warehouse |
| Model Serving validation error | Log **every** Databricks resource the code touches in `resources=[...]` |

---

## References

- [Add resources to a Databricks app](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/resources)
- [Apps in bundles](https://docs.databricks.com/aws/en/dev-tools/bundles/resources#app)
- [Authentication for AI agents (Apps)](https://docs.databricks.com/aws/en/generative-ai/agent-framework/agent-authentication)
- [Authentication for AI agents (Model Serving)](https://docs.databricks.com/aws/en/generative-ai/agent-framework/agent-authentication-model-serving)
- [Log agent resources](https://docs.databricks.com/aws/en/generative-ai/agent-framework/log-agent#authentication-for-databricks-resources)
- [databricks-mcp on PyPI](https://pypi.org/project/databricks-mcp/)
