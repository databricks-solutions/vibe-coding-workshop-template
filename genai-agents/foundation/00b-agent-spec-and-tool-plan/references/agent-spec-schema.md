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
  must_do:
    - "<domain rule the agent must follow>"
  must_not_do:
    - "<domain rule the agent must refuse>"
  benchmark_seeds:
    coverage_buckets:
      - "<domain coverage bucket — e.g. 'policy compliance', 'edge case: empty input'>"
    seed_examples:
      - input: "<persona × user-journey natural-language input>"
        expectations: "<reference behavior the agent should produce>"
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
governance:
  llm_role_endpoints:
    llm_judge_default:
      endpoint: "databricks-claude-sonnet-4-6"  # role binding for every make_judge call
  scorer_suite:
    guidelines:
      - name: "<short name>"
        text: "<free-text rule that becomes a Guidelines scorer>"
        threshold: 0.8
    custom_scorer_rules:
      - name: "<short name>"
        rule: "<deterministic check — regex / numeric / schema>"
    judge_questions:
      - name: "<short name>"
        question: "<domain quality question evaluated by an LLM judge>"
        threshold: 0.8
  verification:
    smoke_test_cases:
      - input: "<domain smoke prompt>"
        expectations: "<observable success signal>"
```

## Eval / Governance Field Rules

The Agent Spec is **tool-agnostic.** Tools are not selected until the Tool Plan (`docs/agent_tool_plan.yaml`, prompt 39). Every eval/governance field in the Spec is shaped by the use case (industry, personas, capabilities, journeys) — never by tool families.

- `agent.must_do[]` / `agent.must_not_do[]` — domain rules. Live under `agent.*` (NOT under `governance.*`); section 49 (prompt registry) registers them as UC prompt assets and section 52's preflight reads them.
- `agent.benchmark_seeds.coverage_buckets[]` — domain coverage labels (e.g. "policy compliance", "edge case: empty input"). NOT tool-shaped (no "Genie query bucket"). Section 50 expands these into ≥20 benchmark rows.
- `agent.benchmark_seeds.seed_examples[]` — `{input, expectations}` per persona × user-journey crossing. Use the actual personas from `agent.target_personas[]` and journeys from `app_spec.ui.user_journeys[]`. Section 50 augments this set with tool-shaped rows from the Tool Plan's `verification.tool_smoke_tests[]` at run time.
- `governance.scorer_suite.guidelines[]` — free-text rules → become Guidelines scorers (section 51, family 2).
- `governance.scorer_suite.custom_scorer_rules[]` — deterministic Python `@scorer` checks (section 51, family 3).
- `governance.scorer_suite.judge_questions[]` — LLM judge questions, domain-shaped (section 51, family 4). Routed through `governance.llm_role_endpoints.llm_judge_default.endpoint`, never the raw model endpoint.
- `governance.verification.smoke_test_cases[]` — domain smoke flow consumed by section 46's smoke gate (the single fail-closed gate that closes Track A).

**Forbidden in the Spec:**

- ❌ Tool-shaped scorer entries (`ka_citation_present`, `RetrievalGroundedness`, `genie_sql_correctness`, `sql_readonly_compliance`) — these belong in the Tool Plan's `runtime_guardrails.tool_shaped_scorers[]` and are derived mechanically from `selected_tools[]`.
- ❌ Tool-specific assertions in `seed_examples[]` or `smoke_test_cases[]` (e.g. "use Genie to look up X", "expect a KA citation"). Spec inputs are natural language; tool exercise lives in the Plan's `verification.tool_smoke_tests[]`.
- ❌ Predicting tool selections in any field. Section 38's IMPORTANT-READ-FIRST block explicitly forbids this.

## Model Field Rules

- `agent.model` is required.
- The value is the raw/backing Databricks model serving endpoint name for the agent.
- Default is `databricks-claude-sonnet-4-6`.
- Prompt generators should ask the user for `agent_model`; if absent, use the default.
- Do not put AI Gateway endpoint names, provider labels, or vague model family labels in `agent.model`.
- Downstream Track A code must not read `agent.model` directly from Python. The Tool Plan converts this value into `runtime_config.llm`, and the agent consumes that through `ModelConfig`.
