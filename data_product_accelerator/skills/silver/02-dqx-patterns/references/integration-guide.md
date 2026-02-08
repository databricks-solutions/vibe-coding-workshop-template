# DQX Integration Guide

## Pattern 1: DLT / Lakeflow Integration (Recommended)

**Official pattern from [DQX docs](https://databrickslabs.github.io/dqx/docs/guide/quality_checks_apply/#applying-checks-in-lakeflow-pipelines):**

```python
# src/company_silver/silver_transactions_dqx.py
import dlt
from databricks.labs.dqx.engine import DQEngine
from databricks.sdk import WorkspaceClient

dq_engine = DQEngine(WorkspaceClient())
checks = [...]  # dict/YAML checks (see rule-patterns.md)

# Step 1: Apply checks in a DLT view (adds diagnostic columns)
@dlt.view
def bronze_dq_check():
    df = dlt.read_stream("bronze_transactions")
    return dq_engine.apply_checks_by_metadata(df, checks)

# Step 2: Valid records go to Silver table (no diagnostic columns)
@dlt.table(
    name="silver_transactions",
    comment="Silver transactions - passed all DQX error-level checks",
    table_properties={
        "quality": "silver",
        "delta.enableChangeDataFeed": "true",
        "validation_framework": "dqx",
    },
    cluster_by_auto=True
)
def silver_transactions():
    df = dlt.read_stream("bronze_dq_check")
    return dq_engine.get_valid(df)

# Step 3: Failed records go to quarantine (with diagnostic columns)
@dlt.table(
    name="silver_transactions_quarantine",
    comment="Quarantine - records with DQX check failures and diagnostics",
    table_properties={
        "quality": "quarantine",
        "layer": "silver",
        "validation_framework": "dqx",
    },
    cluster_by_auto=True
)
def silver_transactions_quarantine():
    df = dlt.read_stream("bronze_dq_check")
    return dq_engine.get_invalid(df)
```

**Key methods:**
- `apply_checks_by_metadata(df, checks)` -- adds `_error` and `_warning` columns
- `get_valid(df)` -- rows without errors (clean, no diagnostic columns)
- `get_invalid(df)` -- rows with errors (includes diagnostic columns)

---

## Pattern 2: Hybrid DLT Expectations + DQX

**Use BOTH DLT expectations AND DQX for complementary benefits:**

```python
import dlt
from databricks.labs.dqx.engine import DQEngine
from databricks.sdk import WorkspaceClient
from data_quality_rules import get_critical_rules_for_table

dq_engine = DQEngine(WorkspaceClient())
dqx_warning_checks = [...]  # Warning-level checks only

@dlt.table(...)
# DLT expectations for critical enforcement (fast, built-in)
@dlt.expect_all_or_fail(get_critical_rules_for_table("silver_transactions"))
def silver_transactions():
    """
    Hybrid validation:
    1. DLT expectations: Critical rules (fast fail, drops invalid)
    2. DQX: Warning-level diagnostics (marks but doesn't drop)
    """
    bronze_df = dlt.read_stream("bronze_transactions")

    # DQX adds diagnostic metadata (doesn't drop, just marks)
    return dq_engine.apply_checks_by_metadata(bronze_df, dqx_warning_checks)
```

**Best practice:** Don't duplicate rules in both DLT and DQX. Use DLT for critical enforcement and DQX for diagnostic/warning checks.

---

## Pattern 3: Gold Layer Pre-Merge Validation (Production)

**Validate aggregated data before MERGE with quarantine:**

**File: `src/company_gold/dqx_gold_checks.py`** (Pure Python, importable)

```python
"""DQX quality checks for Gold layer tables."""

from databricks.labs.dqx.engine import DQEngine
from databricks.sdk import WorkspaceClient
from pyspark.sql import SparkSession, DataFrame
from typing import Tuple, Optional, Dict

def get_fact_checks() -> list:
    """Get DQX checks for fact_sales_daily table."""
    return [
        {
            "name": "non_negative_net_revenue",
            "criticality": "error",
            "check": {
                "function": "is_not_less_than",
                "arguments": {"column": "net_revenue", "limit": 0}
            },
            "metadata": {
                "business_rule": "Net revenue cannot be negative",
                "failure_impact": "Critical - Invalid financial reporting"
            }
        },
        {
            "name": "reasonable_daily_revenue",
            "criticality": "warn",
            "check": {
                "function": "is_not_greater_than",
                "arguments": {"column": "net_revenue", "limit": 100000}
            },
            "metadata": {
                "business_rule": "Daily revenue > $100K is unusual"
            }
        }
    ]

def apply_dqx_validation(
    spark: SparkSession,
    df: DataFrame,
    catalog: str,
    schema: str,
    entity: str,
    enable_quarantine: bool = True
) -> Tuple[DataFrame, Optional[DataFrame], Dict]:
    """Apply DQX validation to DataFrame before MERGE."""
    dq_engine = DQEngine(WorkspaceClient())

    if entity == "fact_sales_daily":
        checks = get_fact_checks()
    else:
        raise ValueError(f"Unknown entity: {entity}")

    print(f"\n  Applying {len(checks)} DQX quality checks...")

    # CRITICAL: Use metadata-based API for dict checks
    valid_df, invalid_df = dq_engine.apply_checks_by_metadata_and_split(df, checks)

    valid_count = valid_df.count()
    invalid_count = invalid_df.count() if invalid_df is not None else 0
    total_count = valid_count + invalid_count

    stats = {
        "total": total_count,
        "valid": valid_count,
        "invalid": invalid_count,
        "pass_rate_pct": round((valid_count / total_count * 100), 2) if total_count > 0 else 0
    }

    print(f"  Valid: {valid_count:,} ({stats['pass_rate_pct']}%)")
    print(f"  Invalid: {invalid_count:,}")

    return valid_df, invalid_df, stats
```

**File: `src/company_gold/merge_gold_tables.py`** (Uses DQX validation)

```python
from dqx_gold_checks import apply_dqx_validation  # Standard import
from delta.tables import DeltaTable

def merge_fact_sales_daily(spark, catalog, silver_schema, gold_schema):
    # ... aggregation logic ...

    # DQX PRE-MERGE VALIDATION
    valid_sales, invalid_sales, stats = apply_dqx_validation(
        spark=spark, df=daily_sales, catalog=catalog,
        schema=gold_schema, entity="fact_sales_daily"
    )

    # Quarantine invalid records
    if stats["invalid"] > 0:
        quarantine_table = f"{catalog}.{gold_schema}.fact_sales_daily_quarantine"
        invalid_sales.write.format("delta").mode("append") \
            .option("mergeSchema", "true").saveAsTable(quarantine_table)

    # Only merge valid records
    if stats["valid"] == 0:
        raise ValueError("No valid records to merge!")

    delta_gold = DeltaTable.forName(spark, f"{catalog}.{gold_schema}.fact_sales_daily")
    delta_gold.alias("target").merge(
        valid_sales.alias("source"),  # Validated DataFrame
        "target.store_number = source.store_number AND ..."
    ).whenMatchedUpdateAll().whenNotMatchedInsertAll().execute()
```

---

## Pattern 4: foreachBatch Streaming (added 0.8.0)

**For Spark Structured Streaming with `foreachBatch`, use a mock WorkspaceClient:**

```python
from unittest.mock import MagicMock
from pyspark.sql import DataFrame
from databricks.labs.dqx.engine import DQEngine
from databricks.labs.dqx.rule import DQRowRule
from databricks.labs.dqx import check_funcs
from databricks.sdk import WorkspaceClient

checks = [
    DQRowRule(
        name="col_value_not_null",
        criticality="error",
        check_func=check_funcs.is_not_null,
        column="value"
    )
]

def validate_micro_batch(batch_df: DataFrame, _: int) -> None:
    mock_ws = MagicMock(spec=WorkspaceClient)
    dq_engine = DQEngine(mock_ws)
    valid_df, invalid_df = dq_engine.apply_checks_and_split(batch_df, checks)
    valid_df.write.format("delta").mode("append").saveAsTable("catalog.schema.output")

input_data = spark.readStream.format("rate-micro-batch").load()
input_data.writeStream.foreachBatch(validate_micro_batch).start()
```

---

## Pattern 5: Multi-Table Checking (added 0.9.3)

**Apply checks to multiple tables in a single call:**

```python
from databricks.labs.dqx.engine import DQEngine
from databricks.labs.dqx.config import InputConfig, OutputConfig, RunConfig, TableChecksStorageConfig
from databricks.sdk import WorkspaceClient

dq_engine = DQEngine(WorkspaceClient())

# Apply checks on tables matching wildcard patterns
dq_engine.apply_checks_and_save_in_tables_for_patterns(
    patterns=["catalog.silver_schema.*"],
    exclude_patterns=["*_dq_output", "*_dq_quarantine"],
    checks_location="catalog.gold_schema.dqx_quality_checks",
    output_table_suffix="_checked",
    quarantine_table_suffix="_quarantine"
)
```

---

## Pattern 6: End-to-End Method

**Single method call for load + apply + save:**

```python
from databricks.labs.dqx.engine import DQEngine
from databricks.labs.dqx.config import InputConfig, OutputConfig
from databricks.sdk import WorkspaceClient

dq_engine = DQEngine(WorkspaceClient())

dq_engine.apply_checks_by_metadata_and_save_in_table(
    checks=checks,
    input_config=InputConfig(location="catalog.silver.transactions"),
    output_config=OutputConfig(location="catalog.silver.transactions_valid", mode="overwrite"),
    quarantine_config=OutputConfig(location="catalog.silver.transactions_quarantine", mode="overwrite"),
)
```

---

## DQX vs. DLT Expectations Comparison

| Feature | DLT Expectations | DQX | Recommendation |
|---------|-----------------|-----|----------------|
| Row-level validation | Yes | Yes | Both work |
| Dataset-level checks | No | Yes (unique, FK, outliers, aggregation) | DQX for complex |
| Failure diagnostics | Basic | Detailed (`_error`, `_warning` columns) | DQX for debugging |
| Auto-profiling | No | Yes (`DQXProfiler`) | DQX for discovery |
| AI-assisted rules | No | Yes (LLM-based, 0.10.0+) | DQX for new sources |
| Quarantine strategies | Drop/fail | Drop/mark/split/save | DQX more flexible |
| YAML/JSON configuration | No | Yes | DQX for declarative |
| Streaming support | Native | Yes (including foreachBatch) | Both work |
| Delta/Lakebase storage | No | Yes | DQX for governance |
| Summary metrics | Via event log | Yes (DQMetricsObserver, 0.10.0+) | DQX for tracking |
| Foreign key validation | No | Yes | DQX for Gold layer |
| Outlier detection | No | Yes (MAD, 0.12.0+) | DQX for anomalies |
| PII detection | No | Yes (Presidio, 0.9.1+) | DQX for compliance |
| Multi-table checking | No | Yes (0.9.3+) | DQX for scale |
| Learning curve | Simple | Moderate | DLT for basics |
| External dependency | Built-in | External library | DLT simpler |

### Anti-Patterns

**Don't:** Duplicate the same rule in both DLT and DQX
```python
# BAD: Same null check in DLT and DQX
@dlt.expect("not_null", "col IS NOT NULL")
def table():
    return dq_engine.apply_checks_by_metadata(df, [
        {"check": {"function": "is_not_null", "arguments": {"column": "col"}}}
    ])
```

**Do:** Use complementary approaches
```python
# GOOD: DLT for critical enforcement, DQX for diagnostics
@dlt.expect_all_or_fail(get_critical_rules())  # Critical
def table():
    return dq_engine.apply_checks_by_metadata(df, warning_checks)  # Warnings only
```

---

## Asset Bundle Job Configuration

### 2-Step Workflow (Store Checks + Merge with Validation)

```yaml
resources:
  jobs:
    gold_merge_job:
      name: "[${bundle.target}] Gold Layer - MERGE with DQX"
      environments:
        - environment_key: default
          spec:
            dependencies:
              - "databricks-labs-dqx>=0.12.0"
      tasks:
        - task_key: store_dqx_checks
          environment_key: default
          notebook_task:
            notebook_path: ../src/company_gold/store_dqx_checks.py
            base_parameters:
              catalog: ${var.catalog}
              gold_schema: ${var.gold_schema}
        - task_key: merge_gold_tables
          depends_on:
            - task_key: store_dqx_checks
          environment_key: default
          notebook_task:
            notebook_path: ../src/company_gold/merge_gold_tables.py
            base_parameters:
              catalog: ${var.catalog}
              silver_schema: ${var.silver_schema}
              gold_schema: ${var.gold_schema}
      schedule:
        quartz_cron_expression: "0 0 4 * * ?"
        timezone_id: "America/New_York"
        pause_status: PAUSED
      tags:
        layer: gold
        compute_type: serverless
```
