run = run_job_by_name("dq", timeout_minutes=30)
rs = run.state.result_state.value if run.state and run.state.result_state else None
if rs != "SUCCESS":
    raise RuntimeError(f"Silver DQ setup did not succeed: {rs}. See troubleshooting below.")
