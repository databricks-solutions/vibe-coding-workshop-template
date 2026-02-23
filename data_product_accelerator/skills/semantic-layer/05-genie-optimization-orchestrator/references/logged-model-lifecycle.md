# LoggedModel Lifecycle Reference

## Overview

Each Genie Space configuration snapshot is stored as an MLflow **LoggedModel**, creating a versioned chain that enables:
- **Config tracking** across optimization iterations
- **Parent lineage** linking each iteration to its predecessor
- **Evaluation linkage** via `mlflow.genai.evaluate(model_id=...)`
- **Promotion** of the best-performing configuration
- **Rollback** to any previous configuration when regressions occur

## Data Flow

```
Orchestrator                  Evaluator Job                MLflow
    |                              |                         |
    |--create_genie_model_version->|                         |
    |  (returns model_id)          |                         |
    |                              |                         |
    |--trigger_evaluation_job----->|                         |
    |  (params: model_id=...)      |                         |
    |                              |--set_active_model------>|
    |                              |  (model_id)             |
    |                              |                         |
    |                              |--genai.evaluate-------->|
    |                              |  (model_id=...)         |
    |                              |  links eval run to model|
    |                              |                         |
    |<-------notebook.exit---------|                         |
    |                              |                         |
    |--promote_best_model--------->|                         |
    |  (tags best model)           |                         |
    |                              |                         |
    |--rollback_to_model---------->|                         |
    |  (restores config artifact)  |                         |
```

## Implementation in `orchestrator.py`

### `create_genie_model_version()`

Creates a LoggedModel for this iteration's Genie Space configuration using `create_external_model()` inside `mlflow.start_run()`.
Called BEFORE evaluation so `mlflow.genai.evaluate(model_id=...)` links correctly.

```python
def create_genie_model_version(space_id, config, iteration, domain,
                                patch_set=None, parent_model_id=None,
                                prompt_versions=None, uc_schema=None) -> str:
    # Fetches UC metadata (columns, tags, routines) via SQL Statement API
    config_hash = hashlib.sha256(...).hexdigest()[:12]
    model_name = f"genie-{domain}-iter{iteration}-{config_hash}"

    with mlflow.start_run(run_name=f"create_model_iter{iteration}_{config_hash}") as creation_run:
        logged_model = mlflow.create_external_model(
            name=model_name,
            source_run_id=creation_run.info.run_id,
            params=model_params,
            tags={"domain": domain, "space_id": space_id, ...},
            model_type="genie-space",
        )
        # Logs model_state/ artifacts (genie_config, UC columns/tags/routines, metadata diff)
        # Logs patches/ artifacts (patch_set.json, patch_summary.json) if patch_set
    return logged_model.model_id
```

### `promote_best_model()`

Tags the best-performing LoggedModel after the optimization loop converges.

```python
def promote_best_model(session):
    best_model_id = session["iterations"][best_iter - 1].get("model_id")
    mlflow.set_logged_model_tags(model_id=best_model_id, tags={
        "promoted": "true",
        "promotion_reason": session.get("convergence_reason"),
        "best_accuracy": str(session.get("best_overall_accuracy")),
    })
```

### `rollback_to_model()`

Restores Genie Space config from a LoggedModel's creation run artifacts when P0 gate fails.
Downloads `model_state/genie_config.json` via `source_run_id`. Guards against missing `source_run_id`.

```python
def rollback_to_model(model_id, space_id):
    model = mlflow.get_logged_model(model_id=model_id)
    if not model.source_run_id:
        return None  # WARNING: cannot download artifacts
    artifact_dir = mlflow.artifacts.download_artifacts(
        run_id=model.source_run_id, artifact_path="model_state"
    )
    # Reads model_state/genie_config.json and returns config dict
    return config
```

## Orchestrator Loop Integration

The `_snapshot_and_get_model_id()` closure wraps `create_genie_model_version()`:

```python
def _snapshot_and_get_model_id(iter_num, patch_set=None, prompt_versions=None):
    config = _fetch_space_config(space_id)
    if config:
        mid = create_genie_model_version(
            space_id, config, iter_num, domain,
            patch_set=patch_set,
            parent_model_id=_prev_model_id,
            prompt_versions=prompt_versions,
            uc_schema=uc_schema,
        )
        _prev_model_id = mid
        return mid
    return None  # WARNING: model tracking disabled for this iteration
```

Called at:
- **Baseline**: `model_id = _snapshot_fn(1)`
- **Per-lever**: `model_id = _snapshot_fn(iter_num, patch_set=proposals)`

## Evaluator Integration

The evaluator receives `model_id` as a job parameter and uses it at:
- `mlflow.set_active_model(model_id=model_id)` — activates model context
- `mlflow.genai.evaluate(model_id=model_id)` — links evaluation run to model

If `model_id` is None (creation failed), the evaluator logs a WARNING and continues
without config version tracking.

## Common Pitfalls

| Pitfall | Consequence | Prevention |
|---------|-------------|------------|
| `_fetch_space_config()` returns empty dict | `model_id` is None, tracking disabled | Verify `?include_serialized_space=true` |
| Exception in `create_genie_model_version()` | Silently caught, `model_id` is None | Check for WARNING in orchestrator output |
| Job YAML `model_id: ""` not overridden | Evaluator skips `set_active_model()` | Orchestrator passes model_id in params_str |
| `promote_best_model()` called with no iterations | Prints warning, no-op | Only call after successful iterations |
| Using `set_active_model()` for creation | No `source_run_id`, artifacts silently dropped | Use `create_external_model()` inside `start_run()` |
