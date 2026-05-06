# Troubleshooting Reference — Data Product Accelerator

**Purpose:** Single source of truth for diagnosing errors across all pipeline steps. When any error occurs, consult this file FIRST before improvising a fix.

**How to use:** Match the error message or symptom below. Apply the fix exactly as described.

---

## Global Directives

Rules that apply to EVERY step. Follow proactively — do not wait for errors.

### No subprocess / shell commands

| Forbidden | Use Instead |
|-----------|-------------|
| `subprocess.run()`, `subprocess.Popen()`, `os.system()`, `os.popen()` | Nothing — shell access does not exist in Genie Code |
| `shell=True` in any call | Nothing — no shell |
| `grep`, `find`, `ls`, `cat`, `head` via subprocess | Use SDK alternatives below |
| List directory contents | `list(w.workspace.list(path=DIR))` — returns `ObjectInfo` with `.path` and `.object_type` |
| Read a workspace file | `base64.b64decode(w.workspace.export(path=WS_PATH).content).decode()` |
| Write a workspace file | Use `write_file()` helper from `@workshop-variables.md` |
| Search for a file by name | Use `w.workspace.list()` on the known directory — do NOT use subprocess `find` |

### SDK Setup

| Rule | Detail |
|------|--------|
| Run pip install first | `%pip install --upgrade databricks-sdk "psycopg[binary]>=3.0" -q` before importing |
| Restart kernel only if needed | Only if `AttributeError: 'WorkspaceClient' object has no attribute 'postgres'` AFTER pip install — then run `dbutils.library.restartPython()`, re-run pip install, and proceed |
| `ERROR: pip's dependency resolver ... googleapis-common-protos ... protobuf` | **Non-fatal warning — ignore it.** Both `databricks-sdk` and `psycopg` installed successfully. Proceed to the next cell. Only restart if the next cell raises `AttributeError: 'WorkspaceClient' object has no attribute 'postgres'`. |
| File writes require mkdirs | Call `w.workspace.mkdirs(parent)` before any `w.workspace.import_()` |
| Use `write_file()` helper | Defined in `@workshop-variables.md` — handles mkdirs and base64 automatically |

### APP_NAME Derivation

| Rule | Detail |
|------|--------|
| Format | `{firstname}-{last_initial}-booking-app` — single letter for last name. Example: `jaiwant.jonathan` → `jaiwant-j-booking-app`, NOT `jaiwant-jonathan-booking-app` |
| Max length | 26 chars, lowercase letters/numbers/hyphens only. No underscores. |
| DB_SCHEMA | `APP_NAME.replace("-", "_")` (e.g. `jaiwant_j_booking_app`) |

---

## Step: Extract from Tables (`extract_from_tables_gc.md`)

| Symptom | Cause | Fix |
|---------|-------|-----|
| `AttributeError: 'WorkspaceClient' object has no attribute 'postgres'` | SDK too old or already loaded before upgrade | `%pip install --upgrade databricks-sdk -q` then `dbutils.library.restartPython()`, re-run pip install, then import |
| `ModuleNotFoundError: No module named 'psycopg'` | psycopg not installed | `%pip install "psycopg[binary]>=3.0" -q` (no restart needed — new packages are available immediately) |
| `NotFound: endpoint id not found` | Hardcoded endpoint name incorrect (e.g. `ep-primary`) | Discover dynamically: resolve **`LAKEBASE_PROJECT_ID`** first (see `lakebase-notebook-connection.md`), then `list(w.postgres.list_endpoints(parent=f"projects/{LAKEBASE_PROJECT_ID}/branches/production"))[0].name` |
| `list_endpoints` returns empty for `projects/{APP_NAME}/...` | **Lakebase project id ≠ formula `APP_NAME`** (e.g. app folder `jaiwant-jo-stayfindr` vs `jaiwant-j-booking-app`) | Follow **`LAKEBASE_PROJECT_ID`** resolution in `@data_product_accelerator/gc-prompt-conversion/lakebase-notebook-connection.md` (scan `apps_lakebase/`) or set `LAKEBASE_PROJECT_ID` manually |
| 0 rows from `information_schema.columns` | Wrong schema filter, empty schema (DDL not run), or wrong `dbname` | Use **`dbname=databricks_postgres`** and **`WHERE table_schema = PG_SCHEMA`** where **`PG_SCHEMA = LAKEBASE_PROJECT_ID.replace('-', '_')`**. Deploy the AppKit app once if tables were never created |
| `FATAL: database "..." does not exist` | App not yet deployed — DDL runs on first startup | Deploy the apps_lakebase app first |
| `password authentication failed` | Token expired (1-hour lifetime) | Call `w.postgres.generate_database_credential(endpoint=ENDPOINT_NAME)` again before reconnecting |
| `TimeoutExpired` on subprocess call | AI used subprocess (forbidden) | See Global Directives above — use `w.workspace.list()` or `w.workspace.export()` instead |

---

## Step: Clone from Source / Bronze Layer (`clone-from-source-gc.md`)

### Job creation (Bronze clone job)

Do **not** maintain a second full `w.jobs.create(...)` snippet in this file — it duplicates [`workshop-variables.md`](workshop-variables.md) and drifts from the helpers.

1. Run the setup block from **`@data_product_accelerator/gc-prompt-conversion/workshop-variables.md`** so `REPO_ROOT`, `APP_NAME`, `TARGET_CATALOG`, `w`, and helpers exist.
2. `notebook_path = (REPO_ROOT + "/src/jaiwant_j_booking_app_bronze/clone_from_source").replace("/Workspace", "", 1)` — no `.py` suffix; verify with `w.workspace.get_status(path=notebook_path)`.
3. Prefer **`create_job(name_suffix="Bronze Clone", notebook_path=notebook_path, base_params={})`** — or copy the **Job Creation Quick Reference** table and example in **`workshop-variables.md`** (`spec=Environment(client="1")` from `databricks.sdk.service.compute`, never raw dicts for `spec`).

### Error Table

| Symptom | Cause | Fix |
|---------|-------|-----|
| `AttributeError: 'dict' object has no attribute 'as_dict'` | Raw dict passed where SDK type expected (e.g. `spec={"client": "1"}`) | Use `spec=Environment(client="1")` from `databricks.sdk.service.compute`. Same applies to `new_settings` in `w.jobs.reset()` — use `JobSettings(...)` not a dict. |
| `Unable to access the notebook "...clone_from_source.py"` | Notebook path includes `.py` extension — workspace strips it for notebooks | Use path WITHOUT `.py`: derive as `(REPO_ROOT + "/path/notebook_name").replace("/Workspace","",1)` |
| `Unable to access the notebook` — path doesn't exist | Notebook file was never written to workspace | The `write_file()` cell must run BEFORE job creation. Verify first: `w.workspace.get_status(path=notebook_path)` |
| `'is not a notebook'` / `INTERNAL_ERROR` on job run | Notebook was saved as `ObjectType.FILE` using `write_file()` — jobs cannot execute FILE type | Delete the file and re-save with `write_notebook()` (uses `ImportFormat.SOURCE` + `Language.PYTHON`). Content must start with `# Databricks notebook source`. |
| `BadRequest: The zip archive contains no items` | `ImportFormat.SOURCE` used without specifying `language=Language.PYTHON` | Always specify both: `format=ImportFormat.SOURCE, language=Language.PYTHON`. Use `write_notebook()` helper which handles this correctly. |
| `FATAL: External authorization failed` (Spark read of source catalog) | `MANAGED_ONLINE_CATALOG` (`jaiwant-j-booking-app_catalog`) blocks Spark reads from serverless — always fails | **Do not retry with Spark.** Use psycopg only — connection + resolution: `@data_product_accelerator/gc-prompt-conversion/lakebase-notebook-connection.md`; clone flow: `@data_product_accelerator/prompts/clone-from-source-gc.md`. |
| `NotFound: Project with name 'projects/jaiwant-j-booking-app' not found` (Bronze clone job) | Clone notebook calls `list_endpoints` for **`projects/{APP_NAME}`** but the real Lakebase project id **differs** from workshop `APP_NAME`; the API **raises** `NotFound` (not an empty list) | **`@data_product_accelerator/gc-prompt-conversion/lakebase-notebook-connection.md`** — resolution block (`try`/`except` on `_endpoints_for(APP_NAME)`, per-directory scan, `list_projects` fallback). Then re-`write_notebook` for `clone_from_source` and re-run the job. |
| `RuntimeError: No endpoints for projects/.../branches/production, and no app folder under .../apps_lakebase with a Lakebase project` (Bronze clone job) | Resolution loop hit **`NotFound`** inside **`_endpoints_for(d)`** and a broad **`except` cleared all candidates** | Same as above — match **`lakebase-notebook-connection.md`** (list dirs first; **`try`/`except` per candidate** only). |
| `FATAL: database "jaiwant_j_booking_app" does not exist` (or similar) during psycopg connect | Wrong **`dbname`** (e.g. **`dbname={DB_SCHEMA}`**) | **`@data_product_accelerator/gc-prompt-conversion/lakebase-notebook-connection.md`** — Key Details: **`dbname=databricks_postgres`**. |
| `ArrowInvalid` / `Rescaling Decimal128 value would cause data loss` during Bronze `createDataFrame` | Postgres **`numeric`** for coordinates mapped to a narrow **`DecimalType`** | **`lakebase-notebook-connection.md`** Key Details row “Bronze clone: PG `numeric` → Spark”; **`clone-from-source-gc.md`** CRITICAL block. |
| `AttributeError: 'WorkspaceClient' object has no attribute 'postgres'` inside job run | Job compute has old pre-installed SDK — the Genie Code `%pip install` does not carry over | Rewrite the notebook via `write_notebook()`. Notebook MUST start with: cell 1 `%pip install --upgrade databricks-sdk "psycopg[binary]>=3.0" -q`, cell 2 `dbutils.library.restartPython()`. All imports and variable derivation MUST come after the restart cell. |
| `SyntaxError: f-string expression part cannot include a backslash` in job run | Backslash-escaped quotes (`\'`) used inside `{}` in a notebook f-string (Python <3.12) | Extract to a variable: `sep = "="*60; print(f"\n{sep}")` instead of `print(f"\n{\'=\'*60}")`. Same applies to same-quote-type inside f-strings. |
| `Table or view not found` on source schema | Source catalog `jaiwant-j-booking-app_catalog` not accessible (endpoint scaled to zero) | Wake the endpoint first via psycopg connect, or wait 30s and retry |
| `Schema 'jaiwant_j_booking_app_bronze' already exists` | Prior run left the schema | `spark.sql("DROP SCHEMA IF EXISTS donotdelete_vibe_coding_catalog.jaiwant_j_booking_app_bronze CASCADE")` |
| `DELTA_TABLE_ALREADY_EXISTS` on clone | Tables from a prior run | Drop and recreate the schema (see above) |
| CDF not enabled on Bronze tables | Delta **`CLONE`** does not copy source TBLPROPERTIES **or** the clone notebook skipped post-write **`ALTER TABLE`** | This workshop Bronze uses psycopg + **`createDataFrame`** + **`ALTER TABLE ... SET TBLPROPERTIES`** — ensure the clone notebook sets CDF (and related props) after each write. If you used **`CLONE`** in another path, re-apply **`ALTER TABLE`** or rebuild. |

---

## All Layers: Delta DDL Constraints

| Symptom | Cause | Fix |
|---------|-------|-----|
| `[WRONG_COLUMN_DEFAULTS_FOR_DELTA_FEATURE_NOT_ENABLED]` on `CREATE TABLE` | DDL uses `DEFAULT` column values (e.g. `is_current BOOLEAN DEFAULT TRUE`, `created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()`); feature not enabled on serverless | Remove ALL `DEFAULT ...` clauses from every `CREATE TABLE` DDL across Silver (DQ rules table), Gold (dimension/fact tables, SCD2 columns `is_current`, `effective_from`, `effective_to`). Set values explicitly in `INSERT`/`MERGE` logic instead. Rewrite the notebook and re-run the job. See Section 7 Rule 4 of `@GENIE-CODE-OVERRIDES.md`. |

---

## Step: Silver Layer (`silver-layer-pipelines-gc.md`)

| Symptom | Cause | Fix |
|---------|-------|-----|
| `dq_rules table not found` during DLT pipeline | DQ setup job not run first | Run `silver_dq_setup_job` BEFORE starting the DLT pipeline — the pipeline reads rules from this table |
| `ResourceConflict: pipeline name '...' is already used by another pipeline` | Your own prior run left a pipeline with the same name — `APP_NAME` is already in the name so this is NOT a cross-attendee collision | Use the idempotent delete-then-create pattern: `existing = list(w.pipelines.list_pipelines(filter=f"name LIKE '%{APP_NAME}%Silver%'"))`, delete each with `w.pipelines.delete(pipeline_id=p.pipeline_id)`, `time.sleep(5)`, then create fresh. **Do NOT call `w.pipelines.update()` as a workaround** — see next row. See Section 6 of `@GENIE-CODE-OVERRIDES.md` for the full pattern. |
| `InvalidParameterValue: Specified 'schema' field is illegal. Reason: Cannot unset 'schema' field once it's defined in the pipeline spec` | `w.pipelines.update()` was called on an existing pipeline — the `target`/`schema` field is immutable and can never be changed via update | Cannot update — must delete and recreate. Use the idempotent delete-then-create pattern from Section 6 of `@GENIE-CODE-OVERRIDES.md`. |
| `EXPECTATIONS_FAILED` — records quarantined | DQ rule threshold too strict or source data has issues | Check the DQ rules table — adjust thresholds or fix source data in Bronze |
| All **`silver_*`** flows **FAILED** / pipeline update **FAILED** with "failed more than 2 times"; **flow_progress** events repeat with little exception text | **Stale streaming checkpoints** after **Bronze re-clone or rebuild**, or incremental update incompatible with new Bronze table versions | Run **`w.pipelines.start_update(pipeline_id=..., full_refresh=True)`** (default in `@data_product_accelerator/prompts/deploy-assets-gc.md` Cell E after Bronze). If still failing: verify SDP reads Bronze with **`spark.readStream.table(...)`** only — see `[DELTA_MISSING_CHANGE_DATA]` row; then delete + recreate pipeline (Section 6 of `@GENIE-CODE-OVERRIDES.md`). |
| `[DELTA_MISSING_CHANGE_DATA] Error getting change data for range [0, N]` | The SDP pipeline notebook used `readChangeFeed=true` but Bronze tables had CDF enabled via `ALTER TABLE` after the initial write — so version 0 has no CDF records | Rewrite the SDP pipeline notebook: replace `spark.readStream.format("delta").option("readChangeFeed", "true")...` with `spark.readStream.table(bronze_table)` in every DLT flow function. See Section 4 of `@GENIE-CODE-OVERRIDES.md` for the correct pattern. Delete + recreate the pipeline (idempotent pattern from Section 6), then re-run with `full_refresh=True`. |
| Silver pipeline fails to read Bronze with CDF | SDP notebook is using `readChangeFeed=true` but CDF was enabled after the initial Bronze write | Switch to standard streaming: use `spark.readStream.table(bronze_table)` — do NOT use `readChangeFeed`. See `[DELTA_MISSING_CHANGE_DATA]` row above. |
| `DLTAnalysisException: ZORDER BY is not compatible with Liquid Clustering` / `Please remove pipelines.autoOptimize.zOrderCols` | Workshop tables use `cluster_by_auto=True` (Liquid clustering). Setting **`pipelines.autoOptimize.zOrderCols`** (via `spark.conf.set`, pipeline `configuration`, or UI) enables Z-order, which conflicts with Liquid clustering | Remove every `pipelines.autoOptimize.zOrderCols` / Z-order config. Keep `cluster_by_auto=True` and normal Delta table properties (`delta.autoOptimize.optimizeWrite`, `delta.autoOptimize.autoCompact`) only. Rewrite notebook, delete + recreate pipeline, `start_update(..., full_refresh=True)`. See Section 4 (`silver/00-silver-layer-setup`) of `@GENIE-CODE-OVERRIDES.md`. |
| `NameError: name 'lit' is not defined` (or vague **Failed to analyze flow** on quarantine) | SDP notebook uses `lit` / `when` / `otherwise` in `quarantine_reason` but **`pyspark.sql.functions` import omits `lit`** (or other symbols) | Add missing imports, e.g. `from pyspark.sql.functions import col, lit, when, current_timestamp, ...` matching all usages. Re-`write_notebook`, delete + recreate pipeline, full refresh. See Section 4 (Silver) of `@GENIE-CODE-OVERRIDES.md`. |
| **Failed to resolve flow:** `'catalog.schema.silver_*_quarantine'` (three-part UC name) | **`@dlt.table(name=...)`** or **`dlt.read_stream("...")`** used a full Unity Catalog path as the flow name; Direct Publishing resolves flows by **short** names only | Use `name="silver_bookings_quarantine"` and `dlt.read_stream("silver_bookings")`, not `donotdelete_....silver_bookings`. Re-`write_notebook`, delete + recreate pipeline. |
| `databricks bundle deploy` command not found | No CLI in Genie Code | Use `w.jobs.create()` + `w.jobs.run_now()` — no CLI/bundle needed |
| `InvalidParameterValue: Invalid filter expression: level = "ERROR"` or `event_type="flow_progress"` | `w.pipelines.list_pipeline_events()` does not accept any `filter=` expressions | Remove the `filter` parameter entirely and filter in Python: `[e for e in w.pipelines.list_pipeline_events(pipeline_id=PIPELINE_ID) if str(e.level) == "EventLevel.ERROR"]` |
| `InvalidParameterValue` on `list_pipeline_events` when using `order_by=` or unsupported kwargs | The REST/SDK contract for `list_pipeline_events` is narrow — extra parameters often fail | Call `list(w.pipelines.list_pipeline_events(pipeline_id=PIPELINE_ID))` without `order_by` (and drop other kwargs unless documented for your SDK version); sort or filter in Python if needed |

---

## Step: Gold Layer (`gold-layer-design-gc.md`, `gold-layer-pipeline-gc.md`)

| Symptom | Cause | Fix |
|---------|-------|-----|
| Schema CSV not found at `context/booking_app_Schema.csv` | `extract_from_tables_gc.md` not run yet | Run the extract step first to generate the schema CSV |
| YAML schema files missing | `gold-layer-design-gc.md` not run yet | Run the design step first — it generates the YAML files used by the pipeline step |
| `[UNRESOLVED_COLUMN.WITH_SUGGESTION] 'X' cannot be resolved. Did you mean one of: [Y, Z, ...]` | INSERT column name was written from memory instead of the YAML spec (e.g. `effective_date` vs `_loaded_at`, `day_of_year` vs `day_name`, `month_num` vs `month_number`) | Before writing INSERT: `print([c['name'] for c in core_specs['table_name']['columns']])` — use ONLY the printed names. If some columns were written wrong and data is already in the table, `ALTER TABLE ... ADD COLUMNS` won't help for renamed columns — fix the INSERT statement instead. |
| `[UNRESOLVED_COLUMN.WITH_SUGGESTION]` on **`cleaning_fee`** / other YAML-only columns during **Gold MERGE** | The `USING` temp view (`src_dim_listing`, etc.) was built **without** columns that exist on the Gold Delta table but **not** in Silver; `MERGE ... INSERT *` / `UPDATE *` resolves those names from **src** | For every Gold-only column, add `lit(None).cast("<type>")` **before** `createOrReplaceTempView`, include it in the **final** `.select(...)`, then `printSchema()` to verify. Compare with `@data_product_accelerator/gc-prompt-conversion/reference_gold_merge_booking_notebook_body.py`. |
| Genie blocks execution: **unsafe** / **mutates workspace** when calling **`write_notebook()`** | Genie Code sandbox treats `w.workspace.import_` as a restricted mutation when combined with other code in the same cell | Split: (1) run Spark/SQL only; (2) second cell or next turn with **only** `write_notebook(path, make_job_notebook(body))`; if still blocked, paste notebook source into workspace UI import, then `create_job` / `run_now` in a jobs-only snippet. |
| `[DELTA_NOT_NULL_CONSTRAINT_VIOLATED] NOT NULL constraint violated for column: X` | `NULL` was inserted into a NOT NULL FK surrogate key column whose referenced dimension is not in the 5 core tables (e.g. `location_sk`) | Check NOT NULL columns first: `[c['name'] for c in core_specs['table']['columns'] if not c.get('nullable', True)]`. For FK columns referencing unpopulated dimensions, use `CAST(0 AS BIGINT) as location_sk` as a placeholder. Never insert `NULL` for a NOT NULL column. |
| `FOREIGN KEY constraint` error on table creation | FK referenced before parent table created | Create dimension tables first, then fact tables — enforce FK dependency order |
| MERGE FAILED — duplicate key violation | Duplicate records in Silver | Add `ROW_NUMBER() OVER (PARTITION BY pk ORDER BY updated_at DESC) = 1` dedup before MERGE |
| `Schema 'jaiwant_j_booking_app_gold' already exists` | Prior run | DROP CASCADE and recreate — user-specific schema, safe to drop |

---

## Step: Deploy Assets (`deploy-assets-gc.md`)

| Symptom | Cause | Fix |
|---------|-------|-----|
| Expected jobs NOT FOUND in workspace | Bundle not deployed yet | Ask workshop admin to run `databricks bundle deploy -t dev` — you cannot deploy from Genie Code |
| `w.jobs.run_now_and_wait()` raises timeout | Job ran longer than expected | Increase `timeout=timedelta(minutes=XX)` — Bronze clone ~30m, Gold merge ~60m |
| Job FAILED — need error details | Need task-level output | Get the `run_id` from `run.tasks[i].run_id` (task-level), then `w.jobs.get_run_output(run_id=task_run_id)` |
| Silver pipeline shows **FAILED** — **`dq_rules` missing** / "table not found" in events | DQ setup job not run before pipeline | Run Silver DQ setup (**deploy-assets** Cell D / `run_job_by_name("dq")`) before Cell E |
| Silver pipeline **FAILED** — all **`silver_*`** flows fail, often after **Bronze re-clone** | Incremental pipeline state / checkpoints out of sync with new Bronze | Use **`start_update(..., full_refresh=True)`** (default Cell E in **deploy-assets-gc**). See Silver table row "All silver_* flows FAILED" above |
| Verification SQL returns 0 rows | Pipeline ran but no data flowed | Check Bronze tables first — if empty, re-run the clone job |
| `statement_execution` warehouse not found | No available warehouse ID | Use `next(w.warehouses.list()).id` to get any running warehouse |

---

## Quick Reference: SDK Alternatives to Shell Commands

Run **`@data_product_accelerator/gc-prompt-conversion/workshop-variables.md`** setup first so **`REPO_ROOT`**, **`w`**, and **`write_file()`** exist. For Genie constraints, see the **Genie Code Constraints** table there (same rules as Global Directives above).

```python
# List files under the workshop repo (adjust subpath as needed)
for obj in w.workspace.list(path=f"{REPO_ROOT}/data_product_accelerator/prompts"):
    print(obj.path, obj.object_type)

# Read a workspace file
import base64
p = f"{REPO_ROOT}/data_product_accelerator/gc-prompt-conversion/troubleshooting_gc.md"
content = base64.b64decode(w.workspace.export(path=p).content).decode()

# Write a plain file — prefer write_file() from workshop-variables
write_file(f"{REPO_ROOT}/some_folder/output.csv", csv_content_string)

# List jobs (large workspaces may need pagination on w.jobs.list())
names = {j.settings.name: j.job_id for j in w.jobs.list() if j.settings and j.settings.name}
print(names)

# Run and wait — or use run_job_by_name("Bronze", ...) from workshop-variables
from datetime import timedelta
run = w.jobs.run_now_and_wait(job_id=JOB_ID, timeout=timedelta(minutes=30))
print(run.state.result_state)
```

> **Paths:** `REPO_ROOT` from workshop-variables is usually `/Workspace/Users/<email>/v2v-in-geniecode/vibe-coding-workshop-template`. Some workspaces use the same tree under `/Users/<email>/...` **without** a `/Workspace` prefix for notebook job paths — use the prefix that matches `w.workspace.get_status` and your existing jobs.
