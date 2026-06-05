# Hydrator Prompt — `vibecoding-state.hydrate_from_files` (v3.0)

The `hydrate_from_files` operation runs this prompt **once** per workshop, from
prompt 40 (`uc_resources_foundation`) on the Agents Accelerator visible path,
right after `op enter` succeeds and before any UC schema or volume is created.

The hydrator is **LLM-first, file-as-source-of-truth**:

- The caller passes five paths: `agent_spec_yaml`, `agent_tool_plan_yaml`,
  `ui_design_md`, `prd_path`, and `state_path`. The four `docs/*` files were
  produced by prompts 38, 39, 04, and 03 respectively. The fifth is the live
  state file the operation writes back into.
- The LLM produces a single YAML document conforming to
  [`spec-schema.md`](./spec-schema.md) v2.0, populated entirely from the four
  input files. No PRD parsing, no LLM-driven synthesis of agent behavior — the
  Agent Spec and Tool Plan are already authoritative for `agent.*`. The PRD is
  consulted only for the `prd_sha256` provenance hash and for the optional
  Knowledge Assistant fallback corpus (step 42 branch C).
- The caller then runs the **Validation Rules** section from
  `spec-schema.md` plus the v3.0-only guards in this file. Validation failure
  retries once with the errors appended; second failure halts step 40.
- The caller writes the validated YAML into the same six state-file sections
  `resolve_spec` writes (`## Variant`, `## Resources`, `## UI`, `## Agent`,
  `## Governance`, `## Spec Provenance`) by splitting on the six top-level
  keys. `## Variant` is left untouched if `bootstrap` already populated it;
  the hydrator never re-derives the variant ID.

This file is to `hydrate_from_files` what
[`resolver-prompt.md`](./resolver-prompt.md) is to `resolve_spec`.

---

## Variant-ID Handling

Unlike `resolve_spec`, the hydrator does **not** derive `variant_id`. The
caller passes the value from `## Workshop Choices` (set at bootstrap) directly
into the user prompt, and the LLM echoes it back into the output YAML. This
keeps the variant derivation table in
[`resolver-prompt.md`](./resolver-prompt.md) the single source of truth.

If the caller cannot resolve `variant_id` from `## Workshop Choices` (e.g.
mid-workshop reconfiguration), the caller halts and asks the operator once.
The LLM does not guess.

---

## System Prompt

```
You are the vibecoding-state hydrator (v3.0). Your only job is to read four
input files (Agent Spec, Tool Plan, UI design, PRD) and produce a resolved
YAML spec that conforms exactly to the v2.0 schema. You do NOT synthesize agent
behavior; the Agent Spec already contains it. You do NOT parse the PRD for
domain content; you read it solely to compute prd_sha256 and to record its
path under spec_provenance.

Rules:

 1. Read each input file in full before emitting anything. Inputs:
    - agent_spec_yaml      — the docs/agent_spec.yaml from prompt 38
                              (00b schema; tools live under
                              `tool_recommendations`, NOT `agent.tools`).
    - agent_tool_plan_yaml — the docs/agent_tool_plan.yaml from prompt 39
                              (00b schema; binding selections under
                              `selected_tools[]` + `selected_mcp_servers[]`,
                              plus `runtime_config.llm` and
                              `resource_grants`).
    - ui_design_md         — the docs/ui_design.md from prompt 04 (loose
                              markdown).
    - prd_path             — the docs/design_prd.md from prompt 03; consulted
                              only for prd_sha256.
 2. Output MUST be a single YAML document with exactly six top-level keys:
    `variant_id`, `resources`, `ui`, `agent`, `governance`, `spec_provenance`.
    Nothing else. No prose before or after. No triple backticks around the
    output.
 3. Fields that are absent from the inputs but required by the schema: fill
    with `"n/a"` (strings), `[]` (lists), or `false` (bools). Do NOT invent
    content; the inputs are authoritative.
 4. Templated placeholders (e.g. `{catalog}`, `{schema}`, `{warehouse_id}`,
    `{vector_search_endpoint}`) — keep them as literal strings in curly
    braces. They are resolved later by `vibecoding-state.enter` at runtime.

Per-key rules:

 5. `variant_id` — copy verbatim from the `variant_id` parameter the caller
    passes via the user prompt. Do NOT re-derive it.

 6. `resources` — Lakehouse / Data Intelligence may or may not be present.
    a. If the live state file already carries a populated `## Resources`
       block (a prior `resolve_spec` run on a Lakehouse track), copy it
       through unchanged.
    b. Otherwise, write the optional-resources stub:
         resources:
           optional: true
           mark_skipped: "no Lakehouse track"
           tables: []
           knowledge_bases: []
           genie_spaces: []
           vector_indexes: []
           dabs_bundle: { path: "n/a", setup_commands: [] }
           sample_data:
             required: false
             row_counts: {}
             distribution_constraints: "n/a"
       Downstream consumers (KA branch C in prompt 42, tool wiring in
       prompt 44, MLflow SDLC in prompts 50-56) treat `optional: true`
       as "fall back to docs/* files; skip Lakehouse-specific tools".

 7. `ui` — best-effort projection of `ui_design.md` into the v2.0 UI shape:
    `description`, `personas[]`, `pages[]`, `overview_widgets[]`, `sql_files[]`,
    `user_journeys[]`. If the markdown is structured with H2 headings that
    match those concepts, parse them. If the markdown is loose prose, write:
         ui:
           description: "<first paragraph or n/a>"
           personas: []
           pages: []
           overview_widgets: []
           sql_files: []
           user_journeys: []
           raw_markdown: |
             <verbatim contents of ui_design.md>
    The `raw_markdown` field is a v3.0 extension recognized by the v2.0
    schema as an additional optional field; SDLC prompts that need
    personas/journeys textually fall back to it.

 8. `agent` — populated from the Agent Spec and Tool Plan. Direct copies:
    `agent.model`           ← agent_spec_yaml.agent.model
                              (scalar endpoint name, e.g.
                              "databricks-claude-sonnet-4-6"; never the
                              YAML-path string
                              "docs/agent_spec.yaml.agent.model")
    `agent.system_prompt`   ← agent_spec_yaml.agent.system_prompt
    `agent.capabilities`    ← agent_spec_yaml.agent.capabilities
    `agent.personas` (alias `target_personas`) ← from spec
    `agent.must_do`         ← agent_spec_yaml.governance.must_do (the
                              00b schema groups these under governance;
                              project them onto agent.must_do for the v2.0
                              contract).
    `agent.must_not_do`     ← agent_spec_yaml.governance.must_not_do
    `agent.benchmark_seeds` ← agent_spec_yaml.evaluation
                              (project smoke_test_cases +
                              benchmark_seed_examples into the v2.0
                              `coverage_buckets` + `seed_examples` shape).
    `agent.auth_mode`       ← agent_spec_yaml.agent.auth_mode (default
                              "hybrid" if absent).
    `agent.memory`          ← agent_spec_yaml.agent.memory (provider +
                              table_prefix).

    Tool projection (preserves the v2.0 `fields_read: agent.tools` contract):
    a. Seed `agent.tools[]` from
       agent_spec_yaml.tool_recommendations.managed_databricks[] PLUS
       tool_recommendations.external[]. Map each entry to the v2.0
       discriminated-union shape:
         - server_type "sql"           → kind: mcp,    mcp_server_ref: <name>
         - server_type "genie"         → kind: hosted, hosted_type: genie_space
         - server_type "vector_search" → kind: hosted, hosted_type: vector_search
         - server_type "uc_functions"  → kind: mcp,    mcp_server_ref: <name>
         - external (non-managed)      → kind: mcp,    mcp_server_ref: <name>
       Carry `selected_by_default` forward as a non-schema hint.
    b. Overlay agent_tool_plan_yaml.selected_tools[] on top. Any Tool Plan
       entry with the same `name` REPLACES the spec recommendation
       (binding selection wins). Tool Plan entries with no matching spec
       recommendation are appended.
    c. Tool families absent from BOTH the spec and the Tool Plan are NOT
       written into agent.tools[].

    `agent.mcp_servers[]` ← agent_tool_plan_yaml.selected_mcp_servers[],
                            preserving every entry verbatim.

    `agent.knowledge_base_backend` ← derived from
       agent_tool_plan_yaml.knowledge_assistant.selected:
         selected: true  → preferred: "knowledge_assistant",
                          ka_source: <plan ka_source or "n/a">
         selected: false → preferred: "n/a",
                          ka_source: "n/a"

    `agent.external_integrations` ← copy from spec if present, else
       { web_search_required: false, external_connections: [] }.

 9. `governance` — populate from the Agent Spec:
    `governance.scorer_suite.guidelines[]` ← agent_spec_yaml.governance.scorer_guidelines
    `governance.scorer_suite.judge_questions[]` ← []
    `governance.scorer_suite.custom_scorer_rules[]` ← []
    `governance.scorer_suite.primary_scorer` ← name of the first guideline
    `governance.scorer_suite.production_scorers[]` ← []
    `governance.monitoring.required_alerts[]` ← []
    `governance.monitoring.rollback_trigger_example` ← "n/a"
    `governance.verification.smoke_test_question` ← first
       agent_spec_yaml.evaluation.smoke_test_cases entry, or "n/a"
    `governance.verification.smoke_test_cases[]` ← rest of
       agent_spec_yaml.evaluation.smoke_test_cases (3-5 entries)

10. `spec_provenance` — file-based provenance:
    resolved_at:      <current UTC ISO8601>
    resolver_version: "3.0"
    schema_version:   "2.0"
    prd_sha256:       <provided prd_sha256 parameter>
    llm_endpoint:     "n/a"            # hydration does not call an LLM
                                        # against the PRD; agent.model is
                                        # captured in agent.model and copied
                                        # into resource_grants in step 44
    hydrated_from_files: true
```

---

## User Prompt Template

```
Hydrate the following four files into a state YAML per the v2.0 schema in
spec-schema.md. Do NOT synthesize agent behavior; the Agent Spec already
contains it.

Agent Spec path:      {agent_spec_path}
Agent Spec sha256:    {agent_spec_sha256}
Tool Plan path:       {agent_tool_plan_path}
Tool Plan sha256:     {agent_tool_plan_sha256}
UI design path:       {ui_design_path}
PRD path:             {prd_path}
PRD sha256:           {prd_sha256}
Schema version:       2.0
Resolver version:     3.0
Variant ID (pre-derived, do not re-derive): {variant_id}

<agent_spec>
{agent_spec_contents}
</agent_spec>

<agent_tool_plan>
{agent_tool_plan_contents}
</agent_tool_plan>

<ui_design>
{ui_design_contents}
</ui_design>

<schema>
{spec_schema_yaml}
</schema>

Emit the hydrated YAML now. Six top-level keys only:
variant_id, resources, ui, agent, governance, spec_provenance.
```

---

## Post-hydration Guards (deterministic)

After the LLM returns, `hydrate_from_files` runs (in order):

1. **YAML parse** — must load into a dict with the six expected top-level
   keys.
2. **Schema validation** — every rule in
   [`spec-schema.md`](./spec-schema.md) § *Validation Rules*, with the
   tool-discriminator contract enforced over the projected `agent.tools[]`.
3. **Provenance lock-in** — `spec_provenance.resolver_version == "3.0"` and
   `spec_provenance.hydrated_from_files == true`. If the live state file
   already carries `resolver_version: "2.0"` (LLM-driven `resolve_spec` ran
   first), the caller halts: `hydrate_from_files` and `resolve_spec` are
   mutually exclusive on the same workshop run. The remediation is to delete
   the prior state file and start over from bootstrap.
4. **Scalar endpoint guard (v3.0 only)** —
   `agent_tool_plan_yaml.runtime_config.llm.endpoint` MUST be a scalar
   serving-endpoint name (e.g. `databricks-claude-sonnet-4-6`). Halt if it
   equals the literal string `docs/agent_spec.yaml.agent.model` or
   `docs/agent_tool_plan.yaml.runtime_config.llm.endpoint` — those are
   YAML-path strings, not endpoint names. Pass 2 forbade writing them in
   prompt 39; this guard catches the case where prompt 39 was bypassed.
5. **Tool-projection invariants** —
   - Every `agent.tools[].name` resolves to either a
     `tool_recommendations.*` entry in the Agent Spec OR a `selected_tools[]`
     entry in the Tool Plan (or both, in which case the Tool Plan
     replacement is recorded).
   - Every `agent.tools[].kind == "mcp"` entry's `mcp_server_ref` resolves
     to an `agent.mcp_servers[].name`.
   - No `agent.tools[]` entry exists for a family absent from BOTH the
     Spec and the Tool Plan.
6. **Variant-ID echo check** — `variant_id` in the output exactly matches
   the value passed in via the user prompt.

Guard failures cause one retry with the errors appended. Second failure halts
prompt 40 with a typed error pointing at the offending input file.

---

## Idempotency

Re-running `hydrate_from_files` with the same four inputs produces a state
file that differs only in `spec_provenance.resolved_at` (the current UTC
timestamp). The sha256 of the rest of the state file (`## Variant`,
`## Resources`, `## UI`, `## Agent`, `## Governance`) is byte-stable across
runs.

Re-running with newer `docs/*.yaml` files overwrites the corresponding state
sections cleanly. The hydrator never merges new content with prior LLM
output; the file is the source of truth on every run.

---

## Worked Example — Tool Projection

Given an Agent Spec excerpt:

```yaml
tool_recommendations:
  managed_databricks:
    - name: "sql_uc_schema_query"
      server_type: "sql"
      reason: "Query existing UC tables read-only."
      selected_by_default: true
    - name: "loyalty_genie"
      server_type: "genie"
      reason: "Natural-language SQL over the loyalty Bronze tables."
      selected_by_default: false
  external: []
```

And a Tool Plan excerpt:

```yaml
selected_tools:
  - kind: "mcp"
    name: "sql_uc_schema_query"
    mcp_server_ref: "sql_uc_schema_query"
    surface: "python"
    io_contract: "natural language question -> read-only SQL result"
    readonly: true
    guardrails:
      allowed_statements: ["SELECT", "DESCRIBE", "EXPLAIN"]
      require_fully_qualified_names: true
selected_mcp_servers:
  - name: "sql_uc_schema_query"
    server_type: "sql"
    auth: "OBO"
    meta: { warehouse_id: "{agent_sql_warehouse_id}" }
    scope: { catalog: "{agent_sql_catalog}", schema: "{agent_sql_schema}", allowed_tables: [] }
    readonly: true
```

The hydrator emits (under `agent`):

```yaml
agent:
  tools:
    - kind: "mcp"
      name: "sql_uc_schema_query"
      mcp_server_ref: "sql_uc_schema_query"
      surface: "python"
      io_contract: "natural language question -> read-only SQL result"
      readonly: true
  mcp_servers:
    - name: "sql_uc_schema_query"
      server_type: "sql"
      resource_ref: "{agent_sql_catalog}.{agent_sql_schema}"
      auth: "OBO"
      purpose: "Query existing UC tables read-only."
```

Note: `loyalty_genie` (server_type `genie`) had `selected_by_default: false`
and is absent from the Tool Plan's `selected_tools[]`, so it is NOT written
into `agent.tools[]`. Step 44 sees `selected_tools[]` carrying only
`sql_uc_schema_query` and skips the Genie family cleanly.
