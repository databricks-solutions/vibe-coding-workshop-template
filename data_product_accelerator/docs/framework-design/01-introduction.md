# 01 — Introduction

## Purpose

The Data Product Accelerator exists to solve a fundamental challenge in data platform development: building production-grade Databricks Lakehouse solutions requires deep expertise across dozens of platform features — Unity Catalog governance, Delta Medallion Architecture, DLT expectations, Genie Spaces, Lakehouse Monitoring, MLflow, GenAI agents — and getting every pattern right takes weeks of learning and iteration.

This framework encodes that expertise as **Agent Skills** — structured knowledge packages that an AI coding assistant reads and follows — enabling a developer to go from a raw schema CSV to a production-ready data platform (with semantic layer, observability, ML pipelines, and GenAI agents) in 20-30 hours instead of 80-120.

The architecture is **skills-first**: instead of embedding patterns in cursor rules (which are limited by IDE context windows), the framework uses lightweight routing rules that point to rich, progressively-disclosed Agent Skills. This design allows unlimited growth while keeping any single interaction within Claude Opus's 200K token budget.

## Scope

### In Scope

- Design-First pipeline methodology (9 stages from schema CSV to GenAI agents)
- Agent Skill architecture (orchestrator/worker pattern, progressive disclosure)
- Complete Medallion Architecture (Bronze → Silver → Gold) with governance
- Semantic layer (Metric Views, Table-Valued Functions, Genie Spaces)
- Observability (Lakehouse Monitoring, AI/BI Dashboards, SQL Alerts)
- ML pipelines (MLflow experiments, Feature Store, batch inference)
- GenAI agents (ResponsesAgent, multi-agent orchestration, evaluation, deployment)
- Project planning methodology with YAML manifest contracts
- Autonomous operations (deploy-poll-diagnose-fix-redeploy loop)
- Enterprise naming, commenting, and tagging standards

### Out of Scope

- Specific customer implementations or domain-specific business logic
- Databricks workspace provisioning and cloud infrastructure setup
- Network security, VPC configuration, or compliance certifications
- Real-time streaming beyond DLT (e.g., Kafka, Kinesis direct ingestion)
- Non-Databricks data platforms or multi-cloud orchestration

## Prerequisites

### Required Infrastructure

| Requirement | Specification |
|-------------|---------------|
| Databricks Workspace | Any cloud (AWS, Azure, GCP) with Unity Catalog enabled |
| SQL Warehouse | Serverless recommended for cost efficiency |
| Databricks CLI | v0.200+ installed and configured |
| Cursor IDE | Latest version with Agent mode enabled |
| Git | Version control for all artifacts |

### Required Permissions

| Permission | Scope | Purpose |
|------------|-------|---------|
| `CREATE CATALOG` / `CREATE SCHEMA` | Workspace | Create medallion layer schemas |
| `CREATE TABLE` / `ALTER TABLE` | Schema | Create and modify Delta tables |
| `CREATE FUNCTION` | Schema | Create TVFs for Genie |
| `USE CATALOG` / `USE SCHEMA` | Catalog/Schema | Access data objects |
| Workspace Admin or Jobs `CAN_MANAGE` | Workspace | Deploy Asset Bundle jobs |
| Model Serving permissions | Workspace | Deploy GenAI agents (stage 9) |

### Knowledge Prerequisites

| Area | Level | Why |
|------|-------|-----|
| SQL | Intermediate | Read/write DDL, DML, and understand joins |
| Python | Basic | Understand PySpark patterns (the skills generate the code) |
| Dimensional modeling | Basic awareness | Know what facts/dimensions are (the skills teach the rest) |
| AI coding assistants | Basic | Know how to invoke Cursor Agent and reference files with `@` |

## Best Practices Matrix

| # | Best Practice | Implementation | Document |
|---|---------------|----------------|----------|
| 1 | Design-First | Design Gold target model before building Bronze/Silver layers | [03-Pipeline](03-design-first-pipeline.md) |
| 2 | Extract, Don't Generate | Script names from Gold YAML; never hardcode table/column names | [04-Agent Skills](04-agent-skills-system.md) |
| 3 | Skills-First | AGENTS.md entry point + 50 skills (not 46 monolithic rules) | [02-Architecture](02-architecture-overview.md) |
| 4 | Progressive Disclosure | SKILL.md → references/ → scripts/ → assets/ | [04-Agent Skills](04-agent-skills-system.md) |
| 5 | Orchestrator-First Routing | Always start with 00-* orchestrator, which loads workers | [04-Agent Skills](04-agent-skills-system.md) |
| 6 | Plan-as-Contract | Planning emits YAML manifests consumed downstream | [03-Pipeline](03-design-first-pipeline.md) |
| 7 | Autonomous Operations | Self-healing deploy-fix-redeploy loop | [06-Common Skills](06-common-skills.md) |
| 8 | UC Governance Everywhere | PII tags, comments, constraints, lineage on every asset | [06-Common Skills](06-common-skills.md) |

## Development Timeline

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| 1. Gold Design + Bronze + Silver | 6-10 hours | Dimensional model, ERDs, YAML schemas, Bronze tables, Silver DLT pipelines |
| 2. Gold Implementation + Planning | 4-6 hours | Gold tables, merge scripts, FK constraints, project plan with manifests |
| 3. Semantic Layer | 3-5 hours | Metric Views, TVFs, Genie Spaces |
| 4. Observability | 3-5 hours | Lakehouse Monitors, AI/BI Dashboards, SQL Alerts |
| 5. ML + GenAI (optional) | 8-16 hours | ML experiments, models, inference, GenAI agents |
| **Total (core)** | **16-26 hours** | Complete data platform with semantic layer and monitoring |
| **Total (with ML/GenAI)** | **24-42 hours** | Full stack including ML and GenAI agents |

## Success Criteria

| Criteria | Target | Measurement |
|----------|--------|-------------|
| Medallion Architecture | Complete Bronze → Silver → Gold pipeline | All layers deployed and data flowing |
| Governance Compliance | 100% of tables with comments, tags, constraints | Audit via naming-tagging-standards checklist |
| Data Quality | DLT expectations on every Silver table | DQ rules stored in Unity Catalog Delta table |
| Semantic Layer | Genie can answer natural language queries | Benchmark questions pass at 95%+ accuracy |
| Observability | Monitors on all Gold tables | Custom business metrics reporting in dashboards |
| Deployment Automation | All resources in Asset Bundles | `databricks bundle deploy -t dev` succeeds |

## Document Conventions

### Skill References

Skills are referenced using their domain path: `data_product_accelerator/skills/{domain}/{skill-name}/SKILL.md`. In the Cursor IDE, use the `@` syntax to reference them directly (e.g., `@data_product_accelerator/skills/gold/00-gold-layer-design/SKILL.md`).

### Diagrams

Architecture and data flow diagrams use Mermaid syntax or ASCII art for portability. ERD diagrams follow the patterns defined in the `gold/08-mermaid-erd-patterns` skill.

### Configuration

All parameterized values use `{placeholder}` syntax. Environment-specific values (catalog names, schema names, workspace URLs) are passed via Asset Bundle parameters or `dbutils.widgets.get()`.

## Next Steps

1. **Read [02-Architecture Overview](02-architecture-overview.md)** to understand the skills-first system design
2. **Review [03-Design-First Pipeline](03-design-first-pipeline.md)** for the 9-stage workflow
3. **Follow [07-Implementation Guide](07-implementation-guide.md)** for step-by-step instructions
