# Workshop Mode Profile

> **This file is ONLY read when the user explicitly includes `planning_mode: workshop` in their prompt.** If you are reading this file without that explicit trigger, STOP and use the default Data Product Acceleration mode instead.

## Purpose

Workshop mode produces a **minimal representative plan** for Learning & Enablement scenarios. The goal is to teach participants the full pattern vocabulary (TVFs, Metric Views, Genie Spaces, Monitoring, Alerts) with the fewest artifacts possible — just enough to demonstrate each pattern type without overwhelming workshop participants.

## Artifact Caps

| Artifact Type | Workshop Cap | Selection Criteria |
|---------------|-------------|-------------------|
| **Domains** | 1-2 max | Pick the domain with the richest Gold table relationships |
| **TVFs** | 3-5 total | One per parameter pattern: (1) date-range, (2) entity-filter, (3) top-N. Optionally add (4) cross-domain join and (5) period-comparison if time permits |
| **Metric Views** | 1-2 total | One per fact table — pick the fact with the most dimension joins |
| **Genie Spaces** | 1 unified | Combine all workshop assets into a single space |
| **Dashboards** | 0-1 | Optional; only if time permits |
| **Monitors** | 1-2 | One fact table monitor + one dimension monitor |
| **Alerts** | 2-3 | One CRITICAL + one WARNING + optionally one INFO (demonstrate severity pattern) |
| **ML Models** | 0-1 | Optional; skip unless explicitly requested |
| **Agents (Phase 2)** | 0-1 | Skip Phase 2 entirely unless explicitly requested |
| **Frontend (Phase 3)** | 0 | Skip Phase 3 entirely unless explicitly requested |
| **Business Questions per Domain** | 3-5 | Most representative questions only |
| **Benchmark Questions per Genie Space** | 3-5 | Focus on pattern variety over coverage |

## Phase Scope

| Include by Default | Include If Requested | Exclude by Default |
|--------------------|---------------------|--------------------|
| 1.2 TVFs | 1.4 Lakehouse Monitoring | 1.1 ML Models |
| 1.3 Metric Views | 1.5 AI/BI Dashboards | Phase 2 (Agents) |
| 1.6 Genie Spaces | 1.7 Alerting | Phase 3 (Frontend) |

## Selection Principle

Pick the **most representative** artifact for each pattern type. Prefer **variety of patterns** over depth in a single domain:

- **TVFs:** Choose examples that show different parameter combinations (date range only, entity filter, top-N with optional parameters). The goal is to demonstrate the TVF pattern vocabulary, not exhaustive coverage.
- **Metric Views:** Choose the fact table with the richest dimension joins to demonstrate the full YAML syntax (measures, dimensions, joins).
- **Genie Space:** One unified space with all workshop assets. Keep under 15 total assets for focused NL quality.
- **Monitors:** One fact table (demonstrates custom metrics) + one dimension (demonstrates baseline monitoring).
- **Alerts:** One CRITICAL threshold alert + one WARNING percentage-change alert (demonstrates severity and query pattern variety).

## Confirmation Protocol

When workshop mode is detected, confirm with the user before proceeding:

> "**Workshop mode activated.** This will produce a minimal representative plan with:
> - 1-2 domains (most representative)
> - 3-5 TVFs (one per parameter pattern)
> - 1-2 Metric Views
> - 1 Genie Space (unified)
> - Phase 1 only (Phase 2/3 excluded unless requested)
>
> Proceed?"

Only after confirmation, apply the caps from this profile as upper-bound constraints over the standard rationalization framework in the main SKILL.md.

## Manifest Behavior

- Add `planning_mode: workshop` to all generated manifest YAML files as a top-level field
- Downstream orchestrators seeing `planning_mode: workshop` MUST NOT expand beyond the listed artifacts via self-discovery
- The manifest is a **hard ceiling** in workshop mode — no additional artifacts should be inferred or created

```yaml
# Example manifest header for workshop mode
version: 1
manifest_type: semantic-layer
planning_mode: workshop    # Downstream: do NOT expand beyond listed artifacts
```

## Estimation (Workshop Mode)

| Phase | Effort |
|-------|--------|
| Phase 1 (workshop scope) | 4-8 hours total |
| Phase 1 + optional addendums | 8-12 hours total |
| Phase 2 (if requested) | +4-6 hours |

Compare with Data Product Acceleration: 31-56 hours for full stack.
