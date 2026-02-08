# CLI vs SDK Quick Reference Table

Side-by-side reference for common operations using CLI and Python SDK.

| Scenario | CLI | SDK |
|----------|-----|-----|
| Check job status | `databricks jobs get-run <ID> --output json \| jq '.state'` | `w.jobs.get_run(run_id=ID).state` |
| Get failed tasks | `... \| jq '.tasks[] \| select(.state.result_state=="FAILED")'` | `[t for t in run.tasks if t.state.result_state == "FAILED"]` |
| Get task output | `databricks jobs get-run-output <TASK_RUN_ID> --output json` | `w.jobs.get_run_output(run_id=TASK_RUN_ID)` |
| Check pipeline | `databricks pipelines get <ID> --output json` | `w.pipelines.get(pipeline_id=ID)` |
| Pipeline events | `databricks pipelines list-pipeline-events <ID>` | `w.pipelines.list_pipeline_events(pipeline_id=ID)` |
| Check cluster | `databricks clusters get <ID> --output json` | `w.clusters.get(cluster_id=ID)` |
| Cluster events | `databricks clusters events <ID> --output json` | `w.clusters.events(cluster_id=ID)` |
| Check monitor | N/A | `w.quality_monitors.get(table_name="...")` |
| Deploy | `databricks bundle deploy -t <target>` | N/A |
| Run job | `databricks bundle run -t <target> <job>` | `w.jobs.run_now(job_id=ID)` |
| Cancel job | `databricks jobs cancel-run <RUN_ID>` | `w.jobs.cancel_run(run_id=ID)` |
| Re-authenticate | `databricks auth login --host <url> --profile <name>` | N/A |
| Warehouse status | `databricks warehouses get <ID> --output json` | `w.warehouses.get(id=ID)` |
| Start warehouse | N/A | `w.warehouses.start(id=ID).result()` |
| List recent runs | `databricks jobs list-runs --job-id <JID> --output json` | `list(w.jobs.list_runs(job_id=JID))` |
| Export notebook | `databricks workspace export <path> --format SOURCE` | N/A |
| Pipeline errors | `... list-pipeline-events <PID> --output json \| jq '[.events[] \| select(.level=="ERROR")]'` | `[e for e in events if e.level == "ERROR"]` |
| Start pipeline | `databricks pipelines start-update <PID>` | `w.pipelines.start_update(pipeline_id=PID)` |
| List bundle resources | `databricks bundle validate 2>&1 \| head -50` | N/A |
| Destroy resources | `databricks bundle destroy -t <target> --auto-approve` | N/A |
