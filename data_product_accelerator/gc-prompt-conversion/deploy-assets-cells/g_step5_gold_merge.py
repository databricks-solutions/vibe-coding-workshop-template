run = run_job_by_name("gold merge", timeout_minutes=60)
rs = run.state.result_state.value if run.state and run.state.result_state else None
if rs != "SUCCESS":
    raise RuntimeError(f"Gold merge did not succeed: {rs}. See troubleshooting below.")
