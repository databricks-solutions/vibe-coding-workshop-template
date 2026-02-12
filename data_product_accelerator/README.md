# Data Product Accelerator

> 50 Agent Skills that teach your AI coding assistant to build fully governed Databricks data products — from a schema CSV to production AI agents.
>
> Built on the open [SKILL.md](https://agentskills.io) format — works with Cursor, Claude Code, Windsurf, Copilot, and Codex.

A comprehensive **skills-based framework** for building production-grade Databricks Lakehouse solutions. Drop a schema CSV, point your AI coding assistant at the skills, and go from raw tables to a fully governed data product with dimensional models, quality pipelines, semantic interfaces, observability, ML, and GenAI agents.

---

## What's Inside

| Component | Description | Count |
|-----------|-------------|-------|
| **Agent Skills** | Structured knowledge packages for AI-assisted Databricks development | 50 skills across 12 domains |
| **AGENTS.md** | Universal entry point with routing table and common skills index | 1 file |
| **Context Files** | Customer schema CSV (the starting input for the pipeline) | 1 file |

---

## Quick Start

### Prerequisites

- Databricks workspace with Unity Catalog enabled
- AI coding assistant with file reference support (Cursor, Claude Code, Windsurf, Copilot, Codex, etc.)
- Databricks CLI v0.200+ installed and configured
- Git for version control

### Getting Started

1. **Clone the repository**

```bash
git clone https://github.com/prashsub/data-product-accelerator.git
cd data-product-accelerator
```

2. **Place your schema CSV** in the `data_product_accelerator/context/` directory

3. **Open in your AI coding assistant** and start with the first prompt:

```
I have a customer schema at @data_product_accelerator/context/Wanderbricks_Schema.csv.
Please design the Gold layer using @data_product_accelerator/skills/gold/00-gold-layer-design/SKILL.md
```

> **Note:** Most IDEs support `@` for file references. If yours doesn't, ask the agent to "read the file at data_product_accelerator/skills/gold/00-gold-layer-design/SKILL.md" instead.

4. **Follow the [QUICKSTART guide](QUICKSTART.md)** for all 9 stages

---

## How It Works

The framework uses a **skills-first architecture**: a single `AGENTS.md` entry point routes the AI assistant to 50 Agent Skills organized by domain. Each skill contains production-tested patterns, reference documentation, executable scripts, and starter templates. Skills use the open [SKILL.md format](https://agentskills.io) — portable across any AI coding assistant.

### Design-First Pipeline (9 Stages)

One prompt per stage. One new agent conversation per stage.

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

### Key Principle: Design-First

Design the target Gold dimensional model **first** (from the customer's schema CSV), then build the data layers (Bronze → Silver) to feed it. This is the opposite of the traditional bottom-up approach.

---

## Repository Structure

This module lives inside a multi-module repository. The framework (skills, docs, context) is in `data_product_accelerator/`, while generated artifacts are created at the **repository root**.

```
repo-root/
│
├── data_product_accelerator/           # Framework module
│   ├── AGENTS.md                       #   Universal entry point (routing table + common skills)
│   ├── QUICKSTART.md                   #   One-prompt-per-stage guide
│   ├── README.md                       #   This file
│   │
│   ├── skills/                         #   50 Agent Skills (open SKILL.md format)
│   │   ├── admin/                      #     Skill creation, auditing, docs (4)
│   │   ├── bronze/                     #     Bronze layer + Faker data (2)
│   │   ├── common/                     #     Cross-cutting shared skills (8)
│   │   ├── exploration/                #     Ad-hoc notebooks (1)
│   │   ├── genai-agents/               #     GenAI agent patterns (9)
│   │   ├── gold/                       #     Gold design + implementation (9)
│   │   ├── ml/                         #     MLflow pipelines (1)
│   │   ├── monitoring/                 #     Monitors, dashboards, alerts (5)
│   │   ├── planning/                   #     Project planning (1)
│   │   ├── semantic-layer/             #     Metric Views, TVFs, Genie (6)
│   │   ├── silver/                     #     DLT pipelines, DQ rules (3)
│   │   └── skill-navigator/            #     Master routing system (1)
│   │
│   ├── context/
│   │   └── Wanderbricks_Schema.csv     #   Customer schema input
│   │
│   └── docs/                           #   Framework documentation
│       └── framework-design/           #     Complete design documentation
│
├── gold_layer_design/                  # GENERATED: dimensional model YAML schemas and ERDs
├── src/                                # GENERATED: notebooks and scripts (Bronze, Silver, Gold, etc.)
├── plans/                              # GENERATED: phase plans and YAML manifest contracts
├── resources/                          # GENERATED: DAB job and pipeline YAML
└── databricks.yml                      # GENERATED: Asset Bundle root configuration
```

> **Note:** Generated artifact directories (`gold_layer_design/`, `src/`, `plans/`, `resources/`, `databricks.yml`) are created by skills during pipeline execution. They do not exist until you run the first stages. Other modules may coexist at the repository root.

---

## Agent Skills by Domain

Skills follow an **orchestrator/worker** pattern: orchestrators (prefixed `00-`) manage end-to-end workflows, workers (prefixed `01-`, `02-`, etc.) handle specific patterns.

| Domain | Orchestrator | Workers | Focus |
|--------|-------------|---------|-------|
| **Gold (Design)** | `00-gold-layer-design` | 7 | ERDs, YAML schemas, dimensional modeling |
| **Bronze** | `00-bronze-layer-setup` | 1 | Table DDLs, Faker data, source copy |
| **Silver** | `00-silver-layer-setup` | 2 | DLT expectations, DQX diagnostics |
| **Gold (Impl)** | `01-gold-layer-setup` | shared | MERGE scripts, FK constraints |
| **Planning** | `00-project-planning` | 0 | Phase plans, YAML manifest contracts |
| **Semantic** | `00-semantic-layer-setup` | 5 | Metric Views, TVFs, Genie Spaces |
| **Monitoring** | `00-observability-setup` | 4 | Monitors, dashboards, SQL alerts |
| **ML** | `00-ml-pipeline-setup` | 0 | MLflow, Feature Store, inference |
| **GenAI** | `00-genai-agents-setup` | 8 | ResponsesAgent, evaluation, deployment |
| **Exploration** | `00-adhoc-exploration-notebooks` | 0 | Ad-hoc analysis notebooks |
| **Common** | — | 8 | Asset Bundles, naming, constraints, imports |

---

## What You Get

After using this framework:

- **Complete Medallion Architecture** — Bronze, Silver, and Gold tables with governance
- **Data Quality** — DLT expectations with quarantine patterns, stored in Unity Catalog
- **Dimensional Model** — Fact and dimension tables with PK/FK constraints
- **Semantic Layer** — Metric Views and TVFs for Genie natural language queries
- **Observability** — Lakehouse Monitors, AI/BI Dashboards, and SQL Alerts
- **ML Pipelines** — MLflow experiments, model training, and batch inference
- **GenAI Agents** — ResponsesAgent with multi-agent Genie orchestration
- **Governance** — PII tags, data classification, rich comments, full lineage

### Time Savings

| Approach | Time | Savings |
|----------|------|---------|
| **Using Framework (core)** | 17-28 hours | — |
| **Using Framework (full stack)** | 31-56 hours | — |
| **From Scratch** | 80-120 hours | — |
| **Savings** | — | **4-6x faster** |

---

## Key Technologies

- **Databricks Unity Catalog** — Governance, lineage, and data classification
- **Delta Lake** — ACID transactions, time travel, and Change Data Feed
- **Delta Live Tables (DLT)** — Streaming pipelines with data quality expectations
- **Databricks Asset Bundles** — Infrastructure as Code for all resources
- **Metric Views** — Semantic metadata layer for AI/BI and Genie
- **Genie Spaces** — Natural language query interface
- **Lakehouse Monitoring** — Data profiling with custom business metrics
- **MLflow** — ML experiment tracking, model registry, and GenAI agents

---

## Documentation

| Document | Purpose |
|----------|---------|
| [AGENTS.md](AGENTS.md) | Universal entry point for any AI coding assistant |
| [QUICKSTART.md](QUICKSTART.md) | One-prompt-per-stage guide (start here) |
| [Framework Design Docs](docs/framework-design/00-index.md) | Complete architecture and design documentation |
| [Skill Navigator](skills/skill-navigator/SKILL.md) | Master skill routing system |

---

## Domain Adaptation

These patterns work for any industry:

| Original | Healthcare | Finance | Manufacturing |
|----------|------------|---------|---------------|
| store | hospital | branch | facility |
| product | medication | financial_product | component |
| transaction | encounter | transaction | production_run |
| revenue | reimbursement | interest_income | output_value |

---

## Pro Tips

1. **One prompt per stage** — Each orchestrator skill handles the full workflow
2. **New conversation per stage** — Start fresh to keep context clean
3. **Start with Gold Design** — Design the target model before building Bronze/Silver
4. **Let the skill do the thinking** — The orchestrator loads its workers and common skills automatically
5. **Test with Faker** — Generate synthetic data before connecting real sources
6. **Deploy to dev first** — Use `databricks bundle deploy -t dev`
7. **If something fails** — The autonomous operations skill handles troubleshooting

---

## Resources

### Official Documentation

- [Databricks Documentation](https://docs.databricks.com/)
- [Unity Catalog](https://docs.databricks.com/unity-catalog/)
- [Delta Lake](https://docs.databricks.com/delta/)
- [DLT Expectations](https://docs.databricks.com/dlt/expectations)
- [Metric Views](https://docs.databricks.com/metric-views/)
- [Lakehouse Monitoring](https://docs.databricks.com/lakehouse-monitoring/)
- [MLflow](https://mlflow.org/docs/latest/)

### Framework Support

- See the [Skill Navigator](skills/skill-navigator/SKILL.md) for routing to the right skill
- Run `@data_product_accelerator/skills/admin/self-improvement/SKILL.md` to capture learnings from errors
- Run `@data_product_accelerator/skills/admin/skill-freshness-audit/SKILL.md` to verify skills are current

---

## License

This repository is intended for educational and development purposes. Please review and customize the patterns for your specific use case and compliance requirements.

---

## Get Started Now

```bash
# Clone the repository
git clone https://github.com/prashsub/data-product-accelerator.git

# Open in your AI coding assistant
cd data-product-accelerator

# Follow the QUICKSTART guide
# → QUICKSTART.md
```

**Core platform (stages 1-7): 17-28 hours**
**Full stack with ML and GenAI (stages 1-9): 31-56 hours**
