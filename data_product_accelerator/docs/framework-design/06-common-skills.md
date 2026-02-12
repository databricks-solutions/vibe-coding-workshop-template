# 06 — Common Skills

## Overview

The 8 common skills are cross-cutting concerns that apply across all pipeline stages. Every orchestrator declares which common skills it depends on in its `common_dependencies` metadata. At minimum, every orchestrator reads `databricks-expert-agent` and `naming-tagging-standards`.

These skills live in `data_product_accelerator/skills/common/` and are indexed in the `AGENTS.md` entry point at the repository root.

## Skill Deep Dives

### 1. databricks-expert-agent

| Field | Value |
|-------|-------|
| **Path** | `data_product_accelerator/skills/common/databricks-expert-agent/SKILL.md` |
| **Read When** | Every task (core agent behavior) |
| **Key Pattern** | "Extract, Don't Generate" — script names from source files |

This is the foundational skill that transforms the AI assistant into a Senior Databricks Solutions Architect. It enforces:

- **Unity Catalog everywhere** — UC-managed catalogs, schemas, tables, views, functions
- **Delta Lake + Medallion** — All data in Delta, Bronze → Silver → Gold layering
- **Data quality by design** — DLT expectations, quarantine patterns
- **Performance & cost** — Predictive Optimization, automatic liquid clustering, Serverless
- **Contracts & semantics** — PK/FK constraints, Metric Views, TVFs
- **Documentation** — Every asset gets a COMMENT and tags

The "Extract, Don't Generate" principle is the most critical pattern: never hardcode table names, column names, or function signatures. Extract them from the Gold YAML schemas.

---

### 2. databricks-asset-bundles

| Field | Value |
|-------|-------|
| **Path** | `data_product_accelerator/skills/common/databricks-asset-bundles/SKILL.md` |
| **Read When** | Creating jobs, pipelines, dashboards, alerts |
| **Key Patterns** | `notebook_task` (not `python_task`), `base_parameters` (not `parameters`), serverless environments |

Defines standard patterns for Databricks Asset Bundles (DABs) — the Infrastructure-as-Code mechanism for deploying Databricks resources. Key rules:

- Always use `notebook_task` with `base_parameters` dict
- Never use `python_task` or CLI-style `parameters` array
- Mandatory serverless environment configuration
- Hierarchical job architecture: atomic → composite → orchestrator
- DLT pipeline, dashboard, and alert resource patterns

---

### 3. databricks-autonomous-operations

| Field | Value |
|-------|-------|
| **Path** | `data_product_accelerator/skills/common/databricks-autonomous-operations/SKILL.md` |
| **Read When** | Deploy/poll/diagnose/fix loop when jobs fail |
| **Key Pattern** | Self-healing Deploy → Poll → Diagnose → Fix → Redeploy cycle |

The most operationally important common skill. When something fails during deployment or job execution, this skill enables the AI assistant to:

1. **Deploy** — `databricks bundle deploy -t {target}`
2. **Poll** — Monitor job/pipeline run status via SDK/CLI
3. **Diagnose** — Read error logs, identify root cause
4. **Fix** — Apply code/config fixes based on error patterns
5. **Redeploy** — Re-deploy and re-run, verify success

This skill also serves as the SDK/CLI/REST API reference for all Databricks operations.

---

### 4. naming-tagging-standards

| Field | Value |
|-------|-------|
| **Path** | `data_product_accelerator/skills/common/naming-tagging-standards/SKILL.md` |
| **Read When** | Creating ANY DDL, COMMENTs, tags, workflows |
| **Key Patterns** | `snake_case`, `dim_`/`fact_` prefixes, dual-purpose COMMENTs, governed tags |

Enforces enterprise naming conventions across every artifact:

- **Table naming:** `snake_case` with `dim_`, `fact_`, `bridge_` prefixes
- **Column naming:** `snake_case`, approved abbreviations (`_id`, `_ts`, `_amt`)
- **Comments:** Dual-purpose format (business + technical/LLM) for tables, columns, TVFs, metric views
- **Tags:** `domain`, `layer`, `data_classification`, `pii`, `cost_center`
- **Workflows:** Job names with `{project}-{domain}-{action}` pattern
- **Budget policies:** Serverless budget policy tags

---

### 5. databricks-python-imports

| Field | Value |
|-------|-------|
| **Path** | `data_product_accelerator/skills/common/databricks-python-imports/SKILL.md` |
| **Read When** | Sharing code between notebooks |
| **Key Pattern** | `sys.path` setup for Asset Bundle paths, `restartPython()` patterns |

Enables code reuse across Databricks notebooks using pure Python files and standard imports. Covers:

- Asset Bundle path setup (`/Workspace/{bundle_root}/src/`)
- Notebook-to-module conversion patterns
- Import patterns vs `%run` magic commands
- Troubleshooting `ModuleNotFoundError` after `restartPython()`

---

### 6. databricks-table-properties

| Field | Value |
|-------|-------|
| **Path** | `data_product_accelerator/skills/common/databricks-table-properties/SKILL.md` |
| **Read When** | Creating tables at any medallion layer |
| **Key Patterns** | TBLPROPERTIES by layer, CDF, auto-optimize, CLUSTER BY AUTO |

Standardizes Delta table properties across all medallion layers:

- **Bronze:** `delta.enableChangeDataFeed`, `layer=bronze`, `source_system`, `domain`
- **Silver (DLT):** `quality=silver`, CDF, row tracking, deletion vectors, auto-compact, auto-optimize
- **Gold:** PK/FK constraints, rich LLM-friendly comments, domain and classification tags
- **All layers:** `CLUSTER BY AUTO` (automatic liquid clustering)

---

### 7. schema-management-patterns

| Field | Value |
|-------|-------|
| **Path** | `data_product_accelerator/skills/common/schema-management-patterns/SKILL.md` |
| **Read When** | Creating schemas, enabling predictive optimization |
| **Key Pattern** | `CREATE SCHEMA IF NOT EXISTS` + predictive optimization |

Provides patterns for Unity Catalog schema creation and management:

- Programmatic schema creation with `CREATE SCHEMA IF NOT EXISTS`
- Predictive Optimization enablement at schema or catalog level
- Schema-level properties and comments
- `ALTER SCHEMA` for enabling optimization

---

### 8. unity-catalog-constraints

| Field | Value |
|-------|-------|
| **Path** | `data_product_accelerator/skills/common/unity-catalog-constraints/SKILL.md` |
| **Read When** | Applying PK/FK constraints in Gold layer |
| **Key Patterns** | Surrogate keys as PK, `ALTER TABLE` after creation, `NOT ENFORCED` |

Defines the correct patterns for Unity Catalog relational constraints:

- Surrogate keys (not business keys) as PRIMARY KEYS
- Facts reference surrogate PKs via FOREIGN KEY
- `NOT NULL` requirement for PK columns
- Constraints applied via `ALTER TABLE` *after* table creation and data loading
- Never define FK inline in `CREATE TABLE` statement
- DATE type casting considerations (`DATE_TRUNC` returns `DATE`)
- Widget parameter naming consistency

## Common Skills Usage Matrix

Shows which common skills each orchestrator depends on:

| Orchestrator | Expert Agent | Asset Bundles | Auto Ops | Naming | Python Imports | Table Props | Schema Mgmt | UC Constraints |
|-------------|:-----------:|:------------:|:-------:|:------:|:-------------:|:-----------:|:-----------:|:--------------:|
| Gold Design | x | | | x | | | | |
| Bronze Setup | x | x | x | x | | x | x | |
| Silver Setup | x | x | x | x | x | x | x | x |
| Gold Impl | x | x | x | x | x | x | x | x |
| Planning | x | | | x | | | | |
| Semantic | x | x | x | x | x | | | |
| Observability | x | x | x | x | x | | | |
| ML Pipeline | x | x | x | x | x | x | | |
| GenAI Agents | x | x | x | x | x | | | |

## References

- [AGENTS.md](../../AGENTS.md) — Universal entry point with common skills index
- [04-Agent Skills System](04-agent-skills-system.md) — Skills architecture
- [05-Skill Domains](05-skill-domains.md) — Complete skill inventory
