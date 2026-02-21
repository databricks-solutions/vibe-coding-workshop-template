# Changelog

All notable changes to the Data Product Accelerator (formerly Vibe Coding Lakehouse Starter Framework) are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [2.0.2] — 2026-02-21

### Framework Visual Docs + Naming Consistency Cleanup

Updated framework visual guides to explicitly model optional Stage 6b as a standalone orchestrator phase, and cleaned stale skill naming references in related docs and monitoring metadata.

### Changed

- **`docs/framework-design/10-skill-navigation-visual-guide.md`** — Added optional Stage 6b routing language and updated the pipeline diagram to show Semantic → Genie Optimization (6b, optional) → Observability sequencing
- **`docs/framework-design/10-skill-navigation-visual-guide.html`** — Updated visual model to include explicit Stage 6b node, separated Stage 6b worker group (4 workers), and refreshed step narration to reflect standalone orchestrator behavior
- **`docs/framework-design/11-skill-hierarchy-tree.html`** — Added dedicated Stage 6b orchestrator branch with its 4 worker skills, updated semantic worker names to canonical paths, and expanded animation sequence to include Stage 6b traversal
- **`skills/monitoring/04-anomaly-detection/SKILL.md`** — Corrected stale `called_by` and integration text references from `silver-layer-creation`/`gold-layer-implementation` to `silver-layer-setup`/`gold-layer-setup`
- **`docs/framework-design/05-skill-domains.md`** — Removed stale legacy orchestrator names and clarified canonical Silver orchestrator naming

---

## [2.0.1] — 2026-02-21

### Documentation Routing Consistency Pass

Aligned stage sequencing and routing language across entry-point docs and the skill navigator so all references consistently include optional Stage 6b (Genie optimization) and current skill naming.

### Changed

- **`AGENTS.md`** — Added Stage 6b to the Design-First pipeline, added orchestrator routing row for `05-genie-optimization-orchestrator`, and added Genie optimization worker-routing keywords
- **`README.md`** — Updated Quick Start wording and pipeline section title/content to include optional Stage 6b between Semantic and Observability
- **`QUICKSTART.md`** — Clarified the guide includes an optional Stage 6b optimization loop and renamed Step 6b heading to explicitly mark it optional
- **`skills/skill-navigator/SKILL.md`** — Updated `last_verified` metadata and added Stage 6b orchestrator route keywords in the orchestrator routing table
- **`skills/skill-navigator/references/domain-indexes.md`** — Added Stage 6b to the pipeline overview and corrected stale cross-stage trigger names to `silver-layer-setup` and `gold-layer-setup`

---

## [2.0.0] — 2026-02-20

### Genie Optimization Skill Decomposition (Introspective AI Architecture)

Decomposed the monolithic `05-genie-space-optimization` skill (18 files, ~6,081 lines) into 1 orchestrator + 4 worker skills following agentskills.io specification, Anthropic context engineering, and long-running agent harness patterns. Each worker is independently testable and loaded on demand. Introduced MLflow-driven 3-layer judge architecture with 8 judges + arbiter, GEPA metadata optimization, and job-based evaluation.

### Added

- **`05-genie-optimization-orchestrator/`** — New orchestrator skill at `skills/semantic-layer/` that routes to 4 workers on demand. Manages session state in MLflow experiment tags. Optimization loop: generate benchmarks → evaluate → optimize → apply → re-evaluate, max 5 iterations with plateau detection.
- **`genie-optimization-workers/01-genie-benchmark-generator/`** — Worker for three-path benchmark intake, ground truth SQL validation via warehouse execution with result hashing, and MLflow Evaluation Dataset sync.
- **`genie-optimization-workers/02-genie-benchmark-evaluator/`** — Worker implementing 3-layer judge architecture: Layer 1 (6 quality judges), Layer 2 (result correctness via DataFrame comparison), Layer 3 (arbiter for disagreement resolution with benchmark auto-correction). Supports job-based and inline evaluation modes.
- **`genie-optimization-workers/03-genie-metadata-optimizer/`** — Worker for GEPA optimize_anything (Tier 1), structured LLM introspection (Tier 2), failure clustering, metadata proposal generation with predicted impact, and optional SIMBA judge alignment (Tier 3).
- **`genie-optimization-workers/04-genie-optimization-applier/`** — Worker for applying metadata changes via 6 control levers with dual persistence (API + repo files), sort_genie_config, and three-phase deployment with self-healing (max 3 retries).
- **`assets/templates/run_genie_evaluation.py`** — Self-contained Databricks notebook for running evaluation as a job with MLflow logging.
- **`assets/templates/genie-evaluation-job-template.yml`** — Databricks Asset Bundle job definition for evaluation notebook.

### Changed

- **Skill count** — 55 → 59 skills (1 monolithic skill replaced by 5 decomposed skills = +4 net)
- **Semantic layer domain** — 6 → 10 skills (1 orchestrator + 4 original workers + 1 optimization orchestrator + 4 optimization workers)
- **QUICKSTART.md** — Updated Step 6b prompt to reference `05-genie-optimization-orchestrator` with MLflow-driven evaluation workflow
- **README.md** — Updated skill count to 59, semantic-layer workers to 9
- **AGENTS.md** — Updated skill count, routing references
- **skill-navigator/SKILL.md** — Updated directory map with `genie-optimization-workers/` subfolder, skill count to 59
- **skill-navigator/references/domain-indexes.md** — Updated Semantic Layer index with optimization orchestrator and 4 workers
- **docs/framework-design/** — Updated skill counts and references across 00-index, 01-introduction, 02-architecture, 03-pipeline, 04-agent-skills, 05-skill-domains, 08-operations-guide, 12-semantic-layer-walkthrough, appendices/B-troubleshooting

### Removed

- **`05-genie-space-optimization/`** — Monolithic skill eliminated after decomposition. All content migrated to the 5 new skills with no regression.
- **`references/optimization-code-patterns.md`** (1,049 lines) — Split across all 4 worker reference files
- **`references/optimization-workflow.md`** (238 lines) — Content merged into orchestrator and worker reference files
- **`references/asset-routing.md`** (150 lines) — Content merged into evaluator judge-definitions.md
- **`scripts/genie_optimizer.py`** (619 lines) — Split into orchestrator.py + 4 worker scripts

### Skill Count Breakdown (59 total)

| Domain | Count | Details |
|--------|-------|---------|
| admin | 4 | create-agent-skill, documentation-organization, self-improvement, skill-freshness-audit |
| bronze | 2 | 1 orchestrator + 1 worker |
| common | 8 | 8 shared cross-cutting skills |
| exploration | 1 | 1 standalone |
| genai-agents | 9 | 1 orchestrator + 8 workers |
| gold | 14 | 2 orchestrators + 7 design-workers + 5 pipeline-workers |
| ml | 1 | 1 orchestrator |
| monitoring | 5 | 1 orchestrator + 4 workers |
| planning | 1 | 1 orchestrator |
| semantic-layer | 10 | 1 orchestrator + 4 workers + 1 optimization orchestrator + 4 optimization workers |
| silver | 3 | 1 orchestrator + 2 workers |
| skill-navigator | 1 | Master routing system |

---

## [1.4.0] — 2026-02-20

### Documentation Consistency & Skill Count Corrections

Comprehensive audit and consistency pass across all navigation and documentation files. Corrected the skill count from 50 to 55 (Gold domain had 14 skills, not 9), fixed stale directory names in the skill navigator, and added missing routing entries.

### Changed

- **QUICKSTART.md** — Rewrote all 9 stage prompts and 5 validation checkpoint prompts to match the `section_input_prompts_dml.sql` pattern: skill reference → "This will involve the following steps:" → bold-action bullet points explaining each phase. Prompts are now self-documenting (users see what will happen) while also priming the LLM with the correct workflow. Added deployment checkpoints after Step 6 (Semantic Layer) and Step 7 (Observability). Added Databricks CLI to prerequisites.
- **AGENTS.md** — Updated skill count from 50 to 55 across all references
- **README.md** — Updated skill count from 50 to 55, fixed Gold domain count from 9 to 14, changed Gold (Impl) workers from "shared" to "5" in the domain table
- **skill-navigator/SKILL.md** — Fixed `pipeline-workers/grain-validation` → `pipeline-workers/04-grain-validation` and `pipeline-workers/merge-schema-validation` → `pipeline-workers/05-schema-validation` in the directory map; added `design-workers/07-design-validation` to the worker routing table
- **CHANGELOG.md v1.3.0** — Corrected stale path `00-project-plan-methodology` → `00-project-planning` (skill was never renamed; path was recorded incorrectly)
- **docs/framework-design/** — Updated skill count from 50 to 55 in `00-index.md`, `01-introduction.md`, `02-architecture-overview.md`, `04-agent-skills-system.md`, `05-skill-domains.md`, and `08-operations-guide.md`

### Skill Count Breakdown (55 total)

| Domain | Count | Details |
|--------|-------|---------|
| admin | 4 | create-agent-skill, documentation-organization, self-improvement, skill-freshness-audit |
| bronze | 2 | 1 orchestrator + 1 worker |
| common | 8 | 8 shared cross-cutting skills |
| exploration | 1 | 1 standalone |
| genai-agents | 9 | 1 orchestrator + 8 workers |
| gold | 14 | 2 orchestrators + 7 design-workers + 5 pipeline-workers |
| ml | 1 | 1 orchestrator |
| monitoring | 5 | 1 orchestrator + 4 workers |
| planning | 1 | 1 orchestrator |
| semantic-layer | 10 | 1 orchestrator + 4 workers + 1 optimization orchestrator + 4 optimization workers |
| silver | 3 | 1 orchestrator + 2 workers |
| skill-navigator | 1 | Master routing system |

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

- **Project planning methodology enhancements** — `data_product_accelerator/skills/planning/00-project-planning/SKILL.md` updated with full methodology for multi-phase Databricks project planning
- **Workshop mode profile** — `data_product_accelerator/skills/planning/00-project-planning/references/workshop-mode-profile.md` for facilitating live workshop sessions
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
