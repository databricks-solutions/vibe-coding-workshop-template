---
name: gold-layer-design
description: End-to-end orchestrator for designing complete Gold layer schemas with ERDs, YAML files, lineage tracking, and comprehensive business documentation. Guides users through dimensional modeling, ERD creation (master/domain/summary based on table count), YAML schema generation, column-level lineage documentation, business onboarding guide creation, source table mapping, and design validation. Orchestrates mandatory dependencies on Gold skills (mermaid-erd-patterns, yaml-driven-gold-setup, gold-layer-documentation, fact-table-grain-validation, gold-layer-schema-validation, gold-layer-merge-patterns). Use when designing a Gold layer from scratch, creating dimensional models, documenting business processes, or preparing for Gold layer implementation.
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
    - mermaid-erd-patterns
    - yaml-driven-gold-setup
    - gold-layer-documentation
    - fact-table-grain-validation
    - gold-layer-schema-validation
    - gold-layer-merge-patterns
  common_dependencies:
    - databricks-expert-agent
    - naming-tagging-standards
  dependencies:
    - mermaid-erd-patterns
    - yaml-driven-gold-setup
    - gold-layer-documentation
    - fact-table-grain-validation
    - gold-layer-schema-validation
    - gold-layer-merge-patterns
  last_verified: "2026-02-07"
  volatility: low
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
| `fact-table-grain-validation` | Phase 2 | Grain validation for fact tables |
| `mermaid-erd-patterns` | Phase 3 | ERD creation and organization strategy |
| `yaml-driven-gold-setup` | Phase 4 | YAML schema file structure and setup script |
| `gold-layer-documentation` | Phase 4 | Dual-purpose documentation standards |
| `gold-layer-schema-validation` | Phase 8 | Schema consistency validation |
| `gold-layer-merge-patterns` | Next Steps | Future implementation guidance |

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

## Step-by-Step Workflow

### Phase 0: Source Schema Intake (MANDATORY First Step)

**This is the entry point for the entire data platform build.** The customer provides a source schema CSV (e.g., `context/Wanderbricks_Schema.csv`) containing table and column metadata. This phase parses it into a structured inventory that drives all subsequent design decisions.

**Input:** `context/{ProjectName}_Schema.csv` — CSV with columns: `table_catalog`, `table_schema`, `table_name`, `column_name`, `ordinal_position`, `full_data_type`, `data_type`, `is_nullable`, `comment`

**Steps:**

1. **Read and parse the schema CSV from `context/`:**

```python
import csv
from pathlib import Path
from collections import defaultdict

def parse_schema_csv(csv_path: Path) -> dict:
    """Parse customer schema CSV into structured table inventory."""
    tables = defaultdict(lambda: {"columns": [], "column_count": 0})
    
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            table_name = row["table_name"]
            tables[table_name]["columns"].append({
                "name": row["column_name"],
                "type": row.get("full_data_type", row.get("data_type", "STRING")),
                "nullable": row.get("is_nullable", "YES") == "YES",
                "comment": row.get("comment", ""),
                "ordinal": int(row.get("ordinal_position", 0)),
            })
            tables[table_name]["column_count"] = len(tables[table_name]["columns"])
            tables[table_name]["catalog"] = row.get("table_catalog", "")
            tables[table_name]["schema"] = row.get("table_schema", "")
    
    return dict(tables)

schema = parse_schema_csv(Path("context/Wanderbricks_Schema.csv"))
print(f"Found {len(schema)} tables")
for table, info in sorted(schema.items()):
    print(f"  {table}: {info['column_count']} columns")
```

2. **Classify tables as dimensions, facts, or bridge/junction:**

```python
def classify_tables(schema: dict) -> dict:
    """Classify tables as dimension, fact, or bridge based on column patterns."""
    classified = {}
    for table_name, info in schema.items():
        cols = {c["name"] for c in info["columns"]}
        col_types = {c["name"]: c["type"] for c in info["columns"]}
        
        # Count FK-like columns (columns ending in _id that reference other tables)
        fk_columns = [c for c in cols if c.endswith("_id") and c != f"{table_name.rstrip('s')}_id"]
        pk_candidates = [c for c in cols if c == f"{table_name.rstrip('s')}_id" or c == f"{table_name}_id"]
        measure_types = {"FLOAT", "DOUBLE", "DECIMAL", "LONG", "INT"}
        measures = [c for c in cols if col_types.get(c, "").upper().split("(")[0] in measure_types 
                    and not c.endswith("_id")]
        timestamps = [c for c in cols if col_types.get(c, "").upper() in {"TIMESTAMP", "DATE"}]
        
        if len(info["columns"]) <= 3 and len(fk_columns) >= 2:
            entity_type = "bridge"
        elif len(fk_columns) >= 2 and len(measures) >= 1:
            entity_type = "fact"
        elif len(timestamps) >= 2 and len(fk_columns) >= 2:
            entity_type = "fact"
        else:
            entity_type = "dimension"
        
        classified[table_name] = {
            **info,
            "entity_type": entity_type,
            "pk_candidates": pk_candidates,
            "fk_columns": fk_columns,
            "measures": measures,
            "timestamps": timestamps,
        }
    return classified
```

3. **Identify FK relationships from column comments and naming patterns:**

```python
import re

def infer_relationships(classified: dict) -> list:
    """Infer FK relationships from column names and comments."""
    relationships = []
    table_names = set(classified.keys())
    
    for table_name, info in classified.items():
        for col in info["columns"]:
            # Pattern 1: Column comment says "Foreign Key to 'X'"
            if col.get("comment"):
                fk_match = re.search(r"[Ff]oreign [Kk]ey to ['\"]?(\w+)['\"]?", col["comment"])
                if fk_match:
                    ref_table = fk_match.group(1)
                    relationships.append({
                        "from_table": table_name,
                        "from_column": col["name"],
                        "to_table": ref_table,
                        "to_column": f"{ref_table.rstrip('s')}_id",
                        "source": "comment",
                    })
                    continue
            
            # Pattern 2: Column name like 'other_table_id' matches a known table
            if col["name"].endswith("_id"):
                base = col["name"][:-3]  # Remove '_id'
                for candidate in table_names:
                    if candidate == table_name:
                        continue
                    # Match: user_id → users, host_id → hosts, property_id → properties
                    if candidate.startswith(base) or candidate == base + "s" or candidate == base + "es":
                        relationships.append({
                            "from_table": table_name,
                            "from_column": col["name"],
                            "to_table": candidate,
                            "to_column": col["name"],
                            "source": "naming_convention",
                        })
                        break
    return relationships
```

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

| Field | Example | Source |
|-------|---------|--------|
| Project Name | `wanderbricks_analytics` | User input |
| Source Schema | `wanderbricks` | Extracted from schema CSV |
| Gold Schema | `wanderbricks_gold` | User input (convention: `{project}_gold`) |
| Business Domain | `travel`, `hospitality` | Inferred from schema CSV tables |
| Primary Use Cases | booking analytics, revenue reporting | User input |
| Key Stakeholders | Revenue Ops, Marketing | User input |
| Reporting Frequency | Daily, Weekly, Monthly | User input |
| Table Count | 15 tables (8 dims, 5 facts, 2 bridge) | Extracted from Phase 0 |
| Inferred Relationships | 12 FK relationships | Extracted from Phase 0 |

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

**MANDATORY: Read this skill using the Read tool BEFORE defining fact table grains:**

1. `skills/gold/fact-table-grain-validation/SKILL.md` — Grain inference from PRIMARY KEY structure, transaction vs aggregated vs snapshot patterns, PK-grain decision tree

**Apply from skill:**
- Infer grain type from PRIMARY KEY structure (transaction, aggregated, snapshot)
- Document grain explicitly for each fact table
- Validate PRIMARY KEY matches grain type using decision tree

**Key Outputs:**
- Dimensions table (name, business key, SCD type, source Silver table)
- Facts table (name, grain, source Silver tables, update frequency)
- Measures table (name, data type, calculation logic, business purpose)
- Relationships table (fact FK → dimension PK, cardinality)
- Domain assignments table (table → domain mapping)

---

### Phase 3: ERD Creation

**MANDATORY: Read this skill using the Read tool BEFORE creating any ERD diagrams:**

1. `skills/gold/mermaid-erd-patterns/SKILL.md` — ERD organization strategy (master/domain/summary), Mermaid syntax standards, domain emoji markers, relationship patterns, cross-domain references

**Activities:**
1. Count tables to determine ERD strategy (1-8, 9-20, 20+)
2. Create Master ERD (`erd_master.md`) with ALL tables grouped by domain
3. Create Domain ERDs (`erd/erd_{domain}.md`) if 9+ tables
4. Create Summary ERD (`erd_summary.md`) if 20+ tables
5. Add Domain Index table to Master ERD

**Critical Rules (from mermaid-erd-patterns):**
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

1. `skills/gold/yaml-driven-gold-setup/SKILL.md` — YAML schema file structure, domain-organized directories, column definition format, PK/FK in YAML
2. `skills/gold/gold-layer-documentation/SKILL.md` — Dual-purpose description pattern (`[Definition]. Business: [...]. Technical: [...].`), surrogate key naming, TBLPROPERTIES metadata, column comment standards

**Activities:**
1. Create domain-organized YAML directory structure (`yaml/{domain}/`)
2. Generate one YAML file per table using templates from `yaml-driven-gold-setup`
3. Include complete column definitions with lineage metadata
4. Document PRIMARY KEY and FOREIGN KEY constraints
5. Apply standard table properties (CDF, row tracking, auto-optimize)
6. Write dual-purpose descriptions following `gold-layer-documentation` patterns

**Critical Rules (from gold-layer-documentation + Non-Negotiable Defaults):**
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

1. `skills/gold/gold-layer-schema-validation/SKILL.md` — Schema consistency validation, DDL-first workflow, column matching between YAML and ERD

**Also read:** `references/validation-checklists.md`

**Validation Activities:**
1. Consistency check: YAML ↔ ERD ↔ Lineage CSV (all columns match)
2. Validate all ERD columns exist in YAML definitions
3. Validate all YAML columns have lineage metadata
4. Validate PRIMARY KEY definitions match grain type
5. Validate FOREIGN KEY references point to valid tables/columns
6. Run lineage validation script

**Outputs:**
- Validation report (pass/fail for each category)
- List of inconsistencies to fix
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

1. `skills/gold/01-gold-layer-setup/SKILL.md` — End-to-end implementation of tables, merge scripts, FK constraints, and Asset Bundle jobs from the YAML designs created here

That skill will in turn invoke:
- `gold-layer-merge-patterns` — SCD Type 1/2 dimension merges, fact aggregation patterns
- `gold-delta-merge-deduplication` — Mandatory deduplication before MERGE
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

## External References

- [Kimball Dimensional Modeling](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/)
- [Unity Catalog Constraints](https://docs.databricks.com/data-governance/unity-catalog/constraints.html)
- [Mermaid ERD Syntax](https://mermaid.js.org/syntax/entityRelationshipDiagram.html)
- [AgentSkills.io Specification](https://agentskills.io/specification)
