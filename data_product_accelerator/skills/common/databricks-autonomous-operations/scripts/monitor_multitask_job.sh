#!/bin/bash
# monitor_multitask_job.sh
#
# Monitors a multi-task Databricks job run until completion,
# then reports task-level results and outputs.
#
# Usage:
#   ./monitor_multitask_job.sh <JOB_RUN_ID> [PROFILE] [POLL_INTERVAL]
#
# Arguments:
#   JOB_RUN_ID     - The run ID to monitor
#   PROFILE        - Databricks config profile (default: DEFAULT)
#   POLL_INTERVAL  - Seconds between polls (default: 30)
#
# Example:
#   ./monitor_multitask_job.sh 123456789 my_profile 60

set -euo pipefail

JOB_RUN_ID=${1:?"Usage: $0 <JOB_RUN_ID> [PROFILE] [POLL_INTERVAL]"}
PROFILE=${2:-DEFAULT}
POLL_INTERVAL=${3:-30}

export DATABRICKS_CONFIG_PROFILE="$PROFILE"

echo "============================================"
echo "  Monitoring Job Run: $JOB_RUN_ID"
echo "  Profile: $PROFILE"
echo "  Poll Interval: ${POLL_INTERVAL}s"
echo "============================================"
echo ""

# --- Phase 1: Poll until completion ---

ITERATION=0
while true; do
  ITERATION=$((ITERATION + 1))
  STATUS=$(databricks jobs get-run "$JOB_RUN_ID" --output json 2>/dev/null)
  LIFECYCLE=$(echo "$STATUS" | jq -r '.state.life_cycle_state')

  if [ "$LIFECYCLE" = "TERMINATED" ] || [ "$LIFECYCLE" = "INTERNAL_ERROR" ]; then
    RESULT=$(echo "$STATUS" | jq -r '.state.result_state // "N/A"')
    echo ""
    echo ">>> Job completed: lifecycle=$LIFECYCLE result=$RESULT"
    break
  fi

  # Show task progress
  TASK_SUMMARY=$(echo "$STATUS" | jq -r '{
    running: ([.tasks[] | select(.state.life_cycle_state == "RUNNING")] | length),
    succeeded: ([.tasks[] | select(.state.result_state == "SUCCESS")] | length),
    failed: ([.tasks[] | select(.state.result_state == "FAILED")] | length),
    pending: ([.tasks[] | select(.state.life_cycle_state == "PENDING")] | length),
    total: (.tasks | length)
  } | "running=\(.running) succeeded=\(.succeeded) failed=\(.failed) pending=\(.pending) total=\(.total)"')

  echo "[$(date +%H:%M:%S)] Poll #${ITERATION}: lifecycle=$LIFECYCLE $TASK_SUMMARY"

  sleep "$POLL_INTERVAL"
done

# --- Phase 2: Collect results ---

echo ""
echo "============================================"
echo "  Task Results"
echo "============================================"

# Summary
echo "$STATUS" | jq '{
  total: (.tasks | length),
  succeeded: ([.tasks[] | select(.state.result_state == "SUCCESS")] | length),
  failed: ([.tasks[] | select(.state.result_state == "FAILED")] | length),
  failed_tasks: [.tasks[] | select(.state.result_state == "FAILED") | .task_key]
}'

# --- Phase 3: Get output from each task ---

echo ""
echo "============================================"
echo "  Task Outputs"
echo "============================================"

echo "$STATUS" | jq -c '.tasks[]' | while read -r task; do
  TASK_KEY=$(echo "$task" | jq -r '.task_key')
  TASK_RUN_ID=$(echo "$task" | jq -r '.run_id')
  TASK_RESULT=$(echo "$task" | jq -r '.state.result_state // "UNKNOWN"')
  TASK_URL=$(echo "$task" | jq -r '.run_page_url // "N/A"')

  echo ""
  echo "--- $TASK_KEY (run_id: $TASK_RUN_ID) ---"
  echo "  Result: $TASK_RESULT"
  echo "  URL: $TASK_URL"

  if [ "$TASK_RESULT" = "SUCCESS" ]; then
    # Get notebook output
    OUTPUT=$(databricks jobs get-run-output "$TASK_RUN_ID" --output json 2>/dev/null || echo '{}')
    NOTEBOOK_RESULT=$(echo "$OUTPUT" | jq -r '.notebook_output.result // "No output"')
    TRUNCATED=$(echo "$OUTPUT" | jq -r '.notebook_output.truncated // false')
    echo "  Output: $NOTEBOOK_RESULT"
    if [ "$TRUNCATED" = "true" ]; then
      echo "  ⚠️  Output was truncated. Check Workspace UI for full logs."
    fi
  elif [ "$TASK_RESULT" = "FAILED" ]; then
    # Get error message
    ERROR=$(echo "$task" | jq -r '.state.state_message // "Unknown error"')
    echo "  Error: $ERROR"

    # Try to get task output for more details
    OUTPUT=$(databricks jobs get-run-output "$TASK_RUN_ID" --output json 2>/dev/null || echo '{}')
    NOTEBOOK_RESULT=$(echo "$OUTPUT" | jq -r '.notebook_output.result // ""')
    if [ -n "$NOTEBOOK_RESULT" ] && [ "$NOTEBOOK_RESULT" != "null" ]; then
      echo "  Notebook Output: $NOTEBOOK_RESULT"
    fi
  fi
done

# --- Phase 4: Final summary ---

echo ""
echo "============================================"
echo "  Final Summary"
echo "============================================"

TOTAL=$(echo "$STATUS" | jq '.tasks | length')
SUCCEEDED=$(echo "$STATUS" | jq '[.tasks[] | select(.state.result_state == "SUCCESS")] | length')
FAILED=$(echo "$STATUS" | jq '[.tasks[] | select(.state.result_state == "FAILED")] | length')
SUCCESS_PCT=$(echo "scale=1; $SUCCEEDED * 100 / $TOTAL" | bc 2>/dev/null || echo "N/A")

echo "  Total tasks:   $TOTAL"
echo "  Succeeded:     $SUCCEEDED"
echo "  Failed:        $FAILED"
echo "  Success rate:  ${SUCCESS_PCT}%"

if [ "$FAILED" -gt 0 ]; then
  echo ""
  echo "  Failed task keys:"
  echo "$STATUS" | jq -r '.tasks[] | select(.state.result_state == "FAILED") | "    - \(.task_key): \(.state.state_message // "No message")"'
fi

echo ""
echo "  Run page: $(echo "$STATUS" | jq -r '.run_page_url // "N/A"')"
echo ""
echo "Done."
