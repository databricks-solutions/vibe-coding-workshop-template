# Job Submission Context vs Notebook Context

When code runs as a **Databricks job submission** rather than an interactive notebook, several assumptions about file paths and dependencies change. This guide covers the key differences and required patterns.

## CWD Differences

| Context | Current Working Directory | `sys.path` behavior |
|---------|--------------------------|---------------------|
| Interactive notebook | Notebook's parent directory | Includes notebook directory |
| Job submission | `/` (filesystem root) | Does NOT include notebook directory by default |

**Impact:** Relative paths like `open("config.yaml")` or `pathlib.Path("./data")` work in notebooks but fail in job submissions. Always use the bundle root path setup pattern from the main skill or construct absolute paths.

## MLflow `log_model()` Temp Directory Behavior

When `mlflow.pyfunc.log_model()` is called, MLflow:

1. Copies the specified `python_model` file (e.g., `agent.py`) to a **temporary directory**
2. Validates the model in that isolated temp directory
3. Packages the model for logging to the tracking server

**Consequence:** Any file referenced by relative path inside `agent.py` (such as `model_config="agent-config.yaml"`) must be **co-located with the model file** or referenced by absolute path. The temp directory will NOT contain files from the original notebook directory.

### Pattern: Packaging Config Files with log_model()

```python
import mlflow
import os

_notebook_path = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
_bundle_root = "/Workspace" + str(_notebook_path).rsplit('/src/', 1)[0]

config_path = os.path.join(_bundle_root, "src", "genai_agents", "agent-config.yaml")

mlflow.pyfunc.log_model(
    artifact_path="agent",
    python_model="agent.py",
    artifacts={"config": config_path},
)
```

Alternatively, use `code_paths` to bundle additional files:

```python
mlflow.pyfunc.log_model(
    artifact_path="agent",
    python_model="agent.py",
    code_paths=[
        os.path.join(_bundle_root, "src/genai_agents/agent-config.yaml"),
        os.path.join(_bundle_root, "src/genai_agents/tools.py"),
    ],
)
```

## `mlflow[databricks]` Dependency on Azure

On Azure Databricks, `mlflow.register_model()` and related deployment functions require Azure-specific dependencies that are NOT included in the base `mlflow` package.

| Package | Azure Support |
|---------|---------------|
| `mlflow` | Missing `azure.core`, `azure.storage` -- will raise `ModuleNotFoundError` |
| `mlflow[databricks]` | Includes all Azure dependencies -- use this |

### Symptom

```
ModuleNotFoundError: No module named 'azure.core'
```

This occurs when calling `mlflow.register_model()`, `mlflow.deployments.create_endpoint()`, or similar functions on Azure.

### Fix

In your `%pip install` cell or `requirements.txt`:

```python
%pip install --upgrade "mlflow[databricks]>=2.12.0" --quiet
dbutils.library.restartPython()
```

Or in `requirements.txt` / `pyproject.toml`:
```
mlflow[databricks]>=2.12.0
```

## `model_config` File Path Requirements

When using `model_config` parameter in `mlflow.pyfunc.log_model()`:

```python
mlflow.pyfunc.log_model(
    artifact_path="agent",
    python_model="agent.py",
    model_config="agent-config.yaml",  # relative path -- risky in job context
)
```

**In notebook context:** Works if `agent-config.yaml` is in the same directory.

**In job context:** Fails with `FileNotFoundError` because CWD is `/`, not the notebook directory.

### Safe Pattern

Always resolve `model_config` to an absolute path using the bundle root:

```python
_notebook_path = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
_bundle_root = "/Workspace" + str(_notebook_path).rsplit('/src/', 1)[0]

config_abs_path = os.path.join(_bundle_root, "src", "genai_agents", "agent-config.yaml")

mlflow.pyfunc.log_model(
    artifact_path="agent",
    python_model="agent.py",
    model_config=config_abs_path,
)
```
