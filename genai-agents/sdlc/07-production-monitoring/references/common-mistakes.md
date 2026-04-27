# Common Mistakes: Production Monitoring

Read this reference when debugging scorer registration, sampling, trace archival,
dashboard queries, or UC OTEL monitoring. Pair with the main
[`../SKILL.md`](../SKILL.md) workflow and validation checklist.

---

## Mistake → impact → fix

| Mistake | Why it hurts | Fix |
|---------|----------------|-----|
| Ignoring return value of `start()` | Scorer appears registered but active monitor handle is wrong | Always assign: `s = s.start(...)` |
| Heavy imports at module top in `@scorer` | Serialization or worker import failures | Move imports inside the scorer function |
| 100% sampling on every LLM judge | Cost and latency spikes | Use the sampling table in the skill; cap expensive judges |
| `model_name` mismatch | Scores not attached to the traced deployment | Use the exact registered model / endpoint name MLflow expects |
| No trace archival | Cannot debug past incidents or backfill | Enable `enable_databricks_trace_archival` early |
| Duplicate scorer names | Confusing lifecycle and dashboards | Namespace by env: `prod_safety`, `staging_safety` |
| Enabling archival per-request | Race conditions and wasted overhead | Call `enable_databricks_trace_archival` once at startup |
| Hardcoded dates in dashboards | Queries go stale | Use `DATEADD(DAY, -N, CURRENT_TIMESTAMP())` |
| Backfill with typo'd scorer name | Silently produces no results | Verify with `list_scorers()` first |
| Missing `set_databricks_monitoring_sql_warehouse_id` (UC OTEL) | Scorer results don't persist to UC Delta tables | Call at startup before registering scorers |
| UC OTEL tables lack `MODIFY` grant | Traces write but scorer results fail silently | Grant `MODIFY` + `SELECT` on all four `*_otel_*` tables |
| Querying wrong OTEL table suffix | No results or unexpected data | `_otel_spans` for traces, `_otel_metrics` for numeric scores, `_otel_annotations` for feedback |

---

## Related references

- [`registered-scorers.md`](registered-scorers.md) — lifecycle and registration details
- [`trace-archival.md`](trace-archival.md) — archival setup and permissions
- [`metric-backfill.md`](metric-backfill.md) — backfill pitfalls
- [`uc-otel-queries.md`](uc-otel-queries.md) — UC OTEL dashboard SQL and export patterns
