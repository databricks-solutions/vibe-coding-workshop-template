---
name: databricks-job-runner
description: "Run Python scripts as Databricks Jobs with correct runtime constraints. Use when creating jobs for MLflow model logging, agent registration, deployment scripts, or any spark_python_task that interacts with Unity Catalog or workspace files."
metadata:
  author: stayfinder-team
  version: "1.0"
compatibility: "Databricks Runtime 14.x+, MLflow 2.10+"
---

# Databricks Job Runner

Guidance for running Python scripts as Databricks Jobs — especially for MLflow model logging, Unity Catalog registration, and agent deployment. This skill captures critical runtime constraints that are NOT obvious from documentation alone.

## When to Use This Skill

Use this skill when:
- Creating a Databricks Job that runs a Python script (`spark_python_task`)
- Logging or registering MLflow models from a workspace file
- Running `log_model.py`, `deploy_agent.py`, or similar scripts on a cluster
- Any job that writes to Unity Catalog (model registry, tables, volumes)

**Read this skill BEFORE creating any job definition.**

## Critical Runtime Constraints

### 1. `__file__` Is NOT Defined in `spark_python_task`

Databricks runs `spark_python_task` scripts via:
```python
exec(compile(f.read(), filename, 'exec'))
```

In this context, `__file__` is **undefined**. Any script that uses `__file__` (e.g., `pathlib.Path(__file__).parent`) will crash with `NameError`.

**Fix:** Never use `__file__` in scripts that run as Databricks Jobs. Use hardcoded workspace paths or environment variables instead:

```python
# BAD — will crash in spark_python_task
script_dir = pathlib.Path(__file__).parent

# GOOD — use a constant or env var
WORKSPACE_BASE = "/Workspace/Users/you@company.com/agents/my_agent"
script_dir = pathlib.Path(WORKSPACE_BASE)
```

### 2. `/Workspace/` FUSE Mount Is NOT Importable

The `/Workspace/` filesystem supports `os.path.exists()`, `os.listdir()`, and `shutil.copytree()` — but Python's `importlib` **CANNOT discover packages** from `/Workspace/` paths, even after adding them to `sys.path`.

This means `from tools.my_tool import my_function` will fail with `No module named 'tools'` if `tools/` lives under `/Workspace/`.

**Fix:** Always copy workspace files to a local POSIX path before importing or logging:

```python
import shutil, sys, os

WORKSPACE_SRC = "/Workspace/Users/you@company.com/agents/my_agent"
LOCAL_DIR = "/tmp/my_agent"

# Copy to local filesystem
if os.path.isdir(LOCAL_DIR):
    shutil.rmtree(LOCAL_DIR)
shutil.copytree(WORKSPACE_SRC, LOCAL_DIR)

# Now Python can import from here
sys.path.insert(0, LOCAL_DIR)

agent_file = os.path.join(LOCAL_DIR, "agent.py")
tools_dir = os.path.join(LOCAL_DIR, "tools")
```

### 3. MLflow `log_model()` Validates Imports at Log Time

When you call `mlflow.langchain.log_model(lc_model="agent.py", code_paths=[...])`, MLflow internally calls `importlib.util.spec_from_file_location()` to load and validate `agent.py` **before** bundling `code_paths`. This means all imports in `agent.py` must resolve at log time — not just at serving time.

**Fix:** Ensure the agent's parent directory is on `sys.path` in `log_model.py` BEFORE calling `log_model()`:

```python
sys.path.insert(0, LOCAL_DIR)  # Must happen before mlflow.*.log_model()
```

### 4. Unity Catalog Requires `SINGLE_USER` Access Mode

Any job cluster that registers models to Unity Catalog (`mlflow.register_model()`) must have:

```json
"data_security_mode": "SINGLE_USER"
```

Without this, `register_model()` will fail with:
```
PERMISSION_DENIED: Access denied to clusters that don't have Unity Catalog enabled
```

### 5. Unity Catalog Requires Explicit Model Signature

All models registered to Unity Catalog MUST have a signature with **both input AND output types**. Providing `input_example` alone is NOT sufficient — MLflow may fail to infer a complete signature, especially when using `mlflow.langchain.log_model()`.

**Fix:** Always provide an explicit signature via `mlflow.models.infer_signature()`:

```python
signature = mlflow.models.infer_signature(
    model_input={"messages": [{"role": "user", "content": "hello"}]},
    model_output={
        "choices": [{
            "message": {"role": "assistant", "content": "response"},
            "index": 0,
            "finish_reason": "stop",
        }]
    },
)

mlflow.langchain.log_model(
    lc_model=agent_file,
    artifact_path="agent",
    signature=signature,   # REQUIRED for UC registration
    input_example=input_example,
    ...
)
```

**Alternative:** Use `mlflow.pyfunc.log_model()` with `python_model="agent.py"` (as shown in the canonical `model-serving/6-logging-registration.md` skill), which auto-infers signatures more reliably than `mlflow.langchain.log_model()`.

### 6. Verify Catalog and Schema Exist Before Registration

Before running a `log_model.py` script that calls `mlflow.register_model(name="catalog.schema.model")`, verify the target catalog and schema exist:

```bash
# Check if schema exists
databricks unity-catalog schemas get <catalog>.<schema>

# If not found, create it
databricks unity-catalog schemas create --catalog-name <catalog> --name <schema>
```

If you don't know which catalog the user has access to, discover it:

```bash
# List available catalogs
databricks unity-catalog catalogs list

# List schemas in a catalog
databricks unity-catalog schemas list --catalog-name <catalog>
```

### 6. Databricks CLI Profile

Always set the CLI profile explicitly before running commands:

```bash
export DATABRICKS_CONFIG_PROFILE=<profile_name>
```

Check `~/.databrickscfg` for available profiles if unsure.

## STRONGLY RECOMMENDED: Use a Notebook First

**Every job failure costs 5-10 minutes** (cluster startup + execution + error retrieval).
A notebook attached to a running cluster gives **instant feedback**.

**Development workflow:**
1. Create an interactive cluster (16.4 LTS ML runtime)
2. `%pip install databricks-langchain langgraph langchain-core databricks-agents` in Cell 1
3. Test the agent graph locally in Cell 2: `GRAPH.invoke({"messages": [...]})`
4. Log the model in Cell 3 (instant error feedback)
5. Deploy from Cell 4
6. **Convert to a job ONLY after everything works in the notebook**

## Critical: Both `pyfunc` and `langchain` `log_model()` Import Code

**Both** `mlflow.pyfunc.log_model(python_model="agent.py")` and
`mlflow.langchain.log_model(lc_model="agent.py")` **import the file during logging**
(MLflow validates the code model). This means **all of agent.py's dependencies must
be installed** on the cluster/notebook before calling `log_model()`.

On Databricks ML runtimes, `databricks-langchain`, `langgraph`, etc. are **NOT
pre-installed**. You MUST `%pip install` them first.

## pyfunc vs langchain `log_model()` Decision Tree

| Approach | Imports at log time? | Deps needed on cluster? | `agents.deploy()` endpoint type |
|----------|---------------------|------------------------|-------------------------------|
| `mlflow.pyfunc.log_model(python_model=file)` | YES (MLflow 3.x) | YES | "pyfunc" |
| `mlflow.langchain.log_model(lc_model=file)` | YES | YES | "langchain/agent" |

**Recommendation:** Use `mlflow.pyfunc.log_model()` — it has better error handling
and signature inference. But be aware that once an endpoint is created with one type,
switching types requires deleting and recreating the endpoint (see below).

## Runtime Compatibility Matrix

| Runtime | pydantic | `databricks-langchain` pip install | `mlflow.langchain.log_model()` |
|---------|----------|-----------------------------------|-------------------------------|
| **15.4 LTS ML** | v1 (compiled .so) | **BREAKS** — upgrades to v2, conflicts with v1 .so | Broken |
| **16.4 LTS ML** | v2 | Works after `%pip install` | `langchain.schema` import fails (stale MLflow code) |

**Bottom line:** Use **16.4 LTS ML** runtime + `%pip install databricks-langchain langgraph` + `mlflow.pyfunc.log_model()`.

## `handle_tool_errors=True` is REQUIRED

When using LangGraph's `ToolNode`, **always** set `handle_tool_errors=True`:

```python
tool_node = ToolNode(ALL_TOOLS, handle_tool_errors=True)
```

Without this, if ANY tool raises an exception, the entire graph crashes and MLflow's
handler returns `null` to the caller. With it, ToolNode catches the error and returns
a `ToolMessage` with the error text, so the LLM can report it gracefully.

Also wrap the agent node in try-except:

```python
def agent_node(state: MessagesState):
    try:
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
        return {"messages": [llm_with_tools.invoke(messages)]}
    except Exception as exc:
        return {"messages": [AIMessage(content=f"Error: {exc}")]}
```

## Endpoint Type Locking (`databricks.agents.deploy()`)

`databricks.agents.deploy()` creates a serving endpoint with a **locked type** based
on the model flavour used during `log_model()`. Once created:

- A "langchain" endpoint CANNOT serve a "pyfunc" model (or vice versa)
- Error: `"Agent endpoint cannot be updated to serve non-agent models or vice-versa"`

**Fix:** Delete the old endpoint completely, then call `agents.deploy()` again to
create a fresh one with the new model type.

```python
from databricks.sdk import WorkspaceClient
w = WorkspaceClient()
w.serving_endpoints.delete("old_endpoint_name")
# Then re-deploy
from databricks import agents
agents.deploy("catalog.schema.model", "version")
```

## Standard Job Cluster Configuration

Use this template for model logging / registration jobs.

**IMPORTANT:** Always validate the spark version first:
```bash
databricks clusters spark-versions | grep "cpu-ml"
```

```json
{
  "spark_version": "16.4.x-cpu-ml-scala2.12",
  "node_type_id": "i3.xlarge",
  "num_workers": 0,
  "data_security_mode": "SINGLE_USER",
  "spark_conf": {
    "spark.master": "local[*]",
    "spark.databricks.cluster.profile": "singleNode"
  },
  "custom_tags": {
    "ResourceClass": "SingleNode"
  }
}
```

Note the `-cpu-` in the spark version — `16.4.x-ml-scala2.12` (without `-cpu-`) is INVALID.

**Speed optimization:** If the workspace has an instance pool for `i3.xlarge`, use `"instance_pool_id": "<pool_id>"` to cut cluster start time from ~4 min to ~30 sec. If a compatible cluster is already running, use `"existing_cluster_id"` to skip provisioning entirely.

## Standard Notebook Template (Recommended over Jobs)

Use this notebook template for initial development. Convert to a job only after
all cells execute successfully.

### Cell 1: Install dependencies
```python
%pip install databricks-langchain langgraph>=0.3.4 langchain-core databricks-agents databricks-sdk
dbutils.library.restartPython()
```

### Cell 2: Test agent locally
```python
import sys, os, shutil

WORKSPACE_SRC = "/Workspace/Users/<user>/agents/<agent_name>"
LOCAL_DIR = "/tmp/<agent_name>"

if os.path.isdir(LOCAL_DIR):
    shutil.rmtree(LOCAL_DIR)
shutil.copytree(WORKSPACE_SRC, LOCAL_DIR)
sys.path.insert(0, LOCAL_DIR)

# Quick smoke test
from agent import GRAPH
result = GRAPH.invoke(
    {"messages": [{"role": "user", "content": "Hello, what can you help with?"}]},
    config={"recursion_limit": 25},
)
print(result["messages"][-1].content)
```

### Cell 3: Log and register model
```python
import mlflow
from mlflow.models.resources import DatabricksServingEndpoint, DatabricksGenieSpace

REGISTERED_MODEL_NAME = "<catalog>.<schema>.<model_name>"
agent_file = os.path.join(LOCAL_DIR, "agent.py")

resources = [
    DatabricksServingEndpoint(endpoint_name="<llm_endpoint>"),
    DatabricksGenieSpace(genie_space_id="<genie_space_id>"),
]

mlflow.set_experiment("/Users/<user>/agent_experiment")

with mlflow.start_run():
    model_info = mlflow.pyfunc.log_model(
        python_model=agent_file,
        artifact_path="agent",
        resources=resources,
        pip_requirements=[
            "mlflow[databricks]>=2.10.0",
            "databricks-langchain",
            "langgraph>=0.3.4",
            "langchain-core",
            "databricks-agents",
            "databricks-sdk",
        ],
        input_example={"messages": [{"role": "user", "content": "Hello"}]},
        registered_model_name=REGISTERED_MODEL_NAME,
    )
    print(f"Model URI: {model_info.model_uri}")
```

### Cell 4: Deploy
```python
from databricks import agents

# Delete old endpoint if switching model types
# from databricks.sdk import WorkspaceClient
# WorkspaceClient().serving_endpoints.delete("old_endpoint")

deployment = agents.deploy(
    REGISTERED_MODEL_NAME,
    model_info.model_uri.split("/")[-1],  # version number
    scale_to_zero_enabled=True,
)
print(f"Endpoint: {deployment.endpoint_name}")
```

### Cell 5: Test deployed endpoint
```python
import requests
from databricks.sdk.core import Config

cfg = Config()
headers = cfg.authenticate()
headers["Content-Type"] = "application/json"
url = f"https://{cfg.host}/serving-endpoints/{deployment.endpoint_name}/invocations"

resp = requests.post(url, json={"messages": [{"role": "user", "content": "Hello"}]}, headers=headers, timeout=120)
print(resp.json())
```

## Pre-Job Checklist

Before creating or running any Databricks Job:

- [ ] Scripts do NOT use `__file__` (use workspace path constants instead)
- [ ] Scripts copy `/Workspace/` files to `/tmp/` before importing or logging
- [ ] `sys.path.insert(0, LOCAL_DIR)` runs BEFORE any `mlflow.*.log_model()` call
- [ ] Job cluster has `"data_security_mode": "SINGLE_USER"` if touching Unity Catalog
- [ ] Target `catalog.schema` exists (check via CLI before running)
- [ ] `DATABRICKS_CONFIG_PROFILE` is set for all CLI commands
- [ ] `signature` is explicitly provided via `mlflow.models.infer_signature()` (UC requires input + output)
- [ ] `pip_requirements` in `log_model()` include all runtime dependencies

## Troubleshooting

| Error | Root Cause | Fix |
|-------|-----------|-----|
| `NameError: __file__ is not defined` | `spark_python_task` uses `exec()` | Use hardcoded path constant |
| `No module named 'tools'` | `/Workspace/` FUSE not importable | `shutil.copytree()` to `/tmp/` |
| `No module named 'databricks_langchain'` | Not pre-installed on ML runtimes | `%pip install` before `log_model()` |
| `cannot import name 'model_validator' from 'pydantic'` | 15.4 runtime has pydantic v1 compiled | Use 16.4 runtime instead |
| `No module named 'langchain.schema'` | 16.4 MLflow has stale `langchain.schema` import | Use `mlflow.pyfunc.log_model()` instead of langchain |
| `PERMISSION_DENIED: clusters without UC` | Missing `data_security_mode` | Add `"SINGLE_USER"` to cluster config |
| `Model did not contain any signature metadata` | UC needs input+output signature | Add `signature=mlflow.models.infer_signature(...)` |
| `RESOURCE_DOES_NOT_EXIST: catalog.schema` | UC schema not created | `databricks schemas create` |
| `Agent endpoint cannot serve non-agent models` | Endpoint type locked from first deployment | Delete endpoint, redeploy fresh |
| `Invalid spark version 15.4.x-ml-scala2.12` | Missing `-cpu-` in version ID | Use `16.4.x-cpu-ml-scala2.12` (query API to verify) |
| `log_model() got unexpected keyword 'name'` | `mlflow.langchain.log_model` uses `artifact_path`, not `name` | Use `artifact_path="agent"` |
| Endpoint returns `null` on tool-use queries | `ToolNode` crashes on tool errors | Set `handle_tool_errors=True` on ToolNode |
| `Cannot read the python file` | `workspace import --language PYTHON` creates a notebook, not a file | Use `workspace import-dir` instead |
| `MAX_CONCURRENT_RUNS_REACHED` | Previous run still active | Cancel previous run first |
