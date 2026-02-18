# Vibe Coding Workshop Template

> **Build end-to-end data products on Databricks with AI-assisted development**

This template is a complete **data product builder** powered by vibe coding. Start from a raw customer schema or existing data, and build your way through the full Databricks stack — Databricks Apps with Lakebase, medallion architecture (Bronze, Silver, Gold), semantic layer, Genie Spaces, ML pipelines, and GenAI agents — all guided by 50 agent skills and your AI coding assistant.

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
| **Databricks CLI** | Yes | `curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh \| sh` |
| **AI-Powered IDE** | Yes | [Cursor](https://cursor.com), [Windsurf](https://windsurf.com), VS Code + Copilot, or similar |
| **Python 3.10+** | Yes | [python.org](https://www.python.org/downloads/) |
| **Git** | Yes | [git-scm.com](https://git-scm.com/) |

### Clone the Template

```bash
git clone https://github.com/databricks-solutions/vibe-coding-workshop-template.git my-project
cd my-project
```

### Choose Your Starting Point

#### Path A: Deploy a Databricks App

Get a FastAPI backend with Lakebase (managed PostgreSQL) running on Databricks Apps:

```bash
cd apps_lakebase
./scripts/setup.sh          # Configure auth + install deps
./scripts/deploy.sh --create # Deploy to Databricks Apps
```

After deployment, open your app URL in the browser.

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
├── apps_lakebase/                  # Databricks App (FastAPI + Lakebase)
│   ├── app.yaml                    #   Databricks App entry point config
│   ├── pyproject.toml              #   Python dependencies
│   ├── server/                     #   FastAPI backend
│   │   ├── app.py                  #     Main application
│   │   └── routers/
│   │       ├── health.py           #     Health/readiness endpoints
│   │       └── api.py              #     API endpoints (workspace, catalogs, query)
│   ├── scripts/                    #   Development & deployment scripts
│   │   ├── setup.sh                #     Configure auth & install deps
│   │   ├── deploy.sh               #     Deploy to Databricks Apps
│   │   ├── watch.sh                #     Local dev server (hot reload)
│   │   ├── run_local.sh            #     Test locally before deploying
│   │   ├── app_status.sh           #     Check deployed app status
│   │   ├── setup-lakebase.sh       #     Set up Lakebase tables
│   │   └── lakebase_manager.py     #     Lakebase connectivity & permissions
│   └── lakebase/
│       └── README.md               #   Lakebase DDL/DML reference
│
├── data_product_accelerator/       # 50 Agent Skills for End-to-End Data Products
│   ├── AGENTS.md                   #   Detailed skill routing table
│   ├── QUICKSTART.md               #   One-prompt-per-stage guide (9 stages)
│   ├── README.md                   #   Accelerator overview
│   ├── context/                    #   Schema CSV inputs (starting point)
│   │   ├── Wanderbricks_Schema.csv
│   │   └── booking_app_schema.csv
│   ├── skills/                     #   50 skills across 12 domains
│   │   ├── admin/                  #     Skill creation, auditing (4)
│   │   ├── bronze/                 #     Bronze layer + Faker data (2)
│   │   ├── common/                 #     Cross-cutting shared skills (8)
│   │   ├── exploration/            #     Ad-hoc notebooks (1)
│   │   ├── genai-agents/           #     GenAI agent patterns (9)
│   │   ├── gold/                   #     Gold design + implementation (9)
│   │   ├── ml/                     #     MLflow pipelines (1)
│   │   ├── monitoring/             #     Monitors, dashboards, alerts (5)
│   │   ├── planning/               #     Project planning (1)
│   │   ├── semantic-layer/         #     Metric Views, TVFs, Genie (6)
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
  └─► Databricks App       — FastAPI + Lakebase, deployed on Databricks Apps
```

Each stage is driven by a single prompt to your AI coding assistant. The 50 agent skills in `data_product_accelerator/` encode production-tested patterns so you get governed, high-quality output at every step.

---

## Data Product Accelerator (50 Agent Skills)

The `data_product_accelerator/` directory contains **50 agent skills** organized by domain that guide your AI assistant through the entire pipeline:

| Domain | Skills | Focus |
|--------|--------|-------|
| **Gold** | 9 | Dimensional modeling, ERDs, YAML schemas, MERGE scripts |
| **GenAI Agents** | 9 | ResponsesAgent, evaluation, deployment |
| **Common** | 8 | Asset Bundles, naming, constraints, imports |
| **Semantic Layer** | 6 | Metric Views, TVFs, Genie Spaces |
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

## Databricks App (FastAPI + Lakebase)

The `apps_lakebase/` directory contains a production-ready **FastAPI backend** with Lakebase (managed PostgreSQL) integration, deployable to Databricks Apps.

**Key features:**
- FastAPI with structured logging and CORS
- Health, readiness, and liveness endpoints
- Unity Catalog integration (catalogs, schemas, tables, SQL queries)
- Lakebase PostgreSQL connectivity
- Optional frontend serving (React/Vite from `client/build`)
- Deploy scripts for Databricks Apps platform

### App Commands

All commands run from the `apps_lakebase/` directory:

| Command | Description |
|---------|-------------|
| `./scripts/setup.sh` | Configure authentication and install dependencies |
| `./scripts/deploy.sh --create` | First deployment (creates the app) |
| `./scripts/deploy.sh` | Update existing app |
| `./scripts/deploy.sh --verbose` | Deploy with detailed output |
| `./scripts/watch.sh` | Start local dev server with hot reload |
| `./scripts/run_local.sh` | Test app locally (production mode) |
| `./scripts/setup-lakebase.sh` | Set up Lakebase tables and permissions |
| `./scripts/app_status.sh` | Check app status and URL |

### Local Development URLs

| Service | URL |
|---------|-----|
| API | http://localhost:8000 |
| API Documentation | http://localhost:8000/docs |
| Health Check | http://localhost:8000/health |
| Readiness Check | http://localhost:8000/ready |
| Frontend (if enabled) | http://localhost:5173 |

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

When you run `./scripts/deploy.sh` from `apps_lakebase/`:

```
┌────────────────────────────────────────────────────────────────────┐
│                     Deployment Process                              │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. BUILD         2. GENERATE        3. SYNC          4. DEPLOY    │
│  ────────────     ────────────       ────────────     ──────────   │
│  Frontend         requirements.txt   Files to         Start app    │
│  (if exists)      from pyproject     Workspace        runtime      │
│                                                                     │
│  client/dist/ ──► requirements.txt ──► /Workspace/... ──► App URL  │
│                                                                     │
│  5. LAKEBASE (optional)                                             │
│  ──────────────────────                                             │
│  Set permissions + create tables                                    │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

### Key Files for Deployment

| File | Purpose |
|------|---------|
| `apps_lakebase/app.yaml` | Defines how Databricks starts your app |
| `apps_lakebase/pyproject.toml` | Python dependencies |
| `apps_lakebase/server/app.py` | Your FastAPI application |

---

## Authentication

### Option 1: Personal Access Token (Recommended for Development)

1. Go to your Databricks workspace
2. Click your username > **User Settings** > **Developer** > **Access Tokens**
3. Generate a new token
4. Run `./scripts/setup.sh` (from `apps_lakebase/`) and enter your token

### Option 2: CLI Profile (Recommended for Production)

1. Configure a CLI profile:
   ```bash
   databricks auth login --host https://your-workspace.cloud.databricks.com --profile myprofile
   ```
2. Run `./scripts/setup.sh` and select "CLI Profile"
3. Enter your profile name

---

## Customizing Your App

### Adding API Endpoints

Edit `apps_lakebase/server/routers/api.py`:

```python
from fastapi import APIRouter

router = APIRouter()

@router.get("/hello")
async def hello():
    return {"message": "Hello from Databricks!"}

@router.get("/data/{table_name}")
async def get_data(table_name: str):
    from databricks.sdk import WorkspaceClient
    w = WorkspaceClient()
    # Query your data...
    return {"table": table_name}
```

### Adding Dependencies

1. Edit `apps_lakebase/pyproject.toml`:
   ```toml
   dependencies = [
       "fastapi>=0.109.0",
       "your-new-package>=1.0.0",  # Add here
   ]
   ```

2. Deploy:
   ```bash
   cd apps_lakebase
   ./scripts/deploy.sh
   ```

---

## Troubleshooting

### "App not found" error

```bash
# Make sure to use --create on first deployment
cd apps_lakebase
./scripts/deploy.sh --create
```

### Authentication failed

```bash
# Reconfigure authentication
rm .env.local
./scripts/setup.sh
```

### Check Databricks CLI

```bash
# Verify CLI is working
databricks --version
databricks current-user me
```

### View App Logs

1. Get your app URL: `./scripts/app_status.sh`
2. Open `<app-url>/logz` in your browser (requires auth)

### Local Testing

```bash
# Test locally before deploying
cd apps_lakebase
./scripts/run_local.sh
# Open http://localhost:8000
```

---

## Resources

- [PRE-REQUISITES.md](PRE-REQUISITES.md) — Workshop prerequisites checklist
- [Data Product Accelerator QUICKSTART](data_product_accelerator/QUICKSTART.md) — 9-stage pipeline guide
- [Databricks Apps Documentation](https://docs.databricks.com/dev-tools/databricks-apps/)
- [Databricks CLI Installation](https://docs.databricks.com/dev-tools/cli/install.html)
- [Databricks SDK for Python](https://docs.databricks.com/dev-tools/sdk-python.html)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Agent Skills (SKILL.md) Format](https://agentskills.io)
- [Unity Catalog](https://docs.databricks.com/unity-catalog/)
- [Delta Live Tables](https://docs.databricks.com/dlt/)
- [Metric Views](https://docs.databricks.com/metric-views/)

---

## Using This Template

This is a **Git template repository**. To use it:

1. Click "Use this template" on GitHub, or clone directly
2. Choose your starting point:
   - **Deploy an app:** `cd apps_lakebase && ./scripts/setup.sh && ./scripts/deploy.sh --create`
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
