# Workshop Execution Steps

> **Purpose:** Step-by-step runbook for executing the Vibe-Coding Workshop from pre-requisites through final E2E verification. Two tracks are supported — choose the one matching your environment.

---

## Track Selection

| Track | Environment | Tools | Pre-reqs |
|-------|-------------|-------|----------|
| **Genie Code** | Databricks notebooks (serverless) | Databricks SDK (`WorkspaceClient`, `write_file`, `validate_and_deploy`) | No local IDE, CLI, Node.js, or npm needed |
| **CLI** | Local AI-powered IDE (Cursor, Windsurf, VS Code) | Databricks CLI, npm, bash | Local toolchain required |

---

## Pre-Requisites — Admin (Both Tracks)

Complete these **before** the workshop. Owner: Workspace Admin / Account Admin.

| # | Step | Est. Time | Details |
|---|------|-----------|---------|
| 1 | **Workspace access for participants** | 1–2 days | Create AD group (e.g., `workshop-participants`), assign all attendees, verify login 48h before |
| 2 | **Unity Catalog — catalog + schema creation** | 30 min | Create workshop catalog; `GRANT USE CATALOG` and `GRANT CREATE SCHEMA` to the AD group |
| 3 | **Serverless SQL Warehouse** | 15 min | Create/share a Serverless SQL Warehouse; grant `CAN USE` to the AD group |
| 4 | **Serverless General Compute (budget policy)** | 15 min | Enable serverless compute; create a budget policy and assign to the AD group |
| 5a | **Enable Databricks Apps** | 15 min | Workspace Settings > Compute > Databricks Apps; grant AD group the **Consumer** entitlement |
| 5b | **Enable Lakebase** | 15 min | Workspace Settings > Compute > Lakebase; grant catalog permissions |
| 6a | **Create service principal** | 10 min | Account Console > Service Principals > Add (note the Application ID = `client_id`) |
| 6b | **Generate OAuth client secret** | 5 min | SP > Secrets tab > Generate secret (copy immediately — shown only once) |
| 6c | **(Optional) MCP app access** | 10 min | Only if running `mcp-appkit-skill`: Workspace User role + `Can Use` on that app — **skip** for SDK-only Genie |
| 6d | **Create secret scope + store credentials** | 10 min | **Optional** for MCP-only flows; SDK-only Genie uses notebook identity — skip unless you use `mcp-setup-gc.md` |
| 6e | **Verify Genie bootstrap** | 5 min | Participants run `workshop-variables.md` three-cell bootstrap; confirm `w` + `validate_and_deploy` exist |

---

## Pre-Requisites — Participant (CLI Track Only)

Genie Code participants skip items 7–12 entirely.

| # | Step | Est. Time |
|---|------|-----------|
| 7 | Install an AI-powered IDE (Cursor recommended) | 15 min |
| 8 | Provision IDE licenses / AI model access | Varies |
| 9 | Access to Claude Sonnet 4.5 or higher | 10 min |
| 10 | Install Databricks CLI | 10 min |
| 11 | Install Node.js v22+ and Git | 10 min |
| 12 | Authenticate to workspace (`databricks configure --profile DEFAULT`) and validate connectivity | 10 min |

---

## Pre-Requisites — Participant (Genie Code Track)

| # | Step | Est. Time | Details |
|---|------|-----------|---------|
| A | **Log in to workspace** | 2 min | Confirm you can access the Databricks workspace URL |
| B | **Verify SDK bootstrap** | 5 min | Run three cells from `apps_lakebase/gc-prompt-conversion/workshop-variables.md` — `%pip install databricks-sdk`, `restartPython`, paste Cell 3; confirm `w`, `APP_BASE`, `validate_and_deploy` exist |

---

---

## Workshop Execution — Genie Code Track

Each step is a separate Genie Code conversation. Use the `_gc.md` prompt files in `apps_lakebase/prompts/`.

### Step 1: Generate PRD

| | |
|---|---|
| **Prompt file** | `apps_lakebase/prompts/generate_prd_gc.md` |
| **Goal** | Generate a Product Requirements Document for StayFindr |
| **Output** | `docs/design_prd.md` (repo root) — personas, user journeys, features, data requirements |
| **Checkpoint** | PRD exists and covers all required sections |

---

### Step 2: Scaffold, UI, mock deploy (single prompt)

| | |
|---|---|
| **Prompt file** | `apps_lakebase/prompts/one-ui-design-local.md` |
| **Goal** | Scaffold a blank AppKit project via skills + `write_file()`, build and polish the UI from the PRD with mock data, deploy to Databricks Apps |
| **Skills used** | `01-appkit-scaffold`, `02-appkit-build`, `03-appkit-deploy` |
| **Key actions** | Read scaffold skill → `write_file()` tree under `APP_BASE` → mock UI → `validate_and_deploy(APP_NAME, APP_BASE)` (SDP only) |
| **Output** | Running Databricks App at a public HTTPS URL serving mock data; `docs/ui_design.md` |
| **Checkpoint** | App is `RUNNING`; UI loads in browser; mock data renders on all pages |

---

### Step 3: Setup Lakebase

| | |
|---|---|
| **Prompt file** | `apps_lakebase/prompts/setup_lakebase_gc.md` |
| **Goal** | Install `@databricks/lakebase` package, configure bundle resources in `databricks.yml` and `app.yaml` |
| **This is config-only** | `server.ts` is NOT modified. Plugin registration happens in Step 4 |
| **Key actions** | `npm install @databricks/lakebase` → add `postgres_projects` to `databricks.yml` → add `valueFrom: postgres` and `DB_SCHEMA` to `app.yaml` |
| **Output** | YAML configs ready for Lakebase auto-provisioning on next deploy |
| **Checkpoint** | `@databricks/lakebase` in `package.json`; `postgres_projects` in `databricks.yml`; `LAKEBASE_ENDPOINT` + `DB_SCHEMA` in `app.yaml`; `npm run build` passes |

---

### Step 4: Wire UI to Lakebase

| | |
|---|---|
| **Prompt file** | `apps_lakebase/prompts/wire_ui_to_lakebase_gc.md` |
| **Goal** | Register `lakebase()` plugin in `server.ts`, create DDL + seed data, build API routes, replace all mock data with API calls |
| **Skills used** | `05-appkit-lakebase-wiring` |
| **Key actions** | Add `lakebase()` to plugins → write idempotent DDL + seed SQL → build Express API routes with `{ data, source }` response contract + mock fallback → create `useLakebaseData` hook + `ConnectionStatus` component → replace all static arrays with API calls |
| **Output** | Fully wired app code; all endpoints return `"source": "mock"` locally (live data after deploy) |
| **Checkpoint** | `npm run build` passes; all static mock data replaced with API calls; DDL is idempotent |

> **Note:** `npm run dev` will crash locally because Lakebase env vars aren't set until after deployment. Use `npm run build` as the validation gate.

---

### Step 5: Deploy and E2E Test with Lakebase

| | |
|---|---|
| **Prompt file** | `apps_lakebase/prompts/deploy_and_test_gc.md` |
| **Goal** | Deploy the Lakebase-wired app; SP creates DB objects on first boot; run full E2E verification |
| **Skills used** | `03-appkit-deploy` |
| **Key actions** | Two-phase deploy (Phase 1 creates Lakebase project, Phase 2 binds resource) → verify `RUNNING` state → test all API endpoints with bearer token → check logs for healthy Lakebase connections → fix errors (up to 3 iterations) → idle connection test (3–5 min) |
| **Output** | Production app with live Lakebase data |
| **Checkpoint** | All 7 verification tests pass: |

**Final verification:**

| Test | Expected |
|------|----------|
| App deployed and RUNNING | `compute_status.state: ACTIVE` |
| UI loads in browser | React app rendered (not error page) |
| `/api/health/lakebase` | `{ "status": "connected", "source": "live" }` |
| All data endpoints | `"source": "live"` with real data |
| App logs | No errors; `ConnectionPool OK` |
| Idle test (5 min) | Still `"source": "live"` after wake |
| ConnectionStatus UI | Shows "Live Data" |

---

---

## Workshop Execution — CLI Track

Each step is a separate agent conversation in your local IDE. Use the prompt templates from `apps_lakebase/Instructions.md`.

### Step 1: Scaffold, Build, and Test Locally

| | |
|---|---|
| **Reference** | `apps_lakebase/Instructions.md` — Step 1 |
| **Goal** | Authenticate, scaffold a blank AppKit project, build UI with mock data from PRD, test at `localhost:8000` |
| **Skills used** | `01-appkit-scaffold`, `02-appkit-build` |
| **Sub-steps** | 1.1 Authenticate + set `APP_NAME` → 1.2 Install agent skills + scaffold → 1.3 Read PRD → 1.4 Build app with mock data → 1.5 Create `ui_design.md` → 1.6 Test locally |
| **Checkpoint** | `npm run dev` runs; UI loads at `localhost:8000`; all pages render with mock data |

---

### Step 2: Deploy (Mock Data)

| | |
|---|---|
| **Reference** | `apps_lakebase/Instructions.md` — Step 2 |
| **Goal** | Deploy the locally-tested app to Databricks Apps with a public HTTPS URL |
| **Skills used** | `03-appkit-deploy` |
| **Sub-steps** | 2.1 Derive app name + set profile → 2.1b Pre-flight build check → 2.2 Deploy via skill |
| **Checkpoint** | App is `RUNNING`; UI loads at app URL; mock data renders correctly |

---

### Step 3: Setup Lakebase

| | |
|---|---|
| **Reference** | `apps_lakebase/Instructions.md` — Step 3 |
| **Goal** | Install Lakebase package, configure bundle resources (config-only — no `server.ts` changes) |
| **Sub-steps** | 3.1 Set `DB_SCHEMA` → 3.2 `npm install @databricks/lakebase` → 3.3 Add `postgres_projects` to `databricks.yml` → 3.4 Add env vars to `app.yaml` → 3.5 Verify |
| **Checkpoint** | Package installed; YAML configs correct; `npm run build` passes |

---

### Step 4: Wire Lakebase Backend

| | |
|---|---|
| **Reference** | `apps_lakebase/Instructions.md` — Step 4 |
| **Goal** | Register `lakebase()` plugin, create DDL/seed data, build API routes, replace mock data with API calls |
| **Skills used** | `05-appkit-lakebase-wiring` |
| **Sub-steps** | Follow skill Steps 1–4: DB schema design → API routes with mock fallback → Frontend wiring (`useLakebaseData` + `ConnectionStatus`) → Build gate (`npm run build`) |
| **Checkpoint** | Build passes; all mock data replaced with API calls; endpoints return `"source": "mock"` locally |

---

### Step 5: Deploy and E2E Test with Lakebase

| | |
|---|---|
| **Reference** | `apps_lakebase/Instructions.md` — Step 5 |
| **Goal** | Deploy Lakebase-wired app, SP creates DB objects, run full E2E verification |
| **Skills used** | `03-appkit-deploy` |
| **Sub-steps** | 5.1 Validate Lakebase config → 5.2 Deploy (two-phase) → 5.3 Test all APIs with bearer token → 5.4 Check logs → 5.5 Fix errors (up to 3 iterations) → 5.6 Idle connection test → 5.7 Grant local dev permissions (optional) |
| **Checkpoint** | 7/7 verification tests pass (same table as Genie Code track above) |

---

## Quick Reference — Prompt File Map (Genie Code Track)

| Step | Prompt File | Description |
|------|-------------|-------------|
| Pre-req B | `apps_lakebase/gc-prompt-conversion/workshop-variables.md` (Cells 1–3) | Verify SDK bootstrap (`w`, `validate_and_deploy`) — optional MCP: `mcp-setup-gc.md` |
| 1 | `apps_lakebase/prompts/generate_prd_gc.md` | Generate PRD for StayFindr |
| 2 | `apps_lakebase/prompts/one-ui-design-local.md` | Scaffold, UI, mock deploy (single prompt) |
| 3 | `apps_lakebase/prompts/setup_lakebase_gc.md` | Lakebase config (YAML only) |
| 4 | `apps_lakebase/prompts/wire_ui_to_lakebase_gc.md` | Wire frontend to Lakebase backend |
| 5 | `apps_lakebase/prompts/deploy_and_test_gc.md` | Final deploy + E2E verification |

---

## Session State

Each step should read `.vibecoding-state.md` (if it exists) from the app root at the start, and append resolved issues, variable values, and workarounds at the end. This prevents re-discovery across steps (~7 min + ~10K tokens saved per session).
