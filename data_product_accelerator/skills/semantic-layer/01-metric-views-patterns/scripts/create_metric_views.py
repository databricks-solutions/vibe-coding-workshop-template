#!/usr/bin/env python3
# Databricks notebook source

"""
Metric Views Creation Script

Creates Metric Views from YAML configuration for Genie AI and AI/BI dashboards.

Supports two YAML architectures:
  - Per-file mode (preferred): One YAML file per metric view, filename = view name
  - Multi-file mode: Single YAML file with list of metric views

Critical: Uses 'WITH METRICS LANGUAGE YAML' syntax (not TBLPROPERTIES).
Critical: The 'name' field is NEVER included in the YAML content sent to Databricks.

Usage (per-file mode - preferred):
  As Databricks notebook (via Asset Bundle job):
    base_parameters:
      catalog: my_catalog
      gold_schema: my_gold
      yaml_dir: src/semantic/metric_views

  As standalone script:
    python create_metric_views.py --catalog my_catalog --gold_schema my_gold \\
        --yaml-dir src/semantic/metric_views/

Usage (multi-file mode):
    python create_metric_views.py --catalog my_catalog --gold_schema my_gold \\
        --yaml-file metric_views.yaml
"""

import os
import sys
import yaml
from pathlib import Path


# ===========================================================================
# PATH SETUP FOR ASSET BUNDLE IMPORTS
# ===========================================================================
try:
    _notebook_path = (
        dbutils.notebook.entry_point.getDbutils()
        .notebook()
        .getContext()
        .notebookPath()
        .get()
    )
    _bundle_root = "/Workspace" + str(_notebook_path).rsplit("/src/", 1)[0]
    if _bundle_root not in sys.path:
        sys.path.insert(0, _bundle_root)
        print(f"✓ Added bundle root to sys.path: {_bundle_root}")
except Exception:
    pass  # Local execution or non-notebook — skip path setup
# ===========================================================================


def get_parameters():
    """
    Get parameters from dbutils widgets (Databricks) or argparse (local).

    Returns: dict with 'catalog', 'gold_schema', and either 'yaml_dir' or 'yaml_file'
    """
    try:
        # Databricks notebook mode — use widgets
        catalog = dbutils.widgets.get("catalog")
        gold_schema = dbutils.widgets.get("gold_schema")
        yaml_dir = dbutils.widgets.get("yaml_dir")
        return {
            "catalog": catalog,
            "gold_schema": gold_schema,
            "yaml_dir": yaml_dir,
            "yaml_file": None,
        }
    except Exception:
        pass

    # Local / CLI mode — use argparse
    import argparse

    parser = argparse.ArgumentParser(description="Create Metric Views from YAML")
    parser.add_argument("--catalog", required=True, help="Unity Catalog name")
    parser.add_argument("--gold_schema", required=True, help="Gold schema name")

    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--yaml-dir",
        help="Directory containing individual metric view YAML files (preferred)",
    )
    mode_group.add_argument(
        "--yaml-file",
        help="Single YAML file containing list of metric views",
    )

    args = parser.parse_args()
    return {
        "catalog": args.catalog,
        "gold_schema": args.gold_schema,
        "yaml_dir": getattr(args, "yaml_dir", None),
        "yaml_file": getattr(args, "yaml_file", None),
    }


def load_metric_views_per_file(yaml_dir, catalog, schema):
    """
    Load metric views from individual YAML files (one per view).

    Preferred architecture: filename (without .yaml) becomes the view name.
    The YAML content must NOT contain a 'name' field.

    Returns: List of (view_name, metric_view_dict) tuples
    """
    yaml_path = Path(yaml_dir)
    if not yaml_path.exists():
        raise FileNotFoundError(f"YAML directory not found: {yaml_dir}")

    metric_views = []

    for yaml_file in sorted(yaml_path.glob("*.yaml")):
        view_name = yaml_file.stem  # filename without extension

        with open(yaml_file, "r") as f:
            yaml_content = f.read()

        # Substitute parameters
        yaml_content = yaml_content.replace("${catalog}", catalog)
        yaml_content = yaml_content.replace("${gold_schema}", schema)

        metric_view = yaml.safe_load(yaml_content)

        if metric_view is None:
            print(f"  ⚠ Skipping empty file: {yaml_file.name}")
            continue

        # Safety: remove 'name' if accidentally included (causes v1.1 error)
        metric_view.pop("name", None)

        metric_views.append((view_name, metric_view))

    return metric_views


def load_metric_views_multi_file(yaml_file, catalog, schema):
    """
    Load metric views from a single YAML file containing a list of views.

    Each list item must have a 'name' field for routing (used in CREATE VIEW).
    The 'name' field is stripped before sending YAML to Databricks.
    Each list item should include 'version: "1.1"'.

    Returns: List of (view_name, metric_view_dict) tuples
    """
    with open(yaml_file, "r") as f:
        yaml_content = f.read()

    # Substitute parameters
    yaml_content = yaml_content.replace("${catalog}", catalog)
    yaml_content = yaml_content.replace("${gold_schema}", schema)

    raw = yaml.safe_load(yaml_content)

    # Handle both list format and mapping-with-list format
    if isinstance(raw, list):
        views_list = raw
    elif isinstance(raw, dict):
        # If there's a top-level version, inject into each view that lacks it
        top_version = raw.get("version")
        views_list = raw.get("views", raw.get("metric_views", []))
        if top_version and isinstance(views_list, list):
            for view in views_list:
                if isinstance(view, dict) and "version" not in view:
                    view["version"] = top_version
    else:
        raise ValueError(f"Unexpected YAML structure in {yaml_file}")

    metric_views = []
    for item in views_list:
        if not isinstance(item, dict):
            continue

        # Extract name for CREATE VIEW statement (NOT sent to Databricks)
        view_name = item.pop("name", None)
        if not view_name:
            raise ValueError(
                "Each metric view in multi-file mode must have a 'name' field"
            )

        metric_views.append((view_name, item))

    return metric_views


def create_metric_view(spark, catalog, schema, view_name, metric_view):
    """
    Create a single metric view using WITH METRICS LANGUAGE YAML syntax.

    Critical: The 'name' field must NOT be in metric_view dict.
    It causes 'Unrecognized field "name"' error in Databricks v1.1.
    """
    fully_qualified_name = f"{catalog}.{schema}.{view_name}"

    print(f"\nCreating metric view: {fully_qualified_name}")

    # Drop existing table/view (might conflict with metric view)
    try:
        spark.sql(f"DROP VIEW IF EXISTS {fully_qualified_name}")
        spark.sql(f"DROP TABLE IF EXISTS {fully_qualified_name}")
    except Exception:
        pass

    # Safety: ensure no 'name' field in YAML content
    metric_view_clean = dict(metric_view)
    metric_view_clean.pop("name", None)

    # Convert to YAML string (this goes inside AS $$...$$)
    yaml_str = yaml.dump(
        metric_view_clean, default_flow_style=False, sort_keys=False
    )

    # Escape single quotes in comment for SQL
    view_comment = metric_view_clean.get("comment", "Metric view for Genie AI")
    if isinstance(view_comment, str):
        view_comment_escaped = view_comment.replace("'", "''").strip()
    else:
        view_comment_escaped = str(view_comment).replace("'", "''").strip()

    # ✅ CORRECT: WITH METRICS LANGUAGE YAML syntax
    create_sql = f"""
    CREATE VIEW {fully_qualified_name}
    WITH METRICS
    LANGUAGE YAML
    COMMENT '{view_comment_escaped}'
    AS $$
{yaml_str}
    $$
    """

    try:
        spark.sql(create_sql)
        print(f"  ✓ Created metric view: {view_name}")

        # Verify it's a METRIC_VIEW (not just VIEW)
        result = spark.sql(
            f"DESCRIBE EXTENDED {fully_qualified_name}"
        ).collect()
        view_type = next(
            (row.data_type for row in result if row.col_name == "Type"),
            "UNKNOWN",
        )

        if view_type == "METRIC_VIEW":
            print(f"  ✓ Verified as METRIC_VIEW")
        else:
            print(f"  ⚠ Warning: Type is {view_type}, expected METRIC_VIEW")

        return True

    except Exception as e:
        print(f"  ✗ Error creating {view_name}: {str(e)}")
        return False


def main():
    """
    Main entry point for metric views creation.

    Reads metric view YAML files and creates all metric views.
    Raises RuntimeError if any metric view fails (job should fail, not succeed silently).
    """
    params = get_parameters()

    catalog = params["catalog"]
    gold_schema = params["gold_schema"]
    yaml_dir = params.get("yaml_dir")
    yaml_file = params.get("yaml_file")

    from pyspark.sql import SparkSession

    spark = SparkSession.builder.appName("Create Metric Views").getOrCreate()

    print("=" * 80)
    print("METRIC VIEWS CREATION")
    print("=" * 80)
    print(f"Catalog: {catalog}")
    print(f"Schema:  {gold_schema}")

    if yaml_dir:
        print(f"Mode:    Per-file (directory: {yaml_dir})")
    else:
        print(f"Mode:    Multi-file (file: {yaml_file})")
    print("=" * 80)

    try:
        # Load metric views based on mode
        if yaml_dir:
            metric_views = load_metric_views_per_file(
                yaml_dir, catalog, gold_schema
            )
        else:
            metric_views = load_metric_views_multi_file(
                yaml_file, catalog, gold_schema
            )

        print(f"\nLoaded {len(metric_views)} metric view(s)")

        if not metric_views:
            print("⚠ No metric views found. Nothing to create.")
            return

        # Create each metric view
        success_count = 0
        failed_views = []

        for view_name, metric_view in metric_views:
            if create_metric_view(
                spark, catalog, gold_schema, view_name, metric_view
            ):
                success_count += 1
            else:
                failed_views.append(view_name)

        print("\n" + "=" * 80)
        print(f"Created {success_count} of {len(metric_views)} metric views")

        if failed_views:
            print(f"❌ Failed to create: {', '.join(failed_views)}")
            # ✅ Raise exception to fail the job
            raise RuntimeError(
                f"Failed to create {len(failed_views)} metric view(s): "
                f"{', '.join(failed_views)}"
            )

        print("✅ All metric views deployed successfully!")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        raise

    finally:
        spark.stop()


if __name__ == "__main__":
    main()
