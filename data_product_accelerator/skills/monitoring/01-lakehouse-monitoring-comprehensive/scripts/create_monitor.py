"""
Core Monitor Management Functions

Uses the Databricks Data Quality API (databricks.sdk.service.dataquality).

Functions:
  - get_table_id() / get_schema_id() — UUID lookup helpers
  - create_table_monitor() — Full monitor creation with DataProfilingConfig
  - delete_monitor_if_exists() — Safe cleanup with output table drops
  - wait_with_progress() — Timer-based fallback wait
"""

import time

try:
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
        RefreshState,
    )

    SDK_AVAILABLE = True
except ImportError:
    print("WARNING: databricks-sdk dataquality module not available.")
    print("Install: pip install databricks-sdk>=0.68.0")
    SDK_AVAILABLE = False

from pyspark.sql import types as T


# ============================================================
# UUID Lookup Helpers
# ============================================================

def get_table_id(w, catalog: str, schema: str, table: str) -> str:
    """
    Get table UUID from three-level name.

    Critical: The Data Quality API requires UUIDs, NOT three-level names.

    Args:
        w: WorkspaceClient
        catalog: Catalog name
        schema: Schema name
        table: Table name

    Returns:
        str: Table UUID
    """
    table_info = w.tables.get(full_name=f"{catalog}.{schema}.{table}")
    return table_info.table_id


def get_schema_id(w, catalog: str, schema: str) -> str:
    """
    Get schema UUID from two-level name.

    Args:
        w: WorkspaceClient
        catalog: Catalog name
        schema: Schema name

    Returns:
        str: Schema UUID
    """
    schema_info = w.schemas.get(full_name=f"{catalog}.{schema}")
    return schema_info.schema_id


# ============================================================
# Monitor Creation
# ============================================================

def create_table_monitor(
    w,
    spark,
    catalog: str,
    schema: str,
    table: str,
    monitoring_schema: str,
    custom_metrics: list = None,
    timestamp_column: str = None,
    granularity=None,
    slicing_exprs: list = None,
    baseline_table_name: str = None,
):
    """
    Create a Data Profiling monitor on a table.

    Uses TimeSeries mode if timestamp_column provided, otherwise Snapshot.

    Args:
        w: WorkspaceClient
        spark: SparkSession
        catalog: Catalog name
        schema: Schema name containing the table
        table: Table name to monitor
        monitoring_schema: Schema name for output tables
        custom_metrics: List of DataProfilingCustomMetric objects
        timestamp_column: Column name for TimeSeries mode (None for Snapshot)
        granularity: AggregationGranularity enum (default: 1 day)
        slicing_exprs: Optional list of columns for dimensional breakdowns
        baseline_table_name: Required for DRIFT metrics in Snapshot mode

    Returns:
        Monitor object
    """
    if not SDK_AVAILABLE:
        raise RuntimeError("databricks-sdk dataquality module not available")

    # Ensure monitoring schema exists
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{monitoring_schema}")

    # Get UUIDs
    table_id = get_table_id(w, catalog, schema, table)
    output_schema_id = get_schema_id(w, catalog, monitoring_schema)

    # Configure monitor mode
    if timestamp_column:
        if granularity is None:
            granularity = AggregationGranularity.AGGREGATION_GRANULARITY_1_DAY
        time_series = TimeSeriesConfig(
            timestamp_column=timestamp_column,
            granularities=[granularity],
        )
        snapshot = None
        mode_label = f"TimeSeries ({timestamp_column}, {granularity.value})"
    else:
        time_series = None
        snapshot = SnapshotConfig()
        mode_label = "Snapshot"

    # Build config
    config = DataProfilingConfig(
        output_schema_id=output_schema_id,
        time_series=time_series,
        snapshot=snapshot,
        custom_metrics=custom_metrics or [],
        slicing_exprs=slicing_exprs or [],
        baseline_table_name=baseline_table_name,
    )

    # Create monitor
    monitor = w.data_quality.create_monitor(
        monitor=Monitor(
            object_type="table",
            object_id=table_id,
            data_profiling_config=config,
        )
    )

    metrics_count = len(custom_metrics) if custom_metrics else 0
    print(f"  Monitor created for {catalog}.{schema}.{table}")
    print(f"    Mode: {mode_label}")
    print(f"    Custom metrics: {metrics_count}")
    print(f"    Output: {catalog}.{monitoring_schema}")
    if slicing_exprs:
        print(f"    Slicing: {', '.join(slicing_exprs)}")

    return monitor


# ============================================================
# Monitor Deletion
# ============================================================

def delete_monitor_if_exists(w, spark, catalog, schema, table, monitoring_schema):
    """
    Delete a monitor and its output tables if they exist.

    Safe to call even if the monitor doesn't exist.

    Args:
        w: WorkspaceClient
        spark: SparkSession
        catalog: Catalog name
        schema: Schema name
        table: Table name
        monitoring_schema: Monitoring output schema name
    """
    # Try to delete monitor definition
    try:
        table_id = get_table_id(w, catalog, schema, table)
        w.data_quality.delete_monitor(
            object_type="table",
            object_id=table_id,
        )
        print(f"  Deleted monitor for {catalog}.{schema}.{table}")
    except Exception as e:
        if "not found" in str(e).lower() or "does not exist" in str(e).lower():
            print(f"  No monitor found for {catalog}.{schema}.{table} (OK)")
        else:
            print(f"  Warning deleting monitor: {e}")

    # Drop output tables
    for suffix in ["_profile_metrics", "_drift_metrics"]:
        fqn = f"{catalog}.{monitoring_schema}.{table}{suffix}"
        try:
            spark.sql(f"DROP TABLE IF EXISTS {fqn}")
            print(f"    Dropped {fqn}")
        except Exception as e:
            print(f"    Warning dropping {fqn}: {e}")


# ============================================================
# Wait for Initialization
# ============================================================

def wait_with_progress(table_name, wait_minutes=20):
    """
    Simple timer-based wait for monitor initialization.

    Fallback for when Refresh-based tracking is not available.
    Prefer wait_for_monitor_refresh() in scripts/wait_for_initialization.py.

    Args:
        table_name: Display name for progress messages
        wait_minutes: How long to wait
    """
    total_seconds = wait_minutes * 60
    start_time = time.time()

    print(f"  Waiting {wait_minutes} minutes for {table_name} monitor...")
    while time.time() - start_time < total_seconds:
        elapsed = (time.time() - start_time) / 60
        remaining = wait_minutes - elapsed
        print(f"    {elapsed:.1f}m elapsed, {remaining:.1f}m remaining...")
        time.sleep(60)

    print(f"  Wait complete for {table_name}")
