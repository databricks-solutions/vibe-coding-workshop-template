# CI/CD templates (DAB jobs and task wiring)

Copy-adapt snippets for **Databricks Asset Bundles** jobs that implement
**evaluate → promote → deploy** and related triggers.

For deeper DAG patterns, retries, and production hardening, see
[`deployment-job-patterns.md`](deployment-job-patterns.md).

---

## Evaluate-then-promote pipeline (`databricks.yml`)

Add a job that runs evaluation, conditionally promotes, then deploys (e.g. to
Apps via a notebook or CLI step):

```yaml
# databricks.yml — add a deployment job
resources:
  jobs:
    agent_deploy_pipeline:
      name: "agent-deploy-pipeline"
      tasks:
        - task_key: evaluate
          notebook_task:
            notebook_path: ./notebooks/evaluate_agent.py
          libraries:
            - pypi:
                package: "mlflow[databricks]>=3.10.1"

        - task_key: promote
          depends_on:
            - task_key: evaluate
          notebook_task:
            notebook_path: ./notebooks/promote_if_passing.py

        - task_key: deploy_app
          depends_on:
            - task_key: promote
          notebook_task:
            notebook_path: ./notebooks/deploy_to_apps.py
```

---

## Pass evaluation results between tasks (`taskValues`)

### `evaluate_agent.py`

```python
import mlflow

results = mlflow.genai.evaluate(data=eval_df, predict_fn=fn, scorers=scorers)
thresholds_met = check_thresholds(results)

dbutils.jobs.taskValues.set(key="thresholds_met", value=thresholds_met)
dbutils.jobs.taskValues.set(key="eval_run_id", value=results.run_id)
```

### `promote_if_passing.py`

```python
thresholds_met = dbutils.jobs.taskValues.get(
    taskKey="evaluate", key="thresholds_met"
)
if not thresholds_met:
    dbutils.notebook.exit("Evaluation did not pass thresholds — skipping promotion")

# Promote champion in UC
eval_run_id = dbutils.jobs.taskValues.get(taskKey="evaluate", key="eval_run_id")
# ... promote logic from SDLC Step 5
```

---

## Trigger on model registration (table update)

Use a **job trigger** so the pipeline runs when new rows appear in a model
version table (adjust catalog/schema/table to your UC layout):

```yaml
# databricks.yml trigger
resources:
  jobs:
    agent_deploy_pipeline:
      trigger:
        table_update:
          table_names:
            - "main.genie_optimization.genie_space_model_versions"
          condition: NEW_ROW
```

> **Note:** MLflow webhooks or other orchestrators can also kick off the same
> job; pick the mechanism your workspace supports and your governance model
> requires.
