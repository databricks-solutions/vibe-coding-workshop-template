run = run_job_by_name("bronze", timeout_minutes=45)
rs = run.state.result_state.value if run.state and run.state.result_state else None
if rs != "SUCCESS":
    raise RuntimeError(f"Bronze clone did not succeed: {rs}. Fix upstream (Lakebase IDs, clone notebook) then re-run. See troubleshooting below.")
