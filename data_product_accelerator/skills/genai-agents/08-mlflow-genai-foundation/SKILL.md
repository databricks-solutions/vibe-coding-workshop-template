---
name: mlflow-genai-foundation
description: Core MLflow 3.0 GenAI patterns for Databricks agents - model signatures, tracing fundamentals, evaluation basics, prompt registry basics. Foundational patterns shared across all agent skills. Triggers on "MLflow GenAI", "MLflow 3.0", "model signature", "autolog", "mlflow.trace".
metadata:
  author: prashanth subrahmanyam
  last_verified: "2026-02-07"
  volatility: high
  domain: genai-agents
  role: worker
  pipeline_stage: 9
  pipeline_stage_name: genai-agents
  upstream_sources:
    - name: "ai-dev-kit"
      repo: "databricks-solutions/ai-dev-kit"
      paths:
        - "databricks-skills/databricks-agent-bricks/SKILL.md"
      relationship: "extended"
      last_synced: "2026-02-19"
      sync_commit: "97a3637"
---

# MLflow GenAI Foundation Patterns

## When to Use

Use this skill when:
- Creating new Databricks GenAI agents
- Implementing MLflow tracing for agents
- Setting up agent evaluation pipelines
- Managing prompts with MLflow Prompt Registry
- Troubleshooting AI Playground compatibility issues
- Understanding foundational MLflow GenAI concepts

---

## ⚠️ CRITICAL: ResponsesAgent is MANDATORY for AI Playground

**Databricks recommends `ResponsesAgent` over `ChatAgent` for all new agents.**

Without proper model signatures, your agent will **NOT work** in AI Playground, Agent Evaluation, or Mosaic AI features.

**Key Points:**
- `ResponsesAgent` automatically infers compatible model signatures
- Manual signatures break AI Playground compatibility
- Use `input` key (not `messages`) in input examples
- Return `ResponsesAgentResponse` objects (not dicts)

**See:** [responses-agent-patterns skill](../responses-agent-patterns/SKILL.md) for complete implementation guide.

---

## ⚠️ CRITICAL: NO LLM Fallback for Data Queries

**When an agent uses Genie Spaces or data retrieval tools, NEVER fall back to LLM when tools fail.**

**Why:** LLM fallback generates **hallucinated fake data** that looks real but is completely fabricated.

**Correct Pattern:**
- Return explicit error messages when tools fail
- Include "I will NOT generate fake data" statement
- Log errors to trace spans for visibility

**See:** [multi-agent-genie-orchestration skill](../multi-agent-genie-orchestration/SKILL.md) for complete pattern.

---

## Model Signatures Overview

### Why Signatures Matter

> "Azure Databricks uses **MLflow Model Signatures** to define agents' input and output schema. Product features like the **AI Playground assume that your agent has one of a set of supported model signatures**."
> — [Microsoft Docs](https://learn.microsoft.com/en-us/azure/databricks/generative-ai/agent-framework/create-agent)

### The Golden Rule

> "If you follow the **recommended approach to authoring agents**, MLflow will **automatically infer a signature** for your agent that is compatible with Azure Databricks product features, with **no additional work required** on your part."
> — [Microsoft Docs](https://learn.microsoft.com/en-us/azure/databricks/generative-ai/agent-framework/create-agent)

### What Breaks Compatibility

| Issue | Impact |
|---|---|
| Manual signature with wrong schema | ❌ AI Playground won't load |
| `PythonModel` instead of `ResponsesAgent` | ❌ No signature inference |
| `messages` input instead of `input` | ❌ Request format mismatch |
| Legacy dict output instead of `ResponsesAgentResponse` | ❌ Response parsing fails |

See [Model Signatures](references/model-signatures.md) for detailed explanation.

---

## Tracing Fundamentals

### Automatic Tracing with autolog

Enable autolog at module level for automatic tracing:

```python
import mlflow

# At the TOP of your main module
mlflow.langchain.autolog(
    log_models=True,
    log_input_examples=True,
    log_model_signatures=True,
    log_inputs=True
)
```

### Manual Tracing with Decorators

Use `@mlflow.trace` for custom functions:

```python
import mlflow

@mlflow.trace(name="my_function", span_type="AGENT")
def my_agent_function(query: str) -> dict:
    """Function is automatically traced."""
    result = process(query)
    return result
```

### Manual Span Creation

For fine-grained control:

```python
import mlflow

def complex_operation(data):
    with mlflow.start_span(name="outer_operation") as span:
        span.set_inputs({"data": data})
        
        with mlflow.start_span(name="inner_step", span_type="LLM") as inner:
            inner.set_inputs({"prompt": "..."})
            result = llm.invoke(...)
            inner.set_outputs({"response": result})
        
        span.set_outputs({"result": result})
        span.set_attributes({"custom_metric": 0.95})
    
    return result
```

See [Tracing Patterns](references/tracing-patterns.md) for complete guide.

---

## Evaluation Basics

### Built-in Scorers

```python
from mlflow.metrics.genai import relevance, safety, Guidelines

results = mlflow.genai.evaluate(
    model=agent,
    data=evaluation_data,
    scorers=[
        Relevance(),
        Safety(),
        GuidelinesAdherence(guidelines=[
            "Include time context",
            "Format costs as USD",
            "Cite sources"
        ])
    ]
)
```

### Custom Scorers with @scorer

```python
from mlflow.genai import scorer, Score

@scorer
def custom_judge(inputs: dict, outputs: dict, expectations: dict = None) -> Score:
    """Custom judge for domain-specific accuracy."""
    response_text = _extract_response_text(outputs)  # Helper required
    score_value = calculate_score(response_text)
    
    return Score(
        value=score_value,
        rationale="Explanation of score"
    )
```

### Production Monitoring

Use `mlflow.genai.assess()` for real-time assessment:

```python
assessment = mlflow.genai.assess(
    inputs={"query": query},
    outputs={"response": response},
    scorers=[Relevance(), Safety()]
)

if assessment.scores["relevance"] < 0.6:
    trigger_quality_alert()
```

See [Evaluation Basics](references/evaluation-basics.md) for complete guide.

---

## Prompt Registry Basics

### Log Prompts

```python
import mlflow.genai

mlflow.genai.log_prompt(
    prompt="""You are a helpful assistant.
    
User context: {user_context}
Query: {query}""",
    artifact_path="prompts/assistant",
    registered_model_name="my_app_assistant_prompt"
)
```

### Load Prompts by Alias

```python
# Load production prompt
prompt = mlflow.genai.load_prompt(
    "prompts:/my_app_assistant_prompt/production"
)

# Load by version
prompt_v1 = mlflow.genai.load_prompt(
    "prompts:/my_app_assistant_prompt/1"
)
```

### Set Aliases

```python
from mlflow import MlflowClient

client = MlflowClient()

client.set_registered_model_alias(
    name="my_app_assistant_prompt",
    alias="production",
    version="2"
)
```

See [Prompt Registry Basics](references/prompt-registry-basics.md) for complete guide.

---

## Agent Logging Patterns

### ResponsesAgent (Recommended)

```python
import mlflow
from mlflow.pyfunc import ResponsesAgent

agent = MyResponsesAgent()

# CRITICAL: Set model before logging
mlflow.models.set_model(agent)

# Input example in ResponsesAgent format
input_example = {
    "input": [{"role": "user", "content": "What is the status?"}]
}

with mlflow.start_run():
    # DO NOT pass signature parameter - auto-inferred!
    mlflow.pyfunc.log_model(
        artifact_path="agent",
        python_model=agent,
        input_example=input_example,
        # signature=...  # ❌ NEVER include this!
        registered_model_name="my_agent",
        pip_requirements=[
            "mlflow>=3.0.0",
            "databricks-sdk>=0.28.0",
        ],
    )
```

**See:** [responses-agent-patterns skill](../responses-agent-patterns/SKILL.md) for complete implementation.

---

## Common Mistakes Quick Reference

| Mistake | Impact | Fix |
|---------|--------|-----|
| Using `PythonModel` instead of `ResponsesAgent` | ❌ No signature inference | Use `ResponsesAgent` |
| Manual signature definition | ❌ Breaks AI Playground | Let MLflow auto-infer |
| Using `messages` instead of `input` | ❌ Format mismatch | Use `input` key |
| Returning dict instead of `ResponsesAgentResponse` | ❌ Parsing fails | Return `ResponsesAgentResponse` |
| Missing `set_model()` before `log_model()` | ⚠️ May fail | Call `set_model()` first |
| LLM fallback for data queries | ❌ Hallucinated data | Return explicit errors |

---

## Validation Checklist

### 🔴 ResponsesAgent & Model Signatures (CRITICAL)
- [ ] Agent class inherits from `mlflow.pyfunc.ResponsesAgent`
- [ ] `predict` method accepts single `request` parameter
- [ ] `predict` returns `ResponsesAgentResponse` object
- [ ] Input example uses `input` key (NOT `messages`)
- [ ] **NO `signature` parameter** in `log_model()` call
- [ ] Agent loads successfully in AI Playground

### Tracing
- [ ] `mlflow.langchain.autolog()` enabled at module level
- [ ] All custom functions decorated with `@mlflow.trace`
- [ ] Span types specified (AGENT, LLM, TOOL, etc.)
- [ ] Inputs and outputs set for manual spans
- [ ] Traces tagged with user_id, session_id, environment

### Evaluation
- [ ] Built-in scorers used where appropriate
- [ ] Custom judges return `Score` objects
- [ ] Evaluation metrics logged to MLflow
- [ ] Production monitoring with `assess()` implemented

### Prompts
- [ ] All prompts logged to registry
- [ ] Production alias set for deployment
- [ ] Prompts loaded by alias in production code

### Agent Logging
- [ ] `ResponsesAgent` interface implemented (not ChatAgent)
- [ ] `set_model()` called before `log_model()`
- [ ] Model registered with proper name
- [ ] Aliases set for dev/staging/production

---

## References

- [Model Signatures](references/model-signatures.md) - Why signatures matter, AI Playground compatibility
- [Tracing Patterns](references/tracing-patterns.md) - autolog, decorators, manual spans
- [Evaluation Basics](references/evaluation-basics.md) - Built-in scorers, custom judges, production monitoring
- [Prompt Registry Basics](references/prompt-registry-basics.md) - Logging, loading, aliases

### Official Documentation
- [Model Signatures for Databricks Features (CRITICAL)](https://learn.microsoft.com/en-us/azure/databricks/generative-ai/agent-framework/create-agent#understand-model-signatures-to-ensure-compatibility-with-azure-databricks-features)
- [MLflow GenAI Concepts](https://docs.databricks.com/aws/en/mlflow3/genai/concepts/)
- [MLflow Tracing](https://docs.databricks.com/aws/en/mlflow3/genai/tracing/)
- [MLflow Scorers](https://docs.databricks.com/aws/en/mlflow3/genai/eval-monitor/concepts/scorers)
- [Prompt Registry](https://docs.databricks.com/aws/en/mlflow3/genai/prompt-version-mgmt/prompt-registry/)

### Related Skills
- [responses-agent-patterns](../responses-agent-patterns/SKILL.md) - Complete ResponsesAgent implementation
- [multi-agent-genie-orchestration](../multi-agent-genie-orchestration/SKILL.md) - NO LLM fallback pattern
- [mlflow-genai-evaluation](../mlflow-genai-evaluation/SKILL.md) - Advanced evaluation patterns
