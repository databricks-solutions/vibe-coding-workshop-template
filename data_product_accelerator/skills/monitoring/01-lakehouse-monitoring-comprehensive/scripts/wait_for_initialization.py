"""
Monitor Initialization Wait Script

Uses Refresh-based tracking from the Data Quality API to poll for
monitor completion. Replaces the legacy status polling approach.

Usage (as Databricks notebook with widgets):
  Passed via base_parameters in Asset Bundle:
    catalog: Target catalog name
    schema: Gold schema name
    monitoring_schema: Schema for monitoring output tables

Usage (as standalone script):
  python wait_for_initialization.py --catalog my_catalog --schema gold --monitoring_schema gold_monitoring
"""

import argparse
import time

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.dataquality import (
    RefreshState,
)


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


# ============================================================
# Refresh-Based Wait
# ============================================================

def wait_for_monitor_refresh(
    w,
    catalog: str,
    schema: str,
    table: str,
    timeout_minutes: int = 30,
    poll_interval_seconds: int = 30,
):
    """
    Wait for the latest refresh of a table monitor to complete.

    Uses Refresh state tracking from the Data Quality API. This is the
    recommended approach, replacing legacy MonitorInfoStatus polling.

    Args:
        w: WorkspaceClient
        catalog: Catalog name
        schema: Schema name
        table: Table name
        timeout_minutes: Maximum wait time
        poll_interval_seconds: Seconds between polls

    Returns:
        bool: True if refresh succeeded, False otherwise
    """
    table_id = get_table_id(w, catalog, schema, table)
    start_time = time.time()
    timeout_seconds = timeout_minutes * 60
    full_name = f"{catalog}.{schema}.{table}"

    print(f"  Waiting for {full_name} monitor refresh...")

    while time.time() - start_time < timeout_seconds:
        try:
            # Get latest refreshes
            refreshes = w.data_quality.list_refresh(
                object_type="table",
                object_id=table_id,
            )

            # Find the most recent refresh (refresh_id is an int)
            latest = None
            for r in refreshes:
                if latest is None or (r.refresh_id is not None and (latest.refresh_id is None or r.refresh_id > latest.refresh_id)):
                    latest = r

            if latest is None:
                elapsed = (time.time() - start_time) / 60
                print(f"    No refreshes found yet ({elapsed:.1f}m elapsed)")
                time.sleep(poll_interval_seconds)
                continue

            if latest.state == RefreshState.MONITOR_REFRESH_STATE_SUCCESS:
                elapsed = (time.time() - start_time) / 60
                print(f"  Refresh SUCCEEDED for {full_name} ({elapsed:.1f}m)")
                return True

            elif latest.state in (
                RefreshState.MONITOR_REFRESH_STATE_FAILED,
                RefreshState.MONITOR_REFRESH_STATE_CANCELED,
            ):
                elapsed = (time.time() - start_time) / 60
                print(f"  Refresh {latest.state.value} for {full_name} ({elapsed:.1f}m)")
                return False

            else:
                elapsed = (time.time() - start_time) / 60
                remaining = timeout_minutes - elapsed
                print(f"    State: {latest.state.value} ({elapsed:.1f}m elapsed, {remaining:.1f}m remaining)")

        except Exception as e:
            elapsed = (time.time() - start_time) / 60
            print(f"    Error checking refresh: {e} ({elapsed:.1f}m elapsed)")

        time.sleep(poll_interval_seconds)

    print(f"  TIMEOUT after {timeout_minutes}m for {full_name}")
    return False


def wait_for_all_monitors(
    w,
    catalog: str,
    schema: str,
    tables: list,
    timeout_minutes: int = 30,
    poll_interval_seconds: int = 30,
):
    """
    Wait for all monitors to complete initialization.

    Polls all monitors in parallel, printing progress for each.

    Args:
        w: WorkspaceClient
        catalog: Catalog name
        schema: Schema name
        tables: List of table names to wait for
        timeout_minutes: Maximum wait time
        poll_interval_seconds: Seconds between polls

    Returns:
        dict: {"success": [...], "failed": [...], "timeout": [...]}
    """
    start_time = time.time()
    timeout_seconds = timeout_minutes * 60

    # Build table ID map
    pending = {}
    for table in tables:
        try:
            table_id = get_table_id(w, catalog, schema, table)
            pending[table] = table_id
        except Exception as e:
            print(f"  WARNING: Could not get ID for {table}: {e}")

    results = {"success": [], "failed": [], "timeout": []}

    print(f"\nWaiting for {len(pending)} monitors (timeout: {timeout_minutes}m)...")
    print("=" * 60)

    while pending and (time.time() - start_time < timeout_seconds):
        completed = []

        for table, table_id in pending.items():
            try:
                refreshes = w.data_quality.list_refresh(
                    object_type="table",
                    object_id=table_id,
                )

                # Find the most recent refresh (refresh_id is an int)
                latest = None
                for r in refreshes:
                    if latest is None or (r.refresh_id is not None and (latest.refresh_id is None or r.refresh_id > latest.refresh_id)):
                        latest = r

                if latest is None:
                    continue

                if latest.state == RefreshState.MONITOR_REFRESH_STATE_SUCCESS:
                    elapsed = (time.time() - start_time) / 60
                    print(f"  OK: {table} ({elapsed:.1f}m)")
                    results["success"].append(table)
                    completed.append(table)
                elif latest.state in (
                    RefreshState.MONITOR_REFRESH_STATE_FAILED,
                    RefreshState.MONITOR_REFRESH_STATE_CANCELED,
                ):
                    elapsed = (time.time() - start_time) / 60
                    print(f"  FAIL: {table} — {latest.state.value} ({elapsed:.1f}m)")
                    results["failed"].append(table)
                    completed.append(table)

            except Exception as e:
                pass  # Continue polling

        for table in completed:
            del pending[table]

        if pending:
            elapsed = (time.time() - start_time) / 60
            remaining = timeout_minutes - elapsed
            print(f"\n  Polling... {len(pending)} pending, {elapsed:.1f}m elapsed, {remaining:.1f}m remaining")
            time.sleep(poll_interval_seconds)

    # Handle remaining as timeout
    for table in pending:
        results["timeout"].append(table)
        print(f"  TIMEOUT: {table}")

    # Summary
    print(f"\n{'=' * 60}")
    print(f"Results: {len(results['success'])} succeeded, {len(results['failed'])} failed, {len(results['timeout'])} timed out")
    return results


# ============================================================
# Main
# ============================================================

def main():
    catalog, schema, monitoring_schema = get_params()
    w = WorkspaceClient()

    # List tables that have monitors
    # NOTE: Customize this list to match your setup_monitors_template.py
    tables_to_wait = [
        "fact_sales_daily",
        "dim_store",
    ]

    print(f"Monitor Initialization Wait")
    print(f"Catalog: {catalog}")
    print(f"Schema: {schema}")
    print(f"Tables: {len(tables_to_wait)}")

    results = wait_for_all_monitors(
        w=w,
        catalog=catalog,
        schema=schema,
        tables=tables_to_wait,
        timeout_minutes=30,
        poll_interval_seconds=30,
    )

    if results["failed"] or results["timeout"]:
        failed_count = len(results["failed"]) + len(results["timeout"])
        raise RuntimeError(
            f"{failed_count} monitors did not complete successfully"
        )

    print("\nAll monitors initialized successfully!")


if __name__ == "__main__":
    main()
