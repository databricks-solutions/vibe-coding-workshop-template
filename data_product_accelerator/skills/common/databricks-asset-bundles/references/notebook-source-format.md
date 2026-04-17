# Databricks Notebook Source Format

Python files executed via `notebook_task` in Databricks Asset Bundles MUST use the Databricks notebook source format. Without it, cell boundaries are not recognized and all code runs as a single block.

## Cell Separators

Every `.py` file run by `notebook_task` must follow this structure:

```python
# Databricks notebook source

# COMMAND ----------

# First code cell
catalog = dbutils.widgets.get("catalog")
print(f"Using catalog: {catalog}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Second Cell — Markdown
# MAGIC This cell renders as Markdown in the Databricks notebook UI.

# COMMAND ----------

# Third code cell
spark.sql(f"USE CATALOG {catalog}")
```

### Rules

| Element | Format | Notes |
|---------|--------|-------|
| File header | `# Databricks notebook source` | MUST be the very first line of the file |
| Cell separator | `# COMMAND ----------` | Exactly 10 dashes. Between every cell |
| Markdown cell | `# MAGIC %md` prefix on each line | Renders as Markdown in UI |
| SQL cell | `# MAGIC %sql` prefix on each line | Executes as SQL in Python notebook |
| Run directive | `# MAGIC %run ./relative_path` | Executes another notebook |

## Complete Notebook Example

```python
# Databricks notebook source

# COMMAND ----------

# MAGIC %md
# MAGIC # Gold Layer Setup
# MAGIC Creates gold-layer tables and applies constraints.

# COMMAND ----------

def get_parameters():
    """Get job parameters from dbutils widgets."""
    catalog = dbutils.widgets.get("catalog")
    gold_schema = dbutils.widgets.get("gold_schema")
    print(f"Catalog: {catalog}, Schema: {gold_schema}")
    return catalog, gold_schema

# COMMAND ----------

catalog, gold_schema = get_parameters()

# COMMAND ----------

spark.sql(f"""
    CREATE TABLE IF NOT EXISTS {catalog}.{gold_schema}.dim_customer (
        customer_sk BIGINT GENERATED ALWAYS AS IDENTITY,
        customer_id STRING NOT NULL,
        customer_name STRING
    )
""")
print("✓ dim_customer created")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Validation
# MAGIC Verify tables were created successfully.

# COMMAND ----------

tables = spark.sql(f"SHOW TABLES IN {catalog}.{gold_schema}").collect()
print(f"✓ {len(tables)} tables in {catalog}.{gold_schema}")
```

## Gotchas

- **Missing `# Databricks notebook source` header** → File is treated as a plain Python script, not a notebook. `dbutils` may not be available and cell separators are ignored.
- **Wrong number of dashes** → `# COMMAND --------` (8 dashes) or `# COMMAND ------------` (12 dashes) will NOT be recognized as cell boundaries. Must be exactly 10: `----------`.
- **Missing cell separator** → All code between two separators runs as one cell. If separators are missing entirely, the entire file is one cell — no incremental output in the UI.
- **`# MAGIC` is literal** → It's not a comment convention; it's a Databricks-specific directive. The `# MAGIC ` prefix (with trailing space) is stripped at execution time.
- **No blank line between separator and code** → While technically valid, adding a blank line after `# COMMAND ----------` improves readability. The separator itself must be on its own line.

## When to Use Notebook Source Format vs Plain Python

| Execution Context | Format Required |
|---|---|
| `notebook_task` in DABs | Databricks notebook source (this format) |
| Interactive Databricks notebook | Databricks notebook source (auto-created by UI) |
| `python_task` / `spark_python_task` | Plain Python (`.py` with `argparse`) |
| Local development / unit tests | Plain Python |

**Rule:** If your `.py` file will be referenced by `notebook_task.notebook_path`, it MUST use this format.
