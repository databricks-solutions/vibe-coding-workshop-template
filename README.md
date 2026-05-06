# Vibe Coding Workshop Template

> **Build end-to-end data products on Databricks with AI-assisted development**

This template is a complete **data product builder** powered by vibe coding. Start from a raw customer schema or existing data, and build your way through the full Databricks stack — Databricks Apps with Lakebase, medallion architecture (Bronze, Silver, Gold), semantic layer, Genie Spaces, ML pipelines, and GenAI agents — all guided by 59 agent skills and your AI coding assistant.

---

## What is Vibe Coding?

**Vibe Coding** is an AI-assisted development approach where you collaborate with AI tools (like Cursor, GitHub Copilot, Claude Code, Windsurf, or similar) to rapidly build, iterate, and deploy production-quality data products. Instead of writing every line from scratch, you describe what you want and let the AI handle the implementation — guided by structured agent skills that encode best practices.

---

## Quick Start

> **Workshop participants:** See [PRE-REQUISITES.md](PRE-REQUISITES.md) for workspace and Unity Catalog setup (Genie / serverless). **Apps Lakebase with MCP:** admins follow [pre-req-mcp-setup.md](pre-req-mcp-setup.md). **Local IDE + CLI (Path A in QUICKSTART):** use the Prerequisites table below.

### Prerequisites

| Tool | Required | Installation |
|------|----------|-------------|
| **Databricks Workspace** | Yes | Access to a Databricks workspace with Unity Catalog |
| **Databricks CLI >= 0.295.0** | Yes | `curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh \| sh` |
| **Node.js v22+** | Yes (Path A) | [nodejs.org](https://nodejs.org/) — required by AppKit |
| **AI-Powered IDE** | Yes | [Cursor](https://cursor.com), [Windsurf](https://windsurf.com), VS Code + Copilot, or similar |
| **Python 3.10+** | Yes | [python.org](https://www.python.org/downloads/) |
| **Git** | Yes | [git-scm.com](https://git-scm.com/) |

### Clone the Template

```bash
git clone https://github.com/databricks-solutions/vibe-coding-workshop-template.git my-project
cd my-project
```

### Choose Your Starting Point

#### Path A: Build and Deploy a Databricks App

Build a full-stack TypeScript app on Databricks AppKit, guided by 6 agent skills:

1. **Genie Code:** [apps_lakebase/prompts/README.md](apps_lakebase/prompts/README.md) (prompt order). **Context:** [apps_lakebase/Instructions.md](apps_lakebase/Instructions.md) (short overview + links).
2. Open your AI coding assistant and prompt:

```
I want to build a Databricks App. Read @apps_lakebase/skills/01-appkit-scaffold/SKILL.md and scaffold a new AppKit project.
```

3. **Genie:** follow `apps_lakebase/prompts/README.md` (PRD → UI → Lakebase → wire → deploy). **Local IDE + CLI:** follow [QUICKSTART.md](QUICKSTART.md) Path A and [apps_lakebase/Instructions.md](apps_lakebase/Instructions.md) → `apps_lakebase/skills/`.

#### Path B: Build an End-to-End Data Pipeline

Take a raw schema CSV through the full medallion architecture to production AI agents — one prompt per stage:

1. Drop your schema CSV into `data_product_accelerator/context/`
2. Open your AI coding assistant and prompt:

```
I have a customer schema at @data_product_accelerator/context/Wanderbricks_Schema.csv.
Please design the Gold layer using @data_product_accelerator/skills/gold/00-gold-layer-design/SKILL.md
```

3. Follow the [9-stage pipeline guide](data_product_accelerator/QUICKSTART.md) — one prompt per stage, one new conversation per stage.

> **Both paths work together.** Build your data pipeline first, then deploy a Databricks App on top of it — or start with the app and add data products incrementally.

---

## Project Structure

```
vibe-coding-workshop-template/
│
├── README.md                       # This file
├── QUICKSTART.md                   # Quick-start guide with two pathways
├── AGENTS.md                       # AI assistant routing (universal entry point)
├── PRE-REQUISITES.md               # Workshop prerequisites checklist (workspace / UC / compute)
├── pre-req-mcp-setup.md            # MCP AppKit admin setup (shared MCP app + OAuth scope)
├── CONTRIBUTING.md                 # Contribution guidelines
├── LICENSE.md                      # License
├── SECURITY.md                     # Security policy
├── env.example                     # Environment variable template
│
├── apps_lakebase/                  # Databricks AppKit Workshop (6 agent skills)
│   ├── Instructions.md             #   Genie overview + links (see prompts/README.md)
│   └── skills/                     #   Agent skills for the full app lifecycle
│       ├── 00-appkit-navigator/    #     Entry-point navigator (read first)
│       ├── 01-appkit-scaffold/     #     Scaffold new AppKit projects (+ agent skills install)
│       ├── 02-appkit-build/        #     Build UI + backend from a PRD
│       ├── 03-appkit-deploy/       #     Deploy to Databricks Apps
│       ├── 04-appkit-plugin-add/   #     Add plugins (Lakebase, Analytics, Genie, Files)
│       └── 05-appkit-lakebase-wiring/ #  Wire Lakebase DDL, API routes, frontend hooks
│
├── data_product_accelerator/       # 59 Agent Skills for End-to-End Data Products
│   ├── AGENTS.md                   #   Detailed skill routing table
│   ├── QUICKSTART.md               #   One-prompt-per-stage guide (9 stages)
│   ├── README.md                   #   Accelerator overview
│   ├── context/                    #   Schema CSV inputs (starting point)
│   ├── skills/                     #   59 skills across 12 domains
│   │   ├── admin/                  #     Skill creation, auditing (4)
│   │   ├── bronze/                 #     Bronze layer + Faker data (2)
│   │   ├── common/                 #     Cross-cutting shared skills (8)
│   │   ├── exploration/            #     Ad-hoc notebooks (1)
│   │   ├── genai-agents/           #     GenAI agent patterns (9)
│   │   ├── gold/                   #     Gold design, implementation, workers (14)
│   │   ├── ml/                     #     MLflow pipelines (1)
│   │   ├── monitoring/             #     Monitors, dashboards, alerts (5)
│   │   ├── planning/               #     Project planning (1)
│   │   ├── semantic-layer/         #     Metric Views, TVFs, Genie, optimization (10)
│   │   ├── silver/                 #     DLT pipelines, DQ rules (3)
│   │   └── skill-navigator/        #     Master routing system (1)
│   └── docs/                       #   Framework design documentation
│
└── agentic-framework/              # Multi-Agent Build Framework
    ├── agents/                     #   Agent prompts for building multi-agent systems
    │   ├── prd-analyzer.md         #     Parse PRDs, map to agent capabilities
    │   ├── skill-scaffolder.md     #     Create new Agent Skills (SKILL.md)
    │   ├── tool-builder.md         #     Build runtime Python tools
    │   ├── agent-tester.md         #     Configure agent behavior tests
    │   ├── agent-ui-wiring-prompt.md #   Guide agent-to-UI wiring
    │   ├── multi-agent-build-prompt.md # Orchestrator build with Foundation Models
    │   ├── databricks-deployer.md  #     Deployment guidance
    │   └── prd-template.md         #     PRD template
    └── skills/
        └── foundation-model-agent-loop/
            └── SKILL.md            #   Tool-calling loop with Foundation Models
```

---

## How It All Fits Together

This template supports a unified workflow from raw data to production data products:

```
Raw Schema CSV or Existing Data
  │
  ├─► Gold Design         — dimensional model, ERDs, YAML schemas
  ├─► Bronze Layer         — source tables + test data (Faker)
  ├─► Silver Layer         — DLT pipelines + data quality expectations
  ├─► Gold Layer           — tables, MERGE scripts, FK constraints
  ├─► Semantic Layer       — Metric Views, TVFs, Genie Spaces
  ├─► Observability        — Lakehouse Monitors, AI/BI Dashboards, SQL Alerts
  ├─► ML Pipelines         — MLflow experiments, training, inference
  ├─► GenAI Agents         — ResponsesAgent, evaluation, deployment
  │
  └─► Databricks App       — AppKit (full-stack TypeScript), deployed on Databricks Apps
```

Each stage is driven by a single prompt to your AI coding assistant. The 59 agent skills in `data_product_accelerator/` encode production-tested patterns so you get governed, high-quality output at every step.

---

## Data Product Accelerator (59 Agent Skills)

The `data_product_accelerator/` directory contains **59 agent skills** organized by domain that guide your AI assistant through the entire pipeline:

| Domain | Skills | Focus |
|--------|--------|-------|
| **Gold** | 14 | Dimensional modeling, design workers, pipeline workers, ERDs, MERGE scripts |
| **Semantic Layer** | 10 | Metric Views, TVFs, Genie Spaces, optimization orchestrator + workers |
| **GenAI Agents** | 9 | ResponsesAgent, evaluation, deployment |
| **Common** | 8 | Asset Bundles, naming, constraints, imports |
| **Monitoring** | 5 | Lakehouse Monitors, dashboards, SQL alerts |
| **Admin** | 4 | Skill creation, auditing, docs |
| **Silver** | 3 | DLT pipelines, expectations, DQX |
| **Bronze** | 2 | Bronze tables, Faker data generation |
| **ML** | 1 | MLflow pipelines |
| **Planning** | 1 | Project planning |
| **Exploration** | 1 | Ad-hoc notebooks |
| **Skill Navigator** | 1 | Master routing system |

See [data_product_accelerator/QUICKSTART.md](data_product_accelerator/QUICKSTART.md) for the step-by-step 9-stage guide.

---

## Databricks AppKit Workshop (6 Agent Skills)

The `apps_lakebase/` directory contains **6 agent skills** and a comprehensive workshop guide for building full-stack TypeScript apps on [Databricks AppKit](https://databricks.github.io/appkit/). The app is **not pre-built** — it gets scaffolded at runtime via `databricks apps init` and built iteratively with your AI coding assistant.

**What gets built:**
- Full-stack TypeScript app (React + Tailwind CSS frontend, AppKit backend)
- SQL Warehouse integration for analytics queries
- Lakebase (managed PostgreSQL) persistence (wired in phases 3-5)
- Deployed to Databricks Apps with hot reload for local dev

### Workshop Skills

| Skill | Purpose |
|-------|---------|
| `00-appkit-navigator` | Entry-point navigator — routes tasks to the correct skill |
| `01-appkit-scaffold` | Scaffold new AppKit projects with plugins (analytics, lakebase, genie, files) |
| `02-appkit-build` | Build UI and backend from a PRD — components, queries, type generation |
| `03-appkit-deploy` | Deploy to Databricks Apps, validate configuration |
| `04-appkit-plugin-add` | Add plugins to an existing AppKit project |
| `05-appkit-lakebase-wiring` | Wire Lakebase DDL, Express API routes, frontend hooks, mock fallback |

### Local Development (after scaffolding)

| Service | URL |
|---------|-----|
| App + API | http://localhost:8000 |
| Health Check | http://localhost:8000/health |

Start the dev server from your scaffolded app directory with `npm run dev`.

---

## Agentic Framework

The `agentic-framework/` directory provides prompts and patterns for building **multi-agent systems** with Databricks Foundation Models.

**Agent prompts** (in `agentic-framework/agents/`):

| Agent | Purpose |
|-------|---------|
| **prd-analyzer** | Parse PRDs, map requirements to agent capabilities |
| **skill-scaffolder** | Create new Agent Skills (SKILL.md) for any domain |
| **tool-builder** | Build runtime Python tools for agents |
| **agent-tester** | Configure tests for agent behavior |
| **agent-ui-wiring-prompt** | Guide agent-to-UI integration |
| **multi-agent-build-prompt** | Build multi-agent orchestrators with Foundation Models |
| **databricks-deployer** | Deployment guidance for agents |
| **prd-template** | PRD template for agent projects |

**Foundation Model Agent Loop** (in `agentic-framework/skills/foundation-model-agent-loop/`):
- Pattern for tool-calling loops with Databricks Foundation Models (e.g., `databricks-meta-llama-3-3-70b-instruct`)
- Supports function calling without custom model deployment

---

## How Deployment Works

After scaffolding your AppKit app, the 5-phase workflow progresses from mock data to a fully wired Lakebase backend:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    AppKit Workshop Phases                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Phase 1: SCAFFOLD + BUILD     Phase 2: DEPLOY (mock data)         │
│  ────────────────────────      ──────────────────────────           │
│  databricks apps init          npm run build                        │
│  Build UI from PRD             databricks apps deploy --profile <P> │
│  npm run dev (localhost:8000)  Verify at Databricks Apps URL        │
│                                                                     │
│  Phase 3: SETUP LAKEBASE       Phase 4: WIRE LAKEBASE              │
│  ──────────────────────        ─────────────────────               │
│  Create Lakebase project       Add Lakebase plugin (skill 04)      │
│  Configure endpoint + compute  DDL, API routes, frontend (skill 05)│
│  Record host in state file     Test locally with mock fallback      │
│                                                                     │
│  Phase 5: DEPLOY + E2E TEST                                        │
│  ────────────────────────                                           │
│  databricks apps deploy (with Lakebase config)                      │
│  Verify live data end-to-end                                        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Key Files in the Generated App

| File | Purpose |
|------|---------|
| `app.yaml` | Defines how Databricks starts your app |
| `databricks.yml` | Databricks bundle configuration |
| `server/server.ts` | AppKit backend entry point |
| `client/src/` | React + Tailwind CSS frontend |
| `package.json` | Node.js dependencies |

See the `03-appkit-deploy` skill for the full deployment workflow.

---

## Authentication

Configure a Databricks CLI profile to authenticate:

```bash
databricks auth login --host https://your-workspace.cloud.databricks.com
```

Verify it works:

```bash
databricks current-user me
```

To use a named profile (useful when working with multiple workspaces):

```bash
databricks auth login --host https://your-workspace.cloud.databricks.com --profile myprofile
databricks current-user me --profile myprofile
```

All skills and CLI commands accept a `--profile` flag to target a specific workspace.

---

## Customizing Your App

After scaffolding, your generated AppKit app is a full-stack TypeScript project. Customize it using standard AppKit patterns:

### Adding Backend Routes

Edit `server/server.ts` in your generated app directory to add Express routes via `appkit.server.extend()`. See the `02-appkit-build` skill for patterns.

### Adding Plugins

Use the `04-appkit-plugin-add` skill to add capabilities:

```
Read @apps_lakebase/skills/04-appkit-plugin-add/SKILL.md and add the Lakebase plugin to my app.
```

Available plugins: `analytics`, `lakebase`, `genie`, `files`

### Adding Dependencies

```bash
npm install your-package
```

### Consulting AppKit Docs

```bash
npx @databricks/appkit docs              # documentation index
npx @databricks/appkit docs "<query>"    # search for a specific topic
```

---

## Troubleshooting

### Check Databricks CLI

```bash
databricks --version          # Should be >= 0.295.0
databricks current-user me    # Verify authentication
databricks auth profiles      # List configured profiles
```

### Authentication failed

```bash
databricks auth login --host https://your-workspace.cloud.databricks.com
```

### Port 8000 in use

```bash
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
npm run dev
```

### View Deployed App Logs

```bash
databricks apps get <APP_NAME> --profile <PROFILE>
```

### Local Testing (after scaffolding)

```bash
cd <your-app-directory>
npm run dev
# Open http://localhost:8000
```

---

## Resources

- [PRE-REQUISITES.md](PRE-REQUISITES.md) — Workshop prerequisites checklist (workspace / UC / compute)
- [pre-req-mcp-setup.md](pre-req-mcp-setup.md) — MCP AppKit admin setup (`mcp-appkit-skill` + `v2v-gc-agent`)
- [AppKit workshop overview](apps_lakebase/Instructions.md) + [Genie prompts](apps_lakebase/prompts/README.md)
- [Data Product Accelerator QUICKSTART](data_product_accelerator/QUICKSTART.md) — 9-stage pipeline guide
- [Databricks AppKit Documentation](https://databricks.github.io/appkit/) — AppKit SDK reference
- [Databricks Apps Documentation](https://docs.databricks.com/dev-tools/databricks-apps/)
- [Databricks CLI Installation](https://docs.databricks.com/dev-tools/cli/install.html)
- [Agent Skills (SKILL.md) Format](https://agentskills.io)
- [Unity Catalog](https://docs.databricks.com/unity-catalog/)
- [Delta Live Tables](https://docs.databricks.com/dlt/)
- [Metric Views](https://docs.databricks.com/metric-views/)

---

## Using This Template

This is a **Git template repository**. To use it:

1. Click "Use this template" on GitHub, or clone directly
2. Choose your starting point:
   - **Build a Databricks App:** [Genie prompts](apps_lakebase/prompts/README.md) + [overview](apps_lakebase/Instructions.md); local CLI: [QUICKSTART.md](QUICKSTART.md) Path A
   - **Build a data product:** Drop a schema CSV in `data_product_accelerator/context/` and follow the [9-stage guide](data_product_accelerator/QUICKSTART.md)
   - **Build agents:** Use the prompts in `agentic-framework/agents/` to scaffold multi-agent systems
3. Iterate with your AI coding assistant — the agent skills handle the patterns

---

<div align="center">

**Ready to build? Let's go!**

```bash
git clone https://github.com/databricks-solutions/vibe-coding-workshop-template.git my-project
cd my-project
```

</div>
