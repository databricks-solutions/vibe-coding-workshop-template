# 08 — Operations Guide

## Overview

This guide covers the ongoing maintenance, evolution, and operational procedures for the Data Product Accelerator. It covers skill freshness auditing, self-improvement workflows, framework updates, and day-to-day operational patterns.

## Daily Operations

### Health Checks

| Check | Frequency | How | Expected Result |
|-------|-----------|-----|-----------------|
| Skill count | Weekly | `find skills -name "SKILL.md" \| wc -l` | 50 skills present |
| Entry point | Weekly | `test -f AGENTS.md && echo "OK"` | AGENTS.md present |
| Broken references | Monthly | Grep for dead links in SKILL.md files | 0 broken links |
| Skill freshness | Monthly | Run `skill-freshness-audit` skill | All skills within verification window |

### Monitoring the Framework

| What to Monitor | Why | Action if Degraded |
|----------------|-----|-------------------|
| Skill accuracy | Databricks API/patterns change | Run freshness audit, update affected skills |
| Context budget | Skills growing too large | Refactor SKILL.md content to references/ |
| Orchestrator coverage | New platform features not covered | Create new worker skill, update orchestrator |
| User feedback | Skills producing incorrect code | Trigger self-improvement workflow |

## Skill Freshness Auditing

### Purpose

Skills encode Databricks platform patterns that evolve over time. The `admin/skill-freshness-audit` skill provides systematic verification that all skills remain current with official documentation.

### Running an Audit

```
Audit skill freshness using @skills/admin/skill-freshness-audit/SKILL.md
```

The audit skill:
1. Inventories all skills and their `last_verified` dates
2. Classifies skills by volatility (low/medium/high)
3. Fetches verification anchor URLs from each skill
4. Compares patterns against live documentation
5. Reports drift and recommends updates

### Volatility Classification

| Volatility | Verification Window | Examples |
|------------|-------------------|----------|
| Low | 6 months | Naming conventions, SQL syntax, Delta properties |
| Medium | 3 months | SDK APIs, DAB patterns, monitoring APIs |
| High | 1 month | GenAI patterns (MLflow 3.x), Genie APIs, new features |

### Audit Report Format

```
SKILL FRESHNESS AUDIT — YYYY-MM-DD

SUMMARY: X skills audited, Y current, Z stale

STALE SKILLS (action required):
  - genai-agents/01-responses-agent-patterns (last verified: 2025-10-01)
    Drift: ResponsesAgent constructor signature changed in MLflow 3.1
    Action: Update streaming patterns in references/streaming-patterns.md

CURRENT SKILLS (no action):
  - gold/02-yaml-driven-gold-setup (last verified: 2026-01-15) ✓
  ...
```

## Self-Improvement Workflow

### When to Trigger

The `admin/self-improvement` skill should be invoked when:
- A skill produces incorrect code during implementation
- A new Databricks pattern is discovered that isn't covered
- A deployment fails due to a pattern the skills got wrong
- After completing a complex task with learnings to capture

### How It Works

```
Learn from this error using @skills/admin/self-improvement/SKILL.md
```

The self-improvement skill:
1. Analyzes the error or learning
2. **Searches existing skills first** (always update over create)
3. Updates the relevant skill's SKILL.md or references/
4. Adds verification anchors for the corrected pattern
5. Updates `last_verified` date

### Key Principle

**Always update existing skills over creating new ones.** The self-improvement skill searches all existing skills before considering a new skill creation.

## Adding New Skills

### When to Create a New Skill

- New Databricks platform feature with distinct patterns (e.g., new API)
- Existing skill exceeds 500 lines in SKILL.md (split needed)
- New domain not covered by any existing skill directory

### Creation Process

```
Create a new skill using @skills/admin/create-agent-skill/SKILL.md
```

### Required Steps

1. Choose the correct domain directory
2. Assign the correct numbered prefix:
   - `00-` for orchestrators (rare — only for new pipeline stages)
   - `01-`, `02-`, etc. for workers
3. Create the directory structure:
   ```
   {domain}/{NN}-{skill-name}/
   ├── SKILL.md
   ├── references/
   │   └── {pattern}.md
   ├── scripts/
   │   └── {utility}.py
   └── assets/templates/
       └── {template}.yaml
   ```
4. Keep SKILL.md under 500 lines (use references/ for detail)
5. Add frontmatter with `name`, `description`, `metadata`
6. Update the skill navigator if adding new routing keywords
7. Update the relevant orchestrator's `dependencies.workers` list

## Updating Existing Skills

### Process

1. Read the current SKILL.md and relevant references/
2. Make the change (pattern update, bug fix, new pattern)
3. Update `metadata.last_verified` to today's date
4. If the change affects other skills, update them too
5. Run the freshness audit to verify no regressions

### What Not to Change

- Skill directory name (breaks references from other skills)
- Numbered prefix (breaks orchestrator dependency declarations)
- Frontmatter `name` field (breaks routing)

## Maintenance Procedures

### Scheduled Maintenance

| Task | Frequency | Steps | Owner |
|------|-----------|-------|-------|
| Skill freshness audit | Monthly | Run `skill-freshness-audit` | Framework maintainer |
| Dead link check | Monthly | Grep external URLs, verify they resolve | Framework maintainer |
| Context budget review | Quarterly | Measure total SKILL.md token counts | Framework maintainer |
| Databricks release review | Per release | Check changelog for pattern-breaking changes | Framework maintainer |

### Ad-hoc Maintenance

| Trigger | Action |
|---------|--------|
| Databricks platform update | Review affected domain skills, update patterns |
| Skill produces wrong code | Run self-improvement workflow |
| New best practice discovered | Update relevant skill or create worker skill |
| Context budget exceeded | Move SKILL.md content to references/ |

## Incident Response

### Skill Produces Incorrect Code

1. **Identify** which skill was loaded (check agent's tool calls)
2. **Isolate** the incorrect pattern (which reference file or SKILL.md section)
3. **Fix** the pattern using self-improvement skill
4. **Verify** the fix produces correct code on a test case
5. **Update** `last_verified` date

### Deployment Failure Due to Skill Pattern

1. **Read error** from Databricks job/pipeline logs
2. **Diagnose** using `databricks-autonomous-operations` skill
3. **Fix** the generated code
4. **If pattern is wrong** — update the skill (not just the generated code)
5. **Redeploy** and verify

### Context Budget Overflow

1. **Symptom:** AI assistant gives incomplete or confused responses
2. **Diagnose:** Check which skills were loaded in the conversation
3. **Fix:** Start a new conversation, load only necessary skills
4. **Prevent:** Ensure SKILL.md files stay under 500 lines

## Access Control

### Framework Maintenance

| Role | Permissions | Responsibility |
|------|-------------|----------------|
| Framework Maintainer | Full write to `skills/` | Skill updates, freshness audits |
| Contributor | PR to `skills/` | New patterns, bug fixes |
| User | Read `skills/` | Use skills via Cursor Agent |

### Skill Update Procedure

All skill changes should go through version control (git). The recommended workflow:

1. Branch from `main`
2. Make skill changes
3. Test with a sample implementation
4. Create PR with description of what changed and why
5. Review and merge

## Performance Tuning

### Key Metrics

| Metric | Target | Action if Exceeded |
|--------|--------|-------------------|
| SKILL.md line count | < 500 lines | Move content to references/ |
| Total skills loaded per conversation | < 10 | Start new conversation between stages |
| Reference file size | < 8K tokens | Split into multiple reference files |
| Time per pipeline stage | See [07-Implementation Guide](07-implementation-guide.md) | Check if skill patterns need optimization |

## References

- [Skill Freshness Audit](../../skills/admin/skill-freshness-audit/SKILL.md)
- [Self-Improvement](../../skills/admin/self-improvement/SKILL.md)
- [Create Agent Skill](../../skills/admin/create-agent-skill/SKILL.md)
- [Skill Navigator](../../skills/skill-navigator/SKILL.md)
