# Industry Data Model Alignment

> Advisory design-time capability that benchmarks a Gold dimensional design against a
> **Databricks Industry Vibe Data Model** (or any canonical industry reference) to measure
> entity coverage, terminology alignment, and gaps — WITHOUT forcing the Gold star schema
> to mimic a normalized business model.

## What "Databricks Industry Vibe Data Models" Are

Two related artifacts published by Databricks:

1. **Vibe Data Modeling** — a Databricks-native, LLM-powered agent that turns a plain-English
   business description into a governed, deployable **Silver-layer business model**: UC schemas,
   tables, foreign keys, classification tags, metric views, an RDFS ontology, a DBML diagram, and
   sample data. Every iteration is validated against **251 enforceable rules**, reviewed by two
   "architect personas," and repaired in an agentic loop before deployment. No version is overwritten.
2. **40+ open-source Lakehouse Industry Data Models** — per-vertical reference models the agent
   produced, drawing on canonical industry schemas (TM Forum SID for telecom, ARTS for retail,
   ACORD for insurance, HL7 for healthcare, BIAN for banking) as **inspiration, not rigid templates**.

References:
- Blog: <https://www.databricks.com/blog/reimagining-data-modeling-lakehouse-introducing-vibe-data-modeling>
- Repo: <https://github.com/databricks-industry-solutions/lakehouse-industry-data-models>
- Design guide: `model-agent/docs/design-guide.md` in that repo

## Critical Nuance: Silver Business Model ≠ Gold Dimensional Model

This is the single most important thing to internalize before running the check.

| Dimension | Vibe / Industry Data Model | This skill's Gold layer |
|-----------|----------------------------|-------------------------|
| Layer | Silver (analytical business model) | Gold (serving / BI) |
| Paradigm | Normalized business entities (≈3NF) | Dimensional / Kimball star schema |
| Primary objects | Business entities + relationships | `dim_*`, `fact_*`, `bridge_*` |
| Keys | Natural/business keys | Surrogate PKs, business keys as attributes |
| Goal | Faithful model of the business | Query-optimized analytics |

**Consequence:** alignment is **semantic coverage**, not structural equivalence. A single industry
business entity (e.g., `customer`) may map to a conformed `dim_customer` plus attributes absorbed
into several facts. Do **not** try to make the Gold model structurally match the business model —
that would defeat the purpose of the Gold layer. The check answers *"is the business concept
represented and named consistently?"*, never *"does the table structure match?"*.

## Two Modes of the Check

Pick based on what the customer can provide (captured in Phase 1 as `industry_reference_source`):

### Mode A — Customer's own Vibe-generated Silver model (strongest)

The customer ran the Vibe agent and has a governed Silver model (DBML, YAML, or a deployed UC
catalog). Highest-value comparison because it already uses the customer's terminology and divisions.
Reduce it to the alignment manifest below (extract entities/domains/attributes/sensitivity from the
DBML or UC catalog).

### Mode B — Published vertical reference model (softer)

No customer Vibe model exists. Use the matching published reference model for the vertical as an
*archetype* benchmark. Expect a lower coverage target — the published model is a superset archetype,
so legitimate "not applicable" gaps are normal and should be waived with rationale, not chased.

## Inputs (captured in Phase 1, recorded in `DESIGN_DECISIONS.md` Section 8)

| Field | Example | Notes |
|-------|---------|-------|
| `industry_vertical` | `retail` | Drives which reference model applies |
| `industry_reference_source` | `vibe_generated` \| `published` \| `none` | `none` skips Validation 6 |
| `industry_reference_path` | `context/industry_reference.yaml` | The normalized alignment manifest (below) |

If `industry_reference_source: none`, Validation 6 is **skipped** and recorded as "not applicable" in
the validation report — never a hard failure.

## The Alignment Manifest (deterministic, offline)

You cannot reliably parse arbitrary DBML/UC at design time, and you should not depend on network
access during validation. Reduce whichever reference you have (Mode A or B) into a single normalized
manifest so the check is deterministic and reproducible. A starter is in
`assets/templates/industry_reference.template.yaml`.

`context/industry_reference.yaml`:

```yaml
industry: retail
source: vibe_generated          # vibe_generated | published
reference: "Databricks Lakehouse Industry Data Model — Retail (ARTS-inspired)"
version: "2026-08"
domains:
  - name: customer
    entities:
      - name: customer
        aliases: [party, shopper, guest, member]
        importance: core        # core | extended | optional
        sensitivity: PII
        core_attributes: [customer_id, full_name, email, loyalty_tier, status]
      - name: customer_address
        aliases: [address, location]
        importance: extended
        sensitivity: PII
        core_attributes: [address_id, customer_id, postal_code, country]
  - name: product
    entities:
      - name: product
        aliases: [item, sku, article]
        importance: core
        sensitivity: none
        core_attributes: [product_id, product_name, category, brand, unit_price]
  - name: sales
    entities:
      - name: sales_transaction
        aliases: [order, sale, purchase, transaction]
        importance: core
        sensitivity: none
        core_attributes: [transaction_id, customer_id, transaction_ts, total_amount]
```

`importance` drives the scoring weight; `aliases` drive terminology matching; `sensitivity` is
cross-checked against the Gold PII tags.

## The Crosswalk Method

The deliverable is a **dim/fact ↔ business-entity crosswalk**, produced by matching Gold tables to
reference entities on name + alias, then classifying:

| Match state | Meaning | Action |
|-------------|---------|--------|
| **Covered** | A Gold table maps to the reference entity (by name/alias) | Record the mapping |
| **Absorbed** | Entity has no own table but its attributes live in a dim/fact | Record with note; counts as covered |
| **Waived** | Entity intentionally out of scope | Require rationale (reuse `SOURCE_TABLE_MAPPING.csv` EXCLUDED) |
| **Planned** | Entity deferred to a later phase | Require phase note (reuse `SOURCE_TABLE_MAPPING.csv` PLANNED) |
| **Gap** | Core/extended entity neither covered nor waived/planned | Flag for review |

`Extension` (a Gold table with no reference entity) is fine and informational — record it as a
customer-specific extension. The worker auto-suggests matches via name/alias; a human confirms
`Absorbed`/`Waived`/`Planned` calls. Only unresolved **core/extended** gaps are noteworthy.

## Scoring Rubric

Report three sub-scores plus a headline coverage %:

1. **Entity coverage** (weighted): `covered_weight / applicable_weight`, weights `core=3, extended=2,
   optional=1`; `Waived`/`Planned` entities are removed from the denominator (not penalized).
2. **Terminology alignment**: fraction of `Covered` entities whose Gold table name matches the
   reference name/alias set (flags "modeled it but named it something the industry won't recognize").
3. **Sensitivity alignment**: fraction of `PII` reference entities whose covering Gold table carries a
   `PII` tag (`layer`/`domain`/`PII` tags are already mandated by `naming-tagging-standards`).

Suggested advisory thresholds (NOT gates):

| Core coverage | Signal |
|---------------|--------|
| ≥ 85% | Strong alignment — proceed |
| 60–85% | Review gaps with stakeholders in Phase 9 |
| < 60% | Likely missing well-known entities — revisit Phase 2 |

## Output Artifact: `INDUSTRY_ALIGNMENT.md`

```markdown
# Industry Data Model Alignment Report

- Industry: retail
- Reference: Databricks Lakehouse Industry Data Model — Retail (vibe_generated)
- Generated: 2026-08-30

## Scorecard
| Metric | Score |
|--------|-------|
| Core entity coverage | 88% |
| Terminology alignment | 92% |
| Sensitivity (PII) alignment | 100% |

## Crosswalk
| Reference entity | Importance | State | Gold table(s) | Notes |
|------------------|-----------|-------|---------------|-------|
| customer | core | Covered | dim_customer | |
| customer_address | extended | Absorbed | dim_customer | Flattened into dim (SCD2) |
| product | core | Covered | dim_product | |
| sales_transaction | core | Covered | fact_sales | grain: one row per line item |
| loyalty_program | extended | Waived | — | Out of scope Phase 1 (see SOURCE_TABLE_MAPPING) |
| supplier | core | Gap | — | ⚠️ No Gold coverage, no waiver — review |

## Extensions (customer-specific, no reference entity)
| Gold table | Domain | Note |
|------------|--------|------|
| dim_channel | sales | Customer-specific omnichannel breakdown |

## Recommendations
- Add `supplier`/`dim_supplier` or explicitly waive it in SOURCE_TABLE_MAPPING.csv.
```

## What NOT to Do

- **Don't force normalization.** Never restructure the Gold star schema to match the business model's shape.
- **Don't import Vibe's 251 rules wholesale.** They target Silver business models. Reuse only
  entity-coverage, terminology, and sensitivity ideas.
- **Don't make it a blocking gate.** It is advisory. `run_design_validation`'s `all_valid` must not
  depend on it.
- **Don't require network access.** Reduce the reference to `industry_reference.yaml` up front; the
  check runs offline against that file.

## Related

- `../SKILL.md` — the worker's Phase 0 / Phase 2 behavior and crosswalk contract
- `../scripts/industry_overlay.py` — matching, overlay, and crosswalk writer implementation
- `design-workers/07-design-validation/SKILL.md` — Validation 6 (consumes the crosswalk)
- `00-gold-layer-design/references/validation-checklists.md` — Industry Alignment checklist
