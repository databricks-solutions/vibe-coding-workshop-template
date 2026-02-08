# Monitor Configuration Reference

## Required Imports

```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.dataquality import (
    Monitor,
    DataProfilingConfig,
    DataProfilingCustomMetric,
    DataProfilingCustomMetricType,
    DataProfilingStatus,
    TimeSeriesConfig,
    SnapshotConfig,
    AggregationGranularity,
    Refresh,
    RefreshState,
    NotificationSettings,
    NotificationDestination,
    CronSchedule,
)
from pyspark.sql import types as T
```

### Graceful Degradation Pattern

```python
try:
    from databricks.sdk.service.dataquality import (
        DataProfilingConfig,
        DataProfilingCustomMetric,
        DataProfilingCustomMetricType,
        TimeSeriesConfig,
        SnapshotConfig,
        AggregationGranularity,
    )
    SDK_AVAILABLE = True
except ImportError:
    print("⚠️ databricks-sdk not available or dataquality module not found.")
    print("   Install: pip install databricks-sdk>=0.68.0")
    SDK_AVAILABLE = False
```

## UUID Lookup Helpers

**Critical:** The Data Quality API requires UUIDs, NOT three-level names.

### Get Table UUID

```python
def get_table_id(w: WorkspaceClient, catalog: str, schema: str, table: str) -> str:
    """Get table UUID from three-level name."""
    table_info = w.tables.get(full_name=f"{catalog}.{schema}.{table}")
    return table_info.table_id
```

### Get Schema UUID

```python
def get_schema_id(w: WorkspaceClient, catalog: str, schema: str) -> str:
    """Get schema UUID from two-level name."""
    schema_info = w.schemas.get(full_name=f"{catalog}.{schema}")
    return schema_info.schema_id
```

## DataProfilingConfig Construction

### TimeSeries Monitor (Fact Tables)

```python
table_id = get_table_id(w, catalog, schema, table)
monitoring_schema_id = get_schema_id(w, catalog, f"{schema}_monitoring")

config = DataProfilingConfig(
    output_schema_id=monitoring_schema_id,
    time_series=TimeSeriesConfig(
        timestamp_column="transaction_date",
        granularities=[AggregationGranularity.AGGREGATION_GRANULARITY_1_DAY]
    ),
    custom_metrics=[
        DataProfilingCustomMetric(
            type=DataProfilingCustomMetricType.DATA_PROFILING_CUSTOM_METRIC_TYPE_AGGREGATE,
            name="total_revenue",
            input_columns=[":table"],
            definition="SUM(net_revenue)",
            output_data_type=T.StructField("output", T.DoubleType()).json()
        ),
    ],
    slicing_exprs=["store_number"],
)

monitor = w.data_quality.create_monitor(
    monitor=Monitor(
        object_type="table",
        object_id=table_id,
        data_profiling_config=config,
    )
)
```

### Snapshot Monitor (Dimension Tables)

```python
table_id = get_table_id(w, catalog, schema, table)
monitoring_schema_id = get_schema_id(w, catalog, f"{schema}_monitoring")

config = DataProfilingConfig(
    output_schema_id=monitoring_schema_id,
    snapshot=SnapshotConfig(),
    custom_metrics=[
        DataProfilingCustomMetric(
            type=DataProfilingCustomMetricType.DATA_PROFILING_CUSTOM_METRIC_TYPE_AGGREGATE,
            name="total_stores",
            input_columns=[":table"],
            definition="COUNT(DISTINCT store_number)",
            output_data_type=T.StructField("output", T.LongType()).json()
        ),
    ],
)

monitor = w.data_quality.create_monitor(
    monitor=Monitor(
        object_type="table",
        object_id=table_id,
        data_profiling_config=config,
    )
)
```

## Granularity Enum Values

| Granularity | Enum Value |
|-------------|-----------|
| 5 minutes | `AggregationGranularity.AGGREGATION_GRANULARITY_5_MINUTES` |
| 30 minutes | `AggregationGranularity.AGGREGATION_GRANULARITY_30_MINUTES` |
| 1 hour | `AggregationGranularity.AGGREGATION_GRANULARITY_1_HOUR` |
| 1 day | `AggregationGranularity.AGGREGATION_GRANULARITY_1_DAY` |
| 1 week | `AggregationGranularity.AGGREGATION_GRANULARITY_1_WEEK` |
| 1 month | `AggregationGranularity.AGGREGATION_GRANULARITY_1_MONTH` |
| 1 year | `AggregationGranularity.AGGREGATION_GRANULARITY_1_YEAR` |

## Notification Settings

```python
config = DataProfilingConfig(
    output_schema_id=monitoring_schema_id,
    time_series=TimeSeriesConfig(
        timestamp_column="transaction_date",
        granularities=[AggregationGranularity.AGGREGATION_GRANULARITY_1_DAY]
    ),
    notification_settings=NotificationSettings(
        on_failure=NotificationDestination(
            email_addresses=["data-eng@company.com"]
        )
    ),
    custom_metrics=[...],
)
```

## Schedule Configuration

```python
config = DataProfilingConfig(
    output_schema_id=monitoring_schema_id,
    schedule=CronSchedule(
        quartz_cron_expression="0 0 6 * * ?",  # Daily at 6 AM
        timezone_id="America/New_York",
    ),
    time_series=TimeSeriesConfig(
        timestamp_column="transaction_date",
        granularities=[AggregationGranularity.AGGREGATION_GRANULARITY_1_DAY]
    ),
    custom_metrics=[...],
)
```

## Refresh Tracking

### Trigger Refresh

```python
refresh = w.data_quality.create_refresh(
    refresh=Refresh(
        object_type="table",
        object_id=table_id,
    )
)
print(f"Refresh ID: {refresh.refresh_id}")
print(f"State: {refresh.state}")
```

### Poll Refresh Status

```python
import time

def wait_for_refresh(w, table_id, refresh_id, timeout_minutes=30):
    """Wait for a refresh to complete using Refresh state tracking."""
    start_time = time.time()
    timeout_seconds = timeout_minutes * 60

    while time.time() - start_time < timeout_seconds:
        refresh = w.data_quality.get_refresh(
            object_type="table",
            object_id=table_id,
            refresh_id=refresh_id,
        )

        if refresh.state == RefreshState.MONITOR_REFRESH_STATE_SUCCESS:
            elapsed = (time.time() - start_time) / 60
            print(f"✓ Refresh completed in {elapsed:.1f} minutes")
            return True
        elif refresh.state in (
            RefreshState.MONITOR_REFRESH_STATE_FAILED,
            RefreshState.MONITOR_REFRESH_STATE_CANCELED,
        ):
            print(f"✗ Refresh {refresh.state.value}")
            return False

        elapsed = (time.time() - start_time) / 60
        print(f"  ⏳ Refresh state: {refresh.state.value} ({elapsed:.1f}m elapsed)")
        time.sleep(30)

    print(f"✗ Timeout after {timeout_minutes} minutes")
    return False
```

### List Refreshes

```python
refreshes = w.data_quality.list_refresh(
    object_type="table",
    object_id=table_id,
)
for r in refreshes:
    print(f"  Refresh {r.refresh_id}: {r.state}")
```

### Cancel Refresh

```python
w.data_quality.cancel_refresh(
    object_type="table",
    object_id=table_id,
    refresh_id=refresh_id,
)
```

## Monitor Mode Decision Matrix

| Table Type | Monitor Mode | Timestamp Column Required? | Drift Without Baseline? |
|------------|-------------|--------------------------|------------------------|
| Fact (daily transactions) | TimeSeries | ✅ Yes | ✅ Yes (consecutive windows) |
| Fact (aggregated) | TimeSeries | ✅ Yes | ✅ Yes |
| Dimension (SCD Type 1) | Snapshot | ❌ No | ❌ Must provide baseline_table |
| Dimension (SCD Type 2) | TimeSeries or Snapshot | Depends on use case | Depends on mode |
| Inference Log | TimeSeries | ✅ Yes | ✅ Yes |

**⚠️ CRITICAL:** Snapshot monitors REQUIRE a `baseline_table_name` for DRIFT metrics. Without it, drift metrics will not compute.

```python
# Snapshot with drift requires baseline
config = DataProfilingConfig(
    output_schema_id=monitoring_schema_id,
    snapshot=SnapshotConfig(),
    baseline_table_name=f"{catalog}.{schema}.{table}_baseline",
    custom_metrics=[...drift metrics...],
)
```

## Slicing Expressions

Slicing adds dimensional breakdowns to monitoring output.

```python
config = DataProfilingConfig(
    slicing_exprs=[
        "store_number",      # Slice by store
        "product_category",  # Slice by category
    ],
    ...
)
```

**Considerations:**
- Each unique slice value creates additional rows in output tables
- High-cardinality columns can cause performance issues
- Limit to 2-3 slicing expressions per monitor

## Delete and Cleanup

```python
def delete_monitor_with_cleanup(w, spark, catalog, schema, table, monitoring_schema):
    """Delete monitor and associated output tables."""
    table_id = get_table_id(w, catalog, schema, table)

    # Delete monitor definition
    try:
        w.data_quality.delete_monitor(
            object_type="table",
            object_id=table_id,
        )
        print(f"✓ Monitor deleted for {catalog}.{schema}.{table}")
    except Exception as e:
        if "not found" in str(e).lower():
            print(f"⚠️ No monitor found for {catalog}.{schema}.{table}")
        else:
            raise

    # Drop output tables
    for suffix in ["_profile_metrics", "_drift_metrics"]:
        fqn = f"{catalog}.{monitoring_schema}.{table}{suffix}"
        try:
            spark.sql(f"DROP TABLE IF EXISTS {fqn}")
            print(f"  ✓ Dropped {fqn}")
        except Exception as e:
            print(f"  ⚠️ Could not drop {fqn}: {e}")
```
