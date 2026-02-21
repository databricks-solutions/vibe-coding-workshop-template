# Databricks notebook source

"""
Accumulating Snapshot Fact Table MERGE Pattern

Accumulating snapshots track the lifecycle of a business process with milestone
columns that fill in over time (e.g., order_date → ship_date → delivery_date).
Unlike transaction facts, rows are UPDATED as milestones are reached.

YAML Properties that trigger this pattern:
  table_properties.grain_type: accumulating_snapshot
  table_properties.entity_type: fact

Key Characteristics:
  - One row per business process instance (e.g., one row per order)
  - Milestone columns start as NULL, filled as events occur
  - Lag/duration columns calculated between milestones
  - Row is updated (not inserted) when new milestones are reached
"""

import yaml
from pathlib import Path
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, current_timestamp, when, datediff, lit, coalesce
)
from delta.tables import DeltaTable


def find_yaml_base() -> Path:
    """Find YAML directory - works in Databricks and locally."""
    possible_paths = [
        Path("../../gold_layer_design/yaml"),
        Path("gold_layer_design/yaml"),
    ]
    for path in possible_paths:
        if path.exists():
            return path
    raise FileNotFoundError(
        "YAML directory not found. Ensure YAMLs are synced in databricks.yml"
    )


def load_table_metadata(yaml_path: Path) -> dict:
    """Extract ALL merge-relevant metadata from a single YAML file."""
    with open(yaml_path) as f:
        config = yaml.safe_load(f)
    columns = config.get("columns", [])
    table_props = config.get("table_properties", {})
    source_tables = set()
    lineage_map = {}
    for c in columns:
        lin = c.get("lineage", {})
        if lin:
            lineage_map[c["name"]] = lin
            if lin.get("source_table"):
                source_tables.add(lin["source_table"])
    return {
        "table_name": config["table_name"],
        "columns": [c["name"] for c in columns],
        "column_types": {c["name"]: c["type"] for c in columns},
        "pk_columns": config.get("primary_key", {}).get("columns", []),
        "business_key": config.get("business_key", {}).get("columns", []),
        "foreign_keys": config.get("foreign_keys", []),
        "scd_type": table_props.get("scd_type", ""),
        "grain": table_props.get("grain", ""),
        "grain_type": table_props.get("grain_type", ""),
        "entity_type": table_props.get("entity_type", ""),
        "milestone_columns": table_props.get("milestone_columns", []),
        "lag_columns": table_props.get("lag_columns", {}),
        "source_tables": list(source_tables),
        "lineage": lineage_map,
    }


def merge_accumulating_snapshot(
    spark: SparkSession,
    catalog: str,
    silver_schema: str,
    gold_schema: str,
    meta: dict,
):
    """
    MERGE pattern for accumulating snapshot fact tables.

    Milestones progress from NULL → populated as events occur.
    Lag/duration columns are recalculated on every update.

    ALL metadata comes from YAML:
    - meta["table_name"] → Gold table name
    - meta["pk_columns"] → MERGE condition (business process identifier)
    - meta["milestone_columns"] → Columns that fill in over time
    - meta["lag_columns"] → Duration calculations between milestones
    """
    table_name = meta["table_name"]
    pk_columns = meta["pk_columns"]
    milestone_cols = meta["milestone_columns"]
    lag_cols = meta["lag_columns"]

    print(f"\n--- Merging {table_name} (Accumulating Snapshot) ---")

    source_table = meta["source_tables"][0]
    silver_table = f"{catalog}.{silver_schema}.{source_table}"
    gold_table = f"{catalog}.{gold_schema}.{table_name}"

    silver_df = spark.table(silver_table)

    # Deduplicate on business key (keep latest event per process instance)
    business_key = meta["business_key"]
    silver_df = (
        silver_df
        .orderBy(col("processed_timestamp").desc())
        .dropDuplicates(business_key)
    )

    # Build MERGE condition from PK
    merge_condition = " AND ".join(
        f"target.{c} = source.{c}" for c in pk_columns
    )

    # Build UPDATE SET: only update milestone columns when source has a value
    # and target is still NULL (milestones only progress forward)
    update_set = {
        "record_updated_timestamp": "current_timestamp()"
    }
    for milestone in milestone_cols:
        update_set[milestone] = (
            f"CASE WHEN target.{milestone} IS NULL AND source.{milestone} IS NOT NULL "
            f"THEN source.{milestone} ELSE target.{milestone} END"
        )

    # Lag/duration columns: recalculate based on updated milestones
    # lag_cols format: {"lag_col_name": {"from": "milestone_a", "to": "milestone_b"}}
    for lag_col, endpoints in lag_cols.items():
        from_col = endpoints["from"]
        to_col = endpoints["to"]
        update_set[lag_col] = (
            f"CASE WHEN COALESCE(source.{to_col}, target.{to_col}) IS NOT NULL "
            f"AND COALESCE(source.{from_col}, target.{from_col}) IS NOT NULL "
            f"THEN DATEDIFF(COALESCE(source.{to_col}, target.{to_col}), "
            f"COALESCE(source.{from_col}, target.{from_col})) END"
        )

    # Build INSERT values (all columns from source + audit timestamps)
    insert_values = {c: f"source.{c}" for c in meta["columns"]
                     if c not in ("record_created_timestamp", "record_updated_timestamp")}
    insert_values["record_created_timestamp"] = "current_timestamp()"
    insert_values["record_updated_timestamp"] = "current_timestamp()"

    # Execute MERGE
    delta_gold = DeltaTable.forName(spark, gold_table)

    merge_builder = (
        delta_gold.alias("target")
        .merge(silver_df.alias("source"), merge_condition)
        .whenMatchedUpdate(set=update_set)
        .whenNotMatchedInsert(values=insert_values)
    )
    merge_builder.execute()

    final_count = spark.table(gold_table).count()
    print(f"  {table_name}: {final_count} rows after merge")
    return final_count
