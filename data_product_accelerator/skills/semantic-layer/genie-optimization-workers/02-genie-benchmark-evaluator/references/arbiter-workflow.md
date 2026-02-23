# Arbiter Workflow

The arbiter is Layer 3 of the Genie Benchmark Evaluator. It runs as a proper `@scorer` inside `mlflow.genai.evaluate()` — the 8th scorer in `all_scorers`. It is **conditional**: when `result_correctness` passes (results match), the arbiter returns `value="skipped"` with zero LLM cost. When results disagree, it invokes the LLM to determine which SQL is correct and drives benchmark auto-correction.

Arbiter verdicts appear in the MLflow Judges tab, Traces, and Evaluation Runs automatically. The arbiter reads `outputs["comparison"]` pre-computed in `genie_predict_fn` — it never calls `spark.sql()` directly.

---

## Arbiter Flow Decision Table

| Verdict | What It Means | Auto-Action |
|---------|---------------|-------------|
| `genie_correct` | Genie's SQL is right; GT SQL is wrong | Update benchmark YAML + MLflow dataset with Genie's SQL |
| `ground_truth_correct` | GT SQL is right; Genie is wrong | Keep benchmark; optimize metadata to fix Genie |
| `both_correct` | Both are valid ways to answer the question | Add disambiguation instruction to Genie Space |
| `neither_correct` | Both SQLs have issues | Flag for human review; do not auto-update |

The arbiter prevents "chasing wrong ground truth" — if the benchmark SQL is incorrect, continuing to optimize toward it wastes iterations.

---

## arbiter_scorer

The arbiter is a `@scorer`-decorated function in `all_scorers`. It reads the pre-computed `outputs["comparison"]` dict from `genie_predict_fn` — no `spark.sql()` calls.

**IMPORTANT:** Do NOT stack `@mlflow.trace` on `@scorer`. The mlflow.genai.evaluate() harness traces scorer execution automatically. Stacking strips `.register()` and leaves the Judges tab empty.

```python
@scorer
def arbiter_scorer(inputs: dict, outputs: dict, expectations: dict) -> Feedback:
    """Layer 3: Arbiter — conditional scorer that fires only when results disagree.

    Reads outputs["comparison"] pre-computed in genie_predict_fn.
    Returns value="skipped" when results match (no LLM call).
    When results disagree, invokes the LLM arbiter via _call_llm_for_scoring()
    and returns one of: genie_correct, ground_truth_correct, both_correct, neither_correct.
    """
    cmp = outputs.get("comparison", {}) if isinstance(outputs, dict) else {}

    if cmp.get("match"):
        return Feedback(name="arbiter", value="skipped",
                        rationale="Results match — arbiter not invoked.",
                        source=CODE_SOURCE)

    if cmp.get("error"):
        return Feedback(name="arbiter", value="skipped",
                        rationale=f"SQL execution error — cannot arbitrate: {cmp['error']}",
                        source=CODE_SOURCE)

    genie_sql = sanitize_sql(_extract_response_text(outputs))
    gt_sql = resolve_sql(expectations.get("expected_response", ""))
    question = inputs.get("question", "")

    _arbiter_instructions = loaded_prompts.get("arbiter", JUDGE_PROMPTS.get("arbiter", ""))
    prompt = (
        f"{_arbiter_instructions}\n\n"
        f"Question: {question}\n"
        f"Ground Truth SQL: {gt_sql}\n"
        f"Genie SQL: {genie_sql}\n"
        f"Result comparison: {json.dumps(cmp)}\n\n"
        'Respond with JSON only: {"verdict": "<genie_correct|ground_truth_correct|both_correct|neither_correct>", '
        '"failure_type": "<wrong_aggregation|wrong_filter|wrong_table|other>", '
        '"blame_set": ["<blamed_object>"], '
        '"rationale": "<brief explanation>"}'
    )
    try:
        result = _call_llm_for_scoring(prompt)
        verdict = result.get("verdict", "ground_truth_correct")
        if verdict not in ("genie_correct", "ground_truth_correct", "both_correct", "neither_correct"):
            verdict = _parse_arbiter_verdict(type("F", (), {"rationale": result.get("rationale", str(result))})())
        _meta = None
        if verdict in ("ground_truth_correct", "neither_correct"):
            _meta = build_asi_metadata(
                failure_type=result.get("failure_type", "other"),
                severity="major", confidence=0.85,
                blame_set=result.get("blame_set", []),
                counterfactual_fix=result.get("rationale", ""))
        return Feedback(
            name="arbiter", value=verdict,
            rationale=result.get("rationale", verdict),
            source=LLM_SOURCE, metadata=_meta)
    except Exception as e:
        verdict = "ground_truth_correct"
        return Feedback(
            name="arbiter", value=verdict,
            rationale=f"Arbiter LLM call failed, defaulting to ground_truth_correct: {e}",
            source=LLM_SOURCE,
            metadata=build_asi_metadata(
                failure_type="other", severity="info", confidence=0.0,
                counterfactual_fix="LLM judge unavailable — retry or check endpoint"))
```

---

## _parse_arbiter_verdict

```python
def _parse_arbiter_verdict(feedback) -> str:
    """Extract verdict from arbiter feedback text."""
    text = str(feedback.rationale if hasattr(feedback, "rationale") else feedback).lower()
    for v in ["genie_correct", "both_correct", "neither_correct", "ground_truth_correct"]:
        if v in text:
            return v
    return "ground_truth_correct"
```

---

## _arbiter_action

```python
def _arbiter_action(verdict: str) -> str:
    actions = {
        "genie_correct": "Auto-update benchmark with Genie SQL as new ground truth.",
        "ground_truth_correct": "Genie SQL is wrong. Optimize metadata to fix.",
        "both_correct": "Add disambiguation instruction to Genie Space.",
        "neither_correct": "Both SQLs need revision. Flag for human review.",
    }
    return actions.get(verdict, "Flag for human review.")
```

---

## handle_arbiter_verdict (Post-Evaluation)

After `mlflow.genai.evaluate()` completes, the orchestrator reads arbiter verdicts from the evaluation results table and calls this function for each non-skipped verdict to drive benchmark auto-correction.

```python
def handle_arbiter_verdict(verdict: dict, question_id: str, genie_sql: str,
                           gt_sql: str, yaml_path: str, domain: str) -> dict:
    """Process arbiter verdict from evaluation results: auto-update benchmark or flag for action.

    Called by the orchestrator AFTER mlflow.genai.evaluate() completes,
    not during scoring. Reads arbiter verdicts from eval_result.tables["eval_results"].

    Returns:
        dict describing the action taken.
    """
    v = verdict["verdict"]

    if v == "genie_correct":
        _update_yaml_ground_truth(yaml_path, domain, question_id, genie_sql)
        return {
            "action": "benchmark_updated",
            "question_id": question_id,
            "old_sql": gt_sql,
            "new_sql": genie_sql,
            "reason": verdict["rationale"],
        }
    elif v == "both_correct":
        return {
            "action": "add_disambiguation",
            "question_id": question_id,
            "reason": verdict["rationale"],
        }
    else:
        return {
            "action": "optimize_metadata",
            "question_id": question_id,
            "reason": verdict["rationale"],
        }
```

---

## _update_yaml_ground_truth

```python
import yaml

def _update_yaml_ground_truth(yaml_path: str, domain: str, question_id: str, new_sql: str):
    """Update a single question's expected_sql in the golden queries YAML."""
    with open(yaml_path) as f:
        data = yaml.safe_load(f)

    questions = data.get(domain, [])
    for q in questions:
        if q.get("id") == question_id:
            q["expected_sql"] = new_sql
            break

    with open(yaml_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)
```
