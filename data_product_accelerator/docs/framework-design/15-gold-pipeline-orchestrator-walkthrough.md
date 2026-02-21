# Gold Pipeline Orchestrator — Visual Walkthrough

How the `01-gold-layer-setup` orchestrator progressively loads 5 pipeline-worker skills across 6 phases, transforming YAML schema designs into production-ready Delta tables with MERGE scripts, FK constraints, and Asset Bundle jobs — all driven by extraction from YAML, never generation from memory.

> **Related skills:** [`01-gold-layer-setup`](../../skills/gold/01-gold-layer-setup/SKILL.md), [`01-yaml-table-setup`](../../skills/gold/pipeline-workers/01-yaml-table-setup/SKILL.md), [`02-merge-patterns`](../../skills/gold/pipeline-workers/02-merge-patterns/SKILL.md), [`03-deduplication`](../../skills/gold/pipeline-workers/03-deduplication/SKILL.md), [`04-grain-validation`](../../skills/gold/pipeline-workers/04-grain-validation/SKILL.md), [`05-schema-validation`](../../skills/gold/pipeline-workers/05-schema-validation/SKILL.md)
>
> **Predecessor:** [`00-gold-layer-design`](../../skills/gold/00-gold-layer-design/SKILL.md) — YAML schemas must exist before this skill runs

---

## The Agent's Journey Through the Gold Pipeline Orchestrator

### Step 0: Skill Activation (~100 tokens)

When a user says something like *"Implement the Gold layer from the YAML designs"*, the agent matches:

```yaml
name: gold-layer-setup
description: >
  End-to-end orchestrator for implementing Gold layer tables, merge scripts, FK constraints,
  and Asset Bundle jobs from YAML schema definitions...
```

Keywords "Gold layer", "YAML", "merge scripts", "FK constraints", "Asset Bundle" match. The agent reads the full SKILL.md (~530 lines).

### Step 1: The Prerequisite Check

Before anything else, the orchestrator verifies that the Gold Design phase is complete:

```
MANDATORY prerequisites from gold/00-gold-layer-design:
  ✅ YAML schema files in gold_layer_design/yaml/{domain}/*.yaml
  ✅ ERD documentation (erd_master.md)
  ✅ Column lineage documentation (COLUMN_LINEAGE.csv)

  ❌ Missing any of these → STOP. Run design skill first.
```

### Step 2: The Guard Rails Lock In

The Gold Pipeline orchestrator has 6 non-negotiable defaults plus the cardinal extraction rule:

| Default | Value | NEVER Do This Instead |
|---------|-------|-----------------------|
| **Serverless** | `environments:` block with `environment_key` | Never define `job_clusters:` |
| **Environments V4** | `environment_version: "4"` | Never omit or use older versions |
| **Auto Liquid Clustering** | `CLUSTER BY AUTO` | Never use `CLUSTER BY (col1, col2)` |
| **Change Data Feed** | `delta.enableChangeDataFeed: "true"` | Never omit |
| **Row Tracking** | `delta.enableRowTracking: "true"` | Never omit |
| **notebook_task** | `notebook_task:` with `base_parameters:` | Never use `python_task:` |

**The Cardinal Rule — Extraction Over Generation:**

```
EVERY value MUST be extracted from Gold YAML files or COLUMN_LINEAGE.csv.
NEVER generate, guess, or hardcode.

Extracted from YAML:  table names, column names/types, PKs, FKs,
                      business keys, grain types, SCD types,
                      source Silver tables, column mappings

Coded by hand:        ONLY aggregation expressions and derived
                      column formulas (business logic)
```

This is the single most important constraint in the entire orchestrator — it prevents hallucinated table/column names that would cause runtime failures.

### Step 3: The Progressive Disclosure Protocol

```
Read skills ONLY when entering the phase that needs them:
  Phase 0: No skills — run validation script
  Phase 1: Read 01-yaml-table-setup + table-properties + unity-catalog + schema-mgmt
  Phase 2: Read 02-merge-patterns + 03-deduplication + 04-grain-validation +
           05-schema-validation + python-imports
  Phase 3: Read asset-bundles → work → persist notes → DISCARD all
  Phase 4-5: User-triggered deployment and validation
```

**At each phase boundary, the agent's working memory should contain ONLY:**
1. Table inventory dict (extracted from YAML in Phase 1 — persists through all phases)
2. Previous phase's summary note
3. Current phase's worker skills (read just-in-time)

---

## Phase 0: Upstream Contract Validation — The Pre-Flight Check

Before writing a single line of implementation code, the agent validates that all Silver → Gold column mappings are correct. This catches the most common source of iteration.

```
┌──────────────────────────────────────────────────────────┐
│                      PHASE 0                             │
│                                                          │
│  No worker skills needed — runs validation script        │
│                                                          │
│  Execute: scripts/validate_upstream_contracts.py         │
│                                                          │
│  For each Gold YAML file:                               │
│  ┌─────────────────────────────────────────┐            │
│  │ dim_customer.yaml                        │            │
│  │   lineage:                               │            │
│  │     customer_name:                       │            │
│  │       silver_table: silver_customers     │            │
│  │       silver_column: cust_name           │            │
│  │                                          │            │
│  │ Check: does silver_customers.cust_name   │            │
│  │        actually exist in the catalog?    │            │
│  │                                          │            │
│  │ ✅ PASSED — column exists                │            │
│  │ ❌ FAILED — fix YAML before proceeding   │            │
│  └─────────────────────────────────────────┘            │
│                                                          │
│  GATE: ALL contracts must show PASSED                   │
│  Backup: merge template also embeds this check as       │
│  fail-fast in main()                                     │
│                                                          │
│  📝 Persist: pass/fail per table, any YAML fixes         │
└──────────────────────────────────────────────────────────┘
```

---

## Phase 1: YAML-Driven Table Creation

The agent creates a single generic script that reads ALL YAML files and generates tables dynamically — no table-specific code.

```
┌──────────────────────────────────────────────────────────┐
│                      PHASE 1                             │
│                                                          │
│  Working Memory:                                         │
│  ┌──────────────────────────────┐                       │
│  │ Phase 0 notes (pass/fail)    │                       │
│  │ 01-yaml-table-setup SKILL    │ ← READ now (worker)   │
│  │ table-properties SKILL       │ ← READ now (common)   │
│  │ unity-catalog-constraints    │ ← READ now (common)   │
│  │ schema-management-patterns   │ ← READ now (common)   │
│  └──────────────────────────────┘                       │
│                                                          │
│  Creates: setup_tables.py (generic, reads YAML)         │
│  ┌─────────────────────────────────────────┐            │
│  │                                          │            │
│  │  def find_yaml_base():                  │            │
│  │      # Discover YAML directory           │            │
│  │      # (synced via databricks.yml)       │            │
│  │                                          │            │
│  │  For each *.yaml in yaml/**/:           │            │
│  │  ┌────────────────────────────────┐     │            │
│  │  │ 1. Parse YAML → table_name,    │     │            │
│  │  │    columns, PKs, FKs, props    │     │            │
│  │  │                                │     │            │
│  │  │ 2. Build DDL dynamically:      │     │            │
│  │  │    CREATE OR REPLACE TABLE     │     │            │
│  │  │    {catalog}.{gold_schema}.    │     │            │
│  │  │    {table_name} (              │     │            │
│  │  │      {col} {type} {NOT NULL},  │     │            │
│  │  │      ...                       │     │            │
│  │  │    )                           │     │            │
│  │  │    CLUSTER BY AUTO     🔴      │     │            │
│  │  │    TBLPROPERTIES (...)  🔴      │     │            │
│  │  │                                │     │            │
│  │  │ 3. Apply PK constraint:        │     │            │
│  │  │    ALTER TABLE ADD CONSTRAINT  │     │            │
│  │  │    pk_{table} PRIMARY KEY      │     │            │
│  │  │    ({pk_cols}) NOT ENFORCED    │     │            │
│  │  └────────────────────────────────┘     │            │
│  └─────────────────────────────────────────┘            │
│                                                          │
│  Creates: add_fk_constraints.py                         │
│  ┌─────────────────────────────────────────┐            │
│  │ Runs AFTER all PKs exist:               │            │
│  │ ALTER TABLE ADD CONSTRAINT              │            │
│  │   fk_{table}_{col} FOREIGN KEY ({col})  │            │
│  │   REFERENCES {ref_table}({ref_col})     │            │
│  │   NOT ENFORCED                          │            │
│  └─────────────────────────────────────────┘            │
│                                                          │
│  📝 Persist: table inventory dict, YAML base path,      │
│     count of tables, any FK failures                     │
│                                                          │
│  🗑️ DISCARD: Phase 1 skills (keep table inventory)     │
└──────────────────────────────────────────────────────────┘
```

### Phase 1b: Advanced Setup Patterns (If Applicable)

```
┌──────────────────────────────────────────────────────────┐
│                    PHASE 1b (optional)                    │
│                                                          │
│  Execution order matters:                               │
│                                                          │
│  1. Create tables ───────── Phase 1                     │
│  2. Apply PKs ───────────── Phase 1                     │
│  3. Role-playing views ──── Phase 1b                    │
│     dim_date → dim_order_date, dim_ship_date            │
│  4. Unknown member rows ─── Phase 1b                    │
│     INSERT (-1, "Unknown", ...) per dimension           │
│  5. Apply FKs ───────────── Phase 1                     │
│  6. Run merge ───────────── Phase 2                     │
│                                                          │
│  ⚠️ Unknown members BEFORE FKs — prevents NULL FKs     │
│     for late-arriving facts                              │
└──────────────────────────────────────────────────────────┘
```

---

## Phase 2: MERGE Script Implementation — The Core Build

This is the longest and most complex phase (~2 hours). The agent loads 4 worker skills simultaneously and builds merge logic for every table.

```
┌──────────────────────────────────────────────────────────┐
│                      PHASE 2                             │
│                                                          │
│  Working Memory:                                         │
│  ┌──────────────────────────────┐                       │
│  │ table_inventory (Phase 1)    │ ← persists forever    │
│  │ Phase 1 notes (paths, PKs)   │                       │
│  │ 02-merge-patterns SKILL      │ ← READ now            │
│  │ 03-deduplication SKILL       │ ← READ now            │
│  │ 04-grain-validation SKILL    │ ← READ now            │
│  │ 05-schema-validation SKILL   │ ← READ now            │
│  │ python-imports SKILL         │ ← READ now (common)   │
│  │ references/advanced-merge    │                       │
│  │ references/design-to-pipeline│                       │
│  └──────────────────────────────┘                       │
│  ⚠️ Peak context load of the orchestrator               │
│                                                          │
│  Step 0 — EXTRACTION FIRST (before any code):           │
│  ┌─────────────────────────────────────────┐            │
│  │ For each YAML file:                      │            │
│  │   meta = load_table_metadata(yaml_path)  │            │
│  │   → table_name, pk_columns, business_key │            │
│  │   → scd_type, grain, columns, lineage    │            │
│  │                                          │            │
│  │ Load COLUMN_LINEAGE.csv:                 │            │
│  │   mappings = load_column_mappings()      │            │
│  │   → silver_col → gold_col renames        │            │
│  │                                          │            │
│  │ Build column expressions automatically:  │            │
│  │   build_column_expressions(meta)         │            │
│  │   → automates ~70% of .withColumn() calls│            │
│  └─────────────────────────────────────────┘            │
│                                                          │
│  For each DIMENSION table:                              │
│  ┌─────────────────────────────────────────┐            │
│  │ 1. Check dimension_pattern from YAML:    │            │
│  │    ├── role_playing → no merge (views)   │            │
│  │    ├── junk → use junk-populate template │            │
│  │    └── standard → SCD merge below        │            │
│  │                                          │            │
│  │ 2. DEDUPLICATE (MANDATORY — from 03):    │            │
│  │    .orderBy(col("processed_timestamp")   │            │
│  │      .desc())                            │            │
│  │    .dropDuplicates(meta["business_key"]) │            │
│  │                                          │            │
│  │ 3. Map columns (from YAML lineage):      │            │
│  │    .withColumn(gold_col, col(silver_col))│            │
│  │                                          │            │
│  │ 4. Generate surrogate key:               │            │
│  │    md5(concat_ws("||", *business_key))   │            │
│  │                                          │            │
│  │ 5. SCD columns (if scd_type == "scd2"):  │            │
│  │    effective_from, effective_to, is_curr  │            │
│  │                                          │            │
│  │ 6. validate_merge_schema() (from 05)     │            │
│  │                                          │            │
│  │ 7. MERGE on business_key (from YAML)     │            │
│  └─────────────────────────────────────────┘            │
│                                                          │
│  For each FACT table:                                   │
│  ┌─────────────────────────────────────────┐            │
│  │ 1. Check grain_type from YAML:           │            │
│  │    ├── accumulating_snapshot → template   │            │
│  │    ├── factless → INSERT only            │            │
│  │    ├── periodic_snapshot → period replace│            │
│  │    └── standard → aggregate merge below  │            │
│  │                                          │            │
│  │ 2. Aggregate to match grain:             │            │
│  │    .groupBy(meta["pk_columns"])          │            │
│  │    .agg(spark_sum(...), ...)             │            │
│  │    ← spark_sum, not sum (shadows!)       │            │
│  │                                          │            │
│  │ 3. Validate grain (from 04):             │            │
│  │    One row per PK combination            │            │
│  │                                          │            │
│  │ 4. validate_merge_schema() (from 05)     │            │
│  │                                          │            │
│  │ 5. MERGE on pk_columns (from YAML)       │            │
│  └─────────────────────────────────────────┘            │
│                                                          │
│  ⚠️ Merge dimensions FIRST, then facts                  │
│     (dependency order from YAML foreign_keys)            │
│                                                          │
│  📝 Persist: merge function inventory (which tables     │
│     use SCD1 vs SCD2, aggregated vs transaction),       │
│     any column mapping issues                            │
│                                                          │
│  🗑️ DISCARD: All 4 worker skills + references          │
└──────────────────────────────────────────────────────────┘
```

---

## Phase 3: Asset Bundle Configuration

```
┌──────────────────────────────────────────────────────────┐
│                      PHASE 3                             │
│                                                          │
│  Working Memory:                                         │
│  ┌──────────────────────────────┐                       │
│  │ table_inventory              │                       │
│  │ Phase 2 notes (merge inv.)   │                       │
│  │ asset-bundles SKILL.md       │ ← READ now            │
│  └──────────────────────────────┘                       │
│  (Phase 2 skills GONE — 2000+ lines freed)              │
│                                                          │
│  Creates two job configurations:                        │
│                                                          │
│  gold_setup_job.yml                                     │
│  ┌────────────────────────────────────────────┐         │
│  │  tasks:                                     │         │
│  │   ┌──────────────────────────┐              │         │
│  │   │ setup_gold_tables        │──┐           │         │
│  │   │ (notebook_task)          │  │           │         │
│  │   │ base_parameters:         │  │           │         │
│  │   │   catalog, gold_schema   │  │           │         │
│  │   └──────────────────────────┘  │           │         │
│  │                    depends_on ──▼           │         │
│  │   ┌──────────────────────────┐              │         │
│  │   │ add_fk_constraints       │              │         │
│  │   │ (notebook_task)          │              │         │
│  │   └──────────────────────────┘              │         │
│  └────────────────────────────────────────────┘         │
│                                                          │
│  gold_merge_job.yml                                     │
│  ┌────────────────────────────────────────────┐         │
│  │  tasks:                                     │         │
│  │   ┌──────────────────────────┐              │         │
│  │   │ merge_gold_tables        │              │         │
│  │   │ (notebook_task)          │              │         │
│  │   │ base_parameters:         │              │         │
│  │   │   catalog, gold_schema,  │              │         │
│  │   │   source_schema          │              │         │
│  │   └──────────────────────────┘              │         │
│  │  schedule: (PAUSED in dev, enabled in prod) │         │
│  └────────────────────────────────────────────┘         │
│                                                          │
│  Updates databricks.yml:                                │
│  ├── sync: gold_layer_design/yaml/**/*.yaml             │
│  │   ⚠️ CRITICAL — without sync, setup_tables.py       │
│  │      cannot find YAML schemas on the cluster!        │
│  ├── resources: gold_setup_job.yml, gold_merge_job.yml  │
│  └── environments: serverless + PyYAML dependency       │
│                                                          │
│  📝 Persist: job YAML paths, databricks.yml sync status │
│  🗑️ DISCARD: asset-bundles SKILL.md                    │
└──────────────────────────────────────────────────────────┘
```

---

## STOP — Artifact Creation Complete

```
┌──────────────────────────────────────────────────────────┐
│                   🛑 STOP GATE                           │
│                                                          │
│  Phases 0-3 complete. All scripts and jobs created:     │
│                                                          │
│  src/{project}_gold/                                    │
│  ├── setup_tables.py          (Phase 1 — generic YAML)  │
│  ├── add_fk_constraints.py    (Phase 1 — FK application) │
│  └── merge_gold_tables.py     (Phase 2 — all merges)    │
│                                                          │
│  resources/gold/                                        │
│  ├── gold_setup_job.yml       (Phase 3 — setup + FK)    │
│  └── gold_merge_job.yml       (Phase 3 — periodic merge) │
│                                                          │
│  ⚠️ Do NOT deploy unless user explicitly requests it    │
└──────────────────────────────────────────────────────────┘
```

---

## Phase 4: Deployment (User-Triggered Only)

```
┌──────────────────────────────────────────────────────────┐
│                      PHASE 4                             │
│                                                          │
│  $ databricks bundle deploy -t dev                      │
│                                                          │
│  Step 1: Setup job (creates tables from YAML)           │
│  ┌──────────────────────┐                               │
│  │ setup_gold_tables    │──┐                            │
│  │ (reads YAML → DDL)   │  │ depends_on                 │
│  └──────────────────────┘  ▼                            │
│  ┌──────────────────────┐                               │
│  │ add_fk_constraints   │                               │
│  │ (ALTER TABLE FK)     │                               │
│  └──────────────────────┘                               │
│                                                          │
│  Step 2: Verify tables                                  │
│  ├── SHOW TABLES IN {catalog}.{gold_schema}             │
│  ├── SHOW CREATE TABLE ... (verify PKs)                 │
│  └── DESCRIBE TABLE EXTENDED ... (verify FKs)           │
│                                                          │
│  Step 3: Merge job (Silver → Gold)                      │
│  ┌──────────────────────┐                               │
│  │ merge_gold_tables    │                               │
│  │ (dims first, then    │                               │
│  │  facts — dependency  │                               │
│  │  order from YAML FK) │                               │
│  └──────────────────────┘                               │
│                                                          │
│  Step 4: Verify data                                    │
│  ├── Record counts per table                            │
│  ├── Grain validation (no PK duplicates)                │
│  ├── FK integrity (no orphaned references)              │
│  └── SCD Type 2 checks (one is_current=true per BK)    │
│                                                          │
│  On failure → databricks-autonomous-operations:          │
│  diagnose → fix → redeploy loop                         │
└──────────────────────────────────────────────────────────┘
```

---

## Phase 4b: Anomaly Detection (User-Triggered)

```
┌──────────────────────────────────────────────────────────┐
│                    PHASE 4b (optional)                    │
│                                                          │
│  Read: monitoring/04-anomaly-detection/SKILL.md          │
│                                                          │
│  Enable schema-level anomaly detection on Gold schema:  │
│  ├── Freshness monitoring (stale Gold table alerts)     │
│  ├── Completeness monitoring (missing data alerts)      │
│  ├── No exclusions — all Gold tables monitored          │
│  └── Non-blocking: if fails, deployment continues       │
└──────────────────────────────────────────────────────────┘
```

---

## Phase 5: Post-Implementation Validation (User-Triggered)

```
┌──────────────────────────────────────────────────────────┐
│                      PHASE 5                             │
│                                                          │
│  Read: design-workers/05-erd-diagrams/SKILL.md           │
│  (cross-reference created tables against ERD)            │
│                                                          │
│  Validation matrix:                                     │
│  ┌─────────────────────────────────────────┐            │
│  │                                          │            │
│  │  ERD ◄────────► Created Tables           │            │
│  │   │  consistency    │                    │            │
│  │   │  check          │                    │            │
│  │   ▼                 ▼                    │            │
│  │  YAML ◄────────► DataFrame Schema        │            │
│  │   │                 │                    │            │
│  │   ▼                 ▼                    │            │
│  │  Lineage ◄──── Silver Source Tables      │            │
│  │                                          │            │
│  │ ✅ All ERD entities have tables          │            │
│  │ ✅ DataFrame columns match DDL           │            │
│  │ ✅ No PK duplicates (grain valid)        │            │
│  │ ✅ No orphaned FK references             │            │
│  │ ✅ SCD2: one is_current=true per BK      │            │
│  │ ✅ Audit timestamps populated            │            │
│  │ ✅ Conformed dims identical across facts  │            │
│  │ ✅ Advanced patterns validated            │            │
│  └─────────────────────────────────────────┘            │
└──────────────────────────────────────────────────────────┘
```

---

## The Complete Flow — Context Budget Over Time

```
Time ─────────────────────────────────────────────────────────▶

Phase:  │  0  │     1      │        2         │   3   │ 4 │ 5 │

        ┌─────┬────────────┬──────────────────┬───────┬───┬───┐
table   │     │████████████│██████████████████│███████│███│███│
inv     │     │  (built)   │                  │       │   │   │
        ├─────┼────────────┼──────────────────┼───────┼───┼───┤
valid.  │█████│            │                  │       │   │   │
script  │     │            │                  │       │   │   │
        ├─────┼────────────┼──────────────────┼───────┼───┼───┤
01-yaml │     │████████████│                  │       │   │   │
setup   │     │            │  discarded       │       │   │   │
        ├─────┼────────────┼──────────────────┼───────┼───┼───┤
tbl-    │     │████████████│                  │       │   │   │
props   │     │            │  discarded       │       │   │   │
        ├─────┼────────────┼──────────────────┼───────┼───┼───┤
unity   │     │████████████│                  │       │   │   │
-cat    │     │            │  discarded       │       │   │   │
        ├─────┼────────────┼──────────────────┼───────┼───┼───┤
schema  │     │████████████│                  │       │   │   │
-mgmt   │     │            │  discarded       │       │   │   │
        ├─────┼────────────┼──────────────────┼───────┼───┼───┤
02-     │     │            │██████████████████│       │   │   │
merge   │     │            │                  │disc.  │   │   │
        ├─────┼────────────┼──────────────────┼───────┼───┼───┤
03-     │     │            │██████████████████│       │   │   │
dedup   │     │            │                  │disc.  │   │   │
        ├─────┼────────────┼──────────────────┼───────┼───┼───┤
04-     │     │            │██████████████████│       │   │   │
grain   │     │            │                  │disc.  │   │   │
        ├─────┼────────────┼──────────────────┼───────┼───┼───┤
05-     │     │            │██████████████████│       │   │   │
schema  │     │            │                  │disc.  │   │   │
        ├─────┼────────────┼──────────────────┼───────┼───┼───┤
asset   │     │            │                  │███████│   │   │
bundles │     │            │                  │       │d. │   │
        ├─────┼────────────┼──────────────────┼───────┼───┼───┤
phase   │     │            │░░░░░░░░░░░░░░░░░░│░░░░░░░│░░░│░░░│
notes   │     │  created → │    (10 lines)    │       │   │   │
        └─────┴────────────┴──────────────────┴───────┴───┴───┘

 ███ = full skill loaded    ░░░ = compact notes (5-10 lines)
```

The Gold Pipeline orchestrator has two distinct peaks:
- **Phase 1:** 1 worker + 3 common skills (table creation)
- **Phase 2:** 4 worker + 1 common skill + 2 references (merge implementation)

Phase 2 is the most skill-intensive phase in the entire orchestrator, but the skills are tightly focused on merge-specific concerns (deduplication, grain, schema validation) and work together as a cohesive unit.

---

## The Pipeline Worker Chain

The 5 pipeline-worker skills form a logical chain that mirrors the merge script's execution order:

```
Phase 0: validate_upstream_contracts.py (no skill)
  └─ Silver → Gold column contract validation
          │
          ▼
Phase 1: 01-yaml-table-setup
  └─ YAML → DDL generation, table creation, PK/FK constraints
     "Pipeline Notes to Carry Forward":
     - Table inventory dict (names, PKs, FKs, domains)
     - YAML base path for runtime discovery
     - Any constraint failures
          │
          ▼
Phase 2: 02-merge-patterns (consumed simultaneously with 03, 04, 05)
  └─ SCD Type 1/2 dimension merges, fact aggregation merges
     02-merge: Column mapping, merge conditions, SCD logic
     03-dedup: ALWAYS deduplicate Silver before MERGE
     04-grain: Validate one row per PK after aggregation
     05-schema: Validate DataFrame matches DDL before MERGE
     "Pipeline Notes to Carry Forward":
     - Merge function inventory (SCD1 vs SCD2, agg vs txn)
     - Execution order (dims first, then facts)
     - Any column mapping issues
          │
          ▼
Phase 3: common/databricks-asset-bundles
  └─ Job YAML, databricks.yml sync, serverless config
          │
          ▼
Phase 4-5: Deployment and validation (user-triggered)
```

---

## The Extraction Flow — YAML as Single Source of Truth

This diagram shows how data flows from YAML into every generated artifact:

```
                    gold_layer_design/yaml/{domain}/{table}.yaml
                    │
                    │ parse
                    ▼
            ┌───────────────────┐
            │  table_inventory  │ (in-memory dict)
            │  dict             │
            └───────┬───────────┘
                    │
        ┌───────────┼───────────────┬──────────────────────┐
        │           │               │                      │
        ▼           ▼               ▼                      ▼
  setup_tables.py  add_fk_       merge_gold_          gold_*_job.yml
  ├── table_name   constraints   tables.py            ├── notebook_path
  ├── columns      ├── FKs      ├── pk_columns        ├── base_parameters
  ├── types        └── refs     ├── business_key       └── schedule
  ├── PKs                       ├── scd_type
  ├── TBLPROPS                  ├── grain
  └── CLUSTER BY                ├── column mappings
     AUTO                       └── merge conditions
                                         │
                                         │ also reads
                                         ▼
                                COLUMN_LINEAGE.csv
                                ├── silver_col → gold_col
                                └── transformation_type
```

Every arrow represents an extraction operation — the agent reads YAML metadata and builds code from it. The only hand-coded elements are aggregation expressions and derived column formulas (business logic).

---

## Post-Completion: The Audit Trail

| # | Phase | Skill / Reference Read | Type | What It Was Used For |
|---|-------|----------------------|------|---------------------|
| 1 | Phase 0 | `scripts/validate_upstream_contracts.py` | Script | Pre-flight Silver column validation |
| 2 | Phase 1 | `pipeline-workers/01-yaml-table-setup/SKILL.md` | Worker | YAML-to-DDL, find_yaml_base(), PKs |
| 3 | Phase 1 | `common/databricks-table-properties/SKILL.md` | Common | Gold TBLPROPERTIES (CDF, row tracking) |
| 4 | Phase 1 | `common/unity-catalog-constraints/SKILL.md` | Common | PK/FK ALTER TABLE syntax |
| 5 | Phase 1 | `common/schema-management-patterns/SKILL.md` | Common | CREATE SCHEMA IF NOT EXISTS |
| 6 | Phase 2 | `pipeline-workers/02-merge-patterns/SKILL.md` | Worker | SCD1/2, fact aggregation, column mapping |
| 7 | Phase 2 | `pipeline-workers/03-deduplication/SKILL.md` | Worker | Mandatory dedup before MERGE |
| 8 | Phase 2 | `pipeline-workers/04-grain-validation/SKILL.md` | Worker | PK-based grain validation |
| 9 | Phase 2 | `pipeline-workers/05-schema-validation/SKILL.md` | Worker | DataFrame↔DDL schema checks |
| 10 | Phase 2 | `common/databricks-python-imports/SKILL.md` | Common | Pure Python modules, no sys.path |
| 11 | Phase 3 | `common/databricks-asset-bundles/SKILL.md` | Common | Job YAML, serverless, notebook_task |
| ... | ... | ... | ... | ... |

---

## Key Design Principles at Work

| # | Principle | How It's Applied |
|---|-----------|-----------------|
| 1 | **YAML as single source of truth** | Every table name, column, PK, FK, SCD type, and grain extracted from YAML at runtime. No hardcoded values. |
| 2 | **Extraction over generation** | `load_table_metadata()` and `load_column_mappings()` replace manual coding. ~70% of column expressions auto-generated from YAML lineage. |
| 3 | **Mandatory deduplication** | EVERY merge function deduplicates Silver before MERGE. Prevents `DELTA_MULTIPLE_SOURCE_ROW_MATCHING_TARGET_ROW_IN_MERGE`. |
| 4 | **Triple validation before merge** | Schema validation (DataFrame matches DDL), grain validation (no PK duplicates), upstream contract validation (Silver columns exist). |
| 5 | **Dimensions before facts** | Merge execution order derived from YAML FK references — dimensions first so fact FKs can reference populated dim PKs. |
| 6 | **Generic scripts, no table-specific code** | `setup_tables.py` creates ALL tables from YAML. Adding a table = adding a YAML file, not editing Python. |
| 7 | **Pre-flight contract validation** | Phase 0 catches Silver column mismatches before any code is written — the most common source of iteration. |

---

## Common Failure Modes

| Error | Root Cause | Fix |
|-------|-----------|-----|
| `FileNotFoundError: gold_layer_design/yaml/` | YAML files not synced in `databricks.yml` | Add `gold_layer_design/yaml/**/*.yaml` to sync paths |
| `ModuleNotFoundError: yaml` | PyYAML not in job environment | Add `pyyaml>=6.0` to environment spec |
| `DELTA_MULTIPLE_SOURCE_ROW_MATCHING` | Deduplication skipped before MERGE | Add `.dropDuplicates(business_key)` |
| `UNRESOLVED_COLUMN` | Column name hardcoded instead of extracted from YAML | Use `load_column_mappings()` from YAML lineage |
| Grain duplicates after merge | Aggregation didn't match PK grain | Verify `.groupBy()` uses exact PK columns from YAML |
| FK constraint failure | Referenced table/column doesn't exist yet | Run setup job (creates all tables) before FK application |
| Silver column mismatch | YAML lineage references wrong Silver column | Run Phase 0 validation, fix YAML, re-run |

---

## What Happens Next

After Gold implementation is complete and validated:

```
Gold Pipeline (this skill)
    │
    ▼
Project Planning (00-project-planning)
    → Plan semantic layer, observability, ML, GenAI phases
    → Emit YAML manifests consumed by downstream stages
    │
    ├──▶ Semantic Layer Setup (00-semantic-layer-setup)
    │    → Metric Views from Gold tables
    │    → TVFs for Genie integration
    │    → Genie Spaces with benchmark questions
    │
    ├──▶ Observability Setup (00-observability-setup)
    │    → Lakehouse Monitoring metrics
    │    → Anomaly detection baselines
    │
    └──▶ ML / GenAI stages
```

The Gold tables, PKs, FKs, and column descriptions created by this orchestrator become the foundation for the semantic layer (Metric Views reference Gold table schemas) and Genie Spaces (column comments drive natural language understanding).
