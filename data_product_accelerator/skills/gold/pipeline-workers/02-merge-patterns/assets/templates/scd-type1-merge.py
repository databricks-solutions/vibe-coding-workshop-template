"""
SCD Type 1 Merge Pattern Template
Use for dimension tables where history doesn't matter - overwrites existing records.
"""
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, current_timestamp
from delta.tables import DeltaTable


def merge_dim_product(spark: SparkSession, catalog: str, silver_schema: str, gold_schema: str):
    """
    Merge dim_product from Silver to Gold (SCD Type 1).
    
    Args:
        spark: SparkSession instance
        catalog: Unity Catalog catalog name
        silver_schema: Silver layer schema name
        gold_schema: Gold layer schema name
    """
    
    silver_table = f"{catalog}.{silver_schema}.silver_product_dim"
    gold_table = f"{catalog}.{gold_schema}.dim_product"
    
    silver_df = spark.table(silver_table)
    
    # Prepare updates with column mappings
    updates_df = (
        silver_df
        .withColumn("product_key", col("upc_code"))  # Business key
        .withColumn("record_updated_timestamp", current_timestamp())
        .select(
            "product_key", "upc_code", "product_description",
            # ... other columns
            "record_updated_timestamp"
        )
    )
    
    delta_gold = DeltaTable.forName(spark, gold_table)
    
    # SCD Type 1: Update all fields when matched
    delta_gold.alias("target").merge(
        updates_df.alias("source"),
        "target.product_key = source.product_key"
    ).whenMatchedUpdateAll(
    ).whenNotMatchedInsertAll(
    ).execute()
    
    record_count = updates_df.count()  # ✅ Good variable name
    print(f"✓ Merged {record_count} records into dim_product")
