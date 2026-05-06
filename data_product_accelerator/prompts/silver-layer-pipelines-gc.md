> **Header:** `@data_product_accelerator/gc-prompt-conversion/gc-prompt-header.md` — read FIRST.
> **CLI / bundle context:** `@data_product_accelerator/skills/silver/00-silver-layer-setup/SKILL.md` + `@data_product_accelerator/skills/common/databricks-asset-bundles/SKILL.md` — Genie uses SDK / `w.pipelines` in this prompt.

---

**Bootstrap:** Run **`@data_product_accelerator/gc-prompt-conversion/workshop-variables.md`** so `w`, `APP_NAME`, `DB_SCHEMA`, and helpers (`write_notebook`, `create_job`, `create_pipeline_idempotent`, `run_job_by_name`) are in scope.

**Task:** **`@data_product_accelerator/skills/silver/00-silver-layer-setup/SKILL.md`** — mirror the CLI prompt intent:

| Original step | Genie execution |
|---------------|----------------|
| SDP pipeline notebooks — incremental from Bronze (**CDF**) | Implement per SKILL. **Workshop caveat:** **`@data_product_accelerator/gc-prompt-conversion/GENIE-CODE-OVERRIDES.md`** §4 (Silver) + **`@data_product_accelerator/gc-prompt-conversion/troubleshooting_gc.md`** — some Bronze setups require **`spark.readStream.table`** to Bronze Delta rather than **`readChangeFeed`**; follow SKILL phases where they align with overrides (avoid blind `readChangeFeed` if SKILL/overrides prescribe streaming table reads). Do not mix Liquid clustering with **`pipelines.autoOptimize.zOrderCols`**. |
| Centralized DQ rules table + expectations | Build DQ rules/metadata as SKILL directs; DQ **setup notebook job** creates the tables the pipeline consumes. |
| Asset Bundle | **Replace with SDK:** notebooks via **`write_notebook()`**, jobs via **`create_job()`**, pipeline via **`create_pipeline_idempotent()`** — no **`databricks bundle validate/deploy/run`**. |
| Deploy/run order | **DQ setup job FIRST** (creates rules table), then **trigger SDP pipeline** (reads rules). |

**Success criteria (same as original):** Notebooks/jobs/pipeline exist and run without Silver-layer errors (bundle validate/deploy → SDK create/run). **Validation:** DQ rules appear in the centralized **`dq_rules`** Delta table (UI or `SELECT`); Silver SDP pipeline completes with expectations checked.

**Catalog / schema (IMPORTANT):** Use only **`donotdelete_vibe_coding_catalog`**. Workshop Silver schema **`jaiwant_j_booking_app_silver`** aligns with **`{DB_SCHEMA}_silver`** when **`APP_NAME`** follows the booking-app formula. If **`donotdelete_vibe_coding_catalog.jaiwant_j_booking_app_silver`** (or **`{TARGET_CATALOG}.{DB_SCHEMA}_silver`**) already exists, **DROP SCHEMA … CASCADE** and recreate — user-specific, safe.

**Shared workspace naming:** Original bundle pattern: **`user_prefix`** in pipeline/job **`name:`** (e.g. `"[${bundle.target} ${var.user_prefix}] Silver Layer Pipeline"`); **`databricks bundle deploy --force`** does not fix name collisions. Read **`@data_product_accelerator/skills/common/databricks-asset-bundles/SKILL.md`** → “Shared Workspace Naming”. In Genie use the same intent: include **`APP_NAME`** in names, e.g. **`[dev {APP_NAME}] Silver Layer Pipeline`** — do not edit the skill.

**Failures:** **`@data_product_accelerator/gc-prompt-conversion/troubleshooting_gc.md`** (Silver / DLT rows).
