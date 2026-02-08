---
name: observability-setup
description: >
  End-to-end orchestrator for setting up Databricks observability including Lakehouse Monitoring,
  AI/BI Dashboards, and SQL Alerts. Guides users through monitor creation for Gold tables,
  dashboard design with monitoring widgets, and config-driven alerting. Orchestrates mandatory
  dependencies on monitoring skills (lakehouse-monitoring-comprehensive, databricks-aibi-dashboards,
  sql-alerting-patterns) and common skills (databricks-asset-bundles, databricks-expert-agent,
  databricks-python-imports).
  Use when setting up observability end-to-end, creating Lakehouse Monitors, building dashboards,
  or configuring SQL alerts.
license: Apache-2.0
metadata:
  author: prashanth subrahmanyam
  version: "1.0.0"
  domain: monitoring
  role: orchestrator
  pipeline_stage: 7
  pipeline_stage_name: observability
  next_stages:
    - ml-pipeline-setup
  workers:
    - lakehouse-monitoring-comprehensive
    - databricks-aibi-dashboards
    - sql-alerting-patterns
  common_dependencies:
    - databricks-asset-bundles
    - databricks-expert-agent
    - databricks-python-imports
    - naming-tagging-standards
    - databricks-autonomous-operations
  consumes:
    - plans/manifests/observability-manifest.yaml
  consumes_fallback: "Gold table inventory (self-discovery from catalog)"
  dependencies:
    - lakehouse-monitoring-comprehensive
    - databricks-aibi-dashboards
    - sql-alerting-patterns
    - databricks-asset-bundles
    - databricks-expert-agent
    - databricks-python-imports
  last_verified: "2026-02-07"
  volatility: medium
---

# Observability Setup Orchestrator

End-to-end workflow for setting up Databricks observability — Lakehouse Monitoring, AI/BI Dashboards, and SQL Alerts — on top of a completed Gold layer and semantic layer.

**Predecessor:** `semantic-layer-setup` skill (Semantic layer should be complete, but Gold tables are the minimum requirement)

**Time Estimate:** 3-5 hours for initial setup, 30 min per additional table/dashboard

**What You'll Create:**
1. Lakehouse Monitors — data quality, drift, and custom business KPIs for Gold tables
2. AI/BI Dashboards — Lakeview dashboards with monitoring widgets and business metrics
3. SQL Alerts — config-driven alerting with severity-based routing

---

## Decision Tree

| Question | Action |
|----------|--------|
| Setting up observability end-to-end? | **Use this skill** — it orchestrates everything |
| Only need Lakehouse Monitoring? | Read `monitoring/01-lakehouse-monitoring-comprehensive/SKILL.md` directly |
| Only need AI/BI Dashboards? | Read `monitoring/02-databricks-aibi-dashboards/SKILL.md` directly |
| Only need SQL Alerts? | Read `monitoring/03-sql-alerting-patterns/SKILL.md` directly |

---

## Mandatory Skill Dependencies

**CRITICAL: Before generating ANY code for observability, you MUST read and follow the patterns in these common skills. Do NOT generate these patterns from memory.**

| Phase | MUST Read Skill (use Read tool on SKILL.md) | What It Provides |
|-------|---------------------------------------------|------------------|
| All phases | `common/databricks-expert-agent` | Core extraction principle: extract names from source, never hardcode |
| Monitor scripts | `common/databricks-python-imports` | Pure Python module patterns for helpers |
| Job deployment | `common/databricks-asset-bundles` | Job YAML, deployment patterns |
| Troubleshooting | `common/databricks-autonomous-operations` | Deploy → Poll → Diagnose → Fix → Redeploy loop when jobs fail |

### Monitoring-Domain Dependencies

| Skill | Requirement | What It Provides |
|-------|-------------|------------------|
| `monitoring/01-lakehouse-monitoring-comprehensive` | **MUST read** at Phase 1 | Monitor setup, custom metrics, graceful degradation |
| `monitoring/02-databricks-aibi-dashboards` | **MUST read** at Phase 2 | Dashboard JSON, widget patterns, deployment |
| `monitoring/03-sql-alerting-patterns` | **MUST read** at Phase 3 | Config-driven alerts, SDK deployment, severity routing |

---

## 🔴 Non-Negotiable Defaults

| Default | Value | Applied Where | NEVER Do This Instead |
|---------|-------|---------------|----------------------|
| **Monitor type** | `MonitorTimeSeries` or `MonitorSnapshot` | Every Lakehouse Monitor | ❌ NEVER skip monitor type selection |
| **Custom metrics** | `input_columns=[":table"]` for table-level KPIs | Every custom business metric | ❌ NEVER use column-level when table-level is needed |
| **Dashboard deployment** | Lakeview JSON with `dataset_catalog`/`dataset_schema` | Every dashboard | ❌ NEVER hardcode catalog/schema in dashboard queries |
| **Alert queries** | Fully qualified table names (no parameters) | Every SQL alert query | ❌ NEVER use parameterized table names in alerts |
| **Serverless** | `environments:` block with `environment_key` | Every monitoring job | ❌ NEVER define `job_clusters:` |

---

## Phased Implementation Workflow

### Phase 0: Read Plan (5 minutes)

**Before starting implementation, check for a planning manifest that defines what to build.**

```python
import yaml
from pathlib import Path

manifest_path = Path("plans/manifests/observability-manifest.yaml")

if manifest_path.exists():
    with open(manifest_path) as f:
        manifest = yaml.safe_load(f)
    
    # Extract implementation checklist from manifest
    monitors = manifest.get('lakehouse_monitors', [])
    dashboards = manifest.get('dashboards', [])
    alerts = manifest.get('alerts', [])
    print(f"Plan: {len(monitors)} monitors, {len(dashboards)} dashboards, {len(alerts)} alerts")
    
    # Each monitor has: table_name, monitor_type, custom_metrics, slicing_exprs
    # Each dashboard has: name, pages, widgets
    # Each alert has: alert_id, severity, query, threshold, schedule
else:
    # Fallback: self-discovery from Gold tables
    print("No manifest found — falling back to Gold table self-discovery")
    # Discover Gold tables from catalog, create one monitor per table
```

**If manifest exists:** Use it as the implementation checklist. Every monitor, dashboard, and alert is pre-defined with configuration details. Track completion against the manifest's `summary` counts.

**If manifest doesn't exist:** Fall back to self-discovery — inventory Gold tables, create one monitor per table (TimeSeries for facts, Snapshot for dimensions), and generate standard dashboards and alerts. This works but may miss custom business KPIs the planning phase would have defined.

---

### Phase 1: Lakehouse Monitoring (1-2 hours)

**MANDATORY: Read each skill below using the Read tool BEFORE writing any code for this phase:**

| # | Skill Path | What It Provides |
|---|------------|------------------|
| 1 | `skills/common/databricks-expert-agent/SKILL.md` | Extract-don't-generate principle |
| 2 | `skills/monitoring/01-lakehouse-monitoring-comprehensive/SKILL.md` | Monitor setup, custom metrics |

**Steps:**
1. Inventory Gold tables that need monitoring (fact tables are highest priority)
2. Choose monitor type per table (TimeSeries for facts, Snapshot for dimensions)
3. Define custom business metrics using `input_columns=[":table"]` for table-level KPIs
4. Create monitor setup script with graceful degradation (delete-then-create pattern)
5. Deploy monitors and verify metric tables are populated
6. Document monitor configuration in Genie Space instructions (if applicable)

### Phase 2: AI/BI Dashboards (1-2 hours)

**MANDATORY: Read each skill below using the Read tool BEFORE writing any code for this phase:**

| # | Skill Path | What It Provides |
|---|------------|------------------|
| 1 | `skills/monitoring/02-databricks-aibi-dashboards/SKILL.md` | Dashboard JSON, widget patterns |

**Steps:**
1. Design dashboard layout: monitoring overview + business metrics sections
2. Create queries using monitoring profile/drift tables
3. Build widget configurations with proper number formatting
4. Set `dataset_catalog` and `dataset_schema` for environment portability
5. Deploy dashboard via Asset Bundle or API
6. Validate all widgets render correctly

### Phase 3: SQL Alerts (1 hour)

**MANDATORY: Read each skill below using the Read tool BEFORE writing any code for this phase:**

| # | Skill Path | What It Provides |
|---|------------|------------------|
| 1 | `skills/monitoring/03-sql-alerting-patterns/SKILL.md` | Config-driven alerts, SDK deployment |
| 2 | `skills/common/databricks-asset-bundles/SKILL.md` | Job YAML for alert deployment |

**Steps:**
1. Create alert configuration table (Delta table-based, severity-driven)
2. Define alert rules: threshold, percentage change, anomaly detection
3. Deploy alerts via Databricks SDK (V2 dict-based or typed classes)
4. Configure notification destinations per severity level
5. Set up Quartz cron schedules for alert evaluation
6. Validate alerts fire correctly with test data

---

## Post-Creation Validation

### Common Skill Compliance
- [ ] Names extracted from Gold YAML (not generated) per `databricks-expert-agent`
- [ ] Asset Bundle YAML follows `databricks-asset-bundles` patterns
- [ ] Python imports follow `databricks-python-imports` patterns

### Observability Specifics
- [ ] Lakehouse Monitors created for all critical Gold tables
- [ ] Custom business metrics use `input_columns=[":table"]` syntax
- [ ] Monitor setup uses graceful degradation (delete-then-create)
- [ ] Dashboard uses `dataset_catalog`/`dataset_schema` for portability
- [ ] Dashboard widgets align with query columns
- [ ] Alert queries use fully qualified table names (no parameters)
- [ ] Alert severity routing configured (critical → PagerDuty, warning → email)
- [ ] All monitoring jobs use serverless compute

---

## Pipeline Progression

**Previous stage:** `semantic-layer-setup` → Metric Views, TVFs, and Genie Spaces should exist

**Next stage:** After completing observability, proceed to:
- **`ml/00-ml-pipeline-setup`** — Set up ML models, experiments, and batch inference

---

## Related Skills

| Skill | Relationship | Path |
|-------|-------------|------|
| `lakehouse-monitoring-comprehensive` | **Mandatory** — Monitor setup | `monitoring/01-lakehouse-monitoring-comprehensive/SKILL.md` |
| `databricks-aibi-dashboards` | **Mandatory** — Dashboard patterns | `monitoring/02-databricks-aibi-dashboards/SKILL.md` |
| `sql-alerting-patterns` | **Mandatory** — Alert framework | `monitoring/03-sql-alerting-patterns/SKILL.md` |
| `databricks-expert-agent` | **Mandatory** — Extraction principle | `common/databricks-expert-agent/SKILL.md` |
| `databricks-asset-bundles` | **Mandatory** — Deployment | `common/databricks-asset-bundles/SKILL.md` |
| `databricks-python-imports` | **Mandatory** — Python patterns | `common/databricks-python-imports/SKILL.md` |

## References

- [Lakehouse Monitoring](https://learn.microsoft.com/en-us/azure/databricks/lakehouse-monitoring/create-monitor-api)
- [AI/BI Dashboards](https://docs.databricks.com/aws/en/dashboards/)
- [SQL Alerts](https://docs.databricks.com/api/workspace/alerts)
