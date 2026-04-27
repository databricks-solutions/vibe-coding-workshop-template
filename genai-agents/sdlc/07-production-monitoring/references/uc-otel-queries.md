# UC OTEL: Tracing Tracks, Dashboard SQL, and Export

Use this reference when building Lakeview / SQL dashboards on Unity Catalog OTEL
trace tables or piping spans to third-party observability platforms. Assumes UC
OTEL trace storage and `set_databricks_monitoring_sql_warehouse_id` are
configured as described in [`../SKILL.md`](../SKILL.md).

Official context: [Store MLflow traces in Unity Catalog](https://docs.databricks.com/aws/en/mlflow3/genai/tracing/trace-unity-catalog),
[Enable production monitoring with UC traces](https://docs.databricks.com/aws/en/mlflow3/genai/tracing/trace-unity-catalog#enable-production-monitoring).

---

## Tracing sources by track

Production monitoring works the same regardless of how traces arrive in UC OTEL
tables:

- **Track A:** Traces from `mlflow.openai.autolog()` and `@mlflow.trace` decorators
- **Track B:** Traces from `trace_destination` parameter in Supervisor API calls
- **Track C:** Traces from the served model's autolog and endpoint-level tracing

All three produce traces in the same UC OTEL Delta tables. The monitoring
queries, registered scorers, and dashboards are identical.

---

## UC OTEL monitoring dashboard queries

Query the UC OTEL Delta tables directly for monitoring dashboards. Replace
`main.agent_traces.my_agent_otel_spans` with your three-level table name. Column
paths in `attributes` depend on your instrumentation; validate with
`DESCRIBE` / sample rows.

```sql
-- Safety score trend (daily)
SELECT
    DATE(start_time) AS day,
    AVG(CAST(JSON_EXTRACT_SCALAR(attributes, '$.scorer.safety.value') AS DOUBLE)) AS avg_safety,
    COUNT(*) AS trace_count
FROM main.agent_traces.my_agent_otel_spans
WHERE span_kind = 'AGENT'
  AND start_time > DATEADD(DAY, -30, CURRENT_TIMESTAMP())
GROUP BY 1
ORDER BY 1;

-- Error rate by hour
SELECT
    DATE_TRUNC('HOUR', start_time) AS hour,
    COUNT(CASE WHEN status_code = 'ERROR' THEN 1 END) AS errors,
    COUNT(*) AS total,
    ROUND(COUNT(CASE WHEN status_code = 'ERROR' THEN 1 END) * 100.0 / COUNT(*), 2) AS error_pct
FROM main.agent_traces.my_agent_otel_spans
WHERE span_kind = 'AGENT'
  AND start_time > DATEADD(HOUR, -24, CURRENT_TIMESTAMP())
GROUP BY 1
ORDER BY 1;

-- Latency percentiles
SELECT
    DATE(start_time) AS day,
    PERCENTILE_CONT(0.50) WITHIN GROUP (
        ORDER BY TIMESTAMPDIFF(MILLISECOND, start_time, end_time)
    ) AS p50_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (
        ORDER BY TIMESTAMPDIFF(MILLISECOND, start_time, end_time)
    ) AS p95_ms,
    PERCENTILE_CONT(0.99) WITHIN GROUP (
        ORDER BY TIMESTAMPDIFF(MILLISECOND, start_time, end_time)
    ) AS p99_ms
FROM main.agent_traces.my_agent_otel_spans
WHERE span_kind = 'AGENT'
  AND start_time > DATEADD(DAY, -7, CURRENT_TIMESTAMP())
GROUP BY 1
ORDER BY 1;

-- Token usage and cost estimation
SELECT
    DATE(start_time) AS day,
    SUM(CAST(JSON_EXTRACT_SCALAR(attributes, '$.llm.token_count.prompt') AS BIGINT)) AS prompt_tokens,
    SUM(CAST(JSON_EXTRACT_SCALAR(attributes, '$.llm.token_count.completion') AS BIGINT)) AS completion_tokens,
    SUM(CAST(JSON_EXTRACT_SCALAR(attributes, '$.llm.token_count.total') AS BIGINT)) AS total_tokens
FROM main.agent_traces.my_agent_otel_spans
WHERE span_kind = 'LLM'
  AND start_time > DATEADD(DAY, -7, CURRENT_TIMESTAMP())
GROUP BY 1
ORDER BY 1;
```

### Table suffix cheat sheet

| Suffix | Use |
|--------|-----|
| `_otel_spans` | Trace / span rows |
| `_otel_metrics` | Numeric metrics |
| `_otel_annotations` | Scores, feedback, annotations |

---

## Third-party OTEL export

UC OTEL tables follow the OpenTelemetry data model, making them compatible with
external observability platforms. Example: query recent spans and reshape for
an OTEL-compatible payload (adapt transport to your collector).

```python
import json
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

# Query recent traces and export as OTEL-compatible JSON
traces = w.statement_execution.execute_statement(
    warehouse_id="<WAREHOUSE_ID>",
    statement="""
        SELECT trace_id, span_id, parent_span_id, span_name, span_kind,
               start_time, end_time, status_code, attributes
        FROM main.agent_traces.my_agent_otel_spans
        WHERE start_time > DATEADD(HOUR, -1, CURRENT_TIMESTAMP())
    """,
)

# Transform to OTEL JSON format for your observability platform
for row in traces.result.data_array:
    otel_span = {
        "traceId": row[0],
        "spanId": row[1],
        "parentSpanId": row[2],
        "operationName": row[3],
        "startTimeUnixNano": row[5],
        "endTimeUnixNano": row[6],
        "status": {"code": row[7]},
        "attributes": json.loads(row[8]) if row[8] else {},
    }
    # Send to your OTEL collector endpoint
    # requests.post(OTEL_COLLECTOR_URL, json=otel_span)
```

---

## See also

- [`monitoring-dashboard-queries.md`](monitoring-dashboard-queries.md) — SQL on
  MLflow **archival** trace tables (non-OTEL path)
- [`common-mistakes.md`](common-mistakes.md) — UC OTEL grants and table suffix
  pitfalls
