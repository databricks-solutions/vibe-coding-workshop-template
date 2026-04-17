# Import Patterns and Examples Reference

Detailed examples for the `databricks-python-imports` skill. For core rules and decision logic, see the parent [SKILL.md](../SKILL.md).

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
- Code needs to be imported in multiple notebooks
- Configuration shared across create/update operations
- Utility functions used across layers (Bronze/Silver/Gold)
- Need code after `restartPython()` (SDK upgrades)
- Want standard Python import semantics

### Use Databricks Notebook When:
- Executable job/task (not shared code)
- Interactive development and testing
- Running as workflow step
- Not imported by other notebooks
- Need Databricks magic commands (`%run`, `%sql`, etc.)

### Use %run When:
- **Before** `restartPython()` only
- One-time code execution in interactive notebooks
- **Not** after `restartPython()` in Asset Bundles
- **Not** for shared code that needs to persist
