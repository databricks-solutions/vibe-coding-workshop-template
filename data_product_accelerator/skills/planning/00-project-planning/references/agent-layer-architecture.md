# Agent Layer Architecture — Detailed Reference

## Core Principle: Agents Use Genie Spaces as Query Interface

**AI Agents DO NOT query data assets directly.** Instead, they use Genie Spaces as their natural language query interface. Genie Spaces translate natural language to SQL and route to appropriate tools (TVFs, Metric Views, ML Models).

## Architecture Diagram (3-Tier)

```
┌───────────────────────────┐
│     AI AGENT (Phase 2)    │
│ (e.g., {Domain} Agent)    │
│   - System Prompt         │
│   - Tools (Genie Spaces)  │
└───────────┬───────────────┘
            │ Natural Language Query
            ▼
┌───────────────────────────┐
│   GENIE SPACE (Phase 1.6) │
│ (e.g., {Domain} Intel)    │
│   - Instructions          │
│   - Data Assets           │
└───────────┬───────────────┘
            │ SQL Query
            ▼
┌───────────────────────────┐
│   DATA ASSETS (Phase 1)   │
│ (TVFs, Metric Views,      │
│  ML Models, Gold Tables)  │
└───────────────────────────┘
```

## Why Genie Spaces (Not Direct SQL)?

| Without Genie Spaces | With Genie Spaces |
|---------------------|-------------------|
| Agents must write SQL | Agents use natural language |
| High SQL complexity for agents | Abstraction layer for agents |
| Direct data asset coupling | Decoupled agent from data schema |
| Manual SQL optimization | Genie handles query optimization |
| Limited natural language understanding | Enhanced NL-to-SQL capabilities |
| Hard to maintain agent prompts | Genie instructions act as agent context |
| No built-in guardrails | Genie provides query guardrails |
| No benchmark testing framework | Genie has built-in benchmark testing |

### Why Agents Should Use Genie Spaces — Summary

1. **Abstraction Layer:** Agents don't need to know SQL syntax or schema details
2. **Schema Evolution:** Data model changes don't break agent implementations
3. **Query Optimization:** Genie Spaces handle SQL optimization automatically
4. **Natural Language:** Genie Spaces are designed for NL-to-SQL translation
5. **Guardrails:** Genie Spaces provide built-in query safety checks
6. **Testing Framework:** Benchmark questions test both Genie and Agent accuracy

## Agent-to-Genie Space Mapping

**The mapping between agents and Genie Spaces depends on your total asset count, not a fixed formula.**

### Mapping Patterns by Scale

**Small projects (≤25 total assets):** All agents share 1 unified Genie Space.

| Agent | Genie Space | Why |
|-------|-------------|-----|
| All domain agents | Unified {Project} Space | Assets fit in one space; splitting would create thin, low-quality spaces |
| Orchestrator Agent | Unified {Project} Space | Same space; orchestrator routes by intent, not by space |

**Medium projects (26-50 total assets):** 2-3 consolidated Genie Spaces.

| Agent | Genie Space | Why |
|-------|-------------|-----|
| {Domain 1} + {Domain 2} Agent | Combined Analytics Space | Related domains share tables; combined for context quality |
| {Domain 3} Agent | {Domain 3} Intelligence | Distinct enough to warrant its own space |
| Orchestrator Agent | Unified {Project} Space | Cross-domain routing |

**Large projects (50+ total assets):** Domain-specific Genie Spaces (but audit that each has 10-25 assets).

| Agent | Genie Space | Why |
|-------|-------------|-----|
| {Domain 1} Agent | {Domain 1} Intelligence | 15-25 assets; semantically cohesive |
| {Domain N} Agent | {Domain N} Intelligence | 15-25 assets; semantically cohesive |
| Orchestrator Agent | Unified {Project} Monitor | Intent classification, multi-agent coordination |

### Capacity Check (Always Run This)

```
For each proposed Genie Space:
  asset_count = tables + metric_views + tvfs + ml_prediction_tables
  
  IF asset_count > 25:  SPLIT (Genie hard limit)
  IF asset_count < 10:  MERGE with related space (too thin for good NL quality)
  IF 10 ≤ asset_count ≤ 25:  OK ✅
```

## Multi-Agent Architecture Diagram (Phase 2)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    USER / FRONTEND APPLICATION                       │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR AGENT                                │
│  Purpose: Intent classification, multi-domain query coordination     │
│  Genie Space: Unified {Project} Monitor                             │
│  Capabilities: Route to specialized agents, synthesize responses     │
└─────────────────────────────────────────────────────────────────────┘
                    │               │               │
        ┌───────────┘               │               └───────────┐
        ▼                           ▼                           ▼
┌───────────────────┐   ┌───────────────────┐   ┌───────────────────┐
│  {Domain 1} Agent │   │  {Domain 2} Agent │   │  {Domain N} Agent │
│  Genie: {D1} Int  │   │  Genie: {D2} Int  │   │  Genie: {DN} Int  │
└───────────────────┘   └───────────────────┘   └───────────────────┘
        │                           │                           │
        ▼                           ▼                           ▼
┌───────────────────────────────────────────────────────────────────────┐
│                         GENIE SPACES (Phase 1.6)                       │
│  Each agent uses its dedicated Genie Space as the query interface      │
└───────────────────────────────────────────────────────────────────────┘
        │                           │                           │
        ▼                           ▼                           ▼
┌───────────────────────────────────────────────────────────────────────┐
│                    DATA ASSETS (Phase 1.1-1.5, 1.7)                    │
│  TVFs | Metric Views | ML Models | Lakehouse Monitors | Gold Tables   │
└───────────────────────────────────────────────────────────────────────┘
```

## Agent-to-Genie Space Design Patterns

| Pattern | Description | When to Use |
|---------|-------------|-------------|
| Unified | All agents share 1 Genie Space | ≤25 total assets; small projects |
| Consolidated | 2-3 spaces grouping related domains | 26-50 total assets; domains share tables |
| 1:1 Mapping | Each domain agent has dedicated space | 50+ assets; domains are semantically distinct |
| Orchestrator + Unified | Orchestrator uses a unified cross-domain space | Multi-domain coordination in any pattern |
| Hierarchical | Orchestrator routes to specialized agents per space | Complex multi-intent queries; large projects |

## System Prompt Derivation

**Genie Space `instructions` become agent system prompts:**
- Keep instructions ≤20 lines (LLM context efficiency)
- Include data asset selection guidance
- Document query patterns and syntax rules
- Add domain-specific business rules

## Three-Level Testing Strategy

### Level 1: Genie Space Standalone (Phase 1.6)

Validate Genie Spaces work before agent integration:
- [ ] All benchmark questions return correct results
- [ ] Query latency < 10 seconds
- [ ] >80% accuracy on domain-specific questions

### Level 2: Agent Integration (Phase 2)

Validate agents correctly use Genie Spaces:
- [ ] Agent correctly routes queries to Genie Space tool
- [ ] Agent interprets Genie Space results accurately
- [ ] >90% intent classification accuracy
- [ ] Correct tool usage patterns

### Level 3: Multi-Agent Workflow (Phase 2)

Validate Orchestrator coordinates specialized agents:
- [ ] Orchestrator correctly classifies multi-domain intent
- [ ] Sub-queries routed to correct specialized agents
- [ ] Responses synthesized coherently
- [ ] >85% multi-intent classification accuracy

### Testing Summary

| Level | What to Test | Success Criteria |
|-------|--------------|------------------|
| 1. Genie Standalone | Genie Space accuracy | >80% benchmark accuracy |
| 2. Agent Integration | Agent uses Genie correctly | >90% tool usage accuracy |
| 3. Multi-Agent | Orchestrator coordination | >85% intent classification |

**Test each level before proceeding to the next.** Do not skip levels.

## Critical Deployment Order

```
Phase 1.1-1.5 (Data Assets) → Phase 1.6 (Genie Spaces) → Phase 2 (Agents)
         ↓                            ↓                        ↓
   Build foundation          Create NL interface        Consume interface
```

**Agents CANNOT be developed until Genie Spaces are deployed and validated.**

## Multi-Agent Query Example (Generic)

```
User: "What was last month's {metric_A} and which {entities_B} performed best?"
                    │
                    ▼
        ┌──────────────────────────────────────┐
        │        Orchestrator Agent            │
        │ Uses: Unified {Project} Monitor      │
        │ Intent: Multi-domain ({D1} + {D2})   │
        └──────────────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        ▼                       ▼
┌───────────────────┐   ┌───────────────────┐
│  {Domain 1} Agent │   │  {Domain 2} Agent │
│  Uses: {D1}       │   │  Uses: {D2}       │
│  Intelligence     │   │  Intelligence     │
└───────────────────┘   └───────────────────┘
        │                       │
        ▼                       ▼
    Genie Space             Genie Space
        │                       │
        ├── get_{d1}_trend      ├── get_{d2}_performance
        ├── {d1}_analytics      ├── {d2}_analytics
        └── {d1}_forecasts      └── get_{d2}_rankings
                    │
                    ▼
        Synthesized Response:
        "{Domain 1} summary + {Domain 2} summary
         combined into a coherent answer"
```

For a concrete worked example with real domain names and data, see [Worked Example: Wanderbricks](worked-example-wanderbricks.md).
