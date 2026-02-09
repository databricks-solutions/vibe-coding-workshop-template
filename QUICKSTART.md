# Quick Start

Deploy your Databricks App in 4 commands:

```bash
# 1. Clone template
git clone https://github.com/YOUR_ORG/vibe-coding-workshop-template.git my-app && cd my-app

# 2. Setup (configure auth + install deps)
cd apps_lakebase && ./scripts/setup.sh

# 3. Deploy
./scripts/deploy.sh --create

# 4. Open your app URL!
```

---

## Repository Layout

This template has three main components:

| Directory | What It Does |
|-----------|-------------|
| `apps_lakebase/` | Databricks App — FastAPI backend + Lakebase integration |
| `agent_skills/` | YAML-driven skill orchestration framework |
| `data_product_accelerator/` | 50 agent skills for building data products (9 stages) |

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

Build a complete Databricks data product using one prompt per stage. See the full guide:

- [data_product_accelerator/QUICKSTART.md](data_product_accelerator/QUICKSTART.md) — Step-by-step (9 stages)
- [data_product_accelerator/AGENTS.md](data_product_accelerator/AGENTS.md) — Skill routing table

Quick example:

```
I have a customer schema at @data_product_accelerator/context/Wanderbricks_Schema.csv.
Please design the Gold layer using @data_product_accelerator/skills/gold/00-gold-layer-design/SKILL.md
```

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

**Full docs**: [README.md](README.md)
