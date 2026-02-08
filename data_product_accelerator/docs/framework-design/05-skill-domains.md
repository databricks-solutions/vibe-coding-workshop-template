# 05 — Skill Domains

## Overview

The framework's 50 Agent Skills are organized into 12 domain directories. Each domain corresponds to a layer of the Medallion Architecture, a platform capability, or an administrative function. This document provides the complete inventory of every skill in every domain.

## Domain Summary

| Domain | Directory | Orchestrator | Workers | Total | Pipeline Stage |
|--------|-----------|-------------|---------|-------|---------------|
| Gold (Design) | `gold/` | `00-gold-layer-design` | 7 workers | 9 | Stage 1 |
| Bronze | `bronze/` | `00-bronze-layer-setup` | 1 worker | 2 | Stage 2 |
| Silver | `silver/` | `00-silver-layer-setup` | 2 workers | 3 | Stage 3 |
| Gold (Impl) | `gold/` | `01-gold-layer-setup` | (shared) | (shared) | Stage 4 |
| Planning | `planning/` | `00-project-planning` | 0 | 1 | Stage 5 |
| Semantic Layer | `semantic-layer/` | `00-semantic-layer-setup` | 5 workers | 6 | Stage 6 |
| Monitoring | `monitoring/` | `00-observability-setup` | 4 workers | 5 | Stage 7 |
| ML | `ml/` | `00-ml-pipeline-setup` | 0 | 1 | Stage 8 |
| GenAI Agents | `genai-agents/` | `00-genai-agents-setup` | 8 workers | 9 | Stage 9 |
| Exploration | `exploration/` | `00-adhoc-exploration-notebooks` | 0 | 1 | Standalone |
| Common | `common/` | — | — | 8 | All stages |
| Admin | `admin/` | — | — | 4 | Meta/utility |

---

## Gold Domain (`gold/`)

Two orchestrators (Design and Implementation) share 7 worker skills.

| Skill | Role | Description |
|-------|------|-------------|
| `00-gold-layer-design` | Orchestrator | Schema CSV → ERDs, YAML schemas, documentation (stage 1) |
| `01-gold-layer-setup` | Orchestrator | YAML → tables, MERGE scripts, FK constraints (stage 4) |
| `02-yaml-driven-gold-setup` | Worker | Dynamic Gold table creation from YAML at runtime |
| `03-gold-layer-documentation` | Worker | Naming conventions, column descriptions, dual-purpose comments |
| `04-gold-layer-merge-patterns` | Worker | Silver-to-Gold MERGE operations, SCD Type 1/2, column mapping |
| `05-gold-delta-merge-deduplication` | Worker | Dedup-before-merge to prevent duplicate key errors |
| `06-fact-table-grain-validation` | Worker | Transaction vs aggregated vs snapshot grain inference |
| `07-gold-layer-schema-validation` | Worker | DataFrame columns vs target table schema validation |
| `08-mermaid-erd-patterns` | Worker | Mermaid ERD syntax, master/domain/summary diagrams |

---

## Bronze Domain (`bronze/`)

| Skill | Role | Description |
|-------|------|-------------|
| `00-bronze-layer-setup` | Orchestrator | End-to-end Bronze layer creation (DDL, data, jobs) |
| `01-faker-data-generation` | Worker | Synthetic data with configurable corruption rates |

---

## Silver Domain (`silver/`)

| Skill | Role | Description |
|-------|------|-------------|
| `00-silver-layer-setup` | Orchestrator | DLT pipelines with DQ rules and quarantine patterns |
| `01-dlt-expectations-patterns` | Worker | DLT expectations with UC Delta table storage |
| `02-dqx-patterns` | Worker | Advanced DQ diagnostics with failure tracking |

Note: Some duplicate directory names exist (`00-silver-layer-creation`, `silver-layer-creation`) as legacy artifacts.

---

## Planning Domain (`planning/`)

| Skill | Role | Description |
|-------|------|-------------|
| `00-project-planning` | Orchestrator | Multi-phase planning with YAML manifest generation |
| `00-project-plan-methodology` | Orchestrator (alt) | Legacy/alternative planning methodology |

---

## Semantic Layer Domain (`semantic-layer/`)

| Skill | Role | Description |
|-------|------|-------------|
| `00-semantic-layer-setup` | Orchestrator | End-to-end semantic layer (Metric Views + TVFs + Genie) |
| `01-metric-views-patterns` | Worker | UC Metric Views with YAML structure and joins |
| `02-databricks-table-valued-functions` | Worker | TVFs for Genie (STRING params, null safety, v3.0 comments) |
| `03-genie-space-patterns` | Worker | Genie Space setup, agent instructions, benchmark questions |
| `04-genie-space-export-import-api` | Worker | Programmatic Genie Space deployment via REST API |
| `05-genie-space-optimization` | Worker | Optimization loop targeting 95%+ accuracy |

---

## Monitoring Domain (`monitoring/`)

| Skill | Role | Description |
|-------|------|-------------|
| `00-observability-setup` | Orchestrator | Monitors + dashboards + alerts end-to-end |
| `01-lakehouse-monitoring-comprehensive` | Worker | Data Quality API monitors with custom metrics |
| `02-databricks-aibi-dashboards` | Worker | Lakeview dashboard JSON, widget patterns, deployment |
| `03-sql-alerting-patterns` | Worker | SQL Alerts V2 with config-driven deployment |
| `04-anomaly-detection` | Worker | Schema-level freshness/completeness monitoring |

---

## ML Domain (`ml/`)

| Skill | Role | Description |
|-------|------|-------------|
| `00-ml-pipeline-setup` | Orchestrator | MLflow experiments, Feature Store, training, inference |

This is a self-contained orchestrator with rich `references/` files (8 reference docs, 4 template scripts, 3 job templates).

---

## GenAI Agents Domain (`genai-agents/`)

The largest domain with the most workers.

| Skill | Role | Description |
|-------|------|-------------|
| `00-genai-agents-setup` | Orchestrator | End-to-end agent implementation |
| `00-genai-agent-implementation` | Orchestrator (alt) | Alternative entry point |
| `01-responses-agent-patterns` | Worker | MLflow ResponsesAgent with streaming |
| `02-mlflow-genai-evaluation` | Worker | LLM judges, custom scorers, thresholds |
| `03-lakebase-memory-patterns` | Worker | Short-term (CheckpointSaver) + long-term (DatabricksStore) |
| `04-prompt-registry-patterns` | Worker | Versioned prompts in Unity Catalog |
| `05-multi-agent-genie-orchestration` | Worker | Parallel domain queries, intent classification |
| `06-deployment-automation` | Worker | Evaluation-then-promote CI/CD |
| `07-production-monitoring` | Worker | Registered scorers, sampling, trace archival |
| `08-mlflow-genai-foundation` | Worker | Core MLflow 3.0 GenAI patterns |
| `08-genie-space-optimization` | Worker | Cross-domain optimization (shared with semantic-layer) |

---

## Exploration Domain (`exploration/`)

| Skill | Role | Description |
|-------|------|-------------|
| `00-adhoc-exploration-notebooks` | Standalone | Dual-format notebooks (Databricks .py + Jupyter .ipynb) |

---

## Common Skills (`common/`)

See [06-Common Skills](06-common-skills.md) for the detailed deep dive.

| Skill | Description |
|-------|-------------|
| `databricks-expert-agent` | Core SA agent behavior, "Extract Don't Generate" |
| `databricks-asset-bundles` | DAB configuration for jobs, pipelines, dashboards |
| `databricks-autonomous-operations` | Self-healing deploy-fix-redeploy loop |
| `naming-tagging-standards` | Enterprise naming, comments, tags |
| `databricks-python-imports` | Code sharing between notebooks |
| `databricks-table-properties` | TBLPROPERTIES, CDF, auto-optimize |
| `schema-management-patterns` | `CREATE SCHEMA`, predictive optimization |
| `unity-catalog-constraints` | PK/FK constraints, surrogate keys |

---

## Admin/Utility Skills (`admin/`)

| Skill | Description |
|-------|-------------|
| `create-agent-skill` | Guides creation of new Agent Skills |
| `documentation-organization` | Documentation structure enforcement + framework authoring |
| `self-improvement` | Agent learning from mistakes |
| `skill-freshness-audit` | Verify skills against latest docs |

---

## Skill Navigator (`skill-navigator/`)

| Skill | Description |
|-------|-------------|
| `skill-navigator` | Master routing, domain indexes, context budget management |

This is the full version of the skill navigator. The condensed routing table lives in `AGENTS.md` at the repository root (the universal entry point for any AI coding assistant).
