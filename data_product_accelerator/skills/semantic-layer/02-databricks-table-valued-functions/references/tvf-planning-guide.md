# TVF Planning Guide

Plan which TVFs to create by identifying common business questions, categorizing them, and mapping them to function signatures before writing any SQL.

## Step 1: Identify Common Business Questions

Collect 10-15 questions your users frequently ask. Categorize them into these standard groups:

### Revenue Questions
- "What are the top 10 stores by revenue?"
- "Show me sales for store X this month"
- "What's the revenue by product category?"

### Product Questions
- "What are the top 5 selling products?"
- "Show me sales for product category X"
- "Which products are underperforming?"

### Entity Questions (Store/Hospital/Account)
- "How is store X performing?"
- "Compare stores by state"
- "Which stores have declining sales?"

### Trend Questions
- "Show me daily sales trend"
- "What's the month-over-month growth?"
- "Weekend vs weekday sales"

---

## Step 2: Map Questions to TVF Signatures

Use this planning table to translate business questions into TVF definitions:

| Question Pattern | TVF Name | Parameters |
|---|---|---|
| Top N {entities} by {metric} | `get_top_{entities}_by_{metric}` | start_date, end_date, top_n |
| {Entity} performance details | `get_{entity}_performance` | {entity}_id, start_date, end_date |
| Top N {items} | `get_top_{items}` | start_date, end_date, top_n |
| {Metric} by {dimension} | `get_{metric}_by_{dimension}` | start_date, end_date |
| Daily {metric} trend | `get_daily_{metric}_trend` | start_date, end_date |
| {Dimension} comparison | `get_{metric}_by_{dimension}` | start_date, end_date |

### Standard Naming Patterns

| Pattern | Template | Example |
|---|---|---|
| **Top N** | `get_top_{entity}_by_{metric}(start_date, end_date, top_n)` | `get_top_stores_by_revenue(...)` |
| **Trending** | `get_{metric}_trend(start_date, end_date, granularity)` | `get_revenue_trend(...)` |
| **Comparison** | `get_{entity}_comparison(entity_list, start_date, end_date)` | `get_store_comparison(...)` |
| **Performance** | `get_{entity}_performance(entity_id, start_date, end_date)` | `get_store_performance(...)` |

---

## Step 3: Domain-Specific Examples

These show how the same patterns adapt across industries:

### Retail Domain

| Question | TVF Name | Parameters |
|---|---|---|
| "What are the top 10 stores by revenue?" | `get_top_stores_by_revenue` | start_date, end_date, top_n |
| "How did store 12345 perform last month?" | `get_store_performance` | store_number, start_date, end_date |
| "What are the top 5 selling products?" | `get_top_products` | start_date, end_date, top_n |
| "Compare sales by state" | `get_sales_by_state` | start_date, end_date |
| "Show me daily sales trend" | `get_daily_sales_trend` | start_date, end_date |

See `references/tvf-examples.md` for complete SQL implementations of all 5 retail TVFs.

### Healthcare Domain

| Question | TVF Name | Parameters |
|---|---|---|
| "What are the top hospitals by patient volume?" | `get_top_hospitals_by_volume` | start_date, end_date, top_n |
| "How is hospital X performing?" | `get_hospital_performance` | hospital_id, start_date, end_date |
| "Show me readmission rates by diagnosis" | `get_readmission_by_diagnosis` | start_date, end_date |
| "Compare patient outcomes by region" | `get_outcomes_by_region` | start_date, end_date |
| "Daily admissions trend" | `get_daily_admissions_trend` | start_date, end_date |

### Finance Domain

| Question | TVF Name | Parameters |
|---|---|---|
| "What are the highest transaction accounts?" | `get_top_accounts_by_transactions` | start_date, end_date, top_n |
| "How is account X performing?" | `get_account_performance` | account_id, start_date, end_date |
| "Show me fraud cases by merchant" | `get_fraud_by_merchant` | start_date, end_date |
| "Compare revenue by product line" | `get_revenue_by_product_line` | start_date, end_date |
| "Daily transaction volume trend" | `get_daily_transaction_trend` | start_date, end_date |

### Hospitality Domain

| Question | TVF Name | Parameters |
|---|---|---|
| "What are the top destinations by bookings?" | `get_top_destinations_by_bookings` | start_date, end_date, top_n |
| "How is property X performing?" | `get_property_performance` | property_id, start_date, end_date |
| "Show me occupancy by property type" | `get_occupancy_by_property_type` | start_date, end_date |
| "Revenue by destination" | `get_revenue_by_destination` | start_date, end_date |
| "Daily booking trend" | `get_daily_booking_trend` | start_date, end_date |

---

## Step 4: Create Requirements Document

Before coding, fill out the requirements template at `assets/templates/tvf-requirements-template.md` with:

1. **Project context** — catalog, schema, primary fact table, key dimensions
2. **Business questions** — 10-15 questions mapped to TVF names and parameters
3. **Available tables** — Gold layer dimensions and facts
4. **Key measures** — aggregation logic for each business metric

This ensures:
- All stakeholder questions are covered
- No TVFs are created without a clear business need
- Parameter types and names are consistent across TVFs
- Cross-references between TVFs are identified (e.g., NOT FOR redirects)

---

## Step 5: Validate Plan Before Coding

Before writing any SQL, verify:

- [ ] Every business question maps to exactly one TVF
- [ ] All required tables exist in the Gold layer
- [ ] All column names verified against YAML schemas (see Schema Validation Rule #0 in `references/tvf-patterns.md`)
- [ ] SCD Type identified for each dimension (Type 1 = no `is_current`, Type 2 = requires `is_current = true`)
- [ ] Parameter types are Genie-compatible (STRING for dates, INT for counts)
- [ ] Required parameters precede optional parameters (with DEFAULT)
- [ ] No duplicate TVFs (overlapping business questions)
- [ ] NOT FOR / PREFERRED OVER cross-references planned
