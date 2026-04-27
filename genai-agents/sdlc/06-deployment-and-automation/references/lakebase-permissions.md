# Lakebase Permissions for Deployed Apps

Complete Postgres-level permission grants required for a Databricks App
service principal to access Lakebase tables. Covers provisioned and
autoscaling Lakebase, all table families (checkpoint, store, app, Drizzle,
public), and a ready-to-run SQL script.

Grounded in:
- [app-templates GRANT patterns](https://github.com/databricks/app-templates)
- `deploy.sh` in this repo

---

## 1. Why Explicit Grants Are Required

Databricks Apps use a **service principal** (SP) for all resource access.
Unlike interactive users, the SP does **not** inherit Unity Catalog table ACLs
when connecting to Lakebase via raw Postgres. You must issue explicit
Postgres `GRANT` statements for every schema and table the app reads or writes.

Without these grants, the app will encounter:
```
ERROR:  permission denied for schema app
ERROR:  permission denied for table checkpoints
```

---

## 2. Provisioned Lakebase Grants

### 2.1 Identify the SP Role

The app's SP maps to a Postgres role. Resolve it from the app metadata:

```bash
SP_CLIENT_ID=$(databricks apps get "$APP_NAME" -o json \
  | python3 -c "import sys,json; d=json.load(sys.stdin); \
     print(d.get('service_principal_client_id',''))")
echo "SP role: $SP_CLIENT_ID"
```

In Lakebase, the SP is typically referenced by its client ID or mapped
username. Check your Lakebase instance for the exact role name.

### 2.2 Schema-Level Grants

```sql
-- Grant access to all schemas the app needs
GRANT USAGE ON SCHEMA app TO "<sp_role>";
GRANT USAGE ON SCHEMA drizzle TO "<sp_role>";
GRANT USAGE ON SCHEMA public TO "<sp_role>";
```

### 2.3 App Schema Tables

The `app` schema contains application-specific tables (sessions, state,
conversation history):

```sql
-- Full CRUD on all existing app tables
GRANT SELECT, INSERT, UPDATE, DELETE
  ON ALL TABLES IN SCHEMA app
  TO "<sp_role>";

-- Auto-grant on future tables created in this schema
ALTER DEFAULT PRIVILEGES IN SCHEMA app
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES
  TO "<sp_role>";
```

### 2.4 Checkpoint Tables

Checkpoint tables store agent state, memory, and conversation checkpoints:

```sql
-- Checkpoint tables (typically in app schema)
GRANT SELECT, INSERT, UPDATE, DELETE
  ON TABLE app.checkpoints TO "<sp_role>";
GRANT SELECT, INSERT, UPDATE, DELETE
  ON TABLE app.checkpoint_blobs TO "<sp_role>";
GRANT SELECT, INSERT, UPDATE, DELETE
  ON TABLE app.checkpoint_writes TO "<sp_role>";
```

### 2.5 Store Tables

Store tables hold persistent key-value data for the agent:

```sql
-- Store tables (if using LangGraph-style stores)
GRANT SELECT, INSERT, UPDATE, DELETE
  ON TABLE app.store TO "<sp_role>";
```

### 2.6 Drizzle Schema

If using Drizzle ORM for schema management:

```sql
-- Drizzle migration tracking
GRANT USAGE ON SCHEMA drizzle TO "<sp_role>";
GRANT SELECT, INSERT, UPDATE, DELETE
  ON ALL TABLES IN SCHEMA drizzle
  TO "<sp_role>";

ALTER DEFAULT PRIVILEGES IN SCHEMA drizzle
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES
  TO "<sp_role>";
```

### 2.7 Public Schema

The `public` schema may contain shared tables or views:

```sql
-- Public schema access
GRANT USAGE ON SCHEMA public TO "<sp_role>";
GRANT SELECT, INSERT, UPDATE, DELETE
  ON ALL TABLES IN SCHEMA public
  TO "<sp_role>";

ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES
  TO "<sp_role>";
```

### 2.8 Sequence Grants

If tables use auto-increment columns (serial/identity):

```sql
-- Sequence access for auto-increment columns
GRANT USAGE ON ALL SEQUENCES IN SCHEMA app TO "<sp_role>";
GRANT USAGE ON ALL SEQUENCES IN SCHEMA drizzle TO "<sp_role>";
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO "<sp_role>";

ALTER DEFAULT PRIVILEGES IN SCHEMA app
  GRANT USAGE ON SEQUENCES TO "<sp_role>";
ALTER DEFAULT PRIVILEGES IN SCHEMA drizzle
  GRANT USAGE ON SEQUENCES TO "<sp_role>";
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT USAGE ON SEQUENCES TO "<sp_role>";
```

---

## 3. Complete Grant Script (Provisioned)

Replace `<sp_role>` with your app's SP client ID or mapped Postgres role.

```sql
-- =============================================================
-- Lakebase Grants for Databricks App Service Principal
-- Run this against the Lakebase Postgres endpoint
-- =============================================================

-- Schema-level access
GRANT USAGE ON SCHEMA app TO "<sp_role>";
GRANT USAGE ON SCHEMA drizzle TO "<sp_role>";
GRANT USAGE ON SCHEMA public TO "<sp_role>";

-- App schema: full CRUD on all tables
GRANT SELECT, INSERT, UPDATE, DELETE
  ON ALL TABLES IN SCHEMA app TO "<sp_role>";
ALTER DEFAULT PRIVILEGES IN SCHEMA app
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "<sp_role>";

-- Drizzle schema: migration tracking
GRANT SELECT, INSERT, UPDATE, DELETE
  ON ALL TABLES IN SCHEMA drizzle TO "<sp_role>";
ALTER DEFAULT PRIVILEGES IN SCHEMA drizzle
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "<sp_role>";

-- Public schema: shared tables
GRANT SELECT, INSERT, UPDATE, DELETE
  ON ALL TABLES IN SCHEMA public TO "<sp_role>";
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "<sp_role>";

-- Sequences (for auto-increment columns)
GRANT USAGE ON ALL SEQUENCES IN SCHEMA app TO "<sp_role>";
GRANT USAGE ON ALL SEQUENCES IN SCHEMA drizzle TO "<sp_role>";
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO "<sp_role>";
ALTER DEFAULT PRIVILEGES IN SCHEMA app
  GRANT USAGE ON SEQUENCES TO "<sp_role>";
ALTER DEFAULT PRIVILEGES IN SCHEMA drizzle
  GRANT USAGE ON SEQUENCES TO "<sp_role>";
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT USAGE ON SEQUENCES TO "<sp_role>";
```

---

## 4. Autoscaling Lakebase

Autoscaling Lakebase has additional considerations:

### 4.1 Attaching Lakebase to an App (Post-Deploy)

Lakebase autoscaling instances are **not yet expressible** as bundle resources
in `databricks.yml`. After `databricks bundle deploy`, attach Lakebase to the
app via the CLI or REST API:

**Option A: CLI (recommended)**

```bash
# Attach Lakebase as an app resource after bundle deploy
APP_NAME="my-agent-app"
LAKEBASE_INSTANCE="my-lakebase-instance"

databricks apps update "$APP_NAME" --json "{
  \"resources\": [
    {\"name\": \"lakebase\", \"lakebase\": {
      \"instance_name\": \"$LAKEBASE_INSTANCE\",
      \"permission\": \"CAN_USE\"
    }}
  ]
}"
```

**Option B: REST API**

```bash
curl -X PATCH "https://$DATABRICKS_HOST/api/2.0/apps/$APP_NAME" \
  -H "Authorization: Bearer $DATABRICKS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "resources": [
      {"name": "lakebase", "lakebase": {
        "instance_name": "my-lakebase-instance",
        "permission": "CAN_USE"
      }}
    ]
  }'
```

**Option C: Python SDK**

```python
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
w.apps.update(
    name="my-agent-app",
    resources=[{
        "name": "lakebase",
        "lakebase": {
            "instance_name": "my-lakebase-instance",
            "permission": "CAN_USE",
        },
    }],
)
```

**Automation tip:** Add the Lakebase attachment as a post-deploy step in your
CI/CD pipeline or `deploy.sh` wrapper, immediately after `databricks bundle deploy`.

### 4.2 Connection Configuration

For autoscaling Lakebase, the app needs connection details as env vars:

```yaml
# app.yaml
env:
  - name: LAKEBASE_HOST
    value: "your-lakebase-host.cloud.databricks.com"
  - name: LAKEBASE_PORT
    value: "443"
  - name: LAKEBASE_DATABASE
    value: "my_database"
  - name: LAKEBASE_INSTANCE_NAME
    value: "my-lakebase-instance"
```

### 4.3 Credential Generation

The app generates Lakebase credentials at runtime using the Databricks SDK:

```python
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
creds = w.api_client.do(
    "POST",
    "/api/2.0/database/credentials",
    body={"instance_name": os.environ["LAKEBASE_INSTANCE_NAME"]},
)
```

---

## 5. Verifying Grants

### 5.1 Test from the App's Perspective

Connect as the SP role and verify access:

```sql
-- Check schema access
SELECT schema_name FROM information_schema.schemata;

-- Check table access
SELECT table_schema, table_name, privilege_type
FROM information_schema.table_privileges
WHERE grantee = '<sp_role>';

-- Test a read
SELECT COUNT(*) FROM app.checkpoints;

-- Test a write
INSERT INTO app.checkpoints (thread_id, checkpoint_id, data)
VALUES ('test', 'test', '{}');
DELETE FROM app.checkpoints WHERE thread_id = 'test';
```

### 5.2 Common Permission Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `permission denied for schema app` | Missing `GRANT USAGE ON SCHEMA` | Run schema grant |
| `permission denied for table checkpoints` | Missing table-level grant | Run table grant |
| `permission denied for sequence` | Auto-increment without sequence grant | Run sequence grant |
| `relation "app.checkpoints" does not exist` | Table not created yet | Run schema migration first |

---

## References

- [app-templates (GitHub)](https://github.com/databricks/app-templates) — GRANT patterns
- [Lakebase documentation](https://docs.databricks.com/aws/en/database/) — provisioned and autoscaling
- [`apps-deployment-patterns.md`](apps-deployment-patterns.md) — deployment workflow
