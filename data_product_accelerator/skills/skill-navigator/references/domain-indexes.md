# Domain Index Summaries

This document contains detailed domain index summaries for the skill navigation system. Token estimates reflect the **post-restructuring** SKILL.md sizes (all under 500 lines). Detailed content is in each skill's `references/` directory.

**Convention:** `00-` prefix = orchestrator, `01+` prefix = worker skills.

**Design-First Pipeline:**
```
context/*.csv → Gold Design (1) → Bronze (2) → Silver (3) → Gold Impl (4) → Planning (5) → Semantic (6) → Genie Optimization (6b) → Observability (7) → ML (8) → GenAI (9)
```

**Input Convention:** Customer schema CSV lives in `context/` directory (e.g., `context/Wanderbricks_Schema.csv`). This is the single starting input that feeds the entire pipeline.

---

## Gold Layer Index (Design Phase — Stage 1)

Gold Design is the **entry point** for the Design-First pipeline. It reads the customer's schema CSV from `context/` and produces YAML schemas, ERDs, and documentation before any tables are created.

See: [Gold Layer Index (Stages 1 & 4)](#gold-layer-index-stages-1--4) below for the complete Gold Layer skill inventory.

---

## Bronze Layer Index (Stage 2)

**Skills in domain:** 2 skills (1 orchestrator, 1 worker)

### Orchestrator

| Skill | Path | ~Tokens |
|---|---|---|
| `bronze-layer-setup` | `bronze/00-bronze-layer-setup/SKILL.md` | ~1.5K |

### Workers

| Skill | Path | ~Tokens | Standalone |
|---|---|---|---|
| `faker-data-generation` | `bronze/01-faker-data-generation/SKILL.md` | ~1.0K | Yes |

**Key Patterns:**
1. Bronze layer optimized for testing/demos (not production ingestion)
2. **Approach A (recommended): Schema CSV + Faker** — reads `context/*.csv` to create Bronze tables matching customer's source schema, then generates Faker data
3. Approach B: Read existing tables directly; Approach C: Copy from external sources
4. Generate dimensions first, then facts (FK integrity)
5. All tables need `CLUSTER BY AUTO`, CDF enabled, governance TBLPROPERTIES

**Schema CSV flow:** `context/*.csv` → Gold Design (stage 1) → Bronze (stage 2) — both read the schema CSV

**When to load full skills:**
- Setting up Bronze end-to-end → Load `bronze/00-bronze-layer-setup`
- Faker patterns only → Load `bronze/01-faker-data-generation`

---

## Silver Layer Index (Stage 3)

**Skills in domain:** 3 skills (1 orchestrator, 2 workers)

### Orchestrator

| Skill | Path | ~Tokens |
|---|---|---|
| `silver-layer-setup` | `silver/00-silver-layer-setup/SKILL.md` | ~1.8K |

### Workers

| Skill | Path | ~Tokens | Standalone |
|---|---|---|---|
| `dlt-expectations-patterns` | `silver/01-dlt-expectations-patterns/SKILL.md` | ~1.7K | Yes |
| `dqx-patterns` | `silver/02-dqx-patterns/SKILL.md` | ~1.3K | Yes (optional, also used by Gold stage 4) |

**Key Patterns:**
1. DLT expectations stored in Unity Catalog Delta table
2. Use `@dlt.expect_all_or_drop()` for strict enforcement
3. DQX provides richer diagnostics than DLT expectations
4. Pre-merge validation catches issues before Gold

**When to load full skills:**
- Creating Silver end-to-end → Load `silver/00-silver-layer-setup`
- DLT expectations only → Load `silver/01-dlt-expectations-patterns`
- Advanced DQX validation → Load `silver/02-dqx-patterns`

---

## Gold Layer Index (Stages 1 & 4)

**Skills in domain:** 14 skills (2 orchestrators, 12 workers)

### Orchestrators

| Skill | Path | Stage | ~Tokens |
|---|---|---|---|
| `gold-layer-design` | `gold/00-gold-layer-design/SKILL.md` | 1 (Design — **entry point**, reads schema CSV) | ~2.0K |
| `gold-layer-setup` | `gold/01-gold-layer-setup/SKILL.md` | 4 (Impl) | ~1.5K |

**Design-First workflow:** `00-gold-layer-design` (stage 1) → reads `context/*.csv` → creates YAML, ERDs, docs → Bronze (stage 2) → Silver (stage 3) → `01-gold-layer-setup` (stage 4) → creates tables, merge scripts, jobs

### Design Workers (Stage 1 — called by `gold-layer-design`)

| Skill | Path | ~Tokens | Standalone |
|---|---|---|---|
| `01-grain-definition` | `gold/design-workers/01-grain-definition/SKILL.md` | ~1.2K | Yes |
| `02-dimension-patterns` | `gold/design-workers/02-dimension-patterns/SKILL.md` | ~1.2K | Yes |
| `03-fact-table-patterns` | `gold/design-workers/03-fact-table-patterns/SKILL.md` | ~1.2K | Yes |
| `04-conformed-dimensions` | `gold/design-workers/04-conformed-dimensions/SKILL.md` | ~1.1K | Yes |
| `05-erd-diagrams` | `gold/design-workers/05-erd-diagrams/SKILL.md` | ~1.2K | Yes |
| `06-table-documentation` | `gold/design-workers/06-table-documentation/SKILL.md` | ~1.1K | Yes |
| `07-design-validation` | `gold/design-workers/07-design-validation/SKILL.md` | ~1.1K | Yes |

### Pipeline Workers (Stage 4 — called by `gold-layer-setup`)

| Skill | Path | ~Tokens | Standalone |
|---|---|---|---|
| `01-yaml-table-setup` | `gold/pipeline-workers/01-yaml-table-setup/SKILL.md` | ~1.8K | Yes |
| `02-merge-patterns` | `gold/pipeline-workers/02-merge-patterns/SKILL.md` | ~1.3K | Yes |
| `03-deduplication` | `gold/pipeline-workers/03-deduplication/SKILL.md` | ~1.4K | Yes |
| `04-grain-validation` | `gold/pipeline-workers/04-grain-validation/SKILL.md` | ~1.2K | Yes |
| `05-schema-validation` | `gold/pipeline-workers/05-schema-validation/SKILL.md` | ~1.1K | Yes |

**Key Patterns:**
1. Always deduplicate before MERGE to prevent duplicate key errors
2. Use explicit column mapping (Silver → Gold names may differ)
3. Fact tables: verify grain (transaction vs aggregated)
4. SCD2 dimensions need `is_current` filtering
5. Design → Implementation flow: YAML schemas must exist before implementation

**When to load full skills:**
- Designing Gold end-to-end → Load `gold/00-gold-layer-design`
- Implementing Gold end-to-end → Load `gold/01-gold-layer-setup`
- Specific task → Load the relevant worker skill directly

---

## Semantic Layer Index (Stage 6)

**Skills in domain:** 10 skills (1 orchestrator, 4 workers, 1 optimization orchestrator, 4 optimization workers)

### Orchestrator

| Skill | Path | ~Tokens |
|---|---|---|
| `semantic-layer-setup` | `semantic-layer/00-semantic-layer-setup/SKILL.md` | ~1.5K |

### Workers

| Skill | Path | ~Tokens | Standalone |
|---|---|---|---|
| `metric-views-patterns` | `semantic-layer/01-metric-views-patterns/SKILL.md` | ~1.4K | Yes |
| `databricks-table-valued-functions` | `semantic-layer/02-databricks-table-valued-functions/SKILL.md` | ~1.3K | Yes |
| `genie-space-patterns` | `semantic-layer/03-genie-space-patterns/SKILL.md` | ~1.5K | Yes |
| `genie-space-export-import-api` | `semantic-layer/04-genie-space-export-import-api/SKILL.md` | ~1.1K | Yes |

### Genie Optimization (Stage 6b — standalone orchestrator + 4 workers)

| Skill | Path | ~Tokens | Standalone |
|---|---|---|---|
| `genie-optimization-orchestrator` | `semantic-layer/05-genie-optimization-orchestrator/SKILL.md` | ~1.5K | Yes |
| `genie-benchmark-generator` | `semantic-layer/genie-optimization-workers/01-genie-benchmark-generator/SKILL.md` | ~1.2K | Yes |
| `genie-benchmark-evaluator` | `semantic-layer/genie-optimization-workers/02-genie-benchmark-evaluator/SKILL.md` | ~1.3K | Yes |
| `genie-metadata-optimizer` | `semantic-layer/genie-optimization-workers/03-genie-metadata-optimizer/SKILL.md` | ~1.2K | Yes |
| `genie-optimization-applier` | `semantic-layer/genie-optimization-workers/04-genie-optimization-applier/SKILL.md` | ~1.2K | Yes |

**Key Patterns:**
1. Metric views use `WITH METRICS LANGUAGE YAML` syntax
2. TVFs must have STRING parameters for Genie compatibility
3. Genie Spaces need comprehensive agent instructions (≤20 lines)
4. Export/Import uses `serialized_space` JSON format
5. Optimization uses MLflow-driven 3-layer judge architecture (8 judges + arbiter)
6. Optimization targets: accuracy ≥95%, repeatability ≥90%
7. Optimization workers: Generator (benchmarks) → Evaluator (judges) → Optimizer (GEPA/introspection) → Applier (6 control levers + dual persistence)

**Cross-domain usage:** `05-genie-optimization-orchestrator` is also used by `genai-agents/00-genai-agents-setup` (Phase 8: Genie Optimization). The orchestrator routes to 4 worker skills in `genie-optimization-workers/`.

**Plan-as-Contract:** The semantic-layer orchestrator `consumes` `plans/manifests/semantic-layer-manifest.yaml` (Phase 0). Falls back to Gold table self-discovery if no manifest exists.

**When to load full skills:**
- Building semantic layer end-to-end → Load `semantic-layer/00-semantic-layer-setup`
- Creating metric views → Load `semantic-layer/01-metric-views-patterns`
- Creating TVFs → Load `semantic-layer/02-databricks-table-valued-functions`
- Setting up Genie Space → Load `semantic-layer/03-genie-space-patterns`
- API automation → Load `semantic-layer/04-genie-space-export-import-api`
- Optimizing Genie → Load `semantic-layer/05-genie-optimization-orchestrator` (routes to workers on demand)
- Generating benchmarks only → Load `genie-optimization-workers/01-genie-benchmark-generator`
- Running evaluation only → Load `genie-optimization-workers/02-genie-benchmark-evaluator`

---

## Monitoring/Observability Index (Stage 7)

**Skills in domain:** 5 skills (1 orchestrator, 4 workers)

### Orchestrator

| Skill | Path | ~Tokens |
|---|---|---|
| `observability-setup` | `monitoring/00-observability-setup/SKILL.md` | ~1.5K |

### Workers

| Skill | Path | ~Tokens | Standalone | Auto-Triggered By |
|---|---|---|---|---|
| `lakehouse-monitoring-comprehensive` | `monitoring/01-lakehouse-monitoring-comprehensive/SKILL.md` | ~1.7K | Yes | — |
| `databricks-aibi-dashboards` | `monitoring/02-databricks-aibi-dashboards/SKILL.md` | ~1.4K | Yes | — |
| `sql-alerting-patterns` | `monitoring/03-sql-alerting-patterns/SKILL.md` | ~1.8K | Yes | — |
| `anomaly-detection` | `monitoring/04-anomaly-detection/SKILL.md` | ~1.5K | Yes | `silver-layer-setup`, `gold-layer-setup` |

**Key Patterns:**
1. Custom metrics use `input_columns=[":table"]` for table-level KPIs
2. Dashboard JSON uses `page.layout` for positioning
3. Alerts use config-driven YAML deployment
4. Monitor setup uses graceful degradation (delete-then-create)
5. **Anomaly detection auto-enabled on Silver/Gold schemas** — freshness/completeness monitoring from day one, no custom metrics needed

**Plan-as-Contract:** The orchestrator `consumes` `plans/manifests/observability-manifest.yaml` (Phase 0). Falls back to Gold table self-discovery if no manifest exists.

**Cross-Stage Trigger:** `04-anomaly-detection` is also invoked by `silver-layer-setup` (stage 3) and `gold-layer-setup` (stage 4) to enable schema-level monitoring at schema creation time, before the observability stage.

**When to load full skills:**
- Setting up observability end-to-end → Load `monitoring/00-observability-setup`
- Lakehouse Monitoring only → Load `monitoring/01-lakehouse-monitoring-comprehensive`
- Creating dashboards → Load `monitoring/02-databricks-aibi-dashboards`
- Setting up alerts → Load `monitoring/03-sql-alerting-patterns`
- Freshness/completeness monitoring → Load `monitoring/04-anomaly-detection`
- Silver/Gold schema setup (auto-triggered) → `04-anomaly-detection` is loaded automatically

---

## Infrastructure/Common Index

**Skills in domain:** 8 shared skills (no orchestrator — these are cross-cutting utilities)

| Skill | Path | ~Tokens | Used By Stages |
|---|---|---|---|
| `databricks-expert-agent` | `common/databricks-expert-agent/SKILL.md` | ~1.2K | 1-9 (all) |
| `databricks-asset-bundles` | `common/databricks-asset-bundles/SKILL.md` | ~1.2K | 1-9 |
| `databricks-autonomous-operations` | `common/databricks-autonomous-operations/SKILL.md` | ~2.0K | 1-9 (troubleshooting) |
| `naming-tagging-standards` | `common/naming-tagging-standards/SKILL.md` | ~1.5K | 1-9 (all) |
| `databricks-python-imports` | `common/databricks-python-imports/SKILL.md` | ~1.9K | 1-9 |
| `databricks-table-properties` | `common/databricks-table-properties/SKILL.md` | ~1.0K | 1-4 |
| `schema-management-patterns` | `common/schema-management-patterns/SKILL.md` | ~0.7K | 1-4 |
| `unity-catalog-constraints` | `common/unity-catalog-constraints/SKILL.md` | ~0.8K | 3-4 |

**Key Patterns:**
1. Use `notebook_task` not `python_task` in DABs
2. Use `base_parameters` dict, not CLI-style `parameters`
3. Schemas created programmatically with `CREATE SCHEMA IF NOT EXISTS`
4. Constraints applied via `ALTER TABLE` after table creation
5. Python imports: use `dbutils.widgets.get()` for DAB notebooks
6. Autonomous operations: Deploy → Poll → Diagnose → Fix → Redeploy (max 3 iterations) when stuck

**When to load `naming-tagging-standards`:**
- Creating any DDL (tables, columns, constraints, functions)
- Writing COMMENTs for tables, columns, TVFs, metric views
- Configuring workflow tags, governed tags, or budget policies
- Reviewing code for naming compliance (snake_case, prefixes, abbreviations)

**When to load `databricks-autonomous-operations`:**
- Any deployment failure (job, pipeline, monitor, alert, Genie Space)
- Error diagnosis and self-healing loop
- SDK/CLI/REST API reference for programmatic operations
- Triggers: "job failed", "troubleshoot", "self-heal", "redeploy", "deploy failed", "pipeline failed"

---

## ML Index (Stage 8)

**Skills in domain:** 1 skill (orchestrator-level, no workers)

| Skill | Path | ~Tokens |
|---|---|---|
| `ml-pipeline-setup` | `ml/00-ml-pipeline-setup/SKILL.md` | ~1.1K |

**Key Patterns:**
1. Use `/Shared/` experiment paths (not `/Users/`)
2. Don't define experiments in Asset Bundles
3. Log datasets inside `mlflow.start_run()` context
4. Inline helpers (don't import modules in DAB notebooks)

**Plan-as-Contract:** The orchestrator `consumes` `plans/manifests/ml-manifest.yaml` (Phase 0). Falls back to Gold table self-discovery if no manifest exists.

---

## GenAI Agents Index (Stage 9)

**Skills in domain:** 9 skills (1 orchestrator, 8 workers) + 1 cross-domain dependency

### Orchestrator

| Skill | Path | ~Tokens |
|---|---|---|
| `genai-agents-setup` | `genai-agents/00-genai-agents-setup/SKILL.md` | ~1.2K |

### Workers

| Skill | Path | ~Tokens | Standalone |
|---|---|---|---|
| `responses-agent-patterns` | `genai-agents/01-responses-agent-patterns/SKILL.md` | ~0.8K | Yes |
| `mlflow-genai-evaluation` | `genai-agents/02-mlflow-genai-evaluation/SKILL.md` | ~1.2K | Yes |
| `lakebase-memory-patterns` | `genai-agents/03-lakebase-memory-patterns/SKILL.md` | ~0.8K | Yes |
| `prompt-registry-patterns` | `genai-agents/04-prompt-registry-patterns/SKILL.md` | ~0.7K | Yes |
| `multi-agent-genie-orchestration` | `genai-agents/05-multi-agent-genie-orchestration/SKILL.md` | ~1.5K | Yes |
| `deployment-automation` | `genai-agents/06-deployment-automation/SKILL.md` | ~0.9K | Yes |
| `production-monitoring` | `genai-agents/07-production-monitoring/SKILL.md` | ~0.9K | Yes |
| `mlflow-genai-foundation` | `genai-agents/08-mlflow-genai-foundation/SKILL.md` | ~1.4K | Yes |

### Cross-Domain Dependencies

| Skill | Path | Domain | Purpose |
|---|---|---|---|
| `genie-optimization-orchestrator` | `semantic-layer/05-genie-optimization-orchestrator/SKILL.md` | Semantic Layer | Genie accuracy testing, control levers, dual persistence |

**Key Patterns:**
1. ResponsesAgent is MANDATORY for all new Databricks GenAI agents
2. Use OBO authentication with automatic context detection
3. LLM-as-judge evaluation with 4-6 guidelines per scorer
4. Lakebase provides both short-term and long-term memory
5. NO LLM fallback pattern for multi-agent Genie orchestration (critical)
6. Genie Space optimization is a cross-domain concern shared with Semantic Layer

**Plan-as-Contract:** The orchestrator `consumes` `plans/manifests/genai-agents-manifest.yaml` (Phase 0). Falls back to Genie Space self-discovery if no manifest exists.

**When to load full skills:**
- Building a new agent end-to-end → Load `genai-agents/00-genai-agents-setup`
- Genie optimization (Phase 8 of agent implementation) → Load `semantic-layer/05-genie-optimization-orchestrator`
- Specific task → Load the relevant worker skill directly

---

## Exploration Index

**Skills in domain:** 1 utility skill

| Skill | Path | ~Tokens |
|---|---|---|
| `adhoc-exploration-notebooks` | `exploration/00-adhoc-exploration-notebooks/SKILL.md` | ~0.9K |

---

## Planning Index (Stage 5)

**Skills in domain:** 1 orchestrator skill

| Skill | Path | ~Tokens |
|---|---|---|
| `project-planning` | `planning/00-project-planning/SKILL.md` | ~1.6K |

**Key Patterns:**
1. Planning starts AFTER Gold layer design and implementation are complete
2. Creates human-readable plan addendums (phase1-addendum-*.md) and phase2/phase3 docs
3. Generates machine-readable YAML manifests (plan-as-contract pattern) for downstream stages
4. Agent Domain Framework: ALL artifacts organized by domain (4-6 per project)
5. Agent Layer Architecture: Agents use Genie Spaces as query interface (not direct SQL)

**Plan-as-Contract Pattern:**
The Planning orchestrator `emits` 4 YAML manifest files consumed by downstream orchestrators:

| Manifest | Consumed By | Defines |
|---|---|---|
| `plans/manifests/semantic-layer-manifest.yaml` | `semantic-layer/00-*` (stage 6) | Metric Views, TVFs, Genie Spaces |
| `plans/manifests/observability-manifest.yaml` | `monitoring/00-*` (stage 7) | Monitors, Dashboards, Alerts |
| `plans/manifests/ml-manifest.yaml` | `ml/00-*` (stage 8) | Feature Tables, Models, Experiments |
| `plans/manifests/genai-agents-manifest.yaml` | `genai-agents/00-*` (stage 9) | Agents, Tools, Eval Datasets |

Each downstream orchestrator has a **Phase 0: Read Plan** that reads its manifest. If the manifest doesn't exist, the orchestrator falls back to Gold table self-discovery.

**Metadata fields:** `emits` (lists generated manifests), `reads` (lists Gold YAML inputs)

**When to load full skills:**
- Creating a project plan → Load `planning/00-project-planning`
- Understanding manifest format → See `references/manifest-generation-guide.md`
- Copy manifest templates → See `assets/templates/manifests/`

---

## Admin Index

**Skills in domain:** 4 utility skills

| Skill | Path | ~Tokens |
|---|---|---|
| `create-agent-skill` | `admin/create-agent-skill/SKILL.md` | ~1.0K |
| `self-improvement` | `admin/self-improvement/SKILL.md` | ~1.8K |
| `documentation-organization` | `admin/documentation-organization/SKILL.md` | ~0.9K |
| `skill-freshness-audit` | `admin/skill-freshness-audit/SKILL.md` | ~1.5K |


**Freshness Audit Key Patterns:**
1. Skills have `last_verified`, `volatility`, and optional `verification_sources` in frontmatter metadata
2. Volatility: high (30 days), medium (90 days), low (180 days) staleness thresholds
3. Scan script at `admin/skill-freshness-audit/scripts/scan_skill_freshness.py` reports stale skills
4. Verification sources map skills to official Databricks/MLflow documentation URLs for drift detection
5. Complements `self-improvement` (proactive audit vs reactive error-based learning)

**When to load:**
- Auditing skill currency → Load `admin/skill-freshness-audit`
- After platform release → Load `admin/skill-freshness-audit`
- Learning from errors → Load `admin/self-improvement`
