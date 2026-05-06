run = run_job_by_name("gold setup", timeout_minutes=30)
rs = run.state.result_state.value if run.state and run.state.result_state else None
if rs != "SUCCESS":
    raise RuntimeError(f"Gold setup did not succeed: {rs}. See troubleshooting below.")
