# Threshold Checking — Complete Reference

Quality gates in the Genie Space Optimizer use two parallel threshold
dictionaries and a pair of helper functions to decide whether an evaluation run
passes. This reference covers the exact values, scale normalization, the
checking implementation, and tuning strategies.

> **Grounded in:**
> `src/genie_space_optimizer/common/config.py` — `DEFAULT_THRESHOLDS`, `MLFLOW_THRESHOLDS`
> `src/genie_space_optimizer/optimization/evaluation.py` — `normalize_scores()`, `all_thresholds_met()`

---

## `DEFAULT_THRESHOLDS` (0-100 Scale)

Used by the optimization harness and the `all_thresholds_met()` gate.
Values represent percentages.

```python
DEFAULT_THRESHOLDS = {
    "syntax_validity":       98.0,
    "schema_accuracy":       95.0,
    "logical_accuracy":      90.0,
    "semantic_equivalence":  90.0,
    "completeness":          90.0,
    "response_quality":       0.0,    # informational — not gating
    "result_correctness":    85.0,
    "asset_routing":         95.0,
}
```

### Per-Metric Rationale

| Metric | Threshold | Rationale |
|---|---|---|
| `syntax_validity` | 98% | SQL must parse. A 2% tolerance covers edge cases where Genie returns commentary instead of SQL. |
| `schema_accuracy` | 95% | Wrong table/column is a high-severity error but LLM judges have ~5% noise margin. |
| `logical_accuracy` | 90% | Logic errors (wrong aggregation, filter) are contextual and LLM judgment is less deterministic. |
| `semantic_equivalence` | 90% | Same rationale as logical accuracy — semantic comparison inherently fuzzy. |
| `completeness` | 90% | Missing a filter or dimension is common for complex questions with implicit requirements. |
| `response_quality` | 0% | Set to 0 because Genie's NL response text is not always available via the API. Informational only. |
| `result_correctness` | 85% | Result-set comparison is strict (hash-based), but empty-result edge cases and temporal drift lower the effective ceiling. |
| `asset_routing` | 95% | MV vs TABLE preference is important for performance but has override logic for matching results. |

### Additional Targets

```python
REPEATABILITY_TARGET = 90.0
```

Repeatability is checked separately (not in `DEFAULT_THRESHOLDS`) because
it requires a prior baseline run for comparison.

---

## `MLFLOW_THRESHOLDS` (0-1 Scale)

Mirrors `DEFAULT_THRESHOLDS` on a 0-1 scale for use with raw
`mlflow.genai.evaluate()` metric keys (which use `{scorer_name}/mean`):

```python
MLFLOW_THRESHOLDS = {
    "syntax_validity/mean":       0.98,
    "schema_accuracy/mean":       0.95,
    "logical_accuracy/mean":      0.90,
    "semantic_equivalence/mean":  0.90,
    "completeness/mean":          0.90,
    "response_quality/mean":      0.0,
    "result_correctness/mean":    0.85,
    "asset_routing/mean":         0.95,
}
```

Use `MLFLOW_THRESHOLDS` when comparing directly against
`eval_result.metrics["syntax_validity/mean"]`. Use `DEFAULT_THRESHOLDS` after
calling `normalize_scores()`.

---

## `normalize_scores()` — Scale Conversion

Converts 0-1 scores to 0-100 for human readability. Leaves scores already
above 1.0 unchanged (they are already on a 0-100 scale).

```python
def normalize_scores(scores: dict[str, float]) -> dict[str, float]:
    """Convert 0-1 scale -> 0-100 scale; leave 0-100 unchanged."""
    normalized: dict[str, float] = {}
    for key, val in scores.items():
        if 0 <= val <= 1.0:
            normalized[key] = round(val * 100, 2)
        else:
            normalized[key] = round(val, 2)
    return normalized
```

**Edge case:** A score of exactly `1.0` is treated as "0-1 scale" and becomes
`100.0`. This is correct for percentage metrics but would be wrong for a scorer
that genuinely returns integer `1`. All scorers in this codebase use binary
`"yes"/"no"` (mapped to 1.0/0.0) or percentage means, so this heuristic is
safe.

---

## `all_thresholds_met()` — Quality Gate

```python
def all_thresholds_met(
    scores: dict[str, float],
    targets: dict[str, float] | None = None,
) -> bool:
    """Return True only when every judge meets its threshold.

    ``scores`` should be on a 0-100 scale. ``targets`` defaults to
    ``DEFAULT_THRESHOLDS`` from config.
    """
    targets = targets or DEFAULT_THRESHOLDS
    for judge, threshold in targets.items():
        actual = scores.get(judge)
        if actual is None:
            return False
        if actual < threshold:
            return False
    return True
```

### Behaviour

- **Missing metric → `False`:** If any threshold key is absent from `scores`,
  the gate fails. This prevents accidentally passing when a scorer did not run.
- **Strict inequality:** `actual < threshold` means the score must meet or
  exceed the target. A score of exactly 90.0 with a threshold of 90.0 passes.
- **`response_quality` at 0.0:** Setting a threshold to 0.0 means any score
  passes, effectively disabling the gate for that metric.
- **Custom targets:** Pass `targets=` to override `DEFAULT_THRESHOLDS` for
  experimental runs or A/B comparisons.

### Typical Usage in the Harness

```python
from genie_space_optimizer.optimization.evaluation import (
    all_thresholds_met,
    normalize_scores,
)

# After mlflow.genai.evaluate():
per_judge = {}
for metric_name in eval_result.metrics:
    if "/mean" in metric_name:
        judge_name = metric_name.replace("/mean", "")
        per_judge[judge_name] = eval_result.metrics[metric_name]

scores_100 = normalize_scores(per_judge)
thresholds_passed = all_thresholds_met(scores_100)
mlflow.log_metric("thresholds_passed", 1.0 if thresholds_passed else 0.0)
```

---

## Threshold Tuning Strategies

### Strategy 1: Raise After Baseline Stabilizes

Start with the defaults. After 3-5 baseline runs show consistent scores,
tighten thresholds to the lower quartile of observed scores. This prevents
regressions without false-failing on normal variance.

### Strategy 2: Per-Space Overrides

Different Genie Spaces have different complexity profiles. A simple 5-question
space may sustain 98% across all judges, while a 50-question space with
temporal queries may need relaxed thresholds. Pass space-specific targets:

```python
relaxed = {**DEFAULT_THRESHOLDS, "result_correctness": 75.0}
all_thresholds_met(scores_100, targets=relaxed)
```

### Strategy 3: Graduated Gating

Use strict thresholds for blocking deployment and relaxed thresholds for
informational alerts:

```python
# Must-pass gate
if not all_thresholds_met(scores_100):
    raise RuntimeError("Quality gate failed — blocking deployment")

# Warning gate
warning_thresholds = {k: v + 5.0 for k, v in DEFAULT_THRESHOLDS.items()}
if not all_thresholds_met(scores_100, targets=warning_thresholds):
    logger.warning("Scores below warning thresholds — review before next iteration")
```

### Strategy 4: Disabling a Metric

Set the threshold to `0.0` (as done for `response_quality`). The metric still
runs and logs but never blocks the gate.

### Strategy 5: Adding New Metrics

When adding a new scorer, add its threshold to both dictionaries:

```python
# config.py
DEFAULT_THRESHOLDS["date_granularity"] = 85.0
MLFLOW_THRESHOLDS["date_granularity/mean"] = 0.85
```

If you forget, `all_thresholds_met()` will ignore the new metric (it only
checks keys present in `targets`). To require it, add the key.

---

## Score Normalization Gotchas

| Scenario | Raw value | After `normalize_scores()` | Correct? |
|---|---|---|---|
| Binary scorer, 80% pass rate | 0.80 | 80.0 | Yes |
| All rows pass | 1.0 | 100.0 | Yes |
| No rows pass | 0.0 | 0.0 | Yes |
| Score already on 0-100 scale (bug) | 85.0 | 85.0 | Yes (passthrough) |
| Scorer returns integer 1 meaning "pass" | 1.0 | 100.0 | Ambiguous (see note above) |

When reading evaluation results from MLflow, scores from `eval_result.metrics`
are always on the 0-1 scale (mean of binary pass/fail per row). Always call
`normalize_scores()` before `all_thresholds_met()`.

---

## Grounded In

- `src/genie_space_optimizer/common/config.py` — `DEFAULT_THRESHOLDS`, `MLFLOW_THRESHOLDS`, `REPEATABILITY_TARGET`
- `src/genie_space_optimizer/optimization/evaluation.py` — `normalize_scores()`, `all_thresholds_met()`
- [Databricks MLflow 3 GenAI: Scorers](https://docs.databricks.com/aws/en/mlflow3/genai/eval-monitor/concepts/scorers)
