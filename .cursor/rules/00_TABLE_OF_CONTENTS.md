# Cursor Rules: End-to-End Data Product Guide
## A Comprehensive Framework for Building Production Databricks Solutions

---

## 📖 About This Guide

This collection of cursor rules represents a **complete, sequential guide** to building production-grade data products on Databricks. Each rule is a chapter in your journey from foundation to advanced implementation.

Think of this as your **comprehensive playbook** - organized like a professional book that takes you from basic principles to sophisticated data product capabilities.

**✨ NEW: Organized by Layer** - Rules are now organized into folders (common, bronze, silver, gold, semantic-layer, monitoring, exploration, planning) for easier navigation.

---

## 🎯 How to Use This Guide

### For New Team Members
Read **PART I (Foundations)** completely before writing any code. Then progress through parts II-IV as you implement each layer.

### For Experienced Developers
Use this as a **reference manual** - jump to specific chapters when implementing features. Always validate against checklists.

### For Architects
Review **PART I** for principles, then use **PART V** to design and orchestrate complete solutions.

---

## 📚 Table of Contents

### **PART I: FOUNDATIONS (common/)** 
*Core principles and architectural patterns that govern everything*

#### **Chapter 1: Architecture & Principles** → `common/01-databricks-expert-agent.mdc`
**What you'll learn**: The non-negotiable principles of production Databricks solutions
- Unity Catalog governance
- Delta Lake + Medallion architecture
- Data quality by design
- Performance & cost optimization
- Modern platform features

**When to read**: Before starting any project
**Lines**: 272 | **Complexity**: Foundation

---

#### **Chapter 2: Platform Infrastructure** → `common/02-databricks-asset-bundles.mdc`
**What you'll learn**: Infrastructure-as-Code for Databricks workflows and pipelines
- Main bundle configuration (databricks.yml)
- Serverless job patterns
- DLT pipeline configurations
- Multi-task jobs with dependencies
- Orchestrator patterns (setup & refresh)
- Schema management as code

**When to read**: When setting up deployment infrastructure
**Lines**: 1200+ | **Complexity**: Foundation
**Key Concepts**: Serverless-first, orchestrators, root_path, pipeline tasks

---

#### **Chapter 3: Unity Catalog Schemas** → `common/03-schema-management-patterns.mdc`
**What you'll learn**: Programmatic schema management patterns
- CREATE SCHEMA IF NOT EXISTS patterns
- Schema variable usage
- Idempotent schema creation
- ⚠️ **DEPRECATED**: resources/schemas.yml pattern (no longer used)

**When to read**: Before creating any tables
**Lines**: 150+ | **Complexity**: Foundation
**Key Concepts**: Programmatic creation, schema variables, idempotent operations

---

#### **Chapter 4: Table Properties Standards** → `common/04-databricks-table-properties.mdc`
**What you'll learn**: Consistent metadata and properties for all tables
- Required TBLPROPERTIES by layer
- CLUSTER BY AUTO (automatic liquid clustering)
- Table and column comment standards
- Domain and classification values
- Governance metadata

**When to read**: Before creating any table in any layer
**Lines**: 258 | **Complexity**: Foundation
**Key Concepts**: CLUSTER BY AUTO, dual-purpose documentation, governance tags

---

#### **Chapter 5: Unity Catalog Constraints** → `common/05-unity-catalog-constraints.mdc`
**What you'll learn**: Primary key and foreign key relationship modeling
- PK/FK constraint patterns
- NOT ENFORCED syntax
- Relational modeling in Delta Lake
- Constraint benefits (lineage, optimization, documentation)

**When to read**: When designing Gold layer schemas
**Lines**: 150+ | **Complexity**: Foundation

---

#### **Chapter 6: Python Code Sharing** → `common/09-databricks-python-imports.mdc`
**What you'll learn**: Sharing code between Databricks notebooks
- Pure Python files (.py) vs Databricks notebooks
- Standard Python imports (not %run)
- DLT imports and helper modules
- sys.path considerations

**When to read**: When creating shared utilities or DLT helpers
**Lines**: 410+ | **Complexity**: Foundation
**Key Concepts**: Pure Python, NO notebook header, standard imports

---

### **PART II: BRONZE LAYER - RAW DATA INGESTION (bronze/)**
*Landing zone for raw data with minimal transformation*

#### **Chapter 7: Faker Data Generation** → `bronze/06-faker-data-generation.mdc`
**What you'll learn**: Generating realistic test data for prototyping
- Faker library patterns for dimensions and facts
- Referential integrity (FK integrity in generated data)
- Reproducible seeded data
- Data quality corruption for testing DQ rules

**When to read**: When creating test/demo Bronze data
**Lines**: 350+ | **Complexity**: Intermediate
**Key Concepts**: Seeded generation, FK integrity, DQ testing

---

### **PART III: SILVER LAYER - VALIDATED DATA (silver/)**
*Data quality layer with cleansing and validation*

#### **Chapter 8: DLT Expectations (Delta Table-Based)** → `silver/07-dlt-expectations-patterns.mdc`
**What you'll learn**: Data quality rules stored in Delta tables
- Delta table for DQ rules storage
- Rules loader module (pure Python)
- @dlt.expect_all_or_drop() patterns
- Severity-based rules (critical vs warning)
- Quarantine patterns
- Direct Publishing Mode

**When to read**: When creating Silver DLT pipelines
**Lines**: 800+ | **Complexity**: Intermediate
**Key Concepts**: Delta table rules, runtime updates, never fails, quarantine

**Official Reference**: [Portable and Reusable Expectations](https://docs.databricks.com/aws/en/ldp/expectation-patterns#portable-and-reusable-expectations)

---

#### **Chapter 9: DQX Integration (Advanced Quality)** → `silver/08-dqx-patterns.mdc`
**What you'll learn**: Databricks Labs DQX for advanced data quality
- DQX vs DLT expectations comparison
- Hybrid approach (DLT + DQX)
- Auto-profiling for rule generation
- Detailed failure diagnostics
- Gold pre-merge validation
- YAML and Delta storage for rules

**When to read**: When needing advanced quality diagnostics
**Lines**: 410+ | **Complexity**: Advanced
**Key Concepts**: Hybrid approach, detailed diagnostics, auto-profiling

---

### **PART IV: GOLD LAYER - ANALYTICS-READY (gold/)**
*Business-focused dimensional models and aggregations*

#### **Chapter 10: Gold Layer Design** → `gold/13-mermaid-erd-patterns.mdc`
**What you'll learn**: Creating ERD diagrams for Gold layer
- Mermaid ERD syntax
- Dimension and fact representation
- Relationship visualization
- Clean professional diagrams

**When to read**: When designing Gold layer schema (before implementation)
**Lines**: 300+ | **Complexity**: Intermediate
**Key Concepts**: ERD-first, visual design, stakeholder approval

---

#### **Chapter 11: YAML-Driven Setup** → `gold/25-yaml-driven-gold-setup.mdc`
**What you'll learn**: Creating tables dynamically from YAML schemas
- YAML as single source of truth
- Generic setup script for all tables
- Runtime YAML discovery
- Schema change = YAML edit only
- Asset Bundle integration

**When to read**: When implementing Gold table creation
**Lines**: 518 | **Complexity**: Intermediate
**Key Concepts**: YAML-driven, single script, 94% code reduction

---

#### **Chapter 12: Schema Validation** → `gold/23-gold-layer-schema-validation.mdc`
**What you'll learn**: Preventing DDL vs YAML mismatches
- Pre-merge schema validation
- Explicit column mapping patterns
- DataFrame vs DDL comparison
- DDL as runtime truth

**When to read**: Before deploying Gold merge scripts
**Lines**: 565 | **Complexity**: Intermediate
**Key Concepts**: Schema validation, explicit mapping, DDL truth

---

#### **Chapter 13: Fact Table Grain** → `gold/24-fact-table-grain-validation.mdc`
**What you'll learn**: Validating fact table grain from DDL
- Grain inference from PRIMARY KEY
- Transaction vs aggregated patterns
- Preventing incorrect grain
- Grain documentation standards

**When to read**: When creating fact tables
**Lines**: 350+ | **Complexity**: Intermediate
**Key Concepts**: Grain validation, PRIMARY KEY inference

---

#### **Chapter 14: MERGE Patterns** → `gold/10-gold-layer-merge-patterns.mdc`
**What you'll learn**: Silver → Gold merge operations
- Column name mapping
- Variable naming (avoid PySpark conflicts)
- SCD Type 1 (overwrite)
- SCD Type 2 (history tracking)
- Fact table aggregation

**When to read**: When implementing Gold merge scripts
**Lines**: 314 | **Complexity**: Intermediate
**Key Concepts**: Explicit mapping, SCD patterns, aggregation

---

#### **Chapter 15: MERGE Deduplication** → `gold/11-gold-delta-merge-deduplication.mdc`
**What you'll learn**: Preventing duplicate key errors in MERGE
- Window function deduplication
- Latest record selection
- Business key vs surrogate key
- Error prevention patterns

**When to read**: When MERGE operations fail with duplicate keys
**Lines**: 250+ | **Complexity**: Intermediate
**Key Concepts**: Deduplication before MERGE, window functions

---

#### **Chapter 16: Gold Documentation** → `gold/12-gold-layer-documentation.mdc`
**What you'll learn**: Dual-purpose documentation standards
- Business + Technical descriptions
- Column comment patterns
- Table grain documentation
- LLM-friendly without "LLM:" prefix

**When to read**: When creating Gold tables
**Lines**: 586 | **Complexity**: Intermediate
**Key Concepts**: Dual-purpose, comprehensive, stakeholder-friendly

---

### **PART V: SEMANTIC LAYER - BUSINESS INTELLIGENCE (semantic-layer/)**
*Natural language queries and business metrics*

#### **Chapter 17: Metric Views** → `semantic-layer/14-metric-views-patterns.mdc`
**What you'll learn**: Creating semantic layer for Genie and BI
- YAML v1.1 specification
- `WITH METRICS LANGUAGE YAML` syntax
- Dimensions, measures, joins
- Format specifications
- Synonyms for LLM

**When to read**: After Gold layer is complete
**Lines**: 650+ | **Complexity**: Intermediate
**Key Concepts**: v1.1, source prefix, format specs, runtime updates

---

#### **Chapter 18: Table-Valued Functions** → `semantic-layer/15-databricks-table-valued-functions.mdc`
**What you'll learn**: Pre-built SQL queries for Genie
- TVF syntax and patterns
- Parameter typing (critical!)
- Top N, trending, comparison patterns
- Genie-optimized queries

**When to read**: After Metric Views are created
**Lines**: 371 | **Complexity**: Intermediate
**Key Concepts**: Typed parameters, RETURNS TABLE, business patterns

---

#### **Chapter 19: Genie Space Setup** → `semantic-layer/16-genie-space-patterns.mdc`
**What you'll learn**: Natural language query interface
- Trusted assets configuration
- Agent instructions (comprehensive)
- Benchmark questions
- Testing and validation

**When to read**: After Metric Views and TVFs are complete
**Lines**: 798 | **Complexity**: Intermediate
**Key Concepts**: Natural language, trusted assets, agent instructions

---

### **PART VI: MONITORING & VISUALIZATION (monitoring/)**
*Observability and business dashboards*

#### **Chapter 20: Lakehouse Monitoring** → `monitoring/17-lakehouse-monitoring-comprehensive.mdc`
**What you'll learn**: Automated data quality and drift monitoring
- Custom metrics (AGGREGATE, DERIVED, DRIFT)
- Profile metrics table structure
- input_columns patterns (critical!)
- Async refresh patterns
- Query patterns for metrics

**When to read**: After Gold layer is deployed
**Lines**: 850+ | **Complexity**: Advanced
**Key Concepts**: Custom metrics, input_columns, async wait, table-level metrics

---

#### **Chapter 21: AI/BI Dashboards** → `monitoring/18-databricks-aibi-dashboards.mdc`
**What you'll learn**: Creating Lakeview visual dashboards
- Dashboard layout patterns
- Counter tiles, charts, tables
- MEASURE() function for Metric Views
- Global filters
- Auto-refresh configuration

**When to read**: After Metric Views are created
**Lines**: 600+ | **Complexity**: Intermediate
**Key Concepts**: UI-based, MEASURE(), layouts, filters

---

#### **Chapter 22: SQL Alerting Framework** → `monitoring/19-sql-alerting-patterns.mdc`
**What you'll learn**: Config-driven SQL alerting with Databricks SDK
- Alert ID convention (DOMAIN-NUMBER-SEVERITY)
- Alert rules configuration table schema
- SQL query patterns (threshold, anomaly, summary)
- Databricks SDK integration for alert deployment
- Two-job pattern (setup + deploy)
- Custom notification templates

**When to read**: After Gold layer is complete for proactive monitoring
**Lines**: 800+ | **Complexity**: Intermediate
**Key Concepts**: Config-driven, fully qualified table names, SDK deployment, dry-run validation

---

### **PART VII: DEVELOPMENT & EXPLORATION (exploration/)**
*Ad-hoc analysis and data exploration*

#### **Chapter 23: Exploration Notebooks** → `exploration/22-adhoc-exploration-notebooks.mdc`
**What you'll learn**: Dual-format notebooks for exploration
- Databricks workspace version (.py with magic commands)
- Local Jupyter version (.ipynb with Databricks Connect)
- Standard helper functions
- Environment-specific patterns

**When to read**: When creating exploration utilities
**Lines**: 800+ | **Complexity**: Intermediate
**Key Concepts**: Dual-format, magic commands, helper functions

---

### **PART VIII: PROJECT PLANNING (planning/)**
*Multi-phase project design and planning*

#### **Chapter 24: Project Plan Methodology** → `planning/26-project-plan-methodology.mdc`
**What you'll learn**: Creating comprehensive project plans
- 5-phase structure (Bronze → Gold → Use Cases → Agents → Frontend)
- Agent Domain Framework (Cost, Security, Performance, Reliability, Quality)
- Phase 3 addendums pattern (7 standard use cases)
- Enrichment methodology
- Artifact tagging and counting

**When to read**: When planning multi-phase data platform solutions
**Lines**: 900+ | **Complexity**: Advanced
**Key Concepts**: 5 phases, agent domains, 7 addendums, comprehensive planning

---

### **PART IX: META RULES (common/)**
*Rules about rules - self-improvement and documentation*

#### **Chapter 25: Cursor Rules Standards** → `common/20-cursor-rules.mdc`
**What you'll learn**: How to create and maintain cursor rules
- Rule file location (.cursor/rules/)
- Naming conventions
- Rule structure and format
- When to create new rules
- Context7 integration

**When to read**: When creating new cursor rules
**Lines**: 300+ | **Complexity**: Meta

---

#### **Chapter 26: Self-Improvement** → `common/21-self-improvement.mdc`
**What you'll learn**: Continuous improvement of cursor rules
- Triggers for rule updates
- Pattern recognition
- Rule improvement workflow
- Documentation of improvements
- Recent improvements log

**When to read**: When updating existing rules based on learnings
**Lines**: 400+ | **Complexity**: Meta

---

#### **Chapter 27: Documentation Organization** → `common/22-documentation-organization.mdc`
**What you'll learn**: Organizing project documentation
- Root directory rules (only README, QUICKSTART, CHANGELOG)
- docs/ folder structure
- Naming conventions
- Auto-cleanup patterns

**When to read**: When creating documentation files
**Lines**: 250+ | **Complexity**: Meta

---

## 📊 Statistics

### By Category
| Category | Rules | Total Lines | Avg Complexity |
|----------|-------|-------------|----------------|
| **Common (Foundations)** | 9 | ~3,000 | Foundation |
| **Bronze** | 1 | ~350 | Intermediate |
| **Silver** | 2 | ~1,200 | Intermediate-Advanced |
| **Gold** | 7 | ~2,800 | Intermediate |
| **Semantic Layer** | 3 | ~1,800 | Intermediate |
| **Monitoring** | 3 | ~2,250 | Intermediate-Advanced |
| **Exploration** | 1 | ~800 | Intermediate |
| **Planning** | 1 | ~900 | Advanced |
| **Total** | **27 rules** | **~13,100 lines** | Varies |

### Complexity Levels
- **Foundation** (9 rules): Core concepts, read these first
- **Intermediate** (15 rules): Implementation patterns
- **Advanced** (2 rules): Complex integrations (DQX, Monitoring)
- **Meta** (3 rules): Self-referential rules

---

## 🗺️ Learning Paths

### Path 1: Rapid Prototyping (8 hours)
**Goal**: Get a working Medallion Architecture quickly

1. **Foundations** (1 hour): Read chapters 1-5
2. **Bronze** (1 hour): Chapter 7 - Generate test data
3. **Silver** (2 hours): Chapter 8 - DLT with Delta table rules
4. **Gold** (3 hours): Chapters 11-12 - YAML-driven setup
5. **Validation** (1 hour): Test end-to-end pipeline

**Output**: Bronze → Silver → Gold pipeline with test data

---

### Path 2: Production Implementation (4 weeks)
**Goal**: Complete production-ready data product

**Week 1: Foundation**
- Day 1-2: Chapters 1-6 (deep dive)
- Day 3: Bronze (Chapter 7)
- Day 4-5: Silver (Chapters 8-9)

**Week 2: Gold Layer**
- Day 1: Design (Chapter 10)
- Day 2-3: Implementation (Chapters 11-14)
- Day 4-5: Validation & docs (Chapters 15-16)

**Week 3: Semantic Layer**
- Day 1-2: Metric Views (Chapter 17)
- Day 3: TVFs (Chapter 18)
- Day 4-5: Genie Space (Chapter 19)

**Week 4: Monitoring & Polish**
- Day 1-2: Lakehouse Monitoring (Chapter 20)
- Day 3: AI/BI Dashboards (Chapter 21)
- Day 4-5: Exploration notebooks, testing, documentation

**Output**: Complete data product with semantic layer, monitoring, and dashboards

---

### Path 3: Data Quality Focus (2 weeks)
**Goal**: Master data quality patterns

**Week 1: Standard DQ**
- Foundation (Chapters 1-5)
- Bronze with Faker DQ corruption (Chapter 7)
- Silver DLT with Delta table rules (Chapter 8)
- Gold schema validation (Chapters 12-13)

**Week 2: Advanced DQ**
- DQX integration (Chapter 9)
- Lakehouse Monitoring with custom metrics (Chapter 20)
- Documentation and testing

**Output**: Multi-layered data quality strategy with monitoring

---

### Path 4: Semantic Layer Specialist (1 week)
**Goal**: Master natural language query capabilities

**Prerequisites**: Gold layer complete

**Day 1-2**: Metric Views (Chapter 17)
**Day 3**: Table-Valued Functions (Chapter 18)
**Day 4**: Genie Space setup (Chapter 19)
**Day 5**: AI/BI Dashboards (Chapter 21)

**Output**: Complete semantic layer with NL query capability

---

## 📖 Cross-References

### Schema Design Flow
1. Chapter 3 (Schema Management) → Chapter 4 (Table Properties) → Chapter 5 (Constraints)
2. Chapter 10 (ERD Design) → Chapter 11 (YAML Setup) → Chapter 12 (Schema Validation)

### Data Quality Flow
1. Chapter 8 (DLT Expectations) → Chapter 9 (DQX) → Chapter 20 (Monitoring)
2. Chapter 7 (Faker with DQ corruption) → Chapter 8 (Silver DQ rules)
3. Chapter 20 (Monitoring) → Chapter 22 (SQL Alerting) for proactive notifications

### Gold Layer Complete Flow
1. Chapter 10 (ERD Design)
2. Chapter 11 (YAML-Driven Setup)
3. Chapter 12 (Schema Validation)
4. Chapter 13 (Grain Validation)
5. Chapter 14 (MERGE Patterns)
6. Chapter 15 (Deduplication)
7. Chapter 16 (Documentation)

### Semantic Layer Complete Flow
1. Chapter 17 (Metric Views)
2. Chapter 18 (TVFs)
3. Chapter 19 (Genie Space)
4. Chapter 21 (AI/BI Dashboards)

---

## 🎓 Certification Checklist

### Bronze Layer Certified
- [ ] Read Chapters 1-7
- [ ] Created Bronze tables with governance metadata
- [ ] Enabled Change Data Feed
- [ ] Generated test data with Faker
- [ ] Verified FK integrity

### Silver Layer Certified
- [ ] Read Chapters 8-9
- [ ] Created dq_rules Delta table
- [ ] Implemented DLT pipeline with Delta table-based rules
- [ ] Created quarantine tables
- [ ] Validated data quality metrics

### Gold Layer Certified
- [ ] Read Chapters 10-16
- [ ] Created ERD diagrams
- [ ] YAML schemas for all tables
- [ ] Implemented YAML-driven setup
- [ ] Schema and grain validation
- [ ] SCD Type 1 and Type 2 patterns
- [ ] Comprehensive documentation

### Semantic Layer Certified
- [ ] Read Chapters 17-19, 21
- [ ] Created Metric Views (v1.1)
- [ ] Implemented 10+ TVFs
- [ ] Configured Genie Space
- [ ] Built AI/BI dashboards

### Production Ready
- [ ] All layers certified
- [ ] Lakehouse Monitoring configured (Chapter 20)
- [ ] SQL Alerting deployed (Chapter 22)
- [ ] Exploration notebooks created (Chapter 23)
- [ ] Complete documentation
- [ ] Asset Bundles deployment (Chapter 2)

---

## 🔄 Continuous Improvement

This guide evolves based on:
- Official Databricks documentation updates
- Real-world implementation learnings
- Community feedback
- New platform features

**Last Major Update**: December 2025
- Added folder organization (common, bronze, silver, gold, semantic-layer, monitoring, exploration, planning)
- Updated all cross-references
- Added learning paths
- Enhanced statistics

See Chapter 26 (Self-Improvement) for the improvement methodology.

---

## 📚 External References

- [Official Databricks Documentation](https://docs.databricks.com/)
- [Unity Catalog](https://docs.databricks.com/unity-catalog/)
- [Delta Lake](https://docs.databricks.com/delta/)
- [DLT Expectations](https://docs.databricks.com/dlt/expectations)
- [Metric Views](https://docs.databricks.com/metric-views/)
- [Lakehouse Monitoring](https://docs.databricks.com/lakehouse-monitoring/)

---

**Remember**: This is not just a set of rules - it's a **complete methodology** for building production data products. Follow the learning paths, validate with checklists, and build iteratively.

**Happy Building! 🚀**
