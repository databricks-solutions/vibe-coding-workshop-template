# AppKit LLM Guardrails

> **Upstream (always check for latest):** https://databricks.github.io/appkit/docs/development/llm-guide
>
> Run `npx @databricks/appkit docs "llm guide"` for the live version. This file is a fallback.
>
> **Client note (IDE & Genie Code).** These are **code-authoring rules** — they apply identically on both clients. On Genie Code `npx` is absent: WebFetch the upstream link above instead of the `npx … docs` command, and note that any `databricks apps validate` mention is IDE-only (skipped on Genie Code; rely on `bundle validate` + server-side build logs).

---

## Hard Rules

1. **Do NOT invent APIs.** Only use documented exports from `@databricks/appkit` and `@databricks/appkit-ui`. If unsure, stick to patterns shown in the docs.
2. **`createApp()` is async.** Always `await createApp(...)`. If top-level await isn't available, use `void createApp(...)` but never ignore promise rejection.
3. **Always `useMemo` query parameters.** Every params object passed to `useAnalyticsQuery` or chart components must be wrapped in `useMemo` — otherwise React triggers infinite refetch loops. For parameterless queries (typegen produces `Record<string, never>`), pass `useMemo(() => ({}), [])`.
4. **Always handle loading/error/empty states.** Use `Skeleton` for loading, error text for errors, and meaningful empty states.
5. **Always use `sql.*` helpers** for query parameter values (`sql.date()`, `sql.string()`, `sql.number()`). Do not pass raw strings or numbers.
6. **SQL results return strings.** `useAnalyticsQuery` may return all column values as strings at runtime, even for `INT`, `DECIMAL`, or `BOOLEAN` columns. Always coerce with `Number()` before arithmetic and comparisons. Without this, expressions like `a + b` produce string concatenation (`"73" + "51" = "7351"`) instead of addition (`73 + 51 = 124`).
7. **Never construct SQL dynamically.** Use parameterized queries with `:paramName` placeholders in `.sql` files.
8. **Never use `require()`.** Use ESM `import`/`export` only. `package.json` must have `"type": "module"`.
9. **Never import Express directly.** Express is bundled inside `@databricks/appkit`. Access it only via `server.extend((app) => { ... })`. Importing Express directly may work locally due to `node_modules` hoisting but fails in production builds where only declared dependencies are bundled.
10. **Chart `data` props require index signatures.** If passing a named TypeScript interface to chart component `data` props, the interface must include `[key: string]: unknown` because `ChartData` expects `Record<string, unknown>[]`.
11. **Import appkit-ui components from `@databricks/appkit-ui/react`.** Always `import { … } from "@databricks/appkit-ui/react"` — **never** the bare `@databricks/appkit-ui`, which has no React export and fails to resolve at build time.
12. **Import the appkit-ui stylesheet as `@databricks/appkit-ui/styles.css`.** In `client/src/index.css` use `@import "@databricks/appkit-ui/styles.css";` — **never** the extension-less `@import "@databricks/appkit-ui/styles";` (only the `.css` path is exported; the extension-less form is unresolvable). Both are exactly what the scaffold ships — preserve them rather than hand-authoring `App.tsx`/`index.css` from memory.
13. **Import only symbols you reference in the same file.** The scaffold's `tsconfig` has `noUnusedLocals: true` and `noUnusedParameters: true`, so an unused import, variable, or function parameter is a **hard build failure** (`error TS6133`), not a warning. Do not pre-import symbols for features you haven't implemented yet; add the import when you add the usage.
14. **A `<Select.Item>`/`<SelectItem>` `value` must be a non-empty string.** Radix throws at runtime if `value=""`. For an "all/any" catch-all option use a sentinel like `value="all"` and filter explicitly (`if (filter !== "all") { … }`) — never an empty string.

---

## TypeScript Import Rules

When `tsconfig.json` has `"verbatimModuleSyntax": true` (AppKit default), always separate type-only imports:

```typescript
import type { ReactNode } from "react";
import { useMemo } from "react";
```

Failure to do this causes build errors in strict TypeScript setups.

---

## SQL Query Rules

- Place all queries in `config/queries/` — each file becomes a query key
- Annotate parameters with `-- @param name TYPE` comments (`STRING`, `NUMERIC`, `BOOLEAN`, `DATE`, `TIMESTAMP`)
- Use `:paramName` placeholders — never concatenate SQL strings
- `:workspaceId` is auto-injected by the server — do NOT annotate it
- `queryKey.sql` runs as service principal; `queryKey.obo.sql` runs as the user's identity
- **Avoid `:limit` in parameterized queries** — typegen may treat the value as a string, causing SQL type errors. Use a hardcoded `LIMIT` value or a CTE pattern instead.

---

## Frontend Component Rules

- Charts are ECharts-based — use props (`xKey`, `yKey`, `colors`), NOT Recharts children (`<XAxis>`, `<Bar>`, etc.)
- Use `format="auto"` on charts unless you have a specific reason for `"json"` or `"arrow"`
- Wrap the root component with `<TooltipProvider>` in `App.tsx` — many AppKit components use tooltips internally
- All data-driven components must show three states: loading → data → empty/error

---

## Pre-Finalization Checklist

### Project Setup
- [ ] `package.json` has `"type": "module"`
- [ ] `tsx` is in devDependencies
- [ ] `dev` script: `NODE_ENV=development tsx watch server/server.ts`
- [ ] `client/index.html` exists with `<div id="root">` and script pointing to `client/src/main.tsx`

### Backend
- [ ] `await createApp({ plugins: [...] })` used
- [ ] `server()` plugin always included
- [ ] If using SQL: `analytics({})` included + `config/queries/*.sql` present
- [ ] Queries use `:param` placeholders, params passed from UI using `sql.*`
- [ ] If workspace-scoped: uses `:workspaceId`

### Frontend
- [ ] `useMemo` wraps all parameter objects
- [ ] Loading/error/empty states are explicit on every data component
- [ ] Charts use props, NOT Recharts children
- [ ] `import type` used for type-only imports
- [ ] appkit-ui components imported from `@databricks/appkit-ui/react` (never bare `@databricks/appkit-ui`)
- [ ] `client/src/index.css` uses `@import "@databricks/appkit-ui/styles.css";` (never extension-less `…/styles`)
- [ ] Scaffold `App.tsx` / `index.css` edited incrementally (not regenerated); `ErrorBoundary.tsx` kept
- [ ] No unused imports/vars/params (scaffold's `noUnusedLocals`/`noUnusedParameters` make these a hard `TS6133` build failure)
- [ ] Every `<SelectItem>` has a non-empty `value` (use a sentinel like `"all"` for catch-all, never `value=""`)

### Never Do
- [ ] Don't build SQL strings manually
- [ ] Don't pass untyped raw params for annotated queries
- [ ] Don't ignore `createApp()`'s promise
- [ ] Don't invent UI components not listed in the docs
- [ ] Don't pass Recharts-style children to AppKit chart components
