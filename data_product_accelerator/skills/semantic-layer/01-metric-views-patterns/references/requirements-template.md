# Metric View Requirements Template

Use this template to gather requirements before creating metric views. Fill in each section to define your metric view design.

## Project Context

| Field | Value |
|-------|-------|
| **Project Name** | _________________ (e.g., retail_analytics, patient_outcomes) |
| **Catalog** | _________________ (e.g., my_catalog) |
| **Gold Schema** | _________________ (e.g., my_project_gold) |
| **Primary Fact Table** | _________________ (e.g., fact_sales_daily, fact_encounters_daily) |

## Metric View Design

| Field | Value |
|-------|-------|
| **Metric View Name** | _________________ (e.g., sales_performance_metrics) |
| **Purpose** | _________________________________________________ (Brief description) |

---

## Dimensions to Include (5-10 dimensions)

| # | Dimension Name | Source | Type | Example Synonyms |
|---|---------------|--------|------|------------------|
| 1 | store_number | fact_table.store_number | Identifier | store id, location, shop |
| 2 | store_name | dim_store.store_name | Name | store, location name |
| 3 | city | dim_store.city | Geographic | store city, location |
| 4 | _____________ | _________________ | _______ | __________________ |
| 5 | _____________ | _________________ | _______ | __________________ |
| 6 | _____________ | _________________ | _______ | __________________ |
| 7 | _____________ | _________________ | _______ | __________________ |
| 8 | _____________ | _________________ | _______ | __________________ |

### Dimension Categories

Use these categories when classifying your dimensions:

- **Identifiers:** IDs, codes, keys (store_number, product_id, patient_mrn)
- **Names:** Display names (store_name, product_description, provider_name)
- **Geographic:** Locations (city, state, region, country)
- **Temporal:** Time attributes (year, quarter, month, weekday)
- **Categories:** Classifications (category, type, status, diagnosis)

---

## Measures to Include (5-10 measures)

| # | Measure Name | Expression | Format | Example Synonyms |
|---|-------------|-----------|--------|------------------|
| 1 | total_revenue | SUM(source.net_revenue) | Currency (USD) | revenue, sales, dollars |
| 2 | total_units | SUM(source.net_units) | Number | units, quantity, volume |
| 3 | transaction_count | SUM(source.transaction_count) | Number | transactions, orders, visits |
| 4 | _____________ | _________________ | _______ | __________________ |
| 5 | _____________ | _________________ | _______ | __________________ |
| 6 | _____________ | _________________ | _______ | __________________ |
| 7 | _____________ | _________________ | _______ | __________________ |
| 8 | _____________ | _________________ | _______ | __________________ |

### Measure Types

- **Currency:** Revenue, cost, amount (format: currency, USD)
- **Counts:** Transaction count, patient count, order count (format: number)
- **Quantities:** Units, volume, weight (format: number)
- **Rates:** Percentages, ratios (format: percentage)
- **Averages:** Avg transaction value, avg length of stay (format: currency or number)

---

## Dimension Joins (if needed)

| Join Alias | Source Table | Join Condition |
|-----------|--------------|----------------|
| dim_store | dim_store | source.store_number = dim_store.store_number AND dim_store.is_current = true |
| dim_product | dim_product | source.upc_code = dim_product.upc_code |
| __________ | ___________ | ______________________________________________ |
| __________ | ___________ | ______________________________________________ |

**Join Rules:**
- Each join must be **direct** from source table: `source.fk = dim.pk`
- **NOT transitive:** `dim1.fk = dim2.pk` is unsupported in v1.1
- SCD2 dimensions: Include `AND {dim}.is_current = true`
- All joins default to LEFT OUTER JOIN

---

## Common Business Questions

List questions users will ask (helps define synonyms and measure design):

1. "What is the total {measure} for {time period}?"
2. "Show me {measure} by {dimension}"
3. "What are the top {N} {entities} by {measure}?"
4. _________________________________________________
5. _________________________________________________
6. _________________________________________________

### Domain-Specific Examples

**Retail:**
- "What is the total revenue for last month?"
- "Show me sales by store"
- "What are the top 10 products by revenue?"
- "What is the return rate by brand?"
- "Average transaction value by city?"

**Healthcare:**
- "What is the patient count for this quarter?"
- "Show me readmissions by diagnosis"
- "What are the top 5 providers by patient volume?"
- "Average length of stay by department?"
- "What is the readmission rate by facility?"

**Finance:**
- "What is the transaction volume for last week?"
- "Show me amounts by account type"
- "Which merchants have the highest fraud rate?"
- "Average transaction amount by channel?"
- "What is the approval rate by product type?"

---

## Input Required Summary

Before starting metric view creation, verify you have:

- [ ] Gold layer fact tables exist (verified with `DESCRIBE TABLE`)
- [ ] Gold layer dimension tables exist (verified with `DESCRIBE TABLE`)
- [ ] Key business metrics and measures defined (with aggregation types)
- [ ] Common business questions listed (for synonym design)
- [ ] Column names verified against actual table schemas

**Output:** 2-3 Metric Views with semantic metadata, formatting, synonyms, and dimension joins.

**Time Estimate:** 2 hours for 2-3 metric views
