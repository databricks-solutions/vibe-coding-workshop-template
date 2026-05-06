# Workshop Variables & Helpers

Standard variable setup and file-writing helper for all Genie Code workshop prompts. Run this block at the start of every prompt (or after a kernel restart).

## Genie Code Constraints (Global — Apply to Every Step)

NEVER use any of the following — they will hang, time out, or fail silently:

| Forbidden | Use Instead |
|-----------|-------------|
| `subprocess.run()`, `subprocess.Popen()`, `os.system()`, `os.popen()` | Nothing — shell access does not exist in Genie Code |
| `shell=True` in any call | Nothing — no shell |
| `grep`, `find`, `ls`, `cat`, `head` via subprocess | Use SDK alternatives below |
| Reading files from local filesystem paths | `base64.b64decode(w.workspace.export(path=WS_PATH).content).decode()` |
| Searching for files by name | `list(w.workspace.list(path=DIR))` — returns `ObjectInfo` with `.path` and `.object_type` |
| Writing files | Use the `write_file()` helper defined below — handles mkdirs and base64 automatically |

## Variables

| Variable | Derivation | Example |
|----------|-----------|---------|
| `APP_NAME` | `{firstname}-{lastinitial}-booking-app` (max 26 chars) | `jaiwant-j-booking-app` |
| `DB_SCHEMA` | `APP_NAME` with hyphens replaced by underscores | `jaiwant_j_booking_app` |
| `TARGET_CATALOG` | Shared Unity Catalog for workshop data (Genie prompts) | `donotdelete_vibe_coding_catalog` |
| `REPO_ROOT` | `/Workspace/Users/{email}/v2v-in-geniecode/vibe-coding-workshop-template` | |
| `APP_BASE` | `{REPO_ROOT}/apps_lakebase/{APP_NAME}` | |

**Lakebase vs `APP_NAME`:** The Databricks App / Lakebase **project id** may differ from formula `APP_NAME` (e.g. `jaiwant-jo-stayfindr`). Prompts that connect with **`w.postgres`** must resolve **`LAKEBASE_PROJECT_ID`** and **`PG_SCHEMA`** per `@data_product_accelerator/gc-prompt-conversion/lakebase-notebook-connection.md` — do not assume `list_endpoints(parent=f"projects/{APP_NAME}/branches/production")` is non-empty. Keep using **`APP_NAME`** / **`DB_SCHEMA`** for job names and paths unless a prompt explicitly overrides them.

## Setup Code

```python
import base64
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.workspace import ImportFormat

w = WorkspaceClient()

email = spark.sql("SELECT current_user()").collect()[0][0]
prefix = email.split("@")[0].replace(".", "-")
parts = prefix.split("-")
APP_NAME = f"{parts[0]}-{parts[-1][0]}-booking-app"[:26]
DB_SCHEMA = APP_NAME.replace("-", "_")
TARGET_CATALOG = "donotdelete_vibe_coding_catalog"

REPO_ROOT = f"/Workspace/Users/{email}/v2v-in-geniecode/vibe-coding-workshop-template"
APP_BASE = f"{REPO_ROOT}/apps_lakebase/{APP_NAME}"

def write_file(path, content):
    """Write a plain file (CSV, YAML, markdown, JSON). Creates ObjectType.FILE — NOT runnable as a notebook job."""
    parent = "/".join(path.split("/")[:-1])
    w.workspace.mkdirs(parent)
    w.workspace.import_(
        path=path,
        content=base64.b64encode(content.encode()).decode(),
        format=ImportFormat.AUTO,
        overwrite=True,
    )
    print(f"✓ Wrote {path.split('/')[-1]}")

def write_notebook(path, content):
    """Write a Python notebook (ObjectType.NOTEBOOK) that can be run by a Databricks job.
    Content MUST start with '# Databricks notebook source'.
    Use this instead of write_file() for any script that will be executed by w.jobs.create().
    Path should NOT have .py extension — notebooks are stored without it."""
    from databricks.sdk.service.workspace import Language
    parent = "/".join(path.split("/")[:-1])
    w.workspace.mkdirs(parent)
    w.workspace.import_(
        path=path,
        content=base64.b64encode(content.encode()).decode(),
        format=ImportFormat.SOURCE,
        language=Language.PYTHON,
        overwrite=True,
    )
    print(f"✓ Wrote notebook {path.split('/')[-1]}")

def run_job_by_name(keyword, timeout_minutes=30):
    """Find and run a job whose name contains both `keyword` and `APP_NAME`.
    Raises ValueError if no matching job is found.
    Returns the completed Run object."""
    import time
    from datetime import timedelta
    matches = [
        j for j in w.jobs.list()
        if j.settings and j.settings.name
        and keyword.lower() in j.settings.name.lower()
        and APP_NAME in (j.settings.name or "")
    ]
    if not matches:
        raise ValueError(f"No job matching '{keyword}' found for {APP_NAME} — create it first via the relevant prompt")
    job = matches[0]
    print(f"Running: {job.settings.name} (id={job.job_id})")
    run = w.jobs.run_now_and_wait(job_id=job.job_id, timeout=timedelta(minutes=timeout_minutes))
    print(f"  Result: {run.state.result_state.value}  URL: {run.run_page_url}")
    return run

def run_sql(sql, warehouse_id=None):
    """Execute a SQL statement via the SQL warehouse and print results.
    If warehouse_id is omitted, uses the first available warehouse."""
    from databricks.sdk.service.sql import StatementState
    wid = warehouse_id or next(w.warehouses.list()).id
    result = w.statement_execution.execute_statement(
        statement=sql,
        warehouse_id=wid,
        wait_timeout="30s",
    )
    if result.status.state == StatementState.SUCCEEDED:
        for row in result.result.data_array or []:
            print(row)
    else:
        print(f"SQL Error: {result.status.error}")

def make_job_notebook(body, extra_imports=""):
    """Wrap a Python body string with the mandatory job notebook header.

    Job compute uses the pre-installed (older) SDK and does NOT inherit
    %pip installs from the Genie Code parent notebook. Every job notebook
    MUST start with: pip install (cell 1), restartPython (cell 2), then
    re-derive variables (cell 3 — Python state is wiped after restart).

    Args:
        body: Python logic for the notebook (executed AFTER restart).
              Must use \\\"\\\\n\\\" for newlines if assembled inline.
        extra_imports: optional newline-joined extra import lines
                       (e.g. 'from pyspark.sql.types import *').

    Returns the full notebook source ready for write_notebook().
    """
    header = '''# Databricks notebook source
# COMMAND ----------
%pip install --upgrade databricks-sdk "psycopg[binary]>=3.0" -q
# COMMAND ----------
dbutils.library.restartPython()
# COMMAND ----------
import base64
import psycopg
from databricks.sdk import WorkspaceClient
'''
    if extra_imports:
        header += extra_imports.rstrip() + "\n"
    header += '''
w = WorkspaceClient()

# Re-derive variables (restart wiped Python state)
email = spark.sql("SELECT current_user()").collect()[0][0]
prefix = email.split("@")[0].replace(".", "-")
parts = prefix.split("-")
APP_NAME = f"{parts[0]}-{parts[-1][0]}-booking-app"[:26]
DB_SCHEMA = APP_NAME.replace("-", "_")
TARGET_CATALOG = "donotdelete_vibe_coding_catalog"

# COMMAND ----------
'''
    return header + body

def create_job(name_suffix, notebook_path, base_params=None, task_key=None):
    """Create a single-task notebook job idempotently.

    Deletes any existing job whose name exactly matches before creating.
    Verifies the notebook exists at notebook_path first (raises if missing).

    Args:
        name_suffix: descriptive name; full job name becomes
                     "[dev {APP_NAME}] {name_suffix}".
        notebook_path: workspace path with NO /Workspace prefix and NO .py.
        base_params: optional dict of notebook parameters.
        task_key: optional task_key; defaults to slugified name_suffix.

    Returns the new job_id.
    """
    from databricks.sdk.service.jobs import Task, NotebookTask, JobEnvironment
    from databricks.sdk.service.compute import Environment

    job_name = f"[dev {APP_NAME}] {name_suffix}"
    w.workspace.get_status(path=notebook_path)  # raises if missing

    for j in w.jobs.list():
        if j.settings and j.settings.name == job_name:
            w.jobs.delete(job_id=j.job_id)
            print(f"  Deleted existing job: {job_name} (id={j.job_id})")

    tk = task_key or name_suffix.lower().replace(" ", "_").replace("-", "_")
    job = w.jobs.create(
        name=job_name,
        environments=[JobEnvironment(environment_key="default", spec=Environment(client="1"))],
        tasks=[Task(
            task_key=tk,
            environment_key="default",
            notebook_task=NotebookTask(
                notebook_path=notebook_path,
                base_parameters=base_params or {},
            ),
        )],
    )
    print(f"\u2713 Created job: {job_name} (id={job.job_id})")
    return job.job_id

def create_pipeline_idempotent(name_suffix, notebook_path, catalog, target):
    """Create an SDP pipeline idempotently.

    Deletes any existing pipeline whose name matches "%{APP_NAME}%{first word
    of name_suffix}%" first. Required because the target/schema field is
    immutable after creation — w.pipelines.update() cannot change it, so
    delete-then-create is the only safe path.

    Args:
        name_suffix: descriptive name; full pipeline name becomes
                     "[dev {APP_NAME}] {name_suffix}".
        notebook_path: workspace path with NO /Workspace prefix and NO .py.
        catalog: target catalog (e.g. TARGET_CATALOG).
        target: target schema (NOT 'schema' — the SDK parameter is 'target').

    Returns the new pipeline_id.
    """
    from databricks.sdk.service.pipelines import PipelineLibrary, NotebookLibrary
    import time

    pipeline_name = f"[dev {APP_NAME}] {name_suffix}"
    w.workspace.get_status(path=notebook_path)  # raises if missing

    keyword = name_suffix.split()[0]  # e.g. "Silver" from "Silver Layer Pipeline"
    existing = list(w.pipelines.list_pipelines(
        filter=f"name LIKE '%{APP_NAME}%{keyword}%'"
    ))
    for p in existing:
        w.pipelines.delete(pipeline_id=p.pipeline_id)
        print(f"  Deleted existing pipeline: {p.name} (id={p.pipeline_id})")
    if existing:
        time.sleep(5)  # let deletion propagate

    pipeline = w.pipelines.create(
        name=pipeline_name,
        libraries=[PipelineLibrary(notebook=NotebookLibrary(path=notebook_path))],
        catalog=catalog,
        target=target,
        serverless=True,
        continuous=False,
        development=True,
    )
    print(f"\u2713 Created pipeline: {pipeline_name} (id={pipeline.pipeline_id})")
    return pipeline.pipeline_id

print(f"APP_NAME:       {APP_NAME}")
print(f"DB_SCHEMA:      {DB_SCHEMA}")
print(f"TARGET_CATALOG: {TARGET_CATALOG}")
print(f"REPO_ROOT:      {REPO_ROOT}")
```

## Helper Quick Reference

| Helper | Purpose | Replaces |
|--------|---------|----------|
| `write_file(path, content)` | Plain workspace file (CSV/YAML/JSON) | `databricks workspace import` |
| `write_notebook(path, content)` | Workspace notebook for jobs | n/a — must be NOTEBOOK type |
| `make_job_notebook(body)` | Wrap body with pip install + restart + variable re-derivation | ~25 lines of inline boilerplate per notebook |
| `create_job(name_suffix, notebook_path, params)` | Idempotent single-task notebook job | `JobEnvironment(...) + Task(...) + NotebookTask(...)` boilerplate (~20 lines) |
| `create_pipeline_idempotent(name_suffix, notebook_path, catalog, target)` | Idempotent SDP pipeline (delete + create — schema field immutable) | ~30 lines of inline boilerplate + ResourceConflict handling |
| `run_job_by_name(keyword)` | Find job by name + APP_NAME, run, poll | `databricks bundle run` |
| `run_sql(sql)` | Execute SQL via warehouse | `databricks query execute` |

## Session Recovery

If your kernel was restarted or you get `NameError`, run:

```python
%pip install --upgrade databricks-sdk "psycopg[binary]>=3.0" -q
```

Then restart the kernel (`dbutils.library.restartPython()`) and re-run the setup code above.

## Job Creation Quick Reference

Key rules for creating Databricks jobs via SDK in Genie Code:

| Rule | Detail |
|------|--------|
| Use `write_notebook()` for job scripts | `write_file()` creates `ObjectType.FILE` — jobs cannot run it. Use `write_notebook()` for any script that a job will execute. |
| Notebook content header | Content MUST start with `# Databricks notebook source` for `write_notebook()` to work |
| **Job notebooks must start with pip install + restart** | First cell: `%pip install --upgrade databricks-sdk "psycopg[binary]>=3.0" -q`. Second cell: `dbutils.library.restartPython()`. All imports and variable derivation MUST come after the restart — Python state is wiped. Without this, jobs fail with `AttributeError: 'WorkspaceClient' object has no attribute 'postgres'`. |
| **Re-derive all variables after restart** | `dbutils.library.restartPython()` wipes Python state. Re-derive `APP_NAME`, `DB_SCHEMA`, catalog names, etc. in the cell after the restart — do not rely on outer notebook variables. |
| **No backslash in f-string `{}` inside notebook content** | Python <3.12: `f"\n{\'=\'*60}"` raises `SyntaxError`. Use a variable: `sep = "="*60; f"\n{sep}"`. Also avoid same-quote-type inside f-string expressions. |
| **MANAGED_ONLINE_CATALOG source — always psycopg** | The apps_lakebase source catalog blocks Spark reads from serverless (`External authorization failed`). Use `w.postgres.list_endpoints()` + `w.postgres.generate_database_credential()` directly. |
| Always use SDK types | Never pass raw dicts — use `Task()`, `NotebookTask()`, `JobEnvironment()`, `JobSettings()` |
| `JobEnvironment.spec` type | `spec=Environment(client="1")` from `databricks.sdk.service.compute` — NOT `spec={"client": "1"}` |
| Notebook path prefix | Strip `/Workspace` from `REPO_ROOT`: `REPO_ROOT.replace("/Workspace", "", 1)` |
| Notebook path extension | No `.py` extension — workspace stores notebooks without it |
| Verify before job creation | `w.workspace.get_status(path=notebook_path)` — raises if missing |

For single-task notebook jobs, **prefer `create_job(name_suffix, notebook_path)`** defined above instead of inlined `w.jobs.create(...)`. Custom multi-task graphs or polling loops: see **`GENIE-CODE-OVERRIDES.md` Section 7** and **`deploy-assets-gc.md`** exemplar cells.
