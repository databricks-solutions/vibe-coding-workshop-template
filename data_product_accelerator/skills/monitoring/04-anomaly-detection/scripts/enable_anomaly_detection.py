"""
Anomaly Detection Management

Enable, disable, and check schema-level anomaly detection
using the Databricks Data Quality API (Public Preview).

SDK Module: databricks.sdk.service.dataquality

Usage:
  python enable_anomaly_detection.py --catalog my_catalog --schema my_gold --action enable
  python enable_anomaly_detection.py --catalog my_catalog --schema my_gold --action disable
  python enable_anomaly_detection.py --catalog my_catalog --schema my_gold --action status
"""

import argparse

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.dataquality import Monitor, AnomalyDetectionConfig


def get_schema_id(w: WorkspaceClient, catalog: str, schema: str) -> str:
    """
    Get the schema UUID required by the Data Quality API.

    Critical: The API requires a UUID (schema_id), NOT the three-level name.
    """
    schema_info = w.schemas.get(full_name=f"{catalog}.{schema}")
    return schema_info.schema_id


def enable_anomaly_detection(
    w: WorkspaceClient,
    catalog: str,
    schema: str,
    excluded_tables: list = None,
):
    """
    Enable anomaly detection on a schema.

    Args:
        w: WorkspaceClient
        catalog: Catalog name
        schema: Schema name
        excluded_tables: Optional list of table names (without catalog.schema prefix)
                         to exclude from monitoring
    """
    schema_id = get_schema_id(w, catalog, schema)

    # Build exclusion list with fully qualified names
    excluded_full_names = None
    if excluded_tables:
        excluded_full_names = [
            f"{catalog}.{schema}.{table}" for table in excluded_tables
        ]

    config = AnomalyDetectionConfig(
        excluded_table_full_names=excluded_full_names
    )

    try:
        monitor = w.data_quality.create_monitor(
            monitor=Monitor(
                object_type="schema",
                object_id=schema_id,
                anomaly_detection_config=config,
            )
        )
        print(f"✓ Anomaly detection enabled on {catalog}.{schema}")
        print(f"  Schema ID: {schema_id}")
        if excluded_full_names:
            print(f"  Excluded tables: {len(excluded_full_names)}")
            for t in excluded_full_names:
                print(f"    - {t}")
        return monitor
    except Exception as e:
        if "already exists" in str(e).lower():
            print(f"⚠️  Anomaly detection already enabled on {catalog}.{schema}")
            print(f"   Use --action status to check, or --action disable then re-enable")
        else:
            print(f"✗ Error enabling anomaly detection: {str(e)}")
            raise


def disable_anomaly_detection(
    w: WorkspaceClient, catalog: str, schema: str
):
    """
    Disable anomaly detection on a schema.

    WARNING: This deletes ALL anomaly detection data. Cannot be undone.
    """
    schema_id = get_schema_id(w, catalog, schema)

    try:
        w.data_quality.delete_monitor(
            object_type="schema",
            object_id=schema_id,
        )
        print(f"✓ Anomaly detection disabled on {catalog}.{schema}")
        print(f"  ⚠️  All monitoring data has been deleted (irreversible)")
    except Exception as e:
        if "does not exist" in str(e).lower() or "not found" in str(e).lower():
            print(f"⚠️  No anomaly detection monitor found on {catalog}.{schema}")
        else:
            print(f"✗ Error disabling anomaly detection: {str(e)}")
            raise


def check_status(w: WorkspaceClient, catalog: str, schema: str):
    """
    Check anomaly detection status for a schema.
    """
    schema_id = get_schema_id(w, catalog, schema)

    try:
        monitor = w.data_quality.get_monitor(
            object_type="schema",
            object_id=schema_id,
        )
        print(f"✓ Anomaly detection is ENABLED on {catalog}.{schema}")
        print(f"  Object Type: {monitor.object_type}")
        print(f"  Object ID: {monitor.object_id}")
        if monitor.anomaly_detection_config:
            excluded = monitor.anomaly_detection_config.excluded_table_full_names or []
            print(f"  Excluded tables: {len(excluded)}")
            for t in excluded:
                print(f"    - {t}")
        return monitor
    except Exception as e:
        if "does not exist" in str(e).lower() or "not found" in str(e).lower():
            print(f"⚠️  Anomaly detection is NOT enabled on {catalog}.{schema}")
        else:
            print(f"✗ Error checking status: {str(e)}")
            raise


def list_all_monitors(w: WorkspaceClient):
    """
    List all monitors in the workspace (both anomaly detection and data profiling).

    NOTE: list_monitor() is marked as (Unimplemented) in the SDK as of v0.68.0.
    This function may fail until the SDK implements it. Use get_monitor() for
    individual lookups instead.
    """
    print("All monitors in workspace:")
    print("=" * 60)

    monitors = w.data_quality.list_monitor()
    ad_count = 0
    dp_count = 0

    for monitor in monitors:
        if monitor.anomaly_detection_config:
            ad_count += 1
            excluded = monitor.anomaly_detection_config.excluded_table_full_names or []
            print(f"  [Anomaly Detection] schema/{monitor.object_id}")
            if excluded:
                print(f"    Excluded: {len(excluded)} tables")
        elif monitor.data_profiling_config:
            dp_count += 1
            status = monitor.data_profiling_config.status or "Unknown"
            table = monitor.data_profiling_config.monitored_table_name or "Unknown"
            print(f"  [Data Profiling] table/{monitor.object_id} ({table}) - {status}")

    print("=" * 60)
    print(f"Total: {ad_count} anomaly detection + {dp_count} data profiling")


def main():
    parser = argparse.ArgumentParser(
        description="Manage Anomaly Detection"
    )
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--schema", required=True)
    parser.add_argument(
        "--action",
        choices=["enable", "disable", "status", "list"],
        default="status",
    )
    parser.add_argument(
        "--exclude",
        nargs="*",
        help="Table names to exclude (without catalog.schema prefix)",
    )

    args = parser.parse_args()
    w = WorkspaceClient()

    if args.action == "enable":
        enable_anomaly_detection(w, args.catalog, args.schema, args.exclude)
    elif args.action == "disable":
        disable_anomaly_detection(w, args.catalog, args.schema)
    elif args.action == "status":
        check_status(w, args.catalog, args.schema)
    elif args.action == "list":
        list_all_monitors(w)


if __name__ == "__main__":
    main()
