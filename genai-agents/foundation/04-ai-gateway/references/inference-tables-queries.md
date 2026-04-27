# AI Gateway Inference Tables — SQL Recipes

These recipes assume an AI Gateway named `skyloyalty-ai-gateway` with inference tables at `main.skyloyalty_ops.gw_skyloyalty_ai_gateway_payload` and usage at `main.skyloyalty_ops.gw_skyloyalty_ai_gateway_usage`. Adjust names for your environment.

---

## 1. Daily Token Spend by Served Entity

```sql
SELECT
  date_trunc('day', request_time) AS day,
  served_entity_id,
  SUM(input_tokens)  AS prompt_tokens,
  SUM(output_tokens) AS completion_tokens,
  SUM(input_tokens + output_tokens) AS total_tokens,
  COUNT(*) AS requests
FROM main.skyloyalty_ops.gw_skyloyalty_ai_gateway_usage
WHERE request_time >= current_date() - INTERVAL 30 DAYS
GROUP BY 1, 2
ORDER BY 1 DESC, total_tokens DESC;
```

---

## 2. Top Users by Token Usage (chargeback)

```sql
SELECT
  user_identity,
  COUNT(*) AS requests,
  SUM(input_tokens + output_tokens) AS total_tokens,
  ROUND(AVG(execution_time_ms), 0) AS avg_latency_ms
FROM main.skyloyalty_ops.gw_skyloyalty_ai_gateway_usage
WHERE request_time >= current_date() - INTERVAL 7 DAYS
GROUP BY user_identity
ORDER BY total_tokens DESC
LIMIT 20;
```

---

## 3. Error Rate by Hour

```sql
SELECT
  date_trunc('hour', request_time) AS hour,
  SUM(CASE WHEN status_code BETWEEN 200 AND 299 THEN 1 ELSE 0 END) AS ok,
  SUM(CASE WHEN status_code = 429 THEN 1 ELSE 0 END) AS rate_limited,
  SUM(CASE WHEN status_code >= 500 THEN 1 ELSE 0 END) AS server_errors,
  COUNT(*) AS total,
  ROUND(100.0 * SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END) / COUNT(*), 2) AS error_pct
FROM main.skyloyalty_ops.gw_skyloyalty_ai_gateway_payload
WHERE request_time >= current_timestamp() - INTERVAL 24 HOURS
GROUP BY 1
ORDER BY 1 DESC;
```

Wire this into a Databricks SQL alert: alert when any hour has `error_pct > 5`.

---

## 4. p95 Latency by Served Entity

```sql
SELECT
  served_entity_id,
  PERCENTILE(execution_time_ms, 0.50) AS p50_ms,
  PERCENTILE(execution_time_ms, 0.95) AS p95_ms,
  PERCENTILE(execution_time_ms, 0.99) AS p99_ms,
  COUNT(*) AS requests
FROM main.skyloyalty_ops.gw_skyloyalty_ai_gateway_payload
WHERE request_time >= current_timestamp() - INTERVAL 24 HOURS
  AND status_code BETWEEN 200 AND 299
GROUP BY served_entity_id;
```

---

## 5. Join Gateway to MLflow OTEL Traces

Assumes the agent passes `databricks_request_id` matching the MLflow trace `request_id`, and traces are archived to `main.skyloyalty_ops.skyloyalty_agent_otel_traces`.

```sql
SELECT
  t.request_id,
  t.trace_status,
  t.execution_time_ms AS trace_latency_ms,
  gw.execution_time_ms AS gateway_latency_ms,
  gw.status_code AS gateway_status,
  gw.input_tokens,
  gw.output_tokens
FROM main.skyloyalty_ops.skyloyalty_agent_otel_traces t
LEFT JOIN main.skyloyalty_ops.gw_skyloyalty_ai_gateway_payload gw
  ON gw.databricks_request_id = t.request_id
WHERE t.start_time >= current_timestamp() - INTERVAL 24 HOURS
ORDER BY t.start_time DESC
LIMIT 200;
```

Use this for: "slow trace detected — was it a slow LLM call or slow tool call?" (compare `gateway_latency_ms` to `trace_latency_ms`).

---

## 6. PII Redaction Incidents

If input/output PII guardrails are set to `REDACT` (not `BLOCK`), count incidents:

```sql
SELECT
  date_trunc('day', request_time) AS day,
  COUNT(*) AS redactions,
  COUNT(DISTINCT user_identity) AS distinct_users
FROM main.skyloyalty_ops.gw_skyloyalty_ai_gateway_payload
WHERE request_time >= current_date() - INTERVAL 7 DAYS
  AND guardrail_pii_redacted = true
GROUP BY 1
ORDER BY 1 DESC;
```

---

## 7. Spend Projection

Rough monthly projection by linear extrapolation of last 7 days:

```sql
WITH weekly AS (
  SELECT
    SUM(input_tokens + output_tokens) AS tokens_7d
  FROM main.skyloyalty_ops.gw_skyloyalty_ai_gateway_usage
  WHERE request_time >= current_timestamp() - INTERVAL 7 DAYS
)
SELECT
  tokens_7d,
  tokens_7d * (30.0 / 7.0) AS projected_monthly_tokens,
  tokens_7d * (30.0 / 7.0) * 0.000008 AS projected_monthly_usd  -- adjust $ per token
FROM weekly;
```

Replace `0.000008` with the actual blended $/token for your served entity.
