# Genie Code Helpers — `data_product_accelerator` (Lakehouse)

Single-file helper library for the V2V Lakehouse Genie Code workflow. V2V genie-code prompts `@`-reference this file. Steps 10-14 use **Section 1**. Step 23 uses **Sections 1 + 2**.

---

## Section 1 — Bootstrap (run once per session; re-run after any kernel restart)

**Forbid-list (do not use in Genie Code):** `databricks` CLI / `databricks bundle …`; `subprocess` / `os.system` / `shell=True`; `npm` / `npx` / `node`; `pip` without `%`; `open(local_path)`, `/tmp/...`, paths outside `/Workspace`; `localhost`, `curl`, `psql`; `git clone`. Use the SDK helpers below.

```python
# Cell 1
%pip install --upgrade databricks-sdk -q
```

```python
# Cell 2
dbutils.library.restartPython()
```

```python
# Cell 3 — variables + helpers (paste the entire block)
import base64, time
from datetime import timedelta
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.workspace import ImportFormat, Language
from databricks.sdk.service.jobs import Task, NotebookTask, JobEnvironment
from databricks.sdk.service.compute import Environment
from databricks.sdk.service.pipelines import PipelineLibrary, NotebookLibrary
from databricks.sdk.service.sql import StatementState

w = WorkspaceClient()
email = spark.sql("SELECT current_user()").collect()[0][0]
prefix = email.split("@")[0].replace(".", "-"); parts = prefix.split("-")
APP_NAME = f"{parts[0]}-{parts[-1][0]}-booking-app"[:26]
DB_SCHEMA = APP_NAME.replace("-", "_")
TARGET_CATALOG = "donotdelete_vibe_coding_catalog"   # workshop default
REPO_ROOT = f"/Workspace/Users/{email}/v2v-in-geniecode/vibe-coding-workshop-template"

def read_file(path):
    """Read a workspace file (CSV/YAML/JSON/md/notebook source). Returns the decoded string."""
    return base64.b64decode(w.workspace.export(path=path).content).decode()

def write_file(path, content):
    """Plain workspace file (CSV/YAML/JSON/md). NOT job-runnable."""
    parent = "/".join(path.split("/")[:-1]); w.workspace.mkdirs(parent)
    w.workspace.import_(path=path, content=base64.b64encode(content.encode()).decode(),
                        format=ImportFormat.AUTO, overwrite=True)

def write_notebook(path, content):
    """Notebook (job-runnable). Content MUST start with '# Databricks notebook source'. Path has NO .py."""
    parent = "/".join(path.split("/")[:-1]); w.workspace.mkdirs(parent)
    w.workspace.import_(path=path, content=base64.b64encode(content.encode()).decode(),
                        format=ImportFormat.SOURCE, language=Language.PYTHON, overwrite=True)

def run_sql(sql, warehouse_id=None):
    """Execute SQL via warehouse, return rows. Picks first warehouse if id omitted."""
    wid = warehouse_id or next(w.warehouses.list()).id
    r = w.statement_execution.execute_statement(statement=sql, warehouse_id=wid, wait_timeout="30s")
    if r.status.state != StatementState.SUCCEEDED: raise RuntimeError(f"SQL: {r.status.error}")
    return r.result.data_array or []

def run_job_by_name(keyword, timeout_minutes=30):
    """Find a job whose name contains `keyword` AND APP_NAME, run, poll. Returns the Run."""
    matches = [j for j in w.jobs.list() if j.settings and j.settings.name
               and keyword.lower() in j.settings.name.lower() and APP_NAME in (j.settings.name or "")]
    if not matches: raise ValueError(f"No job matching '{keyword}' for {APP_NAME}.")
    print(f"Running: {matches[0].settings.name}")
    run = w.jobs.run_now_and_wait(job_id=matches[0].job_id, timeout=timedelta(minutes=timeout_minutes))
    print(f"  {run.state.result_state.value}  {run.run_page_url}")
    return run

def make_job_notebook(body, extra_imports=""):
    """Wrap a body string with the mandatory job-notebook header (pip install + restart + var re-derivation).
    Required because job compute does NOT inherit the parent notebook's pip installs."""
    return ("# Databricks notebook source\n# COMMAND ----------\n"
            "%pip install --upgrade databricks-sdk -q\n# COMMAND ----------\n"
            "dbutils.library.restartPython()\n# COMMAND ----------\n"
            "import base64\nfrom databricks.sdk import WorkspaceClient\n"
            f"{extra_imports.rstrip() + chr(10) if extra_imports else ''}"
            "\nw = WorkspaceClient()\n"
            "email = spark.sql(\"SELECT current_user()\").collect()[0][0]\n"
            "prefix = email.split(\"@\")[0].replace(\".\", \"-\"); parts = prefix.split(\"-\")\n"
            "APP_NAME = f\"{parts[0]}-{parts[-1][0]}-booking-app\"[:26]\n"
            "DB_SCHEMA = APP_NAME.replace(\"-\", \"_\")\n"
            "TARGET_CATALOG = \"donotdelete_vibe_coding_catalog\"\n# COMMAND ----------\n" + body)

def create_job(name_suffix, notebook_path, base_params=None, task_key=None):
    """Single-task notebook job, idempotent (delete-then-create). notebook_path: NO /Workspace prefix, NO .py."""
    job_name = f"[dev {APP_NAME}] {name_suffix}"
    w.workspace.get_status(path=notebook_path)
    for j in w.jobs.list():
        if j.settings and j.settings.name == job_name: w.jobs.delete(job_id=j.job_id)
    tk = task_key or name_suffix.lower().replace(" ", "_").replace("-", "_")
    job = w.jobs.create(name=job_name,
        environments=[JobEnvironment(environment_key="default", spec=Environment(client="1"))],
        tasks=[Task(task_key=tk, environment_key="default",
                    notebook_task=NotebookTask(notebook_path=notebook_path, base_parameters=base_params or {}))])
    print(f"OK job {job_name} (id={job.job_id})")
    return job.job_id

def create_pipeline_idempotent(name_suffix, notebook_path, catalog, target):
    """SDP pipeline, idempotent. `target` is immutable so delete-then-create. Use `target=`, not `schema=`."""
    pipeline_name = f"[dev {APP_NAME}] {name_suffix}"
    w.workspace.get_status(path=notebook_path)
    keyword = name_suffix.split()[0]
    existing = list(w.pipelines.list_pipelines(filter=f"name LIKE '%{APP_NAME}%{keyword}%'"))
    for p in existing: w.pipelines.delete(pipeline_id=p.pipeline_id)
    if existing: time.sleep(5)
    p = w.pipelines.create(name=pipeline_name,
        libraries=[PipelineLibrary(notebook=NotebookLibrary(path=notebook_path))],
        catalog=catalog, target=target, serverless=True, continuous=False, development=True)
    print(f"OK pipeline {pipeline_name} (id={p.pipeline_id})")
    return p.pipeline_id

print(f"APP_NAME={APP_NAME}  DB_SCHEMA={DB_SCHEMA}  TARGET_CATALOG={TARGET_CATALOG}")
```

### Traps (read once — these are the Genie-Code-only landmines)

1. Job notebook content MUST start with `%pip install` + `dbutils.library.restartPython()` + variable re-derivation. Use `make_job_notebook(body)`. Without this, jobs fail with `AttributeError: 'WorkspaceClient' object has no attribute '...'`.
2. Notebook paths: NO `/Workspace` prefix, NO `.py` extension. Strip with `REPO_ROOT.replace("/Workspace", "", 1)`.
3. F-strings: no backslashes inside `{}`, no same-quote-type inside `{}` (Python <3.12 `SyntaxError`).
4. Use SDK type wrappers (`Task`, `NotebookTask`, `JobEnvironment(spec=Environment(...))`), never raw dicts.
5. `w.workspace.get_status(path=...)` BEFORE `w.jobs.create(...)` — fail fast if the notebook is missing.
6. Gold MERGE: `src_*` source temp views MUST `.select(...)` every Gold column the merge references, with `lit(None).cast("<sql_type>")` for any YAML-only Gold column missing from Silver. Otherwise `[UNRESOLVED_COLUMN.WITH_SUGGESTION]` on `src`.
7. No `DEFAULT` clauses in `CREATE TABLE` DDL on serverless (`WRONG_COLUMN_DEFAULTS_FOR_DELTA_FEATURE_NOT_ENABLED`). Set values in INSERT/MERGE.
8. Reserved `TBLPROPERTIES` keys: never `'table_type'` (UC reserves it). Use `'layer'='bronze'` or `'dq_rules_role'='metadata'`.
9. SDP / DLT notebooks: `cluster_by_auto=True` on `@dlt.table`. Never set `pipelines.autoOptimize.zOrderCols` (incompatible with Liquid clustering — `DLTAnalysisException`).
10. Read Bronze with `spark.readStream.table(bronze_table)`, NOT `readChangeFeed=True` (raises `[DELTA_MISSING_CHANGE_DATA]` because CDF was enabled via `ALTER TABLE`).
11. Import every `pyspark.sql.functions` symbol the SDP notebook uses (`col, lit, when, current_timestamp, sha2, concat_ws, coalesce, ...`). Partial imports → `NameError` at pipeline init.

---

## Section 2 — Deploy-Assets Cells (V2V Step 23 only)

Run **after** Section 1 and **after** V2V Steps 12-14 have created the jobs and Silver SDP pipeline. Order: A2 → B → C → D → E → F → G → H. Self-contained Python cells.

### Cell A2 — Constants

```python
# TARGET_CATALOG = "your_other_catalog"   # uncomment to override workshop default
BRONZE_SCHEMA = f"{DB_SCHEMA}_bronze"
SILVER_SCHEMA = f"{DB_SCHEMA}_silver"
GOLD_SCHEMA   = f"{DB_SCHEMA}_gold"
# Allowlists (NEVER add `src_*` merge staging names — those are temp views, not Delta tables)
BRONZE_TABLES = ("bookings", "listings", "reviews")
GOLD_TABLES   = ("dim_listing", "fact_booking", "fact_review")
print(f"{TARGET_CATALOG}  bronze={BRONZE_SCHEMA}  silver={SILVER_SCHEMA}  gold={GOLD_SCHEMA}")
```

### Cell B — Discover (cold-start gate; runs nothing)

```python
def _match(kw):
    return [j for j in w.jobs.list() if j.settings and j.settings.name
            and kw.lower() in j.settings.name.lower() and APP_NAME in (j.settings.name or "")]

required = [("bronze","Bronze clone"), ("dq","Silver DQ"), ("gold setup","Gold setup"), ("gold merge","Gold merge")]
missing_jobs = [label for kw, label in required if not _match(kw)]
pipelines = [p for p in w.pipelines.list_pipelines()
             if APP_NAME in (p.name or "") and "silver" in (p.name or "").lower()]
print(f"Jobs: {sorted(j.settings.name for j in w.jobs.list() if j.settings and j.settings.name and APP_NAME in j.settings.name)}")
print(f"Silver pipelines: {[(p.name, p.pipeline_id) for p in pipelines]}")
if missing_jobs or not pipelines:
    raise RuntimeError(f"COLD START — missing: jobs={missing_jobs}, pipeline_missing={not pipelines}. "
                       f"Complete V2V Steps 10-14 first, then re-run Cell B.")
print("Step 0 PASS")
```

### Cell C — Bronze clone

```python
run = run_job_by_name("bronze", timeout_minutes=45)
if run.state.result_state.value != "SUCCESS": raise RuntimeError(f"Bronze: {run.state.result_state.value}")
```

### Cell D — Silver DQ setup

```python
run = run_job_by_name("dq", timeout_minutes=30)
if run.state.result_state.value != "SUCCESS": raise RuntimeError(f"DQ: {run.state.result_state.value}")
```

### Cell E — Silver pipeline (full refresh)

> `full_refresh=True` is **mandatory**: Bronze re-clone in Cell C invalidates incremental checkpoints. Without it, every `silver_*` flow fails with stale-state errors.

```python
import time
pipelines = [p for p in w.pipelines.list_pipelines()
             if APP_NAME in (p.name or "") and "silver" in (p.name or "").lower()]
if not pipelines: raise ValueError(f"No Silver pipeline for {APP_NAME}. Run V2V Step 13.")

canonical = f"[dev {APP_NAME}] Silver Layer Pipeline"
chosen = next((p for p in pipelines if p.name == canonical), None) \
         or (pipelines[0] if len(pipelines) == 1 else None)
if chosen is None:
    print("Multiple matches — using first sorted; edit this cell to override:")
    for i, p in enumerate(pipelines): print(f"  [{i}] {p.name} id={p.pipeline_id}")
    chosen = sorted(pipelines, key=lambda p: p.name or "")[0]

pid = chosen.pipeline_id
print(f"FULL REFRESH: {chosen.name} (id={pid})")
update = w.pipelines.start_update(pipeline_id=pid, full_refresh=True)
while True:
    latest = (w.pipelines.get(pipeline_id=pid).latest_updates or [None])[0]
    raw = latest.state if latest else None
    state = getattr(raw, "value", raw) if raw is not None else "UNKNOWN"
    print(f"  {state}")
    if state in ("COMPLETED", "FAILED", "CANCELED"): break
    time.sleep(30)
if state != "COMPLETED":
    for e in [e for e in w.pipelines.list_pipeline_events(pipeline_id=pid)
              if "ERROR" in str(getattr(e, "level", e))][:10]:
        print(f"  ERROR: {getattr(e, 'event_type', '')}: {getattr(e, 'message', '')}")
    raise RuntimeError(f"Silver pipeline state={state}")
```

### Cell F — Gold setup

```python
run = run_job_by_name("gold setup", timeout_minutes=30)
if run.state.result_state.value != "SUCCESS": raise RuntimeError(f"Gold setup: {run.state.result_state.value}")
```

### Cell G — Gold merge

```python
run = run_job_by_name("gold merge", timeout_minutes=60)
if run.state.result_state.value != "SUCCESS": raise RuntimeError(f"Gold merge: {run.state.result_state.value}")
```

### Cell H — Verification (allowlisted; never iterate raw `SHOW TABLES`)

```python
def cnt(c, s, t): return spark.sql(f"SELECT COUNT(*) c FROM `{c}`.`{s}`.`{t}`").collect()[0].c

bronze = {t: cnt(TARGET_CATALOG, BRONZE_SCHEMA, t) for t in BRONZE_TABLES}
print("Bronze:", bronze)

dq = cnt(TARGET_CATALOG, SILVER_SCHEMA, "dq_rules")
silver_streaming = [x.tableName for x in spark.sql(f"SHOW TABLES IN {TARGET_CATALOG}.{SILVER_SCHEMA}").collect()
                    if x.tableName.startswith("silver_")]
silver = {t: cnt(TARGET_CATALOG, SILVER_SCHEMA, t) for t in sorted(silver_streaming)}
print(f"Silver: dq_rules={dq}, {silver}")

gold = {t: cnt(TARGET_CATALOG, GOLD_SCHEMA, t) for t in GOLD_TABLES}
print("Gold:", gold)

constraints = spark.sql(f"""
SELECT table_name, constraint_name, constraint_type
FROM {TARGET_CATALOG}.information_schema.table_constraints
WHERE table_schema = '{GOLD_SCHEMA}' ORDER BY table_name, constraint_type""").collect()
pk_n = sum(1 for c in constraints if c.constraint_type == "PRIMARY KEY")
fk_n = sum(1 for c in constraints if c.constraint_type == "FOREIGN KEY")
print(f"Gold constraints: PK={pk_n}, FK={fk_n}")

checks = [
    ("Bronze (3 allowlisted)",  all(v >= 0 for v in bronze.values())),
    ("Silver streaming (>=3)",  len(silver_streaming) >= 3),
    ("DQ rules > 0",            dq > 0),
    ("Gold (3 allowlisted)",    all(v >= 0 for v in gold.values())),
    ("Gold PK (3)",             pk_n == 3),
    ("Gold FK (2)",             fk_n == 2),
]
for label, ok in checks: print(f"  {'PASS' if ok else 'FAIL'}  {label}")
print("ALL PASS" if all(ok for _, ok in checks) else "SOME FAILED")
```

### Failed-task diagnostics (paste after any failed Cell C/D/F/G)

Use **task-level** `run_id` from `tasks[i].run_id`, NOT the parent run. `get_run_output` returns `{}` on the parent.

```python
for t in (w.jobs.get_run(run_id=run.run_id).tasks or []):
    if t.state and t.state.result_state and t.state.result_state.value == "FAILED":
        out = w.jobs.get_run_output(run_id=t.run_id)
        print(f"FAILED {t.task_key}: {t.state.state_message}")
        print(f"  url={t.run_page_url}")
        if out.error: print(f"  api_error={out.error}")
        if out.notebook_output and out.notebook_output.result: print(f"  notebook={out.notebook_output.result}")
```
