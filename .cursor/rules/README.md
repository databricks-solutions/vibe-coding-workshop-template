# Cursor Rules - Databricks Medallion Architecture Framework

## 📂 Organized by Layer

Cursor rules are now organized into logical folders for easier navigation:

```
.cursor/rules/
├── 00_TABLE_OF_CONTENTS.md          # Complete guide with learning paths
├── README.md                         # This file
├── common/                           # Foundation & infrastructure (9 rules)
│   ├── 01-databricks-expert-agent.mdc
│   ├── 02-databricks-asset-bundles.mdc
│   ├── 03-schema-management-patterns.mdc
│   ├── 04-databricks-table-properties.mdc
│   ├── 05-unity-catalog-constraints.mdc
│   ├── 09-databricks-python-imports.mdc
│   ├── 20-cursor-rules.mdc
│   ├── 21-self-improvement.mdc
│   └── 22-documentation-organization.mdc
├── bronze/                           # Bronze layer patterns (1 rule)
│   └── 06-faker-data-generation.mdc
├── silver/                           # Silver layer patterns (2 rules)
│   ├── 07-dlt-expectations-patterns.mdc
│   └── 08-dqx-patterns.mdc
├── gold/                             # Gold layer patterns (7 rules)
│   ├── 10-gold-layer-merge-patterns.mdc
│   ├── 11-gold-delta-merge-deduplication.mdc
│   ├── 12-gold-layer-documentation.mdc
│   ├── 13-mermaid-erd-patterns.mdc
│   ├── 23-gold-layer-schema-validation.mdc
│   ├── 24-fact-table-grain-validation.mdc
│   └── 25-yaml-driven-gold-setup.mdc
├── semantic-layer/                   # Semantic layer patterns (3 rules)
│   ├── 14-metric-views-patterns.mdc
│   ├── 15-databricks-table-valued-functions.mdc
│   └── 16-genie-space-patterns.mdc
├── monitoring/                       # Observability & BI (2 rules)
│   ├── 17-lakehouse-monitoring-comprehensive.mdc
│   └── 18-databricks-aibi-dashboards.mdc
├── exploration/                      # Ad-hoc analysis (1 rule)
│   └── 22-adhoc-exploration-notebooks.mdc
└── planning/                         # Project planning (1 rule)
    └── 26-project-plan-methodology.mdc
```

---

## 🚀 Quick Start

### Step 1: Read the Guide
📖 **[00_TABLE_OF_CONTENTS.md](./00_TABLE_OF_CONTENTS.md)** - Complete framework guide with:
- Sequential learning paths (Rapid Prototyping, Production, Data Quality Focus, Semantic Layer)
- Complexity levels (Foundation, Intermediate, Advanced)
- Cross-references between related rules
- Certification checklists

### Step 2: Choose Your Path

**Rapid Prototyping (8 hours):**
```
common/ (foundations) → bronze/ → silver/ → gold/
```

**Production Implementation (4 weeks):**
```
Week 1: common/ → bronze/ → silver/
Week 2: gold/
Week 3: semantic-layer/
Week 4: monitoring/ → exploration/
```

**Data Quality Focus (2 weeks):**
```
common/ → bronze/ (with DQ) → silver/ (DLT + DQX) → monitoring/
```

### Step 3: Apply Rules Sequentially
Each folder contains rules that build on previous folders. Follow the numbering within each folder.

---

## 📊 Statistics

| Category | Rules | Lines | Focus |
|----------|-------|-------|-------|
| **common/** | 9 | ~3,000 | Foundation & infrastructure |
| **bronze/** | 1 | ~350 | Raw data ingestion |
| **silver/** | 2 | ~1,200 | Data quality & validation |
| **gold/** | 7 | ~2,800 | Analytics-ready models |
| **semantic-layer/** | 3 | ~1,800 | Natural language & BI |
| **monitoring/** | 2 | ~1,450 | Observability & dashboards |
| **exploration/** | 1 | ~800 | Ad-hoc analysis |
| **planning/** | 1 | ~900 | Project methodology |
| **Total** | **26 rules** | **~12,300** | Complete framework |

---

## 🎯 Rule Categories Explained

### common/ - Foundations (Read First!)
Core principles and patterns that apply across all layers:
- Architecture & governance principles
- Asset Bundles (IaC for Databricks)
- Unity Catalog schema management
- Table properties standards
- PK/FK constraints
- Python code sharing
- Meta rules (cursor rules, self-improvement, documentation)

**When to read**: Before starting any implementation

---

### bronze/ - Raw Data Ingestion
Patterns for landing raw data with minimal transformation:
- Faker data generation (for testing/demos)
- Unity Catalog compliance
- Change Data Feed enablement

**When to read**: When creating Bronze layer

---

### silver/ - Data Quality Layer
Validated, cleansed data with comprehensive quality checks:
- DLT expectations with Delta table-based rules
- DQX integration for advanced diagnostics
- Quarantine patterns
- Never-fail pipelines

**When to read**: After Bronze layer is complete

---

### gold/ - Analytics-Ready Layer
Business-focused dimensional models:
- ERD design with Mermaid
- YAML-driven table creation (single source of truth)
- Schema and grain validation
- MERGE patterns (SCD Type 1 & 2)
- Deduplication strategies
- Comprehensive documentation

**When to read**: After Silver layer is deployed

---

### semantic-layer/ - Business Intelligence
Natural language queries and business metrics:
- Metric Views (semantic layer for Genie)
- Table-Valued Functions (pre-built queries)
- Genie Space setup (natural language interface)

**When to read**: After Gold layer is complete

---

### monitoring/ - Observability
Automated monitoring and visualization:
- Lakehouse Monitoring (custom metrics, drift detection)
- AI/BI Lakeview Dashboards

**When to read**: After Gold layer is deployed

---

### exploration/ - Development Tools
Ad-hoc analysis and exploration:
- Dual-format notebooks (Databricks + Jupyter)
- Standard helper functions

**When to read**: When creating exploration utilities

---

### planning/ - Project Methodology
Multi-phase project design:
- 5-phase structure (Bronze → Frontend)
- Agent Domain Framework
- Artifact organization

**When to read**: When planning comprehensive data platform solutions

---

## 🔍 Finding the Right Rule

### By Task
- **Starting a new project?** → `common/01-databricks-expert-agent.mdc`
- **Setting up deployment?** → `common/02-databricks-asset-bundles.mdc`
- **Creating tables?** → `common/04-databricks-table-properties.mdc`
- **Generating test data?** → `bronze/06-faker-data-generation.mdc`
- **Adding data quality?** → `silver/07-dlt-expectations-patterns.mdc`
- **Designing Gold schema?** → `gold/13-mermaid-erd-patterns.mdc`
- **Creating Gold tables?** → `gold/25-yaml-driven-gold-setup.mdc`
- **Merging to Gold?** → `gold/10-gold-layer-merge-patterns.mdc`
- **Creating metrics?** → `semantic-layer/14-metric-views-patterns.mdc`
- **Setting up Genie?** → `semantic-layer/16-genie-space-patterns.mdc`
- **Adding monitoring?** → `monitoring/17-lakehouse-monitoring-comprehensive.mdc`
- **Building dashboards?** → `monitoring/18-databricks-aibi-dashboards.mdc`

### By Problem
- **Duplicate keys in MERGE?** → `gold/11-gold-delta-merge-deduplication.mdc`
- **Schema mismatches?** → `gold/23-gold-layer-schema-validation.mdc`
- **Wrong fact grain?** → `gold/24-fact-table-grain-validation.mdc`
- **Import issues?** → `common/09-databricks-python-imports.mdc`
- **DQX API errors?** → `silver/08-dqx-patterns.mdc`
- **Monitoring metrics not showing?** → `monitoring/17-lakehouse-monitoring-comprehensive.mdc`

---

## 📖 Documentation Standards

All rules follow consistent format:
- **Pattern Recognition** - When to use this rule
- **Benefits** - Why this pattern matters
- **Implementation** - Step-by-step examples
- **Validation Checklist** - Ensure correctness
- **Common Mistakes** - What to avoid
- **References** - Official documentation links

---

## 🔄 Continuous Improvement

Rules are continuously updated based on:
- Official Databricks documentation changes
- Real-world implementation learnings
- Community feedback
- New platform features

See `common/21-self-improvement.mdc` for the improvement methodology.

---

## 🎓 Certification

Complete learning paths and earn certifications:
- ✅ Bronze Layer Certified (Chapters 1-7)
- ✅ Silver Layer Certified (Chapters 8-9)
- ✅ Gold Layer Certified (Chapters 10-16)
- ✅ Semantic Layer Certified (Chapters 17-19, 21)
- ✅ Production Ready (All + Monitoring)

See [00_TABLE_OF_CONTENTS.md](./00_TABLE_OF_CONTENTS.md) for full certification checklists.

---

## 🚦 Using Rules with AI Assistants

These rules are designed to work with AI coding assistants (Cursor, GitHub Copilot, etc.):

1. **Reference specific rules** in your prompts:
   ```
   "Follow gold/25-yaml-driven-gold-setup.mdc to create tables from YAML"
   ```

2. **Use folder context**:
   ```
   "Apply common/ foundation patterns for Unity Catalog setup"
   ```

3. **Sequential implementation**:
   ```
   "Implement Bronze (bronze/), then Silver (silver/), then Gold (gold/)"
   ```

---

## 📚 External Resources

- [Databricks Documentation](https://docs.databricks.com/)
- [Unity Catalog](https://docs.databricks.com/unity-catalog/)
- [Delta Lake](https://docs.databricks.com/delta/)
- [DLT Expectations](https://docs.databricks.com/dlt/expectations)
- [Metric Views](https://docs.databricks.com/metric-views/)

---

## 📞 Support

- **Issues**: Check `common/21-self-improvement.mdc` for rule improvement workflow
- **Updates**: See recent improvements in `00_TABLE_OF_CONTENTS.md`
- **Documentation**: All rules have inline documentation and examples

---

**Version**: December 2025  
**Total Rules**: 26  
**Total Lines**: ~12,300  
**Organization**: Layer-based folders (NEW!)

**Remember**: These rules represent a complete, production-tested methodology for building Databricks data products. Follow sequentially, validate with checklists, and build iteratively.

🚀 **Happy Building!**
