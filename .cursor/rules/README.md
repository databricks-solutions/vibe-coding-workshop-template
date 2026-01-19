# Cursor Rules: End-to-End Data Product Guide

## 🚀 Start Here!

**👉 READ THIS FIRST**: [`00_TABLE_OF_CONTENTS.md`](./00_TABLE_OF_CONTENTS.md)

The Table of Contents provides a **complete, sequential guide** organized like a professional book on building data products with Databricks.

---

## 📖 What's New (October 28, 2025)

### ✨ Major Reorganization

All cursor rules have been reorganized into a **coherent, sequential framework** with:

✅ **22 Numbered Chapters** - Clear progression from foundations to advanced features
✅ **7 Logical Parts** - Grouped by major phases (Foundations, Bronze, Silver, Gold, Semantic, Observability, Process)
✅ **Learning Paths** - Multiple routes through the framework for different roles
✅ **Comprehensive TOC** - Complete guide with decision trees and quick references

### 🔄 What Changed

**All rule files renamed** with chapter numbers for sequential organization:

```
Old: databricks-expert-agent.mdc
New: 01-databricks-expert-agent.mdc (Chapter 1)

Old: dlt-expectations-patterns.mdc
New: 07-dlt-expectations-patterns.mdc (Chapter 8)

Old: metric-views-patterns.mdc  
New: 14-metric-views-patterns.mdc (Chapter 15)

... and so on
```

**See**: [`REORGANIZATION_PLAN.md`](./REORGANIZATION_PLAN.md) for complete mapping.

---

## 🗺️ Quick Navigation

### By Role

**New Developer** → Start with [Chapters 1-5](./00_TABLE_OF_CONTENTS.md#part-i-foundations) (Foundations)

**Data Engineer** → Follow [Complete Path](./00_TABLE_OF_CONTENTS.md#path-2-complete-data-engineer) through all layers

**Quality Engineer** → Jump to [Advanced Quality Path](./00_TABLE_OF_CONTENTS.md#path-3-advanced-quality-engineer)

**Semantic Architect** → Focus on [Semantic Layer Path](./00_TABLE_OF_CONTENTS.md#path-4-semantic-layer-architect)

**Platform Architect** → Review [Platform Path](./00_TABLE_OF_CONTENTS.md#path-5-platform-architect)

### By Layer

**Bronze** → [Chapters 1-7](./00_TABLE_OF_CONTENTS.md#part-ii-bronze-layer---raw-data-ingestion)

**Silver** → [Chapters 8-10](./00_TABLE_OF_CONTENTS.md#part-iii-silver-layer---validated--cleansed-data)

**Gold** → [Chapters 11-14](./00_TABLE_OF_CONTENTS.md#part-iv-gold-layer---business-ready-analytics)

**Semantic Layer** → [Chapters 15-17](./00_TABLE_OF_CONTENTS.md#part-v-semantic-layer--intelligence)

**Monitoring** → [Chapters 18-20](./00_TABLE_OF_CONTENTS.md#part-vi-observability--monitoring)

### By Task

**Setting up infrastructure?** → Chapter 2 (Asset Bundles) + Chapter 3 (Schemas)

**Creating tables?** → Chapter 4 (Table Properties) + layer-specific chapter

**Building semantic layer?** → Chapters 15-17 (Metric Views, TVFs, Genie)

**Adding monitoring?** → Chapters 18-20 (Monitoring setup, metrics, queries)

**Creating test data?** → Chapter 7 (Faker Data Generation)

**Need shared Python code?** → Chapter 10 (Python Imports)

---

## 📚 Framework Structure

### PART I: FOUNDATIONS (Chapters 1-5)
Core principles and architectural patterns that govern everything

| Chapter | File | What You'll Learn |
|---------|------|-------------------|
| 1 | [`01-databricks-expert-agent.mdc`](./01-databricks-expert-agent.mdc) | Architecture & non-negotiable principles |
| 2 | [`02-databricks-asset-bundles.mdc`](./02-databricks-asset-bundles.mdc) | Infrastructure-as-Code for workflows |
| 3 | [`03-schema-management-patterns.mdc`](./03-schema-management-patterns.mdc) | Config-driven schema management |
| 4 | [`04-databricks-table-properties.mdc`](./04-databricks-table-properties.mdc) | Universal table metadata standards |
| 5 | [`05-unity-catalog-constraints.mdc`](./05-unity-catalog-constraints.mdc) | PK/FK relationship modeling |

### PART II: BRONZE LAYER (Chapters 6-7)
Raw data ingestion with minimal transformation

| Chapter | File | What You'll Learn |
|---------|------|-------------------|
| 6 | *(See Chapter 1)* | Bronze layer patterns |
| 7 | [`06-faker-data-generation.mdc`](./06-faker-data-generation.mdc) | Realistic test data generation |

### PART III: SILVER LAYER (Chapters 8-10)
Validated and cleansed data with streaming quality

| Chapter | File | What You'll Learn |
|---------|------|-------------------|
| 8 | [`07-dlt-expectations-patterns.mdc`](./07-dlt-expectations-patterns.mdc) | Comprehensive DQ enforcement |
| 9 | [`08-dqx-patterns.mdc`](./08-dqx-patterns.mdc) | Advanced DQ with detailed diagnostics |
| 10 | [`09-databricks-python-imports.mdc`](./09-databricks-python-imports.mdc) | Sharing code between notebooks |

### PART IV: GOLD LAYER (Chapters 11-14)
Business-ready analytics with documentation

| Chapter | File | What You'll Learn |
|---------|------|-------------------|
| 11 | [`10-gold-layer-merge-patterns.mdc`](./10-gold-layer-merge-patterns.mdc) | Schema-aware transformations |
| 12 | [`11-gold-delta-merge-deduplication.mdc`](./11-gold-delta-merge-deduplication.mdc) | Preventing duplicate errors |
| 13 | [`12-gold-layer-documentation.mdc`](./12-gold-layer-documentation.mdc) | Comprehensive doc standards |
| 14 | [`13-mermaid-erd-patterns.mdc`](./13-mermaid-erd-patterns.mdc) | Professional ERD diagrams |

### PART V: SEMANTIC LAYER (Chapters 15-17)
Making data consumable for humans and AI

| Chapter | File | What You'll Learn |
|---------|------|-------------------|
| 15 | [`14-metric-views-patterns.mdc`](./14-metric-views-patterns.mdc) | Semantic layer for Genie & AI/BI |
| 16 | [`15-databricks-table-valued-functions.mdc`](./15-databricks-table-valued-functions.mdc) | SQL functions for Genie |
| 17 | [`16-genie-space-patterns.mdc`](./16-genie-space-patterns.mdc) | Genie Space setup |

### PART VI: OBSERVABILITY (Chapters 18-20)
Tracking quality, drift, and business metrics

| Chapter | File | What You'll Learn |
|---------|------|-------------------|
| 18 | [`17-lakehouse-monitoring-patterns.mdc`](./17-lakehouse-monitoring-patterns.mdc) | Production monitoring setup |
| 19 | [`18-lakehouse-monitoring-business-drift-metrics.mdc`](./18-lakehouse-monitoring-business-drift-metrics.mdc) | Custom business metrics |
| 20 | [`19-lakehouse-monitoring-custom-metrics-queries.mdc`](./19-lakehouse-monitoring-custom-metrics-queries.mdc) | Dashboard query patterns |

### PART VII: PROCESS (Chapters 21-22)
Maintaining quality and evolving the framework

| Chapter | File | What You'll Learn |
|---------|------|-------------------|
| 21 | [`20-cursor-rules.mdc`](./20-cursor-rules.mdc) | Managing cursor rules |
| 22 | [`21-self-improvement.mdc`](./21-self-improvement.mdc) | Continuous improvement |

---

## 🎯 Quick Decision Tree

**"Which chapter do I need right now?"**

```
Starting a new project?
└─→ Chapter 1 (Architecture & Principles)

Setting up infrastructure?
└─→ Chapter 2 (Asset Bundles) + Chapter 3 (Schemas)

Creating tables?
├─ Bronze → Chapter 4 (Table Properties) + Chapter 6 (Bronze Patterns)
├─ Silver → Chapter 8 (DLT Expectations)
└─ Gold → Chapter 11 (Merge Patterns) + Chapter 13 (Documentation)

Building semantic layer?
├─ For Dashboards → Chapter 15 (Metric Views)
├─ For Genie → Chapter 16 (TVFs) + Chapter 17 (Genie Spaces)
└─ Both → Read all three

Need monitoring?
├─ Setup → Chapter 18 (Monitoring Patterns)
├─ Custom Metrics → Chapter 19 (Business Drift Metrics)
└─ Dashboard Queries → Chapter 20 (Custom Metrics Queries)

Creating test data?
└─→ Chapter 7 (Faker Data Generation)

Need shared Python code?
└─→ Chapter 10 (Python Imports)

Proposing new pattern?
└─→ Chapter 22 (Self-Improvement)
```

---

## ✅ Compliance Checklists

### Before Committing ANY Code

**Bronze Layer**
- [ ] UC-managed with catalog/schema
- [ ] Change Data Feed enabled
- [ ] CLUSTER BY AUTO configured
- [ ] All TBLPROPERTIES set
- [ ] Table comment with "LLM:" prefix
- [ ] All columns have comments

**Silver Layer**
- [ ] DLT streaming table
- [ ] Critical rules use @dlt.expect_all_or_drop
- [ ] Warning rules use @dlt.expect_all
- [ ] Centralized rules in data_quality_rules.py
- [ ] Row tracking & deletion vectors enabled
- [ ] Business key generated

**Gold Layer**
- [ ] PK/FK constraints defined (NOT ENFORCED)
- [ ] SCD2 for dimensions (if needed)
- [ ] Dual-purpose documentation (no "LLM:" prefix)
- [ ] Metric view created
- [ ] ERD documented

**Asset Bundles**
- [ ] Serverless compute
- [ ] Variables for all configs
- [ ] Complete tags (environment, project, layer, job_type)
- [ ] Failure notifications
- [ ] Permissions defined

---

## 📊 Framework Statistics

**Total Chapters**: 22
**Total Lines of Guidance**: ~8,800+
**Patterns Covered**: 22 major patterns
**Code Examples**: 100+ production-ready examples
**Validation Checklists**: 22 comprehensive checklists
**Documentation Links**: 50+ official references
**Parts**: 7 logical groupings

---

## 🎓 Recommended Reading Order

### First Time (Learn Everything)
1. **Read**: Table of Contents (00_TABLE_OF_CONTENTS.md)
2. **Master**: PART I - Foundations (Chapters 1-5)
3. **Implement**: Layer by layer (Parts II-IV)
4. **Enhance**: Semantic layer & monitoring (Parts V-VI)
5. **Contribute**: Process & improvements (Part VII)

### Quick Start (MVP)
1. Chapter 1 (Architecture)
2. Chapter 2 (Infrastructure - basics)
3. Chapter 4 (Table Properties)
4. Chapter 6 (Bronze)
5. Chapter 8 (Silver - basic)
6. Chapter 11 (Gold merge)

### Reference Use (Experienced)
- Jump to specific chapter by number
- Use part groupings to find related patterns
- Check validation checklists before committing
- Cross-reference with official docs

---

## 💡 Pro Tips

1. **Don't skip foundations** - Chapters 1-5 are mandatory
2. **Use checklists** - Validate before every commit
3. **Copy working code** - All examples are production-tested
4. **Follow patterns** - Don't reinvent
5. **Document as you go** - Especially Gold layer
6. **Think LLM-first** - Natural language everywhere
7. **Automate everything** - Asset Bundles for all infrastructure
8. **Monitor everything** - Add monitoring to critical tables
9. **Test with corrupt data** - Use Faker patterns
10. **Improve continuously** - Follow Chapter 22

---

## 🔍 Finding What You Need

### By File Name Pattern
```bash
# Foundation rules
ls -1 0[1-5]-*.mdc

# Silver layer rules  
ls -1 0[7-9]-*.mdc

# Gold layer rules
ls -1 1[0-3]-*.mdc

# Semantic layer rules
ls -1 1[4-6]-*.mdc

# Monitoring rules
ls -1 1[7-9]-*.mdc

# Process rules
ls -1 2[0-1]-*.mdc
```

### By Keyword
Use your editor's search to find patterns across all rules.

### By Checklist
Each chapter has a validation checklist - use them!

---

## 📖 Additional Documentation

| Document | Purpose |
|----------|---------|
| [`00_TABLE_OF_CONTENTS.md`](./00_TABLE_OF_CONTENTS.md) | **START HERE** - Complete framework guide |
| [`REORGANIZATION_PLAN.md`](./REORGANIZATION_PLAN.md) | Details of the reorganization |
| [`RULE_IMPROVEMENT_LOG.md`](./RULE_IMPROVEMENT_LOG.md) | Historical log of changes |
| [`ORCHESTRATOR_RULE_IMPROVEMENTS.md`](./ORCHESTRATOR_RULE_IMPROVEMENTS.md) | Orchestrator pattern case study |

---

## 🤝 Contributing

Want to improve these rules? See **Chapter 22: Self-Improvement Process**

**Quick version:**
1. Identify pattern (3+ uses or official best practice)
2. Validate with team and docs
3. Update appropriate chapter(s)
4. Add examples from real code
5. Update this README
6. Document in RULE_IMPROVEMENT_LOG.md

---

## 🆘 Getting Help

**Stuck on a pattern?**
1. Check chapter's "Common Mistakes" section
2. Review validation checklist
3. Look at examples in `src/`
4. Search RULE_IMPROVEMENT_LOG.md

**Found a bug?**
1. Follow Chapter 22 (Self-Improvement)
2. Document clearly
3. Propose fix with examples
4. Submit for review

---

## 📚 External Resources

Complement this framework with official Databricks resources:
- [Databricks Documentation](https://docs.databricks.com/)
- [Databricks Academy](https://www.databricks.com/learn/training)
- [Unity Catalog](https://docs.databricks.com/unity-catalog/)
- [Delta Lake](https://docs.databricks.com/delta/)
- [DLT](https://docs.databricks.com/dlt/)
- [Metric Views](https://learn.microsoft.com/azure/databricks/metric-views/)

---

## 🎯 Success Criteria

You've mastered this framework when you can:

✅ Explain the 7 non-negotiable principles
✅ Set up complete Asset Bundle with orchestrators
✅ Create properly governed schemas and tables
✅ Build Bronze → Silver → Gold pipelines
✅ Implement centralized DQ rules
✅ Design Metric Views with synonyms
✅ Create Table-Valued Functions for Genie
✅ Configure Lakehouse Monitoring with custom metrics
✅ Build dashboards querying monitoring data
✅ Apply proper documentation standards

---

## 🚀 Getting Started

### Day 1
- Read Table of Contents completely
- Understand the 7 parts
- Review your learning path

### Week 1
- Master PART I (Foundations)
- Understand all 5 core principles
- Review examples in each chapter

### Month 1
- Implement Bronze → Silver → Gold
- Apply patterns to real data
- Follow all checklists

### Quarter 1
- Add semantic layer
- Implement monitoring
- Contribute improvements

---

## 📝 Version History

**Version 2.0** (October 28, 2025) - Major reorganization
- All rules renamed with chapter numbers
- New Table of Contents created
- 7-part structure implemented
- Learning paths added
- Decision trees added

**Version 1.0** (October 2025) - Initial collection
- 21 individual rules
- Basic README
- Alphabetical organization

---

## ⚖️ License & Usage

These rules are internal to this project but represent **production-proven patterns**. Adapt for your projects with attribution.

---

## 🎯 Final Word

This framework represents **thousands of hours of real-world experience** building production data products on Databricks.

Every pattern, every checklist, every example comes from actual working code.

**Your job**: Follow the patterns. Validate with checklists. Contribute improvements.

**Start with the Table of Contents. Build something great. Make it better.**

---

**Current Version**: 2.0 (Reorganized)
**Last Updated**: October 28, 2025
**Total Rules**: 22 chapters across 7 parts
**Next Review**: After major feature implementations

---

*Remember: These aren't just rules - they're accumulated wisdom. Read them. Use them. Improve them.*

👉 **[START HERE: Read the Table of Contents](./00_TABLE_OF_CONTENTS.md)** 👈
