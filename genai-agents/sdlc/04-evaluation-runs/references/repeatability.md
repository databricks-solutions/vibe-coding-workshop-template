# Repeatability evaluation reference

Reference for repeatability assessment — running the same questions multiple times,
comparing SQL and result-hash variance, flagging non-deterministic responses, and
integrating with benchmark quarantine.

Grounded in: `src/genie_space_optimizer/optimization/evaluation.py`
(`run_repeatability_evaluation()` L4039–4388, `extract_reference_sqls()` L4391,
`extract_reference_result_hashes()` L4420),
`src/genie_space_optimizer/common/config.py` (`REPEATABILITY_TARGET`,
`REPEATABILITY_CLASSIFICATIONS`, `FINALIZE_REPEATABILITY_PASSES`).

---

## 1. `run_repeatability_evaluation()` implementation

### Key parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `reference_sqls` | `dict[str, str]` | `{question_id: sql}` from a prior evaluation |
| `reference_result_hashes` | `dict[str, str] \| None` | `{question_id: hash}` for execution comparison |
| `run_label` | `str` | Suffix for run name (e.g. `"final_1"`) |
| `predict_fn` | callable | Same predict_fn used for primary evaluation |

### Step-by-step flow

**Step 1 — Setup:** Set experiment, build run name as
`genie_repeatability_iter{iteration}_{timestamp}_{run_label}`.

**Step 2 — Build DataFrame with previous references:**
```python
eval_records.append({
    "inputs": {"question_id": qid, "question": q, "space_id": sid,
               "expected_sql": esql, "catalog": cat, "gold_schema": gs},
    "expectations": {"expected_response": esql, "expected_asset": asset,
                     "previous_sql": reference_sqls.get(qid, ""),
                     "previous_result_hash": ref_hashes.get(qid, "")},
})
```

The key difference from primary evaluation: `expectations` includes `previous_sql`
and `previous_result_hash` for the repeatability scorer.

**Step 3 — Repeatability-specific scorers:**
```python
from genie_space_optimizer.optimization.scorers import make_repeatability_scorers
scorers = make_repeatability_scorers()
```

**Step 4 — Evaluate** with `_run_evaluate_with_retries()` + sequential fallback.

**Step 5 — Extract scores and compute three-tier sub-metrics** (see § 3).

**Step 6 — Return:**
```python
return {
    "run_id": run.info.run_id, "repeatability_pct": repeatability_pct,
    "repeatability_execution_pct": ..., "repeatability_structural_pct": ...,
    "repeatability_exact_pct": ..., "tier_counts": _tier_counts,
    "per_judge": per_judge, "rows": rows_for_output,
    "scores": normalize_scores(per_judge), "trace_map": rep_trace_map,
}
```

---

## 2. Configuration constants

```python
REPEATABILITY_TARGET = 90.0                 # quality bar for repeatability

REPEATABILITY_CLASSIFICATIONS = {
    95: "IDENTICAL",           # near-perfect reproducibility
    80: "MINOR_VARIANCE",      # acceptable for most use cases
    60: "SIGNIFICANT_VARIANCE",# needs investigation
    0: "CRITICAL_VARIANCE",    # unreliable — action required
}

REPEATABILITY_EXTRA_QUERIES = 2             # extra iterations for stability assessment
FINALIZE_REPEATABILITY_PASSES = 1           # passes in Finalize stage

REPEATABILITY_FIX_BY_ASSET = {
    "TABLE": "Add structured metadata (business_definition, synonyms[]) ...",
    "MV":    "Add structured column metadata to metric view columns ...",
    "TVF":   "Add instruction clarifying deterministic parameter selection ...",
    "NONE":  "Add routing instruction to direct questions to the appropriate asset type.",
}
```

---

## 3. Three-tier sub-metrics

The function recomputes tier classification from row data:

| Tier | Meaning | Detection |
|------|---------|-----------|
| `execution` | Result hash matches previous hash | Both hashes present and equal |
| `structural` | SQL is structurally equivalent | Normalized AST comparison |
| `exact` | SQL text is identical | Hash of normalized SQL matches |
| `first_eval` | No previous reference exists | Missing `previous_sql` and `previous_result_hash` |
| `no_output` | Current eval produced no SQL | Empty response |
| `none` | No match at any tier | Everything else |

```python
if _prev_rh and _curr_rh:
    _tier_counts["execution"] += 1
elif verdict == "yes":
    if _structurally_equivalent(_prev_sql, _curr_sql):
        _tier_counts["structural"] += 1
    elif _sql_hash(_prev_sql) == _sql_hash(_curr_sql):
        _tier_counts["exact"] += 1
else:
    _tier_counts["none"] += 1
```

The headline repeatability is `max(repeatability_execution_pct, scorer_repeatability_pct)`.

---

## 4. Detecting non-deterministic responses

```python
def find_unreliable_questions(rep_result: dict) -> list[dict]:
    """Identify questions with non-deterministic Genie responses."""
    unreliable = []
    for row in rep_result["rows"]:
        verdict = str(
            row.get("repeatability/value") or row.get("feedback/repeatability/value") or ""
        ).lower().strip()
        if verdict != "yes":
            qid = row.get("inputs/question_id") or (row.get("inputs") or {}).get("question_id", "")
            unreliable.append({
                "question_id": qid, "verdict": verdict,
                "previous_sql": (row.get("expectations") or {}).get("previous_sql", ""),
                "current_sql": (row.get("outputs") or {}).get("response", ""),
            })
    return unreliable
```

### Classification

```python
def classify_repeatability(score: float) -> str:
    for threshold in sorted(REPEATABILITY_CLASSIFICATIONS.keys(), reverse=True):
        if score >= threshold:
            return REPEATABILITY_CLASSIFICATIONS[threshold]
    return "CRITICAL_VARIANCE"
```

---

## 5. Statistical analysis: multi-pass variance

```python
import numpy as np

def run_multi_pass_repeatability(n_passes, space_id, experiment_name,
                                  benchmarks, domain, predict_fn,
                                  reference_sqls, **kwargs):
    scores = []
    for i in range(n_passes):
        result = run_repeatability_evaluation(
            space_id=space_id, experiment_name=experiment_name, iteration=0,
            benchmarks=benchmarks, domain=domain, reference_sqls=reference_sqls,
            predict_fn=predict_fn, run_label=f"pass_{i+1}", **kwargs,
        )
        scores.append(result["repeatability_pct"])
    return {
        "mean": np.mean(scores), "std": np.std(scores),
        "cv": np.std(scores) / np.mean(scores) * 100 if np.mean(scores) > 0 else 0,
        "min": np.min(scores), "max": np.max(scores),
        "meets_target": np.mean(scores) >= REPEATABILITY_TARGET,
    }
```

**Coefficient of variation (CV)** measures relative variability:

| CV Range | Interpretation |
|----------|---------------|
| 0–5% | Highly stable |
| 5–15% | Acceptable |
| 15–30% | Concerning |
| >30% | Unreliable |

---

## 6. Extracting references for subsequent evaluations

### `extract_reference_sqls(eval_result)` → `{question_id: sql}`

Builds the mapping from a prior evaluation's output. Handles both flat column
names (`inputs/question_id`) and nested dicts (`request.kwargs.question_id`).

### `extract_reference_result_hashes(eval_result)` → `{question_id: hash}`

Mirrors `extract_reference_sqls()` but pulls the result-set hash. Enables
execution-based (Tier 1) repeatability comparison.

---

## 7. Benchmark quarantine integration

Questions with `CRITICAL_VARIANCE` (score < 60) across multiple passes can be
quarantined — excluded from the accuracy denominator in
`_compute_arbiter_adjusted_accuracy()`.

**Quarantine workflow:**

```
Question fails repeatability
├── Score >= 60 → Keep, log warning
└── Score < 60 → Flag for quarantine
    ├── GT repair attempted and failed? → Quarantine
    └── GT repair not attempted → Try repair first
```

Quarantined questions are logged in `benchmark_precheck.json` and excluded from
accuracy calculations, preventing unstable questions from causing false rollbacks.

---

## 8. MLflow metrics logged

| Metric | Description |
|--------|-------------|
| `repeatability_pct` | Headline (max of execution and scorer) |
| `repeatability_scorer_pct` | Raw scorer-reported |
| `repeatability_execution_pct` | Execution-hash pass rate |
| `repeatability_structural_pct` | Structural SQL pass rate |
| `repeatability_exact_pct` | Exact SQL text match rate |

---

## 9. End-to-end example

```python
from genie_space_optimizer.optimization.evaluation import (
    run_evaluation, run_repeatability_evaluation,
    extract_reference_sqls, extract_reference_result_hashes,
)
from genie_space_optimizer.common.config import REPEATABILITY_TARGET

primary_result = run_evaluation(
    space_id=space_id, experiment_name=exp_name, iteration=0,
    benchmarks=benchmarks, domain=domain, model_id=None, eval_scope="full",
    predict_fn=predict_fn, scorers=scorers, spark=spark,
    catalog="main", gold_schema="gold",
)

ref_sqls = extract_reference_sqls(primary_result)
ref_hashes = extract_reference_result_hashes(primary_result)

rep_result = run_repeatability_evaluation(
    space_id=space_id, experiment_name=exp_name, iteration=0,
    benchmarks=benchmarks, domain=domain, reference_sqls=ref_sqls,
    predict_fn=predict_fn, catalog="main", gold_schema="gold",
    reference_result_hashes=ref_hashes, run_label="stability_check",
)

if rep_result["repeatability_pct"] >= REPEATABILITY_TARGET:
    print(f"PASS — {rep_result['repeatability_pct']:.1f}%")
else:
    print(f"FAIL — {rep_result['repeatability_pct']:.1f}% (target: {REPEATABILITY_TARGET}%)")
    for tier, count in rep_result["tier_counts"].items():
        if count > 0:
            print(f"  {tier}: {count}")
```
