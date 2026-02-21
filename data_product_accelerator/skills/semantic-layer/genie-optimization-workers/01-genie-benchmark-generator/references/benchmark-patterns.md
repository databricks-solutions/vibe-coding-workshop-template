> **Standalone usage:** This reference can be used independently of the orchestrator. Load when writing benchmark questions or reviewing coverage for any Genie Space.

# Benchmark Question Patterns

Complete guide to writing effective benchmark questions for Genie Space optimization.

---

## Benchmark Question Structure

Every benchmark question must include:

```yaml
- id: "domain_NNN"           # Unique identifier (domain_001, domain_002, ...)
  question: "Natural language question"
  expected_sql: "Full SQL query that returns correct result"
  expected_asset: "MV|TVF|TABLE"   # Which asset should Genie use
  category: "aggregation|list|time-series|comparison|detail|ranking"
```

---

## Category Coverage

A complete benchmark suite should cover these categories:

| Category | Description | Expected Asset | Example |
|----------|-------------|----------------|---------|
| **Aggregation** | Total, average, sum, count | Metric View | "What is total revenue?" |
| **Ranking** | Top N, bottom N, highest, lowest | TVF | "Show top 10 customers" |
| **Time-series** | Trends, daily/weekly/monthly | TVF | "Daily sales for last month" |
| **Comparison** | Year-over-year, period vs period | TVF or MV | "Sales this quarter vs last" |
| **Detail** | Specific entity lookup, drill-down | TVF | "Details for customer X" |
| **List** | Show me, which, enumerate | TVF | "Which workspaces are active?" |
| **Threshold** | Above/below/exceeds criteria | TVF | "Jobs running over 2 hours" |
| **Prediction** | Forecast, expected, projected | ML Table | "Predicted demand next month" |

### Minimum Coverage

| Domain Size | Questions | Categories Required |
|-------------|-----------|---------------------|
| Small (1-3 tables) | 10 | At least 4 categories |
| Medium (4-8 tables) | 15 | At least 6 categories |
| Large (9+ tables) | 20-25 | All 8 categories |

---

## Writing Effective Questions

### Rule 1: Use Natural Language

Write questions the way a business user would ask them, not like SQL:

```yaml
# WRONG - too technical
- question: "SELECT SUM(total_cost) FROM fact_usage WHERE date >= '2025-01-01'"

# CORRECT - natural language
- question: "What is our total compute spend this year?"
```

### Rule 2: Cover Synonyms

Test that Genie handles common synonyms:

```yaml
# Same intent, different wording
- id: "cost_001"
  question: "What is total spend?"
- id: "cost_002"
  question: "How much have we spent?"
- id: "cost_003"
  question: "What are our total costs?"
```

### Rule 3: Test Ambiguous Phrases

Include questions with ambiguous terms to verify Genie handles them correctly:

```yaml
- id: "perf_010"
  question: "Show me underperforming workspaces"
  # Ambiguous: underperforming = by cost? by jobs? by latency?
  # Instructions should define this term explicitly
```

### Rule 4: Include Date Variations

Test various time-range patterns:

```yaml
- id: "cost_010"
  question: "What is total spend this month?"
  expected_sql: "... WHERE date >= DATE_TRUNC('month', CURRENT_DATE())"

- id: "cost_011"
  question: "Show costs for last 30 days"
  expected_sql: "... WHERE date >= DATEADD(DAY, -30, CURRENT_DATE())"

- id: "cost_012"
  question: "What was January's spend?"
  expected_sql: "... WHERE date BETWEEN '2026-01-01' AND '2026-01-31'"

- id: "cost_013"
  question: "Compare this quarter to last quarter"
  expected_sql: "... (two subqueries with quarter boundaries)"
```

### Rule 5: Test Edge Cases

```yaml
# Null handling
- id: "edge_001"
  question: "How many workspaces have no cost data?"
  expected_sql: "... WHERE total_cost IS NULL OR total_cost = 0"

# Empty results
- id: "edge_002"
  question: "Show failed jobs from 2020"
  expected_sql: "... WHERE year = 2020"  # May return 0 rows

# Large result sets
- id: "edge_003"
  question: "List all workspaces"
  expected_sql: "SELECT * FROM dim_workspace ORDER BY ..."
```

---

## SQL Expectations

### Metric View Queries

```yaml
- id: "mv_001"
  question: "What is total cost?"
  expected_sql: |
    SELECT MEASURE(total_cost)
    FROM ${catalog}.${schema}.mv_cost_analytics
  expected_asset: "MV"

- id: "mv_002"
  question: "Average daily cost by workspace"
  expected_sql: |
    SELECT workspace_name, MEASURE(avg_daily_cost)
    FROM ${catalog}.${schema}.mv_cost_analytics
    GROUP BY workspace_name
    ORDER BY MEASURE(avg_daily_cost) DESC
  expected_asset: "MV"
```

### TVF Queries

```yaml
- id: "tvf_001"
  question: "Show top 10 costliest workspaces"
  expected_sql: |
    SELECT * FROM ${catalog}.${schema}.get_top_cost_contributors('30', 'workspace')
    LIMIT 10
  expected_asset: "TVF"

- id: "tvf_002"
  question: "Daily cost breakdown for last week"
  expected_sql: |
    SELECT * FROM ${catalog}.${schema}.get_daily_cost_summary(
      DATE_SUB(CURRENT_DATE(), 7),
      CURRENT_DATE()
    )
  expected_asset: "TVF"
```

### Table Queries (Rare)

```yaml
- id: "tbl_001"
  question: "What SKU categories do we have?"
  expected_sql: |
    SELECT DISTINCT sku_category, sku_description
    FROM ${catalog}.${schema}.dim_sku
    ORDER BY sku_category
  expected_asset: "TABLE"
```

---

## Domain-Specific Patterns

### Cost Intelligence

```yaml
cost:
  - id: "cost_001"
    question: "What is our total compute spend this month?"
    expected_sql: "SELECT MEASURE(total_cost) FROM mv_cost_analytics WHERE ..."
    expected_asset: "MV"
    category: "aggregation"

  - id: "cost_002"
    question: "Which workspaces are most expensive?"
    expected_sql: "SELECT * FROM get_top_cost_contributors('30', 'workspace')"
    expected_asset: "TVF"
    category: "ranking"

  - id: "cost_003"
    question: "Show daily cost trend for the last 2 weeks"
    expected_sql: "SELECT * FROM get_daily_cost_summary(...)"
    expected_asset: "TVF"
    category: "time-series"
```

### Reliability

```yaml
reliability:
  - id: "rel_001"
    question: "What is our overall job success rate?"
    expected_sql: "SELECT MEASURE(success_rate) FROM mv_reliability_metrics"
    expected_asset: "MV"
    category: "aggregation"

  - id: "rel_002"
    question: "Show the top 10 most frequently failing jobs"
    expected_sql: "SELECT * FROM get_top_failing_jobs('30', '10')"
    expected_asset: "TVF"
    category: "ranking"

  - id: "rel_003"
    question: "Which jobs failed yesterday?"
    expected_sql: "SELECT * FROM get_failed_jobs('1')"
    expected_asset: "TVF"
    category: "list"
```

### Security

```yaml
security:
  - id: "sec_001"
    question: "How many security events occurred this week?"
    expected_sql: "SELECT MEASURE(event_count) FROM mv_security_metrics WHERE ..."
    expected_asset: "MV"
    category: "aggregation"

  - id: "sec_002"
    question: "Show suspicious access patterns"
    expected_sql: "SELECT * FROM get_security_anomalies('7')"
    expected_asset: "TVF"
    category: "list"
```

---

## Benchmark Intake Validation

Before writing or generating benchmarks, determine the intake path:

### Decision Flow

```
User provides benchmark questions?
│
├── YES (10+ questions)
│   → Validate each against live Genie Space
│   → Report invalid (missing table, no data) with specific reason
│   → Report needs-info (ambiguous terms) with clarification request
│   → Proceed with valid set
│
├── YES (1-9 questions)
│   → Validate each against live Genie Space
│   → Report issues to user
│   → Augment with synthetic to reach 10-15
│   → Show augmentation report for review
│
└── NO (0 questions)
    → Inspect Genie Space trusted assets
    → Generate 10-15 synthetic benchmarks
    → Show to user for review before proceeding
```

### Per-Question Validation

For each user-submitted question, verify:

| Check | Pass Criteria | Failure Action |
|-------|--------------|----------------|
| **Trusted asset match** | At least one MV/TVF/table in the space answers it | Tell user: "No trusted asset can answer this. Available: {list}" |
| **SQL references** | All objects in SQL are trusted in the space | Tell user: "'{table}' isn't a trusted asset. Add it or rewrite." |
| **MEASURE() columns** | Column names exist in MV schema | Tell user: "MEASURE({col}) invalid. Available: {list}" |
| **Ambiguous terms** | Terms defined in Genie Instructions or question | Ask user: "What does '{term}' mean here?" |
| **UC namespace** | SQL uses `${catalog}.${gold_schema}.{object}` | Tell user: "SQL must use full 3-part namespace" |

### Synthetic Generation Strategy

Generate from asset metadata in this priority:

1. **Metric View measures** → aggregation questions (one per measure)
2. **Metric View dimensions** → grouped aggregation questions
3. **TVF signatures** → ranking/time-series/detail questions (one per TVF)
4. **Tables** → list/detail questions (only to fill gaps)
5. **Category fillers** → ensure 4+ categories covered

### Augmentation Rules

When augmenting partial user submissions:

1. User questions always preserved (never replaced)
2. Fill category gaps first (aggregation, ranking, time-series, comparison, list)
3. Fill asset type gaps (if user only tests MVs, add TVF questions)
4. Add synonym variations (2 per key user question)
5. Add date variations ("this month" → "last 30 days" → "Q1 2026")
6. Cap at 15 total

See [Benchmark Intake Workflow](benchmark-intake-workflow.md) for full implementation details.

---

## Validation Checklist

Before running benchmarks:

- [ ] User was prompted for benchmark questions before synthetic generation
- [ ] User-submitted questions validated against live Genie Space trusted assets
- [ ] Invalid questions reported to user with specific reasons (not silently dropped)
- [ ] Every question has a unique `id` (domain_NNN format)
- [ ] Every question has `expected_sql` that actually runs
- [ ] Every question has `expected_asset` (MV, TVF, or TABLE)
- [ ] Every question has a `category` tag
- [ ] Every question has a `source` tag (user, synthetic, augmented)
- [ ] At least 4 different categories covered
- [ ] Synonym variations included (3+ for key queries)
- [ ] Date range variations tested (this month, last 30 days, specific dates)
- [ ] Edge cases included (nulls, empty results)
- [ ] SQL uses full 3-part UC namespace (`${catalog}.${schema}.object`)
- [ ] MEASURE() uses column names, not display names
- [ ] TVF calls include all required parameters
- [ ] At least 10 questions per domain

---

## Generating Benchmarks from Existing Assets

### From Metric Views

For each metric view, generate at least 2 questions:

```python
# Pattern: For each measure, create an aggregation question
for measure in metric_view["measures"]:
    question = f"What is the {measure['description'].lower()}?"
    expected_sql = f"SELECT MEASURE({measure['name']}) FROM {metric_view['source']}"
    # Add as benchmark
```

### From TVFs

For each TVF, generate at least 3 questions:

```python
# Pattern: For each TVF, test basic call + parameter variations
# 1. Basic call with default parameters
# 2. Call with specific date range
# 3. Call with different grouping/filter
```

### From Business Requirements

Map each business requirement to 1-2 benchmark questions:

```
Requirement: "Users need to see cost by department"
→ Benchmark: "What is total cost by department?"
→ Benchmark: "Which department has the highest spend?"
```

---

## Ground Truth Validation

Every ground truth SQL must be executed on the warehouse before acceptance into the benchmark. This prevents "chasing wrong ground truth" — optimizing metadata toward incorrect SQL wastes iterations.

### Validation Flow

```
expected_sql → spark.sql(sql) → success?
├── YES → store result_hash, result_sample, row_count → accept
└── NO  → LLM regenerates SQL (max 3 attempts)
          ├── attempt 2 succeeds → store results → accept
          ├── attempt 3 succeeds → store results → accept
          └── all 3 fail → flag for human review
```

### What Gets Stored

| Field | Type | Description |
|-------|------|-------------|
| `expected_result_hash` | MD5 string | Hash of the result DataFrame (CSV bytes) |
| `expected_result_sample` | JSON string | First 5 rows as JSON for quick comparison |
| `expected_row_count` | integer | Total row count for structural checks |

These fields enable the `result_correctness` scorer (Layer 2) to compare actual vs expected results without re-executing the ground truth SQL every iteration.

### Code Pattern

```python
result = validate_ground_truth_sql(q["expected_sql"], spark)
if result["valid"]:
    q["expected_result_hash"] = result["result_hash"]
    q["expected_result_sample"] = result["result_sample"]
    q["expected_row_count"] = result["row_count"]
else:
    # LLM regeneration with retry
    result = validate_with_retry(q["expected_sql"], spark, llm_regenerate_fn, max_attempts=3)
```

See `optimization-code-patterns.md` §Ground Truth Validation for the full implementation.

---

## MLflow Evaluation Dataset Mapping

The golden-queries YAML is the human-friendly authoring format. It maps to MLflow Evaluation Dataset records for programmatic evaluation.

### YAML → MLflow Field Mapping

| YAML Field | MLflow Field | Required |
|------------|-------------|----------|
| `question` | `inputs.question` | Yes |
| `expected_sql` | `expectations.expected_response` | Yes |
| `expected_asset` | `expectations.expected_asset` | Yes |
| `category` | `expectations.category` / `inputs.category` | Yes |
| `expected_facts` | `expectations.expected_facts` | No |
| `guidelines` | `expectations.guidelines` | No |
| `expected_result_hash` | `expectations.expected_result_hash` | No (auto-populated by GT validation) |
| `expected_result_sample` | `expectations.expected_result_sample` | No (auto-populated) |
| `expected_row_count` | `expectations.expected_row_count` | No (auto-populated) |
| `required_tables` | `expectations.required_tables` | No |
| `required_columns` | `expectations.required_columns` | No |
| `required_joins` | `expectations.required_joins` | No |
| `required_business_logic` | `expectations.required_business_logic` | No |

### MLflow Dataset Limits

- Max **2,000 rows** per dataset
- Max **20 expectations** per record
- Requires `CREATE TABLE` permission in Unity Catalog

### Sync Code

```python
dataset_name = sync_yaml_to_mlflow_dataset(yaml_path, uc_schema, domain)
```

See `optimization-code-patterns.md` §MLflow Dataset Sync.

---

## Metadata Dependency Map

For introspective analysis, each benchmark can optionally declare which metadata it depends on. This helps the optimizer identify which control lever changes will affect which questions.

### Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `required_tables` | list[str] | UC tables referenced by expected SQL | `["fact_usage", "dim_workspace"]` |
| `required_columns` | list[str] | Specific columns needed | `["total_cost", "workspace_name"]` |
| `required_joins` | list[str] | Join relationships expected | `["fact_usage.workspace_id = dim_workspace.id"]` |
| `required_business_logic` | list[str] | Business rules the SQL implements | `["Sum cost over last 30 days"]` |

These fields are auto-populated from `expected_sql` during the benchmark intake workflow, or can be manually specified for complex questions.

### Auto-Population from SQL

```python
def extract_dependencies(expected_sql: str) -> dict:
    """Parse expected_sql to extract table/column references."""
    sql_lower = expected_sql.lower()
    tables = re.findall(r'from\s+([\w.]+)', sql_lower) + re.findall(r'join\s+([\w.]+)', sql_lower)
    return {
        "required_tables": list(set(tables)),
        "required_columns": [],  # requires deeper SQL parsing
        "required_joins": [],
    }
```
