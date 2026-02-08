"""
Fact Table Aggregation Merge Pattern Template
Use for pre-aggregated fact tables from transactional Silver data.
"""
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, current_timestamp, sum as spark_sum, when, count
from delta.tables import DeltaTable


def merge_fact_sales_daily(spark: SparkSession, catalog: str, silver_schema: str, gold_schema: str):
    """
    Merge fact_sales_daily from Silver to Gold.
    
    Args:
        spark: SparkSession instance
        catalog: Unity Catalog catalog name
        silver_schema: Silver layer schema name
        gold_schema: Gold layer schema name
    """
    
    silver_table = f"{catalog}.{silver_schema}.silver_transactions"
    gold_table = f"{catalog}.{gold_schema}.fact_sales_daily"
    
    transactions = spark.table(silver_table)
    
    # Aggregate daily sales
    daily_sales = (
        transactions
        .groupBy("store_number", "upc_code", "transaction_date")
        .agg(
            spark_sum(when(col("quantity_sold") > 0, col("final_sales_price")).otherwise(0)).alias("gross_revenue"),
            spark_sum(col("final_sales_price")).alias("net_revenue"),
            spark_sum(when(col("quantity_sold") > 0, col("quantity_sold")).otherwise(0)).alias("units_sold"),
            count("*").alias("transaction_count"),  # ✅ PySpark function
            # ... more aggregations
        )
        .withColumn("record_created_timestamp", current_timestamp())
        .withColumn("record_updated_timestamp", current_timestamp())
    )
    
    delta_gold = DeltaTable.forName(spark, gold_table)
    
    delta_gold.alias("target").merge(
        daily_sales.alias("source"),
        """target.store_number = source.store_number 
           AND target.upc_code = source.upc_code 
           AND target.transaction_date = source.transaction_date"""
    ).whenMatchedUpdate(set={
        "net_revenue": "source.net_revenue",
        "units_sold": "source.units_sold",
        "transaction_count": "source.transaction_count",
        "record_updated_timestamp": "source.record_updated_timestamp"
    }).whenNotMatchedInsertAll(
    ).execute()
    
    record_count = daily_sales.count()  # ✅ Good variable name
    print(f"✓ Merged {record_count} records into fact_sales_daily")
