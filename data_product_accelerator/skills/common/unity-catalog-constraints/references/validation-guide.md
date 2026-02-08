# Unity Catalog Constraint Validation Guide

## NOT NULL Requirement for Primary Keys

### Error Message

```
Error: Cannot create the primary key because its child column(s) is nullable.
```

### Root Cause

**All surrogate key columns used in PRIMARY KEY constraints MUST be NOT NULL.**

Unity Catalog requires that all columns participating in a PRIMARY KEY constraint are explicitly defined as NOT NULL, even though the constraint itself is NOT ENFORCED.

### Solution

Ensure all PK columns are `NOT NULL`:

```sql
-- ❌ WRONG: Nullable surrogate key
CREATE TABLE dim_store (
    store_key STRING,  -- Missing NOT NULL
    ...
    CONSTRAINT pk_dim_store PRIMARY KEY (store_key) NOT ENFORCED
)

-- ✅ CORRECT: NOT NULL surrogate key
CREATE TABLE dim_store (
    store_key STRING NOT NULL,  -- Required for PK
    ...
    CONSTRAINT pk_dim_store PRIMARY KEY (store_key) NOT ENFORCED
)
```

### Validation Checklist

- [ ] All surrogate key columns are `NOT NULL`
- [ ] All columns in composite PKs are `NOT NULL`
- [ ] Date dimension keys are `NOT NULL`
- [ ] Fact table FK columns are `NOT NULL` (if used in composite PKs)

## Foreign Key Constraint Requirements

### Requirement: FKs Must Reference Primary Keys

**Foreign keys MUST reference PRIMARY KEY columns, even when NOT ENFORCED.**

- FKs can only reference PK columns (not any column)
- FKs must reference exact column(s) in PK definition
- This applies even to informational (NOT ENFORCED) constraints

### Error: FK References Non-PK Column

```
Error: Foreign key constraint references a non-primary key column.
```

**Solution:** Ensure FK references a column that is part of the referenced table's PRIMARY KEY.

```sql
-- ❌ WRONG: FK references non-PK column
ALTER TABLE fact_sales
    ADD CONSTRAINT fk_sales_store 
    FOREIGN KEY (store_number)  -- Business key, not PK
    REFERENCES dim_store(store_number) NOT ENFORCED

-- ✅ CORRECT: FK references PK column
ALTER TABLE fact_sales
    ADD CONSTRAINT fk_sales_store 
    FOREIGN KEY (store_key)  -- Surrogate key (PK)
    REFERENCES dim_store(store_key) NOT ENFORCED
```

## Pre-Deployment Validation Checklist

### Table Creation Phase

- [ ] All dimension tables define PRIMARY KEY inline in CREATE TABLE
- [ ] **NO** fact tables define FOREIGN KEY inline in CREATE TABLE
- [ ] Date columns use explicit `CAST(DATE_TRUNC(...) AS DATE)`
- [ ] All surrogate key columns are `NOT NULL`
- [ ] Reference dimension (dim_date) created before facts that reference it
- [ ] Business keys have UNIQUE constraints where applicable (SCD Type 1)
- [ ] SCD Type 2 dimensions have `is_current` flag

### Constraint Application Phase

- [ ] Separate `constraints.py` script applies ALL FKs via ALTER TABLE
- [ ] Constraint script runs AFTER all table creation tasks
- [ ] Primary keys applied to dimensions before foreign keys applied to facts
- [ ] Each FK references an existing PK column
- [ ] Constraint names follow naming conventions (e.g., `pk_dim_date`, `fk_sales_date`)
- [ ] All constraints include `NOT ENFORCED`

### Schema Validation

- [ ] All surrogate key columns are `NOT NULL`
- [ ] PKs defined on surrogate keys (proper dimensional modeling)
- [ ] FKs reference surrogate PK columns exactly
- [ ] Facts have surrogate FK columns (store_key, product_key, date_key)
- [ ] Business keys have UNIQUE constraints (where applicable)
- [ ] Composite PKs match table grain (e.g., store + product + date)

## Post-Deployment Validation

### Verify Constraints Exist

```sql
-- List all constraints in schema
SHOW CONSTRAINTS IN ${catalog}.${schema};

-- Verify specific constraint
DESCRIBE EXTENDED ${catalog}.${schema}.fact_sales;
-- Check "Constraints" section in output
```

### Verify PK/FK Relationships

```sql
-- Check that FK columns exist and are NOT NULL
DESCRIBE ${catalog}.${schema}.fact_sales;
-- Verify store_key, product_key, date_key are NOT NULL

-- Check that referenced PKs exist
DESCRIBE ${catalog}.${schema}.dim_store;
-- Verify store_key is PRIMARY KEY

-- Test join (should work if constraints correct)
SELECT COUNT(*)
FROM ${catalog}.${schema}.fact_sales f
JOIN ${catalog}.${schema}.dim_store d ON f.store_key = d.store_key;
```

## Common Error Patterns and Solutions

### Error 1: Nullable Primary Key Column

**Error:**
```
Cannot create the primary key because its child column(s) is nullable.
```

**Solution:**
```sql
-- Add NOT NULL to all PK columns
ALTER TABLE dim_store ALTER COLUMN store_key SET NOT NULL;
```

### Error 2: Foreign Key References Non-PK Column

**Error:**
```
Foreign key constraint references a non-primary key column.
```

**Solution:**
```sql
-- Ensure FK references PK column, not business key
-- Change FK to reference surrogate key (PK)
ALTER TABLE fact_sales
    DROP CONSTRAINT fk_sales_store;
    
ALTER TABLE fact_sales
    ADD CONSTRAINT fk_sales_store 
    FOREIGN KEY (store_key)  -- Surrogate key (PK)
    REFERENCES dim_store(store_key) NOT ENFORCED;
```

### Error 3: FK Constraint Fails During CREATE TABLE

**Error:**
```
Table or view not found: dim_store
```

**Solution:**
- Never define FK constraints inline in CREATE TABLE
- Create all tables first, then apply FKs via ALTER TABLE

### Error 4: DATE_TRUNC Type Mismatch

**Error:**
```
Cannot cast TIMESTAMP to DATE
```

**Solution:**
```python
# Always CAST DATE_TRUNC result to DATE
df = df.withColumn("month_start_date", 
    expr("CAST(DATE_TRUNC('MONTH', date) AS DATE)"))
```

### Error 5: Module Import in Notebook

**Error:**
```
ModuleNotFoundError: No module named 'constraints'
```

**Solution:**
- Inline helper functions in notebook, or
- Use pure Python files (not notebooks) for shared code
- Ensure Asset Bundle path setup for imports

### Error 6: Widget Parameter Name Mismatch

**Error:**
```
KeyError: 'catalog' not found in widgets
```

**Solution:**
- Ensure YAML parameters match `dbutils.widgets.get()` names exactly
- Use consistent naming: `catalog`, `schema`, `gold_schema`, etc.

## Production Deployment Checklist

### Before Deployment

- [ ] All tables have PRIMARY KEY constraints (dimensions and facts)
- [ ] All surrogate key columns are NOT NULL
- [ ] Constraint application script is idempotent (can run multiple times)
- [ ] Constraint script runs after all table creation tasks
- [ ] All FKs reference existing PK columns
- [ ] Date columns use explicit CAST(DATE_TRUNC(...) AS DATE)

### During Deployment

- [ ] Create dimension tables first (with PKs)
- [ ] Create fact tables second (with PKs, no FKs)
- [ ] Run constraint application script last
- [ ] Verify constraints applied successfully

### After Deployment

- [ ] Run `SHOW CONSTRAINTS` to verify all constraints exist
- [ ] Test joins between facts and dimensions
- [ ] Verify Unity Catalog lineage shows relationships
- [ ] Check BI tool can discover relationships

## Troubleshooting Guide

### Constraint Not Appearing in Unity Catalog

**Symptoms:** Constraint created successfully but not visible in UC UI.

**Check:**
1. Verify constraint exists: `SHOW CONSTRAINTS IN schema`
2. Check Unity Catalog permissions
3. Refresh Unity Catalog UI

### Join Performance Not Improving

**Symptoms:** PK/FK constraints exist but query optimizer not using them.

**Check:**
1. Verify constraints are NOT ENFORCED (informational)
2. Check that constraints are properly defined
3. Verify column names match exactly
4. Check query plan: `EXPLAIN SELECT ...`

### BI Tool Not Discovering Relationships

**Symptoms:** Tableau/Power BI not showing relationships.

**Check:**
1. Verify PK/FK constraints exist and are visible
2. Check constraint names follow conventions
3. Ensure BI tool has Unity Catalog access
4. Refresh data source in BI tool
