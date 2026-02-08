# Databricks Asset Bundles Configuration Guide

Complete YAML configuration patterns for Databricks Asset Bundles.

## Main Bundle Configuration (databricks.yml)

```yaml
# Databricks Asset Bundle Configuration
# <Project Name> - <Description>

bundle:
  name: <project_name>
  
variables:
  catalog:
    description: Unity Catalog name
    default: <default_catalog>
  
  bronze_schema:
    description: Schema name for Bronze layer (raw data ingestion)
    default: <bronze_schema_name>
  
  silver_schema:
    description: Schema name for Silver layer (cleaned, validated)
    default: <silver_schema_name>
  
  gold_schema:
    description: Schema name for Gold layer (business-ready aggregates)
    default: <gold_schema_name>
  
  warehouse_id:
    description: SQL Warehouse ID for serverless execution
    # ✅ PREFERRED: Use lookup to resolve by name (no hardcoded IDs)
    lookup:
      warehouse: "Shared SQL Warehouse"
    # Alternative: hardcode ID (less portable)
    # default: "<warehouse_id>"

targets:
  dev:
    mode: development
    default: true
    variables:
      catalog: <dev_catalog>
      # Override schema names with dev prefixes if needed
      bronze_schema: dev_<username>_<bronze_schema_name>
      silver_schema: dev_<username>_<silver_schema_name>
      gold_schema: dev_<username>_<gold_schema_name>
      
  prod:
    mode: production
    variables:
      catalog: <prod_catalog>
      # Production uses standard schema names (no prefix)

# Include all resource definitions from resources/ folder
include:
  - resources/*.yml
  - resources/bronze/*.yml
  - resources/silver/*.yml
  - resources/gold/*.yml

# Note: Schemas are NOT defined as resources
# They are created programmatically in setup scripts using:
# spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{schema}")
```

## Serverless Job Pattern

**✅ This is the MANDATORY starting point for every job:**

```yaml
# <Job Name> - <Description>
# Reference: https://github.com/databricks/bundle-examples/blob/main/knowledge_base/serverless_job/resources/serverless_job.yml

resources:
  jobs:
    <job_key>:
      name: "[${bundle.target}] <Job Display Name>"
      
      # ✅ MANDATORY: Serverless environment configuration
      environments:
        - environment_key: "default"
          spec:
            environment_version: "4"
      
      # Job parameters
      parameters:
        - name: catalog
          default: ${var.catalog}
        - name: <param_name>
          default: ${var.<param_name>}
      
      # Tasks
      tasks:
        - task_key: <task_key>
          environment_key: default  # ✅ MANDATORY: Reference the environment
          notebook_task:
            notebook_path: ../src/<path_to_script>.py
            base_parameters:
              catalog: ${var.catalog}
              <param>: ${var.<param>}
          libraries:
            - pypi:
                package: <package_name>
      
      # Schedule (optional)
      schedule:
        quartz_cron_expression: "0 0 2 * * ?"  # Daily at 2 AM
        timezone_id: "America/Los_Angeles"
        pause_status: UNPAUSED
      
      # Permissions
      permissions:
        - level: CAN_VIEW
          group_name: users
      
      # Tags
      tags:
        environment: ${bundle.target}
        project: <project_name>
        layer: <bronze|silver|gold>
        job_type: <setup|pipeline|monitoring>
```

## DLT Pipeline Pattern

### Direct Publishing Mode (Modern Pattern)

**DEPRECATED:**
- ❌ `target: ${var.catalog}.${var.schema}` - Old pattern
- ❌ `LIVE.` prefix in notebook table references

**MODERN (Always use):**
- ✅ `catalog:` + `schema:` fields (separate, not combined)
- ✅ Fully qualified table names in notebooks: `{catalog}.{schema}.{table}`
- ✅ Helper functions to build table names from `spark.conf.get()`

**Benefits of Direct Publishing Mode:**
- Publish to multiple catalogs/schemas
- Better cross-schema lineage
- Explicit catalog control
- Unity Catalog forward-compatible

```yaml
# <Layer> Layer DLT Pipeline (Serverless)
# Reference: https://github.com/databricks/bundle-examples/blob/main/knowledge_base/pipeline_with_schema/resources/pipeline.yml
# 
# Delta Live Tables streaming pipeline with data quality expectations
# Uses serverless compute for automatic scaling and cost optimization

resources:
  pipelines:
    <pipeline_key>:
      name: "[${bundle.target}] <Pipeline Display Name>"
      
      # Pipeline root folder (Lakeflow Pipelines Editor best practice)
      # All pipeline assets must be within this root folder
      # Reference: https://docs.databricks.com/aws/en/ldp/multi-file-editor#root-folder
      root_path: ../src/<layer>_pipeline
      
      # DLT Direct Publishing Mode (Modern Pattern)
      # ✅ Use 'schema' field (not 'target' - deprecated)
      catalog: ${var.catalog}
      schema: ${var.<layer>_schema}
      
      # DLT Libraries (Python notebooks or SQL files)
      libraries:
        - notebook:
            path: ../src/<layer>/<notebook1>.py
        - notebook:
            path: ../src/<layer>/<notebook2>.py
      
      # Pipeline Configuration (passed to notebooks)
      # Use fully qualified table names in notebooks: {catalog}.{schema}.{table}
      configuration:
        catalog: ${var.catalog}
        bronze_schema: ${var.bronze_schema}
        silver_schema: ${var.silver_schema}
        gold_schema: ${var.gold_schema}
        pipelines.enableTrackHistory: "true"
      
      # Serverless Compute
      serverless: true
      
      # Photon Engine
      photon: true
      
      # Channel (CURRENT = latest features)
      channel: CURRENT
      
      # Continuous vs Triggered
      continuous: false
      
      # Development Mode (faster iteration, auto-recovery)
      development: true
      
      # Edition (ADVANCED for expectations, SCD, etc.)
      edition: ADVANCED
      
      # Notifications
      notifications:
        - alerts:
            - on-update-failure
            - on-update-fatal-failure
            - on-flow-failure
          email_recipients:
            - <team-email>@company.com
      
      # Tags
      tags:
        environment: ${bundle.target}
        project: <project_name>
        layer: <layer>
        pipeline_type: medallion
        compute_type: serverless
```

### Modern Library Pattern: Glob Include

For pipelines with multiple notebooks, use `glob` instead of listing each notebook individually:

```yaml
resources:
  pipelines:
    <pipeline_key>:
      name: "[${bundle.target}] <Pipeline Name>"
      root_path: ../src/<layer>_pipeline
      catalog: ${var.catalog}
      schema: ${var.<layer>_schema}
      
      # ✅ MODERN: Glob pattern includes all files in directory
      libraries:
        - glob:
            include: ../src/pipelines/<pipeline_folder>/transformations/**
      
      serverless: true
      photon: true
      edition: ADVANCED
```

**When to use glob vs explicit notebooks:**
- **Glob**: When pipeline has many notebooks in a directory structure
- **Explicit**: When you need precise control over which notebooks are included

---

### Root Path Configuration (Lakeflow Pipelines Editor)

**ALWAYS define a root_path for DLT pipelines** to follow Lakeflow Pipelines Editor best practices.

**Benefits of root_path:**
- ✅ Organizes all pipeline assets in a single folder
- ✅ Enables better IDE experience in Lakeflow Pipelines Editor
- ✅ Improves version control and collaboration
- ✅ Simplifies asset discovery and management
- ✅ Required for multi-file editor features

**Pattern:**
```yaml
resources:
  pipelines:
    my_pipeline:
      name: "[${bundle.target}] My Pipeline"
      
      # Root path - all pipeline assets must be within this folder
      root_path: ../src/<layer>_pipeline
      
      # ... rest of configuration
```

**Folder Structure Example:**
```
src/
├── bronze_pipeline/      # root_path for bronze pipeline
│   ├── ingest_data.py
│   ├── validate_data.py
│   └── helpers/
│       └── common.py
├── silver_pipeline/      # root_path for silver pipeline  
│   ├── silver_dimensions.py
│   ├── silver_facts.py
│   └── data_quality_rules.py
└── gold_pipeline/        # root_path for gold pipeline
    ├── create_aggregates.py
    └── business_logic.py
```

**Important Notes:**
- All `libraries` paths must be within the `root_path`
- Helper modules and configuration files should be in the root folder
- Use consistent naming: `<layer>_pipeline` for clarity
- The root_path is relative to the bundle root directory

**References:**
- [Lakeflow Pipelines Editor - Root Folder](https://docs.databricks.com/aws/en/ldp/multi-file-editor#root-folder)
- [Bundle Pipeline Resources](https://docs.azure.cn/en-us/databricks/dev-tools/bundles/resources#pipelines)

## Dashboard Resource Pattern

**Support for `dataset_catalog` and `dataset_schema` parameters added in Databricks CLI 0.281.0 (January 2026)**

```yaml
resources:
  dashboards:
    <dashboard_key>:
      display_name: "[${bundle.target}] <Dashboard Title>"
      file_path: ../src/dashboards/<dashboard>.lvdash.json  # Relative to resources/
      warehouse_id: ${var.warehouse_id}
      
      # ✅ RECOMMENDED: Default catalog/schema for all datasets in the dashboard
      # Avoids hardcoded catalog references in dashboard JSON
      dataset_catalog: ${var.catalog}
      dataset_schema: ${var.gold_schema}
      
      permissions:
        - level: CAN_RUN
          group_name: "users"
```

**Permission levels:** `CAN_READ`, `CAN_RUN`, `CAN_EDIT`, `CAN_MANAGE`

**Key Rules:**
- Always use `dataset_catalog`/`dataset_schema` to avoid hardcoded catalog names in dashboard JSON
- Dashboard JSON files go in `src/dashboards/` directory
- Use `[${bundle.target}]` prefix in `display_name` for environment differentiation
- Export dashboards from UI, then replace hardcoded catalogs with the parameter approach

---

## SQL Alerts v2 Resource Pattern

**The Alert v2 API schema differs significantly from other resources. Always verify with `databricks bundle schema | grep -A 100 'sql.AlertV2'`.**

```yaml
resources:
  alerts:
    <alert_key>:
      display_name: "[${bundle.target}] <Alert Name>"
      query_text: "SELECT count(*) as c FROM ${var.catalog}.${var.gold_schema}.<table>"
      warehouse_id: ${var.warehouse_id}

      # ✅ CORRECT: Use "evaluation" (NOT "condition")
      evaluation:
        comparison_operator: 'LESS_THAN_OR_EQUAL'  # Triggers when condition is TRUE
        source:                    # NOT nested under "operand.column"
          name: 'c'
          display: 'c'
        threshold:
          value:
            double_value: 100
        notification:              # Subscriptions nested HERE (not top-level)
          notify_on_ok: false
          subscriptions:
            - user_email: "${workspace.current_user.userName}"

      # ✅ CORRECT: Fields directly under schedule (NOT under cron_schedule)
      schedule:
        pause_status: 'UNPAUSED'                        # REQUIRED
        quartz_cron_schedule: '0 0 9 * * ?'             # REQUIRED (daily 9 AM)
        timezone_id: 'America/Los_Angeles'              # REQUIRED

      permissions:
        - level: CAN_RUN
          group_name: "users"
```

**Critical gotchas:**
- Use `evaluation` not `condition`
- Use `source.name` not `operand.column.name`
- Use `quartz_cron_schedule` not `quartz_cron_expression` (different from jobs!)
- `subscriptions` go under `evaluation.notification`, not top-level
- Alerts trigger when condition evaluates to **TRUE** -- choose operator accordingly
- Comparison operators: `EQUAL`, `NOT_EQUAL`, `GREATER_THAN`, `GREATER_THAN_OR_EQUAL`, `LESS_THAN`, `LESS_THAN_OR_EQUAL`

---

## Volume Resource Pattern

```yaml
resources:
  volumes:
    <volume_key>:
      catalog_name: ${var.catalog}
      schema_name: ${var.gold_schema}
      name: "<volume_name>"
      volume_type: "MANAGED"
```

**Volumes use `grants` not `permissions`** -- this is a different format from all other resources:

```yaml
# ❌ WRONG for volumes
permissions:
  - level: CAN_READ
    group_name: "users"

# ✅ CORRECT for volumes
grants:
  - principal: "users"
    privileges:
      - READ_VOLUME
```

---

## Apps Resource Pattern

**Apps resource support added in Databricks CLI 0.239.0 (January 2025)**

Apps have a minimal DAB configuration. Environment variables go in `app.yaml` (source directory), NOT in `databricks.yml`.

### Generate from Existing App (Recommended)

```bash
databricks bundle generate app --existing-app-name my-app --key my_app --profile DEFAULT
```

### Manual Configuration

**resources/my_app.app.yml:**
```yaml
resources:
  apps:
    <app_key>:
      name: <app-name>-${bundle.target}     # Environment-specific naming
      description: "<App description>"
      source_code_path: ../src/app           # Relative to resources/ dir
```

**src/app/app.yaml** (environment variables go here, NOT in databricks.yml):
```yaml
command:
  - "python"
  - "app.py"
env:
  - name: DATABRICKS_WAREHOUSE_ID
    value: "your-warehouse-id"
  - name: DATABRICKS_CATALOG
    value: "main"
  - name: DATABRICKS_SCHEMA
    value: "my_schema"
```

**Key differences from other resources:**
- Environment variables live in `app.yaml` (source dir), not `databricks.yml`
- Configuration is minimal (name, description, source path)
- Apps require `databricks bundle run <app_key>` to start after deployment
- Debug with `databricks apps logs <app-name>` for deployment and runtime errors

---

## SQL Warehouse Job Pattern

```yaml
# <Job Name> using SQL Warehouse
# For SQL-based transformations or table creation

resources:
  jobs:
    <job_key>:
      name: "[${bundle.target}] <Job Display Name>"
      
      # Job parameters
      parameters:
        - name: catalog
          default: ${var.catalog}
        - name: <schema_name>
          default: ${var.<schema_name>}
      
      # Tasks
      tasks:
        - task_key: <task_key>
          sql_task:
            warehouse_id: ${var.warehouse_id}
            query:
              query_id: "<query_id>"  # Reference to saved query
            # OR inline SQL
            file:
              path: ../src/<layer>/<script>.sql
          parameters:
            catalog: ${var.catalog}
            <param>: ${var.<param>}
      
      # Schedule
      schedule:
        quartz_cron_expression: "0 0 * * * ?"  # Hourly
        timezone_id: "UTC"
        pause_status: UNPAUSED
      
      # Tags
      tags:
        environment: ${bundle.target}
        layer: <layer>
```

## Multi-Task Job with Dependencies

```yaml
resources:
  jobs:
    <job_key>:
      name: "[${bundle.target}] <Multi-Step Job>"
      
      environments:
        - environment_key: default
          spec:
            environment_version: "4"
      
      tasks:
        # Task 1: Setup
        - task_key: setup_tables
          environment_key: default
          notebook_task:
            notebook_path: ../src/<layer>/setup_tables.py
            base_parameters:
              catalog: ${var.catalog}
        
        # Task 2: Load data (depends on Task 1)
        - task_key: load_data
          depends_on:
            - task_key: setup_tables
          environment_key: default
          notebook_task:
            notebook_path: ../src/<layer>/load_data.py
            base_parameters:
              catalog: ${var.catalog}
        
        # Task 3: Validate (depends on Task 2)
        - task_key: validate
          depends_on:
            - task_key: load_data
          environment_key: default
          notebook_task:
            notebook_path: ../src/<layer>/validate.py
            base_parameters:
              catalog: ${var.catalog}
      
      # Email notifications on failure
      email_notifications:
        on_failure:
          - <team>@company.com
```

## Environment Specification Pattern

**Share environment configuration across all tasks:**

```yaml
environments:
  - environment_key: default
    spec:
      environment_version: "4"  # Serverless environment version
      dependencies:
        - "Faker==22.0.0"
        - "pandas==2.0.3"
        - "numpy==1.24.3"

tasks:
  - task_key: task1
    environment_key: default  # ✅ Reference shared environment
    notebook_task:
      notebook_path: ../src/script.py
```

**Benefits:**
- Consistent Python environment across tasks
- Centralized dependency management
- Version pinning for reproducibility
- Reduces YAML duplication

## Schema Management

**⚠️ CRITICAL: Schemas are NOT defined as Bundle resources.**

Schemas are created **programmatically** in setup scripts using `CREATE SCHEMA IF NOT EXISTS` statements.

### Pattern
```python
# In Bronze/Gold/ML setup scripts
def create_catalog_and_schema(spark: SparkSession, catalog: str, schema: str):
    """Ensures the Unity Catalog schema exists."""
    print(f"Ensuring catalog '{catalog}' and schema '{schema}' exist...")
    spark.sql(f"CREATE CATALOG IF NOT EXISTS {catalog}")
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{schema}")
    print(f"✓ Schema {catalog}.{schema} ready")
```

### Why Programmatic?
- ✅ **Flexibility** - Logic can adapt based on environment
- ✅ **Idempotent** - Safe to run multiple times
- ✅ **Fast iteration** - No bundle redeployment needed
- ✅ **Error handling** - Can catch and handle failures
- ✅ **Dynamic** - Can create schemas based on runtime conditions

### What databricks.yml Contains
- ✅ Schema **variables** (names used across jobs)
- ❌ NOT schema **resources** (no `resources.schemas:` section)

## Standard Tags Pattern

All jobs and pipelines should include these tags:

```yaml
tags:
  environment: ${bundle.target}  # dev, staging, prod
  project: <project_name>
  layer: <bronze|silver|gold|all>
  job_type: <setup|pipeline|etl|monitoring|ml>
  compute_type: <serverless|cluster>
  orchestrator: "true"  # Only for orchestrator workflows
  owner: <team_name>
  job_level: <atomic|composite|orchestrator>  # For hierarchical architecture
```

**Tag Guidelines:**
- `environment`: Always use `${bundle.target}` for automatic dev/prod differentiation
- `layer`: Use "all" for orchestrators that span multiple layers
- `job_type`: Use "setup" for infrastructure, "pipeline" for data workflows
- `orchestrator`: Set to "true" only for multi-layer orchestration workflows
- `compute_type`: Always "serverless" for new projects
- `job_level`: Required for hierarchical architecture (atomic/composite/orchestrator)

## Schedule Patterns

### Common Cron Expressions
```yaml
# Every hour
schedule:
  quartz_cron_expression: "0 0 * * * ?"
  timezone_id: "UTC"

# Daily at 2 AM
schedule:
  quartz_cron_expression: "0 0 2 * * ?"
  timezone_id: "America/Los_Angeles"

# Every 15 minutes
schedule:
  quartz_cron_expression: "0 */15 * * * ?"
  timezone_id: "UTC"

# Weekdays at 8 AM
schedule:
  quartz_cron_expression: "0 0 8 ? * MON-FRI"
  timezone_id: "America/New_York"

# First day of month at midnight
schedule:
  quartz_cron_expression: "0 0 0 1 * ?"
  timezone_id: "UTC"
```

**Important:** Always set `pause_status: PAUSED` in dev environments to prevent automatic execution.

## Notification Patterns

### DLT Pipeline Notifications
```yaml
notifications:
  - alerts:
      - on-update-failure
      - on-update-fatal-failure
      - on-flow-failure
    email_recipients:
      - data-engineering@company.com
```

### Job Notifications
```yaml
email_notifications:
  on_start:
    - <optional-email>@company.com
  on_success:
    - <optional-email>@company.com
  on_failure:
    - <required-email>@company.com
  on_duration_warning_threshold_exceeded:
    - <optional-email>@company.com

# Set timeout at job level
timeout_seconds: 7200  # 2 hours

# Note: max_retries and min_retry_interval_millis are NOT supported at job level
```

## Permissions Pattern

```yaml
permissions:
  - level: IS_OWNER
    user_name: <owner_email>@company.com
  
  - level: CAN_MANAGE_RUN
    group_name: data_engineers
  
  - level: CAN_VIEW
    group_name: users
```

## Library Dependencies Pattern

```yaml
libraries:
  # PyPI packages
  - pypi:
      package: pandas==2.0.3
  
  # Maven packages
  - maven:
      coordinates: "com.databricks:spark-xml_2.12:0.16.0"
  
  # Whl files
  - whl: ../dist/my_package-0.1.0-py3-none-any.whl
  
  # Jar files
  - jar: ../jars/custom-lib.jar
```

**Best Practice:** Define common dependencies in shared `environments` block rather than per-task `libraries`.

## File Organization

```
project_root/
├── databricks.yml          # Main bundle config
├── resources/
│   # Orchestrators (recommended for production)
│   ├── setup_orchestrator_job.yml     # One-time setup workflow
│   ├── refresh_orchestrator_job.yml   # Recurring data pipeline
│   │
│   # Individual jobs (for granular control)
│   ├── bronze_setup_job.yml
│   ├── bronze_data_generator_job.yml
│   ├── silver_dlt_pipeline.yml
│   ├── gold_table_setup_job.yml
│   ├── gold_merge_job.yml
│   └── gold_semantic_setup_job.yml
│
└── src/
    ├── <project>_bronze/
    ├── <project>_silver/
    └── <project>_gold/
```

### When to Use Orchestrators vs Individual Jobs

**Use Orchestrators when:**
- ✅ Deploying to production (simplified operations)
- ✅ Running complete end-to-end workflows
- ✅ Need guaranteed task execution order
- ✅ Want single workflow to monitor
- ✅ Coordinating across multiple layers (Bronze → Silver → Gold)

**Use Individual Jobs when:**
- ✅ Developing and testing specific layers
- ✅ Need granular control over execution
- ✅ Running ad-hoc operations
- ✅ Debugging specific components
- ✅ Different schedules for different layers

**Best Practice:** Deploy both orchestrators and individual jobs. Use orchestrators for production, individual jobs for development.
