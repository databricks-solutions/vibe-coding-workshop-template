# Vibecoding State — sample-agents-accelerator (hydrated)

<!--
Test fixture for the Agents Accelerator visible path (Pass 3 + 3.5).

This fixture demonstrates a state file produced by
`vibecoding-state.hydrate_from_files` (resolver_version "3.0") rather than by
the LLM-driven `vibecoding-state.resolve_spec` (resolver_version "2.0"). The
workshop ran prompt 40 (`uc_resources_foundation`) on a use-case where no
Lakehouse / Data Intelligence track produced `## Resources`, so:

- `## Spec Provenance` carries `resolver_version: "3.0"` and
  `hydrated_from_files: true`.
- `## Resources` is stamped `optional: true` with
  `mark_skipped: "no Lakehouse track"`.
- `## Agent.agent.tools[]` is populated by the hydrator's tool-projection
  rule (see `hydrator-prompt.md` § *Worked Example — Tool Projection*):
  `tool_recommendations[]` from the Agent Spec is overlaid by
  `selected_tools[]` from the Tool Plan; binding selection wins over
  loose recommendation.

variant_id: v4-agentapp-plus-appkit  (Pathway A — Custom Agent on Apps + AppKit)

This fixture intentionally keeps Workshop Choices, Pathway Applicability,
Global Variables, and Per-Step Log empty/abbreviated; the test surfaces are
`## Spec Provenance`, `## Resources`, and `## Agent`.
-->

**Workshop:** sample-agents-accelerator
**Started:** 2026-04-29T19:55:00Z
**Last updated:** 2026-04-29T20:00:00Z

---

## Workshop Choices

- **use_case_slug:** `sample-agents-accelerator`
- **prd_path:** `docs/design_prd.md`
- **pathway:** `A`
- **track:** `A-custom-agent-apps`
- **dabs_bundle_path:** `n/a`
- **llm_endpoint:** `databricks-claude-sonnet-4-6`

---

## Variant

```yaml
variant_id: "v4-agentapp-plus-appkit"
```

---

## Resources

```yaml
resources:
  optional: true
  mark_skipped: "no Lakehouse track"
  tables: []
  knowledge_bases: []
  genie_spaces: []
  vector_indexes: []
  dabs_bundle:
    path: "n/a"
    setup_commands: []
  sample_data:
    required: false
    row_counts: {}
    distribution_constraints: "n/a"
```

---

## UI

```yaml
ui:
  description: "Internal support assistant embedded in an AppKit dashboard."
  personas:
    - name: "Support Lead"
      role_summary: "Triages incoming tickets and routes to specialists."
  pages: ["Overview", "Tickets"]
  overview_widgets: []
  sql_files: []
  user_journeys:
    - id: "J1"
      title: "Triage open tickets"
      actor: "Support Lead"
      narrative: "Open the dashboard, ask the agent to summarize today's incoming tickets, and route the top three."
      artifacts_produced: ["ranked_table"]
```

---

## Agent

```yaml
agent:
  system_prompt: |
    You are a professional support triage assistant. Cite the source table for
    every data answer and never execute DDL.
  tone_persona: "Professional support triage assistant."
  must_do:
    - "Cite the source table for every data answer."
    - "Show intermediate results before the final synthesis."
  must_not_do:
    - "Execute DDL."
    - "Fabricate ticket metadata."

  model: "databricks-claude-sonnet-4-6"   # scalar endpoint name copied from
                                          # docs/agent_spec.yaml.agent.model
  auth_mode: "hybrid"

  capabilities:
    - "Summarize today's open tickets."
    - "Route a ticket to a specialist queue."
  reviewer_role: "Support Lead"

  memory:
    provider: "lakebase"
    table_prefix: "app.chat"

  # Tool projection rule (hydrate_from_files):
  #   a. Seeded from docs/agent_spec.yaml.tool_recommendations.managed_databricks[]
  #   b. Overlaid by docs/agent_tool_plan.yaml.selected_tools[] (binding wins)
  #   c. Families absent from BOTH spec and plan are NOT written here.
  tools:
    - kind: "mcp"
      name: "sql_uc_schema_query"
      mcp_server_ref: "sql_uc_schema_query"
      surface: "python"
      io_contract: "natural language question -> read-only SQL result with table citations"
      readonly: true

  mcp_servers:
    - name: "sql_uc_schema_query"
      server_type: "sql"
      resource_ref: "{agent_sql_catalog}.{agent_sql_schema}"
      auth: "OBO"
      purpose: "Query existing UC tables read-only."

  knowledge_base_backend:
    preferred: "n/a"
    ka_source: "n/a"
    vs_fallback_index: "n/a"

  external_integrations:
    web_search_required: false
    external_connections: []

  benchmark_seeds:
    coverage_buckets: ["triage", "routing", "edge_cases"]
    seed_examples:
      - bucket: "triage"
        prompt: "What are today's three most urgent open tickets?"
        expected_signal: "ranked table with source table citation + today's date"
      - bucket: "routing"
        prompt: "Route ticket 12345 to the right specialist queue."
        expected_signal: "queue name with rationale citing ticket fields"
```

---

## Governance

```yaml
governance:
  scorer_suite:
    guidelines:
      - name: "source_citation"
        text: "Cite the source table for every data answer."
        threshold: 0.8
    judge_questions: []
    custom_scorer_rules: []
    primary_scorer: "source_citation"
    production_scorers: []
  monitoring:
    required_alerts: []
    rollback_trigger_example: "n/a"
  verification:
    smoke_test_question: "What are today's three most urgent open tickets?"
    smoke_test_cases:
      - "Summarize today's open tickets."
      - "Route ticket 12345 to the right queue."
      - "List tickets that breached SLA in the last 24 hours."
```

---

## Spec Provenance

```yaml
spec_provenance:
  resolved_at: "2026-04-29T20:00:00Z"
  resolver_version: "3.0"        # set by vibecoding-state.hydrate_from_files
  schema_version: "2.0"
  prd_sha256: "<computed>"
  llm_endpoint: "n/a"            # hydration does not call an LLM
  hydrated_from_files: true
```

---

## Per-Step Log

(empty — this is a fixture for the post-hydration shape, not a recorded run)
