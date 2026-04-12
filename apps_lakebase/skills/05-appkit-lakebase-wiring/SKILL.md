---
name: 05-appkit-lakebase-wiring
description: >
  Wire a Lakebase PostgreSQL backend into an existing AppKit project. Covers database
  schema design from a PRD, idempotent DDL, Express API routes with mock fallback,
  React data hooks, and local testing. PRD-independent patterns that apply to any
  AppKit + Lakebase app. Use after registering the Lakebase plugin via
  04-appkit-plugin-add. Triggers on "wire lakebase", "lakebase backend", "CRUD API",
  "lakebase tables", "DDL", "database schema design", "useLakebaseData",
  "mock fallback", "ConnectionStatus", "replace mock data", "connect frontend to
  backend", "API-backed data", "replace static data with database".
license: Apache-2.0
compatibility: Requires Lakebase plugin registered via 04-appkit-plugin-add, Node.js v22+, Databricks CLI >= 0.295.0
allowed-tools: Bash(databricks:*) Bash(npm:*) Bash(curl:*) Bash(node:*) Read
metadata:
  author: prashanth subrahmanyam
  version: "1.0.0"
  domain: apps
  role: lakebase-wiring
  standalone: false
  last_verified: "2026-04-12"
  volatility: medium
  upstream_sources:
    - https://databricks.github.io/appkit/docs/plugins/lakebase
    - https://github.com/databricks/databricks-agent-skills
---

# Wire Lakebase Backend into AppKit

Design a database schema from a PRD, build Express API routes with mock fallback, wire the React frontend to live data, and verify locally.

## When to Use

- Wiring a Lakebase PostgreSQL backend into an AppKit app that already has the plugin registered
- Designing database tables from a PRD or feature spec
- Building CRUD API routes with `server.extend()`
- Replacing static mock data with API-backed data fetching
- Adding a health endpoint and ConnectionStatus indicator

**Not for registering the plugin.** Use `04-appkit-plugin-add` to install and configure the Lakebase plugin first.
**Not for deploying.** Use `03-appkit-deploy` after wiring is complete.

---

## Before You Begin

**Prerequisites — verify these before proceeding:**

1. The Lakebase plugin is registered in `server/server.ts` (via `04-appkit-plugin-add`)
2. Environment variables are configured in `.env` and `app.yaml` (`LAKEBASE_ENDPOINT`, `PGHOST`, `PGDATABASE`, `PGSSLMODE`, `DB_SCHEMA`)
3. `DB_SCHEMA` is set to a user-scoped name derived from `$APP_NAME` (hyphens → underscores, e.g., `prashanth_s_booking_app`)
4. `npm run build` passes with the Lakebase plugin imported

**Read the database design reference first:** Before designing your schema, read [references/database-design-guide.md](references/database-design-guide.md) for normalization rules and PostgreSQL conventions.

**Upstream docs (always check for latest):**

```bash
npx @databricks/appkit docs "lakebase"
```

---

## Step 1: Design the Database Schema

Derive your database schema from the PRD. This step produces DDL and seed data in `server/server.ts`.

### 1a. Identify Entities from the PRD

Read the PRD and extract:

- **Entities** — each major noun becomes a table (e.g., `bookings`, `listings`, `users`)
- **Attributes** — each property becomes a column
- **Relationships** — identify 1:N (FK) and M:N (junction table) relationships
- **Data types** — map PRD fields to PostgreSQL types using the conventions below

### 1b. PostgreSQL Type Conventions

| PRD Concept | PostgreSQL Type | Why |
|-------------|----------------|-----|
| Unique ID | `bigint generated always as identity primary key` | SQL-standard, future-proof (not `serial`) |
| Short text (name, email, status) | `text` | Same performance as `varchar(n)`, no artificial limit |
| Constrained text (status enum) | `text` + `CHECK` constraint | `CHECK (status IN ('pending','confirmed','cancelled'))` |
| Money / price | `numeric(10,2)` | Exact decimal arithmetic (not `float`) |
| Timestamp | `timestamptz default now()` | Always timezone-aware (not `timestamp`) |
| Date only | `date` | Calendar dates without time component |
| Boolean flag | `boolean default false` | 1 byte (not `varchar`) |
| Foreign key | `bigint references other_table(id)` | Always add an index on FK columns |

### 1c. Schema Naming

Use `DB_SCHEMA` (from env var) as the PostgreSQL schema for all objects:

```sql
CREATE SCHEMA IF NOT EXISTS ${DB_SCHEMA};
CREATE TABLE IF NOT EXISTS ${DB_SCHEMA}.bookings ( ... );
```

This prevents collisions when multiple apps share a Lakebase database. All DDL, queries, and grants must use `${DB_SCHEMA}` consistently.

### 1d. Write Idempotent DDL

All DDL runs on every app startup. It must be safe to execute repeatedly.

```typescript
const AppKit = await createApp({
  plugins: [server({ autoStart: false }), lakebase()],
});

const DB_SCHEMA = process.env.DB_SCHEMA || "app";

await AppKit.lakebase.query(`CREATE SCHEMA IF NOT EXISTS ${DB_SCHEMA}`);
await AppKit.lakebase.query(`
  CREATE TABLE IF NOT EXISTS ${DB_SCHEMA}.orders (
    id bigint generated always as identity primary key,
    customer_name text not null,
    amount numeric(10, 2) not null,
    status text default 'pending' check (status in ('pending', 'confirmed', 'cancelled')),
    created_at timestamptz default now()
  )
`);
```

**Index foreign key and frequently filtered columns:**

```typescript
await AppKit.lakebase.query(`
  CREATE INDEX IF NOT EXISTS idx_orders_status
  ON ${DB_SCHEMA}.orders (status)
`);
```

### 1e. Seed Data (Count-Check Pattern)

Use a count-check pattern for idempotent seeding. Do NOT use `ON CONFLICT DO NOTHING` — it fails to prevent duplicates with `identity`/`serial` PKs that auto-generate new IDs on every insert.

```typescript
const seedCheck = await AppKit.lakebase.query(
  `SELECT count(*) AS cnt FROM ${DB_SCHEMA}.orders`
);
if (parseInt(seedCheck.rows[0].cnt) === 0) {
  await AppKit.lakebase.query(`
    INSERT INTO ${DB_SCHEMA}.orders (customer_name, amount, status) VALUES
      ('Alice', 99.99, 'confirmed'),
      ('Bob', 45.00, 'pending'),
      ('Carol', 72.50, 'confirmed')
  `);
  console.log("[Lakebase] Seed data inserted");
}
```

---

## Step 2: Build API Routes

AppKit Lakebase is **server-side only** — there are no frontend hooks like `useAnalyticsQuery`. Use `server.extend()` to add Express routes.

### 2a. Server Setup Pattern

When using `server.extend()`, pass `autoStart: false` to the `server()` plugin and call `AppKit.server.start()` manually after registering all routes:

```typescript
import { createApp, server, lakebase } from "@databricks/appkit";

const AppKit = await createApp({
  plugins: [server({ autoStart: false }), lakebase()],
});

const DB_SCHEMA = process.env.DB_SCHEMA || "app";

// DDL + seed (from Step 1) ...

AppKit.server.extend((app) => {
  // Register routes here (Steps 2b-2d)
});

await AppKit.server.start();
```

> **Do NOT `import express` or `require("express")`.** Express is bundled inside `@databricks/appkit` — access it exclusively via the `app` parameter in `server.extend((app) => { ... })`. Importing Express directly may work locally but fails in production.

### 2b. Response Contract

Every data endpoint must return this shape:

```typescript
{ data: T[], source: "live" | "mock" }
```

- `source: "live"` — data came from Lakebase
- `source: "mock"` — Lakebase unavailable, returning fallback data

### 2c. CRUD Route Pattern (with Mock Fallback)

Every route follows try/catch with mock fallback:

```typescript
app.get("/api/orders", async (req, res) => {
  try {
    const result = await AppKit.lakebase.query(
      `SELECT * FROM ${DB_SCHEMA}.orders ORDER BY created_at DESC`
    );
    console.log(`[Lakebase] /api/orders returned ${result.rows.length} rows`);
    res.json({ data: result.rows, source: "live" });
  } catch (err) {
    console.warn(`[Lakebase] /api/orders fallback: ${err}`);
    res.json({
      data: [{ id: 1, customer_name: "Demo", amount: 99.99, status: "mock" }],
      source: "mock",
    });
  }
});
```

**For parameterized queries**, use `$1`, `$2` placeholders (not string interpolation):

```typescript
app.get("/api/orders/:id", async (req, res) => {
  try {
    const result = await AppKit.lakebase.query(
      `SELECT * FROM ${DB_SCHEMA}.orders WHERE id = $1`,
      [req.params.id]
    );
    res.json({ data: result.rows, source: "live" });
  } catch (err) {
    res.json({ data: [], source: "mock" });
  }
});
```

### 2d. Health Endpoint

Always include a health endpoint:

```typescript
app.get("/api/health/lakebase", async (req, res) => {
  try {
    await AppKit.lakebase.query("SELECT 1");
    res.json({ status: "connected", source: "live" });
  } catch (err) {
    res.json({ status: "disconnected", error: String(err), source: "mock" });
  }
});
```

### 2e. JSON Body Parsing for POST/PUT Routes

Express body parsing requires care since Express is bundled inside AppKit:

**Option A (recommended):** Add `express` as an explicit dependency and import `json()`:

```bash
npm install express
```

```typescript
import express from "express";

AppKit.server.extend((app) => {
  app.use(express.json());
  // POST routes ...
});
```

For an alternative without the extra dependency, see [references/frontend-patterns.md](references/frontend-patterns.md).

### 2f. Connection Resilience

AppKit's Lakebase plugin handles OAuth token rotation and caching automatically. Configure pool settings for additional resilience:

```typescript
await createApp({
  plugins: [
    lakebase({
      pool: {
        max: 10,
        connectionTimeoutMillis: 5000,
        idleTimeoutMillis: 30000,
      },
    }),
  ],
});
```

---

## Step 2g: Build Gate

**You MUST run `npm run build` and fix all errors before proceeding to Step 3.** Backend build errors found after frontend wiring are much harder to diagnose. This gate catches them early.

---

## Step 3: Wire Frontend

Replace all static mock data arrays in React components with API-backed data fetching.

### 3a. `useLakebaseData` Hook

**You MUST read [references/frontend-patterns.md](references/frontend-patterns.md) and copy the `useLakebaseData` hook into `client/src/hooks/useLakebaseData.ts`.** This hook replaces `useState`/`useEffect`/`fetch` boilerplate with a reusable pattern that returns `{ data, source, error }`.

Usage: `const { data, source, error } = useLakebaseData<Order>("/api/orders");`

### 3b. `ConnectionStatus` Component

**You MUST read [references/frontend-patterns.md](references/frontend-patterns.md) and copy the `ConnectionStatus` component.** Place it at the top of every page that fetches data. Pass a `context` string describing the data (e.g., `context="orders"`).

### 3c. Replace Static Mock Data

- Replace all static `data` arrays with `useLakebaseData` hook calls
- For AppKit chart components (`BarChart`, `AreaChart`, `DonutChart`, `DataTable`), use the `data` prop with fetched results — do NOT use `queryKey` (that requires the analytics plugin)

### 3d. Defensive Data Handling

**You MUST read the "Defensive Data Handling" section in [references/frontend-patterns.md](references/frontend-patterns.md).** Key rules: coerce DECIMAL with `Number()`, format DATE with `.toISOString().slice(0,10)`, write mapper functions for snake_case-to-camelCase.

### 3e. TypeScript Interfaces for Chart Compatibility

**You MUST add `[key: string]: unknown` index signatures** to all interfaces passed to AppKit chart `data` props. See [references/frontend-patterns.md](references/frontend-patterns.md) for the pattern.

---

## Step 4: Build Gate and Local Test

### 4a. Build Gate

```bash
cd apps_lakebase/$APP_NAME
npm run build   # Must pass with zero errors
```

Fix TypeScript, ESM, or import errors now. Each deploy cycle takes 3-5 minutes — catching errors locally saves significant time.

### 4b. Run Locally

```bash
cd apps_lakebase/$APP_NAME
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
npm run dev
```

### 4c. Verify

Open `http://localhost:8000` and check:

- UI loads correctly
- Navigation works between pages
- ConnectionStatus shows "Mock Data" (expected — live data comes after deployment)
- All pages render with mock fallback data
- No console errors

### 4d. Test API Endpoints

Run `bash scripts/test-endpoints.sh --endpoints /api/health/lakebase,/api/orders` to verify all API endpoints return valid responses. Or test manually:

```bash
curl -s "http://localhost:8000/api/health/lakebase" | jq .
# Expected: { "status": "disconnected", "source": "mock" }

curl -s "http://localhost:8000/api/orders" | jq .
# Expected: { "data": [...], "source": "mock" }
```

Mock responses confirm the fallback pattern is working. Live data verification happens after deployment.

---

## Gotchas

These are validated by three independent agent runs ([retrospective](../../retrospectives/retrospective_lakebase_wiring.md)):

| Gotcha | Impact | Fix |
|--------|--------|-----|
| `ON CONFLICT DO NOTHING` doesn't prevent duplicate seeds with `identity`/`serial` PKs | Duplicate rows on every restart | Use count-check pattern (`SELECT count(*) → INSERT if 0`) |
| `import express` or `require("express")` | Works locally, crashes in production | Use `server.extend((app) => {...})` exclusively |
| `autoStart: false` missing when using `server.extend()` | Routes not registered; server starts before `extend()` runs | Always pass `server({ autoStart: false })` and call `AppKit.server.start()` after |
| DECIMAL columns returned as strings | `"73" + "51" = "7351"` (concatenation, not addition) | Coerce with `Number()` in mapper functions |
| DATE columns returned as JS Date objects | `String(date)` → `"Fri May 15 2026..."` | Use `.toISOString().slice(0, 10)` for `YYYY-MM-DD` |
| `databricks.yml` postgres resource format | Old `postgres:` format rejected by bundle deployer | Do NOT add postgres resource for Autoscaling; use static env vars in `app.yaml` |
| `valueFrom: postgres` in `app.yaml` | Doesn't resolve without bundle-managed resource | Use static `value:` for all PG env vars |
| `queryKey` on chart components | Requires analytics plugin (not installed) | Use `data` prop with fetched results |
| Stale endpoint hostname in `.env` | Silent connection failures | Re-fetch host: `databricks postgres get-endpoint ... \| jq -r '.status.hosts.host'` |
| Port 8000 already in use | `EADDRINUSE` on `npm run dev` | `lsof -ti:8000 \| xargs kill -9 2>/dev/null \|\| true` before starting |

---

## Quick Reference

| Task | Command / Pattern |
|------|------------------|
| Check live Lakebase docs | `npx @databricks/appkit docs "lakebase"` |
| Derive schema name | `DB_SCHEMA=$(echo "$APP_NAME" \| tr '-' '_')` |
| Test health endpoint | `curl -s http://localhost:8000/api/health/lakebase \| jq .` |
| Build gate | `npm run build` (must pass with zero errors) |
| Kill stale dev server | `lsof -ti:8000 \| xargs kill -9 2>/dev/null \|\| true` |
