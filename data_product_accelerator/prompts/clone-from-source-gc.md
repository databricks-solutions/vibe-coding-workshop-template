> **Header:** `@data_product_accelerator/gc-prompt-conversion/gc-prompt-header.md` — read FIRST.  
> **Lakebase / MANAGED ONLINE:** `@data_product_accelerator/gc-prompt-conversion/lakebase-notebook-connection.md`  
> **CLI / bundle context:** `@data_product_accelerator/skills/common/databricks-asset-bundles/SKILL.md` — Genie uses SDK in this prompt instead of `databricks bundle`.

---

**Original source (UC):** `vibe_coding_workshop_lakebase`.`jaiwant_j_booking` — **Approach C** clone per **`@data_product_accelerator/skills/bronze/00-bronze-layer-setup/SKILL.md`**.

**Genie:** That catalog is often **`MANAGED_ONLINE_CATALOG`** — **Spark reads fail** (`External authorization failed`). Use **psycopg** (`w.postgres` + **`dbname=databricks_postgres`**) into **`donotdelete_vibe_coding_catalog`**, Bronze schema **`{DB_SCHEMA}_bronze`** (matches original **`jaiwant_j_booking_app_bronze`** pattern once `APP_NAME` is resolved). Preserve **CDF + liquid clustering + auto-optimize/auto-compact + COMMENTs** as the SKILL specifies.

**Interactive pip (Genie Cell 1):**

```python
%pip install --upgrade databricks-sdk "psycopg[binary]>=3.0" -q
```

If **`WorkspaceClient` lacks `postgres`:** `dbutils.library.restartPython()`, re-pip, continue. Notebook jobs → wrap body with **`make_job_notebook()`** — **`@data_product_accelerator/gc-prompt-conversion/GENIE-CODE-OVERRIDES.md`** §7.

**CLI → Genie replaces:** Asset Bundle / `databricks bundle` / local clone script → **`write_notebook`**, **`create_job`** (or **`w.jobs.create`** for custom graphs), then **`run_job_by_name("bronze")`** from **`@data_product_accelerator/gc-prompt-conversion/workshop-variables.md`** (`run_now_and_wait` is encapsulated there). Overrides: **`@data_product_accelerator/gc-prompt-conversion/GENIE-CODE-OVERRIDES.md`** §2–3.

**Schema rule (from original):** Use existing **`donotdelete_vibe_coding_catalog`** only; **DROP+CASCADE** `{DB_SCHEMA}_bronze` if it already exists, then recreate.

**Checkpoint:** `get_status(notebook_path)` before job create; notebook path **`(REPO_ROOT + "/src/…").replace("/Workspace","",1)`**, no `.py`.
