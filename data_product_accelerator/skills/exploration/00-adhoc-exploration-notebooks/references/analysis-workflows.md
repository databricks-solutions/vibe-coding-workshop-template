# Data Analysis Workflows

Step-by-step workflows for common exploration scenarios across Bronze, Silver, and Gold layers.

## Common Use Cases

### 1. Quick Data Validation (Bronze → Silver → Gold)

```python
# Compare record counts across layers
compare_tables(catalog, bronze_schema, "bronze_transactions",
               catalog, silver_schema, "silver_transactions")

compare_tables(catalog, silver_schema, "silver_transactions",
               catalog, gold_schema, "fact_sales_daily")

# Check for data quality issues at each layer
check_data_quality(catalog, silver_schema, "silver_transactions")
check_data_quality(catalog, gold_schema, "fact_sales_daily")
```

### 2. Data Quality Investigation

```python
# Check for null and duplicate issues
check_data_quality(catalog, silver_schema, "silver_transactions")

# Deep-dive into specific columns
from pyspark.sql.functions import col, count, when, isnull
df = spark.table(f"{catalog}.{silver_schema}.silver_transactions")

# Find rows with null revenue
df.filter(isnull("revenue")).show()

# Check value ranges
df.select("revenue").describe().show()
```

### 3. Schema Exploration

```python
# Explore a new table
df = explore_table(catalog, gold_schema, "fact_inventory_snapshot", limit=20)

# Verify schema matches YAML definition
expected_cols = ["store_key", "product_key", "date_key", "net_revenue"]
actual_cols = df.columns

missing = set(expected_cols) - set(actual_cols)
extra = set(actual_cols) - set(expected_cols)

if missing:
    print(f"⚠️  Missing columns: {missing}")
if extra:
    print(f"⚠️  Extra columns: {extra}")
```

### 4. Metric View Testing

Test Metric Views directly with SQL to verify they return correct results:

```sql
-- Test metric view aggregation
SELECT 
  store_number,
  MEASURE(`Total Revenue`) as revenue
FROM catalog.gold_schema.sales_performance_metrics
WHERE year = 2024

-- Test with multiple dimensions
SELECT 
  product_category,
  year,
  MEASURE(`Total Revenue`) as revenue,
  MEASURE(`Total Quantity`) as quantity
FROM catalog.gold_schema.sales_performance_metrics
GROUP BY product_category, year
ORDER BY revenue DESC
```

In PySpark:
```python
# Test metric view via Spark SQL
spark.sql("""
    SELECT store_number, MEASURE(`Total Revenue`) as revenue
    FROM {catalog}.{gold_schema}.sales_performance_metrics
    WHERE year = 2024
""".format(catalog=catalog, gold_schema=gold_schema)).show()
```

### 5. Monitoring Metrics Review

Query Lakehouse Monitoring profile metrics to check data health:

```sql
-- Check latest monitoring metrics for a Gold table
SELECT * 
FROM catalog.gold_schema.fact_sales_daily_profile_metrics
WHERE window.end = (
    SELECT MAX(window.end) 
    FROM catalog.gold_schema.fact_sales_daily_profile_metrics
)

-- Check for anomalies in monitoring drift table
SELECT column_name, metric_name, value, expected_value
FROM catalog.gold_schema.fact_sales_daily_drift_metrics
WHERE abs(value - expected_value) / NULLIF(expected_value, 0) > 0.1
ORDER BY abs(value - expected_value) DESC
```

### 6. Table Properties & Governance

```python
# Verify governance metadata
show_table_properties(catalog, gold_schema, "fact_sales_daily")

# Check specific properties
props_df = spark.sql(f"SHOW TBLPROPERTIES {catalog}.{gold_schema}.fact_sales_daily")
props_df.filter("key LIKE '%quality%' OR key LIKE '%domain%'").show(truncate=False)
```

## Step-by-Step Analysis Workflows

### Workflow 1: Initial Data Discovery

Use this when first exploring a new project or unfamiliar dataset.

1. **List all tables in each layer**
   ```python
   list_tables(catalog, bronze_schema)
   list_tables(catalog, silver_schema)
   list_tables(catalog, gold_schema)
   ```

2. **Explore key tables**
   ```python
   explore_table(catalog, silver_schema, "silver_transactions", limit=10)
   explore_table(catalog, gold_schema, "fact_sales_daily", limit=10)
   ```

3. **Check data quality**
   ```python
   check_data_quality(catalog, silver_schema, "silver_transactions")
   ```

4. **Review table properties**
   ```python
   show_table_properties(catalog, gold_schema, "fact_sales_daily")
   ```

### Workflow 2: Data Quality Investigation

Use this when debugging DQ issues or validating DLT expectations.

1. **Identify problematic tables**
   ```python
   list_tables(catalog, silver_schema)
   ```

2. **Check for nulls and duplicates**
   ```python
   check_data_quality(catalog, silver_schema, "problematic_table")
   ```

3. **Compare across layers**
   ```python
   compare_tables(catalog, bronze_schema, "bronze_table",
                  catalog, silver_schema, "silver_table")
   ```

4. **Investigate dropped rows**
   ```python
   bronze_df = spark.table(f"{catalog}.{bronze_schema}.bronze_data")
   silver_df = spark.table(f"{catalog}.{silver_schema}.silver_data")

   print(f"Bronze: {bronze_df.count():,}")
   print(f"Silver: {silver_df.count():,}")
   print(f"Dropped: {bronze_df.count() - silver_df.count():,}")
   ```

### Workflow 3: Schema Validation

Use this after Gold layer deployment to verify schema correctness.

1. **Verify schema matches expectations**
   ```python
   df = explore_table(catalog, gold_schema, "fact_sales_daily")
   df.printSchema()
   ```

2. **Check table properties**
   ```python
   show_table_properties(catalog, gold_schema, "fact_sales_daily")
   ```

3. **Validate column names match YAML**
   ```python
   expected_cols = ["store_key", "product_key", "date_key", "net_revenue"]
   actual_cols = df.columns
   
   missing = set(expected_cols) - set(actual_cols)
   extra = set(actual_cols) - set(expected_cols)
   
   if missing:
       print(f"⚠️  Missing columns: {missing}")
   if extra:
       print(f"⚠️  Extra columns: {extra}")
   if not missing and not extra:
       print("✅ Schema matches expected columns")
   ```

### Workflow 4: Cross-Layer Lineage Validation

Use this to trace data from Bronze → Silver → Gold.

1. **Check row counts at each layer**
   ```python
   for schema, table in [
       (bronze_schema, "bronze_orders"),
       (silver_schema, "silver_orders"),
       (gold_schema, "fact_orders")
   ]:
       count = spark.table(f"{catalog}.{schema}.{table}").count()
       print(f"  {schema}.{table}: {count:,} rows")
   ```

2. **Compare key columns**
   ```python
   compare_tables(catalog, bronze_schema, "bronze_orders",
                  catalog, silver_schema, "silver_orders")
   compare_tables(catalog, silver_schema, "silver_orders",
                  catalog, gold_schema, "fact_orders")
   ```

3. **Spot-check specific records**
   ```python
   # Trace a specific order through all layers
   order_id = "ORD-12345"
   for schema, table in [
       (bronze_schema, "bronze_orders"),
       (silver_schema, "silver_orders"),
       (gold_schema, "fact_orders")
   ]:
       print(f"\n--- {schema}.{table} ---")
       spark.table(f"{catalog}.{schema}.{table}").filter(
           f"order_id = '{order_id}'"
       ).show(truncate=False)
   ```

## Quick Exploration Commands

```python
# List all tables in each layer
list_tables(catalog, bronze_schema)
# list_tables(catalog, silver_schema)
# list_tables(catalog, gold_schema)

# Explore a specific table
# explore_table(catalog, bronze_schema, "bronze_store_dim", limit=10)

# Check data quality
# check_data_quality(catalog, silver_schema, "silver_transactions")

# Compare Bronze vs Silver
# compare_tables(catalog, bronze_schema, "bronze_transactions",
#                catalog, silver_schema, "silver_transactions")

# Show table properties
# show_table_properties(catalog, gold_schema, "fact_sales_daily")
```
