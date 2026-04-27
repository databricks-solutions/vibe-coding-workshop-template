# Bundle Configuration Reference

Databricks Asset Bundles (DAB) configuration for deploying serving endpoints,
apps, and jobs. Grounded in the project's `databricks.yml`.

---

## 1. Bundle Structure

A DAB bundle is defined in `databricks.yml` at the project root:

```yaml
bundle:
  name: "genie-space-optimizer"

variables:
  # Deployment parameters with defaults
  ...

sync:
  include:
    # Files to sync to workspace
    ...

artifacts:
  # Build steps before deploy
  ...

resources:
  apps:
    # Databricks Apps
    ...
  jobs:
    # Databricks Jobs
    ...

targets:
  dev:
    mode: development
    default: true
  staging:
    mode: development
  prod:
    # Production target — no mode override
```

---

## 2. Variables Declaration

Variables parametrize the bundle across environments:

```yaml
variables:
  app_name:
    description: "Databricks App name (must be unique in your workspace)"
    default: "genie-space-optimizer"
  catalog:
    description: "Unity Catalog name for storing optimization state tables"
    default: "main"
  gold_schema:
    description: "Schema within the catalog for optimization tables"
    default: "genie_optimization"
  warehouse_id:
    description: "SQL Warehouse ID for query execution"
    # No default — must be provided at deploy time
  deploy_profile:
    default: "DEFAULT"
```

### Referencing variables

Inside resource definitions, use `${var.variable_name}`:

```yaml
resources:
  apps:
    my-app:
      name: ${var.app_name}
      config:
        env:
          - name: MY_CATALOG
            value: ${var.catalog}
```

### Providing variables at deploy time

```bash
# Via CLI flags
databricks bundle deploy --var warehouse_id=abc123def456

# Via environment variables
export BUNDLE_VAR_warehouse_id=abc123def456
databricks bundle deploy

# Via the deploy.sh wrapper (forwards to bundle deploy)
./deploy.sh --var warehouse_id=abc123def456
```

---

## 3. Resource Declarations

### App resource

```yaml
resources:
  apps:
    genie-space-optimizer-app:
      name: ${var.app_name}
      description: "Genie Space Optimizer"
      source_code_path: ./.build
      user_api_scopes:
        - "dashboards.genie"
        - "files.files"
        - "catalog.catalogs:read"
        - "catalog.schemas:read"
        - "catalog.tables:read"
        - "sql"
      config:
        env:
          - name: GENIE_SPACE_OPTIMIZER_CATALOG
            value: ${var.catalog}
          - name: GENIE_SPACE_OPTIMIZER_SCHEMA
            value: ${var.gold_schema}
          - name: GENIE_SPACE_OPTIMIZER_WAREHOUSE_ID
            value: ${var.warehouse_id}
          - name: GENIE_SPACE_OPTIMIZER_JOB_ID
            value: ${resources.jobs.genie-space-optimizer-runner.id}
      resources:
        - name: "sql-warehouse"
          sql_warehouse:
            id: ${var.warehouse_id}
            permission: "CAN_USE"
      permissions:
        - user_name: "users"
          level: "CAN_USE"
```

Key patterns:

| Pattern | Example | Purpose |
|---------|---------|---------|
| Cross-resource reference | `${resources.jobs.genie-space-optimizer-runner.id}` | Inject job ID into app env |
| OAuth scopes | `user_api_scopes: [...]` | App acts on behalf of users |
| Warehouse binding | `resources[].sql_warehouse` | App can use the warehouse |

### Job resource

See [`deployment-job-patterns.md`](deployment-job-patterns.md) for the complete
job configuration with tasks, parameters, and environments.

### Serving endpoint resource (generic pattern)

```yaml
resources:
  model_serving_endpoints:
    agent-endpoint:
      name: "genie-optimizer-agent-endpoint"
      config:
        served_entities:
          - entity_name: "main.genie_optimization.optimizer_agent"
            entity_version: "1"
            workload_size: "Small"
            scale_to_zero_enabled: true
        auto_capture_config:
          catalog_name: ${var.catalog}
          schema_name: ${var.gold_schema}
          table_name_prefix: "agent_inference"
          enabled: true
      permissions:
        - group_name: "users"
          level: "CAN_QUERY"
```

---

## 4. Permission Grants

### In-bundle permissions

```yaml
resources:
  jobs:
    my-job:
      permissions:
        - group_name: "users"
          level: "CAN_VIEW"
        - service_principal_name: "${var.sp_client_id}"
          level: "CAN_MANAGE"
```

### Post-bundle permissions (deploy.sh)

Some permissions cannot be expressed in the bundle and require post-deploy
API calls:

| Permission | API | Why post-deploy |
|-----------|-----|-----------------|
| Job `CAN_MANAGE` for app SP | `PUT /api/2.0/permissions/jobs/{id}` | SP resolved after app creation |
| Workspace directory access | `PATCH /api/2.0/permissions/directories/{id}` | Directory created during sync |
| MLflow experiment directory | `PATCH /api/2.0/permissions/directories/{id}` | Directory created at runtime |
| UC grants (catalog/schema/warehouse) | Python script via SDK | Complex grant logic |

### UC grants pattern

```python
# resources/grant_app_uc_permissions.py (simplified)
from databricks.sdk import WorkspaceClient

w = WorkspaceClient(profile=profile)

# Grant USE CATALOG
w.grants.update(
    securable_type="catalog",
    full_name=catalog,
    changes=[{"principal": sp_name, "add": ["USE_CATALOG"]}],
)

# Grant USE SCHEMA + CREATE TABLE
w.grants.update(
    securable_type="schema",
    full_name=f"{catalog}.{schema}",
    changes=[{"principal": sp_name, "add": ["USE_SCHEMA", "CREATE_TABLE"]}],
)
```

---

## 5. Environment-Specific Targets

### Development (default)

```yaml
targets:
  dev:
    mode: development
    default: true
```

`mode: development` prefixes resource names with the deployer's username and
adds `[dev]` tags. Useful for isolated testing.

### Staging

```yaml
targets:
  staging:
    mode: development
    variables:
      catalog: "staging_catalog"
      gold_schema: "genie_optimization_staging"
```

Override variables for staging-specific catalog/schema.

### Production

```yaml
targets:
  prod:
    variables:
      catalog: "prod_catalog"
      gold_schema: "genie_optimization"
    # No mode — resources use exact names (no dev prefix)
```

### Deploying to a specific target

```bash
databricks bundle deploy --target staging
databricks bundle deploy --target prod
```

---

## 6. Sync Configuration

Control which files are uploaded to the workspace:

```yaml
sync:
  include:
    - .build
    - .build/**
    - src/genie_space_optimizer/jobs
    - src/genie_space_optimizer/jobs/**
```

The `.databricksignore` file (similar to `.gitignore`) excludes files from sync.
In this project:

- `*.md` files are excluded (documentation not needed at runtime)
- `.build/` is explicitly included (contains the built app and wheel)
- Job notebooks under `src/genie_space_optimizer/jobs/` are included

---

## 7. Artifacts (Build Steps)

```yaml
artifacts:
  default:
    build: >-
      apx build &&
      rm -f .build/.gitignore &&
      python resources/patch_app_yml.py .build/app.yml
        --catalog ${var.catalog}
        --schema ${var.gold_schema}
        --warehouse-id ${var.warehouse_id} &&
      cp .build/genie_space_optimizer-*.whl
         .build/genie_space_optimizer-0.0.0-py3-none-any.whl &&
      echo "databricks-connect>=15.0.0" >> .build/requirements.txt
```

This runs during `databricks bundle deploy`:

1. `apx build` — builds the React frontend and Python wheel
2. Patches `app.yml` with deployment-specific values
3. Normalizes the wheel filename for the job environment
4. Adds `databricks-connect` to the app's requirements

---

## 8. Bundle Validate → Deploy → Run Workflow

### Validate (dry run)

```bash
databricks bundle validate
```

Checks YAML syntax, variable references, and resource definitions without
deploying anything.

### Deploy

```bash
databricks bundle deploy --var warehouse_id=abc123
```

Creates/updates all resources (apps, jobs, endpoints) in the target workspace.
Uses Terraform state under `.bundle/` to track what exists.

### Run a job

```bash
# Run the optimization job with parameters
databricks bundle run genie-space-optimizer-runner \
  --params run_id=test-001,space_id=abc123,catalog=main,schema=genie_optimization
```

### Destroy

```bash
databricks bundle destroy
```

Removes all bundle-managed resources. The project's `destroy.sh` wrapper
handles additional cleanup (deleting jobs first, then destroying the bundle).

---

## 9. DO / DON'T Pairs

### Variable references

```yaml
# DON'T — hardcode values that should be variables
config:
  env:
    - name: CATALOG
      value: "main"  # Won't change across environments
```

```yaml
# DO — use bundle variables
config:
  env:
    - name: CATALOG
      value: ${var.catalog}
```

### Cross-resource references

```yaml
# DON'T — hardcode resource IDs
config:
  env:
    - name: JOB_ID
      value: "12345"  # Breaks on redeploy
```

```yaml
# DO — reference other bundle resources
config:
  env:
    - name: JOB_ID
      value: ${resources.jobs.my-job.id}
```

### Sync patterns

```yaml
# DON'T — sync everything (slow, uploads unnecessary files)
sync:
  include:
    - "**"
```

```yaml
# DO — sync only what's needed
sync:
  include:
    - .build
    - .build/**
    - src/my_project/jobs
    - src/my_project/jobs/**
```

---

## Related Skills

- **Skill 11 (parent) — Model Serving Deployment:** Full deployment automation
- **Skill 00 — MLflow GenAI Foundation:** Dependency versions matching job env
- **Skill 10 — UC Model Management:** Model registration consumed by deploy task
