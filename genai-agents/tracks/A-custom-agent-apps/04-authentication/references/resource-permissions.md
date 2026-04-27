# Resource Permissions Matrix — Complete Reference

Comprehensive guide to every Databricks resource type an agent may need, the
minimum permission required, and how to grant it.

Primary sources:

- [Authentication for AI agents](https://docs.databricks.com/aws/en/generative-ai/agent-framework/agent-authentication)
- [Authentication for AI agents (Model Serving)](https://docs.databricks.com/aws/en/generative-ai/agent-framework/agent-authentication-model-serving)
- [Unity Catalog privileges](https://docs.databricks.com/aws/en/data-governance/unity-catalog/manage-privileges/)

---

## Master permission table

| Resource type | Minimum permission | Grant method | Notes |
| --- | --- | --- | --- |
| **MLflow experiment** | `Can Edit` | UI / CLI / SDK | Required for tracing; SP needs edit to write traces |
| **SQL warehouse** | `Can Use` | UI / CLI / SDK | Required for any SQL execution |
| **Model Serving endpoint** | `Can Query` | UI / CLI / SDK | LLM calls, embeddings |
| **Genie Space** | `Can Run` | UI / CLI / SDK | Natural language queries |
| **Vector Search index** | `Can Select` | UI / CLI / SDK | RAG retrieval |
| **Vector Search endpoint** | `Can Use` | UI / CLI / SDK | Compute for vector ops |
| **UC catalog** | `USE CATALOG` | SQL GRANT | Required to access any child schemas |
| **UC schema** | `USE SCHEMA` | SQL GRANT | Required to access any child objects |
| **UC table** | `SELECT` | SQL GRANT | Read data; add `INSERT`/`MODIFY` for write |
| **UC view** | `SELECT` | SQL GRANT | Read through view |
| **UC function** | `EXECUTE` | SQL GRANT | Call as tool |
| **UC volume** | `READ VOLUME` | SQL GRANT | Read files; `WRITE VOLUME` for write |
| **UC connection** | `USE CONNECTION` | SQL GRANT | External data source access |
| **UC model** | `EXECUTE` | SQL GRANT | Invoke registered model |
| **Prompt Registry (schema)** | `CREATE FUNCTION` + `EXECUTE` + `MANAGE` | SQL GRANT | Store and use prompts |
| **Lakebase instance** | `Can Connect and Create` | UI / CLI | Managed PostgreSQL |
| **Secret scope** | `Can Read` | CLI / SDK | Read secrets |
| **Workspace directory** | `Can Edit` | UI / CLI / SDK | File operations |
| **Dashboard** | `Can View` | UI / CLI / SDK | Read dashboard definitions |
| **Cluster** | `Can Attach To` | UI / CLI / SDK | Attach for compute (uncommon for agents) |

---

## Downstream dependency chains

### Genie Space dependencies

Genie Spaces are **composite resources**. Granting `Can Run` on the space is
necessary but **not sufficient**.

```
Genie Space (Can Run)
├── SQL Warehouse (Can Use)            ← executes generated SQL
├── UC Table 1 (SELECT)               ← queried by Genie
│   ├── UC Schema (USE SCHEMA)
│   └── UC Catalog (USE CATALOG)
├── UC Table 2 (SELECT)
│   ├── UC Schema (USE SCHEMA)
│   └── UC Catalog (USE CATALOG)
├── UC Function 1 (EXECUTE)           ← Genie-defined tools
│   └── UC Schema (USE SCHEMA)
└── UC Function 2 (EXECUTE)
    └── UC Schema (USE SCHEMA)
```

### Vector Search dependencies

```
Vector Search Index (Can Select)
├── Vector Search Endpoint (Can Use)   ← compute for queries
├── Source UC Table (SELECT)           ← index sync source
│   ├── UC Schema (USE SCHEMA)
│   └── UC Catalog (USE CATALOG)
└── Embedding Endpoint (Can Query)     ← if using auto-embedding
```

### UC Function (tool) dependencies

```
UC Function (EXECUTE)
├── UC Schema (USE SCHEMA)
├── UC Catalog (USE CATALOG)
└── (any resources the function body accesses)
    ├── UC Tables it reads (SELECT)
    ├── UC Tables it writes (INSERT/MODIFY)
    └── External connections (USE CONNECTION)
```

### MCP Server dependencies

```
MCP Server URL
├── Vector Search Index (Can Select)   ← if MCP provides retrieval
│   └── (Vector Search dependencies)
├── UC Functions (EXECUTE)             ← if MCP exposes tools
│   └── (Function dependencies)
└── UC Schema (USE SCHEMA)             ← schema namespace in MCP URL
```

---

## SQL GRANT statements for UC resources

### Catalog + schema access (always required)

```sql
-- Grant catalog traversal
GRANT USE CATALOG ON CATALOG my_catalog TO `<principal>`;

-- Grant schema traversal
GRANT USE SCHEMA ON SCHEMA my_catalog.my_schema TO `<principal>`;
```

### Table access

```sql
-- Read-only
GRANT SELECT ON TABLE my_catalog.my_schema.my_table TO `<principal>`;

-- Read-write
GRANT SELECT, INSERT, MODIFY ON TABLE my_catalog.my_schema.my_table TO `<principal>`;

-- All tables in schema (use carefully)
GRANT SELECT ON SCHEMA my_catalog.my_schema TO `<principal>`;
```

### Function access

```sql
-- Single function
GRANT EXECUTE ON FUNCTION my_catalog.my_schema.my_function TO `<principal>`;

-- All functions in schema
GRANT EXECUTE ON SCHEMA my_catalog.my_schema TO `<principal>`;
```

### Volume access

```sql
-- Read only
GRANT READ VOLUME ON VOLUME my_catalog.my_schema.my_volume TO `<principal>`;

-- Read and write
GRANT READ VOLUME, WRITE VOLUME ON VOLUME my_catalog.my_schema.my_volume TO `<principal>`;
```

### Connection access

```sql
GRANT USE CONNECTION ON CONNECTION my_connection TO `<principal>`;
```

### Model access

```sql
GRANT EXECUTE ON MODEL my_catalog.my_schema.my_model TO `<principal>`;
```

### Prompt Registry

```sql
-- Schema-level grants for Prompt Registry
GRANT CREATE FUNCTION ON SCHEMA my_catalog.prompts TO `<principal>`;
GRANT EXECUTE ON SCHEMA my_catalog.prompts TO `<principal>`;
```

### View current grants

```sql
-- Show grants on a specific object
SHOW GRANTS ON TABLE my_catalog.my_schema.my_table;

-- Show grants for a specific principal
SHOW GRANTS TO `<principal>`;

-- Show grants on schema
SHOW GRANTS ON SCHEMA my_catalog.my_schema;
```

### Revoke grants

```sql
-- Revoke specific permission
REVOKE SELECT ON TABLE my_catalog.my_schema.my_table FROM `<principal>`;

-- Revoke all on table
REVOKE ALL PRIVILEGES ON TABLE my_catalog.my_schema.my_table FROM `<principal>`;
```

---

## Databricks CLI commands for non-UC resources

### SQL warehouse permissions

```bash
# View current permissions
databricks permissions get sql/warehouses/<warehouse-id>

# Grant CAN USE
databricks permissions update sql/warehouses/<warehouse-id> \
  --json '{
    "access_control_list": [{
      "service_principal_name": "<sp-name>",
      "permission_level": "CAN_USE"
    }]
  }'
```

### Serving endpoint permissions

```bash
# View current permissions
databricks permissions get serving-endpoints/<endpoint-id>

# Grant CAN QUERY
databricks permissions update serving-endpoints/<endpoint-id> \
  --json '{
    "access_control_list": [{
      "service_principal_name": "<sp-name>",
      "permission_level": "CAN_QUERY"
    }]
  }'
```

### MLflow experiment permissions

```bash
# View current permissions
databricks permissions get mlflow-experiments/<experiment-id>

# Grant CAN EDIT
databricks permissions update mlflow-experiments/<experiment-id> \
  --json '{
    "access_control_list": [{
      "service_principal_name": "<sp-name>",
      "permission_level": "CAN_EDIT"
    }]
  }'
```

### Genie Space permissions

```bash
# Genie Space permissions are managed via the dashboards/genie API
databricks permissions update dashboards/<genie-space-id> \
  --json '{
    "access_control_list": [{
      "service_principal_name": "<sp-name>",
      "permission_level": "CAN_RUN"
    }]
  }'
```

### Secret scope permissions

```bash
# Grant READ on secret scope
databricks secrets put-acl <scope-name> <sp-name> READ
```

---

## Databricks SDK permission management

```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.iam import (
    AccessControlRequest,
    PermissionLevel,
)

w = WorkspaceClient()

# ──── SQL Warehouse ────
w.warehouses.set_permissions(
    warehouse_id="abc123",
    access_control_list=[
        AccessControlRequest(
            service_principal_name="app-my-agent",
            permission_level=PermissionLevel.CAN_USE,
        )
    ],
)

# ──── Serving Endpoint ────
w.serving_endpoints.set_permissions(
    serving_endpoint_id="def456",
    access_control_list=[
        AccessControlRequest(
            service_principal_name="app-my-agent",
            permission_level=PermissionLevel.CAN_QUERY,
        )
    ],
)

# ──── MLflow Experiment ────
w.experiments.set_permissions(
    experiment_id="789",
    access_control_list=[
        AccessControlRequest(
            service_principal_name="app-my-agent",
            permission_level=PermissionLevel.CAN_EDIT,
        )
    ],
)
```

---

## Permission denied debugging flowchart

When you see a `PERMISSION_DENIED` error, follow this diagnostic flow:

```
PERMISSION_DENIED error
│
├─ What resource failed?
│  │
│  ├─ UC resource (table, function, volume, connection)?
│  │  │
│  │  ├─ 1. Check USE CATALOG on parent catalog
│  │  │     SHOW GRANTS ON CATALOG <catalog>;
│  │  │
│  │  ├─ 2. Check USE SCHEMA on parent schema
│  │  │     SHOW GRANTS ON SCHEMA <catalog>.<schema>;
│  │  │
│  │  ├─ 3. Check object-level grant
│  │  │     SHOW GRANTS ON TABLE/FUNCTION/VOLUME <fqn>;
│  │  │
│  │  └─ 4. Check principal identity
│  │        SELECT current_user();  -- who am I?
│  │        -- SP app-id or user email
│  │
│  ├─ Genie Space?
│  │  │
│  │  ├─ 1. Check Can Run on the Genie Space
│  │  ├─ 2. Check Can Use on the SQL Warehouse
│  │  ├─ 3. Check SELECT on ALL underlying tables
│  │  ├─ 4. Check EXECUTE on ALL UC functions in the space
│  │  └─ 5. Check USE CATALOG + USE SCHEMA on parent objects
│  │
│  ├─ SQL Warehouse?
│  │  │
│  │  └─ Check CAN USE permission
│  │     databricks permissions get sql/warehouses/<id>
│  │
│  ├─ Serving Endpoint?
│  │  │
│  │  └─ Check CAN QUERY permission
│  │     databricks permissions get serving-endpoints/<id>
│  │
│  └─ MLflow Experiment?
│     │
│     └─ Check CAN EDIT permission
│        databricks permissions get mlflow-experiments/<id>
│
├─ Which auth mode?
│  │
│  ├─ App auth (SP)?
│  │  └─ Verify SP has grants (find SP app-id, check grants)
│  │
│  ├─ OBO (user)?
│  │  ├─ Verify scopes include the needed API
│  │  └─ Verify user has direct access to the resource
│  │
│  └─ Model Serving passthrough?
│     ├─ Verify resource declared in resources/SystemAuthPolicy
│     ├─ Verify downstream dependencies declared
│     └─ Verify endpoint creator has resource access
│
└─ Environment?
   │
   ├─ Evaluation/notebook?
   │  └─ Check SystemAuthPolicy.resources includes the resource
   │
   ├─ Model Serving?
   │  ├─ System call? → check SystemAuthPolicy.resources
   │  └─ User call? → check UserAuthPolicy.api_scopes
   │
   └─ Databricks Apps?
      ├─ App auth? → check SP grants
      └─ OBO? → check scopes + user permissions
```

---

## Quick diagnostic commands

```bash
# Who am I? (in notebook/job)
databricks current-user me

# What permissions does an SP have on a warehouse?
databricks permissions get sql/warehouses/<warehouse-id> | \
  jq '.access_control_list[] | select(.service_principal_name)'

# List all grants for a UC principal
databricks sql execute --warehouse-id <wh-id> \
  --statement "SHOW GRANTS TO \`<sp-application-id>\`"

# List all grants on a table
databricks sql execute --warehouse-id <wh-id> \
  --statement "SHOW GRANTS ON TABLE catalog.schema.table"

# Check if SP exists
databricks service-principals list --output json | \
  jq '.[] | select(.display_name | contains("my-app"))'
```

---

## Common permission patterns by agent type

### RAG agent

```
Serving endpoint (LLM)    → CAN QUERY
Vector Search index        → Can Select
Vector Search endpoint     → Can Use
UC source table            → SELECT + USE SCHEMA + USE CATALOG
MLflow experiment          → CAN EDIT
```

### SQL analytics agent

```
SQL warehouse              → CAN USE
UC tables (multiple)       → SELECT + USE SCHEMA + USE CATALOG
Serving endpoint (LLM)     → CAN QUERY
MLflow experiment          → CAN EDIT
```

### Genie-based agent

```
Genie Space                → CAN RUN
SQL warehouse              → CAN USE
UC tables (all in space)   → SELECT + USE SCHEMA + USE CATALOG
UC functions (in space)    → EXECUTE + USE SCHEMA
Serving endpoint (LLM)     → CAN QUERY
MLflow experiment          → CAN EDIT
```

### Tool-calling agent

```
Serving endpoint (LLM)     → CAN QUERY
UC functions (tools)        → EXECUTE + USE SCHEMA + USE CATALOG
UC tables (read by tools)   → SELECT + USE SCHEMA + USE CATALOG
UC tables (write by tools)  → INSERT/MODIFY + USE SCHEMA + USE CATALOG
UC volumes (file tools)     → READ/WRITE VOLUME
MLflow experiment           → CAN EDIT
```

---

## Related references

- `app-authorization.md` — Full SP permission granting flow
- `user-authorization.md` — OBO scopes and per-user permissions
- `model-serving-auth-passthrough.md` — MLflow resource declarations and AuthPolicy
- `obo-authentication.md` — Environment detection and auth error handling
