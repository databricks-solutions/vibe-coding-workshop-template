---
name: genai-agents-setup
description: >
  End-to-end orchestrator for implementing production-grade Databricks GenAI agents
  using MLflow 3.0 ResponsesAgent, Genie Spaces, Lakebase memory, and comprehensive
  evaluation. Orchestrates mandatory dependencies on genai-agents skills
  (responses-agent-patterns, mlflow-genai-evaluation, lakebase-memory-patterns,
  prompt-registry-patterns, multi-agent-genie-orchestration, deployment-automation,
  production-monitoring, mlflow-genai-foundation) plus cross-domain dependency on
  semantic-layer/genie-space-optimization.
  Use when implementing AI agents on Databricks, creating multi-agent systems with
  Genie Spaces, setting up agent evaluation pipelines, deploying agents to Model Serving,
  or troubleshooting agent implementation errors.
license: Apache-2.0
metadata:
  author: prashanth subrahmanyam
  version: "2.0.0"
  domain: genai-agents
  role: orchestrator
  pipeline_stage: 9
  pipeline_stage_name: genai-agents
  next_stages: []
  workers:
    - responses-agent-patterns
    - mlflow-genai-evaluation
    - lakebase-memory-patterns
    - prompt-registry-patterns
    - multi-agent-genie-orchestration
    - deployment-automation
    - production-monitoring
    - mlflow-genai-foundation
  cross_domain_dependencies:
    - semantic-layer/05-genie-space-optimization
  common_dependencies:
    - databricks-asset-bundles
    - databricks-expert-agent
    - databricks-python-imports
    - naming-tagging-standards
    - databricks-autonomous-operations
  consumes:
    - plans/manifests/genai-agents-manifest.yaml
  consumes_fallback: "Genie Space inventory (self-discovery from catalog)"
  dependencies:
    - responses-agent-patterns
    - mlflow-genai-evaluation
    - lakebase-memory-patterns
    - prompt-registry-patterns
    - multi-agent-genie-orchestration
    - deployment-automation
    - production-monitoring
    - mlflow-genai-foundation
    - semantic-layer/genie-space-optimization
  last_verified: "2026-02-07"
  volatility: high
  upstream_sources:
    - name: "ai-dev-kit"
      repo: "databricks-solutions/ai-dev-kit"
      paths:
        - "databricks-skills/agent-bricks/SKILL.md"
      relationship: "extended"
      last_synced: "2026-02-09"
      sync_commit: "97a3637"
---

# GenAI Agent Implementation Orchestrator

End-to-end guide for implementing production-grade Databricks GenAI agents using the MLflow 3.0 ResponsesAgent framework with Genie Spaces, Lakebase memory, and comprehensive evaluation.

## When to Use

- Implementing a new AI agent on Databricks from scratch
- Creating multi-agent systems with Genie Space data access
- Setting up agent evaluation pipelines with LLM judges
- Deploying agents to Model Serving with OBO authentication
- Adding memory (short-term conversations, long-term preferences) to agents
- Troubleshooting agent implementation errors (AI Playground, authentication, evaluation)
- Planning agent architecture (orchestrator + worker pattern)

## Architecture Overview

### Recommended: Hybrid Architecture (Genie + Custom Orchestrator)

```
User Query
    │
    ▼
┌─────────────────────┐
│  ResponsesAgent     │  ← MLflow pyfunc model (MANDATORY)
│  (Orchestrator)     │
├─────────────────────┤
│  Intent Classifier  │  ← Routes to domains
│  LangGraph Workflow  │  ← State management
│  Memory Manager     │  ← Short-term + Long-term
└────────┬────────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌────────┐
│ Genie  │ │ Genie  │  ← Domain-specific data access
│ Space  │ │ Space  │     (OBO authentication)
│ (Cost) │ │ (Perf) │
└────────┘ └────────┘
```

**For full architecture details, see:** `references/architecture-overview.md`

### Technology Stack

| Component | Technology | Purpose |
|---|---|---|
| Agent Framework | MLflow ResponsesAgent | AI Playground compatible model |
| Data Access | Genie Spaces + Conversation API | Natural language data queries |
| Orchestration | LangGraph | Multi-agent state management |
| Short-term Memory | Lakebase CheckpointSaver | Conversation continuity |
| Long-term Memory | Lakebase DatabricksStore | User preferences |
| Prompt Management | Unity Catalog + MLflow Registry | Versioned prompts with A/B testing |
| Evaluation | MLflow GenAI Evaluate | LLM judges + custom scorers |
| Monitoring | MLflow Registered Scorers | Continuous production quality |
| Deployment | MLflow Deployment Jobs | Auto-trigger on model version |
| Authentication | OBO + Automatic Auth Passthrough | User-level data governance |

---

## Implementation Phases

### Phase 0: Read Plan (5 minutes)

**Before starting implementation, check for a planning manifest that defines what to build.**

```python
import yaml
from pathlib import Path

manifest_path = Path("plans/manifests/genai-agents-manifest.yaml")

if manifest_path.exists():
    with open(manifest_path) as f:
        manifest = yaml.safe_load(f)
    
    # Extract implementation checklist from manifest
    architecture = manifest.get('architecture', {})
    agents = manifest.get('agents', [])
    evaluation = manifest.get('evaluation', {})
    prompts = manifest.get('prompts', [])
    deployment = manifest.get('deployment', {})
    print(f"Plan: {len(agents)} agents, {len(prompts)} prompts")
    print(f"Architecture: {architecture.get('pattern', 'unknown')}")
    
    # Each agent has: name, domain, genie_space, capabilities, tools, sample_questions
    # Evaluation has: dataset_table, questions_per_domain, scorers, thresholds
else:
    # Fallback: self-discovery from Genie Spaces
    print("No manifest found — falling back to Genie Space self-discovery")
    # Discover existing Genie Spaces, create one agent per space
```

**If manifest exists:** Use it as the implementation checklist. Every agent, tool, evaluation question, and deployment configuration is pre-defined. Track completion against the manifest's `summary` counts.

**If manifest doesn't exist:** Fall back to self-discovery — inventory existing Genie Spaces from the catalog, create one agent per Genie Space, and use default evaluation criteria. This works but may miss specific tool definitions and cross-domain orchestration patterns the planning phase would have defined.

---

### Phase 1: Foundation (ResponsesAgent + Tracing)

**Load skill:** `responses-agent-patterns`

**Goal:** Create a working ResponsesAgent with MLflow tracing that loads in AI Playground.

**Artifacts produced:**
- Agent class inheriting from `ResponsesAgent`
- `predict()` and `predict_stream()` methods
- MLflow tracing with `@mlflow.trace` decorators
- OBO authentication with context detection

**Validate before proceeding:**
- [ ] Agent loads in AI Playground without errors
- [ ] Streaming responses work (delta + done events)
- [ ] Traces visible in MLflow Experiment UI
- [ ] No `signature` parameter in `log_model()`

### Phase 2: Data Access (Genie Spaces)

**Load skill:** `multi-agent-genie-orchestration`

**Goal:** Connect agent to Genie Spaces for structured data access with NO LLM fallback.

**Artifacts produced:**
- Genie Space configuration registry
- Conversation API integration (start_conversation_and_wait)
- Intent classification (domain routing)
- Parallel domain queries (ThreadPoolExecutor)
- Cross-domain response synthesis

**Validate before proceeding:**
- [ ] Genie queries return real data (not hallucinated)
- [ ] Multi-domain queries execute in parallel
- [ ] Error messages are explicit (no data fabrication)
- [ ] Intent classification routes correctly

### Phase 3: Memory (Lakebase)

**Load skill:** `lakebase-memory-patterns`

**Goal:** Add conversation continuity and user preferences.

**Artifacts produced:**
- Lakebase setup script (tables creation)
- CheckpointSaver integration with LangGraph
- DatabricksStore for long-term memory
- Memory tools for agent autonomy
- Graceful degradation (agent works without memory)

**Validate before proceeding:**
- [ ] thread_id returned in custom_outputs
- [ ] Multi-turn conversations maintain context
- [ ] Agent works without memory tables (graceful fallback)
- [ ] User preferences persist across sessions

### Phase 4: Prompt Management

**Load skill:** `prompt-registry-patterns`

**Goal:** Externalize prompts for runtime updates and A/B testing.

**Artifacts produced:**
- Unity Catalog agent_config table
- Prompt registration script
- Lazy loading in agent
- A/B testing (champion/challenger)

**Validate before proceeding:**
- [ ] Prompts loaded from Unity Catalog at runtime
- [ ] Fallback to embedded defaults if UC unavailable
- [ ] SQL injection prevented (escaped quotes)

### Phase 5: Evaluation

**Load skill:** `mlflow-genai-evaluation`

**Goal:** Set up pre-deployment evaluation with LLM judges.

**Artifacts produced:**
- Evaluation dataset (UC table)
- Built-in judges (Relevance, Safety, Guidelines)
- Custom domain-specific scorers
- Threshold configuration
- `_extract_response_text()` helper
- `_call_llm_for_scoring()` helper

**Validate before proceeding:**
- [ ] All custom scorers use `_extract_response_text()`
- [ ] Databricks SDK used for LLM calls (NOT langchain_databricks)
- [ ] 4-6 guidelines (not 8+)
- [ ] Metric aliases defined for backward compatibility

### Phase 6: Deployment

**Load skill:** `deployment-automation`

**Goal:** Automated deployment pipeline triggered by model version creation.

**Artifacts produced:**
- Deployment job YAML (Asset Bundle)
- Dataset linking with `mlflow.log_input()`
- Evaluation-then-promote workflow
- Three MLflow experiments (dev, eval, deploy)

**Validate before proceeding:**
- [ ] Job triggers on MODEL_VERSION_CREATED
- [ ] Dataset linked to evaluation runs
- [ ] Thresholds checked before promotion
- [ ] Model promoted with alias management

### Phase 7: Production Monitoring

**Load skill:** `production-monitoring`

**Goal:** Continuous quality monitoring with sampling-based scorers.

**Artifacts produced:**
- Registered scorers with sampling rates
- Custom heuristic scorers (fast, 100% sampling)
- Trace archival to Unity Catalog
- Monitoring dashboard queries

**Validate before proceeding:**
- [ ] Immutable pattern used (scorer = scorer.start())
- [ ] Safety at 100% sampling, expensive judges at 5-20%
- [ ] Trace archival enabled
- [ ] Dashboard queries return metrics

### Phase 8: Genie Optimization

**Load skill:** `@data_product_accelerator/skills/semantic-layer/05-genie-space-optimization/SKILL.md` (cross-domain)

**Goal:** Improve Genie Space accuracy and repeatability.

**Artifacts produced:**
- Accuracy/repeatability test scripts
- Control lever adjustments
- API update with array sorting
- Dual persistence (API + repository)

**Validate before proceeding:**
- [ ] Repeatability tested (3+ iterations per question)
- [ ] Dual persistence applied (API + repo)
- [ ] Arrays sorted before API updates
- [ ] Rate limiting in place (12+ seconds)

---

## Critical Anti-Patterns (NEVER Do These)

For the complete anti-patterns reference, see `references/anti-patterns.md`.

| Anti-Pattern | Consequence | Correct Pattern |
|---|---|---|
| Manual `signature` in `log_model()` | Breaks AI Playground | Let MLflow auto-infer |
| LLM fallback for data queries | Hallucinated fake data | Return explicit error messages |
| OBO in non-serving contexts | Permission errors | Context detection with env vars |
| Missing `_extract_response_text()` | All scorer scores = 0.0 | Universal extraction helper |
| `langchain_databricks` in scorers | Serverless failures | Databricks SDK |
| 8+ guidelines sections | Score = 0.20 | 4-6 focused guidelines |
| Missing metric aliases | Silent threshold bypass | Define aliases for MLflow versions |
| `scorer.start()` without assignment | Scorers don't start | `scorer = scorer.start()` |
| API-only Genie updates | Lost on redeployment | Dual persistence (API + repo) |
| Unsorted Genie API arrays | API rejection | Sort all arrays before PATCH |

---

## File Structure

For the recommended project file structure, see `references/file-structure.md`.

---

## Summary Validation Checklist

See `references/implementation-checklist.md` for the complete consolidated checklist covering all phases.

---

## Templates

- **Agent class template:** `assets/templates/agent-class-template.py`
- **Agent settings:** `assets/templates/agent-settings-template.py`

---

## References

### Official Documentation
- [Databricks Agent Framework](https://docs.databricks.com/en/generative-ai/agent-framework/)
- [MLflow ResponsesAgent](https://mlflow.org/docs/latest/genai/serving/responses-agent)
- [MLflow GenAI Evaluate](https://mlflow.org/docs/latest/llms/llm-evaluate/)
- [MLflow Tracing](https://mlflow.org/docs/latest/llms/tracing/index.html)
- [Genie Conversation API](https://learn.microsoft.com/en-us/azure/databricks/genie/conversation-api)
- [Production Monitoring](https://learn.microsoft.com/en-us/azure/databricks/mlflow3/genai/eval-monitor/production-monitoring)
- [Lakebase Documentation](https://docs.databricks.com/en/lakebase/)
- [Multi-Agent with Genie](https://docs.databricks.com/aws/en/generative-ai/agent-framework/multi-agent-genie)

### Dependency Skills
| Skill | Purpose |
|---|---|
| `responses-agent-patterns` | ResponsesAgent, streaming, tracing, OBO auth |
| `mlflow-genai-evaluation` | LLM judges, custom scorers, thresholds |
| `lakebase-memory-patterns` | CheckpointSaver, DatabricksStore, graceful degradation |
| `prompt-registry-patterns` | UC storage, MLflow versioning, A/B testing |
| `multi-agent-genie-orchestration` | Genie API, parallel queries, intent classification |
| `deployment-automation` | Deployment jobs, dataset linking, promotion |
| `production-monitoring` | Registered scorers, trace archival, dashboards |
| `mlflow-genai-foundation` | Core MLflow GenAI patterns (tracing, eval basics) |

### Troubleshooting
| Skill | Purpose |
|---|---|
| `common/databricks-autonomous-operations` | Deploy → Poll → Diagnose → Fix → Redeploy loop when jobs fail. Read when stuck during deployment or runtime errors. |

### Cross-Domain Dependencies
| Skill | Domain | Purpose |
|---|---|---|
| `semantic-layer/05-genie-space-optimization` | Semantic Layer | Accuracy testing, control levers, dual persistence |

---

## Pipeline Progression

**Previous stage:** `ml/00-ml-pipeline-setup` → ML models and experiments should be set up

**This is the final stage** in the standard pipeline progression. After completing GenAI agent implementation, the data platform is fully operational with:
- Bronze → Silver → Gold data pipeline
- Semantic layer (Metric Views, TVFs, Genie Spaces)
- Observability (Monitoring, Dashboards, Alerts)
- ML models and experiments
- GenAI agents with evaluation and deployment

---

## Version History

| Date | Version | Changes |
|---|---|---|
| Jan 27, 2026 | 1.0.0 | Initial skill creation from cursor rules 28, 30-35, context prompts, and implementation docs |
