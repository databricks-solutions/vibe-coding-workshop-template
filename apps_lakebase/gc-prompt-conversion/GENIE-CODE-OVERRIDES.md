# Genie Code Overrides — apps_lakebase

> **Read this file FIRST before following any skill in `apps_lakebase/skills/`.** The skills folder contains CLI-based patterns written for the Cursor/local development track. This file maps every CLI operation to its Genie Code equivalent using the **Databricks Python SDK** (`WorkspaceClient`) and `write_file()` from `@apps_lakebase/gc-prompt-conversion/workshop-variables.md`. **No MCP AppKit server is required.**

---

## Section 1: Environment Constraints

Genie Code runs inside Databricks serverless notebooks. The following are **not available** and will fail silently or with cryptic errors if attempted:

| Forbidden | Reason |
|-----------|--------|
| `databricks` CLI | No terminal access |
| `npm`, `npx`, `node` | No Node.js runtime |
| `npm run build`, `npm run dev`, `npm run typegen` | Platform runs these at deploy time, not in the notebook |
| `npx tsc --noEmit` | No TypeScript compiler |
| `bash`, `subprocess`, `os.system`, `os.popen`, `shell=True` | No shell |
| `localhost` / `http://localhost:8000` | No local server |
| `curl $APP_URL/api/...` | Apps auth proxy blocks programmatic requests from notebooks |
| `databricks.yml` / `databricks bundle deploy` | No Asset Bundle workflow; deploy via SDK `validate_and_deploy()` |
| `git clone`, `git`, filesystem paths | No local filesystem |

---

## Section 2: Global CLI → SDK Override Table

When any skill says to run a CLI command, use this table instead:

### App Lifecycle

| CLI Command | Genie Code Override |
|-------------|---------------------|
| `databricks apps create <name>` | `w.apps.create_and_wait(app=App(name=APP_NAME, description="..."))` |
| `databricks apps deploy <name> --source-code-path <path>` | **`validate_and_deploy(APP_NAME, APP_BASE)`** from `workshop-variables.md` — SDK preflight + `create_and_wait` (if missing) + `ensure_app_active` + `deploy_and_wait` with `AppDeployment(source_code_path=APP_BASE)` |
| `databricks apps get <name>` | `w.apps.get(name=APP_NAME)` |
| `databricks apps list` | `list(w.apps.list())` |
| `databricks apps logs <name>` | `list(w.apps.list_deployments(app_name=APP_NAME))` — check deployment status. View full logs in Databricks UI → Compute → Apps. |
| `databricks apps stop <name>` | `w.apps.stop(name=APP_NAME)` |
| `databricks apps delete <name>` | `w.apps.delete(name=APP_NAME)` |

### Auth and Identity

| CLI Command | Genie Code Override |
|-------------|---------------------|
| `databricks current-user me` | `w.current_user.me()` — returns email as `.user_name` |
| `databricks auth token` | Not needed — the Databricks Apps auth proxy handles JWT injection automatically |
| `databricks auth login` | Not needed — `w = WorkspaceClient()` auto-detects notebook context |
| `databricks auth profiles` | Not needed — notebook context is always the current workspace |

### Scaffolding

| CLI Command | Genie Code Override |
|-------------|---------------------|
| `npx @databricks/appkit scaffold <name>` | Implement from `apps_lakebase/skills/01-appkit-scaffold/SKILL.md` Steps 1–4 using `write_file()` under `APP_BASE`, or paste a `FILES` dict / JSON bundle per `mcp-off-paste-genie-bootstrap.md`. |
| `npx @databricks/appkit docs "<query>"` | Read the reference files in `apps_lakebase/skills/<skill>/references/` |
| `bash apps_lakebase/skills/00-appkit-navigator/scripts/validate-prereqs.sh` | Skip in Genie, or run `sdk_preflight_app_folder(APP_BASE)` after scaffold (from `workshop-variables.md` Cell 3) |

#### Scaffold pattern (SDK — use this)

1. Read `apps_lakebase/skills/01-appkit-scaffold/SKILL.md` and `references/appkit-project-structure.md`.
2. `w.workspace.mkdirs(APP_BASE)`.
3. For each required file (`package.json`, `app.yaml`, `app.ts`, `vite.config.ts`, `client/index.html`, `server/server.ts`, …), **`write_file(f"{APP_BASE}/<path>", contents)`** following Section 6 patterns in this file.

**Optional — bulk paste:** If you have JSON `{"files":[{"path":"...","contents":"..."}]}` (e.g. exported from another environment), parse with `json.loads` and loop `write_file` as in `@apps_lakebase/gc-prompt-conversion/mcp-off-paste-genie-bootstrap.md`.

### npm / Node.js

| CLI Command | Genie Code Override |
|-------------|---------------------|
| `npm install @databricks/lakebase` | Add `@databricks/lakebase` to `package.json` via `write_file()`; set `app.yaml` env per `04-appkit-plugin-add` / Section 6 below — follow `setup_lakebase_gc.md` |
| `npm install` | NOT needed — platform runs `npm install` automatically at deploy time |
| `npm run build` | NOT runnable. Validate by reading file content. Build runs on the platform at deploy time. |
| `npm run typegen` | NOT runnable. Skip this step. Type generation runs at deploy time. |
| `npm run dev` | NOT available. Test the app in the browser after deploying to Databricks. |
| `npx tsc --noEmit` | NOT runnable. Validate TypeScript correctness by reviewing file content. |
| `npm ls @databricks/lakebase` | Read `package.json` via `base64.b64decode(w.workspace.export(path=APP_BASE+"/package.json").content).decode()` |

### Lakebase / PostgreSQL

| CLI Command | Genie Code Override |
|-------------|---------------------|
| `databricks postgres generate-database-credential <endpoint>` | `w.postgres.generate_database_credential(endpoint=ENDPOINT_NAME)` |
| `databricks postgres list-projects` | `list(w.postgres.list_projects())` |
| `psql -h <host> -U <user> -d <db>` | Connect via `psycopg.connect(conn_string)` in a notebook cell |

### File Operations

| CLI Command | Genie Code Override |
|-------------|---------------------|
| `echo "..." > /path/to/file` | `write_file(path, content)` — defined in `@apps_lakebase/gc-prompt-conversion/workshop-variables.md` or `one-ui-design-local.md`; see inline patterns below |
| `cat /path/to/file` | `base64.b64decode(w.workspace.export(path=WS_PATH).content).decode()` |
| `ls /path/to/dir` | `[obj.path for obj in w.workspace.list(path=WS_PATH)]` |
| `curl` for local testing | Test in the browser after deploying. Apps auth proxy blocks notebook requests. |

### Validate app config (replaces `appkit validate`)

After Cell 3 from `workshop-variables.md` is loaded:

```python
bad = sdk_preflight_app_folder(APP_BASE)
print(bad if bad else "sdk_preflight OK")
```

Full pre-deploy contract: **`validate_and_deploy(APP_NAME, APP_BASE)`** (includes preflight + deploy).

---

## Section 3: Variable Setup (Python, not bash)

Replace all bash variable derivation (`databricks current-user me`, `jq`, string manipulation) with this Python block:

```python
import base64
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.workspace import ImportFormat

w = WorkspaceClient()

email = spark.sql("SELECT current_user()").collect()[0][0]
prefix = email.split("@")[0].replace(".", "-")
parts = prefix.split("-")
APP_NAME = f"{parts[0]}-{parts[-1][0]}-booking-app"[:26]
DB_SCHEMA = APP_NAME.replace("-", "_")
REPO_ROOT = f"/Workspace/Users/{email}/v2v-in-geniecode/vibe-coding-workshop-template"
APP_BASE = f"{REPO_ROOT}/apps_lakebase/{APP_NAME}"

def write_file(path, content):
    """Write a plain text file (TypeScript, JSON, YAML, markdown) to the workspace."""
    parent = "/".join(path.split("/")[:-1])
    w.workspace.mkdirs(parent)
    w.workspace.import_(
        path=path,
        content=base64.b64encode(content.encode()).decode(),
        format=ImportFormat.AUTO,
        overwrite=True,
    )
    print(f"✓ Wrote {path.split('/')[-1]}")

print(f"APP_NAME:  {APP_NAME}")
print(f"DB_SCHEMA: {DB_SCHEMA}")
print(f"REPO_ROOT: {REPO_ROOT}")
print(f"APP_BASE:  {APP_BASE}")
```

---

## Section 4: Skill-Specific Overrides

### `00-appkit-navigator/SKILL.md`

| Skill instruction | Genie Code action |
|---|---|
| Run `validate-prereqs.sh` | `sdk_preflight_app_folder(APP_BASE)` after scaffold (Cell 3 from `workshop-variables.md`) |
| `npx @databricks/appkit docs "<query>"` | Read reference files in `apps_lakebase/skills/` |
| Route to "lakebase CLI" operations | Use `w.postgres.*` SDK methods instead |

### `01-appkit-scaffold/SKILL.md`

| Skill instruction | Genie Code action |
|---|---|
| `databricks --version` / CLI version check | Skip — no CLI |
| `node --version` / Node.js check | Skip — no Node.js |
| `databricks auth profiles` / profile selection | Skip — notebook auto-authenticates |
| `git clone` Agent Skills repo | Skip — skills are already in `apps_lakebase/skills/` |
| `npx @databricks/appkit scaffold` | Use SDK scaffold pattern in Section 2 (`write_file` + skill `01-appkit-scaffold`). |
| `npm install` after scaffold | Skip — platform runs `npm install` at deploy time |
| `grep "name:" app.yaml` config verification | Read via `w.workspace.export()` and check Python string |
| Any bash/shell command | STOP — use SDK equivalent from this file |

### `02-appkit-build/SKILL.md`

| Skill instruction | Genie Code action |
|---|---|
| `npm run typegen` | Skip entirely — type generation runs at deploy time |
| `npx tsc --noEmit` | Skip — validate TypeScript correctness by reviewing file content |
| `npm run dev` / `localhost:8000` | Skip — test after deploy in browser |
| `npx @databricks/appkit docs "<query>"` | Read `apps_lakebase/skills/02-appkit-build/references/` |
| Write/edit TypeScript files | `write_file(APP_BASE + "/path/to/file.ts", content)` |

### `03-appkit-deploy/SKILL.md`

Deploy is wrapped in a single helper: **`validate_and_deploy()`** from `@apps_lakebase/gc-prompt-conversion/workshop-variables.md` — **SDK preflight** (`sdk_preflight_app_folder`) plus **SDK** create / activate / deploy.

```python
deployment, app_url = validate_and_deploy(APP_NAME, APP_BASE)
```

> **CRITICAL — use ONLY `validate_and_deploy()`. Do NOT write custom deploy code.**
> - Do NOT import `AppDeploymentMode` — in this SDK version it is a string-based enum (`"SNAPSHOT"`), and any internal code that calls `.value` on it crashes with `AttributeError: 'str' object has no attribute 'value'`.
> - Do NOT call `w.apps.deploy_and_wait(...)` directly with a `mode=` parameter.
> - `validate_and_deploy()` does not pass `mode` (SNAPSHOT is the default) and is already tested to work correctly.

The helper:
1. Runs `sdk_preflight_app_folder(APP_BASE)` and raises if required files are missing
2. `w.apps.get(APP_NAME)` or `w.apps.create_and_wait(...)` if missing
3. `ensure_app_active(APP_NAME)` — polls compute until `ACTIVE` using `.state.name` (NOT `str(state)`)
4. `w.apps.deploy_and_wait(app_name=..., app_deployment=AppDeployment(source_code_path=APP_BASE))`
5. Returns `(deployment, app_url)`

> **Why one helper?** Keeps preflight, app creation, ACTIVE polling, and `deploy_and_wait` consistent across prompts and avoids `AppDeployment` kwarg mistakes.

> **Why wrap `source_code_path` in `AppDeployment(...)`?** `deploy_and_wait()` rejects `source_code_path` as a top-level kwarg — it must be inside `AppDeployment(source_code_path=...)`. The helper handles this for you.

| Skill instruction | Genie Code action |
|---|---|
| `databricks apps deploy` | `validate_and_deploy(APP_NAME, APP_BASE)` (see above) |
| `databricks apps get ... \| jq` | `app = w.apps.get(name=APP_NAME); print(app.compute_status.state.name, app.url)` |
| `databricks apps logs ... \| grep` | View in Databricks UI → Compute → Apps → click app → Logs |
| `npm run build` pre-flight | Skip — `sdk_preflight` + deploy catch missing files; platform builds at deploy time |
| `curl $APP_URL/api/...` | Test in browser only — auth proxy blocks notebook requests |

### `04-appkit-plugin-add/SKILL.md`

| Skill instruction | Genie Code action |
|---|---|
| `npx @databricks/appkit docs` | Read `apps_lakebase/skills/04-appkit-plugin-add/references/` |
| `npm install @databricks/lakebase` | Edit `package.json` / `app.yaml` via `write_file()` per `04-appkit-plugin-add` references and `setup_lakebase_gc.md` |
| `npm install @databricks/analytics` | Edit `package.json` `dependencies` section via `write_file()` |
| Any `npm install <package>` | Edit `package.json` directly — platform installs dependencies at deploy time |

#### Lakebase Infrastructure Provisioning

This workshop uses **Lakebase Autoscaling** (`w.postgres.*` API). The full provisioning code with all correct API calls is in `setup_lakebase_gc.md` Step 2 — follow that prompt directly.

Key API rules:
- `w.postgres.get_project(name="projects/{APP_NAME}")` — full path as `name`, NOT `project_id=APP_NAME`
- `w.postgres.create_project(..., project_id=APP_NAME)` — `project_id` is only valid on `create_project`
- The production branch endpoint (`primary`, NOT `ep-primary`) and `databricks_postgres` database are auto-created with the project
- `DB_SCHEMA` is a schema within `databricks_postgres`, NOT a separate Postgres database
- Resource binding always uses `AppResourcePostgres` (NOT `AppResourceDatabase`)

### `05-appkit-lakebase-wiring/SKILL.md`

| Skill instruction | Genie Code action |
|---|---|
| `npm run build` validation | Skip — validate by reading `server.ts` file content |
| `npm run dev` | Skip — test after first deploy in browser |
| `npx @databricks/appkit docs "lakebase"` | Read `apps_lakebase/skills/05-appkit-lakebase-wiring/references/` |
| Write `server.ts`, `app.ts`, hook files | `write_file(APP_BASE + "/path/to/file.ts", content)` |
| Local `curl` API testing | Test after deploy in browser |

**`app.ts` vs skill text:** The skill file may show `createApp({...})` without `await` or older `server({ autoStart: false })` snippets. **For Genie Code, always follow Section 6 below** — **`await createApp`** with `plugins: [lakebase(), server()]` and `onPluginsReady` (no `autoStart`, no `.then()`). This avoids `/api/*` 404s and a stuck **Mock Data** indicator after deploy.

**CRITICAL — Client Page Migration (mandatory, do not skip):**

After writing `server.ts`, these three client pages still import from `../data/mockData` and MUST be rewritten. Leaving them unchanged means the UI shows static hardcoded data even though Lakebase is connected and queries run successfully.

| Page | Required change |
|------|----------------|
| `client/src/pages/HomePage.tsx` | Remove `import { listings } from "../data/mockData"`; use `useLakebaseData<Listing>("/api/listings")` for featured listings |
| `client/src/pages/SearchResultsPage.tsx` | Remove `import { listings } from "../data/mockData"`; use `useLakebaseData<Listing>("/api/listings")` with client-side filtering |
| `client/src/pages/ListingDetailPage.tsx` | Remove `import { listings, reviews } from "../data/mockData"`; use `useLakebaseData` for single listing (`/api/listings/:id`) and reviews (`/api/listings/:id/reviews`) |

After migrating each page, **read it back** and verify the `mockData` import is gone.

**`ConnectionStatus` placement:** Import `ConnectionStatus` in `App.tsx` and render `<ConnectionStatus context="StayFindr" />` in the navbar alongside the nav links. This shows the live/mock/error indicator to users.

---

## Section 5: Session Recovery (WorkspaceClient bootstrap)

If a Genie Code session was reset (kernel recycled, new conversation, missing helpers), run the standard three-cell bootstrap. The full setup block (which defines `w`, `APP_*`, `write_file`, `sdk_preflight_app_folder`, `validate_and_deploy`, `verify_postgres_resource`, `ensure_app_active`) lives in `@apps_lakebase/gc-prompt-conversion/workshop-variables.md`:

```python
# Cell 1 — install packages (own cell, run first)
%pip install databricks-sdk --upgrade -q
```

```python
# Cell 2 — restart the kernel (recommended after SDK upgrade)
dbutils.library.restartPython()
```

```python
# Cell 3 — paste the FULL block from
# @apps_lakebase/gc-prompt-conversion/workshop-variables.md (no extra setup call)
```

> **Kernel restart:** If `%pip install` upgraded the SDK, restart before relying on new SDK symbols (e.g. `AppResourcePostgres`).

> **Single source of truth:** Cell 3 is duplicated across prompts only by reference — always paste from `workshop-variables.md` so helpers stay aligned.

---

## Section 6: AppKit Verified Patterns (Ground Truth)

These are the correct file contents. The skills may show slightly different versions — use these.

### `app.ts` — With Lakebase

```typescript
import { createApp, lakebase, server } from "@databricks/appkit";
import { registerRoutes } from "./server/server.js";

await createApp({
  plugins: [
    lakebase(),
    server(),
  ],
  async onPluginsReady(appkit) {
    await registerRoutes(appkit);
  },
});
```

**Rules:**
- `lakebase()` BEFORE `server()` in plugins array
- Use `onPluginsReady` callback for route registration
- **`await createApp(...)` is REQUIRED** — same reason as pre-Lakebase (see `app.ts` — Without Lakebase): without `await`, `tsx` can finish evaluating `app.ts` before AppKit finishes binding Express routes. Symptom: deploy succeeds, UI loads, but `/api/health` returns **404** or `{ "source": "mock" }` and `ConnectionStatus` never shows **Live Data**. Do **not** call `createApp({...})` as a bare expression.
- Do **not** use `.then()` chains or `appkit.server.start()` for this workshop pattern
- Do **not** use `server({ autoStart: false })` — current AppKit rejects `autoStart` with `ServerError: server({ autoStart }) has been removed` (see `troubleshooting_gc.md`). If you see that error, you are on an outdated snippet — use `server()` plus `onPluginsReady` as above.

### `app.ts` — Without Lakebase

```typescript
import { createApp, server } from "@databricks/appkit";

await createApp({
  plugins: [server()],
});
```

> **Critical:** Use `await createApp(...)` — NOT `export default createApp(...)`. The `export default` form is a Promise that tsx never awaits, so the server never starts. Use a **single import** from `"@databricks/appkit"` — do NOT split as `import createApp from "@databricks/appkit"` + `import { server } from "@databricks/appkit/server"`. The subpath `@databricks/appkit/server` does not exist and causes an immediate crash (`ERR_MODULE_NOT_FOUND`).

### `app.yaml` — Lakebase env section

```yaml
env:
  - name: LAKEBASE_ENDPOINT
    valueFrom: postgres
  - name: DB_SCHEMA
    value: "my_app_schema"
```

Use `valueFrom: postgres` (NOT `valueFrom: database`). The platform injects `PGHOST`, `PGPORT`, `PGDATABASE`, `PGSSLMODE` automatically.

### Map / location UI (Search + detail pages)

Workshop apps use `MapPlaceholder` — a **decorative** panel (emoji + short copy), **not** interactive map tiles (no Mapbox/Google SDK in scope).

| Symptom | Cause | Genie Code fix (prompts only — no skill edits) |
|---------|-------|--------------------------------------------------|
| "Map view" seems missing on Search | `MapPlaceholder` is rendered **below** `FilterSidebar` in a narrow left column; filters push it below the fold on laptop screens | In `SearchResultsPage.tsx`, render `<MapPlaceholder ... />` **above** `<FilterSidebar />`, **or** wrap the left column in a scroll container and make the map **sticky** at the top (`position: sticky; top: 80px`) so the "Map View" panel is always visible. |
| User expects a real map | `MapPlaceholder` is intentional stub UI | Either keep it and set user expectations in copy, **or** add a lightweight **static** map (e.g. OpenStreetMap `staticmap.openstreetmap.de` image URL built from `lat`/`lng`) without new npm dependencies. Do **not** block the workshop on full Leaflet/Mapbox setup. |
| No map on listing detail | Scaffold often omits a map block | If the PRD requires a map on the detail page, add a small map section using `listing.lat` / `listing.lng` from the API (reuse `MapPlaceholder` or a static OSM image). |

### `vite.config.ts` — Correct outDir

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  root: "client",
  plugins: [react()],
  build: {
    outDir: "dist",       // ← "dist" NOT "../dist"
    emptyOutDir: true,
  },
  server: {
    port: 3000,
  },
});
```

> **Critical:** With `root: "client"`, `outDir: "dist"` outputs to `client/dist/` — which is exactly where AppKit's server plugin looks for static files in production. Using `outDir: "../dist"` puts the build at `<APP_ROOT>/dist/` and AppKit cannot find it, causing the app to return empty responses.

### `package.json` — Build script

```json
"build": "(npm run typegen || true) && vite build"
```

The `|| true` prevents typegen failures from blocking the vite build.

### Resource Binding (Lakebase)

```python
from databricks.sdk.service.apps import (
    AppResource, AppResourcePostgres, AppResourcePostgresPostgresPermission
)

AppResource(
    name="postgres",
    postgres=AppResourcePostgres(
        branch=f"projects/{APP_NAME}/branches/production",
        database=db_path,
        permission=AppResourcePostgresPostgresPermission.CAN_CONNECT_AND_CREATE,
    )
)
```

Use `AppResourcePostgres` (NOT `AppResourceDatabase`). Resource name must be `"postgres"`.

---

## Quick Reference: Where to Find Reference Material

When a skill says `npx @databricks/appkit docs "<query>"`, read the corresponding file here instead:

| Skill | Reference Files |
|-------|----------------|
| `01-appkit-scaffold` | `apps_lakebase/skills/01-appkit-scaffold/references/appkit-project-structure.md` |
| `02-appkit-build` | `apps_lakebase/skills/02-appkit-build/references/llm-guardrails.md`, `design-quality.md` |
| `03-appkit-deploy` | `apps_lakebase/skills/03-appkit-deploy/references/app-management.md` |
| `04-appkit-plugin-add` | `apps_lakebase/skills/04-appkit-plugin-add/references/plugin-lakebase.md`, `plugin-analytics.md`, `plugin-genie.md`, `plugin-files.md` |
| `05-appkit-lakebase-wiring` | `apps_lakebase/skills/05-appkit-lakebase-wiring/references/database-design-guide.md`, `frontend-patterns.md`, `multi-table-example.md` |
| Optional MCP → SDK mapping (legacy) | `apps_lakebase/gc-prompt-conversion/MCP-appkit_tooling.md` |
| Troubleshooting | `apps_lakebase/gc-prompt-conversion/troubleshooting_gc.md` |
