# Budget and Cost Controls

`GepaPromptOptimizer` is bounded by `max_metric_calls` — total scorer invocations across candidates and iterations. This reference covers sizing, early-stopping heuristics, and what to do when convergence stalls.

---

## Sizing by Dataset × Prompts × Scorers

Rough formula: `max_metric_calls ≈ dataset_rows × iterations × 1.5`, where `iterations` is 3–6.

| Dataset rows | Prompts | Scorers | `max_metric_calls` | Approx wall time* | Approx LLM $** |
|--------------|---------|---------|--------------------|--------------------|----------------|
| 20 | 1 | 2 | 100 | 10 min | $2–5 |
| 50 | 1 | 2 | 150 | 20 min | $5–10 |
| 50 | 1 | 3–4 | 200 | 25 min | $8–15 |
| 50 | 2 | 3 | 250 | 40 min | $15–25 |
| 100 | 1 | 3 | 300 | 40 min | $15–25 |
| 100 | 2–3 | 3–4 | 400–500 | 60–90 min | $30–60 |

\* Wall time assumes Claude Sonnet 4.6 reflection model on standard Databricks Model Serving.
\** Rough $$ assumes pay-per-token on the judge model — adjust for PT throughput units.

---

## Reading the Convergence Curve

Open the optimization MLflow run while it is executing.

| Pattern | Meaning | Action |
|---------|---------|--------|
| `candidate_score` climbs smoothly, plateaus at ~70% of budget | Healthy convergence | Let it finish |
| Flat at baseline for first 30% of budget | Scorer design issue or gap not prompt-shaped | Kill run; review rationales |
| Climbs on train, dips on dev | Overfitting | Reduce `max_metric_calls`, or add dev-set early stop |
| Oscillates wildly | Scorer is non-deterministic (judge temp > 0) or flaky | Pin judge, `temperature=0`, retry |
| Climbs slowly, still rising at budget end | Under-budget | Raise `max_metric_calls` by 50%, re-run |

---

## Early Stopping

Native early stop is `optimizer=GepaPromptOptimizer(patience=N)` — stop if N consecutive iterations produce no improvement. Typical `patience=3`.

```python
GepaPromptOptimizer(
    reflection_model="databricks:/databricks-claude-sonnet-4-6",
    max_metric_calls=300,
    patience=3,
)
```

Combine with a **train/dev split**: optimize on train, validate on dev after each iteration, stop when dev-score stops improving even if train-score rises.

---

## Reflection Model Choice

Reflection model quality dominates GEPA quality.

| Model | Use for |
|-------|---------|
| `databricks:/databricks-claude-sonnet-4-6` | Recommended default; strong reasoning and instruction following |
| `databricks:/databricks-claude-opus-4-5` | When complex multi-prompt coordination is needed |
| GPT-4-class (via provider gateway) | Also good; benchmark against Sonnet first |
| Weak/small models (7B class) | Not recommended — rewrites are low-quality |

The reflection model is usually the most expensive component per call, but the total reflection-model call count is low (≈ 1 per iteration, not per row), so switching to a stronger reflection model rarely dominates the bill.

---

## Watching Costs Live

```python
import mlflow

with mlflow.start_run(run_name="prompt_opt") as run:
    result = mlflow.genai.optimize_prompts(...)

    # Log cost markers
    mlflow.log_metric("max_metric_calls_used", result.total_metric_calls)
    mlflow.log_metric("iterations_run", len(result.iteration_history))
    mlflow.log_metric("final_improvement",
                      result.final_eval_score - result.initial_eval_score)
```

Compare `total_metric_calls` vs `max_metric_calls`. If always hitting the cap, you're under-budgeted.

---

## Stall Recovery

If three runs in a row show no improvement:

1. **Review scorer rationales on 5 failing rows.** Are they specific enough to rewrite the prompt?
2. **Check `predict_fn` sanity** — kwarg actually reaches the LLM. See [predict-fn-contract.md](predict-fn-contract.md).
3. **Inspect candidate prompts** in the run artifacts. Are they changing meaningfully?
4. **Consider** that the quality gap is not prompt-shaped. Stop optimizing; debug.

---

## Cost Guardrails in CI

If you run prompt optimization from CI on PR merge (don't, usually), hard-cap budget:

```yaml
- name: Prompt optimization (nightly only)
  if: github.event.schedule == '0 3 * * *'
  run: python scripts/optimize_prompt.py --max-metric-calls 200 --budget-usd 25
```

Better pattern: **run optimization by hand from a notebook when Step 4 eval regresses**, then open a PR that flips `@staging` to the new version. CI validates via the standard Step 4 eval run.
