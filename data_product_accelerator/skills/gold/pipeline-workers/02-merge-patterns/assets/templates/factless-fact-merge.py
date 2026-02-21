# Databricks notebook source

"""
Factless Fact Table MERGE Pattern

Factless fact tables record the occurrence of events or coverage relationships
with NO numeric measures. Row existence IS the fact. Examples: student attendance,
promotion coverage, event participation.

YAML Properties that trigger this pattern:
  table_properties.grain_type: factless
  table_properties.entity_type: fact

Key Characteristics:
  - No measure columns (only FK keys + degenerate dimensions + audit timestamps)
  - Row existence represents the event/relationship
  - Simple INSERT-only or MERGE with no aggregation
  - COUNT(*) is the only meaningful measure (computed in BI layer)
"""

import yaml
from pathlib import Path
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, current_timestamp
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
        "grain": table_props.get("grain", ""),
        "grain_type": table_props.get("grain_type", ""),
        "entity_type": table_props.get("entity_type", ""),
        "source_tables": list(source_tables),
        "lineage": lineage_map,
    }


def merge_factless_fact(
    spark: SparkSession,
    catalog: str,
    silver_schema: str,
    gold_schema: str,
    meta: dict,
):
    """
    MERGE pattern for factless fact tables.

    No aggregation needed — row existence IS the fact.
    MERGE prevents duplicates; INSERT only when not matched.

    ALL metadata comes from YAML:
    - meta["table_name"] → Gold table name
    - meta["pk_columns"] → MERGE condition (composite key of all FKs)
    - meta["columns"] → Only FK columns + degenerate dims + audit timestamps
    """
    table_name = meta["table_name"]
    pk_columns = meta["pk_columns"]
    gold_columns = meta["columns"]

    print(f"\n--- Merging {table_name} (Factless Fact) ---")

    source_table = meta["source_tables"][0]
    silver_table = f"{catalog}.{silver_schema}.{source_table}"
    gold_table = f"{catalog}.{gold_schema}.{table_name}"

    silver_df = spark.table(silver_table)

    # Deduplicate on composite PK (all FK columns form the grain)
    silver_df = (
        silver_df
        .orderBy(col("processed_timestamp").desc())
        .dropDuplicates(pk_columns)
    )

    # Select only Gold columns (FKs + degenerate dims + audit)
    # No aggregation — each row is a discrete event/relationship
    non_audit_cols = [c for c in gold_columns
                      if c not in ("record_created_timestamp", "record_updated_timestamp")]
    source_df = (
        silver_df
        .select([col(c) for c in non_audit_cols])
        .withColumn("record_created_timestamp", current_timestamp())
        .withColumn("record_updated_timestamp", current_timestamp())
    )

    # Build MERGE condition from composite PK
    merge_condition = " AND ".join(
        f"target.{c} = source.{c}" for c in pk_columns
    )

    # MERGE: INSERT only when not matched (no UPDATE for factless facts)
    delta_gold = DeltaTable.forName(spark, gold_table)
    insert_values = {c: f"source.{c}" for c in gold_columns}

    (
        delta_gold.alias("target")
        .merge(source_df.alias("source"), merge_condition)
        .whenNotMatchedInsert(values=insert_values)
        .execute()
    )

    final_count = spark.table(gold_table).count()
    print(f"  {table_name}: {final_count} rows after merge")
    return final_count
