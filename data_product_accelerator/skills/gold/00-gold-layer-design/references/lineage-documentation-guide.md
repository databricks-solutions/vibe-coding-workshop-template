# Lineage Documentation Guide

Extracted from `context/prompts/03a-gold-layer-design-prompt.md` Steps 4-5 and 9.

---

## Why Lineage Documentation Matters

**Problem:** Schema mismatches cause 33% of Gold layer bugs during implementation.
- Column names differ between Bronze, Silver, and Gold
- Transformations are implicit (not documented)
- Manual column mapping is error-prone

**Solution:** Explicit lineage documentation in YAML for every column.

---

## Standard Transformation Types

Use these standard codes in the `transformation` field of YAML lineage:

| Type | Description | Example | PySpark Implementation |
|---|---|---|---|
| `DIRECT_COPY` | No transformation | store_number | `col("store_number")` |
| `RENAME` | Column renamed, no value change | company_rcn → company_retail_control_number | `.withColumn("company_retail_control_number", col("company_rcn"))` |
| `CAST` | Data type conversion | STRING → INT | `.withColumn("column", col("column").cast("int"))` |
| `AGGREGATE_SUM` | Simple SUM | SUM(revenue) | `spark_sum("revenue")` |
| `AGGREGATE_SUM_CONDITIONAL` | Conditional SUM | SUM(CASE WHEN qty > 0 ...) | `spark_sum(when(col("qty") > 0, col("revenue")).otherwise(0))` |
| `AGGREGATE_COUNT` | COUNT | COUNT(*) | `count("*")` |
| `AGGREGATE_AVG` | AVG | AVG(price) | `avg("price")` |
| `DERIVED_CALCULATION` | From other Gold columns | avg = total / count | Calculated within Gold MERGE |
| `DERIVED_CONDITIONAL` | CASE/when logic | CASE WHEN qty > 0 ... | `when(col("qty") > 0, "Sale").otherwise("Return")` |
| `HASH_MD5` | MD5 surrogate key | MD5(id \|\| timestamp) | `md5(concat_ws("\|\|", col("id"), col("ts")))` |
| `HASH_SHA256` | SHA256 hash | SHA256(keys) | `sha2(concat_ws("\|\|", col("k1"), col("k2")), 256)` |
| `COALESCE` | Null handling | COALESCE(discount, 0) | `coalesce(col("discount"), lit(0))` |
| `DATE_TRUNC` | Date truncation | DATE_TRUNC('day', ts) | `date_trunc("day", col("ts")).cast("date")` |
| `GENERATED` | Not from source | CURRENT_TIMESTAMP() | `current_timestamp()` |
| `LOOKUP` | From dimension join | Get city from dim_store | Join in MERGE script |

---

## YAML Lineage Schema

Every column MUST have a `lineage:` section:

```yaml
columns:
  - name: {gold_column_name}
    type: {DATA_TYPE}
    nullable: {true|false}
    description: >
      {Dual-purpose description}
    lineage:
      bronze_table: {bronze_table_name}       # or N/A if generated
      bronze_column: {bronze_column_name}      # or N/A
      silver_table: {silver_table_name}        # or N/A
      silver_column: {silver_column_name}      # or N/A
      transformation: "{TRANSFORMATION_TYPE}"  # from standard list
      transformation_logic: "{PySpark/SQL}"    # executable expression
      notes: "{special considerations}"        # optional
```

**For aggregations, ALSO add:**
```yaml
    lineage:
      # ... standard fields ...
      aggregation_logic: "{complete aggregation expression}"
      groupby_columns: ['col1', 'col2', 'col3']
      aggregation_level: "daily"
```

**For derived columns, ALSO add:**
```yaml
    lineage:
      # ... standard fields (bronze/silver = N/A) ...
      depends_on: ['gold_column_1', 'gold_column_2']
```

---

## Column Lineage CSV (MANDATORY)

### File: `gold_layer_design/COLUMN_LINEAGE.csv`

**Required Columns:**

```csv
domain,gold_table,gold_column,data_type,nullable,bronze_table,bronze_column,silver_table,silver_column,transformation_type,transformation_logic
```

| Column | Type | Description |
|--------|------|-------------|
| `domain` | STRING | Business domain (e.g., `booking`, `revenue`) |
| `gold_table` | STRING | Gold layer table name |
| `gold_column` | STRING | Gold layer column name |
| `data_type` | STRING | Data type (e.g., `STRING`, `DECIMAL(18,2)`) |
| `nullable` | BOOLEAN | `true` or `false` |
| `bronze_table` | STRING | Source Bronze table (or `N/A`) |
| `bronze_column` | STRING | Source Bronze column(s) |
| `silver_table` | STRING | Source Silver table (or `N/A`) |
| `silver_column` | STRING | Source Silver column(s) |
| `transformation_type` | STRING | Standard transformation type |
| `transformation_logic` | STRING | PySpark/SQL expression |

### Example CSV

```csv
domain,gold_table,gold_column,data_type,nullable,bronze_table,bronze_column,silver_table,silver_column,transformation_type,transformation_logic
location,dim_store,store_key,STRING,false,bronze_store_dim,"store_id,processed_timestamp",silver_store_dim,"store_id,processed_timestamp",HASH_MD5,"md5(concat_ws('||',col('store_id'),col('processed_timestamp')))"
location,dim_store,store_number,STRING,false,bronze_store_dim,store_number,silver_store_dim,store_number,DIRECT_COPY,"col('store_number')"
location,dim_store,effective_from,TIMESTAMP,false,N/A,N/A,N/A,N/A,GENERATED,"current_timestamp()"
sales,fact_sales_daily,gross_revenue,DECIMAL(18.2),true,bronze_transactions,final_sales_price,silver_transactions,final_sales_price,AGGREGATE_SUM_CONDITIONAL,"spark_sum(when(col('quantity_sold')>0,col('final_sales_price')).otherwise(0))"
```

---

## Column Lineage Markdown (Human-Readable)

### File: `gold_layer_design/COLUMN_LINEAGE.md`

**Template per table:**

```markdown
## Table: {table_name}

**Grain:** {grain description}
**Bronze Source:** {bronze_table}
**Silver Source:** {silver_table}
**Gold Target:** {gold_table}

### Column Lineage

| Gold Column | Type | Bronze Source | Silver Source | Transformation | Logic | Notes |
|---|---|---|---|---|---|---|
| store_key | STRING | store_id, processed_timestamp | store_id, processed_timestamp | HASH_MD5 | `md5(...)` | Surrogate key |
| store_number | STRING | store_number | store_number | DIRECT_COPY | `col('store_number')` | Business key |

### Transformation Summary

**Aggregation Grain:** GROUP BY (col1, col2, col3)

**Silver Query Pattern:**
(PySpark code showing the aggregation)

**Column Mapping for MERGE:**
(Mapping notes for merge script implementation)
```

---

## Consistency Requirements

The COLUMN_LINEAGE.csv MUST be consistent with:

1. **YAML Schema Files** - Every column in YAML must appear in CSV
2. **ERD Diagrams** - Every column in ERD must appear in CSV
3. **COLUMN_LINEAGE.md** - CSV and MD versions must match

Use `scripts/generate_lineage_csv.py` to generate and validate.

---

## Using Lineage to Prevent Common Errors

### Error 1: Column doesn't exist in Silver
```python
# Lineage reveals: company_rcn → company_retail_control_number (RENAME)
# Fix: .withColumn("company_retail_control_number", col("company_rcn"))
```

### Error 2: Wrong transformation logic
```python
# Lineage reveals: gross_revenue uses AGGREGATE_SUM_CONDITIONAL
# Fix: spark_sum(when(col("quantity_sold") > 0, col("final_sales_price")).otherwise(0))
```

### Error 3: Missing CAST
```python
# Lineage reveals: check_in_date uses DATE_TRUNC with .cast("date")
# Fix: date_trunc("day", col("check_in_timestamp")).cast("date")
```

---

## Lineage Accuracy: Silver Column Verification

The `silver_table` and `silver_column` values in YAML lineage are assumptions made during design based on Bronze schema naming conventions. These assumptions may be wrong if the Silver layer renames or transforms columns.

**Rule:** `silver_column` values must match **actual Silver table column names**, not Bronze column names. If Silver renames `company_rcn` to `company_retail_control_number`, the YAML lineage must reference the Silver name.

**Verification:** After the Silver layer is deployed, run the Silver cross-reference script from `00-gold-layer-design/SKILL.md` or the full Phase 0 contract validation from `01-gold-layer-setup/references/design-to-pipeline-bridge.md`.

**Common Mistakes:**
- Copying Bronze column name into `silver_column` without checking if Silver renamed it
- Assuming Silver DLT passes all columns through unchanged (Silver may add derived columns, rename for clarity, or change types)
- Not updating YAML lineage after Silver schema changes

**Prevention:** Always verify `silver_column` values against `DESCRIBE {catalog}.{silver_schema}.{silver_table}` before finalizing YAML designs.
