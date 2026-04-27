# Apps Deployment Patterns

Complete deployment reference for Databricks Apps hosting MLflow AgentServer
agents. Covers bundle-based deployment, file-sync deployment, resource
configuration, MLflow experiment setup, Lakebase integration, and service
principal management.

Grounded in:
- [Author an agent](https://docs.databricks.com/aws/en/generative-ai/agent-framework/author-agent)
- [Deploy a Databricks app](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/deploy)
- [app-templates](https://github.com/databricks/app-templates)
- `deploy.sh` in this repo

---

## 1. Deployment Methods Overview

There are two primary deployment paths for Databricks Apps:

| Method | Best For | Workflow |
|--------|----------|----------|
| **Bundle deploy + run** | Promoted builds, CI/CD, multi-resource orchestration | `bundle validate` → `bundle deploy` → `bundle run` |
| **File sync + apps deploy** | Rapid iteration, local development | `databricks sync` → `databricks apps deploy` |

Both methods produce the same result: a running Databricks App with your agent
code. The bundle path manages infrastructure-as-code (apps, jobs, experiments)
alongside the deployment. The sync path is faster for iterative development.

---

## 2. Bundle Deploy Workflow

### 2.1 Validate

Catches configuration errors before uploading anything:

```bash
databricks bundle validate
```

Checks performed:
- `databricks.yml` schema validity
- Resource references resolve (variables, cross-references)
- Target workspace is reachable with current auth profile
- App name uniqueness in the target workspace

### 2.2 Deploy

Uploads artifacts and registers resource definitions with the workspace:

```bash
databricks bundle deploy
```

What deploy does:
- Syncs source files to the workspace path (usually `~/.bundle/<name>/<target>/files/`)
- Creates or updates Terraform-managed resources (apps, jobs, experiments)
- Registers app configuration (env vars, resources, permissions)
- Runs artifact build commands (if `artifacts:` section is defined)

What deploy does **NOT** do:
- **Does NOT start or restart the app process**
- Does NOT execute app health checks
- Does NOT verify the app is actually serving requests

### 2.3 Run (CRITICAL)

**This step is mandatory.** Without it, your code changes are uploaded but the
app continues running the previous version.

```bash
databricks bundle run <app-resource-name>
```

For example, with the app-templates pattern:

```bash
databricks bundle run agent_openai_agents_sdk
```

What run does:
- Triggers an app deployment (creates a new deployment revision)
- Restarts the app process with the updated code and configuration
- Blocks until the deployment completes (or times out)

### 2.4 Complete Bundle Workflow

```bash
# Full deployment sequence
databricks bundle validate
databricks bundle deploy
databricks bundle run <app-resource-name>

# Verify
databricks apps get <app-name> -o json | python3 -c \
  "import sys,json; d=json.load(sys.stdin); \
   print(f'State: {d[\"compute_status\"][\"state\"]}')"
```

### 2.5 Bundle Variables

Variables parameterize the deployment across environments:

```yaml
# databricks.yml
variables:
  app_name:
    description: "App name (must be unique in workspace)"
    default: "my-agent-app"
  catalog:
    description: "Unity Catalog name"
    default: "main"
  warehouse_id:
    description: "SQL Warehouse ID"
```

Override at deploy time:

```bash
databricks bundle deploy --var warehouse_id=abc123def
databricks bundle run my-app --var warehouse_id=abc123def
```

---

## 3. File Sync Deployment

For rapid iteration when you don't need full bundle orchestration:

### 3.1 Sync Files

```bash
# Resolve your workspace username
DATABRICKS_USERNAME=$(databricks current-user me | jq -r .userName)

# Sync local directory to workspace
databricks sync . "/Users/$DATABRICKS_USERNAME/my-agent-app"
```

`databricks sync` watches for file changes and uploads incrementally.
Use `--watch` for continuous sync during development.

### 3.2 Deploy the App

```bash
databricks apps deploy my-agent-app \
  --source-code-path "/Workspace/Users/$DATABRICKS_USERNAME/my-agent-app"
```

This creates a new deployment revision and restarts the app.

### 3.3 First-Time Setup with Sync

If the app doesn't exist yet:

```bash
# Create the app first
databricks apps create my-agent-app

# Then sync and deploy
databricks sync . "/Users/$DATABRICKS_USERNAME/my-agent-app"
databricks apps deploy my-agent-app \
  --source-code-path "/Workspace/Users/$DATABRICKS_USERNAME/my-agent-app"
```

---

## 4. Resource Configuration in databricks.yml

### 4.1 App Resource

```yaml
resources:
  apps:
    my-agent-app:
      name: ${var.app_name}
      description: "Agent application"
      source_code_path: ./
      config:
        command: ["uv", "run", "start-app"]
        env:
          - name: MLFLOW_TRACKING_URI
            value: "databricks"
          - name: MLFLOW_REGISTRY_URI
            value: "databricks-uc"
          - name: MLFLOW_EXPERIMENT_ID
            value_from: "experiment"
          - name: WAREHOUSE_ID
            value: ${var.warehouse_id}
      resources:
        - name: "experiment"
          experiment:
            experiment_id: ""
            permission: "CAN_MANAGE"
        - name: "sql-warehouse"
          sql_warehouse:
            id: ${var.warehouse_id}
            permission: "CAN_USE"
        - name: "serving-endpoint"
          serving_endpoint:
            name: "my-llm-endpoint"
            permission: "CAN_QUERY"
      permissions:
        - user_name: "users"
          level: "CAN_USE"
```

### 4.2 Resource Types

| Resource Type | Permission Levels | Use Case |
|---------------|-------------------|----------|
| `sql_warehouse` | `CAN_USE`, `CAN_MANAGE` | SQL queries, warehouse-backed tools |
| `serving_endpoint` | `CAN_QUERY`, `CAN_MANAGE` | LLM calls, model serving |
| `experiment` | `CAN_EDIT`, `CAN_MANAGE` | MLflow experiment tracking |
| `secret_scope` | `READ` | API keys, connection strings |

### 4.3 User API Scopes

For apps that call Databricks APIs on behalf of users (OBO):

```yaml
resources:
  apps:
    my-app:
      user_api_scopes:
        - "dashboards.genie"
        - "files.files"
        - "catalog.catalogs:read"
        - "catalog.schemas:read"
        - "catalog.tables:read"
        - "sql"
```

---

## 5. MLflow Experiment Setup for Apps

### 5.1 Experiment as an App Resource

Declare the experiment in `databricks.yml` so the app's SP gets permissions:

```yaml
resources:
  apps:
    my-app:
      resources:
        - name: "experiment"
          experiment:
            experiment_id: ""
            permission: "CAN_MANAGE"
      config:
        env:
          - name: MLFLOW_EXPERIMENT_ID
            value_from: "experiment"
```

The `value_from` directive injects the experiment ID as an environment variable.
Your agent code reads `os.environ["MLFLOW_EXPERIMENT_ID"]` to set the active
experiment.

### 5.2 Post-Deploy Experiment Directory Permissions

The app's SP needs write access to the experiment's parent directory:

```bash
SHARED_EXP_ROOT="/Shared/my-agent-experiments"
databricks workspace mkdirs "$SHARED_EXP_ROOT" 2>/dev/null || true

SHARED_DIR_OBJ_ID=$(databricks workspace get-status "$SHARED_EXP_ROOT" -o json \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['object_id'])")

databricks api patch "/api/2.0/permissions/directories/$SHARED_DIR_OBJ_ID" \
  --json "{\"access_control_list\": [{
    \"service_principal_name\": \"$SP_CLIENT_ID\",
    \"permission_level\": \"CAN_MANAGE\"
  }]}"
```

This grant is typically handled in a deploy script (see `deploy.sh` step 8).

---

## 6. Service Principal Management

### 6.1 Automatic SP Creation

Databricks automatically creates a service principal for each app. Resolve it:

```bash
SP_CLIENT_ID=$(databricks apps get "$APP_NAME" -o json \
  | python3 -c "import sys,json; d=json.load(sys.stdin); \
     print(d.get('service_principal_client_id',''))")
```

### 6.2 Required SP Permissions

After bundle deploy, the SP needs additional grants that the bundle alone
cannot express:

| Resource | Permission | How to Grant |
|----------|------------|--------------|
| Unity Catalog schema | `USE CATALOG`, `USE SCHEMA`, `SELECT` | SQL GRANT statements |
| Job (if app triggers jobs) | `CAN_MANAGE` | Permissions API |
| Bundle workspace directory | `CAN_MANAGE` | Permissions API |
| MLflow experiment directory | `CAN_MANAGE` | Permissions API |
| Lakebase tables | Postgres `GRANT` | SQL on Lakebase endpoint |

### 6.3 Granting UC Permissions to SP

```sql
GRANT USE CATALOG ON CATALOG main TO `<sp-client-id>`;
GRANT USE SCHEMA ON SCHEMA main.my_schema TO `<sp-client-id>`;
GRANT SELECT ON SCHEMA main.my_schema TO `<sp-client-id>`;
```

### 6.4 Granting Job Permissions to SP

```bash
databricks api put "/api/2.0/permissions/jobs/$JOB_ID" \
  --json '{
    "access_control_list": [
      {"service_principal_name": "'$SP_CLIENT_ID'", "permission_level": "CAN_MANAGE"}
    ]
  }'
```

---

## 7. Lakebase Integration

### 7.1 Provisioned Lakebase

Apps do **not** inherit UC table ACLs inside raw Postgres connections. Explicit
SQL grants are required:

```sql
-- Run against the Lakebase Postgres endpoint
GRANT USAGE ON SCHEMA app TO <sp_role>;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA app TO <sp_role>;
GRANT USAGE ON SCHEMA public TO <sp_role>;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO <sp_role>;
```

See [`lakebase-permissions.md`](lakebase-permissions.md) for the complete
permissions script covering all table families.

### 7.2 Autoscaling Lakebase

Autoscaling Lakebase endpoints may require manual resource attachment:

```bash
# Not all Lakebase shapes are expressible in databricks.yml yet
# Use the REST API to attach compute or branch endpoints
databricks api post "/api/2.0/database/..." --json '{...}'
```

Plan for a small follow-up automation step if you rely on autoscaling instances.

---

## 8. Deployment Troubleshooting

| Issue | Symptom | Fix |
|-------|---------|-----|
| App not updating after code change | Old behavior persists | Run `databricks bundle run` after `bundle deploy` |
| `Provider produced inconsistent result` | Terraform plan error | Align `budget_policy_id` between state and workspace; use `bundle deployment bind` |
| Existing app name conflicts | Deploy fails with 409 | `databricks bundle deployment bind <resource> <app-name>` |
| SP cannot access notebooks | Job tasks fail with 403 | Grant SP `CAN_MANAGE` on bundle workspace directory |
| SP cannot write experiments | Tracing/logging fails | Grant SP `CAN_MANAGE` on experiment parent directory |
| Auth fails with PAT | 401 on agent queries | Use OAuth tokens; PATs not supported for Apps |
| App stuck in PENDING | Compute never starts | Check compute quota; only medium/large sizes supported |

---

## 9. Complete Deploy Script Pattern

A production deploy script follows these phases:

```bash
#!/usr/bin/env bash
set -euo pipefail

# Phase 1: Bundle deploy (creates/updates infra)
databricks bundle deploy "${BUNDLE_VAR_FLAGS[@]}"

# Phase 2: Resolve app SP
SP_CLIENT_ID=$(databricks apps get "$APP_NAME" -o json \
  | python3 -c "import sys,json; d=json.load(sys.stdin); \
     print(d.get('service_principal_client_id',''))")

# Phase 3: Grant UC permissions
# (catalog, schema, tables — via SQL or helper script)

# Phase 4: Resolve bundle-managed resources
JOB_ID=$(databricks bundle summary -o json \
  | python3 -c "import sys,json; ...")

# Phase 5: Inject runtime values and redeploy app
# (patch app.yml with job ID, then apps deploy)

# Phase 6: Grant job permissions to SP
databricks api put "/api/2.0/permissions/jobs/$JOB_ID" --json '...'

# Phase 7: Grant SP workspace directory access
databricks api patch "/api/2.0/permissions/directories/$DIR_ID" --json '...'

# Phase 8: Grant SP experiment directory access
databricks api patch "/api/2.0/permissions/directories/$EXP_DIR_ID" --json '...'
```

This pattern is implemented in `deploy.sh` at the project root.

---

## 10. Git-Based Deployment (Beta)

Databricks Apps supports deploying directly from a Git repository:

```bash
# Configure Git source on the app
# Then deploy with a Git reference:
databricks apps deploy my-app --git-branch main
```

Considerations:
- The app's SP must have a Git credential configured for private repos
- Changing the Git repo or switching sources deletes all Git credentials
- Branch/tag references deploy the latest commit; commit SHA pins exactly

---

## References

- [Author an agent (Databricks docs)](https://docs.databricks.com/aws/en/generative-ai/agent-framework/author-agent)
- [Deploy a Databricks app](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/deploy)
- [app-templates (GitHub)](https://github.com/databricks/app-templates)
- [App runtime configuration (app.yaml)](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/app-runtime)
- [Add resources to a Databricks app](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/resources)
- [`local-dev-loop.md`](local-dev-loop.md) — local development workflow
- [`lakebase-permissions.md`](lakebase-permissions.md) — Lakebase permission grants
- [`querying-agents.md`](querying-agents.md) — querying deployed agents
