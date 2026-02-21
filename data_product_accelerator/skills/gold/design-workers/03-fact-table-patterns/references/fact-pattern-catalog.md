# Fact Pattern Catalog

Extended fact table design patterns with YAML examples for Gold layer modeling. These patterns complement the core rules in the main SKILL.md.

---

## Consolidated Fact Tables

### When to Use

When multiple related business processes share the same grain and dimensions, consolidating them into a single fact table simplifies queries and avoids error-prone fact-to-fact joins.

### Example

Separate sales and returns processes, both at the order-line-item grain:

```yaml
table_name: fact_sales_and_returns
description: "Consolidated sales and returns. Business: Unified view of sales revenue and return activity. Technical: Consolidated fact — sales measures populated at sale time, return measures populated at return time."
grain: "One row per order line item"
grain_type: transaction
columns:
  - name: line_item_key
    type: BIGINT
    nullable: false
  - name: order_date_key
    type: BIGINT
    foreign_key:
      references: dim_date.date_key
  - name: return_date_key
    type: BIGINT
    description: "Return date. Technical: NULL if not returned."
    foreign_key:
      references: dim_date.date_key
  - name: product_key
    type: BIGINT
    foreign_key:
      references: dim_product.product_key
  # Sales measures (populated at sale time)
  - name: sales_quantity
    type: INT
    description: "Quantity sold. Technical: Additive. Always populated."
  - name: sales_amount
    type: DOUBLE
    description: "Sales revenue. Technical: Additive. Always populated."
  # Return measures (populated at return time, NULL otherwise)
  - name: return_quantity
    type: INT
    description: "Quantity returned. Technical: Additive. NULL if not returned."
  - name: return_amount
    type: DOUBLE
    description: "Return refund amount. Technical: Additive. NULL if not returned."
```

### Key Rules

- All processes must share the same grain
- Process-specific measures are NULL when that process hasn't occurred
- Include date FKs for each process milestone
- Document which measure groups belong to which process

---

## Header/Line Fact Pattern

### When to Use

When transactions have a natural parent-child structure (order header → order lines, invoice → invoice lines).

### Design Decision

| Approach | When | Grain |
|----------|------|-------|
| **Line-level fact only** | Most queries need line detail | One row per line item |
| **Header-level fact only** | Detail not needed, header totals suffice | One row per header |
| **Both** | Different user groups need different grains | Two fact tables |

### YAML Pattern (Line-Level with Header Reference)

```yaml
table_name: fact_order_lines
description: "Order line items. Business: Individual products within each order. Technical: Line-level grain with degenerate order number for header grouping."
grain: "One row per order line item"
grain_type: transaction
columns:
  - name: order_line_key
    type: BIGINT
    nullable: false
  - name: order_number
    type: STRING
    description: "Order number. Technical: Degenerate dimension — groups lines into orders."
  - name: line_number
    type: INT
  - name: product_key
    type: BIGINT
    foreign_key:
      references: dim_product.product_key
  - name: quantity
    type: INT
  - name: unit_price
    type: DOUBLE
    description: "Unit price. Technical: NON-ADDITIVE — do not SUM."
  - name: line_amount
    type: DOUBLE
    description: "Line total. Technical: Additive (quantity × unit_price)."
```

**Rule:** Store `unit_price` at line level (non-additive) and `line_amount` (additive). Never store only `unit_price` and expect users to multiply.

---

## Late-Arriving Facts

### Problem

A fact record arrives after the reporting period has closed. For example, a sale occurs on January 31 but the data arrives on February 3.

### Design Strategy

```yaml
# Include metadata columns to track late arrivals
table_name: fact_sales
columns:
  # ... standard columns ...
  - name: event_date_key
    type: BIGINT
    description: "When the event actually occurred. Technical: FK to dim_date."
    foreign_key:
      references: dim_date.date_key
  - name: load_date_key
    type: BIGINT
    description: "When the record was loaded. Technical: FK to dim_date. Enables late-arrival detection."
    foreign_key:
      references: dim_date.date_key
```

### Key Rules

- Always include both `event_date_key` (business time) and `load_date_key` (system time)
- Use `event_date_key` for business reporting
- Use `load_date_key` for data quality monitoring and late-arrival detection
- The merge script should use MERGE (not INSERT) to handle restatements

---

## Late-Arriving Dimensions

### Problem

A fact record arrives referencing a dimension member that doesn't exist yet. For example, a sale references a new product not yet in `dim_product`.

### Design Strategy

1. Insert an "inferred" dimension row with the natural key and placeholder attributes
2. When the real dimension data arrives, update the inferred row with actual attributes

```yaml
# dim_product placeholder row
# product_key: auto-generated
# product_name: "Inferred: SKU-12345"
# category_name: "Unknown"
# is_inferred: "Inferred"  # Flag for data quality monitoring
```

### YAML Pattern

```yaml
table_name: dim_product
columns:
  # ... standard columns ...
  - name: inferred_status
    type: STRING
    description: "Inferred member indicator. Business: Whether product details are complete. Technical: Values are 'Confirmed' or 'Inferred' (placeholder pending real data)."
```

---

## Centipede Fact Table Anti-Pattern

### Problem

A fact table with too many dimension foreign keys (15+), making it look like a centipede. This usually indicates mixed grains or inappropriate dimensions.

### Symptoms

- Fact table has 15+ FK columns
- Many FKs are NULL for most rows (mixed grain)
- Queries rarely use more than 5-6 dimensions simultaneously

### Diagnosis

| Cause | Fix |
|-------|-----|
| Mixed grain (some FKs apply only to certain row types) | Split into separate fact tables by grain |
| Redundant dimensions (customer + customer_region as separate FKs) | Denormalize region into dim_customer |
| Audit columns disguised as FKs | Move audit data to a separate tracking table |

### Prevention Rule

**Design guideline:** If a fact table has more than 12-15 dimension foreign keys, review for mixed grains or redundant dimensions before proceeding.

---

## Pre-Calculated Ratio Anti-Pattern

### Problem

Storing ratios, percentages, or averages as the ONLY columns without retaining the additive components.

```yaml
# ❌ BAD: Only the ratio, no components
columns:
  - name: conversion_rate
    type: DOUBLE
    # Cannot correctly aggregate across dimensions!
    # 50% + 30% ≠ 80% (need weighted average)
```

### Fix

```yaml
# ✅ GOOD: Store components, derive ratio in semantic layer
columns:
  - name: conversions
    type: BIGINT
    description: "Conversion count. Technical: Additive."
  - name: total_visitors
    type: BIGINT
    description: "Total visitor count. Technical: Additive."
  # conversion_rate = conversions / total_visitors (computed at query time)
```

### When Pre-Calculation Is Acceptable

Pre-calculated non-additive columns are acceptable when ALL conditions are met:
1. The additive component columns are ALSO stored in the same fact table
2. The pre-calculated column is clearly documented as NON-ADDITIVE
3. The metric is queried in the majority of dashboard queries at the same grain
4. The computation is expensive enough to justify storage

---

## Periodic Snapshot Best Practices

### Snapshotting Frequency

| Entity Type | Typical Frequency | Example |
|-------------|-------------------|---------|
| Financial accounts | Daily | Account balances |
| Inventory | Daily or weekly | Stock levels |
| Subscriptions | Monthly | Active subscriber counts |
| Projects | Weekly | Resource utilization |

### Gap Handling

When a snapshot period has no data (e.g., no inventory count on weekends):

| Strategy | When |
|----------|------|
| **Carry forward** | Balance/level should persist (inventory, account balance) |
| **Leave gap** | Absence means no activity (acceptable for event-based) |
| **Insert zero row** | Explicit zero is meaningful (e.g., zero sales on a holiday) |

Document the gap handling strategy in the YAML `table_properties`:

```yaml
table_properties:
  grain: "daily_account"
  grain_type: "periodic_snapshot"
  gap_handling: "carry_forward"
  snapshot_frequency: "daily"
```
