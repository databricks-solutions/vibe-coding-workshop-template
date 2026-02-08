# Quick Start Guide

## Fast-Track Code: Minimal Working Monitor

Copy-paste this to create a monitor on a Gold table in under 10 minutes (excluding initialization wait time).

```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.dataquality import (
    Monitor,
    DataProfilingConfig,
    DataProfilingCustomMetric,
    DataProfilingCustomMetricType,
    TimeSeriesConfig,
    AggregationGranularity,
)
from pyspark.sql import types as T

# --- Configuration ---
catalog = "my_catalog"
schema = "gold"
table = "fact_sales_daily"
monitoring_schema = f"{schema}_monitoring"
timestamp_column = "transaction_date"

# --- Setup ---
w = WorkspaceClient()

# Create monitoring schema (if not exists)
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{monitoring_schema}")

# Get UUIDs
table_info = w.tables.get(full_name=f"{catalog}.{schema}.{table}")
table_id = table_info.table_id
mon_schema_info = w.schemas.get(full_name=f"{catalog}.{monitoring_schema}")
output_schema_id = mon_schema_info.schema_id

# --- Define Metrics ---
custom_metrics = [
    DataProfilingCustomMetric(
        type=DataProfilingCustomMetricType.DATA_PROFILING_CUSTOM_METRIC_TYPE_AGGREGATE,
        name="total_revenue",
        input_columns=[":table"],
        definition="SUM(net_revenue)",
        output_data_type=T.StructField("output", T.DoubleType()).json()
    ),
    DataProfilingCustomMetric(
        type=DataProfilingCustomMetricType.DATA_PROFILING_CUSTOM_METRIC_TYPE_AGGREGATE,
        name="total_transactions",
        input_columns=[":table"],
        definition="COUNT(*)",
        output_data_type=T.StructField("output", T.LongType()).json()
    ),
    DataProfilingCustomMetric(
        type=DataProfilingCustomMetricType.DATA_PROFILING_CUSTOM_METRIC_TYPE_DERIVED,
        name="avg_revenue_per_txn",
        input_columns=[":table"],
        definition="total_revenue / NULLIF(total_transactions, 0)",
        output_data_type=T.StructField("output", T.DoubleType()).json()
    ),
]

# --- Create Monitor ---
config = DataProfilingConfig(
    output_schema_id=output_schema_id,
    time_series=TimeSeriesConfig(
        timestamp_column=timestamp_column,
        granularities=[AggregationGranularity.AGGREGATION_GRANULARITY_1_DAY]
    ),
    custom_metrics=custom_metrics,
)

monitor = w.data_quality.create_monitor(
    monitor=Monitor(
        object_type="table",
        object_id=table_id,
        data_profiling_config=config,
    )
)
print(f"✓ Monitor created. First refresh will start automatically (~15-20 min).")
```

## Phase-Based Implementation Checklist

### Phase 1: Design (30 min)

- [ ] Identify Gold tables to monitor (start with 2-3 most critical)
- [ ] Determine monitor mode per table (TimeSeries for facts, Snapshot for dimensions)
- [ ] Define 3-5 custom metrics per table (see `references/metric-design-guide.md`)
- [ ] Identify timestamp column for TimeSeries tables
- [ ] Identify slicing columns (1-2 per table max)

### Phase 2: Setup (30 min)

- [ ] Create monitoring schema (`CREATE SCHEMA IF NOT EXISTS`)
- [ ] Test UUID lookups (table and schema)
- [ ] Create monitors using `scripts/create_monitor.py` patterns
- [ ] Verify no errors during creation

### Phase 3: Wait (15-20 min)

- [ ] Run `scripts/wait_for_initialization.py` to track refresh progress
- [ ] Monitor completes with status SUCCESS

### Phase 4: Validate (15 min)

- [ ] Query `_profile_metrics` table — custom metrics appear as columns
- [ ] Query `_drift_metrics` table — drift metrics populated (TimeSeries only)
- [ ] Verify slicing expressions produce expected breakdowns
- [ ] Confirm null_count/row_count stats are reasonable

## Critical Validation Queries

### Verify Custom Metrics Exist

```sql
-- Check that custom metrics appear as columns
DESCRIBE TABLE {catalog}.{monitoring_schema}.{table}_profile_metrics;
-- Look for: total_revenue, total_transactions, avg_revenue_per_txn columns
```

### Verify Data Is Populated

```sql
-- Check profile metrics have data
SELECT COUNT(*) AS rows,
       MIN(window.start) AS earliest,
       MAX(window.end) AS latest
FROM {catalog}.{monitoring_schema}.{table}_profile_metrics;

-- Check custom metric values
SELECT window, total_revenue, total_transactions, avg_revenue_per_txn
FROM {catalog}.{monitoring_schema}.{table}_profile_metrics
WHERE column_name = ':table'
ORDER BY window.start DESC
LIMIT 5;
```

### Verify Drift Metrics (TimeSeries Only)

```sql
SELECT window, column_name, wasserstein_distance
FROM {catalog}.{monitoring_schema}.{table}_drift_metrics
WHERE window IS NOT NULL
ORDER BY window.start DESC
LIMIT 10;
```

## Common Pitfalls

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| Using `"double"` for output_data_type | Monitor created but no custom metrics in output | Use `T.StructField("output", T.DoubleType()).json()` |
| Using `{{metric_name}}` in DERIVED | `INVALID_DERIVED_METRIC` error | Remove `{{ }}`, use direct metric name |
| Missing `{{current_df}}/{{base_df}}` in DRIFT | `INVALID_DRIFT_METRIC` error | Use `{{current_df}}.metric - {{base_df}}.metric` |
| Using table name instead of UUID | `INVALID_PARAMETER_VALUE` error | Use `get_table_id()` to look up UUID |
| Snapshot monitor with DRIFT but no baseline | Drift metrics empty | Provide `baseline_table_name` |
| High-cardinality slicing expression | Monitor takes hours to compute | Limit to low-cardinality columns |
