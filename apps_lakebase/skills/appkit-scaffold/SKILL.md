---
name: appkit-scaffold
description: >
  Scaffold new Databricks AppKit applications using the Databricks CLI and Agent Skills.
  Creates blank or plugin-enabled AppKit projects (Lakebase, Analytics, Genie, Files).
  Use when asked to create a Databricks app, scaffold an AppKit project, bootstrap a
  new app, or set up a full-stack TypeScript Databricks application. Triggers on
  "create app", "new app", "scaffold", "AppKit", "databricks app", "blank app",
  "bootstrap app", "init app". To add a plugin to an existing app, use the
  appkit-plugin-add skill instead.
license: Apache-2.0
compatibility: Requires Databricks CLI >= 0.295.0 and Node.js v22+
metadata:
  author: prashanth subrahmanyam
  version: "1.0.0"
  domain: apps
  role: scaffold
  standalone: true
  last_verified: "2026-04-10"
  volatility: medium
  upstream_sources:
    - https://databricks.github.io/appkit/
    - https://github.com/databricks/databricks-agent-skills
---

# Scaffold Databricks AppKit Applications

Create and configure Databricks AppKit projects — blank or with plugins — using the Databricks CLI and official Agent Skills.

## When to Use

- Creating a brand-new Databricks AppKit application
- Scaffolding a blank app or one with specific plugins (Lakebase, Analytics, Genie, Files)
- Setting up a full-stack TypeScript app that deploys to Databricks Apps

**Not for adding plugins to an existing app.** Use the `appkit-plugin-add` skill for that.

## Prerequisites

Before scaffolding, verify these requirements:

```bash
# 1. Databricks CLI >= 0.295.0
databricks --version

# 2. Node.js v22+
node --version

# 3. Authenticated CLI profile
databricks auth profiles
```

If the CLI is not installed or outdated, see the [Databricks CLI installation guide](https://docs.databricks.com/aws/en/dev-tools/cli/tutorial).

**CRITICAL — Profile Selection:** NEVER auto-select a profile. List all profiles with `databricks auth profiles`, present them to the user, and let the user choose.

---

## Step 1: Install Databricks Agent Skills

Agent Skills give the AI assistant access to data exploration, CLI execution, and workspace resource discovery. They are maintained in the official repository:

**Source repository:** https://github.com/databricks/databricks-agent-skills

**IMPORTANT — Always check the upstream repo for the latest install method BEFORE installing.**
Fetch the README from the repository above (e.g. via `WebFetch`, `curl`, or browsing) to confirm the current installation commands. The install process may change between releases.

**For Cursor** (run in chat):
```
/add-plugin databricks-skills
```

**For Claude Code and other CLI-based assistants:**
```bash
databricks experimental aitools install
```

If you cannot reach the repository, use the bundled fallback script:
```bash
bash scripts/install-agent-skills.sh
```

This is idempotent — safe to run multiple times.

---

## Step 2: Scaffold the App

### Option A: Blank Scaffold (Default)

A minimal AppKit app with only the server plugin — no data plugins.

```bash
databricks apps init --name <APP_NAME> --description "<DESCRIPTION>" --run none --profile <PROFILE>
```

### Option B: Scaffold with Plugins

Add plugins during scaffold using the `--features` flag. Combine multiple features with commas.

```bash
# Analytics only (SQL queries + dashboards)
databricks apps init --name <APP_NAME> --description "<DESC>" --features analytics --warehouse-id <WAREHOUSE_ID> --run none --profile <PROFILE>

# Lakebase only (PostgreSQL persistence)
databricks apps init --name <APP_NAME> --description "<DESC>" --features lakebase --run none --profile <PROFILE>

# Multiple plugins
databricks apps init --name <APP_NAME> --description "<DESC>" --features analytics,lakebase,genie --warehouse-id <WAREHOUSE_ID> --run none --profile <PROFILE>
```

**Available features:** `analytics`, `lakebase`, `genie`, `files`

### Naming Rules

- Max 26 characters, lowercase letters/numbers/hyphens only (no underscores)
- `dev-` prefix adds 4 chars, max 30 total

### Discover Warehouse ID (if needed)

When using `analytics` or `genie` features, you need a SQL Warehouse ID:

```bash
databricks experimental aitools tools get-default-warehouse --profile <PROFILE>
```

---

## Step 3: Post-Scaffold Setup

```bash
cd <APP_NAME>
npm install
npm run dev
```

This starts the dev server with hot reload on `http://localhost:8000`.

### Validate and Deploy

```bash
databricks apps validate
databricks apps deploy --profile <PROFILE>
```

---

## Adding a Plugin to an Existing App

To add a plugin (Lakebase, Analytics, Genie, Files) to an existing AppKit project, use the **`appkit-plugin-add`** skill. It covers plugin registration, environment variables, `app.yaml` configuration, and frontend integration.

After scaffolding with `--features`, consult the `appkit-plugin-add` skill for detailed plugin configuration and frontend integration guidance.

---

## AppKit Documentation (Live)

For the latest API details, component props, and hook signatures — always consult the live docs:

```bash
npx @databricks/appkit docs              # documentation index
npx @databricks/appkit docs "<query>"    # search for a specific topic
npx @databricks/appkit docs --full       # full index with all API entries
```

For project layout and dev workflow details, see [references/appkit-project-structure.md](references/appkit-project-structure.md).

---

## Quick Reference

| Task | Command |
|------|---------|
| Install agent skills | Check [databricks-agent-skills](https://github.com/databricks/databricks-agent-skills) README first, then `databricks experimental aitools install` |
| Scaffold blank app | `databricks apps init --name <N> --run none --profile <P>` |
| Scaffold with analytics | `databricks apps init --name <N> --features analytics --warehouse-id <W> --run none --profile <P>` |
| Get warehouse ID | `databricks experimental aitools tools get-default-warehouse --profile <P>` |
| Explore table schema | `databricks experimental aitools tools discover-schema catalog.schema.table --profile <P>` |
| Run ad-hoc SQL | `databricks experimental aitools tools query "SELECT ..." --profile <P>` |
| Install deps | `cd <APP> && npm install` |
| Dev server | `npm run dev` |
| Build | `npm run build` |
| Validate | `databricks apps validate` |
| Deploy | `databricks apps deploy --profile <P>` |
| Browse AppKit docs | `npx @databricks/appkit docs` |
