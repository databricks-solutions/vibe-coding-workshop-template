# Silver Layer Monitoring Patterns Reference

DQ monitoring views for real-time data quality tracking across Silver layer tables.

---

## Per-Table DQ Metrics View

```python
# Databricks notebook source

"""
{Project} Silver Layer - Data Quality Monitoring Views

Delta Live Tables views for monitoring data quality metrics, expectation failures,
and overall pipeline health across the Silver layer.
"""

import dlt
from pyspark.sql.functions import (
    col, count, sum as spark_sum, avg, min as spark_min, 
    max as spark_max, current_timestamp, lit, when
)

# ============================================================================
# DATA QUALITY METRICS - PER TABLE
# ============================================================================

@dlt.table(
    name="dq_transactions_metrics",
    comment="""LLM: Real-time data quality metrics for transactions showing record counts, 
    validation pass rates, quarantine rates, and business rule compliance""",
    table_properties={
        "quality": "monitoring",
        "layer": "silver",
        "delta.enableChangeDataFeed": "true",
        "delta.enableRowTracking": "true",
        "delta.autoOptimize.autoCompact": "true",
        "delta.autoOptimize.optimizeWrite": "true"
    },
    cluster_by_auto=True  # 🔴 MANDATORY on ALL tables, including monitoring
)
def dq_transactions_metrics():
    """
    Comprehensive data quality metrics for transactions.
    
    Metrics:
    - Total records processed
    - Records in Silver vs Quarantine
    - Pass/fail rates
    - Business rule violations
    """
    silver = dlt.read("silver_transactions")
    quarantine = dlt.read("silver_transactions_quarantine")
    
    # Calculate metrics
    silver_metrics = silver.agg(
        count("*").alias("silver_record_count"),
        spark_sum(when(col("is_return"), 1).otherwise(0)).alias("return_count"),
        spark_sum(when(col("is_loyalty_transaction"), 1).otherwise(0)).alias("loyalty_transaction_count")
    )
    
    quarantine_metrics = quarantine.agg(
        count("*").alias("quarantine_record_count")
    )
    
    # Combine and calculate rates
    return (
        silver_metrics
        .crossJoin(quarantine_metrics)
        .withColumn("total_records", 
                   col("silver_record_count") + col("quarantine_record_count"))
        .withColumn("silver_pass_rate",
                   (col("silver_record_count") / col("total_records")) * 100)
        .withColumn("quarantine_rate",
                   (col("quarantine_record_count") / col("total_records")) * 100)
        .withColumn("metric_timestamp", current_timestamp())
    )
```

---

## Referential Integrity Checks

```python
# ============================================================================
# REFERENTIAL INTEGRITY CHECKS
# ============================================================================

@dlt.table(
    name="dq_referential_integrity",
    comment="""LLM: Referential integrity validation between fact and dimension tables. 
    Identifies orphaned records and missing references.""",
    table_properties={
        "quality": "monitoring",
        "layer": "silver",
        "delta.enableChangeDataFeed": "true",
        "delta.enableRowTracking": "true",
        "delta.autoOptimize.autoCompact": "true",
        "delta.autoOptimize.optimizeWrite": "true"
    },
    cluster_by_auto=True  # 🔴 MANDATORY on ALL tables, including monitoring
)
def dq_referential_integrity():
    """
    Check referential integrity between Silver fact and dimension tables.
    
    Validates:
    - Facts reference valid dimensions
    - No orphaned records
    """
    transactions = dlt.read("silver_transactions")
    stores = dlt.read("silver_store_dim")
    products = dlt.read("silver_product_dim")
    
    # Check for orphaned transactions (invalid store references)
    orphaned_stores = (
        transactions
        .join(stores.select("store_number"), ["store_number"], "left_anti")
        .agg(
            lit("transactions_to_stores").alias("check_name"),
            count("*").alias("orphaned_records")
        )
        .withColumn("status",
                   when(col("orphaned_records") == 0, "PASS")
                   .when(col("orphaned_records") < 10, "WARNING")
                   .otherwise("FAIL"))
        .withColumn("check_timestamp", current_timestamp())
    )
    
    # Check for orphaned transactions (invalid product references)
    orphaned_products = (
        transactions
        .join(products.select("upc_code"), ["upc_code"], "left_anti")
        .agg(
            lit("transactions_to_products").alias("check_name"),
            count("*").alias("orphaned_records")
        )
        .withColumn("status",
                   when(col("orphaned_records") == 0, "PASS")
                   .when(col("orphaned_records") < 10, "WARNING")
                   .otherwise("FAIL"))
        .withColumn("check_timestamp", current_timestamp())
    )
    
    return orphaned_stores.union(orphaned_products)
```

---

## 🔴 MANDATORY: Data Freshness Monitoring

Track the lag between event time (when the business event occurred) and processing time (when Silver processed it). This detects pipeline stalls and late-arriving data.

```python
# ============================================================================
# DATA FRESHNESS MONITORING
# ============================================================================

@dlt.table(
    name="dq_data_freshness",
    comment="""LLM: Data freshness metrics showing lag between event timestamps and 
    processing time. High lag indicates pipeline stalls or late-arriving data.""",
    table_properties={
        "quality": "monitoring",
        "layer": "silver",
        "delta.enableChangeDataFeed": "true",
        "delta.enableRowTracking": "true",
        "delta.autoOptimize.autoCompact": "true",
        "delta.autoOptimize.optimizeWrite": "true"
    },
    cluster_by_auto=True  # 🔴 MANDATORY on ALL tables, including monitoring
)
def dq_data_freshness():
    """
    Data freshness metrics per Silver table.
    
    Metrics:
    - latest_event_timestamp: Most recent event from source data
    - latest_processed_timestamp: Most recent Silver processing time
    - lag_minutes: Time between newest event and now (pipeline staleness)
    - oldest_unprocessed_event: Earliest event timestamp in the current batch
    
    Thresholds:
    - lag_minutes < 60: HEALTHY (within 1 hour)
    - lag_minutes 60-360: WARNING (1-6 hours behind)
    - lag_minutes > 360: CRITICAL (more than 6 hours behind)
    """
    from pyspark.sql.functions import (
        col, count, max as spark_max, min as spark_min,
        current_timestamp, lit, when, round as spark_round
    )
    
    transactions = dlt.read("silver_transactions")
    
    return (
        transactions.agg(
            lit("silver_transactions").alias("table_name"),
            spark_max("transaction_date").alias("latest_event_timestamp"),
            spark_max("processed_timestamp").alias("latest_processed_timestamp"),
            spark_min("transaction_date").alias("oldest_event_timestamp"),
            count("*").alias("total_records")
        )
        .withColumn("lag_minutes",
            spark_round(
                (col("latest_processed_timestamp").cast("long") - 
                 col("latest_event_timestamp").cast("long")) / 60, 
                2
            ))
        .withColumn("freshness_status",
            when(col("lag_minutes") < 60, "HEALTHY")
            .when(col("lag_minutes") < 360, "WARNING")
            .otherwise("CRITICAL"))
        .withColumn("check_timestamp", current_timestamp())
    )
```

### Multi-Table Freshness (Union Pattern)

For pipelines with multiple Silver tables, create a union of freshness metrics:

```python
@dlt.table(
    name="dq_all_tables_freshness",
    comment="LLM: Combined data freshness metrics for all Silver tables",
    table_properties={
        "quality": "monitoring",
        "layer": "silver",
        "delta.enableChangeDataFeed": "true",
        "delta.enableRowTracking": "true",
        "delta.autoOptimize.autoCompact": "true",
        "delta.autoOptimize.optimizeWrite": "true"
    },
    cluster_by_auto=True  # 🔴 MANDATORY on ALL tables, including monitoring
)
def dq_all_tables_freshness():
    """Unified freshness view across all Silver tables."""
    from pyspark.sql.functions import col, count, max as spark_max, current_timestamp, lit, when, round as spark_round
    
    def freshness_for_table(table_name, event_time_col):
        df = dlt.read(table_name)
        return (
            df.agg(
                lit(table_name).alias("table_name"),
                spark_max(event_time_col).alias("latest_event_timestamp"),
                spark_max("processed_timestamp").alias("latest_processed_timestamp"),
                count("*").alias("total_records")
            )
            .withColumn("lag_minutes",
                spark_round(
                    (col("latest_processed_timestamp").cast("long") - 
                     col("latest_event_timestamp").cast("long")) / 60, 2))
            .withColumn("freshness_status",
                when(col("lag_minutes") < 60, "HEALTHY")
                .when(col("lag_minutes") < 360, "WARNING")
                .otherwise("CRITICAL"))
            .withColumn("check_timestamp", current_timestamp())
        )
    
    # Add one call per Silver table (extract table names from project)
    txn = freshness_for_table("silver_transactions", "transaction_date")
    stores = freshness_for_table("silver_store_dim", "processed_timestamp")
    products = freshness_for_table("silver_product_dim", "processed_timestamp")
    
    return txn.union(stores).union(products)
```

---

## Adapting Monitoring for Your Project

### Adding New Table Metrics

For each Silver fact table with a quarantine table, create a metrics view following the pattern:

1. Read both the Silver table and its quarantine table
2. Calculate counts from each
3. CrossJoin to combine
4. Calculate rates (pass rate, quarantine rate)
5. Add metric timestamp

### Adding New Referential Integrity Checks

For each fact-to-dimension relationship:

1. Read the fact table and dimension table
2. Use `left_anti` join on the FK column
3. Count orphaned records
4. Apply status thresholds (0 = PASS, <10 = WARNING, else FAIL)
5. Union all checks into a single view

### Monitoring Template

```python
@dlt.table(
    name="dq_{entity}_metrics",
    comment="LLM: Real-time data quality metrics for {entity}",
    table_properties={
        "quality": "monitoring",
        "layer": "silver",
        "delta.enableChangeDataFeed": "true",
        "delta.enableRowTracking": "true",
        "delta.autoOptimize.autoCompact": "true",
        "delta.autoOptimize.optimizeWrite": "true"
    },
    cluster_by_auto=True  # 🔴 MANDATORY on ALL tables, including monitoring
)
def dq_{entity}_metrics():
    """DQ metrics for {entity}."""
    silver = dlt.read("silver_{entity}")
    quarantine = dlt.read("silver_{entity}_quarantine")
    
    silver_count = silver.agg(count("*").alias("silver_count"))
    quarantine_count = quarantine.agg(count("*").alias("quarantine_count"))
    
    return (
        silver_count
        .crossJoin(quarantine_count)
        .withColumn("total", col("silver_count") + col("quarantine_count"))
        .withColumn("pass_rate", (col("silver_count") / col("total")) * 100)
        .withColumn("quarantine_rate", (col("quarantine_count") / col("total")) * 100)
        .withColumn("metric_timestamp", current_timestamp())
    )
```
