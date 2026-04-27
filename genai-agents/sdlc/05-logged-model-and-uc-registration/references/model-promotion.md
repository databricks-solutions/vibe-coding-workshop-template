# Model Promotion Reference

Complete reference for champion/challenger promotion patterns in Genie Space
Optimizer. Covers LoggedModel aliases, UC registered model aliases, promotion
criteria, automated workflows, manual approval integration, and audit trails.

Grounded in: `src/genie_space_optimizer/optimization/models.py`.

---

## 1. Two-Level Alias System

This codebase uses two independent alias mechanisms:

| Level | API | Set by | Consumer |
|-------|-----|--------|----------|
| **LoggedModel alias** | `mlflow.set_logged_model_alias(model_id, "champion")` | `promote_best_model()` | Experiment UI, MLflow model card |
| **UC registered model alias** | `client.set_registered_model_alias(name, "champion", version)` | `register_uc_model()` | Catalog Explorer, downstream consumers |

Both can coexist in the same pipeline. The LoggedModel alias selects the best
iteration within an optimization run; the UC alias gates whether that iteration
gets promoted to the catalog-visible champion.

---

## 2. LoggedModel Champion Promotion

### Selection criteria

`promote_best_model()` picks the iteration with maximum `overall_accuracy`
from the Delta iterations table:

```python
full_evals = iterations_df[iterations_df["eval_scope"] == "full"]
if full_evals.empty:
    full_evals = iterations_df

best_idx = full_evals["overall_accuracy"].idxmax()
best_row = full_evals.loc[best_idx]
```

Preference is given to `eval_scope == "full"` (complete benchmark) over
partial evaluations.

### Alias setting

```python
alias_fn = getattr(mlflow, "set_logged_model_alias", None)
if callable(alias_fn):
    alias_fn(model_id=best_model_id, alias="champion")
```

The `getattr` guard ensures compatibility across MLflow versions.

### Post-promotion state update

```python
update_run_status(
    spark, run_id, catalog, schema,
    best_iteration=best_iteration,
    best_accuracy=best_accuracy,
    best_model_id=best_model_id,
)
```

This writes the champion selection back to the Delta run table for downstream
consumers and the optimizer UI.

---

## 3. UC Champion Promotion Criteria

The UC `@champion` alias has stricter gating than the LoggedModel alias.
Both criteria must pass:

### Criterion 1: Result correctness (primary)

```python
new_rc = new_scores.get("eval_result_correctness", 0.0)
existing_rc = existing_scores.get("eval_result_correctness", 0.0)
if new_rc < existing_rc:
    should_promote = False
```

Result correctness is the most business-critical metric — it measures whether
the agent returns correct answers to benchmark questions.

### Criterion 2: Average judge score (secondary)

```python
new_avg = sum(new_scores.values()) / max(len(new_scores), 1)
existing_avg = sum(existing_scores.values()) / max(len(existing_scores), 1)
if new_avg < existing_avg:
    should_promote = False
```

The average across all eight judges prevents models that improve on one
dimension while regressing on others.

### The eight judge dimensions

| Judge | What it measures |
|-------|-----------------|
| `eval_result_correctness` | Answer correctness against ground truth |
| `eval_syntax_validity` | SQL syntax correctness |
| `eval_schema_accuracy` | Correct table/column references |
| `eval_logical_accuracy` | Query logic correctness |
| `eval_semantic_equivalence` | Semantic match to reference queries |
| `eval_completeness` | Whether all required data is returned |
| `eval_response_quality` | Natural language response quality |
| `eval_asset_routing` | Correct routing to tables/views |

---

## 4. Automated Promotion Workflow

The full automated flow in a single optimization pipeline:

```
1. Run baseline evaluation (iteration 0)
   └── create_genie_model_version() → baseline model_id

2. Run optimization iterations (1..N)
   └── For each iteration:
       ├── create_genie_model_version() → iter model_id
       └── link_eval_scores_to_model(model_id, scores)

3. Promote best LoggedModel
   └── promote_best_model(spark, run_id, catalog, schema)
       ├── Select max overall_accuracy
       └── set_logged_model_alias(best_model_id, "champion")

4. Register to UC (with gating)
   └── register_uc_model(spark, run_id, catalog, schema)
       ├── Register new version (always)
       ├── Compare scores vs existing @champion
       └── Promote only if both criteria pass
```

### Timing

- Steps 1-2 happen during `run_lever_loop`
- Step 3 happens at the end of optimization, after convergence
- Step 4 happens after step 3, in the finalization phase

---

## 5. Manual Approval Integration

While this codebase uses fully automated promotion, you can add manual gates:

### Pattern: Approval-gated UC promotion

```python
def register_with_approval(
    spark, run_id, catalog, schema, ws,
    auto_promote: bool = False,
):
    """Register to UC; only promote if auto_promote is True."""
    result = register_uc_model(spark, run_id, catalog, schema, ws)
    if result and not auto_promote:
        result["promoted_to_champion"] = False
        logger.info(
            "Version %s registered but awaiting manual approval",
            result["version"],
        )
    return result
```

### Pattern: Threshold-gated promotion

```python
PROMOTION_THRESHOLDS = {
    "eval_result_correctness": 85.0,
    "overall_accuracy": 80.0,
}

def meets_promotion_thresholds(scores: dict[str, float]) -> bool:
    for metric, threshold in PROMOTION_THRESHOLDS.items():
        if scores.get(metric, 0.0) < threshold:
            return False
    return True
```

### Pattern: Repeatability gate

Require the model to meet criteria across multiple evaluation runs:

```python
REPEATABILITY_RUNS = 3
REPEATABILITY_TARGET = 90.0  # from config.py

def check_repeatability(
    tracking_client: MlflowClient,
    run_ids: list[str],
    metric: str = "eval_result_correctness",
) -> bool:
    scores = []
    for rid in run_ids[-REPEATABILITY_RUNS:]:
        data = tracking_client.get_run(rid).data
        scores.append(data.metrics.get(metric, 0.0))
    return all(s >= REPEATABILITY_TARGET for s in scores)
```

---

## 6. Audit Trail

### Tags on UC model versions

Every registered version carries tags for full traceability:

| Tag | Purpose |
|-----|---------|
| `genie.optimization_run_id` | Which optimization run produced this version |
| `genie.iteration` | Which iteration was selected as best |
| `genie.accuracy` | Overall accuracy of the champion iteration |
| `genie.baseline_accuracy` | Baseline accuracy for delta calculation |
| `genie.convergence_reason` | Why the optimizer stopped |
| `genie.source_run_id` | MLflow run with eval artifacts |
| `genie.overall_score` | Average judge score |
| `genie.held_out_accuracy` | Held-out benchmark accuracy (if available) |
| Per-judge scores | `eval_result_correctness`, `eval_syntax_validity`, etc. |

### Tags on UC registered model

| Tag | Purpose |
|-----|---------|
| `genie.space_id` | Genie Space ID |
| `genie.space_name` | Human-readable space name |
| `genie.domain` | Business domain |
| `genie.managed_by` | Always `"genie_space_optimizer"` |

### Lineage

- **Model → Run:** Each version's `run_id` links to the MLflow run with
  full evaluation traces and artifacts.
- **Model → Space:** `space_id` tag and `space_config` artifact link back
  to the Genie Space.
- **Model → Benchmark:** `benchmark_summary` artifact contains the questions,
  scores, and baseline comparison.

---

## 7. Rollback Patterns

### Rollback via LoggedModel

```python
from genie_space_optimizer.optimization.models import rollback_to_model

config = rollback_to_model(w, model_id="m-abc123")
```

Reads the `model_space_config` param from the LoggedModel and applies it
via the Genie PATCH API.

### Rollback via UC version

```python
client = MlflowClient(registry_uri="databricks-uc")

# Demote current champion
client.delete_registered_model_alias(uc_model_name, "champion")

# Promote previous version
client.set_registered_model_alias(uc_model_name, "champion", previous_version)
```

### Rollback checklist

1. Identify the target version (by version number or alias)
2. Verify the version's `space_config` artifact matches expectations
3. Apply the Genie Space config rollback (via `rollback_to_model` or manual)
4. Update the UC `@champion` alias to the rolled-back version
5. Log the rollback event (tag the version, update run status)

---

## 8. DO / DON'T Summary

```python
# DON'T: Promote without metric comparison
client.set_registered_model_alias(name, "champion", version)
```

```python
# DO: Compare against existing champion before promoting
existing = client.get_model_version_by_alias(name, "champion")
if scores_improved(new, existing):
    client.set_registered_model_alias(name, "champion", version)
```

```python
# DON'T: Rely on a single metric for promotion
if new_scores["eval_result_correctness"] > existing:
    promote()  # ignores regressions in other dimensions
```

```python
# DO: Check both primary metric and aggregate
if (new_rc >= existing_rc) and (new_avg >= existing_avg):
    promote()
```

```python
# DON'T: Skip audit tags on UC versions
mv = mlflow.register_model(uri, name)
# (no tags set — version becomes untraceable)
```

```python
# DO: Set comprehensive version tags
for key, value in version_tags.items():
    client.set_model_version_tag(name, mv.version, key, value)
```
