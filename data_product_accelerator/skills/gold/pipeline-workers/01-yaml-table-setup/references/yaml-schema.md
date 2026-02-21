# YAML Schema Reference - Complete Guide

## Complete YAML Schema Structure

### Full Schema Example

```yaml
table_name: dim_example
domain: billing
description: >
  Complete example of Gold layer dimension table with all fields.

primary_key:
  columns: ['id']
  composite: false

columns:
  - name: id
    type: BIGINT
    nullable: false
    description: "Surrogate key for dimension table"
  
  - name: business_key
    type: STRING
    nullable: false
    description: "Natural business key from source system"
  
  - name: name
    type: STRING
    nullable: true
    description: "Human-readable name"
  
  - name: created_timestamp
    type: TIMESTAMP
    nullable: false
    description: "Record creation timestamp"
  
  - name: updated_timestamp
    type: TIMESTAMP
    nullable: true
    description: "Record last update timestamp"

foreign_keys:
  - name: fk_dim_example_parent
    columns: ['parent_id']
    references: 'catalog.schema.dim_parent(id)'
    ref_columns: ['id']
```

## All Supported Fields

### Top-Level Fields

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `table_name` | Yes | string | Table name (without catalog/schema) |
| `domain` | Yes | string | Domain name (billing, compute, etc.) |
| `description` | No | string | Table description (multi-line supported) |
| `primary_key` | No | object | Primary key definition |
| `columns` | Yes | array | Column definitions |
| `foreign_keys` | No | array | Foreign key definitions |

### Column Fields

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `name` | Yes | string | Column name |
| `type` | Yes | string | SQL data type |
| `nullable` | No | boolean | Default: `true` |
| `description` | No | string | Column comment |

### Primary Key Fields

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `columns` | Yes | array | List of column names |
| `composite` | No | boolean | Default: `false` (true if multiple columns) |

### Foreign Key Fields

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `name` | Yes | string | Constraint name |
| `columns` | Yes | array | List of FK column names |
| `references` | Yes | string | Referenced table (catalog.schema.table) |
| `ref_columns` | Yes | array | Referenced column names |

## All Supported Data Types

### Primitive Types
- `STRING`
- `INT`
- `BIGINT`
- `DOUBLE`
- `BOOLEAN`
- `DATE`
- `TIMESTAMP`
- `BINARY`

### Decimal Types
- `DECIMAL(precision,scale)` - e.g., `DECIMAL(38,10)`

### Complex Types
- `ARRAY<element_type>` - e.g., `ARRAY<STRING>`
- `MAP<key_type,value_type>` - e.g., `MAP<STRING,STRING>`
- `STRUCT<field1:type1,field2:type2>` - e.g., `STRUCT<name:STRING,age:INT>`

## Foreign Key Patterns

### Single Column FK

```yaml
foreign_keys:
  - name: fk_fact_sales_customer
    columns: ['customer_id']
    references: 'catalog.schema.dim_customer(customer_id)'
    ref_columns: ['customer_id']
```

### Composite FK

```yaml
foreign_keys:
  - name: fk_fact_sales_store_product
    columns: ['store_id', 'product_id']
    references: 'catalog.schema.dim_store_product(store_id,product_id)'
    ref_columns: ['store_id', 'product_id']
```

## Examples by Table Type

### Dimension Table Example
See `assets/templates/gold-table-template.yaml` for dimension table template.

### Fact Table Example

```yaml
table_name: fact_sales
domain: retail
description: >
  Daily sales fact table with transaction-level grain.

primary_key:
  columns: ['sale_id']
  composite: false

columns:
  - name: sale_id
    type: BIGINT
    nullable: false
    description: "Unique sale identifier"
  
  - name: transaction_date
    type: DATE
    nullable: false
    description: "Date of transaction"
  
  - name: store_id
    type: BIGINT
    nullable: false
    description: "Store dimension key"
  
  - name: product_id
    type: BIGINT
    nullable: false
    description: "Product dimension key"
  
  - name: revenue
    type: DECIMAL(18,2)
    nullable: false
    description: "Total revenue for transaction"
  
  - name: quantity
    type: INT
    nullable: false
    description: "Quantity sold"

foreign_keys:
  - name: fk_fact_sales_store
    columns: ['store_id']
    references: 'catalog.schema.dim_store(store_id)'
    ref_columns: ['store_id']
  
  - name: fk_fact_sales_product
    columns: ['product_id']
    references: 'catalog.schema.dim_product(product_id)'
    ref_columns: ['product_id']
```
