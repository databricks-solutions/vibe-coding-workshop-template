# Agent Tool Plan Schema

`docs/agent_tool_plan.yaml` is the final selected runtime contract consumed by
Track A tool wiring.

```yaml
schema_version: "1.0"
source_agent_spec:
  path: "docs/agent_spec.yaml"
  sha256: "<computed hash>"
runtime_config:
  llm:
    provider: "databricks"
    endpoint: "databricks-claude-sonnet-4-6"  # SCALAR endpoint name copied from docs/agent_spec.yaml.agent.model.
                                              # NEVER write the literal YAML-path string "docs/agent_spec.yaml.agent.model"
                                              # here — see "Runtime Model Route Rules" below and prompt 39 (Pass 2).
    api_base_url: null
    api_mode: "databricks_openai_compatible"
    model_config:
      endpoint_key: "llm_endpoint"
      api_base_url_key: "llm_api_base_url"
      api_mode_key: "llm_api_mode"
selected_mcp_servers:
  - name: "sql_uc_schema_query"
    server_type: "sql"
    url_template: "{workspace_host}/api/2.0/mcp/sql"
    auth: "OBO"
    meta:
      warehouse_id: "{agent_sql_warehouse_id}"
    scope:
      catalog: "{agent_sql_catalog}"
      schema: "{agent_sql_schema}"
      allowed_tables: []
    readonly: true
selected_tools:
  - kind: "mcp"
    name: "sql_uc_schema_query"
    mcp_server_ref: "sql_uc_schema_query"
    surface: "python"
    io_contract: "natural language question -> read-only SQL result with table citations"
    readonly: true
    guardrails:
      allowed_statements: ["SELECT", "DESCRIBE", "EXPLAIN"]
      forbidden_statements: ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "MERGE", "TRUNCATE"]
      require_fully_qualified_names: true
knowledge_assistant:
  selected: false
  creation_required: false
  ka_source: "n/a"
resource_grants:
  app_yaml_oauth_scopes: ["sql"]
  databricks_yml:
    serving_endpoints:
      - name: "databricks-claude-sonnet-4-6"  # SCALAR endpoint name (same value as runtime_config.llm.endpoint).
                                              # NEVER write the literal YAML-path string here.
        permission: "CAN_QUERY"
    sql_warehouses:
      - warehouse_id: "{agent_sql_warehouse_id}"
        permission: "CAN_USE"
runtime_guardrails:
  sql_readonly_default: true
  require_tool_citations: true
verification:
  tool_smoke_tests:
    - tool_name: "sql_uc_schema_query"
      prompt: "Show five rows from an allowed table."
      expected_signal: "SELECT-only query with fully qualified table name."
```

## Runtime Model Route Rules

- Core workshop runs use `provider: "databricks"` and `api_base_url: null`.
- The `endpoint` value MUST be a **scalar Databricks serving-endpoint name** (e.g. `databricks-claude-sonnet-4-6`) copied from `docs/agent_spec.yaml.agent.model`. It MUST NOT be the literal YAML-path string `docs/agent_spec.yaml.agent.model` or `docs/agent_tool_plan.yaml.runtime_config.llm.endpoint` — those are file paths, not endpoint names. The same scalar value is reused verbatim in `resource_grants.databricks_yml.serving_endpoints[].name`.
- Prompt 39 (`agent_tool_selection`) generates these values; Pass 2 of the Agents Accelerator cleanup forbade writing YAML-path strings here. See [`apps_lakebase/prompts/sections/39-agent_tool_selection.md`](../../../../apps_lakebase/prompts/sections/39-agent_tool_selection.md) § *Placeholder Handling* and § *Runtime Model Route* for the canonical rule, and `vibecoding-state.hydrate_from_files` § *Post-hydration Guards* (Scalar endpoint guard) for the v3.0 defense-in-depth check.
- The nested `model_config` keys are the only keys Track A agent code may read from `ModelConfig`.
- AI Gateway is not required for the core workflow. A future or pre-provisioned Gateway route may set `provider: "ai_gateway"` and a non-null `api_base_url`, but no core prompt may create or configure AI Gateway.
