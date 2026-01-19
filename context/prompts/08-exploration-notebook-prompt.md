# Ad-Hoc Data Exploration Notebook Prompt

## 🚀 Quick Start (30 minutes)

**Goal:** Create interactive notebooks for data exploration (works both in Databricks and locally)

**What You'll Create:**
1. `adhoc_exploration.py` - Databricks workspace version (with magic commands)
2. `adhoc_exploration_ipynb.ipynb` - Local Jupyter version (Databricks Connect)
3. Standard helper functions (list tables, explore, check quality, compare)

**Fast Track (Databricks Workspace):**
```python
# 1. Upload adhoc_exploration.py to Databricks
# 2. Run setup cells (installs databricks-sdk)
# 3. Use helper functions:

# List all tables in a schema
list_tables("my_catalog.my_schema")

# Quick exploration
explore_table("my_catalog.my_schema.fact_sales_daily")

# Data quality check
check_data_quality("my_catalog.my_schema.fact_sales_daily")

# Compare schemas
compare_tables(
    "my_catalog.silver_schema.silver_transactions",
    "my_catalog.gold_schema.fact_sales_daily"
)
```

**Fast Track (Local Jupyter):**
```bash
# 1. Install requirements
pip install -r requirements.txt

# 2. Configure Databricks Connect
databricks configure --profile my_profile

# 3. Launch Jupyter
jupyter lab

# 4. Open adhoc_exploration_ipynb.ipynb
```

**Key Differences:**
- **Databricks (.py):** Uses magic commands (`%pip`, `%sql`), `dbutils.widgets.text()` for params
- **Local (.ipynb):** Pure Python, direct variable assignment, requires Databricks Connect

**Standard Helper Functions:**
- `list_tables(schema)` - List all tables in schema
- `explore_table(table_name)` - Schema, sample rows, row count
- `check_data_quality(table_name)` - Nulls, duplicates, value ranges
- `compare_tables(table1, table2)` - Schema comparison
- `show_table_properties(table_name)` - TBLPROPERTIES metadata

**Output:** Interactive exploration notebooks for ad-hoc analysis

📖 **Full guide below** for detailed dual-format patterns →

---

## Quick Reference

**Use this prompt when creating exploration notebooks for your Databricks project.**

**Input Required:**
- Unity Catalog and schema names
- Tables to explore (Bronze, Silver, Gold)
- Common data quality checks needed

**Output:** Dual-format exploration notebook (Databricks + Jupyter) with helper functions.

**Time Estimate:** 1 hour

---

## 📋 Your Requirements (Fill These In First)

### Catalog Configuration
- **Catalog:** _________________ (e.g., `my_catalog`)
- **Bronze Schema:** _________________ (e.g., `my_project_bronze`)
- **Silver Schema:** _________________ (e.g., `my_project_silver`)
- **Gold Schema:** _________________ (e.g., `my_project_gold`)

### Tables to Explore (List 5-10 key tables)

| # | Layer | Table Name | Purpose |
|---|-------|-----------|---------|
| 1 | Bronze | _________ | _______ |
| 2 | Silver | _________ | _______ |
| 3 | Gold | _________ | _______ |

---

## Overview

The ad-hoc exploration notebook provides an interactive environment for exploring and analyzing data across Bronze, Silver, and Gold layers.

**Available Formats:**
- `adhoc_exploration.py` - Databricks notebook format (for Databricks workspace)
- `adhoc_exploration_ipynb.ipynb` - Jupyter notebook format (for local development, JupyterLab, VS Code)

## Setup

### For Databricks Workspace (adhoc_exploration.py)

1. Upload to Databricks workspace
2. Attach to cluster
3. The notebook will automatically install `databricks-sdk[notebook]`
4. Run cells interactively

### For Local Jupyter (adhoc_exploration_ipynb.ipynb)

1. **Install dependencies:**
   ```bash
   cd src/exploration
   pip install -r requirements.txt
   ```

2. **Configure Databricks Connect:**
   ```bash
   databricks configure
   ```
   Or set environment variables:
   ```bash
   export DATABRICKS_HOST="https://your-workspace.cloud.databricks.com"
   export DATABRICKS_TOKEN="your-token"
   ```
   See: https://docs.databricks.com/dev-tools/databricks-connect.html

3. **Update configuration in notebook:**
   - Open the notebook
   - Update the `catalog`, `bronze_schema`, `silver_schema`, `gold_schema` variables in cell 3
   - Run cells interactively

**Note:** The Jupyter version uses direct variable assignment instead of `dbutils.widgets` since widgets require a Databricks runtime.

## Features

### Built-in Helper Functions

1. **`list_tables(schema_name)`**
   - Lists all tables in a schema
   - Shows row counts and table comments
   - Quick overview of available data

2. **`explore_table(schema_name, table_name, limit=10)`**
   - Displays table schema
   - Shows sample data
   - Returns DataFrame for further analysis

3. **`check_data_quality(schema_name, table_name)`**
   - Runs basic data quality checks
   - Shows null counts per column
   - Checks for duplicates in ID columns

4. **`compare_tables(schema1, table1, schema2, table2)`**
   - Compares row counts between two tables
   - Identifies schema differences
   - Useful for Bronze → Silver → Gold validation

5. **`show_table_properties(schema_name, table_name)`**
   - Displays all table properties
   - Shows governance tags
   - Useful for compliance checks

## Usage

### Option 1: Run via Databricks UI

1. Open the notebook in Databricks workspace
2. Attach to a cluster
3. Adjust widget parameters if needed (defaults to dev environment)
4. Run cells interactively

### Option 2: Run via Asset Bundle

```bash
# Deploy the exploration job
databricks bundle deploy -t dev

# Run the exploration notebook
databricks bundle run -t dev adhoc_exploration_job
```

### Option 3: Direct Execution

```python
# In any Databricks notebook, import and use the functions:
%run ./exploration/adhoc_exploration

# Then use the helper functions
list_tables("{your_bronze_schema}")
df = explore_table("{your_gold_schema}", "{your_fact_table}")

# Example (Retail):
# list_tables("retail_bronze")
# df = explore_table("retail_gold", "fact_sales_daily")

# Example (Healthcare):
# list_tables("clinical_bronze")
# df = explore_table("clinical_gold", "fact_encounters")
```

## Common Use Cases

### 1. Quick Data Validation
```python
# Check Bronze → Silver data flow
compare_tables(bronze_schema, "bronze_transactions", 
               silver_schema, "silver_transactions")
```

### 2. Data Quality Investigation
```python
# Check for data issues
check_data_quality(silver_schema, "silver_transactions")
```

### 3. Schema Exploration
```python
# Explore a new table
df = explore_table(gold_schema, "fact_inventory_snapshot", limit=20)
```

### 4. Metric View Testing
```sql
-- Test metric views with SQL
SELECT 
  store_number,
  MEASURE(`Total Revenue`) as revenue
FROM ${catalog}.${gold_schema}.sales_performance_metrics
WHERE year = 2024
```

### 5. Monitoring Metrics Review
```sql
-- Check latest monitoring metrics
SELECT * 
FROM ${catalog}.${gold_schema}.fact_sales_daily_profile_metrics
WHERE window.end = (SELECT MAX(window.end) FROM ${catalog}.${gold_schema}.fact_sales_daily_profile_metrics)
```

## Parameters

The notebook accepts the following parameters (customize defaults for your environment):

- **catalog**: Unity Catalog name (default: `{your_catalog}`)
- **bronze_schema**: Bronze layer schema (default: `{your_project}_bronze`)
- **silver_schema**: Silver layer schema (default: `{your_project}_silver`)
- **gold_schema**: Gold layer schema (default: `{your_project}_gold`)

**Example configurations:**

**Development (with user prefix):**
```python
catalog = "dev_catalog"
bronze_schema = f"dev_{username}_{project}_bronze"
silver_schema = f"dev_{username}_{project}_silver"
gold_schema = f"dev_{username}_{project}_gold"
```

**Production:**
```python
catalog = "prod_catalog"
bronze_schema = f"{project}_bronze"
silver_schema = f"{project}_silver"
gold_schema = f"{project}_gold"
```

## Tips & Tricks

### Visualization
```python
# Use display() for nice table visualizations
display(df.groupBy("store_number").count())
```

### Summary Statistics
```python
# Get summary statistics for numeric columns
df.describe().show()
```

### Column Analysis
```python
# Analyze a specific column
df.groupBy("product_category").count().orderBy("count", ascending=False).display()
```

### Performance Analysis
```python
# Explain query execution plan
df.explain(extended=True)
```

### Sample Data Export
```python
# Export sample data for analysis
sample_df = df.limit(1000)
sample_df.toPandas().to_csv("/tmp/sample_data.csv")
```

## Extending the Notebook

### Add Custom Helper Functions
```python
def my_custom_analysis(schema_name: str, table_name: str):
    """Your custom analysis logic."""
    full_name = f"{catalog}.{schema_name}.{table_name}"
    df = spark.table(full_name)
    
    # Your analysis here
    result = df.groupBy("key_column").agg(...)
    
    display(result)
```

### Add Visualization
```python
import matplotlib.pyplot as plt
import pandas as pd

# Convert to Pandas for plotting
pdf = df.limit(1000).toPandas()
pdf.plot(kind='bar', x='category', y='sales')
plt.show()
```

## Best Practices

1. **Start Small**: Use `.limit()` when exploring large tables
2. **Document Findings**: Add markdown cells to document insights
3. **Save Useful Queries**: Copy useful SQL to documentation
4. **Check Permissions**: Ensure you have read access to all layers
5. **Clean Up**: Comment out expensive operations after running

## Troubleshooting

### "Table not found"
- Check that schema names match your environment (dev vs prod)
- Verify the table exists with `SHOW TABLES IN catalog.schema`

### "Permission denied"
- Ensure you have SELECT permission on the catalog/schema
- Contact admin for access

### Slow queries
- Use `.limit()` for initial exploration
- Filter early in the query chain
- Check query plan with `.explain()`

## Related Documentation

- [Silver Layer README](../../docs/silver/SILVER_LAYER_README.md)
- [Gold Layer README](../../docs/gold/GOLD_LAYER_README.md)
- [Data Quality Guide](../../docs/silver/DQ_QUICKREF.md)
- [Metric Views Guide](../../docs/gold/METRIC_VIEWS_QUICKREF.md)

