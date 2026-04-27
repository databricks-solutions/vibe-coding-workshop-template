# Deployment Job DAG Patterns

Complete reference for the multi-task job DAG used in the Genie Space Optimizer,
grounded in `databricks.yml` and the `run_*.py` task notebooks.

---

## 1. Complete Job Task Structure

The optimization pipeline is a 6-task linear DAG:

```text
preflight → baseline_eval → enrichment → lever_loop → finalize → deploy
```

### Task responsibilities

| Task | Notebook | Duration | Key Output |
|------|----------|----------|------------|
| **preflight** | `run_preflight.py` | 2–10 min | Validated params, Delta tables, benchmarks, experiment setup |
| **baseline_eval** | `run_baseline.py` | 5–20 min | 9-judge scores, accuracy, thresholds_met, model_id |
| **enrichment** | `run_enrichment.py` | 5–15 min | Proactive enrichment patches (descriptions, joins, metadata) |
| **lever_loop** | `run_lever_loop.py` | 15–90 min | Optimized config, best scores, iteration history |
| **finalize** | `run_finalize.py` | 5–15 min | UC model registration, champion promotion, repeatability check |
| **deploy** | `run_deploy.py` | 2–10 min | Endpoint deployment or bundle deploy trigger |

### Dependency chain

Each task declares `depends_on` pointing to its predecessor:

```yaml
tasks:
  - task_key: preflight
    # No depends_on — this is the root task

  - task_key: baseline_eval
    depends_on:
      - task_key: preflight

  - task_key: enrichment
    depends_on:
      - task_key: baseline_eval

  - task_key: lever_loop
    depends_on:
      - task_key: enrichment

  - task_key: finalize
    depends_on:
      - task_key: lever_loop

  - task_key: deploy
    depends_on:
      - task_key: finalize
```

If any task fails, all downstream tasks are skipped. The job run is marked as
failed with the first failing task's error.

---

## 2. taskValues Passing Patterns

Job tasks run in separate processes (potentially on different clusters). They
communicate via `dbutils.jobs.taskValues` — a key-value store scoped to the
job run.

### Setting values (producer task)

```python
# At the end of preflight (after all work succeeds):
dbutils.jobs.taskValues.set(key="run_id", value=run_id)
dbutils.jobs.taskValues.set(key="space_id", value=space_id)
dbutils.jobs.taskValues.set(key="experiment_name", value=exp_name)
dbutils.jobs.taskValues.set(key="experiment_id", value=experiment_id)
dbutils.jobs.taskValues.set(key="benchmark_count", value=len(benchmarks))
dbutils.jobs.taskValues.set(key="levers", value=json.dumps(levers))
```

### Getting values (consumer task)

```python
# In baseline_eval, reading from preflight:
run_id = dbutils.jobs.taskValues.get(taskKey="preflight", key="run_id")
space_id = dbutils.jobs.taskValues.get(taskKey="preflight", key="space_id")
exp_name = dbutils.jobs.taskValues.get(taskKey="preflight", key="experiment_name")
```

### Complete taskValues map

**Preflight publishes → all downstream tasks:**

| Key | Type | Consumers |
|-----|------|-----------|
| `run_id` | `str` | All tasks |
| `space_id` | `str` | All tasks |
| `domain` | `str` | All tasks |
| `catalog` | `str` | All tasks |
| `schema` | `str` | All tasks |
| `experiment_name` | `str` | baseline, enrichment, lever_loop, finalize |
| `experiment_id` | `str` | baseline, lever_loop, finalize |
| `benchmark_count` | `int` | baseline |
| `max_iterations` | `int` | lever_loop |
| `levers` | `str` (JSON array) | lever_loop |
| `apply_mode` | `str` | lever_loop |
| `deploy_target` | `str` | deploy |
| `warehouse_id` | `str` | baseline, enrichment, lever_loop |
| `triggered_by` | `str` | lever_loop |
| `human_corrections` | `str` (JSON array) | lever_loop |
| `max_benchmark_count` | `int` | baseline, lever_loop |

**Baseline publishes → enrichment, lever_loop, finalize:**

| Key | Type | Consumers |
|-----|------|-----------|
| `scores` | `str` (JSON dict) | enrichment, lever_loop, finalize |
| `overall_accuracy` | `float` | lever_loop, finalize |
| `thresholds_met` | `bool` | enrichment, lever_loop |
| `model_id` | `str` | lever_loop, finalize |
| `mlflow_run_id` | `str` | finalize |
| `max_benchmark_count` | `int` | lever_loop |

**Enrichment publishes → lever_loop:**

| Key | Type | Consumers |
|-----|------|-----------|
| `enrichment_model_id` | `str` | lever_loop |
| `enrichment_skipped` | `bool` | lever_loop |

**Lever loop publishes → finalize, deploy:**

| Key | Type | Consumers |
|-----|------|-----------|
| `scores` | `str` (JSON dict) | finalize |
| `accuracy` | `float` | finalize |
| `model_id` | `str` | finalize, deploy |
| `iteration_counter` | `int` | finalize |
| `best_iteration` | `int` | finalize |
| `skipped` | `bool` | finalize |
| `debug_info` | `str` (JSON dict) | finalize |

**Finalize publishes → deploy:**

| Key | Type | Consumers |
|-----|------|-----------|
| `champion_model_name` | `str` | deploy |
| `champion_model_version` | `str` | deploy |
| `champion_alias` | `str` | deploy |
| `repeatability_passed` | `bool` | deploy |
| `held_out_passed` | `bool` | deploy |

### Handling missing keys

`taskValues.get()` returns `None` when the key is absent. Always guard:

```python
# DON'T — crashes with TypeError on None
max_iters = int(dbutils.jobs.taskValues.get(taskKey="preflight", key="max_iterations"))

# DO — provide a default
max_iters = int(
    dbutils.jobs.taskValues.get(
        taskKey="preflight", key="max_iterations", default="5"
    )
)
```

### Serialization rules

| Type | Set | Get |
|------|-----|-----|
| `str`, `int`, `float`, `bool` | Direct | Direct |
| `list`, `dict` | `json.dumps(value)` | `json.loads(raw)` |
| `None` | Avoid — use empty string | Check for `None` or `""` |

---

## 3. Job Parameters Specification

The job declares parameters at the top level, passed to the first task via
`base_parameters` with `{{job.parameters.name}}` substitution:

```yaml
parameters:
  - name: run_id
    default: ""
  - name: space_id
    default: ""
  - name: domain
    default: "default"
  - name: catalog
    default: ""
  - name: schema
    default: ""
  - name: apply_mode
    default: "genie_config"
  - name: levers
    default: "[1,2,3,4,5,6]"
  - name: max_iterations
    default: "5"
  - name: triggered_by
    default: ""
  - name: experiment_name
    default: ""
  - name: deploy_target
    default: ""
  - name: warehouse_id
    default: ""
```

Only the **preflight** task receives `base_parameters`:

```yaml
tasks:
  - task_key: preflight
    notebook_task:
      notebook_path: ./src/genie_space_optimizer/jobs/run_preflight.py
      base_parameters:
        run_id: "{{job.parameters.run_id}}"
        space_id: "{{job.parameters.space_id}}"
        catalog: "{{job.parameters.catalog}}"
        # ... all parameters forwarded
```

Downstream tasks read their inputs exclusively from `taskValues` published
by upstream tasks — they do **not** receive job parameters directly.

---

## 4. MODEL_VERSION_CREATED Trigger

For CI/CD pipelines that should fire when a new model version is registered:

```yaml
resources:
  jobs:
    auto_deploy_job:
      name: "auto-deploy-on-model-registration"
      trigger:
        type: MODEL_VERSION_CREATED
        model_name: "main.genie_optimization.genie_optimizer_agent"
        stages: ["None"]
      tasks:
        - task_key: evaluate
          notebook_task:
            notebook_path: ./jobs/evaluate_model.py
        - task_key: gate_check
          depends_on:
            - task_key: evaluate
          notebook_task:
            notebook_path: ./jobs/gate_check.py
        - task_key: deploy_to_serving
          depends_on:
            - task_key: gate_check
          notebook_task:
            notebook_path: ./jobs/deploy_to_serving.py
```

### Key considerations

| Aspect | Guidance |
|--------|----------|
| `model_name` | Must match the **fully qualified** UC model name |
| `stages` | `["None"]` triggers on any new version; use `["Staging"]` for registry stage transitions |
| Idempotency | The triggered job must handle re-runs gracefully (same version registered twice) |
| Scope | One trigger per registered model; if you have multiple models, create multiple jobs |

The Genie Space Optimizer does **not** use this trigger by default — the app
backend triggers optimization jobs directly via the Jobs API. Add the trigger
only where your org requires version-based CI/CD.

---

## 5. Error Handling and Retry Patterns

### Per-task retry configuration

```yaml
tasks:
  - task_key: baseline_eval
    depends_on:
      - task_key: preflight
    notebook_task:
      notebook_path: ./src/genie_space_optimizer/jobs/run_baseline.py
    timeout_seconds: 14400   # 4 hours max
    max_retries: 0           # No automatic retries at the job level
```

The Genie Space Optimizer uses `max_retries: 0` for all tasks because:

1. **Evaluation has built-in retries** — `_run_evaluate_with_retries()` handles
   transient MLflow/gRPC failures internally (up to 4 attempts).
2. **State mutations** — tasks write to Delta and Genie API; blind retries risk
   duplicate writes or inconsistent state.
3. **Meaningful failures** — if a task fails after exhausting internal retries,
   the root cause needs investigation, not blind re-execution.

### When to enable job-level retries

| Task type | Retry? | Reasoning |
|-----------|--------|-----------|
| Read-only evaluation | Maybe (1–2) | Safe if idempotent |
| State-writing optimization | No | Risk of duplicate patches |
| Deploy/promotion | No | Risk of deploying a bad version twice |
| Preflight (validation) | No | Failures indicate config issues |

### Application-level retry pattern

The app backend (`job_launcher.py`) handles retry logic at a higher level:

1. User clicks "retry" in the UI
2. Backend creates a **new** job run with the same parameters
3. Preflight validates state tables and resumes from the correct point
4. Previous failed run's state is preserved for debugging

### Structured error propagation

Each task follows a consistent error pattern:

```python
try:
    _banner("Step Name")
    result = do_work(...)
    _log("Step complete", key_metric=result["metric"])
except Exception as exc:
    _banner("Step FAILED")
    _log(
        "Failure details",
        error_type=type(exc).__name__,
        error_message=str(exc),
        traceback=traceback.format_exc(),
    )
    raise  # Let the job framework handle the failure
```

---

## 6. Complete databricks.yml Job Section

The full job definition from `databricks.yml`:

```yaml
resources:
  jobs:
    genie-space-optimizer-runner:
      name: "genie-space-optimizer-job"
      description: >-
        Persistent DAG optimization runner managed by Genie Space Optimizer app
        (preflight -> baseline_eval -> enrichment -> lever_loop -> finalize -> deploy).
        SP executes with granted privileges on user schemas.
      max_concurrent_runs: 20
      queue:
        enabled: true
      tags:
        app: "genie-space-optimizer"
        managed-by: "databricks-bundle"
        pattern: "persistent-dag"

      parameters:
        - name: run_id
          default: ""
        - name: space_id
          default: ""
        - name: domain
          default: "default"
        - name: catalog
          default: ""
        - name: schema
          default: ""
        - name: apply_mode
          default: "genie_config"
        - name: levers
          default: "[1,2,3,4,5,6]"
        - name: max_iterations
          default: "5"
        - name: triggered_by
          default: ""
        - name: experiment_name
          default: ""
        - name: deploy_target
          default: ""
        - name: warehouse_id
          default: ""

      tasks:
        - task_key: preflight
          notebook_task:
            notebook_path: ./src/genie_space_optimizer/jobs/run_preflight.py
            base_parameters:
              run_id: "{{job.parameters.run_id}}"
              space_id: "{{job.parameters.space_id}}"
              domain: "{{job.parameters.domain}}"
              catalog: "{{job.parameters.catalog}}"
              schema: "{{job.parameters.schema}}"
              apply_mode: "{{job.parameters.apply_mode}}"
              levers: "{{job.parameters.levers}}"
              max_iterations: "{{job.parameters.max_iterations}}"
              experiment_name: "{{job.parameters.experiment_name}}"
              deploy_target: "{{job.parameters.deploy_target}}"
              warehouse_id: "{{job.parameters.warehouse_id}}"
          environment_key: default
          timeout_seconds: 14400
          max_retries: 0

        - task_key: baseline_eval
          depends_on:
            - task_key: preflight
          notebook_task:
            notebook_path: ./src/genie_space_optimizer/jobs/run_baseline.py
          environment_key: default
          timeout_seconds: 14400
          max_retries: 0

        - task_key: enrichment
          depends_on:
            - task_key: baseline_eval
          notebook_task:
            notebook_path: ./src/genie_space_optimizer/jobs/run_enrichment.py
          environment_key: default
          timeout_seconds: 14400
          max_retries: 0

        - task_key: lever_loop
          depends_on:
            - task_key: enrichment
          notebook_task:
            notebook_path: ./src/genie_space_optimizer/jobs/run_lever_loop.py
          environment_key: default
          timeout_seconds: 14400
          max_retries: 0

        - task_key: finalize
          depends_on:
            - task_key: lever_loop
          notebook_task:
            notebook_path: ./src/genie_space_optimizer/jobs/run_finalize.py
          environment_key: default
          timeout_seconds: 14400
          max_retries: 0

        - task_key: deploy
          depends_on:
            - task_key: finalize
          notebook_task:
            notebook_path: ./src/genie_space_optimizer/jobs/run_deploy.py
          environment_key: default
          timeout_seconds: 14400
          max_retries: 0

      environments:
        - environment_key: default
          spec:
            environment_version: "4"
            dependencies:
              - .build/genie_space_optimizer-0.0.0-py3-none-any.whl
              - "mlflow[databricks]>=3.10.1"
              - "databricks-sdk>=0.40.0"
              - "openai>=1.17"
              - "litellm"

      permissions:
        - group_name: "users"
          level: "CAN_VIEW"
```

### Key design decisions

| Decision | Rationale |
|----------|-----------|
| `max_concurrent_runs: 20` | Multiple spaces can be optimized simultaneously |
| `queue.enabled: true` | Excess runs queue rather than fail |
| `environment_version: "4"` | Serverless compute — no cluster management |
| `timeout_seconds: 14400` | 4-hour max per task (generous for large benchmark sets) |
| `max_retries: 0` | Evaluation has internal retries; task-level retries risk state corruption |
| Only preflight gets `base_parameters` | Downstream tasks read from taskValues exclusively |

---

## 7. Environment and Dependencies

The job uses a **serverless environment** with pinned dependencies:

```yaml
environments:
  - environment_key: default
    spec:
      environment_version: "4"
      dependencies:
        - .build/genie_space_optimizer-0.0.0-py3-none-any.whl
        - "mlflow[databricks]>=3.10.1"
        - "databricks-sdk>=0.40.0"
        - "openai>=1.17"
        - "litellm"
```

The `.whl` file is built from the project source during `databricks bundle deploy`
(see the `artifacts` section in `databricks.yml`). All job code runs from this
wheel, ensuring consistency across tasks.

---

## Related Skills

- **Skill 00 — MLflow GenAI Foundation:** Dependency versions and autolog setup
- **Skill 09 — Evaluation:** The 9-judge scorer system used in baseline and lever loop
- **Skill 10 — UC Model Management:** How finalize registers models for deploy
