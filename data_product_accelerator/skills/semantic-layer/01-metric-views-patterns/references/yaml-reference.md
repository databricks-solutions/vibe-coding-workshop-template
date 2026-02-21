# Metric View YAML Reference (v1.1)

Complete reference for Databricks Metric View YAML structure, fields, and syntax.

## Complete YAML Structure

```yaml
version: "1.1"  # Must be quoted string
comment: >
  PURPOSE: [One-line description of what this metric view provides]
  
  BEST FOR: [Question 1] | [Question 2] | [Question 3] | [Question 4]
  
  NOT FOR: [What this view shouldn't be used for] (use [correct_asset] instead)
  
  DIMENSIONS: [dim1], [dim2], [dim3], [dim4], [dim5]
  
  MEASURES: [measure1], [measure2], [measure3], [measure4], [measure5]
  
  SOURCE: [fact_or_dim_table] ([domain] domain)
  
  JOINS: [dim_table1] ([description]), [dim_table2] ([description])
  
  NOTE: [Any critical caveats, limitations, or important context]

source: ${catalog}.${gold_schema}.<fact_table>

# Optional: Join to dimension tables
joins:
  - name: <dim_table_alias>
    source: ${catalog}.${gold_schema}.<dim_table>
    'on': source.<fk> = <dim_table_alias>.<pk> AND <dim_table_alias>.is_current = true

dimensions:
  - name: <dimension_name>
    expr: source.<column>
    comment: <Business description for LLM understanding>
    display_name: <User-Friendly Name>
    synonyms:
      - <alternative name 1>
      - <alternative name 2>

measures:
  - name: <measure_name>
    expr: SUM(source.<column>)
    comment: <Business description and calculation logic>
    display_name: <User-Friendly Name>
    format:
      type: currency|number|percentage
      currency_code: USD
      decimal_places:
        type: exact|all
        places: 2
      hide_group_separator: false
      abbreviation: compact
    synonyms:
      - <alternative name 1>
      - <alternative name 2>
```

## Field Reference

### Top-Level Fields

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `version` | ✅ Yes | String | Must be `"1.1"` (quoted) |
| `comment` | ✅ Yes | String | Structured description for Genie |
| `source` | ✅ Yes | String | Fully qualified table name or SQL query |
| `filter` | ❌ No | String | SQL boolean expression applied as WHERE clause to all queries |
| `joins` | ❌ No | Array | List of dimension table joins |
| `dimensions` | ✅ Yes | Array | List of dimension columns |
| `measures` | ✅ Yes | Array | List of measure columns |

### Unsupported Fields (v1.1)

**These fields will cause errors and MUST NOT be used:**

| Field | Error | Action |
|-------|-------|--------|
| `name` | `Unrecognized field "name"` | ❌ NEVER include - name is in CREATE VIEW statement |
| `time_dimension` | `Unrecognized field "time_dimension"` | ❌ Remove entirely - use regular dimension instead |
| `window_measures` | `Unrecognized field "window_measures"` | ❌ Remove top-level `window_measures:` array. Individual measure `window:` property is Experimental (v0.1 only, DBR 16.4-17.1). For v1.1, calculate windowed aggregations in SQL/Python. |
| `join_type` | Unsupported | ❌ Remove - defaults to LEFT OUTER JOIN |
| `table` (in joins) | `Missing required creator property 'source'` | ✅ Use `source` instead |

### Join Fields

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `name` | ✅ Yes | String | Alias used to reference joined table (e.g., `dim_store`) |
| `source` | ✅ Yes | String | Fully qualified table path |
| `'on'` | ✅ Yes (or `using`) | String | Join condition (quoted!) using `source.` prefix |
| `using` | ✅ Yes (or `'on'`) | Array | Column names shared between source and join table (alternative to `'on'`) |
| `joins` | ❌ No | Array | Nested joins for snowflake schema (DBR 17.1+) |

**Join Requirements:**
- Each join **MUST have** `name`, `source`, and either `'on'` or `using`
- `ON` clause uses `source.` for main table, join name for joined table
- `USING` clause lists columns with the same name in both tables
- Each first-level join must reference `source` (NOT another join alias — that's transitive)
- For transitive relationships, use nested `joins:` (snowflake schema) or denormalized columns
- SCD2 joins must include `AND {dim_table}.is_current = true`
- **MAP type columns are NOT supported** in joined tables

### Dimension Fields

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `name` | ✅ Yes | String | Dimension identifier |
| `expr` | ✅ Yes | String | Column expression (use `source.` or `{join_name}.`) |
| `comment` | ✅ Yes | String | Business description for LLM understanding |
| `display_name` | ✅ Yes | String | User-friendly name for UI |
| `synonyms` | ✅ Yes | Array | 3-5 alternative names for Genie recognition |

### Measure Fields

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `name` | ✅ Yes | String | Measure identifier |
| `expr` | ✅ Yes | String | Aggregation expression (SUM, COUNT, AVG, etc.) |
| `comment` | ✅ Yes | String | Business description and calculation logic |
| `display_name` | ✅ Yes | String | User-friendly name for UI |
| `format` | ✅ Yes | Object | Formatting configuration |
| `synonyms` | ✅ Yes | Array | 3-5 alternative names for Genie recognition |

### Format Options

**Valid format types (exhaustive):**

| Type | Use For | Common Mistake |
|------|---------|----------------|
| `byte` | Data sizes (storage, memory) | — |
| `currency` | Monetary values (revenue, cost) | — |
| `date` | Date-only values | — |
| `date_time` | Timestamp values | — |
| `number` | Counts, averages, decimals, integers | ❌ `decimal`, ❌ `integer` |
| `percentage` | Ratios, rates, percentages | ❌ `percent` |

**⚠️ `percent` is NOT valid** (use `percentage`). **`decimal` is NOT valid** (use `number`).

#### Byte Format
```yaml
format:
  type: byte
  decimal_places:
    type: exact
    places: 1
  abbreviation: compact
```

#### Currency Format
```yaml
format:
  type: currency
  currency_code: USD  # or EUR, GBP, etc.
  decimal_places:
    type: exact
    places: 2
  hide_group_separator: false  # Show commas
  abbreviation: compact  # Shows 1.5M instead of 1,500,000
```

#### Number Format
```yaml
format:
  type: number
  decimal_places:
    type: all  # Show all decimals
    # OR
    type: exact
    places: 1
  hide_group_separator: false
  abbreviation: compact
```

#### Percentage Format
```yaml
format:
  type: percentage
  decimal_places:
    type: exact
    places: 1  # Shows 45.3%
```

#### Date Format
```yaml
format:
  type: date
  date_format: year_month_day  # YYYY-MM-DD
  leading_zeros: true
```

Date format options: `year_week`, `locale_number_month`, `year_month_day`, `locale_long_month`, `locale_short_month`

#### DateTime Format
```yaml
format:
  type: date_time
  date_format: year_month_day
  time_format: locale_hour_minute_second
  leading_zeros: true
```

Time format options: `locale_hour_minute_second`, `locale_hour_minute`, `no_time`

## Column Reference Rules

### Main Table Columns
- **MUST use `source.` prefix** in all `expr` fields
- Example: `expr: source.revenue` NOT `expr: fact_table.revenue`

### Joined Table Columns
- Use join `name` prefix for joined table columns
- Example: `expr: dim_store.column_name`

### Never Reference Table Names Directly
- ❌ `expr: fact_sales.revenue`
- ✅ `expr: source.revenue`
- ❌ `expr: dim_store.store_name`
- ✅ `expr: dim_store.store_name` (if join name is `dim_store`)

## Expression Syntax

### Supported Aggregations
- `SUM(source.column)` - Sum numeric values
- `COUNT(source.column)` - Count non-null values
- `COUNT(*)` - Count all rows
- `AVG(source.column)` - Average numeric values
- `MIN(source.column)` - Minimum value
- `MAX(source.column)` - Maximum value

### Column References
- `source.column_name` - Column from main table
- `{join_name}.column_name` - Column from joined table
- `dim_property.fact_booking.column_name` - Nested join (snowflake schema)

## Comment Format Structure

### Standardized Comment Template

```yaml
comment: >
  PURPOSE: [One-line description of what this metric view provides].
  
  BEST FOR: [Question 1] | [Question 2] | [Question 3] | [Question 4]
  
  NOT FOR: [What this view shouldn't be used for] (use [correct_asset] instead)
  
  DIMENSIONS: [dim1], [dim2], [dim3], [dim4], [dim5]
  
  MEASURES: [measure1], [measure2], [measure3], [measure4], [measure5]
  
  SOURCE: [fact_or_dim_table] ([domain] domain)
  
  JOINS: [dim_table1] ([description]), [dim_table2] ([description])
  
  NOTE: [Any critical caveats, limitations, or important context]
```

### Element Guidelines

| Element | Format | Example |
|---------|--------|---------|
| **PURPOSE** | Single sentence, no period at end | `Comprehensive cost analytics for Databricks billing` |
| **BEST FOR** | Pipe-separated questions (4-6) | `Total spend | Cost by SKU | Daily trend` |
| **NOT FOR** | Include redirect with parentheses | `Commit tracking (use commit_tracking)` |
| **DIMENSIONS** | Comma-separated, 5-8 key columns | `usage_date, workspace_name, sku_name, owner` |
| **MEASURES** | Comma-separated, 5-8 key metrics | `total_cost, success_rate, avg_duration` |
| **SOURCE** | Table name with domain in parens | `fact_usage (billing domain)` |
| **JOINS** | Table name with brief description | `dim_workspace (workspace details)` |
| **NOTE** | Critical caveat or limitation | `Cost values are list prices` |

## Complete Example

```yaml
version: "1.1"
comment: >
  PURPOSE: Comprehensive sales performance metrics with revenue, units, and customer insights
  
  BEST FOR: Sales by store | Revenue trend over time | Product performance | Customer segments
  
  DIMENSIONS: transaction_date, store_number, brand, month_name
  
  MEASURES: total_revenue, booking_count, avg_transaction_value
  
  SOURCE: fact_sales_daily (retail domain)
  
  JOINS: dim_store (store details), dim_product (product details), dim_date (time dimensions)
  
  NOTE: Revenue excludes tax. Duration metrics exclude queued time.

source: ${catalog}.${gold_schema}.fact_sales_daily

joins:
  - name: dim_store
    source: ${catalog}.${gold_schema}.dim_store
    'on': source.store_number = dim_store.store_number AND dim_store.is_current = true
  
  - name: dim_product
    source: ${catalog}.${gold_schema}.dim_product
    'on': source.upc_code = dim_product.upc_code
  
  - name: dim_date
    source: ${catalog}.${gold_schema}.dim_date
    'on': source.transaction_date = dim_date.date

dimensions:
  - name: transaction_date
    expr: source.transaction_date
    comment: Transaction date for time-based sales analysis and trending
    display_name: Transaction Date
    synonyms:
      - date
      - sale date
      - order date
  
  - name: store_number
    expr: source.store_number
    comment: Store identifier for location-based sales analysis
    display_name: Store Number
    synonyms:
      - store id
      - location number
  
  - name: brand
    expr: dim_product.brand
    comment: Product brand name
    display_name: Brand
    synonyms:
      - product brand
  
  - name: month_name
    expr: dim_date.month_name
    comment: Month name for seasonal analysis
    display_name: Month
    synonyms:
      - month

measures:
  - name: total_revenue
    expr: SUM(source.net_revenue)
    comment: Total net revenue after discounts and returns. Primary revenue metric.
    display_name: Total Revenue
    format:
      type: currency
      currency_code: USD
      decimal_places:
        type: exact
        places: 2
      abbreviation: compact
    synonyms:
      - revenue
      - sales
      - net revenue
      - total sales
  
  - name: booking_count
    expr: COUNT(source.booking_id)
    comment: Total number of transactions
    display_name: Booking Count
    format:
      type: number
      decimal_places:
        type: all
      abbreviation: compact
    synonyms:
      - bookings
      - transactions
      - orders
```
