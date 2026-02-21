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

## Window Measures (Experimental, v0.1 Only)

Window measures enable windowed, cumulative, or semiadditive aggregations. **This feature is Experimental and requires YAML version 0.1 (DBR 16.4-17.1). It is NOT available in v1.1.**

If you are using v1.1 (which this skill targets), calculate windowed aggregations in SQL/Python outside the metric view. The information below is provided for reference if you need v0.1 capabilities.

### Window Measure Syntax

```yaml
version: "0.1"  # Required for window measures
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
| `trailing N unit` | Sliding window of N units back from current |
| `cumulative` | Running total from start to current |
| `current` | Current period only |
| `leading N unit` | N units forward from current |
| `all` | All rows regardless of window |

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
