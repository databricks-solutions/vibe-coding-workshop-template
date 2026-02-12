-- =============================================================================
-- Section Input Prompts DML — Steps 5-11
-- Updated to align with Data Product Accelerator v1.3.0 skills-first architecture
-- All references to deleted context/prompts/ and .cursor/rules/ have been
-- replaced with the correct skills/ SKILL.md paths per QUICKSTART.md
-- =============================================================================

-- Step 9: Table Metadata & Data Dictionary (Bronze Layer) - bypass_llm=TRUE
INSERT INTO ${catalog}.${schema}.section_input_prompts 
(input_id, section_tag, input_template, system_prompt, section_title, section_description, order_number, how_to_apply, expected_output, bypass_llm, version, is_active, inserted_at, updated_at, created_by)
VALUES
(5, 'bronze_table_metadata',
'Copy and paste this prompt to the AI:

```
Run this SQL query and save results to CSV:

Query: SELECT * FROM samples.information_schema.columns WHERE table_schema = ''wanderbricks'' ORDER BY table_name, ordinal_position

Output: context/Wanderbricks_Schema.csv

---

Technical reference (for AI execution):

1. Get warehouse ID:
   databricks warehouses list --output json | jq ''.[0].id''

2. Execute SQL via Statement Execution API:
   databricks api post /api/2.0/sql/statements --json ''{
     "warehouse_id": "<WAREHOUSE_ID>",
     "statement": "<SQL_QUERY>",
     "wait_timeout": "50s",
     "format": "JSON_ARRAY"
   }'' > /tmp/sql_result.json

3. Convert JSON to CSV with Python:
   python3 << ''EOF''
   import json, csv
   with open(''/tmp/sql_result.json'', ''r'') as f:
       result = json.load(f)
   if result.get(''status'', {}).get(''state'') != ''SUCCEEDED'':
       print(f"Query failed: {result.get(''status'')}")
       exit(1)
   columns = [col[''name''] for col in result[''manifest''][''schema''][''columns'']]
   data = result[''result''][''data_array'']
   with open(''<OUTPUT_FILE>'', ''w'', newline='''') as f:
       writer = csv.writer(f)
       writer.writerow(columns)
       writer.writerows(data)
   print(f"Saved {len(data)} rows to <OUTPUT_FILE>")
   EOF

Known warehouse ID: <YOUR_WAREHOUSE_ID> (get via: databricks warehouses list --output json | jq ''.[0].id'')

Common queries:
- Schema info: SELECT * FROM <catalog>.information_schema.columns WHERE table_schema = ''<schema>'' ORDER BY table_name, ordinal_position
- Table list: SELECT * FROM <catalog>.information_schema.tables WHERE table_schema = ''<schema>''
- Sample data: SELECT * FROM <catalog>.<schema>.<table> LIMIT 1000

Expected output (for schema query):
- Console: "Saved 114 rows to context/Wanderbricks_Schema.csv"
- CSV file with columns: table_catalog, table_schema, table_name, column_name, ordinal_position, is_nullable, data_type, comment, ...

Sample CSV rows:
table_catalog,table_schema,table_name,column_name,ordinal_position,...,data_type,...,comment
samples,wanderbricks,amenities,amenity_id,0,...,LONG,...,Unique identifier of the amenity
samples,wanderbricks,amenities,name,1,...,STRING,...,"Name of the amenity (e.g., Wi-Fi, Pool)"
samples,wanderbricks,bookings,booking_id,0,...,LONG,...,Unique identifier of the booking
```',
'Static prompt - no LLM processing required. This prompt is copied directly to the AI coding assistant.',
'Table Metadata & Data Dictionary',
'Extract table schema metadata from Databricks and save as CSV for data dictionary reference',
8,
'## Prerequisite

**Run this in your cloned Template Repository** (see Prerequisites in Step 0).

Ensure Databricks CLI is authenticated.

---

## Steps to Apply

1. Copy the generated prompt using the copy button
2. Paste it into Cursor or VS Code with Copilot
3. The AI will execute the SQL query via Databricks CLI
4. Schema metadata will be saved to context/Wanderbricks_Schema.csv

**Note:** This creates context/Wanderbricks_Schema.csv which documents the Bronze layer tables.

---

## 🔧 What Happens Behind the Scenes

This step does **not** invoke an Agent Skill — it runs a direct SQL extraction via the Databricks CLI. The resulting CSV becomes the **starting input** for the entire Design-First Pipeline:

```
context/Wanderbricks_Schema.csv
  → Gold Design (Step 9)   — reads CSV to design dimensional model
  → Bronze (Step 10)       — uses schema to create tables
  → Silver (Step 11)       — uses schema for DQ expectations
  → Gold Impl (Step 12)    — uses YAML schemas derived from this CSV
```

Every subsequent skill references this CSV (or artifacts derived from it) to **extract** table names, column names, and data types — never generating them from scratch. This is the "Extract, Don''t Generate" principle.

### 🏅 Databricks Best Practices Applied

| Practice | How It''s Used Here |
|----------|-------------------|
| **Unity Catalog `information_schema`** | Queries `information_schema.columns` — the standard UC metadata catalog — instead of proprietary DESCRIBE commands |
| **SQL Statement Execution API** | Uses the REST API (`/api/2.0/sql/statements`) for programmatic SQL execution — the production-grade approach for CI/CD |
| **Data Dictionary as Governance Foundation** | The CSV captures table/column COMMENTs from UC, establishing metadata lineage from day one |
| **Serverless SQL Warehouse** | Executes against a SQL warehouse (not a cluster) for cost-efficient, instant-start queries |',
'## Expected Deliverables

- context/Wanderbricks_Schema.csv file created
- Contains ~114 rows of column metadata
- Includes: table_name, column_name, data_type, comment
- Ready for use as data dictionary reference
- **This CSV is the starting input for the entire Design-First Pipeline** (all subsequent steps reference it)',
true, 1, true, current_timestamp(), current_timestamp(), current_user());

-- Step 9: Gold Layer Design (PRD-aligned) - bypass_LLM = TRUE
INSERT INTO ${catalog}.${schema}.section_input_prompts 
(input_id, section_tag, input_template, system_prompt, section_title, section_description, order_number, how_to_apply, expected_output, bypass_llm, version, is_active, inserted_at, updated_at, created_by)
VALUES
(6, 'gold_layer_design',
'I have a customer schema at @data_product_accelerator/context/Schema.csv.

Please design the Gold layer using @data_product_accelerator/skills/gold/00-gold-layer-design/SKILL.md

The orchestrator skill will automatically load its worker skills for merge patterns, deduplication, documentation standards, Mermaid ERDs, schema validation, grain validation, and YAML-driven setup.',
'Static prompt - no LLM processing required. This prompt is copied directly to the AI coding assistant.',
'Gold Layer Design (PRD-aligned)',
'Design Gold layer using project skills with YAML definitions and Mermaid ERD',
9,
'## 📚 What is the Gold Layer?

The Gold Layer is the **business-ready** analytics layer that transforms Silver data into dimensional models optimized for reporting, dashboards, and AI/ML consumption.

### Why Design Before Implementation?

| Principle | Benefit |
|-----------|---------|
| **Design First** | Catch errors before writing code |
| **YAML as Source of Truth** | Schema changes are reviewable diffs |
| **ERD Documentation** | Visual communication with stakeholders |
| **Documented Grain** | Prevents incorrect aggregations |
| **Lineage Tracking** | Know where every column comes from |

---

## 🏗️ Gold Layer Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           GOLD LAYER DESIGN                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        DIMENSIONAL MODEL                            │   │
│  │                                                                     │   │
│  │   ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    │   │
│  │   │dim_store │    │dim_product│   │dim_date  │    │dim_host  │    │   │
│  │   │ (SCD2)   │    │ (SCD1)   │    │ (Static) │    │ (SCD2)   │    │   │
│  │   └────┬─────┘    └────┬─────┘    └────┬─────┘    └────┬─────┘    │   │
│  │        │               │               │               │          │   │
│  │        └───────────────┴───────┬───────┴───────────────┘          │   │
│  │                                │                                   │   │
│  │                        ┌───────▼───────┐                          │   │
│  │                        │ fact_bookings │                          │   │
│  │                        │   (Daily)     │                          │   │
│  │                        └───────────────┘                          │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Design Artifacts:                                                          │
│  • ERD Diagrams (Mermaid)      • YAML Schema Files                         │
│  • Column Lineage              • Business Documentation                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Prerequisite

**Run this in your cloned Template Repository** (see Prerequisites in Step 0).

Ensure you have:
- ✅ `context/Schema.csv` - Your source schema file (from Bronze/Silver)
- ✅ `data_product_accelerator/skills/gold/00-gold-layer-design/SKILL.md` - The Gold layer design orchestrator skill

---

## Steps to Apply

### Step 1: Start New Agent Thread

Open Cursor and start a **new Agent thread** for clean context.

### Step 2: Copy and Paste the Prompt

1. **Copy the prompt** using the copy button
2. **Paste it into Cursor**
3. The AI will read your schema and the orchestrator skill, which automatically loads all worker skills

### Step 3: Review Generated Design

The AI will create the `gold_layer_design/` folder with:
- ERD diagrams
- YAML schema files
- Lineage documentation

### Step 4: Validate the Design

Check these key elements:

| Element | What to Verify |
|---------|----------------|
| **Grain** | Each fact table has explicit grain definition |
| **SCD Type** | Each dimension has SCD1 or SCD2 specified |
| **Relationships** | All FK relationships documented |
| **Lineage** | Every column traces back to source |

### Step 5: Get Stakeholder Sign-off

Share the ERD and design summary with business stakeholders before proceeding to implementation.

---

## 🔧 What Happens Behind the Scenes

This framework uses a **skills-first architecture** with an **orchestrator/worker pattern**:

1. You paste **one prompt** referencing the orchestrator: `@data_product_accelerator/skills/gold/00-gold-layer-design/SKILL.md`
2. The AI reads the orchestrator skill, which lists **mandatory dependencies** (worker skills + common skills)
3. The AI automatically loads each worker skill as needed during the workflow
4. You never need to reference individual worker skills — the orchestrator handles it

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     ORCHESTRATOR / WORKER PATTERN                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  YOUR PROMPT                                                                │
│  "@data_product_accelerator/skills/gold/00-gold-layer-design/SKILL.md"                              │
│         │                                                                   │
│         ▼                                                                   │
│  ┌─────────────────────────────────────┐                                   │
│  │  ORCHESTRATOR (00-gold-layer-design)│                                   │
│  │  Manages the full design workflow   │                                   │
│  └──────────────┬──────────────────────┘                                   │
│                 │  automatically loads                                      │
│    ┌────────────┼────────────┬────────────┐                                │
│    ▼            ▼            ▼            ▼                                 │
│  ┌──────┐  ┌──────┐   ┌──────┐   ┌──────┐   + 3 more workers             │
│  │ 02-  │  │ 03-  │   │ 06-  │   │ 08-  │                                 │
│  │ YAML │  │ Docs │   │Grain │   │ ERD  │                                 │
│  └──────┘  └──────┘   └──────┘   └──────┘                                 │
│                                                                             │
│  + Common Skills: naming-tagging-standards, databricks-expert-agent        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📋 Worker Skills (Loaded Automatically by Orchestrator)

| Worker Skill | Path | Purpose |
|-----------|------|---------|
| `02-yaml-driven-gold-setup` | `data_product_accelerator/skills/gold/02-*/SKILL.md` | YAML as single source of truth for schemas |
| `03-gold-layer-documentation` | `data_product_accelerator/skills/gold/03-*/SKILL.md` | Dual-purpose (business + technical) documentation standards |
| `04-gold-layer-merge-patterns` | `data_product_accelerator/skills/gold/04-*/SKILL.md` | MERGE/upsert patterns for dimension and fact tables |
| `05-gold-delta-merge-deduplication` | `data_product_accelerator/skills/gold/05-*/SKILL.md` | Handling duplicates in MERGE operations |
| `06-fact-table-grain-validation` | `data_product_accelerator/skills/gold/06-*/SKILL.md` | Grain definition and validation patterns |
| `07-gold-layer-schema-validation` | `data_product_accelerator/skills/gold/07-*/SKILL.md` | Schema validation before deployment |
| `08-mermaid-erd-patterns` | `data_product_accelerator/skills/gold/08-*/SKILL.md` | ERD diagram syntax and organization |

---

### 🏅 Databricks Best Practices Applied

| Practice | How It''s Used Here |
|----------|-------------------|
| **YAML-Driven Dimensional Modeling** | Gold schemas defined as YAML files — reviewable, version-controlled, machine-readable. No embedded DDL strings in Python. |
| **Star Schema with Surrogate Keys** | Dimensions use surrogate keys (BIGINT) as PRIMARY KEYs, not business keys. Facts reference surrogate PKs via FOREIGN KEY constraints. |
| **SCD Type 1 / Type 2 Classification** | Every dimension is classified: SCD1 (overwrite, e.g., `dim_destination`) or SCD2 (versioned with `is_current`/`valid_from`/`valid_to`, e.g., `dim_property`). |
| **Dual-Purpose COMMENTs** | Table and column COMMENTs serve both business users AND Genie/LLMs — written to be human-readable and machine-parseable simultaneously. |
| **Mermaid ERDs for Documentation** | Entity-Relationship Diagrams use Mermaid syntax — renderable in Databricks notebooks, GitHub, and any Markdown viewer. |
| **Column-Level Lineage** | Every Gold column traces back to its Silver source table and column with transformation type (DIRECT_COPY, AGGREGATION, DERIVATION). |
| **Grain Documentation** | Every fact table has an explicit grain statement (e.g., "One row per booking transaction") — prevents incorrect aggregations and joins. |',
'## Expected Deliverables

### 📁 Generated Folder Structure

```
gold_layer_design/
├── README.md                           # Navigation hub
├── erd_master.md                       # Complete ERD (ALWAYS)
├── erd_summary.md                      # Domain overview (if 20+ tables)
├── erd/                                # Domain ERDs (if 9+ tables)
│   ├── erd_booking.md
│   ├── erd_property.md
│   └── erd_host.md
├── yaml/                               # YAML schemas by domain
│   ├── booking/
│   │   ├── dim_booking.yaml
│   │   └── fact_booking_daily.yaml
│   ├── property/
│   │   ├── dim_property.yaml
│   │   └── dim_destination.yaml
│   └── host/
│       └── dim_host.yaml
├── docs/
│   └── BUSINESS_ONBOARDING_GUIDE.md    # ⭐ Business context and stories
├── COLUMN_LINEAGE.csv                  # ⭐ Machine-readable lineage
├── COLUMN_LINEAGE.md                   # Human-readable lineage
├── SOURCE_TABLE_MAPPING.csv            # ⭐ Source table rationale
├── DESIGN_SUMMARY.md                   # Grain, SCD, decisions
└── DESIGN_GAP_ANALYSIS.md             # Coverage analysis
```

---

### 📊 ERD Organization (Based on Table Count)

| Total Tables | ERD Strategy |
|--------------|--------------|
| **1-8 tables** | Master ERD only |
| **9-20 tables** | Master ERD + Domain ERDs |
| **20+ tables** | Master ERD + Summary ERD + Domain ERDs |

---

### 📝 YAML Schema Example

```yaml
# gold_layer_design/yaml/booking/fact_booking_daily.yaml
table_name: fact_booking_daily
domain: booking
grain: "One row per property-date combination"

primary_key:
  columns: [''property_id'', ''check_in_date'']
  composite: true

foreign_keys:
  - columns: [''property_id'']
    references: dim_property(property_id)
  - columns: [''host_id'']
    references: dim_host(host_id)

columns:
  - name: property_id
    type: BIGINT
    nullable: false
    description: >
      Property identifier.
      Business: Links to property dimension.
      Technical: FK to dim_property.property_id.
    lineage:
      silver_table: silver_bookings
      silver_column: property_id
      transformation: "DIRECT_COPY"
```

---

### ✅ Success Criteria Checklist

**ERD Artifacts:**
- [ ] Master ERD created with all tables
- [ ] Domain ERDs created (if 9+ tables)
- [ ] All relationships shown with cardinality

**YAML Schemas:**
- [ ] One YAML file per table
- [ ] Organized by domain folders
- [ ] Primary keys defined
- [ ] Foreign keys defined
- [ ] Column lineage documented

**Mandatory Documentation:**
- [ ] COLUMN_LINEAGE.csv created
- [ ] SOURCE_TABLE_MAPPING.csv created
- [ ] BUSINESS_ONBOARDING_GUIDE.md created
- [ ] DESIGN_SUMMARY.md created

**Validation:**
- [ ] Grain explicitly stated for each fact
- [ ] SCD type specified for each dimension
- [ ] All columns trace back to source
- [ ] Stakeholder sign-off obtained',
true, 1, true, current_timestamp(), current_timestamp(), current_user());

-- Step 10: Bronze Layer Creation (Approach C - Copy Sample Data) - bypass_LLM = TRUE
INSERT INTO ${catalog}.${schema}.section_input_prompts 
(input_id, section_tag, input_template, system_prompt, section_title, section_description, order_number, how_to_apply, expected_output, bypass_llm, version, is_active, inserted_at, updated_at, created_by)
VALUES
(7, 'bronze_layer_creation',
'Set up the Bronze layer using @data_product_accelerator/skills/bronze/00-bronze-layer-setup/SKILL.md with Approach C — copy data from the existing source tables in the samples.wanderbricks schema.

Use default catalog as: <YOUR_CATALOG>',
'Static prompt - no LLM processing required. This prompt is copied directly to the AI coding assistant.',
'Bronze Layer Creation (Approach C)',
'Create Bronze layer by copying sample data from samples.wanderbricks with Asset Bundle structure',
10,
'## 📚 What is the Bronze Layer?

The Bronze Layer is the **raw data landing zone** in the Medallion Architecture. It preserves source data exactly as received, enabling full traceability and reprocessing.

### Why Bronze Matters

| Principle | Benefit |
|-----------|---------|
| **Raw Preservation** | Keep original data for audit and replay |
| **Change Data Feed** | Enable incremental processing downstream |
| **Schema Evolution** | Handle schema changes gracefully |
| **Single Source** | One place for all raw data ingestion |

---

## 🏗️ Bronze Layer in Medallion Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        MEDALLION ARCHITECTURE                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                     │
│  │   BRONZE    │───▶│   SILVER    │───▶│    GOLD     │                     │
│  │   (Raw)     │CDF │  (Cleaned)  │CDF │  (Business) │                     │
│  └─────────────┘    └─────────────┘    └─────────────┘                     │
│        ▲                                                                    │
│        │                                                                    │
│  ┌─────┴─────┐                                                             │
│  │  SOURCE   │  ◀── This step creates Bronze from source                   │
│  │   DATA    │                                                              │
│  └───────────┘                                                              │
│                                                                             │
│  CDF = Change Data Feed (enables incremental processing)                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔀 Three Approaches for Bronze Data

This framework supports 3 approaches for Bronze data:

| Approach | When to Use | What Happens |
|----------|-------------|--------------|
| **A: Generate Fake Data** | Testing/demos before customer delivery | Create DDLs, populate with Faker library |
| **B: Use Existing Bronze** | Customer already has Bronze layer | Skip this step, connect directly |
| **C: Copy from External** | Sample data available (THIS WORKSHOP) | Clone tables from `samples.wanderbricks` |

### 🎯 This Prompt Uses Approach C

We copy sample data from `samples.wanderbricks` because:
- ✅ Real-world data structure (vacation rentals domain)
- ✅ Immediate data availability
- ✅ No synthetic data generation needed
- ✅ Focus on pipeline development, not data creation

---

## Prerequisite

**Run this in your cloned Template Repository** (see Prerequisites in Step 0).

Ensure you have:
- ✅ `data_product_accelerator/skills/bronze/00-bronze-layer-setup/SKILL.md` - The Bronze layer setup skill
- ✅ Access to `samples.wanderbricks` catalog in your Databricks workspace
- ✅ Permissions to create tables in your target catalog

---

## Steps to Apply

### Step 1: Start New Agent Thread

Open Cursor and start a **new Agent thread** for clean context.

### Step 2: Copy and Paste the Prompt

1. **Copy the prompt** using the copy button
2. **Paste it into Cursor**
3. **Update the catalog name** to your target catalog

### Step 3: Review Generated Code

The AI will create:
- Asset Bundle configuration (`databricks.yml`)
- Clone script (`src/wanderbricks_bronze/clone_samples.py`)
- Job definition (`resources/bronze/bronze_clone_job.yml`)

### Step 4: Validate the Bundle

```bash
# Validate bundle configuration
databricks bundle validate -t dev

# Expected: No errors, all resources validated
```

### Step 5: Deploy the Bundle

```bash
# Deploy to Databricks workspace
databricks bundle deploy -t dev

# Expected: Job created successfully
```

### Step 6: Run the Bronze Clone Job

```bash
# Run the Bronze clone job
databricks bundle run -t dev bronze_clone_job

# Or trigger from Databricks UI:
# Workflows → Jobs → [dev] Bronze Clone Job → Run Now
```

### Step 7: Verify in Databricks UI

After job completes:

```sql
-- List all Bronze tables
SHOW TABLES IN {catalog}.{bronze_schema};

-- Check row counts
SELECT COUNT(*) FROM {catalog}.{bronze_schema}.bookings;

-- Verify CDF is enabled
DESCRIBE EXTENDED {catalog}.{bronze_schema}.bookings;
-- Look for: delta.enableChangeDataFeed = true
```

---

## 🔧 What Happens Behind the Scenes

When you paste the prompt, the AI reads `@data_product_accelerator/skills/bronze/00-bronze-layer-setup/SKILL.md` — the **Bronze orchestrator skill**. Behind the scenes:

1. **Orchestrator reads approach** — detects "Approach C" and activates the clone-from-source workflow
2. **Common skills auto-loaded** — the orchestrator''s mandatory dependencies include:
   - `databricks-table-properties` — ensures CDF, liquid clustering, auto-optimize are set
   - `databricks-asset-bundles` — generates proper `databricks.yml` and job YAML
   - `naming-tagging-standards` — applies enterprise naming conventions and COMMENTs
   - `schema-management-patterns` — handles `CREATE SCHEMA IF NOT EXISTS`
   - `databricks-python-imports` — handles shared code modules between notebooks
3. **Code generation** — the skill produces clone scripts that read from `samples.wanderbricks` and write to your catalog with all best practices applied
4. **Deploy loop** — if deployment fails, the `databricks-autonomous-operations` skill kicks in for self-healing (deploy → poll → diagnose → fix → redeploy)

### 🏅 Databricks Best Practices Applied

| Practice | How It''s Used Here |
|----------|-------------------|
| **Change Data Feed (CDF)** | `delta.enableChangeDataFeed = true` on every Bronze table — enables Silver to read only changed rows instead of full table scans |
| **Liquid Clustering** | `CLUSTER BY AUTO` — Databricks automatically chooses optimal clustering columns and reorganizes data layout over time |
| **Auto-Optimize** | `delta.autoOptimize.optimizeWrite = true` + `autoCompact = true` — automatic small file compaction, no manual OPTIMIZE needed |
| **Unity Catalog Governance** | All tables registered in Unity Catalog with proper catalog.schema.table naming, enabling lineage, access control, and discovery |
| **Schema-on-Read with Evolution** | Bronze preserves raw source schema; downstream layers handle schema evolution gracefully |
| **Databricks Asset Bundles (DAB)** | Infrastructure as Code — `databricks.yml` defines jobs, targets, and resources. Deploy with `databricks bundle deploy` for repeatable, CI/CD-ready deployments |
| **Serverless Jobs** | Jobs run on serverless compute — no cluster management, instant startup, pay-per-use cost model |
| **Enterprise Naming Standards** | Tables follow `{schema}.{table_name}` convention; COMMENTs applied to tables and columns for data discovery |

---

## ⚠️ Important: Update Catalog Name

The prompt uses `<YOUR_CATALOG>` as a placeholder.

**You MUST replace this** with your target catalog name before pasting:

```
Use default catalog as: YOUR_CATALOG_NAME_HERE
```

**Note on placeholders in this guide:**
- `{catalog}` = your target catalog name (e.g., `prashanth_catalog`)
- `{bronze_schema}` = the Bronze schema created by the skill (typically `wanderbricks_bronze` — derived from the source schema name)
- Replace these when running verification queries after deployment',
'## Expected Deliverables

### 📁 Generated Asset Bundle Structure

```
project_root/
├── databricks.yml                      # Bundle configuration (updated)
├── src/
│   └── wanderbricks_bronze/
│       ├── __init__.py
│       └── clone_samples.py            # Code to copy sample data
└── resources/
    └── bronze/
        └── bronze_clone_job.yml        # Job configuration
```

---

### 🔄 What the Clone Script Does

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        BRONZE CLONE PROCESS                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  SOURCE                           TARGET                                    │
│  samples.wanderbricks     →       {your_catalog}.{bronze_schema}           │
│                                                                             │
│  ┌─────────────────────┐          ┌─────────────────────┐                  │
│  │ amenities           │  CREATE  │ amenities           │ + CDF enabled    │
│  │ booking_updates     │  TABLE   │ booking_updates     │ + CLUSTER BY AUTO│
│  │ bookings            │   AS     │ bookings            │ + Auto-optimize  │
│  │ clickstream         │ SELECT   │ clickstream         │ + TBLPROPERTIES  │
│  │ countries           │ ──────▶  │ countries           │ + COMMENTs       │
│  │ customer_support_.. │          │ customer_support_.. │                  │
│  │ destinations        │          │ destinations        │                  │
│  │ employees           │          │ employees           │                  │
│  │ hosts               │          │ hosts               │                  │
│  │ page_views          │          │ page_views          │                  │
│  │ payments            │          │ payments            │                  │
│  │ properties          │          │ properties          │                  │
│  │ property_amenities  │          │ property_amenities  │                  │
│  │ property_images     │          │ property_images     │                  │
│  │ reviews             │          │ reviews             │                  │
│  │ users               │          │ users               │                  │
│  └─────────────────────┘          └─────────────────────┘                  │
│                                     (16 tables total)                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 📊 Table Properties (Best Practices Enabled)

| Property | Setting | Why It Matters |
|----------|---------|----------------|
| **Liquid Clustering** | ✅ `CLUSTER BY AUTO` | Automatic data layout optimization |
| **Change Data Feed** | ✅ `delta.enableChangeDataFeed = true` | Enables incremental Silver processing |
| **Auto Optimize** | ✅ `delta.autoOptimize.optimizeWrite = true` | Automatic file compaction |
| **Auto Compact** | ✅ `delta.autoOptimize.autoCompact = true` | Reduces small files |

---

### 📋 Tables Cloned from samples.wanderbricks (16 tables)

| Table | Description | Columns |
|-------|-------------|---------|
| `amenities` | Property amenities (Wi-Fi, Pool, etc.) | 4 |
| `booking_updates` | Change log for booking modifications | 11 |
| `bookings` | Guest booking records | 10 |
| `clickstream` | User click behavior events | 5 |
| `countries` | Country reference data | 3 |
| `customer_support_logs` | Support ticket records | 5 |
| `destinations` | Travel destinations | 6 |
| `employees` | Company employee records | 10 |
| `hosts` | Property host profiles | 9 |
| `page_views` | Website page view events | 7 |
| `payments` | Payment transaction records | 6 |
| `properties` | Vacation rental listings | 13 |
| `property_amenities` | Property-to-amenity mapping (junction) | 2 |
| `property_images` | Property photo references | 6 |
| `reviews` | Guest reviews | 9 |
| `users` | Platform users (guests) | 8 |

---

### ✅ Verification Queries

After the job completes, run these queries to verify:

```sql
-- 1. List all Bronze tables
SHOW TABLES IN {catalog}.{bronze_schema};

-- 2. Check row counts for each table (all 16)
SELECT ''amenities'' as tbl, COUNT(*) as cnt FROM {catalog}.{bronze_schema}.amenities
UNION ALL SELECT ''booking_updates'', COUNT(*) FROM {catalog}.{bronze_schema}.booking_updates
UNION ALL SELECT ''bookings'', COUNT(*) FROM {catalog}.{bronze_schema}.bookings
UNION ALL SELECT ''clickstream'', COUNT(*) FROM {catalog}.{bronze_schema}.clickstream
UNION ALL SELECT ''countries'', COUNT(*) FROM {catalog}.{bronze_schema}.countries
UNION ALL SELECT ''customer_support_logs'', COUNT(*) FROM {catalog}.{bronze_schema}.customer_support_logs
UNION ALL SELECT ''destinations'', COUNT(*) FROM {catalog}.{bronze_schema}.destinations
UNION ALL SELECT ''employees'', COUNT(*) FROM {catalog}.{bronze_schema}.employees
UNION ALL SELECT ''hosts'', COUNT(*) FROM {catalog}.{bronze_schema}.hosts
UNION ALL SELECT ''page_views'', COUNT(*) FROM {catalog}.{bronze_schema}.page_views
UNION ALL SELECT ''payments'', COUNT(*) FROM {catalog}.{bronze_schema}.payments
UNION ALL SELECT ''properties'', COUNT(*) FROM {catalog}.{bronze_schema}.properties
UNION ALL SELECT ''property_amenities'', COUNT(*) FROM {catalog}.{bronze_schema}.property_amenities
UNION ALL SELECT ''property_images'', COUNT(*) FROM {catalog}.{bronze_schema}.property_images
UNION ALL SELECT ''reviews'', COUNT(*) FROM {catalog}.{bronze_schema}.reviews
UNION ALL SELECT ''users'', COUNT(*) FROM {catalog}.{bronze_schema}.users;

-- 3. Verify CDF is enabled (check any table)
DESCRIBE EXTENDED {catalog}.{bronze_schema}.bookings;
-- Look for: delta.enableChangeDataFeed = true

-- 4. Preview sample data
SELECT * FROM {catalog}.{bronze_schema}.bookings LIMIT 5;
```

---

### ✅ Success Criteria Checklist

**Bundle Deployment:**
- [ ] `databricks bundle validate` passes with no errors
- [ ] `databricks bundle deploy` completes successfully
- [ ] Job appears in Databricks Workflows UI

**Job Execution:**
- [ ] Bronze clone job runs without errors
- [ ] All 16 tables cloned successfully
- [ ] Job completes in < 10 minutes

**Table Verification:**
- [ ] All tables visible in Unity Catalog
- [ ] Row counts match source tables
- [ ] CDF enabled on all tables
- [ ] Liquid clustering enabled
- [ ] Sample data looks correct',
true, 1, true, current_timestamp(), current_timestamp(), current_user());

-- Step 11: Silver Layer Pipelines (SDP with Centralized DQ Rules) - bypass_LLM = TRUE
INSERT INTO ${catalog}.${schema}.section_input_prompts 
(input_id, section_tag, input_template, system_prompt, section_title, section_description, order_number, how_to_apply, expected_output, bypass_llm, version, is_active, inserted_at, updated_at, created_by)
VALUES
(8, 'silver_layer_sdp',
'Set up the Silver layer using @data_product_accelerator/skills/silver/00-silver-layer-setup/SKILL.md

Ensure bundle is validated and deployed successfully, and silver layer jobs run with no errors.

Validate the results in the UI to ensure the DQ rules show up in centralized delta table, and that the silver layer pipeline runs successfully with Expectations being checked.',
'Static prompt - no LLM processing required. This prompt is copied directly to the AI coding assistant.',
'Silver Layer Pipelines (SDP)',
'Create Silver layer using Spark Declarative Pipelines with centralized data quality rules',
11,
'## 📚 What is the Silver Layer?

The Silver Layer transforms raw Bronze data into **cleaned, validated, and enriched** data ready for Gold layer consumption.

### Core Philosophy: Schema Cloning

Silver should **mirror the Bronze schema** with minimal changes — same column names, same data types, same grain. The value-add is **data quality**, not transformation:

| ✅ DO in Silver | ❌ DON''T do in Silver (save for Gold) |
|----------------|--------------------------------------|
| Apply DQ rules (null checks, range validation) | Aggregation (SUM, COUNT, GROUP BY) |
| Add derived flags (`is_return`, `is_out_of_stock`) | Join across tables |
| Add business keys (SHA256 hashes) | Complex business logic |
| Add `processed_timestamp` | Schema restructuring |
| Deduplicate records | Rename columns significantly |

**Why?** Silver is the validated copy of source data. Gold handles complex transformations. This keeps Silver focused on data quality and makes troubleshooting easier (column names match source).

### Why Spark Declarative Pipelines (SDP)?

| Feature | Benefit |
|---------|---------|
| **Incremental Ingestion** | Reads only changed data from Bronze using Change Data Feed (CDF) |
| **Built-in Quality Rules** | Expectations framework for data validation |
| **Serverless Compute** | Cost-efficient, auto-scaling execution |
| **Automatic Schema Evolution** | Handles schema changes gracefully |
| **Complete Lineage** | Full data lineage tracking in Unity Catalog |
| **Photon Engine** | Vectorized query execution for faster processing |

---

## Prerequisite

**Run this in your cloned Template Repository** (see Prerequisites in Step 0).

Ensure you have:
- ✅ Bronze layer created and populated (Step 10 complete)
- ✅ `data_product_accelerator/skills/silver/00-silver-layer-setup/SKILL.md` - The Silver layer setup skill (loads worker skills automatically)

---

## Steps to Apply

### Step 1: Generate Silver Layer Code

1. **Start a new Agent thread** in Cursor
2. **Copy the prompt** using the copy button
3. **Paste it into Cursor** and let the AI generate:
   - SDP pipeline notebooks
   - Data quality rules configuration
   - Asset Bundle job definitions

### Step 2: Validate the Bundle

```bash
# Validate bundle configuration
databricks bundle validate -t dev

# Expected: No errors, all resources validated
```

### Step 3: Deploy the Bundle

```bash
# Deploy to Databricks workspace
databricks bundle deploy -t dev

# Expected: Pipeline and jobs created successfully
```

### Step 4: Run DQ Rules Setup Job FIRST ⚠️

**CRITICAL: You must create the DQ rules table before running the pipeline — otherwise the pipeline fails with `Table or view not found: dq_rules`.**

```bash
# Run the DQ rules setup job (creates and populates dq_rules table)
databricks bundle run -t dev silver_dq_setup_job

# Verify the rules table was created:
# SELECT * FROM {catalog}.{silver_schema}.dq_rules
```

### Step 5: Run the Silver DLT Pipeline

```bash
# NOW run the DLT pipeline (it reads rules from the dq_rules table)
databricks bundle run -t dev silver_dlt_pipeline

# Or trigger from Databricks UI:
# Workflows → DLT Pipelines → [dev] Silver Layer Pipeline → Start
```

### Step 6: Validate Results in UI

After pipeline completes, verify in Databricks UI:

1. **Check DQ Rules Table:**
   ```sql
   SELECT * FROM {catalog}.{silver_schema}.dq_rules;
   ```
   ✅ Should show all configured quality rules

2. **Check Pipeline Event Log:**
   - Navigate to: Workflows → DLT Pipelines → Your Pipeline
   - Click "Data Quality" tab
   - ✅ Should show Expectations being evaluated

3. **Check Silver Tables:**
   ```sql
   SHOW TABLES IN {catalog}.{silver_schema};
   SELECT * FROM {catalog}.{silver_schema}.{table} LIMIT 10;
   ```
   ✅ Should show cleaned, validated data

---

## 🔧 What Happens Behind the Scenes

When you paste the prompt, the AI reads `@data_product_accelerator/skills/silver/00-silver-layer-setup/SKILL.md` — the **Silver orchestrator skill**. Behind the scenes:

1. **Orchestrator activates** — reads the Silver setup workflow with streaming ingestion and DQ rules
2. **Worker skills auto-loaded:**
   - `01-dlt-expectations-patterns` — creates portable DQ rules stored in Unity Catalog Delta tables (not hardcoded in notebooks)
   - `02-dqx-patterns` — Databricks DQX framework for advanced validation with detailed failure diagnostics
3. **Common skills auto-loaded (8 total):**
   - `databricks-expert-agent` — core "Extract, Don''t Generate" principle
   - `databricks-table-properties` — ensures proper TBLPROPERTIES (CDF, row tracking, auto-optimize)
   - `databricks-asset-bundles` — generates DLT pipeline YAML and DQ setup job YAML
   - `databricks-python-imports` — ensures `dq_rules_loader.py` is pure Python (no notebook header)
   - `unity-catalog-constraints` — PK constraint on `dq_rules` table: `(table_name, rule_name)`
   - `schema-management-patterns` — `CREATE SCHEMA IF NOT EXISTS` with governance metadata
   - `naming-tagging-standards` — enterprise naming conventions and dual-purpose COMMENTs
   - `databricks-autonomous-operations` — self-healing deploy loop if pipeline fails
4. **Key innovation: Runtime-updateable DQ rules** — expectations are stored in a Delta table, not in code. You can update rules without redeploying the pipeline.

### 🏅 Databricks Best Practices Applied

| Practice | How It''s Used Here |
|----------|-------------------|
| **Spark Declarative Pipelines (SDP/DLT)** | Silver uses SDP for declarative, streaming-first pipelines — define WHAT the data should look like, not HOW to process it |
| **Legacy `import dlt` API** | Uses `import dlt` (not modern `pyspark.pipelines`) because the DQ rules framework depends on `@dlt.expect_all_or_drop()` decorators. Will migrate when Databricks ports expectations to the modern API. |
| **CDF-Based Incremental Reads** | Silver reads from Bronze using Change Data Feed — only processing new/changed rows, not full table scans |
| **Expectations Framework** | DLT Expectations with severity levels: `@dlt.expect_all()` (warn but keep), `@dlt.expect_all_or_drop()` (quarantine bad rows), `@dlt.expect_or_fail()` (halt pipeline — avoided in favor of drop) |
| **Centralized DQ Rules in Delta Tables** | Quality rules stored in `dq_rules` Delta table — updateable at runtime via SQL without code redeployment. PK constraint on `(table_name, rule_name)`. |
| **Quarantine Pattern** | Records failing critical DQ rules are routed to quarantine tables for investigation, not silently dropped |
| **Row Tracking** | `delta.enableRowTracking = true` on EVERY Silver table — required for downstream Gold Materialized Views to use incremental refresh instead of expensive full recomputation |
| **Photon + ADVANCED Edition** | `photon: true` and `edition: ADVANCED` are non-negotiable in pipeline YAML — Photon for vectorized execution, ADVANCED for expectations/CDC support |
| **Serverless DLT Compute** | `serverless: true` in pipeline YAML — auto-scaling, no cluster configuration, no `clusters:` block |
| **Schema Cloning Philosophy** | Silver mirrors Bronze schema (same column names, same grain, no aggregation, no joins). Only adds: DQ rules, derived flags, business keys, `processed_timestamp`. Aggregation belongs in Gold. |
| **Unity Catalog Integration** | Silver tables are UC-managed, inheriting governance, lineage tracking, and access controls from Bronze |
| **Pure Python DQ Loader** | `dq_rules_loader.py` has NO notebook header — it''s a pure Python module importable by DLT notebooks. Cache pattern uses `toPandas()` (not `.collect()`) for performance. |
| **2-Job Deployment Pattern** | Two separate resources: (1) `silver_dq_setup_job` — regular job that creates and populates the `dq_rules` table, (2) `silver_dlt_pipeline` — DLT pipeline that reads rules from the table. Setup job MUST run first. |
| **Data Quality Monitoring** | DQ monitoring views created inside the DLT pipeline — per-table metrics, referential integrity checks, data freshness. Feeds into observability dashboards in later steps. |

---

## 🔍 Key Validation Points

| What to Check | Where | Expected Result |
|---------------|-------|-----------------|
| DQ Rules loaded | `dq_rules` table | Rules visible in Delta table |
| Expectations running | Pipeline event log | Pass/Warn/Fail counts shown |
| Data quality | Silver tables | Clean, standardized data |
| Incremental working | Pipeline metrics | Only new/changed rows processed |',
'## Expected Deliverables

### 📁 Generated Files

```
project_root/
├── databricks.yml                        # Updated with Silver resources
├── src/
│   └── wanderbricks_silver/
│       ├── setup_dq_rules_table.py       # Notebook: Create & populate DQ rules Delta table
│       ├── dq_rules_loader.py            # Pure Python module (NO notebook header!)
│       ├── silver_dimensions.py          # DLT notebook: Dimension tables
│       ├── silver_facts.py               # DLT notebook: Fact tables with quarantine
│       └── data_quality_monitoring.py    # DLT notebook: DQ metrics & freshness views
└── resources/
    └── silver/
        ├── silver_dq_setup_job.yml       # Job: Creates dq_rules table (run FIRST)
        └── silver_dlt_pipeline.yml       # DLT pipeline configuration
```

> **Key file note:** `dq_rules_loader.py` must be a **pure Python module** (no `# Databricks notebook source` header). This is because DLT notebooks import it as a regular module. If it has a notebook header, imports break.

---

### 🔄 Silver Layer Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SILVER LAYER (SDP Pipeline)                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌──────────────────┐    ┌─────────────────────┐        │
│  │   Bronze    │───▶│  SDP Pipeline    │───▶│   Silver Tables     │        │
│  │   Tables    │    │  (Serverless)    │    │   (Cleaned Data)    │        │
│  │   (CDF)     │    │                  │    │                     │        │
│  └─────────────┘    │  • Read CDF      │    └─────────────────────┘        │
│                     │  • Apply DQ      │              │                     │
│                     │  • Transform     │              ▼                     │
│  ┌─────────────┐    │  • Deduplicate   │    ┌─────────────────────┐        │
│  │  DQ Rules   │───▶│                  │    │  Quarantine Table   │        │
│  │  (Delta)    │    └──────────────────┘    │  (Failed Records)   │        │
│  └─────────────┘                            └─────────────────────┘        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 📊 Tables Created

| Table Type | Tables | Description |
|------------|--------|-------------|
| **Silver Dimensions** | `silver_amenities`, `silver_destinations`, ... | Cleaned dimension data mirroring Bronze schema |
| **Silver Facts** | `silver_bookings`, `silver_payments`, ... | Transformed fact data with DQ expectations applied |
| **DQ Rules** | `dq_rules` | Centralized rule definitions (PK: `table_name, rule_name`) |
| **Quarantine** | `quarantine_*` | Records that failed `expect_all_or_drop` critical rules |
| **DQ Monitoring Views** | `dq_metrics_*`, `data_freshness_*` | Per-table quality metrics and freshness tracking |

---

### ✅ Data Quality Framework

| Quality Dimension | Example Rules |
|-------------------|---------------|
| **Completeness** | Required fields not null |
| **Validity** | Values within expected ranges |
| **Uniqueness** | No duplicates on key columns |
| **Consistency** | Cross-field validations |
| **Referential** | Foreign keys exist in parent tables |

---

### 🖼️ Visual Validation in Databricks

**1. DLT Pipeline - Data Quality Tab:**

Shows Expectations results with Pass/Warn/Fail counts for each rule.

**2. Unity Catalog - Silver Schema:**

All Silver tables visible with proper metadata and lineage.

**3. DQ Rules Table:**

```sql
SELECT rule_name, rule_type, expectation, action 
FROM {catalog}.{silver_schema}.dq_rules;
```

---

### ✅ Success Criteria Checklist

**Deployment:**
- [ ] Bundle validates with no errors
- [ ] Bundle deploys successfully
- [ ] DQ rules setup job runs and creates `dq_rules` table (**must run FIRST**)
- [ ] DLT pipeline runs without failures

**Data Quality:**
- [ ] DQ rules loaded into centralized Delta table
- [ ] Expectations show in pipeline event log (Data Quality tab)
- [ ] Quarantine table captures failed records (not silently dropped)

**Tables & Properties:**
- [ ] Silver tables populated with cleaned data
- [ ] Silver column names match Bronze (schema cloning)
- [ ] Row tracking enabled (`delta.enableRowTracking = true`)
- [ ] CDF enabled (`delta.enableChangeDataFeed = true`)
- [ ] `cluster_by_auto=True` on every table

**Pipeline Configuration:**
- [ ] `serverless: true` in pipeline YAML
- [ ] `photon: true` in pipeline YAML
- [ ] `edition: ADVANCED` in pipeline YAML
- [ ] `dq_rules_loader.py` has NO notebook header (pure Python)
- [ ] Incremental processing working (only new/changed rows)',
true, 1, true, current_timestamp(), current_timestamp(), current_user());

-- Step 12: Gold Layer Pipeline (YAML-Driven Implementation) - bypass_LLM = TRUE
INSERT INTO ${catalog}.${schema}.section_input_prompts 
(input_id, section_tag, input_template, system_prompt, section_title, section_description, order_number, how_to_apply, expected_output, bypass_llm, version, is_active, inserted_at, updated_at, created_by)
VALUES
(9, 'gold_layer_pipeline',
'Implement the Gold layer using @data_product_accelerator/skills/gold/01-gold-layer-setup/SKILL.md

Use the gold layer design YAML files as the target destination, and the silver layer tables as source.

Limit pipelines to only 5 tables for purposes of this exercise:
- dim_property
- dim_destination
- dim_user
- dim_host
- fact_booking_detail',
'Static prompt - no LLM processing required. This prompt is copied directly to the AI coding assistant.',
'Gold Layer Pipeline (YAML-Driven)',
'Build Gold layer by reading YAML schemas, creating tables with PK/FK constraints (NOT ENFORCED), and merging from Silver with deduplication',
12,
'## 📚 What is the Gold Layer Pipeline?

The Gold Layer Pipeline **implements** the Gold Layer Design by:
1. Reading YAML schema files (single source of truth)
2. Creating dimension and fact tables with proper constraints
3. Merging data incrementally from Silver layer

### Design vs Implementation

| Step | What Happens | Output |
|------|--------------|--------|
| **Step 9: Design** | Define schemas, ERDs, lineage | `gold_layer_design/` folder |
| **Step 12: Implementation** | Create tables, run merges | Populated Gold tables |

---

## 🎯 Core Philosophy: Extract, Don''t Generate

### Why This Matters

**ALWAYS prefer scripting techniques to extract names from existing source files over generating them from scratch.**

| Approach | Result |
|----------|--------|
| ❌ **Generate from scratch** | Hallucinations, typos, schema mismatches |
| ✅ **Extract from YAML** | 100% accuracy, consistency, no hallucinations |

### What "Extract" Means

```python
# ❌ WRONG: Hardcode table names (might be wrong!)
tables = ["dim_property", "dim_destination", "fact_booking"]

# ✅ CORRECT: Extract from YAML files
import yaml
from pathlib import Path

def get_gold_table_names():
    yaml_dir = Path("gold_layer_design/yaml")
    tables = []
    for yaml_file in yaml_dir.rglob("*.yaml"):
        with open(yaml_file) as f:
            config = yaml.safe_load(f)
            tables.append(config[''table_name''])
    return tables
```

**Benefits:**
- ✅ 100% accuracy (names come from actual schemas)
- ✅ No hallucinations (only existing entities referenced)
- ✅ Consistency across layers
- ✅ Immediate detection of schema changes

---

## 🏗️ Gold Layer Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      GOLD LAYER PIPELINE FLOW (2 Jobs)                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  INPUTS                          PROCESS                       OUTPUT      │
│                                                                             │
│  ┌─────────────────┐   ┌───────────────────────────────────────────────┐  │
│  │ Gold Layer      │   │ gold_setup_job                                │  │
│  │ Design YAML     │──▶│                                               │  │
│  │ (Schema Source) │   │  Task 1: setup_tables.py                     │  │
│  └─────────────────┘   │    • CREATE TABLE from YAML                  │  │
│                         │    • ALTER TABLE ADD PRIMARY KEY              │  │
│  ┌─────────────────┐   │         ↓ depends_on                         │  │
│  │ COLUMN_LINEAGE  │   │  Task 2: add_fk_constraints.py               │  │
│  │ .csv            │   │    • ALTER TABLE ADD FOREIGN KEY (NOT ENFORCED)│  │
│  └─────────────────┘   └───────────────────────────────────────────────┘  │
│                                          ↓                                 │
│  ┌─────────────────┐   ┌───────────────────────────────────────────────┐  │
│  │ Silver Layer    │   │ gold_merge_job                                │  │
│  │ Tables          │──▶│                                               │  │
│  │ (Data Source)   │   │  1. Deduplicate Silver (business_key)         │  │
│  └─────────────────┘   │  2. Map columns (YAML lineage / CSV)         │  │
│                         │  3. Merge dims first (SCD1/SCD2)             │  │
│                         │  4. Merge facts last (FK order)              │  │
│                         └───────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Workshop Scope: 5 Tables

For this exercise, we limit to **5 key tables**:

| Table | Type | Description |
|-------|------|-------------|
| `dim_property` | Dimension (SCD2) | Vacation rental property details |
| `dim_destination` | Dimension (SCD1) | Travel destinations/locations |
| `dim_user` | Dimension (SCD2) | Platform users (guests) |
| `dim_host` | Dimension (SCD2) | Property host profiles |
| `fact_booking_detail` | Fact | Individual booking transactions |

**Why 5 tables?**
- ✅ Demonstrates all patterns (SCD1, SCD2, Fact)
- ✅ Shows FK relationships (Fact → Dimensions)
- ✅ Completes in reasonable time for workshop
- ✅ Full pattern coverage without complexity overload

---

## Prerequisite

**Run this in your cloned Template Repository** (see Prerequisites in Step 0).

Ensure you have:
- ✅ Gold Layer Design completed (Step 9) with YAML files in `gold_layer_design/yaml/`
- ✅ Column lineage documentation in `gold_layer_design/COLUMN_LINEAGE.csv` (Silver→Gold column mappings)
- ✅ Silver Layer populated (Step 11) with data in Silver tables
- ✅ `data_product_accelerator/skills/gold/01-gold-layer-setup/SKILL.md` — The Gold implementation orchestrator (auto-loads 7 worker + 8 common skills)

---

## Steps to Apply

### Step 1: Start New Agent Thread

Open Cursor and start a **new Agent thread** for clean context.

### Step 2: Copy and Paste the Prompt

1. **Copy the prompt** using the copy button
2. **Paste it into Cursor**
3. The AI will read YAML files and generate implementation code

### Step 3: Review Generated Code

The AI will create:
- `setup_tables.py` — reads YAML → CREATE TABLE + PKs
- `add_fk_constraints.py` — reads YAML → ALTER TABLE ADD FK (NOT ENFORCED)
- `merge_gold_tables.py` — dedup Silver → map columns → MERGE (SCD1/SCD2/fact)
- `gold_setup_job.yml` — 2-task job (setup → FK via `depends_on`)
- `gold_merge_job.yml` — merge job (scheduled, PAUSED in dev)

### Step 4: Validate the Bundle

```bash
# Validate bundle configuration
databricks bundle validate -t dev

# Expected: No errors, all resources validated
```

### Step 5: Deploy the Bundle

```bash
# Deploy to Databricks workspace
databricks bundle deploy -t dev

# Expected: Jobs created successfully
```

### Step 6: Run the Gold Setup Job (Tables + PKs + FKs)

```bash
# Run Gold setup (creates tables, adds PKs, then adds FKs)
databricks bundle run -t dev gold_setup_job

# This job has TWO tasks:
#   Task 1: setup_tables (creates tables from YAML + adds PKs)
#   Task 2: add_fk_constraints (depends_on Task 1)
#
# FKs are added here (before data) because UC constraints are
# NOT ENFORCED — they''re informational only, no data validation needed.
```

### Step 7: Run the Gold Merge Job

```bash
# Run Gold merge (populates tables from Silver)
databricks bundle run -t dev gold_merge_job

# Merges dimensions FIRST (SCD1/SCD2), then facts (FK dependency order)
```

### Step 8: Verify in Databricks UI

After all jobs complete:

```sql
-- 1. List Gold tables
SHOW TABLES IN {catalog}.{gold_schema};

-- 2. Check Primary Key constraints
SELECT * FROM information_schema.table_constraints 
WHERE table_schema = ''{gold_schema}'' AND constraint_type = ''PRIMARY KEY'';

-- 3. Check Foreign Key constraints
SELECT * FROM information_schema.table_constraints 
WHERE table_schema = ''{gold_schema}'' AND constraint_type = ''FOREIGN KEY'';

-- 4. Verify row counts
SELECT ''dim_property'' as tbl, COUNT(*) as cnt FROM {catalog}.{gold_schema}.dim_property
UNION ALL SELECT ''dim_destination'', COUNT(*) FROM {catalog}.{gold_schema}.dim_destination
UNION ALL SELECT ''dim_user'', COUNT(*) FROM {catalog}.{gold_schema}.dim_user
UNION ALL SELECT ''dim_host'', COUNT(*) FROM {catalog}.{gold_schema}.dim_host
UNION ALL SELECT ''fact_booking_detail'', COUNT(*) FROM {catalog}.{gold_schema}.fact_booking_detail;

-- 5. Preview fact with dimension lookups
SELECT 
    f.booking_id,
    p.property_name,
    d.destination_name,
    u.first_name || '' '' || u.last_name as guest_name,
    f.total_amount
FROM {catalog}.{gold_schema}.fact_booking_detail f
JOIN {catalog}.{gold_schema}.dim_property p ON f.property_id = p.property_id AND p.is_current = true
JOIN {catalog}.{gold_schema}.dim_destination d ON f.destination_id = d.destination_id
JOIN {catalog}.{gold_schema}.dim_user u ON f.user_id = u.user_id AND u.is_current = true
LIMIT 5;
```

---

## 🔧 What Happens Behind the Scenes

When you paste the prompt, the AI reads `@data_product_accelerator/skills/gold/01-gold-layer-setup/SKILL.md` — the **Gold implementation orchestrator**. Behind the scenes:

1. **YAML-driven approach** — the orchestrator reads your `gold_layer_design/yaml/` files (from Step 9) as the **single source of truth**. Table names, columns, types, PKs, FKs are all extracted from YAML — never generated from scratch.
2. **Worker skills auto-loaded:**
   - `02-yaml-driven-gold-setup` — reads YAML schemas and generates CREATE TABLE DDL
   - `04-gold-layer-merge-patterns` — SCD Type 1/2 dimensions, fact table MERGE operations
   - `05-gold-delta-merge-deduplication` — prevents DELTA_MULTIPLE_SOURCE_ROW_MATCHING errors
   - `03-gold-layer-documentation` — dual-purpose COMMENTs for both business users and Genie
   - `06-fact-table-grain-validation` — validates grain before populating
   - `07-gold-layer-schema-validation` — validates schemas before deployment
3. **Common skills auto-loaded (8 total):**
   - `databricks-expert-agent` — core "Extract, Don''t Generate" principle applied to EVERY YAML read
   - `databricks-asset-bundles` — generates 2 jobs (setup+FK combined, merge separate), `notebook_task` + `base_parameters`
   - `databricks-table-properties` — Gold TBLPROPERTIES (CDF, row tracking, auto-optimize, `layer=gold`)
   - `unity-catalog-constraints` — surrogate keys as PKs (NOT NULL), FK via ALTER TABLE (NOT ENFORCED)
   - `schema-management-patterns` — `CREATE SCHEMA IF NOT EXISTS` with governance metadata
   - `databricks-python-imports` — pure Python modules for shared config (avoids `sys.path` issues)
   - `naming-tagging-standards` — enterprise naming and dual-purpose COMMENTs
   - `databricks-autonomous-operations` — self-healing deploy loop if jobs fail

**Key principle: "Extract, Don''t Generate"** — every table name, column name, and type comes from YAML. The AI never hallucinates schema elements.

### 🏅 Databricks Best Practices Applied

| Practice | How It''s Used Here |
|----------|-------------------|
| **Surrogate Keys as PRIMARY KEYs** | Dimensions use surrogate BIGINT keys (not business keys) as PKs — informational constraints in Unity Catalog for BI tool discovery |
| **FOREIGN KEY Constraints** | Fact tables declare FK relationships to dimensions — enables Genie, Power BI, and Tableau to auto-discover joins |
| **SCD Type 1 (Overwrite)** | Reference dimensions like `dim_destination` use SCD1 — MERGE replaces old values with current values |
| **SCD Type 2 (Versioned History)** | Tracking dimensions like `dim_property`, `dim_host` use SCD2 — `is_current`, `valid_from`, `valid_to` columns preserve history |
| **Delta MERGE with Deduplication** | Pre-deduplicates source rows before MERGE to prevent `DELTA_MULTIPLE_SOURCE_ROW_MATCHING_TARGET_ROW_IN_MERGE` errors. Dedup key = `business_key` from YAML. |
| **2-Job Architecture** | `gold_setup_job` (2 tasks: create tables + add FKs) → `gold_merge_job` (populate data). FKs applied before data because constraints are NOT ENFORCED. |
| **NOT ENFORCED Constraints** | UC PK/FK are informational — they help BI tools discover relationships and improve query planning, but don''t reject invalid data |
| **Dual-Purpose COMMENTs** | Every table and column has a COMMENT serving both business users ("Property name for display") and technical users/Genie ("FK to dim_property.property_sk") |
| **Row Tracking** | `delta.enableRowTracking = true` on every Gold table — required for downstream Materialized View incremental refresh |
| **CLUSTER BY AUTO** | Gold tables use automatic liquid clustering — Databricks chooses optimal columns based on actual query patterns |
| **Predictive Optimization Ready** | Gold tables are structured for Databricks Predictive Optimization — auto-OPTIMIZE, auto-VACUUM, auto-ANALYZE |
| **YAML as Single Source of Truth** | Table schemas live in version-controlled YAML files, not in scattered SQL scripts — enables schema diff reviews in PRs |
| **PyYAML + YAML Sync** | `pyyaml>=6.0` in job environment; YAML files synced in `databricks.yml` — without sync, `setup_tables.py` can''t find schemas in workspace |
| **Variable Shadowing Prevention** | Never name variables `count`, `sum`, `min`, `max` — shadows PySpark functions. Use `spark_sum = F.sum`, `record_count = df.count()` |
| **Column Mapping from Lineage** | Silver→Gold column renames extracted from YAML `lineage.source_column` or `COLUMN_LINEAGE.csv` — never guessed or assumed |

---

## 🔑 Constraint Application Order

**Constraints and data are applied in this order:**

```
┌────────────────────────────────────────────────────────────┐
│  gold_setup_job (2 tasks)                                  │
│                                                            │
│  Task 1: setup_tables.py                                   │
│    • CREATE OR REPLACE TABLE ... (from YAML)               │
│    • ALTER TABLE ... ADD CONSTRAINT pk_ PRIMARY KEY        │
│           ↓ (depends_on)                                   │
│  Task 2: add_fk_constraints.py                             │
│    • ALTER TABLE ... ADD CONSTRAINT fk_ FOREIGN KEY        │
│    • FK references PK → PK must exist first                │
│                                                            │
└────────────────────────────────────────────────────────────┘
                        ↓
┌────────────────────────────────────────────────────────────┐
│  gold_merge_job                                            │
│    • Merge dimensions first (SCD1/SCD2)                    │
│    • Merge facts last (FK dependency order)                │
└────────────────────────────────────────────────────────────┘
```

### ⚠️ Why FKs BEFORE Data?

Unity Catalog constraints are **NOT ENFORCED** — they are **informational only**:
- They do NOT reject invalid data on INSERT/MERGE
- They DO tell BI tools (Genie, Power BI, Tableau) how tables relate
- They DO improve query optimizer join planning
- Data does NOT need to exist for constraints to be applied

This is a key Databricks concept: PK/FK in Unity Catalog are for **metadata enrichment and BI tool discovery**, not data integrity enforcement.',
'## Expected Deliverables

### 📁 Generated Asset Bundle Structure

```
project_root/
├── databricks.yml                          # Bundle config (MUST sync YAML files!)
├── src/
│   └── wanderbricks_gold/
│       ├── setup_tables.py                 # Creates Gold tables from YAML + adds PKs
│       ├── add_fk_constraints.py           # Adds FK constraints (separate script)
│       └── merge_gold_tables.py            # Merges Silver → Gold (dedup + map + merge)
├── resources/
│   └── gold/
│       ├── gold_setup_job.yml              # 2 tasks: setup_tables → add_fk_constraints
│       └── gold_merge_job.yml              # Merge job (scheduled, PAUSED in dev)
└── gold_layer_design/                      # Source of truth (from Step 9 design)
    ├── COLUMN_LINEAGE.csv                  # Silver→Gold column mappings
    └── yaml/
        ├── property/
        │   ├── dim_property.yaml
        │   └── dim_destination.yaml
        ├── user/
        │   ├── dim_user.yaml
        │   └── dim_host.yaml
        └── booking/
            └── fact_booking_detail.yaml
```

> **Critical:** `databricks.yml` must include a sync rule for `gold_layer_design/yaml/**/*.yaml` — without it, the scripts can''t find YAML schemas in the workspace. The environment must also include `pyyaml>=6.0`.

---

### 🔄 What Each Script Does

#### `setup_tables.py` - Table Creation

```python
# Reads YAML → Generates DDL → Creates Tables
for yaml_file in gold_yaml_files:
    config = yaml.safe_load(yaml_file)
    
    # Extract schema from YAML (don''t hardcode!)
    table_name = config[''table_name'']
    columns = config[''columns'']
    primary_key = config[''primary_key'']
    
    # Generate and execute DDL
    ddl = generate_create_table(table_name, columns, primary_key)
    spark.sql(ddl)
```

#### `merge_gold_tables.py` - Data Population

```python
# For each table: Deduplicate → Map Columns → Validate → Merge
for table_name, meta in inventory.items():
    silver_df = spark.table(f"{catalog}.{silver_schema}.{meta[''source_table'']}")
    
    # 1. ALWAYS deduplicate Silver before MERGE (mandatory!)
    deduped_df = silver_df.orderBy(col("processed_timestamp").desc()) \
                          .dropDuplicates(meta["business_key"])
    
    # 2. Map columns (Silver names → Gold names from COLUMN_LINEAGE.csv)
    for gold_col, silver_col in meta["column_mappings"].items():
        deduped_df = deduped_df.withColumn(gold_col, col(silver_col))
    
    # 3. Merge (SCD1 or SCD2 based on YAML scd_type)
    merge_condition = build_merge_condition(meta["pk_columns"])
    merge_into_gold(deduped_df, table_name, merge_condition, meta)

# Note: uses spark_sum = F.sum (never shadow Python builtins)
```

#### `add_fk_constraints.py` - Foreign Keys

```python
# Reads FK definitions from YAML → Adds constraints
for yaml_file in gold_yaml_files:
    config = yaml.safe_load(yaml_file)
    
    for fk in config.get(''foreign_keys'', []):
        # Add FK constraint (NOT ENFORCED for performance)
        spark.sql(f"""
            ALTER TABLE {table_name}
            ADD CONSTRAINT fk_{table}_{ref_table}
            FOREIGN KEY ({fk_columns})
            REFERENCES {ref_table}({ref_columns})
            NOT ENFORCED
        """)
```

---

### 📊 Tables Created with Constraints

| Table | Type | Primary Key | Foreign Keys |
|-------|------|-------------|--------------|
| `dim_property` | Dimension (SCD2) | `property_key` | None |
| `dim_destination` | Dimension (SCD1) | `destination_id` | None |
| `dim_user` | Dimension (SCD2) | `user_key` | None |
| `dim_host` | Dimension (SCD2) | `host_key` | None |
| `fact_booking_detail` | Fact | `booking_id` | → dim_property, dim_destination, dim_user, dim_host |

---

### 🔀 Merge Strategies by Table Type

| Table Type | Merge Strategy | What Happens |
|------------|----------------|--------------|
| **Dimension (SCD1)** | Overwrite | Old values replaced with new |
| **Dimension (SCD2)** | Track History | Old record marked `is_current=false`, new record inserted |
| **Fact** | Upsert | INSERT new, UPDATE existing on PK match |

---

### ✅ Verification Queries

After all jobs complete:

```sql
-- 1. Verify table creation
SHOW TABLES IN {catalog}.{gold_schema};

-- 2. Verify Primary Key constraints
SHOW CONSTRAINTS ON {catalog}.{gold_schema}.dim_property;

-- 3. Verify Foreign Key constraints
SHOW CONSTRAINTS ON {catalog}.{gold_schema}.fact_booking_detail;

-- 4. Verify SCD2 history (multiple versions for same entity)
SELECT property_id, is_current, effective_from, effective_to
FROM {catalog}.{gold_schema}.dim_property
WHERE property_id = 123
ORDER BY effective_from;

-- 5. Verify non-negotiable table properties
SHOW TBLPROPERTIES {catalog}.{gold_schema}.dim_property;
-- Look for: delta.enableChangeDataFeed=true, delta.enableRowTracking=true,
--           delta.autoOptimize.autoCompact=true, layer=gold

-- 6. Verify SCD2: exactly one is_current=true per business key
SELECT property_id, COUNT(*) as current_versions
FROM {catalog}.{gold_schema}.dim_property
WHERE is_current = true
GROUP BY property_id
HAVING COUNT(*) > 1;
-- Expected: ZERO rows (any results = SCD2 bug)

-- 7. Verify fact-dimension joins work (no orphan records)
SELECT 
    f.booking_id,
    p.property_name,
    h.host_name,
    f.total_amount
FROM {catalog}.{gold_schema}.fact_booking_detail f
JOIN {catalog}.{gold_schema}.dim_property p 
    ON f.property_id = p.property_id AND p.is_current = true
JOIN {catalog}.{gold_schema}.dim_host h 
    ON f.host_id = h.host_id AND h.is_current = true
LIMIT 10;
```

---

### ✅ Success Criteria Checklist

**Bundle Deployment:**
- [ ] `databricks bundle validate -t dev` passes (no errors)
- [ ] `databricks bundle deploy -t dev` completes
- [ ] 2 jobs appear in Workflows UI (`gold_setup_job`, `gold_merge_job`)
- [ ] YAML files synced to workspace (verify `gold_layer_design/yaml/` exists)
- [ ] PyYAML dependency present in job environment (`pyyaml>=6.0`)

**Gold Setup Job (2 tasks):**
- [ ] Task 1: All 5 tables created from YAML (no hardcoded DDL)
- [ ] Primary keys added to dimension tables (via `ALTER TABLE`)
- [ ] Task 2: Foreign key constraints added (runs after Task 1 via `depends_on`)
- [ ] Constraints visible in `information_schema.table_constraints`

**Table Properties (non-negotiable):**
- [ ] `CLUSTER BY AUTO` on every table (never specific columns)
- [ ] `delta.enableChangeDataFeed = true` (required for incremental propagation)
- [ ] `delta.enableRowTracking = true` (required for downstream MV refresh)
- [ ] `delta.autoOptimize.autoCompact = true`
- [ ] `delta.autoOptimize.optimizeWrite = true`
- [ ] `layer = gold` in TBLPROPERTIES

**Gold Merge Job:**
- [ ] Dimensions merged BEFORE facts (FK dependency order)
- [ ] Every MERGE deduplicates Silver first (key from YAML `business_key`)
- [ ] Column mappings extracted from YAML/`COLUMN_LINEAGE.csv` (not hardcoded)
- [ ] No variable names shadow PySpark functions (`count`, `sum`, etc.)
- [ ] Row counts match expectations
- [ ] SCD2 dimensions: exactly one `is_current = true` per business key
- [ ] Fact-to-dimension joins resolve correctly (no orphan records)

**Job Configuration:**
- [ ] Jobs use `notebook_task` (never `python_task`)
- [ ] Parameters use `base_parameters` dict (never CLI-style `parameters`)
- [ ] Serverless: `environments` block with `environment_version: "4"`
- [ ] Tags applied: `environment`, `layer=gold`, `job_type`',
true, 1, true, current_timestamp(), current_timestamp(), current_user());

-- Step 13: Create Use-Case Plan (Operationalization Planning) - bypass_LLM = TRUE
INSERT INTO ${catalog}.${schema}.section_input_prompts 
(input_id, section_tag, input_template, system_prompt, section_title, section_description, order_number, how_to_apply, expected_output, bypass_llm, version, is_active, inserted_at, updated_at, created_by)
VALUES
(10, 'usecase_plan',
'Perform project planning using @data_product_accelerator/skills/planning/00-project-planning/SKILL.md with planning_mode: workshop

If a PRD exists at @data_product_accelerator/docs/ui_design.md, reference it for business requirements, user personas, and workflows.',
'Static prompt - no LLM processing required. This prompt is copied directly to the AI coding assistant.',
'Create Use-Case Plan',
'Generate implementation plans for operationalizing use cases with supporting artifacts',
13,
'## 📚 What is Use-Case Planning?

After building the Gold layer (data foundation), we now plan how to **operationalize** that data through various artifacts that serve different use cases.

### From Data to Value

| Layer | What You Have | What''s Next |
|-------|---------------|--------------|
| **Bronze** | Raw data | ✅ Complete |
| **Silver** | Clean data | ✅ Complete |
| **Gold** | Business-ready data | ✅ Complete |
| **Artifacts** | Operational use cases | 👉 **THIS STEP** |

---

## 🎯 Why Plan Before Building?

**The Goal:** Identify use cases FIRST, then create artifacts to realize them.

| Approach | Result |
|----------|--------|
| ❌ Build random artifacts | Unused dashboards, irrelevant metrics |
| ✅ Plan use cases first | Every artifact serves a business need |

### PRD-Driven Planning

If a **Product Requirements Document (PRD)** exists at `docs/ui_design.md`, it provides:

| PRD Element | How It Informs Planning |
|-------------|-------------------------|
| **User Personas** | Who needs what data? |
| **Workflows** | What questions do users ask? |
| **Business Requirements** | What metrics matter most? |
| **Success Criteria** | How do we measure value? |

**PRD → Use Cases → Artifacts**

---

## 🏗️ Agent Layer Architecture (How Artifacts Connect)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   FROM GOLD LAYER TO USE CASES                               │
│                   (Agent Layer Architecture)                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  USERS (Natural Language)                                                   │
│       ↓                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ PHASE 3: Frontend App (Databricks App / Custom UI)                  │    │
│  └──────────────────────────────┬──────────────────────────────────────┘    │
│                                 ↓                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ PHASE 2: AI Agents (orchestrator → domain agents)                   │    │
│  │          Agents query through Genie Spaces — NEVER direct SQL       │    │
│  └──────────────────────────────┬──────────────────────────────────────┘    │
│                                 ↓                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ PHASE 1.6: Genie Spaces (NL-to-SQL interface, ≤ 25 assets each)    │    │
│  └──────────────────────────────┬──────────────────────────────────────┘    │
│                                 ↓                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ PHASE 1 DATA ASSETS (consumed by Genie & Dashboards):               │    │
│  │  1.3 Metric Views │ 1.2 TVFs │ 1.1 ML Tables │ 1.4 Monitors       │    │
│  └──────────────────────────────┬──────────────────────────────────────┘    │
│                                 ↓                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ GOLD LAYER (Foundation — completed in prior steps)                  │    │
│  │  dim_property │ dim_destination │ dim_user │ dim_host │ fact_booking │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

> **Key principle:** Each layer consumes the layer below it. Agents never bypass Genie Spaces to query Gold directly. This provides abstraction, query optimization, and built-in guardrails.

---

## 📋 Phase 1 Addendums (Artifact Categories)

All analytics artifacts are organized as Phase 1 addendums:

| # | Addendum | Artifacts | Downstream Manifest |
|---|----------|-----------|---------------------|
| 1.1 | **ML Models** | Prediction models, feature tables | `ml-manifest.yaml` |
| 1.2 | **TVFs** | Parameterized SQL functions for Genie | `semantic-layer-manifest.yaml` |
| 1.3 | **Metric Views** | Semantic measures & dimensions | `semantic-layer-manifest.yaml` |
| 1.4 | **Lakehouse Monitoring** | Data quality monitors, custom metrics | `observability-manifest.yaml` |
| 1.5 | **AI/BI Dashboards** | Lakeview visualizations | `observability-manifest.yaml` |
| 1.6 | **Genie Spaces** | NL query interfaces (≤ 25 assets each) | `semantic-layer-manifest.yaml` |
| 1.7 | **Alerting Framework** | SQL Alerts with severity routing | `observability-manifest.yaml` |

> **Workshop default:** 1.2 TVFs, 1.3 Metric Views, and 1.6 Genie Spaces are included by default. Others included if requested.

---

## 🔄 Planning Methodology

The planning skill organizes work into **3 phases**, with Phase 1 containing **7 addendums** for all analytics artifacts:

### Phase & Addendum Structure

```
Phase 1: Use Cases (ALL analytics artifacts)
├── 1.1 ML Models           (demand predictors, pricing optimizers)
├── 1.2 TVFs                (parameterized queries for Genie)
├── 1.3 Metric Views        (semantic measures & dimensions)
├── 1.4 Lakehouse Monitoring (data quality monitors)
├── 1.5 AI/BI Dashboards    (Lakeview visualizations)
├── 1.6 Genie Spaces        (natural language query interfaces)
└── 1.7 Alerting Framework   (SQL alerts with severity routing)

Phase 2: Agent Framework (AI Agents with Genie integration)
└── Agents use Genie Spaces as query interface (never direct SQL)

Phase 3: Frontend App (User interface — optional)
└── Databricks Apps or custom UI consuming Phase 1-2 artifacts
```

> **Key insight:** ALL data artifacts (TVFs, Metric Views, Dashboards, Monitors, Alerts, ML, Genie Spaces) are addendums within Phase 1. Agents (Phase 2) and Frontend (Phase 3) **consume** Phase 1 artifacts — they are not separate artifact categories.

### Agent Domain Framework

**Domains emerge from business questions, not fixed categories.** The skill derives domains from your Gold table groupings and stakeholder questions:

| Rule | Why |
|------|-----|
| Domains come from Gold table relationships | Natural boundaries, not arbitrary labels |
| A domain needs ≥ 3 business questions | Fewer = merge into a neighbor domain |
| Two domains sharing > 70% of Gold tables → consolidate | Avoid duplicate artifacts |
| Don''t force a fixed count (2-3 for 5-10 tables is fine) | More domains ≠ better |

**Example for Wanderbricks (hospitality):**

| Domain | Focus Area | Key Gold Tables |
|--------|------------|----------------|
| 💰 **Revenue** | Bookings, pricing, revenue trends | `fact_booking_detail`, `dim_property` |
| 🏠 **Host Performance** | Host activity, ratings, response times | `dim_host`, `fact_review` |
| 👤 **Guest Experience** | Guest behavior, satisfaction, lifetime value | `dim_user`, `fact_booking_detail` |

> **Anti-pattern:** Creating 5+ generic domains (Cost, Performance, Quality, Reliability, Security) that don''t map to your actual Gold tables.

---

## Prerequisite

**Run this in your cloned Template Repository** (see Prerequisites in Step 0).

Ensure you have:
- ✅ Gold Layer Design completed (Step 9)
- ✅ Gold Layer Implementation completed (Step 12)
- ✅ `data_product_accelerator/skills/planning/00-project-planning/SKILL.md` - The project planning skill
- ✅ `docs/ui_design.md` - PRD with business requirements (optional, if available)

---

## Steps to Apply

### Step 1: Start New Agent Thread

Open Cursor and start a **new Agent thread** for clean context.

### Step 2: Copy and Paste the Prompt

1. **Copy the prompt** using the copy button
2. **Paste it into Cursor**
3. The AI will analyze your Gold layer and create use case plans

### Step 3: Review Generated Plans

The AI will create plans in `plans/` folder:
- Phase-specific addendums
- Artifact specifications
- Implementation priorities

### Step 4: Prioritize Use Cases

Review the generated plans and:
- Identify highest-value use cases
- Assign priorities (P0, P1, P2)
- Determine implementation order

### Step 5: Prepare for Implementation

Use the plans to guide subsequent steps:
- Step 14+: Implement artifacts based on plans

---

## 🔧 What Happens Behind the Scenes

When you paste the prompt, the AI reads `@data_product_accelerator/skills/planning/00-project-planning/SKILL.md` — the **Project Planning orchestrator**. Behind the scenes:

1. **Workshop mode detection** — `planning_mode: workshop` activates the workshop profile, which produces a **minimal representative plan** (3-5 TVFs, 1-2 Metric Views, 1 Genie Space) designed for hands-on workshops. The first line of output confirms: `**Planning Mode:** Workshop (explicit opt-in — artifact caps active)`.
2. **Interactive quick start** — the skill asks key decisions before generating plans:
   - Which domains to include (derived from business questions and Gold table groupings)
   - Which Phase 1 addendums to generate (1.1 ML through 1.7 Alerting)
   - Whether to include Phase 2 (Agents) and Phase 3 (Frontend)
   - Agent-to-Genie Space mapping strategy
3. **Artifact Rationalization** — the skill applies rigorous rules to prevent artifact bloat:
   - Every artifact must trace to a business question (no quota-filling)
   - TVFs only where Metric Views can''t answer the question
   - Genie Spaces sized by total asset count (25-asset hard limit per space)
   - Domains consolidated when overlap exceeds 70% of Gold tables
4. **YAML manifest contracts** — 4 machine-readable manifests generated for downstream stages:
   - `semantic-layer-manifest.yaml` (TVFs + Metric Views + Genie Spaces)
   - `observability-manifest.yaml` (Monitors + Dashboards + Alerts)
   - `ml-manifest.yaml` and `genai-agents-manifest.yaml`
5. **Common skills auto-loaded:**
   - `databricks-expert-agent` — "Extract, Don''t Generate" applied to plan-to-implementation handoff
   - `naming-tagging-standards` — enterprise naming conventions for all planned artifacts

**Key concept: Agent Layer Architecture** — Agents (Phase 2) use Genie Spaces (Phase 1.6) as their query interface, NOT direct SQL. This means Genie Spaces must be deployed before agents can consume them.

### 🏅 Databricks Best Practices Applied

| Practice | How It''s Used Here |
|----------|-------------------|
| **Agent Domain Framework** | Domains derived from business questions and Gold table groupings (not forced to a fixed count). Each domain maps to a potential Genie Space. |
| **Artifact Rationalization** | Every artifact must trace to a business question. TVFs only when Metric Views can''t answer. No quota-filling. Prevents artifact bloat. |
| **Genie Space 25-Asset Limit** | Hard constraint: each Genie Space holds ≤ 25 data assets. Plan calculates total assets → determines space count. Under 10 assets = merge. |
| **Deployment Order Discipline** | Build order enforced: Phase 1 addendums (1.2→1.3→1.6→1.5→1.4→1.7→1.1) → Phase 2 (Agents). Genie Spaces MUST exist before Agents can use them. |
| **Agent Layer Architecture** | AI Agents (Phase 2) query data through Genie Spaces (Phase 1.6), never direct SQL. Provides abstraction, optimization, and guardrails. |
| **Serverless-First Architecture** | Every artifact designed for serverless execution — SQL warehouses for queries, serverless jobs for ETL, serverless DLT for pipelines |
| **Lakehouse Monitoring Integration** | Plans include monitor specifications leveraging Databricks Lakehouse Monitoring with custom business metrics (AGGREGATE, DERIVED, DRIFT) |
| **AI/BI Dashboard Planning** | Dashboard specs designed for Databricks AI/BI (Lakeview) — native format with widget-query alignment and parameter configuration |
| **Genie Space Optimization Targets** | Plans include benchmark questions with accuracy targets (95%+) and repeatability targets (90%+). General Instructions ≤ 20 lines. |
| **YAML Manifests as Contracts** | 4 machine-readable manifests bridge planning and implementation. Downstream skills parse manifests (not prose). `planning_mode: workshop` prevents expansion. |
| **Workshop Mode Hard Caps** | When `planning_mode: workshop` is active, artifact counts are capped (3-5 TVFs, 1-2 MVs, 1 Genie Space). Manifests propagate this ceiling to all downstream skills. |

---

## 💡 Use Case Examples for Vacation Rentals

Based on the Wanderbricks Gold layer, typical use cases include:

### Revenue Analytics
- "What is our total booking revenue by destination?"
- "Which properties have the highest average nightly rate?"
- "Revenue trend over the past 12 months?"

### Host Performance
- "Who are our top-performing hosts?"
- "Which hosts have the best guest ratings?"
- "Host response time analysis?"

### Guest Insights
- "Customer lifetime value by segment?"
- "Repeat booking rate analysis?"
- "Guest demographics by destination?"

### Property Optimization
- "Property occupancy rates by season?"
- "Which amenities correlate with higher bookings?"
- "Pricing optimization recommendations?"

### Operational Monitoring
- "Data freshness alerts?"
- "Booking anomaly detection?"
- "Revenue target tracking?"',
'## Expected Deliverables

### 📁 Generated Plan Files

```
plans/
├── README.md                               # Plan index and navigation
├── prerequisites.md                        # Bronze/Silver/Gold summary
├── phase1-use-cases.md                     # Phase 1 master (all analytics artifacts)
│   ├── phase1-addendum-1.1-ml-models.md        # ML model specifications
│   ├── phase1-addendum-1.2-tvfs.md             # TVF definitions
│   ├── phase1-addendum-1.3-metric-views.md     # Metric view specifications
│   ├── phase1-addendum-1.4-lakehouse-monitoring.md  # Monitor configurations
│   ├── phase1-addendum-1.5-aibi-dashboards.md  # Dashboard specifications
│   ├── phase1-addendum-1.6-genie-spaces.md     # Genie Space setups
│   └── phase1-addendum-1.7-alerting.md         # Alert configurations
├── phase2-agent-framework.md               # AI agent specifications (optional)
├── phase3-frontend-app.md                  # App integration plans (optional)
└── manifests/                              # ⭐ Machine-readable contracts
    ├── semantic-layer-manifest.yaml        # TVFs + Metric Views + Genie Spaces
    ├── observability-manifest.yaml         # Monitors + Dashboards + Alerts
    ├── ml-manifest.yaml                    # Feature Tables + Models + Experiments
    └── genai-agents-manifest.yaml          # Agents + Tools + Eval Datasets
```

> **Key innovation: Plan-as-Contract.** The 4 YAML manifests serve as **contracts** between planning and implementation. When downstream skills (semantic layer, monitoring, ML, GenAI) run, they read their manifest to know exactly what to build — enforcing "Extract, Don''t Generate" across the planning-to-implementation handoff. In workshop mode, manifests include `planning_mode: workshop` to prevent downstream skills from expanding beyond listed artifacts.

---

### 📊 Plan Document Structure

Each plan document includes:

```markdown
# Artifact Category Plan

## Overview
- Business objectives
- Target users
- Success metrics

## Artifact Specifications

### Artifact 1: [Name]
- **Agent Domain:** [Derived from your business questions]
- **Description:** [What it does]
- **Source Gold Tables:** [Gold tables used]
- **Business Questions Answered:** [Which stakeholder questions does this serve?]
- **Implementation Priority:** [P0/P1/P2]

### Artifact 2: [Name]
...

## Implementation Timeline
- Sprint assignments
- Dependencies
- Milestones

## Validation Criteria
- How to verify success
- Expected outcomes
```

---

### 🎯 Workshop Mode Artifact Caps

This workshop uses `planning_mode: workshop` — hard caps prevent artifact bloat:

| Category | Workshop Cap | Selection Criteria | Acceleration (default) |
|----------|-------------|-------------------|----------------------|
| **Domains** | 1-2 max | Richest Gold table relationships | Derived from business questions |
| **TVFs** | 3-5 total | One per parameter pattern (date-range, entity-filter, top-N) | ~1-2 per Gold table |
| **Metric Views** | 1-2 total | One per fact table (pick richest joins) | One per distinct grain |
| **Genie Spaces** | 1 unified | All workshop assets in one space (< 15 assets) | Based on 25-asset limit |
| **Dashboards** | 0-1 | Optional if time permits | 5-8 |
| **Monitors** | 1-2 | One fact + one dimension | 10-15 |
| **Alerts** | 2-3 | One CRITICAL + one WARNING (severity demo) | 10-15 |
| **ML Models** | 0-1 | Skip unless explicitly requested | 5-7 |
| **Phase 2 (Agents)** | Skip | Excluded by default in workshop | Full agent framework |
| **Phase 3 (Frontend)** | Skip | Excluded by default in workshop | Databricks App |

> **Selection principle:** Pick the **most representative** artifact for each pattern type. Prefer **variety of patterns** (date-range TVF, entity-filter TVF, top-N TVF) over depth in a single domain. The goal is to teach the full pattern vocabulary with minimum artifacts.

---

### 🔀 Deployment Order (Critical!)

**Phase 1 addendums must be deployed in this order:**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                  PHASE 1 DEPLOYMENT ORDER                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1.2 TVFs ──────────▶ 1.3 Metric Views ──────────▶ 1.6 Genie Spaces       │
│  (parameterized         (semantic measures           (NL-to-SQL using       │
│   queries)               & dimensions)                TVFs + MVs + tables)  │
│                                                            │                │
│  1.4 Monitors ──────▶ 1.7 Alerts                          │                │
│  (data quality          (threshold/anomaly                 │                │
│   profiling)             notifications)                    │                │
│                                                            │                │
│  1.5 Dashboards                                            │                │
│  (visualizes Metric Views + TVFs + Monitors)               │                │
│                                                            │                │
│  1.1 ML Models                                             │                │
│  (predictions feed into Genie Spaces as tables)            │                │
│                                                            ▼                │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ PHASE 2: AI Agents (consume Genie Spaces — deploy AFTER Phase 1.6) │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                          ↓                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ PHASE 3: Frontend App (consumes Agents + Dashboards — optional)     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

> **Why order matters:** Genie Spaces need TVFs and Metric Views to exist before they can be added as assets. Agents need Genie Spaces to exist before they can query through them. Violating this order causes deployment failures.

---

### ✅ Success Criteria Checklist

**Plan Structure:**
- [ ] First line confirms mode: `**Planning Mode:** Workshop (explicit opt-in)`
- [ ] `plans/README.md` provides navigation with links to all documents
- [ ] Phase 1 master + selected addendums (1.2 TVFs, 1.3 MVs, 1.6 Genie included by default in workshop)
- [ ] Each plan document follows standard template (Overview, Specs, Timeline, Validation)

**Agent Domain Framework:**
- [ ] Domains derived from business questions and Gold table groupings
- [ ] Each domain has ≥ 3 business questions (or merged)
- [ ] No two domains share > 70% of Gold tables (or consolidated)
- [ ] Domain count justified (2-3 for 5-10 Gold tables)

**Artifact Rationalization (Prevent Bloat):**
- [ ] Every artifact traces to a business question
- [ ] No TVF duplicates what a Metric View already provides
- [ ] Each Genie Space has ≤ 25 data assets and ≥ 10 assets
- [ ] Genie Space count based on total asset volume (not domain count)
- [ ] Workshop caps respected: 3-5 TVFs, 1-2 MVs, 1 Genie Space

**YAML Manifests (Plan-as-Contract):**
- [ ] 4 manifests generated in `plans/manifests/`
- [ ] `planning_mode: workshop` present in all manifests
- [ ] All table/column references validated against Gold YAML
- [ ] Artifact counts in manifests match plan addendum counts

**Deployment Order:**
- [ ] Phase 1 addendum dependencies documented
- [ ] Genie Spaces listed as deployed AFTER TVFs + Metric Views
- [ ] Agents (Phase 2) listed as deployed AFTER Genie Spaces (if included)

**Use Case Coverage:**
- [ ] Key business questions documented per domain (≥ 3 each)
- [ ] All artifacts tagged with Agent Domain
- [ ] LLM-friendly comments specified for all artifacts
- [ ] Source Gold tables identified for each artifact',
true, 1, true, current_timestamp(), current_timestamp(), current_user());

-- Step 14: Build Genie Space [Metric Views/TVFs] - bypass_LLM = TRUE
INSERT INTO ${catalog}.${schema}.section_input_prompts 
(input_id, section_tag, input_template, system_prompt, section_title, section_description, order_number, how_to_apply, expected_output, bypass_llm, version, is_active, inserted_at, updated_at, created_by)
VALUES
(11, 'genie_space',
'Set up the semantic layer using @data_product_accelerator/skills/semantic-layer/00-semantic-layer-setup/SKILL.md

Implement in this order:

1. **Table-Valued Functions (TVFs)** — using plan at @data_product_accelerator/plans/phase1-addendum-1.2-tvfs.md
2. **Metric Views** — using plan at @data_product_accelerator/plans/phase1-addendum-1.3-metric-views.md
3. **Genie Space** — using plan at @data_product_accelerator/plans/phase1-addendum-1.6-genie-spaces.md
4. **Genie JSON Exports** — create export/import deployment jobs

The orchestrator skill automatically loads worker skills for TVFs, Metric Views, Genie Space patterns, and export/import API.',
'Static prompt - no LLM processing required. This prompt is copied directly to the AI coding assistant.',
'Build Genie Space [Metric Views/TVFs]',
'Create semantic layer with TVFs, Metric Views, and Genie Space for natural language analytics',
14,
'## 📚 What is the Semantic Layer?

The **Semantic Layer** sits between your Gold data and end users, providing:
- **Natural language** access to data
- **Standardized metrics** with business definitions
- **Reusable query patterns** via functions

### Semantic Layer Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          SEMANTIC LAYER STACK                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                   GENIE SPACE (Phase 3)                              │   │
│  │              Natural Language Interface                              │   │
│  │   "What is our total revenue this month by destination?"            │   │
│  │   Serverless SQL Warehouse │ ≤20-line Instructions │ ≥10 Benchmarks │   │
│  └──────────────────────────────┬──────────────────────────────────────┘   │
│                                 │ Data Asset Priority:                      │
│                    ┌────────────┴────────────┐                             │
│                    │ 1st choice   2nd choice │                             │
│                    ▼                         ▼                             │
│  ┌─────────────────────────┐   ┌─────────────────────────┐                │
│  │  METRIC VIEWS (Phase 1) │   │    TVFs (Phase 2)       │                │
│  │  WITH METRICS YAML      │   │  STRING date params     │                │
│  │                         │   │                         │                │
│  │  • Dimensions + Synonyms│   │  • get_revenue_by_period│                │
│  │  • Measures + Formats   │   │  • get_top_properties   │                │
│  │  • Joins (snowflake)    │   │  • get_host_performance │                │
│  │  • v1.1 specification   │   │  • v3.0 bullet comments │                │
│  └────────────┬────────────┘   └────────────┬────────────┘                │
│               │                             │                              │
│               └──────────────┬──────────────┘                              │
│                              │ 3rd choice (raw tables)                     │
│                              ▼                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    GOLD LAYER (prerequisite)                         │   │
│  │   dim_property │ dim_host │ dim_user │ fact_booking_detail │ ...    │   │
│  │   All tables must have column COMMENTs before Genie Space creation  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    OPTIMIZATION (Phase 5)                            │   │
│  │   Benchmark → Test → Apply 6 Levers → Re-test                      │   │
│  │   Target: Accuracy ≥ 95%  │  Repeatability ≥ 90%                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Why This Order Matters

| Phase | Artifact | Depends On | Enables | Non-Negotiable Rule |
|-------|----------|------------|---------|---------------------|
| 0 | **Read Plan** | Semantic layer manifest | All phases | Extract specs from plan, don''t generate |
| 1 | **Metric Views** | Gold tables + COMMENTs | Genie + Dashboards | `WITH METRICS LANGUAGE YAML` syntax |
| 2 | **TVFs** | Gold YAML schemas | Genie NL queries | All date params STRING (not DATE) |
| 3 | **Genie Space** | MVs + TVFs + COMMENTs | End-user queries | ≥10 benchmarks, Serverless warehouse |
| 4 | **JSON Export** | Genie Space | CI/CD deployment | Variable substitution for env portability |
| 5 | **Optimization** | Genie Space deployed | Production readiness | ≥95% accuracy, ≥90% repeatability |

**Build bottom-up:** Metric Views and TVFs FIRST (both depend only on Gold), then Genie Space (depends on both), then Optimize.

---

## 🔧 What Happens Behind the Scenes

When you paste the prompt, the AI reads `@data_product_accelerator/skills/semantic-layer/00-semantic-layer-setup/SKILL.md` — the **Semantic Layer orchestrator**. Behind the scenes:

1. **Phase 0: Read Plan** — the orchestrator first looks for `plans/manifests/semantic-layer-manifest.yaml`. If found, it uses this as the implementation checklist (every TVF, Metric View, and Genie Space pre-defined). If not found, it falls back to self-discovery from Gold tables.
2. **5 Worker skills auto-loaded:**
   - `01-metric-views-patterns` — `WITH METRICS LANGUAGE YAML` syntax, schema validation, join patterns (including snowflake schema)
   - `02-databricks-table-valued-functions` — STRING parameters (non-negotiable), v3.0 bullet-point comments, Top-N via ROW_NUMBER, SCD2 handling
   - `03-genie-space-patterns` — 7-section deliverable structure, General Instructions (≤20 lines), minimum 10 benchmark questions
   - `04-genie-space-export-import-api` — REST API JSON schema for programmatic Genie Space deployment (CI/CD)
   - `05-genie-space-optimization` — iterative 6-lever optimization loop targeting 95%+ accuracy, 90%+ repeatability
3. **5 Common skills auto-loaded:**
   - `databricks-expert-agent` — "Extract, Don''t Generate" applied to all schema references
   - `databricks-asset-bundles` — SQL task jobs for TVF deployment, Python jobs for Metric Views
   - `databricks-python-imports` — pure Python module patterns for Metric View creation scripts
   - `naming-tagging-standards` — enterprise naming for all semantic layer artifacts
   - `databricks-autonomous-operations` — self-healing deploy loop when jobs fail
4. **Phase-ordered execution:** Metric Views → TVFs → Genie Space → API Export → Optimization. Each phase only begins after the previous completes.
5. **Phase 5: Optimization Loop** — after Genie Space creation, the orchestrator runs benchmark questions via the Conversation API and tunes 6 control levers (UC metadata, Metric Views, TVFs, Monitoring tables, ML tables, Genie Instructions) until accuracy ≥95% and repeatability ≥90%.

**Key principle:** The AI reads your plan manifest to **extract** specifications — it doesn''t generate them from scratch. This ensures the semantic layer matches your approved plan exactly.

### 🏅 Databricks Best Practices Applied

| Practice | How It''s Used Here |
|----------|-------------------|
| **Metric View `WITH METRICS LANGUAGE YAML`** | Metric views use Databricks'' native YAML syntax (`CREATE VIEW ... WITH METRICS LANGUAGE YAML AS $$ ... $$`) — NOT regular views with TBLPROPERTIES |
| **TVFs with STRING Parameters** | All TVF date parameters use STRING type — non-negotiable for Genie compatibility. Genie passes dates as strings; DATE type breaks SQL generation. |
| **v3.0 Bullet-Point Comments** | `• PURPOSE:`, `• BEST FOR:`, `• RETURNS:`, `• PARAMS:`, `• SYNTAX:` — Genie parses these structured bullets to decide when to invoke each TVF |
| **Schema Validation Before SQL** | Always read Gold YAML schemas before writing TVF SQL. 100% of compilation errors are caused by referencing non-existent columns. |
| **ROW_NUMBER for Top-N** | Never `LIMIT {param}` in TVFs (SQL compilation error). Use `ROW_NUMBER() OVER(...) + WHERE rank <= top_n` instead. |
| **SCD2 Filter on Dimension Joins** | Every TVF joining dimensions must include `AND dim.is_current = true` — omitting this causes row duplication from historical SCD2 records |
| **Genie Space General Instructions** | ≤20 lines of focused instructions telling Genie which tables to prefer, default time ranges, and disambiguation rules |
| **Minimum 10 Benchmark Questions** | Each Genie Space requires ≥ 10 benchmark questions with exact expected SQL — enables automated accuracy testing via the Conversation API |
| **Column Comments Required** | All Gold tables must have column COMMENTs BEFORE creating a Genie Space — Genie uses these to understand column semantics for SQL generation |
| **Export/Import API for CI/CD** | Genie Space configuration exported as JSON — enables version-controlled deployment across dev/staging/prod environments |
| **Optimization Loop (6 Levers)** | Iterative tuning: UC metadata → Metric Views → TVFs → Monitoring tables → ML tables → Genie Instructions, targeting 95%+ accuracy, 90%+ repeatability |
| **Serverless SQL Warehouse** | Genie Spaces MUST use a Serverless SQL warehouse — required for natural language query execution. NEVER Classic or Pro. |
| **Synonym-Rich Definitions** | 3-5 synonyms per dimension/measure (e.g., "revenue" → "earnings", "income", "amount") — dramatically improves Genie NL understanding |

---

## 📋 The Three Semantic Components

### 1️⃣ Table-Valued Functions (TVFs)

**What:** Parameterized SQL functions that return tables.

```sql
-- Example TVF (v3.0 bullet-point comment format)
CREATE OR REPLACE FUNCTION get_top_properties_by_revenue(
  start_date STRING COMMENT ''Start date (format: YYYY-MM-DD)'',
  end_date STRING COMMENT ''End date (format: YYYY-MM-DD)'',
  top_n INT DEFAULT 10 COMMENT ''Number of top properties to return''
)
RETURNS TABLE(
  rank INT COMMENT ''Property rank by revenue'',
  property_name STRING COMMENT ''Property display name'',
  destination STRING COMMENT ''Property location'',
  total_revenue DECIMAL(18,2) COMMENT ''Total booking revenue for period''
)
COMMENT ''
• PURPOSE: Returns top N properties ranked by booking revenue for a date range
• BEST FOR: "top properties by revenue" | "best performing properties" | "highest earning rentals"
• RETURNS: Individual property rows (rank, name, destination, revenue)
• PARAMS: start_date, end_date (YYYY-MM-DD), top_n (default: 10)
• SYNTAX: SELECT * FROM get_top_properties_by_revenue(''''2024-01-01'''', ''''2024-12-31'''', 10)
''
RETURN
  WITH ranked AS (
    SELECT 
      p.property_name,
      d.destination_name as destination,
      SUM(f.total_amount) as total_revenue,
      ROW_NUMBER() OVER (ORDER BY SUM(f.total_amount) DESC) as rank
    FROM {catalog}.{gold_schema}.fact_booking_detail f
    JOIN {catalog}.{gold_schema}.dim_property p 
      ON f.property_id = p.property_id AND p.is_current = true
    JOIN {catalog}.{gold_schema}.dim_destination d 
      ON f.destination_id = d.destination_id
    WHERE f.booking_date BETWEEN CAST(start_date AS DATE) AND CAST(end_date AS DATE)
    GROUP BY p.property_name, d.destination_name
  )
  SELECT rank, property_name, destination, total_revenue
  FROM ranked
  WHERE rank <= top_n;
```

**⚠️ Critical TVF Rules:**
- ✅ **STRING for date params** — Genie passes dates as strings. DATE type breaks Genie SQL generation.
- ✅ **ROW_NUMBER + WHERE** for Top N — never `LIMIT {param}` (SQL compilation error)
- ✅ **v3.0 bullet-point COMMENT** — `• PURPOSE:`, `• BEST FOR:`, `• RETURNS:`, `• PARAMS:`, `• SYNTAX:`
- ✅ **SCD2 filter** — `AND p.is_current = true` on dimension joins
- ✅ **NULLIF** for all divisions — prevents divide-by-zero errors

---

### 2️⃣ Metric Views

**What:** Semantic definitions with dimensions, measures, and synonyms using Databricks'' `WITH METRICS LANGUAGE YAML` syntax.

```sql
-- Metric Views use YAML syntax, NOT regular SQL views:
CREATE OR REPLACE VIEW {catalog}.{gold_schema}.revenue_analytics_metrics
WITH METRICS
LANGUAGE YAML
COMMENT ''PURPOSE: Revenue and booking analytics...''
AS $$
version: "1.1"

source: {catalog}.{gold_schema}.fact_booking_detail

dimensions:
  - name: destination
    expr: source.destination_name
    comment: Travel destination for geographic analysis
    display_name: Destination
    synonyms: [location, city, travel destination]

measures:
  - name: total_revenue
    expr: SUM(source.total_amount)
    comment: Total booking revenue in USD
    display_name: Total Revenue
    format:
      type: currency
      currency_code: USD
    synonyms: [revenue, earnings, income, amount]

  - name: booking_count
    expr: COUNT(*)
    comment: Number of bookings
    display_name: Booking Count
    synonyms: [bookings, reservations, count]
$$
```

**⚠️ Critical Metric View Rules:**
- ✅ **`WITH METRICS LANGUAGE YAML`** — NOT regular `CREATE VIEW` with TBLPROPERTIES
- ✅ **`AS $$ ... $$`** — YAML wrapped in dollar-quote delimiters (no SELECT)
- ✅ **`version: "1.1"`** — required in every metric view YAML
- ✅ **3-5 synonyms** per dimension/measure — dramatically improves Genie NL accuracy
- ✅ **Format specs** — currency, percentage, number for proper display

---

### 3️⃣ Genie Space

**What:** Natural language interface to your data, configured with a **7-section deliverable structure.**

**Required sections:**

| # | Section | Requirement |
|---|---------|-------------|
| 1 | **Name & Description** | Domain-specific, descriptive name |
| 2 | **Data Assets** | Priority order: Metric Views → TVFs → Gold Tables (≤ 25 total) |
| 3 | **General Instructions** | ≤ 20 lines: table preferences, defaults, disambiguation |
| 4 | **Benchmark Questions** | ≥ 10 questions with exact expected SQL |
| 5 | **Sample Questions** | 5-10 curated examples shown to users |
| 6 | **Warehouse** | Serverless SQL Warehouse (non-negotiable) |
| 7 | **Column Comments** | Verify ALL Gold tables have COMMENTs before creation |

**Data Asset Priority:** Genie uses Metric Views FIRST (pre-aggregated), then TVFs (parameterized), then raw Gold tables. This priority order maximizes accuracy.

**Example benchmark question (with exact SQL):**
```
Q: "What is our total revenue this month?"
SQL: SELECT MEASURE(total_revenue) FROM revenue_analytics_metrics
     WHERE booking_date >= DATE_TRUNC(''month'', CURRENT_DATE())
```

---

## Prerequisite

**Run this in your cloned Template Repository** (see Prerequisites in Step 0).

Ensure you have:
- ✅ Gold Layer Implementation completed (Step 12) — with column COMMENTs on all tables
- ✅ Use-Case Plan created (Step 13) — with `planning_mode: workshop`
- ✅ Plan manifest exists: `plans/manifests/semantic-layer-manifest.yaml`
- ✅ Plan addendum files exist:
  - `plans/phase1-addendum-1.2-tvfs.md`
  - `plans/phase1-addendum-1.3-metric-views.md`
  - `plans/phase1-addendum-1.6-genie-spaces.md`
- ✅ Gold YAML schemas available in `gold_layer_design/yaml/` (for schema validation)

---

## Steps to Apply

### Step 1: Start New Agent Thread

Open Cursor and start a **new Agent thread** for clean context.

### Step 2: Copy and Paste the Prompt

1. **Copy the entire prompt** using the copy button
2. **Paste it into Cursor**
3. The AI will process all 4 implementation steps in order

### Step 3: Phase 0 — Plan Reading

The AI will:
1. Read `plans/manifests/semantic-layer-manifest.yaml` (implementation checklist)
2. Extract exact TVF names, Metric View specs, Genie Space configuration
3. If no manifest exists, fall back to self-discovery from Gold tables

### Step 4: Phase 1 — Metric Views

The AI will:
1. Read Metric View plan (`plans/phase1-addendum-1.3-metric-views.md`)
2. Create YAML definition files (dimensions, measures, synonyms, formats)
3. Create `create_metric_views.py` (reads YAML → `CREATE VIEW WITH METRICS LANGUAGE YAML`)
4. Create `metric_views_job.yml` for Asset Bundle deployment

### Step 5: Phase 2 — TVFs

The AI will:
1. Read TVF plan (`plans/phase1-addendum-1.2-tvfs.md`)
2. Validate Gold YAML schemas (confirm column names/types exist)
3. Create `table_valued_functions.sql` with v3.0 bullet-point COMMENTs
4. Create `tvf_job.yml` (SQL task) for Asset Bundle deployment

### Step 6: Phase 3 — Genie Space

The AI will:
1. Read Genie Space plan (`plans/phase1-addendum-1.6-genie-spaces.md`)
2. Verify ALL Gold tables have column COMMENTs (prerequisite)
3. Configure: data assets (MVs → TVFs → tables), General Instructions (≤20 lines)
4. Create ≥10 benchmark questions with exact expected SQL

### Step 7: Deploy and Validate

```bash
# Deploy all semantic layer jobs
databricks bundle deploy -t dev
databricks bundle run tvf_job -t dev
databricks bundle run metric_views_job -t dev
```

```sql
-- Test TVFs (note: STRING date params, not DATE)
SELECT * FROM get_revenue_by_period(''2024-01-01'', ''2024-12-31'');
SELECT * FROM get_top_properties_by_revenue(''2024-01-01'', ''2024-12-31'', 10);

-- Verify Metric View created correctly
SELECT table_name, table_type 
FROM information_schema.tables 
WHERE table_schema = ''{gold_schema}'' AND table_type = ''METRIC_VIEW'';
```

### Step 8: Phase 5 — Optimization Loop

After Genie Space is created:
1. Run benchmark questions via Conversation API
2. Check accuracy (target: ≥ 95%) and repeatability (target: ≥ 90%)
3. Apply 6 control levers if targets not met:
   - UC metadata → Metric Views → TVFs → Monitoring → ML → Genie Instructions
4. Re-test until targets achieved

---

## 💡 TVF Design Best Practices

### v3.0 Bullet-Point Comment Format (CRITICAL for Genie)

```sql
COMMENT ''
• PURPOSE: [One-line description of what it returns]
• BEST FOR: [Question 1] | [Question 2] | [Question 3]
• RETURNS: [Description of output rows — what each row represents]
• PARAMS: [param1] (required), [param2] (optional, default: X)
• SYNTAX: SELECT * FROM function_name(''''value1'''', ''''value2'''')
''
```

> **Why bullet format?** Genie''s SQL generation engine parses these structured comments to decide WHEN to invoke a TVF and WHICH parameters to pass. Unstructured prose comments reduce Genie accuracy.

### Parameter Rules (Non-Negotiable)

| Rule | Do This | Never Do This |
|------|---------|---------------|
| **Date params** | `start_date STRING COMMENT ''Format: YYYY-MM-DD''` | ❌ `start_date DATE` (breaks Genie) |
| **Param ordering** | Required first, DEFAULT params last | ❌ Optional before required |
| **Top N** | `ROW_NUMBER() OVER(...) + WHERE rank <= top_n` | ❌ `LIMIT top_n` (SQL error in TVF) |
| **Null safety** | `NULLIF(denominator, 0)` for all divisions | ❌ Bare division (divide-by-zero) |
| **SCD2 joins** | `AND dim.is_current = true` | ❌ Joining without SCD2 filter (duplicates) |

### Schema Validation BEFORE Writing SQL

**100% of TVF compilation errors are caused by not consulting Gold YAML schemas first.**

```python
# ALWAYS validate before writing SQL:
# 1. Read gold_layer_design/yaml/{domain}/{table}.yaml
# 2. Confirm column names and types exist
# 3. Then write TVF SQL using validated names
```

---

## 💡 Metric View Best Practices

### COMMENT Format (on the CREATE VIEW, not inside YAML)

```sql
COMMENT ''PURPOSE: Revenue and booking analytics by property and destination.
BEST FOR: "total revenue" | "bookings by destination" | "average nightly rate"
NOT FOR: Host-level metrics (use host_performance_metrics instead)
DIMENSIONS: destination, property_type, booking_month
MEASURES: total_revenue, booking_count, avg_nightly_rate
SOURCE: fact_booking_detail (bookings domain)''
```

### Schema Validation (100% Error Prevention)

```python
# Before writing YAML, validate column names exist:
# 1. Read gold_layer_design/yaml/bookings/fact_booking_detail.yaml
# 2. Confirm "destination_name", "total_amount", "property_type" exist
# 3. Only THEN write dimension/measure expressions using validated names
```

### Synonym Guidelines (3-5 per field)

```yaml
synonyms:
  - exact_alternative    # "revenue" for "total_revenue"
  - business_term        # "earnings" for "total_revenue"
  - abbreviation         # "qty" for "quantity"
  - common_variation     # "amount" for "total_amount"
  - colloquial           # "income" for "total_revenue"
```

> **Why 3-5?** Fewer synonyms miss natural language variations. More than 5 creates ambiguity where Genie can''t distinguish which measure the user means.

---

## 💡 Genie Space Configuration

### General Instructions (≤ 20 Lines)

```
-- These instructions tell Genie HOW to query your data:
1. For revenue queries, prefer revenue_analytics_metrics (Metric View) first
2. For parameterized queries (date ranges, top-N), use TVFs
3. For detail-level queries, use Gold tables directly
4. Default date range: last 30 days if not specified
5. Always join dimensions with is_current = true (SCD2)
6. For host queries, use dim_host; for property queries, use dim_property
7. Revenue = SUM(total_amount) from fact_booking_detail
8. When asked "top N", use get_top_properties_by_revenue TVF
```

> **Why ≤ 20 lines?** Genie''s instruction processing degrades with too many rules. Focus on table preferences, defaults, and common disambiguation.

### Benchmark Questions (Minimum 10, with Exact SQL)

```
-- Each benchmark includes the question AND the expected SQL:
Q1: "What is total revenue this month?"
SQL: SELECT MEASURE(total_revenue) FROM revenue_analytics_metrics WHERE ...

Q2: "Top 10 properties by revenue last year"
SQL: SELECT * FROM get_top_properties_by_revenue(''2025-01-01'', ''2025-12-31'', 10)

Q3: "How many bookings per destination?"
SQL: SELECT destination, MEASURE(booking_count) FROM revenue_analytics_metrics GROUP BY ...
-- ... (minimum 10 total)
```

> **Why exact SQL?** Benchmark SQL enables automated testing via the Conversation API — you can programmatically verify Genie generates correct queries.',
'## Expected Deliverables

### 📁 Semantic Layer Files Created

```
src/wanderbricks_gold/
├── table_valued_functions.sql           # All TVFs in one SQL file (3-5 functions)
├── semantic/
│   └── metric_views/
│       ├── revenue_analytics_metrics.yaml   # Metric view YAML definition
│       └── create_metric_views.py           # Script: reads YAML → CREATE VIEW WITH METRICS
├── genie/
│   └── genie_space_config.json          # Exported Genie Space config (CI/CD)
resources/
├── semantic-layer/
│   ├── tvf_job.yml                      # SQL task to deploy TVFs
│   ├── metric_views_job.yml             # Python task to deploy Metric Views
│   └── genie_deploy_job.yml             # Genie Space import job (optional)
```

**TVF Count:** 3-5 functions (workshop mode) — one per parameter pattern (date-range, entity-filter, top-N)

---

### 📊 Metric View Deployment Pattern

Each Metric View is created via a Python script that reads YAML and runs:

```python
# create_metric_views.py reads YAML → generates DDL
create_sql = f"""
CREATE OR REPLACE VIEW {catalog}.{gold_schema}.{view_name}
WITH METRICS
LANGUAGE YAML
COMMENT ''{view_comment}''
AS $$
{yaml_content}
$$
"""
spark.sql(create_sql)
```

> **Key:** Metric Views use `WITH METRICS LANGUAGE YAML` — NOT regular views with TBLPROPERTIES. This is a non-negotiable syntax requirement.

**Metric View Count:** 1-2 metric views (workshop mode) — one per fact table with richest dimension joins

---

### 📊 TVF Summary Table (Workshop Scope: 3-5 TVFs)

| Pattern | Function | Parameters (all STRING for dates) | Returns |
|---------|----------|----------------------------------|---------|
| **Date Range** | `get_revenue_by_period` | start_date STRING, end_date STRING | Revenue aggregates by destination |
| **Top-N** | `get_top_properties_by_revenue` | start_date STRING, end_date STRING, top_n INT | Top N properties ranked by revenue |
| **Entity Filter** | `get_host_performance` | host_id STRING DEFAULT NULL, min_bookings STRING DEFAULT ''5'' | Host performance metrics |

> **Workshop selection:** One per parameter pattern to teach the full TVF vocabulary. Production would add 10-15 more.

---

### 📊 Metric View Summary (Workshop Scope: 1-2)

| Metric View | Source | Dimensions | Measures | Synonyms |
|-------------|--------|------------|----------|----------|
| `revenue_analytics_metrics` | fact_booking_detail + dim_property + dim_destination | destination, property_type, booking_month | total_revenue, booking_count, avg_nightly_rate | revenue→earnings, bookings→reservations |

> **Workshop selection:** One metric view with richest joins to demonstrate full YAML syntax (dimensions, measures, joins, formats, synonyms).

---

### 🔗 Genie Space Configuration (1 Unified Space)

| Element | Value |
|---------|-------|
| **Name** | Wanderbricks Analytics |
| **Data Assets** | 1 Metric View + 3-5 TVFs + 4 Gold Tables (< 15 total) |
| **General Instructions** | ≤ 20 lines (table preferences, defaults, disambiguation) |
| **Benchmark Questions** | ≥ 10 with exact expected SQL |
| **Sample Questions** | 5-10 curated examples shown to users |
| **Warehouse** | Serverless SQL Warehouse (non-negotiable) |
| **Optimization Target** | Accuracy ≥ 95%, Repeatability ≥ 90% |

---

### ✅ Success Criteria Checklist

**TVFs (non-negotiable):**
- [ ] All date parameters use STRING type (never DATE — breaks Genie)
- [ ] v3.0 bullet-point COMMENT format on every TVF (`• PURPOSE:`, `• BEST FOR:`, etc.)
- [ ] Top-N uses `ROW_NUMBER() + WHERE rank <=` (never `LIMIT {param}`)
- [ ] SCD2 dimension joins include `AND dim.is_current = true`
- [ ] `NULLIF(denominator, 0)` for all divisions
- [ ] Schema validated against Gold YAML before writing SQL
- [ ] 3-5 TVFs created (workshop mode)

**Metric Views (non-negotiable):**
- [ ] Created with `WITH METRICS LANGUAGE YAML` syntax (not regular VIEW)
- [ ] `table_type = ''METRIC_VIEW''` in `information_schema.tables`
- [ ] 3-5 synonyms per dimension/measure
- [ ] Format specifications (currency, percentage) where applicable
- [ ] Source table references validated against Gold YAML
- [ ] 1-2 metric views created (workshop mode)

**Genie Space (non-negotiable):**
- [ ] All Gold tables have column COMMENTs (prerequisite verified)
- [ ] Uses Serverless SQL Warehouse (never Classic or Pro)
- [ ] General Instructions ≤ 20 lines
- [ ] ≥ 10 benchmark questions with exact expected SQL
- [ ] Data assets: Metric Views → TVFs → Gold Tables (priority order)
- [ ] Total data assets ≤ 25 per space (< 15 for workshop)
- [ ] Natural language queries producing correct SQL

**Optimization (target):**
- [ ] Accuracy ≥ 95% (benchmark questions answered correctly)
- [ ] Repeatability ≥ 90% (same question → same SQL each time)
- [ ] 6-lever optimization applied if targets not met

**Deployment:**
- [ ] `tvf_job.yml` — SQL task for TVF deployment
- [ ] `metric_views_job.yml` — Python task for Metric View deployment
- [ ] JSON export created for Genie Space CI/CD (optional)
- [ ] `databricks bundle deploy -t dev` succeeds',
true, 1, true, current_timestamp(), current_timestamp(), current_user());

-- Step 16: Build AI/BI Dashboard - bypass_LLM = TRUE
INSERT INTO ${catalog}.${schema}.section_input_prompts 
(input_id, section_tag, input_template, system_prompt, section_title, section_description, order_number, how_to_apply, expected_output, bypass_llm, version, is_active, inserted_at, updated_at, created_by)
VALUES
(12, 'aibi_dashboard',
'Build an AI/BI (Lakeview) Dashboard using @data_product_accelerator/skills/monitoring/02-databricks-aibi-dashboards/SKILL.md

Reference the dashboard plan at @data_product_accelerator/plans/phase1-addendum-1.1-dashboards.md

The skill provides:
- Dashboard JSON structure with **6-column grid** layout (NOT 12!)
- Widget patterns: KPI counters (v2), charts (v3), tables (v1), filters (v2)
- Query patterns from Metric Views using `MEASURE()` function
- Pre-deployment SQL validation (90% reduction in dev loop time)
- UPDATE-or-CREATE deployment pattern (preserves URLs and permissions)
- Variable substitution (`${catalog}`, `${gold_schema}`) — no hardcoded schemas
- Monitoring table query patterns (window structs, CASE pivots) if Lakehouse Monitors exist

Build the dashboard in this order:
1. Plan layout (KPIs, filters, charts, tables)
2. Create datasets (validated SQL queries)
3. Build widgets with correct version specs
4. Configure parameters (DATE type, not DATETIME)
5. Add Global Filters page
6. Deploy via Workspace Import API',
'Static prompt - no LLM processing required. This prompt is copied directly to the AI coding assistant.',
'Build AI/BI Dashboard',
'Create an AI/BI (Lakeview) dashboard with KPI counters, charts, filters, and automated deployment from Gold layer data',
16,
'## 📊 What is an AI/BI (Lakeview) Dashboard?

**AI/BI Dashboards** (formerly Lakeview) provide **visual, self-service analytics** for business users — no SQL required. They are built from JSON configuration files that define datasets, widgets, pages, and parameters.

**Core Philosophy: Self-Service Analytics**
- ✅ Visual insights for non-technical users
- ✅ Consistent metrics across the organization (via Metric Views)
- ✅ Professional, branded appearance with auto-refresh
- ✅ Automated deployment with validation
- ❌ NOT a code editor — business users interact through UI only

### Lakeview Dashboard Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     AI/BI (LAKEVIEW) DASHBOARD                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    DASHBOARD JSON                                    │   │
│  │              (.lvdash.json configuration file)                      │   │
│  │                                                                     │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │                    PAGES                                     │   │   │
│  │  │  Page 1: Overview    │  Page 2: Details   │  Global Filters │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  │                                                                     │   │
│  │  ┌───────────────────────────────────────────────────────────────┐ │   │
│  │  │                  WIDGETS (6-Column Grid)                       │ │   │
│  │  │                                                               │ │   │
│  │  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐    │ │   │
│  │  │  │ KPI  │ │ KPI  │ │ KPI  │ │ KPI  │ │ KPI  │ │ KPI  │    │ │   │
│  │  │  │ (v2) │ │ (v2) │ │ (v2) │ │ (v2) │ │ (v2) │ │ (v2) │    │ │   │
│  │  │  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘    │ │   │
│  │  │  ┌─────────────────┐ ┌─────────────────┐                    │ │   │
│  │  │  │  Line Chart (v3)│ │  Bar Chart (v3) │                    │ │   │
│  │  │  │  Trend over time│ │  By dimension   │                    │ │   │
│  │  │  └─────────────────┘ └─────────────────┘                    │ │   │
│  │  │  ┌─────────────────────────────────────┐                    │ │   │
│  │  │  │         Data Table (v1)              │                    │ │   │
│  │  │  │         Detailed drill-down          │                    │ │   │
│  │  │  └─────────────────────────────────────┘                    │ │   │
│  │  └───────────────────────────────────────────────────────────────┘ │   │
│  │                                                                     │   │
│  │  ┌───────────────────────────────────────────────────────────────┐ │   │
│  │  │                    DATASETS                                    │ │   │
│  │  │  SQL queries → Metric Views / Gold tables / Monitoring tables │ │   │
│  │  │  Parameters: DATE type (not DATETIME), variable substitution  │ │   │
│  │  └───────────────────────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌──────────────────────┐  ┌──────────────────────┐                       │
│  │   DEPLOY via API     │  │   VALIDATE before     │                       │
│  │   UPDATE-or-CREATE   │  │   deploy (SQL + widget)│                       │
│  │   Preserves URLs     │  │   90% faster dev loop  │                       │
│  └──────────────────────┘  └──────────────────────┘                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Key Concepts

| Concept | What It Means | Why It Matters |
|---------|--------------|----------------|
| **Lakeview JSON** | Dashboards are defined as `.lvdash.json` files | Version-controlled, deployable via API |
| **6-Column Grid** | Widget positions use columns 0-5 (NOT 12!) | #1 cause of widget snapping issues |
| **Widget Versions** | KPIs=v2, Charts=v3, Tables=v1, Filters=v2 | Wrong version causes rendering errors |
| **DATE Parameters** | Use DATE type (not DATETIME) with static defaults | DATETIME with dynamic expressions won''t work |
| **`dataset_catalog`/`dataset_schema`** | Variable substitution for environment portability | Never hardcode catalog/schema in queries |
| **Widget-Query Alignment** | Widget `fieldName` MUST match query output alias | #1 cause of "no fields to visualize" errors |
| **Number Formatting** | Return raw numbers; widgets format them | `FORMAT_NUMBER()` or string concat breaks widgets |
| **Global Filters Page** | Dedicated page for cross-dashboard filtering | Required for consistent filter behavior |

---

## 🔧 What Happens Behind the Scenes

When you paste the prompt, the AI reads `@data_product_accelerator/skills/monitoring/02-databricks-aibi-dashboards/SKILL.md` — the **AI/BI Dashboard worker skill**. Behind the scenes:

1. **Plan reading** — the skill reads your dashboard plan (`plans/phase1-addendum-1.1-dashboards.md`) to extract: KPIs, charts, filters, layout requirements
2. **Dashboard skill loaded** — provides complete JSON templates, widget specs, grid layout rules, query patterns, validation scripts, and deployment workflows
3. **5 Common skills auto-loaded:**
   - `databricks-expert-agent` — "Extract, Don''t Generate" for table/column names
   - `databricks-asset-bundles` — dashboard resource deployment
   - `databricks-python-imports` — deployment script module patterns
   - `naming-tagging-standards` — dashboard and file naming conventions
   - `databricks-autonomous-operations` — self-healing deploy loop
4. **Query pattern selection:** Metric Views → Gold tables → Monitoring tables (priority order)
5. **Pre-deployment validation** — SQL validation + widget-encoding alignment check before import (catches 90% of errors before deploy)
6. **UPDATE-or-CREATE deployment** — Workspace Import API with `overwrite: true` preserves URLs and permissions

**Key principle:** The AI reads your plan to **extract** KPI/chart requirements. Dashboard queries use `${catalog}` and `${gold_schema}` variable substitution — never hardcoded schemas.

> **Note:** For the full observability stack (Lakehouse Monitoring + Dashboards + SQL Alerts), use the orchestrator at `@data_product_accelerator/skills/monitoring/00-observability-setup/SKILL.md`. This step focuses specifically on the dashboard.

### 🏅 Databricks Best Practices Applied

| Practice | How It''s Used Here |
|----------|-------------------|
| **6-Column Grid (NOT 12!)** | Widget widths use 1-6 columns. `width: 6` = full width, `width: 3` = half. This is the #1 cause of layout issues — most platforms use 12 columns, Lakeview uses 6. |
| **Widget Version Specs** | KPI Counters = version 2, Charts (bar/line/pie/area) = version 3, Tables = version 1, Filters = version 2. Wrong version causes rendering failures. |
| **Widget-Query Column Alignment** | Every widget `fieldName` MUST exactly match the SQL alias in its dataset query. Mismatch = "no fields to visualize" error. |
| **Raw Number Formatting** | Queries return raw numbers (e.g., `0.85` for 85%). Widgets apply formatting (`number-percent`, `number-currency`, `number-plain`). NEVER use `FORMAT_NUMBER()` or string concatenation. |
| **DATE Parameters (Not DATETIME)** | Dashboard parameters use `DATE` type with static default values. `DATETIME` with dynamic expressions like `now-30d/d` does NOT work. |
| **Variable Substitution** | All queries use `${catalog}.${gold_schema}` — never hardcoded catalog/schema. Substitution done in Python at deployment time. |
| **Global Filters Page** | Every dashboard includes a `PAGE_TYPE_GLOBAL_FILTERS` page for cross-dashboard date range and dimension filtering. |
| **Metric View Queries** | Dashboards query Metric Views using `MEASURE()` function for consistent metric definitions. Metric Views are preferred over raw Gold tables. |
| **UPDATE-or-CREATE Deployment** | Workspace Import API with `overwrite: true` — single code path for create and update. Preserves dashboard URLs and viewer permissions. |
| **Pre-Deployment SQL Validation** | All dataset queries validated with `SELECT ... LIMIT 1` before dashboard import. Catches UNRESOLVED_COLUMN, TABLE_NOT_FOUND, UNBOUND_PARAMETER errors. |
| **SCD2 Handling in Queries** | Dimension queries use `QUALIFY ROW_NUMBER() OVER(PARTITION BY id ORDER BY change_time DESC) = 1` or `WHERE is_current = true` |
| **"All" Option for Filters** | Filter datasets include `SELECT ''All'' UNION ALL SELECT DISTINCT ...` so users can clear filters |

---

## 📋 Dashboard Components

### Widget Type Reference

| Widget Type | Version | Use Case | Grid Size |
|-------------|---------|----------|-----------|
| **KPI Counter** | v2 | Single metric display (revenue, count) | width: 1-2, height: 2 |
| **Bar Chart** | v3 | Category comparisons (revenue by destination) | width: 3, height: 6 |
| **Line Chart** | v3 | Trends over time (daily revenue) | width: 3, height: 6 |
| **Pie Chart** | v3 | Distribution (booking share by type) | width: 3, height: 6 |
| **Area Chart** | v3 | Stacked trends (revenue by category over time) | width: 3-6, height: 6 |
| **Data Table** | v1 | Detailed drill-down data | width: 6, height: 6+ |
| **Filter** | v2 | Single-select / multi-select / date range | width: 2, height: 2 |

### Chart Scale Rules (Encoding Requirements)

```
Pie Charts:   color.scale = categorical, angle.scale = quantitative
Bar Charts:   x.scale = categorical, y.scale = quantitative
Line Charts:  x.scale = temporal, y.scale = quantitative
Area Charts:  x.scale = temporal, y.scale = quantitative, y.stack = "zero"
```

> **Missing `scale` in encodings** is the #2 cause of "unable to render visualization" errors.

### Standard Dashboard Layout

```
┌─────────────────────────────────────────────────────┐
│ Page 1: Overview                                     │
│                                                     │
│ Row 0 (height 2): Filters                           │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│ │ Date (w2)│ │ Filter(w2│ │ Filter(w2│            │
│ └──────────┘ └──────────┘ └──────────┘            │
│                                                     │
│ Row 2 (height 2): KPI Counters                      │
│ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐       │
│ │KPI │ │KPI │ │KPI │ │KPI │ │KPI │ │KPI │       │
│ │w=1 │ │w=1 │ │w=1 │ │w=1 │ │w=1 │ │w=1 │       │
│ └────┘ └────┘ └────┘ └────┘ └────┘ └────┘       │
│                                                     │
│ Row 4 (height 6): Charts                            │
│ ┌──────────────────┐ ┌──────────────────┐          │
│ │  Line Chart (w3) │ │  Bar Chart  (w3) │          │
│ │  Revenue Trend   │ │  By Destination  │          │
│ └──────────────────┘ └──────────────────┘          │
│                                                     │
│ Row 10 (height 6): Detail Table                     │
│ ┌──────────────────────────────────────┐            │
│ │         Data Table (w6)              │            │
│ │         Full-width drill-down        │            │
│ └──────────────────────────────────────┘            │
│                                                     │
├─────────────────────────────────────────────────────┤
│ Page: Global Filters                                 │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│ │ Date (w2)│ │ Dim  (w2)│ │ Dim  (w2)│            │
│ └──────────┘ └──────────┘ └──────────┘            │
│ pageType: PAGE_TYPE_GLOBAL_FILTERS                  │
└─────────────────────────────────────────────────────┘
```

---

## Prerequisite

**Run this in your cloned Template Repository** (see Prerequisites in Step 0).

Ensure you have:
- ✅ Gold Layer Implementation completed (Step 12) — with column COMMENTs
- ✅ Semantic Layer completed (Step 14) — Metric Views for dashboard queries
- ✅ Use-Case Plan created (Step 13) — with dashboard requirements
- ✅ Plan file exists: `plans/phase1-addendum-1.1-dashboards.md`
- ✅ Gold YAML schemas available for column name validation

---

## Steps to Apply

### Step 1: Start New Agent Thread

Open Cursor and start a **new Agent thread** for clean context.

### Step 2: Copy and Paste the Prompt

1. **Copy the entire prompt** using the copy button
2. **Paste it into Cursor**
3. The AI will build the dashboard in phases

### Step 3: Plan Reading

The AI will:
1. Read dashboard plan (`plans/phase1-addendum-1.1-dashboards.md`)
2. Extract KPI requirements, chart types, filter dimensions
3. Identify data sources (Metric Views preferred over raw Gold tables)

### Step 4: Dataset Creation

The AI will:
1. Create SQL queries for each widget (using `${catalog}` substitution)
2. Use `MEASURE()` function for Metric View queries
3. Include "All" option for filter datasets
4. Handle NULLs with `COALESCE()` and SCD2 with `is_current = true`

### Step 5: Widget and Layout Creation

The AI will:
1. Build KPI counters (version 2) for top-line metrics
2. Build charts (version 3) for trends and comparisons
3. Build data tables (version 1) for drill-down
4. Position using 6-column grid (widths 1-6, NOT 12!)

### Step 6: Parameter and Filter Configuration

The AI will:
1. Add DATE parameters with static defaults (not DATETIME)
2. Create Global Filters page (`PAGE_TYPE_GLOBAL_FILTERS`)
3. Link filter widgets to dataset parameters

### Step 7: Validate and Deploy

```bash
# Pre-deployment validation
python scripts/validate_dashboard_queries.py
python scripts/validate_widget_encodings.py

# Deploy via Asset Bundle or API
databricks bundle deploy -t dev
```

```sql
-- Verify Gold tables have COMMENTs (prerequisite for good queries)
SELECT table_name, comment FROM information_schema.tables 
WHERE table_schema = ''{gold_schema}'' AND comment IS NOT NULL;
```

---

## 💡 Query Pattern Best Practices

### Use Metric Views (Preferred)

```sql
-- ✅ PREFERRED: Query Metric View with MEASURE()
SELECT 
  destination,
  MEASURE(total_revenue) as revenue,
  MEASURE(booking_count) as bookings
FROM ${catalog}.${gold_schema}.revenue_analytics_metrics
WHERE booking_date BETWEEN :start_date AND :end_date
GROUP BY destination
ORDER BY revenue DESC
```

### Direct Gold Table Query (Fallback)

```sql
-- When no Metric View exists for the data
SELECT 
  d.destination_name as destination,
  SUM(f.total_amount) as revenue,
  COUNT(*) as bookings
FROM ${catalog}.${gold_schema}.fact_booking_detail f
JOIN ${catalog}.${gold_schema}.dim_destination d 
  ON f.destination_id = d.destination_id
WHERE f.booking_date BETWEEN :start_date AND :end_date
GROUP BY d.destination_name
ORDER BY revenue DESC
```

### Number Formatting Rules

| Return This | Widget Displays | Format Type |
|-------------|-----------------|-------------|
| `0.85` | `85%` | `number-percent` |
| `1234.56` | `$1,234.56` | `number-currency` |
| `1234` | `1,234` | `number-plain` |

> **NEVER** use `FORMAT_NUMBER()`, `CONCAT(''$'', ...)`, or `CONCAT(..., ''%'')` in queries. Return raw numbers; let widgets format them.',
'## Expected Deliverables

### 📁 Dashboard Files Created

```
docs/dashboards/
├── wanderbricks_analytics_dashboard.lvdash.json   # Dashboard JSON config
└── README.md                                      # Dashboard documentation

scripts/
├── deploy_dashboard.py                            # UPDATE-or-CREATE deployment
├── validate_dashboard_queries.py                  # Pre-deploy SQL validation
└── validate_widget_encodings.py                   # Widget-query alignment check

resources/monitoring/
└── dashboard_deploy_job.yml                       # Asset Bundle deployment job
```

> **Key:** The `.lvdash.json` file IS the dashboard. It contains all datasets, pages, widgets, parameters, and theme settings. Version-control this file.

---

### 📊 Dashboard Configuration Summary (Workshop Scope)

| Element | Value |
|---------|-------|
| **Dashboard Name** | Wanderbricks Analytics Dashboard |
| **Pages** | 2 (Overview + Global Filters) |
| **KPI Counters** | 3-6 top-line metrics (total revenue, bookings, avg rate) |
| **Charts** | 2-4 visualizations (trend line, bar comparison, pie distribution) |
| **Data Tables** | 1 drill-down table |
| **Filters** | Date range + 1-2 dimension filters |
| **Data Sources** | Metric Views (preferred) + Gold tables (fallback) |
| **Parameters** | DATE type with static defaults |
| **Deployment** | UPDATE-or-CREATE via Workspace Import API |

---

### 📊 What Each Widget Does

| Widget | Type | Version | Data Source | Insight |
|--------|------|---------|-------------|---------|
| Total Revenue | KPI Counter | v2 | `revenue_analytics_metrics` | Top-line revenue figure |
| Booking Count | KPI Counter | v2 | `revenue_analytics_metrics` | Total bookings in period |
| Avg Nightly Rate | KPI Counter | v2 | `revenue_analytics_metrics` | Average price metric |
| Revenue Trend | Line Chart | v3 | `fact_booking_detail` | Revenue over time |
| Revenue by Destination | Bar Chart | v3 | `revenue_analytics_metrics` | Geographic breakdown |
| Booking Details | Data Table | v1 | `fact_booking_detail + dims` | Drill-down for analysis |
| Date Range | Filter | v2 | Parameter | Cross-page date filtering |
| Destination | Filter | v2 | `dim_destination` | Geographic filtering |

---

### 📊 6-Column Grid Layout (Critical)

```
┌──────────────────────────────────────────┐
│ Grid columns: 0  1  2  3  4  5          │
│                                          │
│ width: 1 = one column (1/6 of page)     │
│ width: 2 = two columns (1/3 of page)    │
│ width: 3 = three columns (1/2 of page)  │
│ width: 6 = full width (entire page)     │
│                                          │
│ Common layouts:                          │
│ • 6 KPIs: [w1][w1][w1][w1][w1][w1]     │
│ • 3 KPIs: [w2  ][w2  ][w2  ]           │
│ • 2 charts: [w3     ][w3     ]          │
│ • Full table: [w6                ]       │
└──────────────────────────────────────────┘
```

> **#1 mistake:** Using width values from a 12-column grid. In Lakeview, `width: 6` = FULL width, not half!

---

### 📊 Dashboard JSON Structure (Simplified)

```json
{
  "datasets": [
    {
      "name": "kpi_totals",
      "query": "SELECT ... FROM ${catalog}.${gold_schema}.metric_view ..."
    }
  ],
  "pages": [
    {
      "name": "page_overview",
      "displayName": "Overview",
      "layout": [ /* widgets with positions */ ]
    },
    {
      "name": "page_global_filters",
      "displayName": "Global Filters",
      "pageType": "PAGE_TYPE_GLOBAL_FILTERS",
      "layout": [ /* filter widgets */ ]
    }
  ],
  "parameters": [
    {
      "keyword": "start_date",
      "dataType": "DATE",
      "defaultSelection": { "values": { "values": [{"value": "2024-01-01"}] } }
    }
  ]
}
```

---

### ✅ Success Criteria Checklist

**Grid and Layout:**
- [ ] All widget widths use 6-column grid (1-6, never 7-12)
- [ ] KPI row uses consistent heights (height: 2)
- [ ] Chart row uses consistent heights (height: 6)
- [ ] Full-width tables use width: 6
- [ ] Global Filters page included (`PAGE_TYPE_GLOBAL_FILTERS`)

**Widget Versions (non-negotiable):**
- [ ] KPI Counters use version 2 (not 3)
- [ ] Bar/Line/Pie/Area Charts use version 3
- [ ] Data Tables use version 1
- [ ] Filters use version 2

**Widget-Query Alignment:**
- [ ] Every widget `fieldName` matches its SQL alias exactly
- [ ] Pie charts have `scale` on both `color` and `angle` encodings
- [ ] Bar charts have `scale` on both `x` and `y` encodings
- [ ] Line charts use `temporal` scale on x-axis

**Number Formatting:**
- [ ] Percentages returned as 0-1 decimal (widget displays as %)
- [ ] Currency returned as raw number (widget displays as $)
- [ ] No `FORMAT_NUMBER()` or string concatenation in queries

**Parameters:**
- [ ] Date parameters use DATE type (never DATETIME)
- [ ] Static default values (never dynamic expressions like `now-30d`)
- [ ] All parameters defined in dataset''s `parameters` array
- [ ] Filters include "All" option via `UNION ALL`

**Data Sources:**
- [ ] Queries use `${catalog}.${gold_schema}` variable substitution
- [ ] No hardcoded catalog or schema names in queries
- [ ] Metric View queries use `MEASURE()` function where applicable
- [ ] SCD2 dimensions filtered with `is_current = true` or `QUALIFY`
- [ ] NULL values handled with `COALESCE()`

**Deployment:**
- [ ] `.lvdash.json` file created and version-controlled
- [ ] `deploy_dashboard.py` uses UPDATE-or-CREATE pattern
- [ ] `validate_dashboard_queries.py` passes all SQL checks
- [ ] `validate_widget_encodings.py` passes all alignment checks
- [ ] `databricks bundle deploy -t dev` succeeds

**Verification:**
```sql
-- Check dashboard exists in workspace
-- Navigate to: Databricks → Dashboards → find your dashboard

-- Verify data sources are connected
SELECT COUNT(*) FROM ${catalog}.${gold_schema}.fact_booking_detail;

-- Verify Metric Views exist
SELECT table_name, table_type 
FROM information_schema.tables 
WHERE table_schema = ''{gold_schema}'' AND table_type = ''METRIC_VIEW'';
```',
true, 1, true, current_timestamp(), current_timestamp(), current_user());

-- Step 18: Redeploy & Test Application (Autonomous Operations + Repository Documentation) - bypass_LLM = TRUE
INSERT INTO ${catalog}.${schema}.section_input_prompts 
(input_id, section_tag, input_template, system_prompt, section_title, section_description, order_number, how_to_apply, expected_output, bypass_llm, version, is_active, inserted_at, updated_at, created_by)
VALUES
(15, 'redeploy_test',
'Build, deploy, and test the complete application using @data_product_accelerator/skills/common/databricks-autonomous-operations/SKILL.md for self-healing deployment and @data_product_accelerator/skills/common/databricks-asset-bundles/SKILL.md for DAB validation.

After deployment succeeds, document the entire repository using @data_product_accelerator/skills/admin/documentation-organization/SKILL.md in Framework Documentation Authoring mode.

---

## IMPORTANT: Analyze Current Project First

**This step uses your existing project deployment infrastructure.** Before deploying:

1. **Review the current project structure** to identify:
   - Deploy scripts (e.g., `deploy.sh`, `scripts/deploy.py`)
   - Build configurations (`package.json`, `requirements.txt`)
   - DAB configuration (`databricks.yml`)
   - Environment configurations

Use the AI assistant to analyze the project:
```
@codebase What deploy scripts and configurations exist in this project? 
How do I build and deploy this application to Databricks?
```

---

## Deployment Process (Self-Healing Loop)

Follow the autonomous operations skill''s core loop: **Deploy -> Poll -> Diagnose -> Fix -> Redeploy -> Verify** (max 3 iterations before escalation).

### Step 1: Identify Deployment Scripts
Look for existing scripts in your project:
```bash
# Common locations to check:
ls -la deploy.sh
ls -la scripts/
ls -la databricks.yml
cat package.json | grep scripts
```

### Step 2: Build the Application
Based on your project type:

**For React/Node.js frontend:**
```bash
npm install
npm run build
```

**For Python backend:**
```bash
pip install -r requirements.txt
```

### Step 3: Validate the Bundle (Pre-Deploy)
```bash
# Pre-flight validation catches ~80% of errors
databricks bundle validate -t dev
```
If validation fails, read the error, fix the YAML, and re-validate before proceeding.

### Step 4: Deploy Using Project Scripts
Use the deploy scripts found in your project:
```bash
# If deploy.sh exists:
./deploy.sh

# Or if using DAB:
databricks bundle deploy -t dev
```

### Step 5: Deploy DAB Artifacts
If you have Databricks Asset Bundles configured:
```bash
# Authenticate if needed
databricks auth login --host https://e2-demo-field-eng.cloud.databricks.com --profile DEFAULT

# Validate and deploy
databricks bundle validate
databricks bundle deploy -t dev

# Run jobs/pipelines (extract RUN_ID from output URL)
databricks bundle run <job_name> -t dev
```

### Step 6: Poll with Exponential Backoff
After triggering a job run, poll for completion:
```bash
# Poll job status (30s -> 60s -> 120s backoff)
databricks jobs get-run <RUN_ID> --output json | jq -r ''.state.life_cycle_state''
# PENDING -> RUNNING -> TERMINATED

# When TERMINATED, check result:
databricks jobs get-run <RUN_ID> --output json | jq -r ''.state.result_state''
# SUCCESS -> verify    FAILED -> diagnose
```

### Step 7: On Failure — Diagnose
```bash
# CRITICAL: Use TASK run_id, NOT parent job run_id
databricks jobs get-run <JOB_RUN_ID> --output json \
  | jq ''.tasks[] | select(.state.result_state == "FAILED") | {task: .task_key, run_id: .run_id, error: .state.state_message}''

# Get detailed output for each failed task
databricks jobs get-run-output <TASK_RUN_ID> --output json \
  | jq -r ''.notebook_output.result // .error // "No output"''
```

### Step 8: Self-Healing Loop (Fix -> Redeploy -> Re-Poll)
1. Read the source file(s) identified from the error
2. Apply the fix
3. Redeploy: `databricks bundle deploy -t dev`
4. Re-run: `databricks bundle run -t dev <job_name>`
5. Return to Step 6 (Poll)

**Maximum 3 iterations.** After 3 failed attempts, escalate to user with all errors, fixes attempted, and run page URLs.

### Step 9: Verify Deployment
Check deployment status:
```bash
# Check app status
databricks apps get <app-name>

# View logs
databricks apps get <app-name> --output json | jq .app_status

# For multi-task jobs, verify all tasks succeeded:
databricks jobs get-run <RUN_ID> --output json \
  | jq ''.tasks[] | {task: .task_key, result: .state.result_state}''
```

---

## Testing Checklist

After deployment, verify:

### Application Health
- [ ] App URL is accessible
- [ ] `/api/health` returns 200 OK
- [ ] No errors in application logs

### Frontend Functionality
- [ ] UI loads without JavaScript errors
- [ ] Navigation works correctly
- [ ] Forms submit successfully
- [ ] Data displays in tables and charts

### Backend Functionality
- [ ] API endpoints respond correctly
- [ ] Database connections work
- [ ] Authentication/authorization works

### Data Pipelines (if DAB deployed)
- [ ] Bronze jobs completed successfully
- [ ] Silver pipeline processed data
- [ ] Gold tables populated correctly
- [ ] Data visible in dashboards/Genie

---

## Debugging Failed Deployments

If deployment fails:
1. Check build logs for errors
2. Verify environment variables are set
3. Check Databricks workspace permissions
4. Review app.yaml configuration
5. Check network connectivity

```bash
# View deployment logs
databricks apps get <app-name>

# Check bundle deployment status
databricks bundle validate
databricks bundle deploy -t dev --verbose
```

---

## Post-Deployment: Document the Entire Repository

**After deployment succeeds**, run this prompt in a new AI assistant thread:

```
Document this entire repository using @data_product_accelerator/skills/admin/documentation-organization/SKILL.md

Use Framework Documentation Authoring mode to create a complete docs/ set:
- Architecture overview with diagrams
- Component deep dives for each major module
- Deployment guide
- Operations guide (health checks, monitoring, alerting)
- Troubleshooting guide (common errors and solutions)

Also run organizational enforcement:
- Audit root directory for stray .md files
- Move any misplaced docs to correct docs/ subdirectory
- Validate all naming uses kebab-case
```

This generates comprehensive project documentation under `docs/{project-name}-design/`.',
'Static prompt - no LLM processing required. This prompt is copied directly to the AI coding assistant.',
'Redeploy & Test Application',
'Use project deploy scripts and DAB to build, deploy, and test the complete application with self-healing operations and full repository documentation',
18,
'## 🔄 What is Redeploy and Test?

**Redeploy & Test** is not "deploy and pray" — it is a **systematic, self-healing operational loop** powered by the autonomous operations skill. Every deployment follows a disciplined cycle: validate, deploy, poll, diagnose, fix, and verify. After deployment succeeds, the **entire repository** is documented comprehensively.

### Two Skills Working Together

| Skill | Role | When It Activates |
|-------|------|-------------------|
| **Autonomous Operations** | Self-healing deploy loop with diagnostics | During deployment and troubleshooting |
| **Documentation Organization** | Full repository documentation authoring | After deployment succeeds (explicit prompt) |

### Core Principles

| Principle | Benefit |
|-----------|---------|
| **Self-Healing Loop** | Deploy -> Poll -> Diagnose -> Fix -> Redeploy (max 3 iterations) |
| **Pre-Deploy Validation** | `databricks bundle validate` catches ~80% of errors before deploy |
| **Exponential Backoff** | 30s -> 60s -> 120s polling prevents API rate limits |
| **Task-Level Diagnostics** | Get output from failed tasks, not just the parent job |
| **Documentation as Final Step** | Every project gets architecture, operations, and troubleshooting docs |

---

## 🏗️ Self-Healing Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    AUTONOMOUS DEPLOY-TEST-DOCUMENT LOOP                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────┐    ┌──────────┐    ┌──────────────┐    ┌──────────────┐     │
│  │ VALIDATE │───▶│  DEPLOY  │───▶│  POLL        │───▶│  RESULT?     │     │
│  │  Bundle  │    │  Bundle  │    │  (Backoff)   │    │              │     │
│  └──────────┘    └──────────┘    │  30s→60s→120s│    └──────┬───────┘     │
│       ▲                          └──────────────┘           │              │
│       │                                                     │              │
│       │            ┌────────────────────────────────────────┤              │
│       │            │                                        │              │
│       │            ▼                                        ▼              │
│       │     ┌──────────────┐                    ┌──────────────────┐      │
│       │     │    FAILED    │                    │    SUCCESS       │      │
│       │     │              │                    │                  │      │
│       │     │ ┌──────────┐ │                    │ ┌──────────────┐ │      │
│       │     │ │ Diagnose │ │                    │ │ Verify All   │ │      │
│       │     │ │ (task-   │ │                    │ │ Tasks + App  │ │      │
│       │     │ │  level)  │ │                    │ │ Health       │ │      │
│       │     │ └────┬─────┘ │                    │ └──────┬───────┘ │      │
│       │     │      │       │                    │        │         │      │
│       │     │      ▼       │                    │        ▼         │      │
│       │     │ ┌──────────┐ │                    │ ┌──────────────┐ │      │
│       │     │ │   Fix    │ │                    │ │ Document     │ │      │
│       │     │ │  Source  │ │                    │ │ Entire Repo  │ │      │
│       │     │ └────┬─────┘ │                    │ │ (Framework   │ │      │
│       │     │      │       │                    │ │  Authoring)  │ │      │
│       │     └──────┼───────┘                    │ └──────────────┘ │      │
│       │            │                            └──────────────────┘      │
│       │            │                                                      │
│       └────────────┘                                                      │
│       Redeploy (max 3 iterations)                                         │
│                                                                           │
│  After 3 failures ──▶ ESCALATE to user with all errors + run URLs        │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📖 Key Concepts

| Concept | Why It Matters |
|---------|----------------|
| **Self-Healing Loop** | Deploy -> Poll -> Diagnose -> Fix -> Redeploy (max 3 iterations before escalation) |
| **Exponential Backoff** | 30s -> 60s -> 120s polling intervals prevent API rate limits and reduce noise |
| **Task-Level Diagnostics** | `get-run-output` needs the **TASK** `run_id`, not the parent job `run_id` — critical for multi-task jobs |
| **Dependency Ordering** | Bronze -> Silver -> Gold -> Semantic -> Monitoring -> Alerts -> Genie |
| **Structured Notebook Exit** | `dbutils.notebook.exit(json.dumps({...}))` enables machine-parseable output retrieval |
| **Partial Success** | >=90% tasks succeeding = OK; fix individual failures without rerunning everything |
| **Full Repo Documentation** | Post-deployment step generates complete `docs/{project}-design/` with architecture, operations, troubleshooting |
| **Framework Doc Authoring** | 4-step workflow: Requirements Gathering -> File Structure -> Fill Templates -> Quality Validation |
| **Root Directory Hygiene** | Only README.md, QUICKSTART.md, CHANGELOG.md allowed in root; all other docs in `docs/` |
| **43-Item Quality Checklist** | Validates organization, naming, structure, content, usability, and maintenance of all documentation |

---

## Prerequisite

**Run this in your cloned Template Repository** (see Prerequisites in Step 0). These prompts assume you are working in that codebase with a coding assistant (Cursor or Copilot) enabled.

**Before this step, you should have completed:**
- Bronze, Silver, and Gold layer setup (tables populated)
- Semantic layer (Metric Views, TVFs, Genie Space)
- Any application code (frontend/backend)
- DAB configuration (`databricks.yml`)

---

## Steps to Apply

### Step 1: Analyze Project
```
@codebase What deploy scripts and configurations exist? How do I build and deploy?
```

### Step 2: Build Application
```bash
npm install && npm run build  # or equivalent for your project
pip install -r requirements.txt  # if Python backend
```

### Step 3: Validate Bundle (Pre-Deploy)
```bash
databricks bundle validate -t dev
# Catches ~80% of errors — fix any issues before proceeding
```

### Step 4: Deploy Using Project Scripts
```bash
./deploy.sh  # or your project''''s deploy script
# Or: databricks bundle deploy -t dev
```

### Step 5: Deploy DAB Artifacts
```bash
databricks bundle deploy -t dev
databricks bundle run <job_name> -t dev
# Extract RUN_ID from the output URL
```

### Step 6: Poll with Exponential Backoff
```bash
# Poll: 30s -> 60s -> 120s intervals
databricks jobs get-run <RUN_ID> --output json | jq -r ''.state.life_cycle_state''
# When TERMINATED: check .state.result_state
```

### Step 7: On Failure — Diagnose and Fix
```bash
# Get failed tasks (use TASK run_id, not parent)
databricks jobs get-run <RUN_ID> --output json \
  | jq ''.tasks[] | select(.state.result_state == "FAILED") | {task: .task_key, run_id: .run_id}''

# Get task output
databricks jobs get-run-output <TASK_RUN_ID> --output json \
  | jq -r ''.notebook_output.result // .error // "No output"''

# Fix -> Redeploy -> Re-poll (max 3 iterations)
```

### Step 8: Verify All Tasks and Application Health
```bash
# Verify all tasks succeeded
databricks jobs get-run <RUN_ID> --output json \
  | jq ''.tasks[] | {task: .task_key, result: .state.result_state}''

# Check app health
curl -s https://<app-url>/api/health
databricks apps get <app-name> --output json | jq .app_status
```

### Step 9: Run Testing Checklist
- Application health (URL accessible, health endpoint OK)
- Frontend functionality (UI loads, navigation, forms, data display)
- Backend functionality (API endpoints, database, auth)
- Data pipelines (Bronze, Silver, Gold, dashboards, Genie)

### Step 10: Document the Entire Repository
After deployment succeeds, paste this prompt in a **new AI assistant thread**:

```
Document this entire repository using @data_product_accelerator/skills/admin/documentation-organization/SKILL.md

Use Framework Documentation Authoring mode to create a complete docs/ set:
- Architecture overview with diagrams
- Component deep dives for each major module
- Deployment guide
- Operations guide (health checks, monitoring, alerting)
- Troubleshooting guide (common errors and solutions)

Also run organizational enforcement:
- Audit root directory for stray .md files
- Move any misplaced docs to correct docs/ subdirectory
- Validate all naming uses kebab-case
```

This triggers the documentation-organization skill''''s **Mode 2: Framework Documentation Authoring** which:
1. Gathers requirements (framework name, audience, tech stack, components)
2. Generates numbered docs under `docs/{project-name}-design/`
3. Fills templates (index, introduction, architecture, components, implementation, operations, troubleshooting)
4. Validates against the 43-item quality checklist

---

## 🔧 What Happens Behind the Scenes

When you paste the deployment prompt, the AI reads `@data_product_accelerator/skills/common/databricks-autonomous-operations/SKILL.md` — the **autonomous operations skill**. Behind the scenes:

### Autonomous Operations Skill

1. **Bundle Discovery** — reads `databricks.yml` to identify all resources (jobs, pipelines, dashboards, alerts)
2. **Pre-Deploy Validation** — runs `databricks bundle validate` which catches ~80% of errors before deployment
3. **Deploy and Extract** — deploys bundle and extracts RUN_ID from the output URL
4. **Exponential Backoff Polling** — polls job status at 30s -> 60s -> 120s intervals until terminal state
5. **On Failure: Task-Level Diagnosis** — extracts task-level run_ids (NOT parent job run_id), gets detailed output via `get-run-output`, matches errors against the error-solution matrix
6. **Self-Healing Loop** — applies fix, redeploys, re-polls (max 3 iterations before escalation)
7. **On Success: Full Verification** — verifies all tasks succeeded, retrieves structured JSON output from notebooks
8. **Common skills auto-loaded**:
   - `databricks-asset-bundles` — DAB validation and deployment patterns
   - `databricks-expert-agent` — core Databricks best practices
   - `naming-tagging-standards` — enterprise naming conventions

### Documentation Organization Skill (Explicit Post-Deployment Trigger)

After deployment succeeds, the user runs a **separate prompt** that triggers the documentation-organization skill''''s **Framework Documentation Authoring mode (Mode 2)** to document the entire repository:

1. **Requirements Gathering** — skill determines framework name, audience, tech stack, component count, and documentation depth
2. **File Structure Generation** — creates numbered docs under `docs/{project-name}-design/`:
   - `00-index.md` — document index with architecture summary and quick start
   - `01-introduction.md` — purpose, scope, prerequisites, success criteria
   - `02-architecture-overview.md` — Mermaid/ASCII diagrams, data flows, component inventory
   - `03-{component-1}.md` through `NN-{component-N}.md` — component deep dives
   - `{N+1}-implementation-guide.md` — phased steps with validation
   - `{N+2}-operations-guide.md` — health checks, alerting, escalation matrix
   - `appendices/A-code-examples.md`, `B-troubleshooting.md`, `C-references.md`
3. **Quality Validation** — runs 43-item checklist (organization, naming, structure, content, usability, maintenance, special cases)
4. **Organizational Enforcement** — audits root for stray `.md` files, enforces `kebab-case` naming, routes misplaced docs to correct `docs/` subdirectory

### 🏅 Databricks Best Practices Applied

| Practice | How It''''s Used Here |
|----------|-------------------|
| **Self-Healing Deploy Loop** | Max 3 iterations of deploy-diagnose-fix before escalation to user |
| **Exponential Backoff Polling** | 30s -> 60s -> 120s intervals prevent API rate limiting and reduce noise |
| **Task-Level Diagnostics** | Uses **task** `run_id` (not parent job `run_id`) for `get-run-output` — critical for multi-task jobs |
| **Structured Notebook Exit** | JSON output from `dbutils.notebook.exit()` enables machine-parseable result retrieval |
| **Pre-Deploy Validation** | `databricks bundle validate` catches ~80% of errors before any deployment attempt |
| **Dependency-Aware Ordering** | Follows Bronze -> Gold -> Semantic -> Monitoring -> Genie deployment order |
| **Partial Success Handling** | >=90% task success = OK; debug individual failures without rerunning everything |
| **CLI jq Patterns** | Structured JSON parsing for job state, failed tasks, and task output |
| **App Health Verification** | `/api/health` endpoint check + app logs review after deployment |
| **Never Retry Destructive Ops** | No auto-retry of `bundle destroy`, `DROP TABLE`, `DELETE` monitors/alerts |
| **Full Repository Documentation** | Post-deployment prompt triggers Framework Documentation Authoring for entire repo |
| **Numbered Documentation Set** | `docs/{project-name}-design/` with `00-index.md` through `NN-operations-guide.md` |
| **Root Directory Hygiene** | Only README/QUICKSTART/CHANGELOG in root; all other docs in `docs/` hierarchy |
| **Quality Checklist Validation** | 43-item checklist covering organization, naming, structure, content, usability |

---

## ⚠️ Error Troubleshooting Quick Reference

If deployment or jobs fail, check this table first:

| Error | Quick Fix |
|-------|-----------|
| `ModuleNotFoundError` | Add to `%pip install` or DAB environment spec |
| `TABLE_OR_VIEW_NOT_FOUND` | Run setup job first; check 3-part catalog.schema.table path |
| `DELTA_MULTIPLE_SOURCE_ROW_MATCHING` | Deduplicate source before MERGE |
| `Invalid access token (403)` | `databricks auth login --host <url> --profile <name>` |
| `ResourceAlreadyExists` | Delete + recreate (monitors, alerts) |
| `python_task not recognized` | Use `notebook_task` with `notebook_path` |
| `PARSE_SYNTAX_ERROR` | Read failing SQL file, fix syntax, redeploy |
| `Parameter not found` | Use `base_parameters` dict, not CLI-style `parameters` |
| `run_job_task` vs `job_task` | Use `run_job_task` (not `job_task`) |
| Genie `INTERNAL_ERROR` | Deploy semantic layer (TVFs + Metric Views) first |

---

## 📂 Post-Deployment: Document the Entire Repository

After deployment succeeds, run the documentation-organization skill to create comprehensive project documentation.

### The Documentation Prompt

Paste this in a **new AI assistant thread** after deployment:

```
Document this entire repository using @data_product_accelerator/skills/admin/documentation-organization/SKILL.md

Use Framework Documentation Authoring mode to create a complete docs/ set:
- Architecture overview with diagrams
- Component deep dives for each major module
- Deployment guide
- Operations guide (health checks, monitoring, alerting)
- Troubleshooting guide (common errors and solutions)

Also run organizational enforcement:
- Audit root directory for stray .md files
- Move any misplaced docs to correct docs/ subdirectory
- Validate all naming uses kebab-case
```

### Expected Documentation Structure

```
docs/{project-name}-design/
├── 00-index.md                        # Document index, architecture summary
├── 01-introduction.md                 # Purpose, scope, prerequisites
├── 02-architecture-overview.md        # Diagrams, data flows, components
├── 03-{component-1}.md               # Component deep dive
├── 04-{component-2}.md               # Component deep dive
├── ...                                # Additional components
├── {N}-implementation-guide.md        # Phased steps with validation
├── {N+1}-operations-guide.md          # Health checks, alerting, escalation
└── appendices/
    ├── A-code-examples.md             # Code snippets and patterns
    ├── B-troubleshooting.md           # Error-solution matrix
    └── C-references.md                # External references and links
```

### Documentation Naming Rules

| Format | Use For | Example |
|--------|---------|---------|
| `kebab-case.md` | All docs | `deployment-guide.md` |
| `NN-descriptive-name.md` | Framework docs (numbered) | `03-data-pipelines.md` |
| `YYYY-MM-DD-description.md` | Historical/dated records | `2026-02-07-initial-deployment.md` |
| NEVER `PascalCase.md` | -- | `DeploymentGuide.md` |
| NEVER `ALL_CAPS.md` | -- | `DEPLOYMENT_GUIDE.md` |

### 4-Step Documentation Workflow

| Step | What Happens | Output |
|------|-------------|--------|
| 1. Requirements Gathering | Skill asks about framework, audience, components, depth | Requirements table |
| 2. File Structure | Creates numbered file tree under `docs/` | Directory structure |
| 3. Fill Templates | Generates each doc from fill-in-the-blank templates | Complete documentation |
| 4. Quality Validation | Runs 43-item checklist across 7 categories | Validation report |',
'## Expected Deliverables

### 🔄 Deployment Process (Self-Healing Loop)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      SELF-HEALING DEPLOYMENT LOOP                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Iteration 1: Deploy → Run → Poll → [FAIL] → Diagnose → Fix → Redeploy   │
│  Iteration 2: Run → Poll → [FAIL] → Diagnose → Fix → Redeploy             │
│  Iteration 3: Run → Poll → [FAIL] → ESCALATE TO USER                      │
│                                                                             │
│  OR: Deploy → Run → Poll → [SUCCESS] → Verify → Document Repo             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Self-Healing Loop Tracking

| Iteration | Error | Fix Applied | Outcome |
|-----------|-------|-------------|---------|
| 1 | (recorded from diagnosis) | (what was changed) | FAIL / SUCCESS |
| 2 | (recorded from diagnosis) | (what was changed) | FAIL / SUCCESS |
| 3 | (recorded from diagnosis) | (what was changed) | FAIL / ESCALATE |

---

### 📊 Deployment Verification Commands

```bash
# 1. Check overall job status
databricks jobs get-run <RUN_ID> --output json | jq ''.state''

# 2. Get summary of all tasks
databricks jobs get-run <RUN_ID> --output json \
  | jq ''.tasks[] | {task: .task_key, run_id: .run_id, result: .state.result_state}''

# 3. Get failed tasks only
databricks jobs get-run <RUN_ID> --output json \
  | jq ''.tasks[] | select(.state.result_state == "FAILED") | {task: .task_key, error: .state.state_message, url: .run_page_url}''

# 4. Get task output (MUST use TASK run_id, not parent job run_id)
databricks jobs get-run-output <TASK_RUN_ID> --output json \
  | jq -r ''.notebook_output.result // "No output"''

# 5. Check app status
databricks apps get <app-name>
databricks apps get <app-name> --output json | jq .app_status

# 6. Check bundle status
databricks bundle validate
databricks bundle summary
```

---

### ✅ Application Health Checks

**Application:**
- [ ] App deployed and accessible at URL
- [ ] Health endpoint (`/api/health`) returns 200 OK
- [ ] UI loads without JavaScript errors
- [ ] Navigation works correctly
- [ ] Forms submit successfully
- [ ] Data displays in tables and charts
- [ ] Authentication/authorization working
- [ ] API endpoints respond correctly
- [ ] Database connections working
- [ ] No errors in application logs

**DAB Artifacts (if deployed):**
- [ ] All jobs visible in Workflows UI
- [ ] All job tasks completed with `SUCCESS` result state
- [ ] Pipelines running successfully
- [ ] Tables created in Unity Catalog
- [ ] Data flowing correctly through Bronze -> Silver -> Gold
- [ ] Data visible in dashboards/Genie

---

### 📂 Repository Documentation Set Created

After running the documentation-organization prompt, the following structure is generated:

```
docs/{project-name}-design/
├── 00-index.md                        # Document index
├── 01-introduction.md                 # Purpose, scope, prerequisites
├── 02-architecture-overview.md        # Diagrams, data flows
├── 03-{component-1}.md               # Component deep dive
├── ...                                # Additional components
├── {N}-implementation-guide.md        # Build instructions
├── {N+1}-operations-guide.md          # Health checks, alerting
└── appendices/
    ├── A-code-examples.md             # Code patterns
    ├── B-troubleshooting.md           # Error-solution matrix
    └── C-references.md                # External references
```

**Organizational Enforcement Results:**
- [ ] Root directory audited (only README, QUICKSTART, CHANGELOG remain)
- [ ] All doc filenames use `kebab-case`
- [ ] Numbered sequence for framework docs (00-, 01-, 02-, ...)
- [ ] No misplaced `.md` files in root or wrong subdirectories

---

### ✅ Success Criteria Checklist

**Bundle Deployment:**
- [ ] `databricks bundle validate` passes with no errors
- [ ] `databricks bundle deploy` completes successfully
- [ ] All resources deployed to target workspace

**Job Execution and Monitoring:**
- [ ] Jobs triggered and RUN_ID captured
- [ ] Polling with exponential backoff (30s -> 60s -> 120s)
- [ ] All tasks reached terminal state (SUCCESS)
- [ ] Task output retrieved via `get-run-output` using task run_id

**Application Health:**
- [ ] App URL is accessible
- [ ] `/api/health` returns 200 OK
- [ ] UI loads without errors
- [ ] API endpoints respond correctly
- [ ] No errors in application logs

**Self-Healing Loop:**
- [ ] If failures occurred: diagnosed using task-level CLI commands
- [ ] If failures occurred: fix applied and redeployed (max 3 iterations)
- [ ] If escalated: all errors, fixes, and run URLs provided to user

**Data Pipeline Verification:**
- [ ] Bronze tables populated with data
- [ ] Silver pipeline processed without errors
- [ ] Gold tables reflect correct aggregations
- [ ] Dashboards and Genie Spaces functional

**Repository Documentation:**
- [ ] `docs/{project-name}-design/` directory exists with numbered docs
- [ ] Architecture overview includes diagrams (Mermaid or ASCII)
- [ ] Component deep dives cover each major module
- [ ] Operations guide includes health checks and alerting procedures
- [ ] Troubleshooting guide includes common errors and solutions
- [ ] No stray `.md` files in root (only README, QUICKSTART, CHANGELOG)
- [ ] All doc filenames use `kebab-case`
- [ ] 43-item quality checklist passed',
true, 1, true, current_timestamp(), current_timestamp(), current_user());
