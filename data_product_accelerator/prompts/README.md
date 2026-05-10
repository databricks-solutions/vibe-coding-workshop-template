# Data Product Accelerator — Genie Code prompts

These **`*_gc.md`** files run in **Databricks Genie Code** (notebook) with the Databricks Python SDK — no local `databricks bundle` / shell. For CLI / Asset Bundle patterns, use **`data_product_accelerator/skills/common/databricks-asset-bundles/SKILL.md`** and the stage-specific skills referenced in each prompt.

## Once per session (before any prompt below)

1. Read [`@data_product_accelerator/gc-prompt-conversion/gc-prompt-header.md`](../gc-prompt-conversion/gc-prompt-header.md).
2. Paste and run **[`@data_product_accelerator/gc-prompt-conversion/workshop-variables.md`](../gc-prompt-conversion/workshop-variables.md)** so `w`, `REPO_ROOT`, `APP_NAME`, `DB_SCHEMA`, `TARGET_CATALOG`, and helpers exist.

Details: [`GENIE-CODE-OVERRIDES.md`](../gc-prompt-conversion/GENIE-CODE-OVERRIDES.md), [`troubleshooting_gc.md`](../gc-prompt-conversion/troubleshooting_gc.md).

## Handoff after `apps_lakebase` (AppKit + Lakebase → DPA)

Use this when the **five** `apps_lakebase/prompts/` steps are done (`deploy_and_test_gc.md` finished) and you are starting **Lakebase → Lakehouse** in the same or a new Genie thread.

1. **Same checkout** — `REPO_ROOT` in DPA `workshop-variables.md` must be the same workspace repo path you used for the app (e.g. `…/v2v-in-geniecode/vibe-coding-workshop-template`).
2. **Lakebase identity** — App folder name and **Lakebase project id** may differ from formula `APP_NAME`. Before **`extract_from_tables_gc.md`**, read [`lakebase-notebook-connection.md`](../gc-prompt-conversion/lakebase-notebook-connection.md) and resolve **`LAKEBASE_PROJECT_ID`** / **`PG_SCHEMA`** (discovery or set explicitly). Wrong schema → **0 rows** in the extract CSV.
3. **Kernel / packages** — For extract + Bronze, run **`%pip install --upgrade databricks-sdk "psycopg[binary]>=3.0" -q`** in its own cell; restart if the SDK was imported before upgrade (`dbutils.library.restartPython()`), then re-run pip + DPA **`workshop-variables.md`**.
4. **Catalog** — Confirm **`TARGET_CATALOG`** (default `donotdelete_vibe_coding_catalog` in `workshop-variables.md`) exists and your user can create schemas/tables there.
5. **Optional clean slate** — Step 0 [`cleanup_workshop_data_gc.md`](cleanup_workshop_data_gc.md) drops prior `{DB_SCHEMA}_bronze|_silver|_gold` schemas and workshop jobs/pipelines for this `APP_NAME` so Bronze/Silver/Gold reruns do not collide.
6. **Paste order (DPA session)** — `gc-prompt-header.md` → full `workshop-variables.md` → (for extract) `lakebase-notebook-connection.md` → prompts **1→6** in the table below.

## Recommended pipeline order

| Step | Prompt |
|------|--------|
| 0 (optional reset) | [`cleanup_workshop_data_gc.md`](cleanup_workshop_data_gc.md) — Genie/SDK teardown for this `DB_SCHEMA` (shared catalog is not dropped) |
| 1 | [`extract_from_tables_gc.md`](extract_from_tables_gc.md) — schema CSV under `context/` |
| 2 | [`clone-from-source-gc.md`](clone-from-source-gc.md) — Bronze |
| 3 | [`silver-layer-pipelines-gc.md`](silver-layer-pipelines-gc.md) — Silver SDP + DQ |
| 4 | [`gold-layer-design-gc.md`](gold-layer-design-gc.md) — dimensional model + YAML (uses extract CSV; may reference Silver names for lineage if helpful) |
| 5 | [`gold-layer-pipeline-gc.md`](gold-layer-pipeline-gc.md) — Gold DDL + merge jobs |
| 6 | [`deploy-assets-gc.md`](deploy-assets-gc.md) — run jobs + Silver pipeline orchestration; **executable cells** in [`../gc-prompt-conversion/deploy-assets-cells/`](../gc-prompt-conversion/deploy-assets-cells/README.md) |

`REPO_ROOT` must match your workspace checkout (see `workshop-variables.md`).
