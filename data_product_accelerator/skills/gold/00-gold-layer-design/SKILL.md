---
name: gold-layer-design
description: End-to-end orchestrator for designing complete Gold layer schemas with ERDs, YAML files, lineage tracking, and comprehensive business documentation. Guides users through dimensional modeling, ERD creation (master/domain/summary based on table count), YAML schema generation, column-level lineage documentation, business onboarding guide creation, source table mapping, and design validation. Orchestrates design-workers (05-erd-diagrams, 06-table-documentation, 01-grain-definition, 07-design-validation, 02-dimension-patterns, 03-fact-table-patterns, 04-conformed-dimensions). Use when designing a Gold layer from scratch, creating dimensional models, documenting business processes, or preparing for Gold layer implementation.
license: Apache-2.0
metadata:
  author: prashanth subrahmanyam
  version: "3.0.0"
  domain: gold
  role: orchestrator
  pipeline_stage: 1
  pipeline_stage_name: gold-design
  next_stages:
    - bronze-layer-setup
  reads:
    - context/*.csv
  emits:
    - gold_layer_design/yaml/
    - gold_layer_design/erd_master.md
    - gold_layer_design/docs/BUSINESS_ONBOARDING_GUIDE.md
    - gold_layer_design/COLUMN_LINEAGE.csv
    - gold_layer_design/SOURCE_TABLE_MAPPING.csv
  workers:
    - design-workers/01-grain-definition
    - design-workers/02-dimension-patterns
    - design-workers/03-fact-table-patterns
    - design-workers/04-conformed-dimensions
    - design-workers/05-erd-diagrams
    - design-workers/06-table-documentation
    - design-workers/07-design-validation
  common_dependencies:
    - databricks-expert-agent
    - naming-tagging-standards
  dependencies:
    - design-workers/01-grain-definition
    - design-workers/02-dimension-patterns
    - design-workers/03-fact-table-patterns
    - design-workers/04-conformed-dimensions
    - design-workers/05-erd-diagrams
    - design-workers/06-table-documentation
    - design-workers/07-design-validation
  last_verified: "2026-02-07"
  volatility: low
  upstream_sources: []  # Internal dimensional modeling methodology
---

# Gold Layer Design Orchestrator

This skill orchestrates the complete Gold layer design process, ensuring all mandatory deliverables are created with proper dependencies on specialized Gold layer skills.

## When to Use This Skill

- Designing a Gold layer from scratch for a new project
- Creating dimensional models (facts and dimensions)
- Documenting business processes and data lineage
- Preparing for Gold layer implementation (before `03b-gold-layer-setup-prompt`)
- Generating mandatory documentation (Business Onboarding Guide, Source Table Mapping, Column Lineage CSV)

## Critical Dependencies (Read at Indicated Phase)

This skill orchestrates the following skills. Each MUST be read and followed at the phase where it is invoked:

| Skill | Read At | Purpose |
|-------|---------|---------|
| `design-workers/01-grain-definition` | Phase 2 | Grain type decision tree for fact tables |
| `design-workers/02-dimension-patterns` | Phase 2 | Dimension design patterns (role-playing, junk, degenerate, hierarchies) |
| `design-workers/03-fact-table-patterns` | Phase 2 | Fact table patterns (measure additivity, factless, accumulating snapshots) |
| `design-workers/04-conformed-dimensions` | Phase 2 | Enterprise integration (bus matrix, conformed dims, drill-across) |
| `design-workers/05-erd-diagrams` | Phase 3 | ERD creation and organization strategy |
| `design-workers/06-table-documentation` | Phase 4 | Dual-purpose documentation standards |
| `design-workers/07-design-validation` | Phase 8 | YAML↔ERD↔Lineage cross-validation |

### 🔴 Non-Negotiable Defaults (YAML Schemas MUST Encode These)

The design phase produces YAML schemas that drive all downstream table creation. These YAML schemas MUST include the following properties so that `setup_tables.py` generates compliant DDL.

| Default | YAML Location | Value | NEVER Do This Instead |
|---------|---------------|-------|----------------------|
| **Auto Liquid Clustering** | `clustering:` field | `auto` | ❌ NEVER specify column names or omit clustering |
| **Change Data Feed** | `table_properties:` | `'delta.enableChangeDataFeed' = 'true'` | ❌ NEVER omit (required for incremental propagation) |
| **Row Tracking** | `table_properties:` | `'delta.enableRowTracking' = 'true'` | ❌ NEVER omit (breaks downstream MV refresh) |
| **Auto-Optimize** | `table_properties:` | `optimizeWrite` + `autoCompact` = `'true'` | ❌ NEVER omit |
| **Layer Tag** | `table_properties:` | `'layer' = 'gold'` | ❌ NEVER omit or use wrong layer |
| **PK NOT NULL** | `columns:` with `nullable: false` | All PRIMARY KEY columns | ❌ NEVER leave PK columns nullable |

```yaml
# ✅ CORRECT: Every Gold YAML schema MUST include these
table_name: dim_example
clustering: auto  # 🔴 MANDATORY (generates CLUSTER BY AUTO)
table_properties:
  delta.enableChangeDataFeed: "true"     # 🔴 MANDATORY
  delta.enableRowTracking: "true"        # 🔴 MANDATORY
  delta.autoOptimize.optimizeWrite: "true"
  delta.autoOptimize.autoCompact: "true"
  layer: "gold"
```

**Note:** Serverless and Environments V4 are job-level concerns enforced by `gold/01-gold-layer-setup` and `databricks-asset-bundles` during the implementation phase, not during design.

## Quick Start (4-8 hours)

### Deliverables Checklist

**ERD Organization (based on table count):**
- [ ] Master ERD (`erd_master.md`) - ALWAYS required
- [ ] Domain ERDs (`erd/erd_{domain}.md`) - If 9+ tables
- [ ] Summary ERD (`erd_summary.md`) - If 20+ tables

**YAML Schemas (organized by domain):**
- [ ] `gold_layer_design/yaml/{domain}/dim_*.yaml` - Dimension schemas
- [ ] `gold_layer_design/yaml/{domain}/fact_*.yaml` - Fact schemas

**Mandatory Documentation (ALL required):**
- [ ] BUSINESS_ONBOARDING_GUIDE.md - Business processes + real-world stories
- [ ] COLUMN_LINEAGE.csv - Machine-readable column lineage
- [ ] COLUMN_LINEAGE.md - Human-readable lineage
- [ ] SOURCE_TABLE_MAPPING.csv - Source table inclusion/exclusion rationale
- [ ] DESIGN_SUMMARY.md - Design decisions
- [ ] DESIGN_GAP_ANALYSIS.md - Coverage analysis
- [ ] README.md - Navigation hub

### ERD Organization Decision

| Tables | Strategy | Required Deliverables |
|--------|----------|----------------------|
| 1-8 | Master only | `erd_master.md` |
| 9-20 | Master + Domain | `erd_master.md` + `erd/erd_{domain}.md` |
| 20+ | Master + Domain + Summary | `erd_master.md` + `erd_summary.md` + `erd/erd_{domain}.md` |

---

## Working Memory Management

This orchestrator spans 9 phases over 4-8 hours. To maintain coherence without context pollution:

**After each phase, persist a brief summary note** capturing:
- **Phase 0:** Table inventory dict, entity classifications (dim/fact/bridge), FK relationships, suggested domains
- **Phase 1:** Project context (name, schemas, use cases, stakeholders)
- **Phase 2:** Dimensional model: dims, facts, measures, relationships, bus matrix, domain assignments
- **Phase 3:** ERD file paths, strategy used (master-only / master+domain / full)
- **Phase 4:** YAML file paths per domain, schema count, lineage gaps
- **Phases 5-7:** Output file paths (COLUMN_LINEAGE.csv, BUSINESS_ONBOARDING_GUIDE.md, SOURCE_TABLE_MAPPING.csv)
- **Phase 8:** Validation pass/fail summary, inconsistencies to fix

**What to keep in working memory:** Current phase's design-worker skill, the table inventory dict (Phase 0), and previous phase's summary. Discard intermediate outputs (full CSV data, raw ERD source, complete YAML contents) — they are on disk.

**What to offload:** Each design-worker skill has `Design Notes to Carry Forward` and `Next Step` sections. Read them to know what to pass to the next phase.

---

## Step-by-Step Workflow

### Phase 0: Source Schema Intake (MANDATORY First Step)

**This is the entry point for the entire data platform build.** The customer provides a source schema CSV (e.g., `context/Wanderbricks_Schema.csv`) containing table and column metadata. This phase parses it into a structured inventory that drives all subsequent design decisions.

**Input:** `context/{ProjectName}_Schema.csv` — CSV with columns: `table_catalog`, `table_schema`, `table_name`, `column_name`, `ordinal_position`, `full_data_type`, `data_type`, `is_nullable`, `comment`

**Steps:**

1. **Read and parse the schema CSV from `context/`:**

   **MANDATORY: Read** `references/schema-intake-patterns.md` for complete implementations of `parse_schema_csv()`, `classify_tables()`, and `infer_relationships()`.

   - `parse_schema_csv(csv_path)` — Reads CSV into structured dict keyed by table name, with columns, types, nullability, and comments per table.
   - Output: `{table_name: {"columns": [...], "column_count": N, "catalog": ..., "schema": ...}}`

2. **Classify tables as dimensions, facts, or bridge/junction:**

   - `classify_tables(schema)` — Classifies each table based on column patterns:
     - **bridge**: 3 or fewer columns AND 2+ FK-like columns
     - **fact**: 2+ FK columns AND numeric measures, OR 2+ timestamps AND 2+ FKs
     - **dimension**: everything else
   - Also identifies: PK candidates, FK columns, measures, timestamps per table

3. **Identify FK relationships from column comments and naming patterns:**

   - `infer_relationships(classified)` — Two inference strategies:
     - Pattern 1: Column comment contains "Foreign Key to 'X'" → direct FK
     - Pattern 2: Column name `other_table_id` matches a known table name
   - Returns list of `{from_table, from_column, to_table, to_column, source}`

4. **Produce Schema Intake Report:**

The report summarizes: table inventory, entity classification, inferred relationships, and domain suggestions. This feeds Phase 1 (Requirements) and Phase 2 (Dimensional Modeling).

**Output:**
- Printed table inventory with classification (dimension/fact/bridge)
- Inferred FK relationships list
- Suggested domain groupings
- Recommended dimensional model skeleton (which tables → which Gold dims/facts)

**Critical:** The schema CSV is the **single source of truth** for table and column names. ALL downstream phases must extract names from the parsed schema — never generate table/column names from memory.

---

### Phase 1: Requirements Gathering

**Collect the following project context (enhanced with schema intake):**

| Field | Example |
|-------|---------|
| Project Name | `wanderbricks_analytics` |
| Source Schema | `wanderbricks` (from schema CSV) |
| Gold Schema | `wanderbricks_gold` (convention: `{project}_gold`) |
| Business Domain | `travel`, `hospitality` (inferred from schema CSV) |
| Primary Use Cases | booking analytics, revenue reporting |
| Key Stakeholders | Revenue Ops, Marketing |
| Reporting Frequency | Daily, Weekly, Monthly |
| Table Count | 15 tables — 8 dims, 5 facts, 2 bridge (from Phase 0) |
| Inferred Relationships | 12 FK relationships (from Phase 0) |

**Output:** Populated project context document (with Phase 0 schema intake data incorporated)

---

### Phase 2: Dimensional Model Design

**Read and Follow:** `references/dimensional-modeling-guide.md`

**Activities:**
1. Identify 2-5 dimensions with SCD type decisions (Type 1 vs Type 2)
2. Identify 1-3 facts with explicit grain definitions
3. Define measures and metrics with calculation logic
4. Define relationships (FK constraints)
5. Assign tables to domains (Location, Product, Time, Sales, etc.)

**MANDATORY: Read these skills using the Read tool in order during Phase 2:**

1. `data_product_accelerator/skills/gold/design-workers/01-grain-definition/SKILL.md` — Grain inference from PRIMARY KEY structure, transaction vs aggregated vs snapshot patterns, PK-grain decision tree
2. `data_product_accelerator/skills/gold/design-workers/02-dimension-patterns/SKILL.md` — Role-playing, degenerate, junk, mini-dimensions, hierarchy flattening, NULL handling
3. `data_product_accelerator/skills/gold/design-workers/03-fact-table-patterns/SKILL.md` — Measure additivity, factless facts, accumulating snapshots, late-arriving data
4. `data_product_accelerator/skills/gold/design-workers/04-conformed-dimensions/SKILL.md` — Enterprise bus matrix, conformed dimensions, shrunken dims, drill-across patterns

**Apply from skills:**
- Infer grain type from PRIMARY KEY structure (transaction, aggregated, snapshot)
- Document grain explicitly for each fact table
- Validate PRIMARY KEY matches grain type using decision tree
- Apply dimension patterns (denormalize hierarchies, handle NULLs with "Unknown" rows, combine flags into junk dimensions)
- Classify measures as additive, semi-additive, or non-additive
- Build the enterprise bus matrix mapping fact tables to dimensions
- Identify conformed dimensions shared across multiple facts

**Key Outputs:**
- Dimensions table (name, business key, SCD type, source Silver table, dimension pattern applied)
- Facts table (name, grain, source Silver tables, update frequency, fact type)
- Measures table (name, data type, calculation logic, business purpose, additivity classification)
- Relationships table (fact FK → dimension PK, cardinality)
- Domain assignments table (table → domain mapping)
- Enterprise bus matrix (fact tables × dimensions)
- NULL handling strategy (Unknown member rows per dimension)

---

### Phase 3: ERD Creation

**MANDATORY: Read this skill using the Read tool BEFORE creating any ERD diagrams:**

1. `data_product_accelerator/skills/gold/design-workers/05-erd-diagrams/SKILL.md` — ERD organization strategy (master/domain/summary), Mermaid syntax standards, domain emoji markers, relationship patterns, cross-domain references

**Activities:**
1. Count tables to determine ERD strategy (1-8, 9-20, 20+)
2. Create Master ERD (`erd_master.md`) with ALL tables grouped by domain
3. Create Domain ERDs (`erd/erd_{domain}.md`) if 9+ tables
4. Create Summary ERD (`erd_summary.md`) if 20+ tables
5. Add Domain Index table to Master ERD

**Critical Rules (from 05-erd-diagrams):**
- Use domain emoji markers (🏪 Location, 📦 Product, 📅 Time, 💰 Sales, 📊 Inventory)
- Use `PK` markers only (no inline descriptions in ERD)
- Use `by_{column}` pattern for relationship labels
- Group all relationships at end of diagram
- Use bracketed notation for cross-domain references: `dim_store["🏪 dim_store (Location)"]`

**Outputs:**
- `gold_layer_design/erd_master.md` (ALWAYS)
- `gold_layer_design/erd_summary.md` (if 20+ tables)
- `gold_layer_design/erd/erd_{domain}.md` (if 9+ tables)

---

### Phase 4: YAML Schema Generation

**MANDATORY: Read each skill below using the Read tool BEFORE generating any YAML schema files:**

1. `data_product_accelerator/skills/gold/design-workers/06-table-documentation/SKILL.md` — Dual-purpose description pattern (`[Definition]. Business: [...]. Technical: [...].`), surrogate key naming, TBLPROPERTIES metadata, column comment standards

**Activities:**
1. Create domain-organized YAML directory structure (`yaml/{domain}/`)
2. Generate one YAML file per table using templates from `01-yaml-table-setup`
3. Include complete column definitions with lineage metadata
4. Document PRIMARY KEY and FOREIGN KEY constraints
5. Apply standard table properties (CDF, row tracking, auto-optimize)
6. Write dual-purpose descriptions following `06-table-documentation` patterns

**Critical Rules (from design-workers/06-table-documentation + Non-Negotiable Defaults):**
- Pattern: `[Definition]. Business: [context]. Technical: [details].`
- Surrogate keys as PRIMARY KEYS (not business keys)
- Include all TBLPROPERTIES (layer, domain, entity_type, grain, scd_type, etc.)
- Every column MUST have a `lineage:` section
- 🔴 `clustering: auto` in EVERY YAML schema (generates `CLUSTER BY AUTO`)
- 🔴 `delta.enableChangeDataFeed: "true"` in EVERY YAML `table_properties:`
- 🔴 `delta.enableRowTracking: "true"` in EVERY YAML `table_properties:`
- 🔴 All PRIMARY KEY columns MUST have `nullable: false`

**YAML Template Reference:** See `references/yaml-schema-patterns.md`

**Outputs:**
- `gold_layer_design/yaml/{domain}/{table}.yaml` for each table
- Domain-organized folder structure matching ERD domains

---

### Phase 5: Column-Level Lineage Documentation

**Read:** `references/lineage-documentation-guide.md`

**Activities:**
1. Extract lineage from all YAML files
2. Document Bronze → Silver → Gold mapping for EVERY column
3. Specify transformation type from standard list (DIRECT_COPY, RENAME, CAST, AGGREGATE_SUM, AGGREGATE_SUM_CONDITIONAL, AGGREGATE_COUNT, DERIVED_CALCULATION, HASH_MD5, COALESCE, DATE_TRUNC, GENERATED, LOOKUP)
4. Document transformation logic as executable PySpark/SQL
5. Generate both CSV and Markdown formats

**Use Script:** `scripts/generate_lineage_csv.py`

**Outputs:**
- `gold_layer_design/COLUMN_LINEAGE.csv` (machine-readable, MANDATORY)
- `gold_layer_design/COLUMN_LINEAGE.md` (human-readable)

---

### Phase 6: Business Onboarding Guide (MANDATORY)

**Read:** `references/business-documentation-guide.md`  
**Use Template:** `assets/templates/business-onboarding-template.md`

**Required Sections:**
1. Introduction to Business Domain
2. The Business Lifecycle (Key Stages)
3. Key Business Entities (Players/Actors)
4. The Gold Layer Data Model (Overview)
5. Business Processes & Tracking (with ASCII flow diagrams)
   - 5B. Real-World Scenarios (minimum 3-4 detailed stories)
6. Analytics Use Cases
7. AI & ML Opportunities
8. Self-Service Analytics with Genie
9. Data Quality & Monitoring
10. Getting Started (per role: Engineer, Analyst, Scientist, Business User)

**Critical:** Each story must show source system data → Gold layer updates → analytics impact at each stage.

**Output:** `gold_layer_design/docs/BUSINESS_ONBOARDING_GUIDE.md`

---

### Phase 7: Source Table Mapping (MANDATORY)

**Use Template:** `assets/templates/source-table-mapping-template.csv`

**Activities:**
1. List ALL source tables (included, excluded, planned)
2. Assign status: INCLUDED, EXCLUDED, or PLANNED
3. Provide rationale for EVERY row (required, no exceptions)
4. Map INCLUDED tables to Gold tables
5. Assign domains and implementation phases

**Output:** `gold_layer_design/SOURCE_TABLE_MAPPING.csv`

---

### Phase 8: Design Validation

**MANDATORY: Read this skill using the Read tool BEFORE running design validation:**

1. `data_product_accelerator/skills/gold/design-workers/07-design-validation/SKILL.md` — YAML↔ERD↔Lineage cross-validation, PK/FK reference consistency, mandatory field validation

**Also read:** `references/validation-checklists.md`

**Validation Activities:**
1. Consistency check: YAML ↔ ERD ↔ Lineage CSV (all columns match)
2. Validate all ERD columns exist in YAML definitions
3. Validate all YAML columns have lineage metadata
4. Validate PRIMARY KEY definitions match grain type
5. Validate FOREIGN KEY references point to valid tables/columns
6. Run lineage validation script
7. **Upstream cross-reference (conditional):** If upstream source tables already exist (check via `spark.catalog.tableExists()`), run `cross_reference_silver_at_design_time()` from `references/schema-intake-patterns.md` to validate YAML lineage `silver_column` values against actual source table schemas. Fix any mismatches found. If source tables do not exist yet, note that this validation will be enforced as a hard gate during Phase 0 of `01-gold-layer-setup`.

**Outputs:**
- Validation report (pass/fail for each category)
- List of inconsistencies to fix (including any upstream column mismatches)
- Completed design sign-off checklist

---

### Phase 9: Stakeholder Review

**Activities:**
1. Present ERD hierarchy to business stakeholders
2. Review grain definitions for each fact table
3. Confirm measures are complete for reporting needs
4. Validate naming conventions with data governance
5. Review Business Onboarding Guide stories for accuracy
6. Obtain formal design sign-off

**Output:** Stakeholder approval document

---

## Final File Organization

```
gold_layer_design/
├── README.md                          # Navigation hub
├── erd_master.md                      # Complete ERD (ALWAYS)
├── erd_summary.md                     # Domain overview (20+ tables)
├── erd/                               # Domain ERDs (9+ tables)
│   └── erd_{domain}.md
├── yaml/                              # Domain-organized schemas
│   └── {domain}/
│       └── {table}.yaml
├── docs/
│   └── BUSINESS_ONBOARDING_GUIDE.md   # MANDATORY
├── COLUMN_LINEAGE.csv                 # MANDATORY
├── COLUMN_LINEAGE.md                  # Human-readable
├── SOURCE_TABLE_MAPPING.csv           # MANDATORY
├── DESIGN_SUMMARY.md                  # Design decisions
└── DESIGN_GAP_ANALYSIS.md            # Coverage analysis
```

## Key Design Principles

1. **Schema Extraction Over Generation** - Always extract table/column names from YAML. Never generate from scratch. Prevents hallucinations and schema mismatches.

2. **YAML as Single Source of Truth** - All column names, types, constraints, descriptions defined in YAML first. Implementation reads YAML.

3. **Dual-Purpose Documentation** - ALL descriptions serve both business users and technical users (including LLMs like Genie). Pattern: `[Definition]. Business: [...]. Technical: [...].`

4. **Progressive Disclosure** - Core workflow here in SKILL.md. Detailed patterns in `references/`. Templates in `assets/templates/`.

5. **Dependency Orchestration** - Read and follow dependency skills at the phase indicated. Don't skip dependency skills.

## Common Mistakes to Avoid

| Mistake | Impact | Prevention |
|---------|--------|------------|
| Skipping mandatory docs | 2-3 weeks ramp-up time wasted | Always create all 3 starred deliverables |
| Wrong ERD organization | Unreadable diagrams or unnecessary complexity | Follow table count decision tree |
| Incomplete column lineage | 33% of implementation bugs | Every column needs Bronze → Silver → Gold mapping |
| No grain documentation | Table rewrite required | Document grain in every fact YAML |
| Generic business docs | Slow analytics adoption | Include real-world stories with data flow |

## Time Estimates

| Complexity | Tables | Time |
|-----------|--------|------|
| Small | 1-8 | 3-4 hours |
| Medium | 9-20 | 5-6 hours |
| Large | 20+ | 6-10 hours |

## Next Steps After Design

After completing design and obtaining stakeholder sign-off, **read the implementation orchestrator skill:**

1. `data_product_accelerator/skills/gold/01-gold-layer-setup/SKILL.md` — End-to-end implementation of tables, merge scripts, FK constraints, and Asset Bundle jobs from the YAML designs created here

That skill will in turn invoke:
- `pipeline-workers/02-merge-patterns` — SCD Type 1/2 dimension merges, fact aggregation patterns
- `pipeline-workers/03-deduplication` — Mandatory deduplication before MERGE
- `pipeline-workers/01-yaml-table-setup` — YAML-driven DDL generation
- `pipeline-workers/05-schema-validation` — DataFrame↔DDL schema validation
- `pipeline-workers/04-grain-validation` — Pre-merge grain validation
- All other implementation dependencies

## Pipeline Progression

**This is the first stage** in the Design-First pipeline. Start here after receiving the customer's source schema CSV.

**Next stage:** After completing Gold layer design, proceed to:
- **`bronze/00-bronze-layer-setup`** — Create Bronze tables matching the source schema and generate test data with Faker

## Reference Files

- **[Dimensional Modeling Guide](references/dimensional-modeling-guide.md)** - Dimensions, facts, measures, relationships, domain assignment
- **[ERD Organization Strategy](references/erd-organization-strategy.md)** - Master/Domain/Summary ERD patterns
- **[YAML Schema Patterns](references/yaml-schema-patterns.md)** - YAML templates for dimensions, facts, date dimensions
- **[Lineage Documentation Guide](references/lineage-documentation-guide.md)** - Column lineage, transformation types, CSV generation
- **[Business Documentation Guide](references/business-documentation-guide.md)** - Business Onboarding Guide and Source Table Mapping
- **[Validation Checklists](references/validation-checklists.md)** - All design validation checklists

## Post-Completion: Skill Usage Summary (MANDATORY)

**After completing all phases of this orchestrator, output a Skill Usage Summary reflecting what you ACTUALLY did — not a pre-written summary.**

### What to Include

1. Every skill `SKILL.md` or `references/` file you read (via the Read tool), in the order you read them
2. Which phase you were in when you read it
3. Whether it was a **Worker**, **Common**, **Cross-domain**, or **Reference** file
4. A one-line description of what you specifically used it for in this session

### Format

| # | Phase | Skill / Reference Read | Type | What It Was Used For |
|---|-------|----------------------|------|---------------------|
| 1 | Phase N | `path/to/SKILL.md` | Worker / Common / Cross-domain / Reference | One-line description |

### Summary Footer

End with:
- **Totals:** X worker skills, Y common skills, Z reference files read across N phases
- **Skipped:** List any skills from the dependency table above that you did NOT need to read, and why (e.g., "phase not applicable", "user skipped", "no issues encountered")
- **Unplanned:** List any skills you read that were NOT listed in the dependency table (e.g., for troubleshooting, edge cases, or user-requested detours)

---

## External References

- [Kimball Dimensional Modeling](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/) | [Unity Catalog Constraints](https://docs.databricks.com/data-governance/unity-catalog/constraints.html) | [Mermaid ERD Syntax](https://mermaid.js.org/syntax/entityRelationshipDiagram.html) | [AgentSkills.io Specification](https://agentskills.io/specification)
