# GC Prompt Header — apps_lakebase

**Before any prompt in `apps_lakebase/prompts/`:** read **`GENIE-CODE-OVERRIDES.md`** (CLI → SDK), then **`workshop-variables.md`** Cell 1–3 (`w`, `APP_*`, `write_file`, **`validate_and_deploy`**). On errors, open **`troubleshooting_gc.md`** first.

**Environment:** Databricks serverless notebook — no shell, no local Node/npm, no `localhost` / `curl` to the app URL (auth proxy returns `401` from notebooks).

**Do not:** `databricks` / `npm` / `npx` / `subprocess` / `os.system` / `databricks bundle`; do not hand-roll deploy (use **`validate_and_deploy(APP_NAME, APP_BASE)`** only). Do not import **`databricks_mcp`** or call workspace **`appkit_*`** tools — this track is SDK-only.

**Do:** `%pip` + `restartPython` + Cell 3 from `workshop-variables.md`; `write_file` for sources; list/read workspace via `w.workspace.list` / `w.workspace.export`; deploy with `validate_and_deploy`; poll compute with **`app.compute_status.state.name`** (`"ACTIVE"`), never `str(state)`; wrap paths in **`AppDeployment(source_code_path=APP_BASE)`** inside the helper.

**Permissions:** App **service principal** needs **`CAN_READ`** on the folder containing `APP_BASE` and app **`CAN_MANAGE`** as needed so the platform build can read sources (see `.assistant_instructions.md` Deploy Rules).

Canonical snippets: **`GENIE-CODE-OVERRIDES.md` Section 6** (`app.ts`, `app.yaml`, `vite.config.ts`, `package.json` build, `AppResourcePostgres`).
