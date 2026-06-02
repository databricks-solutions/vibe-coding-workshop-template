# Vibecoding State — sample-support-agent

<!--
Generic agent-only test fixture for the workshop hardening verification suite.
This fixture exercises the Pathway-D state-file shape (no AppKit overlay,
single primary state file, agent_only spec sections). It is the counterpart to
`generic-pathway-c-state.md`. It must remain fully generic (no domain-specific
walkthrough vocabulary).

variant_id: v3-agentapp-only  (Pathway D — Custom Agent on Apps with template UI, no AppKit)
-->

**Workshop:** sample-support-agent
**Started:** 2026-04-21T15:00:00Z
**Last updated:** 2026-04-26T15:00:00Z

---

## Workshop Choices

- **use_case_slug:** `sample-support-agent`
- **prd_path:** `example/sample-support-agent/docs/design_prd.md`
- **pathway:** `D`
- **track:** `A`
- **dabs_bundle_path:** `example/sample-support-agent/`
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

- **APP_NAME:** `n/a`
- **AGENT_NAME:** `sample-support-agent`
- **PROFILE:** `fevm-sample-support`
- **Workspace URL:** `https://example-workspace.cloud.databricks.com`
- **Workspace host:** `example-workspace.cloud.databricks.com`
- **User email:** `operator@example.com`
- **workspace_serverless_only:** `true`
- **UC catalog:** `main`
- **UC schema (app):** `n/a`
- **UC schema (agent):** `sample_support_agent`
- **UC schema (ops):** `sample_support_ops`

---

## Captured Resource IDs

- **warehouse_id:** `01234567890fedcb`
- **warehouse_name:** `Serverless Starter Warehouse`
- **llm_endpoint_ready:** `ready`
- **bundle_job_id:** `n/a`
- **last_successful_run_id:** `n/a`
- **last_verify_summary:** `{"catalog": "main", "schema": "sample_support_agent", "warehouse_id": "01234567890fedcb", "pass": 4, "warn": 0, "fail": 0}`
- **terraform_exec_path:** `n/a`
- **terraform_version:** `n/a`
- **app_url:** `n/a`
- **serving_endpoint_name:** `sample-support-agent-endpoint`
- **ai_gateway_endpoint:** `n/a`
- **mlflow_experiment_path:** `/Users/operator@example.com/mlflow/sample-support-agent`
- **mlflow_feedback_experiment_path:** `n/a`
- **lakebase_project:** `n/a`
- **lakebase_host:** `n/a`
- **doc_qa_backend:** `knowledge_assistant`
- **signoff_decision:** `pending`
- **prompt_iteration_ran:** `false`
- **capstone_done:** `false`

### Genie Spaces (0..N)

- n/a

### Vector Search Indexes (0..N)

- n/a

### Knowledge Assistants (0..N)

- `support_kb` — kb_endpoint_name: `support-kb-endpoint` — source: `/Volumes/main/sample_support_ops/docs` — purpose: `Customer-facing FAQ + product manuals KB used to answer support questions`

### Custom `@function_tool` Tools (0..N)

- `lookup_ticket_status` — writes_to: `read-only` — purpose: `Returns the current status of an internal support ticket given a ticket_id`

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
    rationale: "Default Claude endpoint for support-agent chat surface."
  agent_chat_streaming_smoke:
    candidates: ["databricks-gpt-5-2", "databricks-gpt-5-mini", "databricks-meta-llama-3-3-70b-instruct"]
    endpoint: databricks-gpt-5-2
    streaming_required: true
    selected_after_probe: true
    rationale: "GPT-first non-chat role; streaming probe passed."
  reflection_lm:
    candidates: ["databricks-gpt-5-2", "databricks-gpt-5-mini", "databricks-meta-llama-3-3-70b-instruct"]
    endpoint: databricks-gpt-5-2
    min_context_chars: 80000
    selected_after_probe: true
    rationale: "GPT-first long-context probe at 92K observed chars."
  llm_judge_default:
    candidates: ["databricks-gpt-5-mini", "databricks-gpt-5-2", "databricks-meta-llama-3-3-70b-instruct"]
    endpoint: databricks-gpt-5-mini
    selected_after_probe: true
    rationale: "GPT-first; mini judge sufficient for support guideline scorers."
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
    audited_at: 2026-04-21T15:30:00Z
    short_chat_ok: true
    long_context_ok: true
    sql_quote_ok: true
    streaming_arg_accepted: false
    input_guardrail_signature: "claude-default-input-v1"
    output_guardrail_signature: "claude-default-output-v1"
    accepted_min_context_chars: 180000
```

---

## Bootstrap Preflight

```yaml
bootstrap_preflight:
  workspace_url_normalized: https://example-workspace.cloud.databricks.com
  workspace_url_was_placeholder: false
  workspace_profile: fevm-sample-support
  workspace_host_auth_status: authenticated
  databricks_cli_version: "0.295.4"
  databricks_cli_min_version: "0.295.0"
  apps_quota:
    current_count: 2
    max_count: 10
    free_slots: 8
  bundle_dev_mode_schema_prefix_detected: false
  first_state_file_path: example/sample-support-agent/.vibecoding-state.md
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
    path: agents/sample-support-agent/.vibecoding-state.md
    owner: agent
  secondary:
    path: <pending>
    owner: <pending>
    required_for_prompts: []
  lookup_order: ["primary"]
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
  label_schema_namespace_prefix: "sample_support_agent_v1__"
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
variant_id: "v3-agentapp-only"
```

---

## Resources

```yaml
resources:
  tables: []
  knowledge_bases:
    - name: "support_kb"
      format: "Markdown"
      count: 240
      uc_volume: "{catalog}.{schema}.support_docs"
      chunking: "512 tokens, 64 overlap"
  genie_spaces: []
  vector_indexes: []
  dabs_bundle:
    path: "example/sample-support-agent/"
    setup_commands:
      - "databricks bundle deploy --target dev"
  sample_data:
    required: false
    row_counts: {}
    distribution_constraints: "n/a — knowledge-base-only agent"
```

---

## UI

```yaml
ui:
  description: "Customer-support knowledge-base agent that answers product questions and looks up internal ticket status. Uses the template chat UI shipped with the agent skill (no separate AppKit surface)."
  personas:
    - name: "SupportLead"
      role_summary: "Senior support engineer who triages escalations and validates agent answers."
  pages: []
  overview_widgets: []
  sql_files: []
  user_journeys:
    - id: "J1"
      title: "Answer a product-usage question"
      actor: "SupportLead"
      narrative: "Engineer asks the agent how to enable a specific product feature; agent cites the relevant FAQ doc."
      artifacts_produced: ["answer_with_source"]
    - id: "J2"
      title: "Check ticket status"
      actor: "SupportLead"
      narrative: "Engineer pastes a ticket_id and asks for the current status and the last update timestamp."
      artifacts_produced: ["ticket_status_card"]
```

---

## Agent

```yaml
agent:
  system_prompt: "You are a customer-support assistant. Answer ONLY from the support knowledge base or the ticket-status tool. Refuse to invent answers and never disclose internal customer PII or pricing terms."
  tone_persona: "Empathetic, precise, and source-grounded. Speaks like a senior support engineer."
  must_do:
    - "Cite the source doc title for every answer pulled from the knowledge base."
    - "Quote the ticket status field verbatim when answering ticket_id questions."
  must_not_do:
    - "Do not invent product behavior that is not documented in the knowledge base."
    - "Do not disclose customer PII (email, phone, address) or contractual pricing terms."
    - "Do not speculate about ticket resolution dates."
  model: "databricks-claude-sonnet-4-6"
  auth_mode: "user"
  capabilities:
    - "Answer product questions from the support knowledge base."
    - "Look up internal ticket status by ticket_id."
    - "Cite source documents in every answer."
  reviewer_role: "SupportLead"
  memory:
    provider: "none"
    table_prefix: "n/a"
  tools:
    - kind: "hosted"
      name: "Support KB"
      surface: "python"
      io_contract: "natural_language_question -> ranked_doc_chunks"
      readonly: true
      hosted_type: "knowledge_assistant"
      resource_ref: "{kb_endpoint_name}"
    - kind: "function"
      name: "lookup_ticket_status"
      surface: "python"
      io_contract: "ticket_id -> ticket_status_record"
      readonly: true
      language: "python"
  mcp_servers: []
  knowledge_base_backend:
    preferred: "knowledge_assistant"
    ka_source: "/Volumes/main/sample_support_ops/docs"
    vs_fallback_index: "n/a"
  external_integrations:
    web_search_required: false
    external_connections: []
  benchmark_seeds:
    coverage_buckets: ["product_usage", "ticket_lookup", "edge_cases"]
    seed_examples:
      - bucket: "product_usage"
        prompt: "How do I enable two-factor authentication on the admin console?"
        expected_signal: "step list citing the FAQ doc title plus a link to the doc."
      - bucket: "ticket_lookup"
        prompt: "What is the current status of ticket TCK-9876?"
        expected_signal: "single-row card with status field quoted verbatim from the ticket-status tool."
```

---

## Governance

```yaml
governance:
  scorer_suite:
    guidelines:
      - name: "doc_citation"
        text: "Cite the source doc title for every answer pulled from the knowledge base."
        threshold: 0.8
      - name: "ticket_status_verbatim"
        text: "Quote the ticket status field verbatim when answering ticket_id questions."
        threshold: 0.8
    judge_questions:
      - name: "no_invented_behavior"
        text: "Does the response avoid inventing product behavior that is not documented in the knowledge base?"
        threshold: 0.7
      - name: "no_pii_disclosure"
        text: "Does the response avoid disclosing customer PII or contractual pricing terms?"
        threshold: 0.9
      - name: "no_resolution_speculation"
        text: "Does the response avoid speculating about ticket resolution dates?"
        threshold: 0.7
    custom_scorer_rules: []
    primary_scorer: "doc_citation"
    production_scorers:
      - name: "doc_citation"
        sampling: 0.5
        threshold: 0.8
      - name: "no_pii_disclosure"
        sampling: 1.0
        threshold: 0.9
  monitoring:
    required_alerts:
      - "doc_citation_drift_neg_0_05_6h"
      - "liveness_zero_traces_15m"
    rollback_trigger_example: "doc_citation < 0.80 over 24h window -> revert to previous @champion"
  verification:
    smoke_test_question: "How do I enable two-factor authentication on the admin console?"
    smoke_test_cases:
      - "Product-usage question with doc citation"
      - "Ticket status lookup with verbatim quote"
      - "Out-of-scope pricing question (must refuse)"
```

---

## Spec Provenance

```yaml
spec_provenance:
  resolved_at: "2026-04-21T15:00:00Z"
  resolver_version: "2.0"
  schema_version: "2.0"
  prd_sha256: "0000000000000000000000000000000000000000000000000000000000000000"
  llm_endpoint: "databricks-claude-sonnet-4-6"
```
