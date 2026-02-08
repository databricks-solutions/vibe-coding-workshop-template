# Phase 1 Addendum 1.6: Genie Spaces

## Overview

**Status:** {status}
**Dependencies:** Prerequisites (Gold Layer), 1.2 (TVFs), 1.3 (Metric Views), 1.1 (ML Models)
**Artifact Count:** {n} Genie Spaces ({n-1} domain-specific + 1 unified)

---

## Critical: Agent Integration Readiness

⚠️ **Genie Spaces serve as the natural language query interface for Phase 2 AI Agents.**

Each Genie Space will become a "tool" for its corresponding AI agent:
- Genie Space `instructions` → Agent system prompt
- Genie Space data assets → Agent query capabilities
- Genie Space benchmark questions → Agent testing framework

---

## Genie Space Summary

| Domain | Icon | Genie Space Name | Agent Integration |
|--------|------|------------------|-------------------|
| {Domain 1} | {emoji} | {Domain 1} Intelligence | → {Domain 1} Agent tool |
| {Domain 2} | {emoji} | {Domain 2} Intelligence | → {Domain 2} Agent tool |
| Unified | 🌐 | {Project} Monitor | → Orchestrator Agent tool |

---

## {Domain 1} Intelligence Genie Space

### A. Space Name
`{Domain 1} Intelligence`

### B. Description (2-3 sentences)
{Description optimized for LLM understanding. Include primary use cases.}

### C. Sample Questions (5-7 examples)
1. {Question 1}
2. {Question 2}
3. {Question 3}
4. {Question 4}
5. {Question 5}

### D. Data Assets

**Priority Order:** Metric Views → TVFs → ML Prediction Tables → Gold Tables

| Type | Asset | Purpose |
|------|-------|---------|
| Metric View | `{domain}_analytics_metrics` | Broad aggregations |
| TVF | `get_{metric}_by_{dimension}` | Parameterized queries |
| ML Model | `{model}_predictions` | ML-enhanced insights |
| Gold Table | `fact_{entity}` | Direct access (rare) |

### E. General Instructions (≤20 lines)
```
You are {Domain 1} Intelligence, helping users analyze {domain focus}.

DATA ASSET SELECTION:
- Use Metric Views for: {use cases}
- Use TVFs for: {use cases}
- Use ML tables for: {use cases}

QUERY PATTERNS:
- Always use MEASURE() syntax for Metric View aggregations
- TVF parameters use STRING dates (YYYY-MM-DD format)
- Use 3-part namespace: catalog.schema.table

{Additional domain-specific rules}
```

### F. TVF Syntax Guidance
```sql
-- {Domain 1} TVFs require STRING date parameters
SELECT * FROM TABLE(get_{metric}_by_{dimension}('2024-01-01', '2024-12-31'))
```

### G. Benchmark Questions with Exact SQL
1. **{Question 1}**
   ```sql
   SELECT ... FROM TABLE(get_{metric}_by_{dimension}(...))
   ```

2. **{Question 2}**
   ```sql
   SELECT MEASURE(`{measure}`) FROM {metric_view} WHERE ...
   ```

---

## Agent Readiness Validation

After deployment, validate each Genie Space is ready for agent integration:

- [ ] All benchmark questions return correct results
- [ ] Query latency < 10 seconds for typical queries
- [ ] >80% accuracy on domain-specific natural language questions
- [ ] Instructions are concise (≤20 lines) and clear for LLM
- [ ] All data assets are accessible and queryable

---

## Implementation Checklist

### {Domain 1} Intelligence
- [ ] Create Genie Space in Databricks workspace
- [ ] Configure data assets (prioritize Metric Views)
- [ ] Write general instructions (≤20 lines)
- [ ] Add benchmark questions with working SQL
- [ ] Test natural language queries
- [ ] Validate for Phase 2 agent integration

### Unified {Project} Monitor
- [ ] Create unified Genie Space
- [ ] Include all domain data assets
- [ ] Write multi-domain routing instructions
- [ ] Test cross-domain queries
- [ ] Prepare for Orchestrator Agent
