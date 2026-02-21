# Databricks notebook source

"""
Junk Dimension Population Pattern

Junk dimensions consolidate low-cardinality flags and indicators into a single
dimension table, replacing multiple flag columns in fact tables with a single
FK to the junk dimension. Each unique combination of flags gets one row with
a surrogate key.

YAML Properties that trigger this pattern:
  table_properties.dimension_pattern: junk
  table_properties.entity_type: dimension

Key Characteristics:
  - One row per unique combination of flag/indicator values
  - Surrogate key (MD5 hash) generated from all flag columns
  - Populated by extracting DISTINCT flag combinations from Silver source
  - SCD Type 1 (flag combinations are immutable definitions)
  - Typically small table (2^N rows for N boolean flags)
"""

import yaml
from pathlib import Path
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, current_timestamp, md5, concat_ws, lit, coalesce, when
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
        "flag_columns": table_props.get("flag_columns", []),
        "dimension_pattern": table_props.get("dimension_pattern", ""),
        "entity_type": table_props.get("entity_type", ""),
        "source_tables": list(source_tables),
        "lineage": lineage_map,
    }


def populate_junk_dimension(
    spark: SparkSession,
    catalog: str,
    silver_schema: str,
    gold_schema: str,
    meta: dict,
):
    """
    Population pattern for junk dimensions.

    Extracts DISTINCT flag combinations from Silver source and generates
    a surrogate key for each unique combination.

    ALL metadata comes from YAML:
    - meta["table_name"] → Gold table name
    - meta["flag_columns"] → The flag/indicator columns to extract
    - meta["pk_columns"] → Surrogate key column name
    - meta["source_tables"] → Silver source table(s) to scan for flag values
    """
    table_name = meta["table_name"]
    flag_cols = meta["flag_columns"]
    pk_col = meta["pk_columns"][0]  # Surrogate key column

    print(f"\n--- Populating {table_name} (Junk Dimension) ---")

    source_table = meta["source_tables"][0]
    silver_table = f"{catalog}.{silver_schema}.{source_table}"
    gold_table = f"{catalog}.{gold_schema}.{table_name}"

    # Extract DISTINCT flag combinations from Silver
    silver_df = spark.table(silver_table)
    distinct_flags = silver_df.select(flag_cols).distinct()

    # Replace NULLs with "Unknown" for consistent hashing
    for flag_col in flag_cols:
        distinct_flags = distinct_flags.withColumn(
            flag_col,
            coalesce(col(flag_col).cast("string"), lit("Unknown"))
        )

    # Generate surrogate key from flag combination
    source_df = (
        distinct_flags
        .withColumn(
            pk_col,
            md5(concat_ws("||", *[col(c) for c in flag_cols]))
        )
        .withColumn("record_created_timestamp", current_timestamp())
        .withColumn("record_updated_timestamp", current_timestamp())
    )

    # Select only Gold columns
    gold_columns = meta["columns"]
    source_df = source_df.select([col(c) for c in gold_columns])

    # MERGE: INSERT new combinations, no UPDATE (flags are immutable definitions)
    merge_condition = f"target.{pk_col} = source.{pk_col}"
    insert_values = {c: f"source.{c}" for c in gold_columns}

    delta_gold = DeltaTable.forName(spark, gold_table)

    (
        delta_gold.alias("target")
        .merge(source_df.alias("source"), merge_condition)
        .whenNotMatchedInsert(values=insert_values)
        .execute()
    )

    final_count = spark.table(gold_table).count()
    print(f"  {table_name}: {final_count} unique flag combinations")
    return final_count
