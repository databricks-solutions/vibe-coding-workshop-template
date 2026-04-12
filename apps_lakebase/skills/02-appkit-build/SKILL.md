---
name: 02-appkit-build
description: >
  Build full-stack UI and backend features on a Databricks AppKit project from a PRD
  or feature spec. Covers SQL query design, type generation, React frontend with
  AppKit UI components, backend plugin wiring, and distinctive visual design. Use
  when asked to implement a UI, build features from a PRD, create pages or dashboards,
  add components, develop the frontend/backend of an existing AppKit app, build with
  mock data, or use static data for visual prototyping. Triggers on "build UI",
  "implement PRD", "create dashboard", "add page", "build features", "implement
  design", "create components", "build app from PRD", "develop frontend", "mock data",
  "static data", "two-phase data".
license: Apache-2.0
compatibility: Requires an existing AppKit project scaffolded via 01-appkit-scaffold skill, Node.js v22+, Databricks CLI >= 0.295.0
metadata:
  author: prashanth subrahmanyam
  version: "1.0.0"
  domain: apps
  role: build
  standalone: false
  last_verified: "2026-04-10"
  volatility: medium
  upstream_sources:
    - https://github.com/databricks/databricks-agent-skills/tree/main/skills/databricks-apps
    - https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md
    - https://databricks.github.io/appkit/
---

# Build Features on Databricks AppKit

Implement full-stack UI and backend features on an already-scaffolded AppKit project, driven by a PRD or feature spec.

## When to Use

- Implementing a PRD or feature spec on an existing AppKit project
- Building pages, dashboards, or components with `@databricks/appkit-ui`
- Adding SQL queries and wiring them to type-safe React hooks
- Creating a visually distinctive, production-grade frontend

**Not for scaffolding.** Use `01-appkit-scaffold` to create a new project first.
**Not for adding plugins.** Use `04-appkit-plugin-add` to register new plugins.

---

## Before You Begin

**This skill has two upstream masters. Check them when possible — recommended but not blocking.**

1. **Databricks Apps skill (source of truth for AppKit workflow):**
   Fetch the latest from https://github.com/databricks/databricks-agent-skills/tree/main/skills/databricks-apps
   If accessible, check the "Breaking Changes" and "New Patterns" sections.

2. **Anthropic frontend-design skill (inspiration for design quality):**
   Fetch the latest from https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md
   Skim for new aesthetic examples. Skip if latency-constrained.

**Additional live docs (always prefer over bundled references):**

```bash
npx @databricks/appkit docs              # documentation index
npx @databricks/appkit docs "<query>"    # specific topic
```

Key upstream doc pages:
- LLM guardrails: https://databricks.github.io/appkit/docs/development/llm-guide
- Type generation: https://databricks.github.io/appkit/docs/development/type-generation
- UI components: https://databricks.github.io/appkit/docs/api/appkit-ui/
- Configuration: https://databricks.github.io/appkit/docs/configuration
- Architecture: https://databricks.github.io/appkit/docs/architecture

The bundled references below are fallbacks when live docs cannot be reached.

> **Workshop Mode (blank app):** If you are following the AppKit+Lakebase workshop (Phase 1) and scaffolded a blank app without plugins, skip Step 2 (SQL Queries) and the `analytics()` plugin references in Step 4. Use static mock data arrays instead of `useAnalyticsQuery`. The backend only needs `server()` — no `analytics()` plugin. All SQL/typegen sections are not applicable until the Lakebase plugin is added in Phase 4.

---

## Architecture Overview

AppKit is a TypeScript full-stack framework with two packages:

- **`@databricks/appkit`** — backend: Express server, plugin system, SQL query execution, caching, telemetry
- **`@databricks/appkit-ui`** — frontend: React hooks (`useAnalyticsQuery`), UI primitives (Shadcn/Radix), data visualization (ECharts)

```
client/src/App.tsx  →  useAnalyticsQuery("key", params)  →  server/server.ts  →  config/queries/key.sql  →  SQL Warehouse
```

---

## Step 1: Read the PRD

Before writing any code, thoroughly understand:

- **User personas** and their needs
- **Key user journeys** (focus on Happy Path first)
- **Core features** and requirements
- **Data requirements** — what tables/queries will the UI need?

---

## Step 2: Plan and Create SQL Queries

Create `.sql` files in `config/queries/`. Each file becomes a query key.

```sql
-- config/queries/active_users.sql
-- @param startDate DATE
-- @param endDate DATE
SELECT user_id, email, last_login
FROM catalog.schema.users
WHERE last_login BETWEEN :startDate AND :endDate
ORDER BY last_login DESC
```

**Rules:**
- Use `:paramName` placeholders — NEVER construct SQL strings dynamically
- Annotate params with `-- @param name TYPE` (types: `STRING`, `NUMERIC`, `BOOLEAN`, `DATE`, `TIMESTAMP`)
- `:workspaceId` is auto-injected by the server — do NOT annotate it
- `queryKey.sql` runs as service principal; `queryKey.obo.sql` runs as user

Then generate types:

```bash
npm run typegen
```

**Do NOT write UI code until types are generated.** Read `client/src/appKitTypes.d.ts` to see available query types.

---

## Step 3: Design the UI

Before coding components, commit to a design direction. READ [references/design-quality.md](references/design-quality.md) for detailed guidelines.

Key principles:
- Choose a **bold aesthetic direction** — not generic AI aesthetics
- Use AppKit UI primitives (`@databricks/appkit-ui`) as the foundation, then layer distinctive styling on top
- Plan the page layout, component hierarchy, and navigation flow

---

## Step 4: Build the Backend

In `server/server.ts`, ensure plugins are registered:

```typescript
import { createApp, server, analytics } from "@databricks/appkit";

await createApp({
  plugins: [server(), analytics()],
});
```

For non-query APIs (writes, ML endpoints, custom logic), extend the server:

```typescript
const appkit = await createApp({
  plugins: [server({ autoStart: false }), analytics()],
});

appkit.server.extend((app) => {
  app.post("/api/custom-action", (req, res) => { /* ... */ });
});

await appkit.server.start();
```

**NEVER use tRPC or custom routes for SELECT queries** — always use SQL files in `config/queries/`.

---

## Step 4b: TypeScript Validation Gate

**You MUST run `npx tsc --noEmit` and fix all errors before proceeding to Step 5.** TypeScript errors in the backend will cascade to the frontend build and cause deploy failures. Fix them now while the scope is small.

---

## Step 5: Build the Frontend

Implement components in `client/src/`. Start with `App.tsx`.

### Two-Phase Data Pattern

Build the UI in two phases so you get immediate visual feedback before SQL queries are wired up.

**Phase 1 — Static data for immediate visual feedback:**

Use the `data` prop on AppKit data components (charts, tables) with representative sample data. This lets you build and iterate on the UI visually before wiring up live query-driven data.

```tsx
<BarChart
  data={[
    { month: "Jan", revenue: 4200 },
    { month: "Feb", revenue: 5100 },
    { month: "Mar", revenue: 3800 },
  ]}
  xKey="month"
  yKey="revenue"
/>
```

**Phase 2 — Swap to query-driven data (final state):**

Once SQL files exist in `config/queries/` and `npm run typegen` has generated types, replace static `data` with `queryKey` + `params`:

```tsx
import { useAnalyticsQuery } from "@databricks/appkit-ui/react";
import { sql } from "@databricks/appkit-ui/js";

function RevenueChart() {
  const params = useMemo(() => ({
    year: sql.number(2025),
  }), []);

  const { data, loading, error } = useAnalyticsQuery("monthly_revenue", params);

  if (loading) return <Skeleton className="h-32 w-full" />;
  if (error) return <div className="text-destructive">{error}</div>;
  if (!data?.length) return <div className="text-muted-foreground">No data</div>;

  return <BarChart data={data} xKey="month" yKey="revenue" />;
}
```

All static demo data must be replaced with query-driven data before declaring the build complete.

### Hard Rules

READ [references/llm-guardrails.md](references/llm-guardrails.md) for the complete list. Key ones:

- **SQL results return strings** — `useAnalyticsQuery` may return all values as strings at runtime, even for numeric columns. Always coerce with `Number()` before arithmetic to avoid string concatenation bugs
- **Always `useMemo`** on query parameters — prevents infinite refetch loops. For parameterless queries (`Record<string, never>`), pass `useMemo(() => ({}), [])`
- **Always handle loading/error/empty states** — use `Skeleton` for loading
- **Always use `sql.*` helpers** for parameters (`sql.date()`, `sql.string()`, `sql.number()`)
- **Use `import type`** for type-only imports when `verbatimModuleSyntax` is enabled
- **Never invent APIs** — only use documented exports from `@databricks/appkit` and `@databricks/appkit-ui`
- **Never build SQL strings dynamically** — use parameterized queries
- **`createApp()` is async** — always `await` it
- **Wrap root with `<TooltipProvider>`** — many AppKit components use tooltips internally; add this to `App.tsx` by default

### UI Components

AppKit UI components are Shadcn/Radix-based. Data charts are ECharts-based — use props (`xKey`, `yKey`, `colors`), NOT Recharts children.

Check the live docs for the latest component list:

```bash
npx @databricks/appkit docs "appkit-ui API reference"
```

**Note:** The `docs` search matches section headings only. Searching for a component name like `"DataTable"` may fail. Use the full doc path for specific components:

```bash
npx @databricks/appkit docs "./docs/api/appkit-ui/data/DataTable.md"
```

### Chart Components Quick Reference

Available chart components from `@databricks/appkit-ui`:

| Component | Key Props | Use Case |
|-----------|-----------|----------|
| `BarChart` | `xKey`, `yKey`, `colors`, `height`, `title` | Categorical comparison |
| `LineChart` | `xKey`, `yKey`, `colors`, `height` | Trends over time |
| `AreaChart` | `xKey`, `yKey`, `colors`, `height` | Volume trends |
| `PieChart` | `nameKey`, `valueKey`, `colors` | Part-of-whole |
| `DonutChart` | `nameKey`, `valueKey`, `colors` | Part-of-whole (with center) |
| `ScatterChart` | `xKey`, `yKey`, `colors` | Correlation |

All accept either `data` (static array) for Phase 1 or `queryKey` + `parameters` for Phase 2.

For the full list with all props, inspect the type definitions:

```bash
ls node_modules/@databricks/appkit-ui/dist/charts/
```

### Routing

The scaffold generates react-router v7 with `createBrowserRouter`. For multi-page apps, set up routing in `App.tsx`:

- **`createBrowserRouter`** — define routes with path and element
- **`<Outlet />`** — render child routes inside a layout component
- **`<NavLink>`** — navigation links with active state styling
- **`useParams()`** — read URL parameters (e.g. `/orders/:id`)
- **`useNavigate()`** — programmatic navigation

```tsx
import { createBrowserRouter, RouterProvider, NavLink, Outlet } from "react-router-dom";

const router = createBrowserRouter([
  {
    path: "/",
    element: <Layout />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: "orders", element: <Orders /> },
      { path: "orders/:id", element: <OrderDetail /> },
    ],
  },
]);

function Layout() {
  return (
    <div>
      <nav>
        <NavLink to="/">Dashboard</NavLink>
        <NavLink to="/orders">Orders</NavLink>
      </nav>
      <Outlet />
    </div>
  );
}
```

---

## Step 6: Test Locally

```bash
npm run dev
```

Verify at `http://localhost:8000`:
- UI loads without console errors
- Navigation works across pages
- Data queries return results (loading → data flow)
- All interactive elements respond

---

## Known Gotchas

Common runtime surprises that cause bugs or confusion:

| Gotcha | Fix |
|--------|-----|
| SQL results return strings even for numeric columns | Coerce with `Number()` before arithmetic |
| `useAnalyticsQuery` params must be wrapped in `useMemo` | Unwrapped objects trigger infinite refetch loops |
| Parameterless queries generate `Record<string, never>` | Pass `useMemo(() => ({}), [])` |
| Charts are ECharts-based, not Recharts | Use props (`xKey`, `yKey`, `colors`) — not children (`<XAxis>`, `<Bar>`) |
| `import type` required with `verbatimModuleSyntax` | Separate type-only imports or build fails |
| Chart components accept both `data` (static) and `queryKey` (query-driven) props | Use `data` for Phase 1 static data, `queryKey` + `params` for Phase 2 |
| `npx @databricks/appkit docs` search matches section headings only | Use full doc path for specific component lookups |
| `npm run dev` triggers typegen via `predev` hook | `TABLE_OR_VIEW_NOT_FOUND` errors are expected if custom queries reference tables that don't exist yet. Not blocking. |

---

## Pre-Finalization Checklist

Before declaring the build complete:

- [ ] SQL files exist in `config/queries/` for every data need
- [ ] `npm run typegen` has been run after all SQL files are finalized
- [ ] All query parameters wrapped in `useMemo`
- [ ] Loading/error/empty states on every data component
- [ ] `tests/smoke.spec.ts` selectors updated for your app
- [ ] Static demo data renders correctly (swap to live data happens in Phase 4 — Lakebase wiring)
- [ ] `npx tsc --noEmit` passes with zero TypeScript errors (catches unused imports, missing types that block deployment)
- [ ] `npm run dev` runs cleanly at `http://localhost:8000`

---

## What's Next: Deploying

Once local testing passes, deploy to Databricks Apps using the `03-appkit-deploy` skill at `@apps_lakebase/skills/03-appkit-deploy/SKILL.md`. The calling prompt (`02-deploy.md` or `05-e2e-test.md`) will set variables and invoke the skill.

See the [AppKit App Management docs](https://databricks.github.io/appkit/docs/app-management) for advanced deploy options.
