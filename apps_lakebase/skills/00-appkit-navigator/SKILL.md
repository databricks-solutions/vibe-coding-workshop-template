---
name: 00-appkit-navigator
description: >
  Entry-point navigator for Databricks AppKit + Lakebase development. Routes
  tasks to the correct skill based on keyword detection: scaffolding, plugin
  integration, feature building, or deployment. This is a routing skill -- it
  does not generate code. It directs the agent to the correct specialized skill.
  Use this skill as the starting point for any AppKit-related task.
  Triggers on "AppKit", "Lakebase app", "Databricks app", "build app", "deploy
  app", "scaffold app", "add plugin", "AppKit project".
license: Apache-2.0
metadata:
  author: prashanth subrahmanyam
  version: "1.0.0"
  domain: meta
  role: navigator
  standalone: true
  last_verified: "2026-04-10"
  volatility: low
  upstream_sources:
    - https://databricks.github.io/appkit/
    - https://github.com/databricks/databricks-agent-skills
---

# AppKit Lakebase Navigator

Route AppKit + Lakebase tasks to the correct specialized skill.

## Development Lifecycle

AppKit apps follow a linear development lifecycle. Each step maps to a skill or prompt:

```
Step 1          Step 2         Step 3            Step 4                           Step 5
Scaffold ──► Build ──► Deploy mock ──► Setup Lakebase ──► Wire Lakebase      ──► Deploy+E2E
 (01)        (02)     (03-deploy)    (04-plugin-add     (05-lakebase-wiring)   (03-deploy)
                                      + bundle config)
```

| Step | Skill / Prompt | What It Does |
|------|---------------|-------------|
| Scaffold, Build & Test | `01-appkit-scaffold` + `02-appkit-build` | Scaffold a blank AppKit project, build UI with mock data from PRD |
| Deploy to Databricks Apps | `03-appkit-deploy` | Deploy mock-data app to Databricks Apps |
| Setup Lakebase | `04-appkit-plugin-add` + Genie: `apps_lakebase/prompts/setup_lakebase_gc.md` · CLI: `apps_lakebase/skills/04-appkit-plugin-add/SKILL.md` | Install Lakebase plugin and configure bundle resources in `databricks.yml` |
| Wire Lakebase Backend | `04-appkit-plugin-add` + `05-appkit-lakebase-wiring` + Genie: `apps_lakebase/prompts/wire_ui_to_lakebase_gc.md` · CLI: `apps_lakebase/skills/05-appkit-lakebase-wiring/SKILL.md` | Add Lakebase plugin, design schema, build APIs, wire frontend — code changes only, does NOT deploy |
| Deploy and E2E Test | `03-appkit-deploy` + Genie: `apps_lakebase/prompts/deploy_and_test_gc.md` · CLI: `apps_lakebase/skills/03-appkit-deploy/SKILL.md` | Deploy with Lakebase (SP creates DB objects) + E2E test |

**Start at Scaffold, Build & Test** for new projects. Jump to any step if prior steps are complete.

**Lakebase flow:** After **Wire Lakebase Backend**, the app has Lakebase code but runs locally with mock fallback data. **Deploy and E2E Test** deploys so the Service Principal creates database objects, then runs E2E verification.

**Skill-driven vs prompt-driven steps:** Scaffold/Build and Wire Lakebase Backend are skill-driven — the prompt delegates to skills for reusable patterns. Setup Lakebase and Deploy and E2E Test are prompt-driven — the prompt contains application-specific procedures with skills as supplementary references. Skills encode reusable, PRD-independent knowledge (how to scaffold, deploy, register a plugin, wire a database). Prompts encode orchestration and application-specific context (variable values, step prerequisites, handoff instructions).

---

## Task Routing Table

Match the user's request keywords to the correct skill. Read the skill's `SKILL.md` before proceeding.

| Keywords | Route To | Purpose |
|----------|----------|---------|
| "create app", "scaffold", "init", "new app", "bootstrap", "start new project" | `apps_lakebase/skills/01-appkit-scaffold/SKILL.md` | Create a new AppKit project |
| "add plugin", "add lakebase", "add analytics", "add genie", "add files", "integrate postgres", "extend app" | `apps_lakebase/skills/04-appkit-plugin-add/SKILL.md` | Add a plugin to an existing project |
| "build UI", "implement PRD", "create dashboard", "add page", "build features", "develop frontend", "create components" | `apps_lakebase/skills/02-appkit-build/SKILL.md` | Build features from a PRD or spec |
| "setup lakebase", "add lakebase plugin", "lakebase bundle resources", "configure lakebase" | `apps_lakebase/skills/04-appkit-plugin-add/SKILL.md` + Genie: `apps_lakebase/prompts/setup_lakebase_gc.md` | Install Lakebase plugin, declare bundle resources |
| "wire lakebase", "connect lakebase", "lakebase wiring", "lakebase backend", "CRUD API", "lakebase tables", "DDL" | `apps_lakebase/skills/05-appkit-lakebase-wiring/SKILL.md` (patterns) + Genie: `apps_lakebase/prompts/wire_ui_to_lakebase_gc.md` | Wire Lakebase to UI — code changes only, does NOT deploy |
| "database schema design", "useLakebaseData", "ConnectionStatus", "mock fallback", "database design" | `apps_lakebase/skills/05-appkit-lakebase-wiring/SKILL.md` | Lakebase wiring patterns (DDL, API routes, frontend hooks, testing) |
| "e2e test", "test lakebase", "deploy lakebase", "verify live data" | Genie: `apps_lakebase/prompts/deploy_and_test_gc.md` · CLI: `apps_lakebase/skills/03-appkit-deploy/SKILL.md` · Overview: `apps_lakebase/Instructions.md` | Deploy with Lakebase (SP creates DB objects), test APIs, verify idle resilience |
| "lakebase CLI", "lakebase troubleshoot", "lakebase branches", "lakebase roles" | `databricks-lakebase` agent skill (installed via Databricks Agent Skills). Fallback: https://github.com/databricks/databricks-agent-skills/blob/main/skills/databricks-lakebase/SKILL.md | Advanced Lakebase CLI operations, troubleshooting, branches, roles |
| "deploy", "push to production", "ship app", "fix deploy error", "app won't start", "redeploy" | `apps_lakebase/skills/03-appkit-deploy/SKILL.md` | Deploy to Databricks Apps |

---

## Routing Algorithm

```
1. User request received
2. Detect keywords from the routing table above
3. IF "create" / "new" / "scaffold" / "init"         → Read apps_lakebase/skills/01-appkit-scaffold/SKILL.md
4. IF "add plugin" / "integrate" / "add lakebase"     → Read apps_lakebase/skills/04-appkit-plugin-add/SKILL.md
5. IF "build" / "implement" / "PRD" / "UI"            → Read apps_lakebase/skills/02-appkit-build/SKILL.md
6. IF "setup lakebase" / "add lakebase plugin"         → Read apps_lakebase/skills/04-appkit-plugin-add/SKILL.md (plugin install)
                                                        + Genie: apps_lakebase/prompts/setup_lakebase_gc.md
7. IF "wire lakebase" / "connect lakebase" / "DDL"   → Read apps_lakebase/skills/05-appkit-lakebase-wiring/SKILL.md (patterns)
                                                        + Genie: apps_lakebase/prompts/wire_ui_to_lakebase_gc.md
8. IF "e2e test" / "test lakebase" / "deploy lakebase" → Read Genie: apps_lakebase/prompts/deploy_and_test_gc.md
                                                          CLI: apps_lakebase/skills/03-appkit-deploy/SKILL.md
9. IF "lakebase CLI" / "lakebase troubleshoot"        → Read and follow databricks-lakebase agent skill
10. IF "deploy" / "ship" / "fix deploy"               → Read apps_lakebase/skills/03-appkit-deploy/SKILL.md
11. IF ambiguous or multi-step                        → Ask user to clarify, or follow
                                                        the lifecycle order (scaffold → build → deploy)
```

---

## Skill Inventory

| Skill | Path | Role | Standalone | Upstream Sources |
|-------|------|------|-----------|-----------------|
| `01-appkit-scaffold` | `apps_lakebase/skills/01-appkit-scaffold/` | scaffold | yes | [AppKit docs](https://databricks.github.io/appkit/), [databricks-agent-skills](https://github.com/databricks/databricks-agent-skills) |
| `04-appkit-plugin-add` | `apps_lakebase/skills/04-appkit-plugin-add/` | plugin-integration | yes | [AppKit plugin docs](https://databricks.github.io/appkit/docs/plugins/) |
| `02-appkit-build` | `apps_lakebase/skills/02-appkit-build/` | build | no (needs scaffold) | [AppKit docs](https://databricks.github.io/appkit/), [Anthropic frontend-design](https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md) |
| `03-appkit-deploy` | `apps_lakebase/skills/03-appkit-deploy/` | deploy | yes | [App management](https://databricks.github.io/appkit/docs/app-management), [Configuration](https://databricks.github.io/appkit/docs/configuration) |
| `05-appkit-lakebase-wiring` | `apps_lakebase/skills/05-appkit-lakebase-wiring/` | lakebase-wiring | no (needs plugin-add) | [Lakebase plugin docs](https://databricks.github.io/appkit/docs/plugins/lakebase) |

---

To see the full directory tree, run: `find apps_lakebase/skills/ -type f -name "*.md" | sort`

## Skill Dependencies

- **`02-appkit-build`** requires a scaffolded project (`01-appkit-scaffold` must run first)
- **`02-appkit-build`** cross-references `03-appkit-deploy` in its "What's Next" section
- **`03-appkit-deploy`** expects `$APP_NAME` and `$PROFILE` to be set by the caller
- **`04-appkit-plugin-add`** can run at any point after scaffolding
- **`05-appkit-lakebase-wiring`** requires the Lakebase plugin to be registered first (`04-appkit-plugin-add`)

---

## AppKit Documentation (Live)

For the latest API details, always consult the live docs first:

```bash
npx @databricks/appkit docs              # documentation index
npx @databricks/appkit docs "<query>"    # search for a specific topic
npx @databricks/appkit docs --full       # full index with all API entries
```
