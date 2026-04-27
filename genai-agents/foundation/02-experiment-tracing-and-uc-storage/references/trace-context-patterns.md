# Trace Context Patterns — Complete Reference

> **Skill:** 01-experiment-tracing-setup
> **Grounded in:** `src/genie_space_optimizer/optimization/evaluation.py` —
> `update_current_trace()`, trace tags and metadata patterns

---

## 1. How `update_current_trace` Works

`mlflow.update_current_trace()` enriches the active trace with **tags**
and **metadata**. Both are key-value pairs, but they serve different
purposes and have different visibility (and mutability) in the MLflow
UI.

```python
import mlflow

mlflow.update_current_trace(
    metadata={
        "mlflow.trace.user":    "u-12345",
        "mlflow.trace.session": session_id,
        "agent_version":        "1.2.0",
        "space_id":             "abc123",
    },
    tags={
        "domain":   "billing",
        "sla_tier": "gold",
    },
)
```

### Tags vs Metadata

| Property | Tags | Metadata |
| --- | --- | --- |
| **Purpose** | Mutable routing dimensions | Stable identifiers, version pins, audit trail |
| **Searchable** | Yes — `tags.<key>` in `filter_string` | Yes — `metadata.<key>` in `filter_string` |
| **UI affordances** | Filterable columns | Filterable columns + first-class facets for reserved keys (`mlflow.trace.user`, `mlflow.trace.session`) |
| **Size limit** | ~5000 chars per value | ~5000 chars per value |
| **Mutability** | Mutable post-log | **Immutable** post-log |
| **Use for** | `domain`, `sla_tier`, `experiment_arm`, `feature_flag_active` | `mlflow.trace.user`, `mlflow.trace.session`, `mlflow.source.type`, `agent_version`, `deployment_id` |

> **Canonical reference:** see [F2c — Trace context and environments](../../02c-trace-context-and-environments/SKILL.md)
> for the full pattern (reserved metadata fields, auto-populated env
> metadata, `APP_ENVIRONMENT` override, `mlflow-tracing` vs full-MLflow
> package choice). This file documents the supplemental tag taxonomy
> used in the `genie_space_optimizer` reference implementation.

### Call site requirements

`update_current_trace()` must be called from within an active trace context.
Outside of a trace it is a no-op (no error raised). The project wraps it in
a try/except as a defensive pattern:

```python
try:
    mlflow.update_current_trace(tags=_trace_tags, metadata=_trace_metadata)
except Exception:
    pass
```

This matches `evaluation.py` line ~1504 where tags and metadata are set inside
the `@mlflow.trace`-decorated `genie_predict_fn`.

---

## 2. Reserved metadata fields and recommended tag taxonomy

### Reserved metadata fields (MLflow-recognized)

These are **metadata** (immutable, MLflow-recognized for first-class UI
facets), not tags. Always set them under `metadata=` in
`update_current_trace`:

| Metadata key | Example value | Purpose |
| --- | --- | --- |
| `mlflow.trace.user` | `user@example.com` | Attribute trace to triggering user. Lights up per-user filter in the Trace UI. |
| `mlflow.trace.session` | `opt-run-20250315-001` | Group traces from a multi-turn conversation or run. Lights up session grouping in the Trace UI. |
| `mlflow.source.type` | `production` (override of default `LOCAL`/`UNKNOWN`) | Deployment environment. Override from the `APP_ENVIRONMENT` env var. |
| `agent_version` | `2.1.0` | Build / semantic version. Useful for regression cohorts. |

> **Migrating from tags:** earlier code in this codebase (and many
> first-pass deployments) placed `mlflow.trace.user` /
> `mlflow.trace.session` under `tags=`. Reads still work — the values
> remain searchable as `tags.<key>` — but the trace loses its
> immutability guarantee and the UI's user / session facets do not
> light up. Move to `metadata=` when you next touch the call site;
> see [F2c § Track users and sessions](../../02c-trace-context-and-environments/SKILL.md#track-users-and-sessions).

### Project-specific tags

These are **tags** — mutable routing dimensions, free-form. The
`genie_space_optimizer` reference implementation uses these:

| Tag key                        | Example value             | Set by            | Purpose                        |
| ------------------------------ | ------------------------- | ----------------- | ------------------------------ |
| `space_id`                     | `abc123`                  | `evaluation.py`   | Filter traces by Genie Space    |
| `question_id`                  | `q-42`                    | `evaluation.py`   | Link trace to eval question     |
| `genie.optimization_run_id`    | `run-xyz`                 | `evaluation.py`   | Cross-reference with run table  |
| `genie.iteration`              | `3`                       | `evaluation.py`   | Iteration within optimization   |
| `genie.lever`                  | `2`                       | `evaluation.py`   | Which lever was being tested    |
| `genie.eval_scope`             | `full`                    | `evaluation.py`   | Scope of evaluation run         |

### Recommended tags for new agents

These are **mutable routing tags** — pick what makes sense for your
filter / cohort views. For deployment environment specifically, prefer
`mlflow.source.type` under metadata (overridden from `APP_ENVIRONMENT`)
over a free-form `environment` tag.

| Tag key            | Description                                | Example                  |
| ------------------ | ------------------------------------------ | ------------------------ |
| `domain`           | Business domain the agent serves           | `billing`, `support`     |
| `sla_tier`         | SLA cohort for alerting                    | `gold`, `silver`         |
| `model_name`       | LLM model used                             | `claude-sonnet-4-6`      |
| `prompt_version`   | Version of the prompt template             | `v3`                     |
| `experiment_arm`   | A/B test arm                               | `control`, `treatment`   |

### Complete tagging example

```python
import os

import mlflow


@mlflow.trace(name="agent_inference", span_type="AGENT")
def agent_inference(query: str, *, session_id: str, user_id: str) -> dict:
    """Agent entry point with comprehensive trace tagging."""
    mlflow.update_current_trace(
        metadata={
            "mlflow.trace.user":    user_id,
            "mlflow.trace.session": session_id,
            "mlflow.source.type":   os.getenv("APP_ENVIRONMENT", "development"),
            "agent_version":        "2.1.0",
            "query_length":         str(len(query)),
            "input_hash":           _hash(query),
        },
        tags={
            "domain":   "billing",
            "sla_tier": "gold",
        },
    )

    result = _process(query)

    mlflow.update_current_trace(
        metadata={
            "output_length": str(len(str(result))),
            "output_hash":   _hash(str(result)),
        },
    )
    return result
```

---

## 3. Metadata Patterns for Debugging

Metadata is not searchable but appears on the trace detail view. Use it for
values that help investigate specific traces after you have found them via tags.

### Recommended metadata keys

| Key              | Type   | Purpose                                       |
| ---------------- | ------ | --------------------------------------------- |
| `request_id`     | `str`  | Correlate with HTTP request logs               |
| `input_hash`     | `str`  | Detect duplicate or cached inputs              |
| `retry_count`    | `str`  | How many retries occurred before success        |
| `space_id`       | `str`  | Genie Space context (used in evaluation.py)    |
| `iteration`      | `str`  | Optimization iteration number                  |
| `eval_scope`     | `str`  | Whether this was a full or partial eval         |
| `latency_ms`     | `str`  | End-to-end latency for the trace               |
| `cache_hit`      | `str`  | Whether the result came from cache             |

### Example: debugging metadata on a multi-step trace

```python
import hashlib
import time

import mlflow


def run_with_debug_metadata(query: str, request_id: str) -> dict:
    """Attach debugging metadata at multiple points in the trace."""
    start = time.monotonic()

    with mlflow.start_span(name="full_pipeline") as span:
        span.set_inputs({"query": query})

        mlflow.update_current_trace(
            metadata={
                "request_id": request_id,
                "input_hash": hashlib.sha256(query.encode()).hexdigest()[:12],
            },
        )

        result = process_query(query)
        elapsed_ms = int((time.monotonic() - start) * 1000)

        mlflow.update_current_trace(
            metadata={
                "latency_ms": str(elapsed_ms),
                "retry_count": str(result.get("retries", 0)),
                "cache_hit": str(result.get("from_cache", False)).lower(),
            },
        )

        span.set_outputs(result)
        return result
```

---

## 4. Trace Search Patterns Using Tags

### Search traces via the MLflow client

```python
from mlflow.client import MlflowClient

client = MlflowClient()

# All traces for a specific session (reserved metadata field)
traces = client.search_traces(
    experiment_ids=["12345"],
    filter_string="metadata.`mlflow.trace.session` = 'opt-run-20250315-001'",
    max_results=100,
)

# Traces from a specific user in production (both reserved metadata)
traces = client.search_traces(
    experiment_ids=["12345"],
    filter_string=(
        "metadata.`mlflow.trace.user` = 'alice@example.com' "
        "AND metadata.`mlflow.source.type` = 'production'"
    ),
    max_results=50,
)

# Traces for a specific Genie Space and iteration (project-specific tags)
traces = client.search_traces(
    experiment_ids=["12345"],
    filter_string=(
        "tags.`space_id` = 'abc123' "
        "AND tags.`genie.iteration` = '3'"
    ),
    order_by=["timestamp DESC"],
)
```

### Search traces via SQL (Databricks)

On Databricks, traces are queryable via the system tables:

```sql
SELECT
    trace_id,
    timestamp_ms,
    metadata,
    tags,
    status
FROM system.mlflow.traces
WHERE
    experiment_id = '12345'
    AND tags['space_id'] = 'abc123'
    AND metadata['mlflow.source.type'] = 'production'
ORDER BY timestamp_ms DESC
LIMIT 50
```

---

## 5. Integration with Monitoring Dashboards

### Lakeview dashboard queries

Build dashboards that aggregate trace data by tag dimensions:

```sql
-- Error rate by agent version (last 24h)
SELECT
    metadata['agent_version'] AS version,
    COUNT(*) AS total,
    SUM(CASE WHEN status = 'ERROR' THEN 1 ELSE 0 END) AS errors,
    ROUND(100.0 * SUM(CASE WHEN status = 'ERROR' THEN 1 ELSE 0 END) / COUNT(*), 2) AS error_pct
FROM system.mlflow.traces
WHERE
    experiment_id = '12345'
    AND timestamp_ms > (UNIX_TIMESTAMP() - 86400) * 1000
GROUP BY metadata['agent_version']
ORDER BY error_pct DESC
```

```sql
-- P50/P95 latency by domain, production only
SELECT
    tags['domain'] AS domain,
    PERCENTILE(execution_duration_ms, 0.5) AS p50_ms,
    PERCENTILE(execution_duration_ms, 0.95) AS p95_ms,
    COUNT(*) AS trace_count
FROM system.mlflow.traces
WHERE
    experiment_id = '12345'
    AND metadata['mlflow.source.type'] = 'production'
GROUP BY tags['domain']
```

### Tag conventions for alerting

Use consistent tag keys so monitoring rules can match patterns:

```python
ALERT_TAGS = {
    "sla_tier": "gold",
    "on_call_team": "ml-platform",
}

mlflow.update_current_trace(tags=ALERT_TAGS)
```

Then configure alerts on traces where `status = 'ERROR'` AND
`tags['sla_tier'] = 'gold'` to trigger PagerDuty or Slack notifications.
