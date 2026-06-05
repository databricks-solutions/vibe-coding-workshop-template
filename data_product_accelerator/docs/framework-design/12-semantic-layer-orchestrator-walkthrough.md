# Semantic Layer Orchestrator — Visual Walkthrough

How the `00-semantic-layer-setup` orchestrator progressively loads worker skills, manages context, and builds the complete Databricks semantic layer (Metric Views, TVFs, Genie Spaces) from a single manifest.

> **Related skills:** [`00-semantic-layer-setup`](../../skills/semantic-layer/00-semantic-layer-setup/SKILL.md), [`01-metric-views-patterns`](../../skills/semantic-layer/01-metric-views-patterns/SKILL.md), [`02-databricks-table-valued-functions`](../../skills/semantic-layer/02-databricks-table-valued-functions/SKILL.md), [`03-genie-space-patterns`](../../skills/semantic-layer/03-genie-space-patterns/SKILL.md), [`04-genie-space-export-import-api`](../../skills/semantic-layer/04-genie-space-export-import-api/SKILL.md)

---

## The Agent's Journey Through the Semantic Layer Orchestrator

### Step 0: Skill Activation (~100 tokens)

When a user says something like *"Set up the semantic layer for my project"*, the agent framework first evaluates which skill to activate by matching against the `description` field in each skill's YAML frontmatter:

```yaml
name: semantic-layer-setup
description: >
  End-to-end orchestrator for building the Databricks semantic layer including Metric Views,
  Table-Valued Functions (TVFs), and Genie Spaces...
```

This `description` is loaded at startup for ALL skills (~100 tokens each). The keywords "semantic layer", "Metric Views", "TVFs", "Genie Spaces" match the user's intent. The agent activates this skill and reads the full SKILL.md (~536 lines).

### Step 1: The Decision Tree — Should I Even Be Here?

The first thing the agent encounters after the overview is the **Decision Tree**:

| Question | Action |
|----------|--------|
| Building semantic layer end-to-end? | **Use this skill** — it orchestrates everything |
| Only need Metric Views? | Read `01-metric-views-patterns/SKILL.md` directly |
| Only need TVFs? | Read `02-databricks-table-valued-functions/SKILL.md` directly |
| Only need Genie Space setup? | Read `03-genie-space-patterns/SKILL.md` directly |
| Need Genie API automation? | Read `04-genie-space-export-import-api/SKILL.md` directly |
| Need to optimize Genie accuracy? | Read `05-genie-optimization-orchestrator/SKILL.md` directly (routes to 4 workers in `genie-optimization-workers/`) |

For an end-to-end request, the agent stays here. If the user only asked for one component, the agent would route to that specific worker skill instead.

### Step 2: The Guard Rails Lock In

Before any work begins, the agent absorbs the **Non-Negotiable Defaults** — hard constraints it cannot violate during the entire session:

| Default | Value | NEVER Do This Instead |
|---------|-------|-----------------------|
| **Manifest required** | `plans/manifests/semantic-layer-manifest.yaml` | Never create artifacts via self-discovery |
| **Metric View syntax** | `WITH METRICS LANGUAGE YAML` | Never use non-YAML metric views |
| **TVF parameters** | All `STRING` type | Never use DATE, INT, or other non-STRING params |
| **Genie warehouse** | Serverless SQL Warehouse | Never use Classic or Pro warehouse |
| **Benchmark questions** | Minimum 10 per Genie Space | Never deploy without benchmarks |
| **Column comments** | Required on all Gold tables | Never create Genie Space without column comments |

This table acts as a system-level constraint set that the agent internalizes for all subsequent phases.

### Step 3: The Progressive Disclosure Protocol

This is the **meta-strategy** — it tells the agent HOW to use its context window efficiently across the multi-hour task. Grounded in the [AgentSkills.io specification](https://agentskills.io/specification) and [Anthropic's context engineering guidance](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents):

```
DO NOT read all worker skills at the start. Read each skill ONLY when you enter its phase:
  Phase 1: Read 01-metric-views-patterns → work → persist notes → DISCARD
  Phase 2: Read 02-databricks-table-valued-functions → work → persist notes → DISCARD
  Phase 3: Read 03-genie-space-patterns + 04-genie-space-export-import-api → work → persist notes → DISCARD
  Phase 4-6: Read skills/databricks-asset-bundles → work → done
```

Each worker skill ends with a "**Notes to Carry Forward**" section that tells the agent exactly what to persist for downstream phases. The agent uses those notes — not the full skill content — as the bridge between phases.

**At each phase boundary, the agent's working memory should contain ONLY:**
1. `gold_inventory` dict (from Phase 0 — persists through all phases)
2. Previous phase's "Notes to Carry Forward" (structured summary of outputs)
3. Current phase's worker skill (read just-in-time)

Everything else — full YAML bodies, SQL source code, JSON configs — is on disk, retrievable via file paths stored in the notes.

---

## Phase 0: The Foundation — Manifest + Gold Inventory

The agent reads the manifest YAML and builds the `gold_inventory` dict. This is the only phase that doesn't read a worker skill.

```
┌─────────────────────────────────────────────────────────┐
│                      PHASE 0                            │
│                                                         │
│  1. Check: does plans/manifests/semantic-layer-         │
│     manifest.yaml exist?                                │
│     ├── NO  → STOP. Tell user to run planning skill.   │
│     └── YES → Load manifest                            │
│                                                         │
│  2. Parse manifest:                                     │
│     domains:                                            │
│       travel:                                           │
│         metric_views: [revenue_metrics, booking_metrics]│
│         tvfs: [get_bookings_by_date, get_revenue_by_...]│
│         genie_spaces: [travel_analytics]                │
│                                                         │
│  3. Build gold_inventory dict:                          │
│     ├── Parse Gold YAML files                           │
│     ├── Query live catalog (INFORMATION_SCHEMA)         │
│     └── Cross-reference → flag discrepancies            │
│                                                         │
│  4. GATE: gold_inventory must be non-empty              │
│                                                         │
│  📝 Persist: manifest, gold_inventory, planning_mode,   │
│     artifact counts (3 MVs, 5 TVFs, 1 Genie Space)     │
└─────────────────────────────────────────────────────────┘
```

The `gold_inventory` is the **anti-hallucination anchor** — every table and column name the agent uses in ALL subsequent phases must come from this dict, never invented.

```python
gold_inventory = {
    "dim_customer": {
        "columns": {"customer_key": "BIGINT", "customer_name": "STRING", ...},
        "primary_key": ["customer_key"],
        "foreign_keys": []
    },
    "fact_sales": {
        "columns": {"sales_key": "BIGINT", "customer_key": "BIGINT", ...},
        "primary_key": ["sales_key"],
        "foreign_keys": [{"columns": ["customer_key"], "references": "dim_customer"}]
    }
}
```

---

## Phase 1: Metric Views — Just-in-Time Loading

The agent reads the `01-metric-views-patterns/SKILL.md` worker skill (~505 lines), which teaches it YAML syntax, transitive join detection, format types, composability, and validation.

```
┌──────────────────────────────────────────────────────────┐
│                      PHASE 1                             │
│                                                          │
│  Working Memory:                                         │
│  ┌──────────────────────────────┐                       │
│  │ gold_inventory (from Phase 0)│ ← persists forever    │
│  │ Phase 0 notes (counts, mode) │                       │
│  │ 01-metric-views SKILL.md     │ ← READ just-in-time  │
│  │ common/expert-agent SKILL.md │                       │
│  │ common/naming-standards      │                       │
│  │ common/python-imports        │                       │
│  └──────────────────────────────┘                       │
│                                                          │
│  For each manifest metric_view:                         │
│  ┌────────────────────────────┐                         │
│  │ 1. Read manifest entry     │                         │
│  │    name: revenue_metrics   │                         │
│  │    source: fact_booking    │                         │
│  │    dimensions: [date, ...] │                         │
│  │    measures: [revenue, ...]│                         │
│  ├────────────────────────────┤                         │
│  │ 2. Cross-ref vs gold_inv  │                         │
│  │    ✅ fact_booking exists   │                         │
│  │    ✅ all columns found     │                         │
│  ├────────────────────────────┤                         │
│  │ 3. Triple validation gate  │                         │
│  │    ✅ Column existence      │                         │
│  │    ✅ No transitive joins   │                         │
│  │    ✅ Format types valid    │                         │
│  ├────────────────────────────┤                         │
│  │ 4. Generate YAML file →    │                         │
│  │    src/{proj}_semantic/    │                         │
│  │    metric_views/           │                         │
│  │    revenue_metrics.yaml    │                         │
│  ├────────────────────────────┤                         │
│  │ 5. Create creation script  │                         │
│  │    create_metric_views.py  │                         │
│  └────────────────────────────┘                         │
│                                                          │
│  📝 Persist "Metric Views Notes to Carry Forward":      │
│     - MV names: [revenue_metrics, booking_metrics]      │
│     - Paths: src/travel_semantic/metric_views/*.yaml    │
│     - Grain: revenue→fact_booking, booking→fact_booking │
│     - Measures: 8 dims, 12 measures total               │
│     - Composability: avg_order_value uses MEASURE()     │
│                                                          │
│  🗑️ DISCARD: Full 01-metric-views SKILL.md content     │
└──────────────────────────────────────────────────────────┘
```

The critical pattern: the agent writes its actual outputs as structured notes (following the "Notes to Carry Forward" template from the worker skill), then discards the full 505-line worker skill content.

---

## Phase 2: TVFs — Context Handoff in Action

```
┌──────────────────────────────────────────────────────────┐
│                      PHASE 2                             │
│                                                          │
│  Working Memory (note what changed):                     │
│  ┌──────────────────────────────┐                       │
│  │ gold_inventory               │ ← still here          │
│  │ Phase 1 MV notes (5 lines)  │ ← compact handoff     │
│  │ 02-tvf SKILL.md             │ ← NEW, read just now   │
│  │ common/expert-agent          │                       │
│  │ common/naming-standards      │                       │
│  └──────────────────────────────┘                       │
│  (01-metric-views SKILL.md is GONE — 505 lines freed)   │
│                                                          │
│  For each manifest TVF:                                 │
│  ┌─────────────────────────────────────────┐            │
│  │ 1. Read manifest entry                  │            │
│  │    name: get_bookings_by_date_range     │            │
│  │    params: [start_date STRING, ...]     │            │
│  │    gold_tables: [fact_booking_daily]     │            │
│  ├─────────────────────────────────────────┤            │
│  │ 2. Cross-ref vs gold_inventory          │            │
│  │    ✅ fact_booking_daily exists          │            │
│  │    ✅ All referenced columns found       │            │
│  ├─────────────────────────────────────────┤            │
│  │ 3. Generate TVF with:                   │            │
│  │    - ALL STRING parameters              │            │
│  │    - Null safety (COALESCE)             │            │
│  │    - SCD2 handling (is_current=true)    │            │
│  │    - v3.0 structured COMMENT            │            │
│  │    - ${catalog}.${gold_schema} vars     │            │
│  ├─────────────────────────────────────────┤            │
│  │ 4. Create create_tvfs.py (Python        │            │
│  │    notebook for notebook_task —          │            │
│  │    NOT sql_task!)                        │            │
│  └─────────────────────────────────────────┘            │
│                                                          │
│  📝 Persist "TVF Notes to Carry Forward":               │
│     - TVF names: [get_bookings_by_date_range, ...]      │
│     - Paths: src/travel_semantic/table_valued_functions  │
│     - Signatures: get_bookings(start STRING, end STRING)│
│     - Domain: travel domain, 5 TVFs                     │
│                                                          │
│  🗑️ DISCARD: Full 02-tvf SKILL.md content              │
└──────────────────────────────────────────────────────────┘
```

---

## Phase 3: Genie Spaces — The Confluence Point

This is where all prior phases converge. The agent uses **two** worker skills simultaneously and draws on notes from both Phase 1 and Phase 2:

```
┌──────────────────────────────────────────────────────────┐
│                      PHASE 3                             │
│                                                          │
│  Working Memory:                                         │
│  ┌──────────────────────────────┐                       │
│  │ gold_inventory               │ ← still here          │
│  │ Phase 1 MV notes            │ ← MV names & paths    │
│  │ Phase 2 TVF notes           │ ← TVF names & sigs    │
│  │ 03-genie-patterns SKILL.md  │ ← NEW (design)        │
│  │ 04-genie-api SKILL.md       │ ← NEW (JSON schema)   │
│  └──────────────────────────────┘                       │
│                                                          │
│  For each manifest genie_space:                         │
│  ┌────────────────────────────────────────────────┐     │
│  │ 1. Verify Gold tables have column comments     │     │
│  ├────────────────────────────────────────────────┤     │
│  │ 2. Assign assets from prior phase notes:       │     │
│  │    metric_views: [revenue_metrics] ← Phase 1   │     │
│  │    tvfs: [get_bookings_by_date] ← Phase 2      │     │
│  │    tables: [dim_customer, ...] ← gold_inventory │     │
│  ├────────────────────────────────────────────────┤     │
│  │ 3. Write General Instructions (≤20 lines)      │     │
│  │    from 03-genie-patterns 7-section template    │     │
│  ├────────────────────────────────────────────────┤     │
│  │ 4. Create ≥10 benchmark questions with SQL     │     │
│  │    ⚠️ SQL goes in answer[{format:"SQL",        │     │
│  │       content:["SELECT..."]}]                   │     │
│  │    NOT in "expected_sql" field!                  │     │
│  ├────────────────────────────────────────────────┤     │
│  │ 5. Validation gate:                            │     │
│  │    ✅ All table/column refs in gold_inventory   │     │
│  │    ✅ All TVF refs match Phase 2 outputs        │     │
│  │    ✅ All MV refs match Phase 1 outputs         │     │
│  ├────────────────────────────────────────────────┤     │
│  │ 6. Generate JSON config per 04-genie-api:      │     │
│  │    - uuid.uuid4().hex for ALL IDs              │     │
│  │    - All string fields as ["arrays"]            │     │
│  │    - sort_all_arrays() before export            │     │
│  │    - ${catalog}/${gold_schema} template vars    │     │
│  │    → src/{proj}_semantic/genie_configs/*.json   │     │
│  └────────────────────────────────────────────────┘     │
│                                                          │
│  📝 Persist "Genie Space Notes to Carry Forward":       │
│     - Space names: [travel_analytics]                   │
│     - JSON paths: src/travel_semantic/genie_configs/    │
│     - Assets: 2 MVs, 5 TVFs, 3 tables per space        │
│     - Benchmarks: 12 questions per space                │
│     - Warehouse: Serverless SQL                         │
│                                                          │
│  🗑️ DISCARD: Full 03 + 04 SKILL.md content             │
└──────────────────────────────────────────────────────────┘
```

---

## Phase 4: Asset Bundle — Wiring It All Together

```
┌──────────────────────────────────────────────────────────┐
│                      PHASE 4                             │
│                                                          │
│  Working Memory:                                         │
│  ┌──────────────────────────────┐                       │
│  │ gold_inventory               │                       │
│  │ Phase 3 Genie notes         │ ← space names, paths  │
│  │ common/asset-bundles SKILL  │ ← NEW                 │
│  └──────────────────────────────┘                       │
│                                                          │
│  Creates the deployment plumbing:                       │
│                                                          │
│  resources/semantic/semantic_layer_job.yml               │
│  ┌────────────────────────────────────────────┐         │
│  │  tasks:                                     │         │
│  │   ┌──────────────────────────┐              │         │
│  │   │ create_metric_views      │──┐           │         │
│  │   │ (notebook_task)          │  │           │         │
│  │   └──────────────────────────┘  │           │         │
│  │                    depends_on ──▼           │         │
│  │   ┌──────────────────────────┐              │         │
│  │   │ create_table_valued_fns  │──┐           │         │
│  │   │ (notebook_task)          │  │           │         │
│  │   └──────────────────────────┘  │           │         │
│  │                    depends_on ──▼           │         │
│  │   ┌──────────────────────────┐              │         │
│  │   │ deploy_genie_spaces      │              │         │
│  │   │ (notebook_task)          │              │         │
│  │   └──────────────────────────┘              │         │
│  └────────────────────────────────────────────┘         │
│                                                          │
│  Updates databricks.yml:                                 │
│  ├── sync: metric_views/**/*.yaml, genie_configs/**     │
│  ├── resources: semantic_layer_job.yml                   │
│  ├── variables.warehouse_id                             │
│  └── variables.genie_space_id_<name> (for idempotency)  │
│                                                          │
│  ⚠️ ALL 3 tasks use notebook_task, NOT sql_task         │
│     (sql_task can't substitute ${catalog} in DDL)       │
└──────────────────────────────────────────────────────────┘
```

---

## Phase 5: Deploy — Two Commands, Platform-Enforced Ordering

```
┌──────────────────────────────────────────────────────────┐
│                      PHASE 5                             │
│                                                          │
│  $ databricks bundle deploy -t dev                      │
│  $ databricks bundle run semantic_layer_job -t dev      │
│                                                          │
│  Databricks enforces the depends_on chain:              │
│                                                          │
│  ┌────────────┐     ┌────────────┐     ┌──────────┐    │
│  │ Task 1:    │────▶│ Task 2:    │────▶│ Task 3:  │    │
│  │ Metric     │     │ TVFs       │     │ Genie    │    │
│  │ Views      │     │ (notebook) │     │ Spaces   │    │
│  │ (notebook) │     │            │     │ (API)    │    │
│  └────────────┘     └────────────┘     └──────────┘    │
│       ✅                 ✅                 ✅           │
│                                                          │
│  Verification:                                           │
│  ├── SHOW VIEWS IN catalog.gold_schema                  │
│  ├── SHOW FUNCTIONS IN catalog.gold_schema              │
│  └── Check Genie UI / export_genie_space.py --list      │
│                                                          │
│  On failure → autonomous-operations:                     │
│  diagnose → fix → redeploy loop                         │
└──────────────────────────────────────────────────────────┘
```

---

## Phase 6 (Optional): Cross-Environment API Deployment

```
┌──────────────────────────────────────────────────────────┐
│                      PHASE 6                             │
│                                                          │
│  Takes the Phase 3 JSON configs and pushes them to      │
│  staging/prod via REST API:                              │
│                                                          │
│  dev (Phase 5)  ──API──▶  staging  ──API──▶  prod      │
│                                                          │
│  Uses idempotent pattern:                               │
│  ├── space_id exists? → PATCH (no title to avoid        │
│  │   " (updated)" suffix)                               │
│  └── space_id empty?  → POST (create new)               │
│                                                          │
│  Records space IDs → databricks.yml variables            │
│  for next deployment                                     │
└──────────────────────────────────────────────────────────┘
```

---

## The Complete Flow — Context Budget Over Time

Here's a timeline view of what's in the agent's working memory at each phase:

```
Time ──────────────────────────────────────────────────▶

Phase:  │   0   │    1     │    2     │     3      │  4  │ 5 │ 6 │

        ┌───────┬──────────┬──────────┬────────────┬─────┬───┬───┐
gold_   │███████│██████████│██████████│████████████│█████│███│███│
inv     │       │          │          │            │     │   │   │
        ├───────┼──────────┼──────────┼────────────┼─────┼───┼───┤
manifest│███████│          │          │            │     │   │   │
        ├───────┼──────────┼──────────┼────────────┼─────┼───┼───┤
01-MV   │       │██████████│          │            │     │   │   │
skill   │       │ (505 ln) │ discarded│            │     │   │   │
        ├───────┼──────────┼──────────┼────────────┼─────┼───┼───┤
MV      │       │          │░░░░░░░░░░│░░░░░░░░░░░░│     │   │   │
notes   │       │  created │ (5 lines)│ (consumed) │     │   │   │
        ├───────┼──────────┼──────────┼────────────┼─────┼───┼───┤
02-TVF  │       │          │██████████│            │     │   │   │
skill   │       │          │ (481 ln) │ discarded  │     │   │   │
        ├───────┼──────────┼──────────┼────────────┼─────┼───┼───┤
TVF     │       │          │          │░░░░░░░░░░░░│     │   │   │
notes   │       │          │  created │ (consumed) │     │   │   │
        ├───────┼──────────┼──────────┼────────────┼─────┼───┼───┤
03+04   │       │          │          │████████████│     │   │   │
skills  │       │          │          │(630+395 ln)│disc.│   │   │
        ├───────┼──────────┼──────────┼────────────┼─────┼───┼───┤
Genie   │       │          │          │            │░░░░░│░░░│░░░│
notes   │       │          │          │   created  │     │   │   │
        └───────┴──────────┴──────────┴────────────┴─────┴───┴───┘

 ███ = full skill loaded    ░░░ = compact notes (5-10 lines)
```

Without progressive disclosure, the agent would need ~2,000+ lines of worker skill content loaded simultaneously. With it, the maximum concurrent load peaks at Phase 3 (~1,025 lines of skill content + ~10 lines of prior phase notes), then drops sharply for deployment phases.

---

## The "Notes to Carry Forward" Chain

Each worker skill ends with a structured handoff section. These form a chain that the orchestrator relies on:

```
Phase 1: 01-metric-views-patterns
  └─ "Metric Views Notes to Carry Forward"
      - MV names and YAML file paths
      - Grain per view (which fact table)
      - Measure counts per view
      - Composability notes (any MEASURE() references)
              │
              ▼
Phase 2: 02-databricks-table-valued-functions
  └─ "TVF Notes to Carry Forward"
      - TVF names and SQL file paths
      - Parameter signatures (all STRING)
      - Domain assignments
      - Genie-relevant TVFs
              │
              ▼
Phase 3: 03-genie-space-patterns
  └─ "Genie Space Notes to Carry Forward"
      - Space names and JSON config paths
      - Asset assignments per space (MVs + TVFs + tables)
      - Benchmark question counts
      - Warehouse assignment
              │
              ▼
Phase 3: 04-genie-space-export-import-api
  └─ "Genie API Notes to Carry Forward"
      - Deployed space IDs (32-char hex)
      - Variable settings for re-deployment
      - Validation results
              │
              ▼
Phase 4-6: Deployment using accumulated notes
```

---

## Post-Completion: The Audit Trail

After all phases complete, the orchestrator requires the agent to output a **Skill Usage Summary** documenting every skill it actually read, in what phase, and why. This is not pre-written — it must reflect what the agent actually did during the session:

| # | Phase | Skill / Reference Read | Type | What It Was Used For |
|---|-------|----------------------|------|---------------------|
| 1 | Phase 0 | `planning/00-project-planning` (manifest) | Consumed | Load semantic layer manifest |
| 2 | Phase 1 | `skills/databricks-expert-agent/SKILL.md` | Common | Extract-don't-generate principle |
| 3 | Phase 1 | `semantic-layer/01-metric-views-patterns/SKILL.md` | Worker | YAML syntax, validation, joins |
| ... | ... | ... | ... | ... |

This provides full traceability of what the agent used and why.

---

## Key Design Principles at Work

| # | Principle | How It's Applied |
|---|-----------|-----------------|
| 1 | **Manifest-driven, not self-discovered** | The agent never invents artifacts. Everything comes from the plan. |
| 2 | **`gold_inventory` as single source of truth** | Every column reference across all phases is validated against this dict, preventing hallucinated table/column names. |
| 3 | **Just-in-time loading** | Each ~500-line worker skill is loaded only when needed and discarded after, keeping the attention budget focused. |
| 4 | **Structured handoffs via "Notes to Carry Forward"** | Each worker produces a ~5-10 line summary that bridges to the next phase, replacing ~500 lines of context with ~10 lines. |
| 5 | **Triple validation gates** | Phase 1 validates columns + transitive joins + format types. Phase 2 validates table/column references. Phase 3 cross-validates against ALL prior outputs. |
| 6 | **Deployment as code** | Everything converges into a single Asset Bundle job with `depends_on` chains, ensuring Databricks itself enforces execution order at deploy time. |
| 7 | **Idempotent re-deployment** | Space IDs stored as variables enable PATCH (update) instead of POST (duplicate) on subsequent deployments. |

---

## When Things Go Wrong

The orchestrator includes multiple safety nets:

- **Missing manifest** → Hard stop with user-facing message pointing to the planning skill
- **Empty gold_inventory** → Hard stop — Gold tables must be deployed first
- **Transitive joins detected** → Validation gate fails with fix suggestions (denormalize or snowflake schema)
- **Invalid format types** → Validation gate rejects `percent`, `decimal` with correct alternatives
- **Deployment failure** → `databricks-autonomous-operations` skill provides a diagnose → fix → redeploy loop
- **Duplicate Genie Spaces** → Idempotent pattern (space ID variables) prevents duplicates on re-deployment
