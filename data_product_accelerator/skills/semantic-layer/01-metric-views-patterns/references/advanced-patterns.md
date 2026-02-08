# Metric View Patterns and Examples

Complete examples of dimension patterns, measure patterns, joins, and snowflake schema patterns.

## Standard Dimension Patterns

### Geographic Dimensions
```yaml
dimensions:
  - name: store_number
    expr: source.store_number
    comment: Store identifier for location-based analysis
    display_name: Store Number
    synonyms: [store id, location number, store code]
  
  - name: city
    expr: dim_store.city
    comment: City where the location is situated
    display_name: City
    synonyms: [store city, location city]
```

### Product Dimensions
```yaml
dimensions:
  - name: upc_code
    expr: source.upc_code
    comment: Universal Product Code for product identification
    display_name: UPC Code
    synonyms: [product code, upc, barcode]
  
  - name: brand
    expr: dim_product.brand
    comment: Product brand name
    display_name: Brand
    synonyms: [product brand, manufacturer brand]
```

### Time Dimensions (from dim_date)
```yaml
dimensions:
  - name: year
    expr: dim_date.year
    comment: Calendar year for annual analysis
    display_name: Year
    synonyms: [calendar year, fiscal year]
  
  - name: month_name
    expr: dim_date.month_name
    comment: Month name for user-friendly reporting
    display_name: Month Name
    synonyms: [month]
  
  - name: is_weekend
    expr: dim_date.is_weekend
    comment: Weekend indicator for weekend vs weekday analysis
    display_name: Is Weekend
    synonyms: [weekend, weekend flag]
```

## Standard Measure Patterns

### Revenue Measures
```yaml
measures:
  - name: total_revenue
    expr: SUM(source.net_revenue)
    comment: Total net revenue after discounts and returns. Primary revenue metric.
    display_name: Total Revenue
    format:
      type: currency
      currency_code: USD
      decimal_places:
        type: exact
        places: 2
      abbreviation: compact
    synonyms: [revenue, sales, net revenue]
```

### Count Measures
```yaml
measures:
  - name: booking_count
    expr: COUNT(source.booking_id)  # ✅ Use primary key, not SUM(count_column)
    comment: Total number of transactions
    display_name: Booking Count
    format:
      type: number
      decimal_places:
        type: all
    synonyms: [bookings, transactions]
```

## Join Patterns

### SCD2 Dimension Join
```yaml
joins:
  - name: dim_store
    source: ${catalog}.${gold_schema}.dim_store
    'on': source.store_number = dim_store.store_number AND dim_store.is_current = true
```

### Multiple Dimension Joins
```yaml
joins:
  - name: dim_store
    source: ${catalog}.${gold_schema}.dim_store
    'on': source.store_number = dim_store.store_number AND dim_store.is_current = true
  
  - name: dim_product
    source: ${catalog}.${gold_schema}.dim_product
    'on': source.upc_code = dim_product.upc_code
```

## Snowflake Schema Joins (Nested Joins)

**Issue:** Direct joins fail when fact table doesn't have FK to needed dimension.

### ✅ CORRECT: Snowflake Schema (Nested Joins)

```yaml
source: ${catalog}.${gold_schema}.dim_host

joins:
  - name: dim_property
    source: ${catalog}.${gold_schema}.dim_property
    'on': source.host_id = dim_property.host_id AND dim_property.is_current = true
    joins:  # ✅ Nested join under dim_property
      - name: fact_booking
        source: ${catalog}.${gold_schema}.fact_booking_detail
        'on': dim_property.property_id = fact_booking.property_id
```

### Nested Column Reference Pattern

```yaml
measures:
  - name: total_revenue
    expr: SUM(dim_property.fact_booking.total_amount)  # parent.nested.column
```

## Transitive Join Solutions

### ✅ SOLUTION Option 1: Use Foreign Key Directly

```yaml
source: fact_property_engagement

joins:
  - name: dim_property
    source: catalog.schema.dim_property
    'on': source.property_id = dim_property.property_id

dimensions:
  - name: destination_id
    expr: dim_property.destination_id  # ✅ Use FK directly
```

### ✅ SOLUTION Option 2: Denormalize Fact Table

Add destination_id to fact table, then use direct join.

### ✅ SOLUTION Option 3: Create Enriched View

Create SQL view with all needed columns, then use as source.

## Synonym Best Practices

Provide **3-5 synonyms** per dimension/measure:

```yaml
synonyms:
  - <exact alternative name>
  - <business term variant>
  - <abbreviated form>
  - <common misspelling or alternative>
```

**Examples:**
- Revenue → `sales`, `net revenue`, `total sales`, `dollars`
- Store Number → `store id`, `location number`, `store code`
- Units → `quantity`, `volume`, `items sold`, `units sold`

## Professional Language Standards

**❌ Avoid:**
```yaml
comment: Use this because the TVF doesn't work correctly
```

**✅ Use:**
```yaml
comment: >
  Host demographics and verification analytics ONLY.
  → For revenue/booking queries, USE get_host_performance TVF (different join path).
```

## Complete Worked Example (Retail Domain)

A comprehensive metric view covering 12 dimensions and 10 measures for a retail analytics use case.

> **Note:** This YAML would be saved as `sales_performance_metrics.yaml` (filename = view name). The `name` field is NOT included in the YAML content — it comes from the filename and is used in the `CREATE VIEW` statement only.

```yaml
version: "1.1"
comment: >
  PURPOSE: Comprehensive sales performance metrics with revenue, units, and customer insights.
  
  BEST FOR: Sales by store | Revenue trend over time | Product performance | Return analysis
  
  NOT FOR: Inventory levels (use inventory_metrics) | Customer demographics only
  
  DIMENSIONS: transaction_date, store_number, store_name, city, state, upc_code, brand, product_category, year, quarter, month_name, is_weekend
  
  MEASURES: total_revenue, gross_revenue, return_amount, total_units, gross_units, transaction_count, avg_transaction_value, avg_unit_price, return_rate
  
  SOURCE: fact_sales_daily (retail domain)
  
  JOINS: dim_store (store details with SCD2), dim_product (product attributes), dim_date (calendar dimensions)
  
  NOTE: Revenue excludes tax. Return rate is percentage of gross revenue.

source: ${catalog}.${gold_schema}.fact_sales_daily

joins:
  - name: dim_store
    source: ${catalog}.${gold_schema}.dim_store
    'on': source.store_number = dim_store.store_number AND dim_store.is_current = true
  
  - name: dim_product
    source: ${catalog}.${gold_schema}.dim_product
    'on': source.upc_code = dim_product.upc_code
  
  - name: dim_date
    source: ${catalog}.${gold_schema}.dim_date
    'on': source.transaction_date = dim_date.date

dimensions:
  # Fact table dimensions
  - name: store_number
    expr: source.store_number
    comment: Store identifier for location-based sales analysis and store performance tracking
    display_name: Store Number
    synonyms:
      - store id
      - location number
      - store code
  
  - name: upc_code
    expr: source.upc_code
    comment: Universal Product Code for product identification and SKU analysis
    display_name: UPC Code
    synonyms:
      - product code
      - upc
      - barcode
      - sku
  
  - name: transaction_date
    expr: source.transaction_date
    comment: Transaction date for time-based analysis, trending, and period comparisons
    display_name: Transaction Date
    synonyms:
      - date
      - sales date
      - order date
  
  # Store dimension attributes
  - name: store_name
    expr: dim_store.store_name
    comment: Store name for user-friendly location identification in reports and dashboards
    display_name: Store Name
    synonyms:
      - location name
      - store
      - location
  
  - name: city
    expr: dim_store.city
    comment: City where the store is located for geographic analysis and regional performance
    display_name: City
    synonyms:
      - store city
      - location city
  
  - name: state
    expr: dim_store.state
    comment: State where the store is located for state-level aggregations and comparisons
    display_name: State
    synonyms:
      - store state
      - location state
  
  # Product dimension attributes
  - name: brand
    expr: dim_product.brand
    comment: Product brand name for brand performance analysis and market share tracking
    display_name: Brand
    synonyms:
      - product brand
      - manufacturer brand
  
  - name: product_category
    expr: dim_product.product_category
    comment: Product category classification for category-level reporting and analysis
    display_name: Product Category
    synonyms:
      - category
      - product type
  
  # Date dimension attributes
  - name: year
    expr: dim_date.year
    comment: Calendar year for annual analysis and year-over-year comparisons
    display_name: Year
    synonyms:
      - calendar year
      - fiscal year
  
  - name: quarter
    expr: dim_date.quarter
    comment: Calendar quarter (1-4) for quarterly reporting and seasonal analysis
    display_name: Quarter
    synonyms:
      - q
      - fiscal quarter
  
  - name: month_name
    expr: dim_date.month_name
    comment: Month name for user-friendly time-based reporting and monthly trending
    display_name: Month Name
    synonyms:
      - month
      - calendar month
  
  - name: is_weekend
    expr: dim_date.is_weekend
    comment: Weekend indicator for weekend vs weekday sales pattern analysis
    display_name: Is Weekend
    synonyms:
      - weekend
      - weekend flag

measures:
  # Revenue measures
  - name: total_revenue
    expr: SUM(source.net_revenue)
    comment: >
      Total net revenue after discounts and returns. Primary revenue metric for business
      reporting and financial analysis.
    display_name: Total Revenue
    format:
      type: currency
      currency_code: USD
      decimal_places:
        type: exact
        places: 2
      hide_group_separator: false
      abbreviation: compact
    synonyms:
      - revenue
      - net revenue
      - sales
      - total sales
      - dollars
  
  - name: gross_revenue
    expr: SUM(source.gross_revenue)
    comment: >
      Gross revenue before returns. Total sales amount including all positive transactions.
    display_name: Gross Revenue
    format:
      type: currency
      currency_code: USD
      decimal_places:
        type: exact
        places: 2
      abbreviation: compact
    synonyms:
      - gross sales
      - total gross revenue
      - sales before returns
  
  - name: return_amount
    expr: SUM(source.return_amount)
    comment: >
      Total value of returned merchandise. Revenue lost due to product returns.
    display_name: Return Amount
    format:
      type: currency
      currency_code: USD
      decimal_places:
        type: exact
        places: 2
      abbreviation: compact
    synonyms:
      - returns
      - return value
      - returned revenue
  
  # Unit measures
  - name: total_units
    expr: SUM(source.net_units)
    comment: >
      Total units sold after returns. Net quantity of products sold.
    display_name: Total Units
    format:
      type: number
      decimal_places:
        type: all
      hide_group_separator: false
      abbreviation: compact
    synonyms:
      - units
      - units sold
      - quantity
      - volume
      - items sold
  
  - name: gross_units
    expr: SUM(source.gross_units)
    comment: >
      Gross units sold before returns. Total positive unit volume.
    display_name: Gross Units
    format:
      type: number
      decimal_places:
        type: all
      abbreviation: compact
    synonyms:
      - gross volume
      - units before returns
  
  # Transaction measures
  - name: transaction_count
    expr: SUM(source.transaction_count)
    comment: >
      Total number of sales transactions. Count of purchase events.
    display_name: Transaction Count
    format:
      type: number
      decimal_places:
        type: all
      abbreviation: compact
    synonyms:
      - transactions
      - transaction volume
      - sales count
      - number of sales
  
  # Calculated measures
  - name: avg_transaction_value
    expr: AVG(source.avg_transaction_value)
    comment: >
      Average dollar value per transaction. Basket size indicator.
    display_name: Avg Transaction Value
    format:
      type: currency
      currency_code: USD
      decimal_places:
        type: exact
        places: 2
    synonyms:
      - average transaction
      - basket value
      - ticket size
      - average basket
  
  - name: avg_unit_price
    expr: SUM(source.net_revenue) / NULLIF(SUM(source.net_units), 0)
    comment: >
      Average price per unit sold. Calculated as total revenue divided by total units.
    display_name: Avg Unit Price
    format:
      type: currency
      currency_code: USD
      decimal_places:
        type: exact
        places: 2
    synonyms:
      - average price
      - unit price
      - price per unit
  
  - name: return_rate
    expr: (SUM(source.return_amount) / NULLIF(SUM(source.gross_revenue), 0)) * 100
    comment: >
      Percentage of gross revenue returned. Key quality and satisfaction metric.
    display_name: Return Rate
    format:
      type: percentage
      decimal_places:
        type: exact
        places: 1
    synonyms:
      - return percentage
      - return ratio
      - percentage returned
```

## Domain-Specific Business Question Examples

Use these examples to guide synonym creation and measure design for your domain.

### Retail Domain
- "What is the total revenue for last month?"
- "Show me sales by store"
- "What are the top 10 products by revenue?"
- "What is the return rate by brand?"
- "Average transaction value by city?"

### Healthcare Domain
- "What is the patient count for this quarter?"
- "Show me readmissions by diagnosis"
- "What are the top 5 providers by patient volume?"
- "Average length of stay by department?"
- "What is the readmission rate by facility?"

### Finance Domain
- "What is the transaction volume for last week?"
- "Show me amounts by account type"
- "Which merchants have the highest fraud rate?"
- "Average transaction amount by channel?"
- "What is the approval rate by product type?"
