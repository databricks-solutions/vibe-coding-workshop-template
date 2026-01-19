# 🎸 Vibe Coding Workshop Template

> **Build and deploy Databricks Apps with AI-assisted development**

This template provides everything you need to build and deploy full-stack applications on the **Databricks Apps** platform. Use it as a starting point for your own projects.

---

## 🎯 What is Vibe Coding?

**Vibe Coding** is an AI-assisted development approach where you collaborate with AI tools (like Cursor, GitHub Copilot, or similar) to rapidly build, iterate, and deploy production-quality code.

---

## 🚀 Quick Start (5 minutes)

### Prerequisites

Before you begin, you need:

| Tool | Required | Installation |
|------|----------|-------------|
| **Databricks Workspace** | ✅ | Access to a Databricks workspace |
| **Databricks CLI** | ✅ | `curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh \| sh` |
| **Python 3.10+** | ✅ | [python.org](https://www.python.org/downloads/) |
| **Git** | ✅ | [git-scm.com](https://git-scm.com/) |
| **Node.js** | Optional | For frontend development |
| **jq** | Optional | For JSON parsing in scripts |

### Step 1: Clone the Template

```bash
# Clone this template
git clone https://github.com/YOUR_ORG/vibe-coding-workshop-template.git my-app
cd my-app
```

### Step 2: Run Setup

The setup script configures authentication and installs dependencies:

```bash
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
🎉 Deployment complete!

  App URL: https://your-app.cloud.databricks.com
```

Open the URL in your browser to see your running app!

---

## 📁 Project Structure

```
my-app/
│
├── app.yaml                  # Databricks App entry point config
├── pyproject.toml           # Python dependencies
├── requirements.txt         # Generated for deployment (auto-created)
│
├── scripts/                 # 🔧 Development & Deployment Scripts
│   ├── setup.sh            # Configure auth & install deps
│   ├── deploy.sh           # Deploy to Databricks Apps
│   ├── watch.sh            # Local dev server (hot reload)
│   ├── app_status.sh       # Check deployed app status
│   ├── run_local.sh        # Test locally before deploying
│   └── fix.sh              # Format code
│
├── server/                  # 🔧 FastAPI Backend
│   ├── app.py              # Main application
│   └── routers/
│       ├── health.py       # Health check endpoint
│       └── api.py          # Your API endpoints
│
├── client/                  # 🖥️ Frontend (optional)
│   └── ...                 # React/Vite app
│
└── context/                # 📋 Workshop Materials
    ├── prompts/           # AI prompts for building features
    │   ├── 01-bronze-layer-prompt.md
    │   ├── 02-silver-layer-prompt.md
    │   └── ... (17 prompts total)
    └── booking_app_schema.csv  # Sample data schema
```

---

## 🔧 Commands Reference

### Setup & Development

| Command | Description |
|---------|-------------|
| `./scripts/setup.sh` | Configure authentication and install dependencies |
| `./scripts/watch.sh` | Start local dev server with hot reload |
| `./scripts/watch.sh --stop` | Stop the dev server |
| `./scripts/run_local.sh` | Test app locally (production mode) |
| `./scripts/fix.sh` | Format code (Python + JS) |

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
| Frontend (if enabled) | http://localhost:5173 |

---

## 📦 How Deployment Works

When you run `./scripts/deploy.sh`, the following happens:

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Deployment Process                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. BUILD          2. GENERATE         3. SYNC           4. DEPLOY  │
│  ─────────────     ─────────────       ─────────────     ───────────│
│  Frontend          requirements.txt    Files to          Start app  │
│  (if exists)       from pyproject      Workspace         runtime    │
│                                                                      │
│  client/dist/ ──► requirements.txt ──► /Workspace/... ──► App URL   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Key Files for Deployment

| File | Purpose |
|------|---------|
| `app.yaml` | Defines how Databricks starts your app |
| `requirements.txt` | Python dependencies (auto-generated) |
| `server/app.py` | Your FastAPI application |

---

## 🔐 Authentication

### Option 1: Personal Access Token (Recommended for Development)

1. Go to your Databricks workspace
2. Click your username > **User Settings** > **Developer** > **Access Tokens**
3. Generate a new token
4. Run `./scripts/setup.sh` and enter your token

### Option 2: CLI Profile (Recommended for Production)

1. Configure a CLI profile:
   ```bash
   databricks auth login --host https://your-workspace.cloud.databricks.com --profile myprofile
   ```
2. Run `./scripts/setup.sh` and select "CLI Profile"
3. Enter your profile name

---

## 🛠️ Customizing Your App

### Adding API Endpoints

Edit `server/routers/api.py`:

```python
from fastapi import APIRouter

router = APIRouter()

@router.get("/hello")
async def hello():
    return {"message": "Hello from Databricks!"}

@router.get("/data/{table_name}")
async def get_data(table_name: str):
    # Add your Databricks SDK logic here
    from databricks.sdk import WorkspaceClient
    w = WorkspaceClient()
    # Query your data...
    return {"table": table_name}
```

### Adding Dependencies

1. Edit `pyproject.toml`:
   ```toml
   dependencies = [
       "fastapi>=0.109.0",
       "your-new-package>=1.0.0",  # Add here
   ]
   ```

2. Regenerate requirements.txt:
   ```bash
   python scripts/generate_requirements.py
   ```

3. Deploy:
   ```bash
   ./scripts/deploy.sh
   ```

---

## 🐛 Troubleshooting

### "App not found" error

```bash
# Make sure to use --create on first deployment
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
./scripts/run_local.sh
# Open http://localhost:8000
```

---

## 📋 Workshop Prompts

This template includes **17 AI prompts** in `context/prompts/` for building complete data applications:

| Category | Prompts |
|----------|---------|
| **Core Architecture** | Bronze, Silver, Gold layer setup |
| **Semantic Layer** | Metric Views, Table-Valued Functions, Dashboards |
| **Observability** | Monitoring, Data Quality (DQX) |
| **Advanced** | ML Models, AI Agents, Alerts |

See [context/prompts/README.md](context/prompts/README.md) for the full catalog.

---

## 📖 Resources

- [Databricks Apps Documentation](https://docs.databricks.com/dev-tools/databricks-apps/)
- [Databricks CLI Installation](https://docs.databricks.com/dev-tools/cli/install.html)
- [Databricks SDK for Python](https://docs.databricks.com/dev-tools/sdk-python.html)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

---

## 🤝 Using This Template

This is a **Git template repository**. To use it:

1. Click "Use this template" on GitHub, or clone directly
2. Customize the app name in `./scripts/setup.sh`
3. Add your API endpoints in `server/routers/api.py`
4. Deploy with `./scripts/deploy.sh --create`

---

<div align="center">

**Ready to build? Let's go! 🚀**

```bash
./scripts/setup.sh && ./scripts/deploy.sh --create
```

</div>
