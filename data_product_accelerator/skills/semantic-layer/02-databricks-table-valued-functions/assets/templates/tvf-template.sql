-- Template for creating Table-Valued Functions (TVFs) for Genie Spaces
-- Replace <placeholders> with actual values
--
-- Critical rules applied in this template:
-- 1. STRING for date parameters (Genie doesn't support DATE)
-- 2. Required parameters first, optional (DEFAULT) last
-- 3. ROW_NUMBER + WHERE for Top N (not LIMIT with parameter)
-- 4. NULLIF for all divisions (null safety)
-- 5. is_current = true for SCD2 dimension joins
-- 6. v3.0 bullet-point COMMENT format

CREATE OR REPLACE FUNCTION <catalog>.<schema>.<function_name>(
  -- ===== REQUIRED PARAMETERS (no DEFAULT) =====
  start_date STRING COMMENT 'Start date for analysis period (format: YYYY-MM-DD)',
  end_date STRING COMMENT 'End date for analysis period (format: YYYY-MM-DD)',
  -- ===== OPTIONAL PARAMETERS (with DEFAULT) =====
  top_n INT DEFAULT 10 COMMENT 'Number of top results to return (default: 10)'
)
RETURNS TABLE(
  -- ===== RETURNED COLUMNS (all documented) =====
  rank INT COMMENT 'Ranking position based on <primary_metric>',
  <dimension_key> STRING COMMENT '<Dimension> identifier',
  <dimension_name> STRING COMMENT '<Dimension> display name',
  <measure_1> DECIMAL(18,2) COMMENT 'Total <measure_1_description> for the period',
  <measure_2> BIGINT COMMENT 'Total <measure_2_description>',
  <measure_3> BIGINT COMMENT 'Number of <measure_3_description>',
  <calculated_measure> DECIMAL(18,2) COMMENT 'Average <calculated_description> per <denominator>'
)
-- ===== v3.0 BULLET-POINT COMMENT FORMAT =====
COMMENT '
• PURPOSE: <One-line description of what the TVF does>
• BEST FOR: "<Question 1>" | "<Question 2>" | "<Question 3>"
• NOT FOR: <What to avoid> (use <correct_asset> instead) (optional)
• RETURNS: <PRE-AGGREGATED or Individual> rows (<column1>, <column2>, <column3>)
• PARAMS: start_date, end_date, top_n (default: 10)
• SYNTAX: SELECT * FROM <function_name>(''2024-01-01'', ''2024-12-31'', 10)
• NOTE: <Important caveats - DO NOT wrap in TABLE(), etc.> (optional)
'
RETURN
  WITH <cte_name> AS (
    -- Aggregate from fact table with dimension join
    SELECT 
      f.<dimension_key>,
      d.<dimension_name>,
      SUM(f.<measure_column_1>) as <measure_1>,
      SUM(f.<measure_column_2>) as <measure_2>,
      COUNT(f.<count_column>) as <measure_3>
    FROM <catalog>.<schema>.<fact_table> f
    -- Join to dimension (filter for current records if SCD Type 2)
    LEFT JOIN <catalog>.<schema>.<dim_table> d 
      ON f.<dimension_key> = d.<dimension_key> 
      AND d.is_current = true  -- ⚠️ REMOVE if SCD Type 1 (no is_current column)
    -- Cast STRING dates to DATE for filtering
    WHERE f.<date_column> BETWEEN CAST(start_date AS DATE) AND CAST(end_date AS DATE)
    GROUP BY f.<dimension_key>, d.<dimension_name>
  ),
  ranked_results AS (
    SELECT 
      -- Rank using ROW_NUMBER (for parameterized top N)
      ROW_NUMBER() OVER (ORDER BY <measure_1> DESC) as rank,
      <dimension_key>,
      <dimension_name>,
      <measure_1>,
      <measure_2>,
      <measure_3>,
      -- Null-safe division for calculated measures
      <measure_1> / NULLIF(<measure_3>, 0) as <calculated_measure>
    FROM <cte_name>
  )
  -- Filter by rank (not LIMIT) to support parameterized top N
  SELECT * FROM ranked_results
  WHERE rank <= top_n  -- ✅ Use WHERE instead of LIMIT
  ORDER BY rank;
