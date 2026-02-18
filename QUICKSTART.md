# Quick Start

Get started building your data product on Databricks. Choose your starting point:

> **Workshop participants:** Complete the [PRE-REQUISITES.md](PRE-REQUISITES.md) checklist before beginning.

---

## Path A: Deploy a Databricks App

Get a FastAPI backend with Lakebase running on Databricks Apps in 4 commands:

```bash
# 1. Clone template
git clone https://github.com/databricks-solutions/vibe-coding-workshop-template.git my-project && cd my-project

# 2. Setup (configure auth + install deps)
cd apps_lakebase && ./scripts/setup.sh

# 3. Deploy
./scripts/deploy.sh --create

# 4. Open your app URL!
```

---

## Path B: Build an End-to-End Data Pipeline

Take a raw schema CSV through the full medallion architecture — Bronze, Silver, Gold, semantic layer, Genie Spaces, ML, and GenAI agents — using one prompt per stage:

1. Drop your schema CSV into `data_product_accelerator/context/`
2. Open your AI coding assistant (Cursor, Claude Code, Windsurf, etc.)
3. Prompt:

```
I have a customer schema at @data_product_accelerator/context/Wanderbricks_Schema.csv.
Please design the Gold layer using @data_product_accelerator/skills/gold/00-gold-layer-design/SKILL.md
```

4. Follow the full [9-stage pipeline guide](data_product_accelerator/QUICKSTART.md) — one prompt per stage, one new conversation per stage.

---

## Repository Layout

| Directory | What It Does |
|-----------|-------------|
| `apps_lakebase/` | Databricks App — FastAPI backend + Lakebase (managed PostgreSQL) |
| `data_product_accelerator/` | 50 agent skills for building end-to-end data products (9 stages) |
| `agentic-framework/` | Multi-agent build framework for Databricks Foundation Models |

---

## App Commands

All app commands are run from the `apps_lakebase/` directory:

| Task | Command |
|------|---------|
| **Setup** | `./scripts/setup.sh` |
| **First Deploy** | `./scripts/deploy.sh --create` |
| **Update Deploy** | `./scripts/deploy.sh` |
| **Local Dev** | `./scripts/watch.sh` |
| **Check Status** | `./scripts/app_status.sh` |
| **Setup Lakebase** | `./scripts/setup-lakebase.sh` |

---

## Local URLs

- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/health
- **Readiness**: http://localhost:8000/ready

---

## Data Product Accelerator

Build a complete Databricks data product using one prompt per stage:

```
Schema CSV → Gold Design → Bronze → Silver → Gold → Semantic Layer → Observability → ML → GenAI Agents
```

- [data_product_accelerator/QUICKSTART.md](data_product_accelerator/QUICKSTART.md) — Step-by-step (9 stages)
- [data_product_accelerator/AGENTS.md](data_product_accelerator/AGENTS.md) — Skill routing table

---

## Troubleshooting

```bash
# Reconfigure auth
cd apps_lakebase
rm .env.local && ./scripts/setup.sh

# Check connection
databricks current-user me

# Check app status
./scripts/app_status.sh --verbose
```

---

**Full docs**: [README.md](README.md) | **Prerequisites**: [PRE-REQUISITES.md](PRE-REQUISITES.md) | **9-stage guide**: [data_product_accelerator/QUICKSTART.md](data_product_accelerator/QUICKSTART.md)
