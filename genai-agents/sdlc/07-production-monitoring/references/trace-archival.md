# Trace Archival: Delta Table Storage Reference

Persist MLflow traces to Unity Catalog Delta tables for long-term retention,
compliance auditing, SQL analytics, and monitoring dashboard integration.

> **Source**: [Trace storage – Databricks MLflow 3 GenAI](https://docs.databricks.com/aws/en/mlflow3/genai/tracing/storage)

---

## Enabling Trace Archival

```python
import mlflow

mlflow.enable_databricks_trace_archival(
    delta_table_fullname="main.monitoring.agent_traces"
)
```

Call this **once** at application startup (or in a deployment script). After
enablement, all new traces produced by MLflow in the workspace are written to
the specified Delta table.

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `delta_table_fullname` | `str` | Yes | Three-level UC name: `catalog.schema.table` |

### Prerequisites

- The catalog and schema must already exist in Unity Catalog.
- The calling principal needs `CREATE TABLE` (first run) or `MODIFY` (subsequent) on the schema.
- A SQL warehouse or serverless compute must be available for Delta writes.

---

## Archive Table Schema

The platform creates the table with a schema similar to this (column names
and types may evolve — always verify against your workspace):

| Column | Type | Description |
|--------|------|-------------|
| `trace_id` | `STRING` | Unique trace identifier |
| `request_id` | `STRING` | Serving request ID (if from endpoint) |
| `timestamp` | `TIMESTAMP` | Trace creation time |
| `model_name` | `STRING` | Registered model or endpoint name |
| `model_version` | `STRING` | Model version that produced the trace |
| `status` | `STRING` | `OK`, `ERROR`, etc. |
| `execution_time_ms` | `LONG` | Total trace duration in milliseconds |
| `request` | `STRING` | JSON-serialized input |
| `response` | `STRING` | JSON-serialized output |
| `spans` | `ARRAY<STRUCT>` | Nested span tree |
| `tags` | `MAP<STRING, STRING>` | Trace-level tags |
| `assessments` | `ARRAY<STRUCT>` | Scorer results attached to the trace |
| `_ingestion_timestamp` | `TIMESTAMP` | When the row was written to Delta |

### Assessment sub-schema (within `assessments`)

| Field | Type | Description |
|-------|------|-------------|
| `scorer_name` | `STRING` | Name of the registered scorer |
| `score_value` | `STRING` | The numeric or categorical score |
| `rationale` | `STRING` | Explanation from the scorer |
| `timestamp` | `TIMESTAMP` | When the assessment was computed |
| `source_id` | `STRING` | Scorer source identifier |

---

## Recommended Table Layout

```
main.monitoring.agent_traces          ← production
main.monitoring.agent_traces_staging  ← staging / canary
main.monitoring.agent_traces_dev      ← development experiments
```

Use separate tables per environment to avoid cross-contamination of metrics
and to simplify access control.

### Schema setup

```sql
CREATE SCHEMA IF NOT EXISTS main.monitoring
COMMENT 'MLflow trace archival and production monitoring';

GRANT USE SCHEMA ON SCHEMA main.monitoring
TO `monitoring-readers`;

GRANT SELECT ON TABLE main.monitoring.agent_traces
TO `monitoring-readers`;
```

---

## Retention Policies

Delta tables support time travel and `VACUUM` for retention management.

### Keep 90 days of full history

```sql
ALTER TABLE main.monitoring.agent_traces
SET TBLPROPERTIES (
    'delta.logRetentionDuration' = 'interval 90 days',
    'delta.deletedFileRetentionDuration' = 'interval 90 days'
);
```

### Purge old data

```sql
DELETE FROM main.monitoring.agent_traces
WHERE timestamp < DATEADD(DAY, -365, CURRENT_TIMESTAMP());

VACUUM main.monitoring.agent_traces RETAIN 90 HOURS;
```

### Tiered retention strategy

| Tier | Retention | Data |
|------|-----------|------|
| Hot (Delta) | 90 days | Full traces with spans and assessments |
| Warm (archive) | 1 year | Aggregated daily metrics only |
| Cold (compliance) | 7 years | Sampled raw traces for audit trail |

Implement tiered retention with scheduled jobs that aggregate and move data:

```sql
-- Nightly aggregation into warm tier
INSERT INTO main.monitoring.daily_metrics
SELECT
    DATE(timestamp) AS day,
    model_name,
    COUNT(*) AS trace_count,
    AVG(execution_time_ms) AS avg_latency_ms,
    COUNT_IF(status = 'ERROR') AS error_count
FROM main.monitoring.agent_traces
WHERE DATE(timestamp) = DATEADD(DAY, -1, CURRENT_DATE())
GROUP BY 1, 2;
```

---

## Query Patterns for Archived Traces

### Recent errors with full context

```sql
SELECT
    trace_id,
    timestamp,
    model_name,
    status,
    execution_time_ms,
    request,
    response,
    tags
FROM main.monitoring.agent_traces
WHERE status = 'ERROR'
  AND timestamp > DATEADD(HOUR, -24, CURRENT_TIMESTAMP())
ORDER BY timestamp DESC
LIMIT 50;
```

### Scorer results over time

```sql
SELECT
    DATE(a.timestamp) AS day,
    a.scorer_name,
    AVG(CAST(a.score_value AS DOUBLE)) AS avg_score,
    COUNT(*) AS eval_count,
    COUNT_IF(CAST(a.score_value AS DOUBLE) < 0.5) AS failures
FROM main.monitoring.agent_traces t
LATERAL VIEW EXPLODE(t.assessments) AS a
WHERE t.timestamp > DATEADD(DAY, -30, CURRENT_TIMESTAMP())
GROUP BY 1, 2
ORDER BY 1 DESC, 2;
```

### Latency percentiles

```sql
SELECT
    DATE(timestamp) AS day,
    model_name,
    PERCENTILE_APPROX(execution_time_ms, 0.50) AS p50_ms,
    PERCENTILE_APPROX(execution_time_ms, 0.95) AS p95_ms,
    PERCENTILE_APPROX(execution_time_ms, 0.99) AS p99_ms
FROM main.monitoring.agent_traces
WHERE timestamp > DATEADD(DAY, -7, CURRENT_TIMESTAMP())
GROUP BY 1, 2
ORDER BY 1 DESC;
```

### Traces by tag (e.g., user or session)

```sql
SELECT
    trace_id,
    timestamp,
    tags['user_id'] AS user_id,
    tags['session_id'] AS session_id,
    execution_time_ms,
    status
FROM main.monitoring.agent_traces
WHERE tags['user_id'] = 'user-123'
  AND timestamp > DATEADD(DAY, -7, CURRENT_TIMESTAMP())
ORDER BY timestamp DESC;
```

---

## Integration with Monitoring Dashboards

### Lakeview dashboard data source

Point a Lakeview dashboard dataset at the archival table:

```sql
-- Dataset: trace_quality_daily
SELECT
    DATE(timestamp) AS day,
    model_name,
    COUNT(*) AS total_traces,
    COUNT_IF(status = 'OK') AS success_count,
    COUNT_IF(status = 'ERROR') AS error_count,
    AVG(execution_time_ms) AS avg_latency_ms
FROM main.monitoring.agent_traces
WHERE timestamp > DATEADD(DAY, -30, CURRENT_TIMESTAMP())
GROUP BY 1, 2
```

### Alert integration

Use Databricks SQL Alerts on the archival table:

```sql
-- Alert: safety failures spike
SELECT COUNT(*) AS safety_failures
FROM main.monitoring.agent_traces t
LATERAL VIEW EXPLODE(t.assessments) AS a
WHERE a.scorer_name = 'prod_safety'
  AND CAST(a.score_value AS DOUBLE) < 0.5
  AND t.timestamp > DATEADD(HOUR, -1, CURRENT_TIMESTAMP())
```

Trigger when `safety_failures > 5` in the last hour.

---

## Storage Cost Considerations

| Factor | Impact | Mitigation |
|--------|--------|------------|
| Trace payload size | ~1–10 KB per trace (varies with span depth) | Limit span nesting; don't log large payloads |
| Assessment volume | Multiplied by number of active scorers | Use sampling; not all scorers at 100% |
| Delta file compaction | Small files from frequent writes | Schedule `OPTIMIZE` weekly |
| Time travel overhead | Retains deleted data for retention period | `VACUUM` after `DELETE` |
| Partitioning | Speeds queries, adds file overhead | Partition by day only (avoid over-partitioning) |

### Estimated storage (order of magnitude)

| Daily traces | Avg size | Daily storage | Monthly |
|-------------|----------|---------------|---------|
| 1,000 | 5 KB | ~5 MB | ~150 MB |
| 10,000 | 5 KB | ~50 MB | ~1.5 GB |
| 100,000 | 5 KB | ~500 MB | ~15 GB |
| 1,000,000 | 5 KB | ~5 GB | ~150 GB |

---

## Partitioning Strategies

### Recommended: daily partitioning

```sql
ALTER TABLE main.monitoring.agent_traces
SET TBLPROPERTIES ('delta.autoOptimize.optimizeWrite' = 'true');
```

Delta's auto-optimize handles most use cases. For very high-volume tables,
add explicit partitioning:

```sql
CREATE TABLE main.monitoring.agent_traces_partitioned (
    trace_id STRING,
    timestamp TIMESTAMP,
    model_name STRING,
    -- ... other columns ...
    day DATE GENERATED ALWAYS AS (DATE(timestamp))
)
USING DELTA
PARTITIONED BY (day)
LOCATION 'dbfs:/mnt/monitoring/agent_traces';
```

### Liquid clustering (preferred for Databricks)

```sql
ALTER TABLE main.monitoring.agent_traces
CLUSTER BY (timestamp, model_name);
```

Liquid clustering adapts automatically and avoids the rigidity of
Hive-style partitioning. Preferred for new tables on Databricks.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| No traces appearing in table | Archival not enabled or wrong table name | Verify `enable_databricks_trace_archival` call at startup |
| Permission denied on write | Principal lacks `MODIFY` on table | Grant via UC: `GRANT MODIFY ON TABLE ... TO ...` |
| Table growing too fast | No retention policy, all scorers at 100% | Set retention; use sampling for expensive judges |
| Slow queries on archival table | No optimization or clustering | Run `OPTIMIZE`; add liquid clustering |
| Old traces not cleaned up | `VACUUM` not scheduled | Schedule `DELETE` + `VACUUM` in a nightly job |
| Assessment array is empty | Scorers not started or model_name mismatch | Check `list_scorers()` and verify model names |

---

## References

- [Trace storage docs](https://docs.databricks.com/aws/en/mlflow3/genai/tracing/storage)
- [Delta Lake VACUUM](https://docs.databricks.com/en/sql/language-manual/delta-vacuum.html)
- [Liquid clustering](https://docs.databricks.com/en/delta/clustering.html)
- [`monitoring-dashboard-queries.md`](monitoring-dashboard-queries.md) — SQL recipes for dashboards
