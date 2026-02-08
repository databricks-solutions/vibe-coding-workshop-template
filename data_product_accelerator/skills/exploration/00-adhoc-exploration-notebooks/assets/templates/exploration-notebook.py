# Databricks notebook source
# MAGIC %md
# MAGIC # Ad-Hoc Exploration Notebook
# MAGIC 
# MAGIC This notebook provides helper functions for exploring Bronze, Silver, and Gold layer tables.
# MAGIC 
# MAGIC ## Features
# MAGIC - Table discovery and listing
# MAGIC - Schema and sample data exploration
# MAGIC - Data quality checks
# MAGIC - Cross-layer table comparison
# MAGIC - Governance metadata viewing

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
    from pyspark.sql.functions import col
    
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
# MAGIC 
# MAGIC Uncomment and modify the examples below to explore your tables.

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
