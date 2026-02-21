# LLM-Optimized Documentation Patterns

Dual-purpose documentation patterns optimized for Genie and AI/BI tools, including natural language optimization techniques and testing strategies.

## Core Principle: Natural Dual-Purpose Documentation

Every description must serve **both business and technical audiences** without requiring an "LLM:" prefix. The description should read naturally to humans while being structured for LLM parsing.

## Pattern Structure

### Standard Format

```
[Natural description]. Business: [business context and use cases]. Technical: [implementation details and calculations].
```

### Why This Works

1. **Natural Language First:** Starts with human-readable description
2. **Structured Sections:** Clear "Business:" and "Technical:" markers for LLM parsing
3. **No Prefixes:** Avoids "LLM:" or "AI:" prefixes that clutter human reading
4. **Complete Context:** Provides both business meaning and technical implementation

## Examples by Column Type

### Surrogate Key

**❌ Bad:**
```
LLM: Surrogate key (unique per version)
```

**✅ Good:**
```
Surrogate key uniquely identifying each version of a store record. Business: Used for joining fact tables to dimension. Technical: MD5 hash generated from store_id and processed_timestamp to ensure uniqueness across SCD Type 2 versions.
```

**Why:** Natural description first, then structured business/technical sections.

### Measure

**❌ Bad:**
```
Net revenue (gross minus returns)
```

**✅ Good:**
```
Net revenue after subtracting returns from gross revenue. Business: The actual revenue realized from sales, primary KPI for financial reporting. Technical: gross_revenue - return_amount, represents true daily sales value in USD.
```

**Why:** Explains calculation, business context, and technical formula.

### Boolean Flag

**❌ Bad:**
```
is_current: true if current version
```

**✅ Good:**
```
Current version indicator for SCD Type 2 dimension. Business: TRUE indicates active/current record, FALSE indicates historical version. Technical: BOOLEAN, default TRUE, updated when new version created.
```

**Why:** Explains both TRUE and FALSE meanings, plus technical behavior.

## Natural Language Optimization Techniques

### 1. Use Complete Sentences

**❌ Bad:**
```
Store identifier. POS system.
```

**✅ Good:**
```
Store identifier from POS system. Business: Human-readable store identifier used in reports and dashboards. Technical: Alphanumeric code from source system, immutable business key.
```

### 2. Avoid Abbreviations Without Context

**❌ Bad:**
```
UPC code. 12 digits.
```

**✅ Good:**
```
Universal Product Code for product identification. Business: Standard retail product identifier used in inventory and sales systems. Technical: 12-digit UPC format, immutable business identifier.
```

### 3. Explain Calculations Explicitly

**❌ Bad:**
```
Margin percentage
```

**✅ Good:**
```
Profit margin expressed as decimal percentage. Business: Profitability metric showing percentage of revenue retained as profit. Technical: (net_revenue - cost_of_goods_sold) / net_revenue, NULL when net_revenue = 0.
```

### 4. Document NULL Handling

**❌ Bad:**
```
Return rate percentage
```

**✅ Good:**
```
Return rate expressed as decimal percentage (0.0 to 1.0). Business: Percentage of sales returned, key quality metric. Technical: return_count / total_sales_count, NULL when total_sales_count = 0, DECIMAL(5,4) precision (max 99.99%).
```

## Testing Strategies

### 1. Genie Space Testing

Test documentation quality by asking Genie natural language questions:

**Test Questions:**
- "What is the grain of fact_sales_daily?"
- "How is net_revenue calculated?"
- "What does is_current mean in dim_store?"
- "Which tables track store history?"

**Expected Behavior:**
- Genie should understand column meanings from comments
- Genie should explain calculations correctly
- Genie should identify SCD Type 2 patterns
- Genie should understand relationships from foreign key comments

### 2. Documentation Review Checklist

- [ ] Every column has a comment
- [ ] Comments start with natural language description
- [ ] Business section explains use cases and context
- [ ] Technical section explains implementation details
- [ ] Calculations are explicit (formulas included)
- [ ] NULL handling is documented
- [ ] TRUE/FALSE meanings are clear for booleans
- [ ] Relationships are documented in foreign key comments

### 3. Human Readability Test

Read the comment aloud - it should:
- Sound natural to a business user
- Provide technical details for developers
- Not require "LLM:" prefix to understand
- Be self-contained (no external context needed)

## Common Patterns

### Pattern 1: Calculated Measures

**Template:**
```
{Calculation description}. Business: {Business purpose, KPI context}. Technical: {Formula, aggregation method, unit}.
```

**Example:**
```
Average order value calculated as total revenue divided by order count. Business: Key metric for understanding customer spending patterns. Technical: net_revenue / order_count, calculated at daily grain, DECIMAL(18,2) precision.
```

### Pattern 2: Foreign Keys

**Template:**
```
Foreign key referencing {table}.{column}. Business: {Business relationship}. Technical: References surrogate PK {table}.{column} for referential integrity.
```

**Example:**
```
Foreign key referencing dim_store.store_key. Business: Links sales transactions to store location dimension. Technical: References surrogate PK dim_store.store_key for referential integrity.
```

### Pattern 3: SCD Type 2 Fields

**Template:**
```
{Field purpose} for SCD Type 2 dimension versioning. Business: {Business context}. Technical: {Implementation details, join patterns}.
```

**Example:**
```
Start timestamp for SCD Type 2 version validity period. Business: Beginning of time period when this dimension version was active. Technical: TIMESTAMP in UTC, set from source system processed_timestamp, used for time-based joins with WHERE effective_from <= fact_date < effective_to.
```

## Tag Strategies

### Unity Catalog Tags

Use tags to complement comments:

```python
TAGS (
    'domain' = 'retail',
    'layer' = 'gold',
    'entity_type' = 'dimension',
    'scd_type' = '2',
    'contains_pii' = 'false'
)
```

**Why:** Tags provide structured metadata for filtering and governance, while comments provide human-readable context.

### Data Classification Tags

```python
TAGS (
    'data_classification' = 'internal',
    'business_owner' = 'Retail Operations',
    'technical_owner' = 'Data Engineering'
)
```

**Why:** Enables governance and access control while comments explain business meaning.

## Best Practices Summary

1. **Start Natural:** Begin with human-readable description
2. **Structure Clearly:** Use "Business:" and "Technical:" sections
3. **Be Complete:** Include formulas, NULL handling, and edge cases
4. **Avoid Prefixes:** Don't use "LLM:" or "AI:" markers
5. **Test with Genie:** Validate documentation quality with natural language queries
6. **Document Relationships:** Explain foreign key relationships in comments
7. **Explain Calculations:** Include formulas for calculated measures
8. **Clarify Booleans:** Document both TRUE and FALSE meanings

## References

- [Databricks Genie Documentation](https://docs.databricks.com/genie/)
- [Unity Catalog Tags](https://docs.databricks.com/data-governance/unity-catalog/tags.html)
- [Data Classification](https://learn.microsoft.com/en-us/azure/databricks/data-governance/unity-catalog/data-classification)
