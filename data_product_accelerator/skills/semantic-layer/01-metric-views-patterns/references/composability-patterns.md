# Composability and Advanced Measure Patterns

Composability enables building complex metrics by reusing simpler, foundational measures. Instead of writing nested SQL for every derived KPI, define core "atomic" measures once and reference them in composed measures via the `MEASURE()` function.

Source: [Composability in Metric Views](https://docs.databricks.com/aws/en/metric-views/data-modeling/composability)

## Atomic vs Composed Measures

| Measure Type | Description | Example |
|-------------|-------------|---------|
| **Atomic** | Simple, direct aggregation on a source column. Building blocks. | `SUM(o_totalprice)` |
| **Composed** | Combines other measures using `MEASURE()` function. | `MEASURE(total_revenue) / MEASURE(order_count)` |

**Rule:** Always define atomic measures FIRST, then define composed measures that reference them.

## MEASURE() Function

The `MEASURE()` function allows a measure definition to reference any other measure defined within the same metric view.

```yaml
measures:
  # Atomic measures (building blocks)
  - name: total_revenue
    expr: SUM(o_totalprice)
    comment: The gross total value of all orders.
    display_name: Total Revenue

  - name: order_count
    expr: COUNT(1)
    comment: The total number of orders.
    display_name: Order Count

  # Composed measure: Average Order Value
  - name: avg_order_value
    expr: MEASURE(total_revenue) / MEASURE(order_count)
    comment: Total revenue divided by the number of orders.
    display_name: Avg Order Value
    format:
      type: currency
      currency_code: USD
      decimal_places:
        type: exact
        places: 2
```

If the definition of `total_revenue` changes (e.g., a filter to exclude tax is added), `avg_order_value` automatically inherits the change.

## Conditional Logic with FILTER Clause

Use `FILTER` clauses to create conditional aggregations without separate CTEs or CASE expressions:

```yaml
measures:
  # Total orders (denominator)
  - name: total_orders
    expr: COUNT(1)
    comment: Total volume of orders regardless of status.

  # Fulfilled orders (numerator) — filtered
  - name: fulfilled_orders
    expr: COUNT(1) FILTER (WHERE o_orderstatus = 'F')
    comment: Only includes orders marked as fulfilled.

  # Composed ratio
  - name: fulfillment_rate
    expr: MEASURE(fulfilled_orders) / MEASURE(total_orders)
    display_name: Order Fulfillment Rate
    format:
      type: percentage
```

**Multi-aggregate FILTER:** When the expression contains multiple aggregate functions, apply FILTER to each:
```yaml
  - name: revenue_per_customer_open_orders
    expr: SUM(o_totalprice) FILTER (WHERE o_orderstatus='O') / COUNT(DISTINCT o_custkey) FILTER (WHERE o_orderstatus='O')
```

## Top-Level `filter:` Field

A top-level `filter:` applies a SQL boolean WHERE clause to ALL queries against the metric view:

```yaml
version: "1.1"
source: ${catalog}.${gold_schema}.fact_orders
filter: order_date > DATE'2020-01-01'  # Applied to every query

dimensions:
  - name: order_date
    expr: source.order_date
measures:
  - name: total_revenue
    expr: SUM(source.revenue)
```

This is equivalent to adding `WHERE order_date > DATE'2020-01-01'` to every query against this metric view.

## Best Practices

1. **Combine with semantic metadata:** After composing a ratio, use format metadata to automatically display as percentage or currency.
2. **Prioritize readability:** The `expr` for a composed measure should read like a formula: `MEASURE(Gross Profit) / MEASURE(Total Revenue)`.
3. **Use `MEASURE()` for consistency:** Never repeat aggregation logic manually if a measure for that aggregation already exists.
4. **Define atomic measures first:** Establish fundamental measures (SUM, COUNT, AVG) before defining derived measures.

---

## Window Measures (Experimental — supported in v1.1)

Window measures enable windowed, cumulative, or semiadditive aggregations (moving averages, period-over-period changes, running totals). The feature carries **Experimental** status but is **supported in `version: 1.1`** — use `version: "1.1"` in your YAML; you do NOT need to fall back to the legacy v0.1.

> The unsupported field is the top-level `window_measures:` *array* (see SKILL.md). The per-measure `window:` property below is the supported form.

### Required and optional `window` fields

| Field | Required | Description |
|-------|----------|-------------|
| `order` | yes | The dimension that orders the window. Must be a dimension defined in the same metric view. |
| `range` | yes | Extent of the window: `current`, `cumulative`, `trailing N unit`, `leading N unit`, `all`. |
| `semiadditive` | yes | Fallback aggregation (`first` / `last`) when `order` is not in the query's GROUP BY. |
| `offset` | no | Shifts the window frame along `order` by a fixed interval (e.g. `-1 month`). DBR 18.1+. |

### Window Measure Syntax

```yaml
version: "1.1"
measures:
  - name: trailing_7d_customers
    expr: COUNT(DISTINCT o_custkey)
    window:
      - order: date
        range: trailing 7 day
        semiadditive: last
```

### Window Range Options

| Range | Description |
|-------|-------------|
| `trailing N unit` | N units before each point; **excludes** the anchor (current) row by default. Units: `day`, `week`, `month`, `year`. |
| `cumulative` | Running total from the start of the dataset up to and including the current point |
| `current` | Single point — no aggregation across the order dimension (used for semiadditive balances) |
| `leading N unit` | N units after each point; **excludes** the anchor row by default |
| `all` | Entire dataset regardless of window (used for Exclude LOD — see `level-of-detail.md`) |

**Anchor-row modifiers (`inclusive` / `exclusive`):** `trailing` and `leading` exclude the anchor row by default. Append a modifier to change that:
- `trailing 7 day inclusive` — includes the current date in the 7-day window
- `leading 3 month exclusive` — explicitly excludes the current month

### Window Offset (period-over-period; DBR 18.1+)

The `offset` field shifts the window frame backward or forward along the `order` dimension by a fixed interval, enabling prior-period comparisons (MoM, YoY) without a second `current` measure.

```yaml
version: "1.1"
measures:
  - name: sales_same_month_last_year
    expr: SUM(o_totalprice)
    window:
      - order: month
        range: current
        offset: -12 month   # shift the window back 12 months (DBR 18.1+)
        semiadditive: last
```

Negative offsets look backward (prior periods); positive offsets look forward. The `offset` unit must match the grain of the `order` dimension (don't use `-1 day` when `order` is monthly). Confirm your runtime is DBR 18.1+ before using `offset`.

**Month-to-Date (MTD):**
```yaml
measures:
  - name: mtd_revenue
    expr: SUM(o_totalprice)
    window:
      - order: date
        range: trailing 1 month inclusive
        semiadditive: last
```

### Common Patterns

**Period-over-Period Growth:**
```yaml
measures:
  - name: previous_day_sales
    expr: SUM(o_totalprice)
    window:
      - order: date
        range: trailing 1 day
        semiadditive: last
  - name: current_day_sales
    expr: SUM(o_totalprice)
    window:
      - order: date
        range: current
        semiadditive: last
  - name: day_over_day_growth
    expr: (MEASURE(current_day_sales) - MEASURE(previous_day_sales)) / MEASURE(previous_day_sales) * 100
```

**Running Total:**
```yaml
  - name: running_total_sales
    expr: SUM(o_totalprice)
    window:
      - order: date
        range: cumulative
        semiadditive: last
```

**Year-to-Date (YTD):**
```yaml
  - name: ytd_sales
    expr: SUM(o_totalprice)
    window:
      - order: date
        range: cumulative
        semiadditive: last
      - order: year
        range: current
        semiadditive: last
```

**Semiadditive Balance (last known value):**
```yaml
  - name: semiadditive_balance
    expr: SUM(balance)
    window:
      - order: date
        range: current
        semiadditive: last
```

Source: [Window Measures docs](https://docs.databricks.com/aws/en/metric-views/data-modeling/window-measures)
