# Vibe Coding Workshop Template

> **Build and deploy Databricks Apps with AI-assisted development**

This template provides everything you need to build and deploy full-stack applications on the **Databricks Apps** platform — from a FastAPI backend with Lakebase integration to a complete data product accelerator with 50 agent skills.

---

## What is Vibe Coding?

**Vibe Coding** is an AI-assisted development approach where you collaborate with AI tools (like Cursor, GitHub Copilot, Claude Code, Windsurf, or similar) to rapidly build, iterate, and deploy production-quality code.

---

## Quick Start (5 minutes)

### Prerequisites

| Tool | Required | Installation |
|------|----------|-------------|
| **Databricks Workspace** | Yes | Access to a Databricks workspace with Unity Catalog |
| **Databricks CLI** | Yes | `curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh \| sh` |
| **Python 3.10+** | Yes | [python.org](https://www.python.org/downloads/) |
| **Git** | Yes | [git-scm.com](https://git-scm.com/) |
| **Node.js** | Optional | For frontend development |

### Step 1: Clone the Template

```bash
git clone https://github.com/YOUR_ORG/vibe-coding-workshop-template.git my-app
cd my-app
```

### Step 2: Run Setup

The setup script configures authentication and installs dependencies:

```bash
cd apps_lakebase
./scripts/setup.sh
```

You'll be prompted to:
1. Choose authentication method (PAT or CLI profile)
2. Enter your Databricks workspace URL
3. Enter your access token (get from Workspace > User Settings > Access Tokens)
4. Name your app

### Step 3: Deploy to Databricks

```bash
# First deployment (creates the app)
./scripts/deploy.sh --create

# Subsequent deployments
./scripts/deploy.sh
```

### Step 4: Open Your App

After deployment, you'll see your app URL:
```
App URL: https://your-app.cloud.databricks.com
```

Open the URL in your browser to see your running app.

---

## Project Structure

This repository is organized as a **monorepo** with three major components:

```
vibe-coding-workshop-template/
│
├── README.md                       # This file
├── QUICKSTART.md                   # Minimal quick-deploy guide
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
├── agent_skills/                   # Agent Skills Framework (YAML-driven orchestration)
│   ├── README.md                   #   Framework documentation
│   ├── models.py                   #   Pydantic models
│   ├── registry.py                 #   Skill/flow discovery
│   ├── engine.py                   #   Flow orchestration engine
│   ├── router.py                   #   FastAPI router integration
│   ├── prd_mapper.py               #   PRD-to-skills generator
│   ├── skill_registry.yaml         #   Master registry config
│   ├── skills/                     #   Skill manifests (YAML)
│   │   ├── query_rewriter/
│   │   ├── genie_search/
│   │   ├── web_search/
│   │   ├── web_result_summarizer/
│   │   ├── lakebase_search/
│   │   └── location_extractor/
│   ├── flows/                      #   Flow definitions (YAML pipelines)
│   │   ├── assistant_search.yaml
│   │   └── standard_search.yaml
│   ├── executors/                  #   Typed executor classes
│   │   ├── llm_executor.py         #     Databricks model serving
│   │   ├── genie_executor.py       #     Databricks Genie Space
│   │   ├── web_search_executor.py  #     External web search
│   │   ├── lakebase_executor.py    #     Lakebase PostgreSQL
│   │   ├── function_executor.py    #     Python functions
│   │   └── prompt_registry_executor.py  # Databricks Prompt Registry
│   └── tests/                      #   Test suite
│
└── data_product_accelerator/       # 50 Agent Skills for Data Products
    ├── AGENTS.md                   #   Universal entry point (routing table)
    ├── QUICKSTART.md               #   One-prompt-per-stage guide
    ├── README.md                   #   Accelerator overview
    ├── context/                    #   Schema CSV inputs
    │   ├── Wanderbricks_Schema.csv
    │   └── booking_app_schema.csv
    ├── skills/                     #   50 skills across 12 domains
    │   ├── admin/                  #     Skill creation, auditing (4)
    │   ├── bronze/                 #     Bronze layer + Faker data (2)
    │   ├── common/                 #     Cross-cutting shared skills (8)
    │   ├── exploration/            #     Ad-hoc notebooks (1)
    │   ├── genai-agents/           #     GenAI agent patterns (9)
    │   ├── gold/                   #     Gold design + implementation (9)
    │   ├── ml/                     #     MLflow pipelines (1)
    │   ├── monitoring/             #     Monitors, dashboards, alerts (5)
    │   ├── planning/               #     Project planning (1)
    │   ├── semantic-layer/         #     Metric Views, TVFs, Genie (6)
    │   ├── silver/                 #     DLT pipelines, DQ rules (3)
    │   └── skill-navigator/        #     Master routing system (1)
    └── docs/                       #   Framework design documentation
```

---

## Components

### 1. Databricks App (`apps_lakebase/`)

A production-ready **FastAPI backend** with Lakebase (PostgreSQL) integration, deployable to Databricks Apps.

**Key features:**
- FastAPI with structured logging and CORS
- Health, readiness, and liveness endpoints
- Unity Catalog integration (catalogs, schemas, tables, SQL queries)
- Lakebase PostgreSQL connectivity
- Optional frontend serving (React/Vite from `client/build`)
- Deploy scripts for Databricks Apps platform

### 2. Agent Skills Framework (`agent_skills/`)

A dynamic, **declarative framework** for building agentic search and data pipelines. Skills are defined as YAML manifests and composed into flows — no hardcoded orchestration logic.

**Supported skill types:**

| Type | Description |
|------|-------------|
| `llm_call` | Databricks model serving |
| `genie_query` | Databricks Genie Space |
| `web_search` | External web search (SerpAPI, Bing) |
| `lakebase_query` | Lakebase PostgreSQL queries |
| `function` | Arbitrary Python functions |
| `prompt_registry` | Databricks Prompt Registry |

See [agent_skills/README.md](agent_skills/README.md) for full documentation.

### 3. Data Product Accelerator (`data_product_accelerator/`)

**50 agent skills** that teach your AI coding assistant to build fully governed Databricks data products — from a schema CSV to production AI agents.

**Design-First Pipeline (9 stages):**

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

See [data_product_accelerator/README.md](data_product_accelerator/README.md) and [data_product_accelerator/QUICKSTART.md](data_product_accelerator/QUICKSTART.md) for the full guide.

---

## Commands Reference

All app commands are run from the `apps_lakebase/` directory.

### Setup & Development

| Command | Description |
|---------|-------------|
| `./scripts/setup.sh` | Configure authentication and install dependencies |
| `./scripts/watch.sh` | Start local dev server with hot reload |
| `./scripts/run_local.sh` | Test app locally (production mode) |
| `./scripts/setup-lakebase.sh` | Set up Lakebase tables and permissions |

### Deployment

| Command | Description |
|---------|-------------|
| `./scripts/deploy.sh --create` | First deployment (creates the app) |
| `./scripts/deploy.sh` | Update existing app |
| `./scripts/deploy.sh --verbose` | Deploy with detailed output |
| `./scripts/app_status.sh` | Check app status and URL |
| `./scripts/app_status.sh --verbose` | Detailed status with workspace files |

### Local Development URLs

| Service | URL |
|---------|-----|
| API | http://localhost:8000 |
| API Documentation | http://localhost:8000/docs |
| Health Check | http://localhost:8000/health |
| Readiness Check | http://localhost:8000/ready |
| Frontend (if enabled) | http://localhost:5173 |

### Agent Skills Framework

| Command | Description |
|---------|-------------|
| `pytest agent_skills/tests/ -v` | Run agent skills test suite |
| `curl POST /api/skills/execute/{flow_id}` | Execute a flow via API |
| `curl GET /api/skills/registry` | List all registered skills and flows |
| `curl GET /api/skills/health` | Check framework health |

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

### Integrating the Agent Skills Framework

Add the skills router to your FastAPI app:

```python
from agent_skills.router import router as skills_router

app.include_router(skills_router, prefix="/api", tags=["Agent Skills"])
```

Then execute flows via API:

```bash
curl -X POST http://localhost:8000/api/skills/execute/assistant_search \
  -H "Content-Type: application/json" \
  -d '{"inputs": {"message": "Find hotels near Taylor Swift concert in Miami"}}'
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

## Data Product Accelerator Skills

The `data_product_accelerator/` directory contains **50 agent skills** organized by domain:

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

See [data_product_accelerator/QUICKSTART.md](data_product_accelerator/QUICKSTART.md) for the step-by-step guide.

---

## Resources

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
2. Run setup: `cd apps_lakebase && ./scripts/setup.sh`
3. Add your API endpoints in `apps_lakebase/server/routers/api.py`
4. Deploy: `./scripts/deploy.sh --create`
5. Use the Data Product Accelerator skills to build your data platform

---

<div align="center">

**Ready to build? Let's go!**

```bash
cd apps_lakebase && ./scripts/setup.sh && ./scripts/deploy.sh --create
```

</div>
