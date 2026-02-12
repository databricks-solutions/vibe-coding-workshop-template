# Skill Improvement Prompt Template

Reusable prompt for improving existing opinionated skills from generic Databricks reference skills.

---

## The Prompt

Copy the block below, replace the `{placeholders}`, and paste into a new conversation.

---

```
Review and improve the opinionated skill at @data_product_accelerator/skills/{domain}/{skill-name} using
the generic reference material at @databricks-skills/{reference-folder} .

## Context

- **Our skill** (data_product_accelerator/skills/) is part of an opinionated execution framework.
  It prescribes ONE correct way to do things, with mandatory patterns and error prevention.
- **The generic skill** (databricks-skills/) is a reference library offering multiple
  approaches, explanations, and flexibility. It is NOT opinionated.

## Your Task

1. **Read both thoroughly** -- our full skill directory (SKILL.md + references/ + scripts/ +
   assets/) and every file in the generic reference folder.

2. **Identify gaps** -- What does the generic skill cover that ours does NOT?

3. **Filter ruthlessly** -- Only absorb content that meets ALL of these criteria:
   - It is a concrete, opinionated best practice (not "here are 3 options")
   - It prevents a real deployment error or common mistake
   - It applies to our serverless-first, Unity Catalog, Medallion architecture
   - It is NOT already covered in our skill (no duplication)

4. **Do NOT absorb:**
   - Multiple equivalent approaches ("you can do X or Y") -- pick the best one
   - Legacy/deprecated patterns (classic clusters, old API versions)
   - Generic explanations our audience already knows
   - Content that contradicts our existing opinionated choices

5. **Place improvements correctly** using progressive disclosure:
   - **SKILL.md** -- Add brief mentions, "When to Use" triggers, checklist items,
     and deployment commands only. Keep under 500 lines.
   - **references/*.md** -- Add detailed patterns, YAML examples, and gotcha explanations
   - **scripts/*.py** -- Add new validation checks if applicable
   - **assets/templates/*.yaml** -- Update templates with improved defaults

6. **Maintain our conventions:**
   - Mandatory patterns marked with 🔴 MANDATORY
   - Wrong/correct examples with ❌/✅ prefixes
   - Error patterns numbered sequentially (Error N+1, N+2, ...)
   - Validation checklists with `- [ ]` items
   - Version bump in SKILL.md metadata

7. **Output a summary** of what you added, what you intentionally skipped, and why.
```

---

## Placeholders Reference

| Placeholder | Example Values |
|---|---|
| `{domain}` | `common`, `gold`, `silver`, `bronze`, `semantic-layer`, `monitoring`, `ml` |
| `{skill-name}` | `databricks-asset-bundles`, `unity-catalog-constraints`, `metric-views-patterns` |
| `{reference-folder}` | `asset-bundles`, `databricks-unity-catalog`, `databricks-jobs` |

---

## Example Usages

### Example 1: Asset Bundles (already done)
```
Review and improve the opinionated skill at @data_product_accelerator/skills/common/databricks-asset-bundles
using the generic reference material at @databricks-skills/asset-bundles .
```

### Example 2: Unity Catalog Constraints
```
Review and improve the opinionated skill at @data_product_accelerator/skills/common/unity-catalog-constraints
using the generic reference material at @databricks-skills/databricks-unity-catalog .
```

### Example 3: DLT Expectations
```
Review and improve the opinionated skill at @data_product_accelerator/skills/silver/dlt-expectations-patterns
using the generic reference material at @databricks-skills/databricks-dlt .
```

### Example 4: Lakehouse Monitoring
```
Review and improve the opinionated skill at @data_product_accelerator/skills/monitoring/lakehouse-monitoring-comprehensive
using the generic reference material at @databricks-skills/databricks-monitoring .
```

### Example 5: AI/BI Dashboards
```
Review and improve the opinionated skill at @data_product_accelerator/skills/monitoring/databricks-aibi-dashboards
using the generic reference material at @databricks-skills/databricks-dashboards .
```

---

## What "Opinionated" Means in Practice

| Generic Skill Says | Our Opinionated Skill Says |
|---|---|
| "You can use `python_task` or `notebook_task`" | "ALWAYS use `notebook_task`, NEVER `python_task`" |
| "Parameters can be passed via argparse or widgets" | "ALWAYS use `dbutils.widgets.get()`, NEVER `argparse`" |
| "You can use classic clusters or serverless" | "ALWAYS use serverless. Period." |
| "Alerts support these comparison operators..." | "Use `evaluation` not `condition` -- the schema is non-obvious" |
| "Volumes have different permission models..." | "Volumes use `grants` not `permissions` -- do not mix them up" |
| "Here are 3 ways to set warehouse_id..." | "Use `lookup: warehouse:` for portability" |

**The filter:** If the generic skill offers options, pick the best one. If it explains something
that could go wrong, turn it into an error prevention pattern. If it documents a gotcha,
make it a mandatory checklist item.

---

## Quality Checklist for Reviewers

After the agent completes improvements, verify:

- [ ] No "you can do X or Y" language -- exactly one prescribed approach per pattern
- [ ] Every new pattern has ❌ WRONG and ✅ CORRECT examples
- [ ] New errors added sequentially to common-errors.md (Error N+1, ...)
- [ ] Validation script updated with new checks (if applicable)
- [ ] SKILL.md still under 500 lines (detailed content in references/)
- [ ] Version bumped in SKILL.md metadata
- [ ] No duplication with existing content
- [ ] New checklist items added to both SKILL.md and common-errors.md
- [ ] Official documentation links included for new patterns
