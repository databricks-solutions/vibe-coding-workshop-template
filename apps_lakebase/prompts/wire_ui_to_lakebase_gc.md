## Context

> **On ANY error:** STOP and read `@apps_lakebase/gc-prompt-conversion/troubleshooting_gc.md`. Match the error message or symptom in the tables. Apply the fix exactly as described. Do NOT improvise a workaround before checking the troubleshooting reference.

You are Genie Code, an AI assistant on the Databricks workspace. You are wiring a Lakebase PostgreSQL backend into an AppKit web application. Follow the `05-appkit-lakebase-wiring` skill for all reusable patterns (database design, API routes, frontend hooks). Use the PRD to derive application-specific tables, routes, and seed data.

Approach: Start coding after reading the skill. Do not plan the entire implementation in advance — follow the skill steps sequentially and make decisions using the Decision Defaults table in the skill. If a decision is not covered there, pick the simpler option and move on.

Key requirements:

- The `@databricks/lakebase` dependency is in `package.json` and `app.yaml` has `LAKEBASE_ENDPOINT` (`valueFrom: postgres`) and `DB_SCHEMA` (from the **Setup Lakebase** step), but `server.ts` has NOT been modified yet
- This step registers `lakebase()` in `app.ts` AND rewrites `server/server.ts` with DDL, seed data, and API routes
- Follow the **resolved AppKit** pattern: `appkit.server.extend((app) => { ... })` inside `export async function registerRoutes(appkit)` — access SQL via `appkit.lakebase.query()` (not `ctx.lakebase.getPool()` on the `server` import)
- Use `DB_SCHEMA` (from `.vibecoding-state.md`) in all DDL, queries, and grants
- Do NOT deploy in this step — deployment happens in `deploy_and_test_gc.md`
- There is no `npm run build` or `npm run dev` in the notebook — validation is through file content review only. **Compile gate:** the first successful **`deploy_and_test_gc.md`** deploy runs platform `npm install` + build; treat that as the TypeScript gate. A facilitator may optionally run **`npm run build`** locally to catch errors earlier.

**Environment:** Genie Code on Databricks workspace (serverless). No CLI, no npm, no Node.js, no TypeScript compiler. Use file tools for code editing and `executeCode` for Python.

**Prompt sequence:** `one-ui-design-local.md` → `setup_lakebase_gc.md` → **this file** → `deploy_and_test_gc.md` (see `@apps_lakebase/prompts/README.md`).

---

### Session Recovery: SDK bootstrap

> **Skip** if `w`, `APP_BASE`, and `write_file` are still in scope. If the session was reset, re-run **`@apps_lakebase/gc-prompt-conversion/workshop-variables.md`** three-cell bootstrap.

> **Troubleshooting:** See `@apps_lakebase/gc-prompt-conversion/troubleshooting_gc.md` for error resolution.

---

## Your Task

Wire the AppKit web application to a Lakebase database so the UI fetches data from Lakebase PostgreSQL via Express API routes. This step registers the `lakebase()` plugin and writes all database code (DDL, seed data, API routes). Lakebase is the sole data source — there is no SQL warehouse in this flow.

**First:** Read `apps_lakebase/{APP_NAME}/.vibecoding-state.md` — it contains variable values from prior phases (including `DB_SCHEMA`).

**Working directory:** All app files are under `apps_lakebase/{APP_NAME}/` within the repo.

**Prerequisite:** The **Setup Lakebase** step must be complete — `@databricks/lakebase` is in `package.json`, `app.yaml` has `LAKEBASE_ENDPOINT` (`valueFrom: postgres`) and `DB_SCHEMA`, the Lakebase instance is `AVAILABLE`, and a `postgres`-type resource is bound to the app. `server.ts` was NOT modified in that step.

---

### Wire UI to Backend

Read `@apps_lakebase/skills/05-appkit-lakebase-wiring/SKILL.md` and follow **Steps 1-3**. Use the PRD to derive the specific tables, API routes, and seed data. Work incrementally: complete each skill step (DDL, routes, frontend) with a verification pass between them.

The skill covers:

- **Step 1** — Database schema design: PRD-to-schema methodology, PostgreSQL type conventions, idempotent DDL, count-check seed pattern. Also read `@apps_lakebase/skills/05-appkit-lakebase-wiring/references/database-design-guide.md` for normalization rules and data type guidance.
- **Step 2** — API routes: `appkit.server.extend((app) => { ... })` via `registerRoutes(appkit)`, `{ data, source }` response contract, mock fallback, health endpoint (`/api/health` returns wrapped shape — see table below)
- **Step 3** — Frontend wiring: `useLakebaseData` hook, `ConnectionStatus` component, defensive data handling (DECIMAL coercion, DATE coercion, snake_case mapping)

When deployed in the **Deploy and E2E Test** step, the Service Principal will run this code on first boot to create database objects.

---

### App entrypoint (`app.ts`): `onPluginsReady` pattern

After wiring Lakebase, the app uses `onPluginsReady` to register routes before the server auto-starts. **Plugin order is always** `lakebase()` **before** `server()` so `appkit.lakebase` is available when routes register.

```ts
import { createApp, server, lakebase } from "@databricks/appkit";
import { registerRoutes } from "./server/server.js";

await createApp({
  plugins: [lakebase(), server()],
  async onPluginsReady(appkit) {
    await registerRoutes(appkit);
  },
});
```

### Server module (`server/server.ts`): `registerRoutes` + `appkit.server.extend`

Use a named `registerRoutes` function — do not call `server.extend` on the imported `server` plugin function.

```ts
import type { Express } from "express";

export async function registerRoutes(appkit: any) {
  appkit.server.extend((app: any) => {
    // ... mount routes on app; use appkit.lakebase.query() for SQL
  });
}
```

### Required API Routes

All routes go inside a single `appkit.server.extend((app) => { ... })` callback (inside `registerRoutes`):

| Route | Method | Purpose |
|-------|--------|---------|
| `/api/health` | GET | Lakebase connectivity check — returns `{ data: [{ status: "connected" }], source: "live" }` (or `source: "mock"` on fallback) |
| `/api/listings` | GET | List all listings with optional filters (city, type, price, guests) |
| `/api/listings/:id` | GET | Single listing by ID |
| `/api/listings/:id/reviews` | GET | Reviews for a listing |
| `/api/bookings` | POST | Create booking (insert into bookings table) |
| `/api/bookings/:id` | GET | Booking details with listing info via JOIN |

> **Canonical workshop health URL:** implement **`GET /api/health`** only (returns `{ data: [{ status: "connected" }], source: "live" | "mock" }` per table above). Do **not** register **`/api/health/lakebase`** — some external CLI samples use that path; **`deploy_and_test_gc.md`** and **`troubleshooting_gc.md`** assume **`/api/health`**.

---

### Verification

Since there is no `npm run build` in Genie Code, verify by:

1. **Read `app.ts`** — confirm **`await createApp({ plugins: [lakebase(), server()], async onPluginsReady(appkit) { await registerRoutes(appkit); } })`** (lakebase before server; **`await` on `createApp` required**)
2. **Read `server/server.ts`** — confirm `export async function registerRoutes(appkit)` with a single `appkit.server.extend((app) => { ... })`, idempotent DDL, count-check seed, all routes return `{ data, source }` (health uses wrapped `data` array — see table), `DB_SCHEMA` from `process.env.DB_SCHEMA`
3. **Read `server/mock-data.ts`** — confirm camelCase fallback data arrays exist
4. **Cross-check** — API route paths match URLs that client pages will call; nav includes **Bookings** (or equivalent) if the PRD describes that journey
5. **Read `client/src/` pages** — every data-fetching page imports **`ConnectionStatus`** and passes **`source`** from **`useLakebaseData`** (see **`05-appkit-lakebase-wiring/references/frontend-patterns.md`** Step 3b)
6. **List all files** — confirm expected files exist

---

### Checklist

- [ ] `app.ts` uses **`await createApp({ plugins: [lakebase(), server()], async onPluginsReady(appkit) { await registerRoutes(appkit); } })`** — lakebase before server, no `autoStart`, no `.then()`, no `appkit.server.start()`
- [ ] `server/server.ts` exports `registerRoutes` with a single `appkit.server.extend((app) => {...})` call (not `server.extend` on the plugin import)
- [ ] DDL creates schema and all tables with `IF NOT EXISTS` (idempotent)
- [ ] Seed data uses count-check pattern (not `ON CONFLICT`)
- [ ] All API routes return `{ data, source }` with mock fallback
- [ ] **`GET /api/health`** exists (canonical path — not `/api/health/lakebase`) and checks Lakebase connectivity with wrapped `{ data, source }`
- [ ] **`ConnectionStatus`** at top of **every** page that calls **`useLakebaseData`**; hook **`source`** passed through
- [ ] **Navigation** includes PRD journeys (e.g. **Bookings** list/detail or entry point) wired to real **`/api/*`** routes
- [ ] `server/mock-data.ts` created with camelCase fallback data
- [ ] `DB_SCHEMA` used via `process.env.DB_SCHEMA` in all SQL (never hardcoded)
- [ ] All files verified via spot-checks
- [ ] `.vibecoding-state.md` updated with: step name, variables, files created/modified

**Previous step:** `setup_lakebase_gc.md` | **Next step:** `deploy_and_test_gc.md`
