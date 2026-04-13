---
marp: true
theme: default
paginate: true
size: 16:9
title: "Vibe Coding Workshop: Build Data Products with AI"
author: "Prashanth Subrahmanyam"
description: "An animated journey through 59 agent skills for building Databricks data products, apps, and AI agents"
transition: fade
style: |
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&family=Fira+Code:wght@400;600&display=swap');

  :root {
    --bg: #0D1B2A;
    --bg-light: #1B3A4B;
    --bg-code: #162033;
    --text: #C9D6E3;
    --heading: #FFFFFF;
    --accent: #FF3621;
    --green: #00A972;
    --blue: #3B82F6;
    --dim: #3A5068;
  }

  section {
    background: var(--bg);
    color: var(--text);
    font-family: 'Inter', system-ui, sans-serif;
    padding: 48px 64px 36px;
    line-height: 1.5;
  }
  section::after {
    color: var(--dim);
    font-size: 0.5em;
  }

  h1 { color: var(--heading); font-size: 1.75em; font-weight: 800; margin: 0 0 12px; letter-spacing: -0.02em; }
  h2 { color: var(--accent); font-size: 1.25em; font-weight: 700; margin: 0 0 8px; }
  h3 { color: var(--green); font-size: 1.0em; font-weight: 600; margin: 0 0 6px; }
  h4 { color: var(--blue); font-size: 0.9em; font-weight: 600; }
  strong { color: var(--heading); }
  a { color: var(--blue); text-decoration: none; }
  li { margin: 2px 0; }
  ul, ol { margin: 4px 0; }

  /* Title slide */
  section.title {
    background: linear-gradient(135deg, #1B3A4B 0%, #0D1B2A 60%, #0A1628 100%);
    display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center;
  }
  section.title h1 { font-size: 2.4em; margin-bottom: 16px; }
  section.title h2 { color: var(--text); font-weight: 400; font-size: 1.15em; }
  section.title p { color: var(--dim); font-size: 0.85em; }

  /* Section divider */
  section.divider {
    background: linear-gradient(135deg, var(--accent) 0%, #C42A19 100%);
    color: #fff; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center;
  }
  section.divider h1 { font-size: 2.6em; color: #fff; }
  section.divider p { color: rgba(255,255,255,0.85); font-size: 1.1em; max-width: 600px; }

  /* Training module slides */
  section.training {
    background: linear-gradient(180deg, #0F1D32 0%, #0D1B2A 100%);
    border-top: 3px solid var(--blue);
  }

  /* Pipeline progress bar */
  .pl { display: flex; gap: 3px; align-items: center; justify-content: center; margin: 0 0 18px; padding: 8px 12px; background: rgba(0,0,0,0.35); border-radius: 10px; }
  .pl .s { width: 26px; height: 26px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 0.5em; font-weight: 700; background: var(--bg-light); color: #5A7A8A; transition: all 0.3s; }
  .pl .s.done { background: var(--green); color: #fff; }
  .pl .s.now { background: var(--accent); color: #fff; box-shadow: 0 0 12px rgba(255,54,33,0.4); transform: scale(1.15); }
  .pl .c { color: #2A4050; font-size: 0.5em; }

  /* AppKit phase bar */
  .phases { display: flex; gap: 4px; align-items: center; justify-content: center; margin: 0 0 18px; padding: 8px 12px; background: rgba(0,0,0,0.35); border-radius: 10px; }
  .phases .p { padding: 5px 12px; border-radius: 6px; font-size: 0.48em; font-weight: 600; background: var(--bg-light); color: #5A7A8A; }
  .phases .p.done { background: var(--green); color: #fff; }
  .phases .p.now { background: var(--accent); color: #fff; box-shadow: 0 0 10px rgba(255,54,33,0.3); }

  /* Tree displays */
  .tree { background: var(--bg-code); border-radius: 8px; padding: 14px 18px; font-family: 'Fira Code', monospace; font-size: 0.58em; line-height: 1.55; white-space: pre; overflow: hidden; }
  .hl { color: var(--accent); font-weight: 600; }
  .hl2 { color: var(--green); font-weight: 600; }
  .hl3 { color: var(--blue); font-weight: 600; }
  .dim { color: #2A3E4E; }

  /* Two-column layout */
  .cols { display: flex; gap: 24px; align-items: flex-start; }
  .cols > div, .cols > pre { flex: 1; min-width: 0; }

  /* Architecture boxes */
  .box { background: var(--bg-light); border: 1px solid #2D5A6C; border-radius: 8px; padding: 10px 14px; margin: 4px 2px; text-align: center; font-size: 0.7em; }
  .box.accent { border-color: var(--accent); background: rgba(255,54,33,0.1); }
  .box.green { border-color: var(--green); background: rgba(0,169,114,0.08); }
  .box.blue { border-color: var(--blue); background: rgba(59,130,246,0.08); }

  /* Flow layouts */
  .flow { display: flex; align-items: center; gap: 6px; justify-content: center; flex-wrap: wrap; margin: 8px 0; }
  .flow .arr { color: var(--accent); font-size: 1.1em; font-weight: 700; }
  .flow .node { background: var(--bg-light); border: 1px solid #2D5A6C; border-radius: 6px; padding: 6px 12px; font-size: 0.65em; font-weight: 600; }
  .flow .node.active { border-color: var(--accent); color: var(--accent); }

  /* Tag badges */
  .tag { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.55em; font-weight: 700; vertical-align: middle; }
  .tag.o { background: var(--accent); color: #fff; }
  .tag.g { background: var(--green); color: #fff; }
  .tag.b { background: var(--blue); color: #fff; }

  /* Code blocks */
  pre { background: var(--bg-code) !important; border-radius: 8px; font-size: 0.62em; }
  code { font-family: 'Fira Code', monospace; }
  pre code { line-height: 1.5; }

  /* Tables */
  table { font-size: 0.68em; width: 100%; }
  th { background: var(--bg-light) !important; color: var(--heading) !important; font-weight: 600; }
  td { background: var(--bg) !important; border-color: var(--bg-light) !important; }

  /* Mermaid */
  .mermaid { background: transparent !important; text-align: center; margin: 8px 0; }
  .mermaid svg { max-height: 360px; }

  /* Utility */
  .small { font-size: 0.85em; }
  .center { text-align: center; }
  .mt { margin-top: 16px; }
  .fn { font-size: 0.48em; color: var(--dim); margin-top: auto; }
---

<script type="module">
import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
mermaid.initialize({ startOnLoad: true, theme: 'dark', themeVariables: {
  primaryColor: '#FF3621', primaryTextColor: '#E0E7EE', primaryBorderColor: '#FF3621',
  lineColor: '#4A6A7F', secondaryColor: '#1B3A4B', tertiaryColor: '#0D1B2A',
  background: '#0D1B2A', mainBkg: '#1B3A4B', nodeBorder: '#2D5A6C',
  clusterBkg: '#0F1D32', clusterBorder: '#2D5A6C', titleColor: '#FFFFFF',
  edgeLabelBackground: '#0D1B2A', nodeTextColor: '#E0E7EE'
}});
</script>

<!-- _class: title -->
<!-- _paginate: skip -->
<!-- _transition: cover -->

# Vibe Coding Workshop

## Build Data Products with AI-Assisted Development

**59 Agent Skills** &nbsp;|&nbsp; **9 Pipeline Stages** &nbsp;|&nbsp; **5 App Phases**

Powered by Databricks + AI Coding Assistants

<!--
Speaker: Welcome everyone to the Vibe Coding Workshop. Over the next session, we'll take
an animated journey through the entire framework — from raw schema CSVs to production data
products, Databricks Apps, and AI agents. Everything is driven by agent skills that encode
best practices into reusable, AI-readable instructions.
Timing: ~2 min for introductions and orientation.
-->

---

<!-- _paginate: skip -->

# Agenda

<div class="cols">
<div>

### Act I — Welcome & Context
Vibe coding, repo structure, skill anatomy

### Act II — Data Product Accelerator
Animated journey through 9 stages, 59 skills

### Act III — Platform Training
Databricks Apps, AppKit, Lakebase, SDP, Genie

</div>
<div>

### Act IV — AppKit Workshop Journey
5-phase hands-on lifecycle with skills

### Act V — Putting It All Together
Live demo prompts, resources, Q&A

</div>
</div>

<div class="fn">~70 slides | Export: HTML (transitions) | PDF (handout) | PPTX (shareable)</div>

<!--
Speaker: Here's the roadmap. We start with concepts, then dive into the 9-stage data pipeline
animated as a journey through skill trees. Next, platform training on the building blocks.
Then hands-on with AppKit. Finally, you'll get copy-paste prompts to try it yourself.
Timing: ~1 min
-->

---

<!-- _transition: cover -->

# What is Vibe Coding?

> **AI-assisted development** where you collaborate with AI tools to rapidly build, iterate, and deploy production-quality data products.

<div class="cols">
<div>

### You Describe
- Business requirements (PRD)
- Schema CSVs, data sources
- "Build a Gold layer for this schema"

</div>
<div>

### AI Implements
- Reads agent skills for best practices
- Generates production-grade code
- Follows enterprise patterns automatically

</div>
</div>

**The secret sauce:** Agent Skills — structured `SKILL.md` files that encode best practices and patterns the AI reads before writing any code.

<!--
Speaker: Vibe coding flips the ratio — you spend more time describing WHAT you want and less
time writing HOW. The AI handles implementation, guided by 59 agent skills that encode
Databricks best practices. You're the architect; the AI is the builder.
Timing: ~2 min
-->

---

# Repository Overview

This is a **monorepo** with three components:

<div class="mermaid">
graph LR
    Root["vibe-coding-workshop-template/"] --> A["apps_lakebase/"]
    Root --> B["data_product_accelerator/"]
    Root --> C["agentic-framework/"]
    A --> A1["6 Skills<br/>AppKit + Lakebase"]
    B --> B1["59 Skills<br/>9-Stage Pipeline"]
    C --> C1["Agent Prompts<br/>Multi-Agent Framework"]
    Root --> D["Generated Artifacts"]
    D --> D1["gold_layer_design/"]
    D --> D2["src/"]
    D --> D3["plans/ & resources/"]
</div>

**Key rule:** Framework directories are **read-only inputs**. Generated code goes to **repo root**.

<!--
Speaker: Three components live here. The Data Product Accelerator has 59 skills for the full
medallion architecture. AppKit has 6 skills for building Databricks Apps. The Agentic Framework
is for multi-agent systems. All generated code goes to the repo root — never inside the framework dirs.
Timing: ~2 min
-->

---

# Two Pathways

<div class="flow">
<div class="node">Start Here</div>
<div class="arr">→</div>
<div class="node active" style="border-color: var(--green); color: var(--green);">Path A: Build an App</div>
<div class="arr" style="color: var(--dim);">&nbsp;or&nbsp;</div>
<div class="node active">Path B: Build a Data Pipeline</div>
</div>

<div class="cols">
<div>

### Path A — Databricks App <span class="tag g">apps_lakebase/</span>
1. Scaffold AppKit project
2. Build UI from PRD (mock data)
3. Deploy to Databricks Apps
4. Wire Lakebase backend
5. Deploy + E2E test

**6 skills, 5 phases**

</div>
<div>

### Path B — Data Pipeline <span class="tag o">data_product_accelerator/</span>
1. Gold Design from schema CSV
2. Bronze tables + test data
3. Silver DLT pipelines
4. Gold implementation
5. Semantic → Observability → ML → GenAI

**59 skills, 9 stages**

</div>
</div>

**Both paths work together** — build the pipeline first, then deploy an app on top, or vice versa.

<!--
Speaker: Two entry points, same destination. Path A is for the "I want an app" crowd — build
a full-stack Databricks App in 5 phases. Path B is for the data engineers — design-first
pipeline through the full medallion architecture. They converge: your app can query your pipeline's Gold tables.
Timing: ~2 min
-->

---

# What is a SKILL.md?

A **structured instruction file** that any AI coding assistant can read and follow.

<div class="cols">
<div>

```yaml
---
name: gold-layer-design
metadata:
  role: orchestrator
  pipeline_stage: 1
  workers:
    - design-workers/01-grain-definition
    - design-workers/02-dimension-patterns
  common_dependencies:
    - databricks-expert-agent
    - naming-tagging-standards
---
# Gold Layer Design Orchestrator
## When to Use This Skill
- Designing a Gold layer from scratch
- Creating dimensional models
```

</div>
<div>

### Anatomy

- **YAML front matter** — metadata, dependencies, pipeline stage
- **When to Use** — routing keywords
- **Mandatory Dependencies** — skills to read first
- **Step-by-step instructions** — the actual guide
- **`references/`** — detailed patterns (loaded on demand)
- **`scripts/`** — validation utilities
- **`assets/`** — templates and starters

Works with **Cursor, Claude Code, Windsurf, Copilot, Codex** — any agent that reads files.

</div>
</div>

<!--
Speaker: Every skill follows the same structure. YAML front matter has machine-readable metadata
for routing. The body has human-readable instructions. References directories hold the heavy
content, loaded only when needed. This keeps each SKILL.md under 2K tokens — lightweight for
the AI's context window.
Timing: ~2 min
-->

---

# Progressive Disclosure: Tiered Loading

The framework uses **4 tiers** to stay within the AI's context budget:

<div class="flow">
<div class="box" style="min-width:140px;"><strong>Tier 1</strong><br/>Core Skills<br/><span style="color:var(--green)">~4K tokens</span><br/>Always loaded</div>
<div class="arr">→</div>
<div class="box" style="min-width:140px;"><strong>Tier 2</strong><br/>Domain Index<br/><span style="color:var(--green)">~2K/domain</span><br/>On keyword detect</div>
<div class="arr">→</div>
<div class="box" style="min-width:140px;"><strong>Tier 3</strong><br/>SKILL.md<br/><span style="color:var(--green)">~1-2K each</span><br/>On specific task</div>
<div class="arr">→</div>
<div class="box" style="min-width:140px;"><strong>Tier 4</strong><br/>references/<br/><span style="color:var(--green)">~2-8K each</span><br/>On demand only</div>
</div>

| Zone | Token Budget | Strategy |
|------|-------------|----------|
| **Green** (0-20K) | Load freely | Multiple SKILL.md files + 2-3 references |
| **Yellow** (20-50K) | Be selective | SKILL.md files are fine, pick references carefully |
| **Red** (50K+) | Minimize | Reference paths only, run scripts as black boxes |

<!--
Speaker: Why tiers? Claude Opus has a 200K token window, but performance drops if you overload
it. We keep the operating budget at 40-60K tokens. Tier 1 is always loaded. Each subsequent tier
loads only what's needed for the current task. This is how 59 skills fit without blowing the context.
Timing: ~2 min
-->

---

# Orchestrator vs Worker Pattern

<div class="cols">
<div>

### Orchestrator <span class="tag o">00-*</span>
- Manages the **end-to-end workflow** for a stage
- Calls worker skills via mandatory Read pattern
- Defines phases, dependencies, deliverables
- **Entry point** for "build X from scratch"

### Worker <span class="tag g">01-*, 02-*, ...</span>
- Handles a **specific pattern** within a stage
- Can be used standalone or called by orchestrator
- Focused, reusable, composable

</div>
<div>

<div class="tree">
gold/
├── <span class="hl">00-gold-layer-design/</span>    ← ORCHESTRATOR
│   ├── SKILL.md
│   └── references/
├── <span class="hl2">design-workers/</span>
│   ├── 01-grain-definition/
│   ├── 02-dimension-patterns/
│   ├── 03-fact-table-patterns/
│   ├── 04-conformed-dimensions/
│   ├── 05-erd-diagrams/
│   ├── 06-table-documentation/
│   └── 07-design-validation/
└── <span class="hl2">pipeline-workers/</span>
    ├── 01-yaml-table-setup/
    ├── 02-merge-patterns/
    ├── 03-deduplication/
    ├── 04-grain-validation/
    └── 05-schema-validation/
</div>

</div>
</div>

<!--
Speaker: The orchestrator/worker pattern is the backbone of the framework. Orchestrators are
your "00-" numbered entry points — they manage the full workflow for a pipeline stage.
Workers are the specialists — they handle one specific pattern. The Gold domain is unique:
it has two sub-groups of workers (design-time vs implementation-time).
Timing: ~2 min
-->

---

# How the AI Agent Navigates

<div class="mermaid">
graph TD
    A["AGENTS.md<br/>(entry point)"] -->|keyword match| B["skill-navigator/<br/>SKILL.md"]
    B -->|"'Gold design'"| C["gold/00-gold-layer-design<br/>ORCHESTRATOR"]
    B -->|"'Bronze setup'"| D["bronze/00-bronze-layer-setup<br/>ORCHESTRATOR"]
    B -->|"'DLT expectations'"| E["silver/01-dlt-expectations<br/>WORKER (standalone)"]
    C -->|Phase 2| F["design-workers/01-grain-definition"]
    C -->|Phase 2| G["design-workers/02-dimension-patterns"]
    C -->|Phase 3| H["design-workers/05-erd-diagrams"]
    C -->|All phases| I["common/databricks-expert-agent"]
</div>

**Routing algorithm:** Match keywords → prefer orchestrator → orchestrator calls workers per phase → common skills loaded as dependencies.

<!--
Speaker: This is the navigation flow. The AI reads AGENTS.md at the repo root, which routes
to the skill-navigator. The navigator matches keywords to the right orchestrator or worker.
Orchestrators then progressively load workers phase by phase. Common skills like naming-standards
and expert-agent are loaded as cross-cutting dependencies.
Timing: ~2 min
-->

---

<!-- _class: divider -->
<!-- _paginate: skip -->
<!-- _transition: cover -->

# Act II

The Data Product Accelerator

9 stages — 59 skills — one animated journey

<!--
Speaker: Now let's walk through the entire Data Product Accelerator pipeline. I'll show you
each of the 9 stages as a journey through the skill tree, progressively revealing how the
orchestrators and workers connect. Watch the pipeline bar at the top — it tracks our position.
Timing: ~30 sec transition
-->

---

# The 9-Stage Design-First Pipeline

<div class="mermaid">
graph LR
    CSV["Schema CSV"] --> S1["1. Gold<br/>Design"]
    S1 --> S2["2. Bronze"]
    S2 --> S3["3. Silver"]
    S3 --> S4["4. Gold<br/>Impl"]
    S4 --> S5["5. Planning"]
    S5 --> S6["6. Semantic<br/>Layer"]
    S6 --> S6b["6b. Genie<br/>Opt"]
    S6b --> S7["7. Observ-<br/>ability"]
    S7 --> S8["8. ML"]
    S8 --> S9["9. GenAI<br/>Agents"]
</div>

**Design-First means:** Design the Gold model (target) first, then build the layers that feed it.

| Input | Output |
|-------|--------|
| `data_product_accelerator/context/*.csv` | `gold_layer_design/`, `src/`, `plans/`, `resources/`, `databricks.yml` |

<!--
Speaker: This is the full pipeline. It starts with a customer schema CSV and ends with GenAI
agents in production. The key insight is "design-first" — you design the Gold dimensional model
BEFORE building Bronze and Silver. This prevents rework. Let's walk through each stage.
Timing: ~2 min
-->

---

<div class="pl"><div class="s now">1</div><div class="c">›</div><div class="s">2</div><div class="c">›</div><div class="s">3</div><div class="c">›</div><div class="s">4</div><div class="c">›</div><div class="s">5</div><div class="c">›</div><div class="s">6</div><div class="c">›</div><div class="s">7</div><div class="c">›</div><div class="s">8</div><div class="c">›</div><div class="s">9</div></div>

# Stage 1: Gold Layer Design

**Orchestrator:** `gold/00-gold-layer-design` &nbsp; <span class="tag o">ENTRY POINT</span>

<div class="cols">
<div>

### What It Does
- Reads schema CSV from `context/`
- Applies dimensional modeling methodology
- Generates ERDs, YAML schemas, documentation

### Key Deliverables
- `gold_layer_design/yaml/*.yaml` — table definitions
- `gold_layer_design/erd_master.md` — ERD diagrams
- `gold_layer_design/docs/BUSINESS_ONBOARDING_GUIDE.md`
- `gold_layer_design/COLUMN_LINEAGE.csv`

</div>
<div>

### Non-Negotiable Defaults
Every Gold YAML schema **must** include:

```yaml
clustering: auto
table_properties:
  delta.enableChangeDataFeed: "true"
  delta.enableRowTracking: "true"
  delta.autoOptimize.optimizeWrite: "true"
  delta.autoOptimize.autoCompact: "true"
  layer: "gold"
```

</div>
</div>

<!--
Speaker: Stage 1 is where everything begins. You feed in a schema CSV and the orchestrator
drives dimensional modeling — grains, dimensions, facts, conformed dimensions, ERDs, and
documentation. The YAML schemas it produces become the contract that drives ALL downstream stages.
Notice the non-negotiable defaults — every table gets auto liquid clustering, change data feed, etc.
Timing: ~3 min
-->

---

<div class="pl"><div class="s now">1</div><div class="c">›</div><div class="s">2</div><div class="c">›</div><div class="s">3</div><div class="c">›</div><div class="s">4</div><div class="c">›</div><div class="s">5</div><div class="c">›</div><div class="s">6</div><div class="c">›</div><div class="s">7</div><div class="c">›</div><div class="s">8</div><div class="c">›</div><div class="s">9</div></div>

# Stage 1: Gold Design — Worker Tree

The orchestrator calls **7 design workers** across its phases:

<div class="tree">
<span class="hl">gold/00-gold-layer-design</span>  ← ORCHESTRATOR (reads schema CSV)
│
├── Phase 2: Dimensional Modeling
│   ├── <span class="hl2">design-workers/01-grain-definition</span>      grain types, decision tree
│   ├── <span class="hl2">design-workers/02-dimension-patterns</span>    role-playing, junk, degenerate, SCD
│   ├── <span class="hl2">design-workers/03-fact-table-patterns</span>   measure additivity, factless, snapshots
│   └── <span class="hl2">design-workers/04-conformed-dimensions</span>  bus matrix, drill-across queries
│
├── Phase 3: ERD Creation
│   └── <span class="hl2">design-workers/05-erd-diagrams</span>          master/domain/summary based on table count
│
├── Phase 4: Documentation
│   └── <span class="hl2">design-workers/06-table-documentation</span>   business onboarding guide, lineage CSV
│
└── Phase 8: Validation
    └── <span class="hl2">design-workers/07-design-validation</span>     YAML ↔ ERD ↔ Lineage cross-check
</div>

<!--
Speaker: Here's the worker tree for Gold Design. Each worker is loaded by the orchestrator at
the right phase. Grain definition comes first — it determines the granularity of each fact table.
Then dimension and fact patterns. ERDs get created, then documentation, and finally validation
cross-checks everything. The orchestrator manages the sequence.
Timing: ~2 min
-->

---

<div class="pl"><div class="s done">1</div><div class="c">›</div><div class="s now">2</div><div class="c">›</div><div class="s">3</div><div class="c">›</div><div class="s">4</div><div class="c">›</div><div class="s">5</div><div class="c">›</div><div class="s">6</div><div class="c">›</div><div class="s">7</div><div class="c">›</div><div class="s">8</div><div class="c">›</div><div class="s">9</div></div>

# Stage 2: Bronze Layer

**Orchestrator:** `bronze/00-bronze-layer-setup` &nbsp; <span class="tag o">ORCHESTRATOR</span>

<div class="cols">
<div>

### Philosophy
Bronze is optimized for **testing, demos, and rapid prototyping** — not production ingestion.

### What It Creates
- Table DDLs with `CLUSTER BY AUTO`
- Faker-generated realistic test data
- Asset Bundle job YAML (Serverless)

### Worker
- `bronze/01-faker-data-generation` — synthetic data with configurable corruption rates

</div>
<div>

### Non-Negotiable Defaults

```sql
CREATE TABLE IF NOT EXISTS {catalog}.{schema}.{table}
(...)
USING DELTA
CLUSTER BY AUTO
TBLPROPERTIES (
  'delta.enableChangeDataFeed' = 'true',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true',
  'layer' = 'bronze'
)
```

Every job uses **Serverless** + **Environments V4** + `notebook_task` with `base_parameters`.

</div>
</div>

<!--
Speaker: Bronze is our test data factory. The orchestrator reads the same schema CSV and creates
DDLs that match the source system. The Faker worker generates realistic synthetic data with
configurable corruption rates for testing data quality rules downstream. Everything runs Serverless.
Timing: ~2 min
-->

---

<div class="pl"><div class="s done">1</div><div class="c">›</div><div class="s done">2</div><div class="c">›</div><div class="s now">3</div><div class="c">›</div><div class="s">4</div><div class="c">›</div><div class="s">5</div><div class="c">›</div><div class="s">6</div><div class="c">›</div><div class="s">7</div><div class="c">›</div><div class="s">8</div><div class="c">›</div><div class="s">9</div></div>

# Stage 3: Silver Layer

**Orchestrator:** `silver/00-silver-layer-setup` &nbsp; <span class="tag o">ORCHESTRATOR</span>

<div class="cols">
<div>

### What It Creates
1. **`dq_rules` Delta table** — centralized rules in Unity Catalog
2. **`dq_rules_loader.py`** — pure Python module to load rules
3. **Silver SDP/DLT notebooks** — with expectations from Delta table
4. **Pipeline YAML** — Serverless, ADVANCED edition, Photon
5. **DQ monitoring views** — per-table metrics

### Workers
- `01-dlt-expectations-patterns` — `@dlt.expect_all_or_drop()`
- `02-dqx-patterns` — advanced DQX framework

</div>
<div>

### Key Pattern: Delta Table DQ Rules

```python
# Rules stored in Delta table, not hardcoded
rules = load_rules("silver_bookings", "critical")

@dlt.table(
    table_properties={
        "delta.enableRowTracking": "true"
    },
    cluster_by_auto=True
)
@dlt.expect_all_or_drop(rules)
def silver_bookings():
    return read_stream("bronze_bookings")
```

**Benefits:** Runtime-updateable, auditable via time travel, severity-based filtering.

</div>
</div>

<!--
Speaker: Silver is where data quality lives. The key pattern is storing DQ rules in a Delta table
rather than hardcoding them. This means you can update rules with a simple SQL UPDATE — no
redeployment needed. The orchestrator creates the rules table, the loader module, and the
DLT/SDP pipeline that applies them.
Timing: ~3 min
-->

---

<div class="pl"><div class="s done">1</div><div class="c">›</div><div class="s done">2</div><div class="c">›</div><div class="s done">3</div><div class="c">›</div><div class="s now">4</div><div class="c">›</div><div class="s">5</div><div class="c">›</div><div class="s">6</div><div class="c">›</div><div class="s">7</div><div class="c">›</div><div class="s">8</div><div class="c">›</div><div class="s">9</div></div>

# Stage 4: Gold Implementation

**Orchestrator:** `gold/01-gold-layer-setup` &nbsp; <span class="tag o">ORCHESTRATOR</span>

Takes the YAML schemas from Stage 1 and **builds the actual tables, merge scripts, and constraints**.

<div class="tree">
<span class="hl">gold/01-gold-layer-setup</span>  ← ORCHESTRATOR (reads YAML schemas)
│
├── <span class="hl2">pipeline-workers/01-yaml-table-setup</span>     YAML-driven CREATE TABLE DDLs
├── <span class="hl2">pipeline-workers/02-merge-patterns</span>       MERGE INTO with SCD Type 2
├── <span class="hl2">pipeline-workers/03-deduplication</span>        ROW_NUMBER dedup strategies
├── <span class="hl2">pipeline-workers/04-grain-validation</span>     Verify fact table grain integrity
└── <span class="hl2">pipeline-workers/05-schema-validation</span>    Cross-check DDL vs YAML schema
</div>

### Design → Implementation Handoff
Stage 1 produces **YAML schemas** (the contract). Stage 4 consumes them to generate DDL, merge notebooks, and validation scripts. The YAML is the single source of truth.

<!--
Speaker: Stage 4 is the implementation counterpart to Stage 1's design. It reads the YAML schemas
and materializes them as actual Delta tables with proper MERGE scripts, deduplication logic, and
validation. Notice this is the same gold/ directory but different workers — pipeline-workers vs
design-workers. The YAML contract ensures design and implementation stay in sync.
Timing: ~2 min
-->

---

<div class="pl"><div class="s done">1</div><div class="c">›</div><div class="s done">2</div><div class="c">›</div><div class="s done">3</div><div class="c">›</div><div class="s done">4</div><div class="c">›</div><div class="s now">5</div><div class="c">›</div><div class="s">6</div><div class="c">›</div><div class="s">7</div><div class="c">›</div><div class="s">8</div><div class="c">›</div><div class="s">9</div></div>

# Stage 5: Planning

**Orchestrator:** `planning/00-project-planning` &nbsp; <span class="tag o">ORCHESTRATOR</span>

The planning stage generates **YAML manifest files** — contracts that downstream stages consume.

<div class="mermaid">
graph LR
    Gold["Gold YAML<br/>Schemas"] --> Plan["Planning<br/>Orchestrator"]
    Plan --> M1["semantic-layer-<br/>manifest.yaml"]
    Plan --> M2["observability-<br/>manifest.yaml"]
    Plan --> M3["ml-<br/>manifest.yaml"]
    Plan --> M4["genai-agents-<br/>manifest.yaml"]
    M1 --> S6["Stage 6:<br/>Semantic"]
    M2 --> S7["Stage 7:<br/>Observability"]
    M3 --> S8["Stage 8:<br/>ML"]
    M4 --> S9["Stage 9:<br/>GenAI"]
</div>

**Plan-as-Contract:** Each manifest specifies what tables, metrics, monitors, and agents to build. Downstream orchestrators read their manifest in Phase 0 before generating code.

<!--
Speaker: Planning is the coordination layer. It reads the Gold schemas and produces 4 YAML
manifests — one for each downstream stage. These manifests are contracts: they specify exactly
what metric views, monitors, ML models, and agents to build. If a manifest is missing (user
skipped planning), orchestrators fall back to self-discovery from Gold tables.
Timing: ~2 min
-->

---

<div class="pl"><div class="s done">1</div><div class="c">›</div><div class="s done">2</div><div class="c">›</div><div class="s done">3</div><div class="c">›</div><div class="s done">4</div><div class="c">›</div><div class="s done">5</div><div class="c">›</div><div class="s now">6</div><div class="c">›</div><div class="s">7</div><div class="c">›</div><div class="s">8</div><div class="c">›</div><div class="s">9</div></div>

# Stage 6: Semantic Layer

**Orchestrator:** `semantic-layer/00-semantic-layer-setup` &nbsp; <span class="tag o">ORCHESTRATOR</span>

<div class="cols">
<div>

### What It Creates
1. **Metric Views** — YAML semantic definitions
2. **Table-Valued Functions (TVFs)** — parameterized SQL for Genie
3. **Genie Spaces** — NL analytics with instructions + benchmarks

### Workers (4)
- `01-metric-views-patterns`
- `02-databricks-table-valued-functions`
- `03-genie-space-patterns`
- `04-genie-space-export-import-api`

</div>
<div>

### Data Asset Priority for Genie

```
Priority 1: Metric Views
  → Pre-defined business metrics
  → Genie uses these FIRST

Priority 2: TVFs
  → Parameterized queries
  → Genie passes parameters

Priority 3: Raw Tables
  → Full flexibility
  → Genie writes custom SQL
```

**Core principle:** Business context drives AI quality. The richer your Metric Views and agent instructions, the better Genie answers.

</div>
</div>

<!--
Speaker: The semantic layer sits on top of Gold tables and makes them accessible to business
users via natural language. Metric Views are the highest priority — they pre-define business
metrics so Genie doesn't have to figure them out. TVFs handle parameterized patterns. Raw
tables are the fallback. The quality of Genie responses directly correlates with the depth
of context you provide.
Timing: ~3 min
-->

---

<div class="pl"><div class="s done">1</div><div class="c">›</div><div class="s done">2</div><div class="c">›</div><div class="s done">3</div><div class="c">›</div><div class="s done">4</div><div class="c">›</div><div class="s done">5</div><div class="c">›</div><div class="s done">6</div><div class="c">›</div><div class="s now" style="font-size:0.4em">6b</div><div class="c">›</div><div class="s">7</div><div class="c">›</div><div class="s">8</div><div class="c">›</div><div class="s">9</div></div>

# Stage 6b: Genie Optimization

**Standalone Orchestrator:** `semantic-layer/05-genie-optimization-orchestrator`

An **autonomous optimization loop** with 4 specialized workers:

<div class="tree">
<span class="hl">05-genie-optimization-orchestrator</span>  ← STANDALONE ORCHESTRATOR
│
├── <span class="hl2">genie-optimization-workers/01-genie-benchmark-generator</span>
│   Generate benchmark question sets with expected SQL
│
├── <span class="hl2">genie-optimization-workers/02-genie-benchmark-evaluator</span>
│   Run benchmarks, score accuracy & repeatability
│
├── <span class="hl2">genie-optimization-workers/03-genie-metadata-optimizer</span>
│   Optimize table/column comments, agent instructions
│
└── <span class="hl2">genie-optimization-workers/04-genie-optimization-applier</span>
    Apply optimizations via Genie API, re-benchmark
</div>

**Loop:** Generate benchmarks → Evaluate → Optimize metadata → Apply → Re-evaluate → Repeat until target accuracy.

<!--
Speaker: Stage 6b is unique — it's a standalone orchestrator with its own optimization loop.
It generates benchmark questions, evaluates Genie's accuracy, optimizes the metadata (comments,
instructions), applies changes via the API, and re-benchmarks. It's like a training loop for
your Genie Space.
Timing: ~2 min
-->

---

<div class="pl"><div class="s done">1</div><div class="c">›</div><div class="s done">2</div><div class="c">›</div><div class="s done">3</div><div class="c">›</div><div class="s done">4</div><div class="c">›</div><div class="s done">5</div><div class="c">›</div><div class="s done">6</div><div class="c">›</div><div class="s now">7</div><div class="c">›</div><div class="s">8</div><div class="c">›</div><div class="s">9</div></div>

# Stage 7: Observability

**Orchestrator:** `monitoring/00-observability-setup` &nbsp; <span class="tag o">ORCHESTRATOR</span>

<div class="cols">
<div>

### Workers (4)

| Worker | What It Does |
|--------|-------------|
| `01-lakehouse-monitoring` | Table monitors, row counts, schema drift |
| `02-aibi-dashboards` | Lakeview dashboards for data health |
| `03-sql-alerting` | SQL-based alerts with notifications |
| `04-anomaly-detection` | Freshness, completeness, stale table detection |

</div>
<div>

### What It Creates
- Lakehouse Monitors on Gold tables
- AI/BI Lakeview dashboards
- SQL alerts with email/Slack notifications
- Anomaly detection for freshness & completeness
- Asset Bundle job YAML for scheduled monitoring

**Auto-triggered:** Anomaly detection can fire automatically after Silver/Gold setup completes.

</div>
</div>

<!--
Speaker: Observability ensures your data products stay healthy in production. Four workers cover
different aspects — monitoring tables, building dashboards, setting up alerts, and detecting
anomalies. The anomaly detection worker is special — it can auto-trigger after Silver or Gold
setup, adding freshness and completeness checks proactively.
Timing: ~2 min
-->

---

<div class="pl"><div class="s done">1</div><div class="c">›</div><div class="s done">2</div><div class="c">›</div><div class="s done">3</div><div class="c">›</div><div class="s done">4</div><div class="c">›</div><div class="s done">5</div><div class="c">›</div><div class="s done">6</div><div class="c">›</div><div class="s done">7</div><div class="c">›</div><div class="s now">8</div><div class="c">›</div><div class="s">9</div></div>

# Stage 8: ML Pipelines

**Orchestrator:** `ml/00-ml-pipeline-setup` &nbsp; <span class="tag o">ORCHESTRATOR</span>

<div class="cols">
<div>

### What It Creates
- MLflow experiments and tracking
- Feature engineering notebooks
- Model training with hyperparameter tuning
- Model registry integration
- Batch inference pipelines
- Asset Bundle job YAML

</div>
<div>

### Key Patterns
- **MLflow Tracking** — all experiments logged
- **Unity Catalog Models** — registered in UC for governance
- **Feature Tables** — reusable feature engineering
- **Serverless Jobs** — training and inference
- **A/B Testing** — model comparison framework

Gold tables are the feature source. ML models feed back into the data product ecosystem.

</div>
</div>

<!--
Speaker: ML pipelines consume Gold tables as feature sources. The orchestrator sets up the full
MLflow workflow — experiments, training, model registry, and inference. Everything is governed
through Unity Catalog. Models registered here can be served as endpoints for GenAI agents in Stage 9.
Timing: ~1.5 min
-->

---

<div class="pl"><div class="s done">1</div><div class="c">›</div><div class="s done">2</div><div class="c">›</div><div class="s done">3</div><div class="c">›</div><div class="s done">4</div><div class="c">›</div><div class="s done">5</div><div class="c">›</div><div class="s done">6</div><div class="c">›</div><div class="s done">7</div><div class="c">›</div><div class="s done">8</div><div class="c">›</div><div class="s now">9</div></div>

# Stage 9: GenAI Agents

**Orchestrator:** `genai-agents/00-genai-agents-setup` &nbsp; <span class="tag o">ORCHESTRATOR</span>

The **largest domain** — 8 specialized workers:

<div class="tree">
<span class="hl">genai-agents/00-genai-agents-setup</span>  ← ORCHESTRATOR
│
├── <span class="hl2">01-responses-agent-patterns</span>       ResponsesAgent, predict_stream
├── <span class="hl2">02-mlflow-genai-evaluation</span>        LLM judge scorers, evaluation harness
├── <span class="hl2">03-lakebase-memory-patterns</span>       CheckpointSaver, stateful conversations
├── <span class="hl2">04-prompt-registry-patterns</span>       Versioned prompts in Unity Catalog
├── <span class="hl2">05-multi-agent-genie-orchestration</span> Intent classification, Genie routing
├── <span class="hl2">06-deployment-automation</span>           CI/CD for agent deployment
├── <span class="hl2">07-production-monitoring</span>           Registered scorers, drift detection
└── <span class="hl2">08-mlflow-genai-foundation</span>         MLflow tracing, GenAI basics
</div>

From ResponsesAgent to multi-agent orchestration with Genie, memory, prompt versioning, evaluation, and production monitoring.

<!--
Speaker: The GenAI domain is the most expansive — 8 workers covering the full agent lifecycle.
You start with the ResponsesAgent pattern, add memory via Lakebase, version prompts through
Unity Catalog, orchestrate multiple agents with Genie integration, evaluate with LLM judges,
deploy with CI/CD, and monitor in production. This is the capstone of the pipeline.
Timing: ~2 min
-->

---

# Cross-Cutting: 8 Common Skills

These shared skills apply across **all 9 stages**:

| Skill | What It Provides | Used By |
|-------|-----------------|---------|
| **databricks-expert-agent** | Core SA behavior, "Extract Don't Generate" principle | All stages |
| **naming-tagging-standards** | `snake_case`, COMMENTs, PII tags, budget policies | All DDL |
| **databricks-asset-bundles** | Job/pipeline YAML, Serverless config, Environments V4 | Stages 2-9 |
| **databricks-autonomous-operations** | Deploy → Poll → Diagnose → Fix → Redeploy loop | Any deployment |
| **databricks-python-imports** | Pure Python modules, `sys.path` patterns | Silver, Gold, ML |
| **databricks-table-properties** | TBLPROPERTIES: CDF, Row Tracking, Auto-Optimize | Bronze-Gold |
| **schema-management-patterns** | `CREATE SCHEMA IF NOT EXISTS` with governance | Bronze-Gold |
| **unity-catalog-constraints** | PRIMARY KEY, FOREIGN KEY syntax, surrogate keys | Silver-Gold |

**Minimum read:** Always load `databricks-expert-agent` + `naming-tagging-standards`.

<!--
Speaker: These 8 common skills are the shared foundation. They're not tied to any single stage —
orchestrators pull them in as dependencies. The two you should always have loaded are
expert-agent (core behavior) and naming-tagging-standards (enterprise naming). Asset-bundles
is critical for any deployment. Autonomous-operations handles the "deploy, wait, diagnose, fix,
redeploy" loop automatically.
Timing: ~2 min
-->

---

# The Complete Skill Tree — 59 Skills

<div class="cols">
<div class="tree" style="font-size:0.48em; line-height:1.35;">
skills/
├── <span class="hl3">skill-navigator/</span>            navigator
├── <span class="dim">admin/ (4 utility skills)</span>
│
├── <span class="hl">gold/</span>
│   ├── 00-gold-layer-design     <span class="tag o">S1</span>
│   ├── 01-gold-layer-setup      <span class="tag o">S4</span>
│   ├── design-workers/ (7)      <span class="tag g">S1</span>
│   └── pipeline-workers/ (5)    <span class="tag g">S4</span>
│
├── <span class="hl">bronze/</span>
│   ├── 00-bronze-layer-setup    <span class="tag o">S2</span>
│   └── 01-faker-data-generation <span class="tag g">S2</span>
│
├── <span class="hl">silver/</span>
│   ├── 00-silver-layer-setup    <span class="tag o">S3</span>
│   ├── 01-dlt-expectations      <span class="tag g">S3</span>
│   └── 02-dqx-patterns          <span class="tag g">S3</span>
│
├── <span class="hl">planning/</span>
│   └── 00-project-planning      <span class="tag o">S5</span>
</div>
<div class="tree" style="font-size:0.48em; line-height:1.35;">
│
├── <span class="hl">semantic-layer/</span>
│   ├── 00-semantic-layer-setup  <span class="tag o">S6</span>
│   ├── workers (4)              <span class="tag g">S6</span>
│   ├── 05-genie-optimization    <span class="tag o">S6b</span>
│   └── genie-opt-workers/ (4)   <span class="tag g">S6b</span>
│
├── <span class="hl">monitoring/</span>
│   ├── 00-observability-setup   <span class="tag o">S7</span>
│   └── workers (4)              <span class="tag g">S7</span>
│
├── <span class="hl">ml/</span>
│   └── 00-ml-pipeline-setup     <span class="tag o">S8</span>
│
├── <span class="hl">genai-agents/</span>
│   ├── 00-genai-agents-setup    <span class="tag o">S9</span>
│   └── workers (8)              <span class="tag g">S9</span>
│
├── <span class="hl3">common/ (8 shared skills)</span>
└── <span class="dim">exploration/ (1 utility)</span>
</div>
</div>

<span class="tag o">Orchestrator</span> <span class="tag g">Worker</span> <span class="tag b">Meta/Common</span>

<!--
Speaker: Here's the entire tree — 59 skills organized by domain. Orange badges are orchestrators
(entry points), green are workers (specific patterns). The skill-navigator routes to the right
one based on keywords. Common skills (8) are shared dependencies. This tree IS the framework.
Timing: ~2 min
-->

---

# Routing Algorithm

How the skill-navigator matches your request to the right skill:

```
1. User request received
2. Detect domain keywords (see routing table)
3. IF keyword matches an ORCHESTRATOR skill
   → Route to orchestrator
   → Orchestrator calls workers via mandatory Read pattern
4. IF keyword matches a WORKER skill AND no orchestrator context
   → Route to worker directly (standalone mode)
5. IF keyword matches a WORKER skill AND orchestrator is active
   → Let orchestrator handle it (don't load worker separately)
6. IF ambiguous or multi-step
   → Ask user to clarify, or follow lifecycle order
```

**Example:** "Create Silver DLT pipeline with expectations"
→ Matches "Silver" + "DLT" → Routes to `silver/00-silver-layer-setup` (orchestrator)
→ Orchestrator loads `01-dlt-expectations-patterns` at the right phase

<!--
Speaker: The routing algorithm is simple but effective. Keywords drive everything. The key rule:
prefer orchestrators for end-to-end work, workers for specific standalone tasks. The orchestrator
manages when to load each worker — you never need to manually sequence them.
Timing: ~1.5 min
-->

---

<!-- _class: divider -->
<!-- _paginate: skip -->
<!-- _transition: cover -->

# Act III

Platform Training

The building blocks: Databricks Apps, AppKit, Lakebase, SDP, Genie, Unity Catalog

<!--
Speaker: Before we dive into the hands-on workshop, let's make sure everyone understands the
platform components we'll be building on. Six mini-modules, each 2-3 slides, covering the key
concepts and architecture patterns.
Timing: ~30 sec transition
-->

---

<!-- _class: training -->

# Module 1: Databricks Apps

### What is Databricks Apps?

**Managed hosting** for full-stack web applications that run inside the Databricks platform.

<div class="cols">
<div>

### Key Properties
- **Node.js runtime** — your app runs in a container
- **Service Principal identity** — app gets its own SP for API access
- **OBO (On-Behalf-Of)** — user identity flows via `x-forwarded-access-token`
- **Ephemeral filesystem** — no persistent local storage
- **`app.yaml`** — declares env vars, resources, command

</div>
<div>

### Platform Constraints

| Constraint | Value |
|-----------|-------|
| Startup timeout | 10 minutes |
| HTTP proxy timeout | 120 seconds |
| Max apps per workspace | 100 |
| Max file size in bundle | 10 MB |
| Persistent storage | None (use Lakebase or UC Volumes) |

</div>
</div>

<!--
Speaker: Databricks Apps is a managed hosting service. Your app gets a container with Node.js,
a Service Principal for API calls, and auto-injected environment variables. The key constraint
is the ephemeral filesystem — anything your app writes locally is lost on restart. That's why
we use Lakebase for persistence and UC Volumes for files.
Timing: ~2 min
-->

---

<!-- _class: training -->

# Databricks Apps Architecture

<div class="mermaid">
graph LR
    User["User Browser"] -->|"HTTPS + OBO token"| Proxy["Databricks<br/>Proxy"]
    Proxy -->|"x-forwarded-access-token"| App["App Container<br/>(Node.js)"]
    App -->|"SQL queries"| WH["SQL Warehouse"]
    App -->|"CRUD + OAuth"| LB["Lakebase<br/>(PostgreSQL)"]
    App -->|"File ops"| UC["UC Volumes"]
    App -->|"NL queries"| GE["Genie Space"]
    App -->|"LLM calls"| FM["Foundation<br/>Models"]
</div>

### Runtime Environment Variables (auto-injected)

| Variable | Description |
|----------|-------------|
| `DATABRICKS_HOST` | Workspace URL |
| `DATABRICKS_APP_PORT` | Port to bind (default: 8000) |
| `DATABRICKS_APP_NAME` | App name in Databricks |

The app's Service Principal handles auth to downstream services. User identity (OBO) flows through the proxy for per-user access control.

<!--
Speaker: The architecture is straightforward. Users hit the Databricks proxy, which forwards
requests to your app container. The proxy attaches the user's access token so your app can
make OBO calls. Your app connects to backend services — SQL Warehouse for analytics, Lakebase
for CRUD, UC Volumes for files, Genie for NL queries, and Foundation Models for LLM calls.
Timing: ~2 min
-->

---

<!-- _class: training -->

# Module 2: AppKit — TypeScript SDK

### What is AppKit?

A **TypeScript full-stack framework** with a plugin architecture for building Databricks Apps.

<div class="cols">
<div>

### Two Packages

**`@databricks/appkit`** — Backend
- Express server with plugin system
- SQL query execution with caching
- Type generation from SQL files
- Telemetry and health checks

**`@databricks/appkit-ui`** — Frontend
- React hooks (`useAnalyticsQuery`, `useGenieChat`)
- Shadcn/Radix UI primitives
- ECharts data visualization
- File browser components

</div>
<div>

### The Data Flow

```
client/src/App.tsx
  → useAnalyticsQuery("key", params)
    → POST /api/analytics/query/key
      → server/server.ts
        → config/queries/key.sql
          → SQL Warehouse
            → JSON response
              → React renders
```

All type-safe end-to-end via `npm run typegen`.

</div>
</div>

<!--
Speaker: AppKit gives you a TypeScript backend and a React frontend in one package. The backend
handles SQL query execution with caching and retries. The frontend provides type-safe hooks
that call those queries. The typegen step bridges them — it reads your SQL files and generates
TypeScript types automatically.
Timing: ~2 min
-->

---

<!-- _class: training -->

# AppKit Project Structure

After scaffolding with `databricks apps init`:

<div class="cols">
<div class="tree" style="font-size:0.55em;">
my-app/
├── <span class="hl">server/</span>
│   ├── server.ts       <span class="dim">← backend entry point</span>
│   └── .env            <span class="dim">← local dev env vars</span>
├── <span class="hl2">client/</span>
│   ├── index.html
│   ├── vite.config.ts
│   └── src/
│       ├── main.tsx
│       ├── App.tsx     <span class="dim">← main React component</span>
│       └── appKitTypes.d.ts <span class="dim">← auto-generated</span>
├── <span class="hl3">config/queries/</span>
│   └── *.sql           <span class="dim">← SQL files = query keys</span>
├── tests/smoke.spec.ts
├── <span class="hl">app.yaml</span>            <span class="dim">← Databricks Apps config</span>
├── package.json
└── databricks.yml      <span class="dim">← bundle config</span>
</div>
<div>

### Key Patterns

**Plugin registration** in `server/server.ts`:
```typescript
import { createApp, server, analytics,
         lakebase } from "@databricks/appkit";

await createApp({
  plugins: [
    server(),      // Express server
    analytics(),   // SQL Warehouse queries
    lakebase(),    // PostgreSQL CRUD
  ],
});
```

**Custom routes** via `server.extend()`:
```typescript
const appkit = await createApp({
  plugins: [server({ autoStart: false })],
});
appkit.server.extend((app) => {
  app.get("/api/health", (_, res) =>
    res.json({ status: "ok" }));
});
await appkit.server.start();
```

</div>
</div>

<!--
Speaker: This is the canonical project layout. Server code in server/, React in client/, SQL
queries in config/queries/. The filename of each .sql file becomes the query key. Plugin
registration happens in server.ts — you compose plugins freely. For custom API routes beyond
what plugins provide, use server.extend().
Timing: ~2 min
-->

---

<!-- _class: training -->

# AppKit Dev Loop

The development workflow — in order, every time:

<div class="flow">
<div class="node">1. Write SQL</div>
<div class="arr">→</div>
<div class="node">2. npm run typegen</div>
<div class="arr">→</div>
<div class="node">3. Check types</div>
<div class="arr">→</div>
<div class="node">4. Build UI</div>
<div class="arr">→</div>
<div class="node">5. npm run dev</div>
<div class="arr">→</div>
<div class="node">6. Deploy</div>
</div>

<div class="cols">
<div>

### SQL Query File Convention

```sql
-- config/queries/spend_summary.sql
-- @param startDate DATE
-- @param endDate DATE
SELECT department, SUM(amount) as total
FROM catalog.schema.expenses
WHERE expense_date BETWEEN :startDate AND :endDate
GROUP BY department
```

- `.sql` → runs as **Service Principal** (shared cache)
- `.obo.sql` → runs as **user** (per-user cache)

</div>
<div>

### Frontend Hook Usage

```tsx
import { useAnalyticsQuery }
  from "@databricks/appkit-ui/react";
import { sql }
  from "@databricks/appkit-ui/js";

function SpendTable() {
  const params = useMemo(() => ({
    startDate: sql.date("2025-01-01"),
    endDate: sql.date("2025-12-31"),
  }), []);

  const { data, loading, error } =
    useAnalyticsQuery("spend_summary", params);
  // ...
}
```

**Always** wrap params in `useMemo` to prevent refetch loops.

</div>
</div>

<!--
Speaker: The dev loop is strict — SQL first, typegen second, UI third. Never write UI code before
running typegen or your types won't exist. The SQL file convention is powerful — the filename
becomes the API endpoint, and .obo.sql runs as the user for per-user access control. On the
frontend, always memoize your params to avoid infinite refetch loops.
Timing: ~2 min
-->

---

<!-- _class: training -->

# Module 3: Lakebase — Managed PostgreSQL

### What is Lakebase?

**Autoscaling managed PostgreSQL** on Databricks with OAuth-based authentication.

<div class="cols">
<div>

### Key Features
- **OAuth token rotation** — 1-hour tokens, auto-refreshed with 2-minute buffer
- **Scale-to-zero** — `suspend_timeout_duration` stops idle compute
- **Projects / Branches / Endpoints** — Git-like database management
- **No passwords** — all auth via Databricks OAuth

### When to Use

| Use Case | Service |
|----------|---------|
| CRUD / transactional / write-heavy | **Lakebase** |
| Read-only analytics / aggregations | **SQL Warehouse** (Analytics plugin) |

</div>
<div>

### Configuration in AppKit

```typescript
// server/server.ts
import { createApp, server, lakebase }
  from "@databricks/appkit";

await createApp({
  plugins: [server(), lakebase()],
});
```

```env
# .env (local dev)
LAKEBASE_ENDPOINT=projects/<id>/branches/production/endpoints/primary
PGHOST=<endpoint-hostname>
PGPORT=5432
PGDATABASE=databricks_postgres
PGSSLMODE=require
```

The `lakebase()` plugin gives you `AppKit.lakebase.query` — a standard `pg.Pool` with automatic OAuth refresh.

</div>
</div>

<!--
Speaker: Lakebase is managed Postgres — but with OAuth instead of passwords. The plugin handles
token rotation automatically (tokens expire every hour, refreshed 2 minutes early). The key
architectural decision: use Lakebase for CRUD operations (writes, user data, app state) and
SQL Warehouse for read-only analytics (dashboards, aggregations). They complement each other.
Timing: ~2 min
-->

---

<!-- _class: training -->

# Lakebase Database Design

Principles for designing schemas in AppKit + Lakebase applications:

<div class="cols">
<div>

### Design Process
1. Read the PRD → identify **entities** (nouns = tables)
2. Define **columns** (atomic: separate first/last name)
3. Choose **PKs** (`bigint generated always as identity`)
4. Establish **relationships** (FK for 1:N, junction for M:N)
5. **Normalize** (1NF → 2NF → 3NF)
6. Create **seed data**, test queries, refine

### PostgreSQL Type Conventions

| Use Case | Type |
|----------|------|
| Auto-increment ID | `bigint generated always as identity` |
| Text fields | `text` (not `varchar(n)`) |
| Money / prices | `numeric(10,2)` (not `float`) |
| Timestamps | `timestamptz` (not `timestamp`) |
| Booleans | `boolean default false` |

</div>
<div>

### Anti-Patterns to Avoid

- `serial` → use `bigint generated always as identity`
- `varchar(255)` → use `text` (same performance)
- `float` for money → use `numeric(10,2)` (exact)
- `timestamp` → use `timestamptz` (timezone-aware)
- Comma-separated lists → use junction tables
- `phone1`, `phone2`, `phone3` → use child table

### Schema Isolation

```sql
-- All DDL uses DB_SCHEMA from env var
CREATE SCHEMA IF NOT EXISTS ${DB_SCHEMA};
CREATE TABLE IF NOT EXISTS
  ${DB_SCHEMA}.bookings (...);
```

Prevents collisions when multiple apps share a Lakebase database.

</div>
</div>

<!--
Speaker: Database design follows standard relational principles, but with Postgres-specific
conventions. Key callouts: use bigint identity (not serial), text (not varchar), numeric for
money (not float), and timestamptz (always timezone-aware). Schema isolation via DB_SCHEMA
prevents apps from stepping on each other's tables.
Timing: ~2 min
-->

---

<!-- _class: training -->

# Module 4: Spark Declarative Pipelines (SDP/DLT)

### What is SDP?

**Declarative ETL pipelines** — formerly Delta Live Tables (DLT). Define WHAT your pipeline produces; the engine handles HOW.

<div class="cols">
<div>

### Two APIs

**Modern API** (new projects):
```python
from pyspark import pipelines as dp

@dp.table()
def silver_bookings():
    return spark.readStream("bronze_bookings")
```

**Legacy API** (still needed for expectations):
```python
import dlt

@dlt.table()
@dlt.expect_all_or_drop(rules)
def silver_bookings():
    return dlt.read_stream("bronze_bookings")
```

Expectations (`@dlt.expect_all_or_drop`) are not yet in the `dp` API.

</div>
<div>

### Pipeline Non-Negotiables

| Setting | Value | Why |
|---------|-------|-----|
| Serverless | `true` | No cluster management |
| Edition | `ADVANCED` | Required for expectations |
| Photon | `true` | Performance |
| Liquid Clustering | `AUTO` | Auto-optimized layout |
| Row Tracking | `true` | Downstream MV refresh |

### Streaming Ingestion

SDP pipelines read from Bronze via `readStream`, applying DQ rules inline. Failed records can be quarantined to a separate table for analysis.

</div>
</div>

<!--
Speaker: SDP (formerly DLT) lets you define pipelines declaratively. The engine manages execution,
retries, and dependencies. There are two Python APIs — the modern dp API and the legacy dlt API.
We still need the legacy API for data quality expectations. Everything runs Serverless with
ADVANCED edition for full feature access.
Timing: ~2 min
-->

---

<!-- _class: training -->

# SDP/DLT: Delta Table DQ Rules

The key pattern: **DQ rules in a Delta table, not hardcoded**.

<div class="cols">
<div>

### Traditional (Fragile)

```python
# Rules hardcoded in notebook
@dlt.expect_or_drop(
    "valid_amount",
    "amount > 0"
)
@dlt.expect(
    "valid_status",
    "status IN ('active','cancelled')"
)
def silver_orders():
    ...
```

Changing rules = code change + redeploy.

</div>
<div>

### Delta Table (Portable)

```sql
-- dq_rules Delta table
INSERT INTO dq_rules VALUES
('silver_orders', 'valid_amount',
 'amount > 0', 'critical'),
('silver_orders', 'valid_status',
 'status IN (...)', 'warning');
```

```python
# Loader reads rules at runtime
rules = load_rules("silver_orders", "critical")

@dlt.table(cluster_by_auto=True)
@dlt.expect_all_or_drop(rules)
def silver_orders():
    return dlt.read_stream("bronze_orders")
```

Changing rules = `UPDATE` the table. No redeploy.

</div>
</div>

**Benefits:** Auditable (Delta time travel), shareable across pipelines, severity-filtered.

<!--
Speaker: This is the single most impactful pattern in the Silver layer. By storing DQ rules in
a Delta table, you decouple rule management from code deployment. Data stewards can update rules
with SQL. The pipeline picks them up on the next run. Critical rules drop bad records; warning
rules log them but pass through. Delta time travel gives you a full audit history.
Timing: ~2 min
-->

---

<!-- _class: training -->

# Module 5: Genie Spaces

### What is Genie?

**AI/BI natural language query interface** — ask questions in English, get SQL answers from your data.

<div class="cols">
<div>

### Three Components

**1. Agent Instructions** (business context)
- ≤20 lines of General Instructions
- Domain terminology, business rules
- "Revenue means SUM(amount) WHERE status='completed'"

**2. Data Assets** (what Genie can query)
- Priority: Metric Views > TVFs > Tables
- Table/column COMMENTs drive SQL quality

**3. Benchmark Questions** (validation)
- Questions with expected SQL
- Used to test accuracy before launch

</div>
<div>

### Core Principle

> **Business context drives AI quality.**
> The richer your instructions and metadata, the better Genie answers.

### Quality Levers

| Lever | Impact |
|-------|--------|
| Agent Instructions | Highest — teaches business rules |
| Table/Column COMMENTs | High — Genie reads them for SQL generation |
| Metric Views | High — pre-computed metrics Genie uses first |
| TVFs | Medium — parameterized patterns |
| Benchmark Questions | Validation — catches regressions |

</div>
</div>

<!--
Speaker: Genie translates natural language to SQL. The quality of its output depends entirely
on the context you provide. Agent instructions are the highest-impact lever — they teach Genie
your business rules. Table and column COMMENTs are next — Genie reads them when generating SQL.
Metric Views pre-define common aggregations so Genie doesn't have to figure them out.
Timing: ~2 min
-->

---

<!-- _class: training -->

# Genie in AppKit

Embed Genie directly in your Databricks App:

<div class="cols">
<div>

### Plugin Setup

```typescript
// server/server.ts
import { createApp, server, genie }
  from "@databricks/appkit";

await createApp({
  plugins: [
    server(),
    genie({
      spaces: {
        sales: "01ABCDEF12345678",
        support: "01GHIJKL87654321",
      },
    }),
  ],
});
```

Multiple spaces via named aliases.

</div>
<div>

### React Component

```tsx
import { GenieChat }
  from "@databricks/appkit-ui/react";

function GeniePage() {
  return (
    <div style={{ height: 600 }}>
      <GenieChat alias="sales" />
    </div>
  );
}
```

Full-featured chat UI with:
- SSE streaming responses
- Conversation history & replay
- Query result attachments
- Auto-reconnection

Custom chat via `useGenieChat` hook for full control.

</div>
</div>

<!--
Speaker: The Genie plugin makes it trivial to embed natural language analytics in your app. You
configure named space aliases in the server, then drop the GenieChat component in your React UI.
It handles streaming, history, and reconnection automatically. For custom UIs, the useGenieChat
hook gives you lower-level control over messages and status.
Timing: ~2 min
-->

---

<!-- _class: training -->

# Module 6: Unity Catalog & Volumes

<div class="cols">
<div>

### Unity Catalog — Governance Layer

The backbone of data governance across all stages:

- **Catalogs → Schemas → Tables** — 3-level namespace
- **Constraints** — PRIMARY KEY, FOREIGN KEY (informational)
- **Tags** — PII classification, cost center, layer tags
- **COMMENTs** — on tables and columns (Genie reads these!)
- **Volumes** — managed file storage

### Table Properties (every table)

```sql
TBLPROPERTIES (
  'delta.enableChangeDataFeed' = 'true',
  'delta.enableRowTracking' = 'true',
  'delta.autoOptimize.optimizeWrite' = 'true',
  'delta.autoOptimize.autoCompact' = 'true',
  'layer' = 'gold'  -- or 'silver', 'bronze'
)
```

</div>
<div>

### Files Plugin — UC Volumes in AppKit

```typescript
import { createApp, server, files }
  from "@databricks/appkit";

await createApp({
  plugins: [
    server(),
    files({
      maxUploadSize: 5_000_000_000,
    }),
  ],
});
```

```env
# Auto-discovered from env vars
DATABRICKS_VOLUME_UPLOADS=/Volumes/catalog/schema/uploads
DATABRICKS_VOLUME_EXPORTS=/Volumes/catalog/schema/exports
```

**React components:** `DirectoryList`, `FileBreadcrumb`, `FilePreviewPanel`

</div>
</div>

<!--
Speaker: Unity Catalog is the governance layer that ties everything together. Every table, schema,
and volume is governed through UC. The key table properties — Change Data Feed, Row Tracking,
Auto-Optimize — are non-negotiable in this framework. The Files plugin connects AppKit to UC
Volumes for file upload/download, with env-based auto-discovery of volume paths.
Timing: ~2 min
-->

---

<!-- _class: divider -->
<!-- _paginate: skip -->
<!-- _transition: cover -->

# Act IV

AppKit + Lakebase Workshop

5 phases — from scaffold to production with live data

<!--
Speaker: Now for the hands-on part. We'll walk through the complete AppKit + Lakebase workshop
lifecycle — scaffolding a project, building a UI from a PRD, deploying with mock data, wiring
a Lakebase backend, and finally deploying with live data and running E2E tests.
Timing: ~30 sec transition
-->

---

# The 5-Phase Lifecycle

<div class="phases">
<div class="p now">1 Scaffold + Build</div>
<div class="p">2 Deploy Mock</div>
<div class="p">3 Setup Lakebase</div>
<div class="p">4 Wire Backend</div>
<div class="p">5 Deploy + E2E</div>
</div>

<div class="mermaid">
graph LR
    S["Scaffold<br/>(blank app)"] --> B["Build UI<br/>(mock data)"]
    B --> D1["Deploy<br/>(mock)"]
    D1 --> LB["Setup<br/>Lakebase"]
    LB --> W["Wire<br/>Backend"]
    W --> D2["Deploy +<br/>E2E Test"]
    style S fill:#1B3A4B,stroke:#FF3621
    style B fill:#1B3A4B,stroke:#FF3621
    style D1 fill:#1B3A4B,stroke:#2D5A6C
    style LB fill:#1B3A4B,stroke:#2D5A6C
    style W fill:#1B3A4B,stroke:#2D5A6C
    style D2 fill:#1B3A4B,stroke:#2D5A6C
</div>

**Phases 1-2:** Functional UI with mock data (no database needed)
**Phases 3-5:** Add Lakebase backend with live data

| Phase | Skills Used |
|-------|-----------|
| 1 | `01-appkit-scaffold` + `02-appkit-build` |
| 2 | `03-appkit-deploy` |
| 3 | `databricks-lakebase` agent skill |
| 4 | `04-appkit-plugin-add` + `05-appkit-lakebase-wiring` |
| 5 | `03-appkit-deploy` (again) |

<!--
Speaker: Five phases, each building on the last. The first two give you a deployed app with mock
data — no database needed. Phases 3-5 add the Lakebase backend. This split is intentional:
you validate the UI first, then wire the data layer. Each phase maps to specific skills.
Timing: ~2 min
-->

---

<div class="phases">
<div class="p now">1 Scaffold + Build</div>
<div class="p">2 Deploy Mock</div>
<div class="p">3 Setup Lakebase</div>
<div class="p">4 Wire Backend</div>
<div class="p">5 Deploy + E2E</div>
</div>

# Phase 1: Scaffold

**Skill:** `01-appkit-scaffold`

<div class="cols">
<div>

### Steps
1. Authenticate: `databricks auth login --host <URL>`
2. Derive app name from username + use case
3. Scaffold: `databricks apps init --template default`
4. Install dependencies: `npm install`
5. Verify: `npm run dev` → `http://localhost:8000`

### Key Commands

```bash
# Scaffold a blank app
databricks apps init \
  --template default \
  --profile $PROFILE

cd $APP_NAME && npm install
npm run dev
```

</div>
<div>

### What You Get

```
$APP_NAME/
├── server/server.ts    ← server()
├── client/src/App.tsx  ← your UI
├── config/queries/     ← SQL files
├── app.yaml
├── databricks.yml
└── package.json
```

### Workshop Note

Scaffold a **blank** app (no plugins). Plugins are added later in Phase 4.

`TABLE_OR_VIEW_NOT_FOUND` errors from typegen are expected — no SQL queries yet.

</div>
</div>

<!--
Speaker: Phase 1 starts with authentication and scaffolding. The CLI generates the full project
structure. We scaffold blank — no plugins yet — because we want to build the UI with mock data
first. The typegen errors are normal at this point since we haven't added any SQL files.
Timing: ~2 min
-->

---

<div class="phases">
<div class="p now">1 Scaffold + Build</div>
<div class="p">2 Deploy Mock</div>
<div class="p">3 Setup Lakebase</div>
<div class="p">4 Wire Backend</div>
<div class="p">5 Deploy + E2E</div>
</div>

# Phase 1: Build from PRD

**Skill:** `02-appkit-build`

<div class="cols">
<div>

### Process
1. **Read the PRD** — personas, journeys, data needs
2. **Design the UI** — screens, components, navigation
3. **Build with mock data** — static arrays in components
4. **Apply design quality** — distinctive, not generic

### Mock Data Pattern

```tsx
const MOCK_BOOKINGS = [
  { id: 1, guest: "Alice Chen",
    property: "Lakeside Villa",
    status: "confirmed", amount: 450 },
  { id: 2, guest: "Bob Park",
    property: "Mountain Retreat",
    status: "pending", amount: 320 },
];

function BookingList() {
  return MOCK_BOOKINGS.map(b =>
    <BookingCard key={b.id} booking={b} />);
}
```

</div>
<div>

### Design Quality Principles

**Before coding, ask:**
- What is the emotional tone?
- What makes this app feel *distinctive*?
- What is the single most important action?

**Avoid "AI slop":**
- Generic Inter font + purple gradients
- Card grids with identical spacing
- Stock dashboard layouts

**Use:** Shadcn/Radix primitives + custom CSS variables in `client/src/index.css` + intentional color choices.

AppKit includes **ECharts** for data viz and **DataTable** for tabular data.

</div>
</div>

<!--
Speaker: Building from a PRD is where the app takes shape. The key insight: use mock data arrays
first. This lets you validate the entire UI flow without a database. Design quality matters —
the skill references the Anthropic frontend-design patterns to avoid generic-looking AI output.
Make it distinctive.
Timing: ~2 min
-->

---

<div class="phases">
<div class="p done">1 Scaffold + Build</div>
<div class="p now">2 Deploy Mock</div>
<div class="p">3 Setup Lakebase</div>
<div class="p">4 Wire Backend</div>
<div class="p">5 Deploy + E2E</div>
</div>

# Phase 2: Deploy with Mock Data

**Skill:** `03-appkit-deploy`

<div class="cols">
<div>

### Deploy Sequence

```bash
# Build the app
npm run build

# Validate configuration
databricks apps validate --profile $PROFILE

# Deploy to Databricks Apps
databricks apps deploy --profile $PROFILE
```

### Verify

```bash
# Check app status
databricks apps get $APP_NAME \
  --profile $PROFILE

# Stream logs
databricks apps logs $APP_NAME \
  --follow --profile $PROFILE
```

</div>
<div>

### Common Issues & Fixes

| Error | Fix |
|-------|-----|
| Build fails | `npm run build` locally first |
| App won't start (timeout) | Check `app.yaml` command, review logs |
| 403 on workspace | Verify profile with `databricks current-user me` |
| Max apps reached | Delete unused: `databricks apps delete <name>` |

### Key Rule

> **Do NOT improvise workarounds.** Match errors against the Common Errors table in the skill. Don't add `preinstall`/`postinstall` hooks or platform-detection conditionals.

</div>
</div>

<!--
Speaker: First deploy! Build locally, validate, deploy. The validate step catches config issues
before they hit the platform. If the deploy fails, stream logs and match against known errors.
The most important rule: don't improvise workarounds. The skill has a comprehensive error table —
use it. Improvised fixes (like adding npm lifecycle hooks) consistently cause cascading failures.
Timing: ~2 min
-->

---

<div class="phases">
<div class="p done">1 Scaffold + Build</div>
<div class="p done">2 Deploy Mock</div>
<div class="p now">3 Setup Lakebase</div>
<div class="p">4 Wire Backend</div>
<div class="p">5 Deploy + E2E</div>
</div>

# Phase 3: Setup Lakebase Project

Uses the **`databricks-lakebase`** agent skill (not an AppKit skill — a Databricks platform skill).

<div class="cols">
<div>

### Steps
1. Create a Lakebase project via CLI
2. Create a production branch
3. Create a read-write endpoint
4. Configure compute (min/max CUs)
5. Note the endpoint hostname

### Key Commands

```bash
# Create project
databricks lakebase projects create \
  --project-id my-app-db \
  --pg-version 17

# Get endpoint details
databricks lakebase endpoints list \
  --project-id my-app-db \
  --branch-id production
```

</div>
<div>

### Project / Branch / Endpoint Model

```
Project (my-app-db)
├── Branch: production
│   └── Endpoint: primary (read-write)
│       ├── Host: <hostname>
│       ├── Port: 5432
│       └── Database: databricks_postgres
└── Branch: dev (optional)
    └── Endpoint: dev-rw
```

### Compute Sizing

| Setting | Value |
|---------|-------|
| Min CU | 0.5 (scale-to-zero) |
| Max CU | 2.0 (workshop) |
| Suspend timeout | 300s |

</div>
</div>

<!--
Speaker: Phase 3 creates the Lakebase project. The CLI gives you a managed Postgres instance with
a project/branch/endpoint hierarchy (similar to git). For the workshop, we use a single production
branch with one read-write endpoint. Scale-to-zero keeps costs minimal when idle.
Timing: ~2 min
-->

---

<div class="phases">
<div class="p done">1 Scaffold + Build</div>
<div class="p done">2 Deploy Mock</div>
<div class="p done">3 Setup Lakebase</div>
<div class="p now">4 Wire Backend</div>
<div class="p">5 Deploy + E2E</div>
</div>

# Phase 4: Add Lakebase Plugin

**Skill:** `04-appkit-plugin-add`

### Register the plugin in `server/server.ts`:

```typescript
import { createApp, server, lakebase } from "@databricks/appkit";

await createApp({
  plugins: [server(), lakebase()],
});
```

### Configure environment variables:

<div class="cols">
<div>

**`.env` (local dev):**
```env
LAKEBASE_ENDPOINT=projects/<id>/branches/production/endpoints/primary
PGHOST=<endpoint-hostname>
PGPORT=5432
PGDATABASE=databricks_postgres
PGSSLMODE=require
DB_SCHEMA=my_app_schema
```

</div>
<div>

**`app.yaml` (deployed):**
```yaml
env:
  - name: LAKEBASE_ENDPOINT
    value: 'projects/<id>/branches/production/endpoints/primary'
  - name: PGHOST
    value: '<endpoint-hostname>'
  - name: PGPORT
    value: '5432'
  - name: PGDATABASE
    value: 'databricks_postgres'
  - name: PGSSLMODE
    value: 'require'
```

</div>
</div>

<!--
Speaker: Now we add the Lakebase plugin. Two steps: register in server.ts and configure env vars.
The plugin handles OAuth token rotation automatically — no passwords needed. DB_SCHEMA isolates
your app's tables within the shared database. Verify with npm run build to make sure the import compiles.
Timing: ~2 min
-->

---

<div class="phases">
<div class="p done">1 Scaffold + Build</div>
<div class="p done">2 Deploy Mock</div>
<div class="p done">3 Setup Lakebase</div>
<div class="p now">4 Wire Backend</div>
<div class="p">5 Deploy + E2E</div>
</div>

# Phase 4: Wire Lakebase Backend

**Skill:** `05-appkit-lakebase-wiring`

<div class="cols">
<div>

### What Gets Built
1. **DDL** — `CREATE SCHEMA` + `CREATE TABLE IF NOT EXISTS`
2. **Seed data** — `INSERT ... ON CONFLICT DO NOTHING`
3. **API routes** — `server.extend()` for CRUD endpoints
4. **Response format** — `{ data: [...], source: "live"|"mock" }`

### API Route Pattern

```typescript
appkit.server.extend((app) => {
  app.get("/api/bookings", async (req, res) => {
    try {
      const result = await appkit.lakebase.query(
        `SELECT * FROM ${DB_SCHEMA}.bookings
         ORDER BY created_at DESC`
      );
      res.json({
        data: result.rows.map(mapBooking),
        source: "live"
      });
    } catch {
      res.json({ data: MOCK_BOOKINGS, source: "mock" });
    }
  });
});
```

</div>
<div>

### Mock Fallback Pattern

Every API route returns mock data if Lakebase is unavailable:

```
Database available?
  YES → { data: liveRows, source: "live" }
  NO  → { data: mockArray, source: "mock" }
```

This means the app **always works** — with or without a database.

### Type Mapping (API Layer)

```typescript
function mapBooking(row: any): Booking {
  return {
    id: row.id,
    guestName: row.guest_name,     // snake → camel
    amount: Number(row.amount),     // DECIMAL → Number
    checkIn: row.check_in instanceof Date
      ? row.check_in.toISOString().slice(0,10)
      : String(row.check_in),      // Date → ISO
  };
}
```

</div>
</div>

<!--
Speaker: This is the most substantial phase. You design the schema from the PRD, write DDL,
create API routes with server.extend(), and build the mapper layer. The mock fallback pattern
is critical — every endpoint returns mock data if the database isn't available. This means
the app works locally without Lakebase AND degrades gracefully in production.
Timing: ~3 min
-->

---

<div class="phases">
<div class="p done">1 Scaffold + Build</div>
<div class="p done">2 Deploy Mock</div>
<div class="p done">3 Setup Lakebase</div>
<div class="p now">4 Wire Backend</div>
<div class="p">5 Deploy + E2E</div>
</div>

# Phase 4: Frontend Hooks

### `useLakebaseData` — Reusable Data Hook

```tsx
function useLakebaseData<T>(endpoint: string) {
  const [data, setData] = useState<T[]>([]);
  const [source, setSource] = useState<"live" | "mock" | "loading">("loading");

  useEffect(() => {
    fetch(endpoint)
      .then(res => res.json())
      .then(json => { setData(json.data ?? []); setSource(json.source ?? "mock"); })
      .catch(() => setSource("mock"));
  }, [endpoint]);

  return { data, source };
}
```

### `ConnectionStatus` — Visual Data Source Indicator

```tsx
function ConnectionStatus({ source }: { source: "live" | "mock" | "loading" }) {
  if (source === "loading") return <span>Loading...</span>;
  if (source === "live")    return <span className="text-green-600">● Live Data</span>;
  return                           <span className="text-yellow-600">● Mock Data</span>;
}
```

**Place `ConnectionStatus` at the top of every page** that fetches data.

<!--
Speaker: Two reusable patterns for the frontend. useLakebaseData wraps fetch/useState/useEffect
into a single hook — pass an endpoint, get back data and source. ConnectionStatus shows a green
or yellow indicator so users always know if they're seeing live or mock data. Put it on every page.
Timing: ~1.5 min
-->

---

# The Mock-to-Live Transition

<div class="cols">
<div>

### Before (Mock Data)

```tsx
// Static arrays in components
const BOOKINGS = [
  { id: 1, guest: "Alice", ... },
  { id: 2, guest: "Bob", ... },
];

function BookingList() {
  return BOOKINGS.map(b =>
    <BookingCard key={b.id} booking={b} />
  );
}
```

<div class="box" style="border-color: #EAB308;">
<span style="color: #EAB308;">● Mock Data</span> — bookings
</div>

</div>
<div>

### After (Live Data)

```tsx
// API-backed with mock fallback
function BookingList() {
  const { data, source } =
    useLakebaseData<Booking>("/api/bookings");

  return (
    <>
      <ConnectionStatus source={source} />
      {data.map(b =>
        <BookingCard key={b.id} booking={b} />
      )}
    </>
  );
}
```

<div class="box green">
<span style="color: var(--green);">● Live Data</span> — bookings
</div>

</div>
</div>

The transition: replace `MOCK_ARRAY.map(...)` with `useLakebaseData().data.map(...)`.

<!--
Speaker: Here's the before and after. On the left, static mock arrays rendered directly. On the
right, the same component but now powered by the useLakebaseData hook. The data comes from the
API, which returns live data from Lakebase or falls back to mock. The ConnectionStatus indicator
switches from yellow "Mock" to green "Live" when the database connects.
Timing: ~2 min
-->

---

<div class="phases">
<div class="p done">1 Scaffold + Build</div>
<div class="p done">2 Deploy Mock</div>
<div class="p done">3 Setup Lakebase</div>
<div class="p done">4 Wire Backend</div>
<div class="p now">5 Deploy + E2E</div>
</div>

# Phase 5: Deploy + E2E Test

**Skill:** `03-appkit-deploy` (reused from Phase 2)

<div class="cols">
<div>

### Deploy with Lakebase

```bash
# Build
npm run build

# Deploy (SP creates DB objects)
databricks apps deploy --profile $PROFILE
```

On first deploy with Lakebase, the **Service Principal** runs the DDL to create schemas, tables, and seed data.

### E2E Verification

1. Open the deployed app URL
2. Check `ConnectionStatus` shows **● Live Data**
3. Verify CRUD operations work
4. Test idle resilience (Lakebase scale-to-zero → reconnect)

</div>
<div>

### What Gets Verified

| Check | Expected |
|-------|----------|
| App loads | No errors in console |
| ConnectionStatus | Green "Live Data" |
| Data displays | Real rows from Lakebase |
| Create record | New row appears |
| Update record | Changes persist |
| Delete record | Row removed |
| Idle 5+ min, reload | Reconnects to Lakebase |

### Troubleshooting

```bash
# Stream app logs
databricks apps logs $APP_NAME \
  --follow --source APP --profile $PROFILE

# Check Lakebase connectivity
databricks apps logs $APP_NAME \
  --search "Lakebase" --profile $PROFILE
```

</div>
</div>

<!--
Speaker: The final deploy. This time the app has Lakebase wired in, so the Service Principal
creates the database objects on first run. E2E testing verifies everything: the app loads,
shows live data, CRUD works, and — critically — the app handles Lakebase going idle (scale-to-zero)
and reconnecting gracefully.
Timing: ~2 min
-->

---

# AppKit Plugin Architecture

All 5 plugins composing in a single app:

<div class="mermaid">
graph TB
    subgraph AppContainer["App Container (Node.js)"]
        Server["server()"]
        Analytics["analytics()"]
        Lakebase["lakebase()"]
        Genie["genie()"]
        Files["files()"]
    end
    Analytics -->|SQL queries| WH["SQL Warehouse"]
    Lakebase -->|CRUD + OAuth| PG["Lakebase PostgreSQL"]
    Genie -->|NL queries| GS["Genie Space"]
    Files -->|File ops| UC["UC Volumes"]
    Client["React Frontend"] -->|"useAnalyticsQuery"| Analytics
    Client -->|"useLakebaseData (custom)"| Lakebase
    Client -->|"GenieChat / useGenieChat"| Genie
    Client -->|"DirectoryList / FileBreadcrumb"| Files
</div>

Each plugin is **independent** — add only what you need. The `server()` plugin is always required.

<!--
Speaker: Here's the full plugin architecture. Five plugins, each connecting to a different backend
service. The frontend uses specialized hooks and components for each. Plugins compose freely —
you can start with just server(), add analytics() for dashboards, lakebase() for CRUD, genie()
for natural language, and files() for document management. Mix and match.
Timing: ~1.5 min
-->

---

# Skill Dependency Map

How the 6 AppKit skills connect to the 5 workshop phases:

<div class="cols">
<div>

### Phase → Skill Mapping

| Phase | Primary Skill | Supporting |
|-------|--------------|------------|
| 1. Scaffold | `01-appkit-scaffold` | `00-navigator` |
| 1. Build | `02-appkit-build` | — |
| 2. Deploy | `03-appkit-deploy` | — |
| 3. Lakebase | `databricks-lakebase` | — |
| 4. Plugin | `04-appkit-plugin-add` | — |
| 4. Wire | `05-appkit-lakebase-wiring` | — |
| 5. Deploy | `03-appkit-deploy` | — |

</div>
<div>

### Skill Dependencies

<div class="tree" style="font-size:0.55em;">
<span class="hl3">00-appkit-navigator</span>  ← routing only
│
<span class="hl">01-appkit-scaffold</span>     ← standalone
└── <span class="hl">02-appkit-build</span>    ← needs scaffold
│
<span class="hl">03-appkit-deploy</span>       ← standalone
│   (used in Phase 2 AND Phase 5)
│
<span class="hl">04-appkit-plugin-add</span>   ← needs scaffold
└── <span class="hl">05-appkit-lakebase-wiring</span> ← needs plugin
</div>

### Cross-References to Training

- Phase 1 → Module 2 (AppKit) + Module 2 (Dev Loop)
- Phase 3 → Module 3 (Lakebase)
- Phase 4 → Module 3 (Database Design)
- Phase 5 → Module 1 (Databricks Apps)

</div>
</div>

<!--
Speaker: This map shows how skills connect to phases and how the training modules support each
phase. Notice 03-appkit-deploy is used twice — Phase 2 (mock) and Phase 5 (live). The dependency
chain is linear: scaffold → build → deploy, then plugin-add → lakebase-wiring → deploy again.
Timing: ~1.5 min
-->

---

<!-- _class: divider -->
<!-- _paginate: skip -->
<!-- _transition: cover -->

# Act V

Putting It All Together

Two paths, one destination — AI-powered data products on Databricks

<!--
Speaker: Let's bring it all together. Both paths — the data pipeline and the app — converge into
a complete, production-grade solution. I'll show you how to get started with copy-paste prompts.
Timing: ~30 sec transition
-->

---

# Both Paths Converge

<div class="mermaid">
graph TB
    PathB["Path B: Data Pipeline"] --> Gold["Gold Tables"]
    Gold --> Semantic["Semantic Layer<br/>(Metric Views + Genie)"]
    Semantic --> Monitor["Observability"]
    PathA["Path A: Databricks App"] --> AppUI["AppKit UI"]
    AppUI -->|"analytics() plugin"| Gold
    AppUI -->|"genie() plugin"| Semantic
    AppUI -->|"lakebase() plugin"| LB["Lakebase<br/>(App State)"]
    Monitor --> Dash["AI/BI Dashboards"]
    Gold --> ML["ML Models"]
    ML --> Agents["GenAI Agents"]
    Agents -->|"served via"| AppUI
</div>

**The complete picture:**
- **Path B** builds the data foundation (Gold tables, semantic layer, ML models, agents)
- **Path A** builds the user-facing app that queries that foundation
- Together: a production data product with a beautiful frontend

<!--
Speaker: Here's the convergence. Your data pipeline produces Gold tables, a semantic layer, ML
models, and GenAI agents. Your Databricks App queries those Gold tables via the analytics plugin,
embeds Genie via the genie plugin, stores app state in Lakebase, and can serve agent responses.
The two paths aren't separate — they're two halves of the same product.
Timing: ~2 min
-->

---

# Workshop Parameters

Fill in before starting. Referenced throughout all steps.

| Parameter | Description | Your Value |
|-----------|-------------|------------|
| `{workspace_url}` | Your Databricks workspace URL | `https://____________.cloud.databricks.com` |
| `{use_case_slug}` | Short app identifier (e.g., `bookings`) | `________________` |
| `{PROFILE}` | Databricks CLI profile name | `________________` |
| `{user_app_name}` | Lakebase project name (Phase 3 output) | `________________` |
| `{LAKEBASE_HOST}` | Lakebase endpoint hostname (Phase 3 output) | `________________` |

### Pre-flight Check

```bash
# Verify workspace access
databricks current-user me --host {workspace_url}

# Verify CLI version (>= 0.295.0)
databricks --version

# Verify Node.js (>= v22)
node --version
```

<!--
Speaker: Before you start, fill in these parameters. You'll need your workspace URL, a short
name for your app, and your CLI profile. The Lakebase values get filled in during Phase 3.
Run the pre-flight checks to make sure your environment is ready.
Timing: ~1.5 min
-->

---

# Your Turn — Path A Prompts

Copy-paste these into your AI coding assistant to execute each phase:

### Phase 1: Scaffold + Build

```
I want to build a Databricks App. My workspace is {workspace_url}.
Read @apps_lakebase/skills/01-appkit-scaffold/SKILL.md and scaffold a blank AppKit project.
Then read @apps_lakebase/skills/02-appkit-build/SKILL.md and build the UI from @docs/design_prd.md
using mock data arrays.
```

### Phase 2: Deploy

```
Deploy the app to Databricks Apps. Read @apps_lakebase/skills/03-appkit-deploy/SKILL.md
App name: $APP_NAME, Profile: $PROFILE
```

### Phase 4: Wire Lakebase

```
Add the Lakebase plugin and wire the backend. Read @apps_lakebase/skills/04-appkit-plugin-add/SKILL.md
to register the plugin, then @apps_lakebase/skills/05-appkit-lakebase-wiring/SKILL.md
to design the schema, build CRUD APIs, and wire the frontend.
```

<!--
Speaker: These are your copy-paste prompts. Start a new AI conversation for each phase. The @
syntax references files in your workspace — the AI reads the skill and follows its instructions.
Adjust the workspace URL and app name for your setup.
Timing: ~2 min
-->

---

# Your Turn — Path B Prompts

### Stage 1: Gold Design

```
I have a customer schema at @data_product_accelerator/context/Wanderbricks_Schema.csv.
Please design the Gold layer using @data_product_accelerator/skills/gold/00-gold-layer-design/SKILL.md
```

### Stage 2: Bronze

```
Create the Bronze layer with test data. Read @data_product_accelerator/skills/bronze/00-bronze-layer-setup/SKILL.md
Use the schema CSV at @data_product_accelerator/context/Wanderbricks_Schema.csv
```

### Stage 3: Silver

```
Build the Silver DLT pipelines with DQ rules. Read @data_product_accelerator/skills/silver/00-silver-layer-setup/SKILL.md
```

### One prompt per stage. One new conversation per stage.

See the full [9-stage guide](data_product_accelerator/QUICKSTART.md) for all prompts.

<!--
Speaker: Path B follows the same pattern — one prompt per stage, one conversation per stage.
Start with Gold Design and your schema CSV. Each orchestrator handles the entire workflow for
its stage. The QUICKSTART.md file has the complete set of prompts for all 9 stages.
Timing: ~2 min
-->

---

# Resources & Links

<div class="cols">
<div>

### Repository
- [AGENTS.md](AGENTS.md) — Root navigator
- [QUICKSTART.md](data_product_accelerator/QUICKSTART.md) — 9-stage prompts
- [Instructions.md](apps_lakebase/Instructions.md) — AppKit workshop guide
- [PRE-REQUISITES.md](PRE-REQUISITES.md) — Setup checklist

### AppKit Documentation
- [AppKit Docs](https://databricks.github.io/appkit/) — Official docs
- `npx @databricks/appkit docs` — In-terminal docs
- [Agent Skills Repo](https://github.com/databricks/databricks-agent-skills) — Databricks skills

</div>
<div>

### Platform Docs
- [Databricks Apps](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/)
- [Lakebase](https://docs.databricks.com/aws/en/database/)
- [SDP/DLT](https://docs.databricks.com/aws/en/ldp/)
- [Genie Spaces](https://docs.databricks.com/aws/en/genie/)
- [Unity Catalog](https://docs.databricks.com/aws/en/data-governance/unity-catalog/)

### Framework
- [Agent Skills Format](https://agentskills.io) — SKILL.md standard
- [Skill Navigation Guide](data_product_accelerator/docs/framework-design/10-skill-navigation-visual-guide.html)
- [Skill Hierarchy Tree](data_product_accelerator/docs/framework-design/11-skill-hierarchy-tree.html)

</div>
</div>

<!--
Speaker: Bookmark these. The AGENTS.md is your entry point for any AI assistant. The AppKit docs
are the source of truth for API details. The Agent Skills repo has the latest Databricks-maintained
skills. And the framework docs have visual walkthroughs of how orchestrators work.
Timing: ~1 min
-->

---

<!-- _class: title -->
<!-- _paginate: skip -->
<!-- _transition: cover -->

# Thank You

## Build Something Amazing

<br/>

**59 Agent Skills** — ready to guide your AI assistant

**Start now:** Clone the repo, pick a path, paste a prompt

<br/>

Questions?

<!--
Speaker: That's the full journey — from a schema CSV or PRD to a production data product with
a beautiful Databricks App, all powered by AI-assisted development. The skills are ready. Your
AI assistant is ready. All you need is a workspace and a use case. Let's open it up for questions.
Timing: Q&A
-->
