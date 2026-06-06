# Level of Detail (LOD) Expressions in Metric Views

LOD expressions compute aggregates at a granularity **different** from the query's `GROUP BY`. Metric views support two LOD types: **Fixed** and **Exclude**. Use them for percent-of-total, percent-of-category, cohort assignment, and peer-average comparisons — calculations a plain measure cannot express because a measure always resolves at the query grain.

All examples use this skill's placeholder convention (`${catalog}.${gold_schema}`) and the `source.` / `{join_name}.` column-reference rules from the main SKILL.md.

---

## Fixed Level of Detail

A Fixed LOD computes an aggregate at a granularity you define, **ignoring** the dimensions in the query. It answers: "what is the total regardless of how I'm slicing?"

**Declared as a dimension** using a SQL window function with a `PARTITION BY` (or empty `OVER ()` for a global value):

```yaml
fields:                                  # `dimensions:` is an accepted synonym
  - name: global_revenue
    expr: SUM(source.net_revenue) OVER ()          # global — partition by nothing
  - name: category_revenue
    expr: SUM(source.net_revenue) OVER (PARTITION BY source.category)
```

Key properties:
- Fixed LOD dimensions are computed **before** query-time `WHERE` filters are applied.
- They produce a scalar that is constant within each partition.
- Use `ANY_VALUE()` to retrieve that scalar inside a measure expression.

## Percent of Total (most common LOD pattern)

> **Do NOT use `MEASURE(x) / MEASURE(total)` for percent-of-total.** `MEASURE()` resolves both operands at the query's `GROUP BY` level, so the ratio is always `1.0`. You need one side at a coarser grain — that is exactly what a Fixed LOD provides.

```yaml
version: "1.1"
source: ${catalog}.${gold_schema}.fact_orders
fields:
  - name: region
    expr: source.region
  - name: global_revenue                  # Fixed LOD: global total, ignores GROUP BY
    expr: SUM(source.net_revenue) OVER ()
measures:
  - name: revenue
    expr: SUM(source.net_revenue)
  - name: pct_of_total
    expr: MEASURE(`revenue`) / ANY_VALUE(`global_revenue`)
    format:
      type: percentage
      decimal_places:
        type: exact
        places: 1
```

How it works:
1. `global_revenue` computes `SUM(net_revenue)` globally, ignoring the query `GROUP BY`.
2. `ANY_VALUE(global_revenue)` retrieves it as a scalar in the measure context.
3. `MEASURE(revenue)` is the per-group aggregate (respects `GROUP BY`).
4. Division gives the share of the grand total.

## Percent of Category (partitioned Fixed LOD)

```yaml
fields:
  - name: category
    expr: source.category
  - name: subcategory
    expr: source.subcategory
  - name: category_total
    expr: SUM(source.net_revenue) OVER (PARTITION BY source.category)
measures:
  - name: revenue
    expr: SUM(source.net_revenue)
  - name: pct_of_category
    expr: MEASURE(`revenue`) / ANY_VALUE(`category_total`)
```

This gives each subcategory's share within its own category.

## Cohort Assignment with Fixed LOD

```yaml
fields:
  - name: customer_id
    expr: source.customer_id
  - name: first_purchase_month
    expr: DATE_TRUNC('MONTH', MIN(source.order_date) OVER (PARTITION BY source.customer_id))
  - name: order_month
    expr: DATE_TRUNC('MONTH', source.order_date)
measures:
  - name: revenue
    expr: SUM(source.net_revenue)
  - name: customer_count
    expr: COUNT(DISTINCT source.customer_id)
```

`first_purchase_month` always returns the customer's first-ever purchase month regardless of the period being queried — the basis for cohort retention analysis.

## Filtering on a Fixed LOD

Because Fixed LOD is computed before query-time filters, push any filter **inside** the window expression with `CASE` (or a `FILTER` clause):

```yaml
fields:
  - name: active_total
    expr: SUM(CASE WHEN source.status = 'active' THEN source.net_revenue ELSE 0 END) OVER ()
```

---

## Exclude Level of Detail

An Exclude LOD removes a **specific dimension** from the aggregation's partition. The partition is relative to the query `GROUP BY` — it includes all grouped dimensions **except** the excluded one. Use it to compare a row to its peer group.

**Declared as a window measure** with `range: all`:

```yaml
fields:
  - name: region
    expr: source.region
  - name: product
    expr: source.product
measures:
  - name: sales
    expr: SUM(source.amount)
  - name: sales_excl_product            # Exclude `product` from the partition
    expr: SUM(source.amount)
    window:
      - order: product
        range: all
        semiadditive: last
  - name: vs_peer_avg
    expr: MEASURE(`sales`) - MEASURE(`sales_excl_product`)
```

When queried with `GROUP BY product, region`, `sales_excl_product` aggregates across all `product` values within each `region` — effectively excluding `product`. The difference shows how each product compares to its regional peer set.

---

## Constraints

1. Fixed LOD is always a **dimension** with `expr: AGG(...) OVER (PARTITION BY ...)` (or `OVER ()`).
2. Exclude LOD is always a **window measure** with `range: all` (window measures are Experimental but supported in v1.1 — see `composability-patterns.md`).
3. `ANY_VALUE()` is required to read a Fixed LOD scalar inside a measure expression.
4. Fixed LOD is immune to query-time `WHERE` filters (computed before filtering) — filter inside the window expression instead.
5. Do not nest a Fixed LOD inside another Fixed LOD.

## Summary

| LOD Type | Declared As | Mechanism | Use Case |
|----------|-------------|-----------|----------|
| Fixed | Dimension (`fields:`) | `expr: AGG(...) OVER (PARTITION BY ...)` | Percent of total/category, cohort assignment |
| Exclude | Window measure | `window: [{order: dim, range: all, semiadditive: ...}]` | Compare to peer, average excluding one dimension |

See also: [composability-patterns.md](composability-patterns.md) (MEASURE composition, FILTER, window measures) and [querying-metric-views.md](querying-metric-views.md) (how to query these at run time).
