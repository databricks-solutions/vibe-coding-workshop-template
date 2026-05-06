---
name: genie-space-patterns
description: Patterns for setting up Databricks Genie Spaces with comprehensive agent instructions, data assets, and benchmark questions. Use when creating Genie Spaces, configuring agent behavior, selecting data assets, or validating benchmark questions. Includes mandatory 7-section deliverable structure, General Instructions (≤20 lines), data asset organization (Metric Views → TVFs → Tables), benchmark questions with exact SQL, Serverless warehouse mandate, table/column comment requirements for Genie SQL quality, pre-creation table inspection, Conversation API programmatic validation, follow-up vs new conversation patterns, and deployment checklists.
metadata:
  author: prashanth subrahmanyam
  version: "2.2"
  domain: semantic-layer
  role: worker
  pipeline_stage: 6
  pipeline_stage_name: semantic-layer
  called_by:
    - semantic-layer-setup
  standalone: true
  last_verified: "2026-02-20"
  volatility: medium
  upstream_sources:
    - name: "ai-dev-kit"
      repo: "databricks-solutions/ai-dev-kit"
      paths:
        - "databricks-skills/databricks-genie/SKILL.md"
      relationship: "extended"
      last_synced: "2026-02-19"
      sync_commit: "97a3637"
---

# Genie Space Patterns

## Overview

This skill provides patterns for setting up production-ready Databricks Genie Spaces with natural language analytics capabilities. The quality of Genie responses directly correlates with the depth of business context provided in agent instructions.

**Core Principle:** Business context drives AI quality. Comprehensive agent instructions, properly selected data assets, and validated benchmark questions ensure reliable Genie performance.

---

## When to Use This Skill

Use this skill when:
- Creating new Genie Spaces for natural language analytics
- Configuring agent behavior and instructions
- Selecting and organizing data assets (Metric Views, TVFs, Tables)
- Writing benchmark questions for validation
- Troubleshooting Genie query routing issues
- Optimizing Genie Space performance

### 🔀 Hand Off to `genie-space-export-import-api` Skill When:

| User Says / Task Involves | Load Instead |
|---|---|
| "deploy Genie Space via API" | `genie-space-export-import-api` |
| "export Genie Space", "download Genie Space config" | `genie-space-export-import-api` |
| "import Genie Space", "restore Genie Space" | `genie-space-export-import-api` |
| "CI/CD for Genie Spaces" | `genie-space-export-import-api` |
| "migrate Genie Space to another workspace" | `genie-space-export-import-api` |
| "back up Genie Space configuration" | `genie-space-export-import-api` |
| "programmatically create Genie Space from JSON" | `genie-space-export-import-api` |
| "`serialized_space`", "REST API", "`/api/2.0/genie/spaces`" | `genie-space-export-import-api` |

**This skill** covers *what* goes into a Genie Space (instructions, assets, benchmarks).
The **export/import API skill** covers *how* to deploy it programmatically.

---

## Upstream: Genie API Updates

The upstream `databricks-genie` skill provides these MCP tools:

| Tool | Purpose |
|------|---------|
| `list_genie` | List all Genie Spaces accessible to you |
| `create_or_update_genie` | Create or update a Genie Space |
| `get_genie` | Get Genie Space details |
| `delete_genie` | Delete a Genie Space |
| `find_genie_by_name` | Look up a Genie Space by name (when you don't have the space_id) |
| `ask_genie` | Ask a question to a Genie Space, get SQL + results |
| `ask_genie_followup` | Ask follow-up question in existing conversation |

**IMPORTANT:** There is NO system table for Genie spaces (e.g., `system.ai.genie_spaces` does NOT exist). To find a Genie space by name, use the `find_genie_by_name` tool.

---

## Critical Rules

### 1. General Instructions Must Be ≤20 Lines

**⚠️ CRITICAL:** Genie processes General Instructions effectively only when ≤20 lines. Longer instructions get truncated or ignored.

**✅ DO:** Keep General Instructions concise and focused on essential routing rules.

**❌ DON'T:** Exceed 20 lines in General Instructions section.

### 2. Benchmark Questions Must Have Working SQL

**Every benchmark question MUST include copy-paste-ready SQL that actually runs.**

**✅ DO:** Include tested SQL with every benchmark question.

**❌ DON'T:** Provide questions without SQL or untested SQL.

### 3. MEASURE() Uses Column Names, NOT Display Names

**The MEASURE() function requires actual column `name`, NOT `display_name`.**

**❌ WRONG:**
```sql
MEASURE(`Total Revenue`)  -- ❌ FAILS: "Total Revenue" is display_name
```

**✅ CORRECT:**
```sql
MEASURE(total_revenue)  -- ✅ Uses actual column name from YAML
```

### 4. Full UC 3-Part Namespace Required

**All table and function references MUST use full Unity Catalog namespace.**

**❌ WRONG:**
```sql
SELECT * FROM fact_sales;
SELECT * FROM get_revenue_by_period('2024-01-01', '2024-12-31', 'week');
```

**✅ CORRECT:**
```sql
SELECT * FROM ${catalog}.${gold_schema}.fact_sales;
SELECT * FROM ${catalog}.${gold_schema}.get_revenue_by_period('2024-01-01', '2024-12-31', 'week');
```

### 5. Data Asset Hierarchy: Metric Views → TVFs → Tables

**Always add assets in this order:**

1. **Metric Views** (Primary - use first)
   - Pre-aggregated, optimized, rich semantics
   - Best for broad analytical queries

2. **TVFs** (Secondary - use for specific patterns)
   - Parameterized queries, business logic
   - Date-bounded queries, top N rankings

3. **Tables** (Last resort - use sparingly)
   - Only when metric views/TVFs insufficient
   - Reference data, ad-hoc exploration

### 6. Avoid Contradictory Routing Rules

**Issue:** Contradictory rules cause Genie to randomly select wrong assets.

**✅ DO:** Group by question type, not asset
```markdown
Revenue/booking questions:
  - By property → revenue_analytics_metrics
  - By host → get_host_performance TVF (not metric view!)
```

**❌ DON'T:** Create conflicting asset mappings
```markdown
- host_analytics_metrics → for host data
- get_host_performance → for host data  # ❌ CONFLICT!
```

### 7. Define Ambiguous Terms Explicitly

**Common ambiguous terms:** "underperforming", "top performing", "valuable customers", "best hosts"

**✅ DO:** Add explicit definitions
```markdown
## Term Definitions
"underperforming" = properties with revenue below median (use get_underperforming_properties TVF)
"top performing" = highest revenue unless "rated" specified
```

### 8. TVF Syntax Rules

**Common errors to prevent:**

**❌ WRONG:**
```sql
SELECT * FROM TABLE(get_customer_segments(...))  -- ❌ Don't wrap in TABLE()
SELECT * FROM get_customer_segments()            -- ❌ Missing parameters
SELECT * FROM get_customer_segments(...) GROUP BY segment  -- ❌ Unnecessary GROUP BY
```

**✅ CORRECT:**
```sql
SELECT * FROM get_customer_segments('2020-01-01', '2024-12-31')  -- ✅ Direct call with params
```

### 9. 🔴 MANDATORY: Serverless SQL Warehouse Only

**ALWAYS assign a Serverless SQL Warehouse to Genie Spaces. NEVER use Classic or Pro warehouses.**

Serverless provides auto-scaling, instant startup, and cost-efficient idle timedowns -- critical for interactive Genie sessions where users expect sub-10-second responses.

**❌ WRONG:** Classic SQL warehouse with manual cluster sizing.

**✅ CORRECT:** Serverless SQL warehouse (auto-detected or explicitly set).

### 10. Table/Column COMMENTs Are Genie Fuel

**Genie uses Unity Catalog TABLE and COLUMN comments to understand data.** Missing comments = degraded SQL generation quality.

**🔴 MANDATORY:** Before adding ANY table as a trusted asset, verify it has:
- `COMMENT ON TABLE` with a business-friendly description
- `COMMENT ON COLUMN` for every column, including dimension values and business context

See [Table Documentation Skill](../../gold/design-workers/06-table-documentation/SKILL.md) for comment standards.

**❌ WRONG:**
```sql
CREATE TABLE fact_sales (sale_id BIGINT, amt DECIMAL(18,2));  -- No comments, cryptic names
```

**✅ CORRECT:**
```sql
CREATE TABLE fact_sales (
  sale_id BIGINT COMMENT 'Unique sale identifier from POS system',
  total_amount DECIMAL(18,2) COMMENT 'Net sale amount in USD after discounts'
) COMMENT 'Daily retail sales transactions at store-SKU grain';
```

### 11. Pre-Creation Table Inspection Is Mandatory

**Before creating a Genie Space, ALWAYS inspect target table schemas.** Do not rely on assumed schemas.

1. Run `DESCRIBE TABLE EXTENDED` or use `get_table_details` for each trusted asset
2. Verify all tables have TABLE and COLUMN comments
3. Verify descriptive column names (use `customer_lifetime_value` NOT `clv`)
4. Verify proper data types (DATE columns for time-based queries)

See [Configuration Guide](references/configuration-guide.md#pre-creation-table-inspection) for the full inspection checklist.

### 12. Prompt User for Benchmark Questions Before Generating

**Always ask the user for benchmark questions before generating synthetic ones.** User-provided questions reflect real business needs and catch domain-specific edge cases that synthetic generation misses.

**Three outcomes:**
- **User provides 10+:** Validate each one. Report any that can't be answered (missing table, ambiguous terms). Proceed with valid set.
- **User provides 1-9:** Validate provided, report issues, augment with synthetic to reach 10-15 total. Show augmentation to user.
- **User provides none:** Generate 10-15 synthetic benchmarks from asset metadata. Show to user for review.

**If a user question can't be answered**, do NOT silently drop it. Inform the user with the specific reason:
- "Table `X` is not a trusted asset in this space"
- "No data available for churn analysis — available domains are: revenue, bookings, property performance"
- "Term 'underperforming' is ambiguous — how should it be defined?"

See [Benchmark Intake Workflow](references/benchmark-intake-workflow.md) for the full validation and generation pipeline.

### 13. Validate Programmatically via Conversation API

**After deployment, test benchmark questions programmatically using the Conversation API -- not just the UI.**

```python
# ✅ Programmatic validation (reproducible, automated)
result = ask_genie(space_id="your_space_id", question="What were total sales last month?")
assert result["status"] == "COMPLETED"
assert result["row_count"] > 0
```

**Key rules:**
- Start a NEW conversation for each unrelated benchmark question
- Use `ask_genie_followup` ONLY for related follow-up questions within the same topic
- Set timeouts: simple queries (30s), complex joins (60-120s), large scans (120s+)

See [Configuration Guide](references/configuration-guide.md#conversation-api-validation) for full testing patterns.

---

## Quick Reference

### Mandatory 7-Section Structure

Every Genie Space setup MUST produce a document with ALL 7 sections:

| Section | Requirement | Key Constraint |
|---------|-------------|----------------|
| **A. Space Name** | `{Project} {Domain} Analytics Space` | Exact format |
| **B. Space Description** | 2-3 sentences | Business context |
| **C. Sample Questions** | 10-15 questions | Grouped by domain |
| **D. Data Assets** | All tables & metric views | Table format |
| **E. General Instructions** | **≤20 LINES** | **CRITICAL LIMIT** |
| **F. TVFs** | All functions with signatures | Detailed specs |
| **G. Benchmark Questions** | 10-15 with **EXACT SQL** | Working SQL required |

**🔴 Missing any section = INCOMPLETE deliverable. NO EXCEPTIONS.**

---

## Core Setup Pattern

### Step 1: Create Space Document Structure

Follow the mandatory 7-section structure (A-G). Use the [configuration template](assets/templates/genie-space-config.yaml) as a starting point.

### Step 2: Write General Instructions (≤20 Lines)

Use the template from [Agent Instructions Guide](references/agent-instructions.md#general-instructions-mandatory-20-lines):

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

### Step 3: Document Data Assets

Add assets in order: Metric Views → TVFs → Tables. Document each with:
- **Metric Views:** Measures, dimensions, use cases
- **TVFs:** Signature, parameters, return schema, use cases
- **Tables:** Purpose, when to use

See [Configuration Guide](references/configuration-guide.md#section-d-data-assets) for detailed patterns.

### Step 4: Write Benchmark Questions (Interactive Intake)

Benchmark questions validate that Genie routes correctly and generates accurate SQL. **Always prompt the user for their questions first before generating synthetic ones.**

#### Three-Path Workflow

| User Provides | Action |
|--------------|--------|
| **10+ questions** | Validate each against available assets. Report any that can't be answered (missing table, ambiguous terms, need more info). Proceed with valid set. |
| **1-9 questions** | Validate provided questions. Report issues. Augment with synthetic benchmarks to reach 10-15 total. |
| **No questions** | Generate 10-15 synthetic benchmarks from metric view measures, TVF signatures, and table schemas. Show to user for review. |

#### Validation Rules for User-Submitted Questions

For each submitted question, verify:

| Check | What to Verify | If Failed, Tell the User |
|-------|---------------|--------------------------|
| **Asset coverage** | At least one MV/TVF/table can answer it | "No asset in this space can answer '{question}'. Available domains: {list}." |
| **Table existence** | SQL only references trusted assets | "SQL references `{table}` which isn't a trusted asset." |
| **MEASURE() columns** | Column names match actual MV columns | "MEASURE({col}) doesn't match any column. Available: {list}." |
| **UC namespace** | SQL uses `${catalog}.${gold_schema}.{object}` | "SQL must use full 3-part UC namespace." |
| **TVF parameters** | All required parameters present | "TVF `{name}` requires: {params}. Missing: {missing}." |
| **Ambiguous terms** | Terms like "underperforming", "top" are defined | "What does '{term}' mean here? Revenue? Ratings? Bookings?" |

**If a question cannot be answered** (missing table, no matching data), inform the user with the specific reason and suggest alternatives based on available assets.

**If a question needs clarification** (ambiguous terms, missing time range), ask the user to clarify before including it.

#### Synthetic Generation (When User Provides None or Few)

Generate benchmarks from available asset metadata:
1. **From Metric Views** — one aggregation question per measure, one grouped question per dimension
2. **From TVFs** — one question per function matching its use case (ranking, time-series, detail)
3. **From Tables** — list/detail questions for dimension tables (only if needed to fill gaps)
4. **Category coverage** — ensure at least 4 categories: aggregation, ranking, time-series, comparison, list

After generation, **show the synthetic benchmarks to the user** for review before proceeding.

#### Augmentation (When User Provides Partial Set)

When augmenting user-provided questions:
1. **User questions always take priority** — never replace them
2. **Fill category gaps first** — if user only provided aggregation questions, add ranking/time-series/list
3. **Add synonym variations** — test Genie handles "total spend" vs "how much spent" vs "total costs"
4. **Add date variations** — "this month" vs "last 30 days" vs "Q1 2026"
5. **Cap at 15 total** — user questions + synthetic augmentation

See [Benchmark Intake Workflow](references/benchmark-intake-workflow.md) for the full validation pipeline, generation patterns, and augmentation strategy.

#### Output Format for Each Benchmark

Every question must include:
- Natural language question
- Expected SQL (tested and working)
- Expected result description

**⚠️ JSON field name:** In the API-compatible JSON export, benchmark SQL goes in `answer: [{format: "SQL", content: ["SELECT ..."]}]` — **NOT** in a field called `expected_sql`. The term "Expected SQL" here refers to the content, not the JSON field name. See `genie-space-export-import-api` for the exact `BenchmarkQuestion` schema.

See [Configuration Guide](references/configuration-guide.md#section-g-benchmark-questions) for format.

### Step 5: Deploy and Test

**Choose your deployment path:**

| Method | When to Use | Skill |
|---|---|---|
| **UI** | One-off setup, manual curation | This skill (continue below) |
| **REST API / CI/CD** | Automated deployment, cross-workspace migration, version control | **Load [`genie-space-export-import-api`](../genie-space-export-import-api/SKILL.md)** |

**UI deployment steps:**
1. Inspect all target table schemas (verify comments, column names, data types)
2. Create Genie Space in Databricks UI with **Serverless SQL Warehouse**
3. Add trusted assets in order (Metric Views → TVFs → Tables) -- **Gold layer ONLY**
4. Set General Instructions (copy exactly, verify ≤20 lines)
5. Test benchmark questions **programmatically** via Conversation API
6. Validate routing, response quality, and follow-up context

**API deployment steps:** Load the `genie-space-export-import-api` skill for:
- JSON schema structure (`serialized_space` format)
- Template variable substitution (`${catalog}`, `${gold_schema}`)
- Asset inventory-driven generation (prevents "table doesn't exist" errors)
- Export/import scripts (`export_genie_space.py`, `import_genie_space.py`)

See [Configuration Guide](references/configuration-guide.md#deployment-checklist) for complete steps.

---

## Reference Files

Detailed guides are available in the `references/` directory:

### [Configuration Guide](references/configuration-guide.md)
Complete guide for the mandatory 7-section structure:
- Section A-G detailed formats
- Extended space description patterns
- Data asset organization patterns
- Testing and validation procedures
- Deployment checklist
- Success metrics

### [Agent Instructions Guide](references/agent-instructions.md)
Comprehensive patterns for writing effective instructions:
- Extended instructions template (200-500 lines, optional)
- General Instructions consistency patterns
- Ambiguous term definitions
- Metric View vs TVF routing decision table
- TVF syntax guidance
- Professional language standards

### [Troubleshooting Guide](references/troubleshooting.md)
Common issues, debugging steps, and verification procedures:
- Common routing issues and solutions
- MEASURE() function errors
- UC namespace problems
- TVF syntax errors
- Debugging procedures
- Verification checklists

### [Benchmark Intake Workflow](references/benchmark-intake-workflow.md)
Interactive workflow for accepting, validating, and augmenting benchmark questions:
- Three-path intake (full, partial, none)
- Per-question validation pipeline (asset coverage, table existence, MEASURE() columns)
- Synthetic generation from asset metadata
- Augmentation strategy with category coverage
- User feedback templates for issues and suggestions

### [Trusted Assets Guide](references/trusted-assets.md)
Complete guide for organizing and documenting data assets:
- Metric View documentation patterns
- TVF documentation patterns
- Asset selection best practices
- Performance considerations
- Asset organization checklist

### [Genie Space Export - Formatted](references/genie_space_export_formatted.json)
Production-grade Genie Space export JSON (pretty-printed) showing the complete `GenieSpaceExport` schema:
- Full `serialized_space` structure with parsed objects (not nested string)
- All sections: `config.sample_questions`, `data_sources` (tables, metric_views), `instructions` (text, sql_functions, join_specs), `benchmarks`
- Column configs with `get_example_values` and `build_value_dictionary` patterns
- Join specs with relationship type annotations (`--rt=FROM_RELATIONSHIP_TYPE_MANY_TO_ONE--`)
- Benchmark questions with complete SQL answers using `MEASURE()` syntax
- **Use as the primary reference** when creating new Genie Spaces programmatically
- Uses `${catalog}`, `${gold_schema}`, `${warehouse_id}`, `${space_id}`, `${project_name}` template variables

### [Genie Space Export - Compact](references/genie_space_export.json)
Same Genie Space export in original API format (compact, `serialized_space` as escaped string):
- Exact format returned by `GET /api/2.0/genie/spaces/{space_id}`
- `serialized_space` field is a JSON string (not parsed object)
- **Use as the reference** for understanding raw API response format
- Useful for import/export scripts and CI/CD pipelines

---

## Assets

### Templates

#### [Genie Space Config Template](assets/templates/genie-space-config.yaml)
Starter YAML template for structuring Genie Space setup documents:
- All 7 sections with placeholders
- Deployment configuration
- Testing and training checklists

---

## Validation Checklist

Before submitting ANY Genie Space document:

| Section | Requirement | Complete? |
|---------|-------------|-----------|
| **A. Space Name** | Exact name in format `{Project} {Domain} Analytics Space` | ☐ |
| **B. Space Description** | 2-3 sentences describing purpose and users | ☐ |
| **C. Sample Questions** | 10-15 questions grouped by domain | ☐ |
| **D. Data Assets** | ALL metric views, dimensions, facts in table format | ☐ |
| **E. General Instructions** | **≤20 lines** of LLM behavior rules | ☐ |
| **F. TVFs** | ALL functions with signatures and examples | ☐ |
| **G. Benchmark Questions** | 10-15 questions with **EXACT working SQL** | ☐ |

### Additional Quality Checks

- [ ] General Instructions are EXACTLY 20 lines or less (not 21+)
- [ ] User was prompted for benchmark questions before synthetic generation
- [ ] User-submitted questions validated against available assets
- [ ] Invalid user questions reported back with specific reasons (not silently dropped)
- [ ] Benchmark suite has 10-15 questions with 4+ categories covered
- [ ] Every benchmark question has copy-paste-ready SQL
- [ ] SQL in benchmarks actually runs (tested)
- [ ] MEASURE() uses actual column names (not display_name with backticks)
- [ ] All tables/functions have full 3-part UC namespace
- [ ] Metric views documented with measures and dimensions
- [ ] TVFs documented with parameters, returns, and use cases
- [ ] Questions cover all major use cases (revenue, performance, trends)
- [ ] No contradictory routing rules in General Instructions
- [ ] Ambiguous terms explicitly defined
- [ ] Serverless SQL Warehouse assigned (NOT Classic or Pro)
- [ ] ALL trusted asset tables have TABLE and COLUMN comments
- [ ] Column names are descriptive (`customer_lifetime_value` NOT `clv`)
- [ ] Table schemas inspected before space creation (DESCRIBE TABLE EXTENDED)
- [ ] Benchmark questions validated programmatically via Conversation API
- [ ] Only Gold layer tables/views/functions used as trusted assets

---

## Common Mistakes to Avoid

| Mistake | Why It Fails |
|---|---|
| General Instructions > 20 lines | Genie won't process effectively past 20 lines |
| Benchmark questions without SQL | Cannot validate Genie responses |
| Display names in MEASURE() | Requires actual column names from YAML |
| Partial UC namespaces | Always use full 3-part: `${catalog}.${schema}.{object}` |
| Only tables as trusted assets | Start with Metric Views for better performance |
| Contradictory routing rules | Group by question type, not asset |
| Undefined ambiguous terms | Define "underperforming", "top performing" explicitly |
| Incorrect TVF syntax | No TABLE() wrapper, include all params, no extra GROUP BY |
| Classic/Pro SQL Warehouse | ALWAYS use Serverless (fast startup, auto-scaling) |
| Tables without comments | Genie uses UC metadata; missing = worse SQL |
| Cryptic column names (`clv`) | Use descriptive (`customer_lifetime_value`) for accuracy |
| Skipping table inspection | DESCRIBE TABLE EXTENDED before adding assets |
| UI-only testing | Validate programmatically via Conversation API |
| Reusing conversations across topics | New conversation per topic; `ask_genie_followup` only for related |
| Silver/Bronze as trusted assets | Gold layer only; Silver/Bronze lack business semantics |

---

## References

### Official Databricks Documentation
- [Genie Overview](https://docs.databricks.com/genie/)
- [Create a Genie Space](https://docs.databricks.com/genie/create-space.html)
- [Add Trusted Assets](https://docs.databricks.com/genie/trusted-assets.html)
- [Query with Genie](https://docs.databricks.com/genie/query.html)
- [Metric Views Documentation](https://docs.databricks.com/metric-views/)

### Related Skills
- **`genie-space-export-import-api`** - Programmatic deployment, export/import, CI/CD, migration via REST API
- `metric-views-patterns` - Metric view YAML structure
- `databricks-table-valued-functions` - TVF patterns
- `databricks-asset-bundles` - Asset Bundle deployment

---

## Version History

- **v2.3** (Feb 2026) — JSON field name clarification for benchmark SQL (answer vs expected_sql)
- **v2.2** (Feb 20, 2026) - Interactive benchmark question intake
  - Added Rule 12: Prompt user for benchmark questions before generating synthetic ones
  - Added three-path benchmark intake workflow (full, partial, none)
  - Added per-question validation pipeline (asset coverage, table existence, MEASURE() columns, ambiguity detection)
  - Added synthetic benchmark generation from asset metadata (MVs, TVFs, tables)
  - Added augmentation strategy for partial submissions with category coverage
  - Added user feedback templates for invalid/needs-info questions
  - New reference: `benchmark-intake-workflow.md`
  - Updated Step 4 with interactive intake flow
  - Updated validation checklist with benchmark intake checks
  - Renumbered Rule 12→13 (Conversation API validation)
  - **Key Learning:** User-provided questions catch domain-specific edge cases that synthetic generation misses; always ask first

- **v2.1** (Feb 6, 2026) - Genie reference material integration
  - Added Rule 9: Serverless SQL Warehouse mandatory
  - Added Rule 10: Table/Column COMMENT requirements for Genie
  - Added Rule 11: Pre-creation table inspection mandatory
  - Added Rule 12: Programmatic validation via Conversation API
  - Added Gold-layer-only trusted assets mandate
  - Added descriptive column naming requirement
  - Added follow-up vs new conversation pattern
  - Added 8 new Common Mistakes to Avoid
  - Updated validation checklist with 6 new checks
  - Updated deployment steps with inspection and API testing
  - **Key Learning:** Genie uses UC metadata (comments, column names) directly -- missing metadata degrades SQL quality

- **v2.0** (Dec 16, 2025) - Genie optimization patterns from production post-mortem
  - Added General Instructions consistency patterns
  - Added ambiguous term definitions
  - Added Metric View vs TVF routing decision table
  - Added TVF syntax guidance
  - Added professional language standards
  - **Key Learning:** Contradictory rules caused 40% of Genie misrouting

- **v1.0** (Jan 2025) - Initial skill based on Genie Space deployment
  - 7-section mandatory structure
  - Benchmark questions with SQL requirement
  - Extended instructions template

## Genie Space Notes to Carry Forward

After completing Genie Space configuration, carry these notes to the next worker:
- **Genie Space names and JSON paths:** List of all configured spaces with their JSON config file paths
- **Asset assignments per space:** Which Metric Views, TVFs, and Gold Tables are assigned to each space
- **Benchmark question counts:** Number of benchmark questions per space (minimum 10 required)
- **Warehouse assignment:** SQL Warehouse ID assigned to each space
- **Space IDs (if deployed):** Genie Space IDs returned from API creation (needed for idempotent re-deployment)
- **Template variables used:** Confirm `${catalog}` and `${gold_schema}` are used for portability

## Next Step

After Genie Space JSON configs are generated, proceed to:
**`semantic-layer/04-genie-space-export-import-api/SKILL.md`** — If deploying via REST API (recommended for cross-environment promotion). Otherwise, proceed to Phase 4 (Asset Bundle Configuration) in the orchestrator.
