"""
Monitor Setup Template — Complete Notebook

Uses the Databricks Data Quality API (databricks.sdk.service.dataquality).

Usage (as Databricks notebook with widgets):
  Passed via base_parameters in Asset Bundle:
    catalog: Target catalog name
    schema: Gold schema name
    monitoring_schema: Schema for monitoring output tables

Usage (as standalone script):
  python setup_monitors_template.py --catalog my_catalog --schema gold --monitoring_schema gold_monitoring
"""

import argparse
import time

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


# ============================================================
# Configuration
# ============================================================

def get_params():
    """Get parameters from widgets (notebook) or argparse (standalone)."""
    try:
        catalog = dbutils.widgets.get("catalog")
        schema = dbutils.widgets.get("schema")
        monitoring_schema = dbutils.widgets.get("monitoring_schema")
    except Exception:
        parser = argparse.ArgumentParser()
        parser.add_argument("--catalog", required=True)
        parser.add_argument("--schema", required=True)
        parser.add_argument("--monitoring_schema", required=True)
        args = parser.parse_args()
        catalog = args.catalog
        schema = args.schema
        monitoring_schema = args.monitoring_schema

    return catalog, schema, monitoring_schema


# ============================================================
# UUID Helpers
# ============================================================

def get_table_id(w, catalog, schema, table):
    """Get table UUID from three-level name."""
    return w.tables.get(full_name=f"{catalog}.{schema}.{table}").table_id


def get_schema_id(w, catalog, schema):
    """Get schema UUID from two-level name."""
    return w.schemas.get(full_name=f"{catalog}.{schema}").schema_id


# ============================================================
# Monitor Management
# ============================================================

def delete_existing_monitor(w, spark, catalog, schema, table, monitoring_schema):
    """Delete existing monitor and output tables (safe to call if none exists)."""
    try:
        table_id = get_table_id(w, catalog, schema, table)
        w.data_quality.delete_monitor(object_type="table", object_id=table_id)
        print(f"  Deleted existing monitor for {table}")
    except Exception as e:
        if "not found" in str(e).lower() or "does not exist" in str(e).lower():
            pass  # No existing monitor
        else:
            print(f"  Warning: {e}")

    for suffix in ["_profile_metrics", "_drift_metrics"]:
        fqn = f"{catalog}.{monitoring_schema}.{table}{suffix}"
        try:
            spark.sql(f"DROP TABLE IF EXISTS {fqn}")
        except Exception:
            pass


def create_monitor_with_custom_metrics(
    w,
    spark,
    catalog,
    schema,
    table,
    monitoring_schema,
    custom_metrics,
    timestamp_column=None,
    granularity=None,
    slicing_exprs=None,
    baseline_table_name=None,
    recreate=True,
):
    """
    Create a Data Profiling monitor with custom metrics.

    Args:
        w: WorkspaceClient
        spark: SparkSession
        catalog: Catalog name
        schema: Schema name
        table: Table name
        monitoring_schema: Output schema name
        custom_metrics: List of DataProfilingCustomMetric objects
        timestamp_column: For TimeSeries mode (None = Snapshot)
        granularity: AggregationGranularity enum
        slicing_exprs: Dimensional breakdown columns
        baseline_table_name: Required for DRIFT in Snapshot mode
        recreate: If True, delete existing monitor first

    Returns:
        Monitor object
    """
    if recreate:
        delete_existing_monitor(w, spark, catalog, schema, table, monitoring_schema)

    # Get UUIDs
    table_id = get_table_id(w, catalog, schema, table)
    output_schema_id = get_schema_id(w, catalog, monitoring_schema)

    # Configure mode
    if timestamp_column:
        if granularity is None:
            granularity = AggregationGranularity.AGGREGATION_GRANULARITY_1_DAY
        time_series = TimeSeriesConfig(
            timestamp_column=timestamp_column,
            granularities=[granularity],
        )
        snapshot = None
    else:
        time_series = None
        snapshot = SnapshotConfig()

    config = DataProfilingConfig(
        output_schema_id=output_schema_id,
        time_series=time_series,
        snapshot=snapshot,
        custom_metrics=custom_metrics,
        slicing_exprs=slicing_exprs or [],
        baseline_table_name=baseline_table_name,
    )

    monitor = w.data_quality.create_monitor(
        monitor=Monitor(
            object_type="table",
            object_id=table_id,
            data_profiling_config=config,
        )
    )

    print(f"  Created monitor for {catalog}.{schema}.{table}")
    print(f"    Custom metrics: {len(custom_metrics)}")
    return monitor


# ============================================================
# Define Your Monitors Here
# ============================================================

def define_monitors(catalog, schema):
    """
    Define all monitors for the Gold schema.

    Returns:
        List of dicts with monitor configuration.
    """
    monitors = [
        {
            "table": "fact_sales_daily",
            "timestamp_column": "transaction_date",
            "slicing_exprs": ["store_number"],
            "custom_metrics": [
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
                    name="avg_basket_size",
                    input_columns=[":table"],
                    definition="total_revenue / NULLIF(total_transactions, 0)",
                    output_data_type=T.StructField("output", T.DoubleType()).json()
                ),
            ],
        },
        {
            "table": "dim_store",
            "timestamp_column": None,  # Snapshot mode
            "slicing_exprs": None,
            "custom_metrics": [
                DataProfilingCustomMetric(
                    type=DataProfilingCustomMetricType.DATA_PROFILING_CUSTOM_METRIC_TYPE_AGGREGATE,
                    name="total_stores",
                    input_columns=[":table"],
                    definition="COUNT(DISTINCT store_number)",
                    output_data_type=T.StructField("output", T.LongType()).json()
                ),
            ],
        },
    ]

    return monitors


# ============================================================
# Main
# ============================================================

def main():
    catalog, schema, monitoring_schema = get_params()
    w = WorkspaceClient()
    spark = SparkSession.builder.getOrCreate()

    print(f"Monitor Setup: {catalog}.{schema}")
    print(f"Output Schema: {catalog}.{monitoring_schema}")
    print("=" * 60)

    # Ensure monitoring schema exists
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{monitoring_schema}")

    # Get monitor definitions
    monitors = define_monitors(catalog, schema)
    print(f"\nMonitors to create: {len(monitors)}")

    # Track results
    results = {"success": [], "failed": []}

    for monitor_def in monitors:
        table = monitor_def["table"]
        print(f"\n--- {table} ---")

        try:
            create_monitor_with_custom_metrics(
                w=w,
                spark=spark,
                catalog=catalog,
                schema=schema,
                table=table,
                monitoring_schema=monitoring_schema,
                custom_metrics=monitor_def["custom_metrics"],
                timestamp_column=monitor_def.get("timestamp_column"),
                slicing_exprs=monitor_def.get("slicing_exprs"),
                recreate=True,
            )
            results["success"].append(table)
        except Exception as e:
            print(f"  FAILED: {e}")
            results["failed"].append((table, str(e)))

    # Summary
    print(f"\n{'=' * 60}")
    print(f"Results: {len(results['success'])} succeeded, {len(results['failed'])} failed")
    for table in results["success"]:
        print(f"  OK: {table}")
    for table, error in results["failed"]:
        print(f"  FAIL: {table} — {error}")

    if results["failed"]:
        raise RuntimeError(f"{len(results['failed'])} monitors failed to create")


if __name__ == "__main__":
    main()
