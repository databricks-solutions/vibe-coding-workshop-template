# Canonical Phase 1 Addendum Numbering

> Single source of truth for Phase 1 use-case plan addendum filenames, numbers, and downstream consumers. Every skill, prompt, template, and manifest that references an addendum MUST use the filenames in the "Canonical filename" column verbatim. Any drift (e.g. legacy `1.1-dashboards.md`) is a bug and should be corrected to match this table.

## Why this file exists

Plan addendums are the hand-off contract between the Planning skill and every downstream orchestrator (semantic-layer, observability, ML, GenAI agents). Orchestrators reference addendums by exact path (e.g. `plans/phase1-addendum-1.5-aibi-dashboards.md`). If a prompt, template, or manifest uses a stale or incorrect number, the orchestrator quietly skips the file, silently producing an empty phase.

This table is the canonical mapping. When you see a mismatch anywhere in the accelerator, fix the mismatch — do NOT introduce a new numbering scheme.

## Canonical table

| # | Canonical filename | Template source | Consumed by (manifests) | Consumed by (skills/prompts) |
|---|---|---|---|---|
| **1.1** | `plans/phase1-addendum-1.1-ml-models.md` | `planning/00-project-planning/assets/templates/phase1-ml-models-template.md` (TBD) | `ml-manifest.yaml` | `ml/00-ml-pipeline-setup` |
| **1.2** | `plans/phase1-addendum-1.2-tvfs.md` | `planning/00-project-planning/assets/templates/phase1-tvfs-template.md` | `semantic-layer-manifest.yaml` | `semantic-layer/02-databricks-table-valued-functions` |
| **1.3** | `plans/phase1-addendum-1.3-metric-views.md` | `planning/00-project-planning/assets/templates/phase1-metric-views-template.md` | `semantic-layer-manifest.yaml` | `semantic-layer/01-metric-views-patterns` |
| **1.4** | `plans/phase1-addendum-1.4-lakehouse-monitoring.md` | `planning/00-project-planning/assets/templates/phase1-monitoring-template.md` | `observability-manifest.yaml` | `monitoring/01-lakehouse-monitoring-comprehensive` |
| **1.5** | `plans/phase1-addendum-1.5-aibi-dashboards.md` | `planning/00-project-planning/assets/templates/phase1-dashboards-template.md` | `observability-manifest.yaml` | `monitoring/02-databricks-aibi-dashboards`, prompt `sections/14-aibi_dashboard.md` |
| **1.6** | `plans/phase1-addendum-1.6-genie-spaces.md` | `planning/00-project-planning/assets/templates/phase1-genie-spaces-template.md` | `semantic-layer-manifest.yaml` | `semantic-layer/03-genie-space-patterns`, `semantic-layer/04-genie-space-export-import-api`, prompt `sections/15-genie_space.md` |
| **1.7** | `plans/phase1-addendum-1.7-alerting.md` | `planning/00-project-planning/assets/templates/phase1-alerting-template.md` | `observability-manifest.yaml` | `monitoring/03-sql-alerts-patterns` |
| **1.8** | `plans/phase1-addendum-1.8-genai-agents.md` | `planning/00-project-planning/assets/templates/phase2-agent-framework-template.md` | `genai-agents-manifest.yaml` | `genai-agents/00-genai-agents-setup` |

Plus the always-present top-level plan files:

| File | Template source | Purpose |
|---|---|---|
| `plans/phase1-use-cases.md` | `phase1-use-cases-template.md` | Master use-case catalog referenced by every addendum |
| `plans/manifests/gold-dependency-manifest.yaml` | (emitted by Planning skill) | Gold table/column references used by every addendum |
| `plans/gold-gap-remediation.md` | (emitted on live-catalog intersection failure) | Lists missing Gold tables/columns — halts downstream orchestrators |
| `plans/deploy-checkpoint.md` | (emitted by Asset Bundles skill) | Concrete resolved job/warehouse/asset names for the current target |

## Anti-patterns (DO NOT use these filenames)

| Legacy / wrong filename | Replace with |
|---|---|
| `phase1-addendum-1.1-dashboards.md` | `phase1-addendum-1.5-aibi-dashboards.md` |
| `phase1-addendum-dashboards.md` | `phase1-addendum-1.5-aibi-dashboards.md` |
| `phase1-dashboards.md` | `phase1-addendum-1.5-aibi-dashboards.md` |
| `phase1-addendum-tvfs.md` (missing number) | `phase1-addendum-1.2-tvfs.md` |
| `phase1-addendum-genie.md` (abbreviated) | `phase1-addendum-1.6-genie-spaces.md` |
| `phase1-addendum-monitors.md` (abbreviated) | `phase1-addendum-1.4-lakehouse-monitoring.md` |

## Enforcement

When adding a new template, manifest, skill cross-reference, or prompt:

1. Check the canonical table above for the addendum's correct number and filename.
2. Use the filename verbatim — never shorten, re-number, or paraphrase.
3. If a new addendum is needed (e.g. a new subsystem), extend the table here FIRST, then use the new filename everywhere else.

A CI-style audit grep for stale filenames:

```bash
# Should return NO matches (run from repo root):
rg -n "phase1-addendum-1\.1-dashboards|phase1-addendum-dashboards\.md|phase1-dashboards\.md" \
    apps_lakebase/ data_product_accelerator/ agentic-framework/
```
