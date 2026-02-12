# AI-Dev-Kit Lineage Map

Maps every skill in this repository to its upstream source(s) in [`databricks-solutions/ai-dev-kit`](https://github.com/databricks-solutions/ai-dev-kit). Use this map during freshness audits and upstream sync checks.

**Upstream repo:** `databricks-solutions/ai-dev-kit` (branch: `main`)
**Raw URL base:** `https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/`

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
| `genai-agents/00-genai-agents-setup` | `databricks-skills/agent-bricks/SKILL.md` | extended | [Fetch](https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-skills/agent-bricks/SKILL.md) |
| `genai-agents/01-responses-agent-patterns` | `databricks-skills/agent-bricks/SKILL.md` | extended | [Fetch](https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-skills/agent-bricks/SKILL.md) |
| `genai-agents/05-multi-agent-genie-orchestration` | `databricks-skills/agent-bricks/SKILL.md` | extended | [Fetch](https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-skills/agent-bricks/SKILL.md) |
| `genai-agents/06-deployment-automation` | `databricks-skills/model-serving/SKILL.md` | extended | [Fetch](https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-skills/model-serving/SKILL.md) |
| `genai-agents/08-mlflow-genai-foundation` | `databricks-skills/agent-bricks/SKILL.md` | extended | [Fetch](https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-skills/agent-bricks/SKILL.md) |
| `monitoring/02-databricks-aibi-dashboards` | `databricks-skills/aibi-dashboards/SKILL.md` | extended | [Fetch](https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-skills/aibi-dashboards/SKILL.md) |
| `silver/00-silver-layer-setup` | `databricks-skills/spark-declarative-pipelines/SKILL.md` | extended | [Fetch](https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-skills/spark-declarative-pipelines/SKILL.md) |
| `silver/01-dlt-expectations-patterns` | `databricks-skills/spark-declarative-pipelines/SKILL.md` | extended | [Fetch](https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-skills/spark-declarative-pipelines/SKILL.md) |
| `common/databricks-asset-bundles` | `databricks-skills/asset-bundles/SKILL.md` | extended | [Fetch](https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-skills/asset-bundles/SKILL.md) |
| `common/databricks-autonomous-operations` | `databricks-skills/databricks-python-sdk/SKILL.md`, `databricks-skills/databricks-jobs/SKILL.md` | extended | [SDK](https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-skills/databricks-python-sdk/SKILL.md), [Jobs](https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-skills/databricks-jobs/SKILL.md) |
| `common/unity-catalog-constraints` | `databricks-skills/databricks-unity-catalog/SKILL.md` | derived | [Fetch](https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-skills/databricks-unity-catalog/SKILL.md) |
| `common/schema-management-patterns` | `databricks-skills/databricks-unity-catalog/SKILL.md` | derived | [Fetch](https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-skills/databricks-unity-catalog/SKILL.md) |
| `common/databricks-table-properties` | `databricks-skills/databricks-unity-catalog/SKILL.md` | derived | [Fetch](https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-skills/databricks-unity-catalog/SKILL.md) |
| `semantic-layer/03-genie-space-patterns` | `databricks-skills/databricks-genie/SKILL.md` | extended | [Fetch](https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-skills/databricks-genie/SKILL.md) |
| `semantic-layer/04-genie-space-export-import-api` | `databricks-skills/databricks-genie/SKILL.md` | extended | [Fetch](https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-skills/databricks-genie/SKILL.md) |
| `semantic-layer/05-genie-space-optimization` | `databricks-skills/databricks-genie/SKILL.md` | extended | [Fetch](https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-skills/databricks-genie/SKILL.md) |
| `bronze/01-faker-data-generation` | `databricks-skills/synthetic-data-generation/SKILL.md` | extended | [Fetch](https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-skills/synthetic-data-generation/SKILL.md) |
| `ml/00-ml-pipeline-setup` | `databricks-skills/model-serving/SKILL.md`, `databricks-skills/vector-search/SKILL.md` | extended | [Serving](https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-skills/model-serving/SKILL.md), [Vector](https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-skills/vector-search/SKILL.md) |

---

## Reference-Only Mappings

These skills reference upstream for accuracy but their content is largely original.

| Our Skill | AI-Dev-Kit Path(s) | Relationship | Raw URL for Audit |
|---|---|---|---|
| `genai-agents/02-mlflow-genai-evaluation` | `databricks-tools-core/databricks_tools_core/sql/` | reference | [Fetch](https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-tools-core/databricks_tools_core/sql/sql.py) |
| `genai-agents/03-lakebase-memory-patterns` | `databricks-builder-app/` (Lakebase patterns) | reference | [Fetch](https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-builder-app/README.md) |
| `genai-agents/04-prompt-registry-patterns` | `databricks-skills/agent-bricks/SKILL.md` | reference | [Fetch](https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-skills/agent-bricks/SKILL.md) |
| `genai-agents/07-production-monitoring` | `databricks-skills/agent-bricks/SKILL.md` | reference | [Fetch](https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-skills/agent-bricks/SKILL.md) |
| `common/databricks-python-imports` | `databricks-skills/databricks-config/SKILL.md` | reference | [Fetch](https://raw.githubusercontent.com/databricks-solutions/ai-dev-kit/main/databricks-skills/databricks-config/SKILL.md) |

---

## No Upstream (Internal Methodology)

These skills are internal methodology, conventions, or stable patterns with no AI-Dev-Kit lineage. They have `upstream_sources: []` in their frontmatter.

| Our Skill | Reason |
|---|---|
| `admin/create-agent-skill` | Internal convention (AgentSkills.io spec) |
| `admin/self-improvement` | Internal workflow |
| `admin/documentation-organization` | Internal convention |
| `admin/skill-freshness-audit` | This audit system (self-referential) |
| `admin/cursor-rule-to-skill` | Internal conversion utility |
| `skill-navigator` | Internal routing |
| `planning/00-project-planning` | Internal planning methodology |
| `exploration/00-adhoc-exploration-notebooks` | Internal notebook patterns |
| `gold/00-gold-layer-design` | Dimensional modeling methodology |
| `gold/01-gold-layer-setup` | Internal setup patterns |
| `gold/02-yaml-driven-gold-setup` | Internal YAML-driven approach |
| `gold/03-gold-layer-documentation` | Internal documentation patterns |
| `gold/04-gold-layer-merge-patterns` | Stable MERGE SQL patterns |
| `gold/05-gold-delta-merge-deduplication` | Stable deduplication patterns |
| `gold/06-fact-table-grain-validation` | Stable grain validation logic |
| `gold/07-gold-layer-schema-validation` | Stable schema validation logic |
| `gold/08-mermaid-erd-patterns` | Mermaid diagramming patterns |
| `semantic-layer/00-semantic-layer-setup` | Internal orchestrator |
| `semantic-layer/01-metric-views-patterns` | Internal metric view patterns |
| `semantic-layer/02-databricks-table-valued-functions` | Internal TVF patterns |
| `monitoring/00-observability-setup` | Internal orchestrator |
| `monitoring/01-lakehouse-monitoring-comprehensive` | Internal monitoring patterns |
| `monitoring/03-sql-alerting-patterns` | Internal alerting patterns |
| `monitoring/04-anomaly-detection` | Internal anomaly detection patterns |
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

## AI-Dev-Kit Component Summary

For reference, these are the upstream components in `databricks-solutions/ai-dev-kit`:

| Component | Path | What It Contains |
|---|---|---|
| **databricks-skills** | `databricks-skills/` | SKILL.md files for AI assistants (agent-bricks, aibi-dashboards, spark-declarative-pipelines, asset-bundles, databricks-jobs, databricks-genie, model-serving, databricks-unity-catalog, databricks-config, databricks-python-sdk, synthetic-data-generation, unstructured-pdf-generation, vector-search) |
| **databricks-tools-core** | `databricks-tools-core/` | Python library: SQL execution, compute, jobs, serving, file operations, Unity Catalog management |
| **databricks-mcp-server** | `databricks-mcp-server/` | MCP server exposing tools-core as AI-assistant-callable tools |
| **databricks-builder-app** | `databricks-builder-app/` | Full-stack web app (React + FastAPI) with Claude Code integration and Lakebase |
| **ai-dev-project** | `ai-dev-project/` | Starter template project for new AI coding projects |
