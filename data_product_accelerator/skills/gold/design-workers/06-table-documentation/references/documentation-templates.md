# Gold Layer Documentation Templates

Complete column and table comment templates with examples for all field types.

## Column Description Templates by Type

### Surrogate Key

**Template:**
```
Surrogate key uniquely identifying each version of a {entity} record. Business: Used for joining fact tables to dimension. Technical: {Hash method} generated from {source columns} to ensure uniqueness across {SCD type} versions.
```

**Examples:**
```python
store_key STRING NOT NULL COMMENT 'Surrogate key uniquely identifying each version of a store record. Business: Used for joining fact tables to dimension. Technical: MD5 hash generated from store_id and processed_timestamp to ensure uniqueness across SCD Type 2 versions.'

product_key STRING NOT NULL COMMENT 'Surrogate key uniquely identifying each version of a product record. Business: Primary key for product dimension joins. Technical: SHA256 hash of upc_code and effective_from timestamp for SCD Type 2 uniqueness.'

date_key INT NOT NULL COMMENT 'Surrogate key uniquely identifying each date. Business: Used for time-based analysis and reporting. Technical: Integer date key in YYYYMMDD format (e.g., 20250115) for efficient joins and partitioning.'
```

### Business Key

**Template:**
```
{Natural description} uniquely identifying {entity} in source system. Business: {Business use cases and context}. Technical: {Data type, format, source system, immutability}.
```

**Examples:**
```python
store_number STRING COMMENT 'Store identifier from POS system. Business: Human-readable store identifier used in reports and dashboards. Technical: Alphanumeric code from source system, immutable business key.'

upc_code STRING COMMENT 'Universal Product Code for product identification. Business: Standard retail product identifier used in inventory and sales systems. Technical: 12-digit UPC format, immutable business identifier.'

customer_id BIGINT COMMENT 'Customer identifier from CRM system. Business: Primary customer reference for account management and support. Technical: BIGINT from Salesforce, immutable business key.'
```

### Foreign Key

**Template:**
```
Foreign key referencing {referenced_table}.{referenced_column}. Business: {Business relationship context}. Technical: References surrogate PK {referenced_table}.{referenced_column} for referential integrity.
```

**Examples:**
```python
store_key STRING COMMENT 'Foreign key referencing dim_store.store_key. Business: Links sales transactions to store location dimension. Technical: References surrogate PK dim_store.store_key for referential integrity.'

product_key STRING COMMENT 'Foreign key referencing dim_product.product_key. Business: Links sales line items to product dimension. Technical: References surrogate PK dim_product.product_key, current version only (is_current=true).'

date_key INT COMMENT 'Foreign key referencing dim_date.date_key. Business: Links transactions to date dimension for time-based analysis. Technical: References surrogate PK dim_date.date_key in YYYYMMDD format.'
```

### Measure

**Template:**
```
{Calculation description}. Business: {Business purpose, KPI context, reporting use}. Technical: {Formula, aggregation method, unit, precision}.
```

**Examples:**
```python
net_revenue DECIMAL(18,2) COMMENT 'Net revenue after subtracting returns from gross revenue. Business: The actual revenue realized from sales, primary KPI for financial reporting. Technical: gross_revenue - return_amount, represents true daily sales value in USD.'

units_sold INT COMMENT 'Total quantity of products sold in transaction. Business: Primary volume metric for inventory planning and sales analysis. Technical: SUM of quantity field from source transactions, integer count.'

average_order_value DECIMAL(18,2) COMMENT 'Average value per order calculated as total revenue divided by order count. Business: Key metric for understanding customer spending patterns. Technical: net_revenue / order_count, calculated at daily grain, DECIMAL(18,2) precision.'
```

### Percentage

**Template:**
```
{Percentage description} expressed as decimal (0.0 to 1.0). Business: {Business context and interpretation}. Technical: {Calculation formula, NULL handling, precision}.
```

**Examples:**
```python
return_rate_pct DECIMAL(5,4) COMMENT 'Return rate expressed as decimal percentage (0.0 to 1.0). Business: Percentage of sales returned, key quality metric. Technical: return_count / total_sales_count, NULL when total_sales_count = 0, DECIMAL(5,4) precision (max 99.99%).'

margin_pct DECIMAL(5,4) COMMENT 'Profit margin expressed as decimal percentage. Business: Profitability metric showing percentage of revenue retained as profit. Technical: (net_revenue - cost_of_goods_sold) / net_revenue, NULL when net_revenue = 0.'
```

### Boolean Flag

**Template:**
```
{State description} indicator flag. Business: {Business meaning of TRUE/FALSE}. Technical: BOOLEAN, {default value, update behavior}.
```

**Examples:**
```python
is_current BOOLEAN NOT NULL COMMENT 'Current version indicator for SCD Type 2 dimension. Business: TRUE indicates active/current record, FALSE indicates historical version. Technical: BOOLEAN, default TRUE, updated when new version created.'

is_weekend BOOLEAN COMMENT 'Weekend day indicator flag. Business: TRUE for Saturday/Sunday, used for weekend sales analysis. Technical: BOOLEAN derived from day_of_week, TRUE when day_of_week IN (6,7).'

is_active BOOLEAN NOT NULL COMMENT 'Active status indicator for store. Business: TRUE indicates store is currently operating, FALSE indicates closed/inactive. Technical: BOOLEAN, default TRUE, updated via MERGE from source system.'
```

### Timestamp

**Template:**
```
{Timestamp purpose} timestamp. Business: {Business context and use cases}. Technical: TIMESTAMP, {timezone, update behavior, format}.
```

**Examples:**
```python
record_created_timestamp TIMESTAMP NOT NULL COMMENT 'Timestamp when record was first created in Gold layer. Business: Audit trail for data lineage and change tracking. Technical: TIMESTAMP in UTC, set on INSERT, never updated.'

effective_from TIMESTAMP NOT NULL COMMENT 'Start timestamp for SCD Type 2 version validity period. Business: Beginning of time period when this dimension version was active. Technical: TIMESTAMP in UTC, set from source system processed_timestamp, used for time-based joins.'

last_updated_timestamp TIMESTAMP COMMENT 'Timestamp when record was last updated in Gold layer. Business: Tracks most recent data refresh for data freshness monitoring. Technical: TIMESTAMP in UTC, updated on MERGE, NULL on initial INSERT.'
```

### SCD Type 2 Fields

**Template:**
```
{SCD field purpose} for SCD Type 2 dimension versioning. Business: {Business context}. Technical: {Implementation details, join patterns}.
```

**Examples:**
```python
effective_from TIMESTAMP NOT NULL COMMENT 'Start timestamp for SCD Type 2 version validity period. Business: Beginning of time period when this dimension version was active. Technical: TIMESTAMP in UTC, set from source system processed_timestamp, used for time-based joins with WHERE effective_from <= fact_date < effective_to.'

effective_to TIMESTAMP COMMENT 'End timestamp for SCD Type 2 version validity period. Business: End of time period when this dimension version was active, NULL indicates current version. Technical: TIMESTAMP in UTC, NULL for current version, set to next version effective_from when superseded.'

is_current BOOLEAN NOT NULL COMMENT 'Current version indicator for SCD Type 2 dimension. Business: TRUE indicates active/current record, FALSE indicates historical version. Technical: BOOLEAN, default TRUE, used for efficient current version joins (WHERE is_current = true).'
```

## Table Comment Templates

### Dimension Table

**Template:**
```
Gold layer conformed {entity} dimension with {SCD Type}. Business: {Business purpose, history tracking, use cases}. Technical: {SCD implementation details, key strategy, update behavior}.
```

**Examples:**
```python
COMMENT 'Gold layer conformed store dimension with SCD Type 2. Business: Master store reference table with full history tracking for store attribute changes (location, manager, format). Used for store performance analysis and organizational reporting. Technical: SCD Type 2 implementation with surrogate key (store_key) as PRIMARY KEY, business key (store_number) as UNIQUE constraint. Updated via MERGE from Silver layer, maintains full history with effective_from/effective_to timestamps.'

COMMENT 'Gold layer conformed product dimension with SCD Type 1. Business: Master product catalog with current product attributes (name, brand, category). Used for product sales analysis and inventory management. Technical: SCD Type 1 implementation with surrogate key (product_key) as PRIMARY KEY, business key (upc_code) as UNIQUE constraint. Updated via MERGE from Silver layer, overwrites previous values on attribute changes.'
```

### Fact Table

**Template:**
```
Gold layer {period} {subject} fact table with {aggregation level} at {grain}. Business: {Primary use cases, metrics included, reporting purpose}. Technical: Grain is {what one row represents}. {Performance optimizations, key relationships}.
```

**Examples:**
```python
COMMENT 'Gold layer daily sales fact table with store and product aggregation at daily grain. Business: Primary fact table for sales reporting, revenue analysis, and store performance dashboards. Includes net revenue, units sold, and transaction counts. Technical: Grain is one row per store per product per day. Composite PRIMARY KEY (store_key, product_key, date_key). Clustered by date_key for time-based queries. References dim_store, dim_product, dim_date via foreign keys.'

COMMENT 'Gold layer monthly inventory snapshot fact table at monthly grain. Business: Monthly inventory position reporting for supply chain planning and stock level analysis. Technical: Grain is one row per product per store per month. Composite PRIMARY KEY (product_key, store_key, month_key). Snapshot table updated monthly via full refresh.'
```

## Complete Table Example

### SCD Type 2 Dimension

```python
CREATE TABLE ${catalog}.${schema}.dim_store (
    store_key STRING NOT NULL COMMENT 'Surrogate key uniquely identifying each version of a store record. Business: Used for joining fact tables to dimension. Technical: MD5 hash generated from store_id and processed_timestamp to ensure uniqueness across SCD Type 2 versions.',
    store_number STRING NOT NULL COMMENT 'Store identifier from POS system. Business: Human-readable store identifier used in reports and dashboards. Technical: Alphanumeric code from source system, immutable business key.',
    store_name STRING COMMENT 'Store name from source system. Business: Display name for store in reports and dashboards. Technical: VARCHAR(255) from source, may change over time.',
    effective_from TIMESTAMP NOT NULL COMMENT 'Start timestamp for SCD Type 2 version validity period. Business: Beginning of time period when this dimension version was active. Technical: TIMESTAMP in UTC, set from source system processed_timestamp, used for time-based joins.',
    effective_to TIMESTAMP COMMENT 'End timestamp for SCD Type 2 version validity period. Business: End of time period when this dimension version was active, NULL indicates current version. Technical: TIMESTAMP in UTC, NULL for current version, set to next version effective_from when superseded.',
    is_current BOOLEAN NOT NULL COMMENT 'Current version indicator for SCD Type 2 dimension. Business: TRUE indicates active/current record, FALSE indicates historical version. Technical: BOOLEAN, default TRUE, used for efficient current version joins (WHERE is_current = true).',
    CONSTRAINT pk_dim_store PRIMARY KEY (store_key) NOT ENFORCED,
    CONSTRAINT uk_store_number UNIQUE (store_number) NOT ENFORCED
)
USING DELTA
CLUSTER BY AUTO
COMMENT 'Gold layer conformed store dimension with SCD Type 2. Business: Master store reference table with full history tracking for store attribute changes (location, manager, format). Used for store performance analysis and organizational reporting. Technical: SCD Type 2 implementation with surrogate key (store_key) as PRIMARY KEY, business key (store_number) as UNIQUE constraint. Updated via MERGE from Silver layer, maintains full history with effective_from/effective_to timestamps.'
TBLPROPERTIES (
    'delta.enableChangeDataFeed' = 'true',
    'delta.enableRowTracking' = 'true',
    'delta.enableDeletionVectors' = 'true',
    'delta.autoOptimize.autoCompact' = 'true',
    'delta.autoOptimize.optimizeWrite' = 'true',
    'quality' = 'gold',
    'layer' = 'gold',
    'source_layer' = 'silver',
    'source_table' = 'silver_store',
    'domain' = 'retail',
    'entity_type' = 'dimension',
    'scd_type' = '2',
    'contains_pii' = 'false',
    'data_classification' = 'internal',
    'business_owner' = 'Retail Operations',
    'technical_owner' = 'Data Engineering'
);
```

### Fact Table

```python
CREATE TABLE ${catalog}.${schema}.fact_sales_daily (
    store_key STRING NOT NULL COMMENT 'Foreign key referencing dim_store.store_key. Business: Links sales transactions to store location dimension. Technical: References surrogate PK dim_store.store_key for referential integrity.',
    product_key STRING NOT NULL COMMENT 'Foreign key referencing dim_product.product_key. Business: Links sales line items to product dimension. Technical: References surrogate PK dim_product.product_key, current version only (is_current=true).',
    date_key INT NOT NULL COMMENT 'Foreign key referencing dim_date.date_key. Business: Links transactions to date dimension for time-based analysis. Technical: References surrogate PK dim_date.date_key in YYYYMMDD format.',
    net_revenue DECIMAL(18,2) COMMENT 'Net revenue after subtracting returns from gross revenue. Business: The actual revenue realized from sales, primary KPI for financial reporting. Technical: gross_revenue - return_amount, represents true daily sales value in USD.',
    units_sold INT COMMENT 'Total quantity of products sold in transaction. Business: Primary volume metric for inventory planning and sales analysis. Technical: SUM of quantity field from source transactions, integer count.',
    transaction_count INT COMMENT 'Number of transactions included in daily aggregation. Business: Transaction volume metric for operational reporting. Technical: COUNT(*) of source transactions, integer count.',
    CONSTRAINT pk_fact_sales_daily PRIMARY KEY (store_key, product_key, date_key) NOT ENFORCED,
    CONSTRAINT fk_store FOREIGN KEY (store_key) REFERENCES ${catalog}.${schema}.dim_store(store_key) NOT ENFORCED,
    CONSTRAINT fk_product FOREIGN KEY (product_key) REFERENCES ${catalog}.${schema}.dim_product(product_key) NOT ENFORCED,
    CONSTRAINT fk_date FOREIGN KEY (date_key) REFERENCES ${catalog}.${schema}.dim_date(date_key) NOT ENFORCED
)
USING DELTA
CLUSTER BY AUTO
COMMENT 'Gold layer daily sales fact table with store and product aggregation at daily grain. Business: Primary fact table for sales reporting, revenue analysis, and store performance dashboards. Includes net revenue, units sold, and transaction counts. Technical: Grain is one row per store per product per day. Composite PRIMARY KEY (store_key, product_key, date_key). Clustered by date_key for time-based queries. References dim_store, dim_product, dim_date via foreign keys.'
TBLPROPERTIES (
    'delta.enableChangeDataFeed' = 'true',
    'delta.enableRowTracking' = 'true',
    'delta.enableDeletionVectors' = 'true',
    'delta.autoOptimize.autoCompact' = 'true',
    'delta.autoOptimize.optimizeWrite' = 'true',
    'quality' = 'gold',
    'layer' = 'gold',
    'source_layer' = 'silver',
    'source_table' = 'silver_sales',
    'domain' = 'retail',
    'entity_type' = 'fact',
    'grain' = 'daily_store_product',
    'gold_type' = 'aggregated',
    'contains_pii' = 'false',
    'data_classification' = 'internal',
    'business_owner' = 'Retail Operations',
    'technical_owner' = 'Data Engineering'
);
```
