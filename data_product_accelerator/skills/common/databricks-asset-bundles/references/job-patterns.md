# Databricks Asset Bundles Job Patterns

Complete guide to hierarchical job architecture, task types, and parameter passing patterns.

## Hierarchical Job Architecture Pattern

**EVERY PROJECT MUST USE THIS 3-LAYER JOB HIERARCHY:**

### Core Principle: No Notebook Duplication

**Each notebook appears in EXACTLY ONE atomic job.** Higher-level jobs reference lower-level jobs via `run_job_task`, never duplicate notebooks.

### Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                        LAYER 3: MASTER ORCHESTRATORS                          │
│         References Layer 2 composite jobs via run_job_task                    │
│         NO direct notebook references                                          │
├──────────────────────────────────────────────────────────────────────────────┤
│  master_setup_orchestrator                master_refresh_orchestrator         │
│         │                                         │                           │
│    ┌────┴────┬────────────┐              ┌───────┴────────┐                  │
│    ▼         ▼            ▼              ▼                ▼                  │
│ semantic  monitoring   ml_layer    monitoring_ref   ml_inference             │
│  _setup    _setup      _setup         resh                                   │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                        LAYER 2: COMPOSITE JOBS                                │
│         References Layer 1 atomic jobs via run_job_task                       │
│         NO direct notebook references                                          │
├──────────────────────────────────────────────────────────────────────────────┤
│  semantic_layer_setup_job        monitoring_layer_setup_job                  │
│         │                                │                                   │
│    ┌────┴────┐                          │                                   │
│    ▼         ▼                          ▼                                   │
│  tvf_job  metric_view_job      lakehouse_monitoring_setup_job                │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                        LAYER 1: ATOMIC JOBS                                   │
│         Contains actual notebook_task references                              │
│         Single-purpose, testable independently                                │
├──────────────────────────────────────────────────────────────────────────────┤
│  tvf_deployment_job          metric_view_deployment_job                      │
│  lakehouse_monitoring_job    ml_training_pipeline                            │
│  ml_inference_pipeline       gold_setup_job                                  │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Layer 1: Atomic Jobs (Notebook Tasks)

**Atomic jobs contain actual notebook references. Each notebook appears in exactly ONE atomic job.**

```yaml
# Layer 1: Atomic Job - Single purpose, single notebook
# File: resources/semantic/tvf_deployment_job.yml

resources:
  jobs:
    tvf_deployment_job:
      name: "[${bundle.target}] Health Monitor - TVF Deployment"
      description: "Atomic job: Deploys Table-Valued Functions"
      
      environments:
        - environment_key: default
          spec:
            environment_version: "4"
      
      tasks:
        - task_key: deploy_all_tvfs
          environment_key: default
          notebook_task:  # ✅ Actual notebook reference
            notebook_path: ../../src/semantic/tvfs/deploy_tvfs.py
            base_parameters:
              catalog: ${var.catalog}
              gold_schema: ${var.gold_schema}
      
      tags:
        job_level: atomic  # ✅ Mark as atomic
        layer: semantic
```

### Layer 2: Composite Jobs (Job References)

**Composite jobs reference atomic jobs via `run_job_task`. NO direct notebook references.**

```yaml
# Layer 2: Composite Job - References atomic jobs
# File: resources/semantic/semantic_layer_setup_job.yml

resources:
  jobs:
    semantic_layer_setup_job:
      name: "[${bundle.target}] Health Monitor - Semantic Layer Setup"
      description: "Composite job: Deploys TVFs and Metric Views by referencing atomic jobs"
      
      tasks:
        # ✅ Reference atomic job, NOT notebook directly
        - task_key: deploy_tvfs
          run_job_task:
            job_id: ${resources.jobs.tvf_deployment_job.id}
        
        # ✅ Reference another atomic job
        - task_key: deploy_metric_views
          depends_on:
            - task_key: deploy_tvfs
          run_job_task:
            job_id: ${resources.jobs.metric_view_deployment_job.id}
      
      tags:
        job_level: composite  # ✅ Mark as composite
        layer: semantic
```

### Layer 3: Master Orchestrators (Composite References)

**Master orchestrators reference composite and atomic jobs. NO direct notebook references.**

```yaml
# Layer 3: Master Orchestrator - References composite jobs
# File: resources/orchestrators/master_setup_orchestrator.yml

resources:
  jobs:
    master_setup_orchestrator:
      name: "[${bundle.target}] Health Monitor - Master Setup Orchestrator"
      description: "Master orchestrator: References all setup jobs (no direct notebooks)"
      
      tasks:
        # Phase 1: Data Layer (atomic jobs)
        - task_key: bronze_setup
          run_job_task:
            job_id: ${resources.jobs.bronze_setup_job.id}
        
        - task_key: gold_setup
          depends_on:
            - task_key: bronze_setup
          run_job_task:
            job_id: ${resources.jobs.gold_setup_job.id}
        
        # Phase 2: Semantic Layer (composite job → atomic jobs)
        - task_key: semantic_layer_setup
          depends_on:
            - task_key: gold_setup
          run_job_task:
            job_id: ${resources.jobs.semantic_layer_setup_job.id}
        
        # Phase 3: Monitoring Layer (composite job → atomic jobs)
        - task_key: monitoring_layer_setup
          depends_on:
            - task_key: gold_setup
          run_job_task:
            job_id: ${resources.jobs.monitoring_layer_setup_job.id}
        
        # Phase 4: ML Layer (composite job → atomic jobs)
        - task_key: ml_layer_setup
          depends_on:
            - task_key: gold_setup
          run_job_task:
            job_id: ${resources.jobs.ml_layer_setup_job.id}
      
      tags:
        job_level: orchestrator  # ✅ Mark as orchestrator
        orchestrator: master
        layer: all
```

### ❌ WRONG: Notebook Duplication

```yaml
# ❌ WRONG: Same notebook in multiple jobs!

# File 1: resources/semantic/tvf_job.yml
tasks:
  - task_key: deploy_tvfs
    notebook_task:
      notebook_path: ../../src/semantic/tvfs/deploy_tvfs.py  # ❌ Duplicated!

# File 2: resources/orchestrators/setup_orchestrator.yml
tasks:
  - task_key: deploy_tvfs
    notebook_task:
      notebook_path: ../../src/semantic/tvfs/deploy_tvfs.py  # ❌ Same notebook!
```

**Problems:**
- Changes require updating multiple files
- Inconsistent parameter passing
- No single source of truth
- Difficult to track failures

### ✅ CORRECT: Job Reference Pattern

```yaml
# ✅ CORRECT: Notebook in ONE atomic job, referenced by orchestrator

# File 1: resources/semantic/tvf_job.yml (ATOMIC)
tasks:
  - task_key: deploy_tvfs
    notebook_task:
      notebook_path: ../../src/semantic/tvfs/deploy_tvfs.py  # ✅ Single source

# File 2: resources/orchestrators/setup_orchestrator.yml (ORCHESTRATOR)
tasks:
  - task_key: deploy_tvfs
    run_job_task:
      job_id: ${resources.jobs.tvf_deployment_job.id}  # ✅ Reference job, not notebook
```

### Benefits of Hierarchical Architecture

| Benefit | Description |
|---------|-------------|
| **Modularity** | Change one job without affecting others |
| **Debugging** | Isolate failures to specific atomic jobs |
| **Monitoring** | Track success/failure at granular level |
| **Flexibility** | Run any subset of the pipeline |
| **Testability** | Test atomic jobs independently |
| **Ownership** | Clear team responsibility per layer |

### Standard Job Levels Tag

```yaml
tags:
  job_level: <atomic|composite|orchestrator>  # ✅ Always include
```

### Directory Structure Pattern

```
resources/
├── orchestrators/                     # Layer 3: Master orchestrators
│   ├── master_setup_orchestrator.yml
│   └── master_refresh_orchestrator.yml
│
├── semantic/                          # Domain: Semantic Layer
│   ├── semantic_layer_setup_job.yml   # Layer 2: Composite
│   ├── tvf_deployment_job.yml         # Layer 1: Atomic
│   └── metric_view_deployment_job.yml # Layer 1: Atomic
│
├── monitoring/                        # Domain: Monitoring
│   ├── monitoring_layer_setup_job.yml # Layer 2: Composite
│   ├── monitoring_layer_refresh_job.yml # Layer 2: Composite
│   ├── lakehouse_monitoring_setup_job.yml # Layer 1: Atomic
│   └── lakehouse_monitoring_refresh_job.yml # Layer 1: Atomic
│
├── ml/                                # Domain: Machine Learning
│   ├── ml_layer_setup_job.yml         # Layer 2: Composite
│   ├── ml_layer_inference_job.yml     # Layer 2: Composite
│   ├── ml_feature_pipeline.yml        # Layer 1: Atomic
│   ├── ml_training_pipeline.yml       # Layer 1: Atomic
│   └── ml_inference_pipeline.yml      # Layer 1: Atomic
│
└── pipelines/                         # Domain: Data Pipelines
    ├── bronze/
    │   ├── bronze_setup_job.yml       # Layer 1: Atomic
    │   └── bronze_refresh_job.yml     # Layer 1: Atomic
    └── gold/
        ├── gold_setup_job.yml         # Layer 1: Atomic
        └── gold_merge_job.yml         # Layer 1: Atomic
```

### Validation Checklist for Hierarchical Jobs

- [ ] Each notebook appears in exactly ONE atomic job
- [ ] Composite jobs use `run_job_task` only (no `notebook_task`)
- [ ] Master orchestrators use `run_job_task` only (no `notebook_task`)
- [ ] All jobs have `job_level` tag (atomic, composite, or orchestrator)
- [ ] Atomic jobs have `environment_key` and `environments` block
- [ ] Job references use `${resources.jobs.<job_name>.id}` format
- [ ] Dependencies within orchestrators use `depends_on`

### Testing Each Layer

```bash
# Test Layer 1 (Atomic) - Individual functionality
databricks bundle run -t dev tvf_deployment_job
databricks bundle run -t dev metric_view_deployment_job

# Test Layer 2 (Composite) - Domain functionality
databricks bundle run -t dev semantic_layer_setup_job
databricks bundle run -t dev monitoring_layer_setup_job

# Test Layer 3 (Orchestrator) - Complete workflow
databricks bundle run -t dev master_setup_orchestrator
```

## Orchestrator Patterns

### Setup Orchestrator Pattern

```yaml
# Setup Orchestrator - One-time infrastructure bootstrap
# Creates tables, functions, and monitoring across all layers

resources:
  jobs:
    setup_orchestrator_job:
      name: "[${bundle.target}] <Project> Setup Orchestrator"
      description: "Orchestrates complete setup: tables, functions, monitoring"
      
      # Shared environment for all tasks
      environments:
        - environment_key: default
          spec:
            environment_version: "4"
            dependencies:
              - "Faker==22.0.0"  # Common dependencies
      
      tasks:
        # Step 1: Create Bronze tables
        - task_key: setup_bronze_tables
          environment_key: default
          notebook_task:
            notebook_path: ../src/<project>_bronze/setup_tables.py
            base_parameters:
              catalog: ${var.catalog}
              bronze_schema: ${var.bronze_schema}
        
        # Step 2: Create Gold tables (depends on Bronze)
        - task_key: setup_gold_tables
          depends_on:
            - task_key: setup_bronze_tables
          environment_key: default
          notebook_task:
            notebook_path: ../src/<project>_gold/create_gold_tables.py
            base_parameters:
              catalog: ${var.catalog}
              gold_schema: ${var.gold_schema}
        
        # Step 3: Create Table-Valued Functions (SQL)
        - task_key: create_table_valued_functions
          depends_on:
            - task_key: setup_gold_tables
          sql_task:
            warehouse_id: ${var.warehouse_id}
            file:
              path: ../src/<project>_gold/table_valued_functions.sql
            parameters:
              catalog: ${var.catalog}
              gold_schema: ${var.gold_schema}
        
        # Step 4: Create Metric Views
        - task_key: create_metric_views
          depends_on:
            - task_key: create_table_valued_functions
          environment_key: default
          notebook_task:
            notebook_path: ../src/<project>_gold/create_metric_views.py
            base_parameters:
              catalog: ${var.catalog}
              gold_schema: ${var.gold_schema}
        
        # Step 5: Setup Lakehouse Monitoring
        - task_key: setup_lakehouse_monitoring
          depends_on:
            - task_key: create_metric_views
          environment_key: default
          notebook_task:
            notebook_path: ../src/<project>_gold/lakehouse_monitoring.py
            base_parameters:
              catalog: ${var.catalog}
              gold_schema: ${var.gold_schema}
      
      # Email notifications
      email_notifications:
        on_failure:
          - data-engineering@company.com
        on_success:
          - data-engineering@company.com
      
      tags:
        environment: ${bundle.target}
        project: <project_name>
        layer: all
        compute_type: serverless
        job_type: setup
        orchestrator: "true"  # Mark as orchestrator
        job_level: orchestrator
```

### Refresh Orchestrator Pattern

```yaml
# Refresh Orchestrator - Recurring data pipeline execution
# Runs complete Bronze → Silver → Gold pipeline

resources:
  jobs:
    refresh_orchestrator_job:
      name: "[${bundle.target}] <Project> Refresh Orchestrator"
      description: "Orchestrates complete data pipeline: Bronze → Silver → Gold"
      
      environments:
        - environment_key: default
          spec:
            environment_version: "4"
            dependencies:
              - "Faker==22.0.0"
      
      tasks:
        # Step 1: Generate Bronze dimension data
        - task_key: generate_bronze_dimensions
          environment_key: default
          notebook_task:
            notebook_path: ../src/<project>_bronze/generate_dimensions.py
            base_parameters:
              catalog: ${var.catalog}
              schema: ${var.bronze_schema}
              num_stores: "100"
              num_products: "50"
        
        # Step 2: Generate Bronze fact data
        - task_key: generate_bronze_facts
          depends_on:
            - task_key: generate_bronze_dimensions
          environment_key: default
          notebook_task:
            notebook_path: ../src/<project>_bronze/generate_facts.py
            base_parameters:
              catalog: ${var.catalog}
              schema: ${var.bronze_schema}
              num_transactions: "10000"
              num_inventory_records: "5000"
        
        # Step 3: Trigger Silver DLT Pipeline
        - task_key: run_silver_dlt_pipeline
          depends_on:
            - task_key: generate_bronze_facts
          pipeline_task:
            pipeline_id: ${resources.pipelines.silver_dlt_pipeline.id}
            full_refresh: false  # Incremental by default
        
        # Step 4: Merge data into Gold layer
        - task_key: merge_gold_tables
          depends_on:
            - task_key: run_silver_dlt_pipeline
          environment_key: default
          notebook_task:
            notebook_path: ../src/<project>_gold/merge_gold_tables.py
            base_parameters:
              catalog: ${var.catalog}
              silver_schema: ${var.silver_schema}
              gold_schema: ${var.gold_schema}
      
      # Schedule: Daily at 2 AM (PAUSED in dev by default)
      schedule:
        quartz_cron_expression: "0 0 2 * * ?"
        timezone_id: "America/New_York"
        pause_status: PAUSED  # ✅ Always PAUSED in dev
      
      # Timeout at job level
      timeout_seconds: 14400  # 4 hours
      
      # Email notifications
      email_notifications:
        on_start:
          - data-engineering@company.com
        on_failure:
          - data-engineering@company.com
        on_success:
          - data-engineering@company.com
        on_duration_warning_threshold_exceeded:
          - data-engineering@company.com
      
      tags:
        environment: ${bundle.target}
        project: <project_name>
        layer: all
        compute_type: serverless
        job_type: pipeline
        orchestrator: "true"  # Mark as orchestrator
        job_level: orchestrator
```

### Pipeline Task Pattern

**Use `pipeline_task` to trigger DLT pipelines from workflows:**

```yaml
# Trigger a DLT pipeline as part of a workflow
- task_key: run_silver_pipeline
  depends_on:
    - task_key: previous_task
  pipeline_task:
    pipeline_id: ${resources.pipelines.silver_dlt_pipeline.id}  # ✅ Reference by resource ID
    full_refresh: false  # Incremental updates
```

**Benefits:**
- Native DLT integration
- Automatic pipeline state management
- No manual pipeline ID lookup needed
- Supports incremental and full refresh modes

### SQL Task with File Pattern

**Use `sql_task` with `file.path` to execute SQL scripts:**

```yaml
# Execute SQL file via SQL Warehouse
- task_key: create_functions
  depends_on:
    - task_key: previous_task
  sql_task:
    warehouse_id: ${var.warehouse_id}  # Serverless SQL Warehouse
    file:
      path: ../src/<layer>/<script>.sql  # SQL file path
    parameters:
      catalog: ${var.catalog}
      schema: ${var.schema}
```

**When to use:**
- Table-Valued Functions creation
- Complex SQL DDL operations
- Multi-statement SQL scripts
- Avoids Python wrapper overhead

## Python Notebook Parameter Passing (CRITICAL)

**⚠️ ALWAYS use `dbutils.widgets.get()` for notebook_task, NEVER `argparse`**

### The Problem

When notebooks are executed via `notebook_task` in Asset Bundles, parameters are passed through widgets, not command-line arguments. Using `argparse` will cause immediate failure.

**Common Error:**
```
usage: db_ipykernel_launcher.py [-h] --catalog CATALOG --schema SCHEMA
error: the following arguments are required: --catalog, --schema
```

### ❌ WRONG: Using argparse in Notebooks

```python
# Databricks notebook source
from pyspark.sql import SparkSession
import argparse  # ❌ WRONG for notebook_task!


def get_parameters():
    """Get job parameters."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", required=True, help="Catalog name")
    parser.add_argument("--schema", required=True, help="Schema name")
    args = parser.parse_args()  # ❌ This will FAIL in notebook_task
    return args.catalog, args.schema


def main():
    catalog, schema = get_parameters()
    # ... rest of logic
```

**YAML Configuration:**
```yaml
tasks:
  - task_key: my_task
    notebook_task:
      notebook_path: ../src/my_script.py
      base_parameters:  # Parameters passed as widgets
        catalog: ${var.catalog}
        schema: ${var.schema}
```

**Result:** ❌ FAILS with argparse error

### ✅ CORRECT: Using dbutils.widgets.get()

```python
# Databricks notebook source
from pyspark.sql import SparkSession


def get_parameters():
    """Get job parameters from dbutils widgets."""
    catalog = dbutils.widgets.get("catalog")  # ✅ CORRECT
    schema = dbutils.widgets.get("schema")
    
    # Log parameters for debugging
    print(f"Catalog: {catalog}")
    print(f"Schema: {schema}")
    
    return catalog, schema


def main():
    catalog, schema = get_parameters()
    # ... rest of logic
```

**YAML Configuration:**
```yaml
tasks:
  - task_key: my_task
    notebook_task:
      notebook_path: ../src/my_script.py
      base_parameters:  # Parameters passed as widgets
        catalog: ${var.catalog}
        schema: ${var.schema}
```

**Result:** ✅ WORKS correctly

### Pattern: Multiple Parameters

```python
# Databricks notebook source
from pyspark.sql import SparkSession


def get_parameters():
    """Get job parameters from dbutils widgets."""
    catalog = dbutils.widgets.get("catalog")
    bronze_schema = dbutils.widgets.get("bronze_schema")
    gold_schema = dbutils.widgets.get("gold_schema")
    
    print(f"Catalog: {catalog}")
    print(f"Bronze Schema: {bronze_schema}")
    print(f"Gold Schema: {gold_schema}")
    
    return catalog, bronze_schema, gold_schema


def main():
    catalog, bronze_schema, gold_schema = get_parameters()
    
    spark = SparkSession.builder.appName("My Job").getOrCreate()
    
    try:
        # Your logic here
        source_table = f"{catalog}.{bronze_schema}.my_table"
        target_table = f"{catalog}.{gold_schema}.my_table"
        
        print(f"Processing: {source_table} → {target_table}")
        # ... processing logic
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        raise
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
```

### When to Use Each Method

| Execution Context | Parameter Method | Use This |
|---|---|---|
| `notebook_task` in DABs | `base_parameters: {}` | ✅ `dbutils.widgets.get()` |
| Interactive notebook | Widgets | ✅ `dbutils.widgets.get()` |
| Local Python script | Command line | ✅ `argparse` |
| `python_task` in DABs (deprecated) | `parameters: ["--arg"]` | `argparse` |

**Rule:** If your script will run in Databricks (notebook or job), use `dbutils.widgets.get()`. Period.

### Migration Pattern

If you have existing scripts using `argparse`, convert them:

**BEFORE:**
```python
import argparse

def get_parameters():
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--schema", required=True)
    args = parser.parse_args()
    return args.catalog, args.schema
```

**AFTER:**
```python
# Remove: import argparse

def get_parameters():
    """Get job parameters from dbutils widgets."""
    catalog = dbutils.widgets.get("catalog")
    schema = dbutils.widgets.get("schema")
    
    print(f"Catalog: {catalog}")
    print(f"Schema: {schema}")
    
    return catalog, schema
```

**Changes:**
1. ✅ Remove `import argparse`
2. ✅ Replace `ArgumentParser()` with `dbutils.widgets.get()`
3. ✅ Add parameter logging
4. ✅ No changes to function signature (maintains compatibility)

### Validation Checklist for Notebooks

Before deploying any notebook script:

- [ ] Uses `dbutils.widgets.get()` for parameters (NOT `argparse`)
- [ ] No `import argparse` statement
- [ ] Parameters logged for debugging
- [ ] Function returns same signature (for backwards compatibility)
- [ ] YAML uses `notebook_task` with `base_parameters`
- [ ] Tested in Databricks workspace before DAB deployment

### Real-World Impact

**Projects affected by argparse issue:**
- Bronze non-streaming setup/merge (2 files)
- Gold layer setup/merge (17 files)
- **Total:** 19+ files had to be fixed

**Prevention:** Follow this pattern from the start, never use `argparse` in Databricks notebooks.
