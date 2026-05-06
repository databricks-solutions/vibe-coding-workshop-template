# YAML Schema Patterns

Extracted from `context/prompts/03a-gold-layer-design-prompt.md` Step 3. Use alongside the `01-yaml-table-setup` and `06-table-documentation` skills.

---

## Directory Structure (Domain-Organized)

```
gold_layer_design/yaml/
├── location/                 # 🏪 Location domain
│   ├── dim_store.yaml
│   ├── dim_region.yaml
│   └── dim_territory.yaml
├── product/                  # 📦 Product domain
│   ├── dim_product.yaml
│   ├── dim_brand.yaml
│   └── dim_category.yaml
├── time/                     # 📅 Time domain
│   ├── dim_date.yaml
│   └── dim_fiscal_period.yaml
├── sales/                    # 💰 Sales domain
│   ├── fact_sales_daily.yaml
│   └── dim_promotion.yaml
├── inventory/                # 📊 Inventory domain
│   ├── fact_inventory_snapshot.yaml
│   └── dim_warehouse.yaml
└── README.md                 # Domain index
```

**Rules:**
- Each table belongs to exactly ONE domain
- YAML folder name matches domain name in ERDs
- Conformed dimensions (date, geography) get own domain
- Facts go to domain of their primary business measure

---

## Dimension YAML Template (SCD Type 2)

**File: `gold_layer_design/yaml/{domain}/dim_store.yaml`**

```yaml
# Table metadata
table_name: dim_store
domain: location
bronze_source: retail.stores

# Table description (dual-purpose: business + technical)
description: >
  Gold layer conformed store dimension with SCD Type 2 history tracking.
  Business: Maintains complete store lifecycle history including address changes, 
  status updates, and operational attributes. Each store version tracked separately 
  for point-in-time analysis.
  Technical: Slowly Changing Dimension Type 2 implementation with effective dating.
  Surrogate keys enable proper fact table joins to historical store states.

# Grain definition
grain: "One row per store_number per version (SCD Type 2)"

# SCD strategy
scd_type: 2

# Primary key definition
primary_key:
  columns: ['store_key']
  composite: false

# Business key (unique constraint)
business_key:
  columns: ['store_number']
  
# Foreign key definitions
foreign_keys: []

# Column definitions with lineage
columns:
  # Surrogate Key
  - name: store_key
    type: STRING
    nullable: false
    description: >
      Surrogate key uniquely identifying each version of a store record.
      Business: Used for joining fact tables to dimension.
      Technical: MD5 hash generated from store_id and processed_timestamp.
    lineage:
      bronze_table: bronze_store_dim
      bronze_column: store_id, processed_timestamp
      silver_table: silver_store_dim
      silver_column: store_id, processed_timestamp
      transformation: "HASH_MD5"
      transformation_logic: "md5(concat_ws('||', col('store_id'), col('processed_timestamp')))"
  
  # Business Key
  - name: store_number
    type: STRING
    nullable: false
    description: >
      Business key identifying the physical store location.
      Business: The primary identifier used by store operations and field teams.
      Technical: Natural key from source system, same across all historical versions.
    lineage:
      bronze_table: bronze_store_dim
      bronze_column: store_number
      silver_table: silver_store_dim
      silver_column: store_number
      transformation: "DIRECT_COPY"
      transformation_logic: "col('store_number')"
  
  # Attributes
  - name: store_name
    type: STRING
    nullable: true
    description: >
      Official name of the retail store location.
      Business: Used for customer-facing communications and internal reporting.
      Technical: Free-text field from POS system, may change over time.
    lineage:
      bronze_table: bronze_store_dim
      bronze_column: store_name
      silver_table: silver_store_dim
      silver_column: store_name
      transformation: "DIRECT_COPY"
      transformation_logic: "col('store_name')"
  
  # SCD Type 2 Columns
  - name: effective_from
    type: TIMESTAMP
    nullable: false
    description: >
      Start timestamp for this version of the store record.
      Business: Indicates when this set of store attributes became active.
      Technical: SCD Type 2 field, populated from processed_timestamp.
    lineage:
      bronze_table: bronze_store_dim
      bronze_column: processed_timestamp
      silver_table: silver_store_dim
      silver_column: processed_timestamp
      transformation: "DIRECT_COPY"
      transformation_logic: "col('processed_timestamp')"
  
  - name: effective_to
    type: TIMESTAMP
    nullable: true
    description: >
      End timestamp for this version. NULL indicates current version.
      Business: Non-NULL indicates historical record.
      Technical: SCD Type 2 field, set to next version effective_from when superseded.
    lineage:
      bronze_table: N/A
      bronze_column: N/A
      silver_table: N/A
      silver_column: N/A
      transformation: "GENERATED"
      transformation_logic: "lit(None).cast('timestamp')"
  
  - name: is_current
    type: BOOLEAN
    nullable: false
    description: >
      Flag indicating if this is the current active version.
      Business: TRUE for current store attributes. Use WHERE is_current = true.
      Technical: SCD Type 2 flag, updated to FALSE when new version created.
    lineage:
      bronze_table: N/A
      bronze_column: N/A
      silver_table: N/A
      silver_column: N/A
      transformation: "GENERATED"
      transformation_logic: "lit(True)"
  
  # Audit Columns
  - name: record_created_timestamp
    type: TIMESTAMP
    nullable: false
    description: >
      Timestamp when this record was first inserted into Gold.
      Business: Audit field for data lineage.
      Technical: Set once at INSERT time, never updated.
    lineage:
      bronze_table: N/A
      bronze_column: N/A
      silver_table: N/A
      silver_column: N/A
      transformation: "GENERATED"
      transformation_logic: "current_timestamp()"
  
  - name: record_updated_timestamp
    type: TIMESTAMP
    nullable: false
    description: >
      Timestamp when this record was last modified.
      Business: Audit field showing data freshness.
      Technical: Updated on every MERGE operation.
    lineage:
      bronze_table: N/A
      bronze_column: N/A
      silver_table: N/A
      silver_column: N/A
      transformation: "GENERATED"
      transformation_logic: "current_timestamp()"

# Table properties
table_properties:
  contains_pii: true
  data_classification: confidential
  business_owner: Retail Operations
  technical_owner: Data Engineering
  update_frequency: Daily
```

---

## Fact Table YAML Template

**File: `gold_layer_design/yaml/{domain}/fact_sales_daily.yaml`**

```yaml
table_name: fact_sales_daily
domain: sales
bronze_source: sales.transactions

description: >
  Gold layer daily sales fact table at store-product-day grain.
  Business: Primary source for sales performance reporting including revenue, units, 
  and customer metrics. Aggregated from transaction-level Silver data.
  Technical: Grain is one row per store-product-date combination.

grain: "One row per store_number-upc_code-transaction_date combination (daily aggregate)"

primary_key:
  columns: ['store_number', 'upc_code', 'transaction_date']
  composite: true

foreign_keys:
  - columns: ['store_number']
    references: dim_store(store_number)
    nullable: false
  - columns: ['upc_code']
    references: dim_product(upc_code)
    nullable: false
  - columns: ['transaction_date']
    references: dim_date(date)
    nullable: false

columns:
  # Foreign Keys (grain columns)
  - name: store_number
    type: STRING
    nullable: false
    description: >
      Store identifier. Business: Links to store dimension.
      Technical: FK to dim_store.store_number.
    lineage:
      bronze_table: bronze_transactions
      bronze_column: store_number
      silver_table: silver_transactions
      silver_column: store_number
      transformation: "DIRECT_COPY"
      transformation_logic: "col('store_number')"
  
  - name: upc_code
    type: STRING
    nullable: false
    description: >
      Product UPC code. Business: Links to product dimension.
      Technical: FK to dim_product.upc_code.
    lineage:
      bronze_table: bronze_transactions
      bronze_column: upc_code
      silver_table: silver_transactions
      silver_column: upc_code
      transformation: "DIRECT_COPY"
      transformation_logic: "col('upc_code')"
  
  - name: transaction_date
    type: DATE
    nullable: false
    description: >
      Transaction date. Business: Date dimension for time-based analysis.
      Technical: FK to dim_date.date.
    lineage:
      bronze_table: bronze_transactions
      bronze_column: transaction_date
      silver_table: silver_transactions
      silver_column: transaction_date
      transformation: "DIRECT_COPY"
      transformation_logic: "col('transaction_date')"
  
  # Revenue Measures
  - name: gross_revenue
    type: DECIMAL(18,2)
    nullable: true
    description: >
      Total revenue before returns (positive sales only).
      Business: Gross sales amount before adjustments.
      Technical: SUM of positive transaction amounts.
    lineage:
      bronze_table: bronze_transactions
      bronze_column: final_sales_price
      silver_table: silver_transactions
      silver_column: final_sales_price
      transformation: "AGGREGATE_SUM_CONDITIONAL"
      transformation_logic: "spark_sum(when(col('quantity_sold') > 0, col('final_sales_price')).otherwise(0))"
      groupby_columns: ['store_number', 'upc_code', 'transaction_date']
  
  - name: net_revenue
    type: DECIMAL(18,2)
    nullable: true
    description: >
      Net revenue after returns. Business: Primary KPI for financial reporting.
      Technical: SUM(revenue) including negative values for returns.
    lineage:
      bronze_table: bronze_transactions
      bronze_column: final_sales_price
      silver_table: silver_transactions
      silver_column: final_sales_price
      transformation: "AGGREGATE_SUM"
      transformation_logic: "spark_sum('final_sales_price')"
      groupby_columns: ['store_number', 'upc_code', 'transaction_date']
  
  - name: net_units
    type: BIGINT
    nullable: true
    description: >
      Net units sold after returns. Business: For inventory planning.
      Technical: SUM(quantity) including negatives for returns.
    lineage:
      bronze_table: bronze_transactions
      bronze_column: quantity_sold
      silver_table: silver_transactions
      silver_column: quantity_sold
      transformation: "AGGREGATE_SUM"
      transformation_logic: "spark_sum('quantity_sold')"
      groupby_columns: ['store_number', 'upc_code', 'transaction_date']
  
  - name: transaction_count
    type: BIGINT
    nullable: true
    description: >
      Number of transactions. Business: Store performance metric.
      Technical: COUNT(*) from Silver transactions.
    lineage:
      bronze_table: bronze_transactions
      bronze_column: transaction_id
      silver_table: silver_transactions
      silver_column: transaction_id
      transformation: "AGGREGATE_COUNT"
      transformation_logic: "count('*')"
      groupby_columns: ['store_number', 'upc_code', 'transaction_date']
  
  - name: avg_transaction_value
    type: DECIMAL(18,2)
    nullable: true
    description: >
      Average dollar value per transaction. Business: Basket size metric.
      Technical: net_revenue / transaction_count.
    lineage:
      bronze_table: N/A
      bronze_column: N/A
      silver_table: N/A
      silver_column: N/A
      transformation: "DERIVED_CALCULATION"
      transformation_logic: "col('net_revenue') / col('transaction_count')"
      depends_on: ['net_revenue', 'transaction_count']
  
  # Audit
  - name: record_created_timestamp
    type: TIMESTAMP
    nullable: false
    description: >
      Timestamp when aggregate was first created.
      Business: Audit field. Technical: Set at INSERT time.
    lineage:
      bronze_table: N/A
      bronze_column: N/A
      silver_table: N/A
      silver_column: N/A
      transformation: "GENERATED"
      transformation_logic: "current_timestamp()"
  
  - name: record_updated_timestamp
    type: TIMESTAMP
    nullable: false
    description: >
      Timestamp when aggregate was last refreshed.
      Business: Shows data freshness. Technical: Updated on every MERGE.
    lineage:
      bronze_table: N/A
      bronze_column: N/A
      silver_table: N/A
      silver_column: N/A
      transformation: "GENERATED"
      transformation_logic: "current_timestamp()"

table_properties:
  contains_pii: false
  data_classification: internal
  business_owner: Sales Operations
  technical_owner: Data Engineering
  update_frequency: Daily
  aggregation_level: daily
```

---

## Date Dimension YAML Template

**File: `gold_layer_design/yaml/time/dim_date.yaml`**

```yaml
table_name: dim_date
domain: time
bronze_source: generated

description: >
  Gold layer date dimension with calendar attributes.
  Business: Standard date dimension for time-based analysis across all facts.
  Technical: Generated internally, not sourced from Silver.

grain: "One row per calendar date"
scd_type: 1

primary_key:
  columns: ['date']
  composite: false

foreign_keys: []

columns:
  - name: date
    type: DATE
    nullable: false
    description: "Calendar date. Business: Primary date for all analysis. Technical: Primary key."
  
  - name: year
    type: INT
    nullable: false
    description: "Calendar year (YYYY). Business: Annual and YoY analysis. Technical: YEAR(date)."
  
  - name: quarter
    type: INT
    nullable: false
    description: "Calendar quarter (1-4). Business: Quarterly reporting. Technical: QUARTER(date)."
  
  - name: month
    type: INT
    nullable: false
    description: "Calendar month (1-12). Business: Monthly trends. Technical: MONTH(date)."
  
  - name: month_name
    type: STRING
    nullable: false
    description: "Month name (January, etc.). Business: Labels for reports. Technical: DATE_FORMAT(date, 'MMMM')."
  
  - name: week_of_year
    type: INT
    nullable: false
    description: "ISO week of year (1-53). Business: Weekly analysis. Technical: WEEKOFYEAR(date)."
  
  - name: day_of_week
    type: INT
    nullable: false
    description: "Day of week (1=Sunday, 7=Saturday). Business: Day analysis. Technical: DAYOFWEEK(date)."
  
  - name: day_of_week_name
    type: STRING
    nullable: false
    description: "Day name (Monday, etc.). Business: Labels. Technical: DATE_FORMAT(date, 'EEEE')."
  
  - name: is_weekend
    type: BOOLEAN
    nullable: false
    description: "Weekend indicator. Business: Weekend vs weekday analysis. Technical: day_of_week IN (1, 7)."
  
  - name: is_holiday
    type: BOOLEAN
    nullable: true
    description: "Holiday indicator. Business: Holiday impact analysis. Technical: From holiday calendar lookup."

table_properties:
  contains_pii: false
  data_classification: public
  business_owner: Enterprise Data
  technical_owner: Data Engineering
  update_frequency: Static
```
