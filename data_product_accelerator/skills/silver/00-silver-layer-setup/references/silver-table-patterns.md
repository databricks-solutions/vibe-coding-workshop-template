# Silver Table Patterns Reference

Complete DLT table templates for Silver layer creation. These patterns supplement the mandatory skills - ensure you have read `databricks-table-properties` and `dlt-expectations-patterns` before using.

---

## get_bronze_table() Helper Function

**Every DLT notebook MUST include this helper at the top:**

```python
def get_bronze_table(table_name):
    """
    Helper function to get fully qualified Bronze table name from DLT configuration.
    
    Supports DLT Direct Publishing Mode - uses catalog/schema from pipeline config.
    
    Args:
        table_name: Name of the Bronze table (e.g., "bronze_transactions")
    
    Returns:
        Fully qualified table name: "{catalog}.{schema}.{table_name}"
    """
    from pyspark.sql import SparkSession
    spark = SparkSession.getActiveSession()
    catalog = spark.conf.get("catalog")
    bronze_schema = spark.conf.get("bronze_schema")
    return f"{catalog}.{bronze_schema}.{table_name}"
```

**Why This Helper?**
- DLT Direct Publishing Mode requires fully qualified table names
- No more `LIVE.` prefix (deprecated pattern)
- Configuration comes from DLT pipeline YAML
- Single source of truth for table references

**Usage:**
```python
dlt.read_stream(get_bronze_table("bronze_transactions"))
# Expands to: catalog.bronze_schema.bronze_transactions
```

---

## Standard Silver Table Template

**Key Principle: Clone Bronze schema + Load DQ rules from Delta table + Add derived fields**

```python
# Databricks notebook source

"""
{Project} Silver Layer - {Entity Type} Tables with DLT

Delta Live Tables pipeline for Silver {entity_type} tables with:
- Data quality expectations loaded from Delta table (dq_rules)
- Automatic liquid clustering (cluster_by_auto=True)
- Advanced Delta Lake features (row tracking, deletion vectors)
- Schema cloning from Bronze with minimal transformation

Reference: https://docs.databricks.com/aws/en/ldp/expectation-patterns
"""

import dlt
from pyspark.sql.functions import (
    col, current_timestamp, sha2, concat_ws,
    coalesce, when, lit, upper, trim
)

# Import DQ rules loader (pure Python module, not notebook)
from dq_rules_loader import (
    get_critical_rules_for_table,
    get_warning_rules_for_table,
    get_quarantine_condition
)

# Helper for DLT Direct Publishing Mode
def get_bronze_table(table_name):
    """Get fully qualified Bronze table name from DLT configuration."""
    from pyspark.sql import SparkSession
    spark = SparkSession.getActiveSession()
    catalog = spark.conf.get("catalog")
    bronze_schema = spark.conf.get("bronze_schema")
    return f"{catalog}.{bronze_schema}.{table_name}"


# ============================================================================
# SILVER {ENTITY} TABLE
# ============================================================================

@dlt.table(
    name="silver_{entity}",
    comment="""LLM: Silver layer {entity_description} with data quality rules loaded from 
    Delta table, streaming ingestion, and business rule validation""",
    table_properties={
        # ⚠️ MUST read databricks-table-properties/SKILL.md for complete Silver properties
        "quality": "silver",
        "delta.enableChangeDataFeed": "true",
        "delta.enableRowTracking": "true",
        "delta.enableDeletionVectors": "true",
        "delta.autoOptimize.autoCompact": "true",
        "delta.autoOptimize.optimizeWrite": "true",
        "delta.tuneFileSizesForRewrites": "true",
        "application": "{project_name}",
        "project": "{project_demo}",
        "layer": "silver",
        "source_table": "bronze_{entity}",
        "domain": "{domain}",
        "entity_type": "{type}",            # dimension, fact
        "contains_pii": "{true|false}",
        "data_classification": "{confidential|internal}",
        "consumer": "{team}",
        "developer": "edp",
        "support": "edp",
        "business_owner": "{Business Team}",
        "technical_owner": "Data Engineering",
        "business_owner_email": "{email}@company.com",
        "technical_owner_email": "data-engineering@company.com"
    },
    cluster_by_auto=True  # ALWAYS AUTO, never specify columns manually
)
@dlt.expect_all_or_drop(get_critical_rules_for_table("silver_{entity}"))
@dlt.expect_all(get_warning_rules_for_table("silver_{entity}"))
def silver_{entity}():
    """
    Silver {entity} with data quality rules loaded from Unity Catalog Delta table.
    
    Schema Strategy: Clone Bronze schema with minimal transformation
    - Same column names as Bronze
    - Same data types
    - Add derived flags (is_*, has_*)
    - Add business keys (SHA256 hashes)
    - Add processed_timestamp
    
    Data Quality Rules (loaded from {catalog}.{silver_schema}.dq_rules):
    
    CRITICAL (Record DROPPED/QUARANTINED, pipeline continues):
    - Rules loaded from Delta table WHERE severity = 'critical'
    
    WARNING (Logged but record passes through):
    - Rules loaded from Delta table WHERE severity = 'warning'
    """
    return (
        dlt.read_stream(get_bronze_table("bronze_{entity}"))
        
        # ========================================
        # MINIMAL TRANSFORMATIONS (Clone Bronze schema)
        # ========================================
        
        # Add business key (SHA256 hash of natural key)
        .withColumn("{entity}_business_key",
                   sha2(concat_ws("||", col("natural_key1"), col("natural_key2")), 256))
        
        # Add derived boolean flags (simple business indicators)
        .withColumn("is_{flag_name}", 
                   when(col("field") > threshold, True).otherwise(False))
        
        # Add processed timestamp
        .withColumn("processed_timestamp", current_timestamp())
        
        # ========================================
        # AVOID IN SILVER (Save for Gold):
        # - Aggregations
        # - Complex calculations
        # - Joining across tables
        # - Major schema restructuring
        # ========================================
    )
```

---

## Dimension Table Example

```python
@dlt.table(
    name="silver_store_dim",
    comment="LLM: Silver layer store dimension with validated location data and deduplication. Rules loaded dynamically from dq_rules Delta table.",
    table_properties={
        "quality": "silver",
        "delta.enableChangeDataFeed": "true",
        "delta.enableRowTracking": "true",
        "delta.enableDeletionVectors": "true",
        "delta.autoOptimize.autoCompact": "true",
        "delta.autoOptimize.optimizeWrite": "true",
        "delta.tuneFileSizesForRewrites": "true",
        "layer": "silver",
        "source_table": "bronze_store_dim",
        "domain": "retail",
        "entity_type": "dimension",
        "contains_pii": "true",
        "data_classification": "confidential"
    },
    cluster_by_auto=True
)
@dlt.expect_all_or_drop(get_critical_rules_for_table("silver_store_dim"))
@dlt.expect_all(get_warning_rules_for_table("silver_store_dim"))
def silver_store_dim():
    """
    Silver store dimension - clones Bronze schema with validation.
    
    Transformations:
    - Standardize state code (UPPER, TRIM)
    - Add business key hash
    - Add processed timestamp
    - NO aggregation
    - NO complex calculations
    
    DQ Rules (from dq_rules table):
    - CRITICAL: store_number NOT NULL, store_name NOT NULL
    - WARNING: state format (2 letters), valid coordinates
    """
    return (
        dlt.read_stream(get_bronze_table("bronze_store_dim"))
        .withColumn("state", upper(trim(col("state"))))  # Minimal standardization
        .withColumn("store_business_key", 
                   sha2(concat_ws("||", col("store_number"), col("store_name")), 256))
        .withColumn("processed_timestamp", current_timestamp())
    )
```

---

## Fact Table Example with Quarantine

```python
@dlt.table(
    name="silver_transactions",
    comment="""LLM: Silver layer streaming fact table for transactions with comprehensive 
    data quality rules loaded from Delta table and quarantine pattern""",
    table_properties={
        "quality": "silver",
        "delta.enableChangeDataFeed": "true",
        "delta.enableRowTracking": "true",
        "delta.enableDeletionVectors": "true",
        "delta.autoOptimize.autoCompact": "true",
        "delta.autoOptimize.optimizeWrite": "true",
        "delta.tuneFileSizesForRewrites": "true",
        "layer": "silver",
        "source_table": "bronze_transactions",
        "domain": "sales",
        "entity_type": "fact",
        "contains_pii": "true",
        "data_classification": "confidential"
    },
    cluster_by_auto=True
)
@dlt.expect_all_or_drop(get_critical_rules_for_table("silver_transactions"))
@dlt.expect_all(get_warning_rules_for_table("silver_transactions"))
def silver_transactions():
    """
    Silver transactions - clones Bronze with simple derived fields.
    
    Transformations:
    - Calculate total_discount (sum of discount fields)
    - Add is_return flag (quantity < 0)
    - Add business key hash
    - NO daily aggregation (that's Gold)
    - NO dimension lookups (that's Gold)
    
    DQ Rules (from dq_rules table):
    - CRITICAL: transaction_id, store_number, upc_code, date (all NOT NULL)
    - CRITICAL: quantity != 0, price > 0
    - WARNING: reasonable quantity/price ranges, recent transactions
    """
    return (
        dlt.read_stream(get_bronze_table("bronze_transactions"))
        
        # Simple derived fields (single-record calculations only)
        .withColumn("total_discount_amount",
                   coalesce(col("multi_unit_discount"), lit(0)) +
                   coalesce(col("coupon_discount"), lit(0)) +
                   coalesce(col("loyalty_discount"), lit(0)))
        
        # Simple boolean flags
        .withColumn("is_return", when(col("quantity_sold") < 0, True).otherwise(False))
        .withColumn("is_loyalty_transaction", 
                   when(col("loyalty_id").isNotNull(), True).otherwise(False))
        
        # Standard audit fields
        .withColumn("processed_timestamp", current_timestamp())
        .withColumn("transaction_business_key",
                   sha2(concat_ws("||", col("transaction_id")), 256))
    )


# ============================================================================
# QUARANTINE TABLE (Captures records that fail CRITICAL rules)
# ============================================================================

@dlt.table(
    name="silver_transactions_quarantine",
    comment="""LLM: Quarantine table for transactions that failed CRITICAL data quality checks. 
    Records here require manual review and remediation before promotion to Silver.
    Filter condition dynamically generated from dq_rules Delta table.""",
    table_properties={
        "quality": "quarantine",
        "delta.enableChangeDataFeed": "true",
        "delta.enableRowTracking": "true",
        "delta.enableDeletionVectors": "true",
        "delta.autoOptimize.autoCompact": "true",
        "delta.autoOptimize.optimizeWrite": "true",
        "delta.tuneFileSizesForRewrites": "true",
        "layer": "silver",
        "source_table": "bronze_transactions",
        "domain": "sales",
        "entity_type": "quarantine",
        "contains_pii": "true",
        "data_classification": "confidential"
    },
    cluster_by_auto=True
)
def silver_transactions_quarantine():
    """
    Quarantine table for records that fail CRITICAL validations.
    
    Filter condition is automatically generated from dq_rules table as the
    inverse of all critical rules for silver_transactions.
    
    Pipeline behavior:
    - Pipeline continues (no failure)
    - Invalid records captured here
    - Valid records flow to silver_transactions
    - WARNING violations not captured (logged only)
    """
    return (
        dlt.read_stream(get_bronze_table("bronze_transactions"))
        # Use centralized quarantine condition (loaded from dq_rules table)
        .filter(get_quarantine_condition("silver_transactions"))
        .withColumn("quarantine_reason",
            when(col("transaction_id").isNull(), "CRITICAL: Missing transaction ID (primary key)")
            .when(col("store_number").isNull(), "CRITICAL: Missing store number (FK)")
            .when(col("upc_code").isNull(), "CRITICAL: Missing UPC code (FK)")
            .when(col("transaction_date").isNull(), "CRITICAL: Missing transaction date")
            .when(col("quantity_sold") == 0, "CRITICAL: Quantity is zero")
            .when(col("final_sales_price") <= 0, "CRITICAL: Invalid final sales price")
            .otherwise("CRITICAL: Multiple validation failures"))
        .withColumn("quarantine_timestamp", current_timestamp())
    )
```

---

## Derived Field Patterns

### Business Keys (SHA256 Hash)

```python
# Single-column natural key
.withColumn("transaction_business_key",
           sha2(concat_ws("||", col("transaction_id")), 256))

# Multi-column natural key
.withColumn("store_business_key",
           sha2(concat_ws("||", col("store_number"), col("store_name")), 256))
```

### Boolean Flags (Simple Business Indicators)

```python
# Return detection
.withColumn("is_return", when(col("quantity_sold") < 0, True).otherwise(False))

# Loyalty detection
.withColumn("is_loyalty_transaction", 
           when(col("loyalty_id").isNotNull(), True).otherwise(False))

# Out-of-stock indicator
.withColumn("is_out_of_stock",
           when(col("on_hand_quantity") <= 0, True).otherwise(False))
```

### Simple Calculations (Single-Record Only)

```python
# Sum of multiple discount fields
.withColumn("total_discount_amount",
           coalesce(col("multi_unit_discount"), lit(0)) +
           coalesce(col("coupon_discount"), lit(0)) +
           coalesce(col("loyalty_discount"), lit(0)))

# Standardize text fields
.withColumn("state", upper(trim(col("state"))))
.withColumn("product_category", trim(col("product_category")))
```

### Audit Fields (Always Add)

```python
# Processed timestamp
.withColumn("processed_timestamp", current_timestamp())
```

---

## 🔴 MANDATORY: Streaming Deduplication Pattern

**Bronze tables may contain duplicate records** due to incremental DLT streaming, CDC patterns, at-least-once delivery from Kafka/Event Hub, or multiple batch loads. ALWAYS deduplicate in Silver.

### Pattern: Deduplicate by Natural Key (Keep Latest)

```python
from pyspark.sql.window import Window

@dlt.table(
    name="silver_transactions",
    comment="Silver transactions with deduplication by transaction_id",
    table_properties={...},  # Standard Silver properties
    cluster_by_auto=True
)
@dlt.expect_all_or_drop(get_critical_rules_for_table("silver_transactions"))
@dlt.expect_all(get_warning_rules_for_table("silver_transactions"))
def silver_transactions():
    """Deduplicate by natural key, keeping the latest record by event timestamp."""
    raw = dlt.read_stream(get_bronze_table("bronze_transactions"))
    
    # ✅ CORRECT: dropDuplicates for streaming deduplication
    return (
        raw
        .dropDuplicates(["transaction_id"])
        .withColumn("processed_timestamp", current_timestamp())
    )
```

### When Deduplication Is Required

| Source Pattern | Dedup Required? | Key(s) to Deduplicate On |
|---------------|-----------------|--------------------------|
| At-least-once delivery (Kafka, Event Hub) | **Yes** | Message/event ID |
| Auto Loader with retries | **Yes** | Natural business key |
| CDC with multiple updates | **Yes** | Entity key (keep latest by sequence) |
| Idempotent batch loads | **Yes** | Natural business key |
| Guaranteed-once delivery | Optional (defensive) | Natural business key |

**Default stance:** ALWAYS deduplicate. The cost is minimal; the risk of duplicates reaching Gold is high.

```python
# ❌ WRONG: No deduplication
def silver_events():
    return dlt.read_stream(get_bronze_table("bronze_events"))

# ✅ CORRECT: Always deduplicate
def silver_events():
    return (
        dlt.read_stream(get_bronze_table("bronze_events"))
        .dropDuplicates(["event_id"])
    )
```

---

## 🔴 MANDATORY: Preserve Ingestion Metadata from Bronze

Bronze tables typically include `_ingested_at` and `_metadata` columns from Auto Loader. **Preserve these in Silver for lineage and debugging.**

```python
@dlt.table(name="silver_orders", cluster_by_auto=True, ...)
def silver_orders():
    return (
        dlt.read_stream(get_bronze_table("bronze_orders"))
        .dropDuplicates(["order_id"])
        
        # ✅ Preserve Bronze ingestion metadata
        # _ingested_at: When record entered Bronze (processing time)
        # _source_file: Which file the record came from (debugging)
        
        # Add Silver processing timestamp (distinct from Bronze ingestion)
        .withColumn("processed_timestamp", current_timestamp())
        
        # Do NOT drop _ingested_at or _metadata columns
    )
```

**Key distinction:**
- `_ingested_at` = When the record entered Bronze (from Auto Loader). **Preserve for lineage.**
- `processed_timestamp` = When the record was processed by Silver. **Add as new column.**

```python
# ❌ WRONG: Dropping Bronze metadata
.drop("_ingested_at", "_source_file")

# ❌ WRONG: Overwriting Bronze ingestion time
.withColumn("_ingested_at", current_timestamp())  # Destroys lineage!

# ✅ CORRECT: Preserve Bronze metadata, add Silver timestamp separately
.withColumn("processed_timestamp", current_timestamp())  # New column, doesn't overwrite
```

---

## 🔴 MANDATORY: Event-Time vs Processing-Time

ALWAYS use **event timestamps from the source** for business logic. NEVER use `_ingested_at` or `processed_timestamp` for grouping, windowing, or filtering business data.

```python
# ✅ CORRECT: Use event timestamp from source for business logic
.withColumn("is_recent_order",
    when(col("order_date") >= current_date() - lit(30), True).otherwise(False))

# ❌ WRONG: Using processing time for business logic
.withColumn("is_recent_order",
    when(col("processed_timestamp") >= current_date() - lit(30), True).otherwise(False))
```

**Why:** Event timestamps reflect when the business event occurred. Processing timestamps reflect when the pipeline ran. Late-arriving data will have a recent `processed_timestamp` but an older event timestamp. Business logic must use event time for correctness.

---

## Schema Evolution: Full Refresh Required

Streaming tables require a **full refresh** for incompatible schema changes:
- Adding a NOT NULL column
- Changing a column's data type
- Removing a column that downstream tables depend on

```bash
# Trigger full refresh after incompatible schema change
databricks pipelines start-update --pipeline-name "[dev] Silver Layer Pipeline" --full-refresh
```

**Compatible changes (no full refresh needed):**
- Adding a nullable column
- Widening a numeric type (INT -> BIGINT)
- Adding new expectations/rules to the DQ rules table
