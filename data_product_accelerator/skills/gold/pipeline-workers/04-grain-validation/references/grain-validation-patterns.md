# Grain Validation Patterns (Implementation)

This document provides detailed runtime grain validation patterns, merge script examples, and validation SQL for different fact table grain types.

## Complete Merge Script Examples

### Transaction-Level Fact Pattern

**Example Merge Script:**
```python
def merge_fact_sales_transactions(spark, catalog, silver_schema, gold_schema):
    """
    Merge transaction-level sales fact.
    
    GRAIN: One row per individual sale transaction
    PRIMARY KEY: (transaction_id)
    GRAIN TYPE: transaction
    AGGREGATION: Not Required
    """
    # Read Silver transactions (already at transaction grain)
    transactions_df = spark.table(f"{catalog}.{silver_schema}.silver_sales_transactions")
    
    # ✅ No aggregation - pass through individual records
    updates_df = transactions_df.select(
        col("transaction_id"),
        col("customer_id"),
        col("product_id"),
        col("sale_timestamp"),
        col("amount"),
        col("quantity"),
        col("channel")
    )
    
    # Validate grain before merge
    validate_fact_grain(
        spark, updates_df, catalog, gold_schema,
        "fact_sales_transactions",
        ["transaction_id"]
    )
    
    # Merge with transaction-level key
    merge_fact_table(
        spark, updates_df, catalog, gold_schema,
        "fact_sales_transactions",
        ["transaction_id"]
    )
```

### Aggregated Fact Pattern

**Example Merge Script:**
```python
def merge_fact_sales_daily(spark, catalog, silver_schema, gold_schema):
    """
    Merge daily aggregated sales fact.
    
    GRAIN: One row per date-store-product combination (daily aggregate)
    PRIMARY KEY: (date_key, store_key, product_key)
    GRAIN TYPE: aggregated
    AGGREGATION: Required - GroupBy on (date_key, store_key, product_key)
    """
    # Read Silver transactions (transaction-level)
    transactions_df = spark.table(f"{catalog}.{silver_schema}.silver_sales_transactions")
    
    # ✅ Aggregate to daily grain
    daily_sales_df = (
        transactions_df
        .withColumn("date_key", date_format(col("sale_timestamp"), "yyyyMMdd").cast("int"))
        .groupBy("date_key", "store_key", "product_key")
        .agg(
            sum("amount").alias("total_revenue"),
            sum("quantity").alias("total_quantity"),
            count("*").alias("transaction_count"),
            avg("amount" / col("quantity")).alias("avg_unit_price")
        )
    )
    
    # Validate grain before merge
    validate_fact_grain(
        spark, daily_sales_df, catalog, gold_schema,
        "fact_sales_daily",
        ["date_key", "store_key", "product_key"]
    )
    
    # Merge with composite key matching grain
    merge_fact_table(
        spark, daily_sales_df, catalog, gold_schema,
        "fact_sales_daily",
        ["date_key", "store_key", "product_key"]
    )
```

### Snapshot Fact Pattern

**Example Merge Script:**
```python
def merge_fact_inventory_snapshot(spark, catalog, silver_schema, gold_schema):
    """
    Merge inventory snapshot fact.
    
    GRAIN: One row per product-warehouse-date combination (daily snapshot)
    PRIMARY KEY: (product_key, warehouse_key, snapshot_date_key)
    GRAIN TYPE: snapshot
    AGGREGATION: Not Required (snapshots already at grain)
    """
    # Read Silver snapshots (already at snapshot grain)
    snapshots_df = spark.table(f"{catalog}.{silver_schema}.silver_inventory_snapshots")
    
    # ✅ Deduplicate - keep latest snapshot per product-warehouse-date
    deduplicated_df = (
        snapshots_df
        .withColumn("snapshot_date_key", date_format(col("snapshot_timestamp"), "yyyyMMdd").cast("int"))
        .withColumn("row_num", row_number().over(
            Window.partitionBy("product_key", "warehouse_key", "snapshot_date_key")
                  .orderBy(col("snapshot_timestamp").desc())
        ))
        .filter(col("row_num") == 1)
        .drop("row_num", "snapshot_timestamp")
    )
    
    # Validate grain before merge
    validate_fact_grain(
        spark, deduplicated_df, catalog, gold_schema,
        "fact_inventory_snapshot",
        ["product_key", "warehouse_key", "snapshot_date_key"]
    )
    
    # Merge with snapshot key
    merge_fact_table(
        spark, deduplicated_df, catalog, gold_schema,
        "fact_inventory_snapshot",
        ["product_key", "warehouse_key", "snapshot_date_key"]
    )
```

### Hourly Aggregated Fact Pattern

```python
def merge_fact_api_usage_hourly(spark, catalog, silver_schema, gold_schema):
    """
    GRAIN: One row per hour-endpoint combination (hourly aggregate)
    PRIMARY KEY: (date_key, hour_of_day, endpoint_key)
    GRAIN TYPE: aggregated
    """
    requests_df = spark.table(f"{catalog}.{silver_schema}.silver_api_requests")
    
    hourly_df = (
        requests_df
        .withColumn("date_key", date_format(col("timestamp"), "yyyyMMdd").cast("int"))
        .withColumn("hour_of_day", hour(col("timestamp")))
        .groupBy("date_key", "hour_of_day", "endpoint_key")
        .agg(
            count("*").alias("request_count"),
            avg("latency_ms").alias("avg_latency_ms"),
            sum("error_flag").alias("error_count")
        )
    )
    
    merge_fact_table(
        spark, hourly_df, catalog, gold_schema,
        "fact_api_usage_hourly",
        ["date_key", "hour_of_day", "endpoint_key"]
    )
```

### Monthly Snapshot Fact Pattern

```python
def merge_fact_account_balance_monthly(spark, catalog, silver_schema, gold_schema):
    """
    GRAIN: One row per account-month combination (monthly snapshot)
    PRIMARY KEY: (account_key, snapshot_month_key)
    GRAIN TYPE: snapshot
    """
    snapshots_df = spark.table(f"{catalog}.{silver_schema}.silver_account_snapshots")
    
    monthly_df = (
        snapshots_df
        .withColumn("snapshot_month_key", date_format(col("snapshot_date"), "yyyyMM").cast("int"))
        .withColumn("row_num", row_number().over(
            Window.partitionBy("account_key", "snapshot_month_key")
                  .orderBy(col("snapshot_date").desc())
        ))
        .filter(col("row_num") == 1)
        .drop("row_num")
    )
    
    merge_fact_table(
        spark, monthly_df, catalog, gold_schema,
        "fact_account_balance_monthly",
        ["account_key", "snapshot_month_key"]
    )
```

## Validation SQL Patterns

### Check for Duplicate Rows at Grain Level

```sql
-- Transaction grain: Check for duplicate transaction_ids
SELECT 
    transaction_id,
    COUNT(*) as row_count
FROM catalog.schema.fact_sales_transactions
GROUP BY transaction_id
HAVING COUNT(*) > 1;

-- Aggregated grain: Check for duplicate grain combinations
SELECT 
    date_key,
    store_key,
    product_key,
    COUNT(*) as row_count
FROM catalog.schema.fact_sales_daily
GROUP BY date_key, store_key, product_key
HAVING COUNT(*) > 1;

-- Snapshot grain: Check for duplicate snapshots
SELECT 
    product_key,
    warehouse_key,
    snapshot_date_key,
    COUNT(*) as row_count
FROM catalog.schema.fact_inventory_snapshot
GROUP BY product_key, warehouse_key, snapshot_date_key
HAVING COUNT(*) > 1;
```

### Validate Measures Match Grain Type

```sql
-- Transaction grain: Measures should be individual values (not aggregated)
SELECT 
    COUNT(*) as total_rows,
    SUM(CASE WHEN transaction_count = 1 THEN 1 ELSE 0 END) as correct_count
FROM catalog.schema.fact_sales_transactions;

-- Aggregated grain: Measures should be aggregated (SUM, COUNT, AVG)
SELECT 
    COUNT(*) as total_rows,
    SUM(CASE WHEN transaction_count > 1 THEN 1 ELSE 0 END) as aggregated_rows
FROM catalog.schema.fact_sales_daily;

-- Snapshot grain: Measures should be point-in-time values
SELECT 
    product_key,
    snapshot_date_key,
    on_hand_quantity,
    COUNT(*) as snapshot_count
FROM catalog.schema.fact_inventory_snapshot
GROUP BY product_key, snapshot_date_key, on_hand_quantity
HAVING COUNT(*) > 1;
```

### Validate Primary Key Completeness

```sql
-- Check for NULL values in PRIMARY KEY columns
SELECT 
    COUNT(*) as total_rows,
    SUM(CASE WHEN transaction_id IS NULL THEN 1 ELSE 0 END) as null_pk_rows
FROM catalog.schema.fact_sales_transactions;

-- Composite PK: Check all PK columns
SELECT 
    COUNT(*) as total_rows,
    SUM(CASE WHEN date_key IS NULL OR store_key IS NULL OR product_key IS NULL 
        THEN 1 ELSE 0 END) as null_pk_rows
FROM catalog.schema.fact_sales_daily;
```

## Common Mistakes and Fixes

### Mistake 1: Aggregated DDL, Transaction Script

**Problem:**
```python
# DDL (Aggregated)
PRIMARY KEY (date_key, endpoint_key, model_key)

# Script (Transaction - WRONG!)
updates_df = df.select("request_id", ...)  # ❌ Transaction ID
merge_fact_table(..., ["request_id"])      # ❌ Wrong grain!
```

**Fix:**
```python
# ✅ CORRECT: Aggregate to match DDL
updates_df = (
    df
    .withColumn("date_key", date_format(col("timestamp"), "yyyyMMdd").cast("int"))
    .groupBy("date_key", "endpoint_key", "model_key")
    .agg(
        count("*").alias("request_count"),
        avg("latency_ms").alias("avg_latency_ms"),
        sum("error_count").alias("error_count")
    )
)
merge_fact_table(..., ["date_key", "endpoint_key", "model_key"])
```

### Mistake 2: Transaction DDL, Aggregated Script

**Problem:**
```python
# DDL (Transaction)
PRIMARY KEY (query_key)

# Script (Aggregated - WRONG!)
updates_df = df.groupBy("query_key").agg(count("*"))  # ❌ Why aggregate?
merge_fact_table(..., ["query_key"])
```

**Fix:**
```python
# ✅ CORRECT: No aggregation for transaction grain
updates_df = df.select(
    "query_key",
    "execution_duration_ms",
    "rows_returned",
    "query_timestamp"
)
merge_fact_table(..., ["query_key"])
```

### Mistake 3: Ambiguous YAML Grain

**Problem:**
```yaml
# ❌ BAD: Grain not explicitly documented
table_name: fact_model_serving_inference
primary_key:
  columns:
    - date_key
    - endpoint_key
    - model_key
```

**Fix:**
```yaml
# ✅ GOOD: Grain explicitly documented
table_name: fact_model_serving_inference
grain: "Daily aggregate per endpoint-model combination"
grain_type: aggregated
primary_key:
  columns:
    - date_key
    - endpoint_key
    - model_key
measures:
  - name: request_count
    aggregation: SUM
  - name: avg_latency_ms
    aggregation: AVG
```

---

## Accumulating Snapshot Grain Validation

Accumulating snapshot fact tables have one row per business process instance (e.g., one row per order). The grain is the business process identifier, NOT a time-based composite.

**Grain Pattern:** Single or low-cardinality composite PK (e.g., `order_key`), with milestone DATE/TIMESTAMP columns that fill in over time.

**Validation:**
```python
def validate_accumulating_snapshot_grain(df, pk_columns, milestone_columns):
    """Validate accumulating snapshot grain: one row per process instance.
    
    Also validates milestone column monotonicity (earlier milestones
    should precede later ones where both are non-NULL).
    """
    # Standard grain check: one row per PK
    dup_count = df.groupBy(pk_columns).count().filter("count > 1").count()
    if dup_count > 0:
        raise ValueError(
            f"Grain violation: {dup_count} duplicate PK combinations found. "
            f"Accumulating snapshots must have exactly one row per process instance."
        )
    
    # Milestone ordering check (advisory, not blocking)
    for i in range(len(milestone_columns) - 1):
        earlier = milestone_columns[i]
        later = milestone_columns[i + 1]
        violations = df.filter(
            f"{earlier} IS NOT NULL AND {later} IS NOT NULL AND {earlier} > {later}"
        ).count()
        if violations > 0:
            print(f"  WARNING: {violations} rows have {earlier} > {later} (milestone order violation)")
```

**YAML trigger:** `grain_type: accumulating_snapshot`

---

## Factless Fact Grain Validation

Factless fact tables record event occurrences where row existence IS the fact. The grain is typically a composite of all FK columns.

**Grain Pattern:** Composite PK of all FK columns (e.g., `student_key + course_key + date_key`). No measure columns.

**Validation:**
```python
def validate_factless_grain(df, pk_columns, gold_columns):
    """Validate factless fact grain: composite FK key with no measures.
    
    Also validates that no numeric measure columns exist.
    """
    # Standard grain check
    dup_count = df.groupBy(pk_columns).count().filter("count > 1").count()
    if dup_count > 0:
        raise ValueError(
            f"Grain violation: {dup_count} duplicate FK combinations. "
            f"Factless facts must have exactly one row per event/relationship."
        )
    
    # Verify no measure columns (only FKs + degenerate dims + audit timestamps)
    audit_cols = {"record_created_timestamp", "record_updated_timestamp"}
    unexpected_measures = [
        c for c in gold_columns
        if c not in pk_columns and c not in audit_cols
        and not c.endswith("_key") and not c.endswith("_id")
    ]
    if unexpected_measures:
        print(f"  WARNING: Factless fact has non-FK, non-audit columns: {unexpected_measures}")
```

**YAML trigger:** `grain_type: factless`
