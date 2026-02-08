# Genie Integration Guide

Complete guide for optimizing TVFs for Genie Space natural language queries, including comment format, common misuse patterns, and professional language standards.

## Standardized TVF Comment Format (v3.0)

**Problems with unstructured comments:**
- Genie didn't know what questions the TVF was best for
- Column names weren't explicit, causing UNRESOLVED_COLUMN errors
- No guidance on when NOT to use the TVF
- Missing syntax examples led to wrong parameter formats

**Use this standardized bullet-point format for ALL TVF comments:**

```sql
COMMENT '
• PURPOSE: [One-line description of what the TVF does]
• BEST FOR: [Example questions separated by |]
• NOT FOR: [What to avoid - redirect to correct TVF] (optional)
• RETURNS: [PRE-AGGREGATED rows or Individual rows] (exact column list)
• PARAMS: [Parameter names with defaults]
• SYNTAX: SELECT * FROM tvf_name(''param1'', ''param2'')
• NOTE: [Important caveats - DO NOT wrap in TABLE(), etc.] (optional)
'
```

## Example 1: Aggregate TVF (Returns Pre-Aggregated Rows)

```sql
CREATE OR REPLACE FUNCTION get_customer_segments(
  start_date STRING COMMENT 'Start date (format: YYYY-MM-DD)',
  end_date STRING COMMENT 'End date (format: YYYY-MM-DD)'
)
RETURNS TABLE(
  segment_name STRING COMMENT 'Customer segment category',
  customer_count BIGINT COMMENT 'Number of customers in segment',
  total_bookings BIGINT COMMENT 'Total bookings from segment',
  total_revenue DECIMAL(18,2) COMMENT 'Total revenue from segment',
  avg_booking_value DECIMAL(18,2) COMMENT 'Average booking value'
)
COMMENT '
• PURPOSE: Customer behavioral segmentation with booking patterns and revenue metrics
• BEST FOR: "What are our customer segments?" | "Segment performance" | "How many VIP customers?"
• NOT FOR: VIP property preferences (use get_vip_customer_property_preferences) | Individual customer details
• RETURNS: 5 PRE-AGGREGATED rows (segment_name, customer_count, total_bookings, total_revenue, avg_booking_value)
• PARAMS: start_date, end_date (format: YYYY-MM-DD)
• SYNTAX: SELECT * FROM get_customer_segments(''2020-01-01'', ''2024-12-31'')
• NOTE: Column is "segment_name" NOT "segment" | DO NOT add GROUP BY - data is already aggregated
'
RETURN
  ...
```

**Key characteristics of aggregate TVFs:**
- Returns fixed number of rows (e.g., 5 segment rows)
- Data is PRE-AGGREGATED - no GROUP BY needed on top
- Do NOT use in JOINs (no user_id or other keys to join on)

## Example 2: Individual Row TVF (Returns Detail Rows)

```sql
CREATE OR REPLACE FUNCTION get_customer_ltv(
  start_date STRING COMMENT 'Start date (format: YYYY-MM-DD)',
  end_date STRING COMMENT 'End date (format: YYYY-MM-DD)',
  top_n INT DEFAULT 100 COMMENT 'Number of top customers to return'
)
RETURNS TABLE(
  rank BIGINT COMMENT 'Customer rank by lifetime value',
  user_id BIGINT COMMENT 'Customer identifier',
  country STRING COMMENT 'Customer country',
  user_type STRING COMMENT 'User type (individual/business)',
  total_bookings BIGINT COMMENT 'Total bookings',
  lifetime_value DECIMAL(18,2) COMMENT 'Total revenue from customer'
)
COMMENT '
• PURPOSE: Individual customer lifetime value with ranking and booking history
• BEST FOR: "Show VIP customers" | "Most valuable customers" | "Top customers by spend"
• RETURNS: Individual customer rows (rank, user_id, country, user_type, total_bookings, lifetime_value)
• PARAMS: start_date, end_date, top_n (default: 100)
• SYNTAX: SELECT * FROM get_customer_ltv(''2020-01-01'', ''2024-12-31'')
• NOTE: Returns user_id for individual customer analysis | Sorted by lifetime_value DESC
'
RETURN
  ...
```

**Key characteristics of individual row TVFs:**
- Returns variable number of rows based on data
- Each row represents one entity (customer, property, host)
- CAN be used in JOINs (has identifier columns)

## Example 3: TVF with Limitations (Redirect Pattern)

```sql
COMMENT '
• PURPOSE: Comprehensive host performance metrics with accurate revenue from booking transactions
• BEST FOR: "Top performing hosts" | "Impact of verification on performance" | "Host KPIs"
• PREFERRED OVER: host_analytics_metrics (which has join path limitations)
• RETURNS: Individual host rows (host_id, host_name, is_verified, rating, property_count, total_bookings, total_revenue)
• PARAMS: start_date, end_date, top_n (default: 100)
• SYNTAX: SELECT * FROM get_host_performance(''2020-01-01'', ''2024-12-31'')
• NOTE: Returns ACCURATE revenue totals (~$40M) vs metric view (~$1K due to join issues)
'
```

## Key Elements Explained

| Element | Purpose | Why It Matters |
|---------|---------|----------------|
| **PURPOSE** | One-line description | Quick understanding for LLM |
| **BEST FOR** | Example questions (pipe-separated) | LLM matches user query to TVF |
| **NOT FOR** | Redirect to correct asset | Prevents wrong TVF selection |
| **PREFERRED OVER** | Alternative to problematic metric view | Steers away from broken assets |
| **RETURNS** | PRE-AGGREGATED vs Individual + columns | Prevents GROUP BY on aggregates, clarifies available columns |
| **PARAMS** | Parameter names and defaults | Prevents WRONG_NUM_ARGS errors |
| **SYNTAX** | Exact copyable example | Prevents TABLE() wrapper, wrong date format |
| **NOTE** | Critical caveats | Prevents common misuse patterns |

## Common Genie Misuse Patterns to Prevent

### 1. TABLE() Wrapper Error

```sql
-- ❌ WRONG: Genie sometimes wraps TVFs in TABLE()
SELECT * FROM TABLE(get_customer_segments('2020-01-01', '2024-12-31'))
-- Error: NOT_A_SCALAR_FUNCTION

-- ✅ CORRECT: Direct call
SELECT * FROM get_customer_segments('2020-01-01', '2024-12-31')
```

**Prevention:** Add to NOTE: "DO NOT wrap in TABLE()"

### 2. GROUP BY on Pre-Aggregated Data

```sql
-- ❌ WRONG: Adding GROUP BY to already-aggregated output
SELECT segment_name, SUM(total_revenue) 
FROM get_customer_segments('2020-01-01', '2024-12-31')
GROUP BY segment_name
-- Result: Same as without GROUP BY, but confusing

-- ✅ CORRECT: No GROUP BY needed
SELECT * FROM get_customer_segments('2020-01-01', '2024-12-31')
```

**Prevention:** Add to NOTE: "DO NOT add GROUP BY - data is already aggregated"

### 3. Wrong Column Name

```sql
-- ❌ WRONG: Using assumed column name
SELECT segment FROM get_customer_segments(...)
-- Error: UNRESOLVED_COLUMN

-- ✅ CORRECT: Use actual column name
SELECT segment_name FROM get_customer_segments(...)
```

**Prevention:** List exact column names in RETURNS

### 4. Missing Parameters

```sql
-- ❌ WRONG: No parameters when required
SELECT * FROM get_customer_segments()
-- Error: WRONG_NUM_ARGS

-- ✅ CORRECT: Include required parameters
SELECT * FROM get_customer_segments('2020-01-01', '2024-12-31')
```

**Prevention:** Include exact SYNTAX example with parameters

## Professional Language Standards

**❌ Avoid unprofessional language:**
```sql
-- BAD: Negative about other assets
COMMENT 'Use this because the metric view is broken and returns wrong data'
COMMENT 'This TVF actually works unlike the metric view'
```

**✅ Use professional, guiding language:**
```sql
-- GOOD: Professional redirect
COMMENT '
• PREFERRED OVER: host_analytics_metrics for revenue/booking queries (different join paths)
'

-- GOOD: Factual comparison
COMMENT '
• NOTE: Returns ACCURATE revenue totals (~$40M) vs metric view (~$1K)
'
```

## Legacy Format (Deprecated)

The following format is still supported but not recommended for new TVFs:

```sql
COMMENT 'LLM: [Brief description]. Use this for [use cases]. 
Parameters: [parameter list with formats]. 
Example: "[Natural language question 1]" or "[Natural language question 2]"'
```

**Migration:** When updating existing TVFs, convert to the new bullet-point format

## Best Practices Summary

1. **Always use bullet-point format** for structured comments
2. **Include PURPOSE** - One-line description
3. **Include BEST FOR** - 2+ example questions (pipe-separated)
4. **Include RETURNS** - Specify PRE-AGGREGATED or Individual + exact columns
5. **Include PARAMS** - Parameter names with defaults
6. **Include SYNTAX** - Exact copyable example with proper date format
7. **Include NOTE** - Caveats (DO NOT wrap in TABLE(), DO NOT add GROUP BY, etc.)
8. **Use professional language** - Avoid "broken", "doesn't work" phrases
9. **Redirect when needed** - Use NOT FOR or PREFERRED OVER to guide Genie
10. **List exact column names** - Prevents UNRESOLVED_COLUMN errors
