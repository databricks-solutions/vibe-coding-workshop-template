---
name: gold-layer-setup
description: End-to-end orchestrator for implementing Gold layer tables, merge scripts, FK constraints, and Asset Bundle jobs from YAML schema definitions. Guides users through YAML-driven table creation, Silver-to-Gold MERGE operations (SCD Type 1/2 dimensions, aggregated/transaction facts), foreign key constraint application, Asset Bundle job configuration, and post-deployment validation. Orchestrates mandatory dependencies on Gold skills (yaml-driven-gold-setup, gold-layer-schema-validation, gold-layer-merge-patterns, gold-layer-documentation, gold-delta-merge-deduplication, fact-table-grain-validation, mermaid-erd-patterns) and common skills (databricks-asset-bundles, databricks-table-properties, databricks-python-imports, schema-management-patterns, unity-catalog-constraints, databricks-expert-agent). Use when implementing Gold layer from YAML designs, creating table setup scripts, writing merge scripts, deploying Gold layer jobs, or troubleshooting Gold layer implementation errors.
license: Apache-2.0
metadata:
  author: prashanth subrahmanyam
  version: "2.0.0"
  domain: gold
  role: orchestrator
  pipeline_stage: 4
  pipeline_stage_name: gold-implementation
  next_stages:
    - project-planning
  workers:
    - yaml-driven-gold-setup
    - gold-layer-schema-validation
    - gold-layer-merge-patterns
    - gold-layer-documentation
    - gold-delta-merge-deduplication
    - fact-table-grain-validation
    - mermaid-erd-patterns
  common_dependencies:
    - databricks-asset-bundles
    - databricks-table-properties
    - databricks-python-imports
    - schema-management-patterns
    - unity-catalog-constraints
    - databricks-expert-agent
    - naming-tagging-standards
    - databricks-autonomous-operations
  dependencies:
    - yaml-driven-gold-setup
    - gold-layer-schema-validation
    - gold-layer-merge-patterns
    - gold-layer-documentation
    - gold-delta-merge-deduplication
    - fact-table-grain-validation
    - mermaid-erd-patterns
    - databricks-asset-bundles
    - databricks-table-properties
    - databricks-python-imports
    - schema-management-patterns
    - unity-catalog-constraints
    - databricks-expert-agent
  last_verified: "2026-02-07"
  volatility: low
---

# Gold Layer Implementation Orchestrator

This skill orchestrates the complete Gold layer implementation process, transforming YAML schema designs into production-ready Delta tables with merge scripts, FK constraints, and Asset Bundle jobs. It is the natural successor to the `gold/00-gold-layer-design` skill.

**Predecessor:** `gold/00-gold-layer-design` skill (YAML files must exist before using this skill)

**Core Philosophy:** YAML as Single Source of Truth — Python reads YAML at runtime, DDL is generated dynamically, schema changes require YAML edits only.

## When to Use This Skill

- Implementing Gold layer tables from completed YAML designs
- Creating generic YAML-driven table setup scripts
- Writing Silver-to-Gold MERGE scripts (dimensions and facts)
- Applying FK constraints after table creation
- Configuring Asset Bundle jobs for Gold layer deployment
- Troubleshooting Gold layer implementation errors (duplicate keys, schema mismatches, grain violations)

## Prerequisites

**MANDATORY:** Complete `gold/00-gold-layer-design` skill first. The following must exist:
- [ ] YAML schema files in `gold_layer_design/yaml/{domain}/*.yaml`
- [ ] ERD documentation (`erd_master.md`)
- [ ] Column lineage documentation (`COLUMN_LINEAGE.csv`)

## Critical Dependencies (Read at Indicated Phase)

### Gold-Domain Skills

| Skill | Read At | Purpose |
|-------|---------|---------|
| `yaml-driven-gold-setup` | Phase 1 | YAML-to-DDL patterns, setup script structure |
| `gold-layer-documentation` | Phase 1 | Dual-purpose descriptions, table properties |
| `gold-layer-merge-patterns` | Phase 2 | SCD Type 1/2, fact aggregation, column mapping |
| `gold-delta-merge-deduplication` | Phase 2 | Deduplication before MERGE (mandatory) |
| `fact-table-grain-validation` | Phase 2 | Grain inference from PK, pre-merge validation |
| `gold-layer-schema-validation` | Phase 2 | DataFrame-to-DDL schema validation |
| `mermaid-erd-patterns` | Phase 5 | Cross-reference created tables against ERD |

### Common Skills

| Skill | Read At | Purpose |
|-------|---------|---------|
| `databricks-asset-bundles` | Phase 3 | Job YAML patterns, serverless config, sync |
| `databricks-table-properties` | Phase 1 | Standard TBLPROPERTIES by layer |
| `unity-catalog-constraints` | Phase 1 | PK/FK constraint application patterns |
| `schema-management-patterns` | Phase 1 | CREATE SCHEMA IF NOT EXISTS |
| `databricks-python-imports` | Phase 2 | Pure Python modules, avoid sys.path issues |
| `databricks-expert-agent` | All | Schema extraction over generation principle |
| `databricks-autonomous-operations` | Phase 4+ | Deploy → Poll → Diagnose → Fix → Redeploy loop when jobs fail |

### 🔴 Non-Negotiable Defaults (Applied to EVERY Gold Table and Job)

These defaults are ALWAYS applied. There are NO exceptions, NO overrides, NO alternative options.

| Default | Value | Applied Where | NEVER Do This Instead |
|---------|-------|---------------|----------------------|
| **Serverless** | `environments:` block with `environment_key` | Every job YAML | ❌ NEVER define `job_clusters:` or `existing_cluster_id:` |
| **Environments V4** | `environment_version: "4"` | Every job's `environments.spec` | ❌ NEVER omit or use older versions |
| **Auto Liquid Clustering** | `CLUSTER BY AUTO` | Every `CREATE TABLE` in `setup_tables.py` | ❌ NEVER use `CLUSTER BY (col1, col2)` or `PARTITIONED BY` |
| **Change Data Feed** | `'delta.enableChangeDataFeed' = 'true'` | Every table's TBLPROPERTIES | ❌ NEVER omit (required for incremental propagation) |
| **Row Tracking** | `'delta.enableRowTracking' = 'true'` | Every table's TBLPROPERTIES | ❌ NEVER omit (breaks downstream MV refresh) |
| **notebook_task** | `notebook_task:` with `base_parameters:` | Every task in job YAML | ❌ NEVER use `python_task:` or CLI-style `parameters:` |

```sql
-- ✅ CORRECT: Every Gold table DDL MUST include
CREATE OR REPLACE TABLE {catalog}.{schema}.{table_name} (
    ...
)
USING DELTA
CLUSTER BY AUTO          -- 🔴 MANDATORY
TBLPROPERTIES (
    'delta.enableChangeDataFeed' = 'true',     -- 🔴 MANDATORY
    'delta.enableRowTracking' = 'true',        -- 🔴 MANDATORY
    'delta.autoOptimize.autoCompact' = 'true',
    'delta.autoOptimize.optimizeWrite' = 'true',
    'layer' = 'gold'
)
```

```yaml
# ✅ CORRECT: Every Gold job MUST include
environments:
  - environment_key: "default"
    spec:
      environment_version: "4"   # 🔴 MANDATORY
tasks:
  - task_key: setup_tables
    environment_key: default     # 🔴 MANDATORY on every task
    notebook_task:               # 🔴 MANDATORY (never python_task)
      notebook_path: ../src/setup_tables.py
      base_parameters:           # 🔴 MANDATORY (never CLI-style parameters)
        catalog: ${var.catalog}
```

### 🔴 YAML Extraction Over Generation (Merge Scripts Included)

**EVERY value below MUST be extracted from Gold YAML files or COLUMN_LINEAGE.csv. NEVER generate, guess, or hardcode.**

The `gold/00-gold-layer-design` skill produces YAML schemas in `gold_layer_design/yaml/{domain}/*.yaml` and lineage in `COLUMN_LINEAGE.csv`. These are the **single source of truth** for ALL implementation code — including merge scripts.

| What to Extract | YAML Location | Used In | ❌ NEVER Do This |
|----------------|---------------|---------|------------------|
| **Gold table name** | `table_name:` | Merge target, DDL | ❌ NEVER hardcode `"dim_store"` or `"fact_sales_daily"` |
| **Gold column names** | `columns[].name` | `.select()` list, `whenMatchedUpdate` | ❌ NEVER type column names from memory |
| **Column types** | `columns[].type` | Schema validation, cast operations | ❌ NEVER guess types |
| **Primary key columns** | `primary_key.columns[]` | MERGE condition, grain validation | ❌ NEVER hardcode MERGE ON clause |
| **Business key** | `business_key.columns[]` | Deduplication key | ❌ NEVER hardcode `.dropDuplicates(["store_number"])` |
| **Foreign keys** | `foreign_keys[]` | FK constraints, dimension ordering | ❌ NEVER hardcode FK references |
| **SCD type** | `table_properties.scd_type` | SCD1 vs SCD2 merge pattern | ❌ NEVER assume SCD type |
| **Grain type** | `table_properties.grain` | Transaction vs aggregated merge | ❌ NEVER assume grain |
| **Source Silver table** | `lineage.source_table` or `COLUMN_LINEAGE.csv` | Silver source reference | ❌ NEVER guess Silver table names |
| **Column mappings** | `columns[].lineage.source_column` or `COLUMN_LINEAGE.csv` | `.withColumn("gold", col("silver"))` renames | ❌ NEVER guess Silver→Gold renames |
| **Domain** | `domain:` or directory name | Domain-ordered processing | ❌ NEVER hardcode domain lists |

**Extraction Pattern for Merge Scripts:**

```python
# ✅ CORRECT: Extract metadata from YAML BEFORE writing merge logic
import yaml
from pathlib import Path

def load_table_metadata(yaml_path: Path) -> dict:
    """Extract ALL merge-relevant metadata from a single YAML file."""
    with open(yaml_path) as f:
        config = yaml.safe_load(f)
    return {
        "table_name": config["table_name"],
        "columns": [c["name"] for c in config.get("columns", [])],
        "column_types": {c["name"]: c["type"] for c in config.get("columns", [])},
        "pk_columns": config.get("primary_key", {}).get("columns", []),
        "business_key": config.get("business_key", {}).get("columns", []),
        "foreign_keys": config.get("foreign_keys", []),
        "scd_type": config.get("table_properties", {}).get("scd_type", ""),
        "grain": config.get("table_properties", {}).get("grain", ""),
        "entity_type": config.get("table_properties", {}).get("entity_type", ""),
        "lineage": {
            c["name"]: c.get("lineage", {})
            for c in config.get("columns", [])
            if c.get("lineage")
        },
    }

# ✅ CORRECT: Use extracted metadata to build merge logic
meta = load_table_metadata(Path("gold_layer_design/yaml/sales/fact_sales_daily.yaml"))
pk_columns = meta["pk_columns"]          # → ["store_number", "upc_code", "transaction_date"]
gold_columns = meta["columns"]           # → ["store_number", "upc_code", ..., "net_revenue"]
merge_condition = " AND ".join(          # → "target.store_number = source.store_number AND ..."
    f"target.{c} = source.{c}" for c in pk_columns
)
```

```python
# ❌ WRONG: Hardcoding values that exist in YAML
gold_table = "fact_sales_daily"                              # ❌ Hardcoded
merge_condition = "target.store_number = source.store_number # ❌ Hardcoded
    AND target.upc_code = source.upc_code"
select_cols = ["store_number", "upc_code", "net_revenue"]    # ❌ Hardcoded
```

**Column Mapping Extraction from COLUMN_LINEAGE.csv:**

```python
import csv

def load_column_mappings(lineage_csv: Path, gold_table: str) -> dict:
    """Extract Silver→Gold column mappings from design-phase lineage CSV."""
    mappings = {}
    with open(lineage_csv) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["gold_table"] == gold_table:
                silver_col = row["silver_column"]
                gold_col = row["gold_column"]
                if silver_col != gold_col:
                    mappings[gold_col] = silver_col  # gold_name: silver_source
    return mappings

# ✅ CORRECT: Apply extracted mappings
mappings = load_column_mappings(Path("gold_layer_design/COLUMN_LINEAGE.csv"), "dim_store")
for gold_col, silver_col in mappings.items():
    df = df.withColumn(gold_col, col(silver_col))
```

**What CAN be coded (not extracted):**
- Aggregation expressions (business logic: `spark_sum(when(...))`)
- Derived column formulas (business rules: `when(col("close_date").isNotNull(), "Closed")`)
- SCD Type 2 column generation (`md5(concat_ws(...))`)
- Timestamp columns (`current_timestamp()`)

## Quick Start (3-4 hours)

### What You'll Create

1. `setup_tables.py` — Generic script reads YAML, creates all tables dynamically
2. `add_fk_constraints.py` — Apply FK constraints AFTER all PKs exist
3. `merge_gold_tables.py` — Merge Silver to Gold with explicit column mapping
4. `gold_setup_job.yml` — Asset Bundle job for table setup + FK constraints
5. `gold_merge_job.yml` — Asset Bundle job for periodic MERGE operations

### Deliverables Checklist

**Setup Scripts:**
- [ ] `src/{project}_gold/setup_tables.py` — Generic YAML-driven table creation
- [ ] `src/{project}_gold/add_fk_constraints.py` — FK constraint application
- [ ] Verify: `databricks bundle run gold_setup_job -t dev`

**Merge Scripts:**
- [ ] `src/{project}_gold/merge_gold_tables.py` — Silver-to-Gold MERGE
- [ ] Dimension merges (SCD Type 1 or 2) with deduplication
- [ ] Fact merges with aggregation and grain validation
- [ ] Verify: `databricks bundle run gold_merge_job -t dev`

**Asset Bundle Jobs:**
- [ ] `resources/gold/gold_setup_job.yml` — Setup + FK constraints (two tasks)
- [ ] `resources/gold/gold_merge_job.yml` — Periodic merge with schedule
- [ ] YAML files synced in `databricks.yml`

### Fast Track

```bash
# 1. Deploy setup job (creates tables from YAML)
databricks bundle deploy -t dev
databricks bundle run gold_setup_job -t dev

# 2. Verify tables created
# SHOW TABLES IN {catalog}.{gold_schema}

# 3. Run merge job (Silver to Gold)
databricks bundle run gold_merge_job -t dev
```

---

## Step-by-Step Workflow

### Phase 1: YAML-Driven Table Creation (30 min)

**MANDATORY: Read each skill below using the Read tool BEFORE writing any code for this phase:**

1. `skills/gold/yaml-driven-gold-setup/SKILL.md` — YAML-to-DDL patterns, `find_yaml_base()`, `build_create_table_ddl()`
2. `skills/gold/gold-layer-documentation/SKILL.md` — Dual-purpose column descriptions, naming conventions
3. `skills/common/databricks-table-properties/SKILL.md` — Standard TBLPROPERTIES by layer
4. `skills/common/unity-catalog-constraints/SKILL.md` — PK/FK `ALTER TABLE` patterns, NOT NULL requirements
5. `skills/common/schema-management-patterns/SKILL.md` — `CREATE SCHEMA IF NOT EXISTS` pattern

**Activities:**
1. Create `setup_tables.py` — Single generic script reads ALL YAML files, creates tables
2. Create `add_fk_constraints.py` — Applies FK constraints AFTER all PKs exist
3. Define standard table properties (CDF, row tracking, auto-optimize, layer=gold)
4. Handle schema creation with `CREATE SCHEMA IF NOT EXISTS`
5. Enable Predictive Optimization on Gold schema

**Key Implementation Rules:**
- FK constraints via `ALTER TABLE` AFTER all PKs exist (never inline in CREATE TABLE)
- PK columns must be NOT NULL in YAML
- Use `CREATE OR REPLACE TABLE` for idempotent setup
- Include error handling with try/except for constraint application
- YAML directory discovery pattern (`find_yaml_base()`)
- PyYAML dependency in job environment

**Output:** `src/{project}_gold/setup_tables.py` and `src/{project}_gold/add_fk_constraints.py`

See `references/setup-script-patterns.md` for complete implementation patterns.
See `references/fk-constraint-patterns.md` for FK constraint details.
See `scripts/setup_tables_template.py` for starter template.
See `scripts/add_fk_constraints_template.py` for starter template.

---

### Phase 2: MERGE Script Implementation (2 hours)

**MANDATORY: Read each skill below using the Read tool BEFORE writing any merge code:**

1. `skills/gold/gold-layer-merge-patterns/SKILL.md` — SCD Type 1/2, fact aggregation, column mapping, `spark_sum` alias
2. `skills/gold/gold-delta-merge-deduplication/SKILL.md` — Deduplication before MERGE (ALWAYS required, prevents `DELTA_MULTIPLE_SOURCE_ROW_MATCHING_TARGET_ROW_IN_MERGE`)
3. `skills/gold/fact-table-grain-validation/SKILL.md` — Grain inference from PK, transaction vs aggregated patterns
4. `skills/gold/gold-layer-schema-validation/SKILL.md` — `validate_merge_schema()`, DataFrame-to-DDL checks
5. `skills/common/databricks-python-imports/SKILL.md` — Pure Python modules, avoid `sys.path` issues in serverless

**Activities:**

**Step 0 — EXTRACTION FIRST (before writing ANY code):**
1. Load ALL Gold YAML files using `load_table_metadata()` (see YAML Extraction section above)
2. Load `COLUMN_LINEAGE.csv` using `load_column_mappings()` for Silver→Gold renames
3. For each table: extract `table_name`, `pk_columns`, `business_key`, `scd_type`, `grain`, `columns`, `lineage`
4. Build a table inventory dict keyed by table name — this drives ALL merge functions
5. Verify Silver source tables exist: `spark.table(silver_table)` before coding any merge logic

**Step 1 — Create merge functions using extracted metadata:**
1. Create `merge_gold_tables.py` with separate functions per table
2. Implement dimension merges (SCD Type 1 or Type 2 — read `scd_type` from YAML)
3. Implement fact merges (aggregation to match grain — read `grain` from YAML)
4. Add deduplication before every MERGE (MANDATORY — use `business_key` from YAML)
5. Add explicit column mapping (use `lineage.source_column` from YAML or `COLUMN_LINEAGE.csv`)
6. Add schema validation before merge (compare DataFrame columns against YAML `columns[]`)
7. Add grain validation for fact tables (use `pk_columns` from YAML)
8. Merge dimensions FIRST, then facts (dependency order from YAML `foreign_keys`)

**For Each Dimension Table:**

1. **Extract metadata** — `meta = load_table_metadata(yaml_path)` → get `business_key`, `scd_type`, `columns`
2. **Deduplicate** — `.orderBy(col("processed_timestamp").desc()).dropDuplicates(meta["business_key"])` (from YAML)
3. **Map columns** — Loop over `load_column_mappings()` results: `.withColumn(gold_col, col(silver_col))`
4. **Generate surrogate key** — `md5(concat_ws("||", ...))` using columns from YAML `primary_key`
5. **Add SCD columns** — `effective_from`, `effective_to`, `is_current` (only if `scd_type == "scd2"`)
6. **Select explicitly** — `.select(meta["columns"])` — column list FROM YAML, not typed by hand
7. **Validate schema** — Compare DataFrame columns against `meta["columns"]`
8. **Build MERGE condition** — `" AND ".join(f"target.{c} = source.{c}" for c in meta["business_key"])` (from YAML)

**For Each Fact Table:**

1. **Extract metadata** — `meta = load_table_metadata(yaml_path)` → get `pk_columns`, `grain`, `columns`
2. **Infer grain** — Read `grain` from YAML (or infer: composite PK = aggregated, single PK = transaction)
3. **Aggregate** — `.groupBy(meta["pk_columns"]).agg(...)` — grain columns FROM YAML
4. **Validate grain** — Verify one row per `meta["pk_columns"]` combination
5. **Map columns** — Loop over `load_column_mappings()` results
6. **Select explicitly** — `.select(meta["columns"])` — column list FROM YAML
7. **Validate schema** — Compare DataFrame columns against `meta["columns"]`
8. **Build MERGE condition** — `" AND ".join(f"target.{c} = source.{c}" for c in meta["pk_columns"])` (from YAML)

**Critical Rules (from dependency skills):**
- ALWAYS deduplicate Silver before MERGE (prevents `DELTA_MULTIPLE_SOURCE_ROW_MATCHING_TARGET_ROW_IN_MERGE`)
- Deduplication key MUST match MERGE condition key
- Use `spark_sum` not `sum` (avoid shadowing Python builtins)
- Never name variables `count`, `sum`, `min`, `max` (shadows PySpark functions)
- Cast `DATE_TRUNC` results to DATE type
- Inline helper functions or use pure Python modules (not notebook imports)

**Output:** `src/{project}_gold/merge_gold_tables.py`

See `references/merge-script-patterns.md` for complete SCD1/SCD2/fact patterns.
See `scripts/merge_gold_tables_template.py` for starter template.

---

### Phase 3: Asset Bundle Configuration (30 min)

**MANDATORY: Read this skill using the Read tool BEFORE creating job YAML files:**

1. `skills/common/databricks-asset-bundles/SKILL.md` — Job YAML patterns, serverless config, `notebook_task` vs `python_task`, `base_parameters`, sync

**Activities:**
1. Add YAML sync to `databricks.yml` — `gold_layer_design/yaml/**/*.yaml`
2. Create `gold_setup_job.yml` with two tasks (setup tables then add FK constraints)
3. Create `gold_merge_job.yml` with scheduled merge execution
4. Add PyYAML dependency to job environment
5. Configure serverless environment
6. Add tags (environment, layer, job_type)

**Critical Rules (from `databricks-asset-bundles`):**
- Use `notebook_task` not `python_task`
- Use `base_parameters` dict (not CLI-style `parameters`)
- PyYAML dependency: `pyyaml>=6.0` in environment spec
- YAML sync is CRITICAL — without it, `setup_tables.py` cannot find schemas
- FK task depends on setup task (`depends_on`)
- Merge job has optional schedule (PAUSED in dev, enabled in prod)

**Output:** Updated `databricks.yml`, `resources/gold/gold_setup_job.yml`, `resources/gold/gold_merge_job.yml`

See `references/asset-bundle-job-patterns.md` for complete job templates.
See `assets/templates/gold-setup-job-template.yml` and `assets/templates/gold-merge-job-template.yml`.

---

### Phase 4: Deployment and Testing (30 min)

**Activities:**
1. Deploy: `databricks bundle deploy -t dev`
2. Run setup job: `databricks bundle run gold_setup_job -t dev`
3. Verify tables created: `SHOW TABLES IN {catalog}.{gold_schema}`
4. Verify PKs: `SHOW CREATE TABLE {catalog}.{gold_schema}.{table}`
5. Verify FKs: `DESCRIBE TABLE EXTENDED {catalog}.{gold_schema}.{table}`
6. Run merge job: `databricks bundle run gold_merge_job -t dev`
7. Verify record counts, grain, FK relationships, SCD Type 2

See `references/validation-queries.md` for complete validation SQL.

---

### Phase 4b: Enable Anomaly Detection on Gold Schema (5 min)

**MANDATORY: Read this skill using the Read tool:**

1. `skills/monitoring/04-anomaly-detection/SKILL.md` — Schema-level freshness/completeness monitoring

**Why:** Every Gold schema should have anomaly detection enabled from day one. Gold tables are the primary consumer-facing layer — stale or incomplete data here directly impacts dashboards, Genie Spaces, and business decisions.

**Steps:**
1. Enable anomaly detection on the Gold schema after all tables are created
2. No exclusions needed — all Gold tables should be monitored

```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.dataquality import Monitor, AnomalyDetectionConfig

w = WorkspaceClient()

# Get Gold schema UUID
schema_info = w.schemas.get(full_name=f"{catalog}.{gold_schema}")
schema_id = schema_info.schema_id

# Enable anomaly detection on Gold schema (monitor ALL tables)
try:
    w.data_quality.create_monitor(
        monitor=Monitor(
            object_type="schema",
            object_id=schema_id,
            anomaly_detection_config=AnomalyDetectionConfig()
        )
    )
    print(f"✓ Anomaly detection enabled on {catalog}.{gold_schema}")
except Exception as e:
    if "already exists" in str(e).lower():
        print(f"✓ Already enabled (skipping)")
    else:
        print(f"⚠️ Non-blocking: {e}")
```

**Note:** This is non-blocking — if anomaly detection fails to enable, the Gold layer deployment continues. Retry later via `monitoring/04-anomaly-detection/scripts/enable_anomaly_detection.py`.

---

### Phase 5: Post-Implementation Validation (30 min)

**MANDATORY: Read this skill using the Read tool to cross-reference created tables against ERD:**

1. `skills/gold/mermaid-erd-patterns/SKILL.md` — Verify all ERD entities have corresponding tables, all relationships match FK constraints

**Activities:**
1. ERD cross-reference — Compare created tables against `erd_master.md` to confirm nothing was missed
2. Schema validation — DataFrame columns match DDL for all merge functions
3. Grain validation — No duplicate rows at PRIMARY KEY level
4. FK integrity — No orphaned foreign key references
5. SCD Type 2 — Exactly one `is_current = true` per business key
6. Data quality — Record counts, NULL checks, range validations
7. Audit timestamps — `record_created_timestamp` and `record_updated_timestamp` populated

See `references/validation-queries.md` for complete SQL queries.

---

## File Organization

```
project_root/
├── databricks.yml                              # Bundle config (sync YAMLs!)
├── gold_layer_design/
│   └── yaml/                                   # Source of Truth (from design phase)
│       └── {domain}/
│           └── {table}.yaml
├── src/
│   └── {project}_gold/
│       ├── setup_tables.py                     # Phase 1: Generic YAML-driven setup
│       ├── add_fk_constraints.py               # Phase 1: FK constraint application
│       └── merge_gold_tables.py                # Phase 2: Silver-to-Gold MERGE
└── resources/
    └── gold/
        ├── gold_setup_job.yml                  # Phase 3: Setup + FK job
        └── gold_merge_job.yml                  # Phase 3: Merge job
```

## Key Implementation Principles

1. **YAML as Source of Truth** — `setup_tables.py` AND `merge_gold_tables.py` both read YAML at runtime. Schema changes = YAML edits only. No embedded DDL strings, no hardcoded column lists.
2. **Extract, Don't Generate** — EVERY table name, column name, PK, FK, business key, grain type, SCD type, and column mapping MUST be extracted from Gold YAML or `COLUMN_LINEAGE.csv`. The ONLY things coded by hand are aggregation expressions and derived column formulas (business logic).
3. **Deduplication Always** — Every MERGE must deduplicate Silver first. No exceptions. Dedup key = `business_key` from YAML.
4. **Explicit Column Mapping from Lineage** — Never assume Silver names match Gold. Extract renames from YAML `lineage.source_column` or `COLUMN_LINEAGE.csv`.
5. **Schema Validation Before Merge** — Compare DataFrame columns against YAML `columns[]` list before every Delta MERGE.
6. **Grain Validation for Facts** — Read `grain` and `pk_columns` from YAML. Composite PK = aggregated. Single PK = transaction. Always validate before merge.
7. **FK Constraints After PKs** — Foreign keys in a SEPARATE script that reads `foreign_keys[]` from YAML. Runs AFTER all tables and their PKs exist.
8. **Merge Condition from PK** — Build MERGE ON clause programmatically from `primary_key.columns[]` in YAML. Never hardcode MERGE conditions.

## Common Issues Quick Reference

| Issue | Error | Solution | Skill Reference |
|-------|-------|----------|-----------------|
| YAML not found | `FileNotFoundError` | Add to `databricks.yml` sync | `databricks-asset-bundles` |
| PyYAML missing | `ModuleNotFoundError` | Add `pyyaml>=6.0` to environment | `databricks-asset-bundles` |
| Duplicate key MERGE | `DELTA_MULTIPLE_SOURCE_ROW_MATCHING_TARGET_ROW_IN_MERGE` | Deduplicate before merge | `gold-delta-merge-deduplication` |
| Column not found | `UNRESOLVED_COLUMN` | Add explicit column mapping | `gold-layer-schema-validation` |
| Grain duplicates | Multiple rows per PK | Fix aggregation to match PK | `fact-table-grain-validation` |
| Variable shadows function | `'int' object is not callable` | Rename variable (e.g., `count` to `record_count`) | `gold-layer-merge-patterns` |
| FK constraint fails | `Table/column not found` | Run FK script AFTER setup script | `unity-catalog-constraints` |

See `references/common-issues.md` for detailed solutions.

## Validation Checklist

### Setup Phase
- [ ] YAML files exist in `gold_layer_design/yaml/`
- [ ] YAML files synced in `databricks.yml`
- [ ] `setup_tables.py` reads YAML dynamically (no hardcoded DDL)
- [ ] PyYAML dependency in job environment
- [ ] Schema created with `CREATE SCHEMA IF NOT EXISTS`
- [ ] Predictive Optimization enabled
- [ ] Tables created with `CLUSTER BY AUTO`
- [ ] Standard TBLPROPERTIES applied (CDF, row tracking, etc.)
- [ ] PKs added via `ALTER TABLE` after creation
- [ ] FK constraints in separate script, runs after setup

### YAML Extraction Phase (BEFORE Writing Merge Code)
- [ ] `load_table_metadata()` helper included in merge script
- [ ] `build_inventory()` called in `main()` to load ALL table metadata from YAML
- [ ] `load_column_mappings_from_yaml()` or `load_column_mappings_from_csv()` used for renames
- [ ] `build_merge_condition()` used to construct MERGE ON clause from YAML PKs
- [ ] NO hardcoded table names — all come from `meta["table_name"]`
- [ ] NO hardcoded column lists — `.select(meta["columns"])` from YAML
- [ ] NO hardcoded MERGE conditions — built from `meta["pk_columns"]`
- [ ] NO hardcoded dedup keys — come from `meta["business_key"]`
- [ ] NO hardcoded grain columns — come from `meta["pk_columns"]`
- [ ] NO hardcoded Silver table names — come from `meta["source_tables"]`
- [ ] ONLY hand-coded items: aggregation expressions and derived column formulas

### Merge Phase
- [ ] Deduplication before EVERY merge (mandatory, key from YAML `business_key`)
- [ ] Deduplication key matches MERGE condition key (both from YAML)
- [ ] Column mappings extracted from YAML lineage or `COLUMN_LINEAGE.csv` (not guessed)
- [ ] No variable names shadow PySpark functions
- [ ] Schema validation: DataFrame columns match YAML `columns[]` before merge
- [ ] Grain validation for fact tables using YAML `pk_columns`
- [ ] Dimensions merged BEFORE facts (order from YAML `entity_type`)
- [ ] SCD Type 2 includes `is_current` filter (determined by YAML `scd_type`)
- [ ] Aggregated facts use `.groupBy(meta["pk_columns"])` from YAML
- [ ] `whenMatchedUpdate` columns built from YAML (not hardcoded set)
- [ ] Error handling with try/except and debug logging

### Deployment Phase
- [ ] Asset Bundle jobs use `notebook_task` (not `python_task`)
- [ ] Parameters use `base_parameters` dict
- [ ] FK task `depends_on` setup task
- [ ] Merge job has schedule (PAUSED in dev)
- [ ] Tags applied (environment, layer, job_type)
- [ ] Anomaly detection enabled on Gold schema (Phase 4b)

## Time Estimates

| Phase | Duration | Activities |
|-------|----------|------------|
| Phase 1: Setup scripts | 30 min | setup_tables.py + add_fk_constraints.py |
| Phase 2: Merge scripts | 2 hours | Dimension + fact merges with validation |
| Phase 3: Asset Bundle | 30 min | Job YAML files + databricks.yml sync |
| Phase 4: Deployment | 30 min | Deploy, run, verify |
| Phase 5: Validation | 30 min | Schema, grain, FK, SCD2 checks |
| **Total** | **3-4 hours** | For 3-5 tables |

## Next Steps After Implementation

After Gold layer implementation is complete and validated:
1. **Metric Views** — Create semantic metric views from Gold tables
2. **TVFs** — Create Table-Valued Functions for Genie integration
3. **Custom Business Metrics** — Set up Lakehouse Monitoring with AGGREGATE/DERIVED/DRIFT metrics (anomaly detection for baseline freshness/completeness is already enabled in Phase 4b)
4. **Genie Space** — Configure Genie Space with Gold tables, metric views, and TVFs

## Pipeline Progression

**Previous stage:** `silver/00-silver-layer-setup` → Silver tables must exist for Gold merge scripts to read from. Gold YAML designs (from stage 1: `gold/00-gold-layer-design`) must also exist.

**Next stage:** After completing Gold layer implementation, proceed to:
- **`planning/00-project-planning`** — Plan the semantic layer, observability, ML, and GenAI agent phases

## Reference Files

- **[Setup Script Patterns](references/setup-script-patterns.md)** — YAML-driven table creation, `find_yaml_base()`, `build_create_table_ddl()`, PK application
- **[FK Constraint Patterns](references/fk-constraint-patterns.md)** — FK constraint application after PKs, error handling, YAML FK format
- **[Merge Script Patterns](references/merge-script-patterns.md)** — SCD Type 1/2 dimension merges, fact aggregation merges, column mapping, deduplication
- **[Asset Bundle Job Patterns](references/asset-bundle-job-patterns.md)** — gold_setup_job.yml, gold_merge_job.yml, databricks.yml sync
- **[Validation Queries](references/validation-queries.md)** — Schema, grain, FK integrity, SCD Type 2 validation SQL
- **[Common Issues](references/common-issues.md)** — YAML not found, PyYAML missing, duplicate key MERGE, column mismatch, grain duplicates

## External References

- [Delta Lake MERGE](https://docs.delta.io/latest/delta-update.html#upsert-into-a-table-using-merge)
- [Unity Catalog Constraints](https://docs.databricks.com/data-governance/unity-catalog/constraints.html)
- [Databricks Asset Bundles](https://docs.databricks.com/dev-tools/bundles/)
- [AgentSkills.io Specification](https://agentskills.io/specification)
