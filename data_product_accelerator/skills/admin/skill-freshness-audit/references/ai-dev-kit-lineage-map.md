# AI-Dev-Kit Lineage Map

Maps every skill in this repository to its upstream source(s) in [`databricks-solutions/ai-dev-kit`](https://github.com/databricks-solutions/ai-dev-kit). Use this map during freshness audits and upstream sync checks.

**Upstream repo:** `databricks-solutions/ai-dev-kit` (branch: `main`)
**Raw URL base:** `https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/`
**Last full sync:** 2026-02-19

---

## Relationship Types

| Type | Meaning | Sync Priority |
|---|---|---|
| `derived` | Skill content directly draws from upstream source | High — upstream changes likely require skill updates |
| `extended` | Skill extends upstream with significant additional patterns | Medium — check upstream for new base patterns |
| `inspired` | Upstream was conceptual starting point, heavily customized | Low — check upstream for major direction changes |
| `reference` | Skill references upstream for accuracy, content is original | Low — check for API/pattern accuracy only |
| _(none)_ | `upstream_sources: []` — internal methodology, no upstream | None — skip during upstream audits |

---

## Direct Mappings (derived / extended)

These skills have content that directly draws from or extends AI-Dev-Kit. Upstream changes are most likely to require updates here.

| Our Skill | AI-Dev-Kit Path(s) | Relationship | Raw URL for Audit |
|---|---|---|---|
| `genai-agents/00-genai-agents-setup` | `databricks-skills/databricks-agent-bricks/SKILL.md` | extended | [Fetch](https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-skills/databricks-agent-bricks/SKILL.md) |
| `genai-agents/01-responses-agent-patterns` | `databricks-skills/databricks-agent-bricks/SKILL.md` | extended | [Fetch](https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-skills/databricks-agent-bricks/SKILL.md) |
| `genai-agents/05-multi-agent-genie-orchestration` | `databricks-skills/databricks-agent-bricks/SKILL.md` | extended | [Fetch](https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-skills/databricks-agent-bricks/SKILL.md) |
| `genai-agents/06-deployment-automation` | `databricks-skills/databricks-model-serving/SKILL.md` | extended | [Fetch](https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-skills/databricks-model-serving/SKILL.md) |
| `genai-agents/08-mlflow-genai-foundation` | `databricks-skills/databricks-agent-bricks/SKILL.md` | extended | [Fetch](https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-skills/databricks-agent-bricks/SKILL.md) |
| `genai-agents/02-mlflow-genai-evaluation` | `databricks-skills/databricks-mlflow-evaluation/SKILL.md` | extended | [Fetch](https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-skills/databricks-mlflow-evaluation/SKILL.md) |
| `genai-agents/03-lakebase-memory-patterns` | `databricks-skills/databricks-lakebase-provisioned/SKILL.md` | extended | [Fetch](https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-skills/databricks-lakebase-provisioned/SKILL.md) |
| `monitoring/02-databricks-aibi-dashboards` | `databricks-skills/databricks-aibi-dashboards/SKILL.md` | extended | [Fetch](https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-skills/databricks-aibi-dashboards/SKILL.md) |
| `silver/00-silver-layer-setup` | `databricks-skills/databricks-spark-declarative-pipelines/SKILL.md` | extended | [Fetch](https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-skills/databricks-spark-declarative-pipelines/SKILL.md) |
| `silver/01-dlt-expectations-patterns` | `databricks-skills/databricks-spark-declarative-pipelines/SKILL.md` | extended | [Fetch](https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-skills/databricks-spark-declarative-pipelines/SKILL.md) |
| `common/databricks-asset-bundles` | `databricks-skills/databricks-asset-bundles/SKILL.md` | extended | [Fetch](https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-skills/databricks-asset-bundles/SKILL.md) |
| `common/databricks-autonomous-operations` | `databricks-skills/databricks-python-sdk/SKILL.md`, `databricks-skills/databricks-jobs/SKILL.md` | extended | [SDK](https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-skills/databricks-python-sdk/SKILL.md), [Jobs](https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-skills/databricks-jobs/SKILL.md) |
| `common/unity-catalog-constraints` | `databricks-skills/databricks-unity-catalog/SKILL.md` | derived | [Fetch](https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-skills/databricks-unity-catalog/SKILL.md) |
| `common/schema-management-patterns` | `databricks-skills/databricks-unity-catalog/SKILL.md` | derived | [Fetch](https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-skills/databricks-unity-catalog/SKILL.md) |
| `common/databricks-table-properties` | `databricks-skills/databricks-unity-catalog/SKILL.md` | derived | [Fetch](https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-skills/databricks-unity-catalog/SKILL.md) |
| `semantic-layer/01-metric-views-patterns` | `databricks-skills/databricks-metric-views/SKILL.md` | extended | [Fetch](https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-skills/databricks-metric-views/SKILL.md) |
| `semantic-layer/03-genie-space-patterns` | `databricks-skills/databricks-genie/SKILL.md` | extended | [Fetch](https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-skills/databricks-genie/SKILL.md) |
| `semantic-layer/04-genie-space-export-import-api` | `databricks-skills/databricks-genie/SKILL.md` | extended | [Fetch](https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-skills/databricks-genie/SKILL.md) |
| `semantic-layer/05-genie-optimization-orchestrator` | `databricks-skills/databricks-genie/SKILL.md` | extended | [Fetch](https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-skills/databricks-genie/SKILL.md) |
| `bronze/01-faker-data-generation` | `databricks-skills/databricks-synthetic-data-generation/SKILL.md` | extended | [Fetch](https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-skills/databricks-synthetic-data-generation/SKILL.md) |
| `ml/00-ml-pipeline-setup` | `databricks-skills/databricks-model-serving/SKILL.md`, `databricks-skills/databricks-vector-search/SKILL.md` | extended | [Serving](https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-skills/databricks-model-serving/SKILL.md), [Vector](https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-skills/databricks-vector-search/SKILL.md) |

---

## Reference-Only Mappings

These skills reference upstream for accuracy but their content is largely original.

| Our Skill | AI-Dev-Kit Path(s) | Relationship | Raw URL for Audit |
|---|---|---|---|
| `genai-agents/02-mlflow-genai-evaluation` | `databricks-tools-core/databricks_tools_core/sql/` | reference | [Fetch](https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-tools-core/databricks_tools_core/sql/sql.py) |
| `genai-agents/03-lakebase-memory-patterns` | `databricks-builder-app/` (Lakebase patterns) | reference | [Fetch](https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-builder-app/README.md) |
| `genai-agents/04-prompt-registry-patterns` | `databricks-skills/databricks-agent-bricks/SKILL.md` | reference | [Fetch](https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-skills/databricks-agent-bricks/SKILL.md) |
| `genai-agents/07-production-monitoring` | `databricks-skills/databricks-agent-bricks/SKILL.md` | reference | [Fetch](https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-skills/databricks-agent-bricks/SKILL.md) |
| `common/databricks-python-imports` | `databricks-skills/databricks-config/SKILL.md` | reference | [Fetch](https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-skills/databricks-config/SKILL.md) |

---

## Databricks SDK Lineage (reference)

These skills reference the Databricks Python SDK (`databricks/databricks-sdk-py`) as their source of truth for API method signatures and dataclass definitions. They are original content but must stay in sync with SDK changes.

**Upstream repo:** `databricks/databricks-sdk-py` (branch: `main`)
**SDK Docs:** `https://databricks-sdk-py.readthedocs.io/en/latest/`

| Our Skill | SDK Path(s) | Relationship | Docs URL for Audit |
|---|---|---|---|
| `monitoring/01-lakehouse-monitoring-comprehensive` | `databricks/sdk/service/dataquality.py` | reference | [API](https://databricks-sdk-py.readthedocs.io/en/latest/workspace/dataquality/data_quality.html), [Dataclasses](https://databricks-sdk-py.readthedocs.io/en/latest/dbdataclasses/dataquality.html) |
| `monitoring/04-anomaly-detection` | `databricks/sdk/service/dataquality.py` | reference | [API](https://databricks-sdk-py.readthedocs.io/en/latest/workspace/dataquality/data_quality.html), [Dataclasses](https://databricks-sdk-py.readthedocs.io/en/latest/dbdataclasses/dataquality.html) |

**Key verification points for SDK lineage:**
- `DataQualityAPI` method signatures (especially asymmetry: `create_monitor(monitor)` vs `update_monitor(object_type, object_id, monitor, update_mask)`)
- Dataclass field names and types (`Monitor`, `DataProfilingConfig`, `AnomalyDetectionConfig`, etc.)
- Enum values (`DataProfilingCustomMetricType`, `AggregationGranularity`, `RefreshState`)
- Methods marked as `(Unimplemented)` in the SDK (`list_monitor`, `delete_refresh`, `update_refresh`)

---

## Unmapped Upstream Skills

These AI-Dev-Kit skills currently have **no corresponding skill** in our repository. Review during audits to determine if a new skill should be created or an existing skill should add a mapping.

| Upstream Skill | Description | Potential Mapping |
|---|---|---|
| `databricks-app-apx` | Full-stack apps (FastAPI + React) | New skill or extend genai-agents |
| `databricks-app-python` | Python web apps (Dash, Streamlit, Flask) | New skill or extend genai-agents |
| `databricks-dbsql` | DBSQL advanced: SQL scripting, stored procs, pipe syntax, AI functions, geospatial | Broadly useful — consider new common skill |
| `databricks-docs` | Documentation index via llms.txt | Low priority — reference utility |
| `databricks-lakebase-autoscale` | Lakebase with automatic scaling | Complement to lakebase-memory-patterns |
| `databricks-spark-structured-streaming` | Spark Structured Streaming patterns | Could extend silver layer skills |
| `databricks-unstructured-pdf-generation` | Synthetic PDF generation for RAG | Could extend genai-agents |
| `databricks-zerobus-ingest` | ZeroBus ingestion patterns | Could extend bronze layer skills |
| `spark-python-data-source` | Custom Spark Python data sources | Low priority — specialized |
| `TEMPLATE` | Skill template for creating new upstream skills | Reference only |

---

## No Upstream (Internal Methodology)

These skills are internal methodology, conventions, or stable patterns with no external lineage. They have `upstream_sources: []` in their frontmatter.

| Our Skill | Reason |
|---|---|
| `admin/create-agent-skill` | Internal convention (AgentSkills.io spec) |
| `admin/self-improvement` | Internal workflow |
| `admin/documentation-organization` | Internal convention |
| `admin/skill-freshness-audit` | This audit system (self-referential) |
| `skill-navigator` | Internal routing |
| `planning/00-project-planning` | Internal planning methodology |
| `exploration/00-adhoc-exploration-notebooks` | Internal notebook patterns |
| `gold/00-gold-layer-design` | Dimensional modeling methodology |
| `gold/01-gold-layer-setup` | Internal setup patterns |
| `gold/pipeline-workers/01-yaml-table-setup` | Internal YAML-driven approach |
| `gold/design-workers/01-grain-definition` | Internal grain definition patterns |
| `gold/design-workers/02-dimension-patterns` | Internal dimension design patterns |
| `gold/design-workers/03-fact-table-patterns` | Internal fact table design patterns |
| `gold/design-workers/04-conformed-dimensions` | Internal enterprise integration patterns |
| `gold/design-workers/05-erd-diagrams` | Mermaid diagramming patterns |
| `gold/design-workers/06-table-documentation` | Internal documentation patterns |
| `gold/design-workers/07-design-validation` | Internal design validation logic |
| `gold/pipeline-workers/02-merge-patterns` | Stable MERGE SQL patterns |
| `gold/pipeline-workers/03-deduplication` | Stable deduplication patterns |
| `gold/pipeline-workers/04-grain-validation` | Stable grain validation logic |
| `gold/pipeline-workers/05-schema-validation` | Stable schema validation logic |
| `semantic-layer/00-semantic-layer-setup` | Internal orchestrator |
| `semantic-layer/02-databricks-table-valued-functions` | Internal TVF patterns |
| `monitoring/00-observability-setup` | Internal orchestrator |
| `monitoring/03-sql-alerting-patterns` | Internal alerting patterns |
| `silver/02-dqx-patterns` | DQX library (databrickslabs, not ai-dev-kit) |
| `bronze/00-bronze-layer-setup` | Internal setup patterns |
| `common/databricks-expert-agent` | Philosophy/principles (not API-dependent) |
| `common/naming-tagging-standards` | Internal naming convention |

---

## Maintaining This Map

When adding a new skill:

1. Check if the skill's domain has a corresponding AI-Dev-Kit skill in `databricks-skills/`
2. If yes, add the mapping to the appropriate section above
3. Add `upstream_sources` to the new skill's frontmatter (see `assets/templates/verification-metadata.yaml` for the schema)
4. If no upstream, add the skill to the "No Upstream" table with a reason

When AI-Dev-Kit adds a new skill:

1. Check if any existing skills in our repo would benefit from the new upstream skill
2. If yes, update the mapping table and add `upstream_sources` to the affected skill(s)
3. If the new upstream skill covers a gap, consider creating a new skill in our repo
4. Move the skill from "Unmapped Upstream Skills" to the appropriate mapping table

## AI-Dev-Kit Component Summary

For reference, these are the upstream components in `databricks-solutions/ai-dev-kit`:

| Component | Path | What It Contains |
|---|---|---|
| **databricks-skills** | `databricks-skills/` | 25 SKILL.md files for AI assistants — see skill list below |
| **databricks-tools-core** | `databricks-tools-core/` | Python library: SQL execution, compute, jobs, serving, file operations, Unity Catalog management |
| **databricks-mcp-server** | `databricks-mcp-server/` | MCP server exposing tools-core as AI-assistant-callable tools |
| **databricks-builder-app** | `databricks-builder-app/` | Full-stack web app (React + FastAPI) with Claude Code integration and Lakebase |
| **ai-dev-project** | `ai-dev-project/` | Starter template project for new AI coding projects |

### Upstream Skills Inventory (databricks-skills/)

| Category | Skill | Description |
|---|---|---|
| **AI & Agents** | `databricks-agent-bricks` | Knowledge Assistants, Genie Spaces, Supervisor Agents |
| | `databricks-genie` | Genie Spaces: create, curate, query via Conversation API |
| | `databricks-model-serving` | Deploy MLflow models and AI agents to endpoints |
| | `databricks-mlflow-evaluation` | MLflow 3 GenAI evaluation: scorers, MemAlign, GEPA prompt optimization |
| | `databricks-unstructured-pdf-generation` | Generate synthetic PDFs for RAG |
| | `databricks-vector-search` | Vector similarity search for RAG and semantic search |
| **Analytics & Dashboards** | `databricks-aibi-dashboards` | AI/BI dashboards with SQL validation workflow |
| | `databricks-metric-views` | Unity Catalog metric views (YAML-based, dimensions, measures, joins) |
| | `databricks-unity-catalog` | System tables for lineage, audit, billing; volume operations |
| | `databricks-dbsql` | DBSQL advanced: SQL scripting, stored procs, pipe syntax, AI functions, geospatial |
| **Data Engineering** | `databricks-spark-declarative-pipelines` | SDP (formerly DLT) in SQL/Python with serverless compute |
| | `databricks-spark-structured-streaming` | Spark Structured Streaming: Kafka, stream joins, checkpoints |
| | `databricks-jobs` | Multi-task workflows, triggers, schedules |
| | `databricks-synthetic-data-generation` | Realistic test data with Faker, file-based workflow |
| | `databricks-zerobus-ingest` | ZeroBus ingestion patterns |
| **Development & Deployment** | `databricks-asset-bundles` | DABs for multi-environment deployments (apps, dashboards, jobs, pipelines) |
| | `databricks-app-apx` | Full-stack apps (FastAPI + React) |
| | `databricks-app-python` | Python web apps (Dash, Streamlit, Flask) |
| | `databricks-python-sdk` | Python SDK, Connect, CLI, REST API |
| | `databricks-config` | Profile authentication setup |
| | `databricks-lakebase-provisioned` | Managed PostgreSQL for OLTP workloads |
| | `databricks-lakebase-autoscale` | Lakebase with automatic scaling |
| **Reference** | `databricks-docs` | Documentation index via llms.txt |
| | `spark-python-data-source` | Custom Spark Python data sources |
| | `TEMPLATE` | Skill template for new upstream skills |
