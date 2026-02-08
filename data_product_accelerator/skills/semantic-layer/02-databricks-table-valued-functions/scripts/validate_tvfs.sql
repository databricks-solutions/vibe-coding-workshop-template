-- =============================================================================
-- TVF Validation Queries
-- Run these after deploying TVFs to verify correctness
-- Replace {catalog} and {schema} with actual values
-- =============================================================================

-- =============================================================================
-- 1. List all TVFs in schema
-- =============================================================================
SHOW FUNCTIONS IN {catalog}.{schema}
WHERE function_name LIKE 'get_%';

-- =============================================================================
-- 2. View function details (repeat for each TVF)
-- =============================================================================
DESCRIBE FUNCTION EXTENDED {catalog}.{schema}.get_top_stores_by_revenue;

-- =============================================================================
-- 3. Test function execution with explicit parameters
-- =============================================================================
SELECT * FROM {catalog}.{schema}.get_top_stores_by_revenue(
  '2024-01-01', 
  '2024-12-31', 
  5
);

-- =============================================================================
-- 4. Test function execution with default parameters
--    Should return 10 rows (default top_n = 10)
-- =============================================================================
SELECT * FROM {catalog}.{schema}.get_top_stores_by_revenue(
  '2024-01-01', 
  '2024-12-31'
);

-- =============================================================================
-- 5. Validate TVF results against metric view (if available)
--    Ratio should be approximately 1.0
--    If ratio >> 1.0 (e.g., 254), there is likely a cartesian product bug
-- =============================================================================
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

-- =============================================================================
-- 6. Edge case: Empty date range (should return 0 rows, not error)
-- =============================================================================
SELECT * FROM {catalog}.{schema}.get_top_stores_by_revenue(
  '2099-01-01', 
  '2099-12-31', 
  5
);

-- =============================================================================
-- 7. Edge case: Single-day range
-- =============================================================================
SELECT * FROM {catalog}.{schema}.get_top_stores_by_revenue(
  '2024-06-15', 
  '2024-06-15', 
  5
);

-- =============================================================================
-- 8. Verify no TABLE() wrapper needed (should work without TABLE())
-- =============================================================================
-- ✅ CORRECT: Direct call
SELECT * FROM {catalog}.{schema}.get_top_stores_by_revenue('2024-01-01', '2024-12-31');

-- ❌ WRONG: TABLE() wrapper (should fail with NOT_A_SCALAR_FUNCTION)
-- SELECT * FROM TABLE({catalog}.{schema}.get_top_stores_by_revenue('2024-01-01', '2024-12-31'));
