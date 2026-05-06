# GC Prompt Header — apps_lakebase Standard Preamble

**Read this BEFORE following any prompt in `apps_lakebase/prompts/`.** It consolidates the standard environment, error-handling, and skill-reference rules that apply to every Genie Code prompt in the AppKit / Lakebase track of this workshop.

---

## CLI Overrides

`@apps_lakebase/gc-prompt-conversion/GENIE-CODE-OVERRIDES.md` — read FIRST. Apply all CLI overrides before following any skill instruction. The skills under [`apps_lakebase/skills/`](../skills/) were authored for the Cursor/local CLI track and contain `databricks` CLI calls, `npm`, `npx`, `node`, and `localhost` references. The overrides file maps every CLI operation to its Genie Code MCP/SDK equivalent.

---

## Error-Handling Protocol

> **On ANY error:** STOP and read `apps_lakebase/gc-prompt-conversion/troubleshooting_gc.md`. Match the error message or symptom in the tables. Apply the fix exactly as described. Do NOT improvise a workaround before checking the troubleshooting reference.

If the error is not in the troubleshooting catalog, capture the full error text and ask the user before guessing.

---

## Skills Required (read these BEFORE starting any prompt)

- `@apps_lakebase/gc-prompt-conversion/workshop-variables.md` — standard variable setup (`APP_NAME`, `DB_SCHEMA`, `REPO_ROOT`, `APP_BASE`), the `write_file()` helper, and the four AppKit-aware SDK helpers (`setup_mcp_client`, `ensure_app_active`, `validate_and_deploy`, `verify_postgres_resource`)
- `@apps_lakebase/gc-prompt-conversion/MCP-appkit_tooling.md` — full MCP tool reference (all 11 `appkit_*` tool signatures, parameters, return values)

---

## Environment

**Genie Code on Databricks workspace (serverless).** No CLI, no terminal, no local filesystem, no Node.js, no npm.

**NEVER use:**
- `databricks` CLI / `databricks bundle deploy` / `databricks.yml` — use MCP `appkit_validate` + SDK `deploy_and_wait` (or the `validate_and_deploy()` helper)
- `npm`, `npx`, `node`, `npm run build`, `npm run dev`, `npm run typegen`, `npx tsc --noEmit` — the platform runs `npm install` + `npm run build` at deploy time
- `appkit build` / `appkit start` — `@databricks/appkit` has no `build`/`start` CLI; use `vite build` for building and `tsx app.ts` for starting
- `subprocess`, `subprocess.run()`, `os.system()`, `os.popen()`, `shell=True` — no shell access
- `localhost`, `http://localhost:8000`, `curl`, `psql` — no local server; the Apps auth proxy blocks programmatic API calls from notebooks (returns `401 {}`)
- `open(local_path)` / file paths outside `/Workspace` — no local filesystem
- `pip install` without `%` — use `%pip install` magic in a dedicated cell

**Use instead:**
- Bootstrap MCP + WorkspaceClient: `w, mcp_client = setup_mcp_client()` (after pip install + restart)
- List directory: `[obj.path for obj in w.workspace.list(path=DIR)]`
- Read workspace file: `base64.b64decode(w.workspace.export(path=WS_PATH).content).decode()`
- Write workspace file: `write_file(path, content)`
- Validate + deploy app: `deployment, app_url = validate_and_deploy(APP_NAME, APP_BASE)`
- Ensure app compute is ACTIVE: `ensure_app_active(APP_NAME)`
- Confirm postgres-type resource binding: `verify_postgres_resource(APP_NAME)`

---

## MCP + Deploy Contract (for content invoking AppKit)

Every prompt that touches the app's source files or deploys follows this contract:

1. **First three cells (always):**
   ```python
   # Cell 1
   %pip install databricks-mcp --upgrade databricks-sdk -q
   # Cell 2
   dbutils.library.restartPython()
   # Cell 3 — Python state was wiped, so re-derive everything
   # (paste the standard setup block from @apps_lakebase/gc-prompt-conversion/workshop-variables.md)
   w, mcp_client = setup_mcp_client()
   ```

2. **Deploy via `validate_and_deploy()`** — never inline `appkit_validate` + `create_and_wait` + `deploy_and_wait`. The helper handles validation, app create-if-missing, ensure-ACTIVE polling, deploy_and_wait, and prints the URL.

3. **Verify postgres binding via `verify_postgres_resource()`** — never inline a `for r in app.resources` loop. The helper enforces `postgres`-type (not `database`-type) binding which is the most common Lakebase wiring failure.

4. **Use `.state.name`** (returns `"ACTIVE"`) — NOT `str(state)` (returns `"ComputeState.ACTIVE"`) — for any compute polling. The latter never matches `== "ACTIVE"` and causes infinite polling.

5. **Wrap `source_code_path` in `AppDeployment(...)`** — `deploy_and_wait()` rejects `source_code_path` as a top-level kwarg.

See `@apps_lakebase/gc-prompt-conversion/GENIE-CODE-OVERRIDES.md` Section 6 ("AppKit Verified Patterns") for the canonical `app.ts`, `app.yaml`, `package.json`, and resource-binding snippets. After **Wire Lakebase**, `app.ts` must use **`await createApp`** with `[lakebase(), server()]` and `onPluginsReady` — bare `createApp(...)` causes missing `/api/*` routes and a stuck **Mock Data** indicator; map layout guidance is in the same file under **Map / location UI**.
