---
name: appkit-lakebase-navigator
description: >
  Entry-point navigator for Databricks AppKit + Lakebase development. Routes
  tasks to the correct skill based on keyword detection: scaffolding, plugin
  integration, feature building, or deployment. Use this skill as the starting
  point for any AppKit-related task to determine which specialized skill to load.
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

AppKit apps follow a linear development lifecycle. Each step maps to a skill:

```
Scaffold (1) ──► Plugin Add (optional) ──► Build (2) ──► Deploy (3)
```

| Step | Skill | What It Does |
|------|-------|-------------|
| 1 | `appkit-scaffold` | Create a new AppKit project (blank or with plugins) |
| — | `appkit-plugin-add` | Add a plugin to an existing project (Lakebase, Analytics, Genie, Files) |
| 2 | `appkit-build` | Implement UI and backend features from a PRD |
| 3 | `appkit-deploy` | Deploy to Databricks Apps, verify, fix errors |

**Start at step 1** for new projects. Jump to any step if the prior steps are already complete.

---

## Task Routing Table

Match the user's request keywords to the correct skill. Read the skill's `SKILL.md` before proceeding.

| Keywords | Route To | Purpose |
|----------|----------|---------|
| "create app", "scaffold", "init", "new app", "bootstrap", "start new project" | `appkit-scaffold/SKILL.md` | Create a new AppKit project |
| "add plugin", "add lakebase", "add analytics", "add genie", "add files", "integrate postgres", "extend app" | `appkit-plugin-add/SKILL.md` | Add a plugin to an existing project |
| "build UI", "implement PRD", "create dashboard", "add page", "build features", "develop frontend", "create components" | `appkit-build/SKILL.md` | Build features from a PRD or spec |
| "deploy", "push to production", "ship app", "fix deploy error", "app won't start", "redeploy" | `appkit-deploy/SKILL.md` | Deploy to Databricks Apps |

---

## Routing Algorithm

```
1. User request received
2. Detect keywords from the routing table above
3. IF "create" / "new" / "scaffold" / "init"     → Read appkit-scaffold/SKILL.md
4. IF "add plugin" / "integrate" / "add lakebase" → Read appkit-plugin-add/SKILL.md
5. IF "build" / "implement" / "PRD" / "UI"        → Read appkit-build/SKILL.md
6. IF "deploy" / "ship" / "fix deploy"            → Read appkit-deploy/SKILL.md
7. IF ambiguous or multi-step                      → Ask user to clarify, or follow
                                                     the lifecycle order (scaffold → build → deploy)
```

---

## Skill Inventory

| Skill | Path | Role | Standalone | Upstream Sources |
|-------|------|------|-----------|-----------------|
| `appkit-scaffold` | `apps_lakebase/skills/appkit-scaffold/` | scaffold | yes | [AppKit docs](https://databricks.github.io/appkit/), [databricks-agent-skills](https://github.com/databricks/databricks-agent-skills) |
| `appkit-plugin-add` | `apps_lakebase/skills/appkit-plugin-add/` | plugin-integration | yes | [AppKit plugin docs](https://databricks.github.io/appkit/docs/plugins/) |
| `appkit-build` | `apps_lakebase/skills/appkit-build/` | build | no (needs scaffold) | [AppKit docs](https://databricks.github.io/appkit/), [Anthropic frontend-design](https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md) |
| `appkit-deploy` | `apps_lakebase/skills/appkit-deploy/` | deploy | yes | [App management](https://databricks.github.io/appkit/docs/app-management), [Configuration](https://databricks.github.io/appkit/docs/configuration) |

---

## Skill Directory Map

```
apps_lakebase/skills/
├── appkit-lakebase-navigator/          # THIS NAVIGATOR (entry point)
│   └── SKILL.md
│
├── appkit-scaffold/                    # Step 1: Create new AppKit project
│   ├── SKILL.md
│   ├── references/
│   │   └── appkit-project-structure.md
│   └── scripts/
│       └── install-agent-skills.sh
│
├── appkit-plugin-add/                  # Add plugins to existing project
│   ├── SKILL.md
│   └── references/
│       ├── plugin-lakebase.md
│       ├── plugin-analytics.md
│       ├── plugin-genie.md
│       └── plugin-files.md
│
├── appkit-build/                       # Step 2: Build UI + backend from PRD
│   ├── SKILL.md
│   └── references/
│       ├── design-quality.md
│       └── llm-guardrails.md
│
└── appkit-deploy/                      # Step 3: Deploy to Databricks Apps
    ├── SKILL.md
    └── references/
        └── app-management.md
```

---

## Skill Dependencies

- **`appkit-build`** requires a scaffolded project (`appkit-scaffold` must run first)
- **`appkit-build`** cross-references `appkit-deploy` in its "What's Next" section
- **`appkit-deploy`** expects `$APP_NAME` and `$PROFILE` to be set by the caller
- **`appkit-plugin-add`** can run at any point after scaffolding

---

## AppKit Documentation (Live)

For the latest API details, always consult the live docs first:

```bash
npx @databricks/appkit docs              # documentation index
npx @databricks/appkit docs "<query>"    # search for a specific topic
npx @databricks/appkit docs --full       # full index with all API entries
```
