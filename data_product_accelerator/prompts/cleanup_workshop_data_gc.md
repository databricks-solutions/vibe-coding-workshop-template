> **Header:** `@data_product_accelerator/gc-prompt-conversion/gc-prompt-header.md` — read FIRST.
> **Purpose:** Tear down **your** workshop medallion schemas and matching jobs/pipelines so the next Genie run starts cold. **Shared catalog** `donotdelete_vibe_coding_catalog` is **not** dropped — only schemas derived from **`DB_SCHEMA`**.

---

1. Run **`@data_product_accelerator/gc-prompt-conversion/workshop-variables.md`**.

2. **SQL (warehouse / `run_sql`)** — drops Bronze/Silver/Gold **schemas** for this `APP_NAME` (CASCADE removes tables):

```python
cat = TARGET_CATALOG
for suffix in ("_bronze", "_silver", "_gold"):
    sch = f"{DB_SCHEMA}{suffix}"
    run_sql(f"DROP SCHEMA IF EXISTS `{cat}`.`{sch}` CASCADE")
    print(f"Dropped (if existed): {cat}.{sch}")
```

3. **Jobs:** List `w.jobs.list()`, keep jobs where **`APP_NAME`** appears in the name and the name looks like this workshop (e.g. contains `bronze`, `dq`, `gold`, `Silver`). **`w.jobs.delete(job_id=...)`** — print each name before delete.

4. **Pipelines:** `for p in w.pipelines.list_pipelines():` filter **`APP_NAME` in (p.name or "")** and **`silver` in (p.name or "").lower()`**, then **`w.pipelines.delete(pipeline_id=p.pipeline_id)`** (print name/ id first).

5. **Workspace notebooks** under **`{REPO_ROOT}/src/{DB_SCHEMA}_*`** (optional): `w.workspace.list` + recursive delete only if you intend to regenerate notebooks from **`@data_product_accelerator/prompts/clone-from-source-gc.md`** / **`@data_product_accelerator/prompts/silver-layer-pipelines-gc.md`** / **`@data_product_accelerator/prompts/gold-layer-pipeline-gc.md`**. Locally you can use **`data_product_accelerator/scripts/cleanup_workshop_data.py`** instead for UC + jobs + pipelines.

6. **Repo-root design output** (optional, if present in workspace checkout): remove **`gold_layer_design/`** at **`REPO_ROOT`** via workspace delete only if those paths exist and you want a clean **Gold design** run.

> **Never** drop the whole catalog. If unsure, run Step 2 only after printing `DB_SCHEMA` and confirming schemas are yours.
