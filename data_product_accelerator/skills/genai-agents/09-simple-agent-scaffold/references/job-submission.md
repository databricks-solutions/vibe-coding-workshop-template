# Running Steps 2–5 as a Serverless Job

Loaded by `SKILL.md` Step 2 when no interactive cluster is available (common in workshop and restricted workspaces).

## Why serverless

- **Classic clusters fail in restricted networks.** Workshop workspaces frequently restrict classic-cluster egress. The typical failure is `NETWORK_CONFIGURATION_FAILURE` on the control-plane handshake — you never even reach your notebook code.
- **Serverless uses the platform's managed network path**, which is available in every workspace that supports Databricks Apps / Genie / Foundation Models. If those work, serverless jobs work.
- **Fewer dependency surprises.** The `environments[].spec.dependencies` list pins the exact packages; you don't rely on an image's pre-installed versions.

Check `.vibecoding-state.md` — if every prior step used serverless or Databricks Apps, do not introduce a classic cluster for this step.

## Prepare the deploy notebook

Create `deploy_agent.py` (or `.ipynb`) next to `agent.py` and `agent-config.yaml`. Structure it as a notebook with cell separators so each of Steps 2–5 is independently debuggable:

```python
# Databricks notebook source
# COMMAND ----------
# Step 2: local test
# COMMAND ----------
# Step 3: log with MLflow (remember model_config="agent-config.yaml")
# COMMAND ----------
# Step 4: register in Unity Catalog
# COMMAND ----------
# Step 5: deploy to Model Serving
```

Sync the whole directory (`agent.py`, `agent-config.yaml`, `deploy_agent.py`) to the workspace:

```bash
databricks sync . /Users/<you>/booking_app_agents --profile $PROFILE
```

## Submit as a serverless job

```bash
databricks jobs submit --no-wait --profile $PROFILE --json '{
  "run_name": "deploy-agent",
  "tasks": [
    {
      "task_key": "deploy",
      "notebook_task": {
        "notebook_path": "/Users/<you>/booking_app_agents/deploy_agent"
      },
      "environment_key": "default"
    }
  ],
  "environments": [
    {
      "environment_key": "default",
      "spec": {
        "client": "1",
        "dependencies": [
          "databricks-agents",
          "databricks-openai",
          "mlflow[databricks]",
          "mcp",
          "nest_asyncio",
          "uv"
        ]
      }
    }
  ]
}'
```

Key points:

- **Always use `--no-wait`.** Otherwise the CLI blocks until the run finishes and you lose the polling loop.
- **`"client": "1"`** selects the serverless environment client version. Bump when Databricks releases a new one.
- **`"mlflow[databricks]"`** (quoted) — bare `mlflow` breaks `register_model()` on Azure with `ModuleNotFoundError: azure.core`.
- **No `new_cluster`, no `existing_cluster_id`.** If either appears in your JSON you're not serverless.

## Poll the run

```bash
RUN_ID=$(databricks jobs submit --no-wait --profile $PROFILE --json '...' | jq -r '.run_id')

while true; do
  STATE=$(databricks jobs get-run "$RUN_ID" --profile $PROFILE --output json \
          | jq -r '.state.life_cycle_state + "/" + (.state.result_state // "-")')
  echo "$(date +%H:%M:%S) $STATE"
  case "$STATE" in
    TERMINATED/*|INTERNAL_ERROR/*|SKIPPED/*) break ;;
  esac
  sleep 15
done

databricks jobs get-run "$RUN_ID" --profile $PROFILE --output json | jq '.state'
```

## When it fails

| Symptom | Likely cause | Fix |
|---|---|---|
| `NETWORK_CONFIGURATION_FAILURE` | You're on a classic cluster | Remove `new_cluster`, use `environment_key` + `environments` |
| `FileNotFoundError: Config file is not provided` inside `log_model()` | CWD ≠ agent directory (jobs start at `/`) | Pass `model_config="agent-config.yaml"` to `log_model()` — see `SKILL.md` Step 3 |
| `ModuleNotFoundError: azure.core` | Bare `mlflow` on Azure | Change dependency to `"mlflow[databricks]"` |
| Run stuck in `PENDING` > 5 min | Dependency resolution or image warm-up | Check `state_message` in `get-run`; verify `uv` is in the dependency list |

## When to prefer an interactive notebook instead

If you have a working Databricks notebook attached to an interactive cluster or a SQL warehouse profile, and the workspace does not have classic-cluster network restrictions, running cells interactively is faster — you get Step-by-step feedback without a job submit/poll cycle. The serverless-job path documented here is the safe default when you can't assume interactive availability.
