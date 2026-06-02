# Spec Schema — v2.0

This file is the **single source of truth** for the structure of the five spec
sections written into every live state file by the
`vibecoding-state.resolve_spec` operation.

- **Variant** — a single `variant_id` identifying which of the five SkyLoyalty-
  shaped walkthroughs (v1-sup-appkit … v5-integrated-appkit) this workshop run
  instantiates. Used by every consuming skill to gate variant-specific prompts.
- **Resources** — tables (warehouse + Lakebase, unified), Knowledge Bases,
  Genie Spaces, Vector Indexes, the DABs bundle, and sample-data declarations.
- **UI** — app description, personas, pages, overview widgets, SQL files, user
  journeys.
- **Agent** — system prompt, model, auth mode, memory block, tools
  (discriminated union), MCP servers, KB backend, external integrations,
  benchmark seeds.
- **Governance** — scorer suite, monitoring alerts, and verification smoke
  inputs. All three are MLflow-SDLC-oriented and deliberately grouped together,
  separate from the agent runtime shape.

Every field has exactly one or more owners: specific consuming skills that
declare `fields_read:` lists in their YAML frontmatter. The
`retrospective.rollup` drift check parses those lists and halts if the union
of declared reads does not equal the set of fields emitted by `resolve_spec`.
See § **Field Consumer Contract** below.

---

## Schema Version

Every resolved state file is stamped with `schema_version: "2.0"` in
`## Spec Provenance`. Bumps follow semver. Breaking changes require a
`scripts/migrate-spec-v1-to-v2.py`-shaped migrator (v1 → v2 is implemented;
future v2 → vN migrators live alongside).

**Strict v2.0**: `resolve_spec` emits v2.0 exclusively. `vibecoding-state.enter`
halts with a pointer to the migrator if it encounters a state file whose
`spec_provenance.schema_version != "2.0"`. No silent backward-compat shims.

---

## Variant

```yaml
variant_id: string   # enum:
                     #   "v1-sup-appkit"          | Supervisor API + AppKit (Python sidecar)
                     #   "v2-serving-appkit"      | Model Serving endpoint + AppKit
                     #   "v3-agentapp-only"       | Custom Agent on Apps (template UI, no AppKit)
                     #   "v4-agentapp-plus-appkit"| Custom Agent on Apps + separate AppKit  (canonical)
                     #   "v5-integrated-appkit"   | Node-native @openai/agents inside AppKit (single App)
```

Derivation rules live in `resolver-prompt.md` § *Variant-ID Derivation Table*.
`resolve_spec` sets this deterministically from Workshop Choices
(`pathway`, `track`); the LLM does not guess.

---

## Resources

```yaml
resources:
  tables:                        # list — unified warehouse + lakebase
    - full_name:        string   # e.g. "main.skyloyalty.loyalty_members"
      kind:             string   # enum: "warehouse" | "lakebase"
      key_columns:      [string] # PK/FK/grain columns
      approx_rows:      string   # e.g. "100K", "2M" (keep as string)
      refresh_cadence:  string   # "Daily" | "Weekly" | "Monthly" | "Realtime" | "n/a"
      purpose:          string   # one short sentence
      columns:          [string] # OPTIONAL — only populated for kind=lakebase (name + type)
  knowledge_bases:               # list (empty if no KB)
    - name:             string   # was: doc_set_name in v1.0
      format:           string   # "Markdown" | "PDF" | "HTML" | …
      count:            integer
      uc_volume:        string   # templated, e.g. "{catalog}.{schema}.loyalty_docs"
      chunking:         string   # e.g. "512 tokens, 64 overlap"
  genie_spaces:                  # list
    - name:             string
      tables:           [string] # references resources.tables[].full_name (unqualified)
      instructions:     string   # verbatim from PRD
      sample_questions: [string]
  vector_indexes:                # list (was: vector_search_indexes in v1.0)
    - name:             string
      endpoint:         string   # "{vector_search_endpoint}" is a legal templated placeholder
      index:            string   # "{catalog}.{schema}.<index_name>"
      embedding_model:  string
      sync_mode:        string   # "Triggered" | "Continuous"
  dabs_bundle:
    path:               string   # e.g. "example/skyloyalty/" or "n/a"
    setup_commands:     [string] # verbatim commands from PRD Part D
  sample_data:
    required:           bool
    row_counts:         {string: string}  # table_name -> row count (string, e.g. "100K")
    distribution_constraints: string      # free text
```

---

## UI

```yaml
ui:
  description:          string   # one paragraph from PRD top-matter
  personas:                      # list, in PRD order
    - name:             string
      role_summary:     string   # one sentence, synthesized from PRD persona paragraph
  pages:                [string] # e.g. ["Overview", "Members", "Partners", "Campaigns"]
  overview_widgets:     [string] # free form, e.g. "kpi_cards(total_members, active_pct, ...)"
  sql_files:            [string] # SQL file names the app will reference
  user_journeys:                 # list, in PRD order
    - id:               string   # e.g. "J1", "J2"
      title:            string
      actor:            string   # references a persona name
      narrative:        string   # verbatim from PRD Key User Journeys
      artifacts_produced: [string]  # e.g. ["ranked_table", "csv_file", "saved_segment"]
```

---

## Agent

```yaml
agent:
  system_prompt:        string   # SYNTHESIZED paragraph from tone_persona + must_do + must_not_do
  tone_persona:         string   # verbatim from PRD Agent Behavior Constraints
  must_do:              [string] # each bullet verbatim from PRD
  must_not_do:          [string] # each bullet verbatim from PRD

  model:                string   # FIRST-CLASS — e.g. "databricks-claude-sonnet-4-5"
                                 #   Matches agent-langchain-ts DATABRICKS_MODEL convention.
  auth_mode:            string   # FIRST-CLASS — enum: "app" | "user" | "hybrid"
                                 #   See https://docs.databricks.com/aws/en/generative-ai/
                                 #   agent-framework/agent-authentication

  capabilities:         [string] # derived from ui.user_journeys + tools; 3-7 bullets
  reviewer_role:        string   # primary PRD persona name used for labeling sessions

  memory:                        # FIRST-CLASS — was implicit in v1.0
    provider:           string   # enum: "lakebase" | "postgres" | "none"
    table_prefix:       string   # e.g. "app.chat"  (when provider == "none", set "n/a")

  tools:                         # list, DISCRIMINATED UNION on `kind`
    - kind:             string   # enum: "hosted" | "function" | "mcp"
      name:             string   # e.g. "Loyalty Data Query"
      surface:          string   # enum: "python" | "node" | "both"
      io_contract:      string   # "input -> output" short form
      readonly:         bool
      # kind == "hosted" fields
      hosted_type:      string   # OPTIONAL — enum: "genie_space" | "vector_search" |
                                 #            "knowledge_assistant" | "code_interpreter"
      resource_ref:     string   # OPTIONAL — templated placeholder, e.g. "{genie_space_id}"
      # kind == "function" fields
      language:         string   # OPTIONAL — enum: "python" | "typescript"
      # kind == "mcp" fields
      mcp_server_ref:   string   # OPTIONAL — references agent.mcp_servers[].name

  mcp_servers:                   # list
    - name:             string   # NEW in v2.0 — tools[kind=mcp] reference this by name
      server_type:      string   # "genie" | "vector_search" | "sql" | "uc_functions" | "external_<service>"
      resource_ref:     string
      auth:             string   # "SP" | "OBO" | "OAuth"
      purpose:          string

  knowledge_base_backend:
    preferred:          string   # "knowledge_assistant" | "vector_search" | "n/a"
    ka_source:          string   # UC Volume path or "n/a"
    vs_fallback_index:  string   # "{catalog}.{schema}.<index>" or "n/a"

  external_integrations:
    web_search_required: bool
    external_connections:        # list, empty if PRD External Connections = None
      - name:           string
        auth:           string
        purpose:        string

  benchmark_seeds:
    coverage_buckets:   [string] # one bucket per user journey, plus "edge_cases"
    seed_examples:              # list, >= 20 dedup'd
      - bucket:         string   # must match one of coverage_buckets
        prompt:         string
        expected_signal: string  # e.g. "ranked table with source citation + Q1 2025 time period"
```

---

## Governance

```yaml
governance:
  scorer_suite:
    guidelines:                  # one per agent.must_do bullet
      - name:           string   # e.g. "source_citation"
        text:           string   # verbatim must_do bullet
        threshold:      number   # default 0.8 (workshop knob, may be overridden)
    judge_questions:             # one per factuality-shaped agent.must_not_do bullet
      - name:           string   # e.g. "domain_accuracy"
        text:           string
        threshold:      number   # default 0.7
    custom_scorer_rules:         # for tools producing structured output
      - tool_name:      string   # must match agent.tools[].name
        rule:           string   # what the scorer must check
    primary_scorer:     string   # the scorer whose regressions define "failing traces"
                                 #   for agent-as-judge debugging (must match a
                                 #   guidelines/judge/custom name); default is the first
                                 #   guideline
    production_scorers:          # subset of guidelines + judges, with continuous-eval
      - name:           string   #   sampling rate for production monitoring
        sampling:       number   # 0.0 - 1.0 (1.0 = 100%)
        threshold:      number   # optional override

  monitoring:
    required_alerts:    [string] # stable alert ids referenced by
                                 #   monitoring-dashboard-queries.md, e.g.
                                 #   ["citation_drift_neg_0_05_6h", "liveness_zero_traces_15m"]
    rollback_trigger_example:
                        string   # human-readable hint used verbatim in the signoff
                                 #   decision record, e.g. "<primary_scorer> < 0.80 over
                                 #   24h window → revert to previous @champion"

  verification:
    smoke_test_question: string  # one-line question used by 05-lakebase-memory's
                                 #   predict_fn smoke test (defaults to
                                 #   agent.benchmark_seeds.seed_examples[0].prompt if omitted)
    smoke_test_cases:   [string] # 3-5 short natural-language descriptions used by
                                 #   06-evaluation's developer-loop test cases, each
                                 #   one covering a different user journey
```

---

## Spec Provenance

```yaml
spec_provenance:
  resolved_at:          string   # ISO8601 UTC
  resolver_version:     string   # "2.0"
  schema_version:       string   # "2.0"
  prd_sha256:           string   # hash of the PRD file at resolve time
  llm_endpoint:         string   # the llm_endpoint used to synthesize system_prompt
```

---

## State Contract Audit

```yaml
state_contract_audit:
  last_run_at: string            # ISO8601 UTC
  mode: string                   # "warn" | "fail"
  fields_read_but_never_produced: [string]
  fields_produced_but_not_in_schema: [string]
  schema_fields_missing_from_template: [string]
  captured_fields_with_no_consumer: [string]
  productized_debts_status:
    total: integer
    lifted: integer
    parse_errors: integer
```

Populated by the `audit_debts` operation; consumed by `retrospective.rollup` for the rollup-table debt-lift status.

---

## LLM Role Endpoints

`vibecoding-state` binds each LLM-consuming role to a specific Databricks
Foundation Model API (FMAPI) endpoint after a live probe. Every role stores
both the `candidates` list (ordered by preference) and the bound `endpoint`,
along with the rationale and the `selected_after_probe` flag. Do NOT use an
`endpoint`-only shape before probing — consumers MUST be able to detect when
binding has not yet occurred.

```yaml
llm_role_endpoints:
  agent_chat:
    candidates:           [string]
    endpoint:             string
    streaming_required:   bool
    selected_after_probe: bool
    rationale:            string
  agent_chat_streaming_smoke:
    candidates:           [string]
    endpoint:             string
    streaming_required:   bool
    selected_after_probe: bool
    rationale:            string
  reflection_lm:
    candidates:           [string]
    endpoint:             string
    min_context_chars:    integer
    selected_after_probe: bool
    rationale:            string
  llm_judge_default:
    candidates:           [string]
    endpoint:             string
    selected_after_probe: bool
    rationale:            string
  failure_categorizer:
    candidates:           [string]
    endpoint:             string
    selected_after_probe: bool
    rationale:            string
```

---

## Endpoint Guardrail Audit

`scripts/probe_endpoints.py` records the live probe result for every endpoint
that bootstrap considers. Each entry is keyed by the endpoint name and stamped
with the audit time, the four probe outcomes, and the observed input/output
guardrail signatures.

```yaml
endpoint_guardrail_audit:
  <endpoint_name>:
    audited_at:                  string   # ISO8601 UTC
    short_chat_ok:               bool
    long_context_ok:             bool
    sql_quote_ok:                bool
    streaming_arg_accepted:      bool     # true iff the SDK call with
                                          #   `stream=True` did not raise.
                                          #   This is NOT proof the endpoint
                                          #   actually streams chunks — the
                                          #   SDK buffers SSE internally and
                                          #   returns a single response. A
                                          #   real streaming probe (HTTP-
                                          #   level Content-Type assertion +
                                          #   delta-chunk count) is tracked
                                          #   as a TODO in the script.
    input_guardrail_signature:   string
    output_guardrail_signature:  string
    accepted_min_context_chars:  integer  # the input-length floor we
                                          #   submitted successfully (e.g.
                                          #   80000 if `long_context_ok`,
                                          #   else -1; 0 when the long-
                                          #   context probe was skipped via
                                          #   `--skip-long-context`).
                                          #   This is a floor, NOT an
                                          #   observation of the endpoint's
                                          #   true context window.
```

---

## Bootstrap Preflight

`vibecoding-state.bootstrap` runs a structured set of preflights before the
first state file is written. The result is captured into the live state file's
`## Bootstrap Preflight` block. Every field is populated up front so that
downstream prompts (and the `state_contract_audit`) can reason about the
operator's environment without re-running the same shell commands.

```yaml
bootstrap_preflight:
  workspace_url_normalized:               string   # workspace_url with trailing
                                                   #   slash trimmed, scheme
                                                   #   normalized to https://
  workspace_url_was_placeholder:          bool     # true if the operator passed
                                                   #   a literal placeholder
                                                   #   (`<your-workspace-url>`,
                                                   #   empty, or `https://<...>`)
                                                   #   — bootstrap halts when
                                                   #   true
  workspace_profile:                      string   # Databricks CLI profile name
                                                   #   selected after host match
  workspace_host_auth_status:             string   # enum:
                                                   #   "authenticated"      |
                                                   #   "unauthenticated"    |
                                                   #   "wrong_host"
  databricks_cli_version:                 string   # `databricks --version`
                                                   #   output, normalized — OR
                                                   #   the sentinel
                                                   #   "unknown_on_genie_code"
                                                   #   when client_context ==
                                                   #   genie_code (no local CLI
                                                   #   binary; --version is
                                                   #   hard-blocked, Gap-1).
                                                   #   The numeric gate is then
                                                   #   skipped in favor of the
                                                   #   `bundle validate` probe.
  databricks_cli_min_version:             string   # minimum version this repo
                                                   #   requires; merged from
                                                   #   workshop config (default
                                                   #   "0.295.0")
  apps_quota:
    current_count:                        integer  # `databricks apps list`
                                                   #   length
    max_count:                            integer  # workspace cap (typically
                                                   #   10 in shared workspaces)
    free_slots:                           integer  # max_count - current_count
  bundle_dev_mode_schema_prefix_detected: bool     # true when DAB dev mode
                                                   #   prefixes UC schema
                                                   #   resource names (e.g.
                                                   #   `dev_${user}_<schema>`);
                                                   #   downstream prompts MUST
                                                   #   pass the resolved
                                                   #   prefixed schema name
                                                   #   into jobs/notebooks,
                                                   #   not the unprefixed
                                                   #   variable
  first_state_file_path:                  string   # the live state file
                                                   #   bootstrap wrote to —
                                                   #   `example/<use_case_slug>/.vibecoding-state.md`
                                                   #   or
                                                   #   `workshops/<use_case_slug>/.vibecoding-state.md`
                                                   #   — captured before
                                                   #   `$APP_NAME` exists, so
                                                   #   `migrate_canonical` knows
                                                   #   exactly which file to
                                                   #   move
  app_name_known_at_bootstrap:            bool     # always false at bootstrap
                                                   #   (`$APP_NAME` is resolved
                                                   #   later by Module 1 /
                                                   #   Prompt 2); recorded so
                                                   #   downstream gates can tell
                                                   #   if a prompt is reading a
                                                   #   pre- vs post-migrate file
  verify_summary_semantics:
    pass_field:                           string   # JSON key in the verify
                                                   #   notebook output that
                                                   #   carries the pass count
                                                   #   (default: "pass")
    warn_field:                           string   # default: "warn"
    fail_field:                           string   # default: "fail"
    warning_policy:                       string   # enum:
                                                   #   "allow_with_notes"      |
                                                   #   "block_if_load_bearing"
                                                   # — `block_if_load_bearing`
                                                   # means warnings whose names
                                                   # match
                                                   # `gate_load_bearing_checks[]`
                                                   # block the gate
```

`bootstrap` halts (with a typed error message and a remediation hint) if any
of the following are true:

- `workspace_url_was_placeholder == true`.
- `workspace_host_auth_status != "authenticated"`.
- `databricks_cli_version` is older than `databricks_cli_min_version` **and**
  `databricks_cli_version != "unknown_on_genie_code"` (the Genie Code sentinel
  skips the version halt — Gap-1; eligibility is decided by the `bundle
  validate` behavior probe instead).
- `apps_quota.free_slots < 1` and the run will eventually call
  `databricks apps create` (Pathways A/B/C).

The `bundle_dev_mode_schema_prefix_detected` flag is informational at bootstrap
time but **must** be honored by every downstream prompt that passes
`agent_schema`, `ops_schema`, or `uc_schema` into a notebook or job — the
prompt reads the resolved (prefixed) schema name from state, not the
unprefixed variable.

---

## State File Set

Pathway C runs that combine an AppKit app with a separately authored agent (and
some Pathway D variants that read AppKit context) keep state in **two** files:
the AppKit app's `apps_lakebase/$APP_NAME/.vibecoding-state.md` and the agent's
`agents/$AGENT_NAME/.vibecoding-state.md`. Any prompt that needs to read both
declares `state_file_set` so `enter` knows which file is authoritative for which
canonical field, and `enter` can fail fast on conflicts.

Pathways A, B, and pure-D runs that touch only one file omit `state_file_set`
(or set `secondary: null`). The block is required only when a prompt MUST read
both files in the same step.

```yaml
state_file_set:
  primary:
    path:                  string                  # e.g. "apps_lakebase/$APP_NAME/.vibecoding-state.md"
    owner:                 string                  # enum: appkit | agent | root | example
  secondary:
    path:                  string                  # e.g. "agents/$AGENT_NAME/.vibecoding-state.md"
    owner:                 string                  # enum: appkit | agent | root | example
    required_for_prompts:  [string]                # prompt_ids that must read secondary
  lookup_order:            [string]                # e.g. ["primary", "secondary"]
  conflict_policy:         string                  # enum: primary_wins | fail_on_conflict
```

`enter` rule (normative):

- If `state_file_set.secondary` is declared, `enter` reads both files and
  unions their canonical fields per the `Canonical Names` registry below.
- If the same canonical field appears in both files with **different** values,
  `enter` halts unless `conflict_policy: primary_wins` is set explicitly. With
  `primary_wins`, the primary file's value is used and the conflict is logged
  to `## State Contract Audit`.
- `lookup_order` controls which file is consulted first for non-conflicting
  reads; the first hit wins.
- `secondary.required_for_prompts` lists the prompt_ids that MUST resolve the
  secondary file. If `enter` is invoked for one of those prompt_ids and the
  secondary file does not exist, halt with a remediation hint.

---

## Canonical Names

Canonical-name registries pin one spelling per concept across the workshop
surface area: state fields, environment variables, `jq` paths into CLI output,
HTTP headers from Databricks Apps, MLflow Prompt Registry URIs, evaluation
dataset fields, label-schema namespacing, and file paths. Prompts MUST read
from these names; legacy/incorrect spellings are mapped to their canonical
forms here and `state_contract_audit` extends its drift checks to cover
`env_vars`, `http_headers`, `jq_paths`, and `prompt_registry`.

```yaml
canonical_names:
  state_fields: {}                                 # canonical state-field aliases (string -> string)
  env_vars:
    # legacy/incorrect name : canonical name
    # e.g. an old prompt that said `MLFLOW_EXPERIMENT_NAME` must now read `MLFLOW_EXPERIMENT_ID`.
    MLFLOW_EXPERIMENT_NAME: MLFLOW_EXPERIMENT_ID
    WAREHOUSE_ID: MLFLOW_TRACING_SQL_WAREHOUSE_ID
  jq_paths:
    apps_status_state: .app_status.state           # canonical jq path for `databricks apps get` status
  http_headers:
    # x-forwarded-user-info : null  -- this header DOES NOT exist on Databricks Apps;
    # any prompt that expects it is a bug. `state_contract_audit` flags such reads.
    x-forwarded-user-info: null
    x-forwarded-email: x-forwarded-email
    x-forwarded-preferred-username: x-forwarded-preferred-username
    x-forwarded-user: x-forwarded-user
    x-app-user-email: x-app-user-email
  prompt_registry:
    uri_scheme: prompts:/                          # MLflow Prompt Registry URI prefix
    schema_field: uc_agent_schema                  # canonical state field that holds the
                                                   #   UC schema where prompts:/ entries live
  eval_dataset_fields:
    expected_response: expected_response           # canonical column for golden answers
    expected_signal: expected_signal               # canonical column for must-have facets
  label_schema_namespace_prefix: string            # e.g. "<workshop>_v<n>__" — pinned per workshop
  file_paths: {}                                   # canonical file-path aliases (string -> string)
```

Reading rule (normative):

- For `env_vars`, `http_headers`, and `state_fields`: `<legacy_name>:
  <canonical_name>` means "any prompt that still spells it `<legacy_name>` must
  be rewritten to read `<canonical_name>`." The map is one-way (legacy →
  canonical); never invert it.
- A `null` value (e.g. `x-forwarded-user-info: null`) means **the name does
  not exist**. Any prompt that reads it MUST be flagged by
  `state_contract_audit` and rewritten to use one of the listed canonical
  headers (typically `x-forwarded-email` for app-side identity).
- `prompt_registry.uri_scheme` is the only legal scheme for MLflow Prompt
  Registry references; consumers that hardcode `mlflow://` or other schemes
  are flagged.
- `label_schema_namespace_prefix` is set per workshop run (e.g. derived from
  `use_case_slug` plus a workshop version) so labeling sessions in the same
  MLflow experiment do not collide.

---

## State Overrides

`state_overrides[]` is the **only** mechanism by which `enter` may proceed past
a failed gate, a prior-gate mismatch, a failed `hard_assert`, a failed
`preflight_check`, or a non-applicable pathway. Cross-session continuity is
NOT a prose exception — it is recorded as a `state_override` whose `reason`
links to the earlier run's evidence (Per-Step Log section, retrospective entry,
or trace ID).

```yaml
state_overrides:
  - prompt_id:             string   # the prompt whose gate is being overridden
    gate_type:             string   # enum:
                                    #   "require_prior_gate"     |
                                    #   "hard_assert"            |
                                    #   "preflight_check"        |
                                    #   "pathway_applicability"
    original_value:        string   # the failing value (e.g. the actual prior
                                    #   gate string, the hard_assert that
                                    #   evaluated false, or the pathway code
                                    #   that flagged N/A)
    reason:                string   # human-readable justification with
                                    #   evidence link (e.g. "continuation of
                                    #   apps_lakebase/<app>/.vibecoding-state.md
                                    #   run from 2026-04-12; see Per-Step Log
                                    #   ## Prompt 3.2 in that file")
    references:            [string] # OPTIONAL — structured back-references
                                    #   to the deferred action(s) or known
                                    #   quality issue(s) this override
                                    #   covers. Format:
                                    #   "deferred_action:<id>" or
                                    #   "known_issue:<id>". `enter` matches
                                    #   on this list (NOT on substring greps
                                    #   of `reason`) when deciding whether
                                    #   the override covers an open
                                    #   deferred-action or known-issue halt.
    authorized_by:         string   # operator email or signoff record
    applied_at:            string   # ISO8601 UTC
    expires_at:            string   # ISO8601 UTC — overrides MUST have a
                                    #   bounded lifetime; `enter` ignores
                                    #   expired entries
    affected_state_field:  string   # canonical state field whose normal
                                    #   gate semantics are being bypassed
                                    #   (e.g. "captured.last_verify_summary",
                                    #   "spec_provenance.schema_version")
```

`enter` rule (normative):

- For each gate evaluation, scan `state_overrides[]` for an entry whose
  `prompt_id` matches the current prompt AND `gate_type` matches the failing
  gate AND `expires_at` is in the future. If a match exists, the gate is
  treated as satisfied and the override is logged in the Per-Step Log
  `Resolved issues / workarounds` section. Without a match, `enter` halts.
- Overrides with `expires_at` in the past are inert; `enter` treats them as
  absent and halts on the underlying gate. Overrides whose `expires_at` is
  missing, null, `<pending>`, or otherwise not parseable as ISO8601 UTC are
  also treated as inert. `enter` halts on the underlying gate.
- An override on `gate_type: pathway_applicability` lets a prompt run even
  though the Pathway Applicability Matrix marks it as `—` (skip) for the
  current pathway/track. Use sparingly — it changes which gates downstream
  prompts can rely on.
- For `gate_type: hard_assert` and `preflight_check` halts triggered by an
  open `deferred_actions[]` or `mlflow_eval_known_quality_issues[]` entry,
  the override's `references[]` MUST contain a matching
  `"deferred_action:<id>"` or `"known_issue:<id>"` token whose `<id>` equals
  the action's or issue's `id`. The match is exact-string on the `id`, not
  a substring grep on `reason`. `reason` remains the free-text human
  explanation.

---

## Deferred Actions

`deferred_actions[]` makes the workshop's known cross-prompt dependencies
explicit. A deferred action is a piece of work that one prompt cannot complete
in-line (for instance, grants that depend on a deployed app, or column
grounding that depends on a later eval pass) but that another prompt **must**
verify before its own gate can pass. `enter` blocks the target prompt until
the action's `divergence_check` evaluates true (or a `state_override` exists).

```yaml
deferred_actions:
  - id:                    string   # stable identifier
    owner_prompt_role:     string   # the prompt role that originally surfaces
                                    #   the gap
    fix_owner_prompt_role: string   # the prompt role responsible for closing
                                    #   the gap (often == owner_prompt_role,
                                    #   but not always)
    target_prompt_roles:   [string] # prompt roles that MUST NOT run until
                                    #   the action is closed (use a single-
                                    #   element list when only one role is
                                    #   blocked)
    status:                string   # enum: "open" | "resolved" | "waived"
    divergence_check:      string   # boolean expression evaluated against the
                                    #   live state file; true == action closed
```

`enter` rule (normative):

- When the current prompt's role appears in any open deferred action's
  `target_prompt_roles[]`, evaluate `divergence_check` against the live
  state. If it returns false, halt with a remediation hint pointing at
  `fix_owner_prompt_role`. If true, mark the action `resolved` and proceed.
- A `state_override` with `gate_type: hard_assert` (or
  `preflight_check`) on the same `prompt_id` lets the prompt proceed without
  closing the action; the override's `references[]` MUST contain
  `"deferred_action:<id>"` matching the action's `id`.
- `status: waived` skips the divergence check entirely. Use only when the
  workshop run intentionally drops the downstream feature.

The canonical baseline (always present, status `open` until closed) is the
six seeds in `state-template.md`. Operators may add workshop-specific
deferred actions but MUST keep the six seeds.

### Divergence-check grammar

`divergence_check` (used by `deferred_actions[]`) and `remove_when` (used by
`productized_debts[]`) share the same boolean expression DSL evaluated against
the parsed live state file. The grammar is intentionally narrow:

- **Comparison operators:** `==`, `!=`, `>=`, `<=`, `>`, `<`.
- **Logical connectors:** `AND`, `OR` (capitalized; lowercase forms are NOT
  recognized). Connectors join two or more comparison sub-expressions; left-
  to-right precedence with no parentheses. `AND` binds tighter than `OR`.
- **Object-array indexing:** `<list>[<key>='<value>']` selects the first
  array element whose `<key>` field equals `<value>`. The bracket key may
  also reference another canonical state field, e.g.
  `endpoint_guardrail_audit[llm_role_endpoints.agent_chat.endpoint]` —
  the bracketed expression resolves to the value at that dotted path before
  indexing.
- **Dotted field access:** `<field>.<subfield>` walks nested objects.
- **String literals MUST be single-quoted.** Bareword sentinels used in the
  seeds (`resolved`, `present`, `passed`, `done`) MUST be quoted.
- **Boolean literals** stay as bareword `true` / `false` (no quotes).
- **Numeric literals** are bareword (no quotes); semver-shaped strings (e.g.
  `'3.12.0'`) are quoted and compared lexicographically.
- **Empty-array literal** is bareword `[]`. It is the only legal array
  literal in the grammar; non-empty array literals are not supported. Use
  `<field> == []` to assert a list is empty.

Examples (matching the six deferred-action seeds and the five productized-debt seeds):

- `"mlflow_eval_known_quality_issues[id='unresolved_column'].status == 'resolved'"`
- `"agent_runtime_consumes_registered_prompt == true"`
- `"eval_dataset_fields.expected_response == 'present'"`
- `"mlflow_labeling_session_dataset_enrichment_status == 'done'"`
- `"candidate_full_benchmark_reeval_status == 'passed'"`
- `"f2_grants_complete == true"`
- `"endpoint_guardrail_audit[llm_role_endpoints.agent_chat.endpoint].streaming_arg_accepted == true"`
- `"mlflow_version >= '3.12.0' AND judges_with_silent_aggregation_dropouts == []"`
- `"agent.retry_policy.api_connection_error_max_retries >= 3"`
- `"agent_runtime_consumes_registered_prompt == true OR mlflow_eval_known_quality_issues[id='unresolved_column'].status == 'resolved'"`

Note: `AND` binds tighter than `OR` (see § *Logical connectors* above). If
you need different precedence, split the predicate into two separate
`deferred_actions[]` / `productized_debts[]` entries — there are no
parentheses in this grammar.

If a `divergence_check` (or `remove_when`) string fails to parse under this
grammar, `enter` (or `audit_debts`) treats it as evaluating to false and
halts on the underlying gate (with a remediation hint pointing at the
deferred action's or debt's `id` / `name`).

---

## MLflow Eval Known Quality Issues

`mlflow_eval_known_quality_issues[]` records evaluation traces whose results
are known to be unreliable (tool warnings, jq paths returning null,
synthesized stand-ins, scorer floors not met). Surfacing the issue here turns
"silently ignored failure" into "explicit gate that blocks the listed
downstream prompts."

```yaml
mlflow_eval_known_quality_issues:
  - id:                          string   # stable identifier (e.g.
                                          #   "unresolved_column",
                                          #   "tool_warning_genie_query")
    source_prompt_role:          string   # prompt role that ran the failing
                                          #   eval and surfaced the issue
    trace_id:                    string   # MLflow trace ID for forensic
                                          #   linkage
    tool_name:                   string   # the tool whose call produced the
                                          #   issue (or "n/a" if not tool-
                                          #   specific, e.g. dataset coverage)
    error_signature:             string   # short canonical error string —
                                          #   used to dedupe and to match the
                                          #   `gate_load_bearing_checks[]`
                                          #   entry that should block on it
    status:                      string   # enum: "open" | "resolved" | "waived"
    target_prompt_roles_blocked: [string] # prompt roles that MUST NOT run
                                          #   until status != "open" (or a
                                          #   state_override exists)
```

`enter` rule (normative):

- When the current prompt's role appears in any open issue's
  `target_prompt_roles_blocked[]`, halt with a remediation hint pointing at
  the `source_prompt_role` and the `error_signature`. The only ways past are:
  flip `status` to `resolved`/`waived` (with evidence the underlying problem
  is fixed), or add a matching `state_override` whose `references[]` contains
  `"known_issue:<id>"` matching this issue's `id`. Free-text mentions of the
  `id` in `reason` are NOT sufficient — the match is structural.
- New issues appended at runtime MUST set `status: open` and populate
  `target_prompt_roles_blocked[]` with at least the immediate next prompt
  role downstream of `source_prompt_role`.

---

## Gate Load Bearing Checks

`gate_load_bearing_checks[]` is the canonical list of verify-job and audit
warning names that, when present, MUST block the gate rather than
soft-passing. It is the data backing
`bootstrap_preflight.verify_summary_semantics.warning_policy:
block_if_load_bearing` (see § *Bootstrap Preflight*) — when that policy is in
effect, any warning whose check name is in this list converts a "WARN" verdict
into a hard fail at the first verify gate.

**Consumers:**
- `state_contract_audit` (matches load-bearing warnings against this list).
- The first-verify-job summary path with `verify_summary_semantics.warning_policy: block_if_load_bearing` (Task 1.3).

`enter` does NOT directly consult this list — its halts come from `state_overrides[]`, `deferred_actions[]`, `mlflow_eval_known_quality_issues[]`, and prior gates. The list is informational for the audit and verify surfaces.

```yaml
gate_load_bearing_checks:
  - tool_warning                            # any tool-call surfaced a warning
                                            #   (e.g. truncated SQL result)
  - jq_path_returns_null                    # a canonical jq_path resolved to
                                            #   null in CLI output
  - scorer_below_floor                      # a primary scorer fell below its
                                            #   declared threshold
  - dataset_coverage_below_floor            # benchmark/eval dataset coverage
                                            #   below the per-bucket floor
  - synthesized_stand_in                    # a resolver/output synthesized a
                                            #   stand-in value where real data
                                            #   was expected (e.g. fake row,
                                            #   placeholder column)
  - time_to_label_below_floor               # human labeling SLA violated
  - open_deferred_action                    # any `deferred_actions[]` entry
                                            #   listing the current prompt
                                            #   role in `target_prompt_roles[]`
                                            #   is still `open`
  - open_known_quality_issue                # any
                                            #   `mlflow_eval_known_quality_issues[]`
                                            #   entry blocking the current
                                            #   prompt is still `open`
  - bundle_validate_warning_load_bearing    # `databricks bundle validate`
                                            #   surfaced a warning whose name
                                            #   is on the workshop's
                                            #   load-bearing list (e.g.
                                            #   missing schema grant,
                                            #   unprefixed dev-mode resource)
```

Semantics:

- This list is set at `bootstrap` from the merged workshop config and stored
  on the live state file. Workshops MAY append additional check names; they
  MUST NOT remove entries.
- `state_contract_audit` consults this list when classifying audit findings:
  load-bearing warnings are reported as failures (in `mode: fail`, they halt).
- `verify-job` summaries use the names verbatim — a check named
  `scorer_below_floor` in the verify-job's `warnings[]` array is matched
  against `gate_load_bearing_checks[]` by exact string equality.

---

## Productized Debts

`productized_debts[]` records workarounds the workshop deliberately ships with
because closing them in-line would derail the prompt that surfaces them. Each
debt carries a `remove_when` predicate that `audit_debts` evaluates against
the live state file; when the predicate flips true, the debt is marked
`debt_lifted: true` and the next implementation pass MUST remove the
workaround.

"Accepted permanent debt" means **no admin-ticket dependency exists** — the
workshop has full control of the predicate's inputs. It does NOT mean the
debt lacks a `remove_when` predicate. Every entry MUST carry one.

```yaml
productized_debts:
  - name:                       string   # stable identifier (snake_case)
    introduced_at_prompt_role:  string   # the prompt role that originally
                                         #   shipped the workaround
    remove_when:                string   # boolean expression evaluated by
                                         #   `audit_debts` against the live
                                         #   state file, using the same
                                         #   divergence-check grammar as
                                         #   `deferred_actions[]` (extended
                                         #   with AND/OR and `[]` empty-
                                         #   array literal — see
                                         #   § Divergence-check grammar)
    debt_lifted:                bool     # set true by `audit_debts` when
                                         #   `remove_when` evaluates true;
                                         #   the next implementation pass
                                         #   MUST then remove the workaround
    audit_history:                                 # append-only; one entry
                                                   #   per `audit_debts`
                                                   #   evaluation
      - audited_at:             string             # ISO8601 UTC
        debt_lifted_evaluation: string             # enum: "true" | "false"
                                                   #   | "parse_error"
        evaluator_evidence:                        # one entry per consulted
                                                   #   field/clause
          - field_path:         string             # e.g. "mlflow_version" or
                                                   #   "endpoint_guardrail_audit[...].streaming_arg_accepted"
            observed_value:     string             # observed value as a
                                                   #   string (e.g. "'3.11.4'",
                                                   #   "true", "[]")
            clause_outcome:     string             # enum: "pass" | "fail"
                                                   #   | "unresolvable"
        parse_error_detail:     string             # OPTIONAL — populated only
                                                   #   when debt_lifted_evaluation
                                                   #   == "parse_error"
```

For multi-clause `remove_when` predicates, `evaluator_evidence` MUST contain
one entry per clause consulted by the evaluator, in left-to-right order.
AND/OR short-circuiting may stop evaluation early; record only clauses
actually evaluated.

`audit_debts` rule (normative):

- Evaluate `remove_when` against the parsed live state file using the
  divergence-check grammar in § *Deferred Actions* (extended with `AND`,
  `OR`, and the `[]` empty-array literal — see § *Divergence-check grammar*
  in that section).
- If the predicate evaluates true, set `debt_lifted: true` and append an
  entry to `audit_history[]` with `debt_lifted_evaluation: true` and one
  `evaluator_evidence` entry per clause consulted (`clause_outcome: pass`
  for each).
- If the predicate evaluates false (or fails to parse), leave
  `debt_lifted: false` and append an entry with
  `debt_lifted_evaluation: false` (or `parse_error`) and one
  `evaluator_evidence` entry per clause consulted, recording each clause's
  `field_path`, `observed_value`, and `clause_outcome`. For `parse_error`,
  populate `parse_error_detail` with the parser message.
- In `mode: fail`, halt if any debt is marked `debt_lifted: true` but the
  workaround is still detected on a subsequent pass — this is the signal
  that an implementation pass missed its cleanup.

### Seeds

The five canonical seeds are pre-populated by `bootstrap` and MUST be
present on every live state file. Workshops MAY append additional debts
but MUST NOT remove these:

```yaml
productized_debts:
  - name: workspace_sse_guardrail
    introduced_at_prompt_role: appkit_agent_proxy
    remove_when: "endpoint_guardrail_audit[llm_role_endpoints.agent_chat.endpoint].streaming_arg_accepted == true"
    debt_lifted: false
  - name: mlflow_make_judge_aggregations_default
    introduced_at_prompt_role: first_scored_eval
    remove_when: "mlflow_version >= '3.12.0' AND judges_with_silent_aggregation_dropouts == []"
    debt_lifted: false
  - name: predict_fn_input_guardrail_sentinel
    introduced_at_prompt_role: instruction_iteration
    remove_when: "endpoint_guardrail_audit[llm_role_endpoints.llm_judge_default.endpoint].sql_quote_ok == true"
    debt_lifted: false
  - name: predict_fn_api_connection_sentinel
    introduced_at_prompt_role: instruction_iteration
    remove_when: "agent.retry_policy.api_connection_error_max_retries >= 3"
    debt_lifted: false
  - name: predict_fn_sql_table_not_found_sentinel
    introduced_at_prompt_role: instruction_iteration
    remove_when: "mlflow_eval_known_quality_issues[id='unresolved_column'].status == 'resolved'"
    debt_lifted: false
```

Each seed begins with `audit_history: []`; entries are appended on every
`audit_debts` run.

---

## Preflight Check Registry

`preflight_check_registry` is the canonical map of every named preflight check
the workshop knows about. Each entry maps a check name to the skill or prompt
that owns it (`owner`) and the prompt roles whose `enter` MUST halt while the
check has not been recorded as passing (`blocks_prompt_roles[]`). This is the
single source of truth that downstream skills/prompts cite by check name —
schema drift in the registry surfaces immediately because `state_contract_audit`
verifies every `owner` resolves to a real skill path and every check name
referenced from a prompt body resolves to a registry entry.

The registry is shaped as a map keyed by check name (one block per check),
matching the dict-shaped style of `canonical_names.env_vars` and
`endpoint_guardrail_audit`. `enter` and `state_contract_audit` are the only
operations that consume the registry; no new operation is added in this pass.

```yaml
preflight_check_registry:
  <check_name>:
    owner:                string   # skill or prompt id that owns the check
    blocks_prompt_roles:  [string] # prompt roles whose `enter` halts while
                                   #   this check has not passed
```

### Seeds

The canonical seeds are populated by `bootstrap` and MUST be present on
every live state file. Workshops MAY append additional checks but MUST NOT
remove these. (The last seed, `genie_code_manifest_loaded`, is
**client-conditional** — inert on `ide_cli`; see § *State-field mapping* and
the *Genie Code manifest-load gate (normative)* rule below.)

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
  genie_code_manifest_loaded:                    # G3 — client-conditional
    owner: skills/genie-code-environment
    blocks_prompt_roles: [deploy_app, appkit_agent_proxy]
```

The `genie_code_manifest_loaded` seed's `owner` (`skills/genie-code-environment`)
is a **real repo-root skill path** (promoted to `skills/` in Milestone 06 batch
6a), so `state_contract_audit` resolves it like any other skill owner — it is
**not** a forward-reference and carries no land-later carve-out.

**Forward-reference handling (Phase 1.7 → Phase 2/4 sequencing) — RESOLVED.**
The registry was seeded in Phase 1.7 ahead of its producer phases. Each producer
phase has now landed and the corresponding owners/roles resolve to real skills
and prompt roles in the workshop's prompt registry:

- `instruction_iteration` — Phase 2.2 (08b prompt hand-authoring skill at
  `genai-agents/sdlc/08b-prompt-hand-authoring/SKILL.md`). **Resolved.**
- `deployed_app_chat`, `deployed_app_trace_feedback`, `appkit_agent_proxy` —
  Phase 2.1 (applicability matrix prompt-role identifiers). **Resolved.**
- `lakebase_memory` — Phase 4.4 cold-start retry policy contract owned by
  Track A 02 (`tracks/A-custom-agent-apps/02-agent-framework/SKILL.md`) and
  consumed by AppKit 07. **Resolved.** (The `owner: lakebase_memory` value is
  a logical owner alias; the actual producer skill is Track A 02 — see the
  State-field mapping note for `lakebase_cold_start_retry_policy_present`.)
- `local_eval_smoke`, `first_scored_eval`, `trace_feedback`,
  `production_debug`, `monitoring` — Phase 2.1 applicability matrix
  prompt-role identifiers. **Resolved.**

The forward-reference carve-out for these entries is **lifted**:
`state_contract_audit` § *Preflight Check Registry extension* MUST treat
unresolved owners or `blocks_prompt_roles[]` entries from this list as drift
(`mode: fail`) — they no longer have a "scheduled to land later" exemption.
No registry entries currently retain the carve-out; future seeds added ahead
of their producer phase MUST be added back to this list with an explicit
phase reference.

**Overlap with `deferred_actions[]`.** The check `f2_grants_complete` reads
the same top-level boolean field consumed by `deferred_actions[]` § seed
`f2_grants_complete`. The overlap is intentional: the preflight registry is
the fast fail-closed wrapper, while the deferred action is the longer-lived
remediation tracker. Both halts cite the same evidence link. A
`state_override` whose `references[]` contains
`"deferred_action:f2_grants_complete"` covers both halts.

### State-field mapping

Each registry entry corresponds to a state field whose value `enter` reads to
decide whether the check has passed. The mapping is:

| Check name | State field read | Pass condition | Notes |
|------------|------------------|----------------|-------|
| `workspace_url_not_placeholder` | `bootstrap_preflight.workspace_url_was_placeholder` | `== false` | Populated by `bootstrap` step 1 (workspace URL normalization). |
| `workspace_profile_matches_host` | `bootstrap_preflight.workspace_host_auth_status` | `== 'authenticated'` | Populated by `bootstrap` step 2 (profile selection & host match). |
| `databricks_cli_min_version` | `bootstrap_preflight.databricks_cli_version` vs `bootstrap_preflight.databricks_cli_min_version` | installed `>=` minimum — **OR** `databricks_cli_version == "unknown_on_genie_code"` (sentinel auto-satisfies; the numeric compare is undefined on Genie Code, so the `deploy_app` / `appkit_agent_proxy` deploy is gated by the `bundle validate` behavior probe instead — Gap-1) | Populated by `bootstrap` step 3 (CLI version preflight, client-branched). |
| `databricks_apps_capacity` | `bootstrap_preflight.apps_quota.free_slots` | `>= 1` | Populated by `bootstrap` step 4 (apps quota preflight). The `apps_quota.free_slots` field is declared `integer` in § *Bootstrap Preflight*. |
| `mlflow_tracing_sql_warehouse_id_present` | `MLFLOW_TRACING_SQL_WAREHOUSE_ID` (canonical env var per `canonical_names.env_vars`) | non-empty | Produced by F2 (experiment tracing foundation). |
| `predict_fn_signature_matches_runner` | `evaluation_runs_preflight.predict_fn_signature_matches_runner` | `== true` | Produced by SDLC Skill 04 (Evaluation Runs). See § *Evaluation Runs Preflight*. The Skill 04 eval-telemetry contract captures `mlflow_eval_predict_fn_signature` per run; the boolean is set true once a run completes whose captured signature matches the runner-expected `(inputs: dict) -> str` or `(inputs: dict) -> dict` shape. |
| `reflection_lm_large_context_probe` | `endpoint_guardrail_audit[llm_role_endpoints.reflection_lm.endpoint].long_context_ok` AND `accepted_min_context_chars >= 80000` | both true | Produced by `instruction_iteration` (Phase 2.2 / Skill 08b) — see § *Reflection LM large-context probe (normative)* below. |
| `f2_grants_complete` | `f2_grants_complete` | `== true` | Bare top-level boolean produced by F2 (`genai-agents/foundation/02-experiment-tracing-and-uc-storage/SKILL.md`). Bare-on-purpose (similar to `agent_runtime_consumes_registered_prompt`); not an ad-hoc-naming artifact. Overlaps with `deferred_actions[]` seed `f2_grants_complete` — see *Overlap with `deferred_actions[]`* above. |
| `lakebase_cold_start_retry_policy_present` | `lakebase_cold_start_retry_policy.max_attempts` AND `lakebase_cold_start_retry_policy.retry_on` | `max_attempts >= 3` AND `retry_on` includes `'AdminShutdown'` | Produced by Track A 02 (`tracks/A-custom-agent-apps/02-agent-framework/SKILL.md`) — canonical retry-class allowlist is `[AdminShutdown, psycopg_pool.PoolClosed]`. Phase 4.4 contract; AppKit 07 consumes the same field. |
| `system_prompt_review_complete` | `system_prompt_review` block | All three preflight checks in `## System Prompt Review` § *enter rule* pass. | See § *System Prompt Review* for the canonical evaluation rule (the registry entry is the registry-side enforcement; the H2 § *enter rule* is the canonical evaluation logic). |
| `genie_code_manifest_loaded` | `environment_capabilities.client_context` **and** `environment_capabilities.genie_code_manifest_loaded` | `client_context != 'genie_code'` (inert — auto-pass) **OR** `genie_code_manifest_loaded == true` | **Client-conditional (G3).** Owned by `skills/genie-code-environment`; seeded by `bootstrap` step 0 (`n/a` on `ide_cli`, `false` on `genie_code`). The owning manifest flips it `true` when read in the current thread. See § *Genie Code manifest-load gate (normative)* below. |

### Reflection LM large-context probe (normative)

The `reflection_lm_large_context_probe` check MUST NOT be inferred from the
generic bootstrap endpoint guardrail audit alone. Before any prompt that calls
into 08b's diff-summary helper or any iteration helper that consumes
`llm_role_endpoints.reflection_lm.endpoint`, the owning skill
(`instruction_iteration`) MUST run a synchronous synthetic request of
`>= 80000` characters against the bound endpoint and record the result on
`endpoint_guardrail_audit[<reflection_lm.endpoint>].accepted_min_context_chars`
and `long_context_ok`. This preserves the proven Prompt 20g v2 preflight pattern
while removing GEPA from the flow. `enter` halts the listed
`blocks_prompt_roles[]` until both `long_context_ok == true` AND
`accepted_min_context_chars >= 80000` are recorded for the bound endpoint.

### Genie Code manifest-load gate (normative)

The `genie_code_manifest_loaded` check (G3) is the **only client-conditional**
entry in the registry: it is **inert on `ide_cli`** (the behavioral manifest is
optional there — the IDE path is the default and the skill bodies already read
client-agnostic) and **fail-closed on `genie_code`**. Its purpose is the
self-sufficiency hedge (decision #9 / regression I8): before a Genie Code agent
runs its first client-divergent operation — the **first deploy** (`deploy_app`,
`appkit_agent_proxy`) — it MUST have loaded the `skills/genie-code-environment`
behavioral manifest, so the `runDatabricksCli` allow-list tiers, the
bundle-deploy CWD pin + FUSE create-then-validate gap, the App-scaffold
output-dir rule, and the deployed-app OAuth-session pattern are in context.

- **Evaluation.** When the current prompt's role is in `blocks_prompt_roles[]`,
  `enter` reads `environment_capabilities.client_context`. If it is **not**
  `genie_code`, the check is **inert** (auto-pass — no field is consulted). If
  it is `genie_code`, the check passes only when
  `environment_capabilities.genie_code_manifest_loaded == true`; otherwise
  (`false` / `<pending>` / `n/a`) `enter` **halts** with a remediation hint
  pointing at `owner` (`skills/genie-code-environment`): *"read the
  genie-code-environment manifest, then set
  `environment_capabilities.genie_code_manifest_loaded: true`."*
- **Producer.** The owning manifest `skills/genie-code-environment` is
  responsible for flipping the field `true` when it is read in the current
  thread (it carries the matching instruction). `bootstrap` step 0 seeds the
  field (`n/a` on `ide_cli`, `false` on `genie_code`).
- **"This thread" intent.** The flag records a load **in the current Agent
  thread**. On a fresh Genie Code thread the manifest is no longer in context,
  so the agent re-reads it and re-affirms the flag; if `genie_code_manifest_loaded`
  was carried over `true` from a prior thread but the manifest is not in the
  current context, treat it as unread and re-load (degrade-don't-trust). The
  usual escape hatch applies — a `state_override` with
  `gate_type: preflight_check` and `affected_state_field:
  environment_capabilities.genie_code_manifest_loaded`.

### `enter` rule (normative)

- For every check in `preflight_check_registry`, when the current prompt's
  role appears in `blocks_prompt_roles[]`, evaluate the matching state field
  per the State-field mapping table above. If the pass condition is not met
  (or the field is `<pending>` / missing), halt with a remediation hint
  pointing at `owner`. The only ways past are: record the check passing in
  the matching state field, or add a `state_override` with
  `gate_type: preflight_check` whose `affected_state_field` matches the
  check's state field.
- For `reflection_lm_large_context_probe`: `enter` halts unless the synchronous
  large-context probe described above has been recorded for the currently bound
  `llm_role_endpoints.reflection_lm.endpoint`. A passing
  `endpoint_guardrail_audit` entry from bootstrap is NOT sufficient on its own
  — the `accepted_min_context_chars >= 80000` floor MUST be present.
- For `genie_code_manifest_loaded`: `enter` evaluates the check **only when
  `environment_capabilities.client_context == 'genie_code'`** (inert otherwise —
  the sole client-conditional check). On `genie_code` it halts the listed deploy
  roles until `environment_capabilities.genie_code_manifest_loaded == true`. See
  § *Genie Code manifest-load gate (normative)* above.

### `state_contract_audit` rule (normative)

- Every `preflight_check_registry[<check>].owner` MUST resolve to either a real
  skill path under `skill_root` or a known prompt id present in the workshop's
  prompt registry. Unresolved owners are reported as
  `fields_read_but_never_produced` (with the `owner` value as the field) so
  `mode: fail` halts.
- Every check name cited in a prompt body or skill `fields_read:` list MUST
  exist in the registry. Unknown names are reported the same way.

---

## Evaluation Runs Preflight

`evaluation_runs_preflight` is the canonical state block consumed by
`preflight_check_registry.predict_fn_signature_matches_runner`. Owned by SDLC
Skill 04 (`genai-agents/sdlc/04-evaluation-runs/SKILL.md`); written from the
Skill 04 eval-telemetry contract once a scored run completes whose captured
`mlflow_eval_predict_fn_signature` matches the runner-expected
`(inputs: dict) -> str` or `(inputs: dict) -> dict` shape. Replaces the
ad-hoc top-level `predict_fn_signature_matches_runner_status: passed` field
seeded earlier in Phase 1.7 — that name was non-namespaced and used a stringly
enum where a boolean was sufficient.

```yaml
evaluation_runs_preflight:
  predict_fn_signature_matches_runner: bool     # true once a Skill 04 run has
                                                #   captured an
                                                #   `mlflow_eval_predict_fn_signature`
                                                #   matching the runner-expected
                                                #   `(inputs: dict) -> str` or
                                                #   `(inputs: dict) -> dict` shape
  last_run_at:                         string   # ISO8601 UTC of the most recent
                                                #   Skill 04 run that wrote into
                                                #   this block; "<pending>" before
                                                #   any run has executed. Carried
                                                #   for audit traceability.
```

**Producer.** SDLC Skill 04 writes both fields after every scored evaluation
run as part of the eval-telemetry contract. The boolean flips `true` the first
time a run completes whose `mlflow_eval_predict_fn_signature` matches the
runner-expected shape; subsequent matching runs leave it `true` and refresh
`last_run_at`. A run whose captured signature does not match flips the boolean
back to `false` (the registry check halts the next prompt in
`blocks_prompt_roles[]` until the operator fixes the signature and re-runs).

**Consumer.** `preflight_check_registry.predict_fn_signature_matches_runner`
reads `evaluation_runs_preflight.predict_fn_signature_matches_runner == true`.
The registry check halts `local_eval_smoke` and `first_scored_eval` while the
boolean is `false` (or the block is missing).

---

## System Prompt Review

`system_prompt_review` records the structured pre-eval audit of the agent's
hand-authored system prompt. The motivating finding (SkyLoyalty Prompt 20d
retro): the system prompt was hand-authored at Prompt 12 and shipped through
eight intervening prompts to its first scored eval at Prompt 20d without any
review pass — and three of the agent's own `must_do` clauses regressed below
threshold there (`source_citation`, `time_period_disclosure`,
`intermediate_results_visible`). The fix is a single 5-minute pre-eval review
in which each `must_do` / `must_not_do` rule is operationalized with at least
one worked example before the first scored eval is allowed to run.

```yaml
system_prompt_review:
  complete:                bool     # true once every must_do / must_not_do
                                    #   clause has at least one worked example
                                    #   AND the operator has signed off
  reviewed_at:             string   # ISO8601 UTC; "<pending>" before review
  reviewed_by:             string   # operator email or signoff record
  must_do_worked_examples:          # one entry per `agent.must_do` clause
    - rule:                string   # the must_do clause being operationalized
                                    #   (verbatim from agent.must_do[])
      positive_example:    string   # a concrete, copy-paste-ready example of
                                    #   the agent obeying the rule (e.g. an
                                    #   exact line of output, a short
                                    #   transcript, a tool-call shape)
      expected_behavior:   string   # one sentence describing what the
                                    #   evaluator should look for in the
                                    #   model's output
  must_not_do_worked_examples:      # one entry per `agent.must_not_do` clause
    - rule:                string   # the must_not_do clause being
                                    #   operationalized (verbatim from
                                    #   agent.must_not_do[])
      negative_example:    string   # a concrete example of the prohibited
                                    #   behavior the agent must refuse or
                                    #   correct
      refusal_or_correction: string # one sentence describing how the agent
                                    #   should refuse, redirect, or correct
                                    #   the negative example
```

Defaults at bootstrap: `complete: false`, `reviewed_at: <pending>`,
`reviewed_by: <pending>`, `must_do_worked_examples: []`,
`must_not_do_worked_examples: []`. The two example arrays are populated by
the prompt that runs the system-prompt review (Prompt 7.20 in `Instructions.md`,
Prompt 20d in `example/skyloyalty/WALKTHROUGH.md`, section
`mlflow_agent_quality_judges` in `docs/02_seed_section_input_prompts.sql`).

`enter` rule (normative). This check is also registered in
`preflight_check_registry` as `system_prompt_review_complete` per Phase 1.7's
registry-as-canonical contract. The first scored eval prompt MUST evaluate the
following preflight checks before any benchmark run:

```yaml
preflight_checks:
  - system_prompt_review.complete == true
  - count(system_prompt_review.must_do_worked_examples) >= count(agent.must_do)
  - count(system_prompt_review.must_not_do_worked_examples) >= count(agent.must_not_do)
```

Halt suppression follows the standard
`state_overrides[gate_type=preflight_check]` rule (see § *State Overrides*).
The `affected_state_field` for the override MUST be one of
`system_prompt_review.complete`,
`system_prompt_review.must_do_worked_examples`, or
`system_prompt_review.must_not_do_worked_examples` depending on which clause
fails. The field paths `agent.must_do` and `agent.must_not_do` are the
canonical names from § *Agent* — DO NOT introduce a parallel
`agent.system_prompt.must_do_rules` shape.

### Divergence-check grammar extension: `count()`

The preflight checks above introduce one extension to the divergence-check
grammar (see § *Deferred Actions* → *Divergence-check grammar*): the builtin
function `count(<list_path>)`. It evaluates to the integer length of the
list at the resolved dotted path. Semantics:

- The argument MUST be a single dotted path that resolves to a YAML list at
  parse time. Non-list values resolve to `0`.
- `count()` is the ONLY function call permitted in the grammar. No
  user-defined functions, no other builtins, and no nested function calls
  (`count(count(...))` is not legal).
- `count()` may appear on either side of a comparison operator and may
  combine with `AND` / `OR` connectors per the existing grammar rules.

Examples:

- `"count(system_prompt_review.must_do_worked_examples) >= count(agent.must_do)"`
- `"count(agent.must_not_do) > 0 AND count(system_prompt_review.must_not_do_worked_examples) >= count(agent.must_not_do)"`

Parse failures (e.g. `count(<unparseable_path>)`, multi-argument calls,
nested calls) MUST be treated identically to other parse failures: evaluate
to false and halt on the underlying gate with a remediation hint pointing
at the offending preflight check.

---

## Skill Helper Resolutions

`skill_helper_resolutions[]` records the concrete shape selected by
`vibecoding-state.skill_helper_resolution` for every skill-prescribed helper
the workshop has probed. Each entry pins one resolution per `contract_name`;
re-running the operation replaces the prior entry rather than appending a new
one (the most recent `probed_at` always wins).

The motivating finding (recurring-issue #11 in the SkyLoyalty retrospective):
"skill helper vs concrete shape" mismatches recurred 12+ times across Prompts
9 / 13 / 14 / 15 / 16 / 17 / 18 / 20a / 20c / 20d / 20e / 20g v1 — the skill
prescribes a "canonical" surface (an import, a signature, a bundle field, a
JSON path) that the workspace does not ship in that exact shape. The agent
rediscovers the right shape, captures it ad hoc, but the skill stays
unchanged. Lifting resolution into a single operation lets every consuming
skill emit `(contract_name, candidates[], min_cli_version,
inline_template_fallback)` and inherit the same first-callable-wins probe +
capture contract.

```yaml
skill_helper_resolutions:
  - contract_name:        string   # stable identifier emitted by the
                                   #   consuming skill (e.g. "obo_helper",
                                   #   "predict_fn_signature",
                                   #   "genie_space_resource_schema",
                                   #   "apps_get_status_jq_path")
    selected_kind:        string   # enum:
                                   #   "import_path"                     |
                                   #   "function_signature"              |
                                   #   "bundle_resource_schema"          |
                                   #   "api_field_path"                  |
                                   #   "cli_field_path"                  |
                                   #   "cli_version_dependent_schema"    |
                                   #   "inline_template_fallback"
    selected_value:       string   # the candidate's `value` string (or the
                                   #   `inline_template_fallback` string
                                   #   when no candidate's probe succeeded)
    probed_at:            string   # ISO8601 UTC of the run that selected
                                   #   this entry — replaces any prior
                                   #   entry with the same `contract_name`
    fallback_used:        bool     # true when every candidate's probe
                                   #   failed and `inline_template_fallback`
                                   #   was selected; false when a real
                                   #   candidate resolved
```

### Candidate kinds

The six `selected_kind` enum values map to the six probe shapes
`skill_helper_resolution` recognizes (see `SKILL.md` §
*Operation: skill_helper_resolution* for the per-kind probe semantics). A
seventh value (`inline_template_fallback`) is reserved for the case where
every candidate fails and the consuming skill ships a concrete in-template
helper (e.g. `agent_server/long_term_memory.py` for the missing
`databricks_openai.LongTermMemory` case at Prompt 15).

| Kind | Probe surface | Recurring-issue example |
|---|---|---|
| `import_path` | `importlib.util.find_spec` | Prompt 14: `databricks_app.utils.get_user_workspace_client` not installed; in-template helper at `agent_server.utils.get_user_workspace_client` is functionally identical. |
| `function_signature` | `inspect.signature` matches contract | Prompt 16: skill prescribes `predict_fn(messages: list[dict])`; runner expects `predict_fn(question: str) -> str`. |
| `bundle_resource_schema` | `databricks bundle validate --output json` accepts the field set without load-bearing warnings | Prompt 17: `genie_space` needs `name` + `space_id` (not bare `id`); `apps` resource needs `experiment.id` vs `experiment.experiment_id`. |
| `api_field_path` | Read against the endpoint returns non-null at the JSON path | KA serving Responses API `input` vs Chat Completions `messages`. |
| `cli_field_path` | jq path against `databricks <cmd> --output json` returns non-null | `apps get .status.state` vs `.app_status.state` (cross-checks `canonical_names.jq_paths`). |
| `cli_version_dependent_schema` | Installed CLI `>= min_cli_version` AND validate accepts the field without stripping. **On Genie Code (`databricks_cli_version == "unknown_on_genie_code"`)** the version term drops out and the candidate is eligible iff the `databricks bundle validate` probe alone accepts the field (Gap-1). | Prompt 18: v0.297.1's `AppResourceApp` schema silently strips fields; v0.298.0 forwards them. |
| `inline_template_fallback` | n/a — selected only when every other candidate failed | Prompt 15: `databricks_openai.LongTermMemory` does not exist; ship a reference module from the template. |

### Consumer contract

Consuming skills that depend on a resolved helper MUST cite the entry by
`contract_name` in their `fields_read:` frontmatter via the canonical path
`skill_helper_resolutions[contract_name='<name>'].selected_value`. This is
the only path-shape `state_contract_audit` accepts for skill-helper reads;
bare `obo_helper` or `predict_fn_signature` reads (without the registry
indexing) are flagged as legacy spellings and reported under
`fields_read_but_never_produced`.

`state_contract_audit` extends its drift checks to verify (a) every
`fields_read:` entry naming a `contract_name` resolves to an entry in the
live state file's `## Skill Helper Resolutions` section, and (b) every
`skill_helper_resolutions[].selected_kind` is one of the seven enum values
above (rejecting any free-form kind a consuming skill might invent).

### Bootstrap default

Bootstrap initializes `skill_helper_resolutions: []`. Entries are appended
the first time any consuming skill calls `skill_helper_resolution`; there
are no seeds (unlike `productized_debts[]` or `preflight_check_registry`).

---

## Field Consumer Contract

v1.0 maintained a prose `## Field Consumers` table in this file. v2.0 replaces
that with **machine-parseable `fields_read:` frontmatter** on every consumer
skill.

### Declaration format

Every consumer skill MUST declare a top-level `fields_read:` YAML list in its
frontmatter. Each list entry is a dotted-path string rooted at a v2.0 top-level
key. Example:

```yaml
---
name: 02-appkit-build
# ... existing frontmatter keys ...
fields_read:
  - resources.tables
  - ui.description
  - ui.personas
  - ui.pages
  - ui.overview_widgets
  - ui.sql_files
  - ui.user_journeys
---
```

### Known consumer skills (v2.0)

| Skill | Declares reads on |
|-------|-------------------|
| `apps_lakebase/skills/02-appkit-build` | `resources.tables`, `ui.*` |
| `apps_lakebase/skills/05-appkit-lakebase-wiring` | `resources.tables` (kind=lakebase only) |
| `apps_lakebase/skills/06b-appkit-supervisor-wiring` | `agent.system_prompt`, `agent.model`, `agent.auth_mode`, `agent.tools` (hosted), `agent.knowledge_base_backend` |
| `apps_lakebase/skills/06c-appkit-integrated-agent` | `agent.*` (most), `governance.verification.smoke_test_question` |
| `genai-agents/foundation/03-tools-and-data-access` | `resources.knowledge_bases`, `resources.genie_spaces`, `resources.vector_indexes`, `agent.tools`, `agent.mcp_servers`, `agent.knowledge_base_backend`, `agent.external_integrations` |
| `genai-agents/sdlc/02-evaluation-datasets` | `ui.user_journeys`, `agent.benchmark_seeds.*` |
| `genai-agents/sdlc/03-scorers-and-judges` | `governance.scorer_suite.*` |
| `genai-agents/sdlc/04-evaluation-runs` | `agent.reviewer_role` |
| `genai-agents/sdlc/04b-stakeholder-signoff` | `governance.monitoring.rollback_trigger_example` |
| `genai-agents/sdlc/07-production-monitoring` | `governance.scorer_suite.production_scorers`, `governance.monitoring.required_alerts` |
| `genai-agents/tracks/A-custom-agent-apps/02-agent-framework` | `agent.system_prompt`, `agent.capabilities`, `agent.model` |
| `genai-agents/tracks/A-custom-agent-apps/03-tools-and-mcp` | `agent.tools`, `agent.mcp_servers`, `agent.knowledge_base_backend` |
| `genai-agents/tracks/A-custom-agent-apps/05-lakebase-memory` | `agent.memory`, `agent.benchmark_seeds.seed_examples`, `governance.verification.smoke_test_question` |
| `genai-agents/tracks/A-custom-agent-apps/06-evaluation` | `agent.benchmark_seeds.seed_examples`, `governance.verification.smoke_test_cases` |
| `genai-agents/tracks/A-custom-agent-apps/08-debugging` | `governance.scorer_suite.primary_scorer` |
| `alternate_methods/tracks/A-custom-agent-apps-node/02-agent-framework-node` | `agent.system_prompt`, `agent.capabilities`, `agent.model` |
| `alternate_methods/tracks/A-custom-agent-apps-node/03-tools-and-mcp-node` | `agent.tools`, `agent.mcp_servers`, `agent.knowledge_base_backend` |
| `alternate_methods/tracks/A-custom-agent-apps-node/05-lakebase-memory-node` | `agent.memory`, `agent.benchmark_seeds.seed_examples`, `governance.verification.smoke_test_question` |
| `alternate_methods/tracks/A-custom-agent-apps-node/06-evaluation-node` | `agent.benchmark_seeds.seed_examples`, `governance.verification.smoke_test_cases` |

### Drift check

`retrospective.rollup` computes:

- `consumed_fields` = union of every consumer skill's `fields_read:` list,
  expanded to leaf paths (e.g. `ui.*` expands to every leaf under `ui`).
- `produced_fields` = set of dotted-path leaves in the live state file's
  `## Resources`, `## UI`, `## Agent`, `## Governance` blocks (after YAML
  parse).

The rollup halts with a clear error if:

1. `produced_fields - consumed_fields ≠ ∅` — resolver emits a field nothing
   reads (likely a stale field that should be deleted or a missing consumer).
2. `consumed_fields - produced_fields ≠ ∅` — a skill declares it reads a
   field not emitted (likely a schema drift or a typo in `fields_read:`).

See `retrospective-template.md` for the exact rollup prompt.

---

## Validation Rules

`resolve_spec` halts if any of these fail:

1. Every field marked `required` in the schema above is present and non-empty.
2. **Tool discriminator contract**: every `agent.tools[].kind` is one of
   `hosted | function | mcp`, and the kind-specific required fields are present:
   - `kind == "hosted"`: `hosted_type` and `resource_ref` both non-empty.
   - `kind == "function"`: `language` ∈ `{python, typescript}`.
   - `kind == "mcp"`: `mcp_server_ref` resolves to an entry in
     `agent.mcp_servers[].name`.
3. Every `governance.scorer_suite.guidelines[].name` is unique.
4. Every `governance.scorer_suite.custom_scorer_rules[].tool_name` exists in
   `agent.tools[].name`.
5. `agent.benchmark_seeds.seed_examples` has `>= 20` entries after dedup.
6. `agent.benchmark_seeds.seed_examples[].bucket` is always in
   `agent.benchmark_seeds.coverage_buckets`.
7. `agent.reviewer_role` is one of `ui.personas[].name`.
8. If `agent.external_integrations.web_search_required == true`, at least one
   `agent.tools[].kind == "function"` whose name hints at web search.
9. `variant_id` ∈ the five-variant enum.
10. `agent.mcp_servers[].name` values are unique within the list.
11. Every `resources.tables[].kind` ∈ `{warehouse, lakebase}`.
12. `agent.memory.provider` ∈ `{lakebase, postgres, none}`. If `none`,
    `agent.memory.table_prefix` must be `"n/a"`.

---

## Migration from v1.0

See `scripts/migrate-spec-v1-to-v2.py`. The migrator is deterministic for
most fields; tool-kind inference has a documented heuristic (§ C.9 of the
follow-up plan) and prints warnings on ambiguity.

After migration, run `resolve_spec --validate-only` (or equivalent) to
re-check the state file against the Validation Rules above.
