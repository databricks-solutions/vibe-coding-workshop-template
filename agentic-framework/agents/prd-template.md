# PRD Template for Agentic Applications on Databricks

> **How to use this template**: Copy this file to your new project as `docs/design_prd.md` and fill in each section for your business problem. The subagents in `.cursor/agents/` are designed to read this format. Sections marked with which subagent consumes them help you understand why each section matters.
>
> Delete all instructional comments (lines starting with `>`) before finalizing.

---

# Product Requirements Document: [Product Name] - [Short Description]

**Document Version**: 1.0
**Last Updated**: [Date]
**Status**: Draft

---

## 1. Summary

### 1.1 Product Vision

> *Write 2-3 sentences describing what this product does and why it exists.*
> *Consumed by: prd-analyzer (to understand the domain), skill-scaffolder (to name skills appropriately)*

[Product Name] is a [type of application] that [what it does] for [who it serves], enabling [key value proposition].

### 1.2 Problem Statement

> *Describe the problem this product solves. Be specific about pain points.*
> *Consumed by: prd-analyzer (to identify capability gaps)*

[Describe the problem users face today and why existing solutions fall short.]

### 1.3 Target Personas

> *Define 1-3 user personas. Each persona helps the subagents understand what kinds of interactions the system must support.*
> *Consumed by: prd-analyzer (to map requirements), agent-tester (to generate realistic test scenarios)*

#### Persona 1: [Role Name]

**Profile**: [Age range, background, frequency of use, technical comfort level]

**Key Needs**:
- [Need 1]
- [Need 2]
- [Need 3]

#### Persona 2: [Role Name]

**Profile**: [Description]

**Key Needs**:
- [Need 1]
- [Need 2]

### 1.4 Goals

> *Define measurable success criteria. These become validation targets for the agent-tester.*
> *Consumed by: agent-tester (to define pass/fail criteria), prd-analyzer (to prioritize requirements)*

| Goal | Success Metric |
|------|----------------|
| [Goal 1] | [Measurable target] |
| [Goal 2] | [Measurable target] |
| [Goal 3] | [Measurable target] |

### 1.5 Non-Goals

> *Explicitly state what is OUT of scope. This prevents the subagents from generating unnecessary skills.*
> *Consumed by: prd-analyzer (to avoid over-scoping), skill-scaffolder (to know what NOT to build)*

- [Feature or capability that is explicitly excluded]
- [Another exclusion]

---

## 2. Databricks Services

> **IMPORTANT**: This section is unique to this template and critical for the subagents.
> It tells prd-analyzer which services are available and databricks-deployer what to configure.
> Only check services you plan to use. The subagents will skip unchecked services.
> *Consumed by: prd-analyzer, skill-scaffolder, databricks-deployer*

### 2.1 Available Services

Check the services this project will use:

- [ ] **Databricks Genie Space** -- For natural language queries over structured data
  - Genie Space ID: `[to be configured in env]`
  - SQL Warehouse ID: `[to be configured in env]`
  - Tables exposed: [list the tables/views Genie will query, or "TBD"]

- [ ] **Databricks LLM Endpoint (Foundation Model / External Model)** -- For text generation, classification, rewriting
  - Endpoint name: `[to be configured in env]`
  - Model: [e.g., DBRX, Llama, GPT-4, Claude, etc.]
  - Use cases: [query rewriting, summarization, classification, content generation, etc.]

- [ ] **MLflow Model Registry / Unity Catalog** -- For registering and versioning agent models
  - Catalog: `[catalog name]`
  - Schema: `[schema name]`

- [ ] **Databricks Model Serving** -- For deploying agent models as REST endpoints
  - Endpoint name: `[to be configured in env]`

- [ ] **Lakebase (PostgreSQL)** -- For application-level relational data
  - Database tables: [list tables or "see Section 6"]

- [ ] **Delta Lake / Unity Catalog Tables** -- For large-scale analytical data
  - Key tables: [list tables]

- [ ] **Web Search API** -- For external/real-time information
  - Provider: [SerpAPI / Bing / Google CSE / other]

- [ ] **Other services**: [list any additional Databricks or external services]

### 2.2 Authentication

> *How does the app authenticate with Databricks?*

- [ ] Personal Access Token (PAT)
- [ ] OAuth / Service Principal
- [ ] Managed Identity

---

## 3. Architecture Pattern

> *Select the primary pattern for your agentic application. This guides prd-analyzer in mapping
> requirements and skill-scaffolder in choosing skill patterns.*
> *Consumed by: prd-analyzer, skill-scaffolder*

Select the primary pattern(s) that describe your application:

- [ ] **Search Pipeline** -- User queries data, system returns ranked results (e.g., product search, document retrieval, knowledge base)
- [ ] **Conversational Agent** -- Multi-turn dialog with intent routing and context management (e.g., customer support, virtual assistant)
- [ ] **Event-Driven Workflow** -- System reacts to events/triggers and chains processing steps (e.g., order processing, incident response)
- [ ] **Data Pipeline / ETL** -- Ingests, transforms, validates, and outputs data (e.g., data quality, feature engineering)
- [ ] **Monitoring / Alerting** -- Observes metrics, detects anomalies, sends notifications (e.g., fraud detection, SLA monitoring)
- [ ] **Content Generation** -- Produces documents, reports, or recommendations from inputs (e.g., report builder, email generator)
- [ ] **Hybrid / Multi-Pattern** -- Describe: [which patterns and how they combine]

---

## 4. Scope

### 4.1 MVP Scope (In Scope)

> *Group features into logical categories. Each category often maps to one or more agent skills.*
> *Consumed by: prd-analyzer (to map capabilities), skill-scaffolder (to group skills)*

**[Category 1 Name]** (e.g., Search & Discovery, Data Ingestion, Alert Management)
- [Feature 1]
- [Feature 2]
- [Feature 3]

**[Category 2 Name]** (e.g., Processing, Booking, Content Generation)
- [Feature 1]
- [Feature 2]

**[Category 3 Name]** (e.g., Output, Notification, Reporting)
- [Feature 1]
- [Feature 2]

### 4.2 Out of Scope

- [Feature explicitly excluded from MVP]
- [Another exclusion]

---

## 5. User Journeys

> **CRITICAL SECTION**: The agent-tester generates ALL test scenarios from these journeys.
> Write at least 2-3 journeys covering different interaction types.
> Each journey should be a step-by-step table showing input, action, and expected outcome.
> *Consumed by: agent-tester (primary source for test scenarios), prd-analyzer (to map requirements to tools)*

### 5.1 Journey: [Descriptive Name]

**Scenario**: [Who is the user, what are they trying to accomplish, and what is the context?]

| Step | Action | Expected Outcome |
|------|--------|------------------|
| 1 | [What the user does] | [What the system should do/show] |
| 2 | [Next user action] | [System response] |
| 3 | [Continue...] | [System response] |

### 5.2 Journey: [Descriptive Name]

**Scenario**: [Different user, different goal, or different path through the system]

| Step | Action | Expected Outcome |
|------|--------|------------------|
| 1 | [Action] | [Outcome] |
| 2 | [Action] | [Outcome] |

### 5.3 Journey: [Edge Case or Error Scenario]

> *Include at least one journey that covers an error path, fallback, or edge case.*

**Scenario**: [What goes wrong or is unusual about this interaction?]

| Step | Action | Expected Outcome |
|------|--------|------------------|
| 1 | [Action] | [Outcome] |
| 2 | [Something fails or is ambiguous] | [How the system handles it gracefully] |

---

## 6. Functional Requirements

> *Each requirement should have a unique ID, a clear description, and acceptance criteria.*
> *The prd-analyzer maps each requirement to an agent capability and Databricks service.*
> *The agent-tester uses acceptance criteria to validate the implementation.*
> *Consumed by: prd-analyzer, agent-tester, skill-scaffolder*

### 6.1 [Category 1 Name]

#### FR-001: [Requirement Name]
The system shall [what it must do].

**Acceptance Criteria**:
- [Testable criterion 1]
- [Testable criterion 2]
- [Testable criterion 3]

#### FR-002: [Requirement Name]
The system shall [what it must do].

**Acceptance Criteria**:
- [Testable criterion 1]
- [Testable criterion 2]

### 6.2 [Category 2 Name]

#### FR-003: [Requirement Name]
The system shall [what it must do].

**Acceptance Criteria**:
- [Testable criterion 1]
- [Testable criterion 2]

> *Continue adding requirements for each category. Be thorough -- any requirement NOT listed here
> will not be picked up by the subagents.*

---

## 7. Data Entities

> *Define the core data objects your system works with. The prd-analyzer uses this to identify
> data sources, Genie Space tables, and database schemas.*
> *Consumed by: prd-analyzer (to map data sources), databricks-deployer (to configure data services)*

### 7.1 Core Entities

| Entity | Description | Key Relationships |
|--------|-------------|-------------------|
| **[Entity 1]** | [What this entity represents] | [How it relates to other entities] |
| **[Entity 2]** | [What this entity represents] | [How it relates to other entities] |
| **[Entity 3]** | [What this entity represents] | [How it relates to other entities] |

### 7.2 Entity Relationship Overview

> *Use a simple text diagram, Mermaid, or description to show how entities relate.*

```
[Entity A] (1) ── has many ──▶ (N) [Entity B]
                                      │
                                      ├── has ──▶ [Entity C]
                                      └── has ──▶ [Entity D]
```

---

## 8. Non-Functional Requirements

> *Performance, security, and reliability targets. The databricks-deployer uses these
> to configure endpoint scaling, and the agent-tester uses them for performance validation.*
> *Consumed by: databricks-deployer, agent-tester*

### 8.1 Performance

| Requirement | Target |
|-------------|--------|
| [Operation] response time | < [X] seconds |
| [Another operation] | < [X] seconds |
| Concurrent users | [target number] |

### 8.2 Security

- [Security requirement 1]
- [Security requirement 2]

### 8.3 Reliability

- Target [X]% uptime
- [Graceful degradation requirements]
- [Data backup requirements]

---

## 9. Agent Routing Hints

> **OPTIONAL but helpful**: If you know how queries or inputs should be routed between
> different agent tools, describe the routing logic here. This helps prd-analyzer and
> skill-scaffolder generate better routing/classification skills.
> *Consumed by: prd-analyzer, skill-scaffolder*

### 9.1 Input Classification

> *Describe the types of inputs the system receives and where they should be routed.*

| Input Type | Description | Route To |
|------------|-------------|----------|
| [Type 1] | [What this input looks like] | [Which capability handles it] |
| [Type 2] | [What this input looks like] | [Which capability handles it] |
| [Type 3] | [What this input looks like] | [Fallback when primary fails] |

### 9.2 Fallback Chain

> *What happens when the primary handler fails?*

1. Try [primary tool/service]
2. If that fails or returns no data, try [fallback 1]
3. If that also fails, [final fallback behavior]

---

## 10. Release Plan

> *Milestones help skill-scaffolder understand dependency ordering -- which skills to build first.*
> *Consumed by: skill-scaffolder (for build order)*

| Milestone | Target | Key Deliverables |
|-----------|--------|------------------|
| **M1: [Name]** | [Timeframe] | [What gets built] |
| **M2: [Name]** | [Timeframe] | [What gets built] |
| **M3: [Name]** | [Timeframe] | [What gets built] |

---

## Appendix A: Glossary

> *Define domain-specific terms. The subagents use these to generate correctly named skills and tests.*

| Term | Definition |
|------|------------|
| [Term 1] | [Definition] |
| [Term 2] | [Definition] |

---

## Appendix B: Open Questions

> *List unresolved decisions. The prd-analyzer will flag these as risks.*

1. [Open question 1]
2. [Open question 2]

---

*This document is intended for planning purposes and is subject to revision as requirements are refined.*
