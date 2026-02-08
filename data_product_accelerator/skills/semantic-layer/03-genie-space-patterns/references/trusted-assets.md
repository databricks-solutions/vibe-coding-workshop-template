# Trusted Assets Setup Guide

Complete guide for organizing and documenting data assets (Metric Views, TVFs, Tables) for Genie Spaces.

## Data Assets Organization Pattern

### Hierarchy: Metric Views → TVFs → Tables

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

---

## Metric View Documentation Pattern

```markdown
#### [Metric View Display Name]

**Fully Qualified Name:**
```
[catalog].[schema].[metric_view_name]
```

**Description for Genie:**
```
[One-sentence purpose]. [Pre-aggregation details].

DIMENSIONS AVAILABLE:
• [Domain 1]: [dim1], [dim2], [dim3] ([classification details])
• [Domain 2]: [dim1], [dim2], [dim3]
• [Domain 3]: [dim1], [dim2], [dim3]

MEASURES AVAILABLE ([N]+ metrics):
• [Category 1]: [measure1], [measure2], [measure3]
• [Category 2]: [measure1], [measure2], [measure3]
• [Category 3]: [measure1], [measure2], [measure3]

WINDOW MEASURES (Time Intelligence):
• Rolling [N]-day: [measure1]_last_[N]_days, [measure2]_last_[N]_days
• Rolling [N]-day: [measure1]_last_[N]_days
• Year-over-Year: [measure]_yoy, [measure]_yoy_growth

TYPICAL USE CASES:
✓ "[Example question 1]"
✓ "[Example question 2]"
✓ "[Example question 3]"
```

**Example Questions:**
```
• [Question 1]
• [Question 2]
• [Question 3]
• [Question 4]
• [Question 5]
```
```

---

## TVF Documentation Pattern

```markdown
#### [Function Display Name]

**Fully Qualified Name:**
```
[catalog].[schema].[function_name]
```

**Description:**
```
[Purpose statement].

PARAMETERS:
• [param1]: [Description and data type]
• [param2]: [Description and default value if applicable]

RETURNS:
• [col1], [col2], [col3], [col4]

USE WHEN:
[Scenario description], e.g., "[Example natural language query]"
```
```

---

## Common Mistakes to Avoid

### ❌ DON'T: Add Only Tables as Trusted Assets
```markdown
# BAD: No pre-aggregation, poor performance
Trusted Data:
- fact_sales (100M rows)
- fact_inventory (50M rows)
```

### ✅ DO: Add Metric Views First
```markdown
# GOOD: Pre-aggregated, optimized, rich semantics
Trusted Data:
- sales_performance_metrics (metric view, 1M rows, 30+ measures)
- inventory_health_metrics (metric view, 500K rows, 15+ measures)
- get_sales_trend(days_back) (TVF for common pattern)
```

---

## Data Assets Table Format

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

---

## TVF Table Format

| Function Name | Signature | Purpose | When to Use |
|---------------|-----------|---------|-------------|
| get_{query} | `get_{query}(param TYPE)` | {purpose} | {scenario} |

### TVF Details

#### get_{query1}
- **Signature:** `get_{query1}(param STRING, start_date DATE, end_date DATE)`
- **Returns:** {description of columns}
- **Use When:** {specific question pattern}
- **Example:** `SELECT * FROM get_{query1}('value', CURRENT_DATE - 30, CURRENT_DATE)`

---

## Asset Selection Best Practices

### When to Use Metric Views

- General analytical queries without specific parameters
- Multi-dimensional analysis (group by multiple dimensions)
- Standard aggregations (SUM, COUNT, AVG)
- Rolling window calculations (use window measures)
- Year-over-year comparisons (use YoY measures)

**Example:**
```sql
-- ✅ GOOD: Use metric view for general revenue analysis
SELECT 
  property_type,
  MEASURE(total_revenue) as revenue
FROM revenue_analytics_metrics
GROUP BY property_type
ORDER BY revenue DESC;
```

### When to Use TVFs

- Parameterized queries (date ranges, top N, filters)
- Complex business logic (multi-step calculations)
- Specific question patterns (trends, comparisons)
- Individual entity lookups (who are the top customers?)
- Pre-filtered datasets (underperforming properties)

**Example:**
```sql
-- ✅ GOOD: Use TVF for date-bounded trend analysis
SELECT * FROM get_revenue_by_period(
  '2024-01-01', 
  '2024-12-31', 
  'week'
);
```

### When to Use Tables

- When metric views don't have required columns
- When TVFs don't support the query pattern
- For reference data lookups (dimension tables)
- For ad-hoc exploration (sparingly)

**Example:**
```sql
-- ✅ GOOD: Use dimension table for attribute lookups
SELECT 
  property_id,
  property_name,
  property_type
FROM dim_property
WHERE property_type = 'Apartment';
```

---

## Performance Considerations

### Metric Views
- **Pre-aggregated** - Faster queries
- **Optimized** - Automatic clustering and indexing
- **Rich semantics** - Many measures and dimensions
- **Window measures** - Pre-calculated rolling windows

### TVFs
- **Parameterized** - Flexible queries
- **Business logic** - Encapsulated calculations
- **Filtered** - Pre-applied filters reduce data scan
- **Optimized** - Can use Z-ORDER and clustering

### Tables
- **Raw data** - Full table scans
- **Slower** - No pre-aggregation
- **Flexible** - Can query any column
- **Use sparingly** - Only when necessary

---

## 🔴 MANDATORY: Gold Layer Assets ONLY

**NEVER add Bronze or Silver tables as Genie trusted assets.**

| Layer | Allow as Trusted Asset? | Reason |
|-------|------------------------|--------|
| **Gold** | ✅ YES | Business-level semantics, LLM-friendly comments, proper naming |
| **Silver** | ❌ NO | Technical cleansing layer, no business context, streaming internals |
| **Bronze** | ❌ NO | Raw ingestion, data quality issues, no governance metadata |

**Why this matters:**
- Gold tables have `COMMENT ON TABLE` and `COMMENT ON COLUMN` that Genie uses for SQL generation
- Gold tables have descriptive column names (`customer_lifetime_value` not `clv`)
- Gold tables have PK/FK constraints that help Genie understand joins
- Silver/Bronze tables expose internal ETL structure that confuses Genie

---

## 🔴 MANDATORY: Table/Column Comments for Genie

**Genie reads Unity Catalog metadata to understand your data.** Every trusted asset MUST have:

### Table Comments
```sql
-- ✅ CORRECT: Business-friendly, describes grain and scope
COMMENT ON TABLE ${catalog}.${gold_schema}.fact_sales IS
  'Daily retail sales transactions at store-SKU grain. Includes net revenue, discounts, and returns.';

-- ❌ WRONG: Missing comment or technical jargon
-- (no comment set)
-- 'Silver deduplicated output from CDC stream'
```

### Column Comments
```sql
-- ✅ CORRECT: Business meaning, valid values, format hints
COMMENT ON COLUMN ${catalog}.${gold_schema}.fact_sales.total_amount IS
  'Net sale amount in USD after discounts and before tax. Always >= 0.';

COMMENT ON COLUMN ${catalog}.${gold_schema}.dim_customer.segment IS
  'Customer segment: Enterprise, Mid-Market, SMB, or Individual. Assigned by annual spend tier.';

-- ❌ WRONG: No comment or technical description
-- (no comment set)
-- 'decimal(18,2) nullable'
```

### Pre-Addition Verification Query
```sql
-- Run this for EVERY table before adding as trusted asset
SELECT
  t.table_name,
  t.comment AS table_comment,
  c.column_name,
  c.comment AS column_comment
FROM information_schema.tables t
JOIN information_schema.columns c
  ON t.table_catalog = c.table_catalog
  AND t.table_schema = c.table_schema
  AND t.table_name = c.table_name
WHERE t.table_catalog = '${catalog}'
  AND t.table_schema = '${gold_schema}'
  AND t.table_name = '${table_name}'
ORDER BY c.ordinal_position;

-- ❌ REJECT if table_comment IS NULL
-- ❌ REJECT if ANY column_comment IS NULL
```

---

## Column Naming Requirements for Genie

**Genie generates better SQL when column names are self-documenting.**

| ❌ WRONG (Cryptic) | ✅ CORRECT (Descriptive) | Why It Matters |
|---|---|---|
| `clv` | `customer_lifetime_value` | Genie maps "lifetime value" → column name |
| `amt` | `total_amount` | Genie maps "total" or "amount" → column name |
| `dt` | `transaction_date` | Genie maps "date" or "when" → column name |
| `ws_id` | `workspace_id` | Genie maps "workspace" → column name |
| `cat` | `product_category` | Genie maps "category" → column name |
| `is_biz` | `is_business_booking` | Genie maps "business booking" → column name |

**Rule:** If a column name requires a comment to be understood, the name itself is too cryptic. Rename it.

---

## Asset Documentation Checklist

For each Metric View:
- [ ] Fully qualified name (catalog.schema.view_name)
- [ ] One-sentence purpose description
- [ ] List of key dimensions
- [ ] List of key measures (categorized)
- [ ] Window measures (if applicable)
- [ ] 3-5 example use cases/questions
- [ ] Source table has TABLE and COLUMN comments
- [ ] All column names are descriptive (no abbreviations)

For each TVF:
- [ ] Fully qualified name (catalog.schema.function_name)
- [ ] Complete signature with parameter types
- [ ] Parameter descriptions
- [ ] Return column descriptions
- [ ] When to use (specific scenarios)
- [ ] Example query
- [ ] Function COMMENT set with purpose and parameter guidance

For each Table:
- [ ] Fully qualified name (catalog.schema.table_name)
- [ ] Purpose (why include in Genie Space)
- [ ] Key columns
- [ ] Grain (for fact tables)
- [ ] When to use (specific scenarios)
- [ ] TABLE COMMENT set with business-friendly description
- [ ] ALL COLUMN COMMENTs set (zero NULL comments)
- [ ] Column names are self-documenting (no abbreviations)

---

## Asset Organization in Genie Space UI

### Recommended Order

1. **Primary Metric Views** (3-5 views)
   - Most commonly used
   - Cover main business domains
   - Rich with measures

2. **Secondary Metric Views** (2-3 views)
   - Supporting domains
   - Specialized use cases

3. **Table-Valued Functions** (5-10 functions)
   - Common query patterns
   - Parameterized queries
   - Business logic encapsulation

4. **Dimension Tables** (3-5 tables)
   - Reference data
   - Attribute lookups
   - Filtering support

5. **Fact Tables** (1-2 tables, if needed)
   - Only if metric views insufficient
   - Ad-hoc exploration
   - Custom calculations

---

## Validation Checklist

Before adding assets to Genie Space:

- [ ] All metric views tested and return expected results
- [ ] All TVFs tested with sample parameters
- [ ] All tables have proper permissions (SELECT granted)
- [ ] Asset names are descriptive and consistent
- [ ] Documentation includes use cases
- [ ] Performance acceptable (< 10 sec for typical queries)
- [ ] Assets organized in recommended order
- [ ] No duplicate or redundant assets
- [ ] ONLY Gold layer assets included (no Silver/Bronze)
- [ ] Every table has TABLE COMMENT (verified via information_schema)
- [ ] Every column has COLUMN COMMENT (zero NULLs)
- [ ] All column names are descriptive (no abbreviations)
