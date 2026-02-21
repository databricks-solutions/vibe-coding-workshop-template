# 09 — Parallel Execution Guide

## Overview

The QUICKSTART pipeline presents 9 stages as a linear sequence, but several stages have **independent inputs** and can run in parallel. This guide maps every input/output dependency and identifies which prompts can safely execute concurrently — potentially cutting total wall-clock time by 30–40%.

> **Key insight:** The pipeline has two parallelization windows — one early (Steps 1 & 2) and one late (Steps 6, 7 & 8). Everything else is strictly serial due to data or artifact dependencies.

---

## Dependency Map

Each step's inputs determine what it must wait for.

| Step | Stage | Reads From | Produces | Depends On |
|------|-------|-----------|----------|------------|
| **0** | Place Schema CSV | External customer data | `context/Wanderbricks_Schema.csv` | — |
| **1** | Gold Layer Design | Schema CSV | `gold_layer_design/yaml/`, ERDs, lineage | Step 0 |
| **2** | Bronze Layer Setup | Schema CSV | Bronze tables + data in Databricks | Step 0 |
| **3** | Silver Layer Setup | Bronze tables (CDF) | Silver DLT pipeline + DQ rules | Step 2 |
| **4** | Gold Layer Impl | Gold YAML (Step 1) + Silver tables (Step 3) | Gold tables, merges, FK constraints | Step 1 AND Step 3 |
| **4a** | Deployment Checkpoint | Bronze + Silver + Gold jobs | Validated pipeline | Step 4 |
| **5** | Project Planning | Completed Gold tables | `plans/manifests/*.yaml` (4 manifest files) | Step 4 |
| **6** | Semantic Layer | `semantic-layer-manifest.yaml` + Gold tables | TVFs, Metric Views, Genie Spaces | Step 5 |
| **6b** | Genie Optimization | Live Genie Space (Step 6) | Optimized metadata + benchmarks | Step 6 |
| **7** | Observability | `observability-manifest.yaml` + Gold tables | Monitors, dashboards, alerts | Step 5 |
| **8** | ML Pipeline | `ml-manifest.yaml` + Gold tables | MLflow experiments, models, inference | Step 5 |
| **9** | GenAI Agents | `genai-agents-manifest.yaml` + Genie Spaces | ResponsesAgent, multi-agent orchestration | Step 5 AND Step 6 |

---

## Visual Dependency Graph

```
                          ┌─────────────────┐
                          │     Step 0       │
                          │  Place Schema    │
                          │      CSV         │
                          └────────┬─────────┘
                                   │
                   ┌───────────────┴───────────────┐
                   │                               │
                   ▼                               ▼
           ┌───────────────┐               ┌───────────────┐
           │    Step 1     │               │    Step 2     │
           │  Gold Layer   │               │ Bronze Layer  │   ◄── PARALLEL
           │    Design     │               │    Setup      │       GROUP A
           └───────┬───────┘               └───────┬───────┘
                   │                               │
                   │                               ▼
                   │                       ┌───────────────┐
                   │                       │    Step 3     │
                   │                       │ Silver Layer  │   ◄── Serial
                   │                       │    Setup      │       (needs Bronze)
                   │                       └───────┬───────┘
                   │                               │
                   └───────────┬───────────────────┘
                               │
                               ▼  (convergence — needs BOTH)
                       ┌───────────────┐
                       │    Step 4     │
                       │  Gold Layer   │   ◄── Serial
                       │    Impl      │       (needs Step 1 YAML
                       └───────┬───────┘        + Step 3 Silver)
                               │
                               ▼
                       ┌───────────────┐
                       │   Step 4a     │
                       │  Deployment   │   ◄── Checkpoint
                       │  Checkpoint   │       (validate B+S+G)
                       └───────┬───────┘
                               │
                               ▼
                       ┌───────────────┐
                       │    Step 5     │
                       │   Project     │   ◄── Serial
                       │   Planning    │       (analyzes Gold)
                       └───────┬───────┘
                               │
            ┌──────────────────┼──────────────────┐
            │                  │                   │
            ▼                  ▼                   ▼
    ┌───────────────┐  ┌───────────────┐   ┌───────────────┐
    │    Step 6     │  │    Step 7     │   │    Step 8     │
    │   Semantic    │  │ Observability │   │  ML Pipeline  │   ◄── PARALLEL
    │    Layer      │  │    Setup      │   │    Setup      │       GROUP B
    └───────┬───────┘  └───────┬───────┘   └───────────────┘
            │                  │
            ▼                  ▼
    ┌───────────────┐  ┌───────────────┐
    │   Step 6b     │  │  Checkpoint   │
    │ Genie Space   │  │ Validate Obs  │
    │ Optimization  │  └───────────────┘
    └───────┬───────┘
            │
            ▼
    ┌───────────────┐
    │  Checkpoint   │
    │ Validate Sem  │
    └───────┬───────┘
            │
            ▼
    ┌───────────────┐
    │    Step 9     │
    │ GenAI Agents  │   ◄── Serial
    │    Setup      │       (needs Genie Spaces from Step 6)
    └───────────────┘
```

---

## Parallel Groups

### Parallel Group A — Steps 1 and 2 (after Step 0)

| Run Together | Input | Output |
|-------------|-------|--------|
| **Step 1** — Gold Layer Design | Schema CSV | `gold_layer_design/yaml/`, ERDs, lineage |
| **Step 2** — Bronze Layer Setup | Schema CSV | Bronze tables with data in Databricks |

**Why parallel is safe:** Both steps read only the schema CSV. Step 1 produces design artifacts (YAML files, ERDs) while Step 2 creates physical tables in Databricks. There is zero overlap in inputs or outputs.

**Time savings:** Steps 1 and 2 each take 2–3 hours. Running them in parallel saves ~2–3 hours of wall-clock time.

**How to execute:** Open two separate AI agent conversations simultaneously — one for Step 1, one for Step 2.

---

### Serial Chain — Steps 2 → 3 → 4 (convergence)

| Step | Must Wait For | Reason |
|------|--------------|--------|
| **Step 3** (Silver) | Step 2 (Bronze) | Silver DLT pipelines read from Bronze tables via Change Data Feed (CDF). Bronze tables must exist and be populated. |
| **Step 4** (Gold Impl) | Step 1 **AND** Step 3 | Gold implementation reads YAML schema files from Step 1 (`gold_layer_design/yaml/`) and MERGEs data from Silver tables created in Step 3. |

Step 4 is the **convergence point** where both parallel tracks from Group A must be complete.

---

### Serial Gate — Step 5

**Step 5** (Project Planning) must wait for Step 4. It examines the completed Gold tables to generate 4 YAML manifest files that serve as contracts for all downstream stages:

| Manifest | Consumed By |
|----------|-------------|
| `plans/manifests/semantic-layer-manifest.yaml` | Step 6 (Semantic Layer) |
| `plans/manifests/observability-manifest.yaml` | Step 7 (Observability) |
| `plans/manifests/ml-manifest.yaml` | Step 8 (ML Pipeline) |
| `plans/manifests/genai-agents-manifest.yaml` | Step 9 (GenAI Agents) |

---

### Parallel Group B — Steps 6, 7, and 8 (after Step 5)

| Run Together | Manifest Consumed | Output |
|-------------|-------------------|--------|
| **Step 6** — Semantic Layer | `semantic-layer-manifest.yaml` | TVFs, Metric Views, Genie Spaces |
| **Step 7** — Observability | `observability-manifest.yaml` | Monitors, dashboards, alerts |
| **Step 8** — ML Pipeline | `ml-manifest.yaml` | MLflow experiments, models, inference |

**Why parallel is safe:** Each step reads a **different** manifest YAML file from Step 5 and independently references Gold tables. They create non-overlapping Databricks resources (SQL functions vs monitors vs MLflow experiments).

**Time savings:** Steps 6–8 each take 3–12 hours. Running all three in parallel saves significant wall-clock time.

**How to execute:** Open three separate AI agent conversations simultaneously — one for each step.

---

### Serial Tail — Steps 6b and 9

| Step | Must Wait For | Reason |
|------|--------------|--------|
| **Step 6b** (Genie Optimization) | Step 6 | Benchmarks and tunes the live Genie Space created in Step 6. The Genie Space must be deployed and queryable. |
| **Step 9** (GenAI Agents) | Step 5 **AND** Step 6 | Multi-agent Genie orchestration routes queries across Genie Spaces. Requires both the `genai-agents-manifest.yaml` from Step 5 and the deployed Genie Spaces from Step 6. |

> **Note:** Steps 7 and 8 do NOT block Step 9. Only Step 6 does (because of Genie Space integration).

---

## Critical Path

The **critical path** (longest serial chain determining minimum wall-clock time) is:

```
Step 0 → Step 2 → Step 3 → Step 4 → Step 5 → Step 6 → Step 6b → Step 9
         (2-3h)   (2-4h)   (3-4h)   (2-4h)   (3-5h)   (2-3h)   (8-16h)
```

Step 1 runs in parallel with Steps 2+3 and is typically shorter, so it is rarely on the critical path. Steps 7 and 8 run in parallel with Step 6 and are also off the critical path.

**Estimated total time (serial):** 30–50+ hours
**Estimated total time (with parallelization):** 22–40 hours (~30–40% reduction)

---

## Practical Considerations

### Asset Bundle Contention

Steps running in parallel may all modify `databricks.yml` and files under `resources/`. To avoid conflicts:

- **Option A:** Run parallel steps in separate git branches and merge afterward.
- **Option B:** Let each step complete its file generation, then manually resolve any `databricks.yml` merge conflicts before deployment.
- **Option C:** Deploy each step's bundle independently (separate `databricks bundle deploy` runs) — the Databricks workspace handles resource isolation.

### Conversation Isolation

Each step should run in a **separate AI agent conversation** (as recommended in the QUICKSTART tips). This naturally supports parallelism — each conversation has its own context and doesn't interfere with others.

### Checkpoint Validation

Even with parallel execution, respect the three deployment checkpoints:

1. **After Step 4** — Validate Bronze + Silver + Gold together before Planning
2. **After Step 6** — Validate Semantic Layer (TVFs, Metric Views, Genie Spaces) before optimization
3. **After Step 7** — Validate Observability (monitors, dashboards, alerts)

---

## Quick Reference: Execution Order

```
PHASE 1 — Foundation (serial + parallel)
──────────────────────────────────────────
  Step 0:  Place Schema CSV
  Step 1:  Gold Layer Design      ──┐
                                    ├── PARALLEL GROUP A
  Step 2:  Bronze Layer Setup     ──┘
  Step 3:  Silver Layer Setup         (waits for Step 2)
  Step 4:  Gold Layer Impl            (waits for Steps 1 AND 3)
  Step 4a: Deployment Checkpoint      (validate Bronze + Silver + Gold)

PHASE 2 — Planning (serial gate)
──────────────────────────────────────────
  Step 5:  Project Planning           (waits for Step 4)

PHASE 3 — Capabilities (parallel)
──────────────────────────────────────────
  Step 6:  Semantic Layer Setup   ──┐
  Step 7:  Observability Setup    ──┼── PARALLEL GROUP B
  Step 8:  ML Pipeline Setup      ──┘

PHASE 4 — Optimization & Agents (serial tail)
──────────────────────────────────────────
  Step 6b: Genie Space Optimization   (waits for Step 6)
  Step 9:  GenAI Agents Setup         (waits for Steps 5 AND 6)
```

---

## References

- [QUICKSTART.md](../../QUICKSTART.md) — One-prompt-per-stage reference with exact prompts
- [03-Design-First Pipeline](03-design-first-pipeline.md) — Stage details, inputs/outputs, and durations
- [Skill Navigator](../../skills/skill-navigator/SKILL.md) — Full routing table and domain indexes
