# Volatility Classification

Complete volatility ratings for all skills in the repository. Used by the freshness audit to determine staleness thresholds.

| Volatility | Stale After | Rationale |
|---|---|---|
| **high** | 30 days | APIs actively evolving, breaking changes possible between releases |
| **medium** | 90 days | Features evolve incrementally, core patterns stable |
| **low** | 180 days | Patterns and conventions rarely change |

---

## High Volatility (Stale After 30 Days)

These skills reference APIs or features that change frequently. Prioritize these in audits.

| Skill | Domain | Path | Rationale |
|---|---|---|---|
| `responses-agent-patterns` | genai-agents | `genai-agents/01-responses-agent-patterns` | MLflow ResponsesAgent API evolving rapidly |
| `mlflow-genai-evaluation` | genai-agents | `genai-agents/02-mlflow-genai-evaluation` | MLflow evaluate() API, metric names changing |
| `lakebase-memory-patterns` | genai-agents | `genai-agents/03-lakebase-memory-patterns` | Lakebase is new, API evolving |
| `prompt-registry-patterns` | genai-agents | `genai-agents/04-prompt-registry-patterns` | MLflow prompt API maturing |
| `multi-agent-genie-orchestration` | genai-agents | `genai-agents/05-multi-agent-genie-orchestration` | Multi-agent + Genie APIs evolving |
| `deployment-automation` | genai-agents | `genai-agents/06-deployment-automation` | MLflow deployment APIs changing |
| `production-monitoring` | genai-agents | `genai-agents/07-production-monitoring` | Registered scorers API new |
| `mlflow-genai-foundation` | genai-agents | `genai-agents/08-mlflow-genai-foundation` | MLflow 3.x foundation APIs |
| `genai-agents-setup` | genai-agents | `genai-agents/00-genai-agents-setup` | Orchestrator for all GenAI — depends on volatile workers |
| `metric-views-patterns` | semantic-layer | `semantic-layer/01-metric-views-patterns` | Metric Views spec actively evolving |
| `genie-space-export-import-api` | semantic-layer | `semantic-layer/04-genie-space-export-import-api` | Genie API schema changes |
| `genie-space-optimization` | semantic-layer | `semantic-layer/05-genie-space-optimization` | Conversation API + control levers evolving |
| `ml-pipeline-setup` | ml | `ml/00-ml-pipeline-setup` | MLflow 3.x, LoggedModel, Feature Store APIs |
| `mlflow-mlmodels-patterns` | ml | `ml/mlflow-mlmodels-patterns` | Legacy mirror — MLflow APIs changing |

---

## Medium Volatility (Stale After 90 Days)

These skills reference APIs that evolve incrementally. Core patterns are stable but details change.

| Skill | Domain | Path | Rationale |
|---|---|---|---|
| `semantic-layer-setup` | semantic-layer | `semantic-layer/00-semantic-layer-setup` | Orchestrator — depends on volatile workers but own patterns stable |
| `databricks-table-valued-functions` | semantic-layer | `semantic-layer/02-databricks-table-valued-functions` | TVF SQL syntax stable, Genie integration evolving |
| `genie-space-patterns` | semantic-layer | `semantic-layer/03-genie-space-patterns` | Genie Space config evolving moderately |
| `lakehouse-monitoring-comprehensive` | monitoring | `monitoring/01-lakehouse-monitoring-comprehensive` | Monitor API incrementally updated |
| `databricks-aibi-dashboards` | monitoring | `monitoring/02-databricks-aibi-dashboards` | Dashboard JSON schema evolves with features |
| `sql-alerting-patterns` | monitoring | `monitoring/03-sql-alerting-patterns` | Alert API v2 incrementally updated |
| `observability-setup` | monitoring | `monitoring/00-observability-setup` | Orchestrator — depends on medium workers |
| `anomaly-detection` | monitoring | `monitoring/04-anomaly-detection` | New feature, API stabilizing |
| `dlt-expectations-patterns` | silver | `silver/01-dlt-expectations-patterns` | DLT expectations API incrementally updated |
| `dqx-patterns` | silver | `silver/02-dqx-patterns` | DQX library versioned, periodic releases |
| `silver-layer-setup` | silver | `silver/00-silver-layer-setup` | Orchestrator — DLT/LDP API evolving |
| `databricks-asset-bundles` | common | `common/databricks-asset-bundles` | DAB schema adds new resource types |
| `databricks-autonomous-operations` | common | `common/databricks-autonomous-operations` | SDK version, new API endpoints |
| `unity-catalog-constraints` | common | `common/unity-catalog-constraints` | Constraint syntax occasionally enhanced |
| `schema-management-patterns` | common | `common/schema-management-patterns` | Predictive optimization settings evolve |
| `databricks-table-properties` | common | `common/databricks-table-properties` | New table properties added periodically |
| `databricks-python-imports` | common | `common/databricks-python-imports` | Notebook import patterns stable but environment changes |

---

## Low Volatility (Stale After 180 Days)

These skills contain patterns and conventions that rarely change. Audit semi-annually.

| Skill | Domain | Path | Rationale |
|---|---|---|---|
| `bronze-layer-setup` | bronze | `bronze/00-bronze-layer-setup` | Bronze patterns well-established |
| `faker-data-generation` | bronze | `bronze/01-faker-data-generation` | Faker library stable |
| `gold-layer-design` | gold | `gold/00-gold-layer-design` | Dimensional modeling principles stable |
| `gold-layer-setup` | gold | `gold/01-gold-layer-setup` | Gold implementation patterns stable |
| `yaml-driven-gold-setup` | gold | `gold/02-yaml-driven-gold-setup` | YAML-driven DDL is internal convention |
| `gold-layer-documentation` | gold | `gold/03-gold-layer-documentation` | Documentation conventions stable |
| `gold-layer-merge-patterns` | gold | `gold/04-gold-layer-merge-patterns` | MERGE SQL syntax very stable |
| `gold-delta-merge-deduplication` | gold | `gold/05-gold-delta-merge-deduplication` | Deduplication pattern stable |
| `fact-table-grain-validation` | gold | `gold/06-fact-table-grain-validation` | Grain validation logic is internal |
| `gold-layer-schema-validation` | gold | `gold/07-gold-layer-schema-validation` | Schema validation logic is internal |
| `mermaid-erd-patterns` | gold | `gold/08-mermaid-erd-patterns` | Mermaid syntax very stable |
| `project-planning` | planning | `planning/00-project-planning` | Planning methodology is internal |
| `adhoc-exploration-notebooks` | exploration | `exploration/00-adhoc-exploration-notebooks` | Notebook patterns stable |
| `databricks-expert-agent` | common | `common/databricks-expert-agent` | Core philosophy, not API-dependent |
| `naming-tagging-standards` | common | `common/naming-tagging-standards` | Naming conventions rarely change |
| `create-agent-skill` | admin | `admin/create-agent-skill` | AgentSkills.io spec stable |
| `self-improvement` | admin | `admin/self-improvement` | Internal workflow |
| `documentation-organization` | admin | `admin/documentation-organization` | Internal convention |
| `skill-freshness-audit` | admin | `admin/skill-freshness-audit` | This skill — meta-stable |
| `cursor-rule-to-skill` | admin | `cursor-rule-to-skill` | Internal conversion patterns |
| `skill-navigator` | meta | `skill-navigator` | Internal routing |

---

## Summary Counts

| Volatility | Count | % of Total |
|---|---|---|
| **High** | 14 | 23% |
| **Medium** | 17 | 27% |
| **Low** | 21 | 34% |
| **Total Classified** | 52 | — |

> **Note:** Some legacy/duplicate skills (non-numbered versions in gold/, silver/, ml/, semantic-layer/) are not classified separately — they share volatility with their numbered counterparts.
