# {Project Name} Project Plans

**Complete phased implementation plan for {Project Description}**

**Planning Mode:** {acceleration | workshop}
**Selected Planning Source:** `{deployed_gold | gold_design | deployed_silver | deployed_bronze | source_csv}` (set by Phase 0)
**Implementation Readiness:** `{gold_ready | gold_design_only | workshop_deployable | workshop_draft}`
**Requires Gold Promotion:** `{true | false}`

---

## Plan Index

### Prerequisites (mode-aware)

| Layer | Document | Status | Description |
|-------|----------|--------|-------------|
| Bronze | [Prerequisites](./prerequisites.md) | {✅ Complete / Planned only / N/A} | Raw data ingestion ({n} tables) |
| Silver | [Prerequisites](./prerequisites.md) | {✅ Complete / Planned only / N/A} | DLT streaming with DQ |
| Gold | [Prerequisites](./prerequisites.md) | {✅ Complete / 📐 Designed only / Planned only / N/A} | Dimensional model ({n} tables) |

### Project Phases

| Phase | Document | Status | Description |
|-------|----------|--------|-------------|
| UC Catalog | [Use Case Catalog](./use-case-catalog.md) | {status} | Consolidated use case definitions with business questions |
| 1 | [Phase 1: Use Cases](./phase1-use-cases.md) | {status} | Analytics artifacts |
| 2 | [Phase 2: Agent Framework](./phase2-agent-framework.md) | {status} | AI agents |
| 3 | [Phase 3: Frontend App](./phase3-frontend-app.md) | {status} | User interface |

### Phase 1 Addendums

| # | Addendum | Status | Artifacts |
|---|----------|--------|-----------|
| 1.1 | [ML Models](./phase1-addendum-1.1-ml-models.md) | {status} | {count} |
| 1.2 | [TVFs](./phase1-addendum-1.2-tvfs.md) | {status} | {count} |
| 1.3 | [Metric Views](./phase1-addendum-1.3-metric-views.md) | {status} | {count} |
| 1.4 | [Lakehouse Monitoring](./phase1-addendum-1.4-lakehouse-monitoring.md) | {status} | {count} |
| 1.5 | [AI/BI Dashboards](./phase1-addendum-1.5-aibi-dashboards.md) | {status} | {count} |
| 1.6 | [Genie Spaces](./phase1-addendum-1.6-genie-spaces.md) | {status} | {count} |
| 1.7 | [Alerting](./phase1-addendum-1.7-alerting.md) | {status} | {count} |

---

## Agent Domain Framework

| Domain | Icon | Focus Area | Key Planning Assets |
|--------|------|------------|---------------------|
| {Domain 1} | {emoji} | {focus} | {tables from selected planning source} |

---

## Project Scope Summary

### Prerequisites (Data Layers, mode-aware)

| Layer | Schema | Tables | Status |
|-------|--------|--------|--------|
| Bronze | `{schema}` | {n} | {✅ Complete / Planned only / N/A} |
| Silver | `{schema}` | {n} | {✅ Complete / Planned only / N/A} |
| Gold | `{schema}` | {n} | {✅ Complete / 📐 Designed only / Planned only / N/A} |
| **Selected planning source** | — | — | `{planning_source.selected_layer}` |

### Phase 1 (Use Cases)

| Artifact Type | Count |
|---------------|-------|
| TVFs | {n}+ |
| Metric Views | {n} |
| Dashboards | {n} |
| Monitors | {n} |
| Alerts | {n} |
| ML Models | {n} |
| Genie Spaces | {n} |

---

## Success Metrics

| Phase | Criteria | Target |
|-------|----------|--------|
| Use Cases | TVFs deployed | {n}+ |
| Use Cases | Dashboards created | {n}+ |
| Agents | Agents responding | {n}+ |
| Frontend | App deployed | 1 |
