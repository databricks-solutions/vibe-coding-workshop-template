import time

pipelines = [
    p for p in w.pipelines.list_pipelines()
    if APP_NAME in (p.name or "") and "silver" in (p.name or "").lower()
]
if not pipelines:
    raise ValueError(
        f"No Silver pipeline found for APP_NAME={APP_NAME!r}. "
        "Run silver-layer-pipelines-gc.md first."
    )

canonical = f"[dev {APP_NAME}] Silver Layer Pipeline"
chosen = next((p for p in pipelines if p.name == canonical), None)
if chosen is None and len(pipelines) == 1:
    chosen = pipelines[0]
if chosen is None and len(pipelines) > 1:
    print("Multiple Silver pipelines matched — listing candidates (prefer editing pipeline names to match canonical):")
    for i, p in enumerate(pipelines):
        print(f"  [{i}] {p.name!r} id={p.pipeline_id}")
    chosen = sorted(pipelines, key=lambda p: p.name or "")[0]
    print(f"WARNING: Using pipeline {chosen.name!r} id={chosen.pipeline_id}. If wrong, delete stray pipelines or rename, then re-run this cell.")

if chosen is None:
    raise ValueError("Could not select a Silver pipeline.")

pid = chosen.pipeline_id
print(f"Starting FULL REFRESH for Silver pipeline: {chosen.name!r} id={pid}")
update = w.pipelines.start_update(pipeline_id=pid, full_refresh=True)
print(f"  Update ID: {update.update_id}  Pipeline ID: {pid}")

while True:
    pipeline = w.pipelines.get(pipeline_id=pid)
    latest = pipeline.latest_updates[0] if pipeline.latest_updates else None
    raw_state = latest.state if latest else None
    state = getattr(raw_state, "value", raw_state) if raw_state is not None else "UNKNOWN"
    print(f"  Pipeline state: {state}")
    if state in ("COMPLETED", "FAILED", "CANCELED"):
        break
    time.sleep(30)

if state != "COMPLETED":
    events = list(w.pipelines.list_pipeline_events(pipeline_id=pid))
    errors = [e for e in events if "ERROR" in str(getattr(e, "level", e))]
    for e in errors[:10]:
        print(f"  ERROR: {getattr(e, 'event_type', '')}: {getattr(e, 'message', '')}")
    raise RuntimeError(f"Silver pipeline ended with state={state!r}, expected COMPLETED.")
