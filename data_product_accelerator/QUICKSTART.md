# Quickstart: Data Product Accelerator

This guide walks you through building a complete Databricks data platform — from a raw schema CSV to production GenAI agents — using one prompt per stage, plus an optional Stage 6b optimization loop.

> **See also:** [AGENTS.md](AGENTS.md) (routing table for AI agents) | [README.md](README.md) (project overview) | [Skill Navigator](skills/skill-navigator/SKILL.md) (full routing system)
>
> **Advanced:** See [Parallel Execution Guide](docs/framework-design/09-parallel-execution-guide.md) to run independent stages concurrently and reduce total wall-clock time by 30-40%.

---

## Prerequisites

- AI coding assistant with file reference support (Cursor, Claude Code, Windsurf, Copilot, Codex, etc.)
- A Databricks workspace with Unity Catalog
- A schema CSV exported from the customer's source system
- Databricks CLI v0.200+ installed and authenticated (`databricks auth login`)

> **File references:** The prompts below use `@` to reference files (supported by Cursor, Windsurf, and others). If your IDE doesn't support `@`, ask the agent to "read the file at [path]" instead.

---

## Step 0: Place Your Schema CSV

Drop the customer's schema CSV into the `data_product_accelerator/context/` directory:

```
data_product_accelerator/
└── context/
    └── user_name_schema.csv       ← your file here
```

Expected CSV columns: `table_catalog`, `table_schema`, `table_name`, `column_name`, `ordinal_position`, `full_data_type`, `is_nullable`, `comment`

> **Where do generated artifacts go?** All artifacts created by skills (`gold_layer_design/`, `src/`, `plans/`, `resources/`, `databricks.yml`) are placed at the **repository root**, not inside `data_product_accelerator/`. See the [Project Layout](AGENTS.md#project-layout) in AGENTS.md for the full directory map.

---

## Step 1: Gold Layer Design

Design the target dimensional model first — ERDs, YAML schemas, and documentation.

**Prompt:**

```
I have a customer schema at @data_product_accelerator/context/user_name_schema.csv.

Please design the Gold layer using @data_product_accelerator/skills/gold/00-gold-layer-design/SKILL.md

This skill will orchestrate the following end-to-end design workflow:

- **Parse the schema CSV** — read the source schema file, classify each table as a dimension, fact, or bridge, and infer foreign key relationships from column names and comments
- **Design the dimensional model** — identify dimensions (with SCD Type 1/2 decisions), fact tables (with explicit grain definitions), and measures, then assign tables to business domains
- **Create ERD diagrams** — generate Mermaid Entity-Relationship Diagrams organized by table count (master ERD always, plus domain and summary ERDs for larger schemas)
- **Generate YAML schema files** — produce one YAML file per Gold table with column definitions, PK/FK constraints, table properties, lineage metadata, and dual-purpose descriptions (human + LLM readable)
- **Document column-level lineage** — trace every Gold column back through Silver to Bronze with transformation type (DIRECT_COPY, AGGREGATION, DERIVATION, etc.) in both CSV and Markdown formats
- **Create business documentation** — write a Business Onboarding Guide with domain context, real-world scenarios, and role-based getting-started guides
- **Map source tables** — produce a Source Table Mapping CSV documenting which source tables are included, excluded, or planned with rationale for each
- **Validate design consistency** — cross-check YAML schemas, ERD diagrams, and lineage CSV to ensure all columns, relationships, and constraints are consistent

The orchestrator skill will automatically load its worker skills for merge patterns, deduplication, documentation standards, Mermaid ERDs, schema validation, grain validation, and YAML-driven setup.
```

**What it produces** (at the repo root):
- Schema intake report (table inventory, dimension/fact classification, FK relationships)
- Mermaid ERD diagrams
- YAML schema files in `gold_layer_design/yaml/`
- Business onboarding guide
- Column lineage and source table mapping

> **Deep dive:** See [Gold Design Orchestrator Walkthrough](docs/framework-design/13-gold-design-orchestrator-walkthrough.md) for a detailed explanation of how the orchestrator progressively loads worker skills and manages context.

---

## Step 2: Bronze Layer Setup

Create Bronze tables and populate them with data. Three approaches available:

**Approach A — Schema CSV + Faker (recommended for demos):**

```
Set up the Bronze layer using @data_product_accelerator/skills/bronze/00-bronze-layer-setup/SKILL.md with Approach A — generate Faker data matching the source schema at @data_product_accelerator/context/user_name_schema.csv.

This will involve the following steps:

- **Create Bronze table DDLs** — generate CREATE TABLE statements matching the source schema with proper data types, nullability, and column COMMENTs
- **Generate synthetic data** — use the Python Faker library to produce realistic test data for each table, maintaining referential integrity across foreign key relationships
- **Apply enterprise table properties** — enable Change Data Feed (CDF), Liquid Clustering (CLUSTER BY AUTO), auto-optimize, and auto-compact on every table
- **Create Asset Bundle job** — generate a repeatable, version-controlled deployment job (databricks.yml + data generation notebooks)
- **Deploy and run** — validate, deploy the bundle, and execute the data generation job to populate Bronze tables
```

**Approach B — Existing tables (data already in Databricks):**

```
Set up the Bronze layer using @data_product_accelerator/skills/bronze/00-bronze-layer-setup/SKILL.md with Approach B — read from existing tables in the wanderbricks schema.

This will involve the following steps:

- **Discover existing tables** — enumerate tables in the source wanderbricks schema and map columns to Bronze table definitions
- **Create Bronze table DDLs** — generate CREATE TABLE AS SELECT statements that copy structure and data from the existing source tables
- **Apply enterprise table properties** — enable Change Data Feed (CDF), Liquid Clustering (CLUSTER BY AUTO), auto-optimize, and auto-compact on every table
- **Preserve source COMMENTs** — carry over all column-level documentation from the source schema
- **Create Asset Bundle job** — generate a repeatable, version-controlled deployment job (databricks.yml + copy notebooks)
- **Deploy and run** — validate, deploy the bundle, and execute the copy job to populate Bronze tables
```

**Approach C — Copy from source (recommended for workshops):**

```
Set up the Bronze layer using @data_product_accelerator/skills/bronze/00-bronze-layer-setup/SKILL.md with Approach C — copy data from the existing source tables in the samples.wanderbricks schema.

This will involve the following steps:

- **Clone source tables** from the samples.wanderbricks schema into your target catalog's Bronze schema
- **Apply enterprise table properties** — enable Change Data Feed (CDF), Liquid Clustering (CLUSTER BY AUTO), auto-optimize, and auto-compact on every table
- **Preserve source COMMENTs** — carry over all column-level documentation from the source schema
- **Create Asset Bundle job** — generate a repeatable, version-controlled deployment job (databricks.yml + clone script)
- **Deploy and run** — validate, deploy the bundle, and execute the clone job to populate Bronze tables

Use default catalog as: <YOUR_CATALOG>
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

This will involve the following steps:

- **Generate SDP pipeline notebooks** — create Spark Declarative Pipeline notebooks with incremental ingestion from Bronze using Change Data Feed (CDF)
- **Create centralized DQ rules table** — build a configurable data quality rules table with expectations (null checks, range validation, referential integrity)
- **Create Asset Bundle** — generate bundle configuration for both the DQ rules setup job and the SDP pipeline
- **Deploy and run in order** — deploy the bundle, run the DQ rules setup job FIRST (creates the rules table), then run the SDP pipeline (reads rules from the table)

Ensure bundle is validated and deployed successfully, and silver layer jobs run with no errors.

Validate the results in the UI to ensure the DQ rules show up in centralized delta table, and that the silver layer pipeline runs successfully with Expectations being checked.
```

**What it produces:**
- DLT pipeline notebooks with streaming ingestion
- Data quality expectations (stored in Unity Catalog Delta table)
- Quarantine patterns for failed records
- Asset Bundle pipeline configuration

> **Deep dive:** See [Silver Orchestrator Walkthrough](docs/framework-design/14-silver-orchestrator-walkthrough.md) for context-aware loading patterns and DLT pipeline generation details.

---

## Step 4: Gold Layer Implementation

Create the Gold tables, merge scripts, and FK constraints from the YAML designs.

**Prompt:**

```
Implement the Gold layer using @data_product_accelerator/skills/gold/01-gold-layer-setup/SKILL.md

This will involve the following steps:

- **Read YAML schemas** — use the Gold layer design YAML files as the single source of truth for all table definitions, columns, and constraints
- **Create Gold tables** — generate CREATE TABLE DDL from YAML, add PRIMARY KEY constraints, then add FOREIGN KEY constraints (NOT ENFORCED) in dependency order
- **Merge data from Silver** — deduplicate Silver records before MERGE, map columns using YAML lineage metadata, merge dimensions first (SCD1/SCD2) then facts (FK dependency order)
- **Deploy 2-job architecture** — gold_setup_job (2 tasks: create tables + add FK constraints) and gold_merge_job (populate data from Silver)
- **Validate results** — verify table creation, PK/FK constraints, row counts, SCD2 history, and fact-dimension joins

Use the gold layer design YAML files as the target destination, and the silver layer tables as source.
```

**What it produces:**
- Gold table creation scripts (from YAML schemas)
- Silver-to-Gold MERGE notebooks (SCD Type 1/2 dimensions, fact tables)
- FK constraint application scripts
- Asset Bundle job configuration

> **Deep dive:** See [Gold Pipeline Orchestrator Walkthrough](docs/framework-design/15-gold-pipeline-orchestrator-walkthrough.md) for YAML-to-implementation patterns and FK constraint ordering.

### ⚠️ Deployment Checkpoint — Bronze + Silver + Gold

> **Important:** Due to the non-deterministic nature of LLMs, it may take a few tries of troubleshooting with the LLM to ensure the jobs run correctly and the tables are set-up correctly. It's of utmost importance that you verify the output before proceeding further. This is the first deployment checkpoint — validate all three data layers together before moving to planning and downstream stages.

**Recommended:** Validate the full data pipeline (Bronze, Silver, and Gold) before moving to the next step.

**Validation Prompt:**

```
Using @data_product_accelerator/skills/common/databricks-autonomous-operations/SKILL.md, validate, deploy, run, and troubleshoot until success for all data pipeline jobs — Bronze, Silver, and Gold.

This will involve the following steps:

- **Validate the Asset Bundle** — run `databricks bundle validate -t dev` to catch configuration errors before deployment
- **Deploy to workspace** — run `databricks bundle deploy -t dev` to push all resources to the Databricks workspace
- **Run Bronze jobs first** — execute Bronze layer jobs (table creation + data population) and verify all tables exist with data
- **Run Silver DLT pipeline** — execute DQ rules setup job first, then the Silver SDP pipeline; verify expectations are checked and data flows through
- **Run gold_setup_job** — execute Gold table creation and FK constraint tasks (dependency order: tables → PK → FK)
- **Run gold_merge_job** — execute Silver-to-Gold merge tasks (dependency order: dimensions → facts)
- **Diagnose failures at each layer** — on failure, retrieve task-level output (use task run_id, not parent job run_id), check for TABLE_OR_VIEW_NOT_FOUND (upstream not ready), DELTA_MULTIPLE_SOURCE_ROW_MATCHING (dedup needed), or PARSE_SYNTAX_ERROR
- **Apply fixes and redeploy** — fix source files, redeploy, and re-run (max 3 iterations per job before escalation)
```

> **Prerequisite:** Ensure Databricks CLI is installed and authenticated (`databricks auth login`).

---

## Step 5: Project Planning

Plan the semantic layer, observability, ML, and GenAI phases. This stage asks you interactive questions about which domains and addendums to include.

**Prompt (Data Product Acceleration — default):**

```
Perform project planning using @data_product_accelerator/skills/planning/00-project-planning/SKILL.md

This will involve the following steps:

- **Analyze Gold layer** — examine your completed Gold tables to identify natural business domains, key relationships, and analytical questions
- **Reference business context** — if a PRD exists at @docs/design_prd.md, use it for business requirements, user personas, and workflows; if a Business Onboarding Guide exists at gold_layer_design/docs/BUSINESS_ONBOARDING_GUIDE.md, use it for domain context and role-based scenarios
- **Generate use-case plans** — create structured plans organized as Phase 1 addendums (1.2 TVFs, 1.3 Metric Views, 1.4 Monitors, 1.5 Dashboards, 1.6 Genie Spaces, 1.7 Alerts, 1.1 ML Models)
- **Produce YAML manifests** — generate 4 machine-readable manifest files (semantic-layer, observability, ML, GenAI agents) as contracts for downstream implementation stages
- **Define deployment order** — establish build sequence: TVFs → Metric Views → Genie Spaces → Dashboards → Monitors → Alerts → Agents
```

**Prompt (Workshop mode — for Learning & Enablement):**

```
Perform project planning using @data_product_accelerator/skills/planning/00-project-planning/SKILL.md with planning_mode: workshop

This will involve the following steps:

- **Analyze Gold layer** — examine your completed Gold tables to identify natural business domains, key relationships, and analytical questions
- **Reference business context** — if a PRD exists at @docs/design_prd.md, use it for business requirements, user personas, and workflows; if a Business Onboarding Guide exists at gold_layer_design/docs/BUSINESS_ONBOARDING_GUIDE.md, use it for domain context and role-based scenarios
- **Generate use-case plans** — create structured plans organized as Phase 1 addendums (1.2 TVFs, 1.3 Metric Views, 1.4 Monitors, 1.5 Dashboards, 1.6 Genie Spaces, 1.7 Alerts, 1.1 ML Models)
- **Produce YAML manifests** — generate 4 machine-readable manifest files (semantic-layer, observability, ML, GenAI agents) as contracts for downstream implementation stages
- **Apply workshop mode caps** — enforce hard limits (3-5 TVFs, 1-2 Metric Views, 1 Genie Space) to keep the workshop focused on pattern variety over depth
- **Define deployment order** — establish build sequence: TVFs → Metric Views → Genie Spaces → Dashboards → Monitors → Alerts → Agents
```

> **Workshop mode** produces a minimal representative plan designed for hands-on workshops. It is only activated when `planning_mode: workshop` is explicitly included. See `data_product_accelerator/skills/planning/00-project-planning/references/workshop-mode-profile.md` for details.

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

This will involve the following end-to-end workflow:

- **Read plan manifests** — extract TVF, Metric View, and Genie Space specifications from the semantic-layer-manifest.yaml (from Step 5 planning)
- **Create Metric Views** — build Metric Views using `WITH METRICS LANGUAGE YAML` syntax with dimensions, measures, 3-5 synonyms each, and format specifications
- **Create Table-Valued Functions (TVFs)** — write parameterized SQL functions with STRING date params (non-negotiable for Genie), v3.0 bullet-point COMMENTs, and ROW_NUMBER for Top-N patterns
- **Configure Genie Space** — set up natural language query interface with data assets (Metric Views → TVFs → Gold tables priority), General Instructions (≤20 lines), and ≥10 benchmark questions with exact expected SQL
- **Create JSON exports** — export Genie Space configuration as JSON for CI/CD deployment across environments

Implement in this order:

1. **Table-Valued Functions (TVFs)** — using plan at plans/phase1-addendum-1.2-tvfs.md
2. **Metric Views** — using plan at plans/phase1-addendum-1.3-metric-views.md
3. **Genie Space** — using plan at plans/phase1-addendum-1.6-genie-spaces.md
4. **Genie JSON Exports** — create export/import deployment jobs

The orchestrator skill automatically loads worker skills for TVFs, Metric Views, Genie Space patterns, and export/import API.
```

**What it produces:**
- Metric View YAML definitions and SQL creation scripts
- TVFs optimized for Genie (STRING parameters, null safety)
- Genie Space configuration with agent instructions and benchmark questions
- Asset Bundle deployment

> **Deep dive:** See [Semantic Layer Orchestrator Walkthrough](docs/framework-design/12-semantic-layer-orchestrator-walkthrough.md) for manifest-driven orchestration and progressive skill loading.

### ⚠️ Deployment Checkpoint

> **Important:** The semantic layer has multiple interdependent components (TVFs, Metric Views, Genie Spaces). Genie Spaces depend on TVFs and Metric Views being deployed first. Validate the full deployment before proceeding.

**Recommended:** Validate the semantic layer deployment (TVFs, Metric Views, and Genie Space jobs) before moving to the next step.

**Validation Prompt:**

```
Using @data_product_accelerator/skills/common/databricks-autonomous-operations/SKILL.md, validate, deploy, run, and troubleshoot until success for the semantic layer jobs.

This will involve the following steps:

- **Validate the Asset Bundle** — run `databricks bundle validate -t dev` to catch configuration errors before deployment
- **Deploy to workspace** — run `databricks bundle deploy -t dev` to push all resources to the Databricks workspace
- **Run TVF creation job first** — execute TVF SQL scripts (dependency: Gold tables must exist with column COMMENTs)
- **Run Metric View creation job** — execute Metric View YAML creation scripts
- **Run Genie Space setup** — configure Genie Space with data assets (Metric Views → TVFs → Gold tables)
- **Diagnose failures** — on failure, check for SQL syntax errors, missing schema references, or dependency ordering issues
- **Apply fixes and redeploy** — fix source files, redeploy, and re-run (max 3 iterations before escalation)
```

> **Prerequisite:** Ensure Databricks CLI is installed and authenticated (`databricks auth login`).

---

## Step 6b (Optional): Genie Space Optimization

Optimize Genie Space accuracy and repeatability through MLflow-driven benchmark evaluation and iterative control lever adjustments. The optimization orchestrator routes to 4 worker skills on demand: benchmark generation, evaluation (8 judges + arbiter), metadata optimization (GEPA/introspection), and change application.

**Prompt:**

```
Optimize the Genie Space using @data_product_accelerator/skills/semantic-layer/05-genie-optimization-orchestrator/SKILL.md

This will involve the following optimization loop:

- **Generate benchmarks** — create domain-relevant questions with expected SQL, validate ground truth via warehouse execution, sync to MLflow Evaluation Dataset
- **Evaluate with 8 judges** — run each benchmark against the live Genie Space (12-second rate limit), score with 3-layer judge architecture: Layer 1 (syntax, schema, logic, semantics, completeness, routing), Layer 2 (result correctness via DataFrame comparison), Layer 3 (arbiter for disagreements with auto-correction)
- **Introspect and optimize** — cluster failures by systemic root cause, generate metadata proposals mapped to 6 control levers with predicted impact, optionally use GEPA optimize_anything for metadata evolution
- **Apply 6 control levers in priority order** — (1) UC table/column COMMENTs, (2) Metric View metadata, (3) TVF COMMENTs, (4) Monitoring tables, (5) ML tables, (6) Genie Instructions (~4000 char limit, last resort)
- **Dual-persist every change** — apply fixes via BOTH API (immediate) AND repository files (persists across deployments)
- **Re-evaluate and iterate** — run evaluation job again, compare iterations, loop until accuracy ≥95% or max 5 iterations with plateau detection
- **Deploy and document** — bundle deploy optimized space, generate optimization report with before/after metrics logged to MLflow
```

**What it produces:**
- Benchmark question suite with validated ground truth SQL (YAML + MLflow dataset)
- Per-judge accuracy scores and MLflow experiment runs
- Optimized UC metadata, Metric Views, TVFs, and/or Genie Instructions
- Optimization report with before/after metrics and levers applied

> **Deep dive:** See [Agent Walkthrough: Genie Optimization](docs/agent-walkthrough.md) for progressive disclosure patterns, long-running session management, and how the agent navigates the 9-step optimization loop.

---

## Step 7: Observability Setup

Set up Lakehouse Monitors, AI/BI Dashboards, and SQL Alerts.

**Prompt:**

```
Set up observability using @data_product_accelerator/skills/monitoring/00-observability-setup/SKILL.md

This will involve the following end-to-end workflow:

- **Read plan manifests** — extract monitor, dashboard, and alert specifications from the observability-manifest.yaml (from Step 5 planning)
- **Create Lakehouse Monitors** — configure data quality monitors on Gold tables with custom business metrics, profile windows, and anomaly thresholds
- **Build AI/BI Dashboards** — create `.lvdash.json` configurations with KPI counters, charts, data tables, and filters using 6-column grid layout and `MEASURE()` queries against Metric Views
- **Configure SQL Alerts** — set up severity-based alerting (CRITICAL/WARNING/INFO) with notification destinations and scheduling
- **Deploy via Asset Bundle** — generate bundle configuration for monitor setup jobs, dashboard deployment, and alert creation

Reference the observability plan at plans/phase1-addendum-1.4-lakehouse-monitoring.md, plans/phase1-addendum-1.5-aibi-dashboards.md, and plans/phase1-addendum-1.7-alerting.md

The orchestrator skill automatically loads worker skills for Lakehouse Monitoring, AI/BI Dashboards, SQL Alerting, and Anomaly Detection.
```

**What it produces:**
- Lakehouse Monitors with custom business metrics
- AI/BI Dashboard JSON definitions
- SQL Alert configurations with severity-based routing
- Asset Bundle deployment

### ⚠️ Deployment Checkpoint

> **Important:** Observability resources (Lakehouse Monitors, dashboards, alerts) depend on Gold tables being populated with data. Monitors require existing tables to profile, and alerts reference monitor output tables.

**Recommended:** Validate the observability deployment (monitors, dashboards, and alerts) before moving to the next step.

**Validation Prompt:**

```
Using @data_product_accelerator/skills/common/databricks-autonomous-operations/SKILL.md, validate, deploy, run, and troubleshoot until success for the observability jobs.

This will involve the following steps:

- **Validate the Asset Bundle** — run `databricks bundle validate -t dev` to catch configuration errors before deployment
- **Deploy to workspace** — run `databricks bundle deploy -t dev` to push all resources to the Databricks workspace
- **Run Lakehouse Monitor setup** — create monitors and trigger initial refresh on Gold tables
- **Deploy AI/BI Dashboards** — import `.lvdash.json` via Workspace Import API with overwrite
- **Create SQL Alerts** — set up alerts with notification destinations and verify scheduling
- **Diagnose failures** — on failure, check for ResourceAlreadyExists (delete + recreate), missing tables, or update_mask issues on monitors
- **Apply fixes and redeploy** — fix source files, redeploy, and re-run (max 3 iterations before escalation)
```

> **Prerequisite:** Ensure Databricks CLI is installed and authenticated (`databricks auth login`).

---

## Step 8: ML Pipeline Setup

Create ML experiments, model training, and batch inference.

**Prompt:**

```
Set up the ML pipeline using @data_product_accelerator/skills/ml/00-ml-pipeline-setup/SKILL.md

This will involve the following end-to-end workflow:

- **Read plan manifests** — extract ML experiment specifications from the ml-manifest.yaml (from Step 5 planning)
- **Create MLflow experiments** — set up experiment tracking with Unity Catalog model registry integration
- **Build feature engineering notebooks** — create Feature Store feature tables from Gold layer data with point-in-time lookups
- **Create model training notebooks** — implement training pipelines with hyperparameter tuning, cross-validation, and automatic model logging
- **Set up batch inference** — create inference jobs that load registered models, score new data, and write predictions to Gold tables
- **Deploy via Asset Bundle** — generate bundle configuration for training jobs, inference jobs, and model serving endpoints

The orchestrator skill automatically loads common skills for Asset Bundles, naming standards, and autonomous operations.
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

This will involve the following end-to-end workflow:

- **Read plan manifests** — extract agent specifications from the genai-agents-manifest.yaml (from Step 5 planning)
- **Build ResponsesAgent** — implement an MLflow 3.0 ResponsesAgent with streaming support, tool integration, and conversation history
- **Configure multi-agent Genie orchestration** — set up intent classification to route natural language queries across multiple Genie Spaces
- **Create evaluation pipelines** — build LLM judge scorers for relevance, groundedness, and safety, then run evaluations against benchmark datasets
- **Set up deployment automation** — create Model Serving endpoint configuration with traffic routing, A/B testing, and scale-to-zero
- **Configure production monitoring** — set up registered scorers for real-time agent quality monitoring with alerting thresholds

The orchestrator skill automatically loads worker skills for ResponsesAgent patterns, evaluation, memory, prompt registry, multi-agent orchestration, deployment, and monitoring.
```

**What it produces:**
- ResponsesAgent implementation with streaming
- Multi-agent Genie Space orchestration
- Evaluation pipelines with LLM judges
- Model Serving deployment configuration

---

## Tips

- **One prompt per stage.** Each orchestrator skill handles the full workflow for its stage.
- **Parallelize when possible.** See [Parallel Execution Guide](docs/framework-design/09-parallel-execution-guide.md) — Steps 1 & 2 can run concurrently, and Steps 6, 7 & 8 can run in parallel after Planning completes.
- **New conversation per stage.** Start a fresh agent conversation for each stage to keep context clean.
- **The skill does the thinking.** You don't need to specify details — the orchestrator reads its worker skills, common skills, and your existing artifacts automatically.
- **The bullet points help you and the LLM.** Each prompt explains what will happen so you know what to expect, while also priming the LLM with the correct workflow sequence.
- **If something fails,** reference `@data_product_accelerator/skills/common/databricks-autonomous-operations/SKILL.md` for the self-healing loop (Deploy → Poll → Diagnose → Fix → Redeploy, up to 3 iterations).
- **Validate at checkpoints.** There are three deployment checkpoints: after Gold (covers Bronze + Silver + Gold together), after Semantic Layer, and after Observability. Use the validation prompts with `@data_product_accelerator/skills/common/databricks-autonomous-operations/SKILL.md` to deploy, run, and troubleshoot until success. LLM non-determinism may require multiple iterations — verify output before proceeding to the next stage.

---

## Pipeline at a Glance

```
data_product_accelerator/context/*.csv
  → Gold Design (1)      — dimensional model, ERDs, YAML schemas
  → Bronze (2)           — source tables + test data
  → Silver (3)           — DLT pipelines + data quality
  → Gold Impl (4)        — tables, merges, constraints
    ⚠️ Deployment Checkpoint — validate & deploy Bronze + Silver + Gold
  → Planning (5)         — phase plans + manifest contracts
  → Semantic (6)         — Metric Views, TVFs, Genie Spaces
    ⚠️ Deployment Checkpoint — validate & deploy Semantic Layer
  → Genie Optimization (6b) — benchmark, evaluate, tune control levers
  → Observability (7)    — monitors, dashboards, alerts
    ⚠️ Deployment Checkpoint — validate & deploy Observability
  → ML (8)               — experiments, training, inference
  → GenAI Agents (9)     — agents, evaluation, deployment
```
