# Notebook Patterns Reference

Complete code patterns for both `.py` and `.ipynb` formats, helper function implementations, widget fallback patterns, Spark session initialization, dev/prod configuration, `%run` import patterns, and Asset Bundle integration.

## Databricks Workspace Format (.py)

### Complete Template

```python
# Databricks notebook source
# MAGIC %md
# MAGIC # Ad-Hoc Exploration Notebook
# MAGIC 
# MAGIC This notebook provides helper functions for exploring Bronze, Silver, and Gold layer tables.

# COMMAND ----------
# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------
# Default values
catalog = "main"
schema = "default"

# Try widgets (Databricks workspace), fall back to defaults
try:
    dbutils.widgets.text("catalog", catalog, "Catalog")
    dbutils.widgets.text("schema", schema, "Schema")
    catalog = dbutils.widgets.get("catalog")
    schema = dbutils.widgets.get("schema")
except Exception:
    # Widgets not available (Databricks Connect)
    pass

print(f"Using catalog: {catalog}, schema: {schema}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Helper Functions

# COMMAND ----------
def list_tables(catalog_name: str, schema_name: str) -> None:
    """
    List all tables in a schema with metadata.
    
    Args:
        catalog_name: Unity Catalog catalog name
        schema_name: Schema name
    """
    try:
        tables = spark.sql(f"SHOW TABLES IN {catalog_name}.{schema_name}")
        print(f"\n📊 Tables in {catalog_name}.{schema_name}:")
        print("=" * 80)
        tables.show(truncate=False)
    except Exception as e:
        print(f"❌ Error listing tables: {e}")

# COMMAND ----------
def explore_table(catalog_name: str, schema_name: str, table_name: str, limit: int = 10) -> None:
    """
    Explore a table: show schema and sample data.
    
    Args:
        catalog_name: Unity Catalog catalog name
        schema_name: Schema name
        table_name: Table name
        limit: Number of rows to display
    """
    full_table_name = f"{catalog_name}.{schema_name}.{table_name}"
    
    print(f"\n🔍 Exploring {full_table_name}")
    print("=" * 80)
    
    # Show schema
    print("\n📋 Schema:")
    spark.sql(f"DESCRIBE TABLE {full_table_name}").show(truncate=False)
    
    # Show sample data
    print(f"\n📊 Sample Data (first {limit} rows):")
    spark.table(full_table_name).show(limit, truncate=False)
    
    # Show row count
    count = spark.table(full_table_name).count()
    print(f"\n📈 Total Rows: {count:,}")

# COMMAND ----------
def check_data_quality(catalog_name: str, schema_name: str, table_name: str) -> None:
    """
    Check data quality: null counts, duplicates, basic statistics.
    
    Args:
        catalog_name: Unity Catalog catalog name
        schema_name: Schema name
        table_name: Table name
    """
    from pyspark.sql.functions import col, count, when, isnan, isnull
    
    full_table_name = f"{catalog_name}.{schema_name}.{table_name}"
    df = spark.table(full_table_name)
    
    print(f"\n🔍 Data Quality Check: {full_table_name}")
    print("=" * 80)
    
    # Null counts per column
    print("\n📊 Null Counts:")
    null_counts = df.select([
        count(when(isnull(c) | isnan(c), c)).alias(c)
        for c in df.columns
    ]).collect()[0].asDict()
    
    total_rows = df.count()
    for col_name, null_count in null_counts.items():
        null_pct = (null_count / total_rows * 100) if total_rows > 0 else 0
        print(f"  {col_name}: {null_count:,} nulls ({null_pct:.2f}%)")
    
    # Row count
    print(f"\n📈 Total Rows: {total_rows:,}")
    
    # Duplicate check
    print("\n🔍 Duplicate Check:")
    duplicate_count = df.groupBy(df.columns).count().filter(col("count") > 1).count()
    if duplicate_count > 0:
        print(f"  ⚠️ Found {duplicate_count} duplicate row groups")
    else:
        print("  ✅ No duplicates found")

# COMMAND ----------
def compare_tables(
    catalog1: str, schema1: str, table1: str,
    catalog2: str, schema2: str, table2: str
) -> None:
    """
    Compare two tables (e.g., Silver vs Gold) for differences.
    
    Args:
        catalog1, schema1, table1: First table identifiers
        catalog2, schema2, table2: Second table identifiers
    """
    full_table1 = f"{catalog1}.{schema1}.{table1}"
    full_table2 = f"{catalog2}.{schema2}.{table2}"
    
    print(f"\n🔍 Comparing Tables:")
    print(f"  Table 1: {full_table1}")
    print(f"  Table 2: {full_table2}")
    print("=" * 80)
    
    df1 = spark.table(full_table1)
    df2 = spark.table(full_table2)
    
    # Row counts
    count1 = df1.count()
    count2 = df2.count()
    print(f"\n📊 Row Counts:")
    print(f"  {full_table1}: {count1:,} rows")
    print(f"  {full_table2}: {count2:,} rows")
    print(f"  Difference: {abs(count1 - count2):,} rows")
    
    # Column comparison
    cols1 = set(df1.columns)
    cols2 = set(df2.columns)
    common_cols = cols1 & cols2
    only_in_1 = cols1 - cols2
    only_in_2 = cols2 - cols1
    
    print(f"\n📋 Column Comparison:")
    print(f"  Common columns: {len(common_cols)}")
    if only_in_1:
        print(f"  Only in {table1}: {only_in_1}")
    if only_in_2:
        print(f"  Only in {table2}: {only_in_2}")

# COMMAND ----------
def show_table_properties(catalog_name: str, schema_name: str, table_name: str) -> None:
    """
    Show table properties and governance metadata.
    
    Args:
        catalog_name: Unity Catalog catalog name
        schema_name: Schema name
        table_name: Table name
    """
    full_table_name = f"{catalog_name}.{schema_name}.{table_name}"
    
    print(f"\n🏷️ Table Properties: {full_table_name}")
    print("=" * 80)
    
    # Show table properties
    properties = spark.sql(f"SHOW TBLPROPERTIES {full_table_name}").collect()
    print("\n📋 Properties:")
    for prop in properties:
        print(f"  {prop['key']}: {prop['value']}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Usage Examples

# COMMAND ----------
# List all tables
list_tables(catalog, schema)

# COMMAND ----------
# Explore a specific table
# explore_table(catalog, schema, "dim_store")

# COMMAND ----------
# Check data quality
# check_data_quality(catalog, schema, "dim_store")

# COMMAND ----------
# Compare tables across layers
# compare_tables(
#     catalog, "silver", "silver_store",
#     catalog, "gold", "dim_store"
# )

# COMMAND ----------
# Show table properties
# show_table_properties(catalog, schema, "dim_store")
```

## Local Jupyter Format (.ipynb)

### Setup Cell (Markdown)

```markdown
# Ad-Hoc Exploration Notebook

This notebook provides helper functions for exploring Bronze, Silver, and Gold layer tables.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure Databricks connection:
   - Set up Databricks profile: `databricks configure --profile <profile-name>`
   - Or set environment variables: `DATABRICKS_HOST`, `DATABRICKS_TOKEN`

3. Update configuration variables below
```

### Configuration Cell (Python)

```python
# Configuration
catalog = "main"
schema = "default"

# Initialize Spark session
from databricks.connect import DatabricksSession

# CRITICAL: Must specify .serverless() or .clusterId()
spark = DatabricksSession.builder.serverless().profile("profile").getOrCreate()

print(f"Using catalog: {catalog}, schema: {schema}")
```

### Helper Functions Cell (Python)

```python
# Helper Functions (same as .py version, but without MAGIC commands)

def list_tables(catalog_name: str, schema_name: str) -> None:
    """List all tables in a schema with metadata."""
    try:
        tables = spark.sql(f"SHOW TABLES IN {catalog_name}.{schema_name}")
        print(f"\n📊 Tables in {catalog_name}.{schema_name}:")
        print("=" * 80)
        tables.show(truncate=False)
    except Exception as e:
        print(f"❌ Error listing tables: {e}")

# ... (include all other helper functions from .py version)
```

## Dev vs Prod Configuration Patterns

### Development Environment (with user prefix)

```python
import os

# Get username for dev isolation
username = spark.sql("SELECT current_user()").first()[0].split("@")[0].replace(".", "_")
project = "my_project"

catalog = "dev_catalog"
bronze_schema = f"dev_{username}_{project}_bronze"
silver_schema = f"dev_{username}_{project}_silver"
gold_schema = f"dev_{username}_{project}_gold"

print(f"Dev environment: {catalog}.{bronze_schema}")
```

### Production Environment

```python
project = "my_project"

catalog = "prod_catalog"
bronze_schema = f"{project}_bronze"
silver_schema = f"{project}_silver"
gold_schema = f"{project}_gold"

print(f"Prod environment: {catalog}.{bronze_schema}")
```

### Widget-Driven Environment Switching

```python
# Default values
environment = "dev"
catalog = "dev_catalog"

try:
    dbutils.widgets.dropdown("environment", "dev", ["dev", "staging", "prod"], "Environment")
    environment = dbutils.widgets.get("environment")
except Exception:
    pass

# Set catalog based on environment
env_config = {
    "dev": "dev_catalog",
    "staging": "staging_catalog",
    "prod": "prod_catalog"
}
catalog = env_config.get(environment, "dev_catalog")
print(f"Environment: {environment}, Catalog: {catalog}")
```

## %run Import Pattern

Use `%run` to import exploration functions into other notebooks:

```python
# In another Databricks notebook:
%run ./exploration/adhoc_exploration

# Now all helper functions are available in this notebook
list_tables(catalog, bronze_schema)
df = explore_table(catalog, gold_schema, "fact_sales_daily")
check_data_quality(catalog, gold_schema, "fact_sales_daily")
```

**Important:** `%run` executes the target notebook in the calling notebook's context. All variables and functions defined in the target become available.

## Asset Bundle Integration

### YAML Configuration

```yaml
resources:
  jobs:
    exploration_job:
      name: adhoc-exploration
      tasks:
        - task_key: explore_tables
          notebook_task:
            notebook_path: ../src/exploration/adhoc_exploration.py  # ✅ Include .py extension
            base_parameters:
              catalog: ${var.catalog}
              schema: ${var.schema}
```

### Requirements File

```txt
# requirements.txt
databricks-sdk[notebook]>=0.28.0
pyspark>=3.5.0
```

## Domain-Specific Patterns

### Bronze Layer Exploration

```python
# Explore Bronze layer tables
list_tables(catalog, bronze_schema)
explore_table(catalog, bronze_schema, "bronze_orders")
check_data_quality(catalog, bronze_schema, "bronze_orders")
```

### Silver Layer Exploration

```python
# Explore Silver layer tables
list_tables(catalog, silver_schema)
explore_table(catalog, silver_schema, "silver_orders")
check_data_quality(catalog, silver_schema, "silver_orders")
```

### Gold Layer Exploration

```python
# Explore Gold layer tables
list_tables(catalog, gold_schema)
explore_table(catalog, gold_schema, "dim_store")
check_data_quality(catalog, gold_schema, "dim_store")
show_table_properties(catalog, gold_schema, "dim_store")
```

### Cross-Layer Comparison

```python
# Compare Silver vs Gold
compare_tables(
    catalog, silver_schema, "silver_store",
    catalog, gold_schema, "dim_store"
)
```

## Advanced Patterns

### Custom Analysis Functions

```python
def analyze_sales_trends(catalog_name: str, schema_name: str, fact_table: str, days: int = 30):
    """Analyze sales trends for the last N days."""
    from pyspark.sql.functions import sum, date_sub, current_date, col
    
    df = spark.table(f"{catalog_name}.{schema_name}.{fact_table}")
    
    recent_sales = df.filter(
        col("date_key") >= date_sub(current_date(), days)
    ).groupBy("date_key").agg(
        sum("net_revenue").alias("daily_revenue")
    ).orderBy("date_key")
    
    recent_sales.show()
```

### Schema Evolution Tracking

```python
def track_schema_changes(catalog_name: str, schema_name: str, table_name: str):
    """Track schema changes over time using table history."""
    full_table = f"{catalog_name}.{schema_name}.{table_name}"
    
    history = spark.sql(f"DESCRIBE HISTORY {full_table}")
    print(f"\n📜 Schema History for {full_table}:")
    history.select("version", "timestamp", "operation", "operationParameters").show(truncate=False)
```

## Best Practices

1. **Always use widget fallback pattern** for cross-environment compatibility
2. **Initialize Spark with `.serverless()` or `.clusterId()`** — never use default builder
3. **Include `.py` extension** in Asset Bundle notebook paths
4. **Create both formats** (.py and .ipynb) for maximum compatibility
5. **Document helper functions** with docstrings
6. **Use consistent naming** for helper functions across projects
7. **Handle errors gracefully** with try/except blocks
8. **Format output** for readability (tables, separators, emojis)

## References

- [Databricks Connect Documentation](https://docs.databricks.com/dev-tools/databricks-connect.html)
- [Databricks SDK for Python](https://databricks-sdk-py.readthedocs.io/)
- [PySpark SQL Functions](https://spark.apache.org/docs/latest/api/python/reference/pyspark.sql/functions.html)
