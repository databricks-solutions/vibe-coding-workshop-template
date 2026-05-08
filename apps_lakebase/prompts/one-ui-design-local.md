## Context

> **On ANY error:** STOP and read `@apps_lakebase/gc-prompt-conversion/troubleshooting_gc.md`; apply the matching fix. Do not improvise before consulting it.

Read **`@apps_lakebase/gc-prompt-conversion/gc-prompt-header.md`** first (environment, deploy contract, helpers).

Two phases in one run: **A)** scaffold + mock-data UI + `docs/ui_design.md` + deploy · **B)** audit vs PRD, polish interactions/components, redeploy + `.vibecoding-state.md`.

**Refs:** `@appkit-apps` · `@apps_lakebase/gc-prompt-conversion/GENIE-CODE-OVERRIDES.md` · `@apps_lakebase/gc-prompt-conversion/workshop-variables.md` · `@apps_lakebase/skills/01-appkit-scaffold/SKILL.md` · `@apps_lakebase/skills/03-appkit-deploy/SKILL.md`

**Hard rules**

- Genie/session: **Databricks SDK** + `write_file()` — **no** local CLI, npm, node, localhost, npx, curl in the notebook workflow  
- **`@databricks/appkit`** has **no** `appkit build` / `appkit start`; platform runs `npm install` + build at deploy time  
- **Pre-Lakebase:** `await createApp({ plugins: [server()] })` **or** `registerRoutes` + `onPluginsReady` if you add `/api/*` — **never** `lakebase()` until Wire Lakebase  
- **Phase B:** do not change `app.ts` / `server/server.ts` except to fix validate/deploy failures; enhance client code in place  
- **App name:** ≤26 chars, `[a-z0-9-]+`

**Sequence:** **Next:** `setup_lakebase_gc.md` → `wire_ui_to_lakebase_gc.md` → `deploy_and_test_gc.md`

---

## Three-cell bootstrap (before Phase A — every kernel / Genie re-init)

Follow **`@apps_lakebase/gc-prompt-conversion/workshop-variables.md` § Three-Cell Bootstrap** exactly: **Cell 1** `%pip install databricks-sdk --upgrade -q` · **Cell 2** `dbutils.library.restartPython()` · **Cell 3** paste the **full** variable + helper block (defines `w`, `APP_*`, `write_file`, `sdk_preflight_app_folder`, `ensure_app_active`, `validate_and_deploy`, `verify_postgres_resource`).

> **Genie re-initializing clients** often starts **fresh Python**. If helpers are missing, re-run cells **1–2–3** in order.

**Deploy contract:** Use **`deployment, app_url = validate_and_deploy(APP_NAME, APP_BASE)`** after permissions. Grant the **app’s service principal** **`CAN_READ`** on `APP_BASE` and **`CAN_MANAGE`** on the app (and directory grants as needed) so the platform build can read sources — see `@apps_lakebase/gc-prompt-conversion/troubleshooting_gc.md` and `.assistant_instructions.md`. **SDP only** — no deploy Jobs.

---

## Paths and naming

Derive **`APP_NAME`** from `current_user()` → `{firstname}-{lastinitial}-booking-app` (truncate to 26). Set **`REPO_ROOT`** (workspace checkout root) and **`APP_BASE`** = `{REPO_ROOT}/apps_lakebase/{APP_NAME}`.

Docs: **`{REPO_ROOT}/docs/design_prd.md`**, **`{REPO_ROOT}/docs/ui_design.md`**.

Optional: read **`{APP_BASE}/.vibecoding-state.md`** before Phase B if present.

---

# Phase A — Build (mock), design doc, first deploy

1. Read **`{REPO_ROOT}/docs/design_prd.md`**.  
2. **Scaffold:** `01-appkit-scaffold` Steps 1–3 — implement the AppKit tree with **`write_file()`** under `APP_BASE` per the skill and **`GENIE-CODE-OVERRIDES.md`** Section 2 / Section 6 (`mkdirs` first). Scaffold output for `package.json` / `app.yaml` is often wrong → **Steps 2 & 4** of same skill (`tsx`/`vite` in **dependencies**, `vite` root/outDir, `index.html`, `tsconfig`, pre-Lakebase `app.ts`).  
3. **UI (first pass):** `client/src` with router root + `App` layout; pages `HomePage`, `SearchResultsPage`, `ListingDetailPage`, `BookingPage`, `BookingConfirmationPage`, `AgentSearchPage`; stub or real versions of shared pieces under `components/`; **`client/src/data/mockData.ts`** for all mocks.  

   **Must-haves for later polish:** SearchBar dates — check-in `min` = today, check-out ≥ check-in + 1, auto-bump checkout when needed; **`data-testid`** on interactive controls; **`BookingPage`** — name + email required, blur validation, button copy explains state (no silent disable). UX: warm palette, responsive, empty/loading/error on data-driven views.

4. Write **`{REPO_ROOT}/docs/ui_design.md`**: screens, nav (Home→Search→Detail→Booking→Confirm; Home→Agent), palette/typography, which components consume which mocks.  
5. **Permissions (before first deploy):** per `03-appkit-deploy` / overrides — grant the **app service principal** **`CAN_MANAGE`** on the **app** and **`CAN_READ`** (minimum) on **`APP_BASE`** so deploy-time build succeeds.  
6. **Validate + deploy:** `deployment, app_url = validate_and_deploy(APP_NAME, APP_BASE)` (SDK preflight, create-if-missing, `ensure_app_active`, `deploy_and_wait` with **`AppDeployment(source_code_path=APP_BASE)`**).  
7. **Verify:** confirm deployment terminal state from the return value; **`compute_status.state.name`** is `"ACTIVE"` inside the helper path — smoke the printed **URL** in the browser (not `curl` from the notebook).

---

# Phase B — Polish

1. Re-read **`{REPO_ROOT}/docs/design_prd.md`**, **`{REPO_ROOT}/docs/ui_design.md`**, all **`pages/`**, **`components/`**, **`mockData.ts`**, **`App.tsx`** under `APP_BASE`. List gaps vs PRD (dates/guests interactive, amenity filters, map on results, pagination, NL chips, agent clarifying Q + “why” blurbs, gallery not emoji-only, param flow search→booking, booking lookup, shared components deduped).  
2. **Batch 1 — components:** consolidate **SearchBar**, **ListingCard**, **PricingBreakdown**, **PhotoGallery**, **AmenityList**, **ReviewSummary**, **FilterSidebar**, **MapPlaceholder**; refactor pages to import them; match palette from **`ui_design.md`**. SearchBar exposes **three modes:** standard (`/search?city&checkin&checkout&guests`), natural (`type=natural&q=…`), agent (go to **`/agent`**).  
3. **Batch 2 — search:** Home uses shared SearchBar + URL params. Results: read params, sidebar + map stub + **`ListingCard`** + pagination (~8/page); **`type=natural`** → trivial keyword parse → editable chips. **`AgentSearchPage`:** one clarifying question before listings; short rationale per suggestion; multi-turn OK.  
4. **Batch 3 — booking path:** ListingDetail / Booking / Confirmation consume URL dates & guests; dynamic nights and totals. **Booking lookup** (Home or **`/booking-lookup`**): mock `localStorage` or in-memory map by reference.  
5. **Permissions (if needed) + `validate_and_deploy(APP_NAME, APP_BASE)` + browser pass** as in Phase A.  
6. **Write `.vibecoding-state.md`:** phase `one-ui-design-local.md` complete, batches done, leftovers, deploy status (`validate_and_deploy` / SDK preflight).

---

## Done when

- **A:** Scaffold fixed per skill · six pages · mocks · `ui_design.md` · SP grants · `validate_and_deploy` → ACTIVE · smoke OK  
- **B:** Gap list addressed · eight shared components in use · search modes + NL chips + agent UX · full param flow · booking lookup · redeploy verified · state file updated  

**Next:** `setup_lakebase_gc.md`
