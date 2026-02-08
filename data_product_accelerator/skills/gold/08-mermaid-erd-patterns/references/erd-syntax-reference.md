# Mermaid ERD Syntax Reference

Complete Mermaid ERD syntax reference including data types, primary key markers, relationship notation, formatting standards, and reserved keyword avoidance.

## Basic Syntax

### Entity Definition

```mermaid
erDiagram
  entity_name {
    type column_name PK
    type column_name
  }
```

### Example

```mermaid
erDiagram
  dim_store {
    string store_key PK
    string store_number
    string store_name
    boolean is_current
  }
```

## Data Types

Use Databricks SQL type names:

| Databricks Type | Mermaid Usage | Example |
|-----------------|--------------|---------|
| `STRING` | `string` | `string store_key PK` |
| `INT` | `int` | `int date_key PK` |
| `BIGINT` | `bigint` | `bigint customer_id` |
| `DECIMAL(p,s)` | `decimal` | `decimal net_revenue` |
| `DOUBLE` | `double` | `double margin_pct` |
| `DATE` | `date` | `date transaction_date` |
| `TIMESTAMP` | `timestamp` | `timestamp effective_from` |
| `BOOLEAN` | `boolean` | `boolean is_current` |

## Primary Key Markers

### Standard Pattern

```mermaid
erDiagram
  dim_store {
    string store_key PK
    string store_number
  }
```

**Rules:**
- Use `PK` marker (uppercase) after column name
- Only mark primary key columns
- For composite keys, mark all PK columns: `string store_key PK`, `date date_key PK`

## Relationship Notation

### Cardinality Types

| Notation | Meaning | Usage |
|----------|---------|-------|
| `\|\|--o{` | One-to-Many | Dimension to Fact (most common) |
| `\|\|--\|\|` | One-to-One | Rare in dimensional modeling |
| `}o--o{` | Many-to-Many | Requires bridge table |

### Relationship Syntax

```mermaid
entity1 ||--o{ entity2 : label
```

### Examples

**One-to-Many (Dimension to Fact):**
```mermaid
dim_store ||--o{ fact_sales_daily : by_store_number
```

**Composite Key Relationship:**
```mermaid
dim_store ||--o{ fact_sales_daily : by_store_key
dim_product ||--o{ fact_sales_daily : by_product_key
dim_date ||--o{ fact_sales_daily : by_date_key
```

**Cross-Domain Reference:**
```mermaid
dim_store["dim_store (Location)"] ||--o{ fact_sales : by_store_number
```

## Formatting Standards

### Indentation

Use **2 spaces** consistently:

```mermaid
erDiagram
  %% Dimensions
  dim_store {
    string store_key PK
    string store_number
  }
  
  %% Facts
  fact_sales {
    string store_key PK
    date date_key PK
  }
```

### Section Headers

Use visual separators and comments:

```mermaid
erDiagram
  %% ═══════════════════════════════════════════════
  %% 🏪 LOCATION DOMAIN
  %% ═══════════════════════════════════════════════
  dim_store {
    string store_key PK
  }
  
  %% ═══════════════════════════════════════════════
  %% 💰 SALES DOMAIN (Facts)
  %% ═══════════════════════════════════════════════
  fact_sales_daily {
    string store_key PK
    date date_key PK
  }
```

### Relationship Grouping

Group all relationships at the end:

```mermaid
erDiagram
  dim_store { ... }
  dim_product { ... }
  fact_sales { ... }
  
  %% ═══════════════════════════════════════════════
  %% RELATIONSHIPS
  %% ═══════════════════════════════════════════════
  dim_store ||--o{ fact_sales : by_store_key
  dim_product ||--o{ fact_sales : by_product_key
```

## Reserved Keywords

### Avoid SQL Reserved Keywords

**❌ Don't Use:**
```mermaid
dim_date {
  date date  -- 'date' is reserved keyword
  string order  -- 'order' is reserved keyword
  string group  -- 'group' is reserved keyword
}
```

**✅ Use Alternatives:**
```mermaid
dim_date {
  date date_value  -- Clear and unambiguous
  string order_number  -- Descriptive name
  string group_name  -- Descriptive name
}
```

### Common Reserved Keywords to Avoid

| Reserved | Alternative |
|----------|-------------|
| `date` | `date_value`, `calendar_date` |
| `order` | `order_number`, `order_id` |
| `group` | `group_name`, `group_id` |
| `user` | `user_name`, `user_id` |
| `table` | `table_name`, `table_id` |
| `key` | `key_value`, `key_id` |

## Relationship Labeling Patterns

### Standard Pattern: `by_{column_name}`

```mermaid
dim_store ||--o{ fact_sales : by_store_key
dim_product ||--o{ fact_sales : by_product_key
dim_date ||--o{ fact_sales : by_date_key
```

### Composite Key Pattern

For composite foreign keys, label each relationship separately:

```mermaid
dim_store ||--o{ fact_sales : by_store_key
dim_product ||--o{ fact_sales : by_product_key
dim_date ||--o{ fact_sales : by_date_key
```

## Cross-Domain References

### Bracketed Notation

Use bracketed syntax with domain annotation:

```mermaid
erDiagram
  %% Sales Domain
  fact_sales {
    string store_key PK
    string product_key PK
  }
  
  %% Location Domain (external reference)
  dim_store["dim_store (Location)"] {
    string store_key PK
  }
  
  %% Product Domain (external reference)
  dim_product["dim_product (Product)"] {
    string product_key PK
  }
  
  dim_store ||--o{ fact_sales : by_store_key
  dim_product ||--o{ fact_sales : by_product_key
```

## Complete Example: Master ERD

```mermaid
erDiagram
  %% ═══════════════════════════════════════════════
  %% 🏪 LOCATION DOMAIN
  %% ═══════════════════════════════════════════════
  dim_store {
    string store_key PK
    string store_number
    string store_name
    boolean is_current
  }
  
  dim_region {
    string region_key PK
    string region_code
    string region_name
  }
  
  %% ═══════════════════════════════════════════════
  %% 📦 PRODUCT DOMAIN
  %% ═══════════════════════════════════════════════
  dim_product {
    string product_key PK
    string upc_code
    string product_name
    boolean is_current
  }
  
  dim_category {
    string category_key PK
    string category_code
    string category_name
  }
  
  %% ═══════════════════════════════════════════════
  %% 📅 TIME DOMAIN
  %% ═══════════════════════════════════════════════
  dim_date {
    int date_key PK
    date date_value
    int year
    int month
    int day
  }
  
  %% ═══════════════════════════════════════════════
  %% 💰 SALES DOMAIN (Facts)
  %% ═══════════════════════════════════════════════
  fact_sales_daily {
    string store_key PK
    string product_key PK
    int date_key PK
    decimal net_revenue
    int units_sold
  }
  
  %% ═══════════════════════════════════════════════
  %% RELATIONSHIPS
  %% ═══════════════════════════════════════════════
  dim_store ||--o{ fact_sales_daily : by_store_key
  dim_product ||--o{ fact_sales_daily : by_product_key
  dim_date ||--o{ fact_sales_daily : by_date_key
  dim_region ||--o{ dim_store : by_region_key
  dim_category ||--o{ dim_product : by_category_key
```

## Domain-Specific ERD Example

```mermaid
erDiagram
  %% ═══════════════════════════════════════════════
  %% 🏪 LOCATION DOMAIN - DETAILED VIEW
  %% ═══════════════════════════════════════════════
  
  dim_region {
    string region_key PK
    string region_code
    string region_name
  }
  
  dim_territory {
    string territory_key PK
    string territory_code
    string territory_name
    string region_key
  }
  
  dim_store {
    string store_key PK
    string store_number
    string store_name
    string territory_key
    boolean is_current
  }
  
  %% Cross-domain reference (Sales)
  fact_sales_daily["fact_sales_daily (Sales)"] {
    string store_key PK
  }
  
  %% ═══════════════════════════════════════════════
  %% RELATIONSHIPS
  %% ═══════════════════════════════════════════════
  dim_region ||--o{ dim_territory : by_region_key
  dim_territory ||--o{ dim_store : by_territory_key
  dim_store ||--o{ fact_sales_daily : by_store_key
```

## Summary ERD Pattern (20+ Tables)

For very large models, create a summary showing domains as entities:

```mermaid
erDiagram
  LOCATION_DOMAIN["🏪 Location (3 tables)"] {
    string dim_store
    string dim_region
    string dim_territory
  }
  
  PRODUCT_DOMAIN["📦 Product (2 tables)"] {
    string dim_product
    string dim_category
  }
  
  TIME_DOMAIN["📅 Time (1 table)"] {
    string dim_date
  }
  
  SALES_DOMAIN["💰 Sales (2 facts)"] {
    string fact_sales_daily
    string fact_sales_monthly
  }
  
  LOCATION_DOMAIN ||--o{ SALES_DOMAIN : "store analysis"
  PRODUCT_DOMAIN ||--o{ SALES_DOMAIN : "product analysis"
  TIME_DOMAIN ||--o{ SALES_DOMAIN : "time analysis"
```

## Best Practices Summary

1. **Use 2-space indentation** consistently
2. **Add section headers** with visual separators
3. **Use only `PK` markers** (no inline descriptions)
4. **Avoid reserved keywords** (`date` → `date_value`)
5. **Use `by_{column}` pattern** for relationship labels
6. **Group relationships** at the end
7. **Match actual table/column names** from DDL
8. **Use correct Databricks SQL type names**
9. **Use bracketed notation** for cross-domain references
10. **Keep labels concise** and technical

## References

- [Mermaid ERD Syntax](https://mermaid.js.org/syntax/entityRelationshipDiagram.html)
- [Databricks Data Types](https://docs.databricks.com/sql/language-manual/sql-ref-datatypes.html)
