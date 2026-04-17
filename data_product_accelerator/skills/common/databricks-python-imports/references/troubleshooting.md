# Troubleshooting Guide

Common errors and solutions for Databricks Python imports. For core rules and patterns, see the parent [SKILL.md](../SKILL.md).

## ModuleNotFoundError after restartPython()

**Symptoms:**
```python
dbutils.library.restartPython()
from config import get_config
# ModuleNotFoundError: No module named 'config'
```

**Diagnosis Steps:**
1. Check if `config.py` has `# Databricks notebook source` header
2. Verify file is in same directory as importing notebook
3. Check file has `.py` extension

**Solution:**
```python
# In config.py, remove this line if present:
# Databricks notebook source  # Remove this!

# File should start with module docstring:
"""
Configuration module
"""
```

## NameError after %run and restartPython()

**Symptoms:**
```python
%run ./config
dbutils.library.restartPython()
get_config()  # NameError: name 'get_config' is not defined
```

**Root Cause:** `restartPython()` clears all function definitions, including from `%run`

**Solution:** Use standard import instead of `%run`

```python
dbutils.library.restartPython()
from config import get_config  # Persistent import
get_config()  # Works
```

## ModuleNotFoundError: azure.core (Azure Only)

**Symptoms:**
```python
mlflow.register_model(f"models:/{model_name}/1", model_uri)
# ModuleNotFoundError: No module named 'azure.core'
```

**Root Cause:** The base `mlflow` package does not include Azure-specific dependencies. On Azure Databricks, `mlflow.register_model()` and deployment functions require `azure.core`, `azure.storage`, etc.

**Solution:** Install `mlflow[databricks]` instead of `mlflow`:

```python
%pip install --upgrade "mlflow[databricks]>=2.12.0" --quiet
dbutils.library.restartPython()
```

See [job-context-guide.md](job-context-guide.md) for full details on Azure dependency requirements.

## FileNotFoundError for model_config in Job Context

**Symptoms:**
```python
mlflow.pyfunc.log_model(
    artifact_path="agent",
    python_model="agent.py",
    model_config="agent-config.yaml",
)
# FileNotFoundError: [Errno 2] No such file or directory: 'agent-config.yaml'
```

**Root Cause:** In job submission context, CWD is `/`, not the notebook directory. Additionally, `log_model()` copies the model to a temp directory where the YAML file is absent.

**Solution:** Use an absolute path resolved from the bundle root:

```python
_notebook_path = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
_bundle_root = "/Workspace" + str(_notebook_path).rsplit('/src/', 1)[0]

config_path = os.path.join(_bundle_root, "src", "genai_agents", "agent-config.yaml")

mlflow.pyfunc.log_model(
    artifact_path="agent",
    python_model="agent.py",
    model_config=config_path,
)
```

See [job-context-guide.md](job-context-guide.md) for the complete job context patterns.

## Common Mistakes

### Mistake 1: Notebook Header in Shared Code

```python
# config.py
# Databricks notebook source  # Makes it a notebook!

def get_config():
    return {...}
```

**Fix:** Remove the notebook header

```python
# config.py
def get_config():
    return {...}
```

### Mistake 2: Trying to Import Notebook

```python
# job.py
%pip install --upgrade "databricks-sdk>=0.28.0" --quiet
dbutils.library.restartPython()

from config import get_config  # Fails if config.py is notebook
```

**Error:** `ModuleNotFoundError: No module named 'config'`

**Fix:** Convert `config.py` to pure Python file (remove notebook header)

### Mistake 3: Using %run After restartPython()

```python
# job.py
%pip install --upgrade "databricks-sdk>=0.28.0" --quiet
dbutils.library.restartPython()

%run ./config  # Doesn't work in deployed Asset Bundles

get_config()  # NameError: name 'get_config' is not defined
```

**Fix:** Convert to pure Python file and use standard import

```python
%pip install --upgrade "databricks-sdk>=0.28.0" --quiet
dbutils.library.restartPython()

from config import get_config  # Works with pure Python file

get_config()  # Available
```

### Mistake 4: Project-Specific .replace() for Path Resolution

```python
# WRONG -- hardcoded to one project name
_bundle_root = "/Workspace" + str(_notebook_path).replace("/src/booking_app", "")

# WRONG -- breaks when project is renamed
_bundle_root = "/Workspace" + str(_notebook_path).replace("/src/my_project_semantic", "")
```

**Fix:** Use the canonical `rsplit` pattern:

```python
# CORRECT -- works for any project
_bundle_root = "/Workspace" + str(_notebook_path).rsplit('/src/', 1)[0]
```
