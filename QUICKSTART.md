# Quick Start

Get started building your data product on Databricks. Choose your starting point:

> **Workshop participants:** Complete the [PRE-REQUISITES.md](PRE-REQUISITES.md) checklist before beginning.

---

## Path A: Build and Deploy a Databricks App

Build a full-stack TypeScript app on Databricks AppKit, guided by 10 agent skills:

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

Follow the branch-aware workflow in [apps_lakebase/Instructions.md](apps_lakebase/Instructions.md):

| Phase | What Happens | Skill Used |
|-------|-------------|------------|
| 1 | Scaffold + build UI from a PRD, test locally | `01-appkit-scaffold`, `02-appkit-build` |
| 2 | Deploy to Databricks Apps (mock data) | `03-appkit-deploy` |
| 3 | Setup Lakebase bundle resources | `04-appkit-plugin-add`, `apps_lakebase/prompts/03-setup-lakebase.md` |
| 4 | Wire Lakebase backend (local) | `04-appkit-plugin-add`, `05-appkit-lakebase-wiring` |
| 4b | Wire Serving / Agent endpoint (optional) | `04-appkit-plugin-add`, `06-appkit-serving-wiring` |
| 4c | Wire AppKit to a separate Agent App (optional) | `06d-appkit-agent-app-proxy` |
| 4d | Add chat history + feedback (optional) | `07-appkit-chat-history`, `08-appkit-feedback` |
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
| `apps_lakebase/` | AppKit workshop -- 10 agent skills for building full-stack Databricks Apps |
| `genai-agents/` | GenAI agent course -- current orchestrator, prompt guide, Track A custom Agent Apps, and SDLC |
| `data_product_accelerator/` | 77 agent skills for building end-to-end data products (9 stages) |
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

## GenAI Agent Course

Build production GenAI agents on Databricks using the current course navigator:

```
Start with @genai-agents/00-course-orchestrator/SKILL.md.
Use @genai-agents/PROMPT-GUIDE.md for the canonical Track A + AppKit 2-Apps walkthrough.
```

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

**Full docs**: [README.md](README.md) | **Prerequisites**: [PRE-REQUISITES.md](PRE-REQUISITES.md) | **AppKit guide**: [apps_lakebase/Instructions.md](apps_lakebase/Instructions.md) | **9-stage guide**: [data_product_accelerator/QUICKSTART.md](data_product_accelerator/QUICKSTART.md)
