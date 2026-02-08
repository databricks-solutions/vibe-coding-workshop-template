# 07 — Implementation Guide

## Overview

This guide walks you through building a complete Databricks data platform from zero using the Data Product Accelerator. Each phase maps to one or more pipeline stages and requires a single Cursor Agent conversation.

## Prerequisites

- [ ] Databricks workspace with Unity Catalog enabled
- [ ] Cursor IDE installed with Agent mode enabled
- [ ] Databricks CLI v0.200+ installed and configured (`databricks auth login`)
- [ ] Repository cloned locally
- [ ] Customer schema CSV placed in `context/` directory

## Phase 1: Gold Layer Design (2-3 hours)

### Step 1.1: Place the Schema CSV

Drop the customer's source schema CSV into the `context/` directory:

```
context/
└── Wanderbricks_Schema.csv    ← your file here
```

Expected columns: `table_catalog`, `table_schema`, `table_name`, `column_name`, `ordinal_position`, `full_data_type`, `is_nullable`, `comment`

### Step 1.2: Design the Gold Layer

Open a new Cursor Agent conversation and enter:

```
I have a customer schema at @context/Wanderbricks_Schema.csv. Please design the Gold layer using @skills/gold/00-gold-layer-design/SKILL.md
```

**Expected Result:** The agent will:
1. Parse the CSV into a table inventory
2. Classify tables as dimensions vs facts
3. Create Mermaid ERD diagrams
4. Generate YAML schema files in `gold_layer_design/yaml/`
5. Document column lineage and business onboarding

**Validation:**
```
Verify gold_layer_design/yaml/ contains YAML files for each Gold table
Verify each YAML has table_name, columns, primary_key, and foreign_keys
Verify ERD diagrams render correctly in Markdown preview
```

---

## Phase 2: Bronze Layer Setup (2-3 hours)

### Step 2.1: Create Bronze Tables and Data

Open a **new** Cursor Agent conversation:

```
Set up the Bronze layer using @skills/bronze/00-bronze-layer-setup/SKILL.md with Approach A — generate Faker data matching the source schema.
```

For real data instead of Faker, use Approach B (existing tables) or C (copy from source).

**Expected Result:**
- Bronze table DDLs with governance metadata
- Faker data generation notebook
- Asset Bundle job configuration

### Step 2.2: Deploy and Validate

```bash
databricks bundle deploy -t dev
databricks bundle run bronze_setup_job -t dev
```

**Validation:**
```sql
-- Verify tables exist with data
SELECT COUNT(*) FROM {catalog}.bronze.{table_name};

-- Verify CDF is enabled
DESCRIBE DETAIL {catalog}.bronze.{table_name};
```

---

## Phase 3: Silver Layer Setup (2-4 hours)

### Step 3.1: Create DLT Pipelines

Open a **new** Cursor Agent conversation:

```
Set up the Silver layer using @skills/silver/00-silver-layer-setup/SKILL.md
```

**Expected Result:**
- DLT pipeline notebooks with streaming ingestion
- Data quality expectations (Delta table-based)
- Quarantine patterns for invalid records

### Step 3.2: Deploy and Validate

```bash
databricks bundle deploy -t dev
# DLT pipelines are triggered by the Asset Bundle
```

**Validation:**
```sql
-- Verify Silver tables populated
SELECT COUNT(*) FROM {catalog}.silver.{table_name};

-- Check DQ expectations table
SELECT * FROM {catalog}.silver.dq_expectations LIMIT 10;
```

---

## Phase 4: Gold Layer Implementation (3-4 hours)

### Step 4.1: Create Gold Tables and Merge Scripts

Open a **new** Cursor Agent conversation:

```
Implement the Gold layer using @skills/gold/01-gold-layer-setup/SKILL.md
```

**Expected Result:**
- Gold table creation scripts (from YAML schemas)
- Silver-to-Gold MERGE notebooks (SCD Type 1/2 dimensions, fact tables)
- FK constraint application scripts
- Asset Bundle job configuration

### Step 4.2: Deploy and Validate

```bash
databricks bundle deploy -t dev
databricks bundle run gold_setup_job -t dev
databricks bundle run gold_merge_job -t dev
databricks bundle run gold_fk_constraints_job -t dev
```

**Validation:**
```sql
-- Verify Gold tables with constraints
DESCRIBE EXTENDED {catalog}.gold.dim_{entity};
SHOW CONSTRAINTS ON {catalog}.gold.fact_{entity};
```

---

## Phase 5: Project Planning (2-4 hours)

### Step 5.1: Generate Phase Plans

Open a **new** Cursor Agent conversation:

```
Perform project planning using @skills/planning/00-project-planning/SKILL.md
```

The agent will ask interactive questions about which domains and addendums to include.

**Expected Result:**
- Phase plan documents in `plans/`
- YAML manifest files in `plans/manifests/`

---

## Phase 6: Semantic Layer (3-5 hours)

### Step 6.1: Build Metric Views, TVFs, and Genie Spaces

Open a **new** Cursor Agent conversation:

```
Set up the semantic layer using @skills/semantic-layer/00-semantic-layer-setup/SKILL.md
```

**Expected Result:**
- Metric View YAML definitions and SQL creation scripts
- TVFs optimized for Genie
- Genie Space configuration with agent instructions

---

## Phase 7: Observability (3-5 hours)

### Step 7.1: Set Up Monitoring, Dashboards, and Alerts

Open a **new** Cursor Agent conversation:

```
Set up observability using @skills/monitoring/00-observability-setup/SKILL.md
```

**Expected Result:**
- Lakehouse Monitors with custom business metrics
- AI/BI Dashboard JSON definitions
- SQL Alert configurations

---

## Phase 8: ML Pipeline (6-12 hours, optional)

```
Set up the ML pipeline using @skills/ml/00-ml-pipeline-setup/SKILL.md
```

---

## Phase 9: GenAI Agents (8-16 hours, optional)

```
Set up GenAI agents using @skills/genai-agents/00-genai-agents-setup/SKILL.md
```

---

## Post-Implementation Validation

### Validation Checklist

- [ ] All Bronze tables have CDF enabled and governance metadata
- [ ] All Silver tables have DLT expectations and streaming ingestion
- [ ] All Gold tables have PK/FK constraints and rich descriptions
- [ ] Metric Views answer natural language queries via Genie
- [ ] Lakehouse Monitors report custom business metrics
- [ ] All resources deployed via Asset Bundles (`databricks bundle deploy`)
- [ ] No hardcoded table/column names in generated code

### Smoke Tests

```bash
# Verify all bundle resources deployed
databricks bundle validate -t dev

# Run a Gold merge job
databricks bundle run gold_merge_job -t dev

# Check Genie Space accuracy (if stage 6 completed)
# Use Genie Conversation API benchmark
```

## Rollback Procedures

### Quick Rollback (Single Job)

```bash
# Re-deploy previous bundle version
git checkout HEAD~1 -- databricks.yml src/
databricks bundle deploy -t dev
```

### Full Rollback (All Layers)

1. Drop Gold tables: `DROP TABLE IF EXISTS {catalog}.gold.{table_name}`
2. Drop Silver tables (DLT manages these — delete the pipeline)
3. Drop Bronze tables: `DROP TABLE IF EXISTS {catalog}.bronze.{table_name}`
4. Re-deploy from a known-good git commit

## Time Estimates

| Phase | Duration | Cumulative |
|-------|----------|------------|
| Phase 1: Gold Design | 2-3 hours | 2-3 hours |
| Phase 2: Bronze Setup | 2-3 hours | 4-6 hours |
| Phase 3: Silver Setup | 2-4 hours | 6-10 hours |
| Phase 4: Gold Implementation | 3-4 hours | 9-14 hours |
| Phase 5: Planning | 2-4 hours | 11-18 hours |
| Phase 6: Semantic Layer | 3-5 hours | 14-23 hours |
| Phase 7: Observability | 3-5 hours | 17-28 hours |
| Phase 8: ML Pipeline | 6-12 hours | 23-40 hours |
| Phase 9: GenAI Agents | 8-16 hours | 31-56 hours |
| **Core (Phases 1-7)** | **17-28 hours** | |
| **Full Stack** | **31-56 hours** | |
