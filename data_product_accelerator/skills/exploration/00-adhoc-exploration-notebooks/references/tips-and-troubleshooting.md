# Tips, Extensions & Troubleshooting

Practical tips for working with exploration notebooks, extending them with custom analysis, and resolving common issues.

## Tips & Tricks

### Visualization with display()

```python
# Use display() for rich table visualizations in Databricks
display(df.groupBy("store_number").count())

# For charts, click the chart icon in Databricks display() output
display(df.groupBy("product_category").agg(sum("net_revenue").alias("revenue")))
```

### Summary Statistics

```python
# Get summary statistics for all numeric columns
df.describe().show()

# For specific columns
df.select("net_revenue", "quantity_sold").describe().show()
```

### Column Analysis

```python
# Analyze value distribution for a specific column
df.groupBy("product_category").count().orderBy("count", ascending=False).display()

# Distinct value counts
for col_name in df.columns:
    distinct_count = df.select(col_name).distinct().count()
    print(f"  {col_name}: {distinct_count} distinct values")
```

### Performance Analysis

```python
# Explain query execution plan
df.explain(extended=True)

# Check partition pruning
df.filter("date_key >= '2024-01-01'").explain(True)
```

### Sample Data Export

```python
# Export sample data for offline analysis
sample_df = df.limit(1000)
sample_df.toPandas().to_csv("/tmp/sample_data.csv", index=False)

# In Databricks, download from DBFS
dbutils.fs.cp("file:/tmp/sample_data.csv", "dbfs:/tmp/sample_data.csv")
```

## Extending the Notebook

### Adding Custom Helper Functions

```python
def my_custom_analysis(catalog_name: str, schema_name: str, table_name: str):
    """Your custom analysis logic."""
    full_name = f"{catalog_name}.{schema_name}.{table_name}"
    df = spark.table(full_name)
    
    # Your analysis here
    from pyspark.sql.functions import sum, avg, count
    result = df.groupBy("key_column").agg(
        count("*").alias("row_count"),
        sum("revenue").alias("total_revenue"),
        avg("revenue").alias("avg_revenue")
    )
    
    display(result)
```

### Adding Matplotlib Visualization

```python
import matplotlib.pyplot as plt
import pandas as pd

# Convert to Pandas for plotting (limit rows first!)
pdf = df.limit(1000).toPandas()

# Bar chart
pdf.plot(kind='bar', x='category', y='sales')
plt.title("Sales by Category")
plt.tight_layout()
plt.show()

# Time series
pdf_ts = df.groupBy("date_key").agg(sum("net_revenue").alias("revenue")).orderBy("date_key").toPandas()
pdf_ts.plot(x='date_key', y='revenue', kind='line')
plt.title("Revenue Over Time")
plt.tight_layout()
plt.show()
```

### Adding Plotly Interactive Charts (Databricks)

```python
import plotly.express as px

pdf = df.limit(5000).toPandas()
fig = px.scatter(pdf, x="quantity", y="revenue", color="category", title="Quantity vs Revenue")
fig.show()
```

## Troubleshooting

### "Table not found"

**Symptoms:** `AnalysisException: Table or view not found`

**Solutions:**
- Check that schema names match your environment (dev vs prod)
- Verify the table exists: `SHOW TABLES IN catalog.schema`
- Check for typos in catalog/schema/table names
- Ensure the full three-part name is correct: `catalog.schema.table`

```python
# Debug: List available schemas
spark.sql(f"SHOW SCHEMAS IN {catalog}").show()

# Debug: List tables in schema
spark.sql(f"SHOW TABLES IN {catalog}.{schema}").show()
```

### "Permission denied"

**Symptoms:** `PERMISSION_DENIED` or `Access denied`

**Solutions:**
- Ensure you have `SELECT` permission on the catalog/schema/table
- Check if you're using the correct catalog (dev vs prod)
- Contact your Unity Catalog admin for access grants

```sql
-- Check your current permissions
SHOW GRANTS ON SCHEMA catalog.schema;
SHOW GRANTS ON TABLE catalog.schema.table_name;
```

### Slow Queries

**Symptoms:** Queries take minutes or hang

**Solutions:**
- Use `.limit()` for initial exploration — never `SELECT *` on large tables
- Filter early in the query chain
- Check the query plan with `.explain()` for full table scans
- Use `CLUSTER BY` columns in your filters when possible

```python
# ❌ DON'T: Full table scan
df = spark.table("catalog.schema.huge_table")
df.show()

# ✅ DO: Limit and filter first
df = spark.table("catalog.schema.huge_table").filter("date_key >= '2024-01-01'").limit(100)
df.show()
```

### Databricks Connect Connection Issues

**Symptoms:** `ConnectionError`, `AuthenticationError`, timeout

**Solutions:**
- Verify your Databricks profile: `databricks auth env --profile <profile>`
- Check environment variables: `DATABRICKS_HOST`, `DATABRICKS_TOKEN`
- Ensure the cluster/serverless is running
- Check network connectivity to the workspace URL

```python
# Debug: Test connection
from databricks.connect import DatabricksSession
try:
    spark = DatabricksSession.builder.serverless().profile("profile").getOrCreate()
    spark.sql("SELECT 1").show()
    print("✅ Connection successful")
except Exception as e:
    print(f"❌ Connection failed: {e}")
```

## Best Practices

1. **Start Small**: Always use `.limit()` when exploring large tables — start with 10–20 rows
2. **Document Findings**: Add markdown cells to document insights as you explore
3. **Save Useful Queries**: Copy useful SQL/PySpark patterns to documentation or shared notebooks
4. **Check Permissions First**: Verify read access before running complex analyses
5. **Clean Up**: Comment out expensive operations (full counts, groupBy on large tables) after running
6. **Use Caching Wisely**: Cache intermediate DataFrames if you'll reuse them: `df.cache()`
7. **Mind the Costs**: Serverless compute bills per query — avoid runaway loops or repeated full-table scans
