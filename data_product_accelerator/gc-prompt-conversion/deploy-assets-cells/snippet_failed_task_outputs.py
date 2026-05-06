failed_run_id = run.run_id  # parent run from the last run_job_by_name call

run_detail = w.jobs.get_run(run_id=failed_run_id)
failed_tasks = [
    t for t in (run_detail.tasks or [])
    if t.state and t.state.result_state and t.state.result_state.value == "FAILED"
]

for t in failed_tasks:
    print(f"FAILED TASK: {t.task_key}")
    print(f"  Error: {t.state.state_message}")
    print(f"  URL:   {t.run_page_url}")
    output = w.jobs.get_run_output(run_id=t.run_id)
    if output.error:
        print(f"  API error: {output.error}")
    if output.notebook_output and output.notebook_output.result:
        print(f"  Notebook output: {output.notebook_output.result}")
