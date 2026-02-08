# Monitoring Requirements Template

Fill in this template for each Gold table you want to monitor.

---

## Table 1

| Field | Value |
|-------|-------|
| **Table Name** | `catalog.schema.___________` |
| **Monitor Mode** | [ ] TimeSeries / [ ] Snapshot |
| **Timestamp Column** | _______ (required for TimeSeries) |
| **Granularity** | [ ] 1 day / [ ] 1 hour / [ ] 1 week |
| **Slicing Columns** | _______, _______ |
| **Priority** | [ ] P1-Critical / [ ] P2-Important / [ ] P3-Nice-to-have |

### AGGREGATE Metrics

| Name | SQL Definition | Output Type |
|------|---------------|-------------|
| `__________` | `SUM(__________)` | Double |
| `__________` | `COUNT(__________)` | Long |
| `__________` | `AVG(__________)` | Double |

### DERIVED Metrics (from above aggregates)

| Name | Definition (uses aggregate names) | Output Type |
|------|----------------------------------|-------------|
| `__________` | `________ / NULLIF(________, 0)` | Double |

### DRIFT Metrics (period-over-period)

| Name | Definition | Output Type |
|------|-----------|-------------|
| `__________` | `(({{current_df}}.________ - {{base_df}}.________) / NULLIF({{base_df}}.________, 0)) * 100` | Double |

---

## Table 2

| Field | Value |
|-------|-------|
| **Table Name** | `catalog.schema.___________` |
| **Monitor Mode** | [ ] TimeSeries / [ ] Snapshot |
| **Timestamp Column** | _______ |
| **Granularity** | [ ] 1 day / [ ] 1 hour / [ ] 1 week |
| **Slicing Columns** | _______ |
| **Priority** | [ ] P1-Critical / [ ] P2-Important / [ ] P3-Nice-to-have |

### AGGREGATE Metrics

| Name | SQL Definition | Output Type |
|------|---------------|-------------|
| `__________` | `SUM(__________)` | Double |
| `__________` | `COUNT(__________)` | Long |

### DERIVED Metrics

| Name | Definition | Output Type |
|------|-----------|-------------|
| `__________` | `________ / NULLIF(________, 0)` | Double |

### DRIFT Metrics

| Name | Definition | Output Type |
|------|-----------|-------------|
| `__________` | `{{current_df}}.________ - {{base_df}}.________` | Double |

---

## Checklist Before Implementation

- [ ] All tables exist and contain data
- [ ] Timestamp columns identified for TimeSeries tables
- [ ] Slicing columns are low-cardinality (<100 unique values)
- [ ] DERIVED metrics reference only AGGREGATE metrics defined above them
- [ ] DRIFT metrics use `{{current_df}}/{{base_df}}` template syntax
- [ ] Monitoring schema name decided (convention: `{schema}_monitoring`)
- [ ] Alert strategy defined per priority level
