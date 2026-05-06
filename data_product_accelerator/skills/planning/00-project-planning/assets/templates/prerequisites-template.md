# Prerequisites: Data Layer Summary

## Overview

**Planning mode:** {acceleration | workshop}
**Selected planning source:** `{deployed_gold | gold_design | deployed_silver | deployed_bronze | source_csv}` (set by Phase 0)
**Implementation readiness:** `{gold_ready | gold_design_only | workshop_deployable | workshop_draft}`
**Requires Gold promotion:** `{true | false}`
**Description:** Summary of the data layers detected by Phase 0. The selected planning source is the basis for all use cases, addendums, and manifests in this plan.

> **Status conventions:** Use `✅ Complete` for layers that exist with data; `📐 Designed only` when YAML/CSV exists but no live tables (e.g., Gold design YAML when Gold is not yet deployed); `Planned only` for layers explicitly skipped; `N/A` when not relevant for the selected planning source.

---

## Bronze Layer

**Schema:** `{project}_bronze`
**Tables:** {n}
**Status:** {✅ Complete | Planned only | N/A}

| Category | Tables |
|----------|--------|
| {Category 1} | {table_1}, {table_2} |
| {Category 2} | {table_3} |

---

## Silver Layer

**Schema:** `{project}_silver`
**Tables:** {m} streaming tables
**Status:** {✅ Complete | Planned only | N/A}

| Type | Tables |
|------|--------|
| Dimensions | silver_{entity}_dim |
| Facts | silver_{entity} |

---

## Gold Layer

**Schema:** `{project}_gold`
**Tables:** {n} ({d} dimensions + {f} facts)
**Status:** {✅ Complete (deployed) | 📐 Designed only (YAML present, not deployed) | Planned only | N/A}

| Type | Tables |
|------|--------|
| Dimensions | dim_{entity} |
| Facts | fact_{entity} |

---

## Source Schema (CSV) — only when `selected_layer = source_csv`

**Paths:** `data_product_accelerator/context/{file}.csv`
**Entities:** {n}
**Status:** {✅ Present | N/A}

| Entity | Columns |
|--------|---------|
| {entity_1} | {col_1, col_2, ...} |

---

## Next Phase

**→ [Phase 1: Use Cases](./phase1-use-cases.md)**

> `requires_gold_promotion` is **advisory only** — it never blocks deployment. Downstream stages (semantic-layer, observability, ml, genai-agents) deploy against whichever layer `planning_source.selected_layer` declares: Gold for production / acceleration, Silver or Bronze for workshop deployments, with a quality advisory recommending Gold promotion for production. The only state that stops downstream deployment is `implementation_readiness: workshop_draft`, which is emitted only when `selected_layer = source_csv` (no live tables to deploy against).
