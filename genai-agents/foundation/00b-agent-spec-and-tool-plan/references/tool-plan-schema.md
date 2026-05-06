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
  tool_shaped_scorers:                        # derived mechanically from selected_tools[] — see Tool-shaped Derivation
    - "sql_readonly_compliance"
    - "sql_fully_qualified_names"
verification:
  tool_smoke_tests:                            # REQUIRED — one entry per selected_tools[] entry
    - tool_name: "sql_uc_schema_query"
      prompt: "Show five rows from an allowed table."
      expected_signal: "SELECT-only query with fully qualified table name."
```

## Tool-shaped Derivation Rules

`verification.tool_smoke_tests[]` and `runtime_guardrails.tool_shaped_scorers[]` are **mechanically derived from `selected_tools[]`** by prompt 39 (`agent_tool_selection`). The Spec contains no tool-shaped fields — those live here, in the Plan, where the actual selection is known.

### Per-tool smoke test contract

For every entry in `selected_tools[]`, prompt 39 emits one entry under `verification.tool_smoke_tests[]`:

```yaml
- tool_name: "<selected_tools[].name>"
  prompt: "<use-case query that exercises this specific tool>"
  expected_signal: "<observable success signal — TOOL span present, citation present, valid SQL, etc.>"
```

The `prompt` is shaped by the use case (industry, capabilities, schema names) — never a generic placeholder like "list 5 rows". Tool families with no entry in `selected_tools[]` contribute zero smoke tests.

### Tool-shaped scorer mapping

Prompt 39 walks `selected_tools[]` and emits the union (deduped) of these contributions to `runtime_guardrails.tool_shaped_scorers[]`:

| Selected tool family | Scorer hints to add |
|---|---|
| Knowledge Assistant | `ka_citation_present`, `RetrievalGroundedness` |
| Vector Search (managed MCP) | `RetrievalGroundedness` (deduped if KA already added it) |
| Genie | `genie_sql_correctness`, `genie_response_grounded_in_table` |
| SQL MCP | `sql_readonly_compliance`, `sql_fully_qualified_names` |
| UC Functions | `uc_function_signature_match` |
| External MCP (per descriptor) | one entry per high-confidence descriptor (`mcp_research.candidates[].confidence == high` AND selected) |

Tool families absent from `selected_tools[]` (or with `selected: false`) contribute nothing. Section 51 (`mlflow_scorers_and_judges`) reads `runtime_guardrails.tool_shaped_scorers[]` and registers these as additional scorers on top of the generic `governance.scorer_suite.*` registered from the Spec. `RetrievalGroundedness` is therefore registered ONLY if a retrieval tool (KA or Vector Search) appears in `selected_tools[]` — never by default.

### Consumer union semantics

| Consumer prompt | Generic source (Spec) | Tool-shaped source (Plan) | Behavior |
|---|---|---|---|
| 46 (smoke eval + deploy) | `governance.verification.smoke_test_cases[]` | `verification.tool_smoke_tests[]` | Smoke set = union |
| 50 (eval datasets) | `agent.benchmark_seeds.seed_examples[]` (≥20 rows) | `verification.tool_smoke_tests[]` (≥1 row each) | Append |
| 51 (scorers and judges) | `governance.scorer_suite.{guidelines, custom_scorer_rules, judge_questions}` | `runtime_guardrails.tool_shaped_scorers[]` | Union, deduped |
| 52 (first scored eval) | `agent.must_do[]` / `agent.must_not_do[]` for preflight; benchmark table | `selected_tools[]` for failure-shape routing | Failure-shape `tool_call_empty` only fires for tools in `selected_tools[]` |

## Runtime Model Route Rules

- Core workshop runs use `provider: "databricks"` and `api_base_url: null`.
- The `endpoint` value MUST be a **scalar Databricks serving-endpoint name** (e.g. `databricks-claude-sonnet-4-6`) copied from `docs/agent_spec.yaml.agent.model`. It MUST NOT be the literal YAML-path string `docs/agent_spec.yaml.agent.model` or `docs/agent_tool_plan.yaml.runtime_config.llm.endpoint` — those are file paths, not endpoint names. The same scalar value is reused verbatim in `resource_grants.databricks_yml.serving_endpoints[].name`.
- Prompt 39 (`agent_tool_selection`) generates these values; Pass 2 of the Agents Accelerator cleanup forbade writing YAML-path strings here. See [`apps_lakebase/prompts/sections/39-agent_tool_selection.md`](../../../../apps_lakebase/prompts/sections/39-agent_tool_selection.md) § *Placeholder Handling* and § *Runtime Model Route* for the canonical rule, and `vibecoding-state.hydrate_from_files` § *Post-hydration Guards* (Scalar endpoint guard) for the v3.0 defense-in-depth check.
- The nested `model_config` keys are the only keys Track A agent code may read from `ModelConfig`.
- AI Gateway is not required for the core workflow. A future or pre-provisioned Gateway route may set `provider: "ai_gateway"` and a non-null `api_base_url`, but no core prompt may create or configure AI Gateway.
