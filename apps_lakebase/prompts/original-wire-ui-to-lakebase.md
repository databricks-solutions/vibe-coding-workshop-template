## Context

You are a full-stack developer wiring a Lakebase PostgreSQL backend into an AppKit web application. Follow the `05-appkit-lakebase-wiring` skill for all reusable patterns (database design, API routes, frontend hooks, testing). Use the PRD to derive application-specific tables, routes, and seed data.

Approach: Start coding after reading the skill. Do not plan the entire implementation in advance — follow the skill steps sequentially and make decisions using the Decision Defaults table in the skill. If a decision is not covered there, pick the simpler option and move on.

Key requirements:

- The `@databricks/lakebase` package is installed and YAML files are configured (from the **Setup Lakebase** step), but `server.ts` has NOT been modified yet
- This step registers `lakebase()` in the plugins array AND writes all database code (DDL, routes, frontend hooks)
- Follow the `05-appkit-lakebase-wiring` skill for DDL patterns, API route architecture, frontend hooks, and testing
- Use `DB_SCHEMA` (from `.vibecoding-state.md` or `.env`) in all DDL, queries, and grants
- Do NOT deploy in this step — deployment happens in the **Deploy and E2E Test** step
- Local validation is `npm run build` only — `npm run dev` will crash because Lakebase env vars are not set until after the first deploy

This prompt is returned as-is for direct use in Cursor/Copilot. No LLM processing.

---

## Your Task

Wire the AppKit web application to a Lakebase database so the UI fetches data from Lakebase PostgreSQL via Express API routes. This step registers the `lakebase()` plugin in `server.ts` (moved here from Setup Lakebase to avoid runtime crashes in local dev) AND writes all database code. Lakebase is the sole data source — there is no SQL warehouse in this flow. Local validation is **`npm run build` only** — `npm run dev` will crash because Lakebase env vars (`LAKEBASE_ENDPOINT`, `PGHOST`) are not set until after the first deploy. Deployment and live data verification happen in the **Deploy and E2E Test** step.

**First:** Read `apps_lakebase/$APP_NAME/.vibecoding-state.md` if it exists — it contains resolved issues and variable values from prior phases (including `DB_SCHEMA` from the **Setup Lakebase** step).

**Workspace:** `https://adb-4101016551133680.0.azuredatabricks.net/`

**Working directory:** All app code and commands use the `apps_lakebase/` folder. The scaffolded AppKit app lives at `apps_lakebase/$APP_NAME/`.

**Prerequisite:** The **Setup Lakebase** step must be complete — the `@databricks/lakebase` package is installed, bundle resources are declared in `databricks.yml`, and `app.yaml` has `valueFrom: postgres`. Note: `server.ts` was NOT modified in that step — this step adds the `lakebase()` plugin registration along with all database code.

---

### Wire UI to Backend

Read `@apps_lakebase/skills/05-appkit-lakebase-wiring/SKILL.md` and follow **Steps 1-3**. Use your PRD to derive the specific tables, API routes, and seed data. Work incrementally: complete each skill step (DDL, routes, frontend) with a build gate between them. Do not design all tables, routes, and page changes in a single planning pass.

The skill covers:

- **Step 1** — Database schema design: PRD-to-schema methodology, PostgreSQL type conventions, idempotent DDL, count-check seed pattern. Also read `@apps_lakebase/skills/05-appkit-lakebase-wiring/references/database-design-guide.md` for normalization rules and data type guidance.
- **Step 2** — API routes: `server.extend()` pattern, `{ data, source }` response contract, mock fallback, health endpoint
- **Step 3** — Frontend wiring: `useLakebaseData` hook, `ConnectionStatus` component, defensive data handling (DECIMAL coercion, DATE coercion, snake_case mapping)

When deployed in the **Deploy and E2E Test** step, the Service Principal will run this code on first boot to create database objects.

---

### Build Gate

Before proceeding, verify the app builds cleanly:

```bash
cd apps_lakebase/$APP_NAME
npm run build   # Must pass with zero errors
```

Fix any TypeScript, ESM, or import errors now. Each deploy cycle takes 3-5 minutes — catching errors locally saves significant time.

---

### Local Build Validation

Follow **Step 4** of the `05-appkit-lakebase-wiring` skill. In summary:

1. `npm run build` — must pass with zero errors

> **Do NOT run `npm run dev`.** The `lakebase()` plugin throws `ConfigurationError` when `LAKEBASE_ENDPOINT` and `PGHOST` are not set. These env vars are provisioned by the platform on first deploy. `npm run build` is sufficient — it validates all TypeScript, imports, and bundling without executing the code. Runtime testing happens in the **Deploy and E2E Test** step.

---

### Checklist

- [ ] DDL and seed data are idempotent (skill Step 1)
- [ ] API routes return `{ data, source }` with mock fallback (skill Step 2)
- [ ] `useLakebaseData` hook and `ConnectionStatus` component created (skill Step 3)
- [ ] All static mock data replaced with API calls
- [ ] DECIMAL/DATE coercion and snake_case mapping handled
- [ ] `npm run build` passes (do NOT run `npm run dev` — Lakebase env vars not set yet)
- [ ] `.vibecoding-state.md` updated (see below)

**Before finishing**, append to `apps_lakebase/$APP_NAME/.vibecoding-state.md` with:
- Step name (`## Wire Lakebase Backend`)
- Key variable values (`DB_SCHEMA`, API endpoints created)
- Any resolved issues or workarounds encountered during this phase
