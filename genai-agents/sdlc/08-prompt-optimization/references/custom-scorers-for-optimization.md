# Custom Scorers for Prompt Optimization

GEPA is a **reflection-based** optimizer: it reads per-row scores *and* rationales, then proposes edits to the prompt that would improve the rationale-with-score. Quality of the **rationale** therefore dominates optimization quality. Boolean-only scorers lose signal.

---

## Minimum Viable Scorer for Optimization

```python
from mlflow.genai.scorers import scorer
from mlflow.entities import Feedback

@scorer
def citation_scorer(outputs: dict, expectations: dict) -> Feedback:
    expected = set(expectations.get("expected_source_ids", []))
    answer = outputs.get("answer", "") or ""
    found = {sid for sid in expected if sid in answer}
    missing = expected - found
    extra = []

    if not expected:
        return Feedback(
            value=None,
            rationale="No expected_source_ids — scorer skipped this row.",
        )

    score = 1.0 if not missing else max(0.0, 1 - len(missing) / len(expected))
    rationale = (
        f"Cited {sorted(found)}. "
        f"Missing {sorted(missing)}. "
        f"Answer length: {len(answer)} chars."
    )
    return Feedback(value=score, rationale=rationale)
```

Notes:

- `value=None` skips the row (don't penalize missing labels).
- Use **partial credit** (e.g. fraction of citations matched) so GEPA sees a gradient.
- Rationale names what was missing, not just "wrong."

---

## Rationale Quality Rules

GEPA uses rationales as English text for the reflection model. Good rationales are:

1. **Specific**: `"Expected citation to SKY-POL-008 but answer cites SKY-POL-009"` — names the concrete disagreement.
2. **Invariant-free**: don't mention the candidate prompt body in the rationale. The optimizer writes the next prompt; the scorer judges the output.
3. **Short**: 1–3 sentences. Long rationales waste reflection tokens.
4. **Actionable**: "Answer opened with a greeting instead of a status summary" is actionable; "Answer was bad" is not.

---

## Weighted Aggregation

`optimize_prompts` aggregates multiple scorers with equal weight. To weight, wrap in a custom meta-scorer:

```python
@scorer
def weighted_quality(outputs, expectations, inputs) -> Feedback:
    c = citation_scorer(outputs=outputs, expectations=expectations)
    g = guideline_scorer(outputs=outputs, expectations=expectations)
    r = relevance_scorer(outputs=outputs, inputs=inputs)

    # weights: citation 0.5, guideline 0.3, relevance 0.2
    total = 0.5 * (c.value or 0) + 0.3 * (g.value or 0) + 0.2 * (r.value or 0)
    rationale = "\n".join([
        f"Citation ({c.value}): {c.rationale}",
        f"Guideline ({g.value}): {g.rationale}",
        f"Relevance ({r.value}): {r.rationale}",
    ])
    return Feedback(value=total, rationale=rationale)
```

Pass only `weighted_quality` to `optimize_prompts`.

---

## Guideline-Style Judges (LLM-Based)

Use `make_judge` for natural-language guideline checks. Always request a rationale.

```python
from mlflow.genai import make_judge

domain_accuracy_judge = make_judge(
    name="sky_loyalty_domain_accuracy",
    instructions=(
        "Score 1 if the answer follows SkyLoyalty policies (tier tier rules, "
        "status qualification thresholds, and award-booking procedures). "
        "Score 0 otherwise. Explain the specific policy violation in rationale."
    ),
    model="databricks:/databricks-claude-sonnet-4-6",
)
```

LLM judges are **non-deterministic**. When used during optimization:

- Set `temperature=0` (default for `make_judge`).
- Pin the judge model version (use endpoint version alias, not `@latest`).
- Budget accordingly — each optimization row calls every judge.

---

## Debugging a Scorer Before Optimization

1. Run a single row through `predict_fn` by hand.
2. Call the scorer directly with that row's outputs/expectations/inputs.
3. Inspect `Feedback.value` and `Feedback.rationale`.
4. Confirm: "Would a reflection model, reading only this rationale, know how to rewrite the prompt to fix it?"

If the answer to (4) is no, rewrite the rationale before optimizing.

---

## Common Scorer Bugs That Poison Optimization

| Bug | Symptom during optimization | Fix |
|-----|----------------------------|-----|
| `Feedback(value=...)` without `rationale` | Scores climb but rewrites are random | Always return non-empty rationale |
| Scorer raises on a row | Optimizer falls back to 0 for that row — noisy signal | Guard with `try/except`, return `value=None` |
| Scorer reads `outputs["response"]` but predict_fn returns `outputs["answer"]` | All rows score 0 | Match keys |
| Scorer value is always 0 or 1 (no partial credit) | GEPA reflection has no gradient | Return fractional values where possible |
| Judge temperature > 0 | Scores flicker between iterations; optimizer chases noise | `temperature=0` and pin model |
