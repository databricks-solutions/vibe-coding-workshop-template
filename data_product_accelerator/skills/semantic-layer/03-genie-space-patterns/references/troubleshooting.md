# Genie Space Troubleshooting Guide

Common issues, debugging steps, and verification procedures for Databricks Genie Spaces.

## Common Issues

### Issue 1: Genie Routes to Wrong Assets

**Symptoms:**
- Genie selects Metric View when TVF should be used
- Genie selects TVF when Metric View should be used
- Inconsistent routing for similar questions

**Root Causes:**
1. Contradictory routing rules in General Instructions
2. Ambiguous term definitions missing
3. Asset descriptions unclear or conflicting

**Solutions:**

**Fix 1: Remove Contradictory Rules**
```markdown
❌ BAD:
- host_analytics_metrics → for host data
- get_host_performance → for host data  # CONFLICT!

✅ GOOD:
Revenue/booking questions:
  - By property → revenue_analytics_metrics
  - By host → get_host_performance TVF
```

**Fix 2: Define Ambiguous Terms**
```markdown
## Term Definitions
"top performing" = Highest revenue unless "rated" specified.
If "rated" mentioned, use rating-based metric. Otherwise, use revenue.
```

**Fix 3: Group by Question Type**
Organize instructions by question type, not by asset:
```markdown
Revenue Questions:
  - Property-level → revenue_analytics_metrics
  - Host-level → get_host_performance TVF
```

**Verification:**
- Test ambiguous questions (e.g., "top performers", "underperforming")
- Verify Genie routes consistently
- Check that similar questions route to same asset

---

### Issue 2: MEASURE() Function Errors

**Symptoms:**
- `MEASURE()` function fails with "column not found"
- Genie generates SQL with backticks around display names

**Root Cause:**
Using display names instead of actual column names in `MEASURE()`.

**Solution:**

**❌ WRONG:**
```sql
MEASURE(`Total Revenue`)  -- ❌ FAILS: "Total Revenue" is display_name
```

**✅ CORRECT:**
```sql
MEASURE(total_revenue)  -- ✅ Uses actual column name from YAML
```

**Prevention:**
- Always use actual column names from metric view YAML
- Never use display names (even with backticks)
- Test benchmark questions to catch this early

**Verification:**
- Check benchmark question SQL uses actual column names
- Verify SQL runs successfully
- Test Genie queries that use MEASURE()

---

### Issue 3: Missing Full UC Namespace

**Symptoms:**
- SQL errors: "table not found" or "function not found"
- Genie generates SQL without catalog/schema

**Root Cause:**
Not using full 3-part Unity Catalog namespace.

**Solution:**

**❌ WRONG:**
```sql
SELECT * FROM fact_sales;
SELECT * FROM get_revenue_by_period('2024-01-01', '2024-12-31', 'month');
```

**✅ CORRECT:**
```sql
SELECT * FROM ${catalog}.${gold_schema}.fact_sales;
SELECT * FROM ${catalog}.${gold_schema}.get_revenue_by_period('2024-01-01', '2024-12-31', 'month');
```

**Prevention:**
- Always use `${catalog}.${schema}.{object}` format
- Include in all benchmark question SQL
- Verify in General Instructions examples

**Verification:**
- Check all benchmark SQL uses full namespace
- Test SQL runs in target workspace
- Verify Genie generates full namespaces

---

### Issue 4: General Instructions Too Long

**Symptoms:**
- Genie ignores instructions
- Inconsistent behavior
- Instructions get truncated

**Root Cause:**
General Instructions exceed 20 lines.

**Solution:**
- **Reduce to ≤20 lines** - Keep only essential rules
- Move detailed patterns to Extended Instructions (optional)
- Focus on routing rules and critical constraints

**Verification:**
- Count lines in General Instructions (must be ≤20)
- Test that Genie follows instructions
- Verify routing consistency

---

### Issue 5: Benchmark Questions Without Working SQL

**Symptoms:**
- Cannot validate Genie responses
- SQL errors when testing
- Mismatch between expected and actual SQL

**Root Cause:**
Benchmark questions don't include tested, working SQL.

**Solution:**
- **Every benchmark question MUST have SQL**
- Test all SQL before including
- Use actual column names, full namespaces
- Verify SQL runs successfully

**Format:**
```markdown
### Question 1: "What are the top 10 stores by revenue this month?"
**Expected SQL:**
```sql
SELECT 
  store_name,
  MEASURE(total_revenue) as revenue
FROM ${catalog}.${gold_schema}.sales_performance_metrics
WHERE transaction_date >= DATE_TRUNC('month', CURRENT_DATE)
GROUP BY store_name
ORDER BY revenue DESC
LIMIT 10;
```
**Expected Result:** 10 rows with store names and revenue, sorted DESC
```

**Verification:**
- Every benchmark question has SQL block
- All SQL tested and runs successfully
- SQL uses correct column names and namespaces

---

### Issue 6: Incorrect TVF Syntax

**Symptoms:**
- SQL errors when calling TVFs
- Genie wraps TVFs incorrectly
- Missing or incorrect parameters

**Root Cause:**
Incorrect TVF usage patterns.

**Solution:**

**❌ WRONG:**
```sql
SELECT * FROM TABLE(get_customer_segments(...))  -- Don't wrap in TABLE()
SELECT * FROM get_customer_segments()            -- Missing parameters
SELECT * FROM get_customer_segments(...) GROUP BY segment  -- Unnecessary GROUP BY
```

**✅ CORRECT:**
```sql
SELECT * FROM ${catalog}.${gold_schema}.get_customer_segments('2020-01-01', '2024-12-31')
```

**Prevention:**
- Document correct TVF syntax in Section F
- Include examples in benchmark questions
- Test TVF calls in benchmark SQL

**Verification:**
- Check TVF documentation has correct syntax
- Verify benchmark questions use correct syntax
- Test TVF calls run successfully

---

### Issue 7: Asset Selection Order Issues

**Symptoms:**
- Genie prefers tables over metric views
- Performance issues (scanning raw tables)
- Incorrect aggregations

**Root Cause:**
Assets added in wrong order or tables prioritized.

**Solution:**
- **Add assets in correct order:** Metric Views → TVFs → Tables
- **Document hierarchy** in General Instructions
- **Emphasize** "use Metric Views first" in instructions

**Verification:**
- Check asset order in Genie Space
- Verify General Instructions emphasize Metric Views
- Test that Genie prefers metric views

---

### Issue 8: Poor SQL Generation Due to Missing Table/Column Comments

**Symptoms:**
- Genie generates incorrect SQL (wrong columns, wrong joins)
- Genie asks for clarification on simple questions
- Genie doesn't recognize business terms users expect

**Root Cause:**
Missing or inadequate `COMMENT ON TABLE` and `COMMENT ON COLUMN` in Unity Catalog. Genie reads these comments to understand data semantics.

**Solution:**

```sql
-- Step 1: Check which columns lack comments
SELECT column_name, comment
FROM information_schema.columns
WHERE table_catalog = '${catalog}'
  AND table_schema = '${gold_schema}'
  AND table_name = '${table_name}'
  AND comment IS NULL;

-- Step 2: Add business-friendly comments
COMMENT ON TABLE ${catalog}.${gold_schema}.fact_sales IS
  'Daily retail sales transactions at store-SKU grain. Includes net revenue after discounts.';

COMMENT ON COLUMN ${catalog}.${gold_schema}.fact_sales.total_amount IS
  'Net sale amount in USD after discounts and before tax. Always >= 0.';

COMMENT ON COLUMN ${catalog}.${gold_schema}.fact_sales.transaction_date IS
  'Date the sale occurred. Used for time-based filtering (today, last month, YTD).';
```

**Prevention:**
- Run the [Pre-Addition Verification Query](./trusted-assets.md#pre-addition-verification-query) before adding any asset
- Follow the [Gold Layer Documentation Skill](../../gold/gold-layer-documentation/SKILL.md) standards
- Zero NULL comments policy: every column must have a comment

**Verification:**
- [ ] Run information_schema query -- zero NULL comments
- [ ] Comments use business language (not technical jargon)
- [ ] Comments include valid values for enums/categories
- [ ] Re-test benchmark questions after adding comments

---

### Issue 9: Slow Genie Responses (Wrong Warehouse Type)

**Symptoms:**
- Genie responses take 30+ seconds for simple queries
- Warehouse startup delay before first response
- Inconsistent response times

**Root Cause:**
Using Classic or Pro SQL Warehouse instead of Serverless.

**Solution:**

1. Verify warehouse type:
   ```python
   # Check current warehouse assignment
   space = get_genie(space_id="your_space_id")
   # Verify warehouse_id points to a Serverless warehouse
   ```

2. Switch to Serverless:
   ```python
   create_or_update_genie(
       display_name="Your Space Name",  # Must match exactly
       table_identifiers=[...],
       warehouse_id="serverless_warehouse_id"
   )
   ```

**Prevention:**
- ALWAYS use Serverless SQL Warehouses for Genie Spaces
- If auto-detecting, verify the selected warehouse is Serverless type
- See [Warehouse Selection](./configuration-guide.md#warehouse-selection) for mandatory patterns

**Verification:**
- [ ] Warehouse type is Serverless (not Classic or Pro)
- [ ] Simple queries respond in < 10 seconds
- [ ] No manual cluster sizing needed

---

### Issue 10: Follow-up Context Contamination

**Symptoms:**
- Follow-up questions return unexpected results
- Genie applies filters from previous unrelated questions
- "Break that down by X" references wrong context

**Root Cause:**
Reusing `conversation_id` across unrelated questions. Genie carries forward context from the conversation, so unrelated questions inherit wrong filters/context.

**Solution:**

```python
# ❌ WRONG: Same conversation for unrelated questions
result1 = ask_genie(space_id, "Sales by region last month")
result2 = ask_genie_followup(space_id, result1["conversation_id"],
    "How many employees do we have?")  # ❌ Unrelated -- may inherit "last month" filter!

# ✅ CORRECT: New conversation for new topic
result1 = ask_genie(space_id, "Sales by region last month")
result2 = ask_genie(space_id, "How many employees do we have?")  # ✅ Fresh context

# ✅ CORRECT: Follow-up for related drill-down
result1 = ask_genie(space_id, "Sales by region last month")
result2 = ask_genie_followup(space_id, result1["conversation_id"],
    "Which products drove the highest sales in the top region?")  # ✅ Related
```

**Prevention:**
- Use `ask_genie()` (new conversation) for each unrelated question
- Use `ask_genie_followup()` ONLY when the question explicitly references prior context
- In automated testing, always use new conversations for each benchmark question

**Verification:**
- [ ] Each benchmark question uses a separate conversation
- [ ] Follow-up tests explicitly reference prior context ("that", "same for", "break down")
- [ ] No cross-topic context leakage in test results

---

## Debugging Steps

### Step 0: Verify Pre-Requisites

Before debugging Genie behavior, check foundational requirements:
- [ ] Serverless SQL Warehouse assigned (NOT Classic or Pro)
- [ ] ALL trusted asset tables have TABLE and COLUMN comments (zero NULLs)
- [ ] Column names are descriptive (no abbreviations like `clv`, `amt`, `dt`)
- [ ] ONLY Gold layer assets used as trusted assets (no Silver/Bronze)
- [ ] Table schemas were inspected before space creation

### Step 1: Verify 7-Section Structure

Check that all sections are complete:
- [ ] Section A: Space Name (exact format)
- [ ] Section B: Space Description (2-3 sentences)
- [ ] Section C: Sample Questions (10-15 questions)
- [ ] Section D: Data Assets (all documented)
- [ ] Section E: General Instructions (≤20 lines)
- [ ] Section F: TVFs (all documented with signatures)
- [ ] Section G: Benchmark Questions (10-15 with SQL)

### Step 2: Validate General Instructions

- [ ] Count lines (must be ≤20)
- [ ] Check for contradictory rules
- [ ] Verify ambiguous terms defined
- [ ] Confirm routing rules grouped by question type
- [ ] Ensure asset hierarchy emphasized

### Step 3: Test Benchmark Questions

For each benchmark question:
- [ ] SQL included and tested
- [ ] Uses actual column names (not display names)
- [ ] Uses full UC namespace
- [ ] TVF syntax correct (if applicable)
- [ ] SQL runs successfully
- [ ] Expected result documented

### Step 4: Verify Asset Documentation

For each asset:
- [ ] Metric Views: measures and dimensions documented
- [ ] TVFs: signature, parameters, return schema documented
- [ ] Tables: purpose and when to use documented
- [ ] Use cases clear and non-conflicting

### Step 5: Test Genie Routing

Test ambiguous questions:
- [ ] "top performers" routes correctly
- [ ] "underperforming" routes correctly
- [ ] Date-bounded queries use TVFs
- [ ] Broad aggregations use Metric Views
- [ ] Similar questions route consistently

---

## Verification Procedures

### Pre-Deployment Verification

1. **Structure Check**
   - All 7 sections present
   - Each section meets requirements
   - No missing content

2. **General Instructions Check**
   - Line count ≤20
   - No contradictory rules
   - Ambiguous terms defined
   - Routing rules clear

3. **SQL Validation**
   - All benchmark SQL tested
   - Uses correct column names
   - Uses full UC namespace
   - TVF syntax correct

4. **Asset Documentation Check**
   - All assets documented
   - Use cases clear
   - No conflicting descriptions

### Post-Deployment Verification

1. **Routing Test**
   - Test all benchmark questions
   - Verify Genie routes correctly
   - Check for consistent behavior

2. **Response Quality Check**
   - Responses include business context
   - Numbers formatted correctly
   - SQL matches expected patterns
   - No errors or warnings

3. **Performance Check**
   - Response times acceptable (< 10 sec)
   - No table scans (check query plans)
   - Metric views/TVFs used appropriately

---

## Common Mistakes to Avoid

### ❌ General Instructions > 20 Lines
Genie won't process instructions effectively if they exceed 20 lines.

### ❌ Benchmark Questions Without SQL
Cannot validate Genie responses without working SQL.

### ❌ Using Display Names in MEASURE()
MEASURE() requires actual column names from YAML, not display names.

### ❌ Partial UC Namespaces
Always use full 3-part namespace: `${catalog}.${schema}.{object}`

### ❌ Adding Only Tables as Trusted Assets
Start with Metric Views (pre-aggregated) for better performance.

### ❌ Contradictory Routing Rules
Group by question type, not asset, to avoid conflicts.

### ❌ Undefined Ambiguous Terms
Explicitly define terms like "underperforming", "top performing".

### ❌ Incorrect TVF Syntax
Don't wrap TVFs in TABLE(), include all required parameters, avoid unnecessary GROUP BY.

---

## Getting Help

### Check Documentation
- [Configuration Guide](./configuration-guide.md) - Complete setup guide
- [Agent Instructions Guide](./agent-instructions.md) - Instruction patterns
- [Databricks Genie Docs](https://docs.databricks.com/genie/)

### Common Patterns
- Review successful Genie Space examples
- Check benchmark questions for SQL patterns
- Verify asset documentation matches actual assets

### Escalation
If issues persist:
1. Verify all 7 sections complete
2. Check General Instructions ≤20 lines
3. Test all benchmark SQL
4. Review routing rules for conflicts
5. Check asset documentation accuracy

---

## Version History

- **v1.1** (Feb 2026) - New issues from reference material integration
  - Added Issue 8: Poor SQL due to missing comments
  - Added Issue 9: Slow responses from wrong warehouse type
  - Added Issue 10: Follow-up context contamination
  - Added Step 0: Pre-requisite verification to debugging steps

- **v1.0** (Dec 2025) - Initial troubleshooting guide
  - Common issues and solutions
  - Debugging procedures
  - Verification checklists
