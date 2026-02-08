# 04 — Agent Skills System

## Overview

Agent Skills are the primary knowledge mechanism in the Data Product Accelerator. Each skill is a structured directory containing a `SKILL.md` file (the entry point), `references/` files (detailed patterns), `scripts/` (executable utilities), and `assets/templates/` (starter files). Skills follow the [AgentSkills.io specification](https://agentskills.io) and are designed for progressive disclosure — the AI assistant reads only what it needs, keeping context usage efficient.

The skills system replaces the original 46-rule cursor architecture with a more scalable pattern: a single `AGENTS.md` entry point + 50 Agent Skills.

## Skill Types

### Orchestrators (00-*)

Orchestrators manage end-to-end workflows for a pipeline stage. They know which worker skills and common skills to load, in what order, and what each phase produces.

| Property | Value |
|----------|-------|
| Naming | `{domain}/00-{name}/SKILL.md` |
| Token size | ~1-2K tokens |
| Responsibility | Coordinate workers, manage phase flow, declare dependencies |
| Count | 10 (one per pipeline stage + exploration) |

**Example:** `gold/00-gold-layer-design/SKILL.md` — Reads the schema CSV, then orchestrates ERD creation, YAML schema generation, lineage documentation, and business onboarding guide creation by loading 6 worker skills.

### Workers (01-*, 02-*, ...)

Workers provide domain-specific patterns for a single concern. They can be used standalone or called by an orchestrator.

| Property | Value |
|----------|-------|
| Naming | `{domain}/{NN}-{name}/SKILL.md` |
| Token size | ~1-2K tokens (SKILL.md) + 2-8K per reference file |
| Responsibility | Specific patterns (e.g., MERGE operations, ERD syntax, deduplication) |
| Count | 30+ |

**Example:** `gold/05-gold-delta-merge-deduplication/SKILL.md` — Provides the dedup-before-merge pattern that prevents `DELTA_MULTIPLE_SOURCE_ROW_MATCHING_TARGET_ROW_IN_MERGE` errors.

### Common/Shared Skills

Cross-cutting skills that apply across all pipeline stages. Referenced by every orchestrator.

| Property | Value |
|----------|-------|
| Naming | `common/{name}/SKILL.md` (no numbered prefix) |
| Token size | ~1-2K tokens each |
| Responsibility | Enterprise standards, deployment patterns, troubleshooting |
| Count | 8 |

### Admin/Utility Skills

Meta-skills for managing the framework itself.

| Property | Value |
|----------|-------|
| Naming | `admin/{name}/SKILL.md` |
| Responsibility | Skill creation, auditing, documentation, self-improvement |
| Count | 6 |

## Progressive Disclosure

Every skill follows a **4-level progressive disclosure** pattern:

```
Level 1: SKILL.md (~1-2K tokens)
   Overview, critical rules, mandatory dependencies, links to references

Level 2: references/ (2-8K tokens each)
   Detailed patterns, configuration guides, validation checklists
   Only loaded when specific patterns are needed

Level 3: scripts/ (execute on demand)
   Validation utilities, setup scripts, template generators
   Executed as black boxes — don't need to read the source

Level 4: assets/templates/ (copy on demand)
   YAML configs, SQL templates, Python notebook starters
   Copied as starting points, then customized
```

### Skill Directory Structure

```
{domain}/{NN}-{skill-name}/
├── SKILL.md                      # Level 1: Entry point (always read first)
├── references/                   # Level 2: Detailed patterns
│   ├── {pattern-1}.md
│   ├── {pattern-2}.md
│   └── {validation-checklist}.md
├── scripts/                      # Level 3: Executable utilities
│   ├── {setup_script}.py
│   └── {validation_script}.py
└── assets/                       # Level 4: Starter templates
    └── templates/
        ├── {config-template}.yaml
        └── {job-template}.yml
```

### How the AI Navigates

1. **Read SKILL.md first** — Contains overview, critical rules, and links
2. **Read specific references/** — Only when detailed patterns are needed
3. **Execute scripts/** — As black-box utilities when validation or setup is needed
4. **Copy assets/templates/** — As starting points for new files

## Context Budget Management

The skills-first architecture is designed to stay within Claude Opus's 200K token limit.

| Tier | What | Token Budget | Loaded When |
|------|------|-------------|-------------|
| Tier 1 | AGENTS.md entry point | ~1K tokens | Every turn (always on) |
| Tier 2 | Orchestrator SKILL.md | ~1-2K tokens | Task routed to domain |
| Tier 3 | Worker SKILL.md files | ~1-2K each | Orchestrator requests them |
| Tier 4 | Reference files | ~2-8K each | Specific pattern needed |

### Budget Zones

| Zone | Token Range | Guidance |
|------|------------|----------|
| Green | 0-20K | Load multiple SKILL.md files freely |
| Yellow | 20-50K | Be selective about references/ |
| Red | 50K+ | Reference skill paths, don't load; execute scripts as black boxes |

## SKILL.md Anatomy

Every SKILL.md follows a consistent structure:

```yaml
---
name: skill-name
description: >
  What this skill does and when to use it.
metadata:
  author: author name
  version: "1.0"
  domain: gold | silver | bronze | semantic-layer | monitoring | ml | genai-agents | planning | admin | common
  role: orchestrator | worker | utility
  pipeline_stage: 1-9
  standalone: true | false
  dependencies:
    workers: [list of worker skills to read]
    common: [list of common skills to read]
  triggers:
    - "keyword 1"
    - "keyword 2"
  last_verified: "YYYY-MM-DD"
  volatility: low | medium | high
---

# Skill Title

## Overview (brief)
## Critical Rules (non-negotiable patterns)
## Mandatory Dependencies (which skills to read)
## Phase Workflow (for orchestrators)
## Reference Files (links to references/)
```

## Routing Algorithm

```
1. User request received
2. Routing rules (always loaded) detect keywords
3. IF keywords match an ORCHESTRATOR → Route to orchestrator
   └─ Orchestrator reads its worker skills and common skills
4. IF keywords match a WORKER (no orchestrator context) → Route to worker directly
   └─ Workers with standalone: true work independently
5. IF keywords match a COMMON skill → Route to common skill
   └─ Common skills are always standalone
```

## The "Extract, Don't Generate" Principle

This is the most critical pattern enforced by the skills system. It applies to every stage:

| What to Extract | Source of Truth | Extraction Method |
|----------------|----------------|-------------------|
| Table names | `gold_layer_design/yaml/{domain}/*.yaml` | Parse YAML `table_name` field |
| Column names | `gold_layer_design/yaml/{domain}/*.yaml` | Parse YAML `columns[].name` field |
| Column types | `gold_layer_design/yaml/{domain}/*.yaml` | Parse YAML `columns[].type` field |
| Primary keys | `gold_layer_design/yaml/{domain}/*.yaml` | Parse YAML `primary_key` field |
| Foreign keys | `gold_layer_design/yaml/{domain}/*.yaml` | Parse YAML `foreign_keys[]` field |
| Metric view names | `src/semantic/metric_views/*.yaml` | Use filename (without `.yaml`) |
| TVF names | `src/semantic/tvfs/*.sql` | Parse `CREATE OR REPLACE FUNCTION` |
| Monitor names | Monitoring YAML configs | Parse YAML `monitor_name` field |

**Why:** AI code generation hallucinations are the #1 source of production errors. Extracting names from existing source files ensures 100% accuracy.

## Validation Checklist

Before deploying any skill-generated code:

- [ ] Table names extracted from Gold YAML (not hardcoded)
- [ ] Column names extracted from Gold YAML/metadata (not generated)
- [ ] Primary/foreign keys extracted from Gold YAML
- [ ] No hardcoded lists of tables, columns, or functions
- [ ] Schema validation scripts run before deployment
- [ ] Asset Bundle deployment tested in dev target

## References

- [AgentSkills.io Specification](https://agentskills.io) — Skill format standard
- [Skill Navigator](../../skills/skill-navigator/SKILL.md) — Full routing table
- [05-Skill Domains](05-skill-domains.md) — Complete per-domain inventory
- [06-Common Skills](06-common-skills.md) — Shared skill deep dive
