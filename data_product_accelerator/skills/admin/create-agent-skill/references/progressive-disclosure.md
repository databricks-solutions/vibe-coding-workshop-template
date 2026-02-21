# Progressive Disclosure Patterns for Agent Skills

When creating skills with substantial content, use progressive disclosure to manage context efficiently.

## The Three-Level System

Agent Skills use a three-level loading system:

| Level | Content | When Loaded | Token Budget |
|-------|---------|-------------|--------------|
| 1. Metadata | `name` + `description` | Always (skill discovery) | ~100 words |
| 2. Instructions | SKILL.md body | When skill triggers | <5K words |
| 3. Resources | References, scripts, assets | When needed | Unlimited |

## When to Split Content

Split content from SKILL.md into separate files when:

1. **SKILL.md exceeds 500 lines** — Always split
2. **Distinct sections can stand alone** (e.g., API reference, examples)
3. **Content is only needed for specific scenarios** (e.g., troubleshooting)
4. **Multiple code examples could be scripts** (>10 lines each)

## Splitting Strategies

### Strategy 1: Overview + Reference Files

Keep a high-level workflow in SKILL.md, move detailed docs to references/.

```
my-skill/
├── SKILL.md              # Overview, quick reference, decision guide
└── references/
    ├── api-reference.md  # Detailed API documentation
    ├── patterns.md       # Extended pattern library
    └── troubleshoot.md   # Error resolution guide
```

**SKILL.md pattern:**
```markdown
## Quick Reference

Key method: `client.do_thing(param)` — See [API Reference](references/api-reference.md)

Common patterns: Always validate input first — See [Patterns](references/patterns.md)

Errors: Check [Troubleshooting](references/troubleshoot.md)
```

### Strategy 2: Domain-Specific Split

When a skill covers multiple sub-domains:

```
multi-domain-skill/
├── SKILL.md              # Navigation and common patterns
└── references/
    ├── domain-a.md       # Everything about Domain A
    ├── domain-b.md       # Everything about Domain B
    └── domain-c.md       # Everything about Domain C
```

### Strategy 3: Extract Executables

When a skill contains runnable code:

```
automation-skill/
├── SKILL.md              # When/how to run, expected output
├── scripts/
│   ├── validate.py       # Validation utility
│   └── setup.sh          # Setup automation
└── assets/
    └── templates/
        └── config.yaml   # Starter configuration
```

**SKILL.md pattern:**
```markdown
## Validation

Run the validation script to check your configuration:

```bash
python scripts/validate.py --config path/to/config.yaml
```

Expected output: `✅ All checks passed` or specific error messages.
```

### Strategy 4: Working Memory Management (Orchestrators)

Orchestrator skills spanning 3+ phases should include a `## Working Memory Management` section instructing the agent on note-taking discipline:

- **What to persist after each phase** — a brief summary note with key outputs and decisions
- **What to keep in working memory** — only the current phase's worker skill, the primary metadata object (e.g., table inventory dict), and the previous phase's summary note
- **What to discard** — intermediate tool outputs (DDL strings, full DataFrames, raw SQL results) that are reproducible from source files
- **How workers chain** — via "Notes to Carry Forward" and "Next Step" sections at the end of each worker skill

**Worker skill requirements:**
- Every worker must end with a `## [Domain] Notes to Carry Forward` section listing what the next worker needs
- Every worker must end with a `## Next Step` section pointing to the next worker in the chain

**Reference implementation:** `gold/01-gold-layer-setup/SKILL.md` (Working Memory Management section)

**Common skills (always-loaded)** should include a `## Essential Rules (Retain in Working Memory)` section — a condensed 5-rule summary that agents can retain after releasing the full skill content.

## Guidelines

### Keep in SKILL.md
- Core workflow steps (the "how to use" guide)
- Essential patterns (1-2 examples each)
- Decision guides ("if X, do Y; if Z, do W")
- Navigation links to references

### Move to references/
- Comprehensive API documentation
- Extended examples (>5 examples)
- Edge case handling
- Historical context or background
- Validation checklists with >10 items

### Move to scripts/
- Reusable code (>10 lines)
- Validation utilities
- Automation tools
- Code generation helpers

### Move to assets/templates/
- Configuration file templates
- SQL DDL templates
- Job/workflow YAML starters
- Skeleton files meant to be copied

## Validation Checklist

After splitting a skill:

- [ ] SKILL.md is under 500 lines
- [ ] Core workflow is understandable without reading references
- [ ] References are one level deep (no references to references)
- [ ] Each reference file has a single, clear purpose
- [ ] Navigation from SKILL.md to references is explicit (links, not just mentions)
- [ ] Scripts have usage instructions in SKILL.md
- [ ] Templates have "how to customize" notes in SKILL.md
- [ ] Orchestrators with 3+ phases have a `## Working Memory Management` section
- [ ] All workers have "Notes to Carry Forward" and "Next Step" sections
- [ ] Always-loaded common skills have an "Essential Rules (Retain in Working Memory)" summary
