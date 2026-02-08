# Databricks Solution Compliance Checklist

Use this checklist to validate that your Databricks solution follows production-grade best practices before deployment.

## Schema Extraction (CRITICAL)

- [ ] ✅ Table names extracted from Gold YAML (not generated)
- [ ] ✅ Column names extracted from Gold YAML/metadata (not hardcoded)
- [ ] ✅ Column types validated against Gold YAML
- [ ] ✅ Primary/foreign keys extracted from Gold YAML
- [ ] ✅ Metric view names extracted from YAML filenames
- [ ] ✅ TVF names/signatures extracted from SQL files
- [ ] ✅ No hardcoded lists of tables, columns, or functions
- [ ] ✅ Schema validation scripts run before deployment

## Databricks Best Practices

### Unity Catalog & Governance
- [ ] UC-managed tables with lineage and auto liquid clustering
- [ ] Predictive Optimization enabled
- [ ] Table and column comments present
- [ ] Tags applied (layer, domain, source_system, PII where applicable)
- [ ] Lineage tracking enabled

### Delta Lake & Medallion Architecture
- [ ] All tables stored in Delta Lake format
- [ ] Bronze → Silver → Gold layering pattern followed
- [ ] Change Data Feed (CDF) enabled for incremental propagation
- [ ] CLUSTER BY AUTO enabled on all tables

### Data Quality
- [ ] Silver layer is streaming with DLT expectations
- [ ] DLT expectations implemented with quarantine pattern
- [ ] Quality rules documented in metadata tables
- [ ] Error capture patterns implemented

### Gold Layer
- [ ] PRIMARY KEY / FOREIGN KEY constraints defined
- [ ] Mermaid ERD created for relationships
- [ ] LLM-friendly descriptions on all assets
- [ ] Lakehouse Monitoring added for critical tables
- [ ] Custom metrics defined where needed

### Semantic Layer
- [ ] UC Metric Views defined with semantic metadata in YAML
- [ ] Table-Valued Functions (TVFs) created for Genie/BI consumption
- [ ] Metric view names match YAML filenames
- [ ] TVF parameters are STRING type for Genie compatibility

### Infrastructure & Deployment
- [ ] Serverless workflows configured (no manual cluster specs)
- [ ] Asset Bundles define all resources
- [ ] Databricks Repos + CI/CD configured
- [ ] Workflows use Workflows for orchestration

### Performance & Cost
- [ ] Predictive Optimization enabled at schema/catalog level
- [ ] Automatic liquid clustering enabled
- [ ] Auto-optimize properties configured (Silver layer)
- [ ] Z-ORDER only used when workload-justified
- [ ] Photon/Serverless SQL used appropriately

### ML Workloads (if applicable)
- [ ] MLflow integration configured
- [ ] Feature Store used where appropriate
- [ ] Model Serving configured (Serverless preferred)
- [ ] Experiments use `/Shared/` paths (not `/Users/`)

## Documentation

- [ ] Design Summary created with key decisions and trade-offs
- [ ] Runbook Notes documented (deploy, rollback, observe, monitor)
- [ ] Official documentation links included for advanced features
- [ ] Code comments explain schema extraction sources
- [ ] All artifacts are parameterized and documented

## Pre-Deployment Validation

- [ ] Schema extraction scripts tested
- [ ] Column mappings validated
- [ ] Metric view source tables verified
- [ ] TVF signatures match actual SQL files
- [ ] Compliance checklist completed
- [ ] Code reviewed for hardcoded names

## Post-Deployment Verification

- [ ] Tables created with correct schemas
- [ ] Constraints applied successfully
- [ ] Metric views accessible
- [ ] TVFs execute correctly
- [ ] Monitoring dashboards functional
- [ ] Lineage visible in Unity Catalog

---

**Last Updated:** 2025-02-06  
**Version:** 1.0
