# 03 — Design-First Pipeline

## Overview

The Data Product Accelerator follows a **Design-First** pipeline: design the target Gold dimensional model from the customer's source schema CSV, then build the data layers (Bronze → Silver) to feed it, then layer on semantic, observability, ML, and GenAI capabilities. This is the opposite of the traditional bottom-up approach (build Bronze first, figure out Gold later).

The pipeline has 9 stages, each handled by a single orchestrator skill. One prompt per stage. One new Cursor Agent conversation per stage.

## Pipeline Architecture

```
context/*.csv
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

## Stage Details

### Stage 1: Gold Layer Design

| Field | Value |
|-------|-------|
| **Orchestrator** | `gold/00-gold-layer-design` |
| **Input** | `context/{ProjectName}_Schema.csv` |
| **Workers Used** | `gold/08-mermaid-erd-patterns`, `gold/02-yaml-driven-gold-setup`, `gold/03-gold-layer-documentation`, `gold/06-fact-table-grain-validation`, `gold/07-gold-layer-schema-validation`, `gold/04-gold-layer-merge-patterns` |
| **Duration** | 2-3 hours |

**What it does:**
1. Parses the customer schema CSV into a table inventory
2. Classifies tables as dimensions vs facts
3. Creates Mermaid ERD diagrams (master, domain, or summary based on table count)
4. Generates YAML schema files in `gold_layer_design/yaml/{domain}/`
5. Documents column-level lineage (Silver → Gold mappings)
6. Creates a business onboarding guide

**Key output:** `gold_layer_design/yaml/` — the single source of truth for all downstream stages.

**Prompt:**
```
I have a customer schema at @context/Wanderbricks_Schema.csv. Please design the Gold layer using @skills/gold/00-gold-layer-design/SKILL.md
```

---

### Stage 2: Bronze Layer Setup

| Field | Value |
|-------|-------|
| **Orchestrator** | `bronze/00-bronze-layer-setup` |
| **Input** | Schema CSV or existing source tables |
| **Workers Used** | `bronze/01-faker-data-generation` |
| **Duration** | 2-3 hours |

**What it does:**
1. Creates Bronze table DDLs with TBLPROPERTIES, CDF, and governance metadata
2. Populates data via one of three approaches:
   - **Approach A:** Faker synthetic data (recommended for demos)
   - **Approach B:** Read from existing Databricks tables
   - **Approach C:** Copy from source system tables
3. Configures Asset Bundle deployment jobs

**Prompt:**
```
Set up the Bronze layer using @skills/bronze/00-bronze-layer-setup/SKILL.md with Approach A
```

---

### Stage 3: Silver Layer Setup

| Field | Value |
|-------|-------|
| **Orchestrator** | `silver/00-silver-layer-setup` |
| **Input** | Bronze tables |
| **Workers Used** | `silver/01-dlt-expectations-patterns`, `silver/02-dqx-patterns` |
| **Duration** | 2-4 hours |

**What it does:**
1. Creates DLT pipeline notebooks with streaming ingestion from Bronze
2. Implements data quality expectations (stored in a Unity Catalog Delta table)
3. Sets up quarantine patterns for failed records
4. Configures Asset Bundle pipeline deployment

**Prompt:**
```
Set up the Silver layer using @skills/silver/00-silver-layer-setup/SKILL.md
```

---

### Stage 4: Gold Layer Implementation

| Field | Value |
|-------|-------|
| **Orchestrator** | `gold/01-gold-layer-setup` |
| **Input** | Gold YAML schemas (from stage 1) + Silver tables (from stage 3) |
| **Workers Used** | `gold/02-yaml-driven-gold-setup`, `gold/04-gold-layer-merge-patterns`, `gold/05-gold-delta-merge-deduplication`, `gold/06-fact-table-grain-validation`, `gold/07-gold-layer-schema-validation`, `gold/03-gold-layer-documentation`, `gold/08-mermaid-erd-patterns` |
| **Duration** | 3-4 hours |

**What it does:**
1. Creates Gold tables from YAML schemas (dynamic DDL generation)
2. Writes Silver-to-Gold MERGE scripts (SCD Type 1/2 dimensions, fact tables)
3. Applies FK constraints via `ALTER TABLE` after data population
4. Validates schema (DataFrame columns vs target DDL)
5. Configures Asset Bundle jobs

**Prompt:**
```
Implement the Gold layer using @skills/gold/01-gold-layer-setup/SKILL.md
```

---

### Stage 5: Project Planning

| Field | Value |
|-------|-------|
| **Orchestrator** | `planning/00-project-planning` |
| **Input** | Gold tables + YAML schemas |
| **Workers Used** | None (self-contained) |
| **Duration** | 2-4 hours |

**What it does:**
1. Interactively gathers planning requirements (which domains, which addendums)
2. Generates phase plan documents (TVFs, Metric Views, Monitoring, Dashboards, Genie, ML, Alerting)
3. **Emits YAML manifest files** in `plans/manifests/` — implementation contracts for stages 6-9

**Plan-as-Contract pattern:**

```
Gold YAML ─► Planning (stage 5) ─► Manifests ─► Downstream Orchestrators (stages 6-9)
                   │                    │
                emits:              consumes:
                4 manifests         1 manifest each
```

| Manifest | Consumed By |
|----------|-------------|
| `plans/manifests/semantic-layer-manifest.yaml` | Semantic Layer (stage 6) |
| `plans/manifests/observability-manifest.yaml` | Observability (stage 7) |
| `plans/manifests/ml-manifest.yaml` | ML Pipeline (stage 8) |
| `plans/manifests/genai-agents-manifest.yaml` | GenAI Agents (stage 9) |

Each downstream orchestrator has a **Phase 0: Read Plan** step. If no manifest exists (user skipped planning), the orchestrator falls back to **self-discovery** from Gold tables.

**Prompt:**
```
Perform project planning using @skills/planning/00-project-planning/SKILL.md
```

---

### Stage 6: Semantic Layer Setup

| Field | Value |
|-------|-------|
| **Orchestrator** | `semantic-layer/00-semantic-layer-setup` |
| **Input** | Semantic layer manifest + Gold tables |
| **Workers Used** | `semantic-layer/01-metric-views-patterns`, `02-databricks-table-valued-functions`, `03-genie-space-patterns`, `04-genie-space-export-import-api`, `05-genie-space-optimization` |
| **Duration** | 3-5 hours |

**What it does:**
1. Creates Metric View YAML definitions and SQL creation scripts
2. Develops TVFs optimized for Genie (STRING parameters, null safety)
3. Configures Genie Spaces with agent instructions and benchmark questions
4. Deploys via Asset Bundles
5. Runs optimization loop targeting 95%+ accuracy

**Prompt:**
```
Set up the semantic layer using @skills/semantic-layer/00-semantic-layer-setup/SKILL.md
```

---

### Stage 7: Observability Setup

| Field | Value |
|-------|-------|
| **Orchestrator** | `monitoring/00-observability-setup` |
| **Input** | Observability manifest + Gold tables |
| **Workers Used** | `monitoring/01-lakehouse-monitoring-comprehensive`, `02-databricks-aibi-dashboards`, `03-sql-alerting-patterns`, `04-anomaly-detection` |
| **Duration** | 3-5 hours |

**What it does:**
1. Creates Lakehouse Monitors with custom business metrics
2. Builds AI/BI Dashboard JSON definitions
3. Configures SQL Alerts with severity-based routing
4. Enables schema-level anomaly detection

**Prompt:**
```
Set up observability using @skills/monitoring/00-observability-setup/SKILL.md
```

---

### Stage 8: ML Pipeline Setup

| Field | Value |
|-------|-------|
| **Orchestrator** | `ml/00-ml-pipeline-setup` |
| **Input** | ML manifest + Gold tables |
| **Workers Used** | None (self-contained with rich references) |
| **Duration** | 6-12 hours |

**What it does:**
1. Creates MLflow experiments (using `/Shared/` experiment paths)
2. Sets up Feature Store with Unity Catalog integration
3. Implements model training pipelines
4. Configures batch inference jobs
5. Registers models in Unity Catalog Model Registry

**Prompt:**
```
Set up the ML pipeline using @skills/ml/00-ml-pipeline-setup/SKILL.md
```

---

### Stage 9: GenAI Agents Setup

| Field | Value |
|-------|-------|
| **Orchestrator** | `genai-agents/00-genai-agents-setup` |
| **Input** | GenAI manifest + Gold tables + Genie Spaces |
| **Workers Used** | `01-responses-agent-patterns`, `02-mlflow-genai-evaluation`, `03-lakebase-memory-patterns`, `04-prompt-registry-patterns`, `05-multi-agent-genie-orchestration`, `06-deployment-automation`, `07-production-monitoring`, `08-mlflow-genai-foundation` |
| **Duration** | 8-16 hours |

**What it does:**
1. Implements ResponsesAgent with streaming responses
2. Sets up multi-agent Genie Space orchestration
3. Creates evaluation pipelines with LLM judges
4. Configures Lakebase memory (short-term + long-term)
5. Deploys to Model Serving with OBO authentication

**Prompt:**
```
Set up GenAI agents using @skills/genai-agents/00-genai-agents-setup/SKILL.md
```

---

## Pipeline Tips

- **One prompt per stage.** Each orchestrator handles the full workflow.
- **New conversation per stage.** Start a fresh Cursor Agent conversation to keep context clean.
- **The skill does the thinking.** You don't need to specify details — the orchestrator reads its worker skills, common skills, and existing artifacts automatically.
- **If something fails,** the `databricks-autonomous-operations` common skill kicks in (Deploy → Poll → Diagnose → Fix → Redeploy).
- **Stages 6-9 are optional.** A functional data platform exists after stage 4.
- **Stages 6-9 can run in any order** (they're independent of each other).

## References

- [QUICKSTART.md](../../QUICKSTART.md) — One-prompt-per-stage reference with exact prompts
- [Skill Navigator](../../skills/skill-navigator/SKILL.md) — Full routing table and domain indexes
