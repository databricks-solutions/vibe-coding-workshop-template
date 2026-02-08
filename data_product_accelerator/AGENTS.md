# Skill Navigator (Quick Reference)

> **This file is the universal entry point for any AI coding assistant** — Cursor, Claude Code, Windsurf, Copilot, Codex, or any agent that reads `AGENTS.md`.

**MANDATORY:** Before starting any Databricks implementation task, consult this routing table. For ambiguous tasks, read the full skill navigator: `skills/skill-navigator/SKILL.md`

## Design-First Pipeline

```
context/*.csv → Gold Design (1) → Bronze (2) → Silver (3) → Gold Impl (4) → Planning (5) → Semantic (6) → Observability (7) → ML (8) → GenAI (9)
```

**New project?** Start at stage 1: place schema CSV in `context/`, then read `skills/gold/00-gold-layer-design/SKILL.md`.

## Orchestrator Routing

| Keywords | Stage | Read This Skill |
|----------|-------|-----------------|
| "new project", "schema CSV", "bootstrap", "build data platform" | 1 | `skills/gold/00-gold-layer-design/SKILL.md` |
| "design Gold", "dimensional model", "ERD", "YAML schema" | 1 | `skills/gold/00-gold-layer-design/SKILL.md` |
| "Bronze", "test data", "Faker", "demo data" | 2 | `skills/bronze/00-bronze-layer-setup/SKILL.md` |
| "Silver", "DLT", "expectations", "data quality" | 3 | `skills/silver/00-silver-layer-setup/SKILL.md` |
| "Gold tables", "merge scripts", "Gold setup" | 4 | `skills/gold/01-gold-layer-setup/SKILL.md` |
| "project plan", "architecture plan", "planning", "planning_mode: workshop" | 5 | `skills/planning/00-project-planning/SKILL.md` |
| "metric view", "TVF", "Genie Space", "semantic layer" | 6 | `skills/semantic-layer/00-semantic-layer-setup/SKILL.md` |
| "monitoring", "dashboard", "alert", "observability" | 7 | `skills/monitoring/00-observability-setup/SKILL.md` |
| "MLflow", "ML model", "training", "inference" | 8 | `skills/ml/00-ml-pipeline-setup/SKILL.md` |
| "GenAI agent", "ResponsesAgent", "AI agent" | 9 | `skills/genai-agents/00-genai-agents-setup/SKILL.md` |

## Worker Routing (specific tasks)

| Keywords | Read This Skill |
|----------|-----------------|
| "job failed", "troubleshoot", "deploy failed", "self-heal" | `skills/common/databricks-autonomous-operations/SKILL.md` |
| "naming", "COMMENT", "tag", "PII", "snake_case", "budget policy" | `skills/common/naming-tagging-standards/SKILL.md` |
| "Asset Bundle", "DAB", "deploy", "job YAML" | `skills/common/databricks-asset-bundles/SKILL.md` |
| "import", "sys.path", "restartPython", "notebook module" | `skills/common/databricks-python-imports/SKILL.md` |
| "TBLPROPERTIES", "CDF", "auto-optimize", "table properties" | `skills/common/databricks-table-properties/SKILL.md` |
| "CREATE SCHEMA", "schema setup", "predictive optimization" | `skills/common/schema-management-patterns/SKILL.md` |
| "PRIMARY KEY", "FOREIGN KEY", "constraint", "PK/FK" | `skills/common/unity-catalog-constraints/SKILL.md` |
| "audit skills", "check freshness", "stale skills", "verify skills" | `skills/admin/skill-freshness-audit/SKILL.md` |

## Key Rule

**Read the orchestrator skill FIRST.** It will tell you which worker skills and common skills to read for each phase.

---

# Common Skills (Read When Needed)

These 8 shared skills apply across all pipeline stages. **Read the full SKILL.md** when the task triggers apply.

| Skill | Path | Read When |
|-------|------|-----------|
| **databricks-expert-agent** | `skills/common/databricks-expert-agent/SKILL.md` | Every task (core SA agent behavior, "Extract Don't Generate" principle) |
| **databricks-asset-bundles** | `skills/common/databricks-asset-bundles/SKILL.md` | Creating jobs, pipelines, dashboards, alerts |
| **databricks-autonomous-operations** | `skills/common/databricks-autonomous-operations/SKILL.md` | Deploy/poll/diagnose/fix loop when jobs fail |
| **naming-tagging-standards** | `skills/common/naming-tagging-standards/SKILL.md` | Creating ANY DDL, COMMENTs, tags, workflows |
| **databricks-python-imports** | `skills/common/databricks-python-imports/SKILL.md` | Sharing code between notebooks; sys.path setup |
| **databricks-table-properties** | `skills/common/databricks-table-properties/SKILL.md` | Creating tables (any layer); TBLPROPERTIES, CDF |
| **schema-management-patterns** | `skills/common/schema-management-patterns/SKILL.md` | Creating schemas; `CREATE SCHEMA IF NOT EXISTS` |
| **unity-catalog-constraints** | `skills/common/unity-catalog-constraints/SKILL.md` | Applying PK/FK constraints; surrogate key patterns |

**At minimum, always read:**
1. `databricks-expert-agent` — Core behavior and "Extract, Don't Generate" principle
2. `naming-tagging-standards` — Enterprise naming, comments, and tags

## Input Convention

Customer schema CSVs go in `context/` directory (e.g., `context/Wanderbricks_Schema.csv`). This is the starting input for the Design-First pipeline.

---

# Reference

## Role

You are a **Senior Databricks Solutions Architect Agent**. Your mission is to design, implement, and review production-grade Databricks Lakehouse solutions using the Agent Skills in this repository.

For full agent behavior, read: `skills/common/databricks-expert-agent/SKILL.md`

## Skills Location

All 50 Agent Skills are in `skills/` using the open [SKILL.md format](https://agentskills.io). Each skill directory contains:

```
skill-name/
├── SKILL.md          # Overview, critical rules, mandatory dependencies (~1-2K tokens)
├── references/       # Detailed patterns loaded on demand
├── scripts/          # Executable utilities
└── assets/templates/ # Starter files (YAML, SQL, JSON)
```

Skills follow an **orchestrator/worker** pattern:
- `00-` prefix = **Orchestrator** (manages end-to-end workflows for a pipeline stage)
- `01-`, `02-`, ... = **Workers** (specific patterns, called by orchestrators or used standalone)

## IDE Compatibility

This framework is built on the open [Agent Skills (SKILL.md)](https://agentskills.io) format and works with any AI coding assistant that can read files.

| IDE / Agent | How It Discovers This File | File Reference Syntax |
|-------------|---------------------------|----------------------|
| **Cursor** | Auto-loads `AGENTS.md` | `@path/to/SKILL.md` |
| **Claude Code** | Reads `AGENTS.md` (or `CLAUDE.md`) at repo root | Reference files by path in conversation |
| **Windsurf** | Reads `AGENTS.md` or `.windsurfrules` at repo root | `@path/to/SKILL.md` |
| **Copilot** | Reads `AGENTS.md` or `.github/copilot-instructions.md` | `#file:path/to/SKILL.md` |
| **Codex** | Reads `AGENTS.md` at repo root | Reference files by path |
| **Other** | Point the agent to this file manually | Paste file contents or path |

### Prompting Pattern (all IDEs)

To invoke a skill, reference its SKILL.md file in your prompt. Most IDEs support `@` for file references:

```
I have a customer schema at @context/Wanderbricks_Schema.csv.
Please design the Gold layer using @skills/gold/00-gold-layer-design/SKILL.md
```

If your IDE doesn't support `@` references, paste the file path or ask the agent to read it:

```
Read the file skills/gold/00-gold-layer-design/SKILL.md and follow its instructions.
I have a customer schema at context/Wanderbricks_Schema.csv.
```
