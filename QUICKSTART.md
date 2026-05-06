# Quick Start

Get started building your data product on Databricks. Choose your starting point:

> **Workshop participants:** Complete the [PRE-REQUISITES.md](PRE-REQUISITES.md) checklist before beginning. Rows are tagged **Common**, **DPA**, **AppKit-MCP**, and **Genie** — not every row applies to every path (see the legend at the top of that file). Apps Lakebase with MCP also needs admins to finish **[pre-req-mcp-setup.md](pre-req-mcp-setup.md)** before session start.
>
> **Facilitators:** Use the ordered runbook in [WORKSHOP-FACILITATOR-GUIDE.md](WORKSHOP-FACILITATOR-GUIDE.md#0-end-to-end-facilitator-checklist) (section **0 — End-to-end facilitator checklist**) for admin order, optional MCP setup, and day-of track splits.

---

## Path A: Build and Deploy a Databricks App

Build a full-stack TypeScript app on Databricks AppKit, guided by 6 agent skills:

```bash
# 1. Clone template
git clone https://github.com/databricks-solutions/vibe-coding-workshop-template.git my-project && cd my-project

# 2. Authenticate
databricks auth login --host https://your-workspace.cloud.databricks.com

# 3. Open your AI coding assistant and prompt:
```

```
I want to build a Databricks App. Read @apps_lakebase/skills/01-appkit-scaffold/SKILL.md and scaffold a new AppKit project.
```

**Genie Code:** follow [apps_lakebase/prompts/README.md](apps_lakebase/prompts/README.md). **Local IDE:** follow the 5-phase workflow using [apps_lakebase/skills/](apps_lakebase/skills/) (CLI/npm on your machine per each `SKILL.md`); context in [apps_lakebase/Instructions.md](apps_lakebase/Instructions.md):

| Phase | What Happens | Skill Used |
|-------|-------------|------------|
| 1 | Scaffold + build UI from a PRD, test locally | `01-appkit-scaffold`, `02-appkit-build` |
| 2 | Deploy to Databricks Apps (mock data) | `03-appkit-deploy` |
| 3 | Setup Lakebase project | `00-appkit-navigator` |
| 4 | Wire Lakebase backend (local) | `04-appkit-plugin-add`, `05-appkit-lakebase-wiring` |
| 5 | Deploy + E2E test with Lakebase | `03-appkit-deploy` |

---

## Path B: Build an End-to-End Data Pipeline

Take a raw schema CSV through the full medallion architecture -- Bronze, Silver, Gold, semantic layer, Genie Spaces, ML, and GenAI agents -- using one prompt per stage:

1. Drop your schema CSV into `data_product_accelerator/context/`
2. Open your AI coding assistant (Cursor, Claude Code, Windsurf, etc.)
3. Prompt:

```
I have a customer schema at @data_product_accelerator/context/Wanderbricks_Schema.csv.
Please design the Gold layer using @data_product_accelerator/skills/gold/00-gold-layer-design/SKILL.md
```

4. Follow the full [9-stage pipeline guide](data_product_accelerator/QUICKSTART.md) -- one prompt per stage, one new conversation per stage.

---

## Repository Layout

| Directory | What It Does |
|-----------|-------------|
| `apps_lakebase/` | AppKit workshop -- 6 agent skills for building full-stack Databricks Apps |
| `data_product_accelerator/` | 59 agent skills for building end-to-end data products (9 stages) |
| `agentic-framework/` | Multi-agent build framework for Databricks Foundation Models |

---

## AppKit Commands (after scaffolding)

After scaffolding your app with the `01-appkit-scaffold` skill, these commands run from your generated app directory:

| Task | Command |
|------|---------|
| **Install deps** | `npm install` |
| **Dev server** | `npm run dev` |
| **Build** | `npm run build` |
| **Type generation** | `npm run typegen` |
| **Validate** | `databricks apps validate` |
| **Deploy** | `databricks apps deploy --profile <PROFILE>` |
| **AppKit docs** | `npx @databricks/appkit docs` |

---

## Local URLs (after scaffolding)

- **App + API**: http://localhost:8000
- **Health**: http://localhost:8000/health

---

## Data Product Accelerator

Build a complete Databricks data product using one prompt per stage:

```
Schema CSV → Gold Design → Bronze → Silver → Gold → Semantic Layer → Observability → ML → GenAI Agents
```

- [data_product_accelerator/QUICKSTART.md](data_product_accelerator/QUICKSTART.md) -- Step-by-step (9 stages)
- [data_product_accelerator/AGENTS.md](data_product_accelerator/AGENTS.md) -- Skill routing table

---

## Troubleshooting

```bash
# Check CLI version (must be >= 0.295.0)
databricks --version

# Reconfigure auth
databricks auth login --host https://your-workspace.cloud.databricks.com

# Verify connection
databricks current-user me

# Check deployed app
databricks apps get <APP_NAME> --profile <PROFILE>

# Kill stuck dev server
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
```

---

**Full docs**: [README.md](README.md) | **Prerequisites**: [PRE-REQUISITES.md](PRE-REQUISITES.md) | **AppKit Genie prompts**: [apps_lakebase/prompts/README.md](apps_lakebase/prompts/README.md) · [overview](apps_lakebase/Instructions.md) | **9-stage guide**: [data_product_accelerator/QUICKSTART.md](data_product_accelerator/QUICKSTART.md)
