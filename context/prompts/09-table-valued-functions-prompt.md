# Table-Valued Functions (TVFs) Creation Prompt

## 🚀 Quick Start (1 hour)

**Goal:** Create pre-built, parameterized SQL queries for common business questions

**What You'll Create:**
1. `table_valued_functions.sql` - SQL file with 10-15 TVF definitions
2. `tvf_job.yml` - Asset Bundle job (SQL task)

**Fast Track:**
```sql
-- Pattern: CREATE OR REPLACE FUNCTION {name}({params}) RETURNS TABLE
CREATE OR REPLACE FUNCTION get_top_stores_by_revenue(
    start_date DATE,
    end_date DATE,
    top_n INT
)
RETURNS TABLE
COMMENT 'Returns top N stores by total revenue for date range'
AS
    SELECT store_name, SUM(net_revenue) as total_revenue
    FROM fact_sales_daily
    JOIN dim_store USING (store_number)
    WHERE transaction_date BETWEEN start_date AND end_date
    GROUP BY store_name
    ORDER BY total_revenue DESC
    LIMIT top_n;
```

**Critical SQL Rules:**
- ⚠️ Parameter types MUST be explicitly typed (DATE, STRING, INT)
- ⚠️ Parameters go in ORDER BY/WHERE - NOT in LIMIT clause
- ⚠️ Always use `RETURNS TABLE` (not `RETURNS INT` etc.)

**Common Business Patterns:**
- **Top N:** `get_top_{entity}_by_{metric}(start_date, end_date, top_n)`
- **Trending:** `get_{metric}_trend(start_date, end_date, granularity)`
- **Comparison:** `get_{entity}_comparison(entity_list, start_date, end_date)`
- **Performance:** `get_{entity}_performance(entity_id, start_date, end_date)`

**Output:** 10-15 TVFs callable by Genie and queryable via SQL

📖 **Full guide below** for detailed patterns →

---

## Quick Reference

**Use this prompt when creating Table-Valued Functions for Genie Spaces in any Databricks project.**

---

## 📋 Your Requirements (Fill These In First)

**Before creating TVFs, gather these business requirements:**

### Project Context
- **Project Name:** _________________ (e.g., retail_analytics, patient_outcomes)
- **Gold Catalog.Schema:** _________________ (e.g., my_catalog.my_project_gold)
- **Primary Fact Table:** _________________ (e.g., fact_sales_daily, fact_encounters)
- **Key Dimensions:** _________________ (e.g., store, product, date)

### Common Business Questions (10-15 questions)

List the questions your users frequently ask:

| # | Question | TVF Name | Parameters Needed |
|---|----------|----------|-------------------|
| 1 | "What are the top 10 {entities} by {metric}?" | get_top_{entity}_by_{metric} | start_date, end_date, top_n |
| 2 | "How did {entity} X perform last week?" | get_{entity}_performance | {entity}_id, start_date, end_date |
| 3 | "Show me {metric} by {dimension}" | get_{metric}_by_{dimension} | start_date, end_date |
| 4 | _____________________ | _______________ | _________________ |
| 5 | _____________________ | _______________ | _________________ |

**Example - Retail:**
- "What are the top 10 stores by revenue?" → `get_top_stores_by_revenue(start_date, end_date, top_n)`
- "How did store 12345 perform last month?" → `get_store_performance(store_number, start_date, end_date)`

**Example - Healthcare:**
- "What are the top hospitals by patient volume?" → `get_top_hospitals_by_volume(start_date, end_date, top_n)`
- "Show me readmission rates by diagnosis" → `get_readmission_by_diagnosis(start_date, end_date)`

**Example - Finance:**
- "What are the highest transaction accounts?" → `get_top_accounts_by_transactions(start_date, end_date, top_n)`
- "Show me fraud cases by merchant" → `get_fraud_by_merchant(start_date, end_date)`

### Gold Layer Tables Available

| Table Name | Type | Primary Use |
|-----------|------|-------------|
| _________ | Dimension | ___________ |
| _________ | Fact | ___________ |
| _________ | Dimension | ___________ |

### Key Measures to Include

| Measure Name | Aggregation | Description |
|-------------|-------------|-------------|
| total_revenue | SUM(net_revenue) | Total sales revenue |
| _____________ | ______________ | ______________ |
| _____________ | ______________ | ______________ |

---

## Input Required Summary
- Gold layer tables (dimensions and facts)
- Common business questions (from stakeholders)
- Date range requirements (reporting periods)
- Top N requirements (rankings, leaderboards)

**Output:** 10-15 TVFs optimized for Genie natural language queries with LLM-friendly metadata.

**Time Estimate:** 2-3 hours

---

## Core Philosophy: Pre-Built Queries for Natural Language

**⚠️ CRITICAL PRINCIPLE:**

Table-Valued Functions (TVFs) provide **pre-built, parameterized queries** that Genie can invoke:

- ✅ **Parameterized Queries:** Reusable functions with input parameters
- ✅ **LLM-Friendly Metadata:** Rich comments for Genie understanding
- ✅ **Genie-Compatible Types:** STRING for dates, not DATE
- ✅ **Top N Patterns:** Use WHERE rank <= param (not LIMIT param)
- ✅ **Null Safety:** NULLIF for all divisions
- ❌ **No DATE Parameters:** Genie doesn't support DATE type
- ❌ **No LIMIT with Parameters:** Use ROW_NUMBER + WHERE instead

**Why This Matters:**
- Pre-built queries ensure consistent business logic
- LLM metadata helps Genie understand when to use each function
- Proper SQL patterns prevent compile-time errors
- Users get instant answers to common questions

---

## Critical SQL Requirements

### ⚠️ Issue 1: Parameter Types for Genie

**RULE: Use STRING for date parameters, NEVER DATE**

Genie Spaces do not support DATE type parameters. Always use STRING with explicit format documentation.

#### ❌ DON'T: Use DATE parameters
```sql
CREATE OR REPLACE FUNCTION get_sales_by_date_range(
  start_date DATE COMMENT 'Start date',
  end_date DATE COMMENT 'End date'
)
-- ERROR: Parameter start_date has an unsupported type: date
```

#### ✅ DO: Use STRING parameters with CAST
```sql
CREATE OR REPLACE FUNCTION get_sales_by_date_range(
  start_date STRING COMMENT 'Start date (format: YYYY-MM-DD)',
  end_date STRING COMMENT 'End date (format: YYYY-MM-DD)'
)
...
WHERE transaction_date BETWEEN CAST(start_date AS DATE) AND CAST(end_date AS DATE)
```

---

### ⚠️ Issue 2: Parameter Ordering

**RULE: Required parameters MUST come before optional parameters**

#### ❌ DON'T: Mix DEFAULT and non-DEFAULT parameters
```sql
CREATE OR REPLACE FUNCTION get_top_stores(
  top_n INT DEFAULT 10,          -- ❌ DEFAULT parameter first
  start_date STRING,              -- ❌ Required parameter after DEFAULT
  end_date STRING                 -- ❌ Required parameter after DEFAULT
)
-- ERROR: parameter with DEFAULT must not be followed by parameter without DEFAULT
```

#### ✅ DO: Required parameters first
```sql
CREATE OR REPLACE FUNCTION get_top_stores(
  start_date STRING,              -- ✅ Required parameter first
  end_date STRING,                -- ✅ Required parameter second
  top_n INT DEFAULT 10            -- ✅ Optional parameter last
)
```

---

### ⚠️ Issue 3: LIMIT Clauses

**RULE: Use WHERE rank <= param, NEVER LIMIT param**

LIMIT clauses require compile-time constants. Use ROW_NUMBER() with WHERE instead.

#### ❌ DON'T: Use parameter in LIMIT
```sql
SELECT * FROM store_metrics
ORDER BY total_revenue DESC
LIMIT top_n;  -- ❌ ERROR: limit expression must evaluate to a constant value
```

#### ✅ DO: Use ROW_NUMBER with WHERE
```sql
WITH ranked_stores AS (
  SELECT *,
    ROW_NUMBER() OVER (ORDER BY total_revenue DESC) as rank
  FROM store_metrics
)
SELECT * FROM ranked_stores
WHERE rank <= top_n  -- ✅ Parameters work in WHERE
ORDER BY rank;
```

---

## Step 1: Identify Common Business Questions

### Question Categories

**Revenue Questions:**
- "What are the top 10 stores by revenue?"
- "Show me sales for store X this month"
- "What's the revenue by product category?"

**Product Questions:**
- "What are the top 5 selling products?"
- "Show me sales for product category X"
- "Which products are underperforming?"

**Store Questions:**
- "How is store X performing?"
- "Compare stores by state"
- "Which stores have declining sales?"

**Trend Questions:**
- "Show me daily sales trend"
- "What's the month-over-month growth?"
- "Weekend vs weekday sales"

### TVF Planning Table

| Question Pattern | TVF Name | Parameters |
|----------------|---------|------------|
| Top N stores by revenue | `get_top_stores_by_revenue` | start_date, end_date, top_n |
| Store performance details | `get_store_performance` | store_number, start_date, end_date |
| Top N products | `get_top_products` | start_date, end_date, top_n |
| Sales by category | `get_sales_by_category` | start_date, end_date |
| Daily trend | `get_daily_sales_trend` | start_date, end_date |
| State comparison | `get_sales_by_state` | start_date, end_date |

---

## Step 2: TVF Template (All Rules Applied)

### Complete TVF Pattern

```sql
-- =============================================================================
-- TVF: {function_name}
-- Description: {What this function does}
-- Use cases: {When Genie should use this}
-- =============================================================================

CREATE OR REPLACE FUNCTION {catalog}.{schema}.{function_name}(
  -- ===== REQUIRED PARAMETERS (no DEFAULT) =====
  start_date STRING COMMENT 'Start date for analysis period (format: YYYY-MM-DD)',
  end_date STRING COMMENT 'End date for analysis period (format: YYYY-MM-DD)',
  
  -- ===== OPTIONAL PARAMETERS (with DEFAULT) =====
  top_n INT DEFAULT 10 COMMENT 'Number of records to return (default: 10)'
)
RETURNS TABLE(
  -- ===== RETURNED COLUMNS (all documented) =====
  rank INT COMMENT 'Ranking position based on {metric}',
  {dimension}_key STRING COMMENT '{Dimension} identifier',
  {dimension}_name STRING COMMENT '{Dimension} display name',
  total_revenue DECIMAL(18,2) COMMENT 'Total revenue for the period',
  total_units BIGINT COMMENT 'Total units sold',
  transaction_count BIGINT COMMENT 'Number of transactions',
  avg_transaction_value DECIMAL(18,2) COMMENT 'Average value per transaction'
)
-- ===== LLM-FRIENDLY FUNCTION COMMENT =====
COMMENT 'LLM: {Brief description}. Use this for {use cases}. 
Parameters: start_date (YYYY-MM-DD), end_date (YYYY-MM-DD), optional top_n (default 10). 
Example: "{Natural language question 1}" or "{Natural language question 2}"'

RETURN
  WITH base_metrics AS (
    -- Aggregate from fact table
    SELECT 
      f.{dimension}_key,
      d.{dimension}_name,
      SUM(f.net_revenue) as total_revenue,
      SUM(f.net_units) as total_units,
      SUM(f.transaction_count) as transaction_count
    FROM {catalog}.{schema}.{fact_table} f
    -- Join to dimension (filter for current records if SCD2)
    LEFT JOIN {catalog}.{schema}.{dim_table} d 
      ON f.{dimension}_key = d.{dimension}_key 
      AND d.is_current = true
    -- Cast STRING dates to DATE for filtering
    WHERE f.transaction_date BETWEEN CAST(start_date AS DATE) AND CAST(end_date AS DATE)
    GROUP BY f.{dimension}_key, d.{dimension}_name
  ),
  ranked_results AS (
    SELECT 
      -- Rank using ROW_NUMBER (for parameterized top N)
      ROW_NUMBER() OVER (ORDER BY total_revenue DESC) as rank,
      {dimension}_key,
      {dimension}_name,
      total_revenue,
      total_units,
      transaction_count,
      -- Null-safe division
      total_revenue / NULLIF(transaction_count, 0) as avg_transaction_value
    FROM base_metrics
  )
  -- Filter by rank (not LIMIT) to support parameterized top N
  SELECT * FROM ranked_results
  WHERE rank <= top_n
  ORDER BY rank;
```

---

## Step 3: Standard TVF Examples

### 3.1 Top Stores by Revenue

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
COMMENT 'LLM: Returns the top N stores ranked by revenue for a date range. 
Use this for store performance analysis, regional comparisons, and identifying 
best performers. Parameters: start_date, end_date, optional top_n (default 10). 
Example: "What are the top 10 stores by revenue this month?" or 
"Show me the best performing stores"'
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

### 3.2 Store Performance Details

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
COMMENT 'LLM: Returns detailed daily performance metrics for a specific store. 
Use this for store-level deep dives, identifying trends, and comparing to benchmarks. 
Parameters: store_number, start_date, end_date. 
Example: "How did store 12345 perform last week?" or 
"Show me daily sales for store 12345"'
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

### 3.3 Top Products by Revenue

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
COMMENT 'LLM: Returns top N products ranked by revenue for a date range. 
Use this for product performance analysis, category insights, and bestseller identification. 
Parameters: start_date, end_date, optional top_n (default 10). 
Example: "What are the top 5 selling products?" or 
"Show me best performing products this quarter"'
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

### 3.4 Sales by State

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
COMMENT 'LLM: Returns aggregated sales metrics by state. 
Use this for regional analysis, geographic comparisons, and market sizing. 
Parameters: start_date, end_date. 
Example: "Compare sales by state" or "Which state has the highest revenue?"'
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

### 3.5 Daily Sales Trend

```sql
CREATE OR REPLACE FUNCTION {catalog}.{schema}.get_daily_sales_trend(
  start_date STRING COMMENT 'Start date (format: YYYY-MM-DD)',
  end_date STRING COMMENT 'End date (format: YYYY-MM-DD)'
)
RETURNS TABLE(
  transaction_date DATE COMMENT 'Transaction date',
  day_of_week_name STRING COMMENT 'Day name (Monday, etc.)',
  is_weekend BOOLEAN COMMENT 'Weekend indicator',
  total_revenue DECIMAL(18,2) COMMENT 'Daily revenue',
  total_units BIGINT COMMENT 'Daily units',
  transaction_count BIGINT COMMENT 'Daily transactions',
  unique_stores BIGINT COMMENT 'Stores with sales'
)
COMMENT 'LLM: Returns daily sales trend with day-of-week context. 
Use this for trend analysis, identifying patterns, and comparing weekdays vs weekends. 
Parameters: start_date, end_date. 
Example: "Show me daily sales trend for last month" or 
"What is the revenue by day?"'
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

## Step 4: Create TVF SQL File

### File: `src/{project}_gold/table_valued_functions.sql`

```sql
-- =============================================================================
-- {Project} Gold Layer - Table-Valued Functions for Genie
-- 
-- This file contains parameterized functions optimized for Genie Spaces.
-- Each function includes LLM-friendly metadata for natural language understanding.
--
-- Key Patterns:
-- 1. STRING for date parameters (Genie doesn't support DATE type)
-- 2. Required parameters first, optional (DEFAULT) parameters last
-- 3. ROW_NUMBER + WHERE for Top N (not LIMIT with parameter)
-- 4. NULLIF for all divisions (null safety)
-- 5. is_current = true for SCD2 dimension joins
--
-- Usage: Deploy via gold_setup_job or setup_orchestrator_job
-- =============================================================================

-- Set context
USE CATALOG ${catalog};
USE SCHEMA ${gold_schema};

-- =============================================================================
-- TVF 1: Get Top Stores by Revenue
-- =============================================================================
-- {paste get_top_stores_by_revenue from above}

-- =============================================================================
-- TVF 2: Get Store Performance
-- =============================================================================
-- {paste get_store_performance from above}

-- =============================================================================
-- TVF 3: Get Top Products
-- =============================================================================
-- {paste get_top_products from above}

-- =============================================================================
-- TVF 4: Get Sales by State
-- =============================================================================
-- {paste get_sales_by_state from above}

-- =============================================================================
-- TVF 5: Get Daily Sales Trend
-- =============================================================================
-- {paste get_daily_sales_trend from above}

-- Add 5-10 more TVFs based on business requirements...
```

---

## Step 5: Asset Bundle Configuration

### File: `resources/gold_setup_job.yml` (Add TVF Task)

```yaml
resources:
  jobs:
    gold_setup_job:
      name: "[${bundle.target}] {Project} Gold Layer - Setup"
      
      tasks:
        # ... existing table creation tasks ...
        
        # Add TVF creation task
        - task_key: create_table_valued_functions
          depends_on:
            - task_key: create_gold_tables
          sql_task:
            warehouse_id: ${var.warehouse_id}
            file:
              path: ../src/{project}_gold/table_valued_functions.sql
            parameters:
              catalog: ${var.catalog}
              gold_schema: ${var.gold_schema}
      
      tags:
        environment: ${bundle.target}
        layer: gold
        job_type: setup
```

---

## Implementation Checklist

### Phase 1: Planning (30 min)
- [ ] List 10-15 common business questions
- [ ] Categorize questions (revenue, product, store, trend)
- [ ] Map questions to TVF names and parameters
- [ ] Identify required vs optional parameters

### Phase 2: SQL Development (1-2 hours)
- [ ] Create `table_valued_functions.sql`
- [ ] Implement each TVF following the template
- [ ] Verify all date parameters are STRING type
- [ ] Verify parameter ordering (required first)
- [ ] Verify Top N uses ROW_NUMBER + WHERE (not LIMIT)
- [ ] Verify all divisions use NULLIF
- [ ] Verify SCD2 joins include `is_current = true`

### Phase 3: Metadata (30 min)
- [ ] Add function-level COMMENT with "LLM:" prefix
- [ ] Add 2+ example questions per function
- [ ] Add COMMENT to every parameter
- [ ] Add COMMENT to every returned column
- [ ] Include format hints for STRING dates

### Phase 4: Testing (30 min)
- [ ] Compile each function (no syntax errors)
- [ ] Execute with valid parameters
- [ ] Test edge cases (empty results, null values)
- [ ] Verify results match expectations

### Phase 5: Deployment
- [ ] Add to gold_setup_job.yml
- [ ] Deploy: `databricks bundle deploy -t dev`
- [ ] Run: `databricks bundle run gold_setup_job`
- [ ] Test in Genie Space (if applicable)

---

## TVF Creation Checklist

### SQL Compliance
- [ ] All date parameters are STRING type (not DATE)
- [ ] Required parameters come before optional parameters
- [ ] No parameters used in LIMIT clauses
- [ ] All divisions use NULLIF
- [ ] SCD2 joins include `is_current = true`

### Genie Optimization
- [ ] Function COMMENT starts with "LLM:"
- [ ] Function COMMENT includes use cases
- [ ] Function COMMENT includes 2+ example questions
- [ ] All parameters have descriptive COMMENT
- [ ] String parameters include format (e.g., "format: YYYY-MM-DD")
- [ ] All returned columns have COMMENT
- [ ] Column names are business-friendly

---

## Key Principles

### 1. STRING for Dates, Always
```sql
-- ✅ Correct
start_date STRING COMMENT 'Start date (format: YYYY-MM-DD)'

-- ❌ Wrong
start_date DATE COMMENT 'Start date'
```

### 2. Required Parameters First
```sql
-- ✅ Correct order
(start_date STRING, end_date STRING, top_n INT DEFAULT 10)

-- ❌ Wrong order
(top_n INT DEFAULT 10, start_date STRING, end_date STRING)
```

### 3. ROW_NUMBER for Top N
```sql
-- ✅ Correct
WHERE rank <= top_n

-- ❌ Wrong
LIMIT top_n
```

### 4. NULLIF for Divisions
```sql
-- ✅ Correct
revenue / NULLIF(transactions, 0)

-- ❌ Wrong
revenue / transactions
```

### 5. LLM-Friendly Comments
```sql
-- ✅ Correct
COMMENT 'LLM: Returns top N stores by revenue. Use this for store rankings. 
Example: "What are the top 10 stores?"'

-- ❌ Wrong
COMMENT 'Gets store data'
```

---

## Common Mistakes to Avoid

### ❌ Mistake 1: DATE Parameters
```sql
-- Will fail in Genie
start_date DATE COMMENT 'Start date'
```

### ❌ Mistake 2: Wrong Parameter Order
```sql
-- Will fail to compile
CREATE FUNCTION f(optional INT DEFAULT 10, required STRING)
```

### ❌ Mistake 3: LIMIT with Parameter
```sql
-- Will fail to compile
SELECT * FROM data LIMIT top_n
```

### ❌ Mistake 4: Missing Null Safety
```sql
-- Can fail with divide by zero
revenue / transactions
```

### ❌ Mistake 5: Poor Metadata
```sql
-- Won't be discoverable by Genie
COMMENT 'Gets data'
```

---

## Validation Queries

```sql
-- List all TVFs in schema
SHOW FUNCTIONS IN {catalog}.{schema}
WHERE function_name LIKE 'get_%';

-- View function details
DESCRIBE FUNCTION EXTENDED {catalog}.{schema}.get_top_stores_by_revenue;

-- Test function execution
SELECT * FROM {catalog}.{schema}.get_top_stores_by_revenue(
  '2024-01-01', 
  '2024-12-31', 
  5
);

-- Test with default parameter
SELECT * FROM {catalog}.{schema}.get_top_stores_by_revenue(
  '2024-01-01', 
  '2024-12-31'
);
-- Should return 10 rows (default top_n)
```

---

## References

### Official Documentation
- [Databricks Table-Valued Functions](https://docs.databricks.com/sql/language-manual/sql-ref-syntax-qry-select-tvf)
- [Genie Trusted Assets - Functions](https://docs.databricks.com/genie/trusted-assets#tips-for-writing-functions)
- [SQL UDF Best Practices](https://docs.databricks.com/sql/language-manual/sql-ref-syntax-ddl-create-sql-function)

### Framework Rules
- [databricks-table-valued-functions.mdc](mdc:framework/rules/15-databricks-table-valued-functions.mdc)
- [genie-space-patterns.mdc](mdc:framework/rules/16-genie-space-patterns.mdc)

---

## Summary

**What to Create:**
1. `table_valued_functions.sql` - 10-15 TVFs with LLM-friendly metadata
2. Add to `gold_setup_job.yml` - SQL task for deployment

**Critical Rules:**
- STRING for dates (not DATE)
- Required params first, DEFAULT params last
- ROW_NUMBER + WHERE for Top N (not LIMIT)
- NULLIF for all divisions
- LLM: prefix in function comments

**Time Estimate:** 2-3 hours

**Next Action:** Identify common questions, create TVF SQL file, deploy, test in Genie


