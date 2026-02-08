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

### Phase 2: Plan Document Generation

Create plan documents using templates in the following order:

1. **README** — `assets/templates/plans-readme-template.md` (plan index)
2. **Prerequisites** — `assets/templates/prerequisites-template.md` (data layer summary)
3. **Phase 1 Master** — `assets/templates/phase1-use-cases-template.md` (analytics artifacts)
4. **Addendums** (selected in Phase 1):
   - TVFs — `assets/templates/phase1-tvfs-template.md`
   - Alerting — `assets/templates/phase1-alerting-template.md`
   - Genie Spaces — `assets/templates/phase1-genie-spaces-template.md`
5. **Phase 2** — `assets/templates/phase2-agent-framework-template.md` (AI agents)
6. **Phase 3** — `assets/templates/phase3-frontend-template.md` (user interface)

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
4. Validate all table/column references exist in Gold YAML
5. Verify summary counts match actual artifact counts
6. Commit manifests alongside plan documents

**Key principle:** Every artifact in a manifest MUST trace back to (a) a Gold layer table and (b) a business question from the plan addendum.

**Output Structure:**
```
plans/
├── manifests/
│   ├── semantic-layer-manifest.yaml    # → consumed by semantic-layer/00-*
│   ├── observability-manifest.yaml     # → consumed by monitoring/00-*
│   ├── ml-manifest.yaml                # → consumed by ml/00-*
│   └── genai-agents-manifest.yaml      # → consumed by genai-agents/00-*
```

**Downstream consumption:** Each downstream orchestrator (stages 6-9) has a **Phase 0: Read Plan** step that reads its manifest. If the manifest doesn't exist (e.g., user skipped Planning), the orchestrator falls back to self-discovery from Gold tables.

---

## Plan Structure Framework

### Standard Project Phases

```
plans/
├── README.md                              # Index and overview
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

### Core Principle: Business Problems First, Not Artifact Counts

**Every artifact must trace to a specific business question that justifies its existence.** Do not create TVFs, Metric Views, or Genie Spaces to fill a quota. Create them because a stakeholder needs an answer that cannot be obtained any other way.

### Genie Space Capacity Planning

**Hard constraint: Each Genie Space supports up to 25 data assets** (tables, views, metric views, and functions combined).

```
Step 1: Count your queryable assets
  total_assets = Gold_tables + Metric_Views + TVFs + ML_prediction_tables

Step 2: Determine Genie Space count
  IF total_assets ≤ 25  → 1 unified Genie Space (no domain split needed)
  IF total_assets ≤ 50  → 2-3 spaces (group related domains)
  IF total_assets > 50  → consider domain-specific spaces (but rarely > 4-5)

Step 3: Validate each space
  - Each space should have 10-25 assets (under 10 = too thin, consider merging)
  - Assets within a space should be semantically cohesive
  - Genie's NL-to-SQL quality DEGRADES with too many unrelated assets
```

**Decision matrix:**

| Total Queryable Assets | Recommended Spaces | Rationale |
|------------------------|-------------------|-----------|
| ≤ 15 | 1 unified | All assets fit comfortably; Genie context stays focused |
| 16-25 | 1-2 | One may suffice; split only if domains are truly distinct |
| 26-50 | 2-3 | Group related domains; keep each space ≤ 25 |
| 51-75 | 3-4 | Domain-specific; ensure each space has ≥ 10 assets |
| 75+ | 4-6 max | Large projects only; more spaces = more maintenance |

### TVF Rationalization

**Create a TVF only when ALL of these are true:**

1. A business question requires **parameterized filtering** (date ranges, entity filters)
2. The answer requires **multi-table joins or aggregations** beyond a simple `WHERE` clause
3. The same query pattern is needed **repeatedly** (not a one-off analysis)
4. The question **cannot be answered** by a Metric View query alone

**Do NOT create a TVF when:**
- A direct `SELECT` from a Gold table with a `WHERE` clause suffices
- A Metric View already answers the question (use `MEASURE()` syntax instead)
- The TVF would duplicate a Metric View's measures with different filters
- The TVF serves only one dashboard widget and nothing else

**Right-sizing guide:**

| Gold Table Count | Typical TVF Count | Reasoning |
|-----------------|-------------------|-----------|
| 5-10 tables | 5-15 TVFs | ~1-2 TVFs per table for parameterized access |
| 11-20 tables | 10-25 TVFs | Complex joins justify more functions |
| 20+ tables | 15-35 TVFs | Large models; audit for duplication regularly |

### Metric View Rationalization

**One metric view per distinct analytical grain**, not per domain:

- If two domains share the same fact table → one metric view with dimensions for both
- A metric view with only 1-2 measures is rarely justified — fold into a broader view
- Metric Views with joins should cover a full analytical perspective (e.g., "bookings with destination and property details"), not narrow slices

**Right-sizing guide:**

| Fact Table Count | Typical Metric Views | Reasoning |
|-----------------|---------------------|-----------|
| 1-3 facts | 1-3 views | One per fact, with dimension joins |
| 4-6 facts | 3-5 views | Some facts may share a view if similar grain |
| 7+ facts | 4-8 views | Consolidate where grains align |

### Domain Rationalization

**Domains emerge from business problems, not arbitrary counts.**

- Start by listing business questions stakeholders actually ask
- Group questions by the Gold tables they touch
- If two "domains" share >70% of their Gold tables → merge them
- If a "domain" has fewer than 3 distinct business questions → merge it into a neighbor
- Consider Genie Space limits: each domain implies a potential Genie Space

**Practical domain count:**

| Gold Table Count | Typical Domains | Reasoning |
|-----------------|----------------|-----------|
| 5-10 tables | 2-3 domains | Small models don't need 5+ domains |
| 11-20 tables | 3-4 domains | Natural groupings emerge from star schema |
| 20+ tables | 4-6 domains | Large models may justify more, but audit overlap |

### Artifact Naming Conventions

| Artifact | Pattern | Example |
|----------|---------|---------|
| TVF | `get_{domain}_{metric}` | `get_{domain}_by_{dimension}` |
| Metric View | `{domain}_analytics_metrics` | `{domain}_analytics_metrics` |
| Dashboard | `{Domain} {Purpose} Dashboard` | `{Domain} Performance Dashboard` |
| Alert | `{DOMAIN}-NNN-SEVERITY` | `{DOM}-001-CRIT` |
| ML Model | `{Purpose} {Type}` | `{Metric} Forecaster` |
| Monitor | `{table} Monitor` | `{Domain} Data Quality Monitor` |
| Genie Space | `{Domain} {Purpose}` | `{Domain} Intelligence` |
| AI Agent | `{Domain} Agent` | `{Domain} Agent` |

## SQL Query Standards

### Gold Layer Reference Pattern

**ALWAYS use Gold layer tables, NEVER system tables directly.**

```sql
-- WRONG: Direct system table reference
FROM system.billing.usage

-- CORRECT: Gold layer reference with variables
FROM ${catalog}.${gold_schema}.fact_usage
```

### Standard Variable References

```sql
-- Catalog and schema (from parameters)
${catalog}.${gold_schema}.table_name

-- Date parameters (STRING type for Genie compatibility)
WHERE usage_date BETWEEN CAST(start_date AS DATE) AND CAST(end_date AS DATE)

-- SCD Type 2 dimension joins
LEFT JOIN dim_{entity} d 
    ON f.{entity}_id = d.{entity}_id 
    AND d.is_current = TRUE
```

## Documentation Quality Standards

### LLM-Friendly Comments

All artifacts must have comments that help LLMs (Genie, AI/BI) understand:
- What the artifact does
- When to use it
- Example questions it answers

```sql
COMMENT 'LLM: Returns top N {metric} contributors by {dimension} for a date range.
Use this for {use_case_1}, {use_case_2}, and identifying {insight_type}.
Parameters: start_date, end_date (YYYY-MM-DD format), optional top_n (default 10).
Example questions: "What are the top 10 {metric} drivers?" or "Which {dimension} had most {metric}?"'
```

### Summary Tables

Every addendum must include:
1. **Overview table** — All artifacts with agent domain, dependencies, status
2. **By-domain sections** — Artifacts grouped by agent domain
3. **Count summary** — Total artifacts by type and domain
4. **Success criteria** — Measurable targets

## Common Mistakes to Avoid

### DON'T: Mix system tables and Gold tables

```sql
-- BAD: Direct system table
FROM system.billing.usage u
JOIN ${catalog}.${gold_schema}.dim_workspace w ...
```

### DON'T: Forget Agent Domain classification

```markdown
## get_slow_queries (BAD - no domain)

## {Domain}: get_slow_queries (GOOD)
```

### DON'T: Create artifacts without cross-addendum updates

When adding a TVF, also consider:
- Does it need a Metric View counterpart?
- Should there be an Alert?
- Is it Dashboard-worthy?

### DON'T: Use DATE parameters in TVFs (Genie incompatible)

```sql
-- BAD
start_date DATE

-- GOOD
start_date STRING COMMENT 'Format: YYYY-MM-DD'
```

### DON'T: Deploy agents before Genie Spaces

**Genie Spaces MUST be deployed BEFORE agents can use them.**

### DON'T: Create Genie Spaces that exceed the 25-asset limit

```
# BAD: Stuffing 30+ assets degrades NL-to-SQL quality
Genie Space with 15 Gold tables + 20 TVFs + 5 Metric Views = 40 assets ❌

# GOOD: Split by domain cohesion, keep each under 25
Space A: 8 tables + 10 TVFs + 2 MVs = 20 assets ✅
Space B: 7 tables + 10 TVFs + 3 MVs = 20 assets ✅
```

### DON'T: Create one Genie Space per domain when assets are thin

```
# BAD: 5 Genie Spaces with 4 assets each = wasted maintenance
Domain A Space: 2 tables + 1 TVF + 1 MV = 4 assets ❌ (too thin)

# GOOD: Consolidate thin domains into fewer spaces
Combined Space: 10 tables + 5 TVFs + 3 MVs = 18 assets ✅
```

### DON'T: Create TVFs that duplicate Metric View capabilities

```sql
-- BAD: TVF that just wraps what a Metric View already does
CREATE FUNCTION get_total_bookings(start_date STRING, end_date STRING)
-- When a Metric View already has: MEASURE(total_bookings) with date dimension

-- GOOD: TVF adds value Metric Views can't provide
CREATE FUNCTION get_booking_comparison(period_a_start STRING, period_a_end STRING,
                                       period_b_start STRING, period_b_end STRING)
-- Multi-period comparison requires parameterized logic beyond MEASURE()
```

### DON'T: Force a fixed domain count

```
# BAD: "We need 5 domains" → inventing domains to fill quota
Domain 1: Revenue ✅ (real need)
Domain 2: Operations ✅ (real need)  
Domain 3: "Miscellaneous" ❌ (forced)

# GOOD: Let business questions determine domains naturally
2-3 well-defined domains > 5-6 poorly-defined ones
```

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

1. Agent Domain framework provides consistent organization across all artifacts
2. Gold layer references (not system tables) ensure consistency
3. User requirements often span multiple addendums — update all
4. Dashboard JSON files are rich sources of SQL patterns
5. LLM-friendly comments are critical for Genie/AI/BI integration
6. Summary tables help maintain accuracy across large plans
7. Planning starts after data layers are complete — focus on consumption artifacts
8. Agents should NOT write SQL directly — use Genie Spaces as abstraction
9. Genie Spaces provide natural language understanding that agents leverage
10. Each specialized agent has a dedicated Genie Space (1:1 mapping)
11. Orchestrator agent uses Unified Genie Space for intent classification
12. Genie Spaces must be deployed BEFORE agents can be developed
13. Multi-agent workflows require correlation and synthesis in Orchestrator
14. Three-level testing ensures each layer works before next is built
15. General Instructions in Genie Spaces become agent system prompts
16. Abstraction Layer: Agents don't need SQL syntax or schema knowledge
17. Schema Evolution: Data model changes don't break agent implementations
18. Query Optimization: Genie Spaces handle SQL optimization automatically
19. Guardrails: Genie Spaces provide built-in query safety checks
20. Testing Framework: Benchmark questions test both Genie and Agent accuracy
21. System prompt derivation from Genie Space instructions keeps prompts concise (≤20 lines)
22. Three agent-Genie design patterns: 1:1 Mapping, Orchestrator+Unified, Hierarchical
23. Genie Spaces have a 25-asset hard limit — plan space count from total asset volume, not domain count
24. TVFs should only exist when Metric Views cannot answer the business question
25. Domains emerge from business questions and Gold table groupings, not arbitrary counts
26. Fewer well-focused Genie Spaces outperform many thin ones — Genie NL quality degrades with too many unrelated assets
27. Rationalize before creating: count assets first, then decide space boundaries

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
- [databricks-table-valued-functions](skills/semantic-layer/databricks-table-valued-functions/SKILL.md)
- [metric-views-patterns](skills/semantic-layer/metric-views-patterns/SKILL.md)
- [lakehouse-monitoring-comprehensive](skills/monitoring/01-lakehouse-monitoring-comprehensive/SKILL.md)
- [databricks-aibi-dashboards](skills/monitoring/02-databricks-aibi-dashboards/SKILL.md)
- [genie-space-patterns](skills/semantic-layer/genie-space-patterns/SKILL.md) — Genie Space setup for agents

### Agent Framework Technologies
- [LangChain](https://python.langchain.com/) — Agent framework
- [LangGraph](https://langchain-ai.github.io/langgraph/) — Multi-agent workflows

---

## Pipeline Progression

**Previous stage:** `gold/01-gold-layer-setup` → Gold layer tables and merge scripts should be complete

**Next stage:** After completing the project plan for remaining phases, proceed to:
- **`semantic-layer/00-semantic-layer-setup`** — Build Metric Views, TVFs, and Genie Spaces on top of Gold
