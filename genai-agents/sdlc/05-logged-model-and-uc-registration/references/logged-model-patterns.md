# LoggedModel Patterns Reference

Complete reference for the LoggedModel lifecycle in Genie Space Optimizer.
Covers initialization, finalization, model versioning, score linking,
champion promotion, and the full lifecycle flow.

Grounded in: `src/genie_space_optimizer/optimization/models.py` and
`src/genie_space_optimizer/common/config.py`.

---

## 1. Model Name Convention

LoggedModel names use `MODEL_NAME_TEMPLATE` from `config.py`:

```python
MODEL_NAME_TEMPLATE = "genie-space-{{ space_id }}"
```

Formatted at runtime:

```python
from genie_space_optimizer.common.config import MODEL_NAME_TEMPLATE, format_mlflow_template

model_name = format_mlflow_template(MODEL_NAME_TEMPLATE, space_id="abc123def")
# Result: "genie-space-abc123def"
```

The `{{ variable }}` syntax is processed by `format_mlflow_template()`, not
Python `str.format()`. Missing keys are left as-is (partial formatting is safe).

---

## 2. `_initialize_logged_model()` Implementation

Creates a LoggedModel across MLflow API variants. The function tries
`mlflow.initialize_logged_model` first (newer MLflow 3.x), then falls back
to `mlflow.create_logged_model` (earlier 3.x builds).

```python
def _initialize_logged_model(
    *,
    name: str,
    source_run_id: str | None,
    params: dict[str, str],
    tags: dict[str, str],
) -> Any:
    """Create a logged model across MLflow API variants."""
    init_fn = getattr(mlflow, "initialize_logged_model", None)
    if callable(init_fn):
        return init_fn(
            name=name,
            source_run_id=source_run_id,
            params=params,
            tags=tags,
            model_type="agent",
        )

    create_fn = getattr(mlflow, "create_logged_model", None)
    if callable(create_fn):
        return create_fn(name=name, params=params, tags=tags)

    raise RuntimeError("No supported MLflow LoggedModel creation API found")
```

### Parameters logged as model params

| Param key | Source | Example |
|-----------|--------|---------|
| `space_id` | Genie Space ID | `"abc123def"` |
| `domain` | Business domain | `"billing"` |
| `iteration` | Optimization iteration number | `"3"` |
| `uc_schema` | UC schema for the space | `"main.genie_optimization"` |
| `uc_columns_count` | Number of UC columns in metadata | `"42"` |
| `uc_tags_count` | Number of UC tags | `"5"` |
| `uc_routines_count` | Number of UC routines | `"3"` |
| `patch_count` | Number of patches applied this iteration | `"2"` |
| `parent_model_id` | Parent model ID (for lineage) | `"m-abc123"` |
| `snapshot_run_id` | MLflow run that owns the artifacts | `"run-xyz"` |
| `space_config_artifact` | Artifact path for full config JSON | `"model_snapshots/iter_3/space_config.json"` |
| `metadata_artifact` | Artifact path for metadata snapshot | `"model_snapshots/iter_3/metadata_snapshot.json"` |
| `model_space_config` | Truncated config (≤250 chars) | `'{"title":"My Space",...}'` |

### Tags set on the LoggedModel

| Tag key | Purpose |
|---------|---------|
| `domain` | Business domain for filtering |
| `space_id` | Link back to the Genie Space |
| `iteration` | Which optimization iteration |
| `uc_schema` | UC schema context |
| `traceability` | Always `"genie_space_optimizer"` |
| `genie.optimization_run_id` | Links to the optimization run (if provided) |

---

## 3. `_finalize_logged_model()` Implementation

Marks the LoggedModel as `READY`. Gracefully no-ops if the API is unavailable:

```python
def _finalize_logged_model(model_id: str) -> None:
    """Finalize logged model if the MLflow API supports it."""
    finalize_fn = getattr(mlflow, "finalize_logged_model", None)
    if not callable(finalize_fn):
        return
    try:
        finalize_fn(model_id=model_id, status="READY")
    except Exception:
        logger.debug(
            "Ignoring finalize_logged_model failure for %s",
            model_id, exc_info=True,
        )
```

### Status values

| Status | Meaning |
|--------|---------|
| `READY` | Model is finalized and available for consumption |
| `IN_PROGRESS` | Model is still being built (default after `initialize`) |
| `FAILED` | Explicit failure marker (not used in this codebase) |

---

## 4. `create_genie_model_version()` Workflow

This is the main entry point for creating iteration snapshots. It:

1. Formats the model name from `MODEL_NAME_TEMPLATE`
2. Optionally sets the experiment
3. Resolves UC metadata (columns, tags, routines)
4. Builds a `metadata_snapshot` dict
5. Verifies an active MLflow run exists
6. Logs JSON artifacts (`space_config.json`, `metadata_snapshot.json`)
7. Calls `_initialize_logged_model()` with params and tags
8. Calls `_finalize_logged_model()` to mark READY
9. Returns the `model_id` string

### Caller requirements

- **Must be inside `mlflow.start_run()`** — the function raises `RuntimeError` otherwise.
- Artifacts are logged to the caller's run via `_log_dict_artifact()`.

### Return value

- On success: `model_id` string (e.g., `"m-abc123def456"`)
- On failure: empty string `""` (exception is logged but not re-raised)

### Artifact layout

```
<run_artifacts>/
  model_snapshots/
    iter_0/
      space_config.json      # Full Genie Space configuration
      metadata_snapshot.json  # Config + UC metadata + patch set
    iter_1/
      space_config.json
      metadata_snapshot.json
    ...
```

---

## 5. `link_eval_scores_to_model()` for Metric Attachment

Links evaluation metrics to both the MLflow run and the LoggedModel:

```python
def link_eval_scores_to_model(
    model_id: str,
    scores: dict[str, float],
    eval_run_id: str = "",
) -> None:
```

### Dual metric logging

1. **Run-level metrics** — logged via `MlflowClient().log_metric()` (if
   `eval_run_id` provided) or `mlflow.log_metric()` (active run fallback).
   Prefixed with `eval_`.
2. **Model-level metrics** — logged via `mlflow.log_metrics(metrics, model_id=model_id)`
   when the MLflow version supports the `model_id` parameter.

### Fallback chain

```
1. Try mlflow.set_active_model(model_id) + mlflow.log_metrics(model_id=model_id)
2. If TypeError/AttributeError → silently skip model-level metrics
3. If other exception → log debug warning, fall through to run-level only
4. Run-level metrics are always logged regardless of model-level outcome
```

### Metric names

Scores dict keys are prefixed with `eval_` before logging:

```python
scores = {"result_correctness": 0.95, "syntax_validity": 1.0}
# Logged as: eval_result_correctness=0.95, eval_syntax_validity=1.0
```

---

## 6. `promote_best_model()` for Champion Selection

Selects the best iteration and sets the MLflow LoggedModel `champion` alias:

```python
def promote_best_model(
    spark: SparkSession,
    run_id: str,
    catalog: str,
    schema: str,
) -> str | None:
```

### Selection algorithm

1. Load all iterations from Delta for the given `run_id`
2. Filter to `eval_scope == "full"` rows (fall back to all rows if none)
3. Pick the row with maximum `overall_accuracy`
4. Extract `model_id`, `iteration`, `accuracy` from that row

### Alias setting

```python
alias_fn = getattr(mlflow, "set_logged_model_alias", None)
if callable(alias_fn):
    alias_fn(model_id=best_model_id, alias="champion")
```

The `getattr` guard handles MLflow versions that lack `set_logged_model_alias`.

### Run status update

After promotion, updates the optimization run record in Delta:

```python
update_run_status(
    spark, run_id, catalog, schema,
    best_iteration=best_iteration,
    best_accuracy=best_accuracy,
    best_model_id=best_model_id,
)
```

### Return value

- On success: `best_model_id` string
- On failure: `None` (with appropriate logging)

---

## 7. `mlflow.set_logged_model_alias()` Usage

Sets a named alias on a LoggedModel for discovery and rollback:

```python
mlflow.set_logged_model_alias(
    model_id="m-abc123def456",
    alias="champion",
)
```

### Supported aliases in this codebase

| Alias | Set by | Purpose |
|-------|--------|---------|
| `champion` | `promote_best_model()` | Best-performing iteration within an optimization run |

### Alias lookup

```python
model = mlflow.get_logged_model_by_alias(
    name="genie-space-abc123",
    alias="champion",
)
model_id = model.model_id
```

---

## 8. Complete Lifecycle Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    Full LoggedModel Lifecycle                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  1. mlflow.start_run()                                           │
│     └── create_genie_model_version()                             │
│         ├── format model name (MODEL_NAME_TEMPLATE)              │
│         ├── resolve UC metadata                                   │
│         ├── log artifacts (space_config, metadata_snapshot)       │
│         ├── _initialize_logged_model()                           │
│         │   └── mlflow.initialize_logged_model(model_type="agent")│
│         └── _finalize_logged_model()                             │
│             └── mlflow.finalize_logged_model(status="READY")     │
│                                                                   │
│  2. Run evaluation (Skill 09)                                    │
│     └── Produces scores dict                                     │
│                                                                   │
│  3. link_eval_scores_to_model(model_id, scores)                  │
│     ├── Run-level: MlflowClient().log_metric(run_id, ...)       │
│     └── Model-level: mlflow.log_metrics(model_id=model_id)      │
│                                                                   │
│  4. (After all iterations complete)                               │
│     promote_best_model(spark, run_id, catalog, schema)           │
│     ├── Select max overall_accuracy from Delta                    │
│     ├── mlflow.set_logged_model_alias(model_id, "champion")     │
│     └── update_run_status(best_model_id=...)                     │
│                                                                   │
│  5. register_uc_model() (Skill 10 — UC registration)            │
│     └── See uc-gating.md                                         │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 9. Rollback via LoggedModel

`rollback_to_model()` restores a Genie Space configuration from a LoggedModel:

```python
def rollback_to_model(w: WorkspaceClient, model_id: str) -> dict | None:
```

1. Calls `mlflow.get_logged_model(model_id=model_id)`
2. Reads `model_space_config` from model params
3. Deserializes JSON and applies via `patch_space_config(w, space_id, config)`

### Limitations

- `model_space_config` is truncated to 250 characters by `_safe_serialize()`.
  For full config, use the `space_config.json` artifact logged alongside the model.
- Rollback requires an active `WorkspaceClient` with Genie API permissions.

---

## 10. Helper Functions

### `_safe_serialize(obj) -> str`

JSON-serializes an object and truncates to 250 characters for MLflow params
(which have a size limit):

```python
def _safe_serialize(obj: Any) -> str:
    try:
        s = json.dumps(obj, default=str)
        return s[:250] if len(s) > 250 else s
    except Exception:
        return str(obj)[:250]
```

### `_log_dict_artifact(payload, artifact_file)`

Logs a dict as a JSON artifact, with fallback for MLflow versions that lack
`mlflow.log_dict()`:

```python
def _log_dict_artifact(payload: dict[str, Any], artifact_file: str) -> None:
    log_dict_fn = getattr(mlflow, "log_dict", None)
    if callable(log_dict_fn):
        log_dict_fn(payload, artifact_file)
        return

    tmp_dir = Path(tempfile.mkdtemp(prefix="genie-opt-"))
    tmp_file = tmp_dir / Path(artifact_file).name
    tmp_file.write_text(json.dumps(payload, default=str, indent=2))
    mlflow.log_artifact(str(tmp_file), artifact_path=str(Path(artifact_file).parent))
```

### `_resolve_uc_metadata(config, uc_columns, uc_tags, uc_routines)`

Resolves UC metadata from explicit arguments first, falling back to the
`_prefetched_uc_metadata` key in the space config dict:

```python
prefetched = config.get("_prefetched_uc_metadata", {})
resolved_columns = uc_columns if isinstance(uc_columns, list) else prefetched.get("uc_columns", [])
resolved_tags = uc_tags if isinstance(uc_tags, list) else prefetched.get("uc_tags", [])
resolved_routines = uc_routines if isinstance(uc_routines, list) else prefetched.get("uc_routines", [])
```

---

## 11. DO / DON'T Summary

```python
# DON'T: Call create_genie_model_version outside an active run
model_id = create_genie_model_version(w, space_id, config, iteration=1, ...)
# RuntimeError: requires an active MLflow run
```

```python
# DO: Wrap in mlflow.start_run()
with mlflow.start_run():
    model_id = create_genie_model_version(w, space_id, config, iteration=1, ...)
```

```python
# DON'T: Assume set_logged_model_alias always exists
mlflow.set_logged_model_alias(model_id=mid, alias="champion")
# AttributeError on older MLflow builds
```

```python
# DO: Guard with getattr (as promote_best_model does)
alias_fn = getattr(mlflow, "set_logged_model_alias", None)
if callable(alias_fn):
    alias_fn(model_id=mid, alias="champion")
```

```python
# DON'T: Link scores without the eval_ prefix
mlflow.log_metrics({"result_correctness": 0.95}, model_id=model_id)
```

```python
# DO: Use link_eval_scores_to_model which handles prefixing and fallbacks
link_eval_scores_to_model(model_id, {"result_correctness": 0.95}, eval_run_id=run_id)
```
