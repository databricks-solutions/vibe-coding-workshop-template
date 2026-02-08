# CLI + jq Patterns for Autonomous Operations

Complete catalog of `jq` patterns for parsing Databricks CLI JSON output.

---

## Job Monitoring

### Get Job State
```bash
databricks jobs get-run <RUN_ID> --output json | jq '.state'
# Output: {"life_cycle_state": "TERMINATED", "result_state": "SUCCESS", ...}
```

### Get Lifecycle State Only
```bash
databricks jobs get-run <RUN_ID> --output json | jq -r '.state.life_cycle_state'
# Output: TERMINATED
```

### Get Result State Only (when TERMINATED)
```bash
databricks jobs get-run <RUN_ID> --output json | jq -r '.state.result_state'
# Output: SUCCESS | FAILED | TIMEDOUT | CANCELED
```

### Get Error Message
```bash
databricks jobs get-run <RUN_ID> --output json | jq -r '.state.state_message'
```

---

## Multi-Task Job Patterns

### Get All Task Summaries
```bash
databricks jobs get-run <RUN_ID> --output json \
  | jq '.tasks[] | {task: .task_key, run_id: .run_id, result: .state.result_state}'
```

### Get Failed Tasks Only
```bash
databricks jobs get-run <RUN_ID> --output json \
  | jq '.tasks[] | select(.state.result_state == "FAILED") | {
    task: .task_key,
    run_id: .run_id,
    error: .state.state_message,
    url: .run_page_url
  }'
```

### Get Task Progress Summary (counts)
```bash
databricks jobs get-run <RUN_ID> --output json | jq '{
  total: (.tasks | length),
  succeeded: ([.tasks[] | select(.state.result_state == "SUCCESS")] | length),
  failed: ([.tasks[] | select(.state.result_state == "FAILED")] | length),
  running: ([.tasks[] | select(.state.life_cycle_state == "RUNNING")] | length),
  pending: ([.tasks[] | select(.state.life_cycle_state == "PENDING")] | length),
  failed_tasks: [.tasks[] | select(.state.result_state == "FAILED") | .task_key]
}'
```

### Get Task Run IDs for Output Retrieval
```bash
databricks jobs get-run <RUN_ID> --output json \
  | jq -r '.tasks[] | "\(.task_key)\t\(.run_id)\t\(.state.result_state)"'
```

### Get Specific Failed Task Run ID by Name
```bash
FAILED_TASK_RUN_ID=$(databricks jobs get-run <RUN_ID> --output json \
  | jq -r '.tasks[] | select(.task_key == "task_name") | .run_id')
```

---

## Task Output Retrieval

### Get Notebook Output (Single Task)
```bash
# IMPORTANT: Use TASK run_id, NOT parent job run_id
databricks jobs get-run-output <TASK_RUN_ID> --output json \
  | jq -r '.notebook_output.result // "No output"'
```

### Check if Output is Truncated
```bash
databricks jobs get-run-output <TASK_RUN_ID> --output json \
  | jq '.notebook_output.truncated'
```

### Get All Task Outputs in Loop
```bash
TASK_RUN_IDS=$(databricks jobs get-run <JOB_RUN_ID> --output json | jq -r '.tasks[].run_id')

for TASK_ID in $TASK_RUN_IDS; do
  echo "=== Task $TASK_ID ==="
  databricks jobs get-run-output $TASK_ID --output json 2>/dev/null \
    | jq -r '.notebook_output.result // "No output"'
done
```

### Get Failed Task Outputs Only
```bash
FAILED_IDS=$(databricks jobs get-run <JOB_RUN_ID> --output json \
  | jq -r '.tasks[] | select(.state.result_state == "FAILED") | .run_id')

for TASK_ID in $FAILED_IDS; do
  TASK_KEY=$(databricks jobs get-run $TASK_ID --output json | jq -r '.task_key // "unknown"')
  echo "=== FAILED: $TASK_KEY (run_id: $TASK_ID) ==="
  databricks jobs get-run-output $TASK_ID --output json 2>/dev/null \
    | jq -r '.notebook_output.result // "No output"'
  echo ""
done
```

---

## Pipeline Monitoring

### Get Pipeline State
```bash
databricks pipelines get <PIPELINE_ID> --output json | jq '.state'
```

### Get Latest Update State
```bash
databricks pipelines get <PIPELINE_ID> --output json \
  | jq '.latest_updates[0] | {update_id, state, creation_time}'
```

### Get Pipeline Error Events
```bash
databricks pipelines list-pipeline-events <PIPELINE_ID> --output json \
  | jq '[.events[] | select(.level == "ERROR") | {
    timestamp: .timestamp,
    message: .message,
    error: (.error.exceptions // [])[:1]
  }] | .[0:5]'
```

### Get Flow Progress (Expectation Results)
```bash
databricks pipelines list-pipeline-events <PIPELINE_ID> --output json \
  | jq '[.events[] | select(.event_type == "flow_progress") | {
    flow: .origin.flow_name,
    status: .details.flow_progress.status,
    rows: .details.flow_progress.metrics.num_output_rows,
    quality: .details.flow_progress.data_quality
  }] | .[0:10]'
```

### Get Update Progress Events
```bash
databricks pipelines list-pipeline-events <PIPELINE_ID> --output json \
  | jq '[.events[] | select(.event_type == "update_progress") | {
    state: .details.update_progress.state,
    message: .message
  }] | .[0:5]'
```

---

## Cluster Monitoring

### Get Cluster State
```bash
databricks clusters get <CLUSTER_ID> --output json | jq '{
  state: .state,
  state_message: .state_message,
  driver: .driver,
  num_workers: .num_workers
}'
```

### Get Recent Cluster Events
```bash
databricks clusters events <CLUSTER_ID> --output json \
  | jq '[.events[] | {
    timestamp: .timestamp,
    type: .type,
    details: .details
  }] | .[0:10]'
```

### Get Cluster Termination Reason
```bash
databricks clusters get <CLUSTER_ID> --output json \
  | jq '.termination_reason'
```

---

## Warehouse Monitoring

### Get Warehouse State
```bash
databricks warehouses get <WAREHOUSE_ID> --output json | jq '{
  name: .name,
  state: .state,
  num_clusters: .num_clusters,
  auto_stop_mins: .auto_stop_mins
}'
```

---

## Run ID Extraction

### Extract RUN_ID from Bundle Run Output
```bash
# databricks bundle run output format:
# Run URL: https://workspace.cloud.databricks.com/?o=123#job/456/run/789
# Extract the last number (789 = run_id)

RUN_URL=$(databricks bundle run -t dev job_name 2>&1 | grep -o 'https://[^ ]*')
RUN_ID=$(echo $RUN_URL | grep -o '[0-9]*$')
echo "Run ID: $RUN_ID"
```

### Extract Job ID from Bundle Run
```bash
JOB_ID=$(echo $RUN_URL | grep -oP 'job/\K[0-9]+')
echo "Job ID: $JOB_ID"
```

---

## Polling Patterns

### Poll Job Until Completion
```bash
RUN_ID=$1
INTERVAL=30

while true; do
  LIFECYCLE=$(databricks jobs get-run $RUN_ID --output json | jq -r '.state.life_cycle_state')

  if [ "$LIFECYCLE" = "TERMINATED" ]; then
    RESULT=$(databricks jobs get-run $RUN_ID --output json | jq -r '.state.result_state')
    echo "Job completed: $RESULT"
    break
  elif [ "$LIFECYCLE" = "INTERNAL_ERROR" ]; then
    echo "Job hit INTERNAL_ERROR"
    break
  fi

  echo "$(date +%H:%M:%S) Status: $LIFECYCLE"
  sleep $INTERVAL
done
```

### Poll Pipeline Until Completion
```bash
PIPELINE_ID=$1
INTERVAL=30

while true; do
  STATE=$(databricks pipelines get $PIPELINE_ID --output json | jq -r '.latest_updates[0].state')

  if [ "$STATE" = "COMPLETED" ] || [ "$STATE" = "FAILED" ] || [ "$STATE" = "CANCELED" ]; then
    echo "Pipeline update: $STATE"
    break
  fi

  echo "$(date +%H:%M:%S) Pipeline state: $STATE"
  sleep $INTERVAL
done
```

---

## Profile-Based Commands

All commands can use a specific Databricks profile:

```bash
# Method 1: Environment variable (recommended for scripts)
DATABRICKS_CONFIG_PROFILE=my_profile databricks jobs get-run <RUN_ID> --output json

# Method 2: CLI flag
databricks --profile my_profile jobs get-run <RUN_ID> --output json
```

---

## Combined Patterns

### Full Job Monitoring Workflow
```bash
# 1. Launch job
RUN_OUTPUT=$(databricks bundle run -t dev my_job 2>&1)
RUN_URL=$(echo "$RUN_OUTPUT" | grep -o 'https://[^ ]*')
RUN_ID=$(echo "$RUN_URL" | grep -o '[0-9]*$')
echo "Monitoring Run: $RUN_ID"

# 2. Poll until done
while true; do
  STATUS=$(databricks jobs get-run $RUN_ID --output json)
  LIFECYCLE=$(echo $STATUS | jq -r '.state.life_cycle_state')
  [ "$LIFECYCLE" = "TERMINATED" ] && break
  echo "$(date +%H:%M:%S) $LIFECYCLE"
  sleep 30
done

# 3. Check result
RESULT=$(echo $STATUS | jq -r '.state.result_state')
echo "Result: $RESULT"

# 4. If failed, get details
if [ "$RESULT" = "FAILED" ]; then
  echo "=== Failed Tasks ==="
  echo $STATUS | jq '.tasks[] | select(.state.result_state == "FAILED") | {
    task: .task_key,
    error: .state.state_message,
    url: .run_page_url
  }'
fi
```
