---
name: databricks-asset-bundles
description: Standard patterns for Databricks Asset Bundles configuration files for serverless jobs, DLT pipelines, dashboards, alerts, apps, and workflows. Use when creating, configuring, or deploying DABs for infrastructure-as-code deployments. Covers mandatory serverless environment configuration, hierarchical job architecture (atomic/composite/orchestrator), DLT pipeline patterns, dashboard resources with dataset_catalog/dataset_schema, SQL Alerts v2 API schema, Apps lifecycle, Python notebook parameter passing (dbutils.widgets.get vs argparse), deployment error prevention, and pre-deployment validation.
metadata:
  author: prashanth subrahmanyam
  version: "2.0"
  domain: infrastructure
  role: shared
  used_by_stages: [1, 2, 3, 4, 5, 6, 7, 8, 9]
  last_verified: "2026-02-07"
  volatility: medium
  upstream_sources:
    - name: "ai-dev-kit"
      repo: "databricks-solutions/ai-dev-kit"
      paths:
        - "databricks-skills/databricks-asset-bundles/SKILL.md"
      relationship: "extended"
      last_synced: "2026-02-19"
      sync_commit: "97a3637"
---

# Databricks Asset Bundles (DABs)

## Overview

Databricks Asset Bundles provide infrastructure-as-code for deploying Databricks workflows, jobs, and DLT pipelines. This skill standardizes configuration patterns for serverless-first, production-ready deployments with hierarchical job architecture, proper parameter passing, and comprehensive error prevention.

## When to Use This Skill

- Creating or configuring Databricks Asset Bundle YAML files
- Deploying serverless jobs, DLT pipelines, dashboards, alerts, apps, or workflows
- Setting up hierarchical job architectures (atomic/composite/orchestrator)
- Configuring dashboard resources with `dataset_catalog`/`dataset_schema` (CLI 0.281.0+)
- Setting up SQL Alerts v2 (schema differs significantly from other resources)
- Configuring Databricks Apps in DABs (env vars in `app.yaml`, not `databricks.yml`)
- Troubleshooting deployment errors or configuration issues
- Converting notebooks to use proper parameter passing patterns
- Validating bundle configurations before deployment

## Critical Rules (Quick Reference)

### 🔴 MANDATORY: Serverless Environment Configuration (Environments V4)

**EVERY JOB MUST INCLUDE THIS — NO EXCEPTIONS:**

```yaml
resources:
  jobs:
    <job_name>:
      name: "[${bundle.target}] <Display Name>"
      
      # ✅ MANDATORY: Serverless environment with V4
      environments:
        - environment_key: "default"
          spec:
            environment_version: "4"  # 🔴 ALWAYS V4 - never omit or use older versions
      
      tasks:
        - task_key: <task_name>
          environment_key: default  # ✅ MANDATORY: Reference environment in EVERY task
          notebook_task:
            notebook_path: ../src/<script>.py
```

**Validation:** Before deploying ANY job YAML:
- [ ] `environments:` block exists at job level
- [ ] `environment_version: "4"` is set (NEVER omit, NEVER use older versions)
- [ ] Every task has `environment_key: default`
- [ ] NO `job_clusters:`, `existing_cluster_id:`, or `new_cluster:` defined (serverless only)

### 🔴 MANDATORY: Hierarchical Job Architecture

**3-LAYER HIERARCHY - NO EXCEPTIONS:**

1. **Layer 1: Atomic Jobs** - Contain actual `notebook_task` references (single notebook per job)
2. **Layer 2: Composite Jobs** - Reference atomic jobs via `run_job_task` (NO direct notebooks)
3. **Layer 3: Master Orchestrators** - Reference composite/atomic jobs via `run_job_task` (NO direct notebooks)

**Rule:** Each notebook appears in EXACTLY ONE atomic job. Higher-level jobs reference lower-level jobs, never duplicate notebooks.

### 🔴 MANDATORY: Parameter Passing Pattern

**ALWAYS use `dbutils.widgets.get()` for `notebook_task`, NEVER `argparse`:**

```python
# ✅ CORRECT: Databricks notebook
def get_parameters():
    catalog = dbutils.widgets.get("catalog")  # ✅ Works in notebook_task
    schema = dbutils.widgets.get("schema")
    return catalog, schema
```

```yaml
# ✅ CORRECT: YAML configuration
notebook_task:
  notebook_path: ../src/script.py
  base_parameters:  # ✅ Dictionary format
    catalog: ${var.catalog}
    schema: ${var.schema}
```

**Why:** `notebook_task` passes parameters through widgets, not command-line arguments. Using `argparse` causes immediate failure.

### 🔴 MANDATORY: Task Type Pattern

**ALWAYS use `notebook_task`, NEVER `python_task`:**

```yaml
# ✅ CORRECT
tasks:
  - task_key: my_task
    notebook_task:  # ✅ Use notebook_task
      notebook_path: ../src/script.py
      base_parameters:  # ✅ Dictionary format
        catalog: ${var.catalog}

# ❌ WRONG
tasks:
  - task_key: my_task
    python_task:  # ❌ Invalid task type!
      python_file: ../src/script.py
      parameters:  # ❌ CLI-style doesn't work!
        - "--catalog=value"
```

## Core Patterns

### Serverless Job Pattern

```yaml
resources:
  jobs:
    <job_key>:
      name: "[${bundle.target}] <Job Display Name>"
      
      # ✅ MANDATORY: Serverless environment
      environments:
        - environment_key: "default"
          spec:
            environment_version: "4"
      
      tasks:
        - task_key: <task_key>
          environment_key: default  # ✅ MANDATORY
          notebook_task:
            notebook_path: ../src/<script>.py
            base_parameters:
              catalog: ${var.catalog}
      
      tags:
        environment: ${bundle.target}
        project: <project_name>
        layer: <bronze|silver|gold>
```

### DLT Pipeline Pattern

```yaml
resources:
  pipelines:
    <pipeline_key>:
      name: "[${bundle.target}] <Pipeline Display Name>"
      
      # ✅ MANDATORY: Root path for Lakeflow Pipelines Editor
      root_path: ../src/<layer>_pipeline
      
      # ✅ Direct Publishing Mode (Modern Pattern)
      catalog: ${var.catalog}
      schema: ${var.<layer>_schema}
      
      libraries:
        - notebook:
            path: ../src/<layer>/<notebook>.py
      
      configuration:
        catalog: ${var.catalog}
        bronze_schema: ${var.bronze_schema}
      
      serverless: true
      photon: true
      edition: ADVANCED
      
      tags:
        environment: ${bundle.target}
        layer: <layer>
```

### Job Reference Pattern (Hierarchical Architecture)

```yaml
# Layer 1: Atomic Job (contains notebook)
resources:
  jobs:
    tvf_deployment_job:
      name: "[${bundle.target}] TVF Deployment"
      environments:
        - environment_key: default
          spec:
            environment_version: "4"
      tasks:
        - task_key: deploy_tvfs
          environment_key: default
          notebook_task:  # ✅ Actual notebook reference
            notebook_path: ../../src/semantic/tvfs/deploy_tvfs.py
      tags:
        job_level: atomic

# Layer 2: Composite Job (references atomic jobs)
resources:
  jobs:
    semantic_layer_setup_job:
      name: "[${bundle.target}] Semantic Layer Setup"
      tasks:
        - task_key: deploy_tvfs
          run_job_task:  # ✅ Reference job, NOT notebook
            job_id: ${resources.jobs.tvf_deployment_job.id}
        - task_key: deploy_metric_views
          depends_on:
            - task_key: deploy_tvfs
          run_job_task:
            job_id: ${resources.jobs.metric_view_deployment_job.id}
      tags:
        job_level: composite
```

## Job Hierarchy Overview

### Layer 1: Atomic Jobs
- **Purpose:** Single-purpose jobs with actual notebook references
- **Pattern:** Use `notebook_task` with `notebook_path`
- **Tag:** `job_level: atomic`
- **Example:** `tvf_deployment_job`, `gold_setup_job`

### Layer 2: Composite Jobs
- **Purpose:** Domain-level coordination (e.g., semantic layer setup)
- **Pattern:** Use `run_job_task` to reference atomic jobs
- **Tag:** `job_level: composite`
- **Example:** `semantic_layer_setup_job`, `monitoring_layer_setup_job`

### Layer 3: Master Orchestrators
- **Purpose:** Complete workflow coordination across layers
- **Pattern:** Use `run_job_task` to reference composite/atomic jobs
- **Tag:** `job_level: orchestrator`
- **Example:** `master_setup_orchestrator`, `master_refresh_orchestrator`

**Key Principle:** No notebook duplication. Each notebook appears in exactly ONE atomic job.

## Upstream Updates (February 2026)

Recent additions from the upstream `databricks-asset-bundles` skill in AI-Dev-Kit:

### Dashboard `dataset_catalog` / `dataset_schema` (CLI v0.281.0+)

Dashboards now support default catalog/schema for all datasets:
```yaml
resources:
  dashboards:
    my_dashboard:
      display_name: "[${bundle.target}] My Dashboard"
      file_path: ../src/dashboards/dashboard.lvdash.json
      warehouse_id: ${var.warehouse_id}
      dataset_catalog: ${var.catalog}
      dataset_schema: ${var.schema}
```

### Apps Resources (CLI v0.239.0+)

Apps have minimal DAB configuration. Environment variables go in `app.yaml` (source directory), NOT in `databricks.yml`:
```yaml
resources:
  apps:
    my_app:
      name: my-app-${bundle.target}
      description: "My application"
      source_code_path: ../src/app
```

Generate from an existing app: `databricks bundle generate app --existing-app-name my-app --key my_app`

Apps require `databricks bundle run <app_key>` to start after deployment.

### Volume Resources

Volumes use `grants` (not `permissions`):
```yaml
resources:
  volumes:
    my_volume:
      catalog_name: ${var.catalog}
      schema_name: ${var.schema}
      name: "volume_name"
      volume_type: "MANAGED"
```

### App Monitoring

View application logs: `databricks apps logs <app-name> --profile <profile-name>`

## Path Resolution Rules

Relative paths depend on YAML file location:

- From `resources/*.yml` → Use `../src/`
- From `resources/<layer>/*.yml` → Use `../../src/`
- From `resources/<layer>/<sublevel>/*.yml` → Use `../../../src/`

**Rule:** Always verify path depth matches directory structure.

## Reference Files

- **[Configuration Guide](references/configuration-guide.md)**: Complete YAML configuration patterns, environment setup, variables (with warehouse_id lookup), targets, DLT pipelines (with glob libraries), dashboards (dataset_catalog/dataset_schema), SQL Alerts v2, volumes (grants not permissions), Apps, schedules, notifications, permissions, library dependencies
- **[Job Patterns](references/job-patterns.md)**: Hierarchical job architecture (atomic/composite/orchestrator), task types, parameter passing (dbutils.widgets.get vs argparse), orchestrator patterns, SQL tasks, multi-task dependencies
- **[Common Errors](references/common-errors.md)**: Anti-patterns, deployment error prevention (14 common errors including dashboard hardcoded catalog, alert v2 schema mismatch, volume permissions, app env vars), troubleshooting guide, validation checklist, pre-deployment validation script

## Scripts

- **[validate_bundle.py](scripts/validate_bundle.py)**: Pre-deployment validation script to catch common configuration errors

## Assets

- **[bundle-template.yaml](assets/templates/bundle-template.yaml)**: Starter template for a new Databricks Asset Bundle with serverless configuration

## Quick Validation Checklist

Before deploying any bundle:

### Jobs & Pipelines
- [ ] Serverless environment configured (`environments:` block + `environment_key` in tasks)
- [ ] **Environments Version 4:** `environment_version: "4"` in every `environments.spec` (MANDATORY)
- [ ] Using `notebook_task` (NOT `python_task`)
- [ ] Using `base_parameters` dictionary format (NOT CLI-style `parameters`)
- [ ] Notebooks use `dbutils.widgets.get()` (NOT `argparse`)
- [ ] Variable references use `${var.<name>}` format
- [ ] Hierarchical architecture: notebooks in atomic jobs only, composite/orchestrator use `run_job_task`
- [ ] All jobs have `job_level` tag (atomic/composite/orchestrator)
- [ ] Path resolution matches directory structure
- [ ] DLT pipelines have `root_path` defined

### Dashboards
- [ ] Uses `dataset_catalog`/`dataset_schema` params (no hardcoded catalogs in JSON)

### SQL Alerts
- [ ] Uses `evaluation` (not `condition`), `quartz_cron_schedule` (not `quartz_cron_expression`)
- [ ] Schema verified with `databricks bundle schema | grep -A 100 'sql.AlertV2'`

### Volumes & Apps
- [ ] Volumes use `grants` (not `permissions`)
- [ ] App env vars in `app.yaml` (not `databricks.yml`)

### Pre-Deploy
- [ ] Run pre-deployment validation script
- [ ] `databricks bundle validate` passes

## Deployment Commands

```bash
# Validate bundle configuration
databricks bundle validate

# Deploy to dev
databricks bundle deploy -t dev

# Deploy with auto-approve (skip confirmation prompts)
databricks bundle deploy -t dev --auto-approve

# Force deploy (overwrite remote changes)
databricks bundle deploy -t dev --force

# Run specific job
databricks bundle run -t dev <job_name>

# Start an app after deployment
databricks bundle run -t dev <app_resource_key>

# View app logs for debugging
databricks apps logs <app-name> --profile <profile-name>

# Deploy to production
databricks bundle deploy -t prod

# Destroy all resources (cleanup)
databricks bundle destroy -t dev
databricks bundle destroy -t dev --auto-approve
```

## References

### Official Documentation
- [Databricks Asset Bundles](https://docs.databricks.com/aws/en/dev-tools/bundles/)
- [Bundle Resources Reference](https://docs.databricks.com/aws/en/dev-tools/bundles/resources)
- [Serverless Job Example](https://github.com/databricks/bundle-examples/blob/main/knowledge_base/serverless_job/resources/serverless_job.yml)
- [DLT Pipeline Example](https://github.com/databricks/bundle-examples/blob/main/knowledge_base/pipeline_with_schema/resources/pipeline.yml)
