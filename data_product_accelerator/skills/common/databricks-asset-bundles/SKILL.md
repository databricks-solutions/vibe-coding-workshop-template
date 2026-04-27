---
name: databricks-asset-bundles
description: Standard patterns for Databricks Asset Bundles configuration files for serverless jobs, DLT pipelines, dashboards, alerts, apps, and workflows. Use when creating, configuring, or deploying DABs for infrastructure-as-code deployments. Covers mandatory serverless environment configuration, hierarchical job architecture (atomic/composite/orchestrator), DLT pipeline patterns, dashboard resources with dataset_catalog/dataset_schema, SQL Alerts v2 API schema, Apps lifecycle, Python notebook parameter passing (dbutils.widgets.get vs argparse), deployment error prevention, and pre-deployment validation.
metadata:
  author: prashanth subrahmanyam
  version: "3.0"
  domain: infrastructure
  role: shared
  used_by_stages: [1, 2, 3, 4, 5, 6, 7, 8, 9]
  last_verified: "2026-04-16"
  volatility: medium
  upstream_sources:
    - name: "ai-dev-kit"
      repo: "databricks-solutions/ai-dev-kit"
      paths:
        - "databricks-skills/databricks-asset-bundles/SKILL.md"
      relationship: "extended"
      last_synced: "2026-02-19"
      sync_commit: "97a3637"
    - name: "databricks-agent-skills/databricks-dabs"
      repo: "databricks/databricks-agent-skills"
      paths:
        - "skills/databricks-dabs/SKILL.md"
      relationship: "extended"
      last_synced: "2026-04-27"
      sync_commit: "manifest-v2-2026-04-22"
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

### 🔴 MANDATORY: Notebook Source Format

**Python files executed via `notebook_task` MUST use Databricks notebook source format:**

```python
# Databricks notebook source

# COMMAND ----------

catalog = dbutils.widgets.get("catalog")

# COMMAND ----------

spark.sql(f"USE CATALOG {catalog}")
```

**Rules:**
- First line: `# Databricks notebook source`
- Cell separator: `# COMMAND ----------` (exactly 10 dashes)
- Markdown cells: prefix each line with `# MAGIC %md`
- Missing separators → all code runs as a single cell (silent failure)
- **NEVER mix Python code with `# MAGIC %md` in the same cell** — the entire cell renders as markdown and Python is silently ignored
- Common failure: `NameError: name 'xxx' is not defined` — caused by placing `import` or assignments in a `# MAGIC %md` cell. Fix: insert `# COMMAND ----------` between the markdown cell and the code cell

See [Notebook Source Format](references/notebook-source-format.md) for complete reference with examples.

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

## Shared Workspace Naming (Multi-User Environments)

In shared workspaces (workshops, demos), pipeline and job names MUST include a user identifier to prevent name collisions:

```yaml
variables:
  user_prefix:
    description: "User identifier for shared workspaces"
    default: ${workspace.current_user.short_name}

resources:
  pipelines:
    silver_pipeline:
      name: "[${bundle.target} ${var.user_prefix}] Silver Pipeline"
  jobs:
    gold_merge_job:
      name: "[${bundle.target} ${var.user_prefix}] Gold Merge"
```

**Rule:** Always include `${var.user_prefix}` in resource names when deploying to shared workspaces. Without it, the second user to deploy will hit a name conflict that `--force` cannot resolve.

## Profile & Workspace Resolution

Before creating a new bundle or editing `databricks.yml`, check for existing configuration:

1. **Check for existing `databricks.yml`:** If the repo already has one, inherit its `host`/`profile`/`workspace` settings
2. **Check active profile:** Run `databricks auth profiles` — use the profile matching the target workspace
3. **Never hardcode host URLs** — use named profiles or the `DATABRICKS_CONFIG_PROFILE` environment variable

**Gotcha:** When a repo already has a `databricks.yml` pointing to workspace A, and you create a new bundle targeting workspace B, the deploy may silently go to workspace A if you don't override the profile.

## ⚠️ Pitfall: Editing locally, running without redeploying

**Symptom:** You edit a notebook / Python file / SQL script locally, then run `databricks bundle run -t dev <job>` and the job executes the **old** code. You debug for 30 minutes thinking your fix didn't work.

**Root cause:** `bundle run` does NOT sync files. It only triggers the workspace-deployed copy from the **last** `bundle deploy`. Local edits are invisible until you re-run `bundle deploy`.

| Flow | Executes the local edit? |
|---|---|
| `bundle deploy` → `bundle run` | ✅ Yes |
| `bundle run` (after local edit, no deploy) | ❌ No — runs stale workspace copy |
| Clicking "Run" in the Databricks UI on a workspace job | ❌ No — same stale copy |
| Running a workspace notebook interactively via the browser | ❌ No — runs the deployed notebook file |

**Rule:** Every code edit → re-run `bundle deploy` → then `bundle run`. If you are in a tight iteration loop, chain them: `databricks bundle deploy -t dev && databricks bundle run -t dev <job>`.

**Corollary — never hotfix in the Databricks workspace:** Any edit made directly to a file under `/Workspace/.bundle/<target>/files/` is destroyed on the next `bundle deploy`. If you find yourself fixing a bug in the workspace UI, STOP and apply the same fix to the local source — then deploy.

## ⚠️ Pitfall: `--var` at run time does NOT override deploy-time-baked values

`bundle run -t <target> --var="name=value"` is commonly assumed to "override the variable for this run". It does not. Asset Bundle variables are resolved at **deploy time** — the substituted values are baked into the workspace copy of the job YAML, notebooks, and task parameters. At run time, `--var` is consulted only for variables that the task explicitly references *at run time* (e.g. a `notebook_task.base_parameters` expression that reads a variable through `${var.x}` and is NOT pre-rendered by the bundle engine).

**In practice, this means:**

- `warehouse_id: ${var.warehouse_id}` in a `sql_task` is substituted at `bundle deploy`. A subsequent `--var="warehouse_id=..."` at `bundle run` has NO effect. You must re-run `bundle deploy` with the new value.
- `--var` is genuinely useful for trigger-style knobs that a task reads at run time (e.g. a notebook that calls `dbutils.widgets.get("run_mode")`). Those are bound at run time.

**Rule of thumb:** If a variable appears inside a `${var.X}` expression in `databricks.yml` or a resource YAML, treat it as deploy-time-baked. Any change requires a redeploy. When in doubt, redeploy.

The canonical deploy-time-baked variables across the accelerator are:

| Variable | Used by | When it's baked |
|---|---|---|
| `warehouse_id` | `sql_task.warehouse_id`, dashboard queries, Genie Space `semantic_warehouse_id` | `bundle deploy` |
| `catalog`, `gold_schema`, `feature_schema` | SQL parameter substitution across jobs | `bundle deploy` |
| `notification_email` | `email_notifications.on_failure` | `bundle deploy` |

See `semantic-layer/04-genie-space-export-import-api/SKILL.md` §Required `serialized_space` Invariants **and** §`semantic_warehouse_id` MUST be baked at deploy time for the Genie-specific consequence of this rule. Summary: the Genie POST body embeds a concrete 16+ hex warehouse id that the Genie runtime stores verbatim; a `${var.warehouse_id}` placeholder that slips through produces a space that is created successfully but fails every query with "warehouse not found". Pre-flight `_assert_sql_arrays` catches this and halts before the POST — do not work around it at run time.

## ⚠️ Resource Lifecycle Warning

**Removing a resource block from `databricks.yml` triggers Terraform DESTROY of the live resource.**

This applies to ALL managed resources: jobs, pipelines, apps, `postgres_projects`, volumes.

- **NEVER** remove `postgres_projects` or `apps` blocks between deployments
- **NEVER** remove a resource block "because it already exists" — the bundle manages its lifecycle
- If unsure, add resources incrementally; never subtract

See [Error 15](references/common-errors.md) in Common Errors for recovery steps.

## Reference Files

- **[Configuration Guide](references/configuration-guide.md)**: Complete YAML configuration patterns, environment setup, variables (with warehouse_id lookup), targets, DLT pipelines (with glob libraries), dashboards (dataset_catalog/dataset_schema), SQL Alerts v2, volumes (grants not permissions), Apps, schedules, notifications, permissions, library dependencies
- **[Job Patterns](references/job-patterns.md)**: Hierarchical job architecture (atomic/composite/orchestrator), task types, parameter passing (dbutils.widgets.get vs argparse), orchestrator patterns, SQL tasks, multi-task dependencies
- **[Common Errors](references/common-errors.md)**: Anti-patterns, deployment error prevention (17 common errors including Terraform destroy on resource removal, Lakebase soft-delete, --force limitations, dashboard hardcoded catalog, alert v2 schema mismatch, volume permissions, app env vars), troubleshooting guide, validation checklist, pre-deployment validation script
- **[Notebook Source Format](references/notebook-source-format.md)**: Databricks notebook source format (`# Databricks notebook source`, `# COMMAND ----------` cell separators, `# MAGIC %md`). Read when creating or debugging notebooks executed via `notebook_task`

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
- [ ] Notebooks start with `# Databricks notebook source` and use `# COMMAND ----------` separators
- [ ] `base_parameters` includes ALL `dbutils.widgets.get()` params used in the notebook
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
- [ ] Check for existing pipeline/job names in workspace before first deploy
- [ ] Re-read `databricks.yml` before editing (avoid stale reads in long sessions)
- [ ] No resource blocks were removed (removal = Terraform destroy)
- [ ] Run pre-deployment validation script
- [ ] `databricks bundle validate` passes

## Emit Deploy Checkpoint (MANDATORY — run immediately after `bundle validate`)

`databricks bundle validate` emits JSON on stdout (`--output json`) that names **every** resolved job, task, variable, warehouse id, and workspace path that the upcoming `bundle deploy` will act on. Capture this into `plans/deploy-checkpoint.md` BEFORE running `bundle deploy` so downstream prompts and verification steps can reference concrete per-project names instead of template placeholders.

**Why this matters (retrospective action S13):** Every deploy cycle that fails without a checkpoint re-derives the same job / MV / TVF / warehouse id mapping from scratch. That re-derivation is the #1 source of "wrong job run", "wrong warehouse", and "verification ran against stale name" mistakes across the workshop.

### The checkpoint contract

`plans/deploy-checkpoint.md` is a plain Markdown file with a fixed shape, so orchestrators (e.g. prompts `sections/24-deploy_di_assets.md`) can parse it mechanically.

```markdown
# Deploy Checkpoint — <target> — <UTC timestamp>

## Resolved variables

| Variable | Value |
|---|---|
| `catalog` | `{lakehouse_default_catalog}` |
| `gold_schema` | `{user_schema_prefix}_gold` |
| `warehouse_id` | `0a1b2c3d4e5f6789` |
| `notification_email` | `ops@example.com` |

## Jobs (deploy order)

| # | Job key | Resolved name | Tasks |
|---|---|---|---|
| 1 | `metric_views_job` | `dev-{user_schema_prefix}-metric-views` | `create_metric_views` |
| 2 | `tvfs_job` | `dev-{user_schema_prefix}-tvfs` | `create_table_valued_functions` |
| 3 | `genie_spaces_job` | `dev-{user_schema_prefix}-genie-spaces` | `deploy_spaces` |
| 4 | `dashboards_job` | `dev-{user_schema_prefix}-dashboards` | `deploy_dashboards` |

## Metric Views, TVFs, Genie Spaces, Dashboards

| Asset type | Fully-qualified name | Source file |
|---|---|---|
| metric_view | `<catalog>.<schema>.revenue_analytics_metrics` | `src/semantic/metric_views/revenue_analytics_metrics.yaml` |
| tvf         | `<catalog>.<schema>.get_top_properties_by_revenue` | `src/semantic/tvfs/table_valued_functions.sql` |
| genie_space | `spaces/<uuid4-hex>` (title: "Revenue Analytics") | `src/genie_spaces/revenue_analytics.json` |
| dashboard   | `/Shared/dashboards/revenue_overview.lvdash.json` | `src/dashboards/revenue_overview.lvdash.json` |

## Commands to run (in order)

```bash
databricks bundle deploy -t <target>
databricks bundle run -t <target> metric_views_job
databricks bundle run -t <target> tvfs_job
databricks bundle run -t <target> genie_spaces_job
databricks bundle run -t <target> dashboards_job
```
```

### Emit script

Run this **every time** before `bundle deploy`. It is idempotent — re-running simply overwrites the checkpoint with the latest resolution.

```bash
#!/usr/bin/env bash
# scripts/emit_deploy_checkpoint.sh <target>
set -euo pipefail
target="${1:-dev}"

mkdir -p plans
checkpoint="plans/deploy-checkpoint.md"

validate_json="$(databricks bundle validate -t "$target" --output json)"

python - "$target" "$validate_json" <<'PY' > "$checkpoint"
import json, sys, datetime
target, raw = sys.argv[1], sys.argv[2]
data = json.loads(raw)

jobs = data.get("resources", {}).get("jobs", {}) or {}
variables = data.get("variables", {}) or {}

print(f"# Deploy Checkpoint — {target} — {datetime.datetime.utcnow().isoformat()}Z\n")

print("## Resolved variables\n")
print("| Variable | Value |\n|---|---|")
for k, v in sorted(variables.items()):
    val = v.get("value") if isinstance(v, dict) else v
    print(f"| `{k}` | `{val}` |")
print()

print("## Jobs (deploy order)\n")
print("| # | Job key | Resolved name | Tasks |\n|---|---|---|---|")
for i, (key, job) in enumerate(sorted(jobs.items()), start=1):
    name = job.get("name", "")
    tasks = ", ".join(t.get("task_key", "") for t in job.get("tasks", []) or [])
    print(f"| {i} | `{key}` | `{name}` | {tasks} |")
print()

print("## Commands to run (in order)\n")
print("```bash")
print(f"databricks bundle deploy -t {target}")
for key in sorted(jobs):
    print(f"databricks bundle run -t {target} {key}")
print("```")
PY

echo "✓ Wrote $checkpoint"
```

### Skill / prompt contract

- **Skills** never hard-code concrete job names, Metric View names, or warehouse ids. They keep template-variable substitution (`{lakehouse_default_catalog}`, `{user_schema_prefix}_gold`, `${var.warehouse_id}`) intact.
- **Prompts** that need to reference a concrete name (e.g. `sections/24-deploy_di_assets.md`) defer to the **Metric Views / TVFs / Genie Spaces / Dashboards** and **Jobs** tables in `plans/deploy-checkpoint.md` for the per-project values. The prompt continues to render with template variables; the agent reads the checkpoint at execution time.
- Downstream orchestrators (per-task verification in `semantic-layer/00-semantic-layer-setup/SKILL.md`) quote the job keys and asset names from this file, not from memory.

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
