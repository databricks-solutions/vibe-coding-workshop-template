#!/usr/bin/env python3
"""
Genie Benchmark Evaluator CLI

Standalone evaluation script for Genie Space benchmarking. Supports inline
evaluation (query Genie per benchmark, run code judges, log to MLflow) and
job-based evaluation (trigger Databricks Job, poll, read MLflow results).

Usage:
    python genie_evaluator.py --space-id <ID> --benchmarks golden-queries.yaml
    python genie_evaluator.py --space-id <ID> --benchmarks golden-queries.yaml --job-mode
    python genie_evaluator.py --space-id <ID> --benchmarks golden-queries.yaml --evaluate-only

Requirements:
    - databricks-sdk
    - mlflow[databricks]>=3.4.0
    - pyyaml
"""

import time
import json
import yaml
import argparse
import subprocess
import re
from datetime import datetime
from pathlib import Path

try:
    from databricks.sdk import WorkspaceClient
    _w = WorkspaceClient()
except ImportError:
    _w = None

try:
    import mlflow
except ImportError:
    mlflow = None


def _verify_mlflow_tracking():
    """Fail fast if MLflow is not configured for remote tracking."""
    if mlflow is None:
        raise RuntimeError(
            "mlflow is not installed. Install with: pip install 'mlflow[databricks]'"
        )
    tracking_uri = mlflow.get_tracking_uri()
    if tracking_uri != "databricks" and not tracking_uri.startswith("databricks"):
        import os
        host = os.environ.get("DATABRICKS_HOST", "")
        if not host:
            raise RuntimeError(
                "MLflow is not configured for Databricks tracking.\n"
                "Set these environment variables before running:\n"
                "  export DATABRICKS_HOST='https://<workspace>.cloud.databricks.com'\n"
                "  export DATABRICKS_TOKEN='<token>'\n"
                "  export MLFLOW_TRACKING_URI='databricks'\n"
                "Or run inside a Databricks notebook where MLflow is auto-configured."
            )


# =============================================================================
# Core Query
# =============================================================================

def run_genie_query(space_id: str, question: str, max_wait: int = 120) -> dict:
    """Execute a query against Genie and return SQL + status."""
    if _w is None:
        return {"status": "ERROR", "sql": None, "error": "SDK not initialized"}
    try:
        resp = _w.genie.start_conversation(space_id=space_id, content=question)
        conversation_id = resp.conversation_id
        message_id = resp.message_id

        poll_interval = 3
        start = time.time()
        msg = None
        while time.time() - start < max_wait:
            time.sleep(poll_interval)
            msg = _w.genie.get_message(
                space_id=space_id,
                conversation_id=conversation_id,
                message_id=message_id,
            )
            status = str(msg.status) if hasattr(msg, "status") else "UNKNOWN"
            if any(s in status for s in ["COMPLETED", "FAILED", "CANCELLED"]):
                break
            poll_interval = min(poll_interval + 1, 10)

        sql = None
        if msg and hasattr(msg, "attachments") and msg.attachments:
            for att in msg.attachments:
                if hasattr(att, "query") and att.query:
                    sql = att.query.query if hasattr(att.query, "query") else str(att.query)

        return {
            "status": status,
            "sql": sql,
            "conversation_id": conversation_id,
            "message_id": message_id,
        }
    except Exception as e:
        return {"status": "ERROR", "sql": None, "error": str(e)}


# =============================================================================
# Asset Detection
# =============================================================================

def detect_asset_type(sql: str) -> str:
    """Detect asset type (MV, TVF, TABLE) from SQL string."""
    if not sql:
        return "NONE"
    sql_lower = sql.lower()
    if "mv_" in sql_lower or "measure(" in sql_lower:
        return "MV"
    elif "get_" in sql_lower:
        return "TVF"
    return "TABLE"


# =============================================================================
# Inline Evaluation
# =============================================================================

def run_evaluation_iteration(
    space_id: str,
    benchmarks: list,
    experiment_name: str,
    iteration: int,
    uc_schema: str = None,
    model_id: str = None,
) -> dict:
    """Run a single evaluation iteration with MLflow-tracked scoring.

    All metrics and artifacts are logged to the active MLflow experiment.
    Run names follow genie_eval_iter{N}_{timestamp} convention for
    programmatic querying.
    Raises RuntimeError if MLflow is not configured for Databricks tracking.
    """
    _verify_mlflow_tracking()
    mlflow.set_experiment(experiment_name)

    print(f"\n--- Iteration {iteration}: Evaluating {len(benchmarks)} questions ---\n")

    results = []
    run_name = f"genie_eval_iter{iteration}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    with mlflow.start_run(run_name=run_name) as run:
        mlflow.log_param("space_id", space_id)
        mlflow.log_param("iteration", iteration)
        mlflow.log_param("benchmark_count", len(benchmarks))
        print(f"  MLflow Run: {run.info.run_id} ({run_name})")

        for q in benchmarks:
            qid = q.get("id", "?")
            print(f"  [{qid}] {q['question'][:55]}...", end=" ", flush=True)
            result = run_genie_query(space_id, q["question"])

            generated_sql = (result.get("sql") or "").strip()
            expected_asset = q.get("expected_asset", "").upper()
            actual_asset = detect_asset_type(generated_sql) if generated_sql else "NONE"
            correct = actual_asset == expected_asset

            status_str = "PASS" if correct else "FAIL"
            print(f"{status_str} (expected={expected_asset}, got={actual_asset})")
            time.sleep(12)

            mlflow.log_metric(f"q_{qid}_routing", 1.0 if correct else 0.0)
            results.append({
                "question_id": qid,
                "question": q["question"],
                "correct_asset": correct,
                "actual_asset": actual_asset,
                "expected_asset": expected_asset,
                "generated_sql": generated_sql[:200] if generated_sql else None,
            })

        total = len(results)
        correct_count = sum(1 for r in results if r["correct_asset"])
        accuracy = (correct_count / total * 100) if total else 0
        failures = [r for r in results if not r["correct_asset"]]

        mlflow.log_metric("asset_routing_rate", correct_count / total if total else 0)
        mlflow.log_metric("overall_accuracy", accuracy / 100)
        mlflow.log_metric("questions_passed", correct_count)
        mlflow.log_metric("questions_failed", len(failures))

        import tempfile
        import os as _os
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            json.dump(results, tmp, indent=2, default=str)
            tmp_path = tmp.name
        mlflow.log_artifact(tmp_path, artifact_path="evaluation")
        _os.unlink(tmp_path)

        print(f"\n  Accuracy: {correct_count}/{total} ({accuracy:.0f}%)")
        print(f"  Failures: {len(failures)}")
        print(f"  MLflow Run ID: {run.info.run_id}")

    return {
        "iteration": iteration,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "mlflow_run_id": run.info.run_id,
        "overall_accuracy": accuracy,
        "total_questions": total,
        "correct_count": correct_count,
        "failures": [f["question_id"] for f in failures],
        "remaining_failures": [f["question_id"] for f in failures],
        "scores": {"asset_accuracy": accuracy / 100},
    }


# =============================================================================
# Job-Based Evaluation
# =============================================================================

def trigger_evaluation_job(
    space_id: str,
    experiment_name: str,
    iteration: int,
    benchmarks_path: str,
    domain: str,
    target: str = "dev",
    job_name: str = "genie_evaluation_job",
) -> dict:
    """Trigger the genie_evaluation_job via bundle run with parameter overrides.

    Returns:
        dict with run_id (Databricks job run ID) or error.
    """
    cmd = [
        "databricks", "bundle", "run", "-t", target, job_name,
        "--params", f"iteration={iteration}",
    ]

    print(f"\n--- Triggering Evaluation Job (iteration {iteration}) ---")
    print(f"  Command: {' '.join(cmd)}")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        return {"status": "TRIGGER_FAILED", "error": result.stderr, "run_id": None}

    run_id_match = re.search(r"run_id[:\s]+(\d+)", result.stdout)
    run_url_match = re.search(r"(https://[^\s]+)", result.stdout)

    run_id = run_id_match.group(1) if run_id_match else None
    run_url = run_url_match.group(1) if run_url_match else None

    print(f"  Job triggered. Run ID: {run_id}")
    if run_url:
        print(f"  Run URL: {run_url}")

    return {"status": "TRIGGERED", "run_id": run_id, "run_url": run_url, "stdout": result.stdout}


def poll_job_completion(run_id: str, poll_interval: int = 30, max_wait: int = 3600) -> dict:
    """Poll a Databricks job run until it completes or times out.

    Returns:
        dict with life_cycle_state, result_state, notebook_output (if any).
    """
    print(f"\n--- Polling Job Run {run_id} ---")
    start = time.time()

    while time.time() - start < max_wait:
        cmd = ["databricks", "jobs", "get-run", str(run_id), "--output", "json"]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"  Poll error: {result.stderr[:200]}")
            time.sleep(poll_interval)
            continue

        run_data = json.loads(result.stdout)
        state = run_data.get("state", {})
        lifecycle = state.get("life_cycle_state", "UNKNOWN")
        result_state = state.get("result_state", "")

        elapsed = int(time.time() - start)
        print(f"  [{elapsed}s] lifecycle={lifecycle} result={result_state or '-'}")

        if lifecycle == "TERMINATED":
            notebook_output = None
            tasks = run_data.get("tasks", [])
            if tasks:
                task_run_id = tasks[0].get("run_id")
                if task_run_id:
                    out_cmd = ["databricks", "jobs", "get-run-output", str(task_run_id), "--output", "json"]
                    out_result = subprocess.run(out_cmd, capture_output=True, text=True)
                    if out_result.returncode == 0:
                        out_data = json.loads(out_result.stdout)
                        notebook_output = out_data.get("notebook_output", {}).get("result", "")

            return {
                "life_cycle_state": lifecycle,
                "result_state": result_state,
                "notebook_output": notebook_output,
            }

        if lifecycle in ("INTERNAL_ERROR", "SKIPPED"):
            return {
                "life_cycle_state": lifecycle,
                "result_state": state.get("state_message", ""),
                "notebook_output": None,
            }

        time.sleep(poll_interval)

    return {"life_cycle_state": "TIMEOUT", "result_state": "Exceeded max_wait", "notebook_output": None}


def run_evaluation_via_job(
    space_id: str,
    experiment_name: str,
    iteration: int,
    benchmarks_path: str,
    domain: str,
    target: str = "dev",
    model_id: str = None,
) -> dict:
    """Trigger evaluation job, poll for completion, read MLflow results.

    Returns:
        dict compatible with run_evaluation_iteration() output for the
        optimization loop (iteration, overall_accuracy, failures, etc.).
    """
    trigger = trigger_evaluation_job(
        space_id=space_id,
        experiment_name=experiment_name,
        iteration=iteration,
        benchmarks_path=benchmarks_path,
        domain=domain,
        target=target,
    )

    if trigger["status"] != "TRIGGERED" or not trigger.get("run_id"):
        print(f"  ERROR: Job trigger failed: {trigger.get('error', 'unknown')}")
        return {
            "iteration": iteration,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "mlflow_run_id": None,
            "overall_accuracy": 0,
            "total_questions": 0,
            "correct_count": 0,
            "failures": [],
            "remaining_failures": [],
            "scores": {},
            "job_error": trigger.get("error"),
        }

    completion = poll_job_completion(trigger["run_id"])

    if completion["result_state"] != "SUCCESS":
        print(f"  ERROR: Job failed with state: {completion['result_state']}")
        return {
            "iteration": iteration,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "mlflow_run_id": None,
            "overall_accuracy": 0,
            "total_questions": 0,
            "correct_count": 0,
            "failures": [],
            "remaining_failures": [],
            "scores": {},
            "job_error": completion.get("result_state"),
        }

    notebook_output = completion.get("notebook_output")
    if notebook_output:
        try:
            job_result = json.loads(notebook_output)
        except json.JSONDecodeError:
            job_result = {}
    else:
        job_result = {}

    if not job_result:
        _verify_mlflow_tracking()
        latest = query_latest_evaluation(experiment_name, iteration)
        if latest:
            job_result = {
                "run_id": latest["run_id"],
                "overall_accuracy": latest["metrics"].get("overall_accuracy", 0),
                "thresholds_passed": latest["thresholds_passed"],
            }

    overall = job_result.get("overall_accuracy", 0)
    if isinstance(overall, float) and overall <= 1.0:
        overall_pct = overall * 100
    else:
        overall_pct = overall

    return {
        "iteration": iteration,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "mlflow_run_id": job_result.get("run_id"),
        "overall_accuracy": overall_pct,
        "total_questions": job_result.get("questions_total", 0),
        "correct_count": job_result.get("questions_passed", 0),
        "failures": job_result.get("failure_question_ids", []),
        "remaining_failures": job_result.get("failure_question_ids", []),
        "scores": job_result.get("per_judge", {}),
        "thresholds_passed": job_result.get("thresholds_passed", False),
    }


# =============================================================================
# MLflow Query
# =============================================================================

def query_latest_evaluation(experiment_name: str, iteration: int = None) -> dict:
    """Query the latest evaluation run from MLflow for threshold checking."""
    filter_str = "tags.mlflow.runName LIKE 'genie_eval_%'"
    if iteration is not None:
        filter_str = f"tags.mlflow.runName LIKE 'genie_eval_iter{iteration}_%'"

    runs = mlflow.search_runs(
        experiment_names=[experiment_name],
        filter_string=filter_str,
        order_by=["start_time DESC"],
        max_results=1,
    )
    if runs.empty:
        return None
    row = runs.iloc[0]
    return {
        "run_id": row["run_id"],
        "metrics": {k.replace("metrics.", ""): v for k, v in row.items() if k.startswith("metrics.")},
        "thresholds_passed": row.get("metrics.thresholds_passed", 0.0) == 1.0,
    }


# =============================================================================
# CLI Entry Point
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Genie Benchmark Evaluator CLI")
    parser.add_argument("--space-id", required=True, help="Genie Space ID")
    parser.add_argument("--benchmarks", required=True, help="Path to golden queries YAML")
    parser.add_argument("--domain", default="unknown", help="Domain name")
    parser.add_argument("--experiment", default=None, help="MLflow experiment name")
    parser.add_argument("--iteration", type=int, default=1, help="Evaluation iteration number")
    parser.add_argument("--uc-schema", default=None, help="Unity Catalog schema for MLflow datasets/prompts")
    parser.add_argument("--job-mode", action="store_true",
                        help="Run evaluation as Databricks Job instead of inline")
    parser.add_argument("--target", default="dev", help="Bundle target for job mode (default: dev)")
    parser.add_argument("--evaluate-only", action="store_true",
                        help="Run one evaluation and exit (no optimization loop)")
    parser.add_argument("--model-id", default=None,
                        help="LoggedModel ID for MLflow version tracking")

    args = parser.parse_args()

    with open(args.benchmarks) as f:
        all_benchmarks = yaml.safe_load(f)

    if args.domain in all_benchmarks:
        benchmarks = all_benchmarks[args.domain]
    elif "benchmarks" in all_benchmarks:
        benchmarks = all_benchmarks["benchmarks"]
    else:
        benchmarks = all_benchmarks if isinstance(all_benchmarks, list) else []

    if not benchmarks:
        print(f"ERROR: No benchmarks found for domain '{args.domain}'")
        return 1

    experiment_name = args.experiment or f"/genie-optimization/{args.domain}"

    if args.job_mode:
        result = run_evaluation_via_job(
            space_id=args.space_id,
            experiment_name=experiment_name,
            iteration=args.iteration,
            benchmarks_path=args.benchmarks,
            domain=args.domain,
            target=args.target,
            model_id=args.model_id,
        )
    else:
        _verify_mlflow_tracking()
        result = run_evaluation_iteration(
            space_id=args.space_id,
            benchmarks=benchmarks,
            experiment_name=experiment_name,
            iteration=args.iteration,
            uc_schema=args.uc_schema,
            model_id=args.model_id,
        )

    print("\n" + "=" * 60)
    print("Evaluation Complete")
    print("=" * 60)
    print(f"  Iteration:     {result['iteration']}")
    print(f"  Accuracy:       {result['overall_accuracy']:.0f}%")
    print(f"  Total:          {result['total_questions']}")
    print(f"  Passed:         {result['correct_count']}")
    print(f"  Failures:       {result.get('failures', [])}")
    if result.get("mlflow_run_id"):
        print(f"  MLflow Run ID:  {result['mlflow_run_id']}")

    return 0


if __name__ == "__main__":
    exit(main())
