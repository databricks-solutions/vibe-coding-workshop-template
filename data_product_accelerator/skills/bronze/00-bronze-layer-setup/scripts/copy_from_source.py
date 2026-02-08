# Databricks notebook source

"""
{Project Name} Bronze Layer - Copy from Existing Source

Copies data from an existing source to Bronze layer tables.

Supported Sources:
- Existing Unity Catalog tables
- External databases (via JDBC)
- CSV/Parquet files
- Another Databricks workspace

Usage:
  databricks bundle run bronze_copy_job -t dev

Template Instructions:
  1. Replace {project} with your project name
  2. Update table_mappings with your source -> target table pairs
  3. Update get_parameters() with any additional source-specific params
"""

from pyspark.sql import SparkSession


def get_parameters():
    """Get job parameters from dbutils widgets."""
    catalog = dbutils.widgets.get("catalog")
    bronze_schema = dbutils.widgets.get("bronze_schema")
    source_catalog = dbutils.widgets.get("source_catalog")
    source_schema = dbutils.widgets.get("source_schema")

    print(f"Target: {catalog}.{bronze_schema}")
    print(f"Source: {source_catalog}.{source_schema}")

    return catalog, bronze_schema, source_catalog, source_schema


def copy_table(spark, source_catalog, source_schema, source_table,
               target_catalog, target_schema, target_table):
    """
    Copy data from source table to target Bronze table.

    Preserves schema and data, adds ingestion metadata columns
    if not already present in the source.
    """
    print(f"\nCopying {source_catalog}.{source_schema}.{source_table}")
    print(f"     -> {target_catalog}.{target_schema}.{target_table}")

    # Read source
    source_df = spark.table(f"{source_catalog}.{source_schema}.{source_table}")

    # Add ingestion metadata if not exists
    from pyspark.sql.functions import current_timestamp, lit

    if "ingestion_timestamp" not in source_df.columns:
        source_df = source_df.withColumn("ingestion_timestamp", current_timestamp())

    if "source_file" not in source_df.columns:
        source_df = source_df.withColumn(
            "source_file",
            lit(f"copied_from_{source_catalog}.{source_schema}.{source_table}")
        )

    # Write to target
    target_full_name = f"{target_catalog}.{target_schema}.{target_table}"
    source_df.write.mode("overwrite").saveAsTable(target_full_name)

    # Get count
    count = spark.table(target_full_name).count()
    print(f"Copied {count:,} records to {target_full_name}")

    # Enable Change Data Feed
    spark.sql(f"""
        ALTER TABLE {target_full_name}
        SET TBLPROPERTIES (
            'delta.enableChangeDataFeed' = 'true',
            'delta.autoOptimize.optimizeWrite' = 'true',
            'delta.autoOptimize.autoCompact' = 'true',
            'layer' = 'bronze',
            'source_system' = 'copied_from_{source_catalog}.{source_schema}',
            'data_purpose' = 'testing_demo',
            'is_production' = 'false'
        )
    """)
    print(f"Applied Bronze TBLPROPERTIES to {target_full_name}")


def main():
    """Copy all tables from source to Bronze."""
    from pyspark.sql import SparkSession

    # Get parameters
    catalog, bronze_schema, source_catalog, source_schema = get_parameters()

    spark = SparkSession.builder.appName("Bronze Copy from Source").getOrCreate()

    print("=" * 80)
    print("BRONZE LAYER - COPY FROM SOURCE")
    print("=" * 80)

    try:
        # Define table mappings: (source_table, target_table)
        # REPLACE: Update these mappings for your project
        table_mappings = [
            ("source_stores", "bronze_store_dim"),
            ("source_products", "bronze_product_dim"),
            ("source_transactions", "bronze_transactions"),
            # Add more mappings as needed
        ]

        for source_table, target_table in table_mappings:
            try:
                copy_table(spark, source_catalog, source_schema, source_table,
                           catalog, bronze_schema, target_table)
            except Exception as e:
                print(f"Warning: Could not copy {source_table}: {str(e)}")

        print("\n" + "=" * 80)
        print("Copy completed!")
        print("=" * 80)

    except Exception as e:
        print(f"\nError: {str(e)}")
        raise
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
