# GC Prompt Header — apps_lakebase Standard Preamble

**Read this BEFORE following any prompt in `apps_lakebase/prompts/`.** It consolidates the standard environment, error-handling, and skill-reference rules that apply to every Genie Code prompt in the AppKit / Lakebase track of this workshop.

---

## CLI Overrides

`@apps_lakebase/gc-prompt-conversion/GENIE-CODE-OVERRIDES.md` — read FIRST. Apply all CLI overrides before following any skill instruction. The skills under [`apps_lakebase/skills/`](../skills/) were authored for the Cursor/local CLI track and contain `databricks` CLI calls, `npm`, `npx`, `node`, and `localhost` references. The overrides file maps every CLI operation to **Databricks Python SDK** patterns (`w.apps`, `w.workspace`, `w.database`, `w.postgres`, `write_file`).

---

## Error-Handling Protocol

> **On ANY error:** STOP and read `apps_lakebase/gc-prompt-conversion/troubleshooting_gc.md`. Match the error message or symptom in the tables. Apply the fix exactly as described. Do NOT improvise a workaround before checking the troubleshooting reference.

If the error is not in the troubleshooting catalog, capture the full error text and ask the user before guessing.

---

## Skills Required (read these BEFORE starting any prompt)

- `@apps_lakebase/gc-prompt-conversion/workshop-variables.md` — standard variable setup (`APP_NAME`, `DB_SCHEMA`, `REPO_ROOT`, `APP_BASE`), `write_file()`, `sdk_preflight_app_folder`, `ensure_app_active`, **`validate_and_deploy()`** (SDK preflight + deploy), `verify_postgres_resource`
- `@apps_lakebase/gc-prompt-conversion/GENIE-CODE-OVERRIDES.md` — CLI → SDK when skills mention bash/CLI
- `@apps_lakebase/gc-prompt-conversion/troubleshooting_gc.md` — error catalog
- `@apps_lakebase/gc-prompt-conversion/MCP-appkit_tooling.md` — **optional** historical mapping from old MCP tool names to SDK/skill equivalents (workshop does not require `mcp-appkit-skill`)

---

## Environment

**Genie Code on Databricks workspace (serverless).** No CLI, no terminal, no local filesystem, no Node.js, no npm.

**NEVER use:**
- `databricks` CLI / `databricks bundle deploy` / `databricks.yml` — use **`validate_and_deploy(APP_NAME, APP_BASE)`** from `workshop-variables.md` (SDK preflight + `create_and_wait` + `deploy_and_wait`)
- `npm`, `npx`, `node`, `npm run build`, `npm run dev`, `npm run typegen`, `npx tsc --noEmit` — the platform runs `npm install` + `npm run build` at deploy time
- `appkit build` / `appkit start` — `@databricks/appkit` has no `build`/`start` CLI; use `vite build` for building and `tsx app.ts` for starting
- `subprocess`, `subprocess.run()`, `os.system()`, `os.popen()`, `shell=True` — no shell access
- `localhost`, `http://localhost:8000`, `curl`, `psql` — no local server; the Apps auth proxy blocks programmatic API calls from notebooks (returns `401 {}`)
- `open(local_path)` / file paths outside `/Workspace` — no local filesystem
- `pip install` without `%` — use `%pip install` magic in a dedicated cell
- `DatabricksMCPClient`, `databricks_mcp`, `mcp_client.call_tool`, or any `appkit_*` MCP tool — **not part of this workshop path**

**Use instead:**
- After pip + restart: paste **Cell 3** from `@apps_lakebase/gc-prompt-conversion/workshop-variables.md` (defines `w`, `APP_*`, helpers)
- List directory: `[obj.path for obj in w.workspace.list(path=DIR)]`
- Read workspace file: `base64.b64decode(w.workspace.export(path=WS_PATH).content).decode()`
- Write workspace file: `write_file(path, content)`
- Validate + deploy app: `deployment, app_url = validate_and_deploy(APP_NAME, APP_BASE)`
- Ensure app compute is ACTIVE: `ensure_app_active(APP_NAME)` (also called inside `validate_and_deploy`)
- Confirm postgres-type resource binding: `verify_postgres_resource(APP_NAME)`

---

## SDK + Deploy Contract (for content invoking AppKit)

Every prompt that touches the app's source files or deploys follows this contract:

1. **First three cells (always):**
   ```python
   # Cell 1
   %pip install databricks-sdk --upgrade -q
   # Cell 2
   dbutils.library.restartPython()
   # Cell 3 — paste the FULL block from @apps_lakebase/gc-prompt-conversion/workshop-variables.md
   # (defines w, APP_NAME, APP_BASE, write_file, sdk_preflight_app_folder, ensure_app_active,
   #  validate_and_deploy, verify_postgres_resource — no separate setup call)
   ```

2. **Deploy via `validate_and_deploy()` only** — it runs SDK preflight (`sdk_preflight_app_folder`), `w.apps.create_and_wait` if the app is missing, `ensure_app_active`, then `w.apps.deploy_and_wait` with `AppDeployment(source_code_path=APP_BASE)`. Do not hand-roll a different sequence unless troubleshooting directs it.

3. **Verify postgres binding via `verify_postgres_resource()`** — never inline a `for r in app.resources` loop unless troubleshooting asks for raw inspection. The helper enforces `postgres`-type (not `database`-type) binding which is the most common Lakebase wiring failure.

4. **Use `.state.name`** (returns `"ACTIVE"`) — NOT `str(state)` (returns `"ComputeState.ACTIVE"`) — for any compute polling. The latter never matches `== "ACTIVE"` and causes infinite polling.

5. **Wrap `source_code_path` in `AppDeployment(...)`** — `deploy_and_wait()` rejects `source_code_path` as a top-level kwarg.

**Permissions:** The **Databricks App’s service principal** must be able to read `APP_BASE` at build time. Grant **`CAN_READ`** (and typically **`CAN_MANAGE`** on the app) per `.assistant_instructions.md` Deploy Rules — same as when MCP validated on behalf of a different identity; here preflight runs as the notebook user, but the **build** still uses the app SP.

See `@apps_lakebase/gc-prompt-conversion/GENIE-CODE-OVERRIDES.md` Section 6 ("AppKit Verified Patterns") for the canonical `app.ts`, `app.yaml`, `package.json`, and resource-binding snippets. After **Wire Lakebase**, `app.ts` must use **`await createApp`** with `[lakebase(), server()]` and `onPluginsReady` — bare `createApp(...)` causes missing `/api/*` routes and a stuck **Mock Data** indicator; map layout guidance is in the same file under **Map / location UI**.
