# Gold Design Orchestrator — Visual Walkthrough

How the `00-gold-layer-design` orchestrator progressively loads 7 design-worker skills across 10 phases, transforms a raw schema CSV into a complete dimensional model with ERDs, YAML schemas, lineage documentation, and a business onboarding guide.

> **Related skills:** [`00-gold-layer-design`](../../skills/gold/00-gold-layer-design/SKILL.md), [`01-grain-definition`](../../skills/gold/design-workers/01-grain-definition/SKILL.md), [`02-dimension-patterns`](../../skills/gold/design-workers/02-dimension-patterns/SKILL.md), [`03-fact-table-patterns`](../../skills/gold/design-workers/03-fact-table-patterns/SKILL.md), [`04-conformed-dimensions`](../../skills/gold/design-workers/04-conformed-dimensions/SKILL.md), [`05-erd-diagrams`](../../skills/gold/design-workers/05-erd-diagrams/SKILL.md), [`06-table-documentation`](../../skills/gold/design-workers/06-table-documentation/SKILL.md), [`07-design-validation`](../../skills/gold/design-workers/07-design-validation/SKILL.md)

---

## The Agent's Journey Through the Gold Design Orchestrator

### Step 0: Skill Activation (~100 tokens)

When a user says something like *"Design the Gold layer for my project"*, the agent framework matches the `description` field:

```yaml
name: gold-layer-design
description: >
  End-to-end orchestrator for designing complete Gold layer schemas with ERDs, YAML files,
  lineage tracking, and comprehensive business documentation...
```

Keywords "Gold layer", "ERDs", "YAML schemas", "dimensional modeling" match. The agent activates this skill and reads the full SKILL.md (~519 lines).

### Step 1: The Decision — What ERD Strategy?

The orchestrator's first structural decision is based on table count. This determines how many ERD files are created:

| Tables | Strategy | Deliverables |
|--------|----------|-------------|
| 1-8 | Master only | `erd_master.md` |
| 9-20 | Master + Domain | `erd_master.md` + `erd/erd_{domain}.md` |
| 20+ | Master + Domain + Summary | All three tiers |

The agent won't know the table count until Phase 0 (schema intake), so this decision is deferred — but the decision tree is internalized now.

### Step 2: The Guard Rails Lock In

Before any design work, the agent absorbs the **Non-Negotiable Defaults** that every YAML schema must encode:

| Default | YAML Location | Value | NEVER Do This Instead |
|---------|---------------|-------|----------------------|
| **Auto Liquid Clustering** | `clustering:` | `auto` | Never specify column names or omit |
| **Change Data Feed** | `table_properties:` | `delta.enableChangeDataFeed: "true"` | Never omit |
| **Row Tracking** | `table_properties:` | `delta.enableRowTracking: "true"` | Never omit |
| **Auto-Optimize** | `table_properties:` | `optimizeWrite` + `autoCompact` = `"true"` | Never omit |
| **Layer Tag** | `table_properties:` | `layer: "gold"` | Never omit or use wrong layer |
| **PK NOT NULL** | `columns:` | `nullable: false` on all PK columns | Never leave PK nullable |

These constraints propagate through every YAML file generated in Phase 4.

### Step 3: The Progressive Disclosure Protocol

The orchestrator manages 7 worker skills across 10 phases over 4-8 hours. The meta-strategy:

```
DO NOT read all design-worker skills at the start. Read each ONLY at the indicated phase:
  Phase 2: Read 01-grain-definition → 02-dimension-patterns → 03-fact-table-patterns → 04-conformed-dimensions
  Phase 3: Read 05-erd-diagrams → work → persist notes → DISCARD
  Phase 4: Read 06-table-documentation → work → persist notes → DISCARD
  Phase 8: Read 07-design-validation → work → done
```

Phase 2 is the exception — it loads 4 skills simultaneously because dimensional modeling requires grain, dimension, fact, and conformance knowledge together. All other phases load one skill at a time.

**At each phase boundary, the agent's working memory should contain ONLY:**
1. Table inventory dict (from Phase 0 — persists through all phases)
2. Previous phase's summary note (~5-10 lines)
3. Current phase's worker skill (read just-in-time)

---

## Phase 0: Source Schema Intake — The Foundation

The entry point for the entire data platform build. A customer provides a schema CSV, and the agent parses it into the structural foundation for everything that follows.

```
┌─────────────────────────────────────────────────────────┐
│                      PHASE 0                            │
│                                                         │
│  Input: context/{ProjectName}_Schema.csv                │
│  (table_catalog, table_schema, table_name,              │
│   column_name, data_type, is_nullable, comment)         │
│                                                         │
│  1. parse_schema_csv(csv_path)                          │
│     → {table_name: {columns: [...], types: [...]}}      │
│                                                         │
│  2. classify_tables(schema)                             │
│     ├── bridge: ≤3 cols AND 2+ FK-like cols             │
│     ├── fact: 2+ FK cols AND numeric measures           │
│     └── dimension: everything else                      │
│                                                         │
│  3. infer_relationships(classified)                     │
│     ├── Pattern 1: comment "Foreign Key to 'X'"        │
│     └── Pattern 2: column name matches table name      │
│                                                         │
│  4. GATE: table_inventory must be non-empty             │
│                                                         │
│  📝 Persist: table_inventory dict, entity               │
│     classifications, FK relationships,                  │
│     suggested domains, table count                      │
└─────────────────────────────────────────────────────────┘
```

The `table_inventory` is the **anti-hallucination anchor** — every table and column name the agent uses in ALL subsequent phases must come from this parsed CSV, never invented.

```python
table_inventory = {
    "transactions": {
        "columns": {"transaction_id": "BIGINT", "store_id": "INT", "amount": "DECIMAL", ...},
        "classification": "fact",
        "pk_candidates": ["transaction_id"],
        "fk_columns": ["store_id", "product_id", "customer_id"],
        "measures": ["amount", "quantity", "discount"]
    },
    "stores": {
        "columns": {"store_id": "INT", "store_name": "STRING", ...},
        "classification": "dimension",
        "pk_candidates": ["store_id"],
        "fk_columns": [],
        "measures": []
    }
}
```

---

## Phase 1: Requirements Gathering

No worker skill needed — the agent collects project context enriched by Phase 0's schema analysis.

```
┌──────────────────────────────────────────────────────────┐
│                      PHASE 1                             │
│                                                          │
│  Working Memory:                                         │
│  ┌──────────────────────────────┐                       │
│  │ table_inventory (Phase 0)    │ ← persists forever    │
│  │ Phase 0 notes (count, types) │                       │
│  └──────────────────────────────┘                       │
│                                                          │
│  Collect project context:                                │
│  ┌─────────────────────────────────────────┐            │
│  │ Project Name:   wanderbricks_analytics  │            │
│  │ Source Schema:  wanderbricks             │            │
│  │ Gold Schema:    wanderbricks_gold        │            │
│  │ Business Domain: travel, hospitality     │            │
│  │ Use Cases:      booking analytics, ...   │            │
│  │ Stakeholders:   Revenue Ops, Marketing   │            │
│  │ Table Count:    15 (8 dim, 5 fact, 2 br) │            │
│  │ FK Relations:   12 inferred (Phase 0)    │            │
│  └─────────────────────────────────────────┘            │
│                                                          │
│  📝 Persist: project context doc, schema names,          │
│     domain assignments, reporting requirements           │
└──────────────────────────────────────────────────────────┘
```

---

## Phase 2: Dimensional Modeling — The Design Core

This is the skill-intensive phase where 4 worker skills load simultaneously. The agent needs grain, dimension, fact, and conformance knowledge together because they are deeply interrelated.

```
┌──────────────────────────────────────────────────────────┐
│                      PHASE 2                             │
│                                                          │
│  Working Memory:                                         │
│  ┌──────────────────────────────┐                       │
│  │ table_inventory (Phase 0)    │ ← still here          │
│  │ Phase 1 notes (context)      │                       │
│  │ 01-grain-definition SKILL    │ ← READ now            │
│  │ 02-dimension-patterns SKILL  │ ← READ now            │
│  │ 03-fact-table-patterns SKILL │ ← READ now            │
│  │ 04-conformed-dimensions SKILL│ ← READ now            │
│  └──────────────────────────────┘                       │
│  ⚠️ Peak context load: ~2000 lines of skill content     │
│                                                          │
│  For each table in table_inventory:                     │
│  ┌─────────────────────────────────────────┐            │
│  │ Dimensions:                              │            │
│  │  1. Identify SCD type (1 vs 2)          │            │
│  │  2. Apply patterns: role-playing, junk,  │            │
│  │     degenerate, mini-dim, hierarchy      │            │
│  │  3. Define business key                  │            │
│  │  4. Plan NULL handling (Unknown rows)    │            │
│  ├─────────────────────────────────────────┤            │
│  │ Facts:                                   │            │
│  │  1. Infer grain from PK structure        │            │
│  │     (transaction / aggregated / snapshot) │            │
│  │  2. Classify measures (additive /         │            │
│  │     semi-additive / non-additive)         │            │
│  │  3. Identify factless / accumulating      │            │
│  │  4. Document grain explicitly             │            │
│  ├─────────────────────────────────────────┤            │
│  │ Enterprise Integration:                  │            │
│  │  1. Build bus matrix (facts × dims)      │            │
│  │  2. Identify conformed dimensions        │            │
│  │  3. Plan drill-across queries            │            │
│  │  4. Assign tables to domains             │            │
│  └─────────────────────────────────────────┘            │
│                                                          │
│  📝 Persist: dimensional model (dims, facts, measures,  │
│     relationships, bus matrix, domain assignments)       │
│                                                          │
│  🗑️ DISCARD: All 4 design-worker skills (~2000 lines)  │
└──────────────────────────────────────────────────────────┘
```

This is the peak context load of the entire orchestrator. After Phase 2, the 4 skills are discarded — the dimensional model decisions are captured in structured notes and will materialize as YAML files in Phase 4.

---

## Phase 3: ERD Creation

```
┌──────────────────────────────────────────────────────────┐
│                      PHASE 3                             │
│                                                          │
│  Working Memory:                                         │
│  ┌──────────────────────────────┐                       │
│  │ table_inventory              │ ← still here          │
│  │ Phase 2 notes (model)        │ ← compact handoff     │
│  │ 05-erd-diagrams SKILL.md     │ ← NEW, read now       │
│  └──────────────────────────────┘                       │
│  (01-04 skills are GONE — ~2000 lines freed)            │
│                                                          │
│  Apply ERD strategy from Step 1:                        │
│  ┌─────────────────────────────────────────┐            │
│  │ 15 tables → Master + Domain strategy    │            │
│  │                                          │            │
│  │ 1. Create erd_master.md (ALL tables)    │            │
│  │    - Mermaid ERD syntax                 │            │
│  │    - Domain emoji markers:              │            │
│  │      🏪 Location  📦 Product             │            │
│  │      📅 Time      💰 Sales               │            │
│  │    - PK markers only (no inline desc)   │            │
│  │    - Relationships at end of diagram    │            │
│  │    - Domain Index table                 │            │
│  │                                          │            │
│  │ 2. Create erd/erd_{domain}.md per domain│            │
│  │    - Cross-domain refs in brackets:     │            │
│  │      dim_store["🏪 dim_store (Location)"]│            │
│  │    - by_{column} relationship labels    │            │
│  └─────────────────────────────────────────┘            │
│                                                          │
│  📝 Persist: ERD file paths, strategy used               │
│  🗑️ DISCARD: Full 05-erd-diagrams SKILL.md             │
└──────────────────────────────────────────────────────────┘
```

---

## Phase 4: YAML Schema Generation

```
┌──────────────────────────────────────────────────────────┐
│                      PHASE 4                             │
│                                                          │
│  Working Memory:                                         │
│  ┌──────────────────────────────┐                       │
│  │ table_inventory              │ ← still here          │
│  │ Phase 2 model notes          │ ← dims, facts, PKs    │
│  │ Phase 3 ERD notes            │ ← paths, domains      │
│  │ 06-table-documentation SKILL │ ← NEW, read now       │
│  └──────────────────────────────┘                       │
│                                                          │
│  For each table in the dimensional model:               │
│  ┌─────────────────────────────────────────┐            │
│  │ 1. Create yaml/{domain}/{table}.yaml   │            │
│  │                                          │            │
│  │ 2. Include in every YAML:               │            │
│  │    clustering: auto          🔴          │            │
│  │    table_properties:                     │            │
│  │      delta.enableChangeDataFeed: "true"  │            │
│  │      delta.enableRowTracking: "true"     │            │
│  │      delta.autoOptimize.optimizeWrite    │            │
│  │      delta.autoOptimize.autoCompact      │            │
│  │      layer: "gold"                       │            │
│  │                                          │            │
│  │ 3. Dual-purpose descriptions:           │            │
│  │    "[Definition]. Business: [...].       │            │
│  │     Technical: [...]."                   │            │
│  │                                          │            │
│  │ 4. Complete lineage: section per column  │            │
│  │    (Bronze → Silver → Gold)              │            │
│  │                                          │            │
│  │ 5. PK columns: nullable: false  🔴      │            │
│  └─────────────────────────────────────────┘            │
│                                                          │
│  📝 Persist: YAML file paths per domain, schema count    │
│  🗑️ DISCARD: Full 06-table-documentation SKILL.md      │
└──────────────────────────────────────────────────────────┘
```

---

## Phases 5-7: Documentation Generation

Three sequential documentation phases that rely on the YAML schemas from Phase 4. No new worker skills — these use reference files and templates.

```
┌──────────────────────────────────────────────────────────┐
│                    PHASES 5, 6, 7                         │
│                                                          │
│  Working Memory:                                         │
│  ┌──────────────────────────────┐                       │
│  │ table_inventory              │                       │
│  │ Phase 4 notes (YAML paths)   │                       │
│  │ reference files (as needed)  │                       │
│  └──────────────────────────────┘                       │
│                                                          │
│  Phase 5: Column-Level Lineage                          │
│  ┌─────────────────────────────────────────┐            │
│  │ Extract lineage from ALL YAML files     │            │
│  │ Bronze → Silver → Gold per column       │            │
│  │ Standard transforms: DIRECT_COPY,       │            │
│  │   RENAME, CAST, AGGREGATE_SUM, ...      │            │
│  │                                          │            │
│  │ → COLUMN_LINEAGE.csv (machine-readable) │            │
│  │ → COLUMN_LINEAGE.md  (human-readable)   │            │
│  └─────────────────────────────────────────┘            │
│                                                          │
│  Phase 6: Business Onboarding Guide                     │
│  ┌─────────────────────────────────────────┐            │
│  │ 10-section guide with real-world stories│            │
│  │ Source system → Gold updates → Analytics│            │
│  │ Per-role getting started sections       │            │
│  │                                          │            │
│  │ → BUSINESS_ONBOARDING_GUIDE.md          │            │
│  └─────────────────────────────────────────┘            │
│                                                          │
│  Phase 7: Source Table Mapping                          │
│  ┌─────────────────────────────────────────┐            │
│  │ ALL source tables: INCLUDED / EXCLUDED  │            │
│  │ Rationale for every row (no exceptions) │            │
│  │ Domain + implementation phase mapping   │            │
│  │                                          │            │
│  │ → SOURCE_TABLE_MAPPING.csv              │            │
│  └─────────────────────────────────────────┘            │
│                                                          │
│  📝 Persist per phase: output file paths                │
└──────────────────────────────────────────────────────────┘
```

---

## Phase 8: Design Validation — Cross-Referencing Everything

```
┌──────────────────────────────────────────────────────────┐
│                      PHASE 8                             │
│                                                          │
│  Working Memory:                                         │
│  ┌──────────────────────────────┐                       │
│  │ table_inventory              │ ← still here          │
│  │ Phase 4-7 notes (all paths)  │                       │
│  │ 07-design-validation SKILL   │ ← NEW, read now       │
│  └──────────────────────────────┘                       │
│                                                          │
│  Cross-reference validation:                            │
│  ┌─────────────────────────────────────────┐            │
│  │                                          │            │
│  │  YAML ◄──────────► ERD                  │            │
│  │   │    consistency    │                  │            │
│  │   │    check          │                  │            │
│  │   ▼                   ▼                  │            │
│  │  Lineage CSV ◄─── FK Refs               │            │
│  │                                          │            │
│  │ ✅ All ERD columns exist in YAML         │            │
│  │ ✅ All YAML columns have lineage         │            │
│  │ ✅ PK definitions match grain type       │            │
│  │ ✅ FK references → valid tables/columns  │            │
│  │ ✅ Upstream source columns exist (if     │            │
│  │    source tables already deployed)       │            │
│  └─────────────────────────────────────────┘            │
│                                                          │
│  Output: validation pass/fail report,                   │
│          inconsistencies to fix                          │
│                                                          │
│  🗑️ DISCARD: Full 07-design-validation SKILL.md        │
└──────────────────────────────────────────────────────────┘
```

---

## Phase 9: Stakeholder Review

The final phase is human-facing — no worker skills needed:

```
┌──────────────────────────────────────────────────────────┐
│                      PHASE 9                             │
│                                                          │
│  Present to stakeholders:                               │
│  ├── ERD hierarchy (master + domain diagrams)           │
│  ├── Grain definitions for each fact table              │
│  ├── Measures completeness for reporting needs          │
│  ├── Naming conventions review                          │
│  ├── Business Onboarding Guide story accuracy           │
│  └── Formal design sign-off                             │
│                                                          │
│  Output: stakeholder approval document                  │
└──────────────────────────────────────────────────────────┘
```

---

## The Complete Flow — Context Budget Over Time

```
Time ──────────────────────────────────────────────────────────▶

Phase:  │   0   │  1  │      2       │   3   │   4   │ 5-7 │  8  │  9  │

        ┌───────┬─────┬──────────────┬───────┬───────┬─────┬─────┬─────┐
table_  │███████│█████│██████████████│███████│███████│█████│█████│█████│
inv     │       │     │              │       │       │     │     │     │
        ├───────┼─────┼──────────────┼───────┼───────┼─────┼─────┼─────┤
schema  │███████│     │              │       │       │     │     │     │
CSV     │parsed │     │              │       │       │     │     │     │
        ├───────┼─────┼──────────────┼───────┼───────┼─────┼─────┼─────┤
01-04   │       │     │██████████████│       │       │     │     │     │
skills  │       │     │(~2000 lines) │discard│       │     │     │     │
        ├───────┼─────┼──────────────┼───────┼───────┼─────┼─────┼─────┤
model   │       │     │              │░░░░░░░│░░░░░░░│░░░░░│░░░░░│░░░░░│
notes   │       │     │     created  │(10 ln)│       │     │     │     │
        ├───────┼─────┼──────────────┼───────┼───────┼─────┼─────┼─────┤
05-erd  │       │     │              │███████│       │     │     │     │
skill   │       │     │              │       │discard│     │     │     │
        ├───────┼─────┼──────────────┼───────┼───────┼─────┼─────┼─────┤
06-doc  │       │     │              │       │███████│     │     │     │
skill   │       │     │              │       │       │disc.│     │     │
        ├───────┼─────┼──────────────┼───────┼───────┼─────┼─────┼─────┤
07-val  │       │     │              │       │       │     │█████│     │
skill   │       │     │              │       │       │     │     │disc.│
        └───────┴─────┴──────────────┴───────┴───────┴─────┴─────┴─────┘

 ███ = full skill loaded    ░░░ = compact notes (5-10 lines)
```

The peak load is Phase 2 where 4 design-worker skills are loaded simultaneously (~2000 lines). This is unavoidable because dimensional modeling decisions are interdependent. All other phases load at most one worker skill at a time.

---

## The Worker Skill Chain

Each worker skill is read at a specific phase and discarded after. The dimensional model notes from Phase 2 serve as the bridge that connects the design phase to all downstream deliverables:

```
Phase 0: Source Schema Intake (no skill)
  └─ table_inventory dict
          │
          ▼
Phase 1: Requirements (no skill)
  └─ Project context, domain assignments
          │
          ▼
Phase 2: 01-grain + 02-dimension + 03-fact + 04-conformed
  └─ Dimensional model notes
     - Dims: names, SCD types, business keys, patterns
     - Facts: names, grains, measures, additivity
     - Bus matrix, conformed dims, domain assignments
          │
          ▼
Phase 3: 05-erd-diagrams
  └─ ERD file paths, strategy used
          │
          ▼
Phase 4: 06-table-documentation
  └─ YAML file paths per domain, schema count
          │
          ▼
Phases 5-7: Reference files + templates (no skills)
  └─ COLUMN_LINEAGE.csv, BUSINESS_ONBOARDING_GUIDE.md,
     SOURCE_TABLE_MAPPING.csv
          │
          ▼
Phase 8: 07-design-validation
  └─ Validation pass/fail, inconsistencies to fix
          │
          ▼
Phase 9: Stakeholder review (no skill)
```

---

## Final Deliverables

```
gold_layer_design/
├── README.md                          ← Navigation hub
├── erd_master.md                      ← Master ERD (ALWAYS)
├── erd_summary.md                     ← Domain overview (20+ tables)
├── erd/
│   └── erd_{domain}.md                ← Per-domain ERDs (9+ tables)
├── yaml/
│   └── {domain}/
│       └── {table}.yaml               ← YAML schemas (Source of Truth)
├── docs/
│   └── BUSINESS_ONBOARDING_GUIDE.md   ← MANDATORY
├── COLUMN_LINEAGE.csv                 ← MANDATORY (machine-readable)
├── COLUMN_LINEAGE.md                  ← Human-readable lineage
├── SOURCE_TABLE_MAPPING.csv           ← MANDATORY
├── DESIGN_SUMMARY.md                  ← Design decisions
└── DESIGN_GAP_ANALYSIS.md            ← Coverage analysis
```

---

## Post-Completion: The Audit Trail

The orchestrator requires a **Skill Usage Summary** documenting every skill read, in what phase, and why:

| # | Phase | Skill / Reference Read | Type | What It Was Used For |
|---|-------|----------------------|------|---------------------|
| 1 | Phase 0 | `references/schema-intake-patterns.md` | Reference | Parse schema CSV, classify tables, infer FKs |
| 2 | Phase 2 | `design-workers/01-grain-definition/SKILL.md` | Worker | Grain type decision tree for facts |
| 3 | Phase 2 | `design-workers/02-dimension-patterns/SKILL.md` | Worker | SCD types, role-playing, junk dimensions |
| 4 | Phase 2 | `design-workers/03-fact-table-patterns/SKILL.md` | Worker | Measure additivity, factless facts |
| 5 | Phase 2 | `design-workers/04-conformed-dimensions/SKILL.md` | Worker | Bus matrix, drill-across queries |
| 6 | Phase 3 | `design-workers/05-erd-diagrams/SKILL.md` | Worker | ERD organization strategy, Mermaid syntax |
| 7 | Phase 4 | `design-workers/06-table-documentation/SKILL.md` | Worker | Dual-purpose descriptions, TBLPROPERTIES |
| 8 | Phase 8 | `design-workers/07-design-validation/SKILL.md` | Worker | YAML-ERD-Lineage cross-validation |
| ... | ... | ... | ... | ... |

---

## Key Design Principles at Work

| # | Principle | How It's Applied |
|---|-----------|-----------------|
| 1 | **Schema extraction over generation** | `table_inventory` parsed from CSV drives every name. No table/column is ever invented. |
| 2 | **YAML as single source of truth** | Every column name, type, constraint, and description defined in YAML first. Implementation reads YAML. |
| 3 | **Dual-purpose documentation** | All descriptions serve both business users and LLMs: `[Definition]. Business: [...]. Technical: [...].` |
| 4 | **Progressive disclosure with a peak** | Phase 2 loads 4 skills at once (unavoidable), then all subsequent phases load at most 1. |
| 5 | **Cross-validation gates** | Phase 8 validates YAML vs ERD vs Lineage CSV consistency before sign-off. |
| 6 | **Design-first pipeline** | YAML schemas are created here (stage 1), consumed by Bronze, Silver, and Gold implementation stages. |
| 7 | **ERD strategy scales with complexity** | Table count determines whether you get 1, 2, or 3 tiers of ERD diagrams. |

---

## When Things Go Wrong

- **Missing schema CSV** → Hard stop at Phase 0 with message to provide `context/{ProjectName}_Schema.csv`
- **Zero tables classified** → `table_inventory` is empty → hard stop
- **No FK relationships inferred** → Warning (not blocking) — agent proceeds but flags for manual review
- **YAML-ERD mismatch in Phase 8** → Validation report lists specific columns/tables to fix before sign-off
- **Upstream columns don't exist** → Phase 8 conditional check against live catalog, fix YAML lineage
- **Stakeholder rejects design** → Loop back to Phase 2 with feedback, regenerate affected YAML/ERD files

---

## What Happens Next

After design sign-off, this orchestrator hands off to the rest of the pipeline:

```
Gold Design (this skill)
    │
    ▼
Bronze Setup (00-bronze-layer-setup)
    → Create Bronze tables matching source schema
    → Generate test data with Faker
    │
    ▼
Silver Setup (00-silver-layer-setup)
    → SDP/DLT pipelines with DQ rules
    → Schema cloning with quality gates
    │
    ▼
Gold Implementation (01-gold-layer-setup)
    → setup_tables.py reads the YAML from THIS phase
    → merge_gold_tables.py uses the lineage from THIS phase
```

The YAML files created in Phase 4 of this orchestrator become the literal input files for `setup_tables.py` in the Gold implementation stage.
