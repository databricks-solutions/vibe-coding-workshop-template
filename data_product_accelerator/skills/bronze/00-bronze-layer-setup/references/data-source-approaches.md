# Data Source Approaches

Three approaches for populating Bronze layer tables. Choose based on your use case.

---

## Approach A: Generate Fake Data with Faker (Recommended)

**Best for:** Demos, testing, rapid prototyping, learning

**Advantages:**
- No external dependencies
- Reproducible (seeded random data)
- Configurable record counts
- Realistic data patterns
- PII-safe (no real data)

**Steps:**
1. Define table schemas in `setup_tables.py`
2. Create Faker generation functions (use the [`faker-data-generation`](../../faker-data-generation/SKILL.md) skill for patterns)
3. Generate dimensions first (for FK integrity)
4. Generate facts with references to dimensions

### Dimension Generation Pattern

Dimensions are referenced by facts, so must be generated first. Use locale-specific Faker for realistic data.

```python
# Databricks notebook source
# generate_dimensions.py

from pyspark.sql import SparkSession
from faker import Faker
import random
from datetime import datetime, timedelta

# Initialize Faker with seed for reproducibility
fake = Faker()
Faker.seed(42)
random.seed(42)


def generate_dimension_data(
    spark: SparkSession,
    catalog: str,
    schema: str,
    table_name: str,
    generate_record_fn,
    num_records: int = 100
):
    """
    Generic dimension data generator.

    Args:
        spark: SparkSession
        catalog: Unity Catalog name
        schema: Schema name
        table_name: Target table name (e.g., bronze_store_dim)
        generate_record_fn: Function that returns a dict for one record
        num_records: Number of records to generate
    """
    print(f"\nGenerating {num_records} records for {table_name}...")

    data = [generate_record_fn(i) for i in range(num_records)]

    df = spark.createDataFrame(data)
    full_table = f"{catalog}.{schema}.{table_name}"
    df.write.mode("overwrite").saveAsTable(full_table)

    print(f"Generated {num_records} records in {full_table}")
    return df
```

### Date Dimension Pattern (SQL-based)

Date dimensions should be generated via SQL SEQUENCE, not Faker:

```sql
INSERT OVERWRITE {catalog}.{schema}.bronze_date_dim
SELECT
    date,
    YEAR(date) as year,
    QUARTER(date) as quarter,
    MONTH(date) as month,
    DATE_FORMAT(date, 'MMMM') as month_name,
    WEEKOFYEAR(date) as week_of_year,
    DAYOFWEEK(date) as day_of_week,
    DATE_FORMAT(date, 'EEEE') as day_of_week_name,
    DAY(date) as day_of_month,
    DAYOFYEAR(date) as day_of_year,
    CASE WHEN DAYOFWEEK(date) IN (1, 7) THEN true ELSE false END as is_weekend,
    false as is_holiday,
    CURRENT_TIMESTAMP() as ingestion_timestamp,
    'generated' as source_file
FROM (
    SELECT EXPLODE(
        SEQUENCE(
            TO_DATE('{start_date}'),
            TO_DATE('{end_date}'),
            INTERVAL 1 DAY
        )
    ) as date
)
```

### Fact Generation Pattern

Facts reference dimensions. Load dimension keys first to ensure FK integrity:

```python
def generate_fact_data(
    spark: SparkSession,
    catalog: str,
    schema: str,
    table_name: str,
    dimension_keys: dict,
    generate_record_fn,
    num_records: int = 10000
):
    """
    Generic fact data generator with FK integrity.

    Args:
        dimension_keys: Dict of {dim_name: [key_values]} loaded from dimension tables
        generate_record_fn: Function(i, dimension_keys) -> dict
    """
    print(f"\nGenerating {num_records} records for {table_name}...")

    # Load dimension keys for FK integrity
    for dim_name, key_col in dimension_keys.items():
        dim_table = f"{catalog}.{schema}.{dim_name}"
        keys = [row[key_col] for row in spark.table(dim_table).select(key_col).collect()]
        dimension_keys[dim_name] = keys
        print(f"  Loaded {len(keys)} keys from {dim_name}.{key_col}")

    data = [generate_record_fn(i, dimension_keys) for i in range(num_records)]

    df = spark.createDataFrame(data)
    full_table = f"{catalog}.{schema}.{table_name}"
    df.write.mode("overwrite").saveAsTable(full_table)

    print(f"Generated {num_records} records in {full_table}")
    return df
```

### Faker Corruption (for DQ Testing)

For configurable data corruption to test Silver layer DLT expectations, use the [`faker-data-generation`](../../faker-data-generation/SKILL.md) skill. It covers:

- Standard function signatures with `corruption_rate` parameter
- Corruption type categories (missing fields, invalid formats, out-of-range, etc.)
- DQ expectation mapping (`# Will fail: <expectation_name>`)
- Testing scenarios (dev: 10%, staging: 5%, production: 0%)

---

## Approach B: Use Existing Bronze Tables

**Best for:** Testing transformations on real data structures, reusing existing demos

**Advantages:**
- Real data characteristics
- No generation time
- Test on actual schema

**Steps:**
1. Identify source catalog/schema
2. Create tables pointing to existing data (or copy)
3. Add governance metadata
4. Enable Change Data Feed

### Copy Pattern

```python
from pyspark.sql.functions import current_timestamp, lit

def copy_table(spark, source_table, target_table):
    """Copy a table and add ingestion metadata."""
    source_df = spark.table(source_table)

    if "ingestion_timestamp" not in source_df.columns:
        source_df = source_df.withColumn("ingestion_timestamp", current_timestamp())

    if "source_file" not in source_df.columns:
        source_df = source_df.withColumn("source_file", lit(f"copied_from_{source_table}"))

    source_df.write.mode("overwrite").saveAsTable(target_table)
```

### Add Governance Metadata After Copy

```sql
ALTER TABLE {catalog}.{schema}.{table}
SET TBLPROPERTIES (
    'delta.enableChangeDataFeed' = 'true',
    'layer' = 'bronze',
    'source_system' = 'copied_from_{source}',
    'domain' = '{domain}',
    'data_purpose' = 'testing_demo',
    'is_production' = 'false'
);
```

---

## Approach C: Copy from External Source

**Best for:** Loading sample data from CSV, external databases, other workspaces

**Advantages:**
- Use real sample datasets
- One-time copy operation
- Can sanitize/transform on copy

**Steps:**
1. Define connection to source
2. Read data with appropriate connector
3. Write to Bronze tables
4. Add governance metadata

### CSV Pattern

```python
df = spark.read.option("header", True).option("inferSchema", True).csv(path)
df.write.mode("overwrite").saveAsTable(f"{catalog}.{schema}.bronze_{entity}")
```

### External Database Pattern

```python
df = spark.read.format("jdbc") \
    .option("url", jdbc_url) \
    .option("dbtable", source_table) \
    .option("user", username) \
    .option("password", password) \
    .load()

df.write.mode("overwrite").saveAsTable(f"{catalog}.{schema}.bronze_{entity}")
```

### Post-Copy: Always Add Metadata

After any copy operation, apply the standard Bronze TBLPROPERTIES and enable Change Data Feed. Use the [`databricks-table-properties`](../../../common/databricks-table-properties/SKILL.md) skill for the full property template.

---

## Approach Comparison

| Feature | Faker | Existing | External |
|---|---|---|---|
| Setup time | 30-45 min | 15-20 min | 20-30 min |
| Realistic data | High | Highest | High |
| PII risk | None | Depends | Depends |
| Reproducible | Yes (seeded) | Yes | Depends |
| FK integrity | Guaranteed | Depends | Manual |
| Corruption testing | Built-in | No | No |
| External deps | Faker library | Source access | Connection |
