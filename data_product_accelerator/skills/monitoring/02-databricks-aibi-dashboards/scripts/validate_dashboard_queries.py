"""
Pre-deployment SQL validation for Lakeview dashboard queries.

Executes each dataset query with LIMIT 1 against a live warehouse using the
Databricks SDK. Catches UNRESOLVED_COLUMN, TABLE_OR_VIEW_NOT_FOUND,
UNBOUND_SQL_PARAMETER, DATATYPE_MISMATCH, and AMBIGUOUS_REFERENCE errors
before dashboard import.

Usage:
  python validate_dashboard_queries.py DASHBOARD_PATH \
    --catalog CATALOG --gold-schema SCHEMA \
    [--warehouse-id WAREHOUSE_ID] [--profile PROFILE]

Example:
  python validate_dashboard_queries.py docs/dashboards/analytics.lvdash.json \
    --catalog my_catalog --gold-schema my_gold --profile DEFAULT
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


# Default substitutions for common dashboard parameter names. Extend this map
# if your dashboard uses additional :param names.
PARAM_SUBSTITUTIONS: dict[str, str] = {
    # Time range parameters
    r":time_range\.min": "CURRENT_DATE() - INTERVAL 30 DAYS",
    r":time_range\.max": "CURRENT_DATE()",
    r":start_date": "CURRENT_DATE() - INTERVAL 30 DAYS",
    r":end_date": "CURRENT_DATE()",
    r":monitor_time_start": "CURRENT_DATE() - INTERVAL 30 DAYS",
    r":monitor_time_end": "CURRENT_DATE()",
    # Multi-select parameters (return ARRAY)
    r":param_workspace": "ARRAY('All')",
    r":param_catalog": "ARRAY('All')",
    r":param_sku": "ARRAY('All')",
    # Single-select parameters
    r":monitor_slice_key": "'No Slice'",
    r":monitor_slice_value": "'No Slice'",
    # Text input parameters
    r":annual_commit": "1000000",
}


def substitute_parameters(query: str) -> str:
    """Substitute dashboard parameters with test values."""
    result = query
    for pattern, replacement in PARAM_SUBSTITUTIONS.items():
        result = re.sub(pattern, replacement, result)
    return result


def substitute_variables(query: str, catalog: str, gold_schema: str) -> str:
    """Substitute ${catalog} and ${gold_schema} variables with real values."""
    return (
        query.replace("${catalog}", catalog)
        .replace("${gold_schema}", gold_schema)
        .replace("${schema}", gold_schema)
    )


def categorize_error(error_str: str) -> dict:
    """Extract structured info from SQL errors."""
    result: dict = {"error_type": "OTHER"}

    if "UNRESOLVED_COLUMN" in error_str:
        result["error_type"] = "COLUMN_NOT_FOUND"
        match = re.search(r"name `([^`]+)`", error_str)
        if match:
            result["column"] = match.group(1)
        match = re.search(r"Did you mean one of the following\? \[([^\]]+)\]", error_str)
        if match:
            result["suggestions"] = match.group(1)
    elif "AMBIGUOUS_REFERENCE" in error_str:
        result["error_type"] = "AMBIGUOUS_COLUMN"
        match = re.search(r"Reference `([^`]+)`", error_str)
        if match:
            result["column"] = match.group(1)
    elif "TABLE_OR_VIEW_NOT_FOUND" in error_str:
        result["error_type"] = "TABLE_NOT_FOUND"
        match = re.search(r"table or view `([^`]+)`", error_str)
        if match:
            result["table"] = match.group(1)
    elif "UNBOUND_SQL_PARAMETER" in error_str:
        result["error_type"] = "UNBOUND_PARAMETER"
    elif "DATATYPE_MISMATCH" in error_str:
        result["error_type"] = "DATATYPE_MISMATCH"

    return result


def extract_query(dataset: dict) -> str:
    """Extract SQL from a dataset, supporting both `query` and `queryLines`."""
    if "query" in dataset:
        return dataset["query"]
    if "queryLines" in dataset:
        return "\n".join(dataset["queryLines"])
    return ""


def validate_query(client, warehouse_id: str, dataset_name: str, query: str) -> dict:
    """Validate a single query by executing SELECT * FROM (query) LIMIT 1."""
    wrapped = f"SELECT * FROM ({query}) _validation_view LIMIT 1"
    try:
        client.statement_execution.execute_statement(
            warehouse_id=warehouse_id,
            statement=wrapped,
            wait_timeout="30s",
        )
        return {"dataset": dataset_name, "status": "OK", "error": None}
    except Exception as e:  # noqa: BLE001 — surface all error types for reporting
        return {
            "dataset": dataset_name,
            "status": "ERROR",
            "error": str(e),
            "category": categorize_error(str(e)),
        }


def validate_dashboard(
    client,
    warehouse_id: str,
    dashboard_path: Path,
    catalog: str,
    gold_schema: str,
) -> list[dict]:
    """Validate all dataset queries in a dashboard JSON file."""
    with open(dashboard_path) as f:
        dashboard = json.load(f)

    results: list[dict] = []
    for dataset in dashboard.get("datasets", []):
        name = dataset.get("name", "<unnamed>")
        raw_query = extract_query(dataset)
        if not raw_query:
            results.append(
                {"dataset": name, "status": "SKIP", "error": "No query found"}
            )
            continue

        query = substitute_variables(
            substitute_parameters(raw_query), catalog, gold_schema
        )

        result = validate_query(client, warehouse_id, name, query)
        results.append(result)

        icon = "OK " if result["status"] == "OK" else "FAIL"
        print(f"  [{icon}] {name}")
        if result.get("error"):
            print(f"         {result['error'][:200]}")

    return results


def resolve_warehouse_id(client, override: str | None) -> str:
    """Use override if provided, otherwise pick the first available warehouse."""
    if override:
        return override
    warehouses = list(client.warehouses.list())
    if not warehouses:
        raise RuntimeError(
            "No SQL warehouses available in this workspace. "
            "Pass --warehouse-id explicitly."
        )
    return warehouses[0].id


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate dashboard SQL queries against a live warehouse."
    )
    parser.add_argument(
        "dashboard",
        type=Path,
        help="Path to the .lvdash.json dashboard file",
    )
    parser.add_argument(
        "--catalog",
        required=True,
        help="Catalog name to substitute for ${catalog}",
    )
    parser.add_argument(
        "--gold-schema",
        required=True,
        help="Schema name to substitute for ${gold_schema}",
    )
    parser.add_argument(
        "--warehouse-id",
        help="Warehouse ID to execute queries against (defaults to first available)",
    )
    parser.add_argument(
        "--profile",
        default="DEFAULT",
        help="Databricks CLI profile (default: DEFAULT)",
    )
    args = parser.parse_args()

    if not args.dashboard.exists():
        print(f"Error: dashboard file not found: {args.dashboard}", file=sys.stderr)
        return 2

    try:
        from databricks.sdk import WorkspaceClient
    except ImportError:
        print(
            "Error: databricks-sdk is not installed. Run: pip install databricks-sdk",
            file=sys.stderr,
        )
        return 2

    client = WorkspaceClient(profile=args.profile)
    warehouse_id = resolve_warehouse_id(client, args.warehouse_id)

    print(f"Validating: {args.dashboard}")
    print(f"Catalog:    {args.catalog}")
    print(f"Schema:     {args.gold_schema}")
    print(f"Warehouse:  {warehouse_id}")
    print("-" * 60)

    results = validate_dashboard(
        client, warehouse_id, args.dashboard, args.catalog, args.gold_schema
    )

    ok = sum(1 for r in results if r["status"] == "OK")
    failed = sum(1 for r in results if r["status"] == "ERROR")
    skipped = sum(1 for r in results if r["status"] == "SKIP")

    print("-" * 60)
    print(f"Results: {ok} passed, {failed} failed, {skipped} skipped")

    if failed:
        print("\nFailed datasets:")
        for r in results:
            if r["status"] == "ERROR":
                print(f"  - {r['dataset']}: {r['error'][:150]}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
