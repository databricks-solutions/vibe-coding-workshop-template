# Databricks notebook source

"""
Periodic Snapshot Fact Table MERGE Pattern

Periodic snapshots capture cumulative measures at regular intervals (daily,
weekly, monthly). Each snapshot period gets one row per entity. Semi-additive
measures (e.g., account balance) should NOT be summed across time — only
across other dimensions.

YAML Properties that trigger this pattern:
  table_properties.grain_type: periodic_snapshot
  table_properties.entity_type: fact
  table_properties.snapshot_period: daily|weekly|monthly

Key Characteristics:
  - One row per entity per snapshot period
  - Full replacement of each snapshot period (not incremental)
  - Semi-additive measures: additive across non-time dimensions only
  - Snapshot date is part of the composite PK
"""

import yaml
from pathlib import Path
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, current_timestamp, max as spark_max
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
        "grain": table_props.get("grain", ""),
        "grain_type": table_props.get("grain_type", ""),
        "entity_type": table_props.get("entity_type", ""),
        "snapshot_period": table_props.get("snapshot_period", "daily"),
        "source_tables": list(source_tables),
        "lineage": lineage_map,
    }


def merge_periodic_snapshot(
    spark: SparkSession,
    catalog: str,
    silver_schema: str,
    gold_schema: str,
    meta: dict,
):
    """
    MERGE pattern for periodic snapshot fact tables.

    Full replacement per snapshot period — MERGE with UPDATE on match,
    INSERT when not matched. Each entity-period combination gets exactly
    one row with the latest snapshot values.

    ALL metadata comes from YAML:
    - meta["table_name"] → Gold table name
    - meta["pk_columns"] → MERGE condition (entity + snapshot_date)
    - meta["snapshot_period"] → Snapshot granularity (daily/weekly/monthly)
    """
    table_name = meta["table_name"]
    pk_columns = meta["pk_columns"]
    gold_columns = meta["columns"]

    print(f"\n--- Merging {table_name} (Periodic Snapshot, {meta['snapshot_period']}) ---")

    source_table = meta["source_tables"][0]
    silver_table = f"{catalog}.{silver_schema}.{source_table}"
    gold_table = f"{catalog}.{gold_schema}.{table_name}"

    silver_df = spark.table(silver_table)

    # For periodic snapshots, keep only the latest record per entity-period
    silver_df = (
        silver_df
        .orderBy(col("processed_timestamp").desc())
        .dropDuplicates(pk_columns)
    )

    # Select only Gold columns + audit timestamps
    non_audit_cols = [c for c in gold_columns
                      if c not in ("record_created_timestamp", "record_updated_timestamp")]
    source_df = (
        silver_df
        .select([col(c) for c in non_audit_cols])
        .withColumn("record_updated_timestamp", current_timestamp())
    )

    # Build MERGE condition from PK (entity + snapshot_date)
    merge_condition = " AND ".join(
        f"target.{c} = source.{c}" for c in pk_columns
    )

    # Build UPDATE SET: replace all measure columns with latest snapshot
    measure_cols = [c for c in gold_columns
                    if c not in pk_columns
                    and c not in ("record_created_timestamp", "record_updated_timestamp")]
    update_set = {c: f"source.{c}" for c in measure_cols}
    update_set["record_updated_timestamp"] = "current_timestamp()"

    # Build INSERT values
    insert_values = {c: f"source.{c}" for c in gold_columns
                     if c != "record_created_timestamp"}
    insert_values["record_created_timestamp"] = "current_timestamp()"
    insert_values["record_updated_timestamp"] = "current_timestamp()"

    # Execute MERGE (full replacement of snapshot period)
    delta_gold = DeltaTable.forName(spark, gold_table)

    (
        delta_gold.alias("target")
        .merge(source_df.alias("source"), merge_condition)
        .whenMatchedUpdate(set=update_set)
        .whenNotMatchedInsert(values=insert_values)
        .execute()
    )

    final_count = spark.table(gold_table).count()
    print(f"  {table_name}: {final_count} rows after merge")
    return final_count
