# Agent Spec Schema

`docs/agent_spec.yaml` is a design artifact. It recommends agent capabilities
and tools before Databricks resources are created.

```yaml
schema_version: "1.0"
source_prd:
  path: "docs/design_prd.md"
  sha256: "<computed hash>"
agent:
  name: "<derived agent name>"
  purpose: "<one paragraph>"
  target_personas:
    - name: "<persona name>"
      needs: ["<need>"]
  system_prompt: "<draft prompt>"
  capabilities:
    - "<capability>"
  model: "databricks-claude-sonnet-4-6"  # Databricks serving endpoint name; user-overridable via agent_model
  auth_mode: "hybrid"
  memory:
    provider: "lakebase"
    thread_state: true
    long_term_recall: true
tool_recommendations:
  managed_databricks:
    - name: "sql_uc_schema_query"
      server_type: "sql"
      reason: "Query existing Unity Catalog tables without building Genie first."
      selected_by_default: true
  external:
    - name: "<external mcp name>"
      provider: "<provider>"
      reason: "<why it helps>"
      integration_method: "managed_oauth | marketplace | custom_http | dcr | not_supported"
      selected_by_default: false
mcp_research:
  mode: "none | managed_only | web_research"
  candidates:
    - name: "<candidate>"
      source_url: "<url>"
      confidence: "high | medium | low"
knowledge_assistant:
  recommended: true
  reason: "<why KA is useful or why it is skipped>"
  source_strategy: "pre_staged | local_dir | prd_generated | n/a"
evaluation:
  smoke_test_cases:
    - "<question>"
  benchmark_seed_examples:
    - prompt: "<question>"
      expected_signal: "<what good looks like>"
governance:
  must_do:
    - "<rule>"
  must_not_do:
    - "<rule>"
  scorer_guidelines:
    - name: "<name>"
      text: "<guideline>"
      threshold: 0.8
```

## Model Field Rules

- `agent.model` is required.
- The value is the raw/backing Databricks model serving endpoint name for the agent.
- Default is `databricks-claude-sonnet-4-6`.
- Prompt generators should ask the user for `agent_model`; if absent, use the default.
- Do not put AI Gateway endpoint names, provider labels, or vague model family labels in `agent.model`.
- Downstream Track A code must not read `agent.model` directly from Python. The Tool Plan converts this value into `runtime_config.llm`, and the agent consumes that through `ModelConfig`.
