# Unity Catalog Constraint Patterns

## Standard Dimensional Model Patterns

### Dimension Table Pattern (SCD Type 1)

**Use Case:** Dimensions where historical changes are not tracked. Current state only.

```sql
CREATE TABLE ${catalog}.${schema}.dim_product (
    product_key STRING NOT NULL COMMENT 'Surrogate primary key',
    upc_code STRING NOT NULL COMMENT 'Business key (UPC barcode)',
    product_name STRING NOT NULL,
    category STRING,
    brand STRING,
    price DECIMAL(10,2),
    created_timestamp TIMESTAMP NOT NULL,
    updated_timestamp TIMESTAMP NOT NULL,
    CONSTRAINT pk_dim_product PRIMARY KEY (product_key) NOT ENFORCED,
    CONSTRAINT uk_product_upc UNIQUE (upc_code) NOT ENFORCED
)
USING DELTA
CLUSTER BY AUTO
COMMENT 'Product dimension table (SCD Type 1)';
```

**Key Points:**
- Surrogate key (`product_key`) is PRIMARY KEY
- Business key (`upc_code`) has UNIQUE constraint
- All PK columns are NOT NULL
- PK defined inline in CREATE TABLE

### Dimension Table Pattern (SCD Type 2)

**Use Case:** Dimensions where historical changes must be tracked. Multiple versions per business key.

```sql
CREATE TABLE ${catalog}.${schema}.dim_store (
    store_key STRING NOT NULL COMMENT 'Surrogate primary key (unique per version)',
    store_number STRING NOT NULL COMMENT 'Business key (not unique for SCD2)',
    store_name STRING NOT NULL,
    address STRING,
    city STRING,
    state STRING,
    zip_code STRING,
    is_current BOOLEAN NOT NULL COMMENT 'TRUE for current version, FALSE for historical',
    effective_date DATE NOT NULL COMMENT 'When this version became effective',
    expiry_date DATE COMMENT 'When this version expired (NULL for current)',
    created_timestamp TIMESTAMP NOT NULL,
    CONSTRAINT pk_dim_store PRIMARY KEY (store_key) NOT ENFORCED
)
USING DELTA
CLUSTER BY AUTO
COMMENT 'Store dimension table (SCD Type 2 - tracks historical changes)';
```

**Key Points:**
- Surrogate key (`store_key`) is PRIMARY KEY
- Business key (`store_number`) does NOT have UNIQUE constraint (multiple versions allowed)
- `is_current` flag indicates current version
- Facts join to `store_key` and filter `WHERE is_current = TRUE`

### Date Dimension Pattern

**Use Case:** Standard date dimension for time-based analysis.

```sql
CREATE TABLE ${catalog}.${schema}.dim_date (
    date_key INT NOT NULL COMMENT 'Surrogate primary key (YYYYMMDD format)',
    date DATE NOT NULL COMMENT 'Actual date value',
    year INT NOT NULL,
    quarter INT NOT NULL,
    month INT NOT NULL,
    month_name STRING NOT NULL,
    week INT NOT NULL,
    day_of_year INT NOT NULL,
    day_of_month INT NOT NULL,
    day_of_week INT NOT NULL,
    day_name STRING NOT NULL,
    is_weekend BOOLEAN NOT NULL,
    is_holiday BOOLEAN NOT NULL,
    fiscal_year INT NOT NULL,
    fiscal_quarter INT NOT NULL,
    CONSTRAINT pk_dim_date PRIMARY KEY (date_key) NOT ENFORCED,
    CONSTRAINT uk_date UNIQUE (date) NOT ENFORCED
)
USING DELTA
CLUSTER BY AUTO
COMMENT 'Date dimension table for time-based analysis';
```

**Key Points:**
- Integer surrogate key (`date_key`) in YYYYMMDD format
- DATE column for actual date value
- Rich time attributes for analysis
- Both surrogate and natural key have constraints

### Fact Table Pattern

**Use Case:** Transaction or snapshot fact tables referencing dimensions.

```sql
CREATE TABLE ${catalog}.${schema}.fact_sales_daily (
    -- Surrogate foreign keys (reference dimension PKs)
    store_key STRING NOT NULL COMMENT 'FK to dim_store.store_key',
    product_key STRING NOT NULL COMMENT 'FK to dim_product.product_key',
    date_key INT NOT NULL COMMENT 'FK to dim_date.date_key',
    
    -- Business keys (for readability, not used in joins)
    store_number STRING NOT NULL COMMENT 'Business key from dim_store',
    upc_code STRING NOT NULL COMMENT 'Business key from dim_product',
    
    -- Measures
    quantity_sold INT NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    total_amount DECIMAL(18,2) NOT NULL,
    discount_amount DECIMAL(18,2),
    net_amount DECIMAL(18,2) NOT NULL,
    
    -- Metadata
    transaction_id STRING NOT NULL,
    created_timestamp TIMESTAMP NOT NULL,
    
    -- Composite primary key (grain: store + product + date)
    CONSTRAINT pk_fact_sales_daily 
        PRIMARY KEY (store_key, product_key, date_key) NOT ENFORCED
    
    -- ❌ DO NOT define FOREIGN KEY constraints here
    -- Apply FKs via ALTER TABLE after all tables exist
)
USING DELTA
CLUSTER BY AUTO
COMMENT 'Daily sales fact table (grain: store + product + date)';
```

**Key Points:**
- Composite PK on surrogate FKs (defines grain)
- Surrogate FKs reference dimension PKs
- Business keys included for readability
- NO inline FK constraints (apply separately)

## Foreign Key Application Pattern

**CRITICAL:** Foreign keys must be applied AFTER all tables exist, using ALTER TABLE.

```sql
-- Step 1: Create all dimension tables first
CREATE TABLE dim_store (...);
CREATE TABLE dim_product (...);
CREATE TABLE dim_date (...);

-- Step 2: Create fact tables (PK only, no FKs)
CREATE TABLE fact_sales_daily (...);

-- Step 3: Apply foreign keys via ALTER TABLE (separate script)
ALTER TABLE ${catalog}.${schema}.fact_sales_daily
    ADD CONSTRAINT fk_sales_store 
    FOREIGN KEY (store_key) 
    REFERENCES ${catalog}.${schema}.dim_store(store_key) NOT ENFORCED;

ALTER TABLE ${catalog}.${schema}.fact_sales_daily
    ADD CONSTRAINT fk_sales_product 
    FOREIGN KEY (product_key) 
    REFERENCES ${catalog}.${schema}.dim_product(product_key) NOT ENFORCED;

ALTER TABLE ${catalog}.${schema}.fact_sales_daily
    ADD CONSTRAINT fk_sales_date 
    FOREIGN KEY (date_key) 
    REFERENCES ${catalog}.${schema}.dim_date(date_key) NOT ENFORCED;
```

## Correct vs Incorrect Patterns

### ❌ WRONG: Business Key as Primary Key

```sql
CREATE TABLE dim_store (
    store_key STRING NOT NULL,
    store_number STRING NOT NULL PRIMARY KEY,  -- ❌ Business key as PK
    ...
)

CREATE TABLE fact_sales (
    store_number STRING NOT NULL,  -- ❌ References business key
    ...
    CONSTRAINT fk_sales_store FOREIGN KEY (store_number) 
        REFERENCES dim_store(store_number) NOT ENFORCED
)
```

**Problems:**
- Business keys can change (violates PK immutability)
- Facts must update when business key changes
- Not proper dimensional modeling

### ✅ CORRECT: Surrogate Key as Primary Key

```sql
CREATE TABLE dim_store (
    store_key STRING NOT NULL,  -- ✅ Surrogate PK
    store_number STRING NOT NULL,  -- Business key (UNIQUE)
    ...
    CONSTRAINT pk_dim_store PRIMARY KEY (store_key) NOT ENFORCED,
    CONSTRAINT uk_store_number UNIQUE (store_number) NOT ENFORCED
)

CREATE TABLE fact_sales (
    store_key STRING NOT NULL,  -- ✅ Surrogate FK
    store_number STRING NOT NULL,  -- Business key (for readability)
    ...
    CONSTRAINT fk_sales_store FOREIGN KEY (store_key) 
        REFERENCES dim_store(store_key) NOT ENFORCED
)
```

**Benefits:**
- Surrogate keys never change
- Facts remain stable
- Proper dimensional modeling

### ❌ WRONG: Inline Foreign Key in CREATE TABLE

```sql
CREATE TABLE fact_sales (
    store_key STRING NOT NULL,
    ...
    CONSTRAINT fk_sales_store FOREIGN KEY (store_key) 
        REFERENCES dim_store(store_key) NOT ENFORCED  -- ❌ Fails if dim_store PK doesn't exist
)
```

**Problem:** If `dim_store` table doesn't exist or doesn't have PK yet, CREATE TABLE fails.

### ✅ CORRECT: Foreign Key Applied Later

```sql
-- Step 1: CREATE TABLE with PK only
CREATE TABLE fact_sales (
    store_key STRING NOT NULL,
    ...
    CONSTRAINT pk_fact_sales PRIMARY KEY (...) NOT ENFORCED  -- ✅ OK
)

-- Step 2: Apply FK after all tables exist
ALTER TABLE fact_sales
    ADD CONSTRAINT fk_sales_store 
    FOREIGN KEY (store_key) 
    REFERENCES dim_store(store_key) NOT ENFORCED  -- ✅ Safe
```

## Date Type Casting Pattern

### Problem: DATE_TRUNC Returns TIMESTAMP

`DATE_TRUNC()` function returns TIMESTAMP, but tables expect DATE.

### ❌ WRONG: DATE_TRUNC Without Casting

```python
df = df.withColumn("month_start_date", expr("DATE_TRUNC('MONTH', date)"))  # Returns TIMESTAMP
```

**Error:** Type mismatch - TIMESTAMP cannot be inserted into DATE column.

### ✅ CORRECT: Explicit CAST to DATE

```python
df = df.withColumn("month_start_date", expr("CAST(DATE_TRUNC('MONTH', date) AS DATE)"))
```

**Rule:** Always `CAST(DATE_TRUNC(...) AS DATE)` when populating DATE columns.

## Constraint Naming Conventions

| Constraint Type | Pattern | Example |
|----------------|---------|---------|
| Primary Key | `pk_<table_name>` | `pk_dim_store` |
| Foreign Key | `fk_<fact_table>_<dimension>` | `fk_sales_store` |
| Unique (Business Key) | `uk_<table>_<column>` | `uk_store_number` |

## Benefits of NOT ENFORCED Constraints

| Benefit | Description |
|---------|-------------|
| **Zero Runtime Overhead** | Constraints are not validated at write time |
| **Unity Catalog Metadata** | Relationships documented in UC for lineage |
| **Query Optimization** | Optimizer leverages PK/FK metadata for better plans |
| **BI Tool Discovery** | Tools like Tableau/Power BI auto-discover relationships |
| **Flexible Data Loading** | Late-arriving dimensions don't cause load failures |

## Design Philosophy

1. **Surrogate Keys = Primary Keys** - Never use business keys as PKs
2. **Facts Reference Surrogates** - Facts use surrogate FKs, not business keys
3. **Business Keys = Alternate Lookups** - Use UNIQUE constraints for business keys
4. **Informational Constraints** - NOT ENFORCED provides metadata without runtime cost
5. **Separation of Concerns** - Table creation separate from constraint application
