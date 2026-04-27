# UC Gating Reference

Complete reference for Unity Catalog model registration with metric-based
gating. Covers the configuration templates, the `register_uc_model()`
implementation, score comparison logic, champion alias management, and
rollback patterns.

Grounded in: `src/genie_space_optimizer/optimization/models.py` and
`src/genie_space_optimizer/common/config.py`.

---

## 1. Configuration (`config.py`)

### UC Registered Model Template

```python
UC_REGISTERED_MODEL_TEMPLATE = "{{ catalog }}.{{ schema }}.genie_space_{{ space_id }}"
```

Produces a three-level UC name:

```python
from genie_space_optimizer.common.config import (
    UC_REGISTERED_MODEL_TEMPLATE,
    format_mlflow_template,
)

uc_model_name = format_mlflow_template(
    UC_REGISTERED_MODEL_TEMPLATE,
    catalog="main",
    schema="genie_optimization",
    space_id="abc123",
)
# Result: "main.genie_optimization.genie_space_abc123"
```

### Enable/Disable Flag

```python
ENABLE_UC_MODEL_REGISTRATION: bool = True
```

When `False`, `register_uc_model()` returns `None` immediately without
touching Unity Catalog. Use this to disable registration in dev/test
environments or customer workspaces where UC write access is restricted.

---

## 2. `MlflowClient(registry_uri="databricks-uc")` Usage

UC registration requires an MlflowClient configured for the UC registry:

```python
from mlflow.tracking import MlflowClient
from mlflow import set_registry_uri

set_registry_uri("databricks-uc")
client = MlflowClient(registry_uri="databricks-uc")
```

Both the global `set_registry_uri` and the client-level `registry_uri` must
point to `"databricks-uc"`. Without this, `register_model()` writes to the
wrong backend (workspace model registry instead of UC).

### Client operations used

| Operation | Purpose |
|-----------|---------|
| `client.get_registered_model(name)` | Check if UC model exists |
| `client.create_registered_model(name, description)` | Create new UC model |
| `client.update_registered_model(name, description)` | Update model description |
| `client.set_registered_model_tag(name, key, value)` | Set model-level tags |
| `client.set_model_version_tag(name, version, key, value)` | Set version-level tags |
| `client.get_model_version_by_alias(name, alias)` | Fetch champion version for gating |
| `client.set_registered_model_alias(name, alias, version)` | Promote version to alias |

---

## 3. `register_uc_model()` — Full Implementation Walkthrough

The function follows seven steps:

### Step 1: Guard checks

```python
if not ENABLE_UC_MODEL_REGISTRATION:
    logger.info("UC model registration disabled, skipping")
    return None

run_row = load_run(spark, run_id, catalog, schema)
if not run_row:
    return None

best_model_id = run_row.get("best_model_id")
if not best_model_id:
    return None
```

Exits early if registration is disabled, the run doesn't exist, or no
best model was promoted.

### Step 2: Resolve source run and baseline

```python
iterations_df = load_iterations(spark, run_id, catalog, schema)
best_iter_rows = iterations_df[
    (iterations_df["iteration"] == best_iteration)
    & (iterations_df["eval_scope"] == "full")
]
source_run_id = str(best_iter_rows.iloc[0].get("mlflow_run_id", ""))
```

The `source_run_id` is the MLflow run where the best iteration's evaluation
was logged. This run contains the artifacts and metrics to register.

### Step 3: Ensure UC registered model exists

```python
try:
    client.get_registered_model(uc_model_name)
    client.update_registered_model(uc_model_name, description=model_description)
except Exception:
    client.create_registered_model(uc_model_name, description=model_description)
```

Creates the model on first run; updates the description on subsequent runs
(e.g., if the space name changes).

### Step 4: Register a new version

Delegates to `_register_uc_version()` which:

1. Builds a configuration-aware `ModelSignature` from space dimensions
2. Creates a `_GenieConfigSnapshot` pyfunc wrapper
3. Writes artifacts (space config, UC metadata, benchmark summary, data profile)
4. Calls `mlflow.pyfunc.log_model()` within the source run
5. Calls `mlflow.register_model(model_info.model_uri, uc_model_name)`

### Step 5: Fetch per-judge evaluation scores

```python
tracking_client = mlflow.tracking.MlflowClient()
new_run_data = tracking_client.get_run(source_run_id).data
new_scores = {j: new_run_data.metrics.get(j, 0.0) for j in _EVAL_JUDGES}
```

The eight judge dimensions:

```python
_EVAL_JUDGES = [
    "eval_result_correctness", "eval_syntax_validity",
    "eval_schema_accuracy", "eval_logical_accuracy",
    "eval_semantic_equivalence", "eval_completeness",
    "eval_response_quality", "eval_asset_routing",
]
```

### Step 6: Metric-based gating for `@champion` alias

```python
try:
    existing_mv = client.get_model_version_by_alias(uc_model_name, "champion")
    if existing_mv.run_id:
        existing_run_data = tracking_client.get_run(existing_mv.run_id).data
        existing_scores = {j: existing_run_data.metrics.get(j, 0.0) for j in _EVAL_JUDGES}

        new_rc = new_scores.get("eval_result_correctness", 0.0)
        existing_rc = existing_scores.get("eval_result_correctness", 0.0)
        if new_rc < existing_rc:
            should_promote = False

        new_avg = sum(new_scores.values()) / max(len(new_scores), 1)
        existing_avg = sum(existing_scores.values()) / max(len(existing_scores), 1)
        if new_avg < existing_avg:
            should_promote = False
except Exception:
    # No existing champion → promote by default
    pass

if should_promote:
    client.set_registered_model_alias(uc_model_name, "champion", version)
```

### Gating criteria (both must pass)

| Criterion | Metric | Rule |
|-----------|--------|------|
| Result correctness | `eval_result_correctness` | New ≥ existing |
| Average judge score | Mean of all 8 `_EVAL_JUDGES` | New ≥ existing |

If **either** criterion fails, the version is registered but NOT promoted.
The previous champion retains the `@champion` alias.

### Step 7: Version tags and optional deployment job

Version-level tags are set for traceability:

```python
_version_tags = {
    "genie.optimization_run_id": run_id,
    "genie.iteration": str(best_iteration),
    "genie.accuracy": f"{best_accuracy:.1f}",
    "genie.convergence_reason": convergence_reason,
    "genie.source_run_id": source_run_id,
    "genie.overall_accuracy": f"{best_accuracy:.1f}",
    "genie.overall_score": f"{overall_judge_avg:.2f}",
    # + baseline_accuracy, held_out_accuracy, held_out_count, deploy_target
    # + per-judge scores
}
```

---

## 4. `_register_uc_version()` — Pyfunc Wrapper

UC registration requires a valid MLflow model directory. The codebase uses
a minimal `_GenieConfigSnapshot` pyfunc wrapper:

```python
class _GenieConfigSnapshot(mlflow.pyfunc.PythonModel):
    def predict(self, context, model_input, params=None):
        result = {"status": "config_snapshot_only"}
        if context and context.artifacts:
            cfg_path = context.artifacts.get("space_config", "")
            if cfg_path:
                result = json.loads(Path(cfg_path).read_text())
        return pd.DataFrame([result])
```

The wrapper's `predict()` returns the space config from artifacts. The real
value is in the embedded artifacts, not the prediction output.

### Artifacts registered with each version

| Artifact key | Content |
|-------------|---------|
| `space_config` | Full Genie Space JSON configuration |
| `uc_metadata` | Tables, metric views, functions, instructions, join specs |
| `benchmark_summary` | Iteration number, accuracy, baseline, benchmark rows |
| `data_profile` | Data profile from space config |

---

## 5. Score Comparison Against Last UC Champion

Detailed flow for the gating comparison:

```python
def compare_with_champion(
    client: MlflowClient,
    tracking_client: MlflowClient,
    uc_model_name: str,
    new_scores: dict[str, float],
) -> tuple[bool, dict | None]:
    """Compare new scores against the existing UC champion."""
    try:
        existing_mv = client.get_model_version_by_alias(uc_model_name, "champion")
    except Exception:
        return True, None  # no champion → promote

    if not existing_mv.run_id:
        return True, None  # champion has no linked run → promote

    existing_data = tracking_client.get_run(existing_mv.run_id).data
    existing_scores = {j: existing_data.metrics.get(j, 0.0) for j in _EVAL_JUDGES}

    comparison = {
        j: {"new": new_scores.get(j, 0.0), "existing": existing_scores[j]}
        for j in _EVAL_JUDGES
    }

    should_promote = True

    if new_scores.get("eval_result_correctness", 0.0) < existing_scores.get("eval_result_correctness", 0.0):
        should_promote = False

    new_avg = sum(new_scores.values()) / max(len(new_scores), 1)
    existing_avg = sum(existing_scores.values()) / max(len(existing_scores), 1)
    if new_avg < existing_avg:
        should_promote = False

    return should_promote, comparison
```

---

## 6. Registration Decision Logic (Flowchart)

```
ENABLE_UC_MODEL_REGISTRATION?
  ├── False → return None (skip)
  └── True
       │
       ├── run exists? → No → return None
       ├── best_model_id? → No → return None
       ├── source_run_id? → No → return None
       │
       ├── Ensure UC registered model (create or update)
       ├── _register_uc_version() → new version number
       ├── Fetch new scores from source run
       ├── Set version-level tags
       │
       ├── Existing @champion?
       │   ├── No → promote (set_registered_model_alias)
       │   └── Yes
       │       ├── new result_correctness >= existing? → continue
       │       │   └── No → skip promotion
       │       ├── new avg_judge_score >= existing? → continue
       │       │   └── No → skip promotion
       │       └── Both pass → promote
       │
       └── Return {uc_model_name, version, promoted_to_champion, comparison}
```

---

## 7. Edge Cases

### No existing champion

When `get_model_version_by_alias` raises (no champion exists), the new version
is promoted by default. This handles first-time registration.

### Champion exists but has no `run_id`

If the existing champion version was registered without a linked MLflow run
(e.g., manual registration), score comparison is skipped and the new version
is promoted.

### Metrics missing from source run

If a judge metric is missing from the source run, it defaults to `0.0` via
`metrics.get(j, 0.0)`. This can cause unexpected gating outcomes — ensure
all judge metrics are logged before UC registration.

### Registration succeeds but promotion fails

The version is still registered in UC even if promotion fails. The previous
champion alias remains active. Check version tags to find unprovisioned
versions.

### `ENABLE_UC_MODEL_REGISTRATION = False`

No UC operations are performed. The optimization run still completes normally
with LoggedModel aliases (MLflow-level) but no UC registered model.

---

## 8. DO / DON'T Summary

```python
# DON'T: Use default registry URI for UC registration
client = MlflowClient()  # points to workspace model registry
mlflow.register_model(uri, "main.schema.model")  # fails or goes to wrong backend
```

```python
# DO: Explicitly set UC registry URI
mlflow.set_registry_uri("databricks-uc")
client = MlflowClient(registry_uri="databricks-uc")
mlflow.register_model(uri, "main.schema.model")
```

```python
# DON'T: Promote to champion without checking existing metrics
client.set_registered_model_alias(name, "champion", version)  # may regress
```

```python
# DO: Compare against existing champion first
existing_mv = client.get_model_version_by_alias(name, "champion")
existing_scores = get_scores_from_run(existing_mv.run_id)
if scores_improved(new_scores, existing_scores):
    client.set_registered_model_alias(name, "champion", version)
```

```python
# DON'T: Skip the ENABLE_UC_MODEL_REGISTRATION check
mlflow.register_model(uri, uc_model_name)  # runs even when disabled
```

```python
# DO: Gate on the flag
if not ENABLE_UC_MODEL_REGISTRATION:
    return None
```

```python
# DON'T: Hardcode the UC model name
uc_name = f"{catalog}.{schema}.genie_space_{space_id}"  # diverges from template
```

```python
# DO: Use the template
uc_name = format_mlflow_template(
    UC_REGISTERED_MODEL_TEMPLATE,
    catalog=catalog, schema=schema, space_id=space_id,
)
```
