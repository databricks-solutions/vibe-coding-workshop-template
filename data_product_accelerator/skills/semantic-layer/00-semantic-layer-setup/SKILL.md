---
name: semantic-layer-setup
description: >
  End-to-end orchestrator for building the Databricks semantic layer including Metric Views,
  Table-Valued Functions (TVFs), Genie Spaces, and Genie optimization. Guides users through
  metric view creation, TVF development, Genie Space setup, API-driven deployment, and
  optimization loops. Orchestrates mandatory dependencies on semantic-layer skills
  (metric-views-patterns, databricks-table-valued-functions, genie-space-patterns,
  genie-space-export-import-api, genie-space-optimization) and common skills
  (databricks-asset-bundles, databricks-expert-agent, databricks-python-imports).
  Use when building the semantic layer end-to-end, creating Metric Views and TVFs for Genie,
  setting up Genie Spaces, or optimizing Genie accuracy.
license: Apache-2.0
metadata:
  author: prashanth subrahmanyam
  version: "1.0.0"
  domain: semantic-layer
  role: orchestrator
  pipeline_stage: 6
  pipeline_stage_name: semantic-layer
  next_stages:
    - observability-setup
  workers:
    - metric-views-patterns
    - databricks-table-valued-functions
    - genie-space-patterns
    - genie-space-export-import-api
    - genie-space-optimization
  common_dependencies:
    - databricks-asset-bundles
    - databricks-expert-agent
    - databricks-python-imports
    - naming-tagging-standards
    - databricks-autonomous-operations
  consumes:
    - plans/manifests/semantic-layer-manifest.yaml
  consumes_fallback: "Gold table inventory (self-discovery from catalog)"
  dependencies:
    - metric-views-patterns
    - databricks-table-valued-functions
    - genie-space-patterns
    - genie-space-export-import-api
    - genie-space-optimization
    - databricks-asset-bundles
    - databricks-expert-agent
    - databricks-python-imports
  last_verified: "2026-02-07"
  volatility: medium
---

# Semantic Layer Setup Orchestrator

End-to-end workflow for building the Databricks semantic layer — Metric Views, Table-Valued Functions, Genie Spaces, and optimization — on top of a completed Gold layer.

**Predecessor:** `gold-layer-setup` skill (Gold tables must exist before using this skill)

**Time Estimate:** 4-6 hours for initial setup, 1-2 hours per additional domain

**What You'll Create:**
1. Metric Views — YAML-based semantic definitions for each Gold table
2. Table-Valued Functions (TVFs) — parameterized SQL functions for Genie
3. Genie Spaces — configured with agent instructions, data assets, benchmark questions
4. Optimization results — accuracy ≥95%, repeatability ≥90%

---

## Decision Tree

| Question | Action |
|----------|--------|
| Building semantic layer end-to-end? | **Use this skill** — it orchestrates everything |
| Only need Metric Views? | Read `semantic-layer/01-metric-views-patterns/SKILL.md` directly |
| Only need TVFs? | Read `semantic-layer/02-databricks-table-valued-functions/SKILL.md` directly |
| Only need Genie Space setup? | Read `semantic-layer/03-genie-space-patterns/SKILL.md` directly |
| Need Genie API automation? | Read `semantic-layer/04-genie-space-export-import-api/SKILL.md` directly |
| Need to optimize Genie accuracy? | Read `semantic-layer/05-genie-space-optimization/SKILL.md` directly |

---

## Mandatory Skill Dependencies

**CRITICAL: Before generating ANY code for the semantic layer, you MUST read and follow the patterns in these common skills. Do NOT generate these patterns from memory.**

| Phase | MUST Read Skill (use Read tool on SKILL.md) | What It Provides |
|-------|---------------------------------------------|------------------|
| All phases | `common/databricks-expert-agent` | Core extraction principle: extract names from source, never hardcode |
| Metric Views | `common/databricks-python-imports` | Pure Python module patterns for helpers |
| Deployment | `common/databricks-asset-bundles` | Job YAML, deployment patterns |
| Troubleshooting | `common/databricks-autonomous-operations` | Deploy → Poll → Diagnose → Fix → Redeploy loop when jobs fail |

### Semantic-Domain Dependencies

| Skill | Requirement | What It Provides |
|-------|-------------|------------------|
| `semantic-layer/01-metric-views-patterns` | **MUST read** at Phase 1 | YAML syntax, validation, joins, window measures |
| `semantic-layer/02-databricks-table-valued-functions` | **MUST read** at Phase 2 | STRING params, Genie compatibility, null safety |
| `semantic-layer/03-genie-space-patterns` | **MUST read** at Phase 3 | 7-section deliverable, agent instructions, benchmark Qs |
| `semantic-layer/04-genie-space-export-import-api` | **Optional** at Phase 4 | Programmatic Genie Space deployment via REST API |
| `semantic-layer/05-genie-space-optimization` | **MUST read** at Phase 5 | Benchmark testing, 6 control levers, optimization loop |

---

## 🔴 Non-Negotiable Defaults

| Default | Value | Applied Where | NEVER Do This Instead |
|---------|-------|---------------|----------------------|
| **Metric View syntax** | `WITH METRICS LANGUAGE YAML` | Every Metric View DDL | ❌ NEVER use non-YAML metric views |
| **TVF parameters** | All `STRING` type | Every TVF signature | ❌ NEVER use DATE, INT, or other non-STRING params (Genie incompatible) |
| **Genie warehouse** | Serverless SQL Warehouse | Every Genie Space | ❌ NEVER use Classic or Pro warehouse |
| **Benchmark questions** | Minimum 10 per Genie Space | Every Genie Space | ❌ NEVER deploy without benchmarks |
| **Column comments** | Required on all Gold tables | Before Genie Space creation | ❌ NEVER create Genie Space without column comments |

---

## Phased Implementation Workflow

### Phase 0: Read Plan (5 minutes)

**Before starting implementation, check for a planning manifest that defines what to build.**

```python
import yaml
from pathlib import Path

manifest_path = Path("plans/manifests/semantic-layer-manifest.yaml")

if manifest_path.exists():
    with open(manifest_path) as f:
        manifest = yaml.safe_load(f)
    
    # Extract implementation checklist from manifest
    domains = manifest.get('domains', {})
    for domain_name, domain_config in domains.items():
        metric_views = domain_config.get('metric_views', [])
        tvfs = domain_config.get('tvfs', [])
        genie_spaces = domain_config.get('genie_spaces', [])
        print(f"Domain {domain_name}: {len(metric_views)} MVs, {len(tvfs)} TVFs, {len(genie_spaces)} Genie Spaces")
    
    # Use manifest as the implementation checklist
    # Each artifact has name, description, source tables, and business questions
else:
    # Fallback: self-discovery from Gold tables
    print("No manifest found — falling back to Gold table self-discovery")
    # Discover Gold tables from catalog and infer metric views from fact tables
```

**If manifest exists:** Use it as the implementation checklist. Every Metric View, TVF, and Genie Space is pre-defined with names, source tables, dimensions, measures, and business questions. Track completion against the manifest's `summary` counts.

**If manifest doesn't exist:** Fall back to self-discovery — inventory Gold tables, infer metric views from fact tables, and derive TVFs from common business queries. This works but may miss artifacts the planning phase would have caught.

---

### Phase 1: Metric Views (1-2 hours)

**MANDATORY: Read each skill below using the Read tool BEFORE writing any code for this phase:**

| # | Skill Path | What It Provides |
|---|------------|------------------|
| 1 | `skills/common/databricks-expert-agent/SKILL.md` | Extract-don't-generate principle |
| 2 | `skills/semantic-layer/01-metric-views-patterns/SKILL.md` | YAML syntax, validation, joins |

**Steps:**
1. Inventory all Gold tables that need Metric Views
2. For each table, create a Metric View YAML file with dimensions and measures
3. Validate column references against actual Gold table schemas
4. Deploy Metric Views using `CREATE VIEW ... WITH METRICS LANGUAGE YAML`
5. Test each Metric View with sample queries

### Phase 2: Table-Valued Functions (1-2 hours)

**MANDATORY: Read each skill below using the Read tool BEFORE writing any code for this phase:**

| # | Skill Path | What It Provides |
|---|------------|------------------|
| 1 | `skills/semantic-layer/02-databricks-table-valued-functions/SKILL.md` | STRING params, null safety, Genie compat |

**Steps:**
1. Identify business questions that require parameterized queries
2. Design TVF signatures (ALL STRING parameters)
3. Implement TVFs with null safety and SCD2 handling
4. Add v3.0 bullet-point comments for Genie discoverability
5. Deploy and validate with test queries

### Phase 3: Genie Space Setup (1 hour)

**MANDATORY: Read each skill below using the Read tool BEFORE writing any code for this phase:**

| # | Skill Path | What It Provides |
|---|------------|------------------|
| 1 | `skills/semantic-layer/03-genie-space-patterns/SKILL.md` | 7-section deliverable, agent instructions |

**Steps:**
1. Verify all Gold tables have column comments (Genie depends on these)
2. Select data assets: Metric Views → TVFs → Gold Tables (priority order)
3. Write General Instructions (≤20 lines)
4. Create benchmark questions with exact SQL answers (minimum 10)
5. Configure Serverless SQL Warehouse
6. Deploy Genie Space

### Phase 4: API Deployment (Optional, 30 min)

**Read only if automating Genie Space deployment:**

| # | Skill Path | What It Provides |
|---|------------|------------------|
| 1 | `skills/semantic-layer/04-genie-space-export-import-api/SKILL.md` | REST API, JSON schema, CI/CD |

**Steps:**
1. Export existing Genie Space as JSON
2. Parameterize with variable substitution
3. Import to target environment via REST API

### Phase 5: Optimization Loop (1-2 hours)

**MANDATORY: Read each skill below using the Read tool BEFORE writing any code for this phase:**

| # | Skill Path | What It Provides |
|---|------------|------------------|
| 1 | `skills/semantic-layer/05-genie-space-optimization/SKILL.md` | Benchmark testing, 6 control levers |

**Steps:**
1. Run benchmark questions via Conversation API
2. Evaluate accuracy and repeatability scores
3. Apply control levers (UC metadata, Metric Views, TVFs, Instructions)
4. Re-test until accuracy ≥95% and repeatability ≥90%
5. Document optimization results

---

## Post-Creation Validation

### Common Skill Compliance
- [ ] Names extracted from Gold YAML (not generated) per `databricks-expert-agent`
- [ ] Asset Bundle YAML follows `databricks-asset-bundles` patterns
- [ ] Python imports follow `databricks-python-imports` patterns

### Semantic Layer Specifics
- [ ] All Metric Views use `WITH METRICS LANGUAGE YAML` syntax
- [ ] All TVFs use STRING parameters only
- [ ] All TVFs have v3.0 bullet-point comments
- [ ] Genie Space has ≤20 line General Instructions
- [ ] Genie Space has ≥10 benchmark questions with exact SQL
- [ ] Genie Space uses Serverless SQL Warehouse
- [ ] All Gold tables have column comments before Genie Space creation
- [ ] Optimization targets met: accuracy ≥95%, repeatability ≥90%

---

## Pipeline Progression

**Previous stage:** `planning/00-project-planning` → Project plan for semantic layer, observability, ML, and GenAI agent phases should be complete

**Next stage:** After completing the semantic layer, proceed to:
- **`monitoring/00-observability-setup`** — Set up Lakehouse Monitoring, AI/BI Dashboards, and SQL Alerts

---

## Related Skills

| Skill | Relationship | Path |
|-------|-------------|------|
| `metric-views-patterns` | **Mandatory** — Metric View YAML | `semantic-layer/01-metric-views-patterns/SKILL.md` |
| `databricks-table-valued-functions` | **Mandatory** — TVF patterns | `semantic-layer/02-databricks-table-valued-functions/SKILL.md` |
| `genie-space-patterns` | **Mandatory** — Genie Space setup | `semantic-layer/03-genie-space-patterns/SKILL.md` |
| `genie-space-export-import-api` | **Optional** — API automation | `semantic-layer/04-genie-space-export-import-api/SKILL.md` |
| `genie-space-optimization` | **Mandatory** — Optimization loop | `semantic-layer/05-genie-space-optimization/SKILL.md` |
| `databricks-expert-agent` | **Mandatory** — Extraction principle | `common/databricks-expert-agent/SKILL.md` |
| `databricks-asset-bundles` | **Mandatory** — Deployment | `common/databricks-asset-bundles/SKILL.md` |
| `databricks-python-imports` | **Mandatory** — Python patterns | `common/databricks-python-imports/SKILL.md` |

## References

- [Metric Views](https://docs.databricks.com/aws/en/metric-views/semantic-metadata)
- [Table-Valued Functions](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-syntax-qry-select-tvf)
- [Genie Spaces](https://docs.databricks.com/aws/en/genie/trusted-assets)
- [Genie Conversation API](https://docs.databricks.com/api/workspace/genie)
