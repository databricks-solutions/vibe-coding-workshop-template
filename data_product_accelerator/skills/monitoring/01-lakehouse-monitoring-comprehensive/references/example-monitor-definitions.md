# Example Monitor Definitions

## Example 1: Fact Table Monitor (TimeSeries, 9 Metrics)

```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.dataquality import (
    Monitor,
    DataProfilingConfig,
    DataProfilingCustomMetric,
    DataProfilingCustomMetricType,
    TimeSeriesConfig,
    SnapshotConfig,
    AggregationGranularity,
)
from pyspark.sql import types as T


def create_fact_sales_daily_monitor(
    w: WorkspaceClient,
    catalog: str,
    schema: str,
    monitoring_schema: str,
):
    """
    Create monitor for fact_sales_daily with 9 custom metrics.

    Metric Categories:
      - 5 AGGREGATE metrics (revenue, units, transactions, stores, null rate)
      - 2 DERIVED metrics (avg basket size, revenue per store)
      - 2 DRIFT metrics (revenue drift %, volume drift %)

    Monitor Mode: TimeSeries (daily granularity on transaction_date)
    Slicing: store_number
    """
    table = "fact_sales_daily"

    # Get UUIDs
    table_info = w.tables.get(full_name=f"{catalog}.{schema}.{table}")
    table_id = table_info.table_id
    mon_schema = w.schemas.get(full_name=f"{catalog}.{monitoring_schema}")
    output_schema_id = mon_schema.schema_id

    custom_metrics = [
        # ========================================
        # AGGREGATE METRICS (5)
        # ========================================
        # Purpose: Core business KPIs computed from table data

        # Total daily revenue
        DataProfilingCustomMetric(
            type=DataProfilingCustomMetricType.DATA_PROFILING_CUSTOM_METRIC_TYPE_AGGREGATE,
            name="total_daily_revenue",
            input_columns=[":table"],
            definition="SUM(net_revenue)",
            output_data_type=T.StructField("output", T.DoubleType()).json()
        ),

        # Total units sold
        DataProfilingCustomMetric(
            type=DataProfilingCustomMetricType.DATA_PROFILING_CUSTOM_METRIC_TYPE_AGGREGATE,
            name="total_net_units",
            input_columns=[":table"],
            definition="SUM(net_units)",
            output_data_type=T.StructField("output", T.DoubleType()).json()
        ),

        # Total transactions
        DataProfilingCustomMetric(
            type=DataProfilingCustomMetricType.DATA_PROFILING_CUSTOM_METRIC_TYPE_AGGREGATE,
            name="total_transactions",
            input_columns=[":table"],
            definition="COUNT(*)",
            output_data_type=T.StructField("output", T.LongType()).json()
        ),

        # Distinct active stores
        DataProfilingCustomMetric(
            type=DataProfilingCustomMetricType.DATA_PROFILING_CUSTOM_METRIC_TYPE_AGGREGATE,
            name="distinct_stores",
            input_columns=[":table"],
            definition="COUNT(DISTINCT store_number)",
            output_data_type=T.StructField("output", T.LongType()).json()
        ),

        # Revenue null rate (data quality signal)
        DataProfilingCustomMetric(
            type=DataProfilingCustomMetricType.DATA_PROFILING_CUSTOM_METRIC_TYPE_AGGREGATE,
            name="revenue_null_rate",
            input_columns=[":table"],
            definition="SUM(CASE WHEN net_revenue IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*)",
            output_data_type=T.StructField("output", T.DoubleType()).json()
        ),

        # ========================================
        # DERIVED METRICS (2)
        # ========================================
        # Purpose: Ratios computed from AGGREGATE metrics (no table rescan)

        # Average basket size (revenue per transaction)
        DataProfilingCustomMetric(
            type=DataProfilingCustomMetricType.DATA_PROFILING_CUSTOM_METRIC_TYPE_DERIVED,
            name="avg_basket_size",
            input_columns=[":table"],
            definition="total_daily_revenue / NULLIF(total_transactions, 0)",
            output_data_type=T.StructField("output", T.DoubleType()).json()
        ),

        # Revenue per store
        DataProfilingCustomMetric(
            type=DataProfilingCustomMetricType.DATA_PROFILING_CUSTOM_METRIC_TYPE_DERIVED,
            name="revenue_per_store",
            input_columns=[":table"],
            definition="total_daily_revenue / NULLIF(distinct_stores, 0)",
            output_data_type=T.StructField("output", T.DoubleType()).json()
        ),

        # ========================================
        # DRIFT METRICS (2)
        # ========================================
        # Purpose: Period-over-period comparison (consecutive windows)

        # Revenue drift percentage
        DataProfilingCustomMetric(
            type=DataProfilingCustomMetricType.DATA_PROFILING_CUSTOM_METRIC_TYPE_DRIFT,
            name="revenue_drift_pct",
            input_columns=[":table"],
            definition="(({{current_df}}.total_daily_revenue - {{base_df}}.total_daily_revenue) / NULLIF({{base_df}}.total_daily_revenue, 0)) * 100",
            output_data_type=T.StructField("output", T.DoubleType()).json()
        ),

        # Volume drift percentage
        DataProfilingCustomMetric(
            type=DataProfilingCustomMetricType.DATA_PROFILING_CUSTOM_METRIC_TYPE_DRIFT,
            name="volume_drift_pct",
            input_columns=[":table"],
            definition="(({{current_df}}.total_transactions - {{base_df}}.total_transactions) / NULLIF({{base_df}}.total_transactions, 0)) * 100",
            output_data_type=T.StructField("output", T.DoubleType()).json()
        ),
    ]

    config = DataProfilingConfig(
        output_schema_id=output_schema_id,
        time_series=TimeSeriesConfig(
            timestamp_column="transaction_date",
            granularities=[AggregationGranularity.AGGREGATION_GRANULARITY_1_DAY]
        ),
        custom_metrics=custom_metrics,
        slicing_exprs=["store_number"],
    )

    monitor = w.data_quality.create_monitor(
        monitor=Monitor(
            object_type="table",
            object_id=table_id,
            data_profiling_config=config,
        )
    )

    print(f"✓ Monitor created for {catalog}.{schema}.{table}")
    print(f"  Metrics: {len(custom_metrics)} (5 aggregate, 2 derived, 2 drift)")
    print(f"  Mode: TimeSeries (daily on transaction_date)")
    print(f"  Slicing: store_number")
    return monitor
```

## Example 2: Dimension Table Monitor (Snapshot, 4 Metrics)

```python
def create_dim_store_monitor(
    w: WorkspaceClient,
    catalog: str,
    schema: str,
    monitoring_schema: str,
):
    """
    Create monitor for dim_store with 4 custom metrics.

    Metric Categories:
      - 3 AGGREGATE metrics (total stores, active stores, avg age)
      - 1 DERIVED metric (active store ratio)

    Monitor Mode: Snapshot (no timestamp column for dimensions)
    Note: No DRIFT metrics (would require baseline_table_name for Snapshot mode)
    """
    table = "dim_store"

    # Get UUIDs
    table_info = w.tables.get(full_name=f"{catalog}.{schema}.{table}")
    table_id = table_info.table_id
    mon_schema = w.schemas.get(full_name=f"{catalog}.{monitoring_schema}")
    output_schema_id = mon_schema.schema_id

    custom_metrics = [
        # ========================================
        # AGGREGATE METRICS (3)
        # ========================================

        # Total stores in dimension
        DataProfilingCustomMetric(
            type=DataProfilingCustomMetricType.DATA_PROFILING_CUSTOM_METRIC_TYPE_AGGREGATE,
            name="total_stores",
            input_columns=[":table"],
            definition="COUNT(DISTINCT store_number)",
            output_data_type=T.StructField("output", T.LongType()).json()
        ),

        # Active stores (current records only)
        DataProfilingCustomMetric(
            type=DataProfilingCustomMetricType.DATA_PROFILING_CUSTOM_METRIC_TYPE_AGGREGATE,
            name="active_stores",
            input_columns=[":table"],
            definition="SUM(CASE WHEN is_current = true THEN 1 ELSE 0 END)",
            output_data_type=T.StructField("output", T.LongType()).json()
        ),

        # Average store age in days
        DataProfilingCustomMetric(
            type=DataProfilingCustomMetricType.DATA_PROFILING_CUSTOM_METRIC_TYPE_AGGREGATE,
            name="avg_store_age_days",
            input_columns=[":table"],
            definition="AVG(DATEDIFF(CURRENT_DATE(), open_date))",
            output_data_type=T.StructField("output", T.DoubleType()).json()
        ),

        # ========================================
        # DERIVED METRICS (1)
        # ========================================

        # Active store ratio
        DataProfilingCustomMetric(
            type=DataProfilingCustomMetricType.DATA_PROFILING_CUSTOM_METRIC_TYPE_DERIVED,
            name="active_store_ratio",
            input_columns=[":table"],
            definition="active_stores * 100.0 / NULLIF(total_stores, 0)",
            output_data_type=T.StructField("output", T.DoubleType()).json()
        ),
    ]

    config = DataProfilingConfig(
        output_schema_id=output_schema_id,
        snapshot=SnapshotConfig(),
        custom_metrics=custom_metrics,
    )

    monitor = w.data_quality.create_monitor(
        monitor=Monitor(
            object_type="table",
            object_id=table_id,
            data_profiling_config=config,
        )
    )

    print(f"✓ Monitor created for {catalog}.{schema}.{table}")
    print(f"  Metrics: {len(custom_metrics)} (3 aggregate, 1 derived)")
    print(f"  Mode: Snapshot")
    return monitor
```

## Metric Count Guidelines

| Table Type | AGGREGATE | DERIVED | DRIFT | Total |
|------------|----------|---------|-------|-------|
| Critical fact table | 5-8 | 2-4 | 2-3 | 9-15 |
| Standard fact table | 3-5 | 1-2 | 1-2 | 5-9 |
| Dimension table | 2-4 | 1-2 | 0 | 3-6 |
| Reference table | 1-2 | 0-1 | 0 | 1-3 |

**Start conservative** — add metrics incrementally after validating the first batch works correctly.
