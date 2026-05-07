# Genie Code Overrides — data_product_accelerator

> **Read this file FIRST before following any skill in `data_product_accelerator/skills/`.** The skills folder contains CLI-based patterns written for the Cursor/local development track. This file maps every CLI operation to its Genie Code equivalent using the Databricks Python SDK.

## Terminology: MCP

**Genie prompts under `data_product_accelerator/prompts/` do not use `mcp-appkit-skill`, `DatabricksMCPClient`, or `databricks-mcp`.** They use **`WorkspaceClient`** (`w.jobs`, `w.pipelines`, `w.workspace`, `w.statement_execution`, …) and the helpers in **`workshop-variables.md`**.

| Where you see “MCP” | What it means | Genie action |
|---------------------|----------------|---------------|
| **`mcp-appkit-skill` / `appkit_*` tools** | Optional AppKit helper server | **Out of scope here.** For Apps + Lakebase UI, use **`apps_lakebase/prompts/`** and **`apps_lakebase/gc-prompt-conversion/workshop-variables.md`** (`validate_and_deploy`, `w.apps`, Lakebase SDK). |
| **Genie HTTP MCP** (e.g. `/api/2.0/mcp/genie/{space_id}`) | Databricks Genie / agent tool protocol | Only in **GenAI agent** skills — follow those skills’ REST/SDK patterns; not used for medallion DPA cells. |
| **“MCP tool” in a skill** (e.g. run file on cluster) | IDE / assistant integration (Cursor, etc.) | **Not available in Genie.** Use inline Python + SDK equivalents from this file. |

---

## Section 1: Environment Constraints

Genie Code runs inside Databricks serverless notebooks. The following are **not available** and will fail silently or with cryptic errors if attempted:

| Forbidden | Reason |
|-----------|--------|
| `databricks` CLI | No terminal access |
| `databricks bundle validate/deploy/run` | No Asset Bundle workflow; use SDK `w.jobs.create()` + `write_notebook()` instead |
| `python scripts/*.py` | No local Python execution; run logic inline as notebook cells |
| `bash`, `sh`, `subprocess`, `os.system`, `os.popen`, `shell=True` | No shell |
| `find`, `grep`, `ls`, `cat`, `head` via subprocess | Forbidden; use SDK workspace methods |
| `open("file.yaml")` / `with open(path) as f` | No local filesystem; use `w.workspace.export()` |
| `pip install` without `%` | Use `%pip install` magic (note: restart kernel if installing databricks-sdk or psycopg) |
| `jupyter lab`, `databricks configure --profile` | No local dev; run exploration directly in Genie Code |
| `databricks libraries install --cluster-id` | Use `%pip install <package>` |
| `curl` / `requests` to `localhost` | No local server |
| `git clone`, `git` commands, local filesystem paths | No local filesystem |

---

## Section 2: Global CLI → SDK Override Table

When any skill says to run a CLI command, use this table instead:

### Jobs & Bundles

| CLI Command | Genie Code Override |
|-------------|---------------------|
| `databricks bundle validate` | Skip — jobs created directly via SDK; no bundle needed |
| `databricks bundle deploy` | `w.jobs.create(...)` + `write_notebook()` for each task (see `workshop-variables.md` Job Creation Quick Reference) |
| `databricks bundle run <job_name>` | `run_job_by_name("<keyword>")` from `@data_product_accelerator/gc-prompt-conversion/workshop-variables.md` |
| `databricks bundle run --params '{"key":"val"}'` | `w.jobs.run_now_and_wait(job_id=JOB_ID, notebook_params={"key": "val"})` |
| `databricks jobs list` | `list(w.jobs.list())` |
| `databricks jobs get <job_id>` | `w.jobs.get(job_id=JOB_ID)` |
| `databricks runs get-run-output --run-id <TASK_RUN_ID>` | `w.jobs.get_run_output(run_id=TASK_RUN_ID)` — note: use the **task-level** run_id, not the parent job run_id |

### Pipelines (SDP / DLT)

| CLI Command | Genie Code Override |
|-------------|---------------------|
| `databricks pipelines init` | Create pipeline inline: `w.pipelines.create(...)` — see silver section below |
| `databricks pipelines start-update` | `w.pipelines.start_update(pipeline_id=PIPELINE_ID, full_refresh=False)` |
| `databricks pipelines get-update` | `w.pipelines.get_update(pipeline_id=PIPELINE_ID, update_id=UPDATE_ID)` |
| `databricks pipelines list-events` | `list(w.pipelines.list_pipeline_events(pipeline_id=PIPELINE_ID))` |

### File & Workspace Operations

| CLI Command | Genie Code Override |
|-------------|---------------------|
| `databricks workspace import <path> --file <local>` | `write_file(ws_path, content)` or `write_notebook(ws_path, content)` from `workshop-variables.md` |
| `databricks workspace export <path>` | `base64.b64decode(w.workspace.export(path=WS_PATH).content).decode()` |
| `databricks workspace ls <path>` | `list(w.workspace.list(path=DIR))` |
| `databricks workspace mkdirs <path>` | `w.workspace.mkdirs(path)` |
| `open("file.yaml")` / local file read | `base64.b64decode(w.workspace.export(path=WS_PATH).content).decode()` |
| Write to local file | `write_file(ws_path, content)` — see `workshop-variables.md` |
| `find . -name "*.py"` | `list(w.workspace.list(path=DIR))` filtered by `.object_type` |
| `grep -r "pattern" .` | `w.workspace.export()` each file and search content inline |

### SQL & Warehouses

| CLI Command | Genie Code Override |
|-------------|---------------------|
| `databricks query execute` | `run_sql(sql)` from `workshop-variables.md` |
| `databricks warehouses list` | `list(w.warehouses.list())` |
| `databricks warehouses get <id>` | `w.warehouses.get(id=WAREHOUSE_ID)` |
| `spark.sql(...)` | Preferred for DDL/DML in notebook context |

### Packages & Dependencies

| CLI Command | Genie Code Override |
|-------------|---------------------|
| `pip install <package>` | `%pip install <package>` (in a dedicated cell before imports) |
| `pip install -r requirements.txt` | `%pip install <package1> <package2> ...` (list packages inline) |
| `pip install "gepa>=0.1.0"` | `%pip install "gepa>=0.1.0"` |
| `databricks libraries install --cluster-id ... --pypi-package ...` | `%pip install <package>` |

### Scripts

| Skill Instruction | Genie Code Override |
|-------------------|---------------------|
| `python scripts/validate_bundle.py` | Skip — validate by running `w.jobs.get(job_id=JOB_ID)` and checking task states |
| `python scripts/copy_from_source.py` | Run Bronze clone logic inline as notebook cells; use `write_notebook()` to make it a job task |
| `python scripts/validate_schema.py <catalog> <schema>` | Run validation SQL inline: `spark.sql("DESCRIBE TABLE ...")` |
| `python scripts/setup_dqx.py --catalog ... --schema ...` | Run DQX setup logic inline or write as notebook + `w.jobs.create()` |
| `python scripts/export_genie_space.py <space_id>` | SDK inline: `w.genie.get_space(space_id=SPACE_ID)` |
| `python scripts/import_genie_space.py <space_id>` | SDK inline: `w.genie.update_space(...)` or REST via `w.api_client.do("PUT", ...)` |
| `python scripts/orchestrator.py --...` | Run orchestration logic inline across Genie Code cells |
| `python scripts/benchmark_generator.py --...` | Run benchmark generation inline as cells |
| `bash scripts/monitor_multitask_job.sh <run_id>` | Python polling loop: `while True: s = w.jobs.get_run(run_id).state; ...` |
| `bash scripts/create-skill.sh` | Create files via `write_file()` |
| `bash scripts/organize_docs.sh` | Create folders via `w.workspace.mkdirs()`, write files via `write_file()` |

---

## Section 3: Variable Setup

**Every prompt in this workshop uses these standard variables.** Read and run `@data_product_accelerator/gc-prompt-conversion/workshop-variables.md` first. It defines:

| Helper | Purpose |
|--------|---------|
| `APP_NAME` | User-scoped app name (e.g. `jaiwant-j-booking-app`) |
| `DB_SCHEMA` | PostgreSQL schema name (hyphens → underscores) |
| `REPO_ROOT` | `/Workspace/Users/{email}/v2v-in-geniecode/vibe-coding-workshop-template` |
| `write_file(path, content)` | Write plain files (CSV, YAML, markdown) — creates `ObjectType.FILE`, NOT runnable as notebook job |
| `write_notebook(path, content)` | Write Python notebooks — creates `ObjectType.NOTEBOOK` runnable by `w.jobs.create()` |
| `run_job_by_name(keyword)` | Find job matching `keyword` + `APP_NAME`, run it, poll to completion |
| `run_sql(sql)` | Execute SQL via warehouse and print results |

**CRITICAL file-writing rules:**
- `write_file()` → use for CSV, YAML, markdown, JSON — NOT for notebook job scripts
- `write_notebook()` → use for any `.py` content that a Databricks job will execute; content MUST start with `# Databricks notebook source`
- Notebook path for jobs: strip `/Workspace` prefix: `REPO_ROOT.replace("/Workspace", "", 1)`
- No `.py` extension in notebook paths

---

## Section 4: Skill-Specific Overrides

### `common/databricks-asset-bundles/SKILL.md`

The bundle workflow (`databricks.yml` → `databricks bundle deploy`) is **not used in Genie Code**. The skill's bundle YAML patterns are for reference only.

| Skill instruction | Genie Code override |
|---|---|
| Any `databricks bundle ...` command | Jobs created directly via `w.jobs.create()` + `write_notebook()` — no YAML or CLI needed |
| `databricks bundle generate app ...` | Skip — scaffold notebooks inline as strings via `write_notebook()` |
| `bundle.yml` resource definitions | Reference only — translate to `w.jobs.create()` / `w.pipelines.create()` SDK calls |
| Shared workspace naming (`${bundle.target} ${var.user_prefix}`) | Include `APP_NAME` in all job/pipeline `name:` fields: `f"[{APP_NAME}] Bronze Clone"` |

### `common/databricks-autonomous-operations/SKILL.md`

This skill already has a `variant: genie-code` and uses SDK-only patterns. Its references are directly applicable. Additional notes:

| Skill instruction | Genie Code override |
|---|---|
| `bash scripts/monitor_multitask_job.sh <run_id>` | Python polling loop (see workshop-variables Job Creation Quick Reference) |
| `databricks runs get-run-output --run-id <TASK_RUN_ID>` | `w.jobs.get_run_output(run_id=TASK_RUN_ID)` — use the **task-level** run_id from `run_details.tasks[i].run_id`, not the parent run_id |
| CLI reference files in `references/cli-quick-reference.md` | Use `references/sdk-api-reference.md` instead |

### `silver/00-silver-layer-setup/SKILL.md`

| Skill instruction | Genie Code override |
|---|---|
| `databricks pipelines init` | Create pipeline inline via `w.pipelines.create(...)` |
| `databricks pipelines start-update <pipeline_id>` | `w.pipelines.start_update(pipeline_id=PIPELINE_ID, full_refresh=False)` |
| DLT/SDP pipeline notebooks | `write_notebook(path, content)` — content must start with `# Databricks notebook source` |
| `databricks bundle run silver_dq_setup_job` | `run_job_by_name("silver_dq_setup_job")` |
| `databricks bundle run silver_dlt_pipeline` | `w.pipelines.start_update(pipeline_id=PIPELINE_ID, full_refresh=True)` |

**SDP pipeline notebook — Bronze read pattern:**

Every DLT flow function reading from Bronze MUST use `spark.readStream.table()`. Do NOT use `readChangeFeed=true`. Using `readChangeFeed` raises `[DELTA_MISSING_CHANGE_DATA]` because CDF was enabled on Bronze tables via `ALTER TABLE` after the initial write — so version 0 has no CDF records. Standard streaming reads the full snapshot + future appends without needing CDF history.

```python
# CORRECT — standard Delta streaming
@dlt.table(name="silver_bookings", ...)
def silver_bookings():
    bronze_table = f"`{TARGET_CATALOG}`.`{BRONZE_SCHEMA}`.`bookings`"
    return (
        spark.readStream.table(bronze_table)
        .withColumn("_silver_loaded_at", current_timestamp())
    )

# WRONG — raises DELTA_MISSING_CHANGE_DATA
# spark.readStream.format("delta").option("readChangeFeed", "true").option("startingVersion", 0).table(bronze_table)
```

**SDP pipeline notebook — Liquid clustering vs Z-order (mandatory):**

Workshop Silver tables use **`cluster_by_auto=True`** on `@dlt.table` (Liquid clustering). **Never set `pipelines.autoOptimize.zOrderCols`** — not via `spark.conf.set(...)`, not in `w.pipelines.create(..., configuration={...})`, and not in the pipeline UI. Z-order and Liquid clustering are mutually exclusive; the update fails with:

`DLTAnalysisException: ZORDER BY is not compatible with Liquid Clustering. Please remove pipelines.autoOptimize.zOrderCols`

```python
# FORBIDDEN — do not add “helpful” Z-order hints in the SDP notebook:
# spark.conf.set("pipelines.autoOptimize.zOrderCols", "booking_id")

# OK — keep cluster_by_auto=True; delta table TBLPROPERTIES may include
# delta.autoOptimize.optimizeWrite / delta.autoOptimize.autoCompact (not the same as pipeline zOrderCols)
```

**SDP pipeline notebook — PySpark imports for quarantine / `when` chains:**

Quarantine tables often use `when(...).when(...).otherwise(...)`, `lit(...)`, `col(...)`, `concat_ws`, etc. **Import every symbol the notebook uses** from `pyspark.sql.functions` (and `F` / `types` if needed). A partial import line (e.g. only `current_timestamp, sha2, concat_ws, col`) while the body calls `lit` causes **`NameError: name 'lit' is not defined`** or **“Failed to analyze flow”** during pipeline initialization. Prefer an explicit set such as:

`from pyspark.sql.functions import col, lit, when, current_timestamp, sha2, concat_ws, coalesce` (extend as needed for generated `quarantine_reason` logic).

**Silver pipeline creation pattern — always use the idempotent delete-then-create from Section 6.** Do NOT call `w.pipelines.create()` directly without deleting first — the `target`/`schema` field is immutable and a re-run will either raise `ResourceConflict` or `InvalidParameterValue: Cannot unset 'schema' field`. See the full pattern in the "Create a SDP pipeline" block in Section 6 below.

### `semantic-layer/04-genie-space-export-import-api/SKILL.md`

| Skill instruction | Genie Code override |
|---|---|
| `python scripts/export_genie_space.py <space_id> --output <file>` | `space = w.genie.get_space(space_id=SPACE_ID)` then `write_file(path, json.dumps(space.as_dict(), indent=2))` |
| `python scripts/import_genie_space.py <space_id> --input <file>` | Use `w.api_client.do("PUT", f"/api/2.0/genie/spaces/{SPACE_ID}", body=payload)` |
| `python scripts/validate_against_reference.py` | Run validation logic inline: compare dict keys/values |

### `semantic-layer/05-genie-optimization-orchestrator/SKILL.md` and Workers

| Skill instruction | Genie Code override |
|---|---|
| `python scripts/orchestrator.py --space-id ... --iterations ...` | Run each orchestration step as a separate Genie Code cell |
| `python scripts/benchmark_generator.py --...` | Run benchmark generation inline |
| `python scripts/genie_evaluator.py --...` | Run evaluation inline |
| `python scripts/repeatability_tester.py --...` | Run repeatability tests inline |
| `python scripts/metadata_optimizer.py --...` | Run optimization inline |
| `python scripts/optimization_applier.py --...` | Run applier inline |
| `pip install "gepa>=0.1.0"` | `%pip install "gepa>=0.1.0"` in a dedicated cell before imports |
| `databricks libraries install --cluster-id ... --pypi-package gepa` | `%pip install "gepa>=0.1.0"` |

### `monitoring/02-databricks-aibi-dashboards/SKILL.md`

| Skill instruction | Genie Code override |
|---|---|
| `python scripts/validate_dashboard_queries.py` | Run SQL validation inline: `spark.sql("EXPLAIN ...")` or `run_sql(query)` |
| `python scripts/validate_widget_encodings.py` | Read dashboard JSON via `w.workspace.export()` and validate inline |
| `python scripts/deploy_dashboard.py` | Use Databricks SDK lakeview API: `w.lakeview.publish(dashboard_id=DASHBOARD_ID)` |

### `gold/pipeline-workers/05-schema-validation/SKILL.md`

| Skill instruction | Genie Code override |
|---|---|
| `python scripts/validate_schema.py <catalog> <schema>` | Run validation inline: `spark.sql(f"DESCRIBE TABLE {catalog}.{schema}.{table}")` |

### `admin/self-improvement/SKILL.md`

| Skill instruction | Genie Code override |
|---|---|
| `find /path -name "*.md" -type f` | `list(w.workspace.list(path=DIR))` filtered for files |
| `grep -ri "pattern" /path/` | Export each file via `w.workspace.export()` and search string inline |
| `cat file.md` | `base64.b64decode(w.workspace.export(path=WS_PATH).content).decode()` |
| `mkdir -p path/to/dir` | `w.workspace.mkdirs(path)` |
| `cat << EOF > file.md ... EOF` | `write_file(ws_path, content_string)` |
| `echo "content" >> file` | Read existing content, append, then `write_file()` |

### `exploration/00-adhoc-exploration-notebooks/SKILL.md`

| Skill instruction | Genie Code override |
|---|---|
| `pip install -r requirements.txt` | `%pip install <package1> <package2>` |
| `databricks configure --profile <name>` | Skip — `WorkspaceClient()` uses workspace defaults in Genie Code |
| `jupyter lab` | Skip — run exploration directly in Genie Code notebooks |
| `databricks connect configure` | Skip — Databricks Connect is not needed inside Genie Code; Spark is available natively as `spark` |

---

## Section 5: Session Recovery

If your kernel was restarted or you get `NameError: name 'w' is not defined`, run this block before continuing:

```python
%pip install --upgrade databricks-sdk "psycopg[binary]>=3.0" -q
```

Restart the kernel if prompted (`dbutils.library.restartPython()`), then re-run the standard variable setup from `@data_product_accelerator/gc-prompt-conversion/workshop-variables.md`.

---

## Section 6: Verified Patterns

### Read a workspace file

```python
import base64
content = base64.b64decode(w.workspace.export(path=WS_PATH).content).decode()
```

### List workspace directory

```python
items = list(w.workspace.list(path=f"{REPO_ROOT}/data_product_accelerator/context"))
for item in items:
    print(item.path, item.object_type)
```

### Create and run a job (full pattern)

**Use the `make_job_notebook()` + `create_job()` helpers** from `@data_product_accelerator/gc-prompt-conversion/workshop-variables.md` — they handle the mandatory pip install + restart header, idempotent job replacement, and SDK type wiring.

```python
import time

# 1. Build notebook content with the mandatory job header (pip install + restart + var re-derivation)
body = """
# Your job logic starts here — Python state was wiped by restart, so all
# variables (APP_NAME, DB_SCHEMA, TARGET_CATALOG) are already re-derived
# by the header injected by make_job_notebook().

print(f"Running for catalog={TARGET_CATALOG} schema={DB_SCHEMA}")
# spark.sql(...), psycopg.connect(...), etc.
"""
notebook_source = make_job_notebook(body)

notebook_path = (REPO_ROOT + "/src/my_schema/my_notebook").replace("/Workspace", "", 1)
write_notebook(notebook_path, notebook_source)

# 2. Create the job idempotently (deletes any existing job with the same name)
job_id = create_job(
    "My Job",
    notebook_path,
    base_params={"CATALOG": TARGET_CATALOG, "SCHEMA": "my_schema"},
)

# 3. Run + poll
run = w.jobs.run_now(job_id=job_id)
while True:
    s = w.jobs.get_run(run_id=run.run_id).state
    lc = s.life_cycle_state.value if s.life_cycle_state else "UNKNOWN"
    rs = s.result_state.value if s.result_state else "PENDING"
    print(f"  {lc} | {rs}")
    if lc in ("TERMINATED", "SKIPPED", "INTERNAL_ERROR"):
        break
    time.sleep(15)

if rs != "SUCCESS":
    # Get task-level error — use task.run_id, NOT parent run.run_id
    for task in w.jobs.get_run(run_id=run.run_id).tasks:
        if task.run_id:
            out = w.jobs.get_run_output(run_id=task.run_id)
            if out.error:
                print(f"Task error: {out.error}")
```

### Create a SDP pipeline (idempotent — safe to re-run)

**Always use the `create_pipeline_idempotent()` helper.** Calling `w.pipelines.create()` directly causes:
- `ResourceConflict: pipeline name already used` on a re-run
- `InvalidParameterValue: Cannot unset 'schema' field` if you try to `update()` instead (the `target`/`schema` field is immutable — the only recovery is delete + create)

The helper handles delete-then-create + the `target=` (not `schema=`) parameter quirk + propagation sleep. See `@data_product_accelerator/gc-prompt-conversion/workshop-variables.md` → Helper Quick Reference for the implementation.

```python
import time

# 1. Create the pipeline idempotently (deletes any matching existing pipeline first)
PIPELINE_ID = create_pipeline_idempotent(
    "Silver Layer Pipeline",
    notebook_path,
    TARGET_CATALOG,
    SILVER_SCHEMA,
)

# 2. Start a pipeline update
update = w.pipelines.start_update(pipeline_id=PIPELINE_ID, full_refresh=True)
UPDATE_ID = update.update_id

# 3. Poll for completion
while True:
    ev = w.pipelines.get_update(pipeline_id=PIPELINE_ID, update_id=UPDATE_ID)
    state = ev.update.state.value if ev.update and ev.update.state else "UNKNOWN"
    print(f"  Pipeline: {state}")
    if state in ("COMPLETED", "FAILED", "CANCELED"):
        break
    time.sleep(20)

print(f"\u2713 Pipeline final state: {state}")
```

### Drop schema (safe in workshop — user-scoped schemas)

```python
spark.sql(f"DROP SCHEMA IF EXISTS `{TARGET_CATALOG}`.`{SCHEMA}` CASCADE")
spark.sql(f"CREATE SCHEMA `{TARGET_CATALOG}`.`{SCHEMA}`")
print(f"✓ Schema recreated: {TARGET_CATALOG}.{SCHEMA}")
```

---

## Section 7: Notebook Content Authoring Rules

When writing Python notebook content as a string for `write_notebook()`, follow the mandatory rules below. Violating them will cause the job or pipeline to fail (Silver SDP notebooks must also satisfy Rule 5).

### Rule 1: Always include pip install + restart as the first two cells

Every job notebook MUST start with these two cells before any imports or variable derivation:

```
# Databricks notebook source
# COMMAND ----------
%pip install --upgrade databricks-sdk "psycopg[binary]>=3.0" -q
# COMMAND ----------
dbutils.library.restartPython()
# COMMAND ----------
# All imports and logic start here — Python state is wiped after restart
import psycopg
from databricks.sdk import WorkspaceClient
w = WorkspaceClient()

# Re-derive variables (restart wiped Python state)
email = spark.sql("SELECT current_user()").collect()[0][0]
prefix = email.split("@")[0].replace(".", "-")
parts = prefix.split("-")
APP_NAME = f"{parts[0]}-{parts[-1][0]}-booking-app"[:26]
DB_SCHEMA = APP_NAME.replace("-", "_")
```

**Why:** Job compute has the pre-installed (older) SDK. The `%pip install` run in the Genie Code notebook does NOT carry over to the job's compute. Without this, jobs fail with `AttributeError: 'WorkspaceClient' object has no attribute 'postgres'`.

**After `dbutils.library.restartPython()` all variables are gone — re-derive everything** (`APP_NAME`, `DB_SCHEMA`, catalog names, etc.) in the cell after the restart.

### Rule 2: No backslash escaping inside f-string `{}` expressions

Python <3.12 raises `SyntaxError: f-string expression part cannot include a backslash` if you use `\'`, `\"`, or any backslash inside `{}`.

```python
# BAD — SyntaxError when notebook runs
print(f"\n{\'=\'*60}")
print(f"done: {\"value\"}")

# GOOD — extract to a variable first
sep = "=" * 60
print(f"\n{sep}")
label = "value"
print(f"done: {label}")
```

Same rule applies to same-quote-type inside f-strings on Python <3.12:
```python
# BAD
f"{'some string'}"   # inner quotes same as outer f-string delimiter

# GOOD
s = "some string"
f"{s}"
```

### Rule 4: No `DEFAULT` values in `CREATE TABLE` DDL

The Delta `allowColumnDefaults` feature is **not enabled by default on serverless**. Any `CREATE TABLE` that assigns a `DEFAULT` value to a column raises:

```
[WRONG_COLUMN_DEFAULTS_FOR_DELTA_FEATURE_NOT_ENABLED]
```

This applies to **all layers** — DQ rules table, Silver tables, Gold tables including SCD2 columns (`is_current`, `effective_from`, `effective_to`).

```sql
-- BAD — raises WRONG_COLUMN_DEFAULTS_FOR_DELTA_FEATURE_NOT_ENABLED
CREATE TABLE ... (
    is_current     BOOLEAN   DEFAULT TRUE,
    effective_from TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)

-- GOOD — omit DEFAULT, set values in INSERT/MERGE logic
CREATE TABLE ... (
    is_current     BOOLEAN,
    effective_from TIMESTAMP,
    created_at     TIMESTAMP
)
-- Then in INSERT: INSERT INTO ... VALUES (..., true, current_timestamp(), current_timestamp())
-- Then in MERGE:  WHEN NOT MATCHED THEN INSERT (..., is_current, effective_from) VALUES (..., true, current_timestamp())
```

If the generated DDL includes `DEFAULT`, strip all `DEFAULT ...` clauses before executing.

### Rule: Reserved and forbidden `TBLPROPERTIES` keys (DQ `dq_rules`, Silver, Gold)

Unity Catalog and Delta reserve certain **table property names** for system use. Setting them in `CREATE TABLE ... TBLPROPERTIES (...)` or `ALTER TABLE ... SET TBLPROPERTIES` fails with:

```
[UNSUPPORTED_FEATURE.SET_TABLE_PROPERTY] ... is a reserved table property
```

**Known trap (workshop):** Do **not** add **`'table_type' = 'metadata'`** (or any **`table_type`** value) to tag the `dq_rules` table — **`table_type`** is reserved. The model sometimes invents this key by analogy to `information_schema.tables.table_type`. Use a **non-reserved** custom key instead (e.g. **`'dq_rules_role' = 'metadata'`**, **`'rules_table_kind' = 'centralized_dq'`**) or omit extra tags and keep only `layer`, CDF, and auto-optimize keys aligned with `databricks-table-properties`.

Before finalizing any `write_notebook()` DDL string, scan for **`'table_type'`** inside **`TBLPROPERTIES`** and remove or rename it.

### Rule 5: Silver SDP notebooks — no `pipelines.autoOptimize.zOrderCols` with Liquid clustering

Silver `@dlt.table(..., cluster_by_auto=True)` uses **Liquid clustering**. Do **not** set **`pipelines.autoOptimize.zOrderCols`** anywhere in the SDP notebook (no `spark.conf.set`, no extra pipeline `configuration` keys). Same rule as Section 4 Silver override block — Z-order and Liquid clustering are incompatible.

### Rule 6: Gold merge — source temp view must cover every Gold column used by `MERGE`

Gold tables are defined from **YAML** (often aligned to a wide Lakebase schema). Silver workshop tables are a **narrower** extract. For `MERGE INTO ... WHEN MATCHED THEN UPDATE SET * WHEN NOT MATCHED THEN INSERT *`, Spark resolves columns from the **`USING` relation** (`src_*`). If the Gold table has **`cleaning_fee`** (or any YAML-only column) but the DataFrame behind `src_dim_listing` never added that column, analysis fails with **`[UNRESOLVED_COLUMN.WITH_SUGGESTION]`** pointing at `src` with a short column list.

**Required pattern:**

1. For each Gold column **missing** from the Silver DataFrame, add `lit(None).cast("<exact_sql_type>")` (or a business default) **before** `createOrReplaceTempView`.
2. End with an explicit `.select(...)` listing **all** columns the Gold Delta table expects for that merge, **including** the NULL placeholders.
3. Call `printSchema()` on the source DataFrame once per table before `MERGE` to catch omissions.
4. For **string** Silver business keys (`id`, `listing_id`), use casts consistent with Gold DDL; for prefixed string ids (e.g. `r12`), use `regexp_extract(col("id"), r"(\d+)", 1).cast("bigint")` when the Gold key is numeric.

Canonical booking example: `@data_product_accelerator/gc-prompt-conversion/reference_gold_merge_booking_notebook_body.py`.

---

### Rule 3: Source is always psycopg for `MANAGED_ONLINE_CATALOG`

The `apps_lakebase` source catalog (`{APP_NAME}_catalog`) is a `MANAGED_ONLINE_CATALOG` (Lakebase Autoscaling-backed). Spark reads from serverless compute always raise `FATAL: External authorization failed`. **Never attempt a Spark read from this catalog** — go directly to psycopg using `w.postgres.list_endpoints()` + `w.postgres.generate_database_credential()`.

Resolve **`LAKEBASE_PROJECT_ID`** / **`PG_SCHEMA`** and discover **`ENDPOINT_NAME`** / **`host`** per `@data_product_accelerator/gc-prompt-conversion/lakebase-notebook-connection.md` (not repeated here). Refresh credentials per query (tokens expire after ~1 hour):

```python
cred = w.postgres.generate_database_credential(endpoint=ENDPOINT_NAME)
conn_string = (
    f"host={host} dbname=databricks_postgres user={username} "
    f"password={cred.token} sslmode=require"
)
# Filter SQL with: WHERE table_schema = PG_SCHEMA  (or qualify PG_SCHEMA.table_name)
```
