# Advanced Merge Patterns

Additional merge patterns beyond the core SCD Type 1/2 and fact aggregation patterns documented in `merge-script-patterns.md`. These patterns correspond to advanced design patterns from `design-workers/02-dimension-patterns` and `design-workers/03-fact-table-patterns`.

---

## Pattern Selection: YAML-Driven

Select the correct merge pattern based on YAML `table_properties`:

| YAML `grain_type` | YAML `entity_type` | Merge Pattern | Template File |
|---|---|---|---|
| `transaction` | `fact` | Standard fact aggregation | `assets/templates/fact-table-aggregation-merge.py` |
| `accumulating_snapshot` | `fact` | Accumulating snapshot | `assets/templates/accumulating-snapshot-merge.py` |
| `factless` | `fact` | Factless fact | `assets/templates/factless-fact-merge.py` |
| `periodic_snapshot` | `fact` | Periodic snapshot | `assets/templates/periodic-snapshot-merge.py` |
| (any) | `dimension` + `dimension_pattern: junk` | Junk dimension populate | `assets/templates/junk-dimension-populate.py` |
| (any) | `dimension` + `scd_type: 1` | SCD Type 1 | `assets/templates/scd-type1-merge.py` |
| (any) | `dimension` + `scd_type: 2` | SCD Type 2 | `assets/templates/scd-type2-merge.py` |

```python
def select_merge_pattern(meta: dict) -> str:
    """Select merge pattern based on YAML metadata."""
    grain_type = meta.get("grain_type", "")
    entity_type = meta.get("entity_type", "")
    dim_pattern = meta.get("dimension_pattern", "")
    scd_type = str(meta.get("scd_type", ""))

    if entity_type == "fact":
        if grain_type == "accumulating_snapshot":
            return "accumulating_snapshot"
        elif grain_type == "factless":
            return "factless"
        elif grain_type == "periodic_snapshot":
            return "periodic_snapshot"
        else:
            return "fact_aggregation"
    elif entity_type == "dimension":
        if dim_pattern == "junk":
            return "junk_dimension"
        elif scd_type == "2":
            return "scd_type2"
        else:
            return "scd_type1"
    return "scd_type1"
```

---

## Accumulating Snapshot Fact Tables

**When to use:** Business processes with defined milestones that progress over time (e.g., order fulfillment: ordered → shipped → delivered).

**YAML trigger:** `table_properties.grain_type: accumulating_snapshot`

**Key implementation details:**
- One row per business process instance — rows are UPDATED, not inserted, as milestones occur
- Milestone columns (e.g., `ship_date`, `delivery_date`) start NULL and fill in over time
- MERGE UPDATE SET uses conditional logic: only update when target is NULL and source has value
- Lag/duration columns recalculated on every update using DATEDIFF between milestones

**YAML metadata required:**
```yaml
table_properties:
  grain_type: accumulating_snapshot
  milestone_columns: [order_date, ship_date, delivery_date]
  lag_columns:
    days_to_ship: {from: order_date, to: ship_date}
    days_to_deliver: {from: ship_date, to: delivery_date}
```

**Template:** `pipeline-workers/02-merge-patterns/assets/templates/accumulating-snapshot-merge.py`

**Design reference:** `design-workers/03-fact-table-patterns/references/fact-pattern-catalog.md` — Accumulating Snapshot section

---

## Factless Fact Tables

**When to use:** Recording event occurrences or coverage relationships where row existence IS the fact (e.g., student attendance, promotion coverage).

**YAML trigger:** `table_properties.grain_type: factless`

**Key implementation details:**
- No measure columns — only FK keys, degenerate dimensions, and audit timestamps
- Simple MERGE with INSERT only (no UPDATE — row exists or it doesn't)
- COUNT(*) is the only measure, computed in the BI layer
- Composite PK formed by all FK columns

**Template:** `pipeline-workers/02-merge-patterns/assets/templates/factless-fact-merge.py`

**Design reference:** `design-workers/03-fact-table-patterns/references/fact-pattern-catalog.md` — Factless Fact Tables section

---

## Periodic Snapshot Fact Tables

**When to use:** Capturing cumulative state at regular intervals (e.g., daily account balance, weekly inventory level).

**YAML trigger:** `table_properties.grain_type: periodic_snapshot`

**Key implementation details:**
- One row per entity per snapshot period
- Full replacement of each snapshot period (MERGE with UPDATE on match)
- Semi-additive measures: additive across non-time dimensions, NOT across time
- Snapshot date column is part of the composite PK

**YAML metadata required:**
```yaml
table_properties:
  grain_type: periodic_snapshot
  snapshot_period: daily  # or weekly, monthly
```

**Template:** `pipeline-workers/02-merge-patterns/assets/templates/periodic-snapshot-merge.py`

**Design reference:** `design-workers/03-fact-table-patterns/references/fact-pattern-catalog.md` — Periodic Snapshot section

---

## Junk Dimension Population

**When to use:** Consolidating low-cardinality flags/indicators from fact tables into a single dimension (e.g., payment method, shipping type, return flag).

**YAML trigger:** `table_properties.dimension_pattern: junk`

**Key implementation details:**
- Extract DISTINCT flag combinations from Silver source
- Generate MD5 surrogate key from concatenated flag values
- Replace NULL flag values with "Unknown" before hashing (consistent keys)
- INSERT only — flag combinations are immutable definitions
- Typically small table (2^N rows for N boolean flags)

**YAML metadata required:**
```yaml
table_properties:
  dimension_pattern: junk
  flag_columns: [payment_type, is_online, is_gift_wrapped]
```

**Template:** `pipeline-workers/02-merge-patterns/assets/templates/junk-dimension-populate.py`

**Design reference:** `design-workers/02-dimension-patterns/references/dimension-pattern-catalog.md` — Junk Dimensions section

---

## Checklist: Advanced Pattern Implementation

Before implementing any advanced merge pattern:

- [ ] Confirm YAML `grain_type` or `dimension_pattern` matches the pattern
- [ ] Read the corresponding design-worker skill for design rationale
- [ ] Read the template file for implementation structure
- [ ] Extract ALL metadata from YAML (milestone_columns, lag_columns, flag_columns, snapshot_period)
- [ ] Run Silver contract validation (see `references/design-to-pipeline-bridge.md`)
- [ ] Run deduplication before MERGE (mandatory for all patterns)
- [ ] Run grain validation appropriate to the pattern type
- [ ] Run schema validation before MERGE execution
