def _job_match(keyword: str):
    return [
        j for j in w.jobs.list()
        if j.settings and j.settings.name
        and keyword.lower() in j.settings.name.lower()
        and APP_NAME in (j.settings.name or "")
    ]

all_jobs = {j.settings.name: j.job_id for j in w.jobs.list() if j.settings and j.settings.name}
project_jobs = {name: jid for name, jid in all_jobs.items() if APP_NAME in name}

print(f"Jobs found for {APP_NAME}:")
for name, jid in sorted(project_jobs.items()):
    print(f"  OK  {name} (id={jid})")

required = [
    ("bronze", "Bronze clone", _job_match("bronze")),
    ("dq", "Silver DQ setup", _job_match("dq")),
    ("gold setup", "Gold setup", _job_match("gold setup")),
    ("gold merge", "Gold merge", _job_match("gold merge")),
]
missing_jobs = [label for _kw, label, m in required if not m]

pipelines = [
    p for p in w.pipelines.list_pipelines()
    if APP_NAME in (p.name or "") and "silver" in (p.name or "").lower()
]
print(f"\nSilver pipelines matching APP_NAME ({len(pipelines)}):")
for p in pipelines[:15]:
    print(f"  OK  {p.name!r} id={p.pipeline_id}")

missing_pipeline = len(pipelines) == 0

if missing_jobs or missing_pipeline:
    print("\n" + "=" * 60)
    print("COLD START — required resources are missing. Do NOT run Steps 1–5 yet.")
    print("Run these Genie prompts IN ORDER (each creates notebooks/jobs/pipeline via SDK):")
    print("  1. @data_product_accelerator/prompts/extract_from_tables_gc.md")
    print("  2. @data_product_accelerator/prompts/clone-from-source-gc.md")
    print("  3. @data_product_accelerator/prompts/silver-layer-pipelines-gc.md")
    print("  4. @data_product_accelerator/prompts/gold-layer-design-gc.md")
    print("  5. @data_product_accelerator/prompts/gold-layer-pipeline-gc.md")
    print("Then re-run Cell B (Step 0).")
    print("=" * 60)
    if missing_jobs:
        print(f"Missing job categories: {missing_jobs}")
    if missing_pipeline:
        print("Missing: Silver pipeline whose name contains APP_NAME and 'silver'.")
else:
    print("\nStep 0 PASS — all required jobs and at least one Silver pipeline are present.")
