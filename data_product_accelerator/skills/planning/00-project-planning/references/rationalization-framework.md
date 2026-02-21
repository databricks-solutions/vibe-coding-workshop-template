# Artifact Rationalization Framework

## Core Principle: Business Problems First, Not Artifact Counts

**Every artifact must trace to a specific business question that justifies its existence.** Do not create TVFs, Metric Views, or Genie Spaces to fill a quota. Create them because a stakeholder needs an answer that cannot be obtained any other way.

## Genie Space Capacity Planning

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

## TVF Rationalization

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

## Metric View Rationalization

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

## Domain Rationalization

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
