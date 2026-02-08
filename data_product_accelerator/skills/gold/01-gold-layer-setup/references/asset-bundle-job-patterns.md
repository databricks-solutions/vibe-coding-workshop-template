# Asset Bundle Job Patterns

Complete Databricks Asset Bundle job configurations for Gold layer deployment.

## Critical: Sync YAML Files

Add YAML files to the `sync` section of `databricks.yml` — without this, the setup script cannot find the schema files at runtime:

```yaml
# databricks.yml

sync:
  include:
    - src/**/*.py
    - sql/**/*.sql
    - gold_layer_design/yaml/**/*.yaml  # ← CRITICAL!
```

## Gold Setup Job

Two-task job: (1) Create tables from YAML, (2) Apply FK constraints after PKs exist.

```yaml
# resources/gold/gold_setup_job.yml

resources:
  jobs:
    gold_setup_job:
      name: "[${bundle.target}] {Project} Gold Layer - Setup"
      description: "Creates Gold layer tables from YAML schema definitions"

      # PyYAML dependency required
      environments:
        - environment_key: default
          spec:
            environment_version: "4"
            dependencies:
              - "pyyaml>=6.0"

      tasks:
        # Task 1: Create all tables from YAMLs
        - task_key: setup_all_tables
          environment_key: default
          notebook_task:
            notebook_path: ../../src/{project}_gold/setup_tables.py
            base_parameters:
              catalog: ${var.catalog}
              gold_schema: ${var.gold_schema}
              domain: all  # or specific domain
          timeout_seconds: 1800

        # Task 2: Add FK constraints (after PKs exist)
        - task_key: add_fk_constraints
          depends_on:
            - task_key: setup_all_tables
          environment_key: default
          notebook_task:
            notebook_path: ../../src/{project}_gold/add_fk_constraints.py
            base_parameters:
              catalog: ${var.catalog}
              gold_schema: ${var.gold_schema}
              domain: all

      email_notifications:
        on_failure:
          - data-engineering@company.com

      tags:
        environment: ${bundle.target}
        layer: gold
        job_type: setup
```

### Key Configuration Rules

| Rule | Correct | Wrong |
|------|---------|-------|
| Task type | `notebook_task` | `python_task` |
| Parameters | `base_parameters` (dict) | `parameters` (CLI-style) |
| FK dependency | `depends_on: [setup_all_tables]` | No dependency |
| PyYAML | In `environments.spec.dependencies` | Missing |

## Gold Merge Job

Periodic MERGE operations from Silver to Gold:

```yaml
# resources/gold/gold_merge_job.yml

resources:
  jobs:
    gold_merge_job:
      name: "[${bundle.target}] {Project} Gold Layer - MERGE Updates"
      description: "Periodic MERGE operations from Silver to Gold"

      tasks:
        - task_key: merge_gold_tables
          notebook_task:
            notebook_path: ../../src/{project}_gold/merge_gold_tables.py
            base_parameters:
              catalog: ${var.catalog}
              silver_schema: ${var.silver_schema}
              gold_schema: ${var.gold_schema}
          timeout_seconds: 3600

      # Schedule for periodic updates
      schedule:
        quartz_cron_expression: "0 0 3 * * ?"  # Daily at 3 AM
        timezone_id: "America/New_York"
        pause_status: PAUSED  # Enable manually or in prod

      email_notifications:
        on_failure:
          - data-engineering@company.com

      tags:
        environment: ${bundle.target}
        layer: gold
        job_type: pipeline
```

### Schedule Configuration

| Environment | `pause_status` | Schedule |
|-------------|---------------|----------|
| dev | `PAUSED` | Manual trigger only |
| staging | `PAUSED` | Manual trigger for testing |
| prod | `UNPAUSED` | Active cron schedule |

## Notebook Path Convention

Paths are relative to the `resources/` directory:

```
project_root/
├── resources/
│   └── gold/
│       ├── gold_setup_job.yml       # Job definitions here
│       └── gold_merge_job.yml
└── src/
    └── {project}_gold/
        ├── setup_tables.py          # ../../src/{project}_gold/setup_tables.py
        └── merge_gold_tables.py     # ../../src/{project}_gold/merge_gold_tables.py
```

## Tags Convention

All Gold layer jobs should include:

```yaml
tags:
  environment: ${bundle.target}  # dev, staging, prod
  layer: gold
  job_type: setup|pipeline       # setup for one-time, pipeline for recurring
```

## Related Skills

- `databricks-asset-bundles` — Complete DAB configuration patterns
