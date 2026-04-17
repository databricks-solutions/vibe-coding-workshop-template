# Genie Space Configuration Guide

Complete guide for configuring Databricks Genie Spaces with the mandatory 8-section structure.

## Mandatory 8-Section Deliverable Structure

**Every Genie Space setup MUST produce a document with ALL 8 sections below.**
**Missing any section = INCOMPLETE and REJECTED deliverable.**

| Section | What to Provide | Format |
|---------|-----------------|--------|
| **A. Space Name** | Exact Genie Space name | `{Project} {Domain} Analytics Space` |
| **B. Space Description** | 2-3 sentence purpose | Natural language interface for... |
| **C. Sample Questions** | 10-15 user-facing questions | Grouped by domain |
| **D. Data Assets** | ALL tables & metric views | Table format with purpose |
| **E. General Instructions** | **≤20 LINES** LLM behavior rules | Concise numbered list |
| **F. TVFs** | ALL functions with signatures | Table + detailed specs |
| **G. Benchmark Questions** | 10-15 with **EXACT SQL** | Question + Working SQL + Expected result |
| **H. SQL Expressions** | Measures, Filters, Dimensions | Structured `sql_snippets` definitions |

---

## Pre-Creation Table Inspection

**🔴 MANDATORY: Before creating ANY Genie Space, inspect all target table schemas.**

### Inspection Checklist

For every table you plan to add as a trusted asset:

```sql
-- Step 1: Verify table exists and has a comment
DESCRIBE TABLE EXTENDED ${catalog}.${gold_schema}.${table_name};

-- Step 2: Check all columns have comments
SELECT
  column_name,
  data_type,
  comment
FROM information_schema.columns
WHERE table_catalog = '${catalog}'
  AND table_schema = '${gold_schema}'
  AND table_name = '${table_name}'
ORDER BY ordinal_position;

-- ❌ REJECT if ANY column has NULL comment
-- ❌ REJECT if ANY column name is abbreviated (clv, amt, dt, etc.)
```

### What to Verify

| Check | Pass Criteria | Fail Action |
|-------|--------------|-------------|
| Table comment exists | `COMMENT` is not NULL | Add via `COMMENT ON TABLE` |
| All column comments exist | Zero NULL comments | Add via `COMMENT ON COLUMN` |
| Column names are descriptive | No abbreviations | Rename columns or create view |
| Date columns are DATE/TIMESTAMP | Proper date types | Fix in Gold layer DDL |
| Primary keys defined | PK constraint exists | Add constraint |
| Layer is Gold | Table is in Gold schema | Do NOT use Silver/Bronze |

### Programmatic Inspection (Python)

```python
def inspect_table_for_genie(spark, catalog, schema, table_name):
    """Validate a table is ready to be a Genie trusted asset."""
    full_name = f"{catalog}.{schema}.{table_name}"
    
    # Check table comment
    table_info = spark.sql(f"DESCRIBE TABLE EXTENDED {full_name}")
    comment_row = table_info.filter("col_name = 'Comment'").collect()
    if not comment_row or not comment_row[0]['data_type']:
        raise ValueError(f"❌ Table {full_name} has no COMMENT")
    
    # Check column comments
    cols = spark.sql(f"""
        SELECT column_name, comment 
        FROM information_schema.columns
        WHERE table_catalog = '{catalog}'
          AND table_schema = '{schema}'
          AND table_name = '{table_name}'
    """).collect()
    
    missing = [r['column_name'] for r in cols if not r['comment']]
    if missing:
        raise ValueError(f"❌ Columns without comments: {missing}")
    
    print(f"✅ {full_name} passed Genie readiness check")
```

---

## Section A: Space Name

**REQUIRED FORMAT:**
```
Space Name: {Project Name} {Domain} Analytics Space
```

**Examples:**
- `Wanderbricks Revenue Analytics Space`
- `RetailChain Sales Performance Space`
- `Healthcare Patient Outcomes Space`

---

## Section B: Space Description

**REQUIRED FORMAT (2-3 sentences):**
```
Description: Natural language interface for {domain} analytics. 
Enables {user type} to query {data types} without SQL. 
Powered by {key data assets}.
```

### Extended Space Description Pattern

```markdown
BUSINESS CONTEXT:
[Company/Partner] [relationship description]

Products: [Product categories with specific brands/SKUs]
Scope: [What data is tracked: transactions, inventory, operations]
Users: [Target user roles and their needs]

DATA COVERAGE:
• [Quantify scope: N stores, N SKUs, N transactions]
• [Data granularity: daily, hourly, real-time]
• [Key dimensions available]
• [Time range available]

AVAILABLE ANALYTICS:

1. [Domain 1 Name]
   • [Use case 1]
   • [Use case 2]
   • [Use case 3]

2. [Domain 2 Name]
   • [Use case 1]
   • [Use case 2]

USE CASES:
✓ [User role 1] [specific task]
✓ [User role 2] [specific task]
✓ [User role 3] [specific task]
```

---

## Section C: Sample Questions

**REQUIRED: 10-15 questions organized by domain**

```markdown
## Sample Questions

### Revenue Questions
1. "What is the total revenue for the last 30 days?"
2. "Show me the top 10 {entities} by revenue"

### Performance Questions  
3. "Which {entity} had the best performance last quarter?"

### Trend Questions
4. "Show me daily {metric} for the last 7 days"
```

---

## Section D: Data Assets

**REQUIRED FORMAT:**

```markdown
## Data Assets

### Metric Views (PRIMARY - Use First)
| Metric View Name | Purpose | Key Measures |
|------------------|---------|--------------|
| {view_name} | {purpose} | {measures} |

### Dimension Tables
| Table Name | Purpose | Key Columns |
|------------|---------|-------------|
| dim_{entity} | {purpose} | {columns} |

### Fact Tables (if needed)
| Table Name | Purpose | Grain |
|------------|---------|-------|
| fact_{entity} | {purpose} | {grain} |
```

### Data Assets Organization Pattern

**Hierarchy: Metric Views → TVFs → Tables**

**Always add assets in this order:**

1. **Primary Metric Views** (Add first, use most)
   - Pre-aggregated for performance
   - Rich with measures and dimensions
   - Best for broad analytical queries

2. **Table-Valued Functions** (Add second, use for specific patterns)
   - Parameterized queries
   - Business logic encapsulation
   - Complex filtering or calculations

3. **Reference Tables** (Add last, use sparingly)
   - Direct table access
   - When metric views/TVFs insufficient
   - Performance considerations

### Column Configs for Trusted Assets

Every trusted asset table should have `column_configs` in the Genie Space JSON that include:

| Property | Purpose | When to Set |
|---|---|---|
| `synonyms` | User-friendly alternative names for NLQ matching | All dimension columns users might reference by alternate names |
| `get_example_values` | Genie samples real values for LLM context | All filterable dimension columns |
| `build_value_dictionary` | Low-cardinality lookup for exact matching | Text columns with < ~100 distinct values that users filter by |
| `enable_format_assistance` | Genie assists with value formatting | All dimension columns (dates, text, IDs, flags) |
| `enable_entity_matching` | Fuzzy entity name matching | Text/categorical columns users filter by (names, codes, flags) |

**Synonym Placement:**
- **column_configs `synonyms`** → Genie Space JSON (or metric view YAML `synonyms` field)
- **UC COMMENT** → Business definition, grain, valid values — NOT synonyms

See [Agent Instructions Guide](./agent-instructions.md#column-config-flags-for-genie) for the full pattern by column type.

---

## Section E: General Instructions (20 Lines MAX)

**⚠️ CONSTRAINT: EXACTLY 20 LINES OR LESS. NO EXCEPTIONS.**

**REQUIRED FORMAT:**
```markdown
## General Instructions

You are an expert {domain} analyst. Follow these rules:

1. **Primary Data Source:** Always use Metric Views first
2. **Use TVFs:** For common queries, prefer Table-Valued Functions
3. **Date Defaults:** If no date specified, default to last 30 days
4. **Aggregations:** Use SUM for totals, AVG for averages
5. **Sorting:** Sort by primary metric DESC unless specified
6. **Limits:** Return top 10-20 rows for ranking queries
7. **Currency:** Format as USD with 2 decimal places
8. **Percentages:** Show as % with 1 decimal place
9. **Synonyms:** Handle common term equivalents
10. **Context:** Explain results in business terms
11. **Comparisons:** Show absolute values and % difference
12. **Time Periods:** Support today, yesterday, last week, month, quarter, YTD
13. **Null Handling:** Exclude nulls from calculations
14. **Performance:** Never scan raw Bronze/Silver tables
15. **Accuracy:** State assumptions when uncertain
```

See [Agent Instructions Guide](./agent-instructions.md) for extended patterns and best practices.

### Extended Instructions (13-Section Structure)

For production Genie Spaces, the 20-line General Instructions should be complemented by
**Extended Instructions** following the 13-section structure:

**PURPOSE → ASSET ROUTING → BUSINESS DEFINITIONS → DISAMBIGUATION → AGGREGATION RULES → FUNCTION ROUTING → JOIN GUIDANCE → QUERY RULES → QUERY PATTERNS → TEMPORAL FILTERS → DATA QUALITY NOTES → CONSTRAINTS → SQL EXPRESSIONS**

The Extended Instructions go into the `text_instructions` field of the Genie Space JSON
(or are appended to the General Instructions). They provide the full domain playbook that
powers accurate SQL generation. Section 13 (SQL EXPRESSIONS) documents which business
concepts to promote into structured `sql_snippets` for direct Genie matching.

See [Agent Instructions Guide — 13 Mandatory Sections](./agent-instructions.md#the-13-mandatory-sections) for the complete template.

**Key guidance when updating instructions:**
- **Append new rules** to existing instructions — never replace the entire block
- **Number rules sequentially** (existing 1-14, new rules start at 15+)
- **Run all existing benchmarks** after any instruction change to verify no regression

---

## Section F: Table-Valued Functions

**REQUIRED FORMAT:**

```markdown
## Table-Valued Functions

| Function Name | Signature | Purpose | When to Use |
|---------------|-----------|---------|-------------|
| get_{query} | `get_{query}(param TYPE)` | {purpose} | {scenario} |

### TVF Details

#### get_{query1}
- **Signature:** `get_{query1}(param STRING, start_date DATE, end_date DATE)`
- **Returns:** {description of columns}
- **Use When:** {specific question pattern}
- **Example:** `SELECT * FROM get_{query1}('value', CURRENT_DATE - 30, CURRENT_DATE)`
```

---

## Section G: Benchmark Questions with SQL

**⚠️ CRITICAL: Each question MUST have EXACT working SQL**

**REQUIRED FORMAT:**

```markdown
## Benchmark Questions & Expected SQL

### Question 1: "{Natural language question}"
**Expected SQL:**
```sql
SELECT columns FROM table WHERE conditions ORDER BY metric DESC LIMIT n;
```
**Expected Result:** {Description}

---

### Question 2: "{Question using TVF}"
**Expected SQL:**
```sql
SELECT * FROM get_function_name(params);
```
**Expected Result:** {Description}
```

**⚠️ REQUIREMENT: 10-15 benchmark questions with WORKING SQL.**

**⚠️ JSON field name:** In the API-compatible JSON export, benchmark SQL goes in `answer: [{format: "SQL", content: ["SELECT ..."]}]` — **NOT** in a field called `expected_sql`. The term "Expected SQL" here refers to the content, not the JSON field name. See `genie-space-export-import-api` for the exact `BenchmarkQuestion` schema.

### Critical SQL Rules

#### MEASURE() Uses Column Names, NOT Display Names

**The MEASURE() function in metric view queries requires the actual column `name`, NOT the `display_name`.**

**❌ WRONG:**
```sql
SELECT 
  MEASURE(`Total Revenue`) as revenue,      -- ❌ FAILS: "Total Revenue" is display_name
  MEASURE(`Booking Count`) as bookings      -- ❌ FAILS: "Booking Count" is display_name
FROM ${catalog}.${gold_schema}.revenue_analytics_metrics;
```

**✅ CORRECT:**
```sql
SELECT 
  MEASURE(total_revenue) as revenue,      -- ✅ Uses actual column name
  MEASURE(booking_count) as bookings      -- ✅ Uses actual column name
FROM ${catalog}.${gold_schema}.revenue_analytics_metrics;
```

#### Full UC 3-Part Namespace Required

**All table and function references MUST use the full Unity Catalog 3-part namespace.**

**❌ WRONG:**
```sql
SELECT * FROM fact_booking_daily;
SELECT * FROM get_revenue_by_period('2024-01-01', '2024-12-31', 'week');
```

**✅ CORRECT:**
```sql
SELECT * FROM ${catalog}.${gold_schema}.fact_booking_daily;
SELECT * FROM ${catalog}.${gold_schema}.get_revenue_by_period('2024-01-01', '2024-12-31', 'week');
```

#### TVF vs Metric View Decision Logic

**Not every question needs a TVF. Use the right tool for the question.**

| Question Pattern | Tool | Date Handling |
|-----------------|------|---------------|
| "Show X" (no date mentioned) | Metric View | No filter |
| "What is the X rate?" | Metric View | No filter |
| "X by property type" | Metric View | No filter |
| "X last month" | TVF | Specific dates |
| "X for Q4 2024" | TVF | Specific dates |
| "X trend for [period]" | TVF | Date range |

---

## Section H: SQL Expressions

SQL Expressions (`sql_snippets` in the API) provide structured, parseable definitions of business concepts that Genie can match directly against user questions. They complement text instructions and example SQL queries.

### When to Use SQL Expressions vs Other Instruction Types

| Instruction Type | Purpose | Format | Best For |
|---|---|---|---|
| **SQL Expressions (Measures)** | Structured KPI definitions | `SUM(table.column)` | Top 10-20 KPIs users ask about frequently |
| **SQL Expressions (Filters)** | Pre-built WHERE clauses | `table.col = 'value'` | Common business conditions (region, status, tier) |
| **SQL Expressions (Dimensions)** | Grouping/derived attributes | `table.column` or `CASE WHEN...` | Key grouping attributes with user synonyms |
| **Text Instructions** | Free-form behavioral guidance | Markdown text | Routing rules, disambiguation, aggregation rules |
| **Example SQL Queries** | Full query templates | Complete SQL statements | Teaching Genie how to approach common question patterns |

**Key Insight:** SQL Expressions define **individual reusable concepts**. Text instructions define **behavioral rules**. Example SQL queries demonstrate **complete query patterns**. Use all three together for best results.

### The "Promote" Pattern

The recommended workflow for SQL Expressions:

1. **Write business definitions in text instructions first** (Section 3: BUSINESS DEFINITIONS in Extended Instructions)
2. **Identify the top KPIs, common filters, and key dimensions** from those definitions
3. **Promote them into structured `sql_snippets`** for better Genie matching

This avoids duplication while ensuring the most important concepts get structured treatment.

### JSON Schema

SQL Expressions live in `serialized_space.instructions.sql_snippets` with three arrays:

```json
"sql_snippets": {
  "filters": [
    {
      "id": "01f0ad10a1cd17470000000000000001",
      "sql": ["${catalog}.${gold_schema}.dim_store.state = 'CA'"],
      "display_name": "California Stores",
      "instruction": ["Use this filter when the user asks about California, CA, or the state of California."],
      "synonyms": ["california", "CA", "state of california"]
    }
  ],
  "expressions": [
    {
      "id": "01f0ad10ec6214390000000000000001",
      "sql": ["${catalog}.${gold_schema}.dim_date.month_name"],
      "display_name": "Month Name",
      "instruction": ["Use as a grouping dimension when the user asks for data by month."],
      "synonyms": ["month", "monthly", "by month"]
    }
  ],
  "measures": [
    {
      "id": "01f0ad10c9a616dc0000000000000001",
      "sql": ["SUM(${catalog}.${gold_schema}.fact_sales.net_revenue)"],
      "display_name": "Total Revenue",
      "instruction": ["Use for revenue, sales, or dollar amount questions."],
      "synonyms": ["revenue", "sales", "total sales", "dollars"]
    }
  ]
}
```

### Field Requirements

Every SQL Expression entry **MUST** include:

| Field | Type | Requirement |
|---|---|---|
| `id` | string | 32-character hex ID (use `hashlib.md5` or UUID) |
| `sql` | string[] | Working SQL fragment referencing `table.column` from trusted assets |
| `display_name` | string | User-friendly name shown in Genie UI |
| `instruction` | string[] | When and how Genie should apply this expression |
| `synonyms` | string[] | 2-5 alternative terms users might use |

### SQL Requirements by Type

| Type | JSON Key | SQL Must... | Example |
|---|---|---|---|
| **Measure** | `measures` | Use an aggregation function (`SUM`, `AVG`, `COUNT`, etc.) | `SUM(table.total_sales_usd)` |
| **Filter** | `filters` | Evaluate to a boolean condition | `table.country_code = 'US'` |
| **Dimension** | `expressions` | Reference a column or derive a value per row (no aggregation) | `table.zone_combination` or `CASE WHEN ... END` |

### UI Terminology Mapping

The Databricks UI uses different labels than the JSON keys:

| Databricks UI Label | JSON key in `sql_snippets` |
|---|---|
| Measure | `measures` |
| Filter | `filters` |
| Dimension | `expressions` |

### What to Promote into SQL Expressions

| Source (Text Instructions Section) | Promote To | Criteria |
|---|---|---|
| Section 3: BUSINESS DEFINITIONS — KPI formulas | `measures` | Top 10-20 KPIs users ask about |
| Section 5: AGGREGATION RULES — common WHERE clauses | `filters` | Conditions appearing in 3+ benchmark queries |
| Section 4: DISAMBIGUATION — grouping attributes | `expressions` | Columns with synonyms users commonly reference |

### Build Script Pattern

When generating Genie Space JSON programmatically, add `sql_snippets` to the `instructions` dict:

```python
SQL_EXPRESSIONS = {
    "filters": [
        {
            "display_name": "California Stores",
            "sql": f"{DIM_LOC}.state_name = 'CA'",
            "instruction": "Use when filtering to California.",
            "synonyms": ["california", "CA", "state of california"],
        },
    ],
    "expressions": [
        {
            "display_name": "Zone",
            "sql": f"{MV_METRIC}.zone_combination",
            "instruction": "Use when grouping by zone.",
            "synonyms": ["zone", "zone vp", "franchise zone"],
        },
    ],
    "measures": [
        {
            "display_name": "Total Revenue",
            "sql": f"SUM({MV_METRIC}.total_sales_usd)",
            "instruction": "Use for revenue or sales questions.",
            "synonyms": ["revenue", "sales", "total sales"],
        },
    ],
}

# In the build function:
"instructions": {
    "text_instructions": [...],
    "example_question_sqls": [...],
    "join_specs": [...],
    "sql_snippets": {
        k: [
            {
                "id": _id(f"sqlexpr_{k}_{i}"),
                "sql": [expr["sql"]],
                "display_name": expr["display_name"],
                "instruction": [expr["instruction"]],
                "synonyms": expr["synonyms"],
            }
            for i, expr in enumerate(v)
        ]
        for k, v in SQL_EXPRESSIONS.items()
    },
}
```

---

## Warehouse Selection

### 🔴 MANDATORY: Serverless SQL Warehouse Only

**ALWAYS use a Serverless SQL Warehouse for Genie Spaces.**

| Warehouse Type | Allowed for Genie? | Why |
|---|---|---|
| **Serverless** | ✅ YES | Auto-scaling, instant startup, cost-efficient idle |
| **Pro** | ❌ NO | Manual sizing, startup delay, over-provisioning risk |
| **Classic** | ❌ NO | Legacy, no auto-scaling, poor interactive experience |

**Setting the warehouse:**

```python
# ✅ CORRECT: Let tool auto-detect a Serverless warehouse
create_or_update_genie(
    display_name="Sales Analytics",
    table_identifiers=[...],
    # warehouse_id auto-detected (prefers running Serverless)
)

# ✅ CORRECT: Explicit Serverless warehouse ID
create_or_update_genie(
    display_name="Sales Analytics",
    table_identifiers=[...],
    warehouse_id="abc123def456"  # Must be Serverless type
)
```

**Auto-detection priority:**
1. Running Serverless warehouses first
2. Starting warehouses second
3. Smaller sizes preferred (cost-efficient)

---

## Conversation API Validation

### 🔴 MANDATORY: Programmatic Testing After Deployment

**After creating a Genie Space, validate ALL benchmark questions programmatically.**

### Basic Validation Pattern

```python
def validate_genie_space(space_id: str, benchmark_questions: list[dict]):
    """Validate Genie Space with benchmark questions via Conversation API."""
    results = []
    
    for bq in benchmark_questions:
        # ✅ NEW conversation for each unrelated question
        result = ask_genie(
            space_id=space_id,
            question=bq["question"],
            timeout_seconds=60
        )
        
        passed = (
            result["status"] == "COMPLETED"
            and result["row_count"] > 0
        )
        
        results.append({
            "question": bq["question"],
            "status": result["status"],
            "rows": result.get("row_count", 0),
            "sql": result.get("sql", "N/A"),
            "passed": passed
        })
        
        if not passed:
            print(f"❌ FAILED: {bq['question']}")
            print(f"   Status: {result['status']}")
            print(f"   Error: {result.get('error', 'No rows returned')}")
        else:
            print(f"✅ PASSED: {bq['question']}")
    
    pass_rate = sum(1 for r in results if r["passed"]) / len(results) * 100
    print(f"\n{'='*60}")
    print(f"Pass rate: {pass_rate:.0f}% ({sum(1 for r in results if r['passed'])}/{len(results)})")
    print(f"Target: 90%+")
    
    return results
```

### Follow-up Conversation Testing

```python
# ✅ CORRECT: Test follow-up context works
result1 = ask_genie(space_id, "What were total sales last month?")
result2 = ask_genie_followup(
    space_id=space_id,
    conversation_id=result1["conversation_id"],
    question="Break that down by region"
)
# "that" should resolve to "total sales last month"
assert result2["status"] == "COMPLETED"
assert result2["row_count"] > 1  # Multiple regions expected
```

### Timeout Configuration

| Query Complexity | Timeout | Examples |
|---|---|---|
| Simple aggregation | 30 seconds | "Total sales", "Count of customers" |
| Multi-dimension GROUP BY | 60 seconds | "Sales by region and product" |
| Complex joins / CTEs | 120 seconds | "Customer LTV with cohort analysis" |
| Large data scans | 180 seconds | "All transactions for last year" |

### When to Start New vs Follow-up Conversations

| Scenario | Action | Why |
|---|---|---|
| Unrelated benchmark question | `ask_genie()` (new) | Prevents context contamination |
| "Break that down by X" | `ask_genie_followup()` | Needs prior context |
| "Same for last year" | `ask_genie_followup()` | Needs prior context |
| Different domain entirely | `ask_genie()` (new) | Different routing needed |

---

## Genie Space Update Pattern

**To update an existing Genie Space (add tables, change questions, update instructions):**

```python
# The tool finds the existing space by display_name and updates it
create_or_update_genie(
    display_name="Sales Analytics",  # Must match existing name exactly
    table_identifiers=[
        "catalog.gold.fact_sales",
        "catalog.gold.dim_customer",
        "catalog.gold.dim_product",
        "catalog.gold.new_table_added"  # Added new table
    ],
    description="Updated description with new table context",
    sample_questions=[
        "What were total sales last month?",
        "New question about the new table"  # Added new question
    ]
)
```

**Key rules for updates:**
- `display_name` must EXACTLY match the existing space name
- Provide the COMPLETE list of `table_identifiers` (not just additions)
- Provide the COMPLETE list of `sample_questions` (not just additions)
- Re-run Conversation API validation after updates

---

## Deliverable Checklist

Before submitting ANY Genie Space document:

| Section | Requirement | Complete? |
|---------|-------------|-----------|
| **A. Space Name** | Exact name provided | ☐ |
| **B. Space Description** | 2-3 sentences | ☐ |
| **C. Sample Questions** | 10-15 questions | ☐ |
| **D. Data Assets** | All tables & metric views | ☐ |
| **E. General Instructions** | ≤20 lines | ☐ |
| **F. TVFs** | All functions with signatures | ☐ |
| **G. Benchmark Questions** | 10-15 with SQL answers | ☐ |
| **H. SQL Expressions** | Measures, filters, dimensions as `sql_snippets` | ☐ |

**🔴 ALL 8 SECTIONS REQUIRED. NO EXCEPTIONS. 🔴**

---

## Testing and Validation Pattern

### Test Execution Plan

```markdown
### Test Plan

After setting up the Genie Space, systematically test with benchmark questions:

1. **Category 1 ([Name])** - Test [N] questions, verify results
2. **Category 2 ([Name])** - Test [N] questions, verify results
[Continue for all categories]

### Success Criteria

For each question:
- [ ] Genie understands the question
- [ ] Correct metric view or TVF is used
- [ ] Filters are applied correctly
- [ ] Aggregation level is appropriate
- [ ] Results are formatted properly
- [ ] Query completes in < 10 seconds
- [ ] Answer matches expected format
```

---

## Deployment Checklist Pattern

### Pre-Launch Validation

```markdown
## ✅ Deployment Checklist

Before launching to users:

### Configuration
- [ ] Genie Space created with descriptive name
- [ ] Space description added (Section 1)
- [ ] Agent instructions configured (Section 2)
- [ ] SQL Warehouse selected (Serverless recommended)

### Data Assets
- [ ] Metric view: [view1] added as trusted data
- [ ] Metric view: [view2] added as trusted data
- [ ] TVF: [function1] added
- [ ] TVF: [function2] added

### Testing
- [ ] All [N] benchmark questions tested
- [ ] Results validated against expected answers
- [ ] Query performance acceptable (< 10 sec)
- [ ] Error handling verified

### Permissions
- [ ] [Owner group] granted OWNER access
- [ ] [User group 1] granted CAN USE access
- [ ] [User group 2] granted CAN USE access
- [ ] All users have SELECT on metric views and TVFs

### Training
- [ ] User quick start guide distributed
- [ ] Example questions document shared
- [ ] Training session scheduled
- [ ] Support channel created

### Documentation
- [ ] Setup guide finalized
- [ ] Benchmark questions documented
- [ ] Troubleshooting guide created
- [ ] Contact information provided
```

---

## Post-Deployment Audit

After deployment, Genie Space configuration can drift through manual UI edits. Use a structured audit workflow to detect and remediate drift.

### Audit Workflow

```bash
# 1. Export the live Genie Space config
python scripts/audit_genie_space.py \
  --space-id ${space_id} \
  --source-json src/${project}_semantic/genie_configs/${space_name}.json \
  --output audit_report.md

# 2. Review the diff report
# The script compares live vs source and flags:
# - Added/removed trusted assets
# - Modified instructions (line count, content)
# - Changed/removed benchmark questions
# - Modified SQL Expressions (sql_snippets)
# - Warehouse reassignment

# 3. Remediate
# Option A: Update source JSON to reflect intentional UI changes
# Option B: Re-deploy from source JSON to revert unintentional changes
```

### What Gets Audited

| Section | JSON Path | Drift Impact |
|---------|-----------|-------------|
| Trusted assets | `serialized_space.data_sources` | 🔴 Affects query routing |
| General Instructions | `serialized_space.instructions.text` | 🔴 Instructions > 20 lines get truncated |
| SQL Expressions | `serialized_space.instructions.sql_snippets` | 🔴 KPI/filter matching breaks |
| Benchmark questions | `serialized_space.benchmarks` | 🟡 Reduces validation coverage |
| Sample questions | `serialized_space.config.sample_questions` | 🟢 Cosmetic only |
| Warehouse ID | `warehouse_id` | 🔴 Non-serverless degrades performance |

### Integration with CI/CD

Add audit as a pre-promotion gate:

```yaml
# In your DAB or CI/CD pipeline
steps:
  - name: audit-genie-spaces
    script: |
      for config in src/${project}_semantic/genie_configs/*.json; do
        space_name=$(basename "$config" .json)
        space_id=$(jq -r '.space_id' "$config")
        python scripts/audit_genie_space.py \
          --space-id "$space_id" \
          --source-json "$config" \
          --fail-on-drift
      done
```

### Audit Cadence

| Environment | Frequency | Purpose |
|---|---|---|
| Development | After each manual UI edit | Catch unintentional changes |
| Staging | Before promotion to production | Gate for config integrity |
| Production | Weekly (scheduled) | Detect drift from UI editors |

---

## Success Metrics

### KPIs to Track

After deployment, measure:

1. **Adoption Metrics**
   - Number of active users per week
   - Questions asked per day
   - Unique questions (not repeated)

2. **Quality Metrics**
   - Query success rate (target: 90%+)
   - Average response time (target: < 10 sec)
   - User satisfaction rating (target: 4.5/5)

3. **Usage Patterns**
   - Most asked questions (inform future metric views)
   - Most used metric views (validate design)
   - Peak usage times (capacity planning)

4. **Business Impact**
   - Time saved vs traditional dashboards
   - Ad-hoc SQL requests reduction
   - Decisions made faster
