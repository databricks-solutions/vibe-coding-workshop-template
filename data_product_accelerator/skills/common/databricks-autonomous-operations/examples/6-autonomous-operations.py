"""
Databricks SDK - Autonomous Operations Examples

Patterns for monitoring jobs, diagnosing failures, and self-healing workflows.

Jobs API: https://databricks-sdk-py.readthedocs.io/en/latest/workspace/jobs/jobs.html
Pipelines API: https://databricks-sdk-py.readthedocs.io/en/latest/workspace/pipelines/pipelines.html
"""

import json
import time
from datetime import timedelta
from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import NotFound, ResourceAlreadyExists

w = WorkspaceClient()

# =============================================================================
# JOB MONITORING: Poll for Completion
# =============================================================================

def monitor_job_run(run_id: int, poll_interval: int = 30, max_wait_minutes: int = 120) -> dict:
    """
    Poll a job run until completion. Returns the final run status.

    Args:
        run_id: The run ID to monitor
        poll_interval: Seconds between polls (default 30)
        max_wait_minutes: Maximum wait time before timeout (default 120)

    Returns:
        dict with keys: result_state, state_message, tasks (list of task results)
    """
    start_time = time.time()
    max_wait_seconds = max_wait_minutes * 60

    while True:
        elapsed = time.time() - start_time
        if elapsed > max_wait_seconds:
            raise TimeoutError(f"Job run {run_id} did not complete within {max_wait_minutes} minutes")

        run = w.jobs.get_run(run_id=run_id)
        lifecycle = run.state.life_cycle_state.value

        if lifecycle == "TERMINATED":
            result = run.state.result_state.value if run.state.result_state else "UNKNOWN"
            return {
                "result_state": result,
                "state_message": run.state.state_message or "",
                "run_page_url": run.run_page_url,
                "tasks": [
                    {
                        "task_key": t.task_key,
                        "run_id": t.run_id,
                        "result_state": t.state.result_state.value if t.state.result_state else "UNKNOWN",
                        "state_message": t.state.state_message or "",
                    }
                    for t in (run.tasks or [])
                ],
            }

        if lifecycle == "INTERNAL_ERROR":
            return {
                "result_state": "INTERNAL_ERROR",
                "state_message": run.state.state_message or "Internal error",
                "run_page_url": run.run_page_url,
                "tasks": [],
            }

        print(f"[{int(elapsed)}s] Run {run_id}: {lifecycle}")
        time.sleep(poll_interval)


# Usage:
# result = monitor_job_run(run_id=123456)
# if result["result_state"] == "SUCCESS":
#     print("Job succeeded!")
# else:
#     print(f"Job failed: {result['state_message']}")
#     for task in result["tasks"]:
#         if task["result_state"] == "FAILED":
#             print(f"  Failed task: {task['task_key']} - {task['state_message']}")


# =============================================================================
# MULTI-TASK JOB: Get Task-Level Output
# =============================================================================

def get_multi_task_outputs(run_id: int) -> dict:
    """
    Get output from all tasks in a multi-task job.

    CRITICAL: get_run_output() only works on individual TASK run_ids,
    NOT the parent job run_id for multi-task jobs.

    Returns:
        dict mapping task_key -> {result_state, output, error}
    """
    run = w.jobs.get_run(run_id=run_id)
    results = {}

    for task in (run.tasks or []):
        task_result = {
            "result_state": task.state.result_state.value if task.state.result_state else "UNKNOWN",
            "state_message": task.state.state_message or "",
            "run_page_url": task.run_page_url,
            "output": None,
        }

        try:
            # Use TASK run_id, not parent job run_id
            output = w.jobs.get_run_output(run_id=task.run_id)
            if output.notebook_output:
                task_result["output"] = output.notebook_output.result
                task_result["truncated"] = output.notebook_output.truncated
        except Exception as e:
            task_result["output_error"] = str(e)

        results[task.task_key] = task_result

    return results


# Usage:
# outputs = get_multi_task_outputs(run_id=123456)
# for task_key, info in outputs.items():
#     print(f"{task_key}: {info['result_state']}")
#     if info["output"]:
#         print(f"  Output: {info['output'][:200]}")


# =============================================================================
# FAILURE DIAGNOSIS: Extract and Categorize Errors
# =============================================================================

def diagnose_job_failure(run_id: int) -> list:
    """
    Extract failure information from a failed job run.

    Returns list of failure dicts with task_key, error_category, error_message, fix_suggestion.
    """
    run = w.jobs.get_run(run_id=run_id)
    failures = []

    for task in (run.tasks or []):
        if task.state.result_state and task.state.result_state.value == "FAILED":
            error_msg = task.state.state_message or "Unknown error"
            category, suggestion = _categorize_error(error_msg)

            failures.append({
                "task_key": task.task_key,
                "task_run_id": task.run_id,
                "error_category": category,
                "error_message": error_msg,
                "fix_suggestion": suggestion,
                "run_page_url": task.run_page_url,
            })

    return failures


def _categorize_error(error_msg: str) -> tuple:
    """Categorize error and suggest fix."""
    error_msg_lower = error_msg.lower()

    if "modulenotfounderror" in error_msg_lower:
        return "MISSING_DEPENDENCY", "Add %pip install <module> or add to DAB environment spec"
    elif "unresolved_column" in error_msg_lower:
        return "COLUMN_ERROR", "Check column names against DESCRIBE TABLE or Gold YAML schema"
    elif "table_or_view_not_found" in error_msg_lower:
        return "TABLE_NOT_FOUND", "Run setup job first. Verify catalog.schema.table path."
    elif "delta_multiple_source_row_matching" in error_msg_lower:
        return "DUPLICATE_KEYS", "Deduplicate source before MERGE. Use ROW_NUMBER() partition."
    elif "permission" in error_msg_lower or "forbidden" in error_msg_lower:
        return "PERMISSION_DENIED", "Check UC grants: SHOW GRANTS ON TABLE ..."
    elif "parse_syntax_error" in error_msg_lower:
        return "SQL_SYNTAX", "Read and fix the failing SQL statement"
    elif "timeout" in error_msg_lower:
        return "TIMEOUT", "Increase timeout_seconds in DAB YAML"
    elif "cannot import name" in error_msg_lower:
        return "IMPORT_ERROR", "%pip install --upgrade databricks-sdk>=0.40.0"
    elif "outofmemoryerror" in error_msg_lower:
        return "OOM", "Increase memory, optimize query, add .repartition()"
    else:
        return "UNKNOWN", "Read full stack trace from task output for diagnosis"


# Usage:
# failures = diagnose_job_failure(run_id=123456)
# for f in failures:
#     print(f"Task: {f['task_key']}")
#     print(f"  Category: {f['error_category']}")
#     print(f"  Fix: {f['fix_suggestion']}")


# =============================================================================
# RUN A JOB AND MONITOR (Complete Pattern)
# =============================================================================

def run_and_monitor(job_id: int, params: dict = None, poll_interval: int = 30) -> dict:
    """
    Run a job, monitor until completion, and return structured results.

    Args:
        job_id: The job ID to run
        params: Optional notebook parameters
        poll_interval: Seconds between polls

    Returns:
        dict with result_state, outputs (from multi-task), failures (if any)
    """
    # Start the job
    run = w.jobs.run_now(job_id=job_id, notebook_params=params)
    run_id = run.run_id
    print(f"Started run {run_id}")

    # Monitor until completion
    result = monitor_job_run(run_id=run_id, poll_interval=poll_interval)

    # Add task outputs
    if result["result_state"] == "SUCCESS":
        result["outputs"] = get_multi_task_outputs(run_id=run_id)
    elif result["result_state"] == "FAILED":
        result["failures"] = diagnose_job_failure(run_id=run_id)

    return result


# Usage:
# result = run_and_monitor(job_id=123, params={"catalog": "main", "schema": "gold"})


# =============================================================================
# PIPELINE MONITORING
# =============================================================================

def monitor_pipeline_update(pipeline_id: str, poll_interval: int = 30) -> dict:
    """Monitor a DLT pipeline update until completion."""
    while True:
        pipeline = w.pipelines.get(pipeline_id=pipeline_id)

        if not pipeline.latest_updates:
            print("No updates found")
            return {"state": "NO_UPDATES"}

        latest = pipeline.latest_updates[0]
        state = latest.state.value if latest.state else "UNKNOWN"

        if state in ("COMPLETED", "FAILED", "CANCELED"):
            # Get error events if failed
            errors = []
            if state == "FAILED":
                events = w.pipelines.list_pipeline_events(pipeline_id=pipeline_id)
                for event in events:
                    if event.level and event.level.value == "ERROR":
                        errors.append({
                            "message": event.message,
                            "timestamp": str(event.timestamp),
                        })

            return {
                "state": state,
                "update_id": latest.update_id,
                "errors": errors[:5],  # Limit to 5 most recent
            }

        print(f"Pipeline {pipeline_id}: {state}")
        time.sleep(poll_interval)


# Usage:
# w.pipelines.start_update(pipeline_id="abc123")
# result = monitor_pipeline_update(pipeline_id="abc123")
# if result["state"] == "FAILED":
#     for err in result["errors"]:
#         print(f"Error: {err['message']}")


# =============================================================================
# LAKEHOUSE MONITOR OPERATIONS
# =============================================================================

def safe_create_monitor(table_name: str, **monitor_kwargs):
    """Create a monitor, handling ResourceAlreadyExists by deleting first."""
    try:
        monitor = w.quality_monitors.create(table_name=table_name, **monitor_kwargs)
        print(f"Created monitor for {table_name}")
        return monitor
    except ResourceAlreadyExists:
        print(f"Monitor exists for {table_name}, recreating...")
        w.quality_monitors.delete(table_name=table_name)
        # Drop output tables
        # spark.sql(f"DROP TABLE IF EXISTS {table_name}_profile_metrics")
        # spark.sql(f"DROP TABLE IF EXISTS {table_name}_drift_metrics")
        time.sleep(5)  # Brief pause for cleanup
        monitor = w.quality_monitors.create(table_name=table_name, **monitor_kwargs)
        print(f"Recreated monitor for {table_name}")
        return monitor


def check_monitor_status(table_name: str) -> dict:
    """Check monitor status and return diagnostics."""
    try:
        monitor = w.quality_monitors.get(table_name=table_name)
        return {
            "exists": True,
            "status": str(monitor.status) if monitor.status else "UNKNOWN",
            "last_refresh": str(monitor.last_refresh_time) if monitor.last_refresh_time else None,
            "custom_metrics_count": len(monitor.custom_metrics) if monitor.custom_metrics else 0,
        }
    except NotFound:
        return {"exists": False}


# Usage:
# status = check_monitor_status("catalog.schema.fact_usage")
# print(f"Monitor exists: {status['exists']}, Status: {status.get('status')}")


# =============================================================================
# DIAGNOSTIC HELPERS
# =============================================================================

def check_table_exists(full_table_name: str) -> bool:
    """Check if a Unity Catalog table exists."""
    try:
        result = w.tables.exists(full_name=full_table_name)
        return result.table_exists
    except Exception:
        return False


def get_table_columns(full_table_name: str) -> list:
    """Get column names for a table (for schema validation)."""
    try:
        table = w.tables.get(full_name=full_table_name)
        return [col.name for col in table.columns]
    except NotFound:
        return []


def list_recent_runs(job_id: int, limit: int = 5) -> list:
    """List recent runs for a job with their status."""
    runs = []
    for run in w.jobs.list_runs(job_id=job_id):
        runs.append({
            "run_id": run.run_id,
            "start_time": str(run.start_time),
            "result_state": run.state.result_state.value if run.state.result_state else "RUNNING",
            "state_message": run.state.state_message or "",
        })
        if len(runs) >= limit:
            break
    return runs


# Usage:
# recent = list_recent_runs(job_id=123, limit=3)
# for r in recent:
#     print(f"Run {r['run_id']}: {r['result_state']}")


# =============================================================================
# SELF-HEALING WORKFLOW
# =============================================================================

def self_healing_run(job_id: int, max_retries: int = 3, params: dict = None) -> dict:
    """
    Run a job with automatic retry and failure diagnosis.

    This is the SDK equivalent of the autonomous operations loop.
    Max retries before escalation.
    """
    attempts = []

    for attempt in range(1, max_retries + 1):
        print(f"\n=== Attempt {attempt}/{max_retries} ===")

        result = run_and_monitor(job_id=job_id, params=params)
        attempts.append({
            "attempt": attempt,
            "result_state": result["result_state"],
            "failures": result.get("failures", []),
        })

        if result["result_state"] == "SUCCESS":
            print(f"Job succeeded on attempt {attempt}")
            return {"success": True, "attempts": attempts, "result": result}

        # Diagnose and log
        if result.get("failures"):
            for f in result["failures"]:
                print(f"  FAILED: {f['task_key']} ({f['error_category']})")
                print(f"  Fix: {f['fix_suggestion']}")

        if attempt < max_retries:
            print(f"Retrying in 10 seconds...")
            time.sleep(10)

    # Escalation
    print(f"\n=== ESCALATION: Job failed after {max_retries} attempts ===")
    return {
        "success": False,
        "attempts": attempts,
        "escalation": {
            "total_attempts": max_retries,
            "unique_errors": list(set(
                f["error_category"]
                for a in attempts
                for f in a.get("failures", [])
            )),
            "suggestion": "Review task outputs in Databricks UI for full stack traces",
        }
    }


# Usage:
# result = self_healing_run(job_id=123, max_retries=3, params={"catalog": "main"})
# if not result["success"]:
#     print(f"Escalation: {result['escalation']}")
