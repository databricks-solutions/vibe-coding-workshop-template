# TVF Requirements Template

Fill in this template BEFORE creating any TVFs. This ensures business alignment and prevents unnecessary rework.

---

## Project Context

| Field | Value |
|---|---|
| **Project Name** | _________________ (e.g., retail_analytics, patient_outcomes) |
| **Gold Catalog.Schema** | _________________ (e.g., my_catalog.my_project_gold) |
| **Primary Fact Table** | _________________ (e.g., fact_sales_daily, fact_encounters) |
| **Key Dimensions** | _________________ (e.g., store, product, date) |
| **Target TVF Count** | _________________ (recommended: 10-15) |
| **Time Estimate** | _________________ (2-3 hours for 10-15 TVFs) |

---

## Gold Layer Tables Available

| Table Name | Type | Primary Use | SCD Type |
|---|---|---|---|
| _________________ | Dimension | _________________ | Type 1 / Type 2 |
| _________________ | Dimension | _________________ | Type 1 / Type 2 |
| _________________ | Fact | _________________ | N/A |
| _________________ | Dimension | _________________ | Type 1 / Type 2 |
| _________________ | Fact | _________________ | N/A |

---

## Key Measures to Include

| Measure Name | Aggregation | Source Column | Description |
|---|---|---|---|
| total_revenue | SUM(net_revenue) | fact_table.net_revenue | Total sales revenue |
| _________________ | _________________ | _________________ | _________________ |
| _________________ | _________________ | _________________ | _________________ |
| _________________ | _________________ | _________________ | _________________ |
| _________________ | _________________ | _________________ | _________________ |

---

## Common Business Questions (10-15)

List the questions your users frequently ask, then map each to a TVF:

| # | Business Question | TVF Name | Parameters Needed | Pattern |
|---|---|---|---|---|
| 1 | "What are the top 10 _____ by _____?" | get_top_{entity}_by_{metric} | start_date, end_date, top_n | Top N Ranking |
| 2 | "How did _____ X perform last _____?" | get_{entity}_performance | {entity}_id, start_date, end_date | Entity Drilldown |
| 3 | "Show me _____ by _____" | get_{metric}_by_{dimension} | start_date, end_date | Geographic/Category |
| 4 | "Show me daily _____ trend" | get_daily_{metric}_trend | start_date, end_date | Temporal Trend |
| 5 | _________________ | _________________ | _________________ | _________________ |
| 6 | _________________ | _________________ | _________________ | _________________ |
| 7 | _________________ | _________________ | _________________ | _________________ |
| 8 | _________________ | _________________ | _________________ | _________________ |
| 9 | _________________ | _________________ | _________________ | _________________ |
| 10 | _________________ | _________________ | _________________ | _________________ |
| 11 | _________________ | _________________ | _________________ | _________________ |
| 12 | _________________ | _________________ | _________________ | _________________ |
| 13 | _________________ | _________________ | _________________ | _________________ |
| 14 | _________________ | _________________ | _________________ | _________________ |
| 15 | _________________ | _________________ | _________________ | _________________ |

---

## Input Required Summary

Before starting TVF development, verify you have:

- [ ] Gold layer tables (dimensions and facts) deployed and populated
- [ ] Common business questions collected from stakeholders (10-15 questions)
- [ ] Date range requirements defined (reporting periods)
- [ ] Top N requirements defined (rankings, leaderboards)
- [ ] YAML schema files consulted for actual column names (Rule #0)
- [ ] SCD type identified for each dimension (Type 1 vs Type 2)

---

## Output Deliverables

| Deliverable | File Path | Description |
|---|---|---|
| TVF SQL File | `src/{project}_gold/table_valued_functions.sql` | 10-15 TVF definitions |
| TVF Job YAML | `resources/gold/tvf_job.yml` | Asset Bundle job for deployment |
| Schema Mapping | `SCHEMA_MAPPING.md` (optional) | Column reference documentation |

---

## Cross-Reference Planning

Plan which TVFs should redirect to each other via NOT FOR / PREFERRED OVER comments:

| TVF Name | NOT FOR (redirect to) | Reason |
|---|---|---|
| get_top_stores_by_revenue | Individual store detail → get_store_performance | Different granularity |
| get_store_performance | Multi-store comparison → get_top_stores_by_revenue | Different scope |
| _________________ | _________________ | _________________ |
| _________________ | _________________ | _________________ |
