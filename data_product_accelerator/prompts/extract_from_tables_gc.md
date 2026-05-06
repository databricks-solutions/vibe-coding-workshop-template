> **Header:** `@data_product_accelerator/gc-prompt-conversion/gc-prompt-header.md` — read FIRST.  
> **Lakebase:** `@data_product_accelerator/gc-prompt-conversion/lakebase-notebook-connection.md`  
> **CLI / bundle context:** `@data_product_accelerator/skills/common/databricks-asset-bundles/SKILL.md` — Genie uses SDK in this prompt instead of shell extraction.

---

**Original intent:** Query **`information_schema.columns`** for **`vibe_coding_workshop_lakebase`** / **`jaiwant_j_booking`** → save **`data_product_accelerator/context/booking_app_Schema.csv`** — the CSV seeds the Design-First pipeline.

**Genie paths (pick the one your workspace has):**

1. **Warehouse SQL** — if the UC catalog/schema is readable from SQL: use **`run_sql(...)`** from **`@data_product_accelerator/gc-prompt-conversion/workshop-variables.md`** with the same SELECT shape as the original:
   ```sql
   SELECT * FROM vibe_coding_workshop_lakebase.information_schema.columns
   WHERE table_schema = 'jaiwant_j_booking'
   ORDER BY table_name, ordinal_position
   ```
   then **`write_file(OUTPUT_PATH, csv_text)`**.
2. **Lakebase Postgres (typical Apps workshop)** — **`LAKEBASE_PROJECT_ID`**, **`PG_SCHEMA`**, **`psycopg`**, **`WHERE table_schema = '{PG_SCHEMA}'`** per **`@data_product_accelerator/gc-prompt-conversion/lakebase-notebook-connection.md`**; **`write_file`**.

Do **not** use **`open()`**, **`local` jq/curl shells**, or CLI **`databricks api post`** inside Genie — see **`@data_product_accelerator/gc-prompt-conversion/GENIE-CODE-OVERRIDES.md`** §1–2.

**Steps:** **`@data_product_accelerator/gc-prompt-conversion/workshop-variables.md`** → `OUTPUT_PATH = f"{REPO_ROOT}/data_product_accelerator/context/booking_app_Schema.csv"` → `%pip` + psycopg if needed → extract → **`write_file`** → read back sample rows. **0 rows** → wrong schema / **`PG_SCHEMA`** / empty DB — **`@data_product_accelerator/gc-prompt-conversion/troubleshooting_gc.md`**.
