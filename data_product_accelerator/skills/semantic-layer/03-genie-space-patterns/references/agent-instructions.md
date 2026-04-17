# Agent Instructions Guide

Comprehensive guide for writing effective Genie Space agent instructions.

## Core Principle: Business Context Drives AI Quality

**The quality of Genie responses directly correlates with the depth of business context provided in agent instructions.**

**Key Patterns:**
1. **Eight-Section Structure**: A→B→C→D→E→F→G→H (all required)
2. **Concise Instructions**: 20 lines max for LLM behavior rules
3. **Data Asset Hierarchy**: Metric Views (primary) → TVFs (specific) → Tables (reference)
4. **SQL Validation**: Every benchmark question has working SQL

---

## Two Levels of Instructions

**Level 1: General Instructions (MANDATORY - Section E)**
- **MAXIMUM 20 LINES** - Concise behavior rules
- Goes in the mandatory deliverable document
- Covers defaults, formatting, synonyms

**Level 2: Extended Instructions (OPTIONAL - for complex domains)**
- 200-500 lines of detailed business context
- Can be added to Genie Space for better responses
- Use template below if needed

---

## Extended Instructions: 13-Section Structure (Recommended)

Production Genie Spaces benefit from structured, domain-rich instructions that go beyond the ≤20-line General Instructions summary. The **13-section structure** below is the recommended format for Extended Instructions — the comprehensive knowledge base that powers accurate query generation.

### Relationship to General Instructions

| Level | Where It Lives | Length | Purpose |
|---|---|---|---|
| **General Instructions** (Section E) | Genie Space UI "Instructions" field | ≤20 lines | Executive summary of behavior rules |
| **Extended Instructions** (13 sections) | `text_instructions` in Genie JSON or appended to General Instructions | 50-200 lines | Full domain playbook for SQL generation |

The General Instructions are a *concise subset* of the Extended Instructions. When the Extended Instructions are well-structured, the General Instructions become easier to write — they summarize the 13 sections into ≤20 essential rules.

### The 13 Mandatory Sections

Every Extended Instructions block MUST contain these 13 sections, in order:

| # | Section | Purpose | Genie Impact |
|---|---------|---------|-------------|
| 1 | **PURPOSE** | Domain role, core KPI, default filters | ⭐⭐⭐⭐⭐ Critical |
| 2 | **ASSET ROUTING** | Which asset for which question type | ⭐⭐⭐⭐⭐ Critical |
| 3 | **BUSINESS DEFINITIONS** | KPI formulas, hierarchy, terminology | ⭐⭐⭐⭐⭐ Critical |
| 4 | **DISAMBIGUATION** | Resolving ambiguous column/term choices | ⭐⭐⭐⭐⭐ Critical |
| 5 | **AGGREGATION RULES** | Denominators, default filters, NULLIF | ⭐⭐⭐⭐ Very Important |
| 6 | **FUNCTION ROUTING** | MEASURE() vs raw SUM/AVG, column naming | ⭐⭐⭐⭐ Very Important |
| 7 | **JOIN GUIDANCE** | Keys, cardinality, mandatory join filters | ⭐⭐⭐⭐ Very Important |
| 8 | **QUERY RULES** | Namespace, formatting, NULL handling | ⭐⭐⭐⭐ Very Important |
| 9 | **QUERY PATTERNS** | Reusable SQL templates (UNION, drill-down) | ⭐⭐⭐ Important |
| 10 | **TEMPORAL FILTERS** | Mapping user time terms to flag columns | ⭐⭐⭐ Important |
| 11 | **DATA QUALITY NOTES** | Known caveats, filtered-out records | ⭐⭐⭐ Important |
| 12 | **CONSTRAINTS** | Hard limits (namespace, exclusions, layer) | ⭐⭐⭐ Important |
| 13 | **SQL EXPRESSIONS** | Structured measures, filters, dimensions for `sql_snippets` | ⭐⭐⭐⭐ Very Important |

---

### 13-Section Template

```markdown
=================================================================
[PROJECT NAME] — GENIE AGENT INSTRUCTIONS
=================================================================

== 1. PURPOSE ==
You are an expert {domain} analyst for the {report/system name}.
Core KPI: {name} = {formula with clear variable definitions}.
Default filter: {filter_column} = '{value}' for all {kpi} queries.
Users: {target audience, e.g., field operations leaders, executives}.

== 2. ASSET ROUTING ==
| User Intent | Asset | Notes |
|---|---|---|
| Dimension-only lookups (list names, attributes, org hierarchy) | {dim_table} | No metrics — no MEASURE() |
| Pre-aggregated KPIs, period comparisons, APSD-style metrics | {metric_view} with MEASURE() | Primary asset for all KPI questions |
| Ad-hoc drill-downs, date-specific raw data, custom joins | {fact_table} + {dim_date} + {dim_location} | Use JOINs per Section 7 |

⚠️ Route to dimension table when user asks ONLY for attributes
(e.g., "list market leaders", "show stores in Virginia").

== 3. BUSINESS DEFINITIONS ==
- {KPI_1}: {formula} — {one-line explanation}
- {KPI_2}: {formula} — {one-line explanation}
- "{synonym_term}" and "{column_term}" are synonyms ({column_name} field)
- Hierarchy: {Level1} > {Level2} > ... > {LevelN} (e.g., Country > Zone > Region > Market > Area Leader > Store)
- Currency: {primary currency} is consolidated; {secondary} stores also have local amounts
- Time periods: "Day" = latest reporting day, "MTD" = month-to-date, "PY" = prior year same period
⚠️ Promote top KPIs to sql_snippets.measures for structured Genie matching — see Section 13.

== 4. DISAMBIGUATION ==
When multiple columns could match the user's intent, apply these defaults:

| User says | Default column | Reason | Alternative (only if explicitly requested) |
|---|---|---|---|
| "by {grouping}" | {grouping}_combination | Richer context (code + name) | {grouping}_name (name only) |
| "by {grouping} name only" | {grouping}_name | User explicitly requested name-only | — |
| "{term_with_two_meanings}" | {preferred_interpretation} | {reason} | {alternative} |

**Key principle:** When a `_combination` column (code + name) exists alongside a
`_name` column, default to the richer `_combination` column for "by X" queries.
Users see more context; they can always ask for name-only explicitly.

== 5. AGGREGATION RULES ==
- Default denominator for per-unit KPIs: COUNT(DISTINCT {store-day key})
- Default filter: WHERE {same_store_flag} = 'Y' for all {kpi} queries
- Use NULLIF({denominator}, 0) on all division operations
- Default sort: DESC by primary metric unless user specifies otherwise
- Limit ranking queries to top 10-20 rows unless user specifies otherwise

== 6. FUNCTION ROUTING ==
- Use MEASURE({column_name}) for metric view pre-aggregated columns
  ✅ MEASURE(total_sales_usd_day)   — actual column name
  ❌ MEASURE(`Total Sales USD Day`)  — display name FAILS
- Use raw SUM()/AVG()/COUNT() when querying fact tables with JOINs
- Column names in MEASURE() must match the metric view YAML `name` field,
  NOT the `display_name`
⚠️ Measures registered as SQL Expressions (sql_snippets) get priority matching.
  Register the top 10-20 KPIs as sql_snippets.measures — see Section 13.

== 7. JOIN GUIDANCE ==
| Left Table | Right Table | Join Key | Cardinality |
|---|---|---|---|
| {fact_table} | {dim_date} | {fact}.{date_fk} = {dim}.{date_pk} | Many-to-One |
| {fact_table} | {dim_location} | {fact}.{loc_fk} = {dim}.{loc_pk} | Many-to-One |

Always include active-record filters in JOIN conditions where applicable
(e.g., is_record_active = 'Y', open_status_code = 'O').

== 8. QUERY RULES ==
- All tables in {catalog}.{schema} — always use full 3-part names
- For YoY comparisons, show both CY and PY values plus the % change
- Do NOT add WHERE column IS NOT NULL on dimension-only lookups
  unless the user explicitly requests excluding nulls
- Continue using NULLIF for measure denominators per Aggregation Rules

== 9. QUERY PATTERNS ==
Pattern A — Day + MTD side-by-side:
  SELECT 'Day' AS period, MEASURE(...) ...
  UNION ALL
  SELECT 'MTD' AS period, MEASURE(...) ...

Pattern B — CY vs PY comparison:
  SELECT {dim}, 'CY' AS year_label, MEASURE({cy_metric}) ...
  UNION ALL
  SELECT {dim}, 'PY' AS year_label, MEASURE({py_metric}) ...
  ORDER BY {dim}, year_label

Pattern C — Hierarchy drill-down:
  SELECT {level1}, {level2}, {level3}, MEASURE({metric}) ...
  GROUP BY {level1}, {level2}, {level3}
  ORDER BY MEASURE({metric}) DESC

Pattern D — Dual currency (when applicable):
  SELECT {dim}, 'USD' AS currency, MEASURE({usd_metric}) ...
  UNION ALL
  SELECT {dim}, '{local}' AS currency, MEASURE({local_metric}) ...

== 10. TEMPORAL FILTERS ==
Map user time terms to the correct flag columns:

| User says | Filter column | Value |
|---|---|---|
| "today", "current day", "latest day" | {is_current_day_flag} | 'Y' |
| "MTD", "month to date" | {is_mtd_flag} | 'Y' |
| "prior year same day", "PY day" | {is_py_same_day_flag} | 'Y' |
| "prior year MTD" | {is_py_mtd_flag} | 'Y' |
| "last 7 days", "trailing week" | {is_7day_flag} | 'Y' |

{Include MTDay-vs-MTDate switching logic if applicable:}
use_mtdate_flag = 1 on the 1st of month → use date-aligned PY comparison
use_mtdate_flag = 0 otherwise → use weekday-aligned PY comparison

== 11. DATA QUALITY NOTES ==
- Only {qualifying subset} records are included in {dim_table}
  (e.g., only active, open, non-temporarily-closed stores)
- {Column} is NULL for {condition} records
  (e.g., exchange_rate is NULL for USD-denominated records)
- {Special flag}: {definition and qualification criteria}
  (e.g., is_finance_monthly_same_store = 'Y' means store open 28+ days)

== 12. CONSTRAINTS ==
- Always use full 3-part UC namespace: {catalog}.{schema}.{object}
- {Subset exclusion rule} (e.g., PDI and SAP stores excluded from US-only views)
- Only Gold layer tables/views used as trusted assets
- {Any domain-specific hard rules}

== 13. SQL EXPRESSIONS ==
Register key business concepts as structured sql_snippets for direct Genie matching.
These are promoted from Sections 3, 4, and 5 — the text definitions remain as behavioral
context; sql_snippets give Genie parseable, matchable definitions.

MEASURES (promote top KPIs from Section 3):
| display_name | sql | synonyms |
|---|---|---|
| {KPI_1 Name} | SUM({table}.{column}) | {synonym1}, {synonym2} |
| {KPI_2 Name} | AVG({table}.{column}) / NULLIF(COUNT(...), 0) | {synonym1}, {synonym2} |

FILTERS (promote common WHERE clauses from Section 5):
| display_name | sql | synonyms |
|---|---|---|
| {Filter Name} | {table}.{column} = '{value}' | {synonym1}, {synonym2} |
| {Filter Name} | {table}.{flag_column} = 'Y' | {synonym1}, {synonym2} |

DIMENSIONS (promote grouping attributes from Section 4):
| display_name | sql | synonyms |
|---|---|---|
| {Dimension Name} | {table}.{column} | {synonym1}, {synonym2} |
| {Derived Dim Name} | CASE WHEN {table}.{col} ... END | {synonym1}, {synonym2} |

=================================================================
END OF INSTRUCTIONS
=================================================================
```

---

### Instruction Evolution: Append-Only Updates

**🔴 CRITICAL: When optimizing an existing Genie Space, APPEND new rules — never replace the entire instruction block.**

Existing rules were validated by users and benchmarks. Replacing them risks regression
on questions that currently work correctly.

**✅ DO:** Append new sections or rules at the end
```
[existing rules 1-14 unchanged]

15. ASSET ROUTING:
- New routing guidance here...

16. NULL FILTER GUIDANCE:
- New constraint here...
```

**❌ DON'T:** Replace the entire instruction block with a new version
```
[all 14 existing rules deleted and rewritten]
```

**When is replacement acceptable?**
- Only during a planned full migration with benchmark regression testing
- Only when the user explicitly requests a rewrite
- Always run all existing benchmarks after replacement to verify no regression

---

## Column Config Flags for Genie

Beyond instructions, Genie uses `column_configs` in the space JSON to enhance entity matching
and formatting. These flags significantly improve query accuracy.

### enable_format_assistance

Tells Genie to assist with value formatting for the column. Apply to **all dimension columns**
(dates, text, categorical, numeric identifiers).

```json
{"column_name": "date_key_2", "enable_format_assistance": true}
{"column_name": "location_number", "enable_format_assistance": true}
{"column_name": "state_name", "enable_format_assistance": true}
```

### enable_entity_matching

Tells Genie to perform fuzzy entity name matching for the column. Apply to **text/categorical
columns that users filter by** — names, codes, flags, statuses.

```json
{"column_name": "zone_combination", "enable_entity_matching": true}
{"column_name": "market_leader_name", "enable_entity_matching": true}
{"column_name": "is_finance_monthly_same_store", "enable_entity_matching": true}
```

**Do NOT apply** to numeric measure columns (sales, counts, percentages).

### Pattern by Column Type

| Column Type | enable_format_assistance | enable_entity_matching | get_example_values | build_value_dictionary |
|---|---|---|---|---|
| Date/timestamp | ✅ | ❌ | ✅ | ❌ |
| Numeric ID (store#) | ✅ | ❌ | ✅ | ❌ |
| Text name (person, place) | ✅ | ✅ | ✅ | ✅ |
| Categorical flag (Y/N) | ✅ | ✅ | ✅ | ✅ |
| Code (zone_code) | ✅ | ❌ | ✅ | ❌ |
| Numeric measure (sales) | ❌ | ❌ | ❌ | ❌ |
| Percentage measure | ❌ | ❌ | ❌ | ❌ |

### Synonym Placement

**Synonyms go in `column_configs[].synonyms` in the Genie Space JSON (or in metric view
YAML `synonyms` fields), NEVER in materialized view COMMENT strings.**

| Where | What Goes There | Example |
|---|---|---|
| UC Table COMMENT | Purpose + grain | `'Location dimension: store attributes. Grain: one row per store.'` |
| UC Column COMMENT | Business definition, valid values | `'Y/N flag for same-store qualification'` |
| Genie column_configs synonyms | User-friendly alternative names | `["same store", "comp store", "SSS"]` |
| Metric View YAML synonyms | Same as Genie synonyms | `synonyms: ["same store", "comp store"]` |

**❌ DON'T** put synonyms in MV table/column COMMENTs:
```sql
-- BAD: synonyms pollute the UC metadata
COMMENT ON COLUMN dim_location.zone_combination IS
  'Zone code and name. Synonyms: zone, franchise zone, zone combo';
```

**✅ DO** put synonyms in column_configs:
```json
{"column_name": "zone_combination", "synonyms": ["zone", "franchise zone", "zone combo"]}
```

---

## Enrichment Script Pattern

For Genie Spaces with many columns, use a **Python enrichment script** as the canonical
source of truth for `column_configs`. This prevents drift between manual JSON edits and
ensures reproducible regeneration.

### Pattern

```python
# enrich_column_configs.py — Source of truth for column_configs

TABLE_COLUMNS = {
    "dim_location": [
        {"column_name": "zone_combination",
         "get_example_values": True, "build_value_dictionary": True,
         "enable_format_assistance": True, "enable_entity_matching": True,
         "synonyms": ["zone", "franchise zone"],
         "description": ["Combined zone code and name for reporting"]},
        # ... more columns
    ],
}

def enrich(genie_json):
    for table in genie_json["data_sources"]["tables"]:
        table_name = table["identifier"].split(".")[-1]
        if table_name in TABLE_COLUMNS:
            table["column_configs"] = TABLE_COLUMNS[table_name]
    return genie_json
```

**Benefits:**
- Single source of truth — no manual JSON drift
- Reviewable in code review — changes are visible in diffs
- Reproducible — re-run script after any upstream metadata change
- Testable — validate column names against actual schema

---

## Why This Structure?

| Section | Purpose | Impact on Genie Quality |
|---------|---------|------------------------|
| **PURPOSE** | Sets the domain context and core KPI | ⭐⭐⭐⭐⭐ Critical |
| **ASSET ROUTING** | Prevents wrong-asset selection (40% of misrouting) | ⭐⭐⭐⭐⭐ Critical |
| **BUSINESS DEFINITIONS** | Teaches Genie your business concepts | ⭐⭐⭐⭐⭐ Critical |
| **DISAMBIGUATION** | Resolves "by zone" → zone_combination vs zone_name | ⭐⭐⭐⭐⭐ Critical |
| **AGGREGATION RULES** | Correct denominators and default filters | ⭐⭐⭐⭐ Very Important |
| **FUNCTION ROUTING** | MEASURE() vs raw SQL, column naming | ⭐⭐⭐⭐ Very Important |
| **JOIN GUIDANCE** | Correct join keys and cardinality | ⭐⭐⭐⭐ Very Important |
| **QUERY RULES** | Namespace, formatting, NULL handling | ⭐⭐⭐⭐ Very Important |
| **QUERY PATTERNS** | Provides concrete reusable SQL templates | ⭐⭐⭐ Important |
| **TEMPORAL FILTERS** | Maps user time terms to flag columns | ⭐⭐⭐ Important |
| **DATA QUALITY NOTES** | Prevents surprise NULLs and filtered-out records | ⭐⭐⭐ Important |
| **CONSTRAINTS** | Hard limits that prevent broken queries | ⭐⭐⭐ Important |

---

## Critical Patterns for General Instructions

### 1. General Instructions Consistency

**Issue:** Contradictory rules in General Instructions caused Genie to select wrong data assets.

**Prevention Patterns:**

#### Use Explicit Exceptions
```markdown
# GOOD: Clear exception handling
- Host demographics/verification → host_analytics_metrics (attributes only)
⚠️ HOST PERFORMANCE EXCEPTION: For "Top hosts", "Host revenue" → USE get_host_performance TVF
```

#### Group by Question Type, Not Asset
```markdown
# BAD: Asset-first (causes conflicts)
- host_analytics_metrics → for host data
- get_host_performance → for host data

# GOOD: Question-first (clear routing)
Revenue/booking questions:
  - By property → revenue_analytics_metrics
  - By host → get_host_performance TVF (not metric view!)
  - By customer → customer_analytics_metrics

Attribute/demographic questions:
  - Host attributes → host_analytics_metrics
  - Property inventory → property_analytics_metrics
```

#### Use ⚠️ Markers for Critical Routing
```markdown
⚠️ CRITICAL - Metric View Selection:
- Revenue by property type → revenue_analytics_metrics (fact source)
- NOT property_analytics_metrics (dimension source, under-reports)
```

---

### 2. Ambiguous Term Definitions

**Issue:** Subjective terms like "underperforming" had multiple valid interpretations.

**Common Ambiguous Terms:**

| Term | Interpretation 1 | Interpretation 2 |
|---|---|---|
| "underperforming" | Low revenue (some activity) | Zero activity (no bookings) |
| "top performing" | Highest revenue | Highest rating |
| "business vs leisure" | Account type (individual/business) | Trip purpose (is_business_booking) |
| "valuable customers" | Historical spend | Predicted LTV |
| "best hosts" | Most revenue | Highest rating |

**Resolution Pattern:**

```markdown
## Term Definitions

"underperforming" = properties with revenue below median (use get_underperforming_properties TVF)
"top performing" = highest revenue unless "rated" specified
"business vs leisure" = trip purpose (is_business_booking), NOT account type
"valuable customers" = 
  - Historical: use get_customer_ltv TVF
  - Predicted: use customer_ltv_predictions table
"best hosts" = highest revenue per property (use get_host_performance TVF)
```

---

### 3. Metric View vs TVF Routing

**Issue:** Genie selected metric views when TVFs were more appropriate (and vice versa).

**Routing Decision Table:**

| Question Pattern | Best Asset | Reason |
|---|---|---|
| "Show X" (general) | Metric View | No parameters needed |
| "X by [dimension]" | Metric View | Standard aggregation |
| "Top N [entities]" | TVF with `top_n` param | Parameterized ranking |
| "X for [specific date range]" | TVF with date params | Bounded query |
| "X trend for [period]" | TVF (e.g., `get_revenue_by_period`) | Time-series logic |
| "Who are the [entities]?" | TVF returning individuals | Individual rows needed |
| "How many [entities]?" | Metric View or aggregate TVF | Summary stats |
| "Compare X vs Y" | Metric View with GROUP BY | Segmentation |

**Add Routing Rules to General Instructions:**

```markdown
## Query Routing

Revenue questions:
  - General revenue → revenue_analytics_metrics
  - Revenue by time period → get_revenue_by_period TVF
  - Revenue by host → get_host_performance TVF (NOT host_analytics_metrics!)

Customer questions:
  - Customer segments (summary) → get_customer_segments TVF
  - Individual VIP customers → get_customer_ltv TVF
  - Predicted customer value → customer_ltv_predictions table

Host questions:
  - Host demographics → host_analytics_metrics
  - Host revenue/bookings → get_host_performance TVF ⚠️

Property questions:
  - Property counts/inventory → property_analytics_metrics
  - Property performance → get_property_performance TVF
```

---

### 4. TVF Syntax Guidance

**Issue:** Genie wrapped TVFs incorrectly or added unnecessary GROUP BY.

**Common Errors to Prevent:**

```sql
-- ❌ TABLE() wrapper
SELECT * FROM TABLE(get_customer_segments('2020-01-01', '2024-12-31'))
-- Error: NOT_A_SCALAR_FUNCTION

-- ❌ Missing parameters  
SELECT * FROM get_customer_segments()
-- Error: WRONG_NUM_ARGS

-- ❌ GROUP BY on pre-aggregated TVF
SELECT segment_name, COUNT(*) FROM get_customer_segments(...) GROUP BY segment_name
-- Result: Same as without GROUP BY, but confusing
```

**Add Syntax Rules to General Instructions:**

```markdown
## TVF Syntax Rules

1. NEVER wrap TVFs in TABLE() - just call directly:
   ✅ SELECT * FROM get_customer_segments('2020-01-01', '2024-12-31')
   ❌ SELECT * FROM TABLE(get_customer_segments(...))

2. Include required parameters (check TVF signature):
   ✅ get_customer_ltv('2020-01-01', '2024-12-31', 100)
   ❌ get_customer_ltv()

3. Don't GROUP BY on aggregate TVFs - they're pre-aggregated:
   - get_customer_segments: Returns 5 segment rows (already grouped)
   - get_vip_customers: Returns segment stats (already grouped)
   - get_revenue_by_period: Returns time periods (already grouped)
```

---

### 5. Professional Language Standards

**Issue:** Instructions with negative language about assets confused Genie.

**❌ Avoid:**
```markdown
- Don't use host_analytics_metrics - it's broken for revenue
- The metric view returns wrong results so use the TVF
- host_analytics_metrics doesn't work properly
```

**✅ Use:**
```markdown
- Host revenue/bookings → get_host_performance TVF (accurate join path)
- Host attributes/demographics → host_analytics_metrics

⚠️ CRITICAL: get_host_performance TVF is PREFERRED for host revenue metrics
```

---

## Common Mistakes to Avoid

### ❌ DON'T: General Instructions > 20 Lines
```markdown
# BAD: 50+ lines of instructions
Instructions:
[Line 1]
[Line 2]
...
[Line 50]  # ❌ TOO LONG - Genie won't read all of this effectively
```

### ✅ DO: Concise 20-Line General Instructions
```markdown
# GOOD: Exactly 20 lines or less
## General Instructions

You are an expert analyst. Follow these rules:

1. **Primary Data:** Use Metric Views first
2. **TVFs:** Prefer TVFs for common queries
3. **Dates:** Default to last 30 days
4. **Sorting:** DESC by primary metric
5. **Limits:** Top 10-20 for rankings
[... up to 20 lines total]
```

---

## Benchmark Questions Pattern

### Organization by Business Function

Create 20-30 benchmark questions organized by business domain:

```markdown
### **Category 1: [Business Function Name]**

#### Q1.1: [Question Topic]
**Business Question:**
```
[Natural language question as user would ask]
```

**Expected Genie Query Strategy:**
- Metric View: `[metric_view_name]`
- Filter: `[SQL conditions or description]`
- Group By: `[dimensions]`
- Measure: `[metric expression]`
- Sort: `[ORDER BY clause]`
- Limit: `[LIMIT clause if applicable]`

**Expected Answer Format:**
| [Column 1] | [Column 2] | [Column 3] | [Column 4] |
|------------|------------|------------|------------|
| [Example 1] | [Data] | [Data] | [Data] |
| [Example 2] | [Data] | [Data] | [Data] |

**Validation Criteria:**
✓ [Check 1]
✓ [Check 2]
✓ [Check 3]
```

### Question Categories by Complexity

**Simple (Single dimension, single metric):**
- "What are the top 10 [entities] by [metric]?"
- "Show me [metric] by [dimension]"

**Moderate (Multiple dimensions, time filters):**
- "Compare [metric] for [filter1] vs [filter2]"
- "Show [metric] by [dimension] for [time_period]"

**Advanced (Multi-metric, calculated fields, joins):**
- "Show [entities] with high [metric1] but low [metric2]"
- "Compare [metric1] and [metric2] across [dimension1] and [dimension2]"

**Complex (Cross-domain, window functions, multiple data sources):**
- "Show [metric] trend with [comparison] for [filtered_entities]"
- "Analyze [dimension1] by [dimension2] with [calculated_metric]"

### Minimum Coverage

Ensure benchmark questions cover:
- [ ] All primary metric views (at least 3 questions each)
- [ ] All TVFs (at least 1 question each)
- [ ] Common time periods (this month, last quarter, YTD, rolling windows)
- [ ] All major dimensions (geographic, product, time, customer segments)
- [ ] Key business calculations (growth %, rates, averages, rankings)
- [ ] Edge cases (missing data, zero values, negative values)
- [ ] Multi-dimensional analysis (2+ dimensions combined)
- [ ] At least 2 follow-up conversation chains (drill-down from general → specific)

---

## Conversation API Testing Patterns

### 🔴 MANDATORY: Programmatic Validation

**After deployment, ALWAYS validate benchmark questions via the Conversation API.** UI-only testing is not reproducible and misses edge cases.

### Testing Strategy

| Phase | Method | Purpose |
|---|---|---|
| **Pre-deploy** | Test SQL manually | Verify SQL runs and returns expected results |
| **Post-deploy** | `ask_genie()` per question | Verify Genie generates correct SQL from natural language |
| **Follow-up** | `ask_genie_followup()` chains | Verify context is maintained correctly |
| **Regression** | Re-run after updates | Verify updates don't break existing questions |

### New Conversation vs Follow-up Decision

**Start a NEW conversation (`ask_genie()`) when:**
- Testing an unrelated benchmark question
- Switching business domains (revenue → customer → host)
- Running regression tests (each question should be independent)

**Use follow-up (`ask_genie_followup()`) when:**
- Testing drill-down capability ("Break that down by region")
- Testing context retention ("Same for last year")
- Validating pronoun resolution ("Which ones had the highest growth?")

### Handling Genie Responses

| Response Status | Action |
|---|---|
| `COMPLETED` | ✅ Validate row_count > 0 and SQL looks correct |
| `FAILED` | ❌ Rephrase question or fix instructions/assets |
| `TIMEOUT` | ⚠️ Increase timeout or simplify question |
| `CANCELLED` | ⚠️ Re-run (transient issue) |
| `text_response` (clarification) | ⚠️ Add more context to instructions or rephrase question |

### When Genie Asks for Clarification

If `text_response` is returned instead of SQL results, Genie needs more context:

1. **Add the ambiguous term** to General Instructions → Term Definitions
2. **Add a sample question** that demonstrates the expected pattern
3. **Add routing rules** that map the question type to the correct asset
4. **Re-test** via Conversation API

```python
result = ask_genie(space_id, "Show me the top performers")

if result.get("text_response"):
    # Genie asked for clarification -- fix instructions
    print(f"Genie asked: {result['text_response']}")
    # Action: Add to General Instructions:
    #   "top performers" = highest revenue unless "rated" specified
```
