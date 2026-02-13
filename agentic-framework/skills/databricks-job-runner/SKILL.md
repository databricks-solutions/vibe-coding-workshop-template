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

## Standard Job Cluster Configuration

Use this template for model logging / registration jobs:

```json
{
  "spark_version": "16.2.x-cpu-ml-scala2.12",
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

**Speed optimization:** If the workspace has an instance pool for `i3.xlarge`, use `"instance_pool_id": "<pool_id>"` to cut cluster start time from ~4 min to ~30 sec. If a compatible cluster is already running, use `"existing_cluster_id"` to skip provisioning entirely.

## Standard `log_model.py` Template

```python
"""Log and register an agent model in Unity Catalog."""
import os
import sys
import shutil

import mlflow
from mlflow.models.resources import DatabricksServingEndpoint, DatabricksGenieSpace

# --- Config ---
WORKSPACE_SRC = "/Workspace/Users/<user>/agents/<agent_name>"
LOCAL_DIR = "/tmp/<agent_name>"
REGISTERED_MODEL_NAME = "<catalog>.<schema>.<model_name>"

GENIE_SPACE_ID = os.getenv("GENIE_SPACE_ID", "")
LLM_ENDPOINT_NAME = os.getenv("LLM_ENDPOINT_NAME", "databricks-meta-llama-3-3-70b-instruct")

# --- Copy to local FS (required for importlib) ---
if os.path.isdir(LOCAL_DIR):
    shutil.rmtree(LOCAL_DIR)
shutil.copytree(WORKSPACE_SRC, LOCAL_DIR)
sys.path.insert(0, LOCAL_DIR)

agent_file = os.path.join(LOCAL_DIR, "agent.py")
tools_dir = os.path.join(LOCAL_DIR, "tools")

# --- MLflow setup ---
experiment_name = os.getenv(
    "MLFLOW_EXPERIMENT_NAME",
    f"/Users/<user>/agent_experiment",
)
mlflow.set_experiment(experiment_name)

# --- Resources for auto-auth in Model Serving ---
resources = [
    DatabricksServingEndpoint(endpoint_name=LLM_ENDPOINT_NAME),
]
if GENIE_SPACE_ID:
    resources.append(DatabricksGenieSpace(genie_space_id=GENIE_SPACE_ID))

# --- Pip requirements ---
pip_requirements = [
    "mlflow[databricks]>=2.10.0",
    "databricks-langchain",
    "langgraph>=0.3.4",
    "langchain-core",
    "databricks-agents",
    "databricks-sdk",
]

# --- Input example ---
input_example = {
    "messages": [{"role": "user", "content": "Hello"}]
}

# --- Signature (required for UC registration) ---
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

# --- Log and register ---
with mlflow.start_run():
    model_info = mlflow.langchain.log_model(
        lc_model=agent_file,
        artifact_path="agent",
        code_paths=[tools_dir],
        input_example=input_example,
        signature=signature,
        resources=resources,
        pip_requirements=pip_requirements,
    )
    print(f"Logged model URI: {model_info.model_uri}")

    uc_model_info = mlflow.register_model(
        model_uri=model_info.model_uri,
        name=REGISTERED_MODEL_NAME,
    )
    print(f"Registered: {uc_model_info.name} v{uc_model_info.version}")
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
| `PERMISSION_DENIED: clusters without UC` | Missing `data_security_mode` | Add `"SINGLE_USER"` to cluster config |
| `Model did not contain any signature metadata` | UC needs input+output signature | Add `signature=mlflow.models.infer_signature(...)` |
| `RESOURCE_DOES_NOT_EXIST: catalog.schema` | UC schema not created | `databricks schemas create` |
| `Cannot read the python file` | `workspace import --language PYTHON` creates a notebook, not a file | Use `workspace import-dir` instead |
| `MAX_CONCURRENT_RUNS_REACHED` | Previous run still active | Cancel previous run first |
