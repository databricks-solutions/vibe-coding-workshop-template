# Resolver Prompt — `vibecoding-state.resolve_spec` (v2.0)

The `resolve_spec` operation runs this prompt **once** at `bootstrap` time
against the PRD file (`prd_path` captured in `## Workshop Choices`). The LLM
endpoint used is whatever the operator selected as `llm_endpoint` in
`## Workshop Choices` (recommended: `databricks-claude-sonnet-4-5` or
equivalent).

The resolver is **LLM-first with deterministic guards**:

- Before invoking the LLM, the caller derives `variant_id` deterministically
  from Workshop Choices (see § *Variant-ID Derivation Table* below) and
  injects it into both the user prompt and the final YAML.
- The LLM produces the resolved spec as a single YAML document conforming to
  [`spec-schema.md`](./spec-schema.md) v2.0.
- The caller then runs the **Validation Rules** section from `spec-schema.md`
  against the output. If any rule fails, the resolver retries once with the
  validation errors appended to the prompt. If it fails again, bootstrap halts
  and the operator fixes the PRD.
- The caller writes the validated YAML into the five state-file sections
  (`## Variant`, `## Resources`, `## UI`, `## Agent`, `## Governance`,
  `## Spec Provenance`) by splitting on the six top-level keys.

---

## Variant-ID Derivation Table

The caller computes `variant_id` **before** invoking the LLM, from the
`pathway` and `track` values already set in `## Workshop Choices`:

| pathway | track | variant_id |
|---------|-------|------------|
| A | `A-custom-agent-apps` + AppKit-companion | `v4-agentapp-plus-appkit` |
| A | `A-custom-agent-apps` + template UI | `v3-agentapp-only` |
| A | `A-custom-agent-apps-node` (integrated) | `v5-integrated-appkit` |
| B or C | serving + AppKit | `v2-serving-appkit` |
| B or C | supervisor + AppKit | `v1-sup-appkit` |

If Workshop Choices is ambiguous (e.g. pathway A + track unspecified), the
caller halts and asks the operator once. The LLM does not guess the variant.

---

## System Prompt

```
You are the vibecoding-state resolver (v2.0). Your only job is to read a
workshop Product Requirements Document (PRD) and produce a resolved YAML spec
that conforms exactly to the provided JSON schema.

Rules:

1. Read the PRD top-to-bottom. Extract every field in the schema.
2. For "verbatim from PRD" fields, copy the PRD text character-for-character
   after stripping leading/trailing whitespace and any leading list markers
   (e.g. "- ", "1. ", "> "). Do NOT paraphrase.
3. For "SYNTHESIZED" fields (specifically `agent.system_prompt` and
   `agent.capabilities`), produce a single coherent paragraph by
   combining the listed source fields. Keep it under 120 words. Do not
   introduce facts not present in the PRD.
4. For templated placeholders (e.g. `{catalog}`, `{schema}`, `{warehouse_id}`,
   `{genie_space_id}`, `{vector_search_endpoint}`) — keep the placeholder as
   a literal string in curly braces. Do NOT resolve these; they are resolved
   later by `vibecoding-state.enter` at runtime.
5. Output MUST be a single YAML document with exactly six top-level keys:
   `variant_id`, `resources`, `ui`, `agent`, `governance`, `spec_provenance`.
   Nothing else. No prose before or after.
6. Do NOT wrap the YAML in triple backticks. Emit raw YAML.
7. Fields that are absent from the PRD but required by the schema: fill with
   `"n/a"` (strings), `[]` (lists), or `false` (bools). Do not invent content.
8. `spec_provenance.resolved_at` — use the current UTC time in ISO8601.
9. `spec_provenance.prd_sha256` — use the provided `prd_sha256` parameter.
10. `spec_provenance.schema_version` — always `"2.0"`.
11. `spec_provenance.resolver_version` — always `"2.0"`.
12. `spec_provenance.llm_endpoint` — the endpoint that ran this prompt.
13. `variant_id` — copy verbatim from the `variant_id` parameter provided by
    the caller. Do NOT re-derive it.
14. **Tool discriminator contract**: every `agent.tools[]` entry MUST have
    a `kind:` field of `"hosted" | "function" | "mcp"`, plus the
    kind-specific required fields:
    - `kind: hosted` → `hosted_type` (one of `genie_space | vector_search |
      knowledge_assistant | code_interpreter`) and `resource_ref`.
    - `kind: function` → `language` (`python` or `typescript`).
    - `kind: mcp` → `mcp_server_ref` that matches a
      `agent.mcp_servers[].name`.
15. **Unified tables**: `resources.tables[]` merges what v1.0 split into
    `sql_warehouse_tables` and `lakebase_tables`. Each entry MUST have
    `kind: "warehouse"` or `kind: "lakebase"`. Use `columns:` only for
    `kind: lakebase`.
16. **Governance grouping**: scorer suite, monitoring, and verification all
    live under the top-level `governance` key — not under `agent`.
17. **Agent first-class fields**: `agent.model` (e.g.
    "databricks-claude-sonnet-4-5"), `agent.auth_mode`
    (`"app" | "user" | "hybrid"`), and `agent.memory` (`provider` +
    `table_prefix`) are required. Derive from PRD if stated, otherwise set
    sensible defaults from Workshop Choices.
```

---

## User Prompt Template

```
Resolve the following PRD into a spec YAML per the schema in spec-schema.md.

PRD path:      {prd_path}
PRD sha256:    {prd_sha256}
Schema version: 2.0
Resolver version: 2.0
LLM endpoint:  {llm_endpoint}
Variant ID (pre-derived, do not re-derive): {variant_id}

<prd>
{prd_contents}
</prd>

<schema>
{spec_schema_yaml}
</schema>

Emit the resolved YAML now. Six top-level keys only:
variant_id, resources, ui, agent, governance, spec_provenance.
```

---

## Post-resolution Guards (deterministic)

After the LLM returns, `resolve_spec` runs (in order):

1. **YAML parse** — must load into a dict with the six expected top-level keys.
2. **Schema validation** — every rule in `spec-schema.md` §"Validation Rules".
3. **Consumer cross-check** — every `agent.tools[].name` that is
   `kind: function` with `language: python` or a `hosted_type: code_interpreter`
   must appear in the PRD Tools Table literally. (Guards against the LLM
   fabricating tool names.)
4. **Placeholder guard** — any string value that looks like a Databricks
   resource ID (matches `^[0-9a-f]{16,}$` or `^dbdemos-[a-z0-9-]+$`) is
   rejected. Force the LLM to use templated placeholders.
5. **Variant-ID echo check** — `variant_id` in the output must exactly match
   the value passed in via the user prompt.
6. **MCP ref resolution** — every `agent.tools[].mcp_server_ref` (for
   `kind: mcp`) must resolve to an `agent.mcp_servers[].name`.

Guard failures cause one retry with the errors appended. Second failure halts
bootstrap.

---

## Worked Example — `agent.system_prompt`

Given a PRD section:

```md
## Agent Behavior Constraints

**Tone / persona**
- Professional loyalty program data analyst.

**Must do**
- Cite the source (table name for data queries, document name for policy lookups).
- Include the time period in data answers.
- Show intermediate results before the final synthesis for multi-step analysis.

**Must not do**
- Execute DDL.
- Fabricate loyalty program rules.
```

The resolver emits:

```yaml
agent:
  system_prompt: |
    You are a professional loyalty program data analyst. Always cite the source
    (table name for data queries, document name for policy lookups) and include
    the time period in every data answer. For multi-step analysis, show
    intermediate results before the final synthesis. Never execute DDL. Never
    fabricate loyalty program rules.
  tone_persona: "Professional loyalty program data analyst."
  must_do:
    - "Cite the source (table name for data queries, document name for policy lookups)."
    - "Include the time period in data answers."
    - "Show intermediate results before the final synthesis for multi-step analysis."
  must_not_do:
    - "Execute DDL."
    - "Fabricate loyalty program rules."
```

The `system_prompt` paragraph is synthesized (not verbatim), all other fields
are copied verbatim.

---

## Worked Example — `governance.scorer_suite.guidelines`

For every `agent.must_do` bullet, emit one `guidelines` entry with a
kebab-case name:

```yaml
governance:
  scorer_suite:
    guidelines:
      - name: "source_citation"
        text: "Cite the source (table name for data queries, document name for policy lookups)."
        threshold: 0.8
      - name: "time_period_in_data_answers"
        text: "Include the time period in data answers."
        threshold: 0.8
      - name: "show_intermediate_results"
        text: "Show intermediate results before the final synthesis for multi-step analysis."
        threshold: 0.8
```

Default threshold is `0.8`. Workshop operators may override per-guideline
inside `sdlc/03-scorers-and-judges`.

---

## Worked Example — `agent.tools[]` discriminated union

For a PRD Tools Table with three tools (a Genie space, a `@function_tool`
Python function, and an MCP-routed Vector Search), the resolver emits:

```yaml
agent:
  tools:
    - kind: hosted
      name: "Loyalty Data Query"
      surface: both
      io_contract: "NL question -> ranked table + SQL"
      readonly: true
      hosted_type: genie_space
      resource_ref: "{genie_space_id}"
    - kind: function
      name: "compute_discount"
      surface: python
      io_contract: "member_id, tier -> discount_pct"
      readonly: true
      language: python
    - kind: mcp
      name: "Policy Knowledge Lookup"
      surface: both
      io_contract: "NL question -> passage + citation"
      readonly: true
      mcp_server_ref: "vs_policy_docs"

  mcp_servers:
    - name: "vs_policy_docs"
      server_type: "vector_search"
      resource_ref: "{catalog}.{schema}.policy_docs_idx"
      auth: "SP"
      purpose: "Policy KB retrieval"
```

Notice every tool names its kind, every `kind: mcp` tool's `mcp_server_ref`
resolves to an `agent.mcp_servers[].name`, and `surface: both` means the
tool wire-shape is portable across Python (MLflow ResponsesAgent) and Node
(`@openai/agents`) runtimes.
