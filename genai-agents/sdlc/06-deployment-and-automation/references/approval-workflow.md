# Deployment Approval Workflow

Reference for the evaluate-then-promote workflow, threshold gates, manual and
automated approval patterns, and rollback procedures.

---

## 1. Evaluation-Then-Promote Workflow

The deployment pipeline never promotes a model version without evaluation.
The canonical flow:

```text
Register model version
       │
       ▼
  ┌─────────┐
  │ Evaluate │  Run full benchmark suite (9 judges)
  └────┬─────┘
       │
       ▼
  ┌─────────┐
  │  Gate    │  Check all thresholds
  └────┬─────┘
       │
  Pass? ──── No ──→ STOP (log reason, notify)
       │
      Yes
       │
       ▼
  ┌──────────┐
  │ Approve? │  Manual (regulated) or automatic
  └────┬─────┘
       │
       ▼
  ┌──────────┐
  │ Promote  │  Update UC alias (champion → production)
  └────┬─────┘
       │
       ▼
  ┌──────────┐
  │ Deploy   │  Update serving endpoint to new version
  └──────────┘
```

### Key principle

> A model version that has not been evaluated against the current benchmark
> dataset MUST NOT be promoted to a production alias or deployed to a serving
> endpoint.

---

## 2. Threshold Gates from Skill 09

The evaluation produces per-judge scores. Each judge has a threshold defined
in `src/genie_space_optimizer/common/config.py`:

```python
DEFAULT_THRESHOLDS = {
    "syntax_validity": 98.0,
    "schema_accuracy": 95.0,
    "logical_accuracy": 90.0,
    "semantic_equivalence": 90.0,
    "completeness": 90.0,
    "response_quality": 0.0,
    "result_correctness": 85.0,
    "asset_routing": 95.0,
}
```

### Gate check logic

```python
def all_thresholds_met(scores: dict, thresholds: dict) -> bool:
    """Check if every judge score meets or exceeds its threshold."""
    for judge, threshold in thresholds.items():
        score = scores.get(judge, 0.0)
        if score < threshold:
            return False
    return True
```

### 3-Gate pattern (lever loop internal)

During optimization, each iteration's patches are validated through three
sequential gates before acceptance:

| Gate | Scope | Pass Condition |
|------|-------|---------------|
| **Slice** | Benchmarks touching patched objects | No regression vs best scores |
| **P0** | Top 3 critical questions | Zero P0 failures |
| **Full** | All benchmarks | No regression vs best scores |

For deployment promotion (post-optimization), the relevant gate is whether
the **final** scores meet `DEFAULT_THRESHOLDS`.

---

## 3. Automated Approval

When all gates pass and the environment does not require manual sign-off,
promotion happens automatically in the finalize task:

```python
# In finalize task (simplified)
scores = json.loads(dbutils.jobs.taskValues.get(taskKey="lever_loop", key="scores"))
thresholds_met = all_thresholds_met(scores, DEFAULT_THRESHOLDS)

if thresholds_met:
    # Promote to champion alias
    client = MlflowClient()
    client.set_registered_model_alias(
        name=model_name,
        alias="champion",
        version=model_version,
    )
    log("Auto-promoted", model=model_name, version=model_version, alias="champion")
else:
    log("Promotion blocked", reason="thresholds_not_met", scores=scores)
```

### Repeatability gate

Before promotion, the finalize task also runs a **repeatability check** —
re-evaluating the same benchmarks to ensure scores are stable (not a
one-time fluke):

```python
REPEATABILITY_TARGET = 90.0  # from config.py

if repeatability_score < REPEATABILITY_TARGET:
    log("Promotion blocked", reason="repeatability_below_target",
        score=repeatability_score, target=REPEATABILITY_TARGET)
```

### Held-out generalization gate

A subset of benchmarks (15%, configured via `HELD_OUT_RATIO`) is held out
during the lever loop. Finalize evaluates these unseen questions to check
that optimization didn't overfit:

```python
if held_out_accuracy < baseline_accuracy - REGRESSION_THRESHOLD:
    log("Promotion blocked", reason="held_out_regression",
        held_out=held_out_accuracy, baseline=baseline_accuracy)
```

---

## 4. Manual Approval Integration

For regulated environments or high-stakes deployments, insert a manual
approval step between gate check and promotion.

### Approach 1: Separate approval job

```yaml
resources:
  jobs:
    evaluate_job:
      tasks:
        - task_key: evaluate
          notebook_task:
            notebook_path: ./jobs/evaluate_model.py
        - task_key: gate_check
          depends_on:
            - task_key: evaluate
          notebook_task:
            notebook_path: ./jobs/gate_check.py
        # Job ends here — no auto-deploy

    deploy_job:
      # Triggered manually (or by webhook) after human approval
      tasks:
        - task_key: deploy
          notebook_task:
            notebook_path: ./jobs/deploy_to_serving.py
```

A human reviews the evaluation results, then manually triggers `deploy_job`.

### Approach 2: Webhook + ticket system

```python
# In gate_check task, after evaluation passes:
if thresholds_met:
    # Create approval ticket
    create_jira_ticket(
        summary=f"Model {model_name} v{version} ready for promotion",
        description=f"Scores: {json.dumps(scores, indent=2)}",
        assignee=approval_team,
    )
    # The deploy task waits or is triggered by ticket resolution
```

### Approach 3: MLflow model aliases as stages

Use intermediate aliases to signal readiness:

```python
# After evaluation passes
client.set_registered_model_alias(name=model_name, alias="candidate", version=version)

# After manual approval (separate process)
client.set_registered_model_alias(name=model_name, alias="champion", version=version)
client.delete_registered_model_alias(name=model_name, alias="candidate")
```

### Decision matrix

| Environment | Approval | Pattern |
|------------|----------|---------|
| Development | None | Auto-promote on all gates pass |
| Staging | Light | Auto-promote + Slack notification |
| Production (low-risk) | Auto with notification | Auto-promote + post-deploy monitoring |
| Production (regulated) | Manual required | Separate deploy job triggered after approval |

---

## 5. Rollback Procedures

### Serving endpoint rollback

If a newly deployed model version causes issues in production:

```python
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()

# Roll back to previous version
w.serving_endpoints.update_config(
    name="genie-optimizer-endpoint",
    served_entities=[{
        "entity_name": "main.genie_optimization.optimizer_agent",
        "entity_version": str(previous_version),
        "workload_size": "Small",
        "scale_to_zero_enabled": True,
    }],
)
```

### UC alias rollback

```python
from mlflow import MlflowClient

client = MlflowClient()

# Point champion alias back to previous version
client.set_registered_model_alias(
    name="main.genie_optimization.optimizer_agent",
    alias="champion",
    version=str(previous_version),
)
```

### Genie Space config rollback

The lever loop stores configuration snapshots before each iteration. If
optimization degraded the space:

```python
# The harness captures a snapshot before patches
metadata_snapshot = fetch_space_config(w, space_id)

# On gate failure, rollback restores the snapshot
rollback(apply_log, w, space_id, metadata_snapshot)
```

For post-deployment rollback, the finalize task's `config_snapshot` in the
`genie_opt_runs` Delta table contains the pre-optimization configuration.

### Rollback decision tree

```text
Issue detected post-deploy
       │
       ├── Latency spike / errors in serving?
       │   └── Roll back serving endpoint version
       │
       ├── Quality regression detected by monitoring?
       │   └── Roll back UC alias + serving endpoint
       │
       ├── Genie Space giving wrong answers?
       │   └── Restore config snapshot from Delta
       │
       └── All of the above?
           └── Full rollback: config snapshot + UC alias + serving version
```

---

## 6. Monitoring Post-Deployment

After promotion and deployment, monitor for regressions:

| Signal | Source | Action |
|--------|--------|--------|
| Serving endpoint errors | Inference table / endpoint metrics | Roll back if error rate spikes |
| User feedback (thumbs down) | App UI / Genie feedback | Investigate; may trigger re-optimization |
| Automated eval on new data | Scheduled evaluation job | Compare against thresholds |
| Latency degradation | Endpoint metrics | Check model size, concurrency settings |

### Automated regression detection

Schedule a job that periodically re-evaluates the deployed model against
the benchmark dataset:

```yaml
resources:
  jobs:
    scheduled_eval:
      name: "genie-optimizer-regression-check"
      schedule:
        quartz_cron_expression: "0 0 6 * * ?"  # Daily at 6 AM
        timezone_id: "UTC"
      tasks:
        - task_key: evaluate
          notebook_task:
            notebook_path: ./jobs/evaluate_deployed_model.py
            base_parameters:
              model_name: "main.genie_optimization.optimizer_agent"
              alias: "champion"
```

---

## 7. Complete Promotion Flow Example

```python
"""Finalize task promotion logic (simplified from run_finalize.py)."""

import json
from mlflow import MlflowClient

def promote_if_ready(
    scores: dict,
    thresholds: dict,
    repeatability_score: float,
    held_out_accuracy: float,
    baseline_accuracy: float,
    model_name: str,
    model_version: str,
    regression_threshold: float = 5.0,
) -> dict:
    """Evaluate all gates and promote if all pass."""
    client = MlflowClient()
    result = {"promoted": False, "reasons": []}

    # Gate 1: Threshold check
    if not all_thresholds_met(scores, thresholds):
        failing = {k: v for k, v in scores.items() if v < thresholds.get(k, 0)}
        result["reasons"].append(f"Thresholds not met: {failing}")
        return result

    # Gate 2: Repeatability
    if repeatability_score < REPEATABILITY_TARGET:
        result["reasons"].append(
            f"Repeatability {repeatability_score:.1f}% < {REPEATABILITY_TARGET}%"
        )
        return result

    # Gate 3: Held-out generalization
    if held_out_accuracy < baseline_accuracy - regression_threshold:
        result["reasons"].append(
            f"Held-out regression: {held_out_accuracy:.1f}% vs "
            f"baseline {baseline_accuracy:.1f}%"
        )
        return result

    # All gates pass — promote
    client.set_registered_model_alias(
        name=model_name,
        alias="champion",
        version=model_version,
    )
    result["promoted"] = True
    return result
```

---

## Related Skills

- **Skill 09 — Evaluation:** The 9-judge system and threshold definitions
- **Skill 10 — UC Model Management:** How model versions and aliases work
- **Skill 11 (parent) — Model Serving:** Full deployment pipeline context
