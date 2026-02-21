---
name: databricks-python-imports
description: Patterns for sharing code between Databricks notebooks using pure Python files and standard imports. Enables code reuse across notebooks, especially after dbutils.library.restartPython(). Covers Asset Bundle path setup, notebook-to-module conversion, import patterns vs %run magic commands, and troubleshooting ModuleNotFoundError. Use when creating shared configuration modules, utility functions, or helper code that needs to be imported across multiple notebooks in serverless environments.
metadata:
  author: prashanth subrahmanyam
  version: "1.0"
  domain: infrastructure
  role: shared
  used_by_stages: [1, 2, 3, 4, 5, 6, 7, 8, 9]
  last_verified: "2026-02-07"
  volatility: medium
  upstream_sources:
    - name: "ai-dev-kit"
      repo: "databricks-solutions/ai-dev-kit"
      paths:
        - "databricks-skills/databricks-config/SKILL.md"
      relationship: "reference"
      last_synced: "2026-02-19"
      sync_commit: "97a3637"
---
# Databricks Python Imports and Code Sharing

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

### Converting Databricks Notebook to Pure Python File

**BEFORE (Notebook - Not Importable):**
```python
# Databricks notebook source

"""
Centralized Monitor Configuration
"""

from databricks.sdk.service.catalog import MonitorTimeSeries

def get_all_configs():
    return [...]
```

**AFTER (Pure Python - Importable):**
```python
"""
Centralized Monitor Configuration
"""

from databricks.sdk.service.catalog import MonitorTimeSeries

def get_all_configs():
    return [...]
```

**Change Required:** Remove line 1: `# Databricks notebook source`

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

## Use Cases

### Shared Configuration Modules

**Pattern:** Configuration loaded in multiple notebooks/jobs

```python
# monitor_configs.py (pure Python file)
"""
Centralized monitor configurations for all monitoring jobs.
"""

from databricks.sdk.service.catalog import MonitorTimeSeries

def get_all_monitor_configs(catalog: str, schema: str):
    """Returns list of monitor configurations with custom metrics."""
    return [
        {
            "table_name": f"{catalog}.{schema}.fact_sales",
            "custom_metrics": _get_sales_metrics(),
            ...
        }
    ]

def _get_sales_metrics():
    """99 custom metrics for sales monitoring."""
    return [...]
```

**Usage in Multiple Notebooks:**

```python
# setup_monitors.py
from monitor_configs import get_all_monitor_configs

configs = get_all_monitor_configs(catalog, schema)
workspace_client.quality_monitors.create(**configs[0])
```

```python
# update_monitors.py
from monitor_configs import get_all_monitor_configs

configs = get_all_monitor_configs(catalog, schema)
workspace_client.quality_monitors.update(**configs[0])
```

### Shared Utility Functions

**Pattern:** Utility functions used across layers

```python
# data_quality_rules.py (pure Python file)
"""
Centralized data quality rules for all DLT tables.
"""

def get_critical_rules_for_table(table_name: str):
    """Returns critical DQ rules that will drop records."""
    return {...}

def get_warning_rules_for_table(table_name: str):
    """Returns warning DQ rules that will log but pass."""
    return {...}
```

**Usage in DLT Notebooks:**

```python
# silver_transactions.py
import dlt
from data_quality_rules import get_critical_rules_for_table

@dlt.table(...)
@dlt.expect_all_or_fail(get_critical_rules_for_table("silver_transactions"))
def silver_transactions():
    return dlt.read_stream("bronze_transactions")
```

### Shared Helper Functions

```python
# helpers.py (pure Python file)
"""
Common helper functions for data transformations.
"""

from pyspark.sql import DataFrame
from pyspark.sql.functions import col, sha2, concat_ws

def generate_surrogate_key(df: DataFrame, key_columns: list) -> DataFrame:
    """Generates MD5 surrogate key from specified columns."""
    return df.withColumn(
        "surrogate_key",
        sha2(concat_ws("||", *[col(c) for c in key_columns]), 256)
    )
```

## When Each Approach Is Appropriate

### Use Pure Python File When:
- ✅ Code needs to be imported in multiple notebooks
- ✅ Configuration shared across create/update operations
- ✅ Utility functions used across layers (Bronze/Silver/Gold)
- ✅ Need code after `restartPython()` (SDK upgrades)
- ✅ Want standard Python import semantics

### Use Databricks Notebook When:
- ✅ Executable job/task (not shared code)
- ✅ Interactive development and testing
- ✅ Running as workflow step
- ✅ Not imported by other notebooks
- ✅ Need Databricks magic commands (`%run`, `%sql`, etc.)

### Use %run When:
- ✅ **Before** `restartPython()` only
- ✅ One-time code execution in interactive notebooks
- ❌ **Not** after `restartPython()` in Asset Bundles
- ❌ **Not** for shared code that needs to persist

## Common Mistakes

### ❌ Mistake 1: Notebook Header in Shared Code

```python
# config.py
# Databricks notebook source  # ❌ Makes it a notebook!

def get_config():
    return {...}
```

**Fix:** Remove the notebook header

```python
# config.py
def get_config():
    return {...}
```

### ❌ Mistake 2: Trying to Import Notebook

```python
# job.py
%pip install --upgrade "databricks-sdk>=0.28.0" --quiet
dbutils.library.restartPython()

from config import get_config  # ❌ Fails if config.py is notebook
```

**Error:** `ModuleNotFoundError: No module named 'config'`

**Fix:** Convert `config.py` to pure Python file (remove notebook header)

### ❌ Mistake 3: Using %run After restartPython()

```python
# job.py
%pip install --upgrade "databricks-sdk>=0.28.0" --quiet
dbutils.library.restartPython()

%run ./config  # ❌ Doesn't work in deployed Asset Bundles

get_config()  # ❌ NameError: name 'get_config' is not defined
```

**Fix:** Convert to pure Python file and use standard import

```python
%pip install --upgrade "databricks-sdk>=0.28.0" --quiet
dbutils.library.restartPython()

from config import get_config  # ✅ Works with pure Python file

get_config()  # ✅ Available
```

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

## Troubleshooting

### Problem: ModuleNotFoundError after restartPython()

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
# Databricks notebook source  # ❌ Remove this!

# File should start with module docstring:
"""
Configuration module
"""
```

### Problem: NameError after %run and restartPython()

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
from config import get_config  # ✅ Persistent import
get_config()  # ✅ Works
```

## References

- [Share code between Databricks notebooks](https://docs.databricks.com/aws/en/notebooks/share-code) - Official documentation
- [Work with Python and R modules](https://docs.databricks.com/repos/work-with-notebooks-other-files.html#work-with-python-and-r-modules)
- [dbutils.library.restartPython()](https://docs.databricks.com/dev-tools/databricks-utils.html#library-utilities)

## Related Patterns

- [Databricks Asset Bundles Configuration](../databricks-asset-bundles/SKILL.md) - Deployment patterns
- [Lakehouse Monitoring Patterns](../../monitoring/01-lakehouse-monitoring-comprehensive/SKILL.md) - Monitor configuration sharing
- [DLT Expectations Patterns](../../silver/dlt-expectations-patterns/SKILL.md) - DQ rules sharing

---

**Last Updated:** October 24, 2025  
**Pattern Origin:** Production issue resolution - update_monitors job  
**Key Lesson:** Always check if shared code is pure Python file vs. Databricks notebook
