# Custom Metrics Reference

## Required Imports

```python
from databricks.sdk.service.dataquality import (
    DataProfilingCustomMetric,
    DataProfilingCustomMetricType,
)
from pyspark.sql import types as T  # MANDATORY for output_data_type
```

## The Three Custom Metric Types

| Type | Purpose | References | Syntax Pattern |
|------|---------|-----------|----------------|
| **AGGREGATE** | Calculate from table columns | Raw table columns | `SUM(column_name)` |
| **DERIVED** | Calculate from aggregates | Aggregate metric names | `metric_name` (NO `{{ }}`) |
| **DRIFT** | Compare between windows | Metrics + window templates | `{{current_df}}.metric - {{base_df}}.metric` |

## AGGREGATE Metrics

**Purpose:** Calculate statistics directly from table columns

**Syntax:** Raw SQL expressions on table data

```python
DataProfilingCustomMetric(
    type=DataProfilingCustomMetricType.DATA_PROFILING_CUSTOM_METRIC_TYPE_AGGREGATE,
    name="daily_revenue",
    input_columns=[":table"],  # or specific columns: ["col1", "col2"]
    definition="SUM(total_booking_value)",  # Raw SQL on table columns
    output_data_type=T.StructField("output", T.DoubleType()).json()  # MUST use StructField.json()
)
```

**Key Points:**
- References actual table columns
- Uses SQL aggregate functions (SUM, AVG, COUNT, STDDEV, etc.)
- Computed directly on primary table data
- `output_data_type` MUST be `T.StructField().json()` format, NOT a string like `"double"`

## DERIVED Metrics

**Purpose:** Calculate from previously computed aggregate metrics

**Syntax:** Direct reference to aggregate metric names (**NO `{{ }}` templates**)

```python
# First define the aggregates it depends on:
DataProfilingCustomMetric(
    type=DataProfilingCustomMetricType.DATA_PROFILING_CUSTOM_METRIC_TYPE_AGGREGATE,
    name="total_bookings",
    input_columns=[":table"],
    definition="SUM(booking_count)",
    output_data_type=T.StructField("output", T.DoubleType()).json()
),
DataProfilingCustomMetric(
    type=DataProfilingCustomMetricType.DATA_PROFILING_CUSTOM_METRIC_TYPE_AGGREGATE,
    name="total_cancellations",
    input_columns=[":table"],
    definition="SUM(cancellation_count)",
    output_data_type=T.StructField("output", T.DoubleType()).json()
),

# Then define derived metric:
DataProfilingCustomMetric(
    type=DataProfilingCustomMetricType.DATA_PROFILING_CUSTOM_METRIC_TYPE_DERIVED,
    name="cancellation_rate",
    input_columns=[":table"],
    definition="(total_cancellations / NULLIF(total_bookings, 0)) * 100",  # Direct reference, NO {{ }}!
    output_data_type=T.StructField("output", T.DoubleType()).json()
)
```

**Key Points:**
- References aggregate metric **names** directly (no template syntax)
- NEVER use `{{ }}` for DERIVED metrics
- Minimizes recomputation (doesn't scan table again)
- Must reference metrics defined earlier in same monitor
- All referenced metrics must have same `input_columns` value

**Common Error:**
```python
# WRONG - Using template syntax for DERIVED
definition="({{total_cancellations}} / NULLIF({{total_bookings}}, 0)) * 100"
# Error: INVALID_DERIVED_METRIC - UNDEFINED_TEMPLATE_VARIABLE

# CORRECT - Direct reference
definition="(total_cancellations / NULLIF(total_bookings, 0)) * 100"
```

## DRIFT Metrics

**Purpose:** Compare metrics between two time windows or against baseline

**Syntax:** Template syntax with `{{current_df}}` and `{{base_df}}` prefixes

```python
DataProfilingCustomMetric(
    type=DataProfilingCustomMetricType.DATA_PROFILING_CUSTOM_METRIC_TYPE_DRIFT,
    name="revenue_vs_baseline",
    input_columns=[":table"],
    definition="{{current_df}}.daily_revenue - {{base_df}}.daily_revenue",  # MUST use {{ }} templates
    output_data_type=T.StructField("output", T.DoubleType()).json()
)
```

**Key Points:**
- **MUST use `{{current_df}}` and `{{base_df}}` templates**
- Compares same metric across two windows
- Stores results in **drift_metrics** table (not profile_metrics)
- For TimeSeries: Compares consecutive windows
- For Snapshot: Requires baseline table

**Window Comparison Patterns:**

```python
# Absolute difference
definition="{{current_df}}.metric_name - {{base_df}}.metric_name"

# Percentage change
definition="(({{current_df}}.metric_name - {{base_df}}.metric_name) / NULLIF({{base_df}}.metric_name, 0)) * 100"

# Ratio
definition="{{current_df}}.metric_name / NULLIF({{base_df}}.metric_name, 1)"
```

**Common Error:**
```python
# WRONG - Missing window comparison
definition="{{daily_revenue}}"  # Just references metric
# Error: INVALID_DRIFT_METRIC - Must specify current_df and base_df

# CORRECT - Compares windows
definition="{{current_df}}.daily_revenue - {{base_df}}.daily_revenue"
```

## Critical Syntax Rules

| Rule | Correct | Wrong |
|------|---------|-------|
| **SDK Objects** | `DataProfilingCustomMetric(...)` | `{"name": "...", "type": "..."}` (dict) |
| **output_data_type** | `T.StructField("output", T.DoubleType()).json()` | `"double"` (string) |
| **DERIVED syntax** | `metric_name` | `{{metric_name}}` (template) |
| **DRIFT syntax** | `{{current_df}}.metric - {{base_df}}.metric` | `{{metric}}` (no comparison) |
| **imports** | `from pyspark.sql import types as T` | Missing import |

## Monitor Mode and Drift Requirements

**CRITICAL:** Snapshot monitors need baseline table for drift metrics

| Monitor Mode | Consecutive Windows? | Drift Without Baseline? |
|--------------|---------------------|------------------------|
| **TimeSeries** | Yes | Yes (consecutive comparison) |
| **Snapshot** | No | NO (must provide baseline_table_name) |

**For Snapshot Monitors with DRIFT:**

```python
# Option 1: Provide baseline table
DataProfilingConfig(
    snapshot=SnapshotConfig(),
    baseline_table_name=f"{catalog}.{schema}.{table}_baseline",  # Required for drift
    custom_metrics=[...drift metrics...],
    ...
)

# Option 2: Remove drift metrics (simpler)
DataProfilingConfig(
    snapshot=SnapshotConfig(),
    custom_metrics=[...no drift metrics...],  # No baseline needed
    ...
)
```

## Business-Focused Metric Categories

### 1. Transaction Pattern Metrics

**Purpose:** Track customer purchasing behavior changes

```python
# Average spend per transaction
DataProfilingCustomMetric(
    type=DataProfilingCustomMetricType.DATA_PROFILING_CUSTOM_METRIC_TYPE_AGGREGATE,
    name="avg_transaction_amount",
    input_columns=[":table"],
    definition="AVG(avg_transaction_value)",
    output_data_type=T.StructField("output", T.DoubleType()).json()
)

# Items per basket (DERIVED - references AGGREGATE metrics)
DataProfilingCustomMetric(
    type=DataProfilingCustomMetricType.DATA_PROFILING_CUSTOM_METRIC_TYPE_DERIVED,
    name="avg_items_per_transaction",
    input_columns=[":table"],
    definition="total_net_units / NULLIF(total_transactions, 0)",
    output_data_type=T.StructField("output", T.DoubleType()).json()
)
```

### 2. Product Performance Metrics

```python
# Product sales velocity
DataProfilingCustomMetric(
    type=DataProfilingCustomMetricType.DATA_PROFILING_CUSTOM_METRIC_TYPE_AGGREGATE,
    name="product_velocity",
    input_columns=[":table"],
    definition="SUM(net_units) / NULLIF(COUNT(DISTINCT store_number), 0)",
    output_data_type=T.StructField("output", T.DoubleType()).json()
)
```

### 3. Drift Metrics (Period-over-Period Comparison)

```python
# Revenue drift percentage
DataProfilingCustomMetric(
    type=DataProfilingCustomMetricType.DATA_PROFILING_CUSTOM_METRIC_TYPE_DRIFT,
    name="revenue_drift_pct",
    input_columns=[":table"],
    definition="(({{current_df}}.total_net_revenue - {{base_df}}.total_net_revenue) / NULLIF({{base_df}}.total_net_revenue, 0)) * 100",
    output_data_type=T.StructField("output", T.DoubleType()).json()
)
```

## Custom Metric Limitations

**Critical Rule: No Nested Aggregations**

Databricks does NOT support aggregate functions inside other aggregate functions.

```python
# WRONG: Nested aggregation
DataProfilingCustomMetric(
    type=DataProfilingCustomMetricType.DATA_PROFILING_CUSTOM_METRIC_TYPE_AGGREGATE,
    name="top_10_stores_revenue_share",
    definition="(SUM(CASE WHEN net_revenue >= PERCENTILE(net_revenue, 0.9) THEN net_revenue ELSE 0 END) / NULLIF(SUM(net_revenue), 0)) * 100"
    # ERROR: PERCENTILE inside SUM
)

# CORRECT: Two-step pattern (AGGREGATE -> DERIVED)
# Step 1: Define base aggregates
DataProfilingCustomMetric(
    type=DataProfilingCustomMetricType.DATA_PROFILING_CUSTOM_METRIC_TYPE_AGGREGATE,
    name="total_revenue",
    input_columns=[":table"],
    definition="SUM(revenue)",
    output_data_type=T.StructField("output", T.DoubleType()).json()
),
DataProfilingCustomMetric(
    type=DataProfilingCustomMetricType.DATA_PROFILING_CUSTOM_METRIC_TYPE_AGGREGATE,
    name="p90_revenue",
    input_columns=[":table"],
    definition="PERCENTILE(revenue, 0.9)",
    output_data_type=T.StructField("output", T.DoubleType()).json()
),

# Step 2: Define derived ratio
DataProfilingCustomMetric(
    type=DataProfilingCustomMetricType.DATA_PROFILING_CUSTOM_METRIC_TYPE_DERIVED,
    name="top_performer_share",
    input_columns=[":table"],
    definition="p90_revenue / NULLIF(total_revenue, 0) * 100",  # References aggregates
    output_data_type=T.StructField("output", T.DoubleType()).json()
)
```

## Metric Organization Pattern

**Group metrics by business domain with clear comments:**

```python
custom_metrics=[
    # ========================================
    # TRANSACTION PATTERN METRICS
    # ========================================
    # Purpose: Track customer purchasing behavior changes

    DataProfilingCustomMetric(...),  # avg_transaction_amount
    DataProfilingCustomMetric(...),  # avg_items_per_transaction
    DataProfilingCustomMetric(...),  # transactions_per_store_per_day

    # ========================================
    # PRODUCT PERFORMANCE METRICS
    # ========================================
    # Purpose: Monitor product sales velocity and availability

    DataProfilingCustomMetric(...),  # product_velocity
    DataProfilingCustomMetric(...),  # revenue_per_product
    DataProfilingCustomMetric(...),  # product_availability_rate

    # ... more categories
]
```

## Where Custom Metrics Appear

**CRITICAL:** Custom metrics appear as **NEW COLUMNS** in monitoring output tables:
- **AGGREGATE + DERIVED metrics** -> `{table}_profile_metrics` table (as new columns)
- **DRIFT metrics** -> `{table}_drift_metrics` table (as new columns)
- **There is NO separate `custom_metrics` table!**
