"""
SCD Type 2 Merge Pattern Template
Use for dimension tables where you need to track changes over time.
"""
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, current_timestamp, lit, md5, concat_ws, when
from delta.tables import DeltaTable


def merge_dim_store(spark: SparkSession, catalog: str, silver_schema: str, gold_schema: str):
    """
    Merge dim_store from Silver to Gold (SCD Type 2).
    
    Args:
        spark: SparkSession instance
        catalog: Unity Catalog catalog name
        silver_schema: Silver layer schema name
        gold_schema: Gold layer schema name
    """
    
    silver_table = f"{catalog}.{silver_schema}.silver_store_dim"
    gold_table = f"{catalog}.{gold_schema}.dim_store"
    
    silver_df = spark.table(silver_table)
    
    updates_df = (
        silver_df
        # Generate surrogate key
        .withColumn("store_key", md5(concat_ws("||", col("store_id"), col("processed_timestamp"))))
        
        # SCD Type 2 columns
        .withColumn("effective_from", col("processed_timestamp"))
        .withColumn("effective_to", lit(None).cast("timestamp"))
        .withColumn("is_current", lit(True))
        
        # Derived columns
        .withColumn("store_status", 
                   when(col("close_date").isNotNull(), "Closed").otherwise("Active"))
        
        # Column mappings
        .withColumn("company_retail_control_number", col("company_rcn"))
        
        # Timestamps
        .withColumn("record_created_timestamp", current_timestamp())
        .withColumn("record_updated_timestamp", current_timestamp())
        
        .select(
            "store_key", "store_number", "store_name",
            "company_retail_control_number",  # Mapped column
            "effective_from", "effective_to", "is_current",
            # ... other columns
        )
    )
    
    delta_gold = DeltaTable.forName(spark, gold_table)
    
    # SCD Type 2: Only update timestamp for current records
    delta_gold.alias("target").merge(
        updates_df.alias("source"),
        "target.store_number = source.store_number AND target.is_current = true"
    ).whenMatchedUpdate(set={
        "record_updated_timestamp": "source.record_updated_timestamp"
    }).whenNotMatchedInsertAll(
    ).execute()
    
    record_count = updates_df.count()
    print(f"✓ Merged {record_count} records into dim_store")
