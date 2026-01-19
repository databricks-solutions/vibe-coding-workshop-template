# Cursor Rules: End-to-End Data Product Guide
## A Comprehensive Framework for Building Production Databricks Solutions

---

## 📖 About This Guide

This collection of cursor rules represents a **complete, sequential guide** to building production-grade data products on Databricks. Each rule is a chapter in your journey from foundation to advanced implementation.

Think of this as your **comprehensive playbook** - organized like a professional book that takes you from basic principles to sophisticated data product capabilities.

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

### **PART I: FOUNDATIONS** 
*Core principles and architectural patterns that govern everything*

#### **Chapter 1: Architecture & Principles** → `01-databricks-expert-agent.mdc`
**What you'll learn**: The non-negotiable principles of production Databricks solutions
- Unity Catalog governance
- Delta Lake + Medallion architecture
- Data quality by design
- Performance & cost optimization
- Modern platform features

**When to read**: Before starting any project
**Lines**: 272 | **Complexity**: Foundation

---

#### **Chapter 2: Platform Infrastructure** → `02-databricks-asset-bundles.mdc`
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

#### **Chapter 3: Unity Catalog Schemas** → `03-schema-management-patterns.mdc`
**What you'll learn**: Config-driven schema management with governance
- resources/schemas.yml patterns
- Development mode prefix behavior
- Schema variable overrides
- Schema properties and metadata
- CREATE OR REPLACE patterns

**When to read**: Before creating any tables
**Lines**: 200+ | **Complexity**: Foundation
**Key Concepts**: Dev prefixes, config-driven, idempotent operations

---

#### **Chapter 4: Table Properties Standards** → `04-databricks-table-properties.mdc`
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

#### **Chapter 5: Unity Catalog Constraints** → `05-unity-catalog-constraints.mdc`
**What you'll learn**: Primary key and foreign key relationship modeling
- PK/FK constraint patterns
- NOT ENFORCED syntax
- Relational modeling in Delta Lake
- Constraint benefits (lineage, optimization, documentation)

**When to read**: When designing Gold layer schemas
**Lines**: 150+ | **Complexity**: Foundation

---

### **PART II: BRONZE LAYER - RAW DATA INGESTION**
*Capturing data from source systems with minimal transformation*

#### **Chapter 6: Bronze Layer Patterns** → `01-databricks-expert-agent.mdc` (Bronze section)
**What you'll learn**: Raw data ingestion patterns
- Change Data Feed (CDF) enablement
- Minimal transformation philosophy
- Source system metadata
- Predictive Optimization

**When to read**: When implementing Bronze layer
**Complexity**: Basic

---

#### **Chapter 7: Test Data Generation** → `06-faker-data-generation.mdc`
**What you'll learn**: Realistic test data with configurable corruption
- Faker patterns for all entity types
- Data quality corruption for DQ testing
- Dimension and fact generation
- Configurable error injection

**When to read**: When creating Bronze data generators
**Lines**: 250+ | **Complexity**: Basic
**Key Concepts**: Faker, corruption strategies, DQ testing

---

### **PART III: SILVER LAYER - VALIDATED & CLEANSED DATA**
*Streaming data quality with comprehensive validation*

#### **Chapter 8: DLT Expectations Patterns** → `07-dlt-expectations-patterns.mdc`
**What you'll learn**: Comprehensive data quality enforcement
- DLT Direct Publishing Mode (modern pattern)
- Centralized DQ rules (data_quality_rules.py)
- Critical vs. warning expectations
- Expectation decorators (@dlt.expect_all_or_drop)
- Standard patterns by data type
- Quarantine tables (optional)

**When to read**: When implementing Silver layer DLT pipelines
**Lines**: 700+ | **Complexity**: Intermediate
**Key Concepts**: Centralized rules, critical/warning split, get_source_table()

---

#### **Chapter 9: DQX Framework (Advanced)** → `08-dqx-patterns.mdc`
**What you'll learn**: Advanced data quality with detailed diagnostics
- Databricks Labs DQX framework
- Hybrid DLT+DQX approach
- YAML and Delta storage patterns
- Gold layer pre-merge validation
- Quarantine strategies
- API compatibility and troubleshooting

**When to read**: When you need detailed DQ diagnostics beyond basic expectations
**Lines**: 900+ | **Complexity**: Advanced
**Key Concepts**: Hybrid approach, detailed diagnostics, Gold validation

---

#### **Chapter 10: Python Module Imports** → `09-databricks-python-imports.mdc`
**What you'll learn**: Sharing code between Databricks notebooks
- Pure Python file patterns
- Standard import syntax
- Notebook header removal
- When NOT to use %run magic

**When to read**: When creating shared Python modules
**Lines**: 410+ | **Complexity**: Basic
**Key Concepts**: Pure Python files, standard imports, no notebook headers

---

### **PART IV: GOLD LAYER - BUSINESS-READY ANALYTICS**
*Aggregated, documented, and monitored business assets*

#### **Chapter 11: Gold Layer Merge Patterns** → `10-gold-layer-merge-patterns.mdc`
**What you'll learn**: Schema-aware transformations from Silver to Gold
- Column name mapping patterns
- Variable naming (avoiding PySpark function conflicts)
- SCD Type 1 (overwrite) patterns
- SCD Type 2 (historical tracking) patterns
- Fact table aggregation
- Schema evolution handling

**When to read**: When implementing Gold layer merge operations
**Lines**: 350+ | **Complexity**: Intermediate
**Key Concepts**: Column mapping, SCD patterns, MERGE operations

---

#### **Chapter 12: Gold Layer Deduplication** → `11-gold-delta-merge-deduplication.mdc`
**What you'll learn**: Preventing duplicate source key errors in Gold
- Deduplication strategies before MERGE
- Window function patterns
- Handling late-arriving data
- Idempotent merge operations

**When to read**: When implementing fact table merges
**Lines**: 200+ | **Complexity**: Intermediate

---

#### **Chapter 13: Gold Layer Documentation** → `12-gold-layer-documentation.mdc`
**What you'll learn**: Comprehensive documentation standards for business users
- Dual-purpose documentation (human + LLM)
- Table comment patterns
- Column comment standards
- Business context + technical details
- Naming conventions

**When to read**: When documenting Gold layer tables
**Lines**: 300+ | **Complexity**: Basic
**Key Concepts**: Dual-purpose docs, no "LLM:" prefix in Gold

---

#### **Chapter 14: Mermaid ERD Patterns** → `13-mermaid-erd-patterns.mdc`
**What you'll learn**: Professional ERD diagrams for data modeling
- Mermaid syntax for ERDs
- Relationship patterns
- Dimension and fact table representation
- Visual documentation standards

**When to read**: When documenting Gold layer relationships
**Lines**: 150+ | **Complexity**: Basic

---

### **PART V: SEMANTIC LAYER & INTELLIGENCE**
*Making data consumable for humans and AI*

#### **Chapter 15: Metric Views** → `14-metric-views-patterns.mdc`
**What you'll learn**: Semantic layer for Genie and AI/BI
- Metric View YAML structure (v1.1)
- WITH METRICS LANGUAGE YAML syntax
- Dimension patterns (geographic, product, time)
- Measure patterns (revenue, volume, count, percentage)
- Format specifications (currency, number, percentage)
- Join patterns with SCD2 dimensions
- Synonym best practices
- Python script error handling

**When to read**: When creating semantic layer for Genie/dashboards
**Lines**: 600+ | **Complexity**: Advanced
**Key Concepts**: v1.1 spec, source. prefix, synonyms, dual-purpose comments

---

#### **Chapter 16: Table-Valued Functions** → `15-databricks-table-valued-functions.mdc`
**What you'll learn**: SQL functions optimized for Genie Spaces
- TVF syntax and patterns
- Parameter type recommendations (STRING)
- WHERE clause optimization (not LIMIT)
- Parameterization strategies
- Genie-friendly function design
- Common SQL pitfalls

**When to read**: When creating reusable SQL functions for Genie
**Lines**: 450+ | **Complexity**: Intermediate
**Key Concepts**: STRING parameters, WHERE over LIMIT, Genie optimization

---

#### **Chapter 17: Genie Space Setup** → `16-genie-space-patterns.mdc`
**What you'll learn**: Setting up Databricks Genie Spaces with comprehensive instructions
- Agent instructions (comprehensive format)
- Data asset configuration (tables, views, functions)
- Benchmark questions
- Best practices for natural language queries

**When to read**: When deploying Genie Spaces
**Lines**: 350+ | **Complexity**: Intermediate

---

### **PART VI: OBSERVABILITY & MONITORING**
*Tracking quality, drift, and business metrics over time*

#### **Chapter 18: Lakehouse Monitoring (Comprehensive)** → `17-lakehouse-monitoring-comprehensive.mdc`
**What you'll learn**: Complete guide for production monitoring on Gold layer
- **Setup & Configuration**: API-based creation, error handling, SDK compatibility, async operations, cleanup patterns
- **Custom Metrics Design**: Business-focused metrics across 5 categories (transaction, product, customer, promotional, drift)
- **Querying Metrics**: Storage patterns, query patterns for AGGREGATE/DERIVED/DRIFT, AI/BI dashboard datasets
- **Complete Examples**: End-to-end workflows with comprehensive error handling
- **Troubleshooting**: 5 common mistakes, verification workflow, validation checklist

**When to read**: When setting up monitoring on Gold tables or building monitoring dashboards
**Lines**: 1,138 | **Complexity**: Advanced
**Key Concepts**: 
- Table-level KPIs with `input_columns=[":table"]`
- Business-first metric design (5 categories)
- Metrics as table columns (no separate custom_metrics table)
- Query patterns by metric type
- Complete setup → design → query workflow

**✨ Consolidated**: Previously 3 separate rules (setup, metrics, queries) - now one comprehensive guide

---

### **PART VII: PROCESS & IMPROVEMENT**
*Maintaining quality and evolving the framework*

#### **Chapter 19: Cursor Rules Management** → `20-cursor-rules.mdc`
**What you'll learn**: How to manage and create cursor rules
- Rule file placement (.cursor/rules/)
- Naming conventions
- Rule structure and frontmatter
- Context7 integration for Databricks docs

**When to read**: When creating new rules
**Lines**: 73 | **Complexity**: Basic

---

#### **Chapter 20: Self-Improvement Process** → `21-self-improvement.mdc`
**What you'll learn**: Continuous rule improvement
- When to add new rules
- Pattern recognition triggers
- Rule update workflow
- Documentation templates
- Recent improvements log

**When to read**: When proposing rule improvements
**Lines**: 400+ | **Complexity**: Meta

---

## 🗺️ Learning Paths

### Path 1: Quick Start (Build First Product)
**Goal**: Get a basic data product running quickly
1. Chapter 1: Architecture & Principles
2. Chapter 2: Platform Infrastructure (Basics)
3. Chapter 4: Table Properties Standards
4. Chapter 6: Bronze Layer Patterns
5. Chapter 8: DLT Expectations Patterns (Basic)
6. Chapter 11: Gold Layer Merge Patterns

---

### Path 2: Complete Data Engineer
**Goal**: Master all layers and patterns
1. Read all of **PART I** (Foundations)
2. Implement Bronze (Chapters 6-7)
3. Implement Silver (Chapters 8-10)
4. Implement Gold (Chapters 11-14)
5. Add Semantic Layer (Chapters 15-17)
6. Add Monitoring (Chapter 18)

---

### Path 3: Advanced Quality Engineer
**Goal**: Become expert in data quality
1. Chapter 1: Architecture & Principles
2. Chapter 8: DLT Expectations Patterns (Complete)
3. Chapter 9: DQX Framework
4. Chapter 18: Lakehouse Monitoring (Comprehensive)
   - Covers setup, custom metrics, and query patterns

---

### Path 4: Semantic Layer Architect
**Goal**: Master AI-ready data consumption
1. Chapter 13: Gold Layer Documentation
2. Chapter 14: Mermaid ERD Patterns
3. Chapter 15: Metric Views
4. Chapter 16: Table-Valued Functions
5. Chapter 17: Genie Space Setup

---

### Path 5: Platform Architect
**Goal**: Design and orchestrate complete solutions
1. Chapter 1: Architecture & Principles (Complete)
2. Chapter 2: Platform Infrastructure (Complete)
3. Chapter 3: Unity Catalog Schemas
4. Chapter 5: Unity Catalog Constraints
5. Chapter 18: Lakehouse Monitoring (Comprehensive)

---

## 📊 Rules at a Glance

| Chapter | Rule File | Lines | Complexity | When to Use |
|---------|-----------|-------|------------|-------------|
| 1 | `01-databricks-expert-agent.mdc` | 272 | Foundation | Before any project |
| 2 | `02-databricks-asset-bundles.mdc` | 1200+ | Foundation | Setting up infrastructure |
| 3 | `03-schema-management-patterns.mdc` | 200+ | Foundation | Before creating tables |
| 4 | `04-databricks-table-properties.mdc` | 258 | Foundation | Every table creation |
| 5 | `05-unity-catalog-constraints.mdc` | 150+ | Foundation | Gold layer design |
| 6 | *(See Chapter 1 - Bronze section)* | - | Basic | Bronze implementation |
| 7 | `06-faker-data-generation.mdc` | 250+ | Basic | Test data generation |
| 8 | `07-dlt-expectations-patterns.mdc` | 700+ | Intermediate | Silver layer DLT |
| 9 | `08-dqx-patterns.mdc` | 900+ | Advanced | Advanced DQ diagnostics |
| 10 | `09-databricks-python-imports.mdc` | 410+ | Basic | Shared Python modules |
| 11 | `10-gold-layer-merge-patterns.mdc` | 350+ | Intermediate | Gold merge operations |
| 12 | `11-gold-delta-merge-deduplication.mdc` | 200+ | Intermediate | Fact table merges |
| 13 | `12-gold-layer-documentation.mdc` | 300+ | Basic | Gold documentation |
| 14 | `13-mermaid-erd-patterns.mdc` | 150+ | Basic | ERD diagrams |
| 15 | `14-metric-views-patterns.mdc` | 600+ | Advanced | Semantic layer |
| 16 | `15-databricks-table-valued-functions.mdc` | 450+ | Intermediate | SQL functions |
| 17 | `16-genie-space-patterns.mdc` | 350+ | Intermediate | Genie Spaces |
| 18 | `17-lakehouse-monitoring-comprehensive.mdc` | 1,138 | Advanced | Monitor setup+metrics+queries |
| 19 | `20-cursor-rules.mdc` | 73 | Basic | Creating rules |
| 20 | `21-self-improvement.mdc` | 400+ | Meta | Rule improvements |

**Total**: 20 Chapters | ~7,600+ Lines | 7 Complexity Levels

**Note:** Chapter 18 consolidates 3 previous rules (monitoring setup, custom metrics, query patterns) into one comprehensive guide.

---

## 🎯 Quick Decision Tree

**"Which chapter do I need right now?"**

```
Are you starting a new project?
├─ Yes → Chapter 1 (Architecture & Principles)
└─ No → Continue...

Are you setting up infrastructure?
├─ Yes → Chapter 2 (Asset Bundles) + Chapter 3 (Schemas)
└─ No → Continue...

Are you creating tables?
├─ Bronze → Chapter 4 (Table Properties) + Chapter 6 (Bronze Patterns)
├─ Silver → Chapter 8 (DLT Expectations) [+ Chapter 9 (DQX) if needed]
└─ Gold → Chapter 11 (Merge Patterns) + Chapter 13 (Documentation)

Are you building semantic layer?
├─ For Dashboards → Chapter 15 (Metric Views)
├─ For Genie → Chapter 16 (TVFs) + Chapter 17 (Genie Spaces)
└─ Both → Read all three

Do you need monitoring?
└─ Yes → Chapter 18 (Comprehensive Monitoring Guide)
         Covers: Setup, Custom Metrics, Query Patterns

Are you creating test data?
└─ Yes → Chapter 7 (Faker Data Generation)

Do you need shared Python code?
└─ Yes → Chapter 10 (Python Imports)

Are you proposing a new pattern?
└─ Yes → Chapter 20 (Self-Improvement)
```

---

## 📖 How to Read Each Chapter

Each rule file (chapter) follows this structure:

1. **Pattern Recognition** - What problem does this solve?
2. **Core Patterns** - The main implementation patterns
3. **Examples** - Real, working code examples
4. **Anti-Patterns** - Common mistakes to avoid (❌ DON'T)
5. **Validation Checklist** - Verify your implementation
6. **References** - Official Databricks documentation

**Reading Strategy**:
- First time: Read completely, try examples
- Reference use: Jump to specific pattern, check checklist
- Validation: Use checklist before committing code

---

## 🚀 Success Criteria

You've mastered this framework when you can:

✅ **Foundation**
- [ ] Explain the 7 non-negotiable principles
- [ ] Set up a complete Asset Bundle with orchestrators
- [ ] Create properly governed schemas and tables

✅ **Implementation**
- [ ] Build Bronze ingestion with proper metadata
- [ ] Implement Silver DLT with centralized DQ rules
- [ ] Create Gold layer with MERGE and SCD patterns

✅ **Intelligence**
- [ ] Design Metric Views with proper synonyms
- [ ] Create Table-Valued Functions for Genie
- [ ] Set up Genie Spaces with comprehensive instructions

✅ **Observability**
- [ ] Configure Lakehouse Monitoring with custom metrics
- [ ] Build dashboards querying monitoring data
- [ ] Understand AGGREGATE/DERIVED/DRIFT patterns

✅ **Quality**
- [ ] Apply proper table properties and comments
- [ ] Implement appropriate DQ expectations
- [ ] Handle quarantine and error scenarios

---

## 💡 Pro Tips

1. **Don't Skip Foundations** - Chapters 1-5 are mandatory, not optional
2. **Use Checklists** - Every chapter has validation checklists - use them
3. **Copy Working Code** - All examples are from production code - copy and adapt
4. **Follow Patterns** - Don't reinvent - these patterns are battle-tested
5. **Document as You Go** - Especially in Gold layer (dual-purpose comments)
6. **Think LLM-First** - All documentation should be natural language
7. **Automate Everything** - Use Asset Bundles for all infrastructure
8. **Monitor Everything** - Add monitoring to all critical Gold tables
9. **Test with Corrupted Data** - Use Faker patterns to generate DQ issues
10. **Improve Continuously** - Follow Chapter 20 to contribute patterns back

---

## 🤝 Contributing to This Framework

See **Chapter 20: Self-Improvement Process** for the complete workflow.

**Quick version**:
1. Identify pattern (3+ occurrences or official best practice)
2. Validate with team and documentation
3. Update appropriate chapter(s)
4. Add examples from actual code
5. Update this Table of Contents
6. Document in RULE_IMPROVEMENT_LOG.md

---

## 📅 Framework Maintenance

- **Daily**: Apply patterns in new development
- **Weekly**: Review new patterns in code reviews
- **Monthly**: Update rules based on lessons learned
- **Quarterly**: Major documentation review
- **Annually**: Framework architecture review

---

## 🎓 Certification Levels

### Level 1: Foundation Engineer
- Read and understand Chapters 1-7
- Can implement Bronze and basic Silver
- Follows table property standards

### Level 2: Data Product Engineer
- Mastered Chapters 1-14
- Can build complete Bronze → Silver → Gold pipelines
- Implements proper documentation and ERDs

### Level 3: Semantic Layer Architect
- Mastered Chapters 1-17
- Can design and implement complete semantic layers
- Creates Genie-ready data products

### Level 4: Platform Architect
- Mastered all 20 chapters
- Can design enterprise-scale solutions
- Contributes patterns back to framework

---

## 📞 Getting Help

**Stuck on a pattern?**
1. Check the chapter's "Common Mistakes" section
2. Review the validation checklist
3. Look at working examples in src/
4. Search RULE_IMPROVEMENT_LOG.md for similar issues

**Found a bug in the rules?**
1. Follow Chapter 20 (Self-Improvement)
2. Document the issue clearly
3. Propose the fix with examples
4. Submit for team review

---

## 📚 External Learning Resources

Complement this framework with official Databricks training:
- [Databricks Academy](https://www.databricks.com/learn/training)
- [Data Engineering with Databricks](https://www.databricks.com/learn/training/data-engineer)
- [Databricks Certified Data Engineer Associate](https://www.databricks.com/learn/certification/data-engineer-associate)

---

## ⚖️ License & Usage

These rules are internal to this project but represent **production-proven patterns**. Adapt them for your own projects with attribution.

---

## 🎯 Final Word

This framework represents **thousands of hours of real-world experience** building production data products on Databricks. Every pattern, every checklist, every example comes from actual working code.

**Your job is simple**: Follow the patterns, validate with checklists, and contribute improvements back.

**Start with Chapter 1. Build something great. Make it better.**

---

**Version**: 2.0 (Reorganized)
**Last Updated**: October 28, 2025
**Next Review**: After major feature implementations

---

*Remember: These aren't just rules - they're the accumulated wisdom of building production data products. Read them. Use them. Improve them.*

