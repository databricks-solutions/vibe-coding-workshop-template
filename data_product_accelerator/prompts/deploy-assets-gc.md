> **Header:** `@data_product_accelerator/gc-prompt-conversion/gc-prompt-header.md` — read FIRST for environment constraints, error-handling protocol, and required skill references.
>
> **Additional skill for this prompt:** `@data_product_accelerator/skills/common/databricks-autonomous-operations/SKILL.md` — SDK run/poll/diagnose/fix loop (read-only; do not edit the skill).

---

**CLI / bundle equivalent:** validates/deploys Asset Bundle then **`bundle run`** Bronze → Silver DQ → **`silver_dlt_pipeline`** → Gold setup → Gold merge (see **`@data_product_accelerator/skills/common/databricks-asset-bundles/SKILL.md`**). **Genie substitutes** the same dependency order via SDK (**no** **`databricks bundle validate/deploy/run`** in-notebook).

Runs **already-created** medallion notebooks + Silver pipeline after the full accelerator sequence (workshop order: **`extract_from_tables_gc`** → **`clone-from-source-gc`** → **`silver-layer-pipelines-gc`** → **`gold-layer-design-gc`** → **`gold-layer-pipeline-gc`**). **SDK + Spark SQL** — no shell / local FS. AppKit is separate (**`apps_lakebase`**).

**Cell bodies (copy into Genie Python cells):** [`@data_product_accelerator/gc-prompt-conversion/deploy-assets-cells/`](../gc-prompt-conversion/deploy-assets-cells/README.md) — one **`.py`** file per step. This file is the **orchestration + troubleshooting** only.

> **Repo / `@` paths:** The `deploy-assets-cells/*.py` files **ship with this repository** under `data_product_accelerator/gc-prompt-conversion/deploy-assets-cells/` — earlier prompts do **not** create them. If Genie cannot `@`-open them, **Repos → Pull** (or re-add the repo) so that folder exists at `REPO_ROOT`. Then open each referenced `.py` and paste into a **Python** cell; do not skip straight to “run jobs” without loading A2 and B–H code from those files.

**Mapping:** `bronze_clone_job` → Cell **C** · `silver_dq_setup_job` → **D** · `silver_dlt_pipeline` → **E** (**`full_refresh=True`**) · `gold_setup_job` → **F** · `gold_merge_job` → **G** · verification SQL appendix in original → Cell **H** (Python allowlists **`src_*`**).

**Gate order:** **A** → **B** (cold start) → **C**–**G** → **H**. Health-only: **A** + **H**. Failures → **`@data_product_accelerator/gc-prompt-conversion/troubleshooting_gc.md`** + **`@data_product_accelerator/skills/common/databricks-autonomous-operations/SKILL.md`** skill.

---

## Prerequisites — Cell A (mandatory)

### A1 — Workshop helpers

Run the full variable + helper bootstrap from **`@data_product_accelerator/gc-prompt-conversion/workshop-variables.md`** in a **Python** cell. You need: `w`, `APP_NAME`, `DB_SCHEMA`, `REPO_ROOT`, `run_job_by_name`, `run_sql`.

### A2 — Deploy constants

Run the **next** Python cell immediately after A1 — copy from:

**`@data_product_accelerator/gc-prompt-conversion/deploy-assets-cells/a2_deploy_constants.py`**

Uses **`TARGET_CATALOG`** from workshop-variables (printed in A1). Uncomment and set `TARGET_CATALOG` in that file only if your workspace uses a different catalog.

---

> **CRITICAL — `src_*` names.** Names like **`src_dim_listing`**, **`src_fact_booking`**, etc. are **temporary merge view names** from Gold merge notebooks. They are **not** Delta tables in Bronze/Silver/Gold. **Never** row-count them in verification. Use **Cell H** (`h_verification.py`), which allowlists Bronze/Gold base tables and filters Silver `silver_*` tables.

---

## Step 0 — Cell B: Confirm jobs and pipeline exist

Assumes **Cell A** completed (`w`, `APP_NAME` in scope). This step **does not** run jobs; it only **discovers** resources for this `APP_NAME`.

**Code:** **`@data_product_accelerator/gc-prompt-conversion/deploy-assets-cells/b_step0_discover.py`**

---

## Step 1 — Cell C: Bronze clone (before any Silver work)

**Dependency:** None (source is Lakebase / clone logic). **Gate:** `run.state.result_state` must be **SUCCESS**.

**Code:** **`@data_product_accelerator/gc-prompt-conversion/deploy-assets-cells/c_step1_bronze.py`**

If this fails with **Lakebase / `projects/...` not found**, fix **`LAKEBASE_PROJECT_ID`** and connection per `@data_product_accelerator/gc-prompt-conversion/lakebase-notebook-connection.md`, then re-run this step.

---

## Step 2 — Cell D: Silver DQ setup (must run before the pipeline)

**Dependency:** Bronze tables exist (clone succeeded). **Gate:** **SUCCESS**.

**Code:** **`@data_product_accelerator/gc-prompt-conversion/deploy-assets-cells/d_step2_dq.py`**

---

## Step 3 — Cell E: Silver DLT / Lakeflow pipeline

**Dependency:** Silver DQ setup succeeded (`dq_rules` and related metadata). **Gate:** pipeline latest update state **COMPLETED**.

**Full refresh (default here):** This deploy path runs **Bronze clone (Cell C) before** the Silver pipeline. Re-cloning Bronze changes table versions; an **incremental** pipeline update can leave **stale checkpoints** and cause every `silver_*` flow to fail repeatedly. Cell E calls **`start_update(..., full_refresh=True)`**, which rebuilds Silver streaming tables to match the current Bronze. That matches `@data_product_accelerator/gc-prompt-conversion/GENIE-CODE-OVERRIDES.md` (bundle `silver_dlt_pipeline` → full refresh). If Bronze is **unchanged** and you only need incremental Silver, edit **`e_step3_silver_pipeline.py`** to use `full_refresh=False` (advanced).

**Pipeline choice:** If multiple pipelines match `APP_NAME` + `silver`, prefer the canonical workshop name **`[dev {APP_NAME}] Silver Layer Pipeline`**. Otherwise the cell picks a single match; if ambiguous, inspect printed IDs and edit the file to set `chosen` manually.

**Code:** **`@data_product_accelerator/gc-prompt-conversion/deploy-assets-cells/e_step3_silver_pipeline.py`**

---

## Step 4 — Cell F: Gold setup

**Dependency:** Silver pipeline **COMPLETED** (Gold reads Silver). **Gate:** **SUCCESS**.

**Code:** **`@data_product_accelerator/gc-prompt-conversion/deploy-assets-cells/f_step4_gold_setup.py`**

---

## Step 5 — Cell G: Gold merge

**Dependency:** Gold setup succeeded (tables + DDL). **Gate:** **SUCCESS**.

**Code:** **`@data_product_accelerator/gc-prompt-conversion/deploy-assets-cells/g_step5_gold_merge.py`**

---

## Troubleshooting

**On ANY error:** Stop and read `@data_product_accelerator/gc-prompt-conversion/troubleshooting_gc.md` before improvising.

**Failed job — use task `run_id`:** The snippet uses the **parent** run from `run_job_by_name`; `get_run_output` must use each **failed task’s** `t.run_id`.

**Code:** **`@data_product_accelerator/gc-prompt-conversion/deploy-assets-cells/snippet_failed_task_outputs.py`**

Follow the autonomous-operations skill: Run → Diagnose → Fix → Re-run (bounded iterations).

**Multiple Silver pipelines / wrong pipeline:** Re-run Step 0 listing; set `chosen = pipelines[i]` in **`e_step3_silver_pipeline.py`** after inspecting names and IDs. Prefer the name **`[dev {APP_NAME}] Silver Layer Pipeline`**.

**`TABLE_OR_VIEW_NOT_FOUND` on `..._bronze`.`src_*`:** Those are merge staging views, not Bronze clones. Use **Cell H** verification only; do not iterate raw `SHOW TABLES` without filtering `src_*`.

**Silver pipeline FAILED** (all `silver_*` flows fail / "failed more than 2 times", sparse events): Often **stale state after Bronze re-clone**. Cell E already uses **`full_refresh=True`**. If you overrode with incremental or still fail: confirm DQ Step 2 ran; confirm SDP notebook uses **`spark.readStream.table(bronze_table)`** (not `readChangeFeed`) per **`@data_product_accelerator/gc-prompt-conversion/GENIE-CODE-OVERRIDES.md`** §4; then delete + recreate pipeline (§6). See **`@data_product_accelerator/gc-prompt-conversion/troubleshooting_gc.md`** (Silver + Deploy Assets).

---

## Verification — Cell H (primary; Python)

Run in a **Python** cell after **Cell A2** (so `TARGET_CATALOG`, `DB_SCHEMA`, schema constants, and `BRONZE_TABLES` / `GOLD_TABLES` exist). Uses **Spark** (`spark.sql`) — same session as Genie Code.

**Code:** **`@data_product_accelerator/gc-prompt-conversion/deploy-assets-cells/h_verification.py`**

---

## Verification — SQL appendix (secondary)

Use only for **manual** inspection. **Do not** use dynamic loops over `SHOW TABLES` in SQL for row counts — that can pick up **`src_*`** artifacts in the same session.

**`@data_product_accelerator/gc-prompt-conversion/deploy-assets-cells/verification_appendix.sql`**

For counts and constraints, prefer **Cell H** (Python).

---

### Operator checklist

- [ ] Cell A1: **`@data_product_accelerator/gc-prompt-conversion/workshop-variables.md`** executed
- [ ] Cell A2: `a2_deploy_constants.py` ran; `TARGET_CATALOG` and schema constants printed
- [ ] Cell B: Step 0 PASS (or Cold start prompts run, then Step 0 re-run)
- [ ] Cell C: Bronze clone → SUCCESS
- [ ] Cell D: Silver DQ setup → SUCCESS
- [ ] Cell E: Silver pipeline (full refresh) → COMPLETED
- [ ] Cell F: Gold setup → SUCCESS
- [ ] Cell G: Gold merge → SUCCESS
- [ ] Cell H: Verification checklist all PASS; no reliance on `src_*` for Bronze

**Workshop delivery:** After you change this file or any cell under **`deploy-assets-cells/`**, sync **`data_product_accelerator/`** to the workspace (for example `databricks workspace import-dir` / Repos pull). See **[`prompts/README.md`](README.md)** for the full prompt index.

---

## Defaults reference

| Setting | Workshop default |
|--------|-------------------|
| `TARGET_CATALOG` | `donotdelete_vibe_coding_catalog` |
| Bronze / Silver / Gold schemas | `{DB_SCHEMA}_bronze`, `{DB_SCHEMA}_silver`, `{DB_SCHEMA}_gold` |

`DB_SCHEMA` is derived from `APP_NAME` in **`@data_product_accelerator/gc-prompt-conversion/workshop-variables.md`** (hyphens → underscores).
