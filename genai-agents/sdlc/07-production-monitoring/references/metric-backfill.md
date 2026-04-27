# Metric Backfill: Historical Trace Re-Scoring Reference

Re-run registered scorers over historical traces for a given time window.
Essential after policy changes, scorer bug fixes, or when adding new quality
dimensions to an existing production deployment.

> **Source**: [Production monitoring – Databricks MLflow 3 GenAI](https://docs.databricks.com/aws/en/mlflow3/genai/eval-monitor/production-monitoring)

---

## When to Backfill

| Scenario | Example |
|----------|---------|
| New scorer added | Added `prod_relevance` scorer; want scores on last 30 days of traces |
| Scorer bug fixed | Custom scorer had a regex typo; need to re-score affected window |
| Policy tightened | Safety guidelines updated; re-evaluate historical responses |
| Scorer version rotation | Replaced `prod_tone_v1` with `prod_tone_v2`; backfill v2 scores |
| Audit request | Compliance requires scoring of traces from a specific incident window |

---

## Basic Usage

```python
from mlflow.genai import backfill_scorers

backfill_scorers(
    scorer_names=["prod_safety", "prod_correctness"],
    start_time="2026-01-01",
    end_time="2026-03-27",
)
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `scorer_names` | `list[str]` | Yes | Registered scorer names to run |
| `start_time` | `str` | Yes | ISO-8601 date or datetime (inclusive) |
| `end_time` | `str` | Yes | ISO-8601 date or datetime (exclusive) |

### Name matching

Scorer names must **exactly** match what was passed to `.register(name=...)`.
Use `mlflow.genai.list_scorers()` to verify names before backfilling.

```python
import mlflow

scorers = mlflow.genai.list_scorers()
valid_names = [s.name for s in scorers]
print(valid_names)
# ['prod_safety', 'prod_correctness', 'prod_tone', ...]
```

---

## Time Range Selection

### Best practices

| Guideline | Rationale |
|-----------|-----------|
| Start with a narrow window (1 day) | Verify scorer works on real data before full range |
| Align with trace archival retention | No point backfilling beyond what's retained |
| Use date strings for day boundaries | `"2026-03-01"` is cleaner than datetime objects |
| Avoid overlapping with active scoring | Backfill + live scoring on same traces can produce duplicates |

### Window sizing examples

```python
from mlflow.genai import backfill_scorers

# Last 24 hours (narrow test)
backfill_scorers(
    scorer_names=["prod_safety"],
    start_time="2026-03-26",
    end_time="2026-03-27",
)

# Last 7 days
backfill_scorers(
    scorer_names=["prod_safety", "prod_correctness"],
    start_time="2026-03-20",
    end_time="2026-03-27",
)

# Full quarter
backfill_scorers(
    scorer_names=["prod_safety"],
    start_time="2026-01-01",
    end_time="2026-03-27",
)
```

---

## Progress Monitoring

Backfill runs asynchronously on the platform. Monitor progress through:

### 1. MLflow UI

The MLflow Experiments UI shows backfill jobs under the model's monitoring
tab. Check for status, progress percentage, and any errors.

### 2. Trace archival table

Query the archival table for newly scored traces:

```sql
SELECT
    a.scorer_name,
    COUNT(*) AS backfilled_count,
    MIN(t.timestamp) AS earliest_trace,
    MAX(t.timestamp) AS latest_trace
FROM main.monitoring.agent_traces t
LATERAL VIEW EXPLODE(t.assessments) AS a
WHERE a.scorer_name IN ('prod_safety', 'prod_correctness')
  AND a.timestamp > DATEADD(HOUR, -1, CURRENT_TIMESTAMP())
GROUP BY 1;
```

### 3. Programmatic status check

```python
import mlflow

scorers = mlflow.genai.list_scorers()
for s in scorers:
    print(f"{s.name}: status={s.status}")
```

---

## Handling Backfill Failures

### Common failure modes

| Failure | Cause | Recovery |
|---------|-------|----------|
| Scorer not found | Name typo or scorer was deleted | Verify with `list_scorers()`; re-register if needed |
| Timeout on large window | Too many traces in range | Break into smaller windows (weekly chunks) |
| LLM rate limits | Judge scorer hitting endpoint limits | Reduce window size; backfill during off-peak |
| Scorer code error | Bug in custom scorer function | Fix the scorer, re-register, then re-backfill |
| Partial completion | Platform interruption mid-backfill | Re-run same window; platform skips already-scored traces |

### Chunked backfill for large ranges

```python
from datetime import date, timedelta
from mlflow.genai import backfill_scorers

def chunked_backfill(
    scorer_names: list[str],
    start: date,
    end: date,
    chunk_days: int = 7,
) -> None:
    """Break a large backfill into weekly chunks for reliability."""
    current = start
    while current < end:
        chunk_end = min(current + timedelta(days=chunk_days), end)
        print(f"Backfilling {current} to {chunk_end}...")
        try:
            backfill_scorers(
                scorer_names=scorer_names,
                start_time=current.isoformat(),
                end_time=chunk_end.isoformat(),
            )
            print(f"  Completed: {current} to {chunk_end}")
        except Exception as e:
            print(f"  FAILED: {current} to {chunk_end}: {e}")
        current = chunk_end


chunked_backfill(
    scorer_names=["prod_safety", "prod_correctness"],
    start=date(2026, 1, 1),
    end=date(2026, 3, 27),
    chunk_days=7,
)
```

---

## Re-Backfilling After Scorer Updates

When you fix a bug in a scorer or tighten evaluation criteria:

### Step 1: Register the updated scorer

```python
from mlflow.genai.scorers import Safety
from mlflow.genai import ScorerSamplingConfig

new_safety = Safety().register(
    name="prod_safety_v2",
    model_name="my-agent",
)
new_safety = new_safety.start(
    sampling_config=ScorerSamplingConfig(sample_rate=1.0)
)
```

### Step 2: Backfill historical traces with the new scorer

```python
from mlflow.genai import backfill_scorers

backfill_scorers(
    scorer_names=["prod_safety_v2"],
    start_time="2026-01-01",
    end_time="2026-03-27",
)
```

### Step 3: Retire the old scorer

```python
import mlflow

mlflow.genai.delete_scorer("prod_safety_v1")
```

### Step 4: Update dashboard queries

Update any SQL queries or alerts that reference the old scorer name:

```sql
-- Before
WHERE a.scorer_name = 'prod_safety_v1'

-- After
WHERE a.scorer_name = 'prod_safety_v2'

-- Or use LIKE for version-agnostic queries
WHERE a.scorer_name LIKE 'prod_safety%'
```

---

## Backfill vs Live Scoring Interaction

| Aspect | Live scoring | Backfill |
|--------|-------------|----------|
| Trigger | New trace arrives | Explicit API call |
| Sampling | Respects `ScorerSamplingConfig` | Scores all traces in range |
| Deduplication | N/A | Platform may skip already-scored traces |
| Cost | Ongoing, spread over time | Burst; plan for rate limits |
| Latency | Near real-time | Batch; minutes to hours depending on volume |

---

## Validation After Backfill

Confirm backfill succeeded with these checks:

```sql
-- 1. Count backfilled assessments
SELECT
    a.scorer_name,
    COUNT(*) AS assessment_count
FROM main.monitoring.agent_traces t
LATERAL VIEW EXPLODE(t.assessments) AS a
WHERE t.timestamp BETWEEN '2026-01-01' AND '2026-03-27'
  AND a.scorer_name IN ('prod_safety', 'prod_correctness')
GROUP BY 1;

-- 2. Check for gaps (days with zero assessments)
SELECT
    DATE(t.timestamp) AS day,
    COUNT(a.scorer_name) AS assessments
FROM main.monitoring.agent_traces t
LEFT JOIN LATERAL (
    SELECT scorer_name FROM EXPLODE(t.assessments)
    WHERE scorer_name = 'prod_safety'
) a
WHERE t.timestamp BETWEEN '2026-01-01' AND '2026-03-27'
GROUP BY 1
HAVING assessments = 0
ORDER BY 1;

-- 3. Score distribution sanity check
SELECT
    a.scorer_name,
    AVG(CAST(a.score_value AS DOUBLE)) AS avg_score,
    MIN(CAST(a.score_value AS DOUBLE)) AS min_score,
    MAX(CAST(a.score_value AS DOUBLE)) AS max_score,
    STDDEV(CAST(a.score_value AS DOUBLE)) AS stddev_score
FROM main.monitoring.agent_traces t
LATERAL VIEW EXPLODE(t.assessments) AS a
WHERE t.timestamp BETWEEN '2026-01-01' AND '2026-03-27'
  AND a.scorer_name IN ('prod_safety', 'prod_correctness')
GROUP BY 1;
```

---

## References

- [Production monitoring docs](https://docs.databricks.com/aws/en/mlflow3/genai/eval-monitor/production-monitoring)
- [`registered-scorers.md`](registered-scorers.md) — scorer lifecycle and registration
- [`monitoring-dashboard-queries.md`](monitoring-dashboard-queries.md) — dashboard SQL using backfilled data
