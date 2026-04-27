# Evaluation flow reference

Complete reference for the `run_evaluation()` pipeline, covering dataset preparation,
`predict_fn` construction, `mlflow.genai.evaluate()` invocation, result parsing,
score extraction, and MLflow run logging.

Grounded in: `src/genie_space_optimizer/optimization/evaluation.py`
(`run_evaluation()` L3341–4030, `make_predict_fn()` L1441, `_run_evaluate_with_retries()` L2769).

---

## 1. `mlflow.genai.evaluate()` parameter reference

```python
results = mlflow.genai.evaluate(
    data=eval_data,          # pandas DataFrame with 'inputs' and 'expectations' columns
    predict_fn=predict_fn,   # callable: receives inputs dict, returns response dict
    scorers=scorer_list,     # list of scorer callables (see Skill 08)
    model_id=model_id,       # optional: MLflow model ID (starts with "m-")
)
```

### Environment variables affecting evaluation

| Variable | Default | Effect |
|----------|---------|--------|
| `MLFLOW_GENAI_EVAL_MAX_WORKERS` | varies | Parallel workers for predict_fn calls |
| `MLFLOW_GENAI_EVAL_MAX_SCORER_WORKERS` | `"10"` | Parallel workers for scorer execution |
| `GENIE_SPACE_OPTIMIZER_EVAL_MAX_ATTEMPTS` | `"4"` | Maximum retry attempts |
| `GENIE_SPACE_OPTIMIZER_EVAL_RETRY_SLEEP_SECONDS` | `"10"` | Base sleep between retries |

---

## 2. `predict_fn` contract

MLflow unpacks each row's `inputs` dict into keyword arguments for `predict_fn`.
The function receives **only** `inputs`, not the full row with `expectations`.

```python
def predict_fn(inputs: dict) -> dict:
    question = inputs["question"]
    response = agent.generate_response(question)
    return {"response": response}
```

### This codebase: `make_predict_fn()` → `genie_predict_fn()`

`make_predict_fn()` returns a `@mlflow.trace`-decorated closure that:
rate-limits → queries Genie API → fetches result via Statement API →
executes GT SQL → normalizes → compares hashes.

The `inputs` dict keys that become keyword arguments:

| Key | Description |
|-----|-------------|
| `question_id` | Unique benchmark identifier |
| `question` | Natural language question |
| `space_id` | Genie Space ID |
| `expected_sql` | Ground-truth SQL |
| `catalog` | UC catalog name |
| `gold_schema` | Gold schema name |

### Building predict_fn for different agent types

**ResponsesAgent:**
```python
agent = ResponsesAgent(model="databricks-claude-sonnet-4-6")

def responses_predict_fn(inputs: dict) -> dict:
    result = agent.predict({"input": [{"role": "user", "content": inputs["question"]}]})
    return {"response": result.get("output", "")}
```

**Raw LLM (OpenAI-compatible):**
```python
client = OpenAI(base_url="https://...", api_key="...")

def llm_predict_fn(inputs: dict) -> dict:
    resp = client.chat.completions.create(
        model="databricks-claude-sonnet-4-6",
        messages=[{"role": "user", "content": inputs["question"]}],
    )
    return {"response": resp.choices[0].message.content}
```

**Genie Space (this codebase):**
```python
predict_fn = make_predict_fn(
    w=workspace_client, space_id="01ef...", spark=spark,
    catalog="main", schema="gold", warehouse_id="abc123", iteration=0,
)
```

---

## 3. `run_evaluation()` full implementation walkthrough

### Signature

```python
def run_evaluation(
    space_id: str,
    experiment_name: str,
    iteration: int,
    benchmarks: list[dict],
    domain: str,
    model_id: str | None,
    eval_scope: str,
    predict_fn: Any,
    scorers: list[Any],
    *,
    spark: SparkSession | None = None,
    w: WorkspaceClient | None = None,
    catalog: str = "",
    gold_schema: str = "",
    uc_schema: str = "",
    warehouse_id: str = "",
    patched_objects: list[str] | None = None,
    reference_sqls: dict[str, str] | None = None,
    optimization_run_id: str = "",
    lever: int | None = None,
    max_benchmark_count: int = MAX_BENCHMARK_COUNT,
) -> dict:
```

### Step-by-step flow

**Step 1 — Setup:** Sanitize domain, set experiment, build run name from
`BASELINE_RUN_NAME_TEMPLATE` (iteration 0) or `RUN_NAME_TEMPLATE`.

```python
ts = datetime.now().strftime("%Y%m%d_%H%M%S")
_tpl = BASELINE_RUN_NAME_TEMPLATE if iteration == 0 else RUN_NAME_TEMPLATE
run_name = format_mlflow_template(_tpl, iteration=iteration, timestamp=ts)
```

**Step 2 — Tags:** Start MLflow run, set `genie.space_id`, `genie.domain`,
`genie.iteration`, `genie.eval_scope`, `genie.lever`.

**Step 3 — Filter:** `filter_benchmarks_by_scope()` then `_precheck_benchmarks_for_eval()`
quarantines benchmarks with invalid SQL, permission issues, unresolved columns,
or bad join keys.

**Step 4 — Build DataFrame:**
```python
eval_records.append({
    "inputs": {"question_id": qid, "question": q, "space_id": sid,
               "expected_sql": esql, "catalog": cat, "gold_schema": gs},
    "expectations": {"expected_response": esql, "expected_asset": asset,
                     "previous_sql": ref_sqls.get(qid, "")},
})
eval_data = pd.DataFrame(eval_records)
```

If `reference_sqls` is provided, `repeatability_scorer` is auto-added to scorers.

**Step 5 — Evaluate with retries:** `_run_evaluate_with_retries()`, falling back
to `_run_evaluate_sequential_fallback()` on retryable errors.

**Step 6 — Extract scores:**
```python
per_judge = {name.replace("/mean", ""): val
             for name, val in eval_result.metrics.items() if "/mean" in name}
scores_100 = normalize_scores(per_judge)
thresholds_passed = all_thresholds_met(scores_100)
```

**Step 7 — Process rows:** Iterate `eval_result.tables["eval_results"]` for
arbiter verdicts, judge rationales, assessment metadata, failure artifacts.

**Step 8 — Arbiter-adjusted accuracy:** `_compute_arbiter_adjusted_accuracy()`
overrides raw `result_correctness` when the arbiter determines Genie was correct
despite a hash mismatch. Also arbiter-adjusts `logical_accuracy`,
`semantic_equivalence`, `completeness`, `schema_accuracy` for these rows.

**Step 9 — Log and return:**
```python
mlflow.log_metrics({"overall_accuracy": accuracy, "thresholds_passed": 1.0 if passed else 0.0, ...})

return {
    "run_id": run.info.run_id, "mlflow_run_id": run.info.run_id,
    "run_name": run_name, "iteration": iteration,
    "overall_accuracy": arbiter_adjusted_accuracy,
    "scores": scores_100, "thresholds_met": thresholds_passed,
    "per_judge": per_judge, "failure_question_ids": failure_ids,
    "arbiter_verdicts": arbiter_verdicts, "rows": rows_for_output,
    "trace_map": trace_map, ...
}
```

---

## 4. Result parsing

### `results.metrics` — flat dict of `{metric_name: float}`

```python
per_judge = {}
for name, value in results.metrics.items():
    if "/mean" in name:
        per_judge[name.replace("/mean", "")] = value
```

### `results.tables["eval_results"]` — pandas DataFrame, one row per benchmark

| Column pattern | Description |
|---------------|-------------|
| `inputs/*` | Input fields passed to predict_fn |
| `expectations/*` | Expected values for scorers |
| `outputs/*` | predict_fn return values |
| `{judge}/value` | Per-row judge verdict |
| `{judge}/rationale` | Judge explanation |
| `arbiter/value` | Arbiter verdict |
| `trace_id` | MLflow trace ID |

---

## 5. Score normalization

```python
def normalize_scores(scores: dict[str, float]) -> dict[str, float]:
    """Convert 0-1 → 0-100; leave 0-100 unchanged."""
    return {k: round(v * 100, 2) if 0 <= v <= 1.0 else round(v, 2) for k, v in scores.items()}
```

| Scale | Dict | Example key | Used by |
|-------|------|-------------|---------|
| 0–1 | `MLFLOW_THRESHOLDS` | `syntax_validity/mean` | MLflow native metrics |
| 0–100 | `DEFAULT_THRESHOLDS` | `syntax_validity` | `all_thresholds_met()` |

Always call `normalize_scores()` before comparing against `DEFAULT_THRESHOLDS`.

---

## 6. Retry wrapper

Multi-tier retry strategy:

```
Attempt 1 → workers=1
Attempt 2 → workers=EVAL_SINGLE_WORKER_FALLBACK, sleep 10s
Attempt 3 → sleep 20s
Attempt 4 → sleep 30s
→ Sequential fallback (one row at a time) on retryable failure
```

**Retryable exceptions** (`_is_retryable_eval_exception()`):
- `AttributeError` with "NoneType" + "info"/"assessments"/"trace"
- gRPC / `_MultiThreadedRendezvous` errors
- Harness traceback with NoneType trace references

**Harness patches** (`_patch_mlflow_harness_none_trace()`): guards
`_get_new_expectations` and `batch_link_traces_to_run` against None traces.

---

## 7. MLflow logging summary

| Category | What is logged |
|----------|---------------|
| **Params** | `space_id`, `iteration`, `dataset`, `eval_scope`, `num_scorers`, `domain`, `benchmark_count`, `model_id`, `catalog`, `gold_schema` |
| **Metrics** | `overall_accuracy`, `correct_count`, `total_questions`, `failure_count`, `excluded_count`, `thresholds_passed`, `harness_retry_count` |
| **Tags** | `genie.space_id`, `genie.domain`, `genie.iteration`, `genie.eval_scope`, `genie.optimization_run_id`, `genie.lever`, `evaluation_status` |
| **Artifacts** | `evaluation_runtime/evaluate_attempts.json`, `evaluation_runtime/benchmark_precheck.json`, `evaluation_runtime/question_failure_artifacts.json`, `evaluation_failure/evaluate_failure.json` (on error) |

### Trace recovery

When Genie API calls involving Spark Connect lose MLflow trace context, the
function extracts `trace_id` from rows where available and uses
`_recover_trace_map()` to search experiment traces by
`genie.optimization_run_id` + `genie.iteration` tags for the rest.

---

## 8. End-to-end example

```python
import mlflow
from genie_space_optimizer.common.config import (
    DEFAULT_THRESHOLDS, EXPERIMENT_PATH_TEMPLATE, format_mlflow_template,
)
from genie_space_optimizer.optimization.evaluation import (
    make_predict_fn, run_evaluation,
)
from genie_space_optimizer.optimization.scorers import make_all_scorers

exp_name = format_mlflow_template(
    EXPERIMENT_PATH_TEMPLATE, space_id="01ef...", domain="sales",
)
benchmarks = [{"id": "q1", "question": "Total sales by region?",
               "expected_sql": "SELECT region, SUM(amount) FROM sales GROUP BY region"}]

predict_fn = make_predict_fn(
    w=ws_client, space_id="01ef...", spark=spark,
    catalog="main", schema="gold", warehouse_id="abc123", iteration=0,
)
scorers = make_all_scorers(spark=spark, catalog="main", gold_schema="gold", domain="sales")

result = run_evaluation(
    space_id="01ef...", experiment_name=exp_name, iteration=0,
    benchmarks=benchmarks, domain="sales", model_id=None, eval_scope="full",
    predict_fn=predict_fn, scorers=scorers, spark=spark,
    catalog="main", gold_schema="gold",
)

if result["thresholds_met"]:
    print(f"PASS — accuracy: {result['overall_accuracy']:.1f}%")
else:
    for judge, score in result["scores"].items():
        threshold = DEFAULT_THRESHOLDS.get(judge, 0)
        if score < threshold:
            print(f"  FAIL: {judge}: {score:.1f} < {threshold:.1f}")
```
