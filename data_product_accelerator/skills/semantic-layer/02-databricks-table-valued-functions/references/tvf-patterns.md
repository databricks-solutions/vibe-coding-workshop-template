# TVF SQL Patterns and Best Practices

Complete reference for SQL patterns, parameter types, schema validation, and cartesian product prevention.

## Schema Validation BEFORE Writing SQL

### ⚠️ CRITICAL: Rule #0

**RULE #0: Always consult YAML schema definitions before writing any TVF SQL**

**Case Study:** Wanderbricks TVF Deployment (Dec 10, 2025)
- 26 TVFs across 5 domains
- 6 deployment iterations
- 45 minutes of debugging
- 30+ individual column reference fixes

**Root Cause:** Assumed column names without consulting YAML schema files.

**100% of SQL compilation errors were caused by not consulting YAML schemas first.**

### Pre-Development Checklist (MANDATORY)

#### Step 1: Read YAML Schema Files (5 minutes)

```bash
# Navigate to schema definitions
cd gold_layer_design/yaml

# List all tables
find . -name "*.yaml" -type f

# Check actual column names for each table you'll reference
grep "^table_name:\|  - name:" geography/dim_destination.yaml
grep "^table_name:\|  - name:" identity/dim_host.yaml
grep "^table_name:\|  - name:" property/dim_property.yaml
grep "^table_name:\|  - name:" booking/fact_booking_daily.yaml

# Check for SCD Type 2 (requires is_current filter)
grep "^scd_type:" */dim_*.yaml
```

**What to Look For:**
- ✅ Actual column names (not assumptions)
- ✅ SCD Type 1 vs Type 2 (affects join syntax)
- ✅ Which columns are denormalized vs require joins
- ✅ Data types (INT vs BIGINT, DATE vs TIMESTAMP)

#### Step 2: Create SCHEMA_MAPPING.md (2 minutes)

Document the actual schema in a reference file:

```markdown
# TVF Schema Mapping Reference

## Dimensions

### dim_destination
- destination_id (BIGINT, PK)
- destination (STRING) -- ✅ NOT 'city'!
- state_or_province (STRING) -- ✅ NOT 'state'!
- country (STRING)
- SCD Type: 1 (no is_current)

### dim_property
- property_key (STRING, PK - surrogate)
- property_id (BIGINT, business key)
- host_id (BIGINT, FK)
- destination_id (BIGINT, FK)
- title (STRING)
- property_type (STRING)
- SCD Type: 2 (has is_current) -- ⚠️ Must filter!

## Common Join Patterns

```sql
-- SCD Type 2 dimension (has is_current)
LEFT JOIN dim_property dp 
  ON fbd.property_id = dp.property_id 
  AND dp.is_current = true  -- ✅ REQUIRED

-- SCD Type 1 dimension (no is_current)
LEFT JOIN dim_destination dd 
  ON fbd.destination_id = dd.destination_id
  -- ✅ No is_current filter needed
```
```

**Benefits:**
- Single source of truth for your TVF development
- Quick reference while coding
- Prevents 100% of column name errors
- Helps future developers

#### Step 3: Validate Live Schema (Optional but Recommended)

```sql
-- Verify actual column names in deployed tables
DESCRIBE TABLE catalog.schema.dim_destination;
DESCRIBE TABLE catalog.schema.dim_property;
DESCRIBE TABLE catalog.schema.fact_booking_daily;
```

### Common Schema Gotchas

#### 1. Column Name Variations

| What You Assume | What Actually Exists | Table |
|----------------|---------------------|-------|
| `city` | `destination` | dim_destination |
| `state` | `state_or_province` | dim_destination |
| `function_name` | `routine_name` | information_schema.routines |

**Lesson:** Never assume. Always check YAML.

#### 2. SCD Type 1 vs Type 2

**Type 1 (No history):**
```yaml
# dim_destination.yaml
scd_type: 1  # ✅ No is_current column

# SQL Join:
LEFT JOIN dim_destination dd 
  ON fbd.destination_id = dd.destination_id
  -- ✅ No is_current filter needed
```

**Type 2 (With history):**
```yaml
# dim_property.yaml
scd_type: 2  # ⚠️ Has is_current column!

# SQL Join:
LEFT JOIN dim_property dp 
  ON fbd.property_id = dp.property_id 
  AND dp.is_current = true  -- ✅ MUST filter for current version
```

**Common Error:** Forgetting `is_current = true` on SCD Type 2 joins results in duplicate rows.

#### 3. Denormalized vs Join Columns

**Check which columns exist in fact table:**

```yaml
# fact_booking_daily.yaml
columns:
  - property_id       # ✅ FK to dim_property
  - destination_id    # ✅ FK to dim_destination
  - booking_count     # ✅ Measure
  # ❌ NO host_id - Must join through dim_property
  # ❌ NO status - Use fact_booking_detail for transaction status
```

**Correct Query:**
```sql
-- ✅ Get host info via property dimension
SELECT 
  fbd.booking_count,
  dh.name as host_name  -- ✅ Join through property
FROM fact_booking_daily fbd
LEFT JOIN dim_property dp 
  ON fbd.property_id = dp.property_id 
  AND dp.is_current = true
LEFT JOIN dim_host dh 
  ON dp.host_id = dh.host_id 
  AND dh.is_current = true
```

**Wrong Query:**
```sql
-- ❌ Assumes host_id is denormalized
SELECT 
  fbd.booking_count,
  dh.name as host_name
FROM fact_booking_daily fbd
LEFT JOIN dim_host dh 
  ON fbd.host_id = dh.host_id  -- ❌ Column doesn't exist!
```

### ROI Analysis

| Activity | Time | When |
|----------|------|------|
| Read YAML schemas | 5 min | **Before coding** |
| Create SCHEMA_MAPPING.md | 2 min | **Before coding** |
| Run validation script | 30 sec | **Before deployment** |
| **Total Prep** | **~8 min** | **Upfront** |

**Without Schema Validation:**
- 6 deployment iterations
- 40 min debugging
- 30+ bug fixes
- Total: 45 min

**With Schema Validation:**
- 1 deployment iteration
- 0 min debugging
- 0 bugs
- Total: 8 min prep + 5 min deploy = 13 min

**ROI:** 71% time reduction (45 min → 13 min)  
**First-Time Success Rate:** 0% → 95%+

## Critical SQL Requirements

### Issue 1: Parameter Types for Genie Compatibility

**RULE: Use STRING for date parameters, not DATE**

Genie Spaces do not support DATE type parameters. Always use STRING with explicit format documentation.

#### ❌ DON'T: Use DATE parameters
```sql
CREATE OR REPLACE FUNCTION get_sales_by_date_range(
  start_date DATE COMMENT 'Start date',
  end_date DATE COMMENT 'End date'
)
...
WHERE transaction_date BETWEEN start_date AND end_date
```

**Error:**
```
Parameter start_date has an unsupported type: date
Parameter end_date has an unsupported type: date
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

**Benefits:**
- ✅ Works with Genie natural language processing
- ✅ Clear format documentation for users
- ✅ Type-safe conversion inside function

### Issue 2: Parameter Ordering with DEFAULT Values

**RULE: Parameters with DEFAULT must come AFTER parameters without DEFAULT**

SQL functions require all required parameters first, optional parameters last.

#### ❌ DON'T: Mix DEFAULT and non-DEFAULT parameters
```sql
CREATE OR REPLACE FUNCTION get_top_stores(
  top_n INT DEFAULT 10,          -- ❌ DEFAULT parameter first
  start_date STRING,              -- ❌ Required parameter after DEFAULT
  end_date STRING                 -- ❌ Required parameter after DEFAULT
)
```

**Error:**
```
[USER_DEFINED_FUNCTIONS.NOT_A_VALID_DEFAULT_PARAMETER_POSITION]
User defined function is invalid: parameter with DEFAULT must not be 
followed by parameter without DEFAULT.
```

#### ✅ DO: Required parameters first, optional last
```sql
CREATE OR REPLACE FUNCTION get_top_stores(
  start_date STRING,              -- ✅ Required parameter first
  end_date STRING,                -- ✅ Required parameter
  top_n INT DEFAULT 10            -- ✅ Optional parameter last
)
```

**Parameter Order Rules:**
1. All required parameters (no DEFAULT)
2. All optional parameters (with DEFAULT)
3. Never mix the two groups

### Issue 3: LIMIT Clauses Cannot Use Parameters

**RULE: Use WHERE rank <= parameter instead of LIMIT parameter**

LIMIT clauses require compile-time constants. Use WHERE with ROW_NUMBER() instead.

#### ❌ DON'T: Use parameter in LIMIT clause
```sql
RETURN
  WITH store_metrics AS (
    SELECT ...,
      ROW_NUMBER() OVER (ORDER BY total_revenue DESC) as rank
    FROM ...
  )
  SELECT * FROM store_metrics
  ORDER BY total_revenue DESC
  LIMIT top_n;  -- ❌ Cannot use parameter here
```

**Error:**
```
[INVALID_LIMIT_LIKE_EXPRESSION.IS_UNFOLDABLE]
The limit like expression "outer(get_top_stores.top_n)" is invalid.
The limit expression must evaluate to a constant value.
```

#### ✅ DO: Use WHERE clause with rank
```sql
RETURN
  WITH store_metrics AS (
    SELECT ... FROM ...
  ),
  ranked_stores AS (
    SELECT ...,
      ROW_NUMBER() OVER (ORDER BY total_revenue DESC) as rank
    FROM store_metrics
  )
  SELECT * FROM ranked_stores
  WHERE rank <= top_n  -- ✅ Can use parameter in WHERE
  ORDER BY rank;
```

**Why This Works:**
- `LIMIT` is evaluated at compile-time (needs constant)
- `WHERE` is evaluated at runtime (can use parameters)
- `WHERE rank <= N` achieves same result as `LIMIT N`

## Cartesian Product Bug Prevention

### ⚠️ CRITICAL: The Bug That Inflated Revenue by 254x

**Case Study:** Wanderbricks `get_revenue_by_period` TVF reported $35.8M revenue when actual was $141K.

**Root Cause:** Self-join on a table that was already aggregated in a CTE.

#### ❌ BUGGY PATTERN: Re-Joining After Aggregation

```sql
-- BUG: This pattern causes cartesian product!
CREATE FUNCTION get_revenue_by_period(...)
RETURN
  WITH period_data AS (
    -- First CTE: Aggregate revenue from fact table
    SELECT
      DATE_TRUNC(time_grain, fbd.check_in_date) AS period_start,
      period_name,
      SUM(fbd.total_booking_value) as total_revenue,  -- ✅ Aggregated here
      ...
    FROM ${catalog}.${schema}.fact_booking_daily fbd
    WHERE fbd.check_in_date BETWEEN ...
    GROUP BY DATE_TRUNC(...), period_name
  ),
  aggregated_periods AS (
    -- Second CTE: BUG - Re-joins the same table!
    SELECT
      pd.period_start,
      pd.period_name,
      SUM(pd.total_revenue) as total_revenue,  -- 🔥 ALREADY SUMMED!
      SUM(fbd.booking_count) as booking_count  -- 🔥 JOINED AGAIN
    FROM period_data pd
    LEFT JOIN ${catalog}.${schema}.fact_booking_daily fbd  -- ❌ CARTESIAN PRODUCT!
      ON DATE_TRUNC(time_grain, fbd.check_in_date) = pd.period_start
      AND fbd.check_in_date BETWEEN ...
    GROUP BY pd.period_start, pd.period_name
  )
  SELECT * FROM aggregated_periods;
```

**Why It's Wrong:**
1. `period_data` already aggregates from `fact_booking_daily` (e.g., 100 rows → 10 periods)
2. `aggregated_periods` joins `period_data` back to `fact_booking_daily`
3. Each period row matches ALL detail rows for that period
4. 1 period row × 100 matching detail rows = 100x multiplication
5. SUM() then adds these inflated values together

**Actual Bug Impact:**
- Expected revenue per week: ~$141K
- Actual buggy output: ~$35.8M  
- **Inflation factor: 254x**

#### ✅ CORRECT PATTERN: Single Aggregation, No Self-Join

```sql
-- CORRECT: Single aggregation pass, no self-join
CREATE FUNCTION get_revenue_by_period(...)
RETURN
  SELECT
    DATE_TRUNC(time_grain, fbd.check_in_date) AS period_start,
    CASE
      WHEN time_grain = 'week' THEN CONCAT('Week ', WEEKOFYEAR(fbd.check_in_date), ' ', YEAR(fbd.check_in_date))
      WHEN time_grain = 'month' THEN DATE_FORMAT(fbd.check_in_date, 'MMMM yyyy')
      ...
    END AS period_name,
    SUM(fbd.total_booking_value) as total_revenue,  -- ✅ Aggregate once
    SUM(fbd.booking_count) as booking_count,        -- ✅ Same aggregation pass
    SUM(fbd.cancellation_count) as cancellation_count,
    ...
  FROM ${catalog}.${schema}.fact_booking_daily fbd
  WHERE fbd.check_in_date BETWEEN CAST(start_date AS DATE) AND CAST(end_date AS DATE)
  GROUP BY DATE_TRUNC(time_grain, fbd.check_in_date), period_name
  ORDER BY period_start;
```

**Why It's Correct:**
- Single pass over `fact_booking_daily`
- All aggregations in same GROUP BY
- No CTEs that re-join the source table
- Results are accurate

### Detection Rules

**WARNING SIGN 1: CTE that aggregates, followed by join back to same source**
```sql
-- 🚨 WARNING: CTE1 reads from table_A, CTE2 joins table_A
WITH cte1 AS (
  SELECT ... SUM(...) FROM table_A ...
),
cte2 AS (
  SELECT ... FROM cte1 JOIN table_A ...  -- 🔥 DANGER!
)
```

**WARNING SIGN 2: SUM of a SUM**
```sql
-- 🚨 WARNING: Summing something that's already summed
SUM(already_aggregated_column)  -- Was this already a SUM()?
```

**WARNING SIGN 3: Dramatic result differences**
```
Metric view result:  $141K
TVF result:          $35.8M
Ratio:               254x  -- 🚨 Almost certainly a cartesian product!
```

### Prevention Checklist

**Before deploying any TVF with aggregations:**
- [ ] Each CTE aggregates from source tables ONLY ONCE
- [ ] No CTE re-joins a table that was already read in a prior CTE
- [ ] If multiple CTEs, they join to EACH OTHER, not back to source
- [ ] Results validated against known good source (metric view)
- [ ] Spot check: result order of magnitude matches expectations

**Validation Query:**
```sql
-- Compare TVF result to metric view result
WITH tvf_result AS (
  SELECT SUM(total_revenue) as tvf_total
  FROM get_revenue_by_period('2024-10-01', '2024-12-31', 'week')
),
metric_result AS (
  SELECT SUM(MEASURE(total_revenue)) as metric_total
  FROM revenue_analytics_metrics
  WHERE check_in_date BETWEEN '2024-10-01' AND '2024-12-31'
)
SELECT 
  tvf_total,
  metric_total,
  tvf_total / NULLIF(metric_total, 0) as ratio  -- Should be ~1.0
FROM tvf_result, metric_result;
```

**Expected:** ratio ≈ 1.0  
**Bug indicator:** ratio >> 1.0 (e.g., 254)

## Null Safety Best Practices

**RULE: Always use NULLIF() for division to prevent divide-by-zero errors**

```sql
-- ❌ DON'T: Direct division
total_revenue / transaction_count as avg_transaction_value

-- ✅ DO: Null-safe division
total_revenue / NULLIF(transaction_count, 0) as avg_transaction_value
```

## SCD Type 2 Dimension Handling

**RULE: Always filter for current records when joining SCD2 dimensions**

```sql
-- ✅ Correct: Filter for current version
LEFT JOIN dim_store ds 
  ON fsd.store_number = ds.store_number 
  AND ds.is_current = true
```

## Complete TVF Pattern (All Rules Applied)

```sql
-- Function: Get top performing stores by revenue
CREATE OR REPLACE FUNCTION get_top_stores_by_revenue(
  -- Required parameters first (no DEFAULT)
  start_date STRING COMMENT 'Start date (format: YYYY-MM-DD)',
  end_date STRING COMMENT 'End date (format: YYYY-MM-DD)',
  -- Optional parameters last (with DEFAULT)
  top_n INT DEFAULT 10 COMMENT 'Number of top stores to return'
)
RETURNS TABLE(
  -- Every column documented
  rank INT COMMENT 'Store rank by revenue',
  store_number STRING COMMENT 'Store identifier',
  store_name STRING COMMENT 'Store name',
  total_revenue DECIMAL(18,2) COMMENT 'Total revenue for period',
  total_units BIGINT COMMENT 'Total units sold',
  transaction_count BIGINT COMMENT 'Number of transactions',
  avg_transaction_value DECIMAL(18,2) COMMENT 'Average transaction value',
  unique_products BIGINT COMMENT 'Number of unique products sold'
)
RETURN
  WITH store_metrics AS (
    SELECT 
      store_number,
      store_name,
      SUM(net_revenue) as total_revenue,
      SUM(net_units) as total_units,
      SUM(transaction_count) as transaction_count,
      COUNT(DISTINCT upc_code) as unique_products
    FROM fact_sales_daily
    -- Cast STRING dates to DATE for comparison
    WHERE transaction_date BETWEEN CAST(start_date AS DATE) AND CAST(end_date AS DATE)
    GROUP BY store_number, store_name
  ),
  ranked_stores AS (
    SELECT 
      ROW_NUMBER() OVER (ORDER BY total_revenue DESC) as rank,
      store_number,
      store_name,
      total_revenue,
      total_units,
      transaction_count,
      total_revenue / NULLIF(transaction_count, 0) as avg_transaction_value,
      unique_products
    FROM store_metrics
  )
  -- Use WHERE rank <= parameter instead of LIMIT parameter
  SELECT * FROM ranked_stores
  WHERE rank <= top_n
  ORDER BY rank;
```

## SQL File Organization

When creating multiple TVFs, organize them in a single SQL file with clear section markers.

### File Path Convention

```
src/{project}_gold/table_valued_functions.sql
```

### File Structure Template

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
CREATE OR REPLACE FUNCTION get_top_stores_by_revenue(...)
...;

-- =============================================================================
-- TVF 2: Get Store Performance
-- =============================================================================
CREATE OR REPLACE FUNCTION get_store_performance(...)
...;

-- =============================================================================
-- TVF 3: Get Top Products
-- =============================================================================
CREATE OR REPLACE FUNCTION get_top_products(...)
...;

-- Continue for 10-15 TVFs based on business requirements...
```

**Key conventions:**
- Header comment block summarizes all key patterns
- `USE CATALOG` / `USE SCHEMA` with parameterized variables
- Section separators (`-- ===`) between each TVF
- Numbered sections for easy navigation
- See `references/tvf-examples.md` for 5 complete TVF implementations

## Asset Bundle Deployment

Deploy TVFs using a `sql_task` in your Asset Bundle job configuration.

### Job YAML: `resources/gold/tvf_job.yml`

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

**Key configuration:**
- `sql_task` (not `notebook_task`) for pure SQL files
- `warehouse_id` required for SQL task execution
- `depends_on` ensures Gold tables exist before TVFs reference them
- Parameters passed via `parameters` dict (substituted as `${catalog}`, `${gold_schema}`)
- Cross-reference `databricks-asset-bundles` skill for complete DAB patterns

## Post-Deployment Validation Queries

After deploying TVFs, run these queries to verify correctness. See `scripts/validate_tvfs.sql` for a ready-to-run script.

### List All TVFs in Schema

```sql
SHOW FUNCTIONS IN {catalog}.{schema}
WHERE function_name LIKE 'get_%';
```

### View Function Details

```sql
DESCRIBE FUNCTION EXTENDED {catalog}.{schema}.get_top_stores_by_revenue;
```

### Test Function Execution

```sql
-- With explicit parameters
SELECT * FROM {catalog}.{schema}.get_top_stores_by_revenue(
  '2024-01-01', 
  '2024-12-31', 
  5
);

-- With default parameter (should return 10 rows)
SELECT * FROM {catalog}.{schema}.get_top_stores_by_revenue(
  '2024-01-01', 
  '2024-12-31'
);
```

### Validate Against Metric View

Compare TVF totals to metric view totals. Ratio should be approximately 1.0. If ratio >> 1.0 (e.g., 254), there is a cartesian product bug — see the Cartesian Product Bug Prevention section above.

```sql
WITH tvf_result AS (
  SELECT SUM(total_revenue) as tvf_total
  FROM {catalog}.{schema}.get_top_stores_by_revenue('2024-01-01', '2024-12-31', 999999)
),
metric_result AS (
  SELECT SUM(MEASURE(total_revenue)) as metric_total
  FROM {catalog}.{schema}.{metric_view_name}
  WHERE transaction_date BETWEEN '2024-01-01' AND '2024-12-31'
)
SELECT 
  tvf_total,
  metric_total,
  tvf_total / NULLIF(metric_total, 0) as ratio  -- Should be ~1.0
FROM tvf_result, metric_result;
```
