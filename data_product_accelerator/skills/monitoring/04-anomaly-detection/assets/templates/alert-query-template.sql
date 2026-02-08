-- Anomaly Detection Alert Query Template
-- Use with Databricks SQL Alerts
--
-- Parameter: :min_tables_affected (integer)
--   Minimum number of downstream queries impacted before triggering alert.
--   Set to 0 to alert on ALL unhealthy tables.
--   Set to 10+ to only alert on high-impact issues.
--
-- Setup:
--   1. Click Alerts > Create alert
--   2. Paste this query
--   3. Set trigger: Rows returned > 0
--   4. Set schedule: Every 1 hour
--   5. (Optional) Customize email template - see references/alert-patterns.md

WITH rounded_data AS (
  SELECT
    DATE_TRUNC('HOUR', event_time) AS evaluated_at,
    CONCAT(catalog_name, '.', schema_name, '.', table_name) AS full_table_name,
    status,
    MAX(downstream_impact.num_queries_on_affected_tables) AS impacted_queries,
    MAX(freshness.commit_freshness.predicted_value) AS commit_expected,
    MAX(freshness.commit_freshness.last_value) AS commit_actual,
    MAX(completeness.daily_row_count.min_predicted_value) AS completeness_expected,
    MAX(completeness.daily_row_count.last_value) AS completeness_actual
  FROM system.data_quality_monitoring.table_results
  GROUP BY ALL
)
SELECT
  evaluated_at,
  full_table_name,
  status,
  commit_expected,
  commit_actual,
  completeness_expected,
  completeness_actual,
  impacted_queries
FROM rounded_data
WHERE
  evaluated_at >= current_timestamp() - INTERVAL 6 HOURS
  -- Adjust threshold: 0 = all unhealthy, 10+ = high-impact only
  AND impacted_queries > :min_tables_affected
  AND status = 'Unhealthy';
