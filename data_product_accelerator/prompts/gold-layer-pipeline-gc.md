> **Header:** `@data_product_accelerator/gc-prompt-conversion/gc-prompt-header.md` — read FIRST.  
> **Merge reference:** `@data_product_accelerator/gc-prompt-conversion/reference_gold_merge_booking_notebook_body.py`  
> **CLI / bundle context:** `@data_product_accelerator/skills/gold/01-gold-layer-setup/SKILL.md` — Genie uses SDK / jobs in this prompt instead of bundle-only flows.

---

**Bootstrap:** **`@data_product_accelerator/gc-prompt-conversion/workshop-variables.md`**.

**Task:** **`@data_product_accelerator/skills/gold/01-gold-layer-setup/SKILL.md`**:

- YAML as source of truth → CREATE TABLE → PK → FK (**NOT ENFORCED**) → MERGE Silver → **gold_setup_job** (**2 tasks**) + **gold_merge_job**
- Silver as source for facts/dims (**5 core tables** exercise cap from original).

**Catalog / schema:** **`donotdelete_vibe_coding_catalog`**, Gold **`{DB_SCHEMA}_gold`** (original **`jaiwant_j_booking_app_gold`**). **DROP+CASCADE** if exists.

**CLI → Genie:** bundle / `databricks bundle run` → **`write_notebook`**, **`create_job`**, **`w.jobs.create`** for multi-task gold setup — **`@data_product_accelerator/gc-prompt-conversion/GENIE-CODE-OVERRIDES.md`** §7 notebook headers (**pip → restart → re-derive vars**).

**High-risk deltas (YAML vs Silver mismatch, booking workshop):** **`@data_product_accelerator/gc-prompt-conversion/troubleshooting_gc.md`** (Gold sections) + **`@data_product_accelerator/gc-prompt-conversion/reference_gold_merge_booking_notebook_body.py`** — NOT NULL placeholders, **`lit(None).cast`** for missing Silver cols, string id casting, skip empty **`silver_bookings`**.
