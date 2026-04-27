# When to Run Prompt Optimization

Prompt optimization (`mlflow.genai.optimize_prompts`) is powerful but not free. It costs scorer calls (LLM $$), reflection-model calls, and wall time. This reference helps you decide whether the cost is justified for a given quality gap.

---

## Decision Checklist

Run optimization only if **all of A** and **at least one of B** are true.

### A. Pre-conditions (all required)

- Prompt is registered in UC Prompt Registry with a stable alias (`@production`).
- Evaluation dataset has ≥ 20 rows with `expectations` populated.
- At least one scorer returns per-row `Feedback(value, rationale)`.
- A baseline evaluation run exists showing the failing scorer below threshold on dev set.
- You can reproduce the failure locally by calling the agent with the baseline prompt.

### B. Optimization is likely to help (any one)

- The failing scorer measures **output shape/content**: citation accuracy, format compliance, guideline following, tone, required fields, refusal behavior.
- Manual prompt edits improved one failing case but regressed another — iteration cost is high.
- Two prompts interact (planner + answerer) and you need joint tuning.
- You have 3+ custom guidelines and tuning each by hand is not converging.

---

## When NOT to Optimize

Prompt optimization wastes budget (and can degrade quality) in these cases.

| Symptom | Real problem | Go to |
|---------|--------------|-------|
| Agent cannot find the right document | Retrieval / index coverage | Vector Search tuning |
| Agent returns stale data | Tool/data freshness | Tool implementation |
| Agent calls wrong tool | Tool description / selection logic | [tracks/A-custom-agent-apps/03-tools-and-mcp](../../tracks/A-custom-agent-apps/03-tools-and-mcp/SKILL.md) |
| Latency is bad but quality is fine | Model / infra | Model serving config |
| Scorer is flaky (judge inconsistent) | Scorer design | [03-scorers-and-judges](../../03-scorers-and-judges/SKILL.md) |
| Only 1–2 failing rows out of 20 | Noise, not signal | Accept; add to labeling queue |
| Eval dataset has `expectations=None` on most rows | No signal for optimizer | [02-evaluation-datasets](../../02-evaluation-datasets/SKILL.md) — fill expectations |

---

## Cost/Benefit Estimation

A single optimization run with `max_metric_calls=150` on a 50-row dataset with 3 scorers will cost roughly:

- **150 scorer calls × 3 scorers ≈ 450 LLM calls** at the judge model (usually the same as your agent model).
- **~30–60 reflection-model calls** on the reflection model (Claude Sonnet 4.6+).
- **~15–30 min wall time** on a standard Databricks Model Serving endpoint.

Rule of thumb: if a manual prompt edit would take you < 30 min and you have a concrete theory of the fix, edit manually. Reserve optimization for when the space of possible edits is large (multi-paragraph instruction or multi-prompt system).

---

## Signs Optimization Is Working

Watch the optimization run live in MLflow UI → Run → metrics tab:

- `candidate_score` climbs over iterations, then plateaus. Good.
- `candidate_score` flat at baseline for > 30% of budget. Bad — stop and review scorer rationales; likely a scorer design issue or non-prompt-shaped gap.
- Score climbs on train split but fails on dev split. Overfitting — shrink `max_metric_calls` or reduce scorer count.

---

## When Three Iterations Don't Help

If you've run optimization 3 times on the same prompt with no sustained dev-set improvement:

1. **Stop.** The gap is not prompt-shaped.
2. Review per-row `Feedback.rationale` on the failing rows manually.
3. Check whether failures correlate with retrieval misses, tool call errors, or upstream data issues.
4. File an issue-focused eval subset (see [02-evaluation-datasets](../../02-evaluation-datasets/SKILL.md)) and debug via [tracks/A-custom-agent-apps/08-debugging](../../tracks/A-custom-agent-apps/08-debugging/SKILL.md).
