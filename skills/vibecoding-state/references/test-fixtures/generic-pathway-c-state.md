# Vibecoding State — sample-retail-agent

<!--
Generic Pathway-C test fixture for the workshop hardening verification suite.
This fixture exercises every cross-cutting state-file shape (preflight,
endpoints, gate load-bearing checks, deferred actions, overrides, audit, spec
sections) with a hypothetical retail product-search agent. It must remain
fully generic (no domain-specific walkthrough vocabulary) — see
`tmp/workshop-hardening-verification.md` for the smoke checks that consume this
file.

variant_id: v4-agentapp-plus-appkit  (Pathway C — Custom Agent on Apps + separate AppKit)
-->

**Workshop:** sample-retail-agent
**Started:** 2026-04-20T15:00:00Z
**Last updated:** 2026-04-26T15:00:00Z

---

## Workshop Choices

- **use_case_slug:** `sample-retail-agent`
- **prd_path:** `example/sample-retail-agent/docs/design_prd.md`
- **pathway:** `C`
- **track:** `A`
- **dabs_bundle_path:** `example/sample-retail-agent/`
- **llm_endpoint:** `databricks-claude-sonnet-4-6`

---

## Pathway Applicability Matrix

| Module                          | A | B | C | D |
|---------------------------------|---|---|---|---|
| 0 — Infrastructure Setup        | opt | opt | req | req |
| 1 — Build App (scaffold+test)   | req | req | req | — |
| 2 — Deploy App (Analytics)      | req | req | req | — |
| 3 — Lakebase (setup+wire+E2E)   | — | req | req | — |
| 4 — Agent Foundation            | — | — | req | req |
| 5 — Agent Creation (track A/B/C) | — | — | req | req |
| 6 — Integrate Agent into App    | — | — | req | — |
| 7 — Agent SDLC Pipeline          | — | — | req | req |
| 8 — Capstone (optional)          | — | opt | opt | opt |

Legend: `req` = required, `opt` = optional, `—` = skip.

---

## Global Variables

- **APP_NAME:** `sample-retail-app`
- **AGENT_NAME:** `sample-retail-agent`
- **PROFILE:** `fevm-sample-retail`
- **Workspace URL:** `https://example-workspace.cloud.databricks.com`
- **Workspace host:** `example-workspace.cloud.databricks.com`
- **User email:** `operator@example.com`
- **workspace_serverless_only:** `true`
- **UC catalog:** `main`
- **UC schema (app):** `sample_retail`
- **UC schema (agent):** `sample_retail_agent`
- **UC schema (ops):** `sample_retail_ops`

---

## Captured Resource IDs

- **warehouse_id:** `01234567890abcde`
- **warehouse_name:** `Serverless Starter Warehouse`
- **llm_endpoint_ready:** `ready`
- **bundle_job_id:** `987654321012345`
- **last_successful_run_id:** `123456789098765`
- **last_verify_summary:** `{"catalog": "main", "schema": "sample_retail", "warehouse_id": "01234567890abcde", "pass": 6, "warn": 0, "fail": 0}`
- **terraform_exec_path:** `n/a`
- **terraform_version:** `n/a`
- **app_url:** `https://sample-retail-app-1234.databricksapps.com`
- **serving_endpoint_name:** `sample-retail-agent-endpoint`
- **ai_gateway_endpoint:** `n/a`
- **mlflow_experiment_path:** `/Users/operator@example.com/mlflow/sample-retail-app-agent`  <!-- /Users/<user_email>/mlflow/<APP_NAME>-agent -->
- **mlflow_feedback_experiment_path:** `/Users/operator@example.com/mlflow/sample-retail-app-feedback`  <!-- /Users/<user_email>/mlflow/<APP_NAME>-feedback -->
- **lakebase_project:** `sample-retail-lakebase`
- **lakebase_host:** `instance-sample-retail.database.cloud.databricks.com`
- **doc_qa_backend:** `n/a`
- **signoff_decision:** `pending`
- **prompt_iteration_ran:** `false`
- **capstone_done:** `false`

### Genie Spaces (0..N)

- `retail_orders_space` — id: `space_abc123` — title: `Retail Orders Explorer` — purpose: `Natural-language queries against orders + products tables`

### Vector Search Indexes (0..N)

- n/a

### Knowledge Assistants (0..N)

- n/a

### Custom `@function_tool` Tools (0..N)

- `get_product_recommendations` — writes_to: `read-only` — purpose: `Returns top-N similar products given an order context`

### External MCP Connections (0..N)

- n/a

---

## State Contract Audit

```yaml
last_run_at: 2026-04-26T15:00:00Z
mode: fail
fields_read_but_never_produced: []
fields_produced_but_not_in_schema: []
schema_fields_missing_from_template: []
captured_fields_with_no_consumer: []
productized_debts_status:
  total: 5
  lifted: 0
  parse_errors: 0
```

---

## LLM Role Endpoints

```yaml
llm_role_endpoints:
  agent_chat:
    candidates: ["databricks-claude-sonnet-4-6"]
    endpoint: databricks-claude-sonnet-4-6
    streaming_required: false
    selected_after_probe: true
    rationale: "Default Claude endpoint for in-app chat surface; single candidate."
  agent_chat_streaming_smoke:
    candidates: ["databricks-gpt-5-2", "databricks-gpt-5-mini", "databricks-meta-llama-3-3-70b-instruct"]
    endpoint: databricks-gpt-5-2
    streaming_required: true
    selected_after_probe: true
    rationale: "GPT-first non-chat role; streaming OK on first probe."
  reflection_lm:
    candidates: ["databricks-gpt-5-2", "databricks-gpt-5-mini", "databricks-meta-llama-3-3-70b-instruct"]
    endpoint: databricks-gpt-5-2
    min_context_chars: 80000
    selected_after_probe: true
    rationale: "GPT-first; long-context probe passed at 96K observed chars."
  llm_judge_default:
    candidates: ["databricks-gpt-5-mini", "databricks-gpt-5-2", "databricks-meta-llama-3-3-70b-instruct"]
    endpoint: databricks-gpt-5-mini
    selected_after_probe: true
    rationale: "GPT-first; mini judge sufficient for guideline scorers."
  failure_categorizer:
    candidates: ["databricks-gpt-5-mini", "databricks-gpt-5-2", "databricks-meta-llama-3-3-70b-instruct"]
    endpoint: databricks-gpt-5-mini
    selected_after_probe: true
    rationale: "GPT-first; categorization runs do not need full GPT-5."
```

---

## Endpoint Guardrail Audit

```yaml
endpoint_guardrail_audit:
  databricks-claude-sonnet-4-6:
    audited_at: 2026-04-20T15:30:00Z
    short_chat_ok: true
    long_context_ok: true
    sql_quote_ok: true
    streaming_arg_accepted: false
    input_guardrail_signature: "claude-default-input-v1"
    output_guardrail_signature: "claude-default-output-v1"
    accepted_min_context_chars: 180000
  databricks-gpt-5-2:
    audited_at: 2026-04-20T15:32:00Z
    short_chat_ok: true
    long_context_ok: true
    sql_quote_ok: true
    streaming_arg_accepted: true
    input_guardrail_signature: "gpt5-default-input-v1"
    output_guardrail_signature: "gpt5-default-output-v1"
    accepted_min_context_chars: 96000
```

---

## Bootstrap Preflight

```yaml
bootstrap_preflight:
  workspace_url_normalized: https://example-workspace.cloud.databricks.com
  workspace_url_was_placeholder: false
  workspace_profile: fevm-sample-retail
  workspace_host_auth_status: authenticated
  databricks_cli_version: "0.295.4"
  databricks_cli_min_version: "0.295.0"
  apps_quota:
    current_count: 3
    max_count: 10
    free_slots: 7
  bundle_dev_mode_schema_prefix_detected: false
  first_state_file_path: example/sample-retail-agent/.vibecoding-state.md
  app_name_known_at_bootstrap: false
  verify_summary_semantics:
    pass_field: "pass"
    warn_field: "warn"
    fail_field: "fail"
    warning_policy: "block_if_load_bearing"
```

---

## State File Set

```yaml
state_file_set:
  primary:
    path: apps_lakebase/sample-retail-app/.vibecoding-state.md
    owner: appkit
  secondary:
    path: agents/sample-retail-agent/.vibecoding-state.md
    owner: agent
    required_for_prompts: [appkit_agent_proxy, deployed_app_chat, deployed_app_trace_feedback]
  lookup_order: ["primary", "secondary"]
  conflict_policy: fail_on_conflict
```

---

## Canonical Names

```yaml
canonical_names:
  state_fields: {}
  env_vars:
    MLFLOW_EXPERIMENT_NAME: MLFLOW_EXPERIMENT_ID
    WAREHOUSE_ID: MLFLOW_TRACING_SQL_WAREHOUSE_ID
  jq_paths:
    apps_status_state: .app_status.state
  http_headers:
    x-forwarded-user-info: null
    x-forwarded-email: x-forwarded-email
    x-forwarded-preferred-username: x-forwarded-preferred-username
    x-forwarded-user: x-forwarded-user
    x-app-user-email: x-app-user-email
  prompt_registry:
    uri_scheme: prompts:/
    schema_field: uc_agent_schema
  eval_dataset_fields:
    expected_response: expected_response
    expected_signal: expected_signal
  label_schema_namespace_prefix: "sample_retail_agent_v1__"
  file_paths: {}
```

---

## State Overrides

```yaml
state_overrides: []
```

---

## Deferred Actions

```yaml
deferred_actions:
  - id: f2_grants_complete
    owner_prompt_role: experiment_tracing_foundation
    fix_owner_prompt_role: experiment_tracing_foundation
    target_prompt_roles: [deployed_app_trace_feedback]
    status: open
    divergence_check: "f2_grants_complete == true"
  - id: prompt16_column_grounding
    owner_prompt_role: local_eval_smoke
    fix_owner_prompt_role: local_eval_smoke
    target_prompt_roles: [first_scored_eval]
    status: open
    divergence_check: "mlflow_eval_known_quality_issues[id='unresolved_column'].status == 'resolved'"
  - id: registered_prompt_runtime_consumption
    owner_prompt_role: prompt_registry
    fix_owner_prompt_role: instruction_iteration
    target_prompt_roles: [instruction_iteration]
    status: open
    divergence_check: "agent_runtime_consumes_registered_prompt == true"
  - id: eval_dataset_expected_response
    owner_prompt_role: evaluation_dataset
    fix_owner_prompt_role: evaluation_dataset
    target_prompt_roles: [first_scored_eval]
    status: open
    divergence_check: "eval_dataset_fields.expected_response == 'present'"
  - id: labeling_session_dataset_enrichment
    owner_prompt_role: human_labeling
    fix_owner_prompt_role: human_labeling
    target_prompt_roles: [stakeholder_signoff]
    status: open
    divergence_check: "mlflow_labeling_session_dataset_enrichment_status == 'done'"
  - id: full_benchmark_candidate_reeval
    owner_prompt_role: instruction_iteration
    fix_owner_prompt_role: instruction_iteration
    target_prompt_roles: [production_registration]
    status: open
    divergence_check: "candidate_full_benchmark_reeval_status == 'passed'"
```

---

## MLflow Eval Known Quality Issues

```yaml
mlflow_eval_known_quality_issues: []
```

---

## Gate Load Bearing Checks

```yaml
gate_load_bearing_checks:
  - tool_warning
  - jq_path_returns_null
  - scorer_below_floor
  - dataset_coverage_below_floor
  - synthesized_stand_in
  - time_to_label_below_floor
  - open_deferred_action
  - open_known_quality_issue
  - bundle_validate_warning_load_bearing
```

---

## Productized Debts

```yaml
productized_debts:
  - name: workspace_sse_guardrail
    introduced_at_prompt_role: appkit_agent_proxy
    remove_when: "endpoint_guardrail_audit[llm_role_endpoints.agent_chat.endpoint].streaming_arg_accepted == true"
    debt_lifted: false
    audit_history: []
  - name: mlflow_make_judge_aggregations_default
    introduced_at_prompt_role: first_scored_eval
    remove_when: "mlflow_version >= '3.12.0' AND judges_with_silent_aggregation_dropouts == []"
    debt_lifted: false
    audit_history: []
  - name: predict_fn_input_guardrail_sentinel
    introduced_at_prompt_role: instruction_iteration
    remove_when: "endpoint_guardrail_audit[llm_role_endpoints.llm_judge_default.endpoint].sql_quote_ok == true"
    debt_lifted: false
    audit_history: []
  - name: predict_fn_api_connection_sentinel
    introduced_at_prompt_role: instruction_iteration
    remove_when: "agent.retry_policy.api_connection_error_max_retries >= 3"
    debt_lifted: false
    audit_history: []
  - name: predict_fn_sql_table_not_found_sentinel
    introduced_at_prompt_role: instruction_iteration
    remove_when: "mlflow_eval_known_quality_issues[id='unresolved_column'].status == 'resolved'"
    debt_lifted: false
    audit_history: []
```

---

## Preflight Check Registry

```yaml
preflight_check_registry:
  workspace_url_not_placeholder:
    owner: bootstrap
    blocks_prompt_roles: [bootstrap]
  workspace_profile_matches_host:
    owner: bootstrap
    blocks_prompt_roles: [bootstrap]
  databricks_cli_min_version:
    owner: vibecoding-state
    blocks_prompt_roles: [deploy_app, appkit_agent_proxy]
  databricks_apps_capacity:
    owner: deploy_app
    blocks_prompt_roles: [deploy_app]
  mlflow_tracing_sql_warehouse_id_present:
    owner: experiment_tracing_foundation
    blocks_prompt_roles: [trace_feedback, production_debug, monitoring]
  predict_fn_signature_matches_runner:
    owner: evaluation_runs
    blocks_prompt_roles: [local_eval_smoke, first_scored_eval]
  reflection_lm_large_context_probe:
    owner: instruction_iteration
    blocks_prompt_roles: [instruction_iteration]
  f2_grants_complete:
    owner: experiment_tracing_foundation
    blocks_prompt_roles: [deployed_app_trace_feedback, production_debug]
  lakebase_cold_start_retry_policy_present:
    owner: lakebase_memory
    blocks_prompt_roles: [deployed_app_chat, appkit_agent_proxy]
  system_prompt_review_complete:
    owner: first_scored_eval
    blocks_prompt_roles: [first_scored_eval]
```

---

## Evaluation Runs Preflight

```yaml
evaluation_runs_preflight:
  predict_fn_signature_matches_runner: false
  last_run_at: <pending>
```

---

## System Prompt Review

```yaml
system_prompt_review:
  complete: false
  reviewed_at: <pending>
  reviewed_by: <pending>
  must_do_worked_examples: []
  must_not_do_worked_examples: []
```

---

## Skill Helper Resolutions

```yaml
skill_helper_resolutions: []
```

---

## Per-Step Log

<!-- Per-step entries appended at runtime; intentionally empty in this fixture. -->

---

## Variant

```yaml
variant_id: "v4-agentapp-plus-appkit"
```

---

## Resources

```yaml
resources:
  tables:
    - full_name: "main.sample_retail_ops.orders"
      kind: "warehouse"
      key_columns: ["order_id", "customer_id"]
      approx_rows: "500K"
      refresh_cadence: "Daily"
      purpose: "Order header records used for product-search context."
    - full_name: "main.sample_retail_ops.products"
      kind: "warehouse"
      key_columns: ["product_id"]
      approx_rows: "50K"
      refresh_cadence: "Weekly"
      purpose: "Product catalog with category, price, and inventory."
  knowledge_bases: []
  genie_spaces:
    - name: "retail_orders_space"
      tables: ["orders", "products"]
      instructions: "Answer natural-language questions about orders and products. Always include the order_id when applicable."
      sample_questions:
        - "What were the top 10 products by revenue last month?"
        - "How many orders shipped to California in Q1 2026?"
        - "Which products are out of stock right now?"
  vector_indexes: []
  dabs_bundle:
    path: "example/sample-retail-agent/"
    setup_commands:
      - "databricks bundle deploy --target dev"
      - "databricks bundle run setup_infra"
  sample_data:
    required: true
    row_counts:
      orders: "500K"
      products: "50K"
    distribution_constraints: "Orders distributed across 12 months; products span 8 categories."
```

---

## UI

```yaml
ui:
  description: "Retail product-search assistant for ops staff who need quick, grounded answers about orders and inventory."
  personas:
    - name: "RetailOps"
      role_summary: "Operations analyst who triages order issues and inventory questions."
  pages: ["Overview", "Orders", "Products"]
  overview_widgets:
    - "kpi_cards(total_orders, revenue_last_30d, out_of_stock_count)"
  sql_files: ["overview.sql", "orders.sql", "products.sql"]
  user_journeys:
    - id: "J1"
      title: "Find slow-moving products"
      actor: "RetailOps"
      narrative: "Analyst asks the agent which products have not sold in the last 30 days and exports the list."
      artifacts_produced: ["ranked_table", "csv_file"]
    - id: "J2"
      title: "Investigate a customer order"
      actor: "RetailOps"
      narrative: "Analyst pastes an order_id and asks the agent for shipment status and related products."
      artifacts_produced: ["order_detail_card"]
```

---

## Agent

```yaml
agent:
  system_prompt: "You are a retail operations assistant. Always cite the table or tool that produced your answer. Refuse to speculate about pricing changes or inventory not present in the queried tables."
  tone_persona: "Concise, factual, and source-grounded. Speaks like a helpful ops analyst."
  must_do:
    - "Cite the source table or tool for every numeric claim."
    - "Include the order_id or product_id when answering item-specific questions."
    - "Acknowledge when the requested data is not in scope and offer the closest in-scope alternative."
  must_not_do:
    - "Do not invent products, SKUs, or prices that are not in the products table."
    - "Do not make policy recommendations about pricing or staffing."
  model: "databricks-claude-sonnet-4-6"
  auth_mode: "hybrid"
  capabilities:
    - "Query orders and products tables via Genie."
    - "Recommend related products via the get_product_recommendations function tool."
    - "Cite source tables in every answer."
  reviewer_role: "RetailOps"
  memory:
    provider: "lakebase"
    table_prefix: "app.chat"
  tools:
    - kind: "hosted"
      name: "Retail Orders Genie"
      surface: "python"
      io_contract: "natural_language_question -> sql_result_table"
      readonly: true
      hosted_type: "genie_space"
      resource_ref: "{genie_space_id}"
    - kind: "function"
      name: "get_product_recommendations"
      surface: "python"
      io_contract: "order_id -> ranked_product_list"
      readonly: true
      language: "python"
  mcp_servers: []
  knowledge_base_backend:
    preferred: "n/a"
    ka_source: "n/a"
    vs_fallback_index: "n/a"
  external_integrations:
    web_search_required: false
    external_connections: []
  benchmark_seeds:
    coverage_buckets: ["slow_moving_products", "order_lookup", "edge_cases"]
    seed_examples:
      - bucket: "slow_moving_products"
        prompt: "Which products had no orders in the last 30 days?"
        expected_signal: "ranked table with product_id + product_name + last_order_date, sourced from products + orders join."
      - bucket: "order_lookup"
        prompt: "What is the status of order ORD-12345?"
        expected_signal: "single-row card citing orders table with shipment status field."
```

---

## Governance

```yaml
governance:
  scorer_suite:
    guidelines:
      - name: "source_citation"
        text: "Cite the source table or tool for every numeric claim."
        threshold: 0.8
      - name: "id_inclusion"
        text: "Include the order_id or product_id when answering item-specific questions."
        threshold: 0.8
      - name: "scope_acknowledgement"
        text: "Acknowledge when the requested data is not in scope and offer the closest in-scope alternative."
        threshold: 0.8
    judge_questions:
      - name: "no_invented_products"
        text: "Does the response avoid inventing products, SKUs, or prices that are not in the products table?"
        threshold: 0.7
      - name: "no_policy_advice"
        text: "Does the response avoid making policy recommendations about pricing or staffing?"
        threshold: 0.7
    custom_scorer_rules: []
    primary_scorer: "source_citation"
    production_scorers:
      - name: "source_citation"
        sampling: 0.5
        threshold: 0.8
      - name: "no_invented_products"
        sampling: 0.5
        threshold: 0.7
  monitoring:
    required_alerts:
      - "source_citation_drift_neg_0_05_6h"
      - "liveness_zero_traces_15m"
    rollback_trigger_example: "source_citation < 0.80 over 24h window -> revert to previous @champion"
  verification:
    smoke_test_question: "Which products had no orders in the last 30 days?"
    smoke_test_cases:
      - "Slow-moving product lookup with citation"
      - "Single order_id status lookup"
      - "Out-of-scope question about staffing"
```

---

## Spec Provenance

```yaml
spec_provenance:
  resolved_at: "2026-04-20T15:00:00Z"
  resolver_version: "2.0"
  schema_version: "2.0"
  prd_sha256: "0000000000000000000000000000000000000000000000000000000000000000"
  llm_endpoint: "databricks-claude-sonnet-4-6"
```
