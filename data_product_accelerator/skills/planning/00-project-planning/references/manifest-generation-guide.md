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
| `genai-agents-manifest.yaml` | `genai-agents/00-genai-agents-setup` (stage 9) | Agents, Tools, Eval Datasets |

---

## Generation Workflow

### Step 1: Review Gold Layer Design

Before generating manifests, review the Gold layer outputs:

```
gold_layer_design/
├── yaml/{domain}/*.yaml        # Table schemas (columns, types, PKs, FKs)
├── erd_master.md                # Entity-Relationship Diagram
└── docs/BUSINESS_ONBOARDING_GUIDE.md  # Business context
```

**Extract from Gold YAML:**
- Table names → Determines which monitors, metric views, and features to create
- Column names → Dimensions, measures, feature columns
- Primary keys → Feature table PKs, monitor slicing expressions
- Foreign keys → Join paths for metric views, TVF queries
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
1. A Gold layer table (from `gold_layer_design/yaml/`)
2. A business question or use case (from the plan addendum)

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

- [ ] All table references exist in `gold_layer_design/yaml/`
- [ ] All column references exist in the referenced table's YAML
- [ ] All metric view sources reference valid fact/dim tables
- [ ] All TVF `gold_tables_used` reference valid tables
- [ ] All Genie Space assets reference valid metric views and TVFs from the same manifest
- [ ] All monitor `timestamp_column` values exist in the referenced table
- [ ] All alert queries reference fully qualified table names
- [ ] All model `feature_table` values are defined in the `feature_tables` section
- [ ] Summary counts match actual counts in the manifest
- [ ] Business questions are specific and testable
- [ ] Domain names are consistent across all 4 manifests
