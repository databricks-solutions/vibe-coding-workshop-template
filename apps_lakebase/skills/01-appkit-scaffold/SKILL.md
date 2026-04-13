---
name: 01-appkit-scaffold
description: >
  Scaffold new Databricks AppKit applications using the Databricks CLI and Agent Skills.
  Creates blank or plugin-enabled AppKit projects (Lakebase, Analytics, Genie, Files).
  Use when asked to create a Databricks app, scaffold an AppKit project, bootstrap a
  new app, or set up a full-stack TypeScript Databricks application. Triggers on
  "create app", "new app", "scaffold", "AppKit", "databricks app", "blank app",
  "bootstrap app", "init app". To add a plugin to an existing app, use the
  04-appkit-plugin-add skill instead.
license: Apache-2.0
compatibility: Requires Databricks CLI >= 0.295.0 and Node.js v22+
allowed-tools: Bash(databricks:*) Bash(npm:*) Bash(git:*) Bash(node:*) Read
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

**Not for adding plugins to an existing app.** Use the `04-appkit-plugin-add` skill for that.

## Prerequisites

Before scaffolding, verify these requirements. Run `bash apps_lakebase/skills/00-appkit-navigator/scripts/validate-prereqs.sh --profile $PROFILE` to check all prerequisites at once, or verify manually:

```bash
# 1. Databricks CLI >= 0.295.0
databricks --version

# 2. Node.js v22+
node --version

# 3. Authenticated CLI profile
databricks auth profiles

# 4. Verify access to the target workspace
databricks current-user me --host <WORKSPACE_URL>
# If this returns 403, you do not have access. Stop and ask the user for a different workspace.
```

If the CLI is not installed or outdated, see the [Databricks CLI installation guide](https://docs.databricks.com/aws/en/dev-tools/cli/tutorial).

**Profile Selection:** If the calling prompt specifies a profile, use it. Otherwise, list all profiles with `databricks auth profiles`, present them to the user, and let the user choose. Do not silently default to a profile when multiple are available.

**Programmatic profile discovery** (for scripted or multi-phase workflows):

```bash
TARGET_HOST="<WORKSPACE_URL>"
PROFILE=$(databricks auth profiles --output json 2>/dev/null \
  | jq -r --arg host "$TARGET_HOST" \
    '[.profiles[] | select(.host == $host)] | .[0].name // empty')

if [ -z "$PROFILE" ]; then
  databricks auth login --host "$TARGET_HOST"
  PROFILE=$(databricks auth profiles --output json 2>/dev/null \
    | jq -r --arg host "$TARGET_HOST" \
      '[.profiles[] | select(.host == $host)] | .[0].name // empty')
fi
```

---

## Step 1: Install Databricks Agent Skills

Agent Skills give the AI assistant access to data exploration, CLI execution, and workspace resource discovery. They are maintained in the official repository:

**Source repository:** https://github.com/databricks/databricks-agent-skills

**IMPORTANT — Always check the upstream repo for the latest install method BEFORE installing.**
Fetch the README from the repository above (e.g. via `WebFetch`, `curl`, or browsing) to confirm the current installation commands. The install process may change between releases.

### Install to the project (all IDEs)

Clone the skills into the project-level `.agents/skills/` directory. This path follows the [agentskills.io](https://agentskills.io) cross-agent standard and is discovered by Cursor, VS Code / Copilot, Windsurf, Claude Code, and any compatible agent.

```bash
git clone --depth 1 https://github.com/databricks/databricks-agent-skills .agents/skills/databricks-skills
```

The `.agents/` directory is already in `.gitignore` — cloned skills are not committed to the repo.

### Optional: IDE-native install (in addition to the project clone)

Some IDEs have their own plugin/skill systems that provide deeper integration. These are **optional extras** on top of the project-level install above.

| IDE | Optional extra | What it does |
|-----|---------------|-------------|
| **Cursor** | `/add-plugin databricks-skills` (run in chat) | Installs to Cursor's plugin cache for cross-project availability |
| **Claude Code** | `databricks experimental aitools skills install` | Installs to `~/.claude/skills/` for cross-project availability |
| **VS Code / Copilot** | No extra needed | Discovers `.agents/skills/` automatically ([docs](https://code.visualstudio.com/docs/copilot/customization/agent-skills)) |
| **Windsurf** | No extra needed | Discovers `.agents/skills/` automatically ([docs](https://docs.windsurf.com/windsurf/cascade/skills)) |

### Fallback

If you cannot reach the repository, use the bundled fallback script:
```bash
bash scripts/install-agent-skills.sh
```

### Verification

After installation, confirm the skills are available. The CLI tools should respond:
```bash
databricks experimental aitools tools --help
```

Verify the Lakebase skill is present (needed in the **Setup Lakebase** step and later):
```bash
ls .agents/skills/databricks-skills/skills/databricks-lakebase/SKILL.md 2>/dev/null \
  && echo "Lakebase skill: OK" \
  || echo "WARNING: Lakebase skill not found — re-run git clone step"
```

This is idempotent — safe to run multiple times.

---

## Step 2: Scaffold the App

### Pre-scaffold check

Before scaffolding, verify that agent skills from Step 1 are available:

```bash
databricks experimental aitools tools --help
```

If this command fails or is not recognized, go back to Step 1 and install agent skills first. **Do not proceed without completing Step 1.**

### Option A: Blank Scaffold (Default)

A minimal AppKit app with only the server plugin — no data plugins.

```bash
databricks apps init --name <APP_NAME> --description "<DESCRIPTION>" --run none --profile <PROFILE>
```

### Option B: Scaffold with Plugins

Add plugins during scaffold using the `--features` flag. Combine multiple features with commas.

```bash
# Analytics only (SQL queries + dashboards)
databricks apps init --name <APP_NAME> --description "<DESC>" --features analytics --set analytics.sql-warehouse.id=<WAREHOUSE_ID> --run none --profile <PROFILE>

# Lakebase only (PostgreSQL persistence)
databricks apps init --name <APP_NAME> --description "<DESC>" --features lakebase --run none --profile <PROFILE>

# Multiple plugins
databricks apps init --name <APP_NAME> --description "<DESC>" --features analytics,lakebase,genie --set analytics.sql-warehouse.id=<WAREHOUSE_ID> --run none --profile <PROFILE>
```

**Available features:** `analytics`, `lakebase`, `genie`, `files`

### Non-Interactive Shells (AI Assistants, CI)

When running from a non-interactive shell (no TTY), `--name` is mandatory — the CLI will error with `"--name is required in non-interactive mode"` if omitted. Always provide `--name`, `--run none`, and `--profile`.

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

# Verify scaffold produced expected files
ls app.yaml databricks.yml package.json server/server.ts

npm install
npm run dev
```

If any files are missing, the scaffold may have partially failed. Re-run the scaffold command with `--run none` and try again.

This starts the dev server with hot reload on `http://localhost:8000`.

---

## What's Next

After the scaffold is working locally:

- **Build features:** Use the `02-appkit-build` skill to implement UI and backend from a PRD
- **Deploy:** Use the `03-appkit-deploy` skill for the full deploy workflow (config validation, build, deploy, UI verification, error diagnosis). Do not run `databricks apps deploy` directly from this skill — the deploy skill covers it more thoroughly.
- **Add plugins:** Use the `04-appkit-plugin-add` skill to add Lakebase, Analytics, Genie, or Files plugins

---

## Adding a Plugin to an Existing App

To add a plugin (Lakebase, Analytics, Genie, Files) to an existing AppKit project, use the **`04-appkit-plugin-add`** skill. It covers plugin registration, environment variables, `app.yaml` configuration, and frontend integration.

After scaffolding with `--features`, consult the `04-appkit-plugin-add` skill for detailed plugin configuration and frontend integration guidance.

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
| Install agent skills | `git clone --depth 1 https://github.com/databricks/databricks-agent-skills .agents/skills/databricks-skills` (all IDEs) |
| Scaffold blank app | `databricks apps init --name <N> --run none --profile <P>` |
| Scaffold with analytics | `databricks apps init --name <N> --features analytics --set analytics.sql-warehouse.id=<W> --run none --profile <P>` |
| Get warehouse ID | `databricks experimental aitools tools get-default-warehouse --profile <P>` |
| Explore table schema | `databricks experimental aitools tools discover-schema catalog.schema.table --profile <P>` |
| Run ad-hoc SQL | `databricks experimental aitools tools query "SELECT ..." --profile <P>` |
| Install deps | `cd <APP> && npm install` |
| Dev server | `npm run dev` |
| Build | `npm run build` |
| Validate | `databricks apps validate` |
| Deploy | `databricks apps deploy --profile <P>` |
| Browse AppKit docs | `npx @databricks/appkit docs` |
