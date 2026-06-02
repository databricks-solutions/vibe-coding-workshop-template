# Databricks Asset Bundles Common Errors & Troubleshooting

Comprehensive guide to anti-patterns, deployment errors, and troubleshooting.

## Common Mistakes to Avoid

❌ **Don't do this:**

### Notebook Duplication (CRITICAL)
```yaml
# ❌ WRONG: Same notebook in multiple jobs
# File 1: resources/semantic/tvf_job.yml
tasks:
  - task_key: deploy_tvfs
    notebook_task:
      notebook_path: ../../src/deploy_tvfs.py  # ❌ Also in orchestrator!

# File 2: resources/orchestrators/setup.yml
tasks:
  - task_key: deploy_tvfs
    notebook_task:
      notebook_path: ../../src/deploy_tvfs.py  # ❌ Duplicated notebook!

# ✅ CORRECT: Use run_job_task in orchestrator
# File 2: resources/orchestrators/setup.yml
tasks:
  - task_key: deploy_tvfs
    run_job_task:
      job_id: ${resources.jobs.tvf_deployment_job.id}  # ✅ Reference job
```

```bash
# ❌ WRONG: Creating shell scripts to reorganize code
# Asset Bundles can't execute shell scripts during deployment
# scripts/split_domains.sh  # Don't create these!
# scripts/reorganize_code.sh

# Code organization should be done:
# 1. Directly in Python/SQL files (proper imports, modular functions)
# 2. Via manual file moves/edits (not automated scripts)
# 3. Through proper project structure from the start
```

```yaml
# ❌ Hardcoded cluster config (not serverless)
cluster:
  spark_version: "13.3.x-scala2.12"
  node_type_id: "i3.xlarge"
  num_workers: 2

# ❌ No environments block
jobs:
  my_job:
    name: my_job  # ❌ Missing [${bundle.target}] prefix

# ❌ No tags, no error handling
tasks:
  - task_key: task1
    python_task:  # ❌ Should be notebook_task
      python_file: script.py

# ❌ WRONG: max_retries at job level (unsupported)
timeout_seconds: 7200
max_retries: 2
min_retry_interval_millis: 60000

# ❌ WRONG: Schedule not paused in dev
schedule:
  quartz_cron_expression: "0 0 2 * * ?"
  pause_status: UNPAUSED  # Will run automatically in dev!

# ❌ WRONG: Triggering DLT pipeline via Python wrapper
- task_key: run_pipeline
  python_task:
    python_file: ../src/trigger_dlt.py
    parameters:
      - "--pipeline-id=abc123"

# ❌ WRONG: Duplicated dependencies across tasks
- task_key: task1
  notebook_task:
    notebook_path: ../src/script1.py
  libraries:
    - pypi:
        package: Faker==22.0.0

- task_key: task2
  notebook_task:
    notebook_path: ../src/script2.py
  libraries:
    - pypi:
        package: Faker==22.0.0  # Duplicated!
```

```python
# ❌ WRONG: Using argparse in notebooks for DABs
# Databricks notebook source
import argparse  # ❌ Will fail in notebook_task!

def get_parameters():
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", required=True)
    args = parser.parse_args()  # ❌ Error: arguments are required
    return args.catalog
```

✅ **Do this:**
```yaml
resources:
  jobs:
    my_job:
      name: "[${bundle.target}] My Job"
      
      # ✅ Serverless environment
      environments:
        - environment_key: "default"
          spec:
            environment_version: "4"
      
      # ✅ Proper tags
      tags:
        environment: ${bundle.target}
        project: my_project
        layer: bronze
      
      # ✅ Error handling (timeout at job level)
      timeout_seconds: 7200
      
      tasks:
        - task_key: task1
          environment_key: default  # ✅ Reference environment
          notebook_task:  # ✅ Use notebook_task
            notebook_path: ../src/bronze/script.py
            base_parameters:  # ✅ Use base_parameters
              catalog: ${var.catalog}

# ✅ CORRECT: Schedule paused in dev
schedule:
  quartz_cron_expression: "0 0 2 * * ?"
  pause_status: PAUSED  # Enable manually in UI or prod

# ✅ CORRECT: Trigger DLT pipeline natively
- task_key: run_pipeline
  pipeline_task:
    pipeline_id: ${resources.pipelines.silver_dlt_pipeline.id}
    full_refresh: false

# ✅ CORRECT: Shared environment
environments:
  - environment_key: default
    spec:
      environment_version: "4"
      dependencies:
        - "Faker==22.0.0"

tasks:
  - task_key: task1
    environment_key: default
    notebook_task:
      notebook_path: ../src/script1.py
  
  - task_key: task2
    environment_key: default
    notebook_task:
      notebook_path: ../src/script2.py
```

```python
# ✅ CORRECT: Using dbutils.widgets for notebooks in DABs
# Databricks notebook source

def get_parameters():
    """Get job parameters from dbutils widgets."""
    catalog = dbutils.widgets.get("catalog")  # ✅ Works correctly
    print(f"Catalog: {catalog}")
    return catalog
```

## Deployment Error Prevention Patterns

**Critical patterns discovered from production deployments to prevent common errors.**

### Error 1: Duplicate Resource Files

**Problem:** Same resource defined in multiple locations causes conflicts.

❌ **WRONG:**
```
resources/
├── bronze_pipeline.yml           # Duplicate!
└── bronze/
    └── bronze_pipeline.yml       # Duplicate!
```

✅ **CORRECT:**
```
resources/
└── bronze/
    └── bronze_pipeline.yml       # Single source of truth
```

**Rule:** NEVER duplicate `.yml` files. Use subdirectories for organization, not duplication.

---

### Error 2: Path Resolution from Subdirectories

**Problem:** Relative paths behave differently depending on YAML file location.

❌ **WRONG:**
```yaml
# File: resources/gold/my_job.yml
tasks:
  - task_key: my_task
    notebook_task:
      notebook_path: ../src/my_script.py  # ❌ Wrong depth!
```

✅ **CORRECT:**
```yaml
# File: resources/gold/my_job.yml
tasks:
  - task_key: my_task
    notebook_task:
      notebook_path: ../../src/my_script.py  # ✅ Correct depth

# File: resources/my_job.yml (root level)
tasks:
  - task_key: my_task
    notebook_task:
      notebook_path: ../src/my_script.py  # ✅ Correct depth
```

**Rule:**
- From `resources/*.yml` → Use `../src/`
- From `resources/<layer>/*.yml` → Use `../../src/`
- From `resources/<layer>/<sublevel>/*.yml` → Use `../../../src/`

---

### Error 3: Invalid Task Type (python_task)

**Problem:** `python_task` is not a valid task type in Databricks Asset Bundles.

❌ **WRONG:**
```yaml
tasks:
  - task_key: my_task
    python_task:                      # ❌ Invalid task type!
      python_file: ../src/script.py
      parameters:
        - "--param=value"
```

✅ **CORRECT:**
```yaml
tasks:
  - task_key: my_task
    notebook_task:                    # ✅ Use notebook_task
      notebook_path: ../src/script.py
      base_parameters:
        param: value
```

**Rule:** ALWAYS use `notebook_task` with `notebook_path`, NEVER `python_task` with `python_file`.

---

### Error 4: Invalid Parameter Format

**Problem:** CLI-style parameters don't work in `notebook_task`.

❌ **WRONG:**
```yaml
notebook_task:
  notebook_path: ../src/script.py
  parameters:                         # ❌ CLI-style doesn't work!
    - "--catalog=my_catalog"
    - "--schema=my_schema"
```

✅ **CORRECT:**
```yaml
notebook_task:
  notebook_path: ../src/script.py
  base_parameters:                    # ✅ Dictionary format
    catalog: my_catalog
    schema: my_schema
```

**Rule:** Use `base_parameters` with dictionary format, NOT `parameters` with CLI-style strings.

---

### Error 5: Wrong Variable References

**Problem:** Missing `var.` prefix in variable substitution.

❌ **WRONG:**
```yaml
base_parameters:
  catalog: ${catalog}                 # ❌ Missing 'var.' prefix
  schema: ${bronze_schema}            # ❌ Missing 'var.' prefix
```

✅ **CORRECT:**
```yaml
base_parameters:
  catalog: ${var.catalog}             # ✅ Correct variable reference
  schema: ${var.bronze_schema}        # ✅ Correct variable reference
```

**Rule:** ALWAYS use `${var.<variable_name>}` format for bundle variables.

---

### Error 6: Invalid Orchestrator Task Reference

**Problem:** Using `job_task` instead of `run_job_task`.

❌ **WRONG:**
```yaml
tasks:
  - task_key: run_bronze_job
    job_task:                         # ❌ Invalid field!
      job_id: ${resources.jobs.bronze_job.id}
```

✅ **CORRECT:**
```yaml
tasks:
  - task_key: run_bronze_job
    run_job_task:                     # ✅ Correct field
      job_id: ${resources.jobs.bronze_job.id}
```

**Rule:** Use `run_job_task` to reference other jobs, NOT `job_task`.

---

### Error 7: Invalid SQL Task Syntax

**Problem:** Inline SQL queries require `query_id` or `file.path`.

❌ **WRONG:**
```yaml
tasks:
  - task_key: validate
    sql_task:
      warehouse_id: ${var.warehouse_id}
      query: "SELECT COUNT(*) FROM table"  # ❌ Not supported!
```

✅ **CORRECT Option 1 (File):**
```yaml
tasks:
  - task_key: validate
    sql_task:
      warehouse_id: ${var.warehouse_id}
      file:
        path: ../sql/validate.sql       # ✅ Reference SQL file
```

✅ **CORRECT Option 2 (Saved Query):**
```yaml
tasks:
  - task_key: validate
    sql_task:
      warehouse_id: ${var.warehouse_id}
      query:
        query_id: "abc123"              # ✅ Reference saved query ID
```

**Rule:** NEVER use inline SQL in `sql_task`. Use `file.path` or `query_id`.

---

### Error 8: Missing Subdirectory in Include Paths

**Problem:** Not including subdirectories when resources are moved.

❌ **WRONG:**
```yaml
# File: databricks.yml
include:
  - resources/*.yml
  - resources/bronze/*.yml            # Missing streaming/!
```

✅ **CORRECT:**
```yaml
# File: databricks.yml
include:
  - resources/*.yml
  - resources/bronze/*.yml
  - resources/bronze/streaming/*.yml  # ✅ Include subdirectories
```

**Rule:** When organizing resources into subdirectories, update `include:` paths in `databricks.yml`.

---

### Error 9: Pipeline Task Path Must Match root_path

**Problem:** DLT pipeline libraries reference files outside `root_path`.

❌ **WRONG:**
```yaml
resources:
  pipelines:
    my_pipeline:
      root_path: ../src/bronze/streaming
      libraries:
        - notebook:
            path: ../../bronze/other/script.py  # ❌ Outside root_path!
```

✅ **CORRECT:**
```yaml
resources:
  pipelines:
    my_pipeline:
      root_path: ../src/bronze/streaming
      libraries:
        - notebook:
            path: ../src/bronze/streaming/script.py  # ✅ Within root_path
```

**Rule:** All DLT pipeline library paths MUST be within the specified `root_path`.

---

### Error 10: Authentication Token Expiration

**Problem:** Default Databricks token expires, causing deployment failures.

❌ **ERROR:**
```
Error: Invalid access token. [ReqId: ...] (403)
```

✅ **SOLUTION:**
```bash
# Re-authenticate with specific profile
databricks auth login --host <workspace-url> --profile <profile-name>

# Verify authentication
databricks auth profiles

# Deploy with explicit profile
DATABRICKS_CONFIG_PROFILE=<profile-name> databricks bundle validate
DATABRICKS_CONFIG_PROFILE=<profile-name> databricks bundle deploy -t dev
```

**Rule:** Always use named profiles and re-authenticate before deployments. Never rely on default token.

---

### Error 11: Dashboard Hardcoded Catalog

**Problem:** Dashboard JSON contains hardcoded catalog names, breaking cross-environment deployment.

❌ **WRONG:**
```yaml
resources:
  dashboards:
    my_dashboard:
      display_name: "[${bundle.target}] Dashboard"
      file_path: ../src/dashboards/my_dashboard.lvdash.json
      warehouse_id: ${var.warehouse_id}
      # ❌ No dataset_catalog/dataset_schema - catalog hardcoded in JSON!
```

✅ **CORRECT:**
```yaml
resources:
  dashboards:
    my_dashboard:
      display_name: "[${bundle.target}] Dashboard"
      file_path: ../src/dashboards/my_dashboard.lvdash.json
      warehouse_id: ${var.warehouse_id}
      dataset_catalog: ${var.catalog}       # ✅ CLI 0.281.0+ (Jan 2026)
      dataset_schema: ${var.gold_schema}    # ✅ Overrides JSON defaults
```

**Rule:** Always use `dataset_catalog`/`dataset_schema` parameters (CLI v0.281.0+) to avoid hardcoded catalogs in dashboard JSON.

---

### Error 12: Alert v2 Schema Mismatch

**Problem:** SQL Alerts v2 API uses different field names than expected. This is the #1 most common alert deployment failure.

❌ **WRONG:**
```yaml
# These field names DO NOT EXIST in Alerts v2:
condition:                    # ❌ Should be "evaluation"
  op: LESS_THAN              # ❌ Should be "comparison_operator"
  operand:
    column:                   # ❌ Should be "source" at top level
      name: "r"

schedule:
  cron_schedule:              # ❌ Fields are directly under schedule
    quartz_cron_expression: "..."

subscriptions:                # ❌ Should be under evaluation.notification
  - destination_type: "EMAIL"
```

✅ **CORRECT:**
```yaml
evaluation:                   # ✅ Not "condition"
  comparison_operator: 'LESS_THAN_OR_EQUAL'  # ✅ Full name
  source:                     # ✅ Top-level, not nested
    name: 'c'
    display: 'c'
  threshold:
    value:
      double_value: 100
  notification:               # ✅ Subscriptions nested here
    subscriptions:
      - user_email: "${workspace.current_user.userName}"

schedule:                     # ✅ Fields directly under schedule
  pause_status: 'UNPAUSED'
  quartz_cron_schedule: '0 0 9 * * ?'   # ✅ Not quartz_cron_expression
  timezone_id: 'America/Los_Angeles'
```

**Rule:** ALWAYS inspect the schema first: `databricks bundle schema | grep -A 100 'sql.AlertV2'`

---

### Error 13: Volume Permissions Format

**Problem:** Volumes use `grants` not `permissions` -- different from all other resource types.

❌ **WRONG:**
```yaml
resources:
  volumes:
    my_volume:
      catalog_name: ${var.catalog}
      schema_name: ${var.gold_schema}
      name: "my_volume"
      volume_type: "MANAGED"
      permissions:             # ❌ Volumes don't use permissions!
        - level: CAN_READ
          group_name: "users"
```

✅ **CORRECT:**
```yaml
resources:
  volumes:
    my_volume:
      catalog_name: ${var.catalog}
      schema_name: ${var.gold_schema}
      name: "my_volume"
      volume_type: "MANAGED"
      grants:                  # ✅ Volumes use grants
        - principal: "users"
          privileges:
            - READ_VOLUME
```

**Rule:** Use `grants` (not `permissions`) for volume resources.

---

### Error 14: App Environment Variables in Wrong Location

**Problem:** App environment variables defined in `databricks.yml` instead of `app.yaml`.

❌ **WRONG:**
```yaml
# databricks.yml or resource file
resources:
  apps:
    my_app:
      name: my-app
      source_code_path: ../src/app
      env:                     # ❌ Env vars don't go here!
        DATABRICKS_CATALOG: "main"
```

✅ **CORRECT:**
```yaml
# src/app/app.yaml (env vars go HERE)
command: ["python", "app.py"]
env:
  - name: DATABRICKS_CATALOG
    value: "main"
  - name: DATABRICKS_WAREHOUSE_ID
    value: "your-warehouse-id"
```

**Rule:** Environment variables for apps go in `app.yaml` (source directory), not in the DAB resource file.

**Debugging apps:** Use `databricks apps logs <app-name>` to see deployment progress, errors, and runtime output.

---

## Pre-Deployment Validation Script

**Use this script to catch errors before deployment:**

```bash
#!/bin/bash
# File: scripts/validate_bundle.sh

echo "🔍 Pre-Deployment Validation"
echo "========================================"

# 1. Check for duplicate YAML files
echo "1. Checking for duplicate resource files..."
duplicates=$(find resources -name "*.yml" | awk -F/ '{print $NF}' | sort | uniq -d)
if [ -n "$duplicates" ]; then
    echo "❌ ERROR: Duplicate resource files found:"
    echo "$duplicates"
    exit 1
fi
echo "✅ No duplicate files"

# 2. Check for python_task usage (invalid)
echo "2. Checking for invalid python_task..."
if grep -r "python_task:" resources/ > /dev/null 2>&1; then
    echo "❌ ERROR: Found python_task (should be notebook_task)"
    grep -rn "python_task:" resources/
    exit 1
fi
echo "✅ No python_task found"

# 3. Check for CLI-style parameters (invalid)
echo "3. Checking for CLI-style parameters..."
if grep -r 'parameters:' resources/ | grep -E '"\-\-' > /dev/null 2>&1; then
    echo "❌ ERROR: Found CLI-style parameters (should be base_parameters)"
    grep -rn 'parameters:' resources/ | grep -E '"\-\-'
    exit 1
fi
echo "✅ No CLI-style parameters found"

# 4. Check for missing var. prefix
echo "4. Checking for variable references..."
if grep -r '\${catalog}' resources/ > /dev/null 2>&1; then
    echo "❌ ERROR: Found \${catalog} without var. prefix"
    grep -rn '\${catalog}' resources/
    exit 1
fi
echo "✅ Variable references correct"

# 5. Check for job_task (should be run_job_task)
echo "5. Checking for invalid job_task..."
if grep -r "job_task:" resources/ | grep -v "run_job_task:" > /dev/null 2>&1; then
    echo "❌ ERROR: Found job_task (should be run_job_task)"
    grep -rn "job_task:" resources/ | grep -v "run_job_task:"
    exit 1
fi
echo "✅ No invalid job_task found"

# 6. Validate bundle syntax
echo "6. Validating bundle syntax..."
if ! databricks bundle validate; then
    echo "❌ ERROR: Bundle validation failed"
    exit 1
fi
echo "✅ Bundle validation passed"

echo ""
echo "========================================"
echo "✅ All pre-deployment checks passed!"
echo "Ready to deploy with: databricks bundle deploy -t dev"
```

**Make it executable:**
```bash
chmod +x scripts/validate_bundle.sh
```

**Run before every deployment:**
```bash
./scripts/validate_bundle.sh && databricks bundle deploy -t dev
```

## Validation Checklist

When creating Asset Bundle configurations:

### Hierarchical Job Architecture (MANDATORY)
- [ ] Each notebook appears in exactly ONE atomic job (no duplication)
- [ ] Atomic jobs (Layer 1) use `notebook_task` with `notebook_path`
- [ ] Composite jobs (Layer 2) use `run_job_task` only (NO `notebook_task`)
- [ ] Master orchestrators (Layer 3) use `run_job_task` only (NO `notebook_task`)
- [ ] All jobs have `job_level` tag: `atomic`, `composite`, or `orchestrator`
- [ ] Job references use `${resources.jobs.<job_name>.id}` format
- [ ] Dependencies within orchestrators use `depends_on`

### General Configuration
- [ ] Use serverless compute for all new jobs/pipelines
- [ ] Include `[${bundle.target}]` prefix in names
- [ ] Define all parameters with defaults
- [ ] Use variable substitution (`${var.<name>}`)
- [ ] Include appropriate tags (add `orchestrator: "true"` for orchestrators)
- [ ] Set up failure notifications
- [ ] Use cron schedules for recurring jobs
- [ ] Set `pause_status: PAUSED` in dev for scheduled jobs
- [ ] Set timeouts at job level (`timeout_seconds`)
- [ ] Do NOT use `max_retries` or `min_retry_interval_millis` at job level (unsupported)
- [ ] Define permissions explicitly

### DLT Pipelines
- [ ] Use ADVANCED edition for DLT with expectations
- [ ] Enable Photon for DLT pipelines
- [ ] Define `root_path` for all DLT pipelines (Lakeflow Pipelines Editor best practice)
- [ ] Ensure all pipeline assets are within the `root_path`
- [ ] Use `pipeline_task` to trigger DLT pipelines (not Python/shell wrappers)

### Task Configuration (CRITICAL - Prevent Deployment Errors)
- [ ] Use `notebook_task` with `notebook_path` (NEVER `python_task` with `python_file`)
- [ ] Use `base_parameters` dictionary format (NOT CLI-style `parameters` with `--flags`)
- [ ] **Python notebooks use `dbutils.widgets.get()` for parameters (NEVER `argparse`)**
- [ ] Use `${var.variable_name}` format (NOT `${variable_name}` without `var.`)
- [ ] Use `run_job_task` to reference jobs (NOT `job_task`)
- [ ] Use `sql_task` with `file.path` or `query_id` (NOT inline SQL)
- [ ] Share environment specs across tasks with `environments` + `environment_key`
- [ ] Use `depends_on` to ensure correct task execution order

### Path Resolution (CRITICAL - Prevent Path Errors)
- [ ] Reference correct library paths based on YAML file location:
  - From `resources/*.yml` → Use `../src/`
  - From `resources/<layer>/*.yml` → Use `../../src/`
  - From `resources/<layer>/<sublevel>/*.yml` → Use `../../../src/`
- [ ] Update `databricks.yml` include paths when adding subdirectories
- [ ] Verify no duplicate `.yml` files across `resources/` directory

### Dashboards
- [ ] Use `dataset_catalog`/`dataset_schema` parameters (CLI v0.281.0+)
- [ ] No hardcoded catalog names in dashboard JSON
- [ ] Dashboard JSON exported and stored in `src/dashboards/`

### SQL Alerts
- [ ] Use `evaluation` (not `condition`) for alert criteria
- [ ] Use `quartz_cron_schedule` (not `quartz_cron_expression`) in alert schedule
- [ ] `subscriptions` nested under `evaluation.notification`
- [ ] Schema verified with `databricks bundle schema | grep -A 100 'sql.AlertV2'`

### Volumes
- [ ] Use `grants` (not `permissions`) for volume resources

### Apps
- [ ] Environment variables defined in `app.yaml` (source dir), not `databricks.yml`
- [ ] App started with `databricks bundle run <app_key>` after deployment

### Pre-Deployment Validation
- [ ] Run pre-deployment validation script (catches 80% of errors)
- [ ] Authenticate with named profile (`databricks auth login --profile <name>`)
- [ ] Run `databricks bundle validate` successfully
- [ ] Test in dev environment before promoting to prod

## Deployment Commands

### Initial Setup (One-Time)

```bash
# Validate bundle configuration
databricks bundle validate

# Deploy all resources (jobs, pipelines - NOT schemas)
databricks bundle deploy -t dev

# Run setup orchestrator (creates SCHEMAS, tables, functions, monitoring)
# This is where schemas are created programmatically using CREATE SCHEMA IF NOT EXISTS
databricks bundle run -t dev setup_orchestrator_job

# Run refresh orchestrator (populates data)
databricks bundle run -t dev refresh_orchestrator_job
```

### Individual Job Execution

```bash
# Run specific individual jobs
databricks bundle run -t dev bronze_setup_job
databricks bundle run -t dev bronze_data_generator_job
databricks bundle run -t dev gold_table_setup_job
databricks bundle run -t dev gold_merge_job

# Trigger DLT pipeline
databricks pipelines start-update --pipeline-name "[dev] Silver Layer Pipeline"
```

### Production Deployment

```bash
# Deploy to production
databricks bundle deploy -t prod

# Run setup once
databricks bundle run -t prod setup_orchestrator_job

# Enable scheduled refresh (or run manually)
databricks bundle run -t prod refresh_orchestrator_job
```

### Apps

```bash
# Start/deploy an app after bundle deploy
databricks bundle run <app_resource_key> -t dev

# View app logs (deployment progress, errors, runtime output)
databricks apps logs <app-name> --profile <profile-name>
```

### Cleanup

```bash
# Destroy all resources in dev (interactive confirmation)
databricks bundle destroy -t dev

# Destroy without confirmation prompts
databricks bundle destroy -t dev --auto-approve

# Force deploy (overwrite remote changes)
databricks bundle deploy -t dev --force

# Deploy without confirmation prompts
databricks bundle deploy -t dev --auto-approve
```

---

### Error 15: Resource Removal Triggers Terraform Destroy (CRITICAL)

**Problem:** Removing a resource block from `databricks.yml` between deployments causes Terraform to **destroy** the live resource. This is catastrophic for stateful resources like `postgres_projects` (Lakebase databases) and `apps`.

❌ **WRONG:**
```yaml
# Phase 1: databricks.yml includes postgres_projects
resources:
  postgres_projects:
    my_db:
      name: "my-lakebase-db"

# Phase 2: Developer removes block thinking "it already exists"
# resources:
#   postgres_projects:    ← REMOVED
#     my_db:              ← Terraform interprets this as "delete the database"
```

✅ **CORRECT:**
```yaml
# ALWAYS keep resource blocks for live infrastructure
resources:
  postgres_projects:
    my_db:
      name: "my-lakebase-db"

  apps:
    my_app:
      name: my-app-${bundle.target}
      source_code_path: ../src/app
      resources:
        - name: "lakebase-db"
          type: "postgres"
          postgres_project:
            project_name: "my-lakebase-db"
```

**Rule:** NEVER remove a resource from `databricks.yml` unless you intend to destroy it. Resources managed by the bundle have their lifecycle tied to their YAML definition.

**Recovery from accidental destroy:**
1. Recreate the resource manually via CLI or UI
2. Re-add the resource block to `databricks.yml`
3. Run `databricks bundle deploy --force` to re-sync state
4. Verify resource exists: `databricks lakebase projects list` (for Lakebase)

**Downstream impact:** ~6 minutes wasted per incident, plus manual recovery that permanently degrades IaC state tracking.

---

### Error 16: Lakebase Project Soft-Delete Errors

**Problem:** Lakebase projects use soft-delete. Recreating a recently deleted project or referencing a deleted one produces confusing errors.

| Error Message | Cause | Fix |
|---|---|---|
| `project with such id already exists` | Re-creating a soft-deleted project with the same name | Use a different project name, or wait for the soft-delete purge window to pass |
| `NOT_FOUND: project id not found` | Referencing a project that was deleted | Verify the project exists: `databricks lakebase projects list --profile <profile>` |

**Debugging:**
```bash
# List all Lakebase projects (including status)
databricks lakebase projects list --profile <profile>

# Check a specific project
databricks lakebase projects get <project-id> --profile <profile>
```

---

### Error 17: `--force` Flag Does Not Fix Name Conflicts

**Problem:** `--force` handles Terraform **state drift** (remote state differs from local), but does NOT resolve API-level name uniqueness errors such as DLT pipeline name collisions.

❌ **WRONG:**
```bash
# Pipeline name "[dev] Silver Pipeline" already exists in workspace
# Developer tries --force expecting it to delete and recreate
databricks bundle deploy -t dev --force  # ❌ Still fails with name conflict
```

✅ **CORRECT:**
```bash
# Option 1: Delete the conflicting resource first
databricks pipelines delete --pipeline-name "[dev] Silver Pipeline"
databricks bundle deploy -t dev

# Option 2: Change the pipeline name to avoid collision
# Edit YAML: name: "[${bundle.target} ${var.user_prefix}] Silver Pipeline"
databricks bundle deploy -t dev
```

**Rule:** `--force` = "overwrite remote Terraform state with local state." It does NOT delete-and-recreate resources or resolve API-level name uniqueness errors. For name conflicts, delete the existing resource or change the name.
