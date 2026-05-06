# Silver Layer Pipeline Configuration Reference

Silver-specific DLT pipeline and DQ setup job YAML examples. These supplement the patterns in `databricks-asset-bundles` - **MUST read that skill first** for full configuration guidance.

---

## 🔴 Non-Negotiable Pipeline Defaults

These settings are ALWAYS applied to every Silver pipeline. There are NO exceptions.

```yaml
# 🔴 MANDATORY on every Silver pipeline YAML:
serverless: true      # NEVER use classic clusters
photon: true          # NEVER disable Photon
edition: ADVANCED     # NEVER use CORE or PRO (expectations require ADVANCED)
```

```yaml
# ❌ NEVER do any of these:
serverless: false                    # Classic clusters are forbidden
clusters:                            # No cluster definitions allowed
  - label: default
    num_workers: 4
photon: false                        # Photon must be enabled
edition: CORE                        # CORE/PRO don't support expectations
```

---

## DLT Pipeline Configuration

### File: `resources/silver_dlt_pipeline.yml`

```yaml
resources:
  pipelines:
    silver_dlt_pipeline:
      name: "[${bundle.target}] Silver Layer Pipeline"
      
      # Pipeline root folder (Lakeflow Pipelines Editor best practice)
      # All pipeline assets must be within this root folder
      root_path: ../src/{project}_silver
      
      # DLT Direct Publishing Mode (Modern Pattern)
      # ✅ Use 'schema' field (not 'target' - deprecated)
      catalog: ${var.catalog}
      schema: ${var.silver_schema}
      
      # DLT Libraries (Python notebooks or SQL files)
      libraries:
        - notebook:
            path: ../src/{project}_silver/silver_dimensions.py
        - notebook:
            path: ../src/{project}_silver/silver_transactions.py
        - notebook:
            path: ../src/{project}_silver/silver_inventory.py
        - notebook:
            path: ../src/{project}_silver/data_quality_monitoring.py
      
      # Pipeline Configuration (passed to notebooks)
      # Use fully qualified table names in notebooks: {catalog}.{schema}.{table}
      configuration:
        catalog: ${var.catalog}
        bronze_schema: ${var.bronze_schema}
        silver_schema: ${var.silver_schema}
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
            - data-engineering@company.com
      
      # Tags
      tags:
        environment: ${bundle.target}
        project: {project_name}
        layer: silver
        pipeline_type: medallion
        compute_type: serverless
```

### Key Configuration Notes

| Field | Value | Why |
|-------|-------|-----|
| `catalog` + `schema` | Use these (Direct Publishing) | `target` is deprecated |
| `root_path` | Points to source folder | Required for Lakeflow Pipelines Editor |
| `serverless` | `true` | Cost-efficient, no cluster management |
| `edition` | `ADVANCED` | 🔴 **MANDATORY** - Required for DLT expectations AND SCD/CDC. CORE and PRO editions do NOT support expectations or CDC. |
| `photon` | `true` | Performance optimization |
| `development` | `true` for dev, `false` for prod | Auto-recovery in dev mode |
| `configuration` | Pass catalog, bronze/silver schemas | Used by `get_bronze_table()` and `dq_rules_loader.py` |

### Edition Requirements (Common Source of Pipeline Failures)

| Feature | CORE | PRO | ADVANCED |
|---------|------|-----|----------|
| Streaming tables | Yes | Yes | Yes |
| Materialized views | Yes | Yes | Yes |
| **DLT Expectations** (`@dlt.expect*`) | **No** | **No** | **Yes** |
| **Change Data Capture (CDC)** | No | No | **Yes** |
| **SCD Type 1/2** | No | No | **Yes** |

```yaml
# ❌ WRONG: Default edition (CORE) - expectations silently ignored or fail
edition: CORE

# ✅ CORRECT: ADVANCED required for our DQ rules framework
edition: ADVANCED
```

**Error you'll see with wrong edition:** `Expectations are not supported in CORE edition. Please upgrade to ADVANCED.`

---

## DQ Setup Job Configuration

### File: `resources/silver_dq_setup_job.yml`

**One-time job to create and populate the DQ rules table:**

```yaml
resources:
  jobs:
    silver_dq_setup_job:
      name: "[${bundle.target}] {Project} Silver Layer - DQ Rules Setup"
      description: "One-time: Create and populate data quality rules Delta table"
      
      tasks:
        - task_key: setup_dq_rules_table
          notebook_task:
            notebook_path: ../src/{project}_silver/setup_dq_rules_table.py
            base_parameters:
              catalog: ${var.catalog}
              silver_schema: ${var.silver_schema}
      
      email_notifications:
        on_failure:
          - data-engineering@company.com
      
      tags:
        environment: ${bundle.target}
        layer: silver
        job_type: setup
```

### Key Job Notes

| Field | Value | Why |
|-------|-------|-----|
| `notebook_task` | NOT `python_task` | Databricks notebook execution |
| `base_parameters` | Dict format | Passed to `dbutils.widgets.get()` |
| Single task | No dependencies | One-time setup, no orchestration needed |

---

## Deployment Order

**CRITICAL: The DQ rules table MUST exist before the DLT pipeline runs.**

```bash
# Step 1: Deploy all resources
databricks bundle deploy -t dev

# Step 2: Run DQ rules setup job FIRST
databricks bundle run silver_dq_setup_job -t dev

# Step 3: Verify rules table was created
# Run in SQL Editor:
# SELECT * FROM {catalog}.{silver_schema}.dq_rules ORDER BY table_name, severity;

# Step 4: THEN start the DLT pipeline
databricks pipelines start-update --pipeline-name "[dev] Silver Layer Pipeline"
```

**Why This Order?**
- The DLT pipeline imports `dq_rules_loader.py` which reads from the `dq_rules` table
- If the table doesn't exist, the pipeline will fail with: `Table or view not found: dq_rules`
- The setup job is idempotent (uses `CREATE OR REPLACE TABLE` and `mode("overwrite")`)

---

## Pre-Deployment Validation (Dry Run)

ALWAYS validate the pipeline before deploying to production. Use `validate_only` mode to check for syntax errors, missing tables, and schema mismatches without creating any tables.

```bash
# Step 1: Deploy bundle (uploads files, creates pipeline definition)
databricks bundle deploy -t dev

# Step 2: Validate pipeline (dry run - no tables created)
databricks pipelines start-update --pipeline-name "[dev] Silver Layer Pipeline" --validate-only

# Step 3: Check for errors
databricks pipelines get-events --pipeline-name "[dev] Silver Layer Pipeline" --max-results 10
```

**What validation catches:**
- Missing DQ rules table (forgot to run setup job)
- Import errors in `dq_rules_loader.py`
- Column reference errors in expectations
- Missing Bronze tables
- Invalid table property values

**When to skip validation:** Never. Always validate before first run.

---

## Table Retention Properties (High-Volume Silver Tables)

For Silver fact tables that process millions of records daily, configure retention to manage storage costs:

```yaml
# In pipeline configuration -> table_properties
table_properties:
  # Standard Silver properties (MUST read databricks-table-properties)
  "delta.enableChangeDataFeed": "true"
  "delta.enableRowTracking": "true"
  "delta.enableDeletionVectors": "true"
  "delta.autoOptimize.autoCompact": "true"
  "delta.autoOptimize.optimizeWrite": "true"
  
  # Retention for high-volume tables
  "delta.logRetentionDuration": "30 days"             # Transaction log retention
  "delta.deletedFileRetentionDuration": "7 days"      # Vacuum retention
```

**When to set retention:**
- Silver fact tables with >1M records/day
- Tables with frequent updates (CDC sources)
- Tables where storage cost is a concern

**When NOT to set retention:**
- Dimension tables (small, infrequent changes)
- Tables that need long history for time-travel queries
- Compliance-regulated data with mandatory retention periods

---

## Production vs Development

For production deployments, change these settings. **Serverless, Photon, ADVANCED edition, and auto liquid clustering remain unchanged across all environments.**

```yaml
# In silver_dlt_pipeline.yml for production target
targets:
  prod:
    variables:
      catalog: prod_catalog
      bronze_schema: prod_bronze
      silver_schema: prod_silver
    
    # Override pipeline settings for prod
    resources:
      pipelines:
        silver_dlt_pipeline:
          development: false    # Disable dev mode
          continuous: false     # Triggered (not continuous) unless needed
          # 🔴 These NEVER change between environments:
          # serverless: true      (inherited from base - NEVER override to false)
          # photon: true          (inherited from base - NEVER override to false)
          # edition: ADVANCED     (inherited from base - NEVER downgrade)
```

**What changes between dev and prod:**
| Setting | Dev | Prod |
|---------|-----|------|
| `development` | `true` | `false` |
| `catalog` | `dev_catalog` | `prod_catalog` |
| `continuous` | `false` | `false` (or `true` for real-time) |

**What NEVER changes:**
| Setting | Value | Reason |
|---------|-------|--------|
| `serverless` | `true` | No classic clusters. Period. |
| `photon` | `true` | Vectorized execution always on. |
| `edition` | `ADVANCED` | Required for expectations. |
| `cluster_by_auto` | `True` | On every `@dlt.table()`. |
