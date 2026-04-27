# Monitoring Dashboard Queries: SQL Reference

Complete SQL recipes for building production monitoring dashboards from MLflow
trace archival tables. Designed for Databricks Lakeview dashboards with
parameterized datasets.

> **Assumes**: trace archival enabled to `main.monitoring.agent_traces`
> (see [`trace-archival.md`](trace-archival.md)).

---

## Table Reference

All queries target the trace archival Delta table. Adjust the three-level
name to match your deployment:

```
main.monitoring.agent_traces       ← production
main.monitoring.agent_traces_staging  ← staging
```

Column names may vary by MLflow version. Verify against your table with:

```sql
DESCRIBE main.monitoring.agent_traces;
```

---

## 1. Daily Quality Trends

Rolling quality overview across all scorers.

```sql
SELECT
    DATE(t.timestamp) AS day,
    a.scorer_name,
    AVG(CAST(a.score_value AS DOUBLE)) AS avg_score,
    COUNT(*) AS eval_count,
    COUNT_IF(CAST(a.score_value AS DOUBLE) < 0.5) AS failure_count,
    ROUND(
        COUNT_IF(CAST(a.score_value AS DOUBLE) < 0.5) * 100.0 / COUNT(*),
        2
    ) AS failure_rate_pct
FROM main.monitoring.agent_traces t
LATERAL VIEW EXPLODE(t.assessments) AS a
WHERE t.timestamp > DATEADD(DAY, -30, CURRENT_TIMESTAMP())
GROUP BY 1, 2
ORDER BY 1 DESC, 2
```

**Lakeview widget**: Line chart, X=day, Y=avg_score, color=scorer_name.

---

## 2. Hourly Error Rate

Detect spikes in real-time quality degradation.

```sql
SELECT
    DATE_TRUNC('HOUR', t.timestamp) AS hour,
    COUNT(*) AS total_traces,
    COUNT_IF(t.status = 'ERROR') AS error_count,
    ROUND(
        COUNT_IF(t.status = 'ERROR') * 100.0 / NULLIF(COUNT(*), 0),
        2
    ) AS error_rate_pct
FROM main.monitoring.agent_traces t
WHERE t.timestamp > DATEADD(HOUR, -48, CURRENT_TIMESTAMP())
GROUP BY 1
ORDER BY 1 DESC
```

**Lakeview widget**: Bar chart, X=hour, Y=error_rate_pct. Add alert
at threshold (e.g., > 5%).

---

## 3. Per-Scorer Performance

Detailed scorer-level metrics for operational review.

```sql
SELECT
    a.scorer_name,
    COUNT(*) AS total_evaluations,
    AVG(CAST(a.score_value AS DOUBLE)) AS avg_score,
    PERCENTILE_APPROX(CAST(a.score_value AS DOUBLE), 0.50) AS median_score,
    MIN(CAST(a.score_value AS DOUBLE)) AS min_score,
    MAX(CAST(a.score_value AS DOUBLE)) AS max_score,
    STDDEV(CAST(a.score_value AS DOUBLE)) AS stddev_score,
    COUNT_IF(CAST(a.score_value AS DOUBLE) = 0.0) AS zero_scores,
    COUNT_IF(CAST(a.score_value AS DOUBLE) = 1.0) AS perfect_scores
FROM main.monitoring.agent_traces t
LATERAL VIEW EXPLODE(t.assessments) AS a
WHERE t.timestamp > DATEADD(DAY, -7, CURRENT_TIMESTAMP())
GROUP BY 1
ORDER BY avg_score ASC
```

**Lakeview widget**: Table with conditional formatting (red for avg_score < 0.7).

---

## 4. Latency Distribution

End-to-end latency analysis with percentile breakdowns.

```sql
SELECT
    DATE(timestamp) AS day,
    model_name,
    COUNT(*) AS trace_count,
    ROUND(AVG(execution_time_ms), 0) AS avg_ms,
    ROUND(PERCENTILE_APPROX(execution_time_ms, 0.50), 0) AS p50_ms,
    ROUND(PERCENTILE_APPROX(execution_time_ms, 0.90), 0) AS p90_ms,
    ROUND(PERCENTILE_APPROX(execution_time_ms, 0.95), 0) AS p95_ms,
    ROUND(PERCENTILE_APPROX(execution_time_ms, 0.99), 0) AS p99_ms,
    MAX(execution_time_ms) AS max_ms
FROM main.monitoring.agent_traces
WHERE timestamp > DATEADD(DAY, -14, CURRENT_TIMESTAMP())
GROUP BY 1, 2
ORDER BY 1 DESC
```

**Lakeview widget**: Multi-line chart, X=day, Y=p50/p95/p99, color by percentile.

---

## 5. User Satisfaction Trends

Tracks multi-turn scorer signals (frustration, completeness) over time.

```sql
SELECT
    DATE(t.timestamp) AS day,
    a.scorer_name,
    AVG(CAST(a.score_value AS DOUBLE)) AS avg_score,
    COUNT(*) AS sessions_scored,
    COUNT_IF(CAST(a.score_value AS DOUBLE) < 0.3) AS poor_sessions
FROM main.monitoring.agent_traces t
LATERAL VIEW EXPLODE(t.assessments) AS a
WHERE a.scorer_name IN (
    'prod_user_frustration',
    'prod_conversation_completeness'
)
AND t.timestamp > DATEADD(DAY, -30, CURRENT_TIMESTAMP())
GROUP BY 1, 2
ORDER BY 1 DESC, 2
```

**Note**: UserFrustration scores are inverted — lower is better (less
frustration). ConversationCompleteness is standard — higher is better.

**Lakeview widget**: Dual-axis line chart or separate panels per scorer.

---

## 6. Alert Threshold Queries

Pre-built queries for Databricks SQL Alerts.

### Safety failures in the last hour

```sql
SELECT COUNT(*) AS safety_failures
FROM main.monitoring.agent_traces t
LATERAL VIEW EXPLODE(t.assessments) AS a
WHERE a.scorer_name = 'prod_safety'
  AND CAST(a.score_value AS DOUBLE) < 0.5
  AND t.timestamp > DATEADD(HOUR, -1, CURRENT_TIMESTAMP())
```

**Alert config**: Trigger when `safety_failures > 5`. Notify via email/Slack.

### Error rate exceeds threshold

```sql
SELECT
    ROUND(
        COUNT_IF(status = 'ERROR') * 100.0 / NULLIF(COUNT(*), 0),
        2
    ) AS error_rate_pct
FROM main.monitoring.agent_traces
WHERE timestamp > DATEADD(HOUR, -1, CURRENT_TIMESTAMP())
```

**Alert config**: Trigger when `error_rate_pct > 10`.

### Average quality drop below baseline

```sql
SELECT
    a.scorer_name,
    AVG(CAST(a.score_value AS DOUBLE)) AS avg_score_last_hour
FROM main.monitoring.agent_traces t
LATERAL VIEW EXPLODE(t.assessments) AS a
WHERE t.timestamp > DATEADD(HOUR, -1, CURRENT_TIMESTAMP())
GROUP BY 1
HAVING AVG(CAST(a.score_value AS DOUBLE)) < 0.7
```

**Alert config**: Trigger when any scorer drops below 0.7 average.

### Latency spike

```sql
SELECT
    ROUND(PERCENTILE_APPROX(execution_time_ms, 0.95), 0) AS p95_ms
FROM main.monitoring.agent_traces
WHERE timestamp > DATEADD(MINUTE, -30, CURRENT_TIMESTAMP())
```

**Alert config**: Trigger when `p95_ms > 10000` (10 seconds).

### No traces received (liveness check)

```sql
SELECT COUNT(*) AS trace_count
FROM main.monitoring.agent_traces
WHERE timestamp > DATEADD(MINUTE, -15, CURRENT_TIMESTAMP())
```

**Alert config**: Trigger when `trace_count = 0` (endpoint may be down).

---

## 6b. Alert Queries on UC OTEL Tables (MLflow 3.11+)

If you're using the newer UC OTEL trace storage (`*_otel_traces` / `*_otel_spans` / `*_otel_annotations`) instead of (or in addition to) the legacy trace archival, use these alert queries. They read the assessment table directly — no `LATERAL VIEW EXPLODE`.

Assumes tables like `main.skyloyalty_ops.skyloyalty_agent_otel_traces` and `..._otel_annotations`. Adjust names.

### OTEL: Scorer below threshold in last hour

```sql
SELECT
    assessment_name,
    AVG(value) AS avg_value,
    COUNT(*)   AS n_traces_scored,
    SUM(CASE WHEN value < 0.7 THEN 1 ELSE 0 END) AS n_below_threshold
FROM main.skyloyalty_ops.skyloyalty_agent_otel_annotations
WHERE assessment_source IN ('SCORER', 'JUDGE')
  AND timestamp > current_timestamp() - INTERVAL 1 HOUR
GROUP BY assessment_name
HAVING AVG(value) < 0.7
```

**Alert config**: Trigger on any row returned (i.e. any scorer averaging < 0.7 in the last hour).

### OTEL: Failed trace rate

```sql
SELECT
    ROUND(100.0 * COUNT_IF(trace_status = 'ERROR') / NULLIF(COUNT(*), 0), 2) AS error_pct
FROM main.skyloyalty_ops.skyloyalty_agent_otel_traces
WHERE start_time > current_timestamp() - INTERVAL 1 HOUR
```

**Alert config**: Trigger when `error_pct > 5` over any 1h window.

### OTEL: Human negative feedback rate

```sql
SELECT
    assessment_name,
    COUNT(*) AS n_negative,
    COUNT(DISTINCT request_id) AS traces_with_negative
FROM main.skyloyalty_ops.skyloyalty_agent_otel_annotations
WHERE assessment_source = 'HUMAN'
  AND (value < 0.5 OR value = false)
  AND timestamp > current_timestamp() - INTERVAL 24 HOUR
GROUP BY assessment_name
HAVING COUNT(*) >= 3
```

**Alert config**: Trigger on any row returned. 3+ human negatives in a day is a real signal, not noise.

### OTEL: Production regression — citation scorer sliding window

Detect gradual drift by comparing 6h averages:

```sql
WITH recent AS (
  SELECT AVG(value) AS recent_avg
  FROM main.skyloyalty_ops.skyloyalty_agent_otel_annotations
  WHERE assessment_name = 'source_citation_scorer'
    AND timestamp > current_timestamp() - INTERVAL 6 HOUR
),
baseline AS (
  SELECT AVG(value) AS baseline_avg
  FROM main.skyloyalty_ops.skyloyalty_agent_otel_annotations
  WHERE assessment_name = 'source_citation_scorer'
    AND timestamp BETWEEN current_timestamp() - INTERVAL 48 HOUR
                      AND current_timestamp() - INTERVAL 24 HOUR
)
SELECT
  recent_avg,
  baseline_avg,
  (recent_avg - baseline_avg) AS drift
FROM recent, baseline
WHERE (recent_avg - baseline_avg) < -0.05
```

**Alert config**: Trigger when `drift < -0.05` (5-point drop vs previous-day baseline). This is the rollback-trigger type of alert — wire it to PagerDuty / Slack ops channel.

### OTEL: Budget guard — LLM token spike

If AI Gateway is in use, join the gateway inference table:

```sql
SELECT
  ROUND(SUM(input_tokens + output_tokens) / 1e6, 2) AS million_tokens_last_hour
FROM main.skyloyalty_ops.gw_skyloyalty_ai_gateway_usage
WHERE request_time > current_timestamp() - INTERVAL 1 HOUR
HAVING SUM(input_tokens + output_tokens) > 5e6   -- 5 million tokens/hour baseline
```

**Alert config**: Trigger on any row. Sudden spike = either a viral day or a runaway agent.

### Wiring alerts to incident response

Recommended priorities:

| Alert | Priority | Response |
|-------|----------|----------|
| OTEL scorer < 0.7 (1h) | P2 | Slack notify; investigate within 4h |
| OTEL error_pct > 5 (1h) | P1 | Page on-call; investigate now |
| Human negative feedback ≥ 3 (24h) | P2 | Label session + add to regression subset |
| Scorer drift < -0.05 | P1 | Consider alias rollback |
| Token spike 5M/h | P2 | Check caller distribution; rate-limit if needed |
| Liveness: 0 traces in 15 min | P1 | Page on-call; likely app or endpoint down |

See the [04b-stakeholder-signoff](../../04b-stakeholder-signoff/SKILL.md) skill's "rollback trigger" field — these are the alerts you agreed to in the signoff.

---

## 7. Session-Level Quality Analysis

Aggregate quality metrics per conversation session (requires `session_id` tag).

```sql
SELECT
    t.tags['session_id'] AS session_id,
    MIN(t.timestamp) AS session_start,
    MAX(t.timestamp) AS session_end,
    COUNT(*) AS turn_count,
    AVG(t.execution_time_ms) AS avg_latency_ms,
    COUNT_IF(t.status = 'ERROR') AS errors,
    -- Per-scorer averages within the session
    AVG(CASE WHEN a.scorer_name = 'prod_safety'
        THEN CAST(a.score_value AS DOUBLE) END) AS avg_safety,
    AVG(CASE WHEN a.scorer_name = 'prod_correctness'
        THEN CAST(a.score_value AS DOUBLE) END) AS avg_correctness
FROM main.monitoring.agent_traces t
LATERAL VIEW EXPLODE(t.assessments) AS a
WHERE t.tags['session_id'] IS NOT NULL
  AND t.timestamp > DATEADD(DAY, -7, CURRENT_TIMESTAMP())
GROUP BY 1
HAVING turn_count > 1
ORDER BY avg_safety ASC
LIMIT 100
```

**Lakeview widget**: Table sorted by worst safety scores — surface
problematic sessions for manual review.

---

## 8. Model Version Comparison

Compare quality across model versions during canary or A/B deployments.

```sql
SELECT
    t.model_version,
    a.scorer_name,
    COUNT(*) AS eval_count,
    AVG(CAST(a.score_value AS DOUBLE)) AS avg_score,
    COUNT_IF(CAST(a.score_value AS DOUBLE) < 0.5) AS failures
FROM main.monitoring.agent_traces t
LATERAL VIEW EXPLODE(t.assessments) AS a
WHERE t.timestamp > DATEADD(DAY, -7, CURRENT_TIMESTAMP())
  AND t.model_version IS NOT NULL
GROUP BY 1, 2
ORDER BY 2, 1
```

**Lakeview widget**: Grouped bar chart, X=model_version, Y=avg_score,
grouped by scorer_name.

---

## 9. Volume and Throughput

Traffic patterns for capacity planning.

```sql
SELECT
    DATE_TRUNC('HOUR', timestamp) AS hour,
    model_name,
    COUNT(*) AS traces,
    ROUND(COUNT(*) / 60.0, 2) AS traces_per_minute,
    ROUND(AVG(execution_time_ms), 0) AS avg_latency_ms,
    ROUND(SUM(execution_time_ms) / 1000.0, 1) AS total_compute_sec
FROM main.monitoring.agent_traces
WHERE timestamp > DATEADD(DAY, -7, CURRENT_TIMESTAMP())
GROUP BY 1, 2
ORDER BY 1 DESC
```

---

## Complete Lakeview Dashboard Definition

Example JSON structure for a monitoring dashboard with the queries above.
Import into Lakeview or use as a template.

```json
{
  "displayName": "GenAI Agent Monitoring",
  "warehouse_id": "YOUR_WAREHOUSE_ID",
  "pages": [
    {
      "name": "overview",
      "displayName": "Overview",
      "layout": [
        {
          "widget": {
            "name": "daily_quality",
            "title": "Daily Quality Trends (30d)",
            "spec": {
              "version": 3,
              "widgetType": "area",
              "encodings": {
                "x": {"fieldName": "day", "scale": {"type": "temporal"}},
                "y": {"fieldName": "avg_score", "scale": {"domain": [0, 1]}},
                "color": {"fieldName": "scorer_name"}
              }
            },
            "queries": [
              {
                "name": "daily_quality_query",
                "query": {
                  "datasetName": "daily_quality_trends",
                  "disaggregated": true
                }
              }
            ]
          },
          "position": {"x": 0, "y": 0, "width": 6, "height": 4}
        },
        {
          "widget": {
            "name": "error_rate",
            "title": "Hourly Error Rate (48h)",
            "spec": {
              "version": 3,
              "widgetType": "bar",
              "encodings": {
                "x": {"fieldName": "hour", "scale": {"type": "temporal"}},
                "y": {"fieldName": "error_rate_pct"}
              }
            },
            "queries": [
              {
                "name": "error_rate_query",
                "query": {
                  "datasetName": "hourly_error_rate",
                  "disaggregated": true
                }
              }
            ]
          },
          "position": {"x": 0, "y": 4, "width": 6, "height": 4}
        },
        {
          "widget": {
            "name": "latency_percentiles",
            "title": "Latency Distribution (14d)",
            "spec": {
              "version": 3,
              "widgetType": "line",
              "encodings": {
                "x": {"fieldName": "day", "scale": {"type": "temporal"}},
                "y": {"fieldName": "p95_ms"}
              }
            },
            "queries": [
              {
                "name": "latency_query",
                "query": {
                  "datasetName": "latency_distribution",
                  "disaggregated": true
                }
              }
            ]
          },
          "position": {"x": 0, "y": 8, "width": 6, "height": 4}
        }
      ]
    },
    {
      "name": "scorers",
      "displayName": "Scorer Detail",
      "layout": [
        {
          "widget": {
            "name": "scorer_stats",
            "title": "Per-Scorer Performance (7d)",
            "spec": {
              "version": 3,
              "widgetType": "table"
            },
            "queries": [
              {
                "name": "scorer_detail_query",
                "query": {
                  "datasetName": "per_scorer_performance",
                  "disaggregated": true
                }
              }
            ]
          },
          "position": {"x": 0, "y": 0, "width": 6, "height": 6}
        }
      ]
    },
    {
      "name": "sessions",
      "displayName": "Session Quality",
      "layout": [
        {
          "widget": {
            "name": "problem_sessions",
            "title": "Lowest Quality Sessions (7d)",
            "spec": {
              "version": 3,
              "widgetType": "table"
            },
            "queries": [
              {
                "name": "session_query",
                "query": {
                  "datasetName": "session_quality",
                  "disaggregated": true
                }
              }
            ]
          },
          "position": {"x": 0, "y": 0, "width": 6, "height": 6}
        }
      ]
    },
    {
      "name": "versions",
      "displayName": "Model Versions",
      "layout": [
        {
          "widget": {
            "name": "version_comparison",
            "title": "Quality by Model Version (7d)",
            "spec": {
              "version": 3,
              "widgetType": "bar",
              "encodings": {
                "x": {"fieldName": "model_version"},
                "y": {"fieldName": "avg_score"},
                "color": {"fieldName": "scorer_name"}
              }
            },
            "queries": [
              {
                "name": "version_query",
                "query": {
                  "datasetName": "model_version_comparison",
                  "disaggregated": true
                }
              }
            ]
          },
          "position": {"x": 0, "y": 0, "width": 6, "height": 4}
        }
      ]
    }
  ],
  "datasets": [
    {
      "name": "daily_quality_trends",
      "displayName": "Daily Quality Trends",
      "query": "SELECT DATE(t.timestamp) AS day, a.scorer_name, AVG(CAST(a.score_value AS DOUBLE)) AS avg_score, COUNT(*) AS eval_count, COUNT_IF(CAST(a.score_value AS DOUBLE) < 0.5) AS failure_count FROM main.monitoring.agent_traces t LATERAL VIEW EXPLODE(t.assessments) AS a WHERE t.timestamp > DATEADD(DAY, -30, CURRENT_TIMESTAMP()) GROUP BY 1, 2 ORDER BY 1 DESC, 2"
    },
    {
      "name": "hourly_error_rate",
      "displayName": "Hourly Error Rate",
      "query": "SELECT DATE_TRUNC('HOUR', t.timestamp) AS hour, COUNT(*) AS total_traces, COUNT_IF(t.status = 'ERROR') AS error_count, ROUND(COUNT_IF(t.status = 'ERROR') * 100.0 / NULLIF(COUNT(*), 0), 2) AS error_rate_pct FROM main.monitoring.agent_traces t WHERE t.timestamp > DATEADD(HOUR, -48, CURRENT_TIMESTAMP()) GROUP BY 1 ORDER BY 1 DESC"
    },
    {
      "name": "per_scorer_performance",
      "displayName": "Per-Scorer Performance",
      "query": "SELECT a.scorer_name, COUNT(*) AS total_evaluations, AVG(CAST(a.score_value AS DOUBLE)) AS avg_score, MIN(CAST(a.score_value AS DOUBLE)) AS min_score, MAX(CAST(a.score_value AS DOUBLE)) AS max_score, COUNT_IF(CAST(a.score_value AS DOUBLE) = 0.0) AS zero_scores FROM main.monitoring.agent_traces t LATERAL VIEW EXPLODE(t.assessments) AS a WHERE t.timestamp > DATEADD(DAY, -7, CURRENT_TIMESTAMP()) GROUP BY 1 ORDER BY avg_score ASC"
    },
    {
      "name": "latency_distribution",
      "displayName": "Latency Distribution",
      "query": "SELECT DATE(timestamp) AS day, model_name, ROUND(PERCENTILE_APPROX(execution_time_ms, 0.50), 0) AS p50_ms, ROUND(PERCENTILE_APPROX(execution_time_ms, 0.95), 0) AS p95_ms, ROUND(PERCENTILE_APPROX(execution_time_ms, 0.99), 0) AS p99_ms FROM main.monitoring.agent_traces WHERE timestamp > DATEADD(DAY, -14, CURRENT_TIMESTAMP()) GROUP BY 1, 2 ORDER BY 1 DESC"
    },
    {
      "name": "session_quality",
      "displayName": "Session Quality",
      "query": "SELECT t.tags['session_id'] AS session_id, MIN(t.timestamp) AS session_start, COUNT(*) AS turn_count, AVG(CASE WHEN a.scorer_name = 'prod_safety' THEN CAST(a.score_value AS DOUBLE) END) AS avg_safety FROM main.monitoring.agent_traces t LATERAL VIEW EXPLODE(t.assessments) AS a WHERE t.tags['session_id'] IS NOT NULL AND t.timestamp > DATEADD(DAY, -7, CURRENT_TIMESTAMP()) GROUP BY 1 HAVING turn_count > 1 ORDER BY avg_safety ASC LIMIT 100"
    },
    {
      "name": "model_version_comparison",
      "displayName": "Model Version Comparison",
      "query": "SELECT t.model_version, a.scorer_name, COUNT(*) AS eval_count, AVG(CAST(a.score_value AS DOUBLE)) AS avg_score FROM main.monitoring.agent_traces t LATERAL VIEW EXPLODE(t.assessments) AS a WHERE t.timestamp > DATEADD(DAY, -7, CURRENT_TIMESTAMP()) AND t.model_version IS NOT NULL GROUP BY 1, 2 ORDER BY 2, 1"
    }
  ]
}
```

---

## Query Patterns Cheat Sheet

| Need | Key technique |
|------|---------------|
| Access assessment fields | `LATERAL VIEW EXPLODE(t.assessments) AS a` |
| Filter by scorer | `WHERE a.scorer_name = 'prod_safety'` |
| Filter by tag | `WHERE t.tags['user_id'] = '...'` |
| Time windows | `DATEADD(DAY, -N, CURRENT_TIMESTAMP())` |
| Percentiles | `PERCENTILE_APPROX(col, 0.95)` |
| Failure rate | `COUNT_IF(condition) * 100.0 / NULLIF(COUNT(*), 0)` |
| Day grouping | `DATE(timestamp)` or `DATE_TRUNC('DAY', timestamp)` |
| Hour grouping | `DATE_TRUNC('HOUR', timestamp)` |

---

## References

- [Databricks SQL functions](https://docs.databricks.com/en/sql/language-manual/sql-ref-functions.html)
- [Lakeview dashboard API](https://docs.databricks.com/en/dashboards/index.html)
- [`trace-archival.md`](trace-archival.md) — table setup and retention
- [`metric-backfill.md`](metric-backfill.md) — backfilling historical scores
- [`registered-scorers.md`](registered-scorers.md) — scorer names referenced in queries
