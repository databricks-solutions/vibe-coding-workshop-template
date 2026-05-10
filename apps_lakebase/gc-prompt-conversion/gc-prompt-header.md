# GC Prompt Header — apps_lakebase

**Before any prompt in `apps_lakebase/prompts/`:** read **`GENIE-CODE-OVERRIDES.md`** (CLI → SDK), then **`workshop-variables.md`** Cell 1–3 (`w`, `APP_*`, `write_file`, **`validate_and_deploy`**). On errors, open **`troubleshooting_gc.md`** first.

**Environment:** Databricks serverless notebook — no shell, no local Node/npm, no `localhost` / `curl` to the app URL (auth proxy returns `401` from notebooks).

**Bundle (CLI / Cursor) vs Genie SDK track:** The **`original-*.md`** prompts in `apps_lakebase/prompts/` use **`postgres_projects`** in **`databricks.yml`** and may use a two-phase **`apps.app.resources.postgres`** bind. The **Genie Code** track achieves the same **effect** with **`setup_lakebase_gc.md`**: **`create_database_instance_and_wait`**, **`create_database_instance_role`**, **`list_databases`**, **`w.apps.update`** + **`App.from_dict`** — no **`databricks bundle`** in the notebook. Order: **`README.md`** in this folder.

**Do not:** `databricks` / `npm` / `npx` / `subprocess` / `os.system` / `databricks bundle`; do not hand-roll deploy (use **`validate_and_deploy(APP_NAME, APP_BASE)`** only). Do not import **`databricks_mcp`** or call **`appkit_*`** tools (MCP server **or** IDE/host tools such as **`appkit_get_app_status`**, **`appkit_list_apps`**, **`appkit_scaffold_app`**). Do not open **`MCP-appkit_tooling.md`** / **`@mcp-appkit-tooling`** unless the user explicitly asked for the optional MCP facilitator path — this track is **SDK-only** (`w.apps`, `validate_and_deploy`).

**Do:** `%pip` + `restartPython` + Cell 3 from `workshop-variables.md`; `write_file` for sources; list/read workspace via `w.workspace.list` / `w.workspace.export`; deploy with `validate_and_deploy`; poll compute with **`app.compute_status.state.name`** (`"ACTIVE"`), never `str(state)`; wrap paths in **`AppDeployment(source_code_path=APP_BASE)`** inside the helper.

**Permissions:** App **service principal** needs **`CAN_READ`** on the folder containing `APP_BASE` and app **`CAN_MANAGE`** as needed so the platform build can read sources (see `.assistant_instructions.md` Deploy Rules).

Canonical snippets: **`GENIE-CODE-OVERRIDES.md` Section 6** (`app.ts`, `app.yaml`, `vite.config.ts`, `package.json` build, `AppResourcePostgres`). **Mock first deploy (`one-ui-design-local.md`):** use **only** the **Without Lakebase** `app.ts` pattern — **no** `lakebase()`, **no** `LAKEBASE_*` / `valueFrom: postgres` in `app.yaml`, **no** postgres **`resources`** until **`setup_lakebase_gc.md`** / **`wire_ui_to_lakebase_gc.md`**.
