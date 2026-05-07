# GC Prompt Header — Standard Preamble

**Read this BEFORE following any prompt in `data_product_accelerator/prompts/`.** It consolidates the standard environment, error-handling, and skill-reference rules that apply to every Genie Code prompt in this workshop.

**Cross-component:** Databricks **Apps / AppKit + Lakebase** (UI app) live under **`apps_lakebase/prompts/`** — SDK-only Genie path; see **`apps_lakebase/gc-prompt-conversion/gc-prompt-header.md`** and **`apps_lakebase/gc-prompt-conversion/workshop-variables.md`**. This header governs **data product** prompts only.

---

## CLI Overrides

`@data_product_accelerator/gc-prompt-conversion/GENIE-CODE-OVERRIDES.md` — read FIRST. Apply all CLI overrides before following any skill instruction. The skills folder under `data_product_accelerator/skills/` was authored for the Cursor/local CLI track and contains many `databricks` CLI calls. The overrides file maps every CLI operation to its Genie Code SDK equivalent.

---

## Error-Handling Protocol

> **On ANY error:** STOP and read `@data_product_accelerator/gc-prompt-conversion/troubleshooting_gc.md`. Match the error message or symptom in the tables. Apply the fix exactly as described. Do NOT improvise a workaround before checking the troubleshooting reference.

If the error is not in the troubleshooting catalog, capture the full error text and ask the user before guessing.

---

## Skills required (every prompt)

- `@data_product_accelerator/gc-prompt-conversion/workshop-variables.md` — `w`, `REPO_ROOT`, `APP_NAME`, `DB_SCHEMA`, `TARGET_CATALOG`, `write_file` / `write_notebook`, `run_job_by_name`, `run_sql`, `make_job_notebook`, `create_job`, `create_pipeline_idempotent`

**Load only when the active prompt mentions Lakebase/psycopg:**

- `@data_product_accelerator/gc-prompt-conversion/lakebase-notebook-connection.md` — project id resolution, `_endpoints_for`/`NotFound` handling, `dbname`/`PG_SCHEMA`

**Load only for `gold-layer-pipeline-gc.md`:**

- `@data_product_accelerator/gc-prompt-conversion/reference_gold_merge_booking_notebook_body.py` — booking merge canon (YAML column order, Silver subset, placeholders)

---

## Environment

**Genie Code on Databricks workspace (serverless).** No CLI, no terminal, no local filesystem, no `npm`, no Node.js.

**NEVER use:**
- `subprocess`, `subprocess.run()`, `subprocess.Popen()`, `os.system()`, `os.popen()` — no shell access
- `shell=True` in any call — no shell
- `grep`, `find`, `ls`, `cat`, `head` via subprocess — use SDK alternatives below
- `open(local_path)` / file paths outside `/Workspace` — no local filesystem
- `pip install` without `%` — use `%pip install` magic in a dedicated cell

**Use instead** (see `workshop-variables.md` → Genie Code Constraints for full list):
- List directory: `list(w.workspace.list(path=DIR))`
- Read workspace file: `base64.b64decode(w.workspace.export(path=WS_PATH).content).decode()`
- Write workspace file: `write_file(path, content)` or `write_notebook(path, content)` helpers
- Run SQL: `run_sql(sql)` helper
- Run job by name: `run_job_by_name(keyword)` helper
- Create job: `create_job(name_suffix, notebook_path)` helper
- Create pipeline idempotently: `create_pipeline_idempotent(name_suffix, notebook_path, catalog, target)` helper
- Wrap notebook content with mandatory pip install + restart header: `make_job_notebook(body)` helper

---

## Notebook Authoring Contract (for content passed to `write_notebook()`)

When generating Python content that a Databricks job will execute, **always** use `make_job_notebook(body)` from `workshop-variables.md`. It prepends the four mandatory cells (pip install + restartPython + imports + variable re-derivation) so the resulting notebook works on the job's clean compute. See `GENIE-CODE-OVERRIDES.md` Section 7 for the full rules (no backslash in f-string `{}`, psycopg-only for `MANAGED_ONLINE_CATALOG` sources, no `DEFAULT` columns in `CREATE TABLE` DDL).
