# Databricks notebook source

"""
{Project} Gold Layer - MERGE Operations (YAML-Driven)

Performs Delta MERGE operations to update Gold layer tables from Silver.
ALL metadata (table names, column names, PKs, business keys, grain, SCD type)
is extracted from Gold YAML files. Only aggregation expressions and derived
column formulas are hand-coded business logic.

Handles:
- YAML-driven metadata extraction (table names, columns, PKs, mappings)
- SCD Type 2 dimension updates with deduplication
- Fact table aggregation with grain validation
- Schema validation before every MERGE
- Column mapping from YAML lineage or COLUMN_LINEAGE.csv

Usage:
  databricks bundle run gold_merge_job -t dev
"""

import yaml
import csv
from pathlib import Path
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import (
    col,
    current_timestamp,
    md5,
    concat_ws,
    when,
    sum as spark_sum,
    count,
    avg,
    lit,
    coalesce,
)
from delta.tables import DeltaTable


# =============================================================================
# YAML EXTRACTION HELPERS (extract, don't generate)
# =============================================================================

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

    # Extract source Silver table from lineage metadata
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
        "entity_type": table_props.get("entity_type", ""),
        "source_tables": list(source_tables),
        "lineage": lineage_map,
    }


def load_column_mappings_from_yaml(meta: dict) -> dict:
    """Extract Silver→Gold column renames from YAML lineage.

    Returns: {gold_column_name: silver_source_column_name} for renames only
    """
    mappings = {}
    for gold_col, lineage in meta.get("lineage", {}).items():
        source_col = lineage.get("source_column", "")
        if source_col and source_col != gold_col:
            mappings[gold_col] = source_col
    return mappings


def build_merge_condition(pk_columns: list, include_is_current: bool = False) -> str:
    """Build MERGE ON clause from PK columns extracted from YAML."""
    conditions = [f"target.{c} = source.{c}" for c in pk_columns]
    if include_is_current:
        conditions.append("target.is_current = true")
    return " AND ".join(conditions)


def build_inventory(yaml_base: Path, domain: str = "all") -> dict:
    """Build complete table inventory from YAML files."""
    inventory = {}
    if domain.lower() == "all":
        domains = [d.name for d in yaml_base.iterdir() if d.is_dir()]
    else:
        domains = [domain]

    for d in domains:
        domain_path = yaml_base / d
        if not domain_path.exists():
            continue
        for yaml_file in sorted(domain_path.glob("*.yaml")):
            meta = load_table_metadata(yaml_file)
            inventory[meta["table_name"]] = meta

    return inventory


# =============================================================================
# MERGE FUNCTIONS (metadata from YAML, business logic hand-coded)
# =============================================================================

def merge_dimension_scd2(
    spark: SparkSession,
    catalog: str,
    silver_schema: str,
    gold_schema: str,
    meta: dict,
    mappings: dict,
):
    """
    Merge a SCD Type 2 dimension from Silver to Gold.

    FROM YAML: table_name, business_key, columns, source_tables
    HAND-CODED: surrogate key formula, derived columns
    """
    table_name = meta["table_name"]              # ← FROM YAML
    business_key = meta["business_key"]           # ← FROM YAML
    gold_columns = meta["columns"]                # ← FROM YAML
    source_table = meta["source_tables"][0]       # ← FROM YAML lineage

    print(f"\n--- Merging {table_name} (SCD Type 2) ---")

    silver_table = f"{catalog}.{silver_schema}.{source_table}"
    gold_table = f"{catalog}.{gold_schema}.{table_name}"

    # Step 1: Read and deduplicate Silver source
    silver_raw = spark.table(silver_table)
    original_count = silver_raw.count()

    silver_df = (
        silver_raw
        .orderBy(col("processed_timestamp").desc())
        .dropDuplicates(business_key)   # ← FROM YAML business_key
    )

    dedupe_count = silver_df.count()
    print(
        f"  Deduplicated: {original_count} → {dedupe_count} records "
        f"({original_count - dedupe_count} duplicates removed)"
    )

    # Step 2: Apply column mappings FROM YAML lineage
    df = silver_df
    for gold_col, silver_col in mappings.items():
        df = df.withColumn(gold_col, col(silver_col))

    # Step 3: Add SCD Type 2 columns + derived columns
    # Surrogate key from business key columns (FROM YAML)
    df = (
        df
        .withColumn(
            meta["pk_columns"][0],  # surrogate key column name FROM YAML
            md5(concat_ws("||", *[col(c) for c in business_key],
                          col("processed_timestamp"))),
        )
        .withColumn("effective_from", col("processed_timestamp"))
        .withColumn("effective_to", lit(None).cast("timestamp"))
        .withColumn("is_current", lit(True))
        # TODO: Add table-specific derived columns here (business logic)
        .withColumn("record_created_timestamp", current_timestamp())
        .withColumn("record_updated_timestamp", current_timestamp())
    )

    # Step 4: Select ONLY columns in Gold DDL — list FROM YAML
    updates_df = df.select(gold_columns)

    # Step 5: Build MERGE condition FROM YAML
    merge_cond = build_merge_condition(
        business_key, include_is_current=True
    )

    # Step 6: MERGE into Gold
    delta_gold = DeltaTable.forName(spark, gold_table)
    (
        delta_gold.alias("target")
        .merge(updates_df.alias("source"), merge_cond)
        .whenMatchedUpdate(
            set={"record_updated_timestamp": "source.record_updated_timestamp"}
        )
        .whenNotMatchedInsertAll()
        .execute()
    )

    print(f"✓ Merged {updates_df.count()} records into {table_name}")


def merge_fact_aggregated(
    spark: SparkSession,
    catalog: str,
    silver_schema: str,
    gold_schema: str,
    meta: dict,
    agg_expressions: list,
    derived_fns: list = None,
):
    """
    Merge an aggregated fact table from Silver to Gold.

    FROM YAML: table_name, pk_columns (grain), columns, source_tables
    HAND-CODED: agg_expressions (business logic), derived_fns
    """
    table_name = meta["table_name"]              # ← FROM YAML
    grain_columns = meta["pk_columns"]            # ← FROM YAML (composite PK = grain)
    gold_columns = meta["columns"]                # ← FROM YAML
    source_table = meta["source_tables"][0]       # ← FROM YAML lineage

    print(f"\n--- Merging {table_name} (Aggregated Fact) ---")

    silver_table = f"{catalog}.{silver_schema}.{source_table}"
    gold_table = f"{catalog}.{gold_schema}.{table_name}"

    transactions = spark.table(silver_table)

    # Step 1: Aggregate to grain FROM YAML pk_columns
    agg_df = transactions.groupBy(*grain_columns).agg(*agg_expressions)

    # Step 2: Add derived metrics (business logic — hand-coded)
    if derived_fns:
        for fn in derived_fns:
            agg_df = fn(agg_df)

    agg_df = (
        agg_df
        .withColumn("record_created_timestamp", current_timestamp())
        .withColumn("record_updated_timestamp", current_timestamp())
    )

    # Step 3: Validate grain — columns FROM YAML
    distinct_grain = agg_df.select(*grain_columns).distinct().count()
    total_rows = agg_df.count()

    if distinct_grain != total_rows:
        raise ValueError(
            f"Grain validation failed for {table_name}!\n"
            f"  Grain columns (from YAML PK): {grain_columns}\n"
            f"  Distinct combinations: {distinct_grain}\n"
            f"  Total rows: {total_rows}"
        )

    print(f"  ✓ Grain validation passed: {total_rows} unique combinations")

    # Step 4: Select ONLY columns in Gold DDL — list FROM YAML
    available_cols = set(agg_df.columns)
    select_cols = [c for c in gold_columns if c in available_cols]
    result_df = agg_df.select(select_cols)

    # Step 5: Build MERGE condition and update set FROM YAML
    merge_cond = build_merge_condition(grain_columns)
    pk_set = set(grain_columns)
    audit_cols = {"record_created_timestamp"}
    update_cols = {
        c: f"source.{c}" for c in select_cols
        if c not in pk_set and c not in audit_cols
    }

    # Step 6: MERGE into Gold
    delta_gold = DeltaTable.forName(spark, gold_table)
    (
        delta_gold.alias("target")
        .merge(result_df.alias("source"), merge_cond)
        .whenMatchedUpdate(set=update_cols)
        .whenNotMatchedInsertAll()
        .execute()
    )

    print(f"✓ Merged {total_rows} records into {table_name}")


# =============================================================================
# PER-TABLE BUSINESS LOGIC (hand-coded aggregation expressions)
# =============================================================================

def get_agg_expressions_for(table_name: str) -> list:
    """Return aggregation expressions for a specific fact table.

    This is the ONLY place where business logic is hand-coded.
    Everything else (table names, columns, grain, PKs) comes from YAML.
    """
    # TODO: Add per-table aggregation expressions
    # Example for fact_sales_daily:
    # if table_name == "fact_sales_daily":
    #     return [
    #         spark_sum(when(col("quantity_sold") > 0,
    #                       col("final_sales_price")).otherwise(0)).alias("gross_revenue"),
    #         spark_sum(col("final_sales_price")).alias("net_revenue"),
    #         count("*").alias("transaction_count"),
    #     ]
    raise NotImplementedError(
        f"No aggregation expressions defined for {table_name}. "
        f"Add them to get_agg_expressions_for() — this is per-table business logic."
    )


def get_derived_fns_for(table_name: str) -> list:
    """Return derived column functions for a specific fact table.

    This is per-table business logic. Everything else comes from YAML.
    """
    # TODO: Add per-table derived column functions
    return []


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def get_parameters():
    """Get job parameters from dbutils widgets."""
    catalog = dbutils.widgets.get("catalog")
    silver_schema = dbutils.widgets.get("silver_schema")
    gold_schema = dbutils.widgets.get("gold_schema")

    print(f"Catalog: {catalog}")
    print(f"Silver Schema: {silver_schema}")
    print(f"Gold Schema: {gold_schema}")

    return catalog, silver_schema, gold_schema


def main():
    """Main entry point for Gold layer MERGE operations.

    Uses YAML inventory to determine:
    - Which tables exist (from YAML files)
    - Table order (dimensions FIRST, then facts)
    - Merge pattern (SCD type, grain type from YAML)
    - Column lists, PKs, business keys (all from YAML)
    """
    catalog, silver_schema, gold_schema = get_parameters()

    spark = SparkSession.builder.appName("Gold Layer MERGE").getOrCreate()

    print("=" * 80)
    print("GOLD LAYER MERGE OPERATIONS (YAML-Driven)")
    print(f"Source: {catalog}.{silver_schema}")
    print(f"Target: {catalog}.{gold_schema}")
    print("=" * 80)

    try:
        # Step 1: Build inventory FROM YAML (single source of truth)
        yaml_base = find_yaml_base()
        inventory = build_inventory(yaml_base)
        print(f"✓ Loaded {len(inventory)} table definitions from YAML")

        # Step 2: Separate dimensions and facts (FROM YAML entity_type)
        dimensions = {
            k: v for k, v in inventory.items()
            if v["entity_type"] == "dimension"
        }
        facts = {
            k: v for k, v in inventory.items()
            if v["entity_type"] == "fact"
        }

        print(f"  Dimensions: {list(dimensions.keys())}")
        print(f"  Facts: {list(facts.keys())}")

        # Step 3: Merge dimensions FIRST (facts may reference dimensions)
        for table_name, meta in dimensions.items():
            mappings = load_column_mappings_from_yaml(meta)
            if meta["scd_type"] == "scd2":
                merge_dimension_scd2(
                    spark, catalog, silver_schema, gold_schema, meta, mappings
                )
            # TODO: Add SCD Type 1 handler

        # Step 4: Merge facts AFTER dimensions
        for table_name, meta in facts.items():
            agg_exprs = get_agg_expressions_for(table_name)
            derived_fns = get_derived_fns_for(table_name)
            merge_fact_aggregated(
                spark, catalog, silver_schema, gold_schema,
                meta, agg_exprs, derived_fns
            )

        print("\n" + "=" * 80)
        print("✓ Gold layer MERGE completed successfully!")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Error during Gold layer MERGE: {str(e)}")
        raise

    finally:
        spark.stop()


if __name__ == "__main__":
    main()
