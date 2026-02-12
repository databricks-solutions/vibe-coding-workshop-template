# Quickstart: Data Product Accelerator

This guide walks you through building a complete Databricks data platform — from a raw schema CSV to production GenAI agents — using one prompt per stage.

> **See also:** [AGENTS.md](AGENTS.md) (routing table for AI agents) | [README.md](README.md) (project overview) | [Skill Navigator](skills/skill-navigator/SKILL.md) (full routing system)

---

## Prerequisites

- AI coding assistant with file reference support (Cursor, Claude Code, Windsurf, Copilot, Codex, etc.)
- A Databricks workspace with Unity Catalog
- A schema CSV exported from the customer's source system

> **File references:** The prompts below use `@` to reference files (supported by Cursor, Windsurf, and others). If your IDE doesn't support `@`, ask the agent to "read the file at [path]" instead.

---

## Step 0: Place Your Schema CSV

Drop the customer's schema CSV into the `data_product_accelerator/context/` directory:

```
data_product_accelerator/
└── context/
    └── Wanderbricks_Schema.csv    ← your file here
```

Expected CSV columns: `table_catalog`, `table_schema`, `table_name`, `column_name`, `ordinal_position`, `full_data_type`, `is_nullable`, `comment`

> **Where do generated artifacts go?** All artifacts created by skills (`gold_layer_design/`, `src/`, `plans/`, `resources/`, `databricks.yml`) are placed at the **repository root**, not inside `data_product_accelerator/`. See the [Project Layout](AGENTS.md#project-layout) in AGENTS.md for the full directory map.

---

## Step 1: Gold Layer Design

Design the target dimensional model first — ERDs, YAML schemas, and documentation.

**Prompt:**

```
I have a customer schema at @data_product_accelerator/context/Wanderbricks_Schema.csv. Please design the Gold layer using @data_product_accelerator/skills/gold/00-gold-layer-design/SKILL.md
```

**What it produces** (at the repo root):
- Schema intake report (table inventory, dimension/fact classification, FK relationships)
- Mermaid ERD diagrams
- YAML schema files in `gold_layer_design/yaml/`
- Business onboarding guide
- Column lineage and source table mapping

---

## Step 2: Bronze Layer Setup

Create Bronze tables and populate them with data. Three approaches available:

**Approach A — Schema CSV + Faker (recommended for demos):**

```
Set up the Bronze layer using @data_product_accelerator/skills/bronze/00-bronze-layer-setup/SKILL.md with Approach A — generate Faker data matching the source schema.
```

**Approach B — Existing tables (data already in Databricks):**

```
Set up the Bronze layer using @data_product_accelerator/skills/bronze/00-bronze-layer-setup/SKILL.md with Approach B — read from existing tables in the wanderbricks schema.
```

**Approach C — Copy from source:**

```
Set up the Bronze layer using @data_product_accelerator/skills/bronze/00-bronze-layer-setup/SKILL.md with Approach C — copy data from the existing source tables in the wanderbricks schema.
```

**What it produces:**
- Bronze table DDLs with TBLPROPERTIES, CDF, and governance metadata
- Data generation or copy notebooks
- Asset Bundle job configuration

---

## Step 3: Silver Layer Setup

Create DLT pipelines with data quality expectations.

**Prompt:**

```
Set up the Silver layer using @data_product_accelerator/skills/silver/00-silver-layer-setup/SKILL.md
```

**What it produces:**
- DLT pipeline notebooks with streaming ingestion
- Data quality expectations (stored in Unity Catalog Delta table)
- Quarantine patterns for failed records
- Asset Bundle pipeline configuration

---

## Step 4: Gold Layer Implementation

Create the Gold tables, merge scripts, and FK constraints from the YAML designs.

**Prompt:**

```
Implement the Gold layer using @data_product_accelerator/skills/gold/01-gold-layer-setup/SKILL.md
```

**What it produces:**
- Gold table creation scripts (from YAML schemas)
- Silver-to-Gold MERGE notebooks (SCD Type 1/2 dimensions, fact tables)
- FK constraint application scripts
- Asset Bundle job configuration

---

## Step 5: Project Planning

Plan the semantic layer, observability, ML, and GenAI phases. This stage asks you interactive questions about which domains and addendums to include.

**Prompt (Data Product Acceleration — default):**

```
Perform project planning using @data_product_accelerator/skills/planning/00-project-planning/SKILL.md
```

**Prompt (Workshop mode — for Learning & Enablement):**

```
Perform project planning using @data_product_accelerator/skills/planning/00-project-planning/SKILL.md with planning_mode: workshop
```

> **Workshop mode** produces a minimal representative plan (3-5 TVFs, 1-2 Metric Views, 1 Genie Space) designed for hands-on workshops. It is only activated when `planning_mode: workshop` is explicitly included. See `data_product_accelerator/skills/planning/00-project-planning/references/workshop-mode-profile.md` for details.

**What it produces:**
- Phase plan documents (TVFs, Metric Views, Monitoring, Dashboards, Genie Spaces, ML, Alerting)
- YAML manifest files in `plans/manifests/` (contracts for downstream stages)
- Prerequisites summary

---

## Step 6: Semantic Layer Setup

Create Metric Views, Table-Valued Functions, and Genie Spaces.

**Prompt:**

```
Set up the semantic layer using @data_product_accelerator/skills/semantic-layer/00-semantic-layer-setup/SKILL.md
```

**What it produces:**
- Metric View YAML definitions and SQL creation scripts
- TVFs optimized for Genie (STRING parameters, null safety)
- Genie Space configuration with agent instructions and benchmark questions
- Asset Bundle deployment

---

## Step 7: Observability Setup

Set up Lakehouse Monitors, AI/BI Dashboards, and SQL Alerts.

**Prompt:**

```
Set up observability using @data_product_accelerator/skills/monitoring/00-observability-setup/SKILL.md
```

**What it produces:**
- Lakehouse Monitors with custom business metrics
- AI/BI Dashboard JSON definitions
- SQL Alert configurations with severity-based routing
- Asset Bundle deployment

---

## Step 8: ML Pipeline Setup

Create ML experiments, model training, and batch inference.

**Prompt:**

```
Set up the ML pipeline using @data_product_accelerator/skills/ml/00-ml-pipeline-setup/SKILL.md
```

**What it produces:**
- MLflow experiment notebooks
- Model training with Feature Store integration
- Batch inference jobs
- Unity Catalog model registration

---

## Step 9: GenAI Agents Setup

Build AI agents with Genie Space integration, evaluation, and deployment.

**Prompt:**

```
Set up GenAI agents using @data_product_accelerator/skills/genai-agents/00-genai-agents-setup/SKILL.md
```

**What it produces:**
- ResponsesAgent implementation with streaming
- Multi-agent Genie Space orchestration
- Evaluation pipelines with LLM judges
- Model Serving deployment configuration

---

## Tips

- **One prompt per stage.** Each orchestrator skill handles the full workflow for its stage.
- **New conversation per stage.** Start a fresh agent conversation for each stage to keep context clean.
- **The skill does the thinking.** You don't need to specify details — the orchestrator reads its worker skills, common skills, and your existing artifacts automatically.
- **If something fails,** the `databricks-autonomous-operations` common skill kicks in for troubleshooting (Deploy → Poll → Diagnose → Fix → Redeploy).

---

## Pipeline at a Glance

```
data_product_accelerator/context/*.csv
  → Gold Design (1)      — dimensional model, ERDs, YAML schemas
  → Bronze (2)           — source tables + test data
  → Silver (3)           — DLT pipelines + data quality
  → Gold Impl (4)        — tables, merges, constraints
  → Planning (5)         — phase plans + manifest contracts
  → Semantic (6)         — Metric Views, TVFs, Genie Spaces
  → Observability (7)    — monitors, dashboards, alerts
  → ML (8)               — experiments, training, inference
  → GenAI Agents (9)     — agents, evaluation, deployment
```
