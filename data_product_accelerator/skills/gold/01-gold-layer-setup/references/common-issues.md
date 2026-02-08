# Common Issues & Solutions

Troubleshooting guide for Gold layer implementation errors.

## Issue 1: YAML Files Not Found

**Error:** `FileNotFoundError: YAML directory not found. Ensure YAMLs are synced in databricks.yml`

**Cause:** The `databricks.yml` sync section does not include the YAML directory, so files are not deployed to the workspace.

**Solution:** Add YAMLs to sync in `databricks.yml`:

```yaml
sync:
  include:
    - gold_layer_design/yaml/**/*.yaml
```

**Skill Reference:** `databricks-asset-bundles`

---

## Issue 2: PyYAML Not Available

**Error:** `ModuleNotFoundError: No module named 'yaml'`

**Cause:** PyYAML is not included in the serverless environment dependencies.

**Solution:** Add dependency to the job environment:

```yaml
environments:
  - environment_key: default
    spec:
      environment_version: "4"
      dependencies:
        - "pyyaml>=6.0"
```

**Skill Reference:** `databricks-asset-bundles`

---

## Issue 3: Duplicate Key MERGE Error

**Error:** `[DELTA_MULTIPLE_SOURCE_ROW_MATCHING_TARGET_ROW_IN_MERGE] Cannot perform Merge as multiple source rows matched and attempted to modify the same target row`

**Cause:** Silver table contains duplicate business keys (from incremental DLT streaming, CDC, SCD Type 2 tracking, or test data generation).

**Solution:** Add deduplication before MERGE:

```python
silver_raw = spark.table(silver_table)
original_count = silver_raw.count()

silver_df = (
    silver_raw
    .orderBy(col("processed_timestamp").desc())  # Latest first
    .dropDuplicates(["business_key"])  # Keep latest per key
)

dedupe_count = silver_df.count()
print(f"  Deduplicated: {original_count} → {dedupe_count} records")
```

**Critical:** The deduplication key MUST match the MERGE condition key.

**Skill Reference:** `gold-delta-merge-deduplication`

---

## Issue 4: Column Name Mismatch

**Error:** `[UNRESOLVED_COLUMN] A column with name 'X' cannot be resolved`

**Cause:** Silver table uses different column names than Gold DDL (e.g., Silver has `company_rcn`, Gold expects `company_retail_control_number`).

**Solution:** Add explicit column mapping:

```python
updates_df = (
    silver_df
    .withColumn("gold_column_name", col("silver_column_name"))
    .select("gold_column_name", ...)  # Only Gold columns
)
```

**Prevention:** Always run schema validation before merge:

```python
validate_merge_schema(spark, updates_df, catalog, gold_schema, table_name)
```

**Skill Reference:** `gold-layer-schema-validation`

---

## Issue 5: Grain Duplicates

**Error:** Multiple rows per grain combination (grain validation fails)

**Cause:** Aggregation does not match the PRIMARY KEY columns, or `.groupBy()` is missing columns.

**Solution:** Ensure aggregation matches PRIMARY KEY:

```python
# If PK is (store_number, upc_code, transaction_date)
daily_sales = transactions.groupBy(
    "store_number", "upc_code", "transaction_date"
).agg(...)
```

**Validation:**

```python
distinct_count = df.select(*grain_columns).distinct().count()
total_count = df.count()
assert distinct_count == total_count, "Grain validation failed!"
```

**Skill Reference:** `fact-table-grain-validation`

---

## Issue 6: Variable Shadows PySpark Function

**Error:** `'int' object is not callable` when calling `count()`, `sum()`, etc.

**Cause:** A local variable is named the same as an imported PySpark function, shadowing the function:

```python
from pyspark.sql.functions import count

# Later in the code...
count = updates_df.count()  # ❌ Shadows imported 'count' function!
df.agg(count("*"))          # Error: 'int' object is not callable
```

**Solution:** Use descriptive variable names:

```python
record_count = updates_df.count()  # ✅ No conflict
df.agg(count("*"))                 # ✅ Uses imported function
```

**Common variables to avoid:**
- `count` → use `record_count`, `row_count`
- `sum` → use `total`, `sum_value`
- `min` → use `min_value`
- `max` → use `max_value`

**Skill Reference:** `gold-layer-merge-patterns`

---

## Issue 7: FK Constraint Fails

**Error:** `Table/column 'X' not found` when applying FK constraint

**Cause:** The referenced table's PK does not exist yet because FK constraints were applied inline during CREATE TABLE or before all tables were created.

**Solution:** Run FK constraints in a SEPARATE script that executes AFTER all tables and PKs are created:

```yaml
# In gold_setup_job.yml
tasks:
  - task_key: setup_all_tables
    # ... creates all tables with PKs

  - task_key: add_fk_constraints
    depends_on:
      - task_key: setup_all_tables  # ← Runs AFTER setup
    # ... applies FK constraints
```

**Skill Reference:** `unity-catalog-constraints`

---

## Issue 8: DATE_TRUNC Schema Merge Error

**Error:** Schema mismatch during merge — `DATE_TRUNC` returns TIMESTAMP but Gold DDL expects DATE.

**Cause:** `DATE_TRUNC('day', timestamp_col)` returns a TIMESTAMP in Spark, not a DATE.

**Solution:** Always CAST the result to DATE:

```python
.withColumn("transaction_date",
           col("transaction_timestamp").cast("date"))

# Or if using DATE_TRUNC:
.withColumn("transaction_date",
           date_trunc("day", col("transaction_timestamp")).cast("date"))
```

---

## Quick Diagnosis Flowchart

```
Error during Gold layer?
├── FileNotFoundError → Check databricks.yml sync
├── ModuleNotFoundError → Check job environment dependencies
├── DELTA_MULTIPLE_SOURCE_ROW → Add deduplication before merge
├── UNRESOLVED_COLUMN → Check column mapping (Silver → Gold)
├── Grain validation failed → Check groupBy matches PK
├── 'int' object not callable → Rename shadowed variable
├── FK constraint failed → Check depends_on in job YAML
└── Schema mismatch → Cast DATE_TRUNC to DATE
```
