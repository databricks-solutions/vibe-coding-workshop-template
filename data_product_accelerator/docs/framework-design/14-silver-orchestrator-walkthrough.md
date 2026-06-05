# Silver Orchestrator — Visual Walkthrough

How the `00-silver-layer-setup` orchestrator progressively loads 2 worker skills and 6 common skills across 7 phases, building production-grade Spark Declarative Pipelines (SDP/DLT) with Delta table-based data quality rules, quarantine patterns, and monitoring views.

> **Related skills:** [`00-silver-layer-setup`](../../skills/silver/00-silver-layer-setup/SKILL.md), [`01-dlt-expectations-patterns`](../../skills/silver/01-dlt-expectations-patterns/SKILL.md), [`02-dqx-patterns`](../../skills/silver/02-dqx-patterns/SKILL.md)
>
> **Common skills used:** [`databricks-expert-agent`](skills/databricks-expert-agent/SKILL.md), [`databricks-table-properties`](../../skills/common/databricks-table-properties/SKILL.md), [`databricks-python-imports`](../../skills/common/databricks-python-imports/SKILL.md), [`databricks-asset-bundles`](skills/databricks-asset-bundles/SKILL.md), [`schema-management-patterns`](../../skills/common/schema-management-patterns/SKILL.md), [`unity-catalog-constraints`](../../skills/common/unity-catalog-constraints/SKILL.md)

---

## The Agent's Journey Through the Silver Orchestrator

### Step 0: Skill Activation (~100 tokens)

When a user says something like *"Create the Silver layer for my project"*, the agent framework matches:

```yaml
name: silver-layer-setup
description: >
  End-to-end orchestrator for creating Silver layer pipelines using Spark Declarative Pipelines
  (SDP, formerly DLT) with Delta table-based data quality rules, quarantine patterns, and monitoring views...
```

Keywords "Silver layer", "SDP", "DLT", "data quality rules" match the user's intent. The agent reads the full SKILL.md (~580 lines).

### Step 1: The Decision Tree — Should I Even Be Here?

| Question | Action |
|----------|--------|
| Creating a Silver layer from scratch? | **Use this skill** — it orchestrates everything |
| Only need DLT expectations patterns? | Read `silver/01-dlt-expectations-patterns/SKILL.md` directly |
| Need advanced DQX validation? | Read `silver/02-dqx-patterns/SKILL.md` directly |
| Need Asset Bundle configuration? | Read `skills/databricks-asset-bundles/SKILL.md` directly |
| Need table properties reference? | Read `common/databricks-table-properties/SKILL.md` directly |

### Step 2: The Guard Rails Lock In

The Silver orchestrator has 6 non-negotiable defaults that apply to every table and pipeline:

| Default | Value | NEVER Do This Instead |
|---------|-------|-----------------------|
| **Serverless** | `serverless: true` | Never set `serverless: false` or define `clusters:` |
| **Auto Liquid Clustering** | `cluster_by_auto=True` | Never use `cluster_by=["col1", "col2"]` |
| **Edition** | `edition: ADVANCED` | Never use CORE or PRO (expectations require ADVANCED) |
| **Photon** | `photon: true` | Never set `photon: false` |
| **Row Tracking** | `delta.enableRowTracking: "true"` | Never omit (breaks downstream MV refresh) |
| **Change Data Feed** | `delta.enableChangeDataFeed: "true"` | Never omit (required for incremental propagation) |

Plus two API constraints:
- **Always use `import dlt`** (legacy API) — NOT `from pyspark import pipelines as dp`
- **`dq_rules_loader.py` must be pure Python** — NO `# Databricks notebook source` header

### Step 3: The Core Philosophy — Schema Cloning

The orchestrator establishes a key design philosophy that the agent must follow throughout:

```
Silver layer = Bronze schema clone + data quality rules

✅ Same column names as Bronze
✅ Same data types (minimal conversions)
✅ Same grain (no aggregation)
✅ Add: DQ rules, derived flags, business keys, processed_timestamp

❌ No major schema restructuring
❌ No aggregations (that's for Gold)
❌ No complex business logic
❌ No cross-table joins
```

### Step 4: The Progressive Disclosure Protocol

The Silver orchestrator manages 2 worker skills, 6 common skills, and 3 reference files across 7 phases:

```
Read skills ONLY at the phase where they are needed:
  Phase 1: Read expert-agent + schema-management → work → persist notes
  Phase 2: Read dlt-expectations + table-properties + unity-catalog → work → persist notes
  Phase 3: Read python-imports + dlt-expectations → work → persist notes
  Phase 4: Read table-properties + dlt-expectations → work → persist notes
  Phase 5: No skills needed — use reference files
  Phase 6: Read asset-bundles → work → persist notes
  Phase 7 (user-triggered): Read anomaly-detection → work → done
```

**At each phase boundary, the agent's working memory should contain ONLY:**
1. Table list from Phase 1 (persists through all phases)
2. Previous phase's summary note
3. Current phase's skills (read just-in-time)
4. The constraint: `dq_rules_loader.py` must be pure Python (carry through ALL phases)

---

## Phase 1: Requirements & Schema Setup

```
┌──────────────────────────────────────────────────────────┐
│                      PHASE 1                             │
│                                                          │
│  Working Memory:                                         │
│  ┌──────────────────────────────┐                       │
│  │ expert-agent SKILL.md        │ ← READ now            │
│  │ schema-management SKILL.md   │ ← READ now            │
│  └──────────────────────────────┘                       │
│                                                          │
│  Steps:                                                  │
│  ┌─────────────────────────────────────────┐            │
│  │ 1. Map Bronze tables → Silver tables    │            │
│  │    bronze_transactions → silver_trans.   │            │
│  │    bronze_products → silver_products     │            │
│  │    bronze_stores → silver_stores         │            │
│  │                                          │            │
│  │ 2. Define DQ rules per entity            │            │
│  │    ├── Critical: NOT NULL on PKs, FKs   │            │
│  │    ├── Warning: Range checks, format     │            │
│  │    └── Quarantine: high-volume facts     │            │
│  │                                          │            │
│  │ 3. CREATE SCHEMA IF NOT EXISTS           │            │
│  │    (from schema-management-patterns)     │            │
│  │                                          │            │
│  │ 4. Verify Bronze tables exist            │            │
│  │    Extract schemas — don't hardcode!     │            │
│  │    (from expert-agent extraction rule)   │            │
│  └─────────────────────────────────────────┘            │
│                                                          │
│  📝 Persist: schema names, table list, DQ strategy       │
└──────────────────────────────────────────────────────────┘
```

---

## Phase 2: DQ Rules Table Setup

```
┌──────────────────────────────────────────────────────────┐
│                      PHASE 2                             │
│                                                          │
│  Working Memory:                                         │
│  ┌──────────────────────────────┐                       │
│  │ Phase 1 notes (table list)   │ ← compact handoff     │
│  │ 01-dlt-expectations SKILL.md │ ← READ now (worker)   │
│  │ table-properties SKILL.md    │ ← READ now (common)   │
│  │ unity-catalog-constraints    │ ← READ now (common)   │
│  └──────────────────────────────┘                       │
│                                                          │
│  Creates the centralized DQ rules engine:               │
│  ┌─────────────────────────────────────────┐            │
│  │                                          │            │
│  │  setup_dq_rules_table.py                │            │
│  │  ┌──────────────────────────────┐       │            │
│  │  │ CREATE TABLE IF NOT EXISTS   │       │            │
│  │  │   dq_rules (                 │       │            │
│  │  │     table_name STRING,       │       │            │
│  │  │     rule_name STRING,        │       │            │
│  │  │     rule_expression STRING,  │       │            │
│  │  │     severity STRING,         │       │            │
│  │  │     ...                      │       │            │
│  │  │   )                          │       │            │
│  │  │   TBLPROPERTIES (...)        │ ← from│            │
│  │  │   ← table-properties skill   │       │            │
│  │  │                              │       │            │
│  │  │ ALTER TABLE ADD CONSTRAINT   │       │            │
│  │  │   pk_dq_rules PRIMARY KEY   │ ← from│            │
│  │  │   (table_name, rule_name)    │       │            │
│  │  │   NOT ENFORCED               │ unity │            │
│  │  │                              │catalog│            │
│  │  │ INSERT rules for each table  │       │            │
│  │  └──────────────────────────────┘       │            │
│  └─────────────────────────────────────────┘            │
│                                                          │
│  📝 Persist: DQ table path, rule count, severity dist.   │
└──────────────────────────────────────────────────────────┘
```

---

## Phase 3: Rules Loader Module

```
┌──────────────────────────────────────────────────────────┐
│                      PHASE 3                             │
│                                                          │
│  Working Memory:                                         │
│  ┌──────────────────────────────┐                       │
│  │ Phase 2 notes (DQ table)     │                       │
│  │ python-imports SKILL.md      │ ← READ now            │
│  │ dlt-expectations SKILL.md    │ ← still from Phase 2  │
│  └──────────────────────────────┘                       │
│                                                          │
│  ⚠️ CRITICAL: This file must be PURE PYTHON             │
│     NO "# Databricks notebook source" header!            │
│                                                          │
│  Creates: dq_rules_loader.py                            │
│  ┌─────────────────────────────────────────┐            │
│  │                                          │            │
│  │  # NO notebook header! (pure Python)    │            │
│  │                                          │            │
│  │  _cache = {}  # Module-level cache       │            │
│  │                                          │            │
│  │  def _load_rules(table_name):            │            │
│  │      if table_name not in _cache:        │            │
│  │          df = spark.table("dq_rules")    │            │
│  │          _cache[table_name] =            │            │
│  │              df.filter(...).toPandas()   │            │
│  │                  ← toPandas, NOT collect │            │
│  │      return _cache[table_name]           │            │
│  │                                          │            │
│  │  def get_critical_rules_for_table(name): │            │
│  │      ...                                 │            │
│  │  def get_warning_rules_for_table(name):  │            │
│  │      ...                                 │            │
│  │  def get_quarantine_condition(name):     │            │
│  │      ...                                 │            │
│  └─────────────────────────────────────────┘            │
│                                                          │
│  📝 Persist: loader path, confirm pure Python            │
└──────────────────────────────────────────────────────────┘
```

---

## Phase 4: DLT Notebooks — The Main Build

```
┌──────────────────────────────────────────────────────────┐
│                      PHASE 4                             │
│                                                          │
│  Working Memory:                                         │
│  ┌──────────────────────────────┐                       │
│  │ Phase 1 notes (table list)   │ ← table names         │
│  │ Phase 3 notes (loader path)  │                       │
│  │ table-properties SKILL.md    │ ← READ now            │
│  │ dlt-expectations SKILL.md    │ ← READ now            │
│  └──────────────────────────────┘                       │
│                                                          │
│  For each Silver table:                                 │
│  ┌─────────────────────────────────────────┐            │
│  │                                          │            │
│  │  import dlt                   ← ALWAYS   │            │
│  │  from dq_rules_loader import  ...        │            │
│  │                                          │            │
│  │  @dlt.table(                             │            │
│  │    name="silver_transactions",           │            │
│  │    table_properties={                    │            │
│  │      "delta.enableChangeDataFeed": "true"│ 🔴        │
│  │      "delta.enableRowTracking": "true",  │ 🔴        │
│  │      ...from table-properties skill      │            │
│  │    },                                    │            │
│  │    cluster_by_auto=True        🔴        │            │
│  │  )                                       │            │
│  │  @dlt.expect_all_or_drop(                │            │
│  │    get_critical_rules_for_table(...)      │            │
│  │  )                                       │            │
│  │  @dlt.expect_all(                        │            │
│  │    get_warning_rules_for_table(...)       │            │
│  │  )                                       │            │
│  │  def silver_transactions():              │            │
│  │    return dlt.read_stream(               │            │
│  │      get_bronze_table("bronze_trans...")  │            │
│  │    )                                     │            │
│  │                                          │            │
│  │  For high-volume facts: quarantine table │            │
│  │  using get_quarantine_condition()         │            │
│  └─────────────────────────────────────────┘            │
│                                                          │
│  📝 Persist: notebook paths, expectation counts          │
└──────────────────────────────────────────────────────────┘
```

---

## Phase 5: Monitoring Views

```
┌──────────────────────────────────────────────────────────┐
│                      PHASE 5                             │
│                                                          │
│  Working Memory:                                         │
│  ┌──────────────────────────────┐                       │
│  │ Phase 4 notes (notebooks)    │                       │
│  │ references/monitoring-        │ ← reference file     │
│  │   patterns.md                 │   (not a skill)      │
│  └──────────────────────────────┘                       │
│  (No new worker skills — reference files only)           │
│                                                          │
│  Creates: data_quality_monitoring.py                    │
│  ┌─────────────────────────────────────────┐            │
│  │ Per-table DQ metrics views              │            │
│  │ ├── Record counts (total, pass, fail)   │            │
│  │ ├── Pass/fail rates by rule             │            │
│  │ └── Trend over time                     │            │
│  │                                          │            │
│  │ Referential integrity checks            │            │
│  │ ├── Orphaned records detection          │            │
│  │ └── Cross-table FK validation           │            │
│  │                                          │            │
│  │ Data freshness monitoring               │            │
│  │ └── Max processed_timestamp per table   │            │
│  └─────────────────────────────────────────┘            │
│                                                          │
│  📝 Persist: monitoring view paths, metric definitions   │
└──────────────────────────────────────────────────────────┘
```

---

## Phase 6: Pipeline & Job Configuration

```
┌──────────────────────────────────────────────────────────┐
│                      PHASE 6                             │
│                                                          │
│  Working Memory:                                         │
│  ┌──────────────────────────────┐                       │
│  │ Phase 4-5 notes (all paths)  │                       │
│  │ asset-bundles SKILL.md       │ ← READ now            │
│  └──────────────────────────────┘                       │
│                                                          │
│  Creates two YAML configurations:                       │
│  ┌─────────────────────────────────────────┐            │
│  │                                          │            │
│  │  silver_dlt_pipeline.yml                │            │
│  │  ┌──────────────────────────────────┐   │            │
│  │  │ serverless: true        🔴       │   │            │
│  │  │ photon: true            🔴       │   │            │
│  │  │ edition: ADVANCED       🔴       │   │            │
│  │  │ catalog: ${var.catalog}          │   │            │
│  │  │ schema: ${var.silver_schema}     │   │            │
│  │  │ libraries:                       │   │            │
│  │  │   - notebook: silver_dims.py     │   │            │
│  │  │   - notebook: silver_trans.py    │   │            │
│  │  │   - notebook: monitoring.py      │   │            │
│  │  └──────────────────────────────────┘   │            │
│  │                                          │            │
│  │  silver_dq_setup_job.yml                │            │
│  │  ┌──────────────────────────────────┐   │            │
│  │  │ notebook_task:                   │   │            │
│  │  │   notebook_path: setup_dq_rules  │   │            │
│  │  │   base_parameters:               │   │            │
│  │  │     catalog: ${var.catalog}      │   │            │
│  │  │     silver_schema: ${var...}     │   │            │
│  │  └──────────────────────────────────┘   │            │
│  └─────────────────────────────────────────┘            │
│                                                          │
│  📝 Persist: pipeline YAML path, job YAML path           │
└──────────────────────────────────────────────────────────┘
```

---

## STOP — Artifact Creation Complete

After Phase 6, all files have been created. The agent stops and reports what was built:

```
┌──────────────────────────────────────────────────────────┐
│                   🛑 STOP GATE                           │
│                                                          │
│  Created files:                                          │
│  ├── src/{project}_silver/                              │
│  │   ├── setup_dq_rules_table.py    (Phase 2)          │
│  │   ├── dq_rules_loader.py         (Phase 3, PURE PY) │
│  │   ├── silver_dimensions.py       (Phase 4)          │
│  │   ├── silver_transactions.py     (Phase 4)          │
│  │   └── data_quality_monitoring.py (Phase 5)          │
│  └── resources/                                         │
│      ├── silver_dlt_pipeline.yml    (Phase 6)          │
│      └── silver_dq_setup_job.yml    (Phase 6)          │
│                                                          │
│  ⚠️ Do NOT deploy unless user explicitly requests it    │
└──────────────────────────────────────────────────────────┘
```

---

## Deployment Order (User-Triggered Only)

When the user says "deploy", the order is critical — DQ rules table must exist BEFORE the DLT pipeline runs:

```
┌──────────────────────────────────────────────────────────┐
│                   DEPLOYMENT                             │
│                                                          │
│  $ databricks bundle deploy -t dev                      │
│                                                          │
│  Step 1: DQ rules setup FIRST                           │
│  ┌──────────────────────┐                               │
│  │ silver_dq_setup_job  │ ← Creates dq_rules table     │
│  │ (notebook_task)      │    and populates rules        │
│  └──────────┬───────────┘                               │
│             │ MUST complete before                       │
│             ▼                                            │
│  Step 2: DLT pipeline SECOND                            │
│  ┌──────────────────────┐                               │
│  │ Silver DLT Pipeline  │ ← Reads rules from table     │
│  │ (serverless SDP)     │    via dq_rules_loader.py     │
│  └──────────────────────┘                               │
│                                                          │
│  ❌ WRONG ORDER: Pipeline before DQ setup                │
│     → "Table or view not found: dq_rules"               │
└──────────────────────────────────────────────────────────┘
```

---

## Phase 7 (User-Triggered): Anomaly Detection

```
┌──────────────────────────────────────────────────────────┐
│                      PHASE 7                             │
│                                                          │
│  ⚠️ Only when user explicitly requests it               │
│                                                          │
│  Read: monitoring/04-anomaly-detection/SKILL.md          │
│                                                          │
│  Enable schema-level anomaly detection:                 │
│  ├── Freshness monitoring (stale table alerts)          │
│  ├── Completeness monitoring (missing data alerts)      │
│  ├── Exclude metadata tables (dq_rules)                 │
│  └── Non-blocking: if fails, Silver still works         │
└──────────────────────────────────────────────────────────┘
```

---

## The Complete Flow — Context Budget Over Time

```
Time ─────────────────────────────────────────────────────▶

Phase:  │   1   │   2   │  3  │     4      │  5  │  6  │  7  │

        ┌───────┬───────┬─────┬────────────┬─────┬─────┬─────┐
table   │███████│███████│█████│████████████│█████│█████│█████│
list    │       │       │     │            │     │     │     │
        ├───────┼───────┼─────┼────────────┼─────┼─────┼─────┤
expert  │███████│       │     │            │     │     │     │
agent   │       │       │     │            │     │     │     │
        ├───────┼───────┼─────┼────────────┼─────┼─────┼─────┤
schema  │███████│       │     │            │     │     │     │
mgmt    │       │disc.  │     │            │     │     │     │
        ├───────┼───────┼─────┼────────────┼─────┼─────┼─────┤
01-dlt  │       │███████│█████│████████████│     │     │     │
expect  │       │       │     │  (re-read) │disc.│     │     │
        ├───────┼───────┼─────┼────────────┼─────┼─────┼─────┤
table   │       │███████│     │████████████│     │     │     │
props   │       │       │     │  (re-read) │disc.│     │     │
        ├───────┼───────┼─────┼────────────┼─────┼─────┼─────┤
unity   │       │███████│     │            │     │     │     │
catalog │       │       │disc.│            │     │     │     │
        ├───────┼───────┼─────┼────────────┼─────┼─────┼─────┤
python  │       │       │█████│            │     │     │     │
imports │       │       │     │discarded   │     │     │     │
        ├───────┼───────┼─────┼────────────┼─────┼─────┼─────┤
asset   │       │       │     │            │     │█████│     │
bundles │       │       │     │            │     │     │disc.│
        ├───────┼───────┼─────┼────────────┼─────┼─────┼─────┤
anomaly │       │       │     │            │     │     │█████│
detect  │       │       │     │            │     │     │ opt │
        └───────┴───────┴─────┴────────────┴─────┴─────┴─────┘

 ███ = skill loaded    disc. = discarded
```

The Silver orchestrator has a flatter context curve than Gold Design or Semantic Layer — most phases load 1-2 common skills plus possibly the `dlt-expectations` worker. The peak is Phase 4 where DLT notebooks are created using patterns from both `dlt-expectations` and `table-properties`.

---

## The Skill Dependency Graph

Unlike the semantic layer's linear chain, the Silver orchestrator's dependencies form a tree where multiple phases re-read the same skills:

```
                    00-silver-layer-setup (orchestrator)
                    │
        ┌───────────┼───────────────────────────┐
        │           │                           │
  Worker Skills   Common Skills            References
        │           │                           │
  ┌─────┴─────┐    ├── expert-agent (Ph 1)     ├── silver-table-patterns
  │           │    ├── schema-mgmt  (Ph 1)     ├── monitoring-patterns
  │ 01-dlt-   │    ├── table-props  (Ph 2,4)   └── pipeline-configuration
  │ expect.   │    ├── unity-cat.   (Ph 2)
  │ (Ph 2-4)  │    ├── python-imp.  (Ph 3)
  │           │    ├── asset-bun.   (Ph 6)
  │ 02-dqx   │    └── autonomous-ops (Ph 4+)
  │ (optional)│
  └───────────┘

  Re-read pattern: dlt-expectations is used in Phases 2, 3, and 4
  (DQ table DDL → loader cache pattern → decorator patterns)
```

---

## Post-Completion: The Audit Trail

| # | Phase | Skill / Reference Read | Type | What It Was Used For |
|---|-------|----------------------|------|---------------------|
| 1 | Phase 1 | `skills/databricks-expert-agent/SKILL.md` | Common | Extraction principle for Bronze schema names |
| 2 | Phase 1 | `common/schema-management-patterns/SKILL.md` | Common | CREATE SCHEMA DDL with governance metadata |
| 3 | Phase 2 | `silver/01-dlt-expectations-patterns/SKILL.md` | Worker | DQ rules table DDL, rule population |
| 4 | Phase 2 | `common/databricks-table-properties/SKILL.md` | Common | Metadata table TBLPROPERTIES |
| 5 | Phase 2 | `common/unity-catalog-constraints/SKILL.md` | Common | PK constraint on dq_rules table |
| 6 | Phase 3 | `common/databricks-python-imports/SKILL.md` | Common | Pure Python loader (no notebook header) |
| 7 | Phase 4 | `silver/01-dlt-expectations-patterns/SKILL.md` | Worker | DLT decorator patterns (re-read) |
| 8 | Phase 4 | `common/databricks-table-properties/SKILL.md` | Common | Silver TBLPROPERTIES (re-read) |
| 9 | Phase 6 | `skills/databricks-asset-bundles/SKILL.md` | Common | Pipeline YAML, job YAML, serverless config |
| ... | ... | ... | ... | ... |

---

## Key Design Principles at Work

| # | Principle | How It's Applied |
|---|-----------|-----------------|
| 1 | **Schema cloning** | Silver mirrors Bronze column names/types. No restructuring. DQ rules are the value-add. |
| 2 | **DQ rules as data** | Rules stored in a Delta table, not hardcoded in notebooks. Updatable at runtime without redeploying pipelines. |
| 3 | **Deployment ordering** | DQ setup job must run BEFORE DLT pipeline. The orchestrator enforces this with a STOP gate and explicit deployment instructions. |
| 4 | **Pure Python loader** | `dq_rules_loader.py` has no notebook header — this enables `import` from DLT notebooks without `%run` or `sys.path` hacks. |
| 5 | **Legacy API by design** | `import dlt` is used because `@dlt.expect_all_or_drop()` decorators are not yet available in the modern `dp` API. |
| 6 | **Serverless everything** | Pipeline: `serverless: true`. Jobs: `environments` block. No cluster definitions anywhere. |
| 7 | **Row tracking for downstream** | Every Silver table has `delta.enableRowTracking: "true"` — without it, Gold materialized views cannot do incremental refresh. |

---

## Common Failure Modes

| Error | Root Cause | Fix |
|-------|-----------|-----|
| `Table or view not found: dq_rules` | DLT pipeline ran before DQ setup job | Run `silver_dq_setup_job` first |
| `ModuleNotFoundError: dq_rules_loader` | Loader file has notebook header | Remove `# Databricks notebook source` line |
| `Incompatible schema change` | Streaming table schema evolved | Trigger full refresh: `--full-refresh` |
| Aggregation in Silver notebook | Business logic belongs in Gold | Remove groupBy/agg, keep transaction grain |
| `cluster_by=["col1"]` in DLT table | Manual clustering instead of auto | Replace with `cluster_by_auto=True` |
| `from pyspark import pipelines as dp` | Modern API incompatible with DQ framework | Use `import dlt` |
| Missing row tracking | Downstream MVs do expensive full recompute | Add `delta.enableRowTracking: "true"` |

---

## What Happens Next

After the Silver layer is complete and deployed:

```
Silver Setup (this skill)
    │
    ▼
Gold Implementation (01-gold-layer-setup)
    → setup_tables.py creates Gold tables from YAML
    → merge_gold_tables.py reads Silver tables
    → FK constraints reference Silver-populated dimensions
```

The Silver tables created here become the direct input for the Gold merge scripts. Column names, types, and data quality guarantees established in this orchestrator carry forward as the contract that Gold implementation depends on.
