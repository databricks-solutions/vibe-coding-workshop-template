# Agent Skill Examples

Annotated examples of well-structured Agent Skills to guide creation of new skills.

---

## Example 1: Minimal Skill (No Subdirectories)

A small skill that fits entirely in SKILL.md. Good for focused, single-pattern skills.

```
schema-management-patterns/
└── SKILL.md    (186 lines)
```

**Frontmatter:**
```yaml
---
name: schema-management-patterns
description: Provides patterns for creating and managing Unity Catalog schemas in Databricks. Covers CREATE SCHEMA IF NOT EXISTS, TBLPROPERTIES for Predictive Optimization, and schema-level governance tagging. Use when creating new schemas, enabling optimization features, or standardizing schema creation across environments.
metadata:
  author: databricks-sa
  version: "1.0"
  domain: common
---
```

**Why it works:**
- Self-contained — no need for references/
- Under 200 lines — well within the 500-line budget
- Clear trigger keywords in description: "schema", "CREATE SCHEMA", "optimization"

---

## Example 2: Medium Skill (With References)

A skill with detailed patterns split into references for progressive disclosure.

```
metric-views-patterns/
├── SKILL.md                            (~150 lines)
└── references/
    ├── yaml-reference.md               (YAML schema documentation)
    ├── validation-checklist.md         (Pre-deployment checks)
    └── advanced-patterns.md            (Window measures, joins)
```

**SKILL.md structure:**
```markdown
# Metric Views Patterns

Overview and critical syntax rules.

## Critical Rules
1. Always use `WITH METRICS LANGUAGE YAML`
2. Source must be a Delta table in Unity Catalog
3. All STRING parameters for Genie compatibility

## Quick Reference
[Table of essential YAML fields]

## Detailed Resources
- [YAML Reference](references/yaml-reference.md) — Complete field documentation
- [Validation Checklist](references/validation-checklist.md) — Pre-deployment checks
- [Advanced Patterns](references/advanced-patterns.md) — Window measures, joins
```

**Why it works:**
- SKILL.md gives you enough to start immediately
- References loaded only when you need specifics
- Clear navigation from SKILL.md to each reference

---

## Example 3: Full Skill (References + Scripts + Assets)

A comprehensive skill using all optional directories.

```
databricks-asset-bundles/
├── SKILL.md                            (~120 lines)
├── references/
│   ├── configuration-guide.md          (Bundle YAML structure)
│   ├── job-patterns.md                 (Job types and configuration)
│   └── common-errors.md               (Error resolution)
├── scripts/
│   └── validate_bundle.py             (Bundle validation utility)
└── assets/
    └── templates/
        └── bundle-template.yaml       (Starter bundle configuration)
```

**SKILL.md structure:**
```markdown
# Databricks Asset Bundles

## Critical Rules
1. Use `notebook_task` not `python_task`
2. Use `base_parameters` dict, not CLI-style `parameters`
3. Never define experiments in bundles

## Quick Start
Copy [bundle-template.yaml](assets/templates/bundle-template.yaml) and customize.

## Validation
Run `python scripts/validate_bundle.py` before deploying.

## Detailed Guides
- [Configuration Guide](references/configuration-guide.md)
- [Job Patterns](references/job-patterns.md)
- [Common Errors](references/common-errors.md)
```

**Why it works:**
- Quick start with copy-paste template
- Validation via script (execute, don't read)
- Three reference files for deep dives
- SKILL.md stays under 150 lines

---

## Example 4: Orchestrator Skill

A skill that coordinates multiple other skills in sequence.

```
gold-layer-design/
├── SKILL.md                            (~350 lines)
├── references/
│   ├── dimensional-modeling-guide.md
│   ├── yaml-schema-patterns.md
│   └── validation-checklists.md
├── scripts/
│   └── generate_lineage_csv.py
└── assets/
    └── templates/
        ├── business-onboarding-template.md
        └── column-lineage-template.csv
```

**SKILL.md structure:**
```markdown
# Gold Layer Design (Orchestrator)

## Workflow Overview
1. Gather business requirements → Use this skill
2. Create dimensional model → Calls `05-erd-diagrams`
3. Define YAML schemas → Calls `01-yaml-table-setup`
4. Document for LLMs → Calls `06-table-documentation`
5. Validate design → Calls `07-design-validation`

## Step 1: Business Requirements
[Instructions + link to onboarding template]

## Step 2: Dimensional Model
[Instructions + delegates to 05-erd-diagrams skill]
...
```

**Why it works:**
- Clearly identifies itself as an orchestrator
- Names the skills it delegates to
- Each step either does work or delegates
- Has its own templates for unique tasks

---

## Anti-Patterns to Avoid

### Too Many Small Skills
**BAD:** 20 skills with 50 lines each
**GOOD:** 5 skills with 200 lines each + references

### Deeply Nested References
**BAD:** `references/auth/oauth/tokens.md` (3 levels deep)
**GOOD:** `references/auth-oauth-tokens.md` (flat)

### Missing Trigger Keywords
**BAD:** `description: Handles authentication.`
**GOOD:** `description: Handles OAuth 2.0 authentication for Databricks APIs. Use when configuring API tokens, service principals, or OAuth flows. Triggers on "auth", "token", "OAuth", "service principal".`

### SKILL.md as Dump
**BAD:** 800-line SKILL.md with everything
**GOOD:** 150-line SKILL.md with clear links to 3 reference files
