---
name: silver-layer-setup
description: End-to-end orchestrator for creating Silver layer DLT pipelines with Delta table-based data quality rules, quarantine patterns, and monitoring views. Orchestrates mandatory dependencies on common skills (databricks-table-properties, databricks-python-imports, databricks-asset-bundles, schema-management-patterns, unity-catalog-constraints, databricks-expert-agent) and Silver-domain skills (dlt-expectations-patterns, dqx-patterns). Use when creating a Silver layer from scratch, setting up Bronze-to-Silver pipelines, or implementing Silver DLT with streaming ingestion and runtime-updateable DQ rules.
metadata:
  author: prashanth subrahmanyam
  version: "2.0"
  domain: silver
  role: orchestrator
  pipeline_stage: 3
  pipeline_stage_name: silver
  next_stages:
    - gold-layer-setup
  workers:
    - dlt-expectations-patterns
    - dqx-patterns
  common_dependencies:
    - databricks-asset-bundles
    - databricks-expert-agent
    - databricks-python-imports
    - databricks-table-properties
    - schema-management-patterns
    - unity-catalog-constraints
    - naming-tagging-standards
    - databricks-autonomous-operations
  source: context/prompts/02-silver-layer-prompt.md
  last_verified: "2026-02-07"
  volatility: medium
  upstream_sources:
    - name: "ai-dev-kit"
      repo: "databricks-solutions/ai-dev-kit"
      paths:
        - "databricks-skills/spark-declarative-pipelines/SKILL.md"
      relationship: "extended"
      last_synced: "2026-02-09"
      sync_commit: "97a3637"
---

# Silver Layer Setup - Orchestrator Skill

End-to-end workflow for creating production-grade Silver layer DLT pipelines with Delta table-based data quality rules, quarantine patterns, streaming ingestion, and monitoring views.

**Time Estimate:** 3-4 hours for initial setup, 1 hour per additional table

**What You'll Create:**
1. `dq_rules` Delta table - Centralized rules repository in Unity Catalog
2. `dq_rules_loader.py` - Pure Python module to load rules at runtime
3. `silver_*.py` - DLT notebooks with expectations loaded from Delta table
4. `silver_dlt_pipeline.yml` - Serverless DLT pipeline configuration
5. DQ monitoring views - Per-table metrics and referential integrity checks

---

## Decision Tree

| Question | Action |
|----------|--------|
| Creating a Silver layer from scratch? | **Use this skill** - it orchestrates everything |
| Only need DLT expectations patterns? | Read `silver/01-dlt-expectations-patterns/SKILL.md` directly |
| Need advanced DQX validation? | Read `silver/02-dqx-patterns/SKILL.md` directly |
| Need Asset Bundle configuration? | Read `common/databricks-asset-bundles/SKILL.md` directly |
| Need table properties reference? | Read `common/databricks-table-properties/SKILL.md` directly |
| Need pure Python import patterns? | Read `common/databricks-python-imports/SKILL.md` directly |

---

## Mandatory Skill Dependencies

**CRITICAL: Before generating ANY code for the Silver layer, you MUST read and follow the patterns in these common skills. Do NOT generate these patterns from memory.**

| Phase | MUST Read Skill (use Read tool on SKILL.md) | What It Provides |
|-------|---------------------------------------------|------------------|
| All phases | `common/databricks-expert-agent` | Core extraction principle: extract names from source, never hardcode |
| Schema setup | `common/schema-management-patterns` | CREATE SCHEMA DDL with governance metadata |
| DQ rules table | `common/databricks-table-properties` | TBLPROPERTIES for the dq_rules metadata table |
| DQ rules table | `common/unity-catalog-constraints` | PRIMARY KEY constraint syntax |
| Rules loader | `common/databricks-python-imports` | Pure Python module patterns (NO notebook header) |
| DLT notebooks | `common/databricks-table-properties` | Silver-layer TBLPROPERTIES (CDF, row tracking, auto-optimize) |
| Pipeline config | `common/databricks-asset-bundles` | DLT pipeline YAML, job YAML, serverless config |
| Troubleshooting | `common/databricks-autonomous-operations` | Deploy → Poll → Diagnose → Fix → Redeploy loop when jobs/pipelines fail |

**NEVER do these without FIRST reading the corresponding skill:**
- NEVER write `table_properties={...}` without reading `databricks-table-properties`
- NEVER write Python import patterns without reading `databricks-python-imports`
- NEVER write Asset Bundle YAML without reading `databricks-asset-bundles`
- NEVER write `CREATE SCHEMA` without reading `schema-management-patterns`
- NEVER define PK/FK constraints without reading `unity-catalog-constraints`

### 🔴 Non-Negotiable Defaults (Applied to EVERY Silver Table and Pipeline)

These defaults are ALWAYS applied. There are NO exceptions, NO overrides, NO alternative options.

| Default | Value | Applied Where | NEVER Do This Instead |
|---------|-------|---------------|----------------------|
| **Serverless** | `serverless: true` | Pipeline YAML | ❌ NEVER set `serverless: false` or define `clusters:` |
| **Auto Liquid Clustering** | `cluster_by_auto=True` | Every `@dlt.table()` | ❌ NEVER use `cluster_by=["col1", "col2"]` or `partition_cols=` |
| **Edition** | `edition: ADVANCED` | Pipeline YAML | ❌ NEVER use `CORE` or `PRO` (expectations require ADVANCED) |
| **Photon** | `photon: true` | Pipeline YAML | ❌ NEVER set `photon: false` |
| **Row Tracking** | `"delta.enableRowTracking": "true"` | Every table's `table_properties` | ❌ NEVER omit (breaks downstream MV refresh) |
| **Change Data Feed** | `"delta.enableChangeDataFeed": "true"` | Every table's `table_properties` | ❌ NEVER omit (required for incremental propagation) |

```python
# ✅ CORRECT: Every @dlt.table() MUST include these
@dlt.table(
    name="silver_anything",
    table_properties={
        "delta.enableChangeDataFeed": "true",
        "delta.enableRowTracking": "true",
        # ... other properties from databricks-table-properties
    },
    cluster_by_auto=True  # 🔴 MANDATORY on every table, including monitoring views
)
```

```yaml
# ✅ CORRECT: Pipeline YAML MUST include these
serverless: true      # 🔴 MANDATORY - no classic clusters
photon: true          # 🔴 MANDATORY - vectorized execution
edition: ADVANCED     # 🔴 MANDATORY - required for expectations
```

### Silver-Domain Dependencies

| Skill | Requirement | What It Provides |
|-------|-------------|------------------|
| `silver/01-dlt-expectations-patterns` | **MUST read** | DQ rules table DDL, rules loader cache pattern, DLT decorators, quarantine generation, runtime rule updates |
| `silver/02-dqx-patterns` | **Optional** | Read only when user needs richer diagnostics than DLT expectations, or pre-merge validation |

---

## Core Philosophy: Schema Cloning

**The Silver layer should essentially clone the source Bronze schema with minimal transformations:**

- **Same column names** as Bronze (no complex renaming)
- **Same data types** (minimal type conversions)
- **Same grain** (no aggregation - that's for Gold)
- **Add data quality rules** (the main value-add)
- **Add derived flags** (business indicators like `is_return`, `is_out_of_stock`)
- **Add business keys** (SHA256 hashes for tracking)
- **Add timestamps** (`processed_timestamp`)

**What NOT to do in Silver:**
- No major schema restructuring
- No aggregations (save for Gold)
- No complex business logic (simple flags only)
- No joining across tables (dimension lookups in Gold)

**Why:** Silver is the validated copy of source data. Gold handles complex transformations. This keeps Silver focused on data quality and makes troubleshooting easier (column names match source).

### Python API: ALWAYS use `import dlt` (Legacy API)

Our DQ rules framework (`dlt-expectations-patterns`) is built on the legacy `import dlt` API. **ALWAYS use this API for Silver layer creation.**

```python
# ✅ CORRECT: Legacy API (our standard)
import dlt
from dq_rules_loader import get_critical_rules_for_table

@dlt.table(name="silver_transactions", cluster_by_auto=True)
@dlt.expect_all_or_drop(get_critical_rules_for_table("silver_transactions"))
def silver_transactions():
    return dlt.read_stream(get_bronze_table("bronze_transactions"))
```

```python
# ❌ WRONG: Modern SDP API (not compatible with our DQ rules framework)
from pyspark import pipelines as dp

@dp.table(name="silver_transactions")
def silver_transactions():
    return spark.readStream.table("bronze_transactions")
```

**Why not modern `dp` API?** The `@dlt.expect_all_or_drop()` and `@dlt.expect_all()` decorators from our `dlt-expectations-patterns` skill require the `dlt` module. When Databricks fully migrates expectations to `dp`, update both this skill and `dlt-expectations-patterns`.

---

## File Structure

```
src/{project}_silver/
├── setup_dq_rules_table.py        # Databricks notebook: Create and populate DQ rules Delta table
├── dq_rules_loader.py             # Pure Python (NO notebook header): Load rules from Delta table
├── silver_dimensions.py           # DLT notebook: Dimension tables (stores, products, etc.)
├── silver_transactions.py         # DLT notebook: Fact table with quarantine
├── silver_inventory.py            # DLT notebook: Additional fact tables (if applicable)
└── data_quality_monitoring.py     # DLT notebook: DQ monitoring views
```

**Critical Files:**
- `dq_rules_loader.py` must be **pure Python** (NO `# Databricks notebook source` header)
- Run `silver_dq_setup_job` BEFORE deploying DLT pipeline

---

## Phased Implementation Workflow

### Phase 1: Requirements & Schema Setup (30 min)

**Pre-Condition - MUST read these skills first:**
1. Read `common/databricks-expert-agent/SKILL.md` - Apply extraction principle throughout
2. Read `common/schema-management-patterns/SKILL.md` - Use for Silver schema DDL

**Steps:**
1. Fill in requirements template: `assets/templates/requirements-template.md`
   - Map Bronze tables to Silver tables
   - Define DQ rules per entity (critical vs warning)
   - Identify quarantine candidates
2. Create Silver schema using pattern from `schema-management-patterns`
3. Verify Bronze tables exist and extract their schemas (don't hardcode column names)

---

### Phase 2: DQ Rules Table Setup (30 min)

**Pre-Condition - MUST read these skills first:**
1. Read `silver/01-dlt-expectations-patterns/SKILL.md` - Use for DQ rules table DDL and population
2. Read `common/databricks-table-properties/SKILL.md` - Apply metadata table TBLPROPERTIES
3. Read `common/unity-catalog-constraints/SKILL.md` - Apply PK constraint on (table_name, rule_name)

**Steps:**
1. Create `setup_dq_rules_table.py` notebook
2. Define DQ rules table DDL (schema from `dlt-expectations-patterns`)
3. Apply TBLPROPERTIES from `databricks-table-properties`
4. Apply PK constraint: `CONSTRAINT pk_dq_rules PRIMARY KEY (table_name, rule_name) NOT ENFORCED`
5. Populate rules using the requirements from Phase 1
6. Deploy and run: `databricks bundle run silver_dq_setup_job -t dev`
7. Verify: `SELECT * FROM {catalog}.{silver_schema}.dq_rules`

---

### Phase 3: Rules Loader Module (15 min)

**Pre-Condition - MUST read these skills first:**
1. Read `common/databricks-python-imports/SKILL.md` - CRITICAL: loader must be pure Python
2. Read `silver/01-dlt-expectations-patterns/SKILL.md` - Use cache pattern with `toPandas()`

**Steps:**
1. Create `dq_rules_loader.py` as pure Python file (NO notebook header!)
2. Implement functions: `get_critical_rules_for_table()`, `get_warning_rules_for_table()`, `get_quarantine_condition()`
3. Use module-level cache pattern with `toPandas()` (NOT `.collect()`) from `dlt-expectations-patterns`
4. Test import: `from dq_rules_loader import get_critical_rules_for_table`

---

### Phase 4: DLT Notebooks - Silver Tables (1-2 hours)

**Pre-Condition - MUST read these skills first:**
1. Read `common/databricks-table-properties/SKILL.md` - Extract Silver TBLPROPERTIES
2. Read `silver/01-dlt-expectations-patterns/SKILL.md` - Use decorator patterns
3. (Optional) Read `silver/02-dqx-patterns/SKILL.md` - Only if user needs hybrid DQX+DLT

**Steps:**
1. Create DLT notebooks using patterns from `references/silver-table-patterns.md`
2. Include `get_bronze_table()` helper in every notebook (see references/)
3. For each table:
   - Apply Silver TBLPROPERTIES from `databricks-table-properties`
   - Apply `@dlt.expect_all_or_drop(get_critical_rules_for_table(...))` decorator
   - Apply `@dlt.expect_all(get_warning_rules_for_table(...))` decorator
   - Clone Bronze schema with minimal transformations
   - Add derived flags, business keys, `processed_timestamp`
   - Set `cluster_by_auto=True` (NEVER specify columns manually)
4. For high-volume fact tables: create quarantine table using `get_quarantine_condition()`

**See:** `references/silver-table-patterns.md` for complete templates

---

### Phase 5: Monitoring Views (30 min)

**No external skill dependencies** - use `references/monitoring-patterns.md`

**Steps:**
1. Create `data_quality_monitoring.py` DLT notebook
2. Add per-table DQ metrics views (record counts, pass/fail rates)
3. Add referential integrity checks (orphaned records between fact and dimension)
4. Add data freshness monitoring

**See:** `references/monitoring-patterns.md` for complete patterns

---

### Phase 6: Pipeline & Job Configuration (15 min)

**Pre-Condition - MUST read these skills first:**
1. Read `common/databricks-asset-bundles/SKILL.md` - DLT pipeline YAML, job YAML patterns

**Steps:**
1. Create `resources/silver_dlt_pipeline.yml` using patterns from `databricks-asset-bundles`
2. Create `resources/silver_dq_setup_job.yml` for the DQ rules setup job
3. Set DLT Direct Publishing Mode: `catalog` + `schema` fields (NOT `target`)
4. Pass configuration: `catalog`, `bronze_schema`, `silver_schema`
5. Set: `serverless: true`, `edition: ADVANCED`, `photon: true`

**See:** `references/pipeline-configuration.md` for Silver-specific examples

**CRITICAL Deployment Order:**
```bash
# 1. Deploy everything
databricks bundle deploy -t dev

# 2. Run DQ rules setup FIRST (creates dq_rules table)
databricks bundle run silver_dq_setup_job -t dev

# 3. Verify rules table exists
# SELECT * FROM {catalog}.{silver_schema}.dq_rules

# 4. THEN run DLT pipeline (loads rules from table)
databricks pipelines start-update --pipeline-name "[dev] Silver Layer Pipeline"
```

---

### Phase 7: Enable Anomaly Detection on Silver Schema (5 min)

**Pre-Condition - MUST read this skill first:**
1. Read `monitoring/04-anomaly-detection/SKILL.md` — Schema-level freshness/completeness monitoring

**Why:** Every Silver schema should have anomaly detection enabled from day one. It builds freshness and completeness ML baselines immediately, catching stale/incomplete tables before downstream consumers notice.

**Steps:**
1. Enable anomaly detection on the Silver schema (uses `enable_anomaly_detection_on_schema()` from the anomaly-detection skill)
2. Exclude metadata tables that are not data pipeline outputs (e.g., `dq_rules`)
3. Verify enablement via Catalog Explorer or SDK

```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.dataquality import Monitor, AnomalyDetectionConfig

w = WorkspaceClient()

# Get Silver schema UUID
schema_info = w.schemas.get(full_name=f"{catalog}.{silver_schema}")
schema_id = schema_info.schema_id

# Enable anomaly detection (exclude metadata tables)
try:
    w.data_quality.create_monitor(
        monitor=Monitor(
            object_type="schema",
            object_id=schema_id,
            anomaly_detection_config=AnomalyDetectionConfig(
                excluded_table_full_names=[
                    f"{catalog}.{silver_schema}.dq_rules",  # Metadata, not pipeline output
                ]
            )
        )
    )
    print(f"✓ Anomaly detection enabled on {catalog}.{silver_schema}")
except Exception as e:
    if "already exists" in str(e).lower():
        print(f"✓ Already enabled (skipping)")
    else:
        print(f"⚠️ Non-blocking: {e}")
```

**Note:** This is non-blocking — if anomaly detection fails to enable (permissions, preview limitations), the Silver layer setup continues. Retry later via `monitoring/04-anomaly-detection/scripts/enable_anomaly_detection.py`.

---

## Common Mistakes (Silver-Specific)

### Mistake 1: Deploying DLT Before DQ Setup Job
```
Pipeline Error: Table or view not found: dq_rules
```
**Fix:** Run `silver_dq_setup_job` BEFORE deploying/running DLT pipeline.

### Mistake 2: Notebook Header in Loader File
```python
# dq_rules_loader.py
# Databricks notebook source  # <-- Makes it a notebook, breaks imports!
```
**Fix:** Remove `# Databricks notebook source` line. Read `databricks-python-imports` for correct pattern.

### Mistake 3: Aggregation in Silver
```python
# WRONG: Aggregation belongs in Gold
def silver_sales_daily():
    return dlt.read_stream(...).groupBy("store", "date").agg(sum("revenue"))
```
**Fix:** Keep Silver at transaction grain. Aggregate in Gold.

### Mistake 4: Manual Clustering Columns
```python
# WRONG
@dlt.table(cluster_by=["store_number", "transaction_date"])
```
**Fix:** Always use `cluster_by_auto=True`. Never specify columns.

### Mistake 5: Using expect_or_fail
```python
# WRONG: Pipeline fails on bad data
@dlt.expect_or_fail("valid_id", "id IS NOT NULL")
```
**Fix:** Use `@dlt.expect_all_or_drop()` for critical rules. Pipeline continues, bad records quarantined.

### Mistake 6: Hardcoding Table Names
```python
# WRONG: Hardcoded table reference
dlt.read_stream("my_catalog.bronze.transactions")
```
**Fix:** Use `get_bronze_table()` helper with DLT configuration. See `references/silver-table-patterns.md`.

### Mistake 7: Schema Evolution Without Full Refresh
```
Error: Incompatible schema change detected on streaming table
```
**Fix:** Streaming tables require a **full refresh** for incompatible schema changes (adding NOT NULL columns, changing types). Trigger with: `databricks pipelines start-update --pipeline-name "..." --full-refresh`

### Mistake 8: Missing Row Tracking (Breaks Downstream MVs)
```python
# ❌ WRONG: Missing delta.enableRowTracking
table_properties={
    "delta.enableChangeDataFeed": "true",
    # Row tracking missing!
}
```
**Fix:** ALWAYS include `"delta.enableRowTracking": "true"` in Silver table properties. Without it, downstream Gold materialized views cannot use incremental refresh and will do expensive full recomputation.

### Mistake 9: Using Modern `dp` API with DQ Rules Framework
```python
# ❌ WRONG: dp API doesn't work with our dlt-expectations decorators
from pyspark import pipelines as dp
@dp.table(name="silver_transactions")
@dlt.expect_all_or_drop(get_critical_rules_for_table(...))  # Mixes APIs!
```
**Fix:** ALWAYS use `import dlt` for Silver notebooks that use our DQ rules framework. See "Python API" section above.

---

## Post-Creation Validation

Before considering the Silver layer complete, verify each item and confirm its source:

### Common Skill Compliance
- [ ] Table properties match `databricks-table-properties` Silver layer spec (not generated from memory)
- [ ] Python imports follow `databricks-python-imports` patterns (loader has NO notebook header)
- [ ] Asset Bundle YAML follows `databricks-asset-bundles` patterns (notebook_task, base_parameters)
- [ ] Schema DDL follows `schema-management-patterns` (IF NOT EXISTS, governance metadata)
- [ ] PK constraint follows `unity-catalog-constraints` syntax (NOT ENFORCED keyword)
- [ ] Names extracted from source files per `databricks-expert-agent` (not hardcoded)

### Silver-Domain Skill Compliance
- [ ] DQ rules table follows `dlt-expectations-patterns` DDL
- [ ] Rules loader uses cache pattern from `dlt-expectations-patterns` (toPandas, not collect)
- [ ] DLT decorators follow `dlt-expectations-patterns` (expect_all_or_drop, expect_all)
- [ ] Quarantine condition uses `dlt-expectations-patterns` generation pattern

### Silver Layer Specifics
- [ ] Schema cloning: Silver columns match Bronze (no aggregation, no joins)
- [ ] `get_bronze_table()` helper used for all source table references
- [ ] `cluster_by_auto=True` on every table (NEVER manual cluster keys)
- [ ] `delta.enableRowTracking` = `true` on every Silver table (required for downstream MV incremental refresh)
- [ ] Quarantine tables created for high-volume fact tables
- [ ] DQ monitoring views created (including data freshness)
- [ ] Deployment order correct: DQ setup job runs BEFORE DLT pipeline
- [ ] `import dlt` used (NOT `from pyspark import pipelines as dp`)
- [ ] `serverless: true` in pipeline YAML (NEVER classic clusters)
- [ ] `photon: true` in pipeline YAML
- [ ] `edition: ADVANCED` set in pipeline YAML (required for expectations/CDC)
- [ ] No `clusters:` block in pipeline YAML (serverless manages compute)
- [ ] Deduplication applied where Bronze may have duplicate records
- [ ] `processed_timestamp` added to every Silver table
- [ ] Event timestamps preserved from Bronze (not replaced by processing time)
- [ ] Anomaly detection enabled on Silver schema (Phase 7)
- [ ] Metadata tables (e.g., `dq_rules`) excluded from anomaly detection

---

## Reference Files

### Silver Table Patterns
- **`references/silver-table-patterns.md`** - Complete DLT table templates: standard pattern, dimension example, fact example with quarantine, `get_bronze_table()` helper, derived field patterns

### Monitoring Patterns
- **`references/monitoring-patterns.md`** - DQ monitoring views: per-table metrics, referential integrity checks, data freshness monitoring

### Pipeline Configuration
- **`references/pipeline-configuration.md`** - Silver-specific DLT pipeline YAML and DQ setup job YAML examples (supplements `databricks-asset-bundles`)

## Templates

### Requirements Template
- **`assets/templates/requirements-template.md`** - Fill-in-first requirements gathering: project context, Bronze-to-Silver table mapping, DQ rules per entity, quarantine strategy

## Related Skills

| Skill | Relationship | Path |
|-------|-------------|------|
| `dlt-expectations-patterns` | **Mandatory** - DQ rules, loader, decorators | `silver/01-dlt-expectations-patterns/SKILL.md` |
| `dqx-patterns` | **Optional** - Advanced validation | `silver/02-dqx-patterns/SKILL.md` |
| `anomaly-detection` | **Mandatory** - Schema freshness/completeness monitoring | `monitoring/04-anomaly-detection/SKILL.md` |
| `databricks-expert-agent` | **Mandatory** - Extraction principle | `common/databricks-expert-agent/SKILL.md` |
| `databricks-table-properties` | **Mandatory** - Silver TBLPROPERTIES | `common/databricks-table-properties/SKILL.md` |
| `databricks-python-imports` | **Mandatory** - Pure Python loader | `common/databricks-python-imports/SKILL.md` |
| `databricks-asset-bundles` | **Mandatory** - Pipeline/job YAML | `common/databricks-asset-bundles/SKILL.md` |
| `schema-management-patterns` | **Mandatory** - Schema DDL | `common/schema-management-patterns/SKILL.md` |
| `unity-catalog-constraints` | **Mandatory** - PK constraint | `common/unity-catalog-constraints/SKILL.md` |

## Pipeline Progression

**Previous stage:** `bronze/00-bronze-layer-setup` → Bronze tables must exist before creating Silver

**Next stage:** After completing the Silver layer, proceed to:
- **`gold/01-gold-layer-setup`** — Implement Gold layer tables, merge scripts, and FK constraints from the YAML designs created in stage 1

---

## References

### Official Databricks Documentation
- [DLT Expectations](https://docs.databricks.com/aws/en/dlt/expectations)
- [Portable and Reusable Expectations](https://docs.databricks.com/aws/en/ldp/expectation-patterns#portable-and-reusable-expectations)
- [Share Code Between Notebooks](https://docs.databricks.com/aws/en/notebooks/share-code)
- [Automatic Clustering](https://docs.databricks.com/aws/en/delta/clustering#enable-or-disable-automatic-liquid-clustering)
- [Lakeflow Declarative Pipelines (SDP)](https://docs.databricks.com/aws/en/ldp/) - Modern pipeline framework overview
- [Python API: `pyspark.pipelines`](https://docs.databricks.com/aws/en/ldp/developer/python-ref) - Modern Python API reference (future migration target)
- [Row Tracking](https://docs.databricks.com/aws/en/delta/row-tracking) - Required for incremental MV refresh
- [Schema Evolution in Streaming Tables](https://docs.databricks.com/aws/en/ldp/develop#schema-evolution) - Full refresh requirements
- [Pipeline Edition Comparison](https://docs.databricks.com/aws/en/ldp/configure-pipeline#editions) - ADVANCED required for expectations/CDC
