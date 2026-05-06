---
name: project-planning
description: >-
  Create multi-phase project plans for Databricks data platform solutions
  with Agent Domain Framework and Agent Layer Architecture. Includes interactive
  Quick Start with key decisions, industry-specific domain patterns, complete
  phase document templates (Use Cases, Agents, Frontend), Genie Space integration
  patterns, deployment order requirements, and worked examples. Use when planning
  any Databricks solution post-Gold layer — observability, analytics, agent-based
  frameworks, or multi-artifact projects.
metadata:
  author: prashanth subrahmanyam
  version: "2.0"
  domain: planning
  role: orchestrator
  pipeline_stage: 5
  pipeline_stage_name: planning
  next_stages:
    - semantic-layer-setup
  workers: []
  common_dependencies:
    - databricks-expert-agent
    - naming-tagging-standards
  emits:
    - plans/use-case-catalog.md
    - plans/manifests/semantic-layer-manifest.yaml
    - plans/manifests/observability-manifest.yaml
    - plans/manifests/ml-manifest.yaml
    - plans/manifests/genai-agents-manifest.yaml
  reads:
    - gold_layer_design/yaml/
    - gold_layer_design/erd_master.md
    - gold_layer_design/docs/BUSINESS_ONBOARDING_GUIDE.md
  supported_modes:
    - acceleration     # Full breadth (DEFAULT) — all domains, all artifacts, full rationalization
    - workshop         # Learning & Enablement — minimal representative sampling with hard artifact caps
  default_mode: acceleration
  last_verified: "2026-02-07"
  volatility: low
  upstream_sources: []  # Internal planning methodology
---

# Project Plan Methodology for Databricks Solutions

## Planning Mode

**Default: Data Product Acceleration** — full breadth, all domains, all artifacts. This is the standard behavior described in this entire skill document below.

**Workshop mode** is available for Learning & Enablement scenarios with hard artifact caps. It is NEVER activated unless the user includes the **exact phrase** `planning_mode: workshop` in their prompt.

### Mode Detection Rules

1. **Default is ALWAYS `acceleration`.** If the user does not explicitly declare workshop mode, use acceleration.
2. **Workshop mode requires EXPLICIT opt-in.** The user must include one of these EXACT phrases:
   - `planning_mode: workshop`
   - `"workshop mode"`
   - `"use workshop mode"`
3. **Do NOT infer workshop mode** from words like "small", "simple", "demo", "limited", "quick", "basic", "training", or "few". These are NOT triggers. A user may want a narrow-scope acceleration plan — that's still acceleration mode with fewer use cases.
4. **When in doubt, ask.** If the user's intent is ambiguous (e.g., "Create a plan for a workshop"), ask: *"Would you like full Data Product Acceleration mode (default) or Workshop mode with limited artifacts? To use workshop mode, include `planning_mode: workshop` in your request."*
5. **Confirm mode at the start.** The first line of any plan output should state the active mode:
   - `**Planning Mode:** Data Product Acceleration (default)`
   - `**Planning Mode:** Workshop (explicit opt-in — artifact caps active)`
6. **When workshop mode is activated,** read `references/workshop-mode-profile.md` for artifact caps, phase scope, and selection criteria. Do NOT read that reference otherwise.
7. **Propagate mode to manifests.** Add `planning_mode: workshop` or `planning_mode: acceleration` to all generated manifest YAML files. Downstream orchestrators seeing `workshop` MUST NOT expand beyond the listed artifacts via self-discovery.

## Overview

Comprehensive methodology for creating multi-phase project plans for Databricks data platform solutions. This skill combines interactive project planning with architectural methodology, including templates, worked examples, and quality standards.

**Key Assumption:** Planning starts AFTER Bronze ingestion and Gold layer design are complete. These are prerequisites, not phases.

## When to Use This Skill

Use this skill when:
- Creating architectural plans for Databricks data platform projects
- Building observability, analytics, or monitoring solutions
- Planning multi-artifact solutions (TVFs, Metric Views, Dashboards, Genie Spaces, Alerts, ML Models)
- Developing agent-based frameworks for platform management
- Creating frontend applications for data platform interaction
- Starting a new project after Gold layer is complete

## Quick Start (5 Minutes)

### Fast Track: Create Your Project Plan

```bash
# 1. Verify prerequisites are complete:
#    - Bronze ingestion ✅
#    - Silver DLT streaming ✅
#    - Gold dimensional model ✅

# 2. Run this prompt with your project info:
"Create a phased project plan for {project_name} with:
- Gold tables: {n} tables ({d} dimensions + {f} facts)
- Use cases: {use_case_1, use_case_2, use_case_3, etc.}
- Target audience: {executives, analysts, data scientists}
- Agent domains: {domain1, domain2, domain3, domain4, domain5}"

# 3. Output: Complete plan structure in plans/ folder
```

### Key Decisions (Answer These First)

| Decision | Options | Your Choice |
|----------|---------|-------------|
| Agent Domains | Derive from business questions (typically 2-5) | __________ |
| Phase 1 Addendums | TVFs, Metric Views, Dashboards, Monitoring, Genie, Alerts, ML | __________ |
| Phase 2 Scope | AI Agents (optional) or skip | __________ |
| Phase 3 Scope | Frontend App (optional) or skip | __________ |
| Genie Space Count | Based on asset count vs 25-asset limit (see Rationalization) | __________ |
| Agent Architecture | Agents use Genie Spaces (recommended) or Direct SQL | __________ |
| Agent-Genie Mapping | 1:1, consolidated, or unified (based on asset volume) | __________ |

## Working Memory Management

This orchestrator spans 3 phases. To maintain coherence without context pollution:

**After each phase, persist a brief summary note** capturing:
- **Phase 1:** Domain list with Gold table mappings, addendum selections, business questions per domain, artifact count estimates
- **Phase 2:** Plan document file paths, cross-references verified, total artifact counts by type
- **Phase 3:** Manifest file paths (semantic-layer, observability, ml, genai-agents), validation results, summary counts

**What to keep in working memory:** Current phase's template, domain list + artifact inventory, and previous phase's summary. Discard intermediate outputs — they are on disk. Read templates from `assets/templates/` and references just-in-time, not upfront.

---

## Step-by-Step Workflow

### Phase 1: Requirements Gathering

#### Project Information

| Field | Your Value |
|-------|------------|
| Project Name | {project_name} |
| Business Domain | {hospitality, retail, healthcare, finance, etc.} |
| Primary Use Cases | {use_case_1, use_case_2, use_case_3, etc.} |
| Target Stakeholders | {executives, analysts, data scientists, operations} |

#### Prerequisites Status

| Layer | Count | Status |
|-------|-------|--------|
| Bronze Tables | {n} | ✅ Complete |
| Silver Tables | {m} | ✅ Complete |
| Gold Dimensions | {d} | ✅ Complete |
| Gold Facts | {f} | ✅ Complete |

#### Define Agent Domains

Derive domains from your business questions and Gold table groupings (see Artifact Rationalization Framework). Do not force a fixed number — let the data model and use cases determine natural boundaries.

| Domain | Icon | Focus Area | Key Gold Tables | Est. Business Questions |
|--------|------|------------|-----------------|------------------------|
| {Domain 1} | {emoji} | {focus} | {tables} | {count} |
| {Domain 2} | {emoji} | {focus} | {tables} | {count} |
| ... | ... | ... | ... | ... |

**Sizing check:** If a domain has < 3 business questions, consider merging it. If two domains share > 70% of Gold tables, consolidate.

See [Industry Domain Patterns](references/industry-domain-patterns.md) for examples by industry.

#### Phase 1 Addendum Selection

| # | Addendum | Include? | Artifact Count |
|---|----------|----------|----------------|
| 1.1 | ML Models | {Yes/No} | {count} |
| 1.2 | Table-Valued Functions | {Yes/No} | {count} |
| 1.3 | Metric Views | {Yes/No} | {count} |
| 1.4 | Lakehouse Monitoring | {Yes/No} | {count} |
| 1.5 | AI/BI Dashboards | {Yes/No} | {count} |
| 1.6 | Genie Spaces | {Yes/No} | {count} |
| 1.7 | Alerting Framework | {Yes/No} | {count} |

#### Key Business Questions by Domain

List 5-10 key questions per domain that the solution must answer:

**{Domain 1}:**
1. {Question 1}
2. {Question 2}
3. {Question 3}
4. {Question 4}
5. {Question 5}

#### Use Case Catalog

After defining business questions and selecting addendums, consolidate into a **Use Case Catalog** — one entry per distinct analytical or operational problem the solution will address. Each use case ties business questions to the Gold tables and artifacts that solve them. Use `assets/templates/use-case-catalog-template.md` for the full format.

| UC# | Use Case Name | Domain | Gold Tables | Artifact Types | Example Question |
|-----|--------------|--------|-------------|---------------|-----------------|
| UC-001 | {Descriptive Name} | {Domain} | `fact_*`, `dim_*` | TVF, MV, Dashboard | "{Natural language question}?" |
| UC-002 | ... | ... | ... | ... | ... |

**Use Case Catalog Rules:**
- Every use case MUST include 3-5 business questions phrased in natural language
- Every business question from the domain sections above MUST map to at least one use case
- Every artifact in the addendum summaries MUST trace back to at least one use case question
- Questions should be phrased as stakeholders would ask them (these become Genie benchmark candidates)
- Group related questions into a single use case when they share the same Gold tables and grain

See [Worked Example: Wanderbricks](references/worked-example-wanderbricks.md) for 3 fully worked-out use case cards.

**Stakeholder Checkpoint:** After generating the use case catalog, pause and present the Use Case Summary table to the user for confirmation before proceeding to addendum generation. If the user requests changes, update the catalog and domain questions before continuing.

### Phase 2: Plan Document Generation

Create plan documents using templates in the following order:

1. **README** — `assets/templates/plans-readme-template.md` (plan index)
2. **Prerequisites** — `assets/templates/prerequisites-template.md` (data layer summary)
3. **Use Case Catalog** — `assets/templates/use-case-catalog-template.md` (consolidated use case definitions)
4. **Phase 1 Master** — `assets/templates/phase1-use-cases-template.md` (analytics artifacts)
5. **Addendums** (selected in Phase 1):
   - TVFs — `assets/templates/phase1-tvfs-template.md`
   - Alerting — `assets/templates/phase1-alerting-template.md`
   - Genie Spaces — `assets/templates/phase1-genie-spaces-template.md`
6. **Phase 2** — `assets/templates/phase2-agent-framework-template.md` (AI agents)
7. **Phase 3** — `assets/templates/phase3-frontend-template.md` (user interface)

### Phase 3: Manifest Generation (Plan-as-Contract)

After creating plan documents, generate **machine-readable YAML manifests** that downstream orchestrators consume as implementation contracts.

**Why manifests?** The "Extract, Don't Generate" principle applies to the planning-to-implementation handoff. Manifests ensure downstream orchestrators implement exactly what was planned — no missed artifacts, no naming inconsistencies.

**MANDATORY: Read the manifest generation guide:**

| # | Reference Path | What It Provides |
|---|----------------|------------------|
| 1 | `references/manifest-generation-guide.md` | Full manifest workflow, validation, consumption pattern |

**Steps:**
1. Review Gold layer YAML schemas in `gold_layer_design/yaml/`
2. For each plan addendum, extract the concrete artifact definitions
3. Generate 4 YAML manifests using templates from `assets/templates/manifests/`:
   - `plans/manifests/semantic-layer-manifest.yaml` — TVFs, Metric Views, Genie Spaces
   - `plans/manifests/observability-manifest.yaml` — Monitors, Dashboards, Alerts
   - `plans/manifests/ml-manifest.yaml` — Feature Tables, Models, Experiments
   - `plans/manifests/genai-agents-manifest.yaml` — Agents, Tools, Eval Datasets
4. For each artifact in a manifest, add `use_case_refs` listing the UC# it implements (from `plans/use-case-catalog.md`)
5. Validate all table/column references exist in Gold YAML
6. Verify summary counts match actual artifact counts
7. Run `python scripts/validate_use_case_coverage.py plans/use-case-catalog.md` to verify coverage
8. Commit manifests alongside plan documents

**Key principle:** Every artifact in a manifest MUST trace back to (a) a Gold layer table and (b) a business question from the plan addendum.

**Output Structure:**
```
plans/
├── use-case-catalog.md                    # Consolidated use case definitions
├── manifests/
│   ├── semantic-layer-manifest.yaml       # → consumed by semantic-layer/00-*
│   ├── observability-manifest.yaml        # → consumed by monitoring/00-*
│   ├── ml-manifest.yaml                   # → consumed by ml/00-*
│   └── genai-agents-manifest.yaml         # → consumed by genai-agents/00-*
```

**Downstream consumption:** Each downstream orchestrator (stages 6-9) has a **Phase 0: Read Plan** step that reads its manifest. If the manifest doesn't exist (e.g., user skipped Planning), the orchestrator falls back to self-discovery from Gold tables.

---

## Plan Structure Framework

### Standard Project Phases

```
plans/
├── README.md                              # Index and overview
├── use-case-catalog.md                    # Consolidated use case definitions
├── prerequisites.md                       # Bronze/Silver/Gold summary (optional)
├── phase1-use-cases.md                    # Analytics artifacts (master)
│   ├── phase1-addendum-1.1-ml-models.md
│   ├── phase1-addendum-1.2-tvfs.md
│   ├── phase1-addendum-1.3-metric-views.md
│   ├── phase1-addendum-1.4-lakehouse-monitoring.md
│   ├── phase1-addendum-1.5-aibi-dashboards.md
│   ├── phase1-addendum-1.6-genie-spaces.md
│   └── phase1-addendum-1.7-alerting.md
├── phase2-agent-framework.md              # AI Agents
├── phase3-frontend-app.md                 # User Interface
└── manifests/                             # Machine-readable contracts
    ├── semantic-layer-manifest.yaml       # → semantic-layer/00-*
    ├── observability-manifest.yaml        # → monitoring/00-*
    ├── ml-manifest.yaml                   # → ml/00-*
    └── genai-agents-manifest.yaml         # → genai-agents/00-*
```

### Phase Dependencies

```
Prerequisites (Bronze → Silver → Gold) → Phase 1 (Use Cases) → Phase 2 (Agents) → Phase 3 (Frontend)
         [COMPLETE]                               ↓
                                           All Addendums
```

## Agent Domain Framework

### Core Principle

**ALL artifacts across ALL phases MUST be organized by Agent Domain.** This ensures:
- Consistent categorization across 100+ artifacts
- Clear ownership by future AI agents
- Easy discoverability for users
- Aligned tooling for each domain

### Agent Domain Application

Every artifact (TVF, Metric View, Dashboard, Alert, ML Model, Monitor, Genie Space) must:
1. Be tagged with its Agent Domain
2. Use the domain's Gold tables
3. Answer domain-specific questions
4. Be grouped with related domain artifacts in documentation

**Example Pattern:**
```markdown
## {Domain}: get_{metric}_by_{dimension}

**Agent Domain:** {Domain}
**Gold Tables:** `fact_{entity}`, `dim_{entity}`
**Business Questions:** "What are the top {metric} by {dimension}?"
```

See [Industry Domain Patterns](references/industry-domain-patterns.md) for domain templates by industry.

## Agent Layer Architecture Pattern

### Core Principle: Agents Use Genie Spaces as Query Interface

**AI Agents DO NOT query data assets directly.** Instead, they use Genie Spaces as their natural language query interface. Genie Spaces translate natural language to SQL and route to appropriate tools.

```
USERS (Natural Language)
    ↓
PHASE 2: AI AGENT LAYER (LangChain/LangGraph)
    ├── Orchestrator Agent (intent classification)
    └── Specialized Agents (1 per domain)
            ↓
PHASE 1.6: GENIE SPACES (NL Query Execution)
    ├── {Domain 1} Intelligence Genie Space
    ├── {Domain 2} Intelligence Genie Space
    └── Unified {Project} Monitor
            ↓
PHASE 1: DATA ASSETS (Agent Tools)
    ├── Metric Views (pre-aggregated - use FIRST)
    ├── TVFs (parameterized queries)
    ├── ML Predictions (ML-powered insights)
    └── Lakehouse Monitors (drift detection)
            ↓
PREREQUISITES: GOLD LAYER (Foundation)
```

### Deployment Order (Critical!)

**Genie Spaces MUST be deployed BEFORE agents can use them.**

```
Phase 1.1-1.5 (Data Assets) → Phase 1.6 (Genie Spaces) → Phase 2 (Agents)
         ↓                            ↓                        ↓
   Build foundation          Create NL interface        Consume interface
```

For detailed architecture, design patterns, "Why Genie Spaces" comparison, and testing strategy, see [Agent Layer Architecture](references/agent-layer-architecture.md).

## Artifact Rationalization Framework

**MANDATORY: Read** `references/rationalization-framework.md` for complete sizing guides, decision matrices, and naming conventions.

**Core Principle:** Every artifact must trace to a specific business question. Do not create artifacts to fill quotas.

**Critical constraints (always enforce, even without reading the reference):**
- Genie Spaces: **max 25 assets per space**; 10-25 per space is optimal; <10 = merge spaces
- TVFs: **only** when Metric Views cannot answer the question (requires parameterized multi-table logic)
- Metric Views: one per distinct analytical grain, not per domain
- Domains: emerge from business questions (min 3 questions per domain); merge if >70% Gold table overlap
- Naming: `get_{domain}_{metric}` for TVFs, `{domain}_analytics_metrics` for Metric Views

## SQL Query Standards

**ALWAYS use Gold layer tables, NEVER system tables directly.** Reference pattern: `${catalog}.${gold_schema}.table_name`

- Date parameters: `STRING` type (Genie compatible), cast at query time: `CAST(start_date AS DATE)`
- SCD Type 2 joins: `LEFT JOIN dim_{entity} d ON f.{entity}_id = d.{entity}_id AND d.is_current = TRUE`

## Documentation Quality Standards

**LLM-Friendly Comments** — All artifacts must include: what it does, when to use it, example questions it answers. Pattern: `COMMENT 'LLM: Returns top N {metric}... Example questions: "What are the top 10...?"'`

**Summary Tables** — Every addendum must include: overview table (all artifacts with domain, dependencies, status), by-domain sections, count summary, and success criteria.

## Common Mistakes to Avoid

| Mistake | Correct Approach |
|---------|-----------------|
| Querying `system.*` tables directly | Always use Gold layer: `${catalog}.${gold_schema}.fact_*` |
| Omitting Agent Domain on artifacts | Every artifact must be tagged: `## {Domain}: get_{metric}` |
| Adding a TVF without cross-addendum check | Also consider: Metric View counterpart? Alert? Dashboard? |
| Using `DATE` type in TVF parameters | Use `STRING COMMENT 'Format: YYYY-MM-DD'` (Genie compatible) |
| Deploying agents before Genie Spaces | Genie Spaces MUST be deployed first — agents consume them |
| Genie Space with 25+ assets | Split by domain cohesion; each space 10-25 assets |
| One Genie Space per domain when assets are thin | Consolidate thin domains (<10 assets) into fewer spaces |
| TVF that duplicates a Metric View | TVFs only when multi-period/multi-table parameterized logic is needed |
| Forcing a fixed domain count | Let business questions determine domains — 2-3 focused > 5-6 thin |

## Reference Files

- **[Phase Details](references/phase-details.md)** — Full phase and addendum descriptions with deliverables
- **[Estimation Guide](references/estimation-guide.md)** — Effort estimation, dependency management, risks
- **[Agent Layer Architecture](references/agent-layer-architecture.md)** — Detailed architecture, "Why Genie Spaces" comparison, design patterns, testing strategy, multi-agent query example
- **[Industry Domain Patterns](references/industry-domain-patterns.md)** — Domain templates for Hospitality, Retail, Healthcare, Finance, SaaS, and Databricks System Tables
- **[Worked Example: Wanderbricks](references/worked-example-wanderbricks.md)** — Complete 101-artifact project example with TVF SQL, Metric View YAML, Alert YAML
- **[Manifest Generation Guide](references/manifest-generation-guide.md)** — Plan-as-contract pattern: how to generate YAML manifests for downstream orchestrators

## Assets

### Plan Templates
- **[Project Plan Template](assets/templates/project-plan-template.md)** — Generic phase template with SQL standards
- **[Prerequisites Template](assets/templates/prerequisites-template.md)** — Data layer summary (Bronze/Silver/Gold)
- **[Use Case Catalog Template](assets/templates/use-case-catalog-template.md)** — Consolidated use case definitions with business questions
- **[Phase 1 Use Cases Template](assets/templates/phase1-use-cases-template.md)** — Master analytics artifacts
- **[Phase 1 TVFs Template](assets/templates/phase1-tvfs-template.md)** — Table-Valued Functions addendum
- **[Phase 1 Alerting Template](assets/templates/phase1-alerting-template.md)** — Alerting framework addendum
- **[Phase 1 Genie Spaces Template](assets/templates/phase1-genie-spaces-template.md)** — Genie Spaces addendum with Agent readiness
- **[Phase 2 Agent Framework Template](assets/templates/phase2-agent-framework-template.md)** — AI agents with Genie integration
- **[Phase 3 Frontend Template](assets/templates/phase3-frontend-template.md)** — User interface
- **[Plans README Template](assets/templates/plans-readme-template.md)** — plans/ folder index

### Manifest Templates (Plan-as-Contract)
- **[Semantic Layer Manifest](assets/templates/manifests/semantic-layer-manifest.yaml)** — TVFs, Metric Views, Genie Spaces contract
- **[Observability Manifest](assets/templates/manifests/observability-manifest.yaml)** — Monitors, Dashboards, Alerts contract
- **[ML Manifest](assets/templates/manifests/ml-manifest.yaml)** — Feature Tables, Models, Experiments contract
- **[GenAI Agents Manifest](assets/templates/manifests/genai-agents-manifest.yaml)** — Agents, Tools, Eval Datasets contract

## Validation Checklist

### Structure
- [ ] Follows standard template
- [ ] Has Overview with Status, Dependencies, Effort
- [ ] Organized by Agent Domain
- [ ] Includes code examples
- [ ] Has Success Criteria table
- [ ] Has References section

### Content Quality
- [ ] All queries use Gold layer tables (not system tables)
- [ ] All artifacts tagged with Agent Domain
- [ ] LLM-friendly comments on all artifacts
- [ ] Examples use `${catalog}.${gold_schema}` variables
- [ ] Summary tables are accurate and complete

### Cross-References
- [ ] Main phase document links to addendums
- [ ] Addendums link back to main phase
- [ ] Related artifacts cross-reference each other
- [ ] Dependencies are documented

### Use Case Traceability
- [ ] Use case catalog exists with one entry per distinct business problem
- [ ] Every use case includes 3-5 business questions in natural language
- [ ] Every business question from domain sections maps to at least one use case
- [ ] Every artifact in addendum summaries traces back to at least one use case question
- [ ] Use case catalog cross-references addendum documents

### Completeness
- [ ] Domains derived from business questions (not forced to a fixed count)
- [ ] Every TVF traces to a business question that Metric Views cannot answer
- [ ] Every Metric View covers a distinct analytical grain (no duplicates)
- [ ] Key business questions documented per domain (≥3 per domain)
- [ ] All Phase 1 addendums included
- [ ] User requirements addressed
- [ ] Reference patterns incorporated

### Rationalization (Prevent Bloat)
- [ ] Each Genie Space has ≤ 25 data assets
- [ ] No Genie Space has < 10 assets (merge thin spaces)
- [ ] Genie Space count justified by asset volume (not just domain count)
- [ ] No TVF duplicates a Metric View query
- [ ] No domain has < 3 distinct business questions (merge small domains)
- [ ] Domains with >70% Gold table overlap are consolidated

### Agent Layer Architecture (If Phase 2 Included)
- [ ] Agent-to-Genie Space mapping documented (1:1 recommended)
- [ ] Deployment order specified (Genie Spaces before Agents)
- [ ] Three-level testing strategy defined
- [ ] Orchestrator agent included for multi-domain coordination
- [ ] Genie Space instructions documented (become agent system prompts)
- [ ] Agent tool definitions reference Genie Spaces (not direct SQL)

## Key Learnings

1. **Agent Domain framework** provides consistent organization across all artifacts — every artifact gets a domain tag
2. **Gold layer references only** — never query `system.*` tables directly; use `${catalog}.${gold_schema}.*`
3. **Cross-addendum updates** — user requirements span multiple addendums; update all affected documents
4. **LLM-friendly comments** are critical for Genie/AI/BI integration — include example questions
5. **Agents use Genie Spaces as abstraction** — agents don't write SQL; Genie handles NL-to-SQL translation, optimization, and guardrails
6. **1:1 Agent-to-Genie mapping** recommended; Orchestrator agent uses Unified Genie Space for intent classification
7. **Deploy Genie Spaces before agents** — three-level testing: assets → Genie → Agents
8. **Genie Space 25-asset hard limit** — plan space count from total asset volume, not domain count; fewer focused spaces > many thin ones
9. **Rationalize before creating** — every artifact must trace to a business question; TVFs only when Metric Views can't answer
10. **Domains emerge from data** — business questions and Gold table groupings determine natural domain boundaries

## References

### Official Documentation
- [Databricks Docs](https://docs.databricks.com/)
- [Unity Catalog](https://docs.databricks.com/unity-catalog/)
- [Delta Live Tables](https://docs.databricks.com/dlt/)
- [Lakehouse Monitoring](https://docs.databricks.com/lakehouse-monitoring/)
- [Metric Views](https://docs.databricks.com/metric-views/)
- [Genie Spaces](https://docs.databricks.com/genie/)
- [Model Serving](https://docs.databricks.com/machine-learning/model-serving/)
- [Foundation Models (DBRX)](https://docs.databricks.com/machine-learning/foundation-models/)
- [Databricks System Tables](https://docs.databricks.com/administration-guide/system-tables/)
- [SQL Alerts](https://docs.databricks.com/sql/user/alerts/)
- [Table-Valued Functions](https://docs.databricks.com/sql/language-manual/sql-ref-syntax-ddl-create-sql-function.html)

### Related Skills
- [databricks-table-valued-functions](../../semantic-layer/02-databricks-table-valued-functions/SKILL.md)
- [metric-views-patterns](../../semantic-layer/01-metric-views-patterns/SKILL.md)
- [lakehouse-monitoring-comprehensive](../../monitoring/01-lakehouse-monitoring-comprehensive/SKILL.md)
- [databricks-aibi-dashboards](../../monitoring/02-databricks-aibi-dashboards/SKILL.md)
- [genie-space-patterns](../../semantic-layer/03-genie-space-patterns/SKILL.md) — Genie Space setup for agents

### Agent Framework Technologies
- [LangChain](https://python.langchain.com/) | [LangGraph](https://langchain-ai.github.io/langgraph/)

## Pipeline Progression

**Previous stage:** `gold/01-gold-layer-setup` → Gold layer tables and merge scripts should be complete

**Next stage:** After completing the project plan for remaining phases, proceed to:
- **`semantic-layer/00-semantic-layer-setup`** — Build Metric Views, TVFs, and Genie Spaces on top of Gold

---

## Post-Completion: Skill Usage Summary (MANDATORY)

**After completing all phases of this orchestrator, output a Skill Usage Summary reflecting what you ACTUALLY did — not a pre-written summary.**

### What to Include

1. Every skill `SKILL.md` or `references/` file you read (via the Read tool), in the order you read them
2. Which phase you were in when you read it
3. Whether it was a **Common**, **Reference**, or **Template** file
4. A one-line description of what you specifically used it for in this session

### Format

| # | Phase | Skill / Reference Read | Type | What It Was Used For |
|---|-------|----------------------|------|---------------------|
| 1 | Phase N | `path/to/SKILL.md` | Common / Reference / Template | One-line description |

### Summary Footer

End with:
- **Totals:** X common skills, Y reference files, Z templates read across N phases
- **Manifests emitted:** List each manifest file generated and its artifact count
- **Skipped:** List any expected references or templates that you did NOT need to read, and why
- **Unplanned:** List any skills you read that were NOT listed in the dependency table (e.g., for troubleshooting, edge cases, or user-requested detours)
