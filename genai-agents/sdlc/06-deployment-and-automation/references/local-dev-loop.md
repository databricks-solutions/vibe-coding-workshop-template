# Local Development Loop

Complete reference for running Databricks Apps agents locally during
development. Covers the `uv run` quickstart workflow, local server
startup, evaluation, preflight checks, environment configuration, and
differences between local and deployed execution.

Grounded in:
- [Author an agent](https://docs.databricks.com/aws/en/generative-ai/agent-framework/author-agent)
- [app-templates](https://github.com/databricks/app-templates)

---

## 1. Prerequisites

### 1.1 Required Tools

| Tool | Purpose | Install |
|------|---------|---------|
| `uv` | Python package manager, script runner | [uv installation](https://docs.astral.sh/uv/getting-started/installation/) |
| `nvm` / Node 20 | Chat UI frontend build | [nvm installation](https://github.com/nvm-sh/nvm) |
| Databricks CLI | Auth, sync, bundle commands | [CLI installation](https://docs.databricks.com/aws/en/dev-tools/cli/install) |

### 1.2 Databricks CLI Authentication (IDE/local-dev only)

Configure a profile per **PRE-REQUISITES §11** before running local commands. **Genie Code:** pre-authenticated — skip profile setup; this entire local-dev loop is IDE-only. Verify:

```bash
databricks auth token
databricks current-user me
```

The local dev server uses your CLI profile for workspace authentication.
This is how it accesses serving endpoints, warehouses, and UC resources.

### 1.3 Node Version

The chat UI requires Node 20 LTS:

```bash
nvm use 20
# or
nvm install 20
```

---

## 2. Quickstart Workflow

The app-templates encode common tasks as `uv` scripts defined in
`pyproject.toml`. The typical development loop:

```bash
# 1. First-time setup (installs deps, configures environment)
uv run quickstart

# 2. Start local agent server
uv run start-app

# 3. Run evaluation (in another terminal)
uv run agent-evaluate

# 4. Pre-deployment validation
uv run preflight
```

### 2.1 `uv run quickstart`

First-time environment setup:

- Creates a virtual environment via `uv`
- Installs Python dependencies from `pyproject.toml` / `requirements.txt`
- Prompts for workspace configuration (host, warehouse ID, etc.)
- Writes a `.env` file with local overrides
- Installs Node dependencies for the chat UI (if applicable)

```bash
cd my-agent-app
uv run quickstart
```

Expected output:
```
✓ Virtual environment created
✓ Dependencies installed
? Databricks workspace host: https://your-workspace.cloud.databricks.com
? SQL Warehouse ID: abc123def456
✓ .env file written
✓ Setup complete — run `uv run start-app` to start
```

### 2.2 `uv run start-app`

Starts the MLflow AgentServer locally:

```bash
uv run start-app
```

This typically runs:
```bash
uvicorn start_server:app --host 0.0.0.0 --port 8000 --reload
```

The `--reload` flag enables hot reload: file changes trigger automatic
server restart without manual intervention.

After startup, the chat UI is available at `http://localhost:8000`.
The `/invocations` endpoint accepts agent requests.

### 2.3 `uv run agent-evaluate`

Runs the evaluation harness against the agent:

```bash
uv run agent-evaluate
```

This executes `agent_server/evaluate_agent.py` (or equivalent), which:

- Loads evaluation fixtures (test inputs and expected outputs)
- Calls the agent via the local `/invocations` endpoint or in-process
- Uses `mlflow.genai.evaluate()` to score responses
- Writes results to the configured MLflow experiment

Run evaluation after making agent changes to catch regressions.

### 2.4 `uv run preflight`

Pre-deployment validation:

```bash
uv run preflight
```

Checks performed:
- `databricks.yml` is valid (`databricks bundle validate`)
- `app.yaml` configuration is syntactically correct
- Required resources are accessible (warehouse, serving endpoint)
- Agent loads successfully under `model_uri`
- Dependencies resolve without conflicts

Always run preflight before deploying to catch issues early.

---

## 3. Environment Configuration

### 3.1 `.env` File

Local development reads environment variables from a `.env` file at the
project root. The `quickstart` script creates this, but you can also
create it manually:

```bash
# .env — local development overrides
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
DATABRICKS_TOKEN=  # leave empty to use CLI OAuth

# Agent configuration
LLM_MODEL=databricks-claude-sonnet-4-6
WAREHOUSE_ID=abc123def456

# MLflow
MLFLOW_TRACKING_URI=databricks
MLFLOW_REGISTRY_URI=databricks-uc
MLFLOW_EXPERIMENT_ID=/Shared/my-agent/dev

# Lakebase (if applicable)
LAKEBASE_HOST=your-lakebase-host.cloud.databricks.com
LAKEBASE_PORT=443
LAKEBASE_DATABASE=my_database
```

### 3.2 Environment Variable Precedence

1. Shell environment variables (highest priority)
2. `.env` file values
3. `app.yaml` defaults (only used in deployed mode)
4. Code defaults (lowest priority)

### 3.3 Required vs Optional Variables

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `DATABRICKS_HOST` | Yes | — | Workspace URL |
| `LLM_MODEL` | Yes | — | Serving endpoint name |
| `WAREHOUSE_ID` | Yes (if using SQL tools) | — | SQL warehouse for queries |
| `MLFLOW_TRACKING_URI` | No | `databricks` | MLflow tracking destination |
| `MLFLOW_EXPERIMENT_ID` | No | — | Active experiment for tracing |
| `LAKEBASE_HOST` | No | — | Lakebase endpoint (optional) |

---

## 4. Hot Reload

### 4.1 uvicorn --reload

The `start-app` script includes `--reload` by default. This watches for
Python file changes and restarts the server automatically.

Watched paths (default: current directory):
- `agent.py` — agent logic changes
- `start_server.py` — server configuration changes
- `config.yml` — agent config changes
- Any imported Python module

### 4.2 Reload Limitations

Hot reload does **not** pick up changes to:
- `pyproject.toml` / `requirements.txt` (requires `uv sync` or reinstall)
- `.env` file (requires server restart)
- `app.yaml` (only used in deployed mode)
- Node dependencies (requires `npm install`)

### 4.3 Manual Restart

If hot reload doesn't catch a change:

```bash
# Ctrl+C to stop the server
# Then restart
uv run start-app
```

---

## 5. Local vs Deployed Differences

Understanding these differences prevents "works locally, fails deployed" bugs.

### 5.1 Authentication

| Aspect | Local | Deployed |
|--------|-------|----------|
| Identity | Your user (CLI OAuth) | App service principal |
| Token source | `databricks auth token` | Auto-injected by Apps runtime |
| OBO support | Not available | Via `x-forwarded-access-token` header |
| PAT support | Works for CLI, **not for agent queries** | Not supported |

### 5.2 Environment Detection

```python
import os

def is_deployed() -> bool:
    return bool(os.environ.get("DATABRICKS_APP_NAME"))
```

| Variable | Local | Deployed |
|----------|-------|----------|
| `DATABRICKS_APP_NAME` | Not set | Set to app name |
| `DATABRICKS_RUNTIME_VERSION` | Not set | Not set (Apps != clusters) |
| `IS_IN_DB_MODEL_SERVING_ENV` | Not set | Not set (Apps != Model Serving) |

### 5.3 Resource Access

| Resource | Local | Deployed |
|----------|-------|----------|
| SQL Warehouse | Via CLI auth | Via `app.yaml` resource + SP |
| Serving Endpoint | Via CLI auth | Via `app.yaml` resource + SP |
| MLflow Experiment | Via CLI auth | Via experiment resource + SP |
| Lakebase | Direct connection (if reachable) | Via app networking + SP grants |
| Unity Catalog | Via CLI auth | Via SP grants |

### 5.4 Chat UI

| Aspect | Local | Deployed |
|--------|-------|----------|
| URL | `http://localhost:8000` | `https://<app-name>.databricksapps.com` |
| Auth | None (local only) | Databricks workspace OAuth |
| Persistent history | Typically not configured | Available via Lakebase |

---

## 6. Debugging Locally

### 6.1 Server Logs

The uvicorn server logs requests to stdout:

```bash
INFO:     127.0.0.1:54321 - "POST /invocations HTTP/1.1" 200 OK
```

Enable debug logging:

```bash
LOGLEVEL=DEBUG uv run start-app
```

### 6.2 Testing the Agent Directly

Send a request to the local server:

```bash
curl -X POST http://localhost:8000/invocations \
  -H "Content-Type: application/json" \
  -d '{
    "input": [{"role": "user", "content": "Hello"}]
  }'
```

Streaming:

```bash
curl -X POST http://localhost:8000/invocations \
  -H "Content-Type: application/json" \
  -d '{
    "input": [{"role": "user", "content": "Hello"}],
    "stream": true
  }'
```

### 6.3 Python Debugger

For step-through debugging, run uvicorn directly:

```bash
python -m debugpy --listen 5678 --wait-for-client \
  -m uvicorn start_server:app --host 0.0.0.0 --port 8000
```

Then attach your IDE debugger to port 5678.

### 6.4 MLflow Trace Inspection

Traces generated locally are written to the configured MLflow experiment.
View them in the Databricks workspace UI or locally:

```python
import mlflow
client = mlflow.MlflowClient()
traces = client.search_traces(experiment_ids=["<exp-id>"], max_results=5)
for t in traces:
    print(t.info.request_id, t.info.status)
```

---

## 7. Workflow Summary

```
┌─────────────────────────────────────────────┐
│  Local Development Loop                      │
│                                              │
│  1. uv run quickstart     (first time only)  │
│  2. uv run start-app      (start server)     │
│  3. Edit agent.py          (make changes)     │
│     ↳ auto-reload picks up changes           │
│  4. curl /invocations      (test manually)    │
│  5. uv run agent-evaluate  (run evals)        │
│  6. uv run preflight       (validate deploy)  │
│  7. databricks bundle deploy + run (deploy)   │
│                                              │
│  Repeat 3–5 until satisfied                  │
└─────────────────────────────────────────────┘
```

---

## References

- [Author an agent](https://docs.databricks.com/aws/en/generative-ai/agent-framework/author-agent) — step 3 (local dev)
- [app-templates](https://github.com/databricks/app-templates) — quickstart scripts
- [uv documentation](https://docs.astral.sh/uv/) — package manager
- [`apps-deployment-patterns.md`](apps-deployment-patterns.md) — deployment workflow
- [`querying-agents.md`](querying-agents.md) — querying deployed agents
