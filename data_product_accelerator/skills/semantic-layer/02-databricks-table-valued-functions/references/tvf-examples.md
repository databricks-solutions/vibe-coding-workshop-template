# TVF Complete Examples

Five production-ready TVF examples demonstrating different query patterns. These use a generic retail domain but are adaptable to any business domain (healthcare, finance, hospitality, etc.).

All examples follow the skill's critical rules:
- STRING for date parameters (not DATE)
- Required parameters before optional (DEFAULT) parameters
- ROW_NUMBER + WHERE for Top N (not LIMIT)
- NULLIF for all divisions
- SCD Type 2 joins include `is_current = true`
- v3.0 bullet-point COMMENT format

---

## Example 1: Top N Ranking Pattern — `get_top_stores_by_revenue`

**Pattern demonstrated:** Aggregation → Ranking → Parameterized Top N with dimension join

```sql
CREATE OR REPLACE FUNCTION {catalog}.{schema}.get_top_stores_by_revenue(
  start_date STRING COMMENT 'Start date for analysis (format: YYYY-MM-DD)',
  end_date STRING COMMENT 'End date for analysis (format: YYYY-MM-DD)',
  top_n INT DEFAULT 10 COMMENT 'Number of top stores to return'
)
RETURNS TABLE(
  rank INT COMMENT 'Store rank by revenue',
  store_number STRING COMMENT 'Store identifier',
  store_name STRING COMMENT 'Store display name',
  city STRING COMMENT 'Store city',
  state STRING COMMENT 'Store state',
  total_revenue DECIMAL(18,2) COMMENT 'Total revenue for period',
  total_units BIGINT COMMENT 'Total units sold',
  transaction_count BIGINT COMMENT 'Number of transactions',
  avg_transaction_value DECIMAL(18,2) COMMENT 'Average transaction value',
  unique_products BIGINT COMMENT 'Number of unique products sold'
)
COMMENT '
• PURPOSE: Returns the top N stores ranked by revenue for a date range
• BEST FOR: "What are the top 10 stores by revenue this month?" | "Show me best performing stores" | "Store rankings"
• RETURNS: Individual store rows (rank, store_number, store_name, city, state, total_revenue, total_units, transaction_count, avg_transaction_value, unique_products)
• PARAMS: start_date, end_date, top_n (default: 10)
• SYNTAX: SELECT * FROM get_top_stores_by_revenue(''2024-01-01'', ''2024-12-31'', 10)
• NOTE: Uses ROW_NUMBER for parameterized top N | Sorted by total_revenue DESC
'
RETURN
  WITH store_metrics AS (
    SELECT 
      fsd.store_number,
      ds.store_name,
      ds.city,
      ds.state,
      SUM(fsd.net_revenue) as total_revenue,
      SUM(fsd.net_units) as total_units,
      SUM(fsd.transaction_count) as transaction_count,
      COUNT(DISTINCT fsd.upc_code) as unique_products
    FROM {catalog}.{schema}.fact_sales_daily fsd
    LEFT JOIN {catalog}.{schema}.dim_store ds 
      ON fsd.store_number = ds.store_number 
      AND ds.is_current = true
    WHERE fsd.transaction_date BETWEEN CAST(start_date AS DATE) AND CAST(end_date AS DATE)
    GROUP BY fsd.store_number, ds.store_name, ds.city, ds.state
  ),
  ranked_stores AS (
    SELECT 
      ROW_NUMBER() OVER (ORDER BY total_revenue DESC) as rank,
      store_number,
      store_name,
      city,
      state,
      total_revenue,
      total_units,
      transaction_count,
      total_revenue / NULLIF(transaction_count, 0) as avg_transaction_value,
      unique_products
    FROM store_metrics
  )
  SELECT * FROM ranked_stores
  WHERE rank <= top_n
  ORDER BY rank;
```

---

## Example 2: Entity Drilldown Pattern — `get_store_performance`

**Pattern demonstrated:** Single-entity detailed view with daily granularity (no Top N needed)

```sql
CREATE OR REPLACE FUNCTION {catalog}.{schema}.get_store_performance(
  p_store_number STRING COMMENT 'Store number to analyze',
  start_date STRING COMMENT 'Start date (format: YYYY-MM-DD)',
  end_date STRING COMMENT 'End date (format: YYYY-MM-DD)'
)
RETURNS TABLE(
  store_number STRING COMMENT 'Store identifier',
  store_name STRING COMMENT 'Store name',
  transaction_date DATE COMMENT 'Transaction date',
  total_revenue DECIMAL(18,2) COMMENT 'Daily revenue',
  total_units BIGINT COMMENT 'Daily units sold',
  transaction_count BIGINT COMMENT 'Daily transaction count',
  avg_transaction_value DECIMAL(18,2) COMMENT 'Average transaction value',
  unique_products BIGINT COMMENT 'Unique products sold'
)
COMMENT '
• PURPOSE: Returns detailed daily performance metrics for a specific store
• BEST FOR: "How did store 12345 perform last week?" | "Show me daily sales for store 12345" | "Store deep dive"
• NOT FOR: Comparing multiple stores (use get_top_stores_by_revenue or get_sales_by_state)
• RETURNS: Individual daily rows (store_number, store_name, transaction_date, total_revenue, total_units, transaction_count, avg_transaction_value, unique_products)
• PARAMS: p_store_number, start_date, end_date
• SYNTAX: SELECT * FROM get_store_performance(''12345'', ''2024-01-01'', ''2024-01-31'')
• NOTE: Sorted by transaction_date ASC | One row per day
'
RETURN
  SELECT 
    fsd.store_number,
    ds.store_name,
    fsd.transaction_date,
    SUM(fsd.net_revenue) as total_revenue,
    SUM(fsd.net_units) as total_units,
    SUM(fsd.transaction_count) as transaction_count,
    SUM(fsd.net_revenue) / NULLIF(SUM(fsd.transaction_count), 0) as avg_transaction_value,
    COUNT(DISTINCT fsd.upc_code) as unique_products
  FROM {catalog}.{schema}.fact_sales_daily fsd
  LEFT JOIN {catalog}.{schema}.dim_store ds 
    ON fsd.store_number = ds.store_number 
    AND ds.is_current = true
  WHERE fsd.store_number = p_store_number
    AND fsd.transaction_date BETWEEN CAST(start_date AS DATE) AND CAST(end_date AS DATE)
  GROUP BY fsd.store_number, ds.store_name, fsd.transaction_date
  ORDER BY fsd.transaction_date;
```

---

## Example 3: Product Ranking Pattern — `get_top_products`

**Pattern demonstrated:** Multi-dimension ranking with category context and cross-store distribution

```sql
CREATE OR REPLACE FUNCTION {catalog}.{schema}.get_top_products(
  start_date STRING COMMENT 'Start date (format: YYYY-MM-DD)',
  end_date STRING COMMENT 'End date (format: YYYY-MM-DD)',
  top_n INT DEFAULT 10 COMMENT 'Number of products to return'
)
RETURNS TABLE(
  rank INT COMMENT 'Product rank by revenue',
  upc_code STRING COMMENT 'Product UPC code',
  product_description STRING COMMENT 'Product description',
  brand STRING COMMENT 'Product brand',
  category STRING COMMENT 'Product category',
  total_revenue DECIMAL(18,2) COMMENT 'Total revenue',
  total_units BIGINT COMMENT 'Total units sold',
  stores_sold BIGINT COMMENT 'Number of stores selling this product'
)
COMMENT '
• PURPOSE: Returns top N products ranked by revenue for a date range
• BEST FOR: "What are the top 5 selling products?" | "Show me best performing products this quarter" | "Product bestsellers"
• NOT FOR: Product performance at a specific store (filter results or create store-product TVF)
• RETURNS: Individual product rows (rank, upc_code, product_description, brand, category, total_revenue, total_units, stores_sold)
• PARAMS: start_date, end_date, top_n (default: 10)
• SYNTAX: SELECT * FROM get_top_products(''2024-01-01'', ''2024-12-31'', 5)
• NOTE: stores_sold shows distribution breadth | Sorted by total_revenue DESC
'
RETURN
  WITH product_metrics AS (
    SELECT 
      fsd.upc_code,
      dp.product_description,
      dp.brand,
      dp.category,
      SUM(fsd.net_revenue) as total_revenue,
      SUM(fsd.net_units) as total_units,
      COUNT(DISTINCT fsd.store_number) as stores_sold
    FROM {catalog}.{schema}.fact_sales_daily fsd
    LEFT JOIN {catalog}.{schema}.dim_product dp 
      ON fsd.upc_code = dp.upc_code
    WHERE fsd.transaction_date BETWEEN CAST(start_date AS DATE) AND CAST(end_date AS DATE)
    GROUP BY fsd.upc_code, dp.product_description, dp.brand, dp.category
  ),
  ranked_products AS (
    SELECT 
      ROW_NUMBER() OVER (ORDER BY total_revenue DESC) as rank,
      upc_code,
      product_description,
      brand,
      category,
      total_revenue,
      total_units,
      stores_sold
    FROM product_metrics
  )
  SELECT * FROM ranked_products
  WHERE rank <= top_n
  ORDER BY rank;
```

---

## Example 4: Geographic Aggregation Pattern — `get_sales_by_state`

**Pattern demonstrated:** Geographic rollup with per-entity averages (no Top N, full result set)

```sql
CREATE OR REPLACE FUNCTION {catalog}.{schema}.get_sales_by_state(
  start_date STRING COMMENT 'Start date (format: YYYY-MM-DD)',
  end_date STRING COMMENT 'End date (format: YYYY-MM-DD)'
)
RETURNS TABLE(
  state STRING COMMENT 'State abbreviation',
  store_count BIGINT COMMENT 'Number of stores in state',
  total_revenue DECIMAL(18,2) COMMENT 'Total state revenue',
  total_units BIGINT COMMENT 'Total units sold',
  transaction_count BIGINT COMMENT 'Total transactions',
  avg_revenue_per_store DECIMAL(18,2) COMMENT 'Average revenue per store'
)
COMMENT '
• PURPOSE: Returns aggregated sales metrics by state for regional analysis
• BEST FOR: "Compare sales by state" | "Which state has the highest revenue?" | "Regional performance"
• NOT FOR: Store-level detail within a state (use get_top_stores_by_revenue and filter)
• RETURNS: PRE-AGGREGATED rows by state (state, store_count, total_revenue, total_units, transaction_count, avg_revenue_per_store)
• PARAMS: start_date, end_date
• SYNTAX: SELECT * FROM get_sales_by_state(''2024-01-01'', ''2024-12-31'')
• NOTE: DO NOT add GROUP BY - data is already aggregated by state | Sorted by total_revenue DESC
'
RETURN
  SELECT 
    ds.state,
    COUNT(DISTINCT fsd.store_number) as store_count,
    SUM(fsd.net_revenue) as total_revenue,
    SUM(fsd.net_units) as total_units,
    SUM(fsd.transaction_count) as transaction_count,
    SUM(fsd.net_revenue) / NULLIF(COUNT(DISTINCT fsd.store_number), 0) as avg_revenue_per_store
  FROM {catalog}.{schema}.fact_sales_daily fsd
  LEFT JOIN {catalog}.{schema}.dim_store ds 
    ON fsd.store_number = ds.store_number 
    AND ds.is_current = true
  WHERE fsd.transaction_date BETWEEN CAST(start_date AS DATE) AND CAST(end_date AS DATE)
  GROUP BY ds.state
  ORDER BY total_revenue DESC;
```

---

## Example 5: Temporal Trend Pattern — `get_daily_sales_trend`

**Pattern demonstrated:** Time-series analysis with day-of-week context from date dimension

```sql
CREATE OR REPLACE FUNCTION {catalog}.{schema}.get_daily_sales_trend(
  start_date STRING COMMENT 'Start date (format: YYYY-MM-DD)',
  end_date STRING COMMENT 'End date (format: YYYY-MM-DD)'
)
RETURNS TABLE(
  transaction_date DATE COMMENT 'Transaction date',
  day_of_week_name STRING COMMENT 'Day name (Monday, Tuesday, etc.)',
  is_weekend BOOLEAN COMMENT 'Weekend indicator (true for Saturday/Sunday)',
  total_revenue DECIMAL(18,2) COMMENT 'Daily revenue',
  total_units BIGINT COMMENT 'Daily units',
  transaction_count BIGINT COMMENT 'Daily transactions',
  unique_stores BIGINT COMMENT 'Stores with sales that day'
)
COMMENT '
• PURPOSE: Returns daily sales trend with day-of-week context for pattern analysis
• BEST FOR: "Show me daily sales trend for last month" | "What is the revenue by day?" | "Weekend vs weekday sales"
• RETURNS: Individual daily rows (transaction_date, day_of_week_name, is_weekend, total_revenue, total_units, transaction_count, unique_stores)
• PARAMS: start_date, end_date
• SYNTAX: SELECT * FROM get_daily_sales_trend(''2024-01-01'', ''2024-01-31'')
• NOTE: Join to dim_date for day_of_week context | Sorted by transaction_date ASC
'
RETURN
  SELECT 
    fsd.transaction_date,
    dd.day_of_week_name,
    dd.is_weekend,
    SUM(fsd.net_revenue) as total_revenue,
    SUM(fsd.net_units) as total_units,
    SUM(fsd.transaction_count) as transaction_count,
    COUNT(DISTINCT fsd.store_number) as unique_stores
  FROM {catalog}.{schema}.fact_sales_daily fsd
  LEFT JOIN {catalog}.{schema}.dim_date dd 
    ON fsd.transaction_date = dd.date
  WHERE fsd.transaction_date BETWEEN CAST(start_date AS DATE) AND CAST(end_date AS DATE)
  GROUP BY fsd.transaction_date, dd.day_of_week_name, dd.is_weekend
  ORDER BY fsd.transaction_date;
```

---

## Pattern Summary

| Example | Pattern | Key Technique | Top N? | Dimension Join |
|---------|---------|---------------|--------|----------------|
| 1. get_top_stores_by_revenue | Top N Ranking | ROW_NUMBER + WHERE rank <= top_n | Yes | SCD2 (is_current) |
| 2. get_store_performance | Entity Drilldown | Filter by entity ID, daily granularity | No | SCD2 (is_current) |
| 3. get_top_products | Multi-Dimension Ranking | ROW_NUMBER + category context | Yes | SCD1 (no is_current) |
| 4. get_sales_by_state | Geographic Aggregation | GROUP BY geography, per-entity averages | No | SCD2 (is_current) |
| 5. get_daily_sales_trend | Temporal Trend | Date dimension join, day-of-week context | No | Date dimension |

## Adapting to Other Domains

These retail examples map to any domain:

| Retail Pattern | Healthcare Equivalent | Finance Equivalent | Hospitality Equivalent |
|---|---|---|---|
| get_top_stores_by_revenue | get_top_hospitals_by_volume | get_top_accounts_by_transactions | get_top_properties_by_bookings |
| get_store_performance | get_hospital_performance | get_account_performance | get_property_performance |
| get_top_products | get_top_procedures | get_top_products_by_volume | get_top_amenities |
| get_sales_by_state | get_patients_by_region | get_transactions_by_region | get_bookings_by_destination |
| get_daily_sales_trend | get_daily_admissions_trend | get_daily_transaction_trend | get_daily_booking_trend |
