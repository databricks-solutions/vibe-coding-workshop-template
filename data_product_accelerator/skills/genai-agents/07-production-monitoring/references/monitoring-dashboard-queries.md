# Monitoring Dashboard Queries

SQL queries for building monitoring dashboards from production scorer metrics and archived traces.

## Average Scores Query

```sql
-- Average scores by scorer over time
SELECT 
    DATE_TRUNC('hour', timestamp) AS hour,
    scorer_name,
    AVG(score_value) AS avg_score,
    COUNT(*) AS evaluation_count
FROM catalog.schema.scorer_metrics
WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL 24 HOURS
GROUP BY DATE_TRUNC('hour', timestamp), scorer_name
ORDER BY hour DESC, scorer_name;
```

## Score Trends Query

```sql
-- Score trends over time (daily aggregation)
SELECT 
    DATE(timestamp) AS date,
    scorer_name,
    AVG(score_value) AS avg_score,
    MIN(score_value) AS min_score,
    MAX(score_value) AS max_score,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY score_value) AS median_score,
    COUNT(*) AS evaluation_count
FROM catalog.schema.scorer_metrics
WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL 30 DAYS
GROUP BY DATE(timestamp), scorer_name
ORDER BY date DESC, scorer_name;
```

## Failure Rates Query

```sql
-- Failure rates by scorer (score < threshold)
SELECT 
    DATE_TRUNC('day', timestamp) AS day,
    scorer_name,
    COUNT(*) AS total_evaluations,
    SUM(CASE WHEN score_value < threshold THEN 1 ELSE 0 END) AS failures,
    ROUND(
        100.0 * SUM(CASE WHEN score_value < threshold THEN 1 ELSE 0 END) / COUNT(*),
        2
    ) AS failure_rate_pct
FROM catalog.schema.scorer_metrics
WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL 7 DAYS
GROUP BY DATE_TRUNC('day', timestamp), scorer_name
ORDER BY day DESC, failure_rate_pct DESC;
```

## Volume Tracking Query

```sql
-- Evaluation volume by scorer
SELECT 
    DATE_TRUNC('hour', timestamp) AS hour,
    scorer_name,
    COUNT(*) AS evaluation_count,
    COUNT(DISTINCT trace_id) AS unique_traces
FROM catalog.schema.scorer_metrics
WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL 24 HOURS
GROUP BY DATE_TRUNC('hour', timestamp), scorer_name
ORDER BY hour DESC, evaluation_count DESC;
```

## Score Distribution Query

```sql
-- Score distribution by scorer
SELECT 
    scorer_name,
    CASE 
        WHEN score_value >= 0.9 THEN 'Excellent (0.9+)'
        WHEN score_value >= 0.7 THEN 'Good (0.7-0.9)'
        WHEN score_value >= 0.5 THEN 'Fair (0.5-0.7)'
        ELSE 'Poor (<0.5)'
    END AS score_bucket,
    COUNT(*) AS count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY scorer_name), 2) AS pct
FROM catalog.schema.scorer_metrics
WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL 7 DAYS
GROUP BY scorer_name, score_bucket
ORDER BY scorer_name, score_bucket;
```

## Trace Error Analysis Query

```sql
-- Traces with errors and associated scorer results
SELECT 
    t.trace_id,
    t.trace_info.timestamp,
    t.trace_info.status,
    sm.scorer_name,
    sm.score_value,
    sm.rationale
FROM catalog.schema.agent_traces t
LEFT JOIN catalog.schema.scorer_metrics sm
    ON t.trace_id = sm.trace_id
WHERE t.trace_info.status = 'ERROR'
  AND t.trace_info.timestamp >= CURRENT_TIMESTAMP - INTERVAL 24 HOURS
ORDER BY t.trace_info.timestamp DESC;
```

## Scorer Performance Query

```sql
-- Scorer evaluation performance (latency)
SELECT 
    scorer_name,
    AVG(evaluation_latency_ms) AS avg_latency_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY evaluation_latency_ms) AS p95_latency_ms,
    MAX(evaluation_latency_ms) AS max_latency_ms,
    COUNT(*) AS total_evaluations
FROM catalog.schema.scorer_metrics
WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL 24 HOURS
GROUP BY scorer_name
ORDER BY avg_latency_ms DESC;
```

## Complete Dashboard Query

```sql
-- Comprehensive dashboard query
WITH hourly_metrics AS (
    SELECT 
        DATE_TRUNC('hour', timestamp) AS hour,
        scorer_name,
        AVG(score_value) AS avg_score,
        COUNT(*) AS evaluation_count,
        SUM(CASE WHEN score_value < threshold THEN 1 ELSE 0 END) AS failures
    FROM catalog.schema.scorer_metrics
    WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL 24 HOURS
    GROUP BY DATE_TRUNC('hour', timestamp), scorer_name
)
SELECT 
    hour,
    scorer_name,
    avg_score,
    evaluation_count,
    failures,
    ROUND(100.0 * failures / evaluation_count, 2) AS failure_rate_pct,
    CASE 
        WHEN avg_score >= 0.9 THEN 'Excellent'
        WHEN avg_score >= 0.7 THEN 'Good'
        WHEN avg_score >= 0.5 THEN 'Fair'
        ELSE 'Poor'
    END AS health_status
FROM hourly_metrics
ORDER BY hour DESC, scorer_name;
```

## Usage in Dashboards

```python
# Example: Query for dashboard
dashboard_query = """
SELECT 
    DATE_TRUNC('hour', timestamp) AS hour,
    scorer_name,
    AVG(score_value) AS avg_score,
    COUNT(*) AS evaluation_count
FROM catalog.schema.scorer_metrics
WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL 24 HOURS
GROUP BY DATE_TRUNC('hour', timestamp), scorer_name
ORDER BY hour DESC, scorer_name
"""

# Execute and visualize
metrics_df = spark.sql(dashboard_query)
# ... visualization code
```
