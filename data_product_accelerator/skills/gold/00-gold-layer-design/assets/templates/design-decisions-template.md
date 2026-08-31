# DESIGN_DECISIONS.md

> **Purpose:** This file is the per-run contract between the orchestrator and every subagent that produces YAML, ERD, lineage, or validation artifacts. Fill it out at the end of Phase 2 — **before** any YAML is generated in Phase 4 — and include its full text (not by path reference) in every subagent prompt.
>
> **Lifecycle:** Written once by the orchestrator in Phase 2; read by every Phase 3-7 step; re-read by Phase 8 semantic validation. Never regenerated mid-run.

---

## 1. Table Inventory

One row per Gold table. Derived from Phase 0 entity classification and Phase 2 dimensional modeling.

| Table name | Entity type (dim/fact/bridge) | Domain | SCD type | Grain (facts only) | Source Silver table(s) |
|------------|-------------------------------|--------|----------|--------------------|------------------------|
| `dim_customer` | dim | customer | SCD Type 2 | — | silver.customer |
| `fact_sales_daily` | fact | sales | — | store × product × day | silver.sales_transactions |
| ... | ... | ... | ... | ... | ... |

---

## 2. Foreign-Key Format Contract

Every `foreign_keys:` entry in every YAML file MUST use exactly this shape:

```yaml
foreign_keys:
  - columns: ["fk_column_name"]
    references: target_table(target_column)
    nullable: true   # or false
```

**Rules:**
- The three keys `columns`, `references`, `nullable` are mandatory. No other keys are permitted on an FK entry.
- `columns:` is always a list, even for single-column FKs.
- `references:` is always `target_table(target_column)` — no schema/catalog prefix at design time.
- `nullable:` is required even when `false`. No defaulting.
- If `nullable: true`, the target dimension MUST declare an `unknown_member:` block (see §5 below and `references/yaml-schema-patterns.md`).

---

## 3. Description Format Contract

Every `description:` string — table-level and column-level — MUST match:

```
One-sentence definition. Business: <business context>. Technical: <implementation details>.
```

**Rules:**
- The literal string `Business:` and `Technical:` are required section markers.
- **Do NOT include literal `[`, `]`, `<`, or `>` characters** in descriptions. The angle brackets above are placeholder syntax for THIS template only.
- Descriptions are single-line or paragraph YAML block scalars — do not embed newlines inside the Business: / Technical: sections.
- Column descriptions should be self-contained; do not prefix with `"LLM:"`, `"TODO:"`, or similar scaffolding.

**Example (correct):**
```yaml
description: "Customer surrogate key. Business: Unique customer identifier used across all fact joins. Technical: MD5 hash of customer_id and effective_from."
```

---

## 4. Transformation Type Enum

Every `lineage.transformation` value across every YAML column MUST be one of these 15 standard types (from `references/lineage-documentation-guide.md`):

```
DIRECT_COPY | RENAME | CAST | AGGREGATE_SUM | AGGREGATE_SUM_CONDITIONAL
AGGREGATE_COUNT | AGGREGATE_AVG | DERIVED_CALCULATION | DERIVED_CONDITIONAL
HASH_MD5 | HASH_SHA256 | COALESCE | DATE_TRUNC | GENERATED | LOOKUP
```

**Edge-case mapping — do NOT invent new types:**

| Source pattern | Correct type | Not this |
|----------------|--------------|----------|
| Boolean-to-text conversion (`is_verified` → `"Verified"/"Unverified"`) | `DERIVED_CONDITIONAL` | ~~BOOLEAN_TO_LABEL~~ |
| SCD2 `effective_to` close (auto-generated during merge) | `GENERATED` | ~~SCD2_CLOSE~~ |
| SCD2 `is_current` flag | `GENERATED` | ~~SCD2_CURRENT_FLAG~~ |
| Join to another table to bring in attributes | `LOOKUP` | ~~JOIN_LOOKUP~~ |
| Rename + type change in one step | `RENAME` (document the cast in `transformation_logic`) | ~~RENAME_CAST~~ |

Validation 5 in `design-workers/07-design-validation` fails the run if any other value appears.

---

## 5. Top-Level YAML Key Contract

Every Gold YAML file MUST have these mandatory top-level keys:

- `table_name`
- `domain`
- `description`
- `table_properties` (includes `delta.enableChangeDataFeed`, `delta.enableRowTracking`, `delta.autoOptimize.optimizeWrite`, `delta.autoOptimize.autoCompact`, `layer: gold`)
- `clustering: auto`
- `columns`
- `primary_key`

**Dimension-only keys** (present in every `dim_*.yaml`):

- `scd_type` (`SCD_TYPE_1`, `SCD_TYPE_2`)
- `business_key` (columns that uniquely identify a source entity, distinct from the surrogate PK)
- `unknown_member` — required when any fact FK to this dim has `nullable: true`; recommended for every business dim regardless

**Fact-only keys** (present in every `fact_*.yaml`):

- `grain` (plain-English grain statement)
- `grain_type` (`transactional`, `periodic_snapshot`, `accumulating_snapshot`)
- `fact_type` (`transactional`, `snapshot`, `factless`)
- `foreign_keys` (list of FK entries using the §2 format)
- `measures` (each with `name`, `type`, `additivity`, `description`)

---

## 6. Boolean-to-Text Conversion List

Per `02-dimension-patterns` Rule 3, every boolean source column in a **business-sourced** dimension is rewritten as a STRING attribute in the Gold layer. List each conversion here so subagents use consistent target values.

| Source table.column | Source type | Gold table.column | Gold type | Gold values |
|---------------------|-------------|-------------------|-----------|-------------|
| `silver.user.is_verified` | BOOLEAN | `dim_user.verification_status` | STRING | `"Verified"` / `"Unverified"` |
| `silver.user.is_active` | BOOLEAN | `dim_user.active_status` | STRING | `"Active"` / `"Inactive"` |
| ... | ... | ... | ... | ... |

**Exception — generated date/time dimensions.** `dim_date` (and `dim_time` if present) MAY retain `BOOLEAN` for indicator columns (`is_weekend`, `is_holiday`, `is_business_day`, `is_month_end`, …). These dimensions are generated, not sourced from a business system; the canonical template in `references/yaml-schema-patterns.md` uses BOOLEAN for these columns and Validation 5 whitelists them.

---

## 7. Population Strategy

Every Gold table's YAML declares a `population_strategy` so the Gold pipeline (step `01-gold-layer-setup`) knows how to load it:

| Table | `population_strategy` | Pipeline behavior |
|-------|----------------------|-------------------|
| All Silver-sourced dims/facts | `merge_from_silver` | MERGE from the Silver source named in lineage |
| `dim_date` (and `dim_time`) | `generate_sequence` | INSERT from a generated date/time sequence — NO Silver source |

**`dim_date` is a special case:** it has `silver_table: None` in lineage and is populated by a one-time INSERT from sequence generation, NOT a MERGE from Silver. Document it here so the Gold pipeline does not fail trying to read a non-existent Silver source.

---

## 8. Industry Alignment (Optional)

Fill this in ONLY when `industry_reference_source` ≠ `none`. It records how the Gold design aligns to a **Databricks Industry Vibe Data Model** (or other canonical industry reference). Owned by `design-workers/08-industry-alignment`; scored advisory-only by Validation 6. This alignment is **semantic coverage, not structural equivalence** — never invent Gold tables for uncovered entities.

| Field | Value |
|-------|-------|
| Industry vertical | `retail` |
| Reference source | `vibe_generated` \| `published` |
| Reference path | `context/industry_reference.yaml` |
| Provisional coverage % (Phase 0 overlay) | `88%` |

**Domain renames** (source/working name → canonical industry domain):

| From | To (industry domain) |
|------|----------------------|
| `sales_txn` | `sales` |

**Conformed-dimension promotions** (entities shared across 2+ facts):

| Dimension | Shared by (facts) |
|-----------|-------------------|
| `dim_customer` | `fact_sales`, `fact_returns` |

**Terminology changes** (off-standard name → industry name):

| From (Gold) | To (industry term) |
|-------------|--------------------|
| `dim_buyer` | `dim_customer` |

**Gap dispositions** (every `core`/`extended` industry entity with no Gold coverage):

| Industry entity | Importance | Disposition | Rationale |
|-----------------|-----------|-------------|-----------|
| `supplier` | core | `Waived` | No supplier source data in Phase 1 (see SOURCE_TABLE_MAPPING.csv) |
| `inventory_position` | extended | `Planned` | Deferred to Phase 2 implementation |

---

## Sign-off Checklist

Before handing off to Phase 3:

- [ ] Table inventory complete (no TBDs on entity type, domain, or SCD type)
- [ ] Every fact in §1 has a grain sentence
- [ ] FK format in §2 is the only shape any subagent will use
- [ ] Description format in §3 is agreed and the no-literal-brackets rule is explicit
- [ ] Transformation enum in §4 is the only allowed set
- [ ] Top-level key contract in §5 matches `references/yaml-schema-patterns.md`
- [ ] Boolean-to-text list in §6 is complete for every business dim
- [ ] Population strategy in §7 set for every table (`generate_sequence` for `dim_date`/`dim_time`, `merge_from_silver` otherwise)
- [ ] `gold_layer_design/DESIGN_DECISIONS.md` written to disk
- [ ] This file will be embedded verbatim in every Phase 4 subagent prompt
- [ ] (If `industry_reference_source` ≠ `none`) Section 8 complete: coverage %, domain/terminology changes, and every core/extended gap dispositioned; `INDUSTRY_CROSSWALK.csv` written
