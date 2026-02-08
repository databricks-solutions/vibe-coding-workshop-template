# Data Product Accelerator — Design Documentation

## Overview

The Data Product Accelerator is an **AI-assisted development system** for building production-grade Databricks Lakehouse solutions. It uses a **skills-first architecture** where Agent Skills encode domain expertise, orchestration workflows, and production patterns — enabling an AI coding assistant to build complete Medallion Architecture implementations from a single schema CSV input.

> **Core Principle:**
> *Design-First, Extract-Don't-Generate* — Design the target Gold dimensional model from the customer's schema CSV, then build data layers to feed it, using scripted extraction from source files rather than AI-generated names.

## Document Index

| # | Document | Description |
|---|----------|-------------|
| 01 | [Introduction](01-introduction.md) | Purpose, scope, prerequisites, best practices matrix, success criteria |
| 02 | [Architecture Overview](02-architecture-overview.md) | Skills-first architecture, data flows, technology stack, design principles |
| 03 | [Design-First Pipeline](03-design-first-pipeline.md) | 9-stage pipeline from schema CSV to GenAI agents, Plan-as-Contract pattern |
| 04 | [Agent Skills System](04-agent-skills-system.md) | Orchestrator/worker skill pattern, progressive disclosure, context budgets |
| 05 | [Skill Domains](05-skill-domains.md) | Per-domain skill inventory — Bronze through GenAI Agents |
| 06 | [Common Skills](06-common-skills.md) | 8 cross-cutting shared skills deep dive |
| 07 | [Implementation Guide](07-implementation-guide.md) | Step-by-step workshop walkthrough from zero to production |
| 08 | [Operations Guide](08-operations-guide.md) | Maintenance, skill freshness auditing, self-improvement, evolution |

## Appendices

| # | Document | Description |
|---|----------|-------------|
| A | [Code Examples](appendices/A-code-examples.md) | Complete working code snippets for key patterns |
| B | [Troubleshooting](appendices/B-troubleshooting.md) | Error reference and solutions |
| C | [References](appendices/C-references.md) | Official documentation links and external resources |

## Framework Architecture Summary

```
┌──────────────────────────────────────────────────────────────────────┐
│                     DATA PRODUCT ACCELERATOR                            │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │              AGENTS.md (Universal Entry Point)                │    │
│  │  ┌─────────────────────────┐ ┌────────────────────────────┐  │    │
│  │  │  Orchestrator Routing   │ │ Common Skills Index        │  │    │
│  │  │  (Route to skills)      │ │ (8 shared skills)          │  │    │
│  │  └─────────────────────────┘ └────────────────────────────┘  │    │
│  └──────────────────────────────────┬───────────────────────────┘    │
│                                     │ routes to                      │
│  ┌──────────────────────────────────▼───────────────────────────┐    │
│  │              skills/ (50 Agent Skills)               │    │
│  │                                                               │    │
│  │  ┌──────────────┐  ┌───────────────┐  ┌──────────────────┐  │    │
│  │  │ Orchestrators │  │    Workers     │  │  Common Skills   │  │    │
│  │  │ (00-*)        │  │ (01-*, 02-*)  │  │  (shared)        │  │    │
│  │  │               │  │               │  │                  │  │    │
│  │  │ Gold Design   │  │ Faker Data    │  │ Expert Agent     │  │    │
│  │  │ Bronze Setup  │  │ DLT Expect.   │  │ Asset Bundles    │  │    │
│  │  │ Silver Setup  │  │ Merge Patterns│  │ Autonomous Ops   │  │    │
│  │  │ Gold Impl.    │  │ Schema Valid. │  │ Naming Standards │  │    │
│  │  │ Planning      │  │ ERD Patterns  │  │ Python Imports   │  │    │
│  │  │ Semantic      │  │ Genie API     │  │ Table Properties │  │    │
│  │  │ Observability │  │ Eval/Scoring  │  │ Schema Mgmt      │  │    │
│  │  │ ML Pipeline   │  │ Memory        │  │ UC Constraints   │  │    │
│  │  │ GenAI Agents  │  │ Deployment    │  │                  │  │    │
│  │  └──────────────┘  └───────────────┘  └──────────────────┘  │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                     │                                │
│                                     ▼                                │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │            DESIGN-FIRST PIPELINE (9 STAGES)                   │    │
│  │                                                               │    │
│  │  context/*.csv → Gold Design → Bronze → Silver → Gold Impl   │    │
│  │    → Planning → Semantic → Observability → ML → GenAI        │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                     │                                │
│                                     ▼                                │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │                    GENERATED OUTPUT                            │    │
│  │  src/ notebooks • Asset Bundles • YAML schemas • SQL • Python │    │
│  └──────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────┘
```

## Quick Start

1. **Understand the Architecture**: Start with [02-Architecture Overview](02-architecture-overview.md)
2. **Learn the Pipeline**: Read [03-Design-First Pipeline](03-design-first-pipeline.md) for the 9-stage workflow
3. **Explore the Skills**: Review [04-Agent Skills System](04-agent-skills-system.md) for orchestrator/worker patterns
4. **Build Something**: Follow [07-Implementation Guide](07-implementation-guide.md) for a step-by-step workshop

## Best Practices Showcased

| # | Best Practice | Implementation | Document |
|---|---------------|----------------|----------|
| 1 | Extract, Don't Generate | Script table/column names from Gold YAML, never hardcode | [04-Agent Skills](04-agent-skills-system.md) |
| 2 | Design-First Pipeline | Design Gold target model before building Bronze/Silver layers | [03-Pipeline](03-design-first-pipeline.md) |
| 3 | Progressive Disclosure | SKILL.md (~2K) → references/ (2-8K) → scripts/ (on demand) | [04-Agent Skills](04-agent-skills-system.md) |
| 4 | Skills-First Architecture | AGENTS.md entry point + 50 skills (not 46 rules) | [02-Architecture](02-architecture-overview.md) |
| 5 | Plan-as-Contract | Planning emits YAML manifests consumed by downstream stages | [03-Pipeline](03-design-first-pipeline.md) |
| 6 | Orchestrator-First Routing | Route to 00-* orchestrator, which loads worker skills as needed | [04-Agent Skills](04-agent-skills-system.md) |
| 7 | Autonomous Operations | Deploy → Poll → Diagnose → Fix → Redeploy without human intervention | [06-Common Skills](06-common-skills.md) |
| 8 | Unity Catalog Governance | PII tags, comments, constraints, lineage on every asset | [02-Architecture](02-architecture-overview.md) |

## Key Statistics

| Metric | Value |
|--------|-------|
| Agent Skills | 50 across 12 domains |
| Orchestrator Skills | 10 (one per pipeline stage + utilities) |
| Worker Skills | 30+ (domain-specific patterns) |
| Common/Shared Skills | 8 (cross-cutting concerns) |
| Admin/Utility Skills | 6 (skill creation, auditing, documentation) |
| Always-On Cursor Rules | 2 (routing only) |
| Pipeline Stages | 9 (Gold Design → GenAI Agents) |
| Domains Covered | Bronze, Silver, Gold, Semantic, Monitoring, ML, GenAI, Planning, Exploration, Admin |
| Time Savings | 4-6x faster than from-scratch development |
| Target Implementation Time | 20-30 hours (full stack) |

## Related Documentation

- [QUICKSTART.md](../../QUICKSTART.md) — One-prompt-per-stage guide (the primary usage guide)
- [README.md](../../README.md) — Project overview
- [Skill Navigator](../../skills/skill-navigator/SKILL.md) — Intelligent skill routing system
