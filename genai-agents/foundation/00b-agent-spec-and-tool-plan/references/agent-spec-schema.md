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
  model: "databricks-claude-sonnet-4-6"
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
