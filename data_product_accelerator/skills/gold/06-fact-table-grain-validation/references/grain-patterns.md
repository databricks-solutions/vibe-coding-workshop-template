# Fact Table Grain Patterns

This document provides detailed grain validation patterns, SQL examples, and implementation strategies for different fact table grain types.

## Grain Type Analysis

### Transaction-Level Fact Pattern

**When to Use:**
- **One row per business event** (sale, click, API call)
- **Primary Key:** Single surrogate key (`transaction_id`, `event_id`, `request_id`)
- **Measures:** Individual event metrics (amount, duration, count=1)

**Key Characteristics:**
- ✅ No `.groupBy()` or `.agg()` in merge script
- ✅ Single surrogate key as PRIMARY KEY
- ✅ Measures are direct pass-through (no SUM, AVG, COUNT)
- ✅ One source row → one target row

**Example DDL:**
```sql
CREATE TABLE fact_sales_transactions (
  transaction_id BIGINT NOT NULL,
  customer_id BIGINT NOT NULL,
  product_id BIGINT NOT NULL,
  sale_timestamp TIMESTAMP NOT NULL,
  amount DECIMAL(18,2) NOT NULL,
  quantity INT NOT NULL,
  channel STRING,
  PRIMARY KEY (transaction_id) NOT ENFORCED
)
```

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

**When to Use:**
- **Pre-aggregated summaries** (daily sales, hourly usage)
- **Primary Key:** Composite key of dimensions defining grain (`date_key, store_key, product_key`)
- **Measures:** Aggregated metrics (total_revenue, avg_latency, request_count)

**Key Characteristics:**
- ✅ Uses `.groupBy()` on grain dimensions
- ✅ Uses `.agg()` with SUM, COUNT, AVG, MAX
- ✅ Composite PRIMARY KEY matches `.groupBy()` columns
- ✅ Multiple source rows → one target row per grain

**Example DDL:**
```sql
CREATE TABLE fact_sales_daily (
  date_key INT NOT NULL,
  store_key INT NOT NULL,
  product_key INT NOT NULL,
  total_revenue DECIMAL(18,2) NOT NULL,
  total_quantity INT NOT NULL,
  transaction_count BIGINT NOT NULL,
  avg_unit_price DECIMAL(18,2) NOT NULL,
  PRIMARY KEY (date_key, store_key, product_key) NOT ENFORCED
)
```

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

**When to Use:**
- **Point-in-time state** (daily inventory levels, account balances)
- **Primary Key:** Entity + date (`entity_key, snapshot_date_key`)
- **Measures:** Current values at snapshot time (on_hand_quantity, balance_amount)

**Key Characteristics:**
- ✅ No aggregation (snapshots already at correct grain)
- ✅ May need deduplication (latest snapshot wins)
- ✅ Composite PK: entity keys + snapshot date
- ✅ Measures are point-in-time values (not SUMs)

**Example DDL:**
```sql
CREATE TABLE fact_inventory_snapshot (
  product_key INT NOT NULL,
  warehouse_key INT NOT NULL,
  snapshot_date_key INT NOT NULL,
  on_hand_quantity INT NOT NULL,
  reserved_quantity INT NOT NULL,
  available_quantity INT NOT NULL,
  cost_per_unit DECIMAL(18,2) NOT NULL,
  PRIMARY KEY (product_key, warehouse_key, snapshot_date_key) NOT ENFORCED
)
```

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
-- Check that transaction_count is always 1
SELECT 
    COUNT(*) as total_rows,
    SUM(CASE WHEN transaction_count = 1 THEN 1 ELSE 0 END) as correct_count
FROM catalog.schema.fact_sales_transactions;

-- Aggregated grain: Measures should be aggregated (SUM, COUNT, AVG)
-- Check that transaction_count > 1 for some rows
SELECT 
    COUNT(*) as total_rows,
    SUM(CASE WHEN transaction_count > 1 THEN 1 ELSE 0 END) as aggregated_rows
FROM catalog.schema.fact_sales_daily;

-- Snapshot grain: Measures should be point-in-time values
-- Check that measures are not aggregated (no SUM/COUNT patterns)
SELECT 
    product_key,
    snapshot_date_key,
    on_hand_quantity,
    -- Should be single value, not sum of multiple snapshots
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
# What grain is this? Daily aggregate? Hourly? Per request?
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

## Extended Pattern Examples

### Hourly Aggregated Fact

```sql
CREATE TABLE fact_api_usage_hourly (
  date_key INT NOT NULL,
  hour_of_day INT NOT NULL,
  endpoint_key INT NOT NULL,
  request_count BIGINT NOT NULL,
  avg_latency_ms DOUBLE NOT NULL,
  error_count BIGINT NOT NULL,
  PRIMARY KEY (date_key, hour_of_day, endpoint_key) NOT ENFORCED
)
```

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

### Monthly Snapshot Fact

```sql
CREATE TABLE fact_account_balance_monthly (
  account_key INT NOT NULL,
  snapshot_month_key INT NOT NULL,
  balance_amount DECIMAL(18,2) NOT NULL,
  transaction_count INT NOT NULL,
  PRIMARY KEY (account_key, snapshot_month_key) NOT ENFORCED
)
```

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
