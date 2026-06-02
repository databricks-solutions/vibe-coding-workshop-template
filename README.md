# Vibe Coding Workshop Template

> **Build end-to-end data products on Databricks with AI-assisted development**

This template is a complete **data product builder** powered by vibe coding. Start from a raw customer schema or existing data, and build your way through the full Databricks stack — Databricks Apps with Lakebase, medallion architecture (Bronze, Silver, Gold), semantic layer, Genie Spaces, ML pipelines, and GenAI agents — all guided by 77 accelerator skills, a standalone GenAI agent course, and your AI coding assistant.

---

## What is Vibe Coding?

**Vibe Coding** is an AI-assisted development approach where you collaborate with AI tools (like Cursor, GitHub Copilot, Claude Code, Windsurf, or similar) to rapidly build, iterate, and deploy production-quality data products. Instead of writing every line from scratch, you describe what you want and let the AI handle the implementation — guided by structured agent skills that encode best practices.

---

## Quick Start

> **Workshop participants:** See [PRE-REQUISITES.md](PRE-REQUISITES.md) for the full setup checklist (workspace access, CLI, IDE, and authentication).

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

Build a full-stack TypeScript app on Databricks AppKit, guided by 10 agent skills:

1. Read the workshop guide: [apps_lakebase/Instructions.md](apps_lakebase/Instructions.md)
2. Open your AI coding assistant and prompt:

```
I want to build a Databricks App. Read @apps_lakebase/skills/01-appkit-scaffold/SKILL.md and scaffold a new AppKit project.
```

3. Follow the branch-aware workflow in Instructions.md:
   - **Phase 1:** Scaffold + build UI from a PRD, test locally (uses `01-appkit-scaffold` and `02-appkit-build` skills)
   - **Phase 2:** Deploy to Databricks Apps with mock data (uses `03-appkit-deploy` skill)
   - **Phase 3:** Setup Lakebase bundle resources (uses `04-appkit-plugin-add` and `apps_lakebase/prompts/03-setup-lakebase.md`)
   - **Phase 4:** Wire Lakebase backend locally (uses `04-appkit-plugin-add` and `05-appkit-lakebase-wiring` skills)
   - **Phase 4b (optional):** Wire Model Serving / Agent endpoint (uses `04-appkit-plugin-add` and `06-appkit-serving-wiring` skills)
   - **Phase 4c (optional):** Wire AppKit to a separate Agent App with OBO proxying (uses `06d-appkit-agent-app-proxy`)
   - **Phase 4d (optional):** Add persistent chat history and feedback (uses `07-appkit-chat-history` and `08-appkit-feedback`)
   - **Phase 5:** Deploy + E2E test with Lakebase (uses `03-appkit-deploy` skill)

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
├── PRE-REQUISITES.md               # Workshop prerequisites checklist
├── CONTRIBUTING.md                 # Contribution guidelines
├── LICENSE.md                      # License
├── SECURITY.md                     # Security policy
├── env.example                     # Environment variable template
│
├── apps_lakebase/                  # Databricks AppKit Workshop (10 agent skills)
│   ├── Instructions.md             #   Comprehensive workshop guide
│   ├── prompts/                    #   Numbered prompt files for each workshop step
│   └── skills/                     #   Agent skills for the full app lifecycle
│       ├── 00-appkit-navigator/    #     Entry-point navigator (read first)
│       ├── 01-appkit-scaffold/     #     Scaffold new AppKit projects (+ agent skills install)
│       ├── 02-appkit-build/        #     Build UI + backend from a PRD
│       ├── 03-appkit-deploy/       #     Deploy to Databricks Apps
│       ├── 04-appkit-plugin-add/   #     Add plugins (Lakebase, Analytics, Genie, Files, Serving)
│       ├── 05-appkit-lakebase-wiring/ #  Wire Lakebase DDL, API routes, frontend hooks
│       ├── 06-appkit-serving-wiring/  #  Wire Model Serving / Agent endpoint to frontend
│       ├── 06d-appkit-agent-app-proxy/ # Wire AppKit frontend to a separate Agent App
│       ├── 07-appkit-chat-history/    #  Persist chat conversations in Lakebase
│       └── 08-appkit-feedback/        #  Add thumbs feedback linked to MLflow assessments
│
├── presentations/                  # Workshop slide deck (Marp, HTML, PDF, PPTX)
│
├── genai-agents/                   # GenAI Agent Development Course
│   ├── 00-course-orchestrator/     #   Current GenAI course navigator
│   ├── PROMPT-GUIDE.md             #   Canonical Track A + AppKit 2-Apps prompts
│   ├── foundation/                 #   UC resources, MLflow, tracing, tools, AI Gateway
│   ├── tracks/                     #   Track A custom Agent Apps
│   └── sdlc/                       #   Prompt registry, evals, deployment, monitoring
│
├── data_product_accelerator/       # 77 Agent Skills for End-to-End Data Products
│   ├── AGENTS.md                   #   Detailed skill routing table
│   ├── QUICKSTART.md               #   One-prompt-per-stage guide (9 stages)
│   ├── README.md                   #   Accelerator overview
│   ├── context/                    #   Schema CSV inputs (starting point)
│   ├── skills/                     #   77 skills across 12 domains
│   │   ├── admin/                  #     Skill creation, auditing (4)
│   │   ├── bronze/                 #     Bronze layer + Faker data (2)
│   │   ├── common/                 #     Cross-cutting shared skills (8)
│   │   ├── exploration/            #     Ad-hoc notebooks (1)
│   │   ├── genai-agents/           #     GenAI course mirror, tracks, SDLC, capstone
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

Each stage is driven by a single prompt to your AI coding assistant. The 77 agent skills in `data_product_accelerator/` encode production-tested patterns so you get governed, high-quality output at every step.

---

## Data Product Accelerator (77 Agent Skills)

The `data_product_accelerator/` directory contains **77 agent skills** organized by domain that guide your AI assistant through the entire pipeline:

| Domain | Skills | Focus |
|--------|--------|-------|
| **Gold** | 14 | Dimensional modeling, design workers, pipeline workers, ERDs, MERGE scripts |
| **Semantic Layer** | 5 | Metric Views, TVFs, Genie Spaces, export/import API |
| **GenAI Agents** | 31 | Course orchestrator, foundation, Track A/B/C, SDLC, capstone, simple agent scaffold |
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

## Databricks AppKit Workshop (10 Agent Skills)

The `apps_lakebase/` directory contains **10 agent skills** and a comprehensive workshop guide for building full-stack TypeScript apps on [Databricks AppKit](https://databricks.github.io/appkit/). The app is **not pre-built** — it gets scaffolded at runtime via `databricks apps init` and built iteratively with your AI coding assistant.

**What gets built:**
- Full-stack TypeScript app (React + Tailwind CSS frontend, AppKit backend)
- Optional SQL Warehouse integration for analytics queries
- Lakebase (managed PostgreSQL) persistence (wired after the mock-data app is deployed)
- Optional agent chat with either Model Serving or a separate Agent App proxy
- Optional persistent chat history and MLflow-linked feedback
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
| `06-appkit-serving-wiring` | Wire Model Serving / Agent endpoint to frontend (streaming, invoke) |
| `06d-appkit-agent-app-proxy` | Wire an AppKit frontend to a separate Agent App with OBO forwarding |
| `07-appkit-chat-history` | Persist agent chat conversations in Lakebase with session auth |
| `08-appkit-feedback` | Add thumbs up/down feedback linked to MLflow assessments |

### Local Development (after scaffolding)

| Service | URL |
|---------|-----|
| App + API | http://localhost:8000 |
| Health Check | http://localhost:8000/health |

Start the dev server from your scaffolded app directory with `npm run dev`.

---

## GenAI Agent Development Course

The root `genai-agents/` directory is the current course entry point for production GenAI agents on Databricks. Start with `genai-agents/00-course-orchestrator/SKILL.md`, then use `genai-agents/PROMPT-GUIDE.md` for the canonical Track A + AppKit 2-Apps walkthrough.

**Canonical flow:**

```
Foundation (UC, MLflow, tracing, tools)
  → Track A custom Agent App on Databricks Apps
  → AppKit frontend proxy with OBO (`06d`)
  → Chat history + feedback (`07`, `08`)
  → SDLC pipeline (prompt registry, evals, deployment, monitoring)
```

The canonical GenAI agent skills live in the root `genai-agents/` tree; stage 9 of the data product pipeline routes into the same agent-building patterns via `genai-agents/00-course-orchestrator/SKILL.md`. For Databricks-platform reference patterns (Knowledge Assistants, Genie Spaces, Model Serving, etc.) see the upstream registry [`databricks/databricks-agent-skills`](https://github.com/databricks/databricks-agent-skills); local skills here extend or specialize those for our workshop and accelerator use cases.

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

After scaffolding your AppKit app, the workflow progresses from mock data to a wired backend, with optional branches for agent chat, a separate Agent App proxy, chat history, and feedback:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    AppKit Workshop Lifecycle                         │
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
│  Add Lakebase bundle config    Add Lakebase plugin (skill 04)      │
│  Configure endpoint + compute  DDL, API routes, frontend (skill 05)│
│  Record host in state file     Test locally with mock fallback      │
│                                                                     │
│  Optional Agent Branches                                             │
│  ───────────────────────                                             │
│  Skill 06: Model Serving / Agent endpoint                            │
│  Skill 06d: Separate Agent App proxy with OBO forwarding             │
│  Skill 07: Persistent chat history                                   │
│  Skill 08: User feedback linked to MLflow assessments                │
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

Authentication is a **client-specific, one-time setup** — the full guide lives in **[PRE-REQUISITES.md §11](PRE-REQUISITES.md)** (the single home for local auth):

- **IDE/CLI client:** authenticate the Databricks CLI locally (PRE-REQUISITES §11). Verify with `databricks current-user me`; all skills and CLI commands accept a `--profile` flag to target a specific workspace (use `--profile myprofile` when juggling multiple workspaces).
- **Genie Code client:** already authenticated to its host workspace — nothing to configure, and omit `--profile` from every command.

---

## Customizing Your App

After scaffolding, your generated AppKit app is a full-stack TypeScript project. Customize it using standard AppKit patterns:

### Adding Backend Routes

Edit `server/server.ts` in your generated app directory to add tRPC routes or custom endpoints. See the `02-appkit-build` skill for patterns.

### Adding Plugins

Use the `04-appkit-plugin-add` skill to add capabilities:

```
Read @apps_lakebase/skills/04-appkit-plugin-add/SKILL.md and add the Lakebase plugin to my app.
```

Available plugins: `analytics`, `lakebase`, `genie`, `files`, `serving`

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

Re-run the IDE/CLI auth from **[PRE-REQUISITES.md §11](PRE-REQUISITES.md)** (does not apply to Genie Code — it is pre-authenticated). Then re-verify:

```bash
databricks current-user me
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

- [PRE-REQUISITES.md](PRE-REQUISITES.md) — Workshop prerequisites checklist
- [Workshop Presentation](presentations/README.md) — Marp slide deck (HTML, PDF, PPTX)
- [AppKit Workshop Guide](apps_lakebase/Instructions.md) — Databricks App workshop guide
- [GenAI Agent Prompt Guide](genai-agents/PROMPT-GUIDE.md) — canonical Track A + AppKit 2-Apps course prompts
- [Data Product Accelerator QUICKSTART](data_product_accelerator/QUICKSTART.md) — 9-stage pipeline guide
- [Databricks AppKit Documentation](https://databricks.github.io/appkit/) — AppKit SDK reference
- [Databricks Apps Documentation](https://docs.databricks.com/dev-tools/databricks-apps/)
- [Databricks CLI Installation](https://docs.databricks.com/dev-tools/cli/install.html)
- [Agent Skills (SKILL.md) Format](https://agentskills.io)
- [Unity Catalog](https://docs.databricks.com/unity-catalog/)
- [Delta Live Tables](https://docs.databricks.com/dlt/)
- [Metric Views](https://docs.databricks.com/metric-views/)

### Authoritative upstream skill registries

For canonical Databricks-platform skills (Apps, Lakebase, Model Serving, DABs, Pipelines, Core), see [`databricks/databricks-agent-skills`](https://github.com/databricks/databricks-agent-skills). The local skills in this repo extend or specialize those for our workshop and accelerator use cases. Where a local skill genuinely derives from an upstream skill, its frontmatter records a structured `upstream_sources` entry that the freshness scanner audits for drift; lighter "see also" references appear as a `## See Also` footer in the skill body. The `databricks-solutions/ai-dev-kit` registry remains a parallel authoritative source for accelerator-specific medallion / semantic-layer / ML patterns.

---

## Using This Template

This is a **Git template repository**. To use it:

1. Click "Use this template" on GitHub, or clone directly
2. Choose your starting point:
   - **Build a Databricks App:** Follow the [AppKit workshop guide](apps_lakebase/Instructions.md) — scaffold, build, deploy, and wire Lakebase
   - **Build a data product:** Drop a schema CSV in `data_product_accelerator/context/` and follow the [9-stage guide](data_product_accelerator/QUICKSTART.md)
   - **Build a GenAI agent:** Start with [genai-agents/00-course-orchestrator/SKILL.md](genai-agents/00-course-orchestrator/SKILL.md) and use [genai-agents/PROMPT-GUIDE.md](genai-agents/PROMPT-GUIDE.md) for the AppKit 2-Apps walkthrough
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
