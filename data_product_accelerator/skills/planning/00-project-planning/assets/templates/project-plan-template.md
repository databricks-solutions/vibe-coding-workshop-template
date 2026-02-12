# Phase X: {Phase Name}

## Overview

**Status:** 📋 Planned | 🚧 In Progress | ✅ Complete  
**Dependencies:** {List dependencies}  
**Effort Estimate:** {X weeks/days}  
**Owner:** {Name/Team}

## Objectives

- {Objective 1}
- {Objective 2}
- {Objective 3}

## Agent Domain Organization

All artifacts MUST be organized by Agent Domain:

| Domain | Icon | Focus Area |
|--------|------|------------|
| {Domain 1} | {emoji} | {focus} |
| {Domain 2} | {emoji} | {focus} |
| {Domain 3} | {emoji} | {focus} |
| {Domain 4} | {emoji} | {focus} |
| {Domain 5} | {emoji} | {focus} |

## Artifacts by Domain

### {Domain 1}

#### {Artifact Name}

**Type:** {TVF | Metric View | Dashboard | Alert | ML Model | Monitor | Genie Space}  
**Gold Tables:** `fact_{entity}`, `dim_{entity}`  
**Business Questions:** "{Question}"  
**Dependencies:** {List dependencies}  
**Status:** 📋 Planned | 🚧 In Progress | ✅ Complete

**Description:**
{Detailed description of what this artifact does}

**Example:**
```sql
-- For TVFs, Metric Views, Alerts
SELECT ...
FROM ${catalog}.${gold_schema}.fact_{entity}
WHERE ...
```

**LLM-Friendly Comment:**
```sql
COMMENT 'LLM: {Description of what it does, when to use it, example questions}'
```

---

### {Domain 2}

{Repeat structure for each domain}

---

## Summary Table

| Artifact | Type | Domain | Gold Tables | Status | Dependencies |
|----------|------|--------|-------------|--------|---------------|
| {Name} | TVF | {Domain} | `fact_{entity}` | ✅ Complete | Gold layer |
| {Name} | Metric View | {Domain} | `fact_{entity}` | 🚧 In Progress | Gold layer |

## Artifact Count Summary

| Domain | TVFs | Metric Views | Dashboards | Alerts | ML Models | Monitors | Genie Spaces |
|--------|------|--------------|------------|--------|-----------|----------|-------------|
| {Domain 1} | X | X | X | X | X | X | X |
| {Domain 2} | X | X | X | X | X | X | X |
| {Domain 3} | X | X | X | X | X | X | X |
| {Domain 4} | X | X | X | X | X | X | X |
| {Domain 5} | X | X | X | X | X | X | X |
| **Total** | X | X | X | X | X | X | X |

## Success Criteria

| Criterion | Target | Status |
|-----------|--------|--------|
| All domains covered | {n} domains | ✅ |
| Minimum artifact counts | {See standards} | 🚧 |
| Gold layer references | 100% | ✅ |
| LLM-friendly comments | 100% | ✅ |
| Testing complete | All artifacts | 🚧 |

## SQL Query Standards

### Gold Layer Reference Pattern

**ALWAYS use Gold layer tables, NEVER system tables directly.**

```sql
-- ❌ WRONG: Direct system table reference
FROM system.billing.usage

-- ✅ CORRECT: Gold layer reference with variables
FROM ${catalog}.${gold_schema}.fact_{entity}
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

### LLM-Friendly Comments

All artifacts must have comments that help LLMs (Genie, AI/BI) understand:

```sql
COMMENT 'LLM: {Description}.
Use this for {use cases}.
Parameters: {parameter descriptions}.
Example questions: "{Question 1}" or "{Question 2}"'
```

## Artifact Naming Conventions

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

## Common Mistakes to Avoid

### Don't: Mix system tables and Gold tables

```sql
-- BAD: Direct system table
FROM system.{source}.{table} u
JOIN ${catalog}.${gold_schema}.dim_{entity} d ...
```

### Don't: Forget Agent Domain classification

```markdown
## get_{metric} (BAD - no domain)

## {Domain}: get_{metric} (GOOD)
```

### Don't: Create artifacts without cross-addendum updates

When adding a TVF, also consider:
- Does it need a Metric View counterpart?
- Should there be an Alert?
- Is it Dashboard-worthy?

### Don't: Use DATE parameters in TVFs (Genie incompatible)

```sql
-- BAD
start_date DATE

-- GOOD
start_date STRING COMMENT 'Format: YYYY-MM-DD'
```

## References

- Related skills: See `data_product_accelerator/skills/` directory
- Official Documentation: https://docs.databricks.com/

## Notes

{Any additional notes, learnings, or considerations}
