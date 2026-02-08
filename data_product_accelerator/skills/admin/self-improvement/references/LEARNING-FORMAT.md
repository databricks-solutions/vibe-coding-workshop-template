# Skill Creation Reference

Detailed documentation for creating skills from learnings.

## Skill Naming Convention

```
kebab-case-descriptive-name
```

**Requirements:**
- Max 64 characters
- Lowercase letters, numbers, and hyphens only
- No leading/trailing hyphens
- No consecutive hyphens

**Examples:**
- `notebook-import-patterns`
- `api-version-validation`
- `databricks-naming-conventions`

## Directory Structure

```
skills/{skill-name}/
├── SKILL.md              # Required - main instructions
├── references/           # Optional - detailed documentation
│   └── REFERENCE.md
├── assets/               # Optional - templates, examples
│   └── template.md
└── scripts/              # Optional - utility scripts
    └── helper.sh
```

## Description Best Practices

The description is **critical** for skill discovery. Include:

1. **WHAT** the skill does (first sentence)
2. **WHEN** to use it (trigger scenarios)
3. **Trigger keywords** that should activate this skill

**Good examples:**
```yaml
description: Prevent import failures in Databricks notebooks. Use when importing helper functions, working with DLT notebooks, or encountering cryptic import errors.

description: Correct naming conventions for Databricks tables across layers. Use before writing queries, creating tables, or when seeing "table not found" errors.

description: Avoid complex sys.path workarounds. Use when tempted to manipulate Python path or after 2+ failed import attempts.
```

**Bad examples:**
```yaml
# Too vague
description: Helps with imports.

# Missing triggers
description: A skill about naming conventions.

# Too long (over 1024 chars)
description: This skill provides comprehensive documentation about...
```

## Skill Categories

### Error Prevention
Skills that prevent recurring technical errors.

**Characteristics:**
- Specific error message or behavior to watch for
- Clear correct vs incorrect patterns
- Actionable prevention checklist

**Template focus:**
- Emphasize "Common Symptoms" section
- Include specific error messages
- Provide exact code fixes

### Assumption Correction
Skills that correct common misconceptions.

**Characteristics:**
- Expectation vs reality mismatch
- No error message (silent failure)
- Verification steps

**Template focus:**
- Emphasize "The Problem" section with clear contrast
- Include verification commands
- Focus on "how to check" before assuming

### Simplification
Skills that document simpler approaches.

**Characteristics:**
- Complex approach that didn't work
- Simple solution discovered
- Recognition pattern for when to simplify

**Template focus:**
- Show the overcomplicated approach clearly
- Emphasize the simple solution
- Include "when to step back" guidance

## Updating Existing Skills

When updating rather than creating:

### What to Update
- Add new example to existing section
- Add new symptom to "Common Symptoms"
- Expand prevention checklist
- Add reference links

### What NOT to Change
- Skill name (would break references)
- Core problem description (unless incorrect)
- Existing working patterns

### Update Pattern
```markdown
## The Solution

[Existing content...]

### Additional Pattern (Added YYYY-MM-DD)
[New pattern discovered]
```

## Cross-Referencing Skills

### Linking to Related Skills
```markdown
## References

- Related: [notebook-import-patterns](../notebook-import-patterns/SKILL.md)
- See also: [databricks-naming-conventions](../databricks-naming-conventions/SKILL.md)
```

## Maintenance

### Weekly Review
1. Check for duplicate skills (merge if overlapping)
2. Update outdated patterns
3. Add new examples from recent work

### Skill Consolidation
If two skills overlap significantly:
1. Merge into one skill with broader scope
2. Update description to cover both cases
3. Delete the narrower skill
4. Update any references
