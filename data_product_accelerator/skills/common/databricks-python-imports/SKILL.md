---
name: databricks-python-imports
description: Patterns for sharing code between Databricks notebooks using pure Python files and standard imports. Covers Asset Bundle path setup (rsplit canonical pattern), notebook-to-module conversion, import patterns vs %run magic commands, job submission context vs notebook context, MLflow model packaging path requirements, and troubleshooting ModuleNotFoundError. Use when creating shared modules, deploying jobs that import local code, or packaging MLflow models with local dependencies.
metadata:
  author: prashanth subrahmanyam
  version: "1.1"
  domain: infrastructure
  role: shared
  used_by_stages: [1, 2, 3, 4, 5, 6, 7, 8, 9]
  last_verified: "2026-06-02"
  volatility: medium
  clients: [ide_cli, genie_code]   # deploy via databricks-asset-bundles (the spine); Genie detail via genie-code-environment
  deploy_verb: "bundle deploy --target dev"
  deploy_note: "import/path patterns are client-agnostic; relative ../.. links are repo-relative skill cross-refs (RULE_6: portable, retained)"
  coverage: all_stages
  upstream_sources:
    - name: "databricks-agent-skills"
      repo: "databricks/databricks-agent-skills"
      paths:
        - "skills/databricks-core/SKILL.md"
      relationship: "reference"
      last_synced: "2026-08-30"
      sync_commit: "ca92a6c"
---
# Databricks Python Imports and Code Sharing

## CRITICAL: Canonical Path Resolution

The ONLY acceptable pattern for computing the Asset Bundle root is `rsplit`:

```python
_bundle_root = "/Workspace" + str(_notebook_path).rsplit('/src/', 1)[0]
```

NEVER use project-specific `.replace()` calls. This is the #1 failure mode observed in production.

| Pattern | Verdict |
|---------|---------|
| `rsplit('/src/', 1)[0]` | CORRECT -- works for any project |
| `.replace("/src/my_project", "")` | WRONG -- breaks when project name changes |
| `.replace("/src/booking_app_semantic", "")` | WRONG -- hardcoded to one project |

## Shared Helper: `_notebook_paths.py` (PREFERRED)

**New scripts must use the shared helper — do not re-implement bundle-root resolution inline.**

- **Source of truth:** [`assets/_notebook_paths.py`](assets/_notebook_paths.py)
- **Exports:** `resolve_bundle_root`, `ensure_bundle_root_on_path`, `bundle_path`, `fail_loud`
- **Scaffold placement:** copy to `src/common/_notebook_paths.py` in the generated project so every notebook can import it with `from src.common._notebook_paths import ...`.

### Canonical notebook header (new scripts)

```python
# Databricks notebook source
import sys, os
from pathlib import Path

# Minimal bootstrap: prepend bundle root to sys.path so we can import the helper.
try:
    _nb = (
        dbutils.notebook.entry_point.getDbutils()
        .notebook().getContext().notebookPath().get()
    )
    _root = "/Workspace" + str(_nb).rsplit("/src/", 1)[0]
    if _root not in sys.path:
        sys.path.insert(0, _root)
except Exception:
    pass  # Local execution

from src.common._notebook_paths import ensure_bundle_root_on_path, bundle_path, fail_loud

BUNDLE_ROOT = ensure_bundle_root_on_path(verbose=True)
# ... the rest of your notebook follows ...
```

### Fail-loud rule (CRITICAL)

**Never use `sys.exit(0)` to report a failure.** Exit code 0 is success — Databricks Jobs will mark the run as green and silently propagate broken deploys to downstream tasks.

| Pattern | Verdict |
|---------|---------|
| `raise RuntimeError("…")` / `fail_loud("…")` | CORRECT — job marked FAILED, traceback visible |
| `sys.exit(0)` after printing an error | WRONG — run shows green, failure hidden |
| `sys.exit(1)` | Acceptable for top-level CLI; prefer `raise` in notebooks |

### `__file__` is undefined in notebook cells

Do not use `__file__` to locate asset files inside a Databricks notebook — it raises `NameError` once the code runs in the notebook context. Always use `bundle_path("src", "semantic", "metric_views", "revenue.yaml")` (or the raw `rsplit` pattern) instead.

## When NOT to Use This Skill

Skip this skill entirely when:
- Single-notebook scenarios with no cross-notebook imports
- Notebooks that don't share code with other notebooks or pure Python modules
- Pure SQL notebooks or `%run`-only workflows without `restartPython()`

## Core Principle: Pure Python Files for Importable Code

**Key Rule:** To share code between Databricks notebooks using standard Python imports, the shared code must be a **pure Python file (.py)**, not a Databricks notebook.

**Reference:** [Share code between Databricks notebooks](https://docs.databricks.com/aws/en/notebooks/share-code)

## ⚠️ CRITICAL: Asset Bundle Path Setup

**When deploying notebooks via Databricks Asset Bundles**, you MUST add a `sys.path` setup block to enable imports from other folders. Without this, you'll get `ModuleNotFoundError: No module named 'src'`.

### Required Path Setup Pattern

Add this block immediately after `# Databricks notebook source`:

```python
# Databricks notebook source
# ===========================================================================
# PATH SETUP FOR ASSET BUNDLE IMPORTS
# ===========================================================================
# This enables imports from src.ml.config and src.ml.utils when deployed
# via Databricks Asset Bundles. The bundle root is computed dynamically.
# Reference: https://docs.databricks.com/aws/en/notebooks/share-code
import sys
import os

try:
    # Get current notebook path and compute bundle root
    _notebook_path = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
    _bundle_root = "/Workspace" + str(_notebook_path).rsplit('/src/', 1)[0]
    if _bundle_root not in sys.path:
        sys.path.insert(0, _bundle_root)
        print(f"✓ Added bundle root to sys.path: {_bundle_root}")
except Exception as e:
    print(f"⚠ Path setup skipped (local execution): {e}")
# ===========================================================================
"""
Your notebook docstring here...
"""
# COMMAND ----------

# Now imports work!
from src.ml.config.feature_registry import FeatureRegistry
from src.ml.utils.training_base import setup_training_environment
```

### Why This Is Needed

1. **Asset Bundles deploy to `/Workspace/.bundle/<target>/files/`**
2. **The Python path doesn't include the bundle root by default**
3. **This setup dynamically computes the bundle root from the notebook path**

### Script to Add Path Setup

Use `scripts/add_path_setup_to_notebooks.py` to batch-add this setup to all notebooks:

```bash
python3 scripts/add_path_setup_to_notebooks.py
```

## File Type Identification

### Pure Python File (✅ Importable)

```python
"""
Module documentation

This file can be imported using standard Python imports.
"""

from databricks.sdk import WorkspaceClient
import pyspark.sql.types as T

def get_configuration():
    """Shared function"""
    return {...}
```

**Characteristics:**
- ✅ No special Databricks headers
- ✅ Standard Python module structure
- ✅ Can be imported with `from module import function`
- ✅ Works after `dbutils.library.restartPython()`

### Databricks Notebook (❌ Not Importable)

```python
# Databricks notebook source

"""
Module documentation

This file CANNOT be imported using standard Python imports.
"""

from databricks.sdk import WorkspaceClient
import pyspark.sql.types as T

def get_configuration():
    """Shared function"""
    return {...}
```

**Characteristics:**
- ❌ Has `# Databricks notebook source` header
- ❌ Cannot be imported after `restartPython()`
- ❌ Must use `%run` magic command (doesn't persist after restart)
- ✅ Can be executed as a job/task

## Pattern Recognition

### When You See Import Errors After restartPython()

```python
# Notebook with restartPython()
%pip install --upgrade "databricks-sdk>=0.28.0" --quiet
dbutils.library.restartPython()

# Databricks notebook source

from monitor_configs import get_all_monitor_configs  # ❌ ModuleNotFoundError

# This fails if monitor_configs.py is a Databricks notebook!
```

**Checklist:**
1. ✅ Check if the module file has `# Databricks notebook source` header
2. ✅ If present, remove it to convert to pure Python file
3. ✅ Test import - should work with standard Python import
4. ❌ Don't create complex workarounds (code duplication, sys.path manipulation)

## Conversion Pattern

To convert a Databricks notebook to an importable pure Python file, remove the `# Databricks notebook source` header line. That is the only change required. See [references/import-patterns-and-examples.md](references/import-patterns-and-examples.md) for a detailed before/after walkthrough.

## Import Patterns

### ✅ CORRECT: Standard Python Import

```python
# notebook.py (Databricks notebook)

%pip install --upgrade "databricks-sdk>=0.28.0" --quiet

# Databricks notebook source

dbutils.library.restartPython()

# Databricks notebook source

# ✅ Works if config_module.py is a pure Python file
from config_module import get_configuration

from databricks.sdk import WorkspaceClient
...

def main():
    config = get_configuration()  # ✅ Available
    ...
```

**Requirements:**
- `config_module.py` must be a **pure Python file** (no notebook header)
- Place import **after** `restartPython()` block
- Use standard Python import syntax

### ❌ WRONG: Complex Workarounds

```python
# ❌ DON'T: Use %run (doesn't work after restartPython() in Asset Bundles)
%run ./config_module

# ❌ DON'T: Manipulate sys.path
import sys
sys.path.insert(0, "/some/path")

# ❌ DON'T: Duplicate code
def get_configuration():  # Duplicated from another file
    return {...}

# ❌ DON'T: Use exec() or eval()
exec(open("config_module.py").read())
```

**Why These Fail:**
- `%run` doesn't persist after `restartPython()` in deployed .py files
- `sys.path` manipulation doesn't help if file is a notebook
- Code duplication creates maintenance burden
- `exec()` is a security risk and hard to debug

## Job Submission Context vs Notebook Context

When code runs as a **job submission** (not interactive notebook), key differences apply:

- **CWD is `/`**, not the notebook directory -- relative file paths fail
- **MLflow `log_model()` copies code to a temp directory** -- relative file references (e.g., `model_config="agent-config.yaml"`) will fail unless the file is co-located or referenced with an absolute path
- **`mlflow[databricks]`** is required on Azure (not just `mlflow`) -- without it, `mlflow.register_model()` raises `ModuleNotFoundError: azure.core`

See [references/job-context-guide.md](references/job-context-guide.md) for full patterns and examples.

## Use Cases and Examples

Common patterns: shared configuration modules (monitor configs, DQ rules), utility functions used across layers (Bronze/Silver/Gold), and helper functions (surrogate keys, transformations). See [references/import-patterns-and-examples.md](references/import-patterns-and-examples.md) for detailed code examples and a decision table for when to use pure Python files vs notebooks vs `%run`.

## Common Mistakes and Troubleshooting

See [references/troubleshooting.md](references/troubleshooting.md) for diagnosis steps and fixes for:
- `ModuleNotFoundError` after `restartPython()` (notebook header issue)
- `NameError` after `%run` and `restartPython()` (use standard import)
- `ModuleNotFoundError: azure.core` on Azure (use `mlflow[databricks]`)
- `FileNotFoundError` for `model_config` YAML in job context (use absolute paths)
- Project-specific `.replace()` anti-pattern (use `rsplit`)

## Validation Checklist

When creating shared code:

- [ ] File is pure Python (no `# Databricks notebook source` header)
- [ ] Has proper docstring explaining purpose
- [ ] Functions are well-documented
- [ ] Can be imported with standard `import` or `from ... import ...`
- [ ] Works after `restartPython()` if needed
- [ ] Used in at least 2 notebooks (if not, consider inlining)

When importing shared code:

- [ ] Import statement after `restartPython()` block
- [ ] Using standard Python import (not `%run`)
- [ ] Source file is pure Python file
- [ ] No sys.path manipulation needed
- [ ] No code duplication

When using Asset Bundle path setup:

- [ ] Uses `rsplit('/src/', 1)[0]` -- NEVER `.replace()` with project-specific strings
- [ ] Path setup block is immediately after `# Databricks notebook source`
- [ ] On Azure with MLflow: using `mlflow[databricks]`, not just `mlflow`

## References

- [Share code between Databricks notebooks](https://docs.databricks.com/aws/en/notebooks/share-code) - Official documentation
- [Work with Python and R modules](https://docs.databricks.com/repos/work-with-notebooks-other-files.html#work-with-python-and-r-modules)
- [dbutils.library.restartPython()](https://docs.databricks.com/dev-tools/databricks-utils.html#library-utilities)

## Related Patterns

- [Databricks Asset Bundles Configuration](../databricks-asset-bundles/SKILL.md) - Deployment patterns
- [Lakehouse Monitoring Patterns](../../monitoring/01-lakehouse-monitoring-comprehensive/SKILL.md) - Monitor configuration sharing
- [DLT Expectations Patterns](../../silver/dlt-expectations-patterns/SKILL.md) - DQ rules sharing

---

**Last Updated:** April 16, 2026  
**Pattern Origin:** Production issue resolution - update_monitors job  
**Key Lesson:** Always use `rsplit('/src/', 1)[0]` for path resolution; always check if shared code is pure Python file vs. Databricks notebook
