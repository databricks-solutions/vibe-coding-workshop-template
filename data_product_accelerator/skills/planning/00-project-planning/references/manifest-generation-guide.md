# Manifest Generation Guide

## Purpose

This guide explains the **plan-as-contract** pattern: how the Planning orchestrator (stage 5) generates structured YAML manifests that downstream orchestrators (stages 6-9) consume as implementation contracts.

---

## Why Manifests?

The "Extract, Don't Generate" principle applies to the planning-to-implementation handoff:

| Without Manifests | With Manifests |
|---|---|
| Downstream orchestrators self-discover Gold tables | Explicit list of artifacts to create |
| Risk of missing TVFs, monitors, or agents | Complete checklist with nothing missed |
| Inconsistent naming across stages | Unified naming from a single plan |
| No traceability from plan to implementation | Clear lineage: plan → manifest → artifact |
| Each orchestrator re-derives business questions | Business questions defined once, reused everywhere |

---

## Manifest Types

| Manifest | Consumed By | Defines |
|---|---|---|
| `semantic-layer-manifest.yaml` | `semantic-layer/00-semantic-layer-setup` (stage 6) | Metric Views, TVFs, Genie Spaces |
| `observability-manifest.yaml` | `monitoring/00-observability-setup` (stage 7) | Monitors, Dashboards, Alerts |
| `ml-manifest.yaml` | `ml/00-ml-pipeline-setup` (stage 8) | Feature Tables, Models, Experiments |
| `genai-agents-manifest.yaml` | `genai-agents/00-course-orchestrator` (stage 9) | Agents, Tools, Eval Datasets |
| `gold-dependency-manifest.yaml` | Planning self-validation + downstream | Gold tables/columns referenced by all addendums (acceleration default; workshop with Gold source) |
| `source-dependency-manifest.yaml` | Planning self-validation + downstream | Source-layer tables/columns referenced by all addendums (workshop with Silver/Bronze/source CSV) |

## Layer-Aware Manifest Header (MANDATORY in all manifests)

Every manifest emitted by Planning carries a `planning_source` block plus readiness markers, populated by Phase 0:

```yaml
planning_mode: acceleration | workshop
planning_source:
  selected_layer: deployed_gold | gold_design | deployed_silver | deployed_bronze | source_csv
  schema: "<catalog>.<schema>"           # null when selected_layer = source_csv
  source_yaml_dir: "gold_layer_design/yaml"          # only when selected_layer = gold_design
  source_csv_paths: ["data_product_accelerator/context/<file>.csv"]   # only for source_csv
  selected_at: "<ISO-8601 UTC>"
implementation_readiness: gold_ready | gold_design_only | workshop_deployable | workshop_draft
requires_gold_promotion: true | false   # advisory only; never gates deployment
```

| `selected_layer` | `implementation_readiness` | `requires_gold_promotion` | Downstream behavior |
|---|---|---|---|
| `deployed_gold` | `gold_ready` | `false` | Full production deploy path |
| `gold_design` | `gold_design_only` | `false` | Validate against `gold_layer_design/yaml/`; warn-only on live mismatch; deploy once Gold is provisioned |
| `deployed_silver` | `workshop_deployable` | `false` (advisory: recommended for production) | Workshop deployment runs directly against `silver_schema`; Genie-quality advisory printed |
| `deployed_bronze` | `workshop_deployable` | `false` (advisory: recommended for production) | Workshop deployment runs directly against `bronze_schema`; stronger Genie-quality advisory |
| `source_csv` | `workshop_draft` | `false` (advisory) | Planning contract only; downstream stops because no live tables exist |

### Strict vs Advisory Validation

- **Acceleration + `deployed_gold`** — fail-loud on any live-catalog gap (existing behavior).
- **Acceleration + `gold_design`** — only allowed if explicitly accepted; emit `gold-gap-remediation.md` as a warning.
- **Workshop + `deployed_gold`** — fail-loud on any gap (parity with acceleration; Gold is Gold).
- **Workshop + `deployed_silver` / `deployed_bronze`** — emit `source-gap-remediation.md` as a warning if the live catalog is missing manifest-declared tables. The semantic-layer orchestrator deploys Metric Views, TVFs, and Genie Spaces directly against the selected layer with a quality advisory.
- **Workshop + `source_csv`** — emit `source-gap-remediation.md` and continue planning, but the semantic-layer orchestrator will stop because there are no live tables to deploy against.

---

## Generation Workflow

### Step 1: Review Planning Source (mode-aware)

Phase 0 in the main SKILL.md selects the planning source. Before generating manifests, review the artifacts produced by that source:

| Selected layer | Inputs to review |
|---|---|
| `deployed_gold` | `gold_layer_design/yaml/`, `gold_layer_design/erd_master.md`, `gold_layer_design/docs/BUSINESS_ONBOARDING_GUIDE.md`, plus the live `<catalog>.<gold_schema>` |
| `gold_design` | `gold_layer_design/yaml/` and ERD only (Gold not yet deployed) |
| `deployed_silver` | Live `<catalog>.<silver_schema>` table list and column metadata via `information_schema.columns` |
| `deployed_bronze` | Live `<catalog>.<bronze_schema>` table list and column metadata |
| `source_csv` | `data_product_accelerator/context/*.csv` schema definitions |

**Extract from the selected source:**
- Table names → Determines which monitors, metric views, and features to create
- Column names → Dimensions, measures, feature columns
- Primary keys → Feature table PKs, monitor slicing expressions
- Foreign keys (or inferred FKs in Silver/Bronze) → Join paths for metric views, TVF queries
- Domain groupings → Agent domains, dashboard organization

### Step 2: Generate Human-Readable Plan Documents

Use the existing plan addendum templates:

```
plans/
├── phase1-addendum-1.1-ml-models.md
├── phase1-addendum-1.2-tvfs.md
├── phase1-addendum-1.3-metric-views.md
├── phase1-addendum-1.4-lakehouse-monitoring.md
├── phase1-addendum-1.5-aibi-dashboards.md
├── phase1-addendum-1.6-genie-spaces.md
├── phase1-addendum-1.7-alerting.md
└── phase2-agent-framework.md
```

These markdown files contain the detailed reasoning, business justification, and design decisions. They are human-readable documentation.

### Step 3: Generate Machine-Readable Manifests

From the plan documents, generate structured YAML manifests:

```
plans/manifests/
├── semantic-layer-manifest.yaml     # TVFs + Metric Views + Genie Spaces
├── observability-manifest.yaml      # Monitors + Dashboards + Alerts
├── ml-manifest.yaml                 # Feature Tables + Models + Experiments
└── genai-agents-manifest.yaml       # Agents + Tools + Eval Datasets
```

**Key principle:** Every artifact in a manifest MUST trace back to:
1. A planning-source table (Gold table from `gold_layer_design/yaml/` or live Gold; Silver/Bronze table from the live catalog; or a source CSV entity — matching `planning_source.selected_layer`)
2. A business question or use case (from the plan addendum)

**Use case cross-referencing:** For each artifact entry in a manifest, include a `use_case_refs` list containing the UC# identifiers from `plans/use-case-catalog.md` that the artifact implements. This creates a reverse link from manifests back to the use case catalog, enabling traceability from implementation contracts all the way to business problems.

### Step 4: Validate Manifests

Before handing off to downstream orchestrators:

```python
import yaml
from pathlib import Path

def validate_manifest(manifest_path: str, gold_yaml_dir: str):
    """Validate all table references in manifest exist in Gold YAML."""
    with open(manifest_path) as f:
        manifest = yaml.safe_load(f)
    
    # Collect all Gold table names from YAML
    gold_tables = set()
    for yaml_file in Path(gold_yaml_dir).rglob("*.yaml"):
        with open(yaml_file) as f:
            schema = yaml.safe_load(f)
            gold_tables.add(schema.get('table_name', yaml_file.stem))
    
    # Validate all references
    errors = []
    # ... check each table reference in manifest against gold_tables
    
    return errors
```

---

## Unified Genie Space Handling

Most projects map 1 Genie Space per domain under `domains[].genie_spaces[]`. Some projects (workshop mode, or projects with ≤ 15 total queryable assets) consolidate into a single **unified** Genie Space spanning multiple domains.

For the unified case, use the documented `unified_genie_space` key (singular) at the top level of `semantic-layer-manifest.yaml`:

```yaml
unified_genie_space:
  name: "{Project} Intelligence"
  domains_covered: ["{domain_1}", "{domain_2}"]
  assets:
    metric_views: [...]
    tvfs: [...]
    tables: [...]
  total_asset_count: "{N}"   # Must be ≤ 25
```

**Downstream precedence rule:** The semantic-layer orchestrator MUST check for `unified_genie_space` FIRST.

- If `unified_genie_space` is present: create that single space and SKIP per-domain `genie_spaces[]` entries.
- If `unified_genie_space` is absent: iterate `domains[].genie_spaces[]` normally.

**Anti-pattern — schema deviation:** Do NOT invent alternative keys (e.g., `unified_genie_spaces` plural, `cross_domain_genie`, `shared_space`). Downstream consumers only recognize `unified_genie_space` (singular). If you find the template truly insufficient for your case, extend the template with a documented new key and update this guide BEFORE emitting the manifest — never ship ad-hoc schema.

## Consumption Pattern

### How Downstream Orchestrators Use Manifests

Each downstream orchestrator follows this Phase 0 pattern:

```python
# Phase 0: Read Plan (MANDATORY first step)
manifest_path = "plans/manifests/{domain}-manifest.yaml"

if Path(manifest_path).exists():
    with open(manifest_path) as f:
        manifest = yaml.safe_load(f)
    
    # Use manifest as implementation checklist
    for artifact in manifest['domains'][domain]['metric_views']:
        create_metric_view(artifact)
    
    # Track progress
    completed = []
    for item in manifest_items:
        implement(item)
        completed.append(item['name'])
    
    # Validate completeness
    assert len(completed) == manifest['summary']['total_metric_views']
else:
    # Fallback: self-discovery from Gold tables
    gold_tables = discover_gold_tables(catalog, gold_schema)
    # ... derive what to create from table inspection
```

### Fallback Strategy

If manifests don't exist (e.g., user skipped Planning or is working on a single layer):

| Orchestrator | Fallback Strategy |
|---|---|
| Semantic Layer | Discover Gold tables, infer metric views from fact tables, generate TVFs from common queries |
| Observability | Discover Gold tables, create one monitor per table, generate standard dashboards |
| ML | Discover Gold fact tables, infer feature columns, create one model per domain |
| GenAI Agents | Discover Genie Spaces, create one agent per domain |

The fallback is always inferior to manifests (may miss edge cases, naming inconsistencies, etc.), but it ensures the pipeline doesn't break if Planning is skipped.

---

## Metadata Flow

```
Gold YAML schemas ──────────────────────────────────────┐
                                                         │
Plan addendum markdown ──► Planning Orchestrator ──► Manifests ──► Downstream Orchestrators
                              (stage 5)             (YAML)           (stages 6-9)
                                │                      │
                                ▼                      ▼
                          emits: [manifests]     consumes: [manifests]
                          reads: [gold_yaml]     consumes_fallback: "self-discovery"
```

### SKILL.md Metadata Fields

| Field | Used By | Purpose |
|---|---|---|
| `emits` | Planning orchestrator | Lists manifest files it generates |
| `reads` | Planning orchestrator | Lists Gold YAML directories it reads |
| `consumes` | Downstream orchestrators | Lists manifest files it expects |
| `consumes_fallback` | Downstream orchestrators | Strategy if manifest missing |

---

## Templates

Manifest templates are located at:

```
assets/templates/manifests/
├── semantic-layer-manifest.yaml
├── observability-manifest.yaml
├── ml-manifest.yaml
└── genai-agents-manifest.yaml
```

Copy a template, replace placeholders (`{domain}`, `{metric}`, `{entity}`, etc.), and save to `plans/manifests/`.

---

## Validation Checklist

Before handing off manifests to downstream orchestrators:

- [ ] Every manifest carries `planning_mode`, `planning_source`, `implementation_readiness`, `requires_gold_promotion` (populated by Phase 0)
- [ ] All table references exist in the planning source (`gold_layer_design/yaml/` for Gold sources; live `information_schema.columns` for deployed Silver/Bronze; the source CSV for `source_csv`)
- [ ] All column references exist in the referenced table within the planning source
- [ ] All metric view sources reference valid fact/dim tables (Gold sources) or the closest Silver/Bronze equivalent (workshop deployments on `deployed_silver` / `deployed_bronze`)
- [ ] All TVF `gold_tables_used` (or `source_assets_used` for workshop deployments on Silver/Bronze) reference valid tables
- [ ] All Genie Space assets reference valid metric views and TVFs from the same manifest. **Production trusted assets are Gold-only**. Workshop Genie Spaces built on Silver/Bronze are deployable but carry a quality caveat: raw layers typically lack curated COMMENTs and dimensional joins, so NL accuracy will be lower than on Gold. Promote to Gold for production.
- [ ] All monitor `timestamp_column` values exist in the referenced table
- [ ] All alert queries reference fully qualified table names
- [ ] All model `feature_table` values are defined in the `feature_tables` section
- [ ] Summary counts match actual counts in the manifest
- [ ] Business questions are specific and testable
- [ ] Domain names are consistent across all manifests (semantic, observability, ml, genai-agents, source/gold-dependency)
- [ ] All artifacts have `use_case_refs` linking back to the use case catalog
- [ ] Every UC# referenced in manifests exists in `plans/use-case-catalog.md`
