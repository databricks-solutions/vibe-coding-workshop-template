# Gate checking reference

Complete reference for threshold gates, improvement detection, regression checking,
and deployment gate logic. Covers the full decision chain from evaluation scores
to accept/reject/rollback.

Grounded in: `src/genie_space_optimizer/optimization/evaluation.py` (L900–927),
`src/genie_space_optimizer/optimization/optimizer.py` (`detect_regressions` L9223–9253),
`src/genie_space_optimizer/common/config.py` (`DEFAULT_THRESHOLDS`, `REGRESSION_THRESHOLD`).

---

## 1. `all_thresholds_met()` implementation

The primary gate function. Scores must be on the **0–100 scale**.

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

### Default thresholds (0–100 scale)

```python
DEFAULT_THRESHOLDS = {
    "syntax_validity": 98.0,
    "schema_accuracy": 95.0,
    "logical_accuracy": 90.0,
    "semantic_equivalence": 90.0,
    "completeness": 90.0,
    "response_quality": 0.0,    # informational only
    "result_correctness": 85.0,
    "asset_routing": 95.0,
}
```

### Corresponding MLflow thresholds (0–1 scale)

```python
MLFLOW_THRESHOLDS = {
    "syntax_validity/mean": 0.98,
    "schema_accuracy/mean": 0.95,
    "logical_accuracy/mean": 0.90,
    "semantic_equivalence/mean": 0.90,
    "completeness/mean": 0.90,
    "response_quality/mean": 0.0,
    "result_correctness/mean": 0.85,
    "asset_routing/mean": 0.95,
}
```

**CRITICAL:** Never compare `DEFAULT_THRESHOLDS` (0–100) against raw MLflow
metrics (0–1). Always run `normalize_scores()` first.

---

## 2. `detect_regressions()` — comparing against baseline

Defined in `optimizer.py`, this function checks whether any metric dropped more
than a configurable threshold compared to the previous best scores.

```python
def detect_regressions(
    current_scores: dict[str, float],
    previous_scores: dict[str, float],
    threshold: float = REGRESSION_THRESHOLD,
    skip_judges: set[str] | None = None,
) -> list[dict]:
    """Detect if any metric dropped more than ``threshold`` percentage points.

    Parameters
    ----------
    skip_judges : set[str] | None
        Judge names to exclude from regression checking. Use for
        informational judges whose convergence threshold is 0.0
        (e.g. ``response_quality``).
    """
    regressions: list[dict] = []
    for key in previous_scores:
        if skip_judges and key in skip_judges:
            continue
        prev_val = previous_scores.get(key, 0)
        curr_val = current_scores.get(key, 0)
        if curr_val < prev_val - threshold:
            regressions.append({
                "judge": key,
                "previous": prev_val,
                "current": curr_val,
                "drop": prev_val - curr_val,
            })
    return regressions
```

### Configuration

| Constant | Default | Source | Description |
|----------|---------|--------|-------------|
| `REGRESSION_THRESHOLD` | `5.0` | config.py L83 | Max allowed drop (percentage points) |
| `MAX_NOISE_FLOOR` | `5.0` | config.py L84 | Cap on noise floor estimate |

### Noise-floor adjustment

In the lever loop, the effective regression tolerance is:

```python
effective_regression_tol = max(REGRESSION_THRESHOLD, noise_floor)
```

With small benchmark sets (e.g. 10 questions), the noise floor can be 10%+,
so the effective tolerance rises to prevent false rollbacks.

### Informational judges

Judges with a threshold of `0.0` (like `response_quality`) are classified as
informational and can be skipped:

```python
_informational_judges = {j for j, t in DEFAULT_THRESHOLDS.items() if t == 0.0}
regressions = detect_regressions(
    full_scores, best_scores,
    threshold=effective_regression_tol,
    skip_judges=_informational_judges,
)
```

---

## 3. Deployment gate logic

The three-gate system in the lever loop evaluates each iteration:

### Gate 1: Slice gate (fast check)

Run evaluation on a **subset** of benchmarks related to the patched objects.
Quick feedback on whether the patch helped.

| Config | Default | Description |
|--------|---------|-------------|
| `SLICE_GATE_TOLERANCE` | `15.0` | Max allowed drop on the slice |
| `ENABLE_SLICE_GATE` | `False` | Feature flag |
| `SLICE_GATE_MIN_REDUCTION` | `0.5` | Min failure reduction to pass |

### Gate 2: P0 gate (critical questions)

Evaluate the top 3 most critical questions. Zero P0 failures required.

### Gate 3: Full gate (comprehensive)

Full benchmark evaluation with regression detection:

```python
# In the lever loop (harness.py)
effective_regression_tol = max(REGRESSION_THRESHOLD, noise_floor)

# Skip informational judges
_informational_judges = {j for j, t in DEFAULT_THRESHOLDS.items() if t == 0.0}
if full_accuracy >= best_accuracy - 2 * noise_floor:
    _informational_judges.add("asset_routing")

regressions = detect_regressions(
    full_scores, best_scores,
    threshold=effective_regression_tol,
    skip_judges=_informational_judges,
)

# Gate decision
if not regressions:
    # ACCEPT iteration
    pass
else:
    # ROLLBACK iteration
    pass
```

### Accept vs rollback decision tree

```
Full eval complete
│
├── regressions detected?
│   ├── YES → ROLLBACK
│   │   └── Record regression details
│   │   └── Revert to best_scores / best_model_id
│   │   └── Increment consecutive_rollbacks
│   │
│   └── NO → ACCEPT
│       └── Update best_scores / best_model_id
│       └── Write iteration to Delta
│       └── Register instruction version snapshot
│       └── Reset consecutive_rollbacks = 0
│
└── consecutive_rollbacks >= CONSECUTIVE_ROLLBACK_LIMIT?
    └── YES → STOP lever loop (optimizer is stuck)
```

---

## 4. Reporting: which metrics passed/failed

`run_evaluation()` logs `thresholds_passed` as an MLflow metric and returns it.
When `EVAL_DEBUG` is enabled, `_print_eval_summary()` prints each judge with
PASS/FAIL markers.

### Programmatic reports

```python
def print_threshold_report(eval_result: dict) -> None:
    scores, passed = eval_result["scores"], eval_result["thresholds_met"]
    print(f"\nOverall: {'PASS' if passed else 'FAIL'}")
    for judge, threshold in sorted(DEFAULT_THRESHOLDS.items()):
        score = scores.get(judge, 0.0)
        status = "PASS" if score >= threshold else "FAIL"
        print(f"  {judge:<24s} {score:6.1f}  (>= {threshold:.1f})  {status}")


def print_regression_report(regressions: list[dict]) -> None:
    for reg in regressions:
        print(f"  {reg['judge']}: {reg['current']:.1f} ← {reg['previous']:.1f} "
              f"(dropped {reg['drop']:.1f} pts)")
```

---

## 5. Gate feedback logging

Gate outcomes are attached to evaluation traces as MLflow Feedback assessments
via `log_gate_feedback_on_traces()`. Each trace gets a `gate_{type}` assessment
with value `"accept"` or `"rollback"`, rationale including regression summary,
and metadata with `lever`, `iteration`, `question_id`, and `regressions`.

---

## 6. Integration with deployment automation (Skill 11)

The deployment gate requires **both** absolute and relative quality:

```python
def should_deploy(eval_result: dict, baseline_result: dict) -> bool:
    if not eval_result["thresholds_met"]:
        return False
    regressions = detect_regressions(
        eval_result["scores"], baseline_result["scores"], threshold=REGRESSION_THRESHOLD,
    )
    return len(regressions) == 0
```

### Gate override

For manual approval, set tags for audit trail:

```python
mlflow.set_tags({
    "gate.override": "true",
    "gate.override_reason": reason,
    "gate.approver": approver,
})
```

---

## 7. Common gate-checking mistakes

| Mistake | Consequence | Fix |
|---------|-------------|-----|
| Comparing 0–100 scores to `MLFLOW_THRESHOLDS` | False passes/failures | Use `DEFAULT_THRESHOLDS` with normalized scores |
| Ignoring noise floor for small benchmarks | False rollbacks | Use `max(REGRESSION_THRESHOLD, noise_floor)` |
| Including informational judges in regression check | Blocks progress on non-critical metrics | Use `skip_judges` parameter |
| Checking improvement without arbiter adjustment | Inaccurate comparison | Use arbiter-adjusted accuracy from eval result |
| Hardcoding threshold values | Drift from config | Always read from `DEFAULT_THRESHOLDS` |
