# Model Serving Authentication Passthrough — Complete Reference

When an agent is **logged and served** on Databricks Model Serving, declare
resource dependencies at `mlflow.pyfunc.log_model()` time. Databricks provisions
a **system service principal** with short-lived, auto-rotated credentials for
the declared resources — no manual PAT management required.

Primary sources:

- [Authentication for AI agents (Model Serving)](https://docs.databricks.com/aws/en/generative-ai/agent-framework/agent-authentication-model-serving)
- [Log an agent for deployment](https://docs.databricks.com/aws/en/generative-ai/agent-framework/log-agent)
- [mlflow.pyfunc.log_model](https://mlflow.org/docs/latest/api_reference/python_api/mlflow.pyfunc.html#mlflow.pyfunc.log_model)

---

## How it works

```
Developer                        Model Serving
  │                                   │
  │ mlflow.pyfunc.log_model(          │
  │   resources=[...],                │
  │   auth_policy=AuthPolicy(...)     │
  │ )                                 │
  │ ─────────────────────────────────►│
  │                                   │
  │              Platform creates     │
  │              system SP with       │
  │              access to declared   │
  │              resources            │
  │                                   │
  │              SP credentials are   │
  │              auto-rotated and     │
  │              injected as env      │
  │              vars at runtime      │
  │                                   │
  │              WorkspaceClient()    │
  │              auto-discovers       │
  │              credentials          │
  │                                   │
```

**Key behaviors:**

- The endpoint **creator** must be able to access all logged resources.
- The system SP **may not appear** in normal SP listings.
- If the model version is removed from the endpoint, the system SP is deleted.
- Credentials are **M2M OAuth-style**, short-lived, auto-rotated.

---

## Resource type reference

### `DatabricksServingEndpoint`

Access to Model Serving endpoints (LLM calls, embeddings, etc.).

```python
from mlflow.models.resources import DatabricksServingEndpoint

DatabricksServingEndpoint(endpoint_name="my-llm-endpoint")
```

| Property | Value |
| --- | --- |
| Permission granted to SP | `CAN_QUERY` |
| Minimum MLflow version | `2.13.1` |
| Supports OBO (UserAuthPolicy) | Yes |
| Common use | LLM inference, embedding generation |

### `DatabricksVectorSearchIndex`

Access to Vector Search indexes for RAG retrieval.

```python
from mlflow.models.resources import DatabricksVectorSearchIndex

DatabricksVectorSearchIndex(index_name="catalog.schema.my_index")
```

| Property | Value |
| --- | --- |
| Permission granted to SP | `Can Select` |
| Minimum MLflow version | `2.13.1` |
| Supports OBO (UserAuthPolicy) | Yes |
| Common use | RAG document retrieval |

**Downstream dependency:** The SP also needs `SELECT` on the source table backing
the index, plus `USE CATALOG` / `USE SCHEMA` on parent objects.

### `DatabricksLakebase`

Access to Lakebase (managed PostgreSQL) for agent memory and state.

```python
from mlflow.models.resources import DatabricksLakebase

DatabricksLakebase(database_instance_name="my-lakebase-instance")
```

| Property | Value |
| --- | --- |
| Permission granted to SP | `Can Connect and Create` |
| Minimum MLflow version | `3.3.2` |
| Supports OBO (UserAuthPolicy) | No (system only) |
| Common use | Agent memory, session state, conversation history |

### `DatabricksSQLWarehouse`

Access to SQL warehouses for query execution.

```python
from mlflow.models.resources import DatabricksSQLWarehouse

DatabricksSQLWarehouse(warehouse_id="abc123def456")
```

| Property | Value |
| --- | --- |
| Permission granted to SP | `CAN USE` |
| Minimum MLflow version | `2.16.1` |
| Supports OBO (UserAuthPolicy) | Yes |
| Common use | SQL execution, Genie query backend |

### `DatabricksGenieSpace`

Access to Genie Spaces for natural language data querying.

```python
from mlflow.models.resources import DatabricksGenieSpace

DatabricksGenieSpace(genie_space_id="01ef1234567890ab")
```

| Property | Value |
| --- | --- |
| Permission granted to SP | `Can Run` |
| Minimum MLflow version | `2.17.1` |
| Supports OBO (UserAuthPolicy) | Yes |
| Common use | Natural language data queries |

**Downstream dependencies (CRITICAL):** Genie Spaces require access to:

- SQL warehouse (`DatabricksSQLWarehouse`)
- All underlying tables (`SELECT` + `USE SCHEMA` + `USE CATALOG`)
- UC functions used in the space (`EXECUTE`)

### `DatabricksUCConnection`

Access to Unity Catalog connections (external data sources).

```python
from mlflow.models.resources import DatabricksUCConnection

DatabricksUCConnection(connection_name="my_snowflake_conn")
```

| Property | Value |
| --- | --- |
| Permission granted to SP | `Use Connection` |
| Minimum MLflow version | `2.16.1` |
| Supports OBO (UserAuthPolicy) | Yes |
| Common use | Querying external databases via federation |

---

## Full `resources` parameter example

```python
import os
from mlflow.models.resources import (
    DatabricksServingEndpoint,
    DatabricksVectorSearchIndex,
    DatabricksLakebase,
    DatabricksSQLWarehouse,
    DatabricksGenieSpace,
    DatabricksUCConnection,
)

LLM_ENDPOINT = os.environ.get("LLM_ENDPOINT", "databricks-claude-sonnet-4-6")
WAREHOUSE_ID = os.environ.get("WAREHOUSE_ID", "")
LAKEBASE_INSTANCE = os.environ.get("LAKEBASE_INSTANCE", "")

GENIE_SPACES = {
    "cost": os.environ.get("COST_GENIE_SPACE_ID", ""),
    "security": os.environ.get("SECURITY_GENIE_SPACE_ID", ""),
    "performance": os.environ.get("PERFORMANCE_GENIE_SPACE_ID", ""),
}

def build_resources():
    """Build the complete resource list for log_model."""
    resources = []

    # LLM endpoint
    resources.append(DatabricksServingEndpoint(endpoint_name=LLM_ENDPOINT))

    # Vector Search (RAG)
    resources.append(DatabricksVectorSearchIndex(index_name="prod.docs.embeddings"))

    # Memory store
    if LAKEBASE_INSTANCE:
        resources.append(DatabricksLakebase(database_instance_name=LAKEBASE_INSTANCE))

    # SQL warehouse (for Genie and direct SQL)
    if WAREHOUSE_ID:
        resources.append(DatabricksSQLWarehouse(warehouse_id=WAREHOUSE_ID))

    # All Genie Spaces
    for domain, space_id in GENIE_SPACES.items():
        if space_id:
            resources.append(DatabricksGenieSpace(genie_space_id=space_id))

    # External connections
    resources.append(DatabricksUCConnection(connection_name="snowflake_prod"))

    return resources
```

---

## System SP lifecycle on Model Serving

### Creation

When you deploy a model version to an endpoint:

1. Databricks reads the `resources` list from the logged model.
2. A **system service principal** is created (or reused) for that model version.
3. The SP is granted permissions on each declared resource.
4. Credentials are injected as environment variables in the serving container.

### Runtime

- `WorkspaceClient()` with no arguments auto-discovers the injected credentials.
- Credentials are **M2M OAuth tokens**, not PATs.
- Tokens are **auto-rotated** — no manual renewal needed.
- The SP identity is used for **system-level** operations.

### Deletion

- When the model version is **removed** from the endpoint, the system SP is **deleted**.
- If you **redeploy** a different version, a new SP may be created.
- The old SP's permissions are revoked automatically.

### Visibility

- The system SP **may not appear** in the workspace admin console SP list.
- Use the serving endpoint's metadata to verify resource access.
- Audit logs show the system SP's actions with a synthetic identity.
- **`SHOW GRANTS \`<sp-uuid>\` ON SCHEMA …` is NOT a valid check** — it returns
  empty for system SPs (they're invisible to SCIM) even after a `GRANT …
  SUCCEEDED`. The SP also **rotates** across deploys, so a grant to an older
  UUID is dead. Verify access end-to-end (query the endpoint), not via
  `SHOW GRANTS`. Prefer OBO so no system-SP UC grant is needed at all.

---

## AuthPolicy for OBO on Model Serving

For agents that need **user-level access** (not just system SP), declare an
`AuthPolicy` with both system and user policies.

### AuthPolicy structure

```python
from mlflow.models.auth_policy import AuthPolicy, SystemAuthPolicy, UserAuthPolicy

def build_auth_policy():
    # System policy: resources for automatic passthrough (SP)
    system_resources = build_resources()  # from above
    system_policy = SystemAuthPolicy(resources=system_resources)

    # User policy: API scopes for OBO.
    # For the Managed MCP Genie path (McpServerToolkit, /api/2.0/mcp/genie/{id})
    # the scope is "mcp.genie" — "dashboards.genie" (the Conversation API scope)
    # returns 403 on the MCP endpoint. "sql" covers warehouse + statement exec.
    user_policy = UserAuthPolicy(api_scopes=[
        "mcp.genie",
        "sql",
    ])

    return AuthPolicy(
        system_auth_policy=system_policy,
        user_auth_policy=user_policy,
    )
```

### Logging with AuthPolicy

```python
import mlflow

mlflow.pyfunc.log_model(
    artifact_path="agent",
    python_model=agent,
    auth_policy=build_auth_policy(),
    pip_requirements=[
        "mlflow>=3.0.0",
        "databricks-sdk>=0.30.0",
        "databricks-ai-bridge>=0.1.0",
    ],
)
```

### When to use `resources` vs `auth_policy`

| Parameter | When to use |
| --- | --- |
| `resources=[...]` | System SP only; no OBO needed |
| `auth_policy=AuthPolicy(system_auth_policy=..., user_auth_policy=...)` | Both system SP and OBO needed |

**CRITICAL:** If you use `auth_policy`, do **not** also pass `resources` — they
conflict. Put all resources inside `SystemAuthPolicy.resources`.

### Runtime behavior with AuthPolicy

| Context | Auth mechanism | Client |
| --- | --- | --- |
| Evaluation / notebooks | `SystemAuthPolicy` → system SP with declared resources | `WorkspaceClient()` |
| Model Serving (system calls) | `SystemAuthPolicy` → system SP credentials | `WorkspaceClient()` |
| Model Serving (user calls) | `UserAuthPolicy` → OBO with declared scopes | `WorkspaceClient(credentials_strategy=ModelServingUserCredentials())` |

### Enabling OBO in serving endpoint config

When using `AuthPolicy` with `UserAuthPolicy`, you must also enable identity
passthrough in the serving endpoint:

```yaml
resources:
  model_serving_endpoints:
    my_agent:
      name: my-agent
      config:
        served_entities:
          - name: current
            entity_name: ${var.catalog}.${var.schema}.my_agent
            entity_version: "${var.agent_version}"
            workload_size: Small
            scale_to_zero_enabled: true
            environment_vars:
              DATABRICKS_USE_IDENTITY_PASSTHROUGH: "true"
```

---

## Version requirements summary

| Resource class | Minimum MLflow | OBO support |
| --- | --- | --- |
| `DatabricksServingEndpoint` | 2.13.1 | Yes |
| `DatabricksVectorSearchIndex` | 2.13.1 | Yes |
| `DatabricksSQLWarehouse` | 2.16.1 | Yes |
| `DatabricksUCConnection` | 2.16.1 | Yes |
| `DatabricksGenieSpace` | 2.17.1 | Yes |
| `DatabricksLakebase` | 3.3.2 | No |
| `AuthPolicy` | 3.0.0 | — |
| `ModelServingUserCredentials` | — | Requires `databricks-ai-bridge>=0.1.0` |

---

## Validation checklist

### Resources

- [ ] Every Databricks resource the agent calls is declared in `resources` or `SystemAuthPolicy.resources`
- [ ] All downstream dependencies are included (Genie → tables + warehouse + functions)
- [ ] MLflow version meets minimum for each resource type
- [ ] Endpoint creator has access to all declared resources

### AuthPolicy (if using OBO)

- [ ] `auth_policy` parameter used (not `resources` + `auth_policy` together)
- [ ] `SystemAuthPolicy.resources` includes all resources
- [ ] `UserAuthPolicy.api_scopes` includes only needed scopes
- [ ] `DATABRICKS_USE_IDENTITY_PASSTHROUGH: "true"` set in endpoint config
- [ ] `databricks-ai-bridge>=0.1.0` in pip_requirements
- [ ] Agent code detects environment and uses correct client

### Testing

- [ ] Evaluation with `mlflow.evaluate()` succeeds (system SP path)
- [ ] Model Serving deployment succeeds (no missing resource errors)
- [ ] End-user queries in serving use OBO identity (check audit logs)
- [ ] Genie queries succeed in both evaluation and serving contexts

---

## Common issues

| Symptom | Cause | Fix |
| --- | --- | --- |
| `PERMISSION_DENIED` in evaluation | Missing resource in `SystemAuthPolicy` | Add the resource to system resources list |
| `PERMISSION_DENIED` in serving (system) | Endpoint creator lacks resource access | Verify creator's permissions |
| `PERMISSION_DENIED` in serving (OBO) | Missing scope in `UserAuthPolicy` | Add the required API scope |
| Both `resources` and `auth_policy` passed | Parameter conflict | Use only `auth_policy`; put resources in `SystemAuthPolicy` |
| Genie fails but SQL works | Genie Space not declared as resource | Add `DatabricksGenieSpace` + `DatabricksSQLWarehouse` |
| `ImportError: DatabricksGenieSpace` | MLflow version too old | Upgrade to mlflow >= 2.17.1 |

---

## Related references

- `obo-authentication.md` — OBO patterns with environment detection and error handling
- `resource-permissions.md` — Full permission matrix for all resource types
- `app-authorization.md` — Service principal authentication on Databricks Apps
