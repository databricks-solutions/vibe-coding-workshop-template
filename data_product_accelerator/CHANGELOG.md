# Changelog

All notable changes to the Data Product Accelerator (formerly Vibe Coding Lakehouse Starter Framework) are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [1.3.1] — 2026-02-08

### Development Documentation Consolidation

Consolidated all development prompt files into a single comprehensive SQL-format documentation file for better organization and maintainability.

### Added

- **`docs/development/section_input_prompts_dml.sql`** — Comprehensive 3,758-line SQL documentation consolidating all skill conversion and improvement prompts

### Removed

- **`docs/development/05-naming-comment-standards.md`** — Consolidated into section_input_prompts_dml.sql
- **`docs/development/06-tagging-standards.md`** — Consolidated into section_input_prompts_dml.sql
- **`docs/development/comprehensive-agent-implementation-prompt.md`** — Consolidated into section_input_prompts_dml.sql
- **`docs/development/convert-genai-agents-to-skills-prompt.md`** — Consolidated into section_input_prompts_dml.sql
- **`docs/development/convert-gold-design-prompt-to-skill.md`** — Consolidated into section_input_prompts_dml.sql
- **`docs/development/convert-gold-implementation-prompt-to-skill.md`** — Consolidated into section_input_prompts_dml.sql
- **`docs/development/improve-genai-agents-from-databricks-skills.md`** — Consolidated into section_input_prompts_dml.sql
- **`docs/development/merge-project-plan-prompt-into-skill.md`** — Consolidated into section_input_prompts_dml.sql

---

## [1.3.0] — 2026-02-07

### Project Plan Methodology, Tagging Standards Overhaul & .cursor Cleanup

New project plan methodology skill, comprehensive tagging standards rewrite with canonical YAML schema, workshop mode for live sessions, updated Wanderbricks schema, and final cleanup of all leftover `.cursor/` duplicates.

### Added

- **Project plan methodology skill** — `data_product_accelerator/skills/planning/00-project-plan-methodology/SKILL.md` (565 lines) with full methodology for multi-phase Databricks project planning
- **Workshop mode profile** — `data_product_accelerator/skills/planning/00-project-plan-methodology/references/workshop-mode-profile.md` for facilitating live workshop sessions
- **Canonical tagging schema** — `data_product_accelerator/skills/common/naming-tagging-standards/references/canonical-tagging-schema.yaml` (125 lines) defining the authoritative tag taxonomy for org-wide standardization
- **Rule-to-skill converter script** — `data_product_accelerator/skills/admin/cursor-rule-to-skill/scripts/convert-rule-to-skill.py` restored

### Changed

- **Naming & tagging standards skill** — major rewrite of SKILL.md (+280 lines) and `references/tagging-patterns.md` (+463 lines) with canonical tag taxonomy, governance enforcement patterns, budget policy tagging, and tag validation workflows
- **Wanderbricks schema CSV** — `context/Wanderbricks_Schema.csv` updated with revised schema definitions (114 lines changed)
- **Project planning skill** — added workshop mode detection and quick-start profile references
- **QUICKSTART.md** — updated prompts and formatting

### Removed

- **`context/tagging-config.template.yaml`** — replaced by canonical schema at `data_product_accelerator/skills/common/naming-tagging-standards/references/canonical-tagging-schema.yaml`
- **`.cursor/rules/common/skill-navigator.mdc`** — last remaining cursor rule; routing now handled entirely by `AGENTS.md`
- **`.cursor/skills/gold/01-gold-layer-implementation/SKILL.md`** — duplicate of `data_product_accelerator/skills/gold/01-gold-layer-setup/`
- **`.cursor/skills/monitoring/anomaly-detection/`** — entire duplicate directory (SKILL.md, references, scripts, templates); canonical version at `data_product_accelerator/skills/monitoring/04-anomaly-detection/`
- **`.cursor/skills/silver/00-silver-layer-creation/SKILL.md`** — duplicate of `data_product_accelerator/skills/silver/00-silver-layer-setup/`

---

## [1.2.0] — 2026-02-08

### Renamed: Data Product Accelerator

Repository renamed from "Vibe Coding Lakehouse Starter" to **Data Product Accelerator** to accurately reflect the framework's purpose: transforming a schema CSV into a fully governed, production-ready Databricks data product served by AI agents.

### Changed

- **Repository name** — `vibe_coding_lakehouse_starter_repo` → `data-product-accelerator`
- **README.md** — New title, subtitle highlighting 50 Agent Skills and open SKILL.md format, updated repo URLs
- **QUICKSTART.md** — Updated title to "Data Product Accelerator"
- **docs/framework-design/** — Renamed from `docs/vibe-coding-framework-design/`; all internal "Vibe Coding" references updated
- **CHANGELOG.md** — Added "formerly" note for historical context

### Removed

- **`genai-agents/08-genie-space-optimization/SKILL.md`** — duplicate of `semantic-layer/05-genie-space-optimization`; consolidated to single location

---

## [1.1.0] — 2026-02-07

### Multi-IDE Support & Skills Relocation

Skills moved from `.cursor/skills/` to the root `data_product_accelerator/skills/` directory, making the framework **IDE-agnostic**. A new `AGENTS.md` entry point enables automatic discovery by Cursor, Claude Code, Windsurf, Copilot, Codex, and any agent that reads `AGENTS.md`.

### Added

- **`AGENTS.md`** — universal entry point for any AI coding assistant, combining skill navigator routing table, common skills index, role definition, and IDE compatibility matrix
- **Anomaly detection references and scripts** — `references/alert-patterns.md`, `references/configuration-guide.md`, `references/results-schema.md`, `scripts/enable_anomaly_detection.py`, `scripts/query_results.py`, `assets/templates/alert-query-template.sql`
- **Exploration skill enhancements** — expanded `analysis-workflows.md`, new `tips-and-troubleshooting.md`, new `requirements-template.md` asset
- **Silver layer creation skill** — comprehensive `00-silver-layer-creation/SKILL.md` (510 lines) in `.cursor/skills/`
- **Cursor rule** — `.cursor/rules/common/skill-navigator.mdc` for Cursor-specific routing

### Changed

- **Skills location** — moved from `.cursor/skills/` to root `data_product_accelerator/skills/` directory for IDE-agnostic access
- **All skill path references** — updated across QUICKSTART.md, README.md, docs/, and internal skill cross-references from `.cursor/skills/` to `data_product_accelerator/skills/`
- **Architecture overview** — updated `02-architecture-overview.md` with new paths and MLflow GenAI foundation patterns
- **Cursor rules** — consolidated from 2 root-level rules (`skill-navigator.mdc`, `common-skills-reference.mdc`) to 1 rule at `.cursor/rules/common/skill-navigator.mdc`

### Removed

- **`.cursor/rules/skill-navigator.mdc`** — replaced by `AGENTS.md` (universal) + `.cursor/rules/common/skill-navigator.mdc` (Cursor-specific)
- **`.cursor/rules/common-skills-reference.mdc`** — content merged into `AGENTS.md`
- **`.cursor/skills/admin/cursor-rule-to-skill/`** — entire skill directory removed
- **`.cursor/skills/admin/cursor-rules/`** — skill removed

---

## [1.0.0] — 2026-02-07

### Architecture — Skills-First Migration

Complete restructuring from a rules-heavy architecture (46 cursor rules) to a **skills-first architecture** (2 routing rules + 50+ Agent Skills). This is the largest change in the project's history — a **breaking change** that consolidates duplicated patterns and establishes clear skill ordering.

### Added

- **Agent Skills framework** — 50+ skills organized across 12 domains with orchestrator/worker pattern
  - `gold/` — 2 orchestrators + 7 workers (design, YAML setup, merge, dedup, ERD, schema validation, grain validation, documentation)
  - `bronze/` — 1 orchestrator + 1 worker (layer setup, Faker data generation)
  - `silver/` — 1 orchestrator + 2 workers (DLT expectations, DQX patterns)
  - `semantic-layer/` — 1 orchestrator + 5 workers (Metric Views, TVFs, Genie Spaces, API, optimization)
  - `monitoring/` — 1 orchestrator + 4 workers (Lakehouse Monitoring, dashboards, alerts, anomaly detection)
  - `ml/` — 1 orchestrator (MLflow, Feature Store, training, inference)
  - `genai-agents/` — 1 orchestrator + 8 workers (ResponsesAgent, evaluation, memory, prompts, multi-agent, deployment, monitoring, foundation)
  - `planning/` — 1 orchestrator (phase plans, YAML manifest contracts)
  - `exploration/` — 1 standalone (dual-format notebooks)
  - `common/` — 8 shared skills (Expert Agent, Asset Bundles, Autonomous Ops, Naming Standards, Python Imports, Table Properties, Schema Management, UC Constraints)
  - `admin/` — 6 utilities (skill creator, cursor rules, documentation organization, self-improvement, freshness audit, rule-to-skill converter)
- **Skill Navigator** — intelligent routing system with keyword-based task detection
- **Common Skills Reference** — always-on index of 8 cross-cutting shared skills
- **QUICKSTART.md** — one-prompt-per-stage guide for the 9-stage pipeline
- **Framework design documentation** — 8 documents + 3 appendices in `docs/framework-design/`
- **CHANGELOG.md** — project changelog following Keep a Changelog format
- **Naming and tagging standards** skill — enterprise naming conventions, dual-purpose comments, governed tags
- **Autonomous operations** skill — self-healing deploy-poll-diagnose-fix-redeploy loop
- **Anomaly detection** skill — schema-level freshness/completeness monitoring via Data Quality API
- **GenAI agents** skills — MLflow 3.0 ResponsesAgent, Lakebase memory, prompt registry, multi-agent Genie orchestration, evaluation with LLM judges, deployment automation, production monitoring
- **Skill freshness auditing** — systematic verification of skills against official documentation
- **Self-improvement** skill — agent learning from mistakes with skill updates
- **Progressive disclosure** — SKILL.md → references/ → scripts/ → assets/templates/ layering

### Changed

- **Architecture** — migrated from 46 cursor rules to 2 routing rules + 50 skills
- **Skill numbering** — all skills now use numbered prefixes (`00-` orchestrators, `01-`+ workers)
- **Lakehouse Monitoring** skill — updated to use new Data Quality API (`databricks.sdk.service.dataquality`)
- **Gold layer implementation** skill — consolidated references and templates
- **Common skills** — updated Asset Bundles, Table Properties, Schema Management, UC Constraints, Python Imports
- **README.md** — fully rewritten for skills-first architecture

### Removed

- **46 cursor rules** — all `.mdc` rules in domain subdirectories (bronze, silver, gold, semantic-layer, monitoring, ml, genai-agents, planning, exploration, admin, common) replaced by Agent Skills
- **`.cursor/rules/README.md`** — framework overview (replaced by QUICKSTART.md and design docs)
- **`.cursor/rules/00_TABLE_OF_CONTENTS.md`** — rules table of contents (replaced by skill navigator)
- **`context/prompts/`** — all 17 reusable prompt templates (replaced by skill-based workflow where one `@` reference per stage replaces explicit prompts)
- **`databricks-tools-core/`** — entire Python SDK toolkit (12 modules, tests, docs)
- **`databricks-skills/`** — entire external skills library (agent-bricks, AI/BI dashboards, asset bundles, apps, Python SDK, jobs, Unity Catalog, model serving, SDP, synthetic data, etc.)
- **GenAI agent rule files** — 8 `.mdc` rules + 5 summary/review documents replaced by 10 Agent Skills

---

## [0.4.0] — 2026-02-06

### Added

- GenAI agent patterns — ResponsesAgent, evaluation, memory, orchestration, deployment, monitoring
- Enhanced semantic layer skills — Genie Space optimization, export/import API
- Gold and Silver layer skills with progressive disclosure
- Comprehensive agent skills framework with Databricks tooling integration
- Project plan phase details reference documentation

---

## [0.3.0] — 2026-01-27

### Added

- Cursor rules navigator with tiered context loading
- Enhanced cursor rule patterns across all domains

### Changed

- Updated cursor rules with improved patterns and cross-references

---

## [0.2.0] — 2026-01-21

### Added

- Schema extraction patterns for Gold layer merge operations ("Extract, Don't Generate" principle)
- UAT deployment target configuration
- Genie Space export/import API rule
- Instructions.pdf getting started guide

### Changed

- Updated `databricks.yml` Asset Bundle configuration

### Removed

- Example dashboard file (cleanup)

---

## [0.1.0] — 2026-01-21

### Added

- Initial repository structure with Medallion Architecture framework
- 27 cursor rules across 9 categories (common, bronze, silver, gold, semantic-layer, monitoring, exploration, planning, admin)
- 17 reusable prompt templates for AI-assisted code generation
- Wanderbricks example schema CSV
- `databricks-tools-core` Python SDK toolkit
- `databricks-skills` external skills library

---

## [0.0.x] — 2025-12-11 to 2026-01-02

### Added

- Customer Segmentation ML model pipeline
- SQL alerting framework for Wanderbricks
- Capability audit and Figma design prompts
- Agent architecture, SQL alerts, and documentation prompts
- Enhanced alerting framework with cursor rules integration

### Changed

- Reorganized docs, refactored plans, updated semantic layer
- Expanded Wanderbricks example in project plan prompt
- Updated databricks-asset-bundles cursor rule
