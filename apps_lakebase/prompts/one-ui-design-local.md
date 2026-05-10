## Context

> **On ANY error:** STOP and read `@apps_lakebase/gc-prompt-conversion/troubleshooting_gc.md`; apply the matching fix. Do not improvise before consulting it.

Read **`@apps_lakebase/gc-prompt-conversion/gc-prompt-header.md`** first (environment, deploy contract, helpers).

You are implementing the **combined** workshop intent of the legacy **CLI** prompts archived in **`original-ui-one-design.md`**: (1) **product + UI + API stubs** from the PRD, design doc, and AppKit layout under **`APP_BASE`**; (2) **first deploy to Databricks Apps** with the same rigor as the old “Deploy” prompt (preflight, permissions, deploy, browser verify, state file) — **without** any local terminal, `npm run dev`, or `localhost` (**Genie = SDK + `write_file()` only**).

**Phases:** **A)** scaffold + mock-phase UI + `docs/ui_design.md` + **create workspace App** + SP grants + **`validate_and_deploy`** + browser smoke · **B)** PRD/UI gap pass, component polish, redeploy + **`.vibecoding-state.md`**.

**Important:** Do **not** assume a workspace App named **`APP_NAME`** exists. **Create it with the SDK after** the scaffold tree is on disk and **before** SP grants (grants require a real app + service principal).

**Refs (SDK + repo skills only — in this order):** `@apps_lakebase/gc-prompt-conversion/GENIE-CODE-OVERRIDES.md` · `@apps_lakebase/gc-prompt-conversion/workshop-variables.md` · `@apps_lakebase/skills/01-appkit-scaffold/SKILL.md` · `@apps_lakebase/skills/03-appkit-deploy/SKILL.md`

**Do not load or follow for this prompt:** `@mcp-appkit-tooling`, `MCP-appkit_tooling.md`, `@appkit-apps`, or any **MCP / tool-calling** path (`DatabricksMCPClient`, workspace `appkit_*` tools, or host tools such as **`appkit_get_app_status`**). Those are **out of scope**.

### CLI reference → Genie (read `original-ui-one-design.md` for full CLI text)

| Legacy CLI / local IDE step | Genie Code equivalent |
|-----------------------------|------------------------|
| `databricks auth login`, `jq` / `current-user` for `APP_NAME` | **`workshop-variables.md` Cell 3** — `email`, `APP_NAME`, `REPO_ROOT`, `APP_BASE` |
| `npm run build` / local server | **No** notebook `npm`. **`sdk_preflight_app_folder(APP_BASE)`** + platform **`npm install` / `vite build`** at **`deploy_and_wait`** time |
| `apps_lakebase/src/...`, `routes.py`, `app.py` | **AppKit:** `client/src/...`, **`server/server.ts`** via **`appkit.server.extend`**, **`app.ts`** — see **`01-appkit-scaffold`** + **Section 6** of **`GENIE-CODE-OVERRIDES.md`** |
| “UI must call APIs, no mocks” (original strict) | **This workshop (pre-Lakebase):** **`client/src/data/mockData.ts`** + **`/api/*`** stubs in **`server/server.ts`** where useful; full Lakebase-backed APIs come in **`wire_ui_to_lakebase_gc.md`** |
| `databricks apps deploy` / bundle deploy | **`validate_and_deploy(APP_NAME, APP_BASE)`** only (**SDP**) |
| Read `.vibecoding-state.md` before deploy | Same — optional **before Phase A** if the file exists (may pin `APP_NAME` / notes) |

**Hard rules**

- **No MCP AppKit:** no **`appkit_*`** tools. Status / deploy: **`validate_and_deploy`** + **`w.apps`** only.  
- **No CLI / shell / subprocess** in the notebook — **`GENIE-CODE-OVERRIDES.md`**.  
- **`@databricks/appkit`** has **no** `appkit build` / `appkit start`; platform runs install + build at deploy.  
- **Pre-Lakebase:** `await createApp({ plugins: [server()] })` **or** `registerRoutes` + `onPluginsReady` for `/api/*` — **never** `lakebase()` until **`wire_ui_to_lakebase_gc.md`**.  
- **Phase B:** do not change `app.ts` / `server/server.ts` except to fix validate/deploy failures; enhance **`client/`** in place.  
- **App name:** ≤26 chars, `[a-z0-9-]+` (hyphens, not underscores).

**Sequence:** **Next:** `setup_lakebase_gc.md` → `wire_ui_to_lakebase_gc.md` → `deploy_and_test_gc.md`

---

## Three-cell bootstrap (before Phase A — every kernel / Genie re-init)

Follow **`@apps_lakebase/gc-prompt-conversion/workshop-variables.md` § Three-Cell Bootstrap** exactly: **Cell 1** `%pip install databricks-sdk --upgrade -q` · **Cell 2** `dbutils.library.restartPython()` · **Cell 3** paste the **full** variable + helper block (defines `w`, `APP_*`, `write_file`, `sdk_preflight_app_folder`, `ensure_app_active`, `validate_and_deploy`, `verify_postgres_resource`).

> **Genie re-initializing clients** often starts **fresh Python**. If helpers are missing, re-run cells **1–2–3** in order.

**Deploy contract:** **(1)** Preflight files under **`APP_BASE`** (**Phase A step 5**). **(2)** **Create** the workspace App if missing (**Phase A step 6**). **(3)** Grant the app SP **`CAN_READ`** on `APP_BASE` and **`CAN_MANAGE`** on the app (**Phase A step 7**). **(4)** **`deployment, app_url = validate_and_deploy(APP_NAME, APP_BASE)`** (**Phase A step 8** — preflight again, `ensure_app_active`, deploy). See **`troubleshooting_gc.md`** (typegen / build / `TABLE_OR_VIEW` notes) and **`.assistant_instructions.md`**. **SDP only** — no deploy Jobs.

---

## Paths and naming

Derive **`APP_NAME`** from `current_user()` → `{firstname}-{lastinitial}-booking-app` (truncate to 26). Set **`REPO_ROOT`** (workspace checkout root) and **`APP_BASE`** = `{REPO_ROOT}/apps_lakebase/{APP_NAME}`.

Docs: **`{REPO_ROOT}/docs/design_prd.md`**, **`{REPO_ROOT}/docs/ui_design.md`**.

Optional: if **`{APP_BASE}/.vibecoding-state.md`** exists, read it **before Phase A** for pinned `APP_NAME`, URLs, or prior fixes (aligns with the old deploy prompt’s “read state first”).

---

# Phase A — Product, scaffold, mock UI, design doc, first deploy

0. **Optional state:** read **`{APP_BASE}/.vibecoding-state.md`** when present.  
1. Read **`{REPO_ROOT}/docs/design_prd.md`** — personas, happy-path journeys, core features.  
2. **Scaffold:** **`01-appkit-scaffold`** Steps 1–3 — implement the AppKit tree with **`write_file()`** under **`APP_BASE`** per the skill and **`GENIE-CODE-OVERRIDES.md`** Sections 2 / 6 (`w.workspace.mkdirs(APP_BASE)` first). Fix **`package.json` / `app.yaml`** per skill Steps 2 & 4 (`tsx`/`vite` in **dependencies**, Vite `root`/`outDir`, `client/index.html`, `tsconfig`, pre-Lakebase **`app.ts`**).  
3. **UI (first pass) + API stubs:** under **`client/src/`**: router root + `App` layout; pages **`HomePage`**, **`SearchResultsPage`**, **`ListingDetailPage`**, **`BookingPage`**, **`BookingConfirmationPage`**, **`AgentSearchPage`**; shared pieces under **`components/`**; **`client/src/data/mockData.ts`** for listing/search/booking mocks. In **`server/server.ts`**, add **`/api/*`** handlers (e.g. health, stub JSON) consistent with **`01-appkit-scaffold`** — pages may read mocks **and/or** call **`fetch('/api/...')`** where wired. **Nav shell:** include header/nav links for every major PRD journey (e.g. **Bookings** or “My bookings” if the PRD describes post-booking views) so **`wire_ui_to_lakebase_gc.md`** only swaps data sources instead of inventing IA.  

   **Must-haves for later polish:** SearchBar dates — check-in `min` = today, check-out ≥ check-in + 1, auto-bump checkout when needed; **`data-testid`** on interactive controls; **`BookingPage`** — name + email required, blur validation, button copy explains state (no silent disable). UX: warm palette, responsive, empty/loading/error on data-driven views.

4. Write **`{REPO_ROOT}/docs/ui_design.md`**: screens, nav (Home→Search→Detail→Booking→Confirm; Home→Agent), palette/typography, which components consume which mocks / APIs.  
5. **SDK preflight (replaces local `npm run build`):** run **`sdk_preflight_app_folder(APP_BASE)`** — fix all reported missing paths before creating the app. **Do not** run `npm` in the notebook; the **deploy** step runs the platform build. If **`troubleshooting_gc.md`** mentions typegen / warehouse noise for mock phase, apply it — do not block deploy on optional typegen-only failures called out there.  

   **Mock-only gate (must pass before step 6 — read back `app.ts` + `app.yaml` via `w.workspace.export` if unsure):**  
   - **`app.ts`:** imports **`createApp, server`** from **`@databricks/appkit`** only — **no** `lakebase`, **no** `plugins: [lakebase(), ...]`**. Use **`await createApp({ plugins: [server()], ... })`** with **`onPluginsReady`** only if **`server/server.ts`** registers **`/api/*`**; otherwise **`await createApp({ plugins: [server()] })`**. Canonical snippet: **`GENIE-CODE-OVERRIDES.md` Section 6 — “Without Lakebase”** — **ignore** “With Lakebase” until **`wire_ui_to_lakebase_gc.md`**.  
   - **`app.yaml`:** **no** env vars named **`LAKEBASE_*`**, **no** **`valueFrom: postgres`**, **no** Lakebase **`DB_SCHEMA`** line for this phase. **`resources`:** absent or **`[]`** — **no** postgres resource yet (**`setup_lakebase_gc.md`** adds binding).  
   - **Violating this gate** → **`ConfigurationError`** at runtime (plugin expects postgres creds that are not bound).

6. **Create the Databricks App (after scaffold, before SP grants):** **`w.apps.get(APP_NAME)`** — if missing, **`w.apps.create_and_wait(app=App(name=APP_NAME, description="StayFindr -- AppKit booking app", default_source_code_path=APP_BASE))`** with **`App`** from **`databricks.sdk.service.apps`** (already imported in Cell 3 if present). **Do not** grant until this succeeds.  
7. **Permissions:** per **`03-appkit-deploy`** *concepts* (use **SDK** grants, not CLI) — SP from **`w.apps.get(APP_NAME).service_principal_client_id`**; **`CAN_MANAGE`** on the **app**; **`CAN_READ`** on **`APP_BASE`**.  
8. **Validate + deploy:** **`deployment, app_url = validate_and_deploy(APP_NAME, APP_BASE)`** — preflight, **`ensure_app_active`**, **`deploy_and_wait`** with **`AppDeployment(source_code_path=APP_BASE)`**. For failure triage patterns, read **`03-appkit-deploy`** but **do not** execute shell commands from that skill.  
9. **Verify (before treating deploy as “done” or writing `.vibecoding-state.md`):**  
   - From **`validate_and_deploy`**: deployment succeeded + **`w.apps.get(APP_NAME).compute_status.state.name == "ACTIVE"`**.  
   - **Also** read **`app_status`** on the same object (e.g. **`w.apps.get(APP_NAME).app_status.state.name == "RUNNING"`**). Deployment **`SUCCEEDED`** with **ACTIVE** compute can still leave **`app_status`** **`CRASHED`** if **`app.ts` / `server/server.ts`** misbehaves at runtime.  
   - If **`app_status`** is not **`RUNNING`**, **do not** advance to Phase B state — open **`troubleshooting_gc.md`**, match logs (**`w.apps.get_logs`** / Apps UI **Logs** / **`/logz`** when signed in), **`write_file`** fixes, **`validate_and_deploy`** again until **`RUNNING`**.  
   - Print **`app_url`**; user smokes the **URL** in a browser (no `curl` from notebook). **No** **`appkit_get_app_status`**.

---

# Phase B — Polish, redeploy, state file

1. Re-read **`{REPO_ROOT}/docs/design_prd.md`**, **`{REPO_ROOT}/docs/ui_design.md`**, **`pages/`**, **`components/`**, **`mockData.ts`**, **`App.tsx`**, **`server/server.ts`**. List gaps vs PRD (dates/guests, filters, map stub, pagination, NL chips, agent UX, gallery, param flow, booking lookup, dedupe).  
2. **Batch 1 — components:** consolidate **SearchBar**, **ListingCard**, **PricingBreakdown**, **PhotoGallery**, **AmenityList**, **ReviewSummary**, **FilterSidebar**, **MapPlaceholder**; refactor pages; match **`ui_design.md`**. SearchBar: standard / natural / agent modes.  
3. **Batch 2 — search:** URL params, sidebar + map stub + **`ListingCard`** + pagination; natural type + chips; **`AgentSearchPage`** clarifying Q + rationale.  
4. **Batch 3 — booking path:** URL dates & guests; totals; **booking lookup** (`localStorage` or in-memory).  
5. **Permissions (if needed) + `validate_and_deploy(APP_NAME, APP_BASE)` + browser pass** as in Phase A.  
6. **Write / append `apps_lakebase/{APP_NAME}/.vibecoding-state.md`:** only after **Phase A step 9** shows **`app_status` RUNNING** (and redeploy loop if it was not). Record phase **`one-ui-design-local.md`** complete; **`APP_NAME`**, **`REPO_ROOT`**, deploy URL; batches done; leftovers; align with legacy deploy prompt’s “append resolved issues” requirement.

---

## Done when

- **A:** PRD read · scaffold per **`01-appkit-scaffold`** · six pages · mocks + API stubs · **`ui_design.md`** · SDK preflight OK · **workspace App created** · SP grants · **`validate_and_deploy`** → compute **ACTIVE** and **`app_status` RUNNING** (else **`troubleshooting_gc.md`** + redeploy) · smoke URL  
- **B:** Gaps addressed · eight shared components · search modes + agent UX · booking lookup · redeploy verified · **`.vibecoding-state.md`** updated  

**Next:** `setup_lakebase_gc.md`
