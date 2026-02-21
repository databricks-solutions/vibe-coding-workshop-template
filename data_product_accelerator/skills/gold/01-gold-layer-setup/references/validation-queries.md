# Validation Queries

Complete SQL queries for post-deployment Gold layer validation.

## Schema Validation

### Check Table Creation

```sql
-- List all Gold tables
USE CATALOG {catalog};
SHOW TABLES IN {gold_schema};
```

### Verify PRIMARY KEY Constraints

```sql
-- Check DDL includes PK constraint
SHOW CREATE TABLE {catalog}.{gold_schema}.dim_store;
```

### Check Column Definitions Match YAML

```sql
-- Verify columns, types, and descriptions
DESCRIBE TABLE EXTENDED {catalog}.{gold_schema}.dim_store;
```

### Check Table Properties

```sql
-- Verify TBLPROPERTIES (CDF, layer, domain, etc.)
SHOW TBLPROPERTIES {catalog}.{gold_schema}.dim_store;
```

## Grain Validation

### Verify Fact Table Grain (should be equal)

```sql
SELECT
  COUNT(*) as total_records,
  COUNT(DISTINCT CONCAT(store_number, '|', upc_code, '|', transaction_date))
    as unique_combinations
FROM {catalog}.{gold_schema}.fact_sales_daily;
```

### Find Duplicate Grain Rows (should return 0)

```sql
SELECT
  store_number, upc_code, transaction_date, COUNT(*) as dup_count
FROM {catalog}.{gold_schema}.fact_sales_daily
GROUP BY store_number, upc_code, transaction_date
HAVING COUNT(*) > 1;
```

### Generic Grain Validation Template

```sql
-- Replace {grain_columns} with actual PK columns
SELECT
  COUNT(*) as total_records,
  COUNT(DISTINCT CONCAT_WS('|', {grain_columns})) as unique_combinations,
  COUNT(*) - COUNT(DISTINCT CONCAT_WS('|', {grain_columns})) as duplicates
FROM {catalog}.{gold_schema}.{table_name};
```

## FK Integrity

### Verify No Orphaned Records (should return 0)

```sql
SELECT COUNT(*) as orphaned_sales
FROM {catalog}.{gold_schema}.fact_sales_daily f
LEFT JOIN {catalog}.{gold_schema}.dim_store d
  ON f.store_number = d.store_number
  AND d.is_current = true
WHERE d.store_number IS NULL;
```

### Generic FK Integrity Template

```sql
-- Replace with actual table/column names
SELECT COUNT(*) as orphaned_records
FROM {catalog}.{gold_schema}.{fact_table} f
LEFT JOIN {catalog}.{gold_schema}.{dim_table} d
  ON f.{fk_column} = d.{pk_column}
WHERE d.{pk_column} IS NULL;
```

## SCD Type 2 Validation

### Verify Only One Current Version Per Business Key

```sql
-- Should return 0 rows (no business keys with multiple current versions)
SELECT store_number, COUNT(*) as current_versions
FROM {catalog}.{gold_schema}.dim_store
WHERE is_current = true
GROUP BY store_number
HAVING COUNT(*) > 1;
```

### Check for Overlapping Effective Dates

```sql
-- Should return 0 rows (no overlapping date ranges)
SELECT *
FROM {catalog}.{gold_schema}.dim_store a
JOIN {catalog}.{gold_schema}.dim_store b
  ON a.store_number = b.store_number
  AND a.store_key != b.store_key
WHERE a.effective_from < COALESCE(b.effective_to, '9999-12-31')
  AND COALESCE(a.effective_to, '9999-12-31') > b.effective_from;
```

## Data Quality Checks

### Record Count Sanity

```sql
-- Compare Silver vs Gold record counts
SELECT
  'silver' as layer, COUNT(*) as records
FROM {catalog}.{silver_schema}.silver_store_dim
UNION ALL
SELECT
  'gold' as layer, COUNT(*) as records
FROM {catalog}.{gold_schema}.dim_store;
```

### NULL Check on Required Columns

```sql
-- PK columns should never be NULL
SELECT
  COUNT(*) as total,
  SUM(CASE WHEN store_key IS NULL THEN 1 ELSE 0 END) as null_store_key,
  SUM(CASE WHEN store_number IS NULL THEN 1 ELSE 0 END) as null_store_number
FROM {catalog}.{gold_schema}.dim_store;
```

### Audit Timestamp Verification

```sql
-- All records should have timestamps
SELECT
  COUNT(*) as total,
  SUM(CASE WHEN record_created_timestamp IS NULL THEN 1 ELSE 0 END) as null_created,
  SUM(CASE WHEN record_updated_timestamp IS NULL THEN 1 ELSE 0 END) as null_updated
FROM {catalog}.{gold_schema}.dim_store;
```

## Validation Summary Query

Run all validations and summarize:

```sql
SELECT 'Grain Check' as validation, 
       CASE WHEN COUNT(*) = COUNT(DISTINCT CONCAT_WS('|', {grain_cols}))
            THEN 'PASS' ELSE 'FAIL' END as result
FROM {catalog}.{gold_schema}.{fact_table}

UNION ALL

SELECT 'FK Integrity' as validation,
       CASE WHEN orphan_count = 0 THEN 'PASS' ELSE 'FAIL' END as result
FROM (
  SELECT COUNT(*) as orphan_count
  FROM {catalog}.{gold_schema}.{fact_table} f
  LEFT JOIN {catalog}.{gold_schema}.{dim_table} d
    ON f.{fk_col} = d.{pk_col}
  WHERE d.{pk_col} IS NULL
)

UNION ALL

SELECT 'SCD2 Current' as validation,
       CASE WHEN multi_current = 0 THEN 'PASS' ELSE 'FAIL' END as result
FROM (
  SELECT COUNT(*) as multi_current
  FROM (
    SELECT {business_key}, COUNT(*) as cnt
    FROM {catalog}.{gold_schema}.{dim_table}
    WHERE is_current = true
    GROUP BY {business_key}
    HAVING COUNT(*) > 1
  )
);
```

---

## Accumulating Snapshot Validation

```sql
-- Validate milestone monotonicity (earlier milestones should precede later ones)
SELECT 'Milestone Order' as validation,
       CASE WHEN violations = 0 THEN 'PASS' ELSE 'FAIL' END as result,
       violations as detail
FROM (
  SELECT COUNT(*) as violations
  FROM {catalog}.{gold_schema}.{fact_table}
  WHERE {earlier_milestone} IS NOT NULL
    AND {later_milestone} IS NOT NULL
    AND {earlier_milestone} > {later_milestone}
);

-- Validate lag/duration columns are consistent with milestones
SELECT 'Lag Consistency' as validation,
       CASE WHEN mismatches = 0 THEN 'PASS' ELSE 'FAIL' END as result
FROM (
  SELECT COUNT(*) as mismatches
  FROM {catalog}.{gold_schema}.{fact_table}
  WHERE {from_milestone} IS NOT NULL
    AND {to_milestone} IS NOT NULL
    AND {lag_column} != DATEDIFF({to_milestone}, {from_milestone})
);
```

---

## Factless Fact Validation

```sql
-- Validate no measure columns contain non-zero values
-- (factless facts should only have FK keys + audit timestamps)
SELECT 'No Measures' as validation,
       CASE WHEN measure_count = 0 THEN 'PASS' ELSE 'FAIL' END as result
FROM (
  SELECT COUNT(*) as measure_count
  FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_CATALOG = '{catalog}'
    AND TABLE_SCHEMA = '{gold_schema}'
    AND TABLE_NAME = '{fact_table}'
    AND DATA_TYPE IN ('DECIMAL', 'DOUBLE', 'FLOAT', 'INT', 'BIGINT')
    AND COLUMN_NAME NOT LIKE '%_key'
    AND COLUMN_NAME NOT LIKE '%_id'
);

-- Validate grain: no duplicate FK combinations
SELECT 'Factless Grain' as validation,
       CASE WHEN dups = 0 THEN 'PASS' ELSE 'FAIL' END as result
FROM (
  SELECT COUNT(*) as dups
  FROM (
    SELECT {pk_columns}, COUNT(*) as cnt
    FROM {catalog}.{gold_schema}.{fact_table}
    GROUP BY {pk_columns}
    HAVING COUNT(*) > 1
  )
);
```

---

## Unknown Member Row Validation

```sql
-- Verify unknown member exists in each dimension
SELECT 'Unknown Member' as validation,
       table_name,
       CASE WHEN cnt > 0 THEN 'PASS' ELSE 'FAIL' END as result
FROM (
  SELECT '{dim_table}' as table_name,
         COUNT(*) as cnt
  FROM {catalog}.{gold_schema}.{dim_table}
  WHERE {pk_column} = '-1'
);

-- Verify unknown member has no NULLs in NOT NULL columns
SELECT 'Unknown No Nulls' as validation,
       CASE WHEN null_count = 0 THEN 'PASS' ELSE 'FAIL' END as result
FROM (
  SELECT COUNT(*) as null_count
  FROM {catalog}.{gold_schema}.{dim_table}
  WHERE {pk_column} = '-1'
    AND ({business_key} IS NULL OR {required_col} IS NULL)
);
```

---

## Role-Playing View Validation

```sql
-- Verify role-playing views exist and reference the physical table
SHOW VIEWS IN {catalog}.{gold_schema} LIKE 'dim_%_date';

-- Verify view returns same row count as physical table
SELECT 'View Row Count' as validation,
       CASE WHEN view_cnt = phys_cnt THEN 'PASS' ELSE 'FAIL' END as result
FROM (
  SELECT 
    (SELECT COUNT(*) FROM {catalog}.{gold_schema}.{view_name}) as view_cnt,
    (SELECT COUNT(*) FROM {catalog}.{gold_schema}.{physical_table}) as phys_cnt
);
```
