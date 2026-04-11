---
name: appkit-plugin-add
description: >
  Add plugins to an existing Databricks AppKit project. Covers Lakebase (PostgreSQL),
  Analytics (SQL queries + dashboards), Genie (natural language AI/BI), and Files
  (UC Volumes). Guides through plugin registration, environment variables, app.yaml
  configuration, and frontend integration. Use when asked to add a plugin to an
  existing app, integrate Lakebase, add analytics, connect a Genie space, enable
  file uploads, or extend an AppKit project with new capabilities. Triggers on
  "add plugin", "add lakebase", "add analytics", "add genie", "add files plugin",
  "integrate postgres", "add database", "add dashboards", "add file browser",
  "extend app", "connect genie space".
license: Apache-2.0
compatibility: Requires an existing AppKit project with Node.js v22+ and Databricks CLI >= 0.295.0
metadata:
  author: prashanth subrahmanyam
  version: "1.0.0"
  domain: apps
  role: plugin-integration
  standalone: true
  last_verified: "2026-04-10"
  volatility: medium
  upstream_sources:
    - https://databricks.github.io/appkit/docs/plugins/
    - https://github.com/databricks/databricks-agent-skills
---

# Add Plugins to an Existing AppKit Project

Add Lakebase, Analytics, Genie, or Files plugins to a Databricks AppKit project that has already been scaffolded.

## When to Use

- Adding a new plugin to an existing AppKit project
- Integrating PostgreSQL (Lakebase), SQL dashboards (Analytics), natural language queries (Genie), or file management (Files)
- Extending an app that was scaffolded blank or needs an additional plugin

**Not for scaffolding a new app.** To create a new AppKit project (blank or with plugins), use the `appkit-scaffold` skill instead.

---

## Before You Begin

**IMPORTANT — The upstream AppKit docs are the source of truth, not this skill.**
AppKit may have plugins beyond the four listed here. Always check the upstream docs first to discover all available plugins and get the latest configuration details:

- **Plugin docs:** https://databricks.github.io/appkit/docs/plugins/
- **CLI docs browser:** `npx @databricks/appkit docs "<plugin-name>"`
- **Full plugin list:** `npx @databricks/appkit docs "plugins"`

The bundled reference files below cover commonly used plugins as a fallback when the live docs cannot be reached. If the user requests a plugin not listed here, consult the upstream docs directly.

---

## Step 1: Identify Which Plugin to Add

The table below covers plugins bundled with this skill. AppKit may offer additional plugins not listed here — check the upstream docs (`npx @databricks/appkit docs "plugins"`) for the full list.

| Plugin | Keywords | READ this reference |
|--------|----------|---------------------|
| **Lakebase** | PostgreSQL, database, persistence, CRUD, pg, ORM | [references/plugin-lakebase.md](references/plugin-lakebase.md) |
| **Analytics** | SQL queries, dashboards, charts, warehouse, data viz | [references/plugin-analytics.md](references/plugin-analytics.md) |
| **Genie** | Natural language, AI/BI, Genie spaces, conversational | [references/plugin-genie.md](references/plugin-genie.md) |
| **Files** | File upload/download, UC Volumes, file browser | [references/plugin-files.md](references/plugin-files.md) |

If the plugin you need is listed above, **READ its reference file before proceeding** — it contains the import, config, env vars, `app.yaml` changes, frontend hooks, and gotchas. For any other plugin, consult the upstream docs directly.

---

## Step 2: Register the Plugin

In `server/server.ts`, import the plugin and add it to the `plugins` array:

```typescript
import { createApp, server, <pluginName> } from "@databricks/appkit";

await createApp({
  plugins: [
    server(),
    <pluginName>(),
  ],
});
```

### Multiple Plugins

Plugins compose freely — add as many as needed:

```typescript
import { createApp, server, analytics, lakebase, genie, files } from "@databricks/appkit";

await createApp({
  plugins: [
    server(),
    analytics(),
    lakebase(),
    genie(),
    files(),
  ],
});
```

---

## Step 3: Configure Environment Variables

Each plugin requires specific environment variables. After reading the plugin reference file, add the required variables to:

1. **`.env`** — for local development
2. **`app.yaml`** — for deployed apps

See the plugin-specific reference for exact variable names and values.

---

## Step 4: Frontend Integration

Most plugins provide React hooks and/or components from `@databricks/appkit-ui/react`:

| Plugin | Key frontend exports |
|--------|---------------------|
| **Analytics** | `useAnalyticsQuery` hook, `sql` parameter helpers |
| **Genie** | `GenieChat` component, `useGenieChat` hook |
| **Files** | `DirectoryList`, `FileBreadcrumb`, `FilePreviewPanel` components |
| **Lakebase** | Server-side only (no frontend components) |

See the plugin-specific reference for usage examples.

---

## AppKit Documentation (Live)

For the latest API details, component props, and hook signatures:

```bash
npx @databricks/appkit docs              # documentation index
npx @databricks/appkit docs "<query>"    # search for a specific topic
npx @databricks/appkit docs --full       # full index with all API entries
```

---

## Quick Reference

| Task | Command / Action |
|------|-----------------|
| Check live plugin docs | `npx @databricks/appkit docs "<plugin>"` |
| Get warehouse ID (for Analytics/Genie) | `databricks experimental aitools tools get-default-warehouse --profile <P>` |
| Generate query types (Analytics) | `npm run typegen` |
| Validate app | `databricks apps validate` |
| Deploy | `databricks apps deploy --profile <P>` |
