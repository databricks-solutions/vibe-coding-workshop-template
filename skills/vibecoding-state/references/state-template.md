# Vibecoding State — <USE_CASE_SLUG>

<!--
This is the GENERALIZED state-file template for the Instructions.md workshop.
It lives inside the `vibecoding-state` skill so it travels with the
skill to any project that adopts this course.

WORKFLOW:
  1. At the start of the workshop, the agent reads this template directly
     from `skills/vibecoding-state/references/state-template.md`
     and copies it to the bootstrap live path:
       example/<use_case_slug>/.vibecoding-state.md
     (there is NO intermediate per-use-case template — one copy, not two.)
  2. Replace <USE_CASE_SLUG> in the title and <ISO timestamp> placeholders.
     Fill Workshop Choices from the PRD.
  3. `vibecoding-state.resolve_spec` (schema v2.0) runs once, deriving
     `variant_id` from Workshop Choices (pathway+track) and writing the six
     spec sections — ## Variant, ## Resources, ## UI, ## Agent, ## Governance,
     ## Spec Provenance — into the header (above the history marker that
     immediately precedes ## Per-Step Log). `## Per-Step Log` is the only
     section that lives below the history marker; everything `enter` may
     read (workshop choices, captured ids, the six spec sections, contracts,
     and audits) lives above. See `spec-schema.md` and `resolver-prompt.md`
     for the exact shape, and the "State File Size Discipline" section in
     this skill's SKILL.md for the header/history split rationale.
     ## Bootstrap Preflight is written by the bootstrap operation BEFORE the spec is resolved; it sits above ## Per-Step Log so its values are visible to every prompt that reads state.
     ## State File Set and ## Canonical Names also sit above ## Per-Step Log: ## State File Set is filled in (or left at defaults) by `bootstrap` and consulted by `enter` whenever a prompt must read both an AppKit and an agent state file; ## Canonical Names is the registry of pinned spellings (env vars, headers, jq paths, prompts:/ scheme, eval dataset columns) and is read by every prompt and by `state_contract_audit`.
     ## State Overrides, ## Deferred Actions, ## MLflow Eval Known Quality Issues, ## Gate Load Bearing Checks, ## Productized Debts, ## Preflight Check Registry, ## System Prompt Review, and ## Skill Helper Resolutions also sit above ## Per-Step Log: they are the fail-closed contract `enter` (and `audit_debts`, `skill_helper_resolution`) consults on every prompt. State overrides are the only way past a failed gate / hard_assert / preflight / pathway-applicability check (cross-session continuity is recorded here, not in prose). Deferred actions are the canonical baseline of cross-prompt dependencies that block downstream prompts until their `divergence_check` returns true. Known quality issues block the listed `target_prompt_roles_blocked[]` until status flips off `open`. Gate load-bearing checks back the verify-job `warning_policy: block_if_load_bearing` rule. Productized debts record workarounds the workshop deliberately ships with — `audit_debts` evaluates each `remove_when` predicate and flips `debt_lifted: true` when the workaround can be removed. The preflight check registry is the canonical map of named preflight checks (owner skill/prompt + `blocks_prompt_roles[]`); `enter` halts every listed prompt role until the matching state field records the check as passing. The system-prompt review records the pre-eval worked-example audit of `agent.must_do` / `agent.must_not_do` (defaults: `complete: false`, both example arrays empty); `enter` halts the first scored eval prompt until each rule has at least one worked example and the operator has signed off. Skill helper resolutions record the concrete shape selected for every skill-prescribed helper contract probed at runtime (defaults: empty list); consuming skills cite resolved helpers via `skill_helper_resolutions[contract_name='<name>'].selected_value`.
  4. The state file is migrated (or, for a data-product run, bootstrap-created) at
     its canonical live path as soon as the owning root is resolved:
       - Pathways A / B / C:  <app_root>/.vibecoding-state.md  (= <artifact_root>/<app_name>/.vibecoding-state.md, the top-level app dir — NOT apps_lakebase/<app_name>/), once $APP_NAME is known (Module 1).
       - Track A agent app (Pathways C / D): <agent_app_root>/.vibecoding-state.md  (= <artifact_root>/<agent_app_name>/.vibecoding-state.md, the top-level agent app dir — NOT apps_lakebase/<agent_app_name>/), once $AGENT_APP_NAME is known (Track A clone / Module 4).
       - Data-product / lakehouse track (Bronze→Silver→Gold→semantic, no app/agent app): <dp_bundle_root>/.vibecoding-state.md  (= <artifact_root>/{user_schema_prefix}_<use_case_slug>_dab/.vibecoding-state.md, the data-product bundle root). The FIRST lakehouse prompt (Bronze) bootstrap-creates it from this template if absent — DP-track state must NOT be left in the temporary example/ path (that omission was the "state survived only in chat summary" defect). This is the data-product analog of <app_root>/<agent_app_root>.
  5. Every subsequent prompt READS the entire file first, then writes its
     `## Prompt <N>` (or `## Phase <N.M>` / `## Module <N>`) section. The write is
     IDEMPOTENT by prompt id: if a `## Prompt <N>` section already exists (a
     re-run after a retry / context reset), REPLACE it in place; only APPEND when
     no section for that id exists. Never create a second section for the same id
     (duplicate entries were a live regression).
  6. Never edit a DIFFERENT prior step's section — treat other steps as an
     append-only log; only a step's own re-run may replace its own section.
  7. Live state files are gitignored. Only this template (inside the skill)
     is committed.

DOWNSTREAM:
  - Retrospective entries accumulate in `example/<use_case>/retrospective.md`
    using `skills/vibecoding-state/references/retrospective-template.md`.

SCHEMA VERSION:
  - This template corresponds to schema v2.0. `vibecoding-state.enter` will
    halt if it encounters a state file with `spec_provenance.schema_version`
    != "2.0". Run `scripts/migrate-spec-v1-to-v2.py` on older files.
-->

**Workshop:** <USE_CASE_SLUG>
**Started:** <ISO timestamp>
**Last updated:** <ISO timestamp>

---

## Environment Capabilities

<!--
Section 0. Written by `vibecoding-state.bootstrap` step 0 BEFORE anything else, and read by
`enter` / `exit` and every prompt. This is the RULE_0 (navigation preamble) / RULE_1 (deploy
verb) source of truth: the skill/prompt BODY stays one content set across clients — only the
navigation preamble and the CLI channel vary by `client_context`.

Detection (bootstrap step 0) — [inference, pending the live Genie Code probe]:
  - `runDatabricksCli` tool / Genie serverless markers present  ⇒  client_context: genie_code
      cli_channel: runDatabricksCli ; bundle_deploy.page_context_required: true
      state_file_root: <user project workspace path>
      artifact_root:  <user project workspace path>   # where artifacts build, e.g. /Workspace/Users/<email>/<repo>
      skills_install_root: <git-folder workspace path> # the clone, e.g. /Workspace/Users/<email>/.assistant/skills/<repo>
      skill_ref_root: skills/<clone-folder>          # readSkillFile prefix, = "skills/" + basename(skills_install_root), e.g. skills/vibe-coding-workshop
  - otherwise                                                    ⇒  client_context: ide_cli
      cli_channel: local_shell ; bundle_deploy.page_context_required: false
      state_file_root: <local repo path>
      artifact_root:  <local repo path>
      skills_install_root: <local repo path>         # same as artifact_root on ide_cli (no separate clone)
      skill_ref_root: ""                             # empty — repo-relative skill paths / @-mentions resolve as-is

`artifact_root` is where RELATIVE artifact paths in prompt bodies resolve (`<ARTIFACT_ROOT>/docs/design_prd.md`).
It defaults equal to `state_file_root` and is kept as a distinct field so an app/agent subdir can later diverge
without overloading `state_file_root`. On genie_code it is the USER PROJECT root
(`/Workspace/Users/<email>/<repo>`) — NOT the skills clone — so generated bundles/apps/docs never land inside the
read-only `.assistant/skills/` framework folder. Bare relative paths are unsafe on genie_code because its CWD is
page-type-dependent — see `skills/genie-code-environment` §8. `git clone` creates only the `skills_install_root`
clone, not `artifact_root`, so `resolve_root` / `bootstrap` step 0 create `artifact_root` (`mkdir -p` semantics) if
absent before the first write.
`skills_install_root` is the read-side anchor: the cloned-repo path under
`/Workspace/Users/<email>/.assistant/skills/<repo>` on genie_code (= `artifact_root` on ide_cli, where the repo IS
the project). It is decoupled from `artifact_root` so the workshop builds artifacts in the user project while
skills keep loading from the clone.
`skill_ref_root` is derived from it: the prefix that makes a repo-relative SKILL path loadable on genie_code via
`readSkillFile` (`<skill_ref_root>/data_product_accelerator/skills/.../SKILL.md`), = `"skills/" +
basename(skills_install_root)`. Empty on ide_cli (paths/@-mentions resolve from the workspace root). See
`skills/genie-code-environment` §8.
`dp_bundle_root` is the write-side anchor for the data-product pipeline: a SELF-CONTAINED Databricks Asset
Bundle project directory `<artifact_root>/{user_schema_prefix}_<use_case_slug>_dab` (e.g.
`…/vibe-coding-workshop/jane_d_booking_app_dab`) shared by every DP stage (bronze→silver→gold→semantic).
The `{user_schema_prefix}_` prefix is the SAME username-derived prefix used for the `{user_schema_prefix}_bronze`
/ `_silver` / `_gold` schemas (companion app supplies it on genie_code; on ide_cli it derives from the
authenticated user, e.g. `jane_d`); prefixing the folder disambiguates concurrent users in a shared
workspace. The bundle `name:` inside `databricks.yml` MUST match this folder name
(`bundle: { name: {user_schema_prefix}_<use_case_slug>_dab }`) for the same reason. Generated `databricks.yml` /
`src/` / `resources/` live UNDER it — never at the bare clone root (mixing generated artifacts into the framework
clone is the "one level too high" bug) and never inside a read-only framework dir (`data_product_accelerator/` etc.).
On genie_code it is also the **`bundle deploy` page-context root** (be on this folder's page to deploy). It is
derived once `use_case_slug` is known (bootstrap), so `resolve_root` (pre-bootstrap) does not produce it.
`app_root` is the write-side anchor for the AppKit application track (Pathways A/B/C) — the exact analog of
`dp_bundle_root`: a SELF-CONTAINED app project directory `<artifact_root>/<app_name>` (e.g.
`…/vibe-coding-workshop/jane-d-booking`), a TOP-LEVEL sibling of `{user_schema_prefix}_<use_case_slug>_dab` — NOT nested under
`apps_lakebase/` and NOT the bare clone root. The scaffolded app (`app.yaml`, `databricks.yml`, `server/`,
`client/`, and `<app_root>/.vibecoding-state.md`) lives UNDER it on BOTH clients, so the app's root folder has
parity regardless of coding agent. On genie_code it is the `apps init --output-dir` target. It is derived once
`APP_NAME` is known (Module 1 / prompt 04); `<pending>` until then. The app deploys via `apps deploy` (RULE_9
exception), not `bundle deploy`, so there is no `bundle`-style page-context pin.
`agent_app_root` is the write-side anchor for the Track A custom-agent application (Pathways C/D) — the exact
analog of `app_root`: a SELF-CONTAINED agent project directory `<artifact_root>/<agent_app_name>` (e.g.
`…/vibe-coding-workshop/booking-support-agent`), a TOP-LEVEL sibling of `<app_name>` and `{user_schema_prefix}_<use_case_slug>_dab`
— NOT nested under `apps_lakebase/` and NOT the bare clone root. The cloned agent framework (`app.yaml`,
`pyproject.toml`, `databricks.yml`, `server/`, and `<agent_app_root>/.vibecoding-state.md`) lives UNDER it on
BOTH clients, so the agent app's root folder has parity regardless of coding agent. On genie_code it is the
`apps init --output-dir` target and the `uv`-based FastAPI server builds server-side via `apps deploy`
(`mode=SNAPSHOT`) — there is no local `uv run dev` loop. It is derived once `AGENT_APP_NAME` is known (Track A
clone / prompt 43); `<pending>` until then. Like `app_root`, the agent app deploys via `bundle deploy` (for the
agent's bundle resources) plus `apps deploy` (for the host), not a bare-shell `databricks` call. `n/a` for
Pathways A/B (no agent app).
Client-invariant fields (same for both clients):
  bundle_deploy.verb = "bundle deploy --target dev"   (never a bare-shell `databricks` call)
  app_deploy         = { verb: "apps deploy", gated: true }   (RULE_9 exception)
  destructive_ops    = confirm_required
-->

```yaml
environment_capabilities:
  client_context: <ide_cli | genie_code>        # detected at bootstrap step 0
  cli_channel: <local_shell | runDatabricksCli>
  bundle_deploy: { verb: "bundle deploy --target dev", page_context_required: <true | false> }
  app_deploy:    { verb: "apps deploy", gated: true }
  destructive_ops: confirm_required
  state_file_root: <local repo path | user project workspace path>
  artifact_root: <local repo path | user project workspace path>   # relative artifact paths resolve here (<ARTIFACT_ROOT>/<relpath>); defaults to state_file_root; on genie_code the USER PROJECT root (e.g. /Workspace/Users/<email>/<repo>), NOT the skills clone
  skills_install_root: <local repo path | git-folder workspace path>   # the cloned repo (read-side). On genie_code /Workspace/Users/<email>/.assistant/skills/<repo>; on ide_cli same as artifact_root. Decoupled from artifact_root so artifacts build in the user project while skills load from the clone.
  skill_ref_root: <"" | "skills/<clone-folder>">   # readSkillFile prefix for repo-relative SKILL paths on genie_code (= "skills/" + basename(skills_install_root)); empty on ide_cli
  dp_bundle_root: <artifact_root>/{user_schema_prefix}_<use_case_slug>_dab   # self-contained DAB project dir for the data-product pipeline; username-prefixed (same {user_schema_prefix}_ as the _bronze/_silver/_gold schemas) so concurrent users never collide. The bundle name: in databricks.yml MUST match this folder name. Generated databricks.yml/src/resources live here, and on genie_code it is the `bundle deploy` page-context root. Derived at bootstrap (needs use_case_slug + user_schema_prefix); <pending> until then.
  app_root: <artifact_root>/<app_name>   # self-contained AppKit app project dir (Pathways A/B/C); top-level sibling of dp_bundle_root, NOT under apps_lakebase/ and NOT the bare clone root. app.yaml/databricks.yml/server/client and app_root/.vibecoding-state.md live here on BOTH clients (root-folder parity). On genie_code it is the `apps init --output-dir` target. Derived once APP_NAME is known (Module 1 / prompt 04); <pending> until then. n/a for Pathway D (agent-only).
  agent_app_root: <artifact_root>/<agent_app_name>   # self-contained Track A custom-agent project dir (Pathways C/D); top-level sibling of app_root and dp_bundle_root, NOT under apps_lakebase/ and NOT the bare clone root. app.yaml/pyproject.toml/databricks.yml/server and agent_app_root/.vibecoding-state.md live here on BOTH clients (root-folder parity). On genie_code it is the `apps init --output-dir` target and builds the uv/FastAPI server server-side via `apps deploy` (mode=SNAPSHOT) — no local `uv run dev`. Derived once AGENT_APP_NAME is known (Track A clone / prompt 43); <pending> until then. n/a for Pathways A/B.
  genie_code_manifest_loaded: <n/a | false | true>   # G3 — seeded by bootstrap step 0: `n/a` on ide_cli (check is inert), `false` on genie_code. On genie_code the owning skill `skills/genie-code-environment` MUST flip this to `true` once it is read in the current thread; the first deploy/divergent prompt's `enter` halts while it is `false`/`<pending>`.
  # detected_via: <runDatabricksCli | genie_serverless_marker | no_managed_cli_channel>
```

---

## Workshop Choices

<!-- Fill these in before starting Module 0. They do not change mid-workshop. -->

- **use_case_slug:** `<short-hyphen-lowercase-slug, max 26 chars>`
- **prd_path:** `<path/to/design_prd.md, e.g. example/<use_case>/docs/design_prd.md>`
- **pathway:** `<A | B | C | D>`
  - A = App Only (Analytics)
  - B = App + Lakebase
  - C = App + Integrated Agent  (requires track)
  - D = Agent Only                (requires track)
- **track:** `<A | B | C | n/a>`  <!-- n/a for pathways A and B -->
  - Track A = Custom Agent on Databricks Apps
  - Track B = Supervisor API
  - Track C = Model Serving (standalone endpoint)
- **dabs_bundle_path:** `<path, e.g. example/<use_case>/ | n/a>`
- **llm_endpoint:** `<e.g. databricks-claude-sonnet-4-6>`
- **enable_lakebase_cdf:** `<true | false>`  <!-- default false; Pathways B/C only. Gates the `sync_from_lakebase` genie-code fork (input_id 931): false = one-time CLONE of the Lakebase tables into the lakehouse user-scoped schema; true = attempt Lakebase Change Data Feed, with automatic announced fallback to clone when the workspace cannot host CDF (default-storage catalog / preview off). Surfaced to prompts as the `{enable_lakebase_cdf}` placeholder. -->

---

## Pathway Applicability Matrix

<!--
This matrix tells each prompt whether its module applies for the chosen pathway.
For any step that does NOT apply, the agent writes `N/A — pathway <X>` instead
of `<pending>` in the per-step log, and in any resource ID it would have populated.
-->

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

- **APP_NAME:** `<pending>`  <!-- Pathways A/B/C; for D this is `n/a` -->
- **AGENT_NAME:** `<pending>` <!-- Pathways C/D; for A/B this is `n/a` -->
- **PROFILE:** `<pending>`  <!-- AUTHORITATIVE key — Databricks CLI profile, e.g. fevm-jane-doe-pat. Do not also use `workspace_profile`. -->
- **Workspace URL:** `<pending>`
- **Workspace host:** `<pending>`
- **User email:** `<pending>`
- **workspace_serverless_only:** `<pending | true | false>`  <!-- Set by Prompt 1 preflight from `databricks compute-policies list`. Drives whether bundle uses `environments:` vs `job_clusters:` -->
- **UC catalog:** `<pending>`         <!-- e.g. main or <workspace>_catalog -->
- **UC schema (app):** `<pending>`    <!-- e.g. bookings -->
- **UC schema (agent):** `<pending>`  <!-- e.g. bookings_agent -->
- **UC schema (ops):** `<pending>`    <!-- e.g. bookings_ops -->

---

## Captured Resource IDs

<!--
Agents replace `<pending>` with resolved values as resources are created.
Use `<n/a>` for any resource that does not apply to the chosen pathway/track.
Lists are used when the PRD defines multiple of something (Genie Spaces,
Vector Search indexes, Knowledge Assistants, custom tools).
-->

- **warehouse_id:** `<pending>`
- **warehouse_name:** `<pending>`                <!-- Human-readable name, e.g. "Serverless Starter Warehouse" -->
- **llm_endpoint_ready:** `<pending | ready | not_ready>`
- **bundle_job_id:** `<pending | n/a>`           <!-- setup_infra job ID from `databricks bundle deploy` -->
- **last_successful_run_id:** `<pending | n/a>`  <!-- Last green `databricks bundle run setup_infra` run_id -->
- **last_verify_summary:** `<pending | n/a>`     <!-- JSON payload from 05_verify_infrastructure.py notebook.exit (catalog, schema, warehouse_id, vector_search_*, genie_space_id, pass/warn/fail) -->
- **terraform_exec_path:** `<pending | n/a>`     <!-- $(which terraform) if the Terraform-key workaround was applied -->
- **terraform_version:** `<pending | n/a>`       <!-- e.g. 1.14.8 -->
- **app_url:** `<pending | n/a>`
- **serving_endpoint_name:** `<pending | n/a>`   <!-- n/a for A and B -->
- **ai_gateway_endpoint:** `<pending | n/a>`     <!-- n/a for A and B -->
- **mlflow_experiment_path:** `<pending | n/a>`  <!-- n/a for A and B. Derivation rule (Pathways C and D): `/Users/<user_email>/mlflow/<APP_NAME or AGENT_NAME>-agent` (e.g. `/Users/jane.doe@example.com/mlflow/jane-d-stayfinder-agent`). NEVER set this to a generic suffix like `Tracing`, `traces`, or `my-agent`; the leaf MUST carry the same `${FIRSTNAME}-${LASTINITIAL}-${use_case_slug}` identity that backs `APP_NAME` / `AGENT_NAME` so attendees on a shared workspace never collide. F2 (`02-experiment-tracing-and-uc-storage`) consumes this; do not let it construct its own. -->
- **mlflow_feedback_experiment_path:** `<pending | n/a>` <!-- n/a for A, B, D. Derivation rule (Pathway C only): `/Users/<user_email>/mlflow/<APP_NAME>-feedback`. Mirrors `mlflow_experiment_path` so the AppKit feedback skill (`08-appkit-feedback`) never falls back to generic placeholders like `/Shared/my-app-feedback`. -->
- **lakebase_project:** `<pending | n/a>`        <!-- n/a for A and D -->
- **lakebase_host:** `<pending | n/a>`           <!-- n/a for A and D -->
- **doc_qa_backend:** `<pending | n/a>`          <!-- "knowledge_assistant" | "vector_search" ; n/a for A, B -->
- **signoff_decision:** `<pending | n/a>`        <!-- "APPROVED" | "REJECTED" ; n/a for A, B -->
- **prompt_iteration_ran:** `false`
- **capstone_done:** `false`

### Genie Spaces (0..N)

<!-- One bullet per Genie Space in the PRD. Mark unused entire section `n/a` if none. -->
- `<name>` — id: `<pending>` — title: `<pending>` — purpose: `<short purpose>`

### Vector Search Indexes (0..N)

<!-- `endpoint` is the VS endpoint name; `index` is the 3-part UC name `<catalog>.<schema>.<index>` -->
- `<name>` — endpoint: `<pending>` — index: `<catalog>.<schema>.<index_name>` — purpose: `<short purpose>`

### Knowledge Assistants (0..N)

- `<name>` — kb_endpoint_name: `<pending>` — source: `<UC Volume path>` — purpose: `<short purpose>`

### Custom `@function_tool` Tools (0..N)

- `<tool_name>` — writes_to: `<table or volume, or "read-only">` — purpose: `<short purpose>`

### External MCP Connections (0..N)

- `<service>` — connection: `<name>` — auth: `<OAuth / SP / OBO>` — purpose: `<short purpose>`

---

## State Contract Audit

```yaml
last_run_at: <pending>
mode: fail
fields_read_but_never_produced: []
fields_produced_but_not_in_schema: []
schema_fields_missing_from_template: []
captured_fields_with_no_consumer: []
productized_debts_status:
  total: 0
  lifted: 0
  parse_errors: 0
```

---

## LLM Role Endpoints

<!--
Default candidates encode the "GPT first for non-chat roles, Llama fallback only"
operator decision. `agent_chat` keeps Claude as the single candidate because the
in-app chat surface is already wired to it. `endpoint`, `selected_after_probe`,
and `rationale` are populated by `vibecoding-state.llm_role_endpoint_probe`
during bootstrap — do NOT set `endpoint` by hand before probing.
-->

```yaml
llm_role_endpoints:
  agent_chat:
    candidates: ["databricks-claude-sonnet-4-6"]
    endpoint: <pending>
    streaming_required: false
    selected_after_probe: false
    rationale: <pending>
  agent_chat_streaming_smoke:
    candidates: ["databricks-gpt-5-2", "databricks-gpt-5-mini", "databricks-meta-llama-3-3-70b-instruct"]
    endpoint: <pending>
    streaming_required: true
    selected_after_probe: false
    rationale: <pending>
  reflection_lm:
    candidates: ["databricks-gpt-5-2", "databricks-gpt-5-mini", "databricks-meta-llama-3-3-70b-instruct"]
    endpoint: <pending>
    min_context_chars: 80000
    selected_after_probe: false
    rationale: <pending>
  llm_judge_default:
    candidates: ["databricks-gpt-5-mini", "databricks-gpt-5-2", "databricks-meta-llama-3-3-70b-instruct"]
    endpoint: <pending>
    selected_after_probe: false
    rationale: <pending>
  failure_categorizer:
    candidates: ["databricks-gpt-5-mini", "databricks-gpt-5-2", "databricks-meta-llama-3-3-70b-instruct"]
    endpoint: <pending>
    selected_after_probe: false
    rationale: <pending>
```

---

## Endpoint Guardrail Audit

<!--
Populated by `vibecoding-state.endpoint_guardrail_audit`, which shells out to
`skills/vibecoding-state/scripts/probe_endpoints.py`. One entry per
endpoint considered (every candidate across every role, deduplicated). See
`spec-schema.md` § *Endpoint Guardrail Audit* for the field definitions.
-->

```yaml
endpoint_guardrail_audit: {}
```

---

## Bootstrap Preflight

<!--
Populated by `vibecoding-state.bootstrap` BEFORE the spec sections are written.
Captures the operator's environment (workspace URL normalization, CLI version,
apps quota, DAB dev-mode prefix detection, first state file path, verify-job
PASS/WARN/FAIL semantics) so downstream prompts and `state_contract_audit`
have a single source of truth. See `spec-schema.md` § *Bootstrap Preflight*
for field definitions and the hard-halt rules.

Defaults below match a fresh bootstrap run that has not yet been populated.
`databricks_cli_min_version` is set to `0.295.0` — bump together with
`spec-schema.md` and the SQL-seed comment when the workshop raises its floor.
-->

```yaml
bootstrap_preflight:
  workspace_url_normalized: <pending>
  workspace_url_was_placeholder: <pending>
  workspace_profile: <pending>
  workspace_host_auth_status: <pending>          # authenticated | unauthenticated | wrong_host
  databricks_cli_version: <pending>             # ide_cli: `databricks --version`; genie_code: "unknown_on_genie_code" (--version hard-blocked, Gap-1 → version gate skipped, bundle-validate probe instead)
  databricks_cli_min_version: "0.295.0"
  apps_quota:
    current_count: <pending>
    max_count: <pending>
    free_slots: <pending>
  bundle_dev_mode_schema_prefix_detected: false
  first_state_file_path: <pending>
  app_name_known_at_bootstrap: false
  verify_summary_semantics:
    pass_field: "pass"
    warn_field: "warn"
    fail_field: "fail"
    warning_policy: "allow_with_notes"           # allow_with_notes | block_if_load_bearing
```

---

## State File Set

<!--
Declared when a prompt must read BOTH an AppKit state file
(<app_root>/.vibecoding-state.md, the top-level app dir) and an agent state file
(<agent_app_root>/.vibecoding-state.md, the top-level agent app dir) in the same
step. Pathways A, B, and pure-D runs leave `secondary` at <pending> / null and never trip the
multi-file path. `enter` consults `lookup_order` for non-conflicting reads and
applies `conflict_policy` when the same canonical field appears in both files
with different values. See `spec-schema.md` § *State File Set* for the
normative rules.
-->

```yaml
state_file_set:
  primary:
    path: <pending>
    owner: <pending>                             # appkit | agent | root | example
  secondary:
    path: <pending>
    owner: <pending>                             # appkit | agent | root | example
    required_for_prompts: []
  lookup_order: ["primary"]
  # Default is fail_on_conflict — Pathway-C prompts that intentionally tolerate
  # divergence between AppKit and agent state must opt in to primary_wins
  # explicitly per prompt or per session via state_overrides[].
  conflict_policy: fail_on_conflict               # primary_wins | fail_on_conflict
```

---

## Canonical Names

<!--
Pinned spellings for every cross-cutting name the workshop touches: legacy
state-field aliases, env vars, jq paths into Databricks CLI output, HTTP
headers exposed to Databricks Apps, MLflow Prompt Registry URI scheme + schema
field, evaluation-dataset column names, label-schema namespace prefix, and
file paths. Values below are the canonical mappings — they are NOT
`<pending>`. `state_contract_audit` extends its drift checks to flag any
prompt that uses a legacy spelling instead of the canonical one, and any
prompt that reads a header marked `null` (e.g. `x-forwarded-user-info`, which
does not exist on Databricks Apps).

Direction of each map: `<legacy_or_incorrect_name>: <canonical_name>`. Never
invert. A `null` value means the name does not exist; reject any read on it.
-->

```yaml
canonical_names:
  state_fields: {}
  env_vars:
    # legacy/incorrect name : canonical name
    MLFLOW_EXPERIMENT_NAME: MLFLOW_EXPERIMENT_ID
    WAREHOUSE_ID: MLFLOW_TRACING_SQL_WAREHOUSE_ID
  jq_paths:
    apps_status_state: .app_status.state
  http_headers:
    # null = header does not exist on Databricks Apps; reject any prompt that reads it.
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
  label_schema_namespace_prefix: <pending>       # e.g. "<use_case_slug>_v<n>__"
  file_paths: {}
```

---

## State Overrides

<!--
The ONLY mechanism by which `enter` may proceed past a failed gate, a
prior-gate mismatch, a failed `hard_assert`, a failed `preflight_check`, or a
non-applicable pathway. Cross-session continuity is recorded here as an
override (with an evidence link to the earlier run), NOT as prose narration in
a Per-Step Log entry. Each entry MUST have a bounded `expires_at`; expired
entries are inert and `enter` halts on the underlying gate. See
`spec-schema.md` § *State Overrides* for the normative rules.

Default is an empty list — operators add entries deliberately.
-->

```yaml
state_overrides: []
```

---

## Deferred Actions

<!--
Canonical baseline of cross-prompt dependencies the workshop knows about up
front. Each entry blocks every prompt role listed in `target_prompt_roles[]` from passing its gate until
`divergence_check` evaluates true (or a `state_override` entry covers it).
The six seeds below are the workshop's hard-coded baseline — they MUST always
be present at bootstrap time. Workshops MAY append additional deferred
actions; they MUST NOT remove the seeds. See `spec-schema.md` § *Deferred
Actions* for the normative rules.
-->

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

<!--
Populated as eval issues surface (tool warnings, jq paths returning null,
scorer floors not met, synthesized stand-ins). Each open entry blocks every
prompt role listed in `target_prompt_roles_blocked[]`. Defaults to an empty
list at bootstrap; entries are appended at runtime. See `spec-schema.md`
§ *MLflow Eval Known Quality Issues* for the normative rules.
-->

```yaml
mlflow_eval_known_quality_issues: []
```

---

## Gate Load Bearing Checks

<!--
Canonical list of verify-job and audit warning names that, when present, MUST
block the gate rather than soft-pass. Backs
`bootstrap_preflight.verify_summary_semantics.warning_policy:
block_if_load_bearing`. Workshops MAY append additional check names but MUST
NOT remove entries. See `spec-schema.md` § *Gate Load Bearing Checks* for the
normative rules.
-->

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

<!--
Workarounds the workshop deliberately ships with. Each entry carries a
`remove_when` predicate (same divergence-check grammar as
`deferred_actions[]`, extended with AND/OR and the `[]` empty-array
literal — see `spec-schema.md` § *Divergence-check grammar*) that
`audit_debts` evaluates against the live state file. When the predicate
flips true, `audit_debts` sets `debt_lifted: true` and the next
implementation pass MUST remove the workaround.

"Accepted permanent debt" means no admin-ticket dependency exists; it does
NOT mean the debt lacks a `remove_when`. Workshops MAY append additional
debts; they MUST NOT remove the five seeds below. See `spec-schema.md`
§ *Productized Debts* for the normative rules.

`audit_history` starts empty; entries are appended on every `audit_debts`
run.
-->

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

<!--
Canonical map of every named preflight check the workshop knows about. Each
entry maps a check name to its `owner` (the skill or prompt that owns the
check) and `blocks_prompt_roles[]` (the prompt roles whose `enter` MUST halt
while the check has not been recorded as passing). Bootstrap pre-populates
the canonical seeds below; workshops MAY append additional checks but MUST NOT
remove the seeds. See `spec-schema.md` § *Preflight Check Registry* for the
state-field mapping table, the synchronous reflection-LM probe rule, the
client-conditional `genie_code_manifest_loaded` rule, and the normative
`enter` / `state_contract_audit` consumption rules.
-->

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
  genie_code_manifest_loaded:                    # G3 — client-conditional (inert on ide_cli)
    owner: skills/genie-code-environment
    blocks_prompt_roles: [deploy_app, appkit_agent_proxy]
```

---

## Evaluation Runs Preflight

<!--
Canonical state block consumed by
`preflight_check_registry.predict_fn_signature_matches_runner`. Owned by SDLC
Skill 04 (`genai-agents/sdlc/04-evaluation-runs/SKILL.md`). The boolean flips
`true` the first time a Skill 04 run completes whose captured
`mlflow_eval_predict_fn_signature` matches the runner-expected
`(inputs: dict) -> str` or `(inputs: dict) -> dict` shape; a non-matching
signature flips it back to `false`. `last_run_at` is carried for audit
traceability. See `spec-schema.md` § *Evaluation Runs Preflight*.
-->

```yaml
evaluation_runs_preflight:
  predict_fn_signature_matches_runner: false
  last_run_at: <pending>
```

---

## System Prompt Review

<!--
Records the structured pre-eval audit of the agent's hand-authored system
prompt. Defaults: `complete: false`, `reviewed_at: <pending>`,
`reviewed_by: <pending>`, both example arrays empty `[]`. The arrays are
populated by the prompt that runs the system-prompt review (the prompt that
maps to `first_scored_eval` — Prompt 7.20 in `Instructions.md`, Prompt 20d in
`example/skyloyalty/WALKTHROUGH.md`, section `mlflow_agent_quality_judges` in
`docs/02_seed_section_input_prompts.sql`).

`enter` enforces the following preflight checks at the first scored eval:

  - system_prompt_review.complete == true
  - count(system_prompt_review.must_do_worked_examples) >= count(agent.must_do)
  - count(system_prompt_review.must_not_do_worked_examples) >= count(agent.must_not_do)

The field paths `agent.must_do` and `agent.must_not_do` are the canonical names
from `spec-schema.md` § *Agent* — DO NOT introduce a parallel
`agent.system_prompt.must_do_rules` shape. See `spec-schema.md` § *System Prompt
Review* for the normative rules and the `count()` divergence-check grammar
extension.
-->

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

<!--
Records the concrete shape selected by `vibecoding-state.skill_helper_resolution`
for every skill-prescribed helper contract the workshop has probed. Defaults
to an empty list at bootstrap; entries are appended (or replaced by
`contract_name`) every time `skill_helper_resolution` runs.

This is the structural fix for retrospective recurring-issue #11 ("skill
helper vs concrete shape") — 12+ instances across SkyLoyalty Prompts
9/13/14/15/16/17/18/20a/20c/20d/20e/20g v1 where the skill prescribes a
canonical surface (import path, function signature, bundle field, JSON
path) that the workspace does not ship in that exact shape. Lifting
resolution into a single operation lets every consuming skill emit
`(contract_name, candidates[], min_cli_version, inline_template_fallback)`
and inherit the same first-callable-wins probe + capture contract.

Each entry pins one resolution per `contract_name`; re-running
`skill_helper_resolution` replaces the prior entry (the most recent
`probed_at` always wins). Consuming skills cite resolved helpers via
`skill_helper_resolutions[contract_name='<name>'].selected_value` in their
`fields_read:` frontmatter — `state_contract_audit` flags any bare
`obo_helper`/`predict_fn_signature` read that does not use the registry
indexing path.

See `spec-schema.md` § *Skill Helper Resolutions* for the candidate-kind
table (the seven `selected_kind` enum values) and the consumer contract.
-->

```yaml
skill_helper_resolutions: []
```

---

<!-- HISTORY -->

## Per-Step Log

<!--
Every completed prompt writes a section below using this template. The write is
idempotent by prompt id: if a `## Prompt <id>` section already exists (re-run
after a retry/reset), REPLACE it in place; only APPEND when none exists. Never
log the same prompt id twice.

For prompts that do NOT apply to the chosen pathway, the agent still writes a
section with Outcome = `Skipped (N/A for pathway <X>)` so the log is complete
and retrospectives can reason about applicability.

Canonical section template:

## Prompt <N> (or Module <N> / Phase <N.M>) — <short title>

**Step name:** <e.g. Scaffold, Build & Test>
**Module:** <0 | 1 | 2 | 3.1 | 3.2 | 3.3 | 4 | 5-A1 | 5-A2 | 5-B0 | 5-C1 | 6.1 | 6.2 | 7-20a | ...>
**Completed:** <ISO timestamp>
**Pathway applicability:** <applies | skipped — pathway <X>>
**Track applicability:** <applies | n/a | skipped — track <Y>>
**Skills invoked:**
- <skill path 1>
- <skill path 2>

**Variables set this step:**
- `<key>`: `<value>`

**Resolved issues / workarounds:**
- <what broke and how it was fixed; "none" if clean>

**Verification:**
- [x] <objective check that passed>
- [x] <...>

**Gate:** <Local testing passed | Deployment RUNNING | Eval thresholds met | Signoff APPROVED | Skipped — N/A | etc.>

HARD RULE: do not declare a build/modify prompt complete until the Gate reads
`Local testing passed`. Skipped steps have Gate = `Skipped — N/A for pathway <X>`.
-->

---

<!--
## Spec Sections — added by `vibecoding-state.resolve_spec` (schema v2.0)

`resolve_spec` runs ONCE at bootstrap and appends these six sections verbatim
from the LLM output (after validation). Do NOT fill them in by hand.

  ## Variant
    variant_id: "<one of: v1-sup-appkit | v2-serving-appkit | v3-agentapp-only |
                         v4-agentapp-plus-appkit | v5-integrated-appkit>"

  ## Resources
    resources:
      tables:          [...]   # unified warehouse + lakebase with kind discriminator
      knowledge_bases: [...]
      genie_spaces:    [...]
      vector_indexes:  [...]
      dabs_bundle:     {...}
      sample_data:     {...}

  ## UI
    ui:
      description:       "..."
      personas:          [...]
      pages:             [...]
      overview_widgets:  [...]
      sql_files:         [...]
      user_journeys:     [...]

  ## Agent
    agent:
      system_prompt:         "..."
      tone_persona:          "..."
      must_do:               [...]
      must_not_do:           [...]
      model:                 "..."   # e.g. databricks-claude-sonnet-4-5
      auth_mode:             "..."   # app | user | hybrid
      capabilities:          [...]
      reviewer_role:         "..."
      memory:                {provider: ..., table_prefix: ...}
      tools:                 [...]   # discriminated union: kind=hosted|function|mcp
      mcp_servers:           [...]
      knowledge_base_backend:{...}
      external_integrations: {...}
      benchmark_seeds:       {...}

  ## Governance
    governance:
      scorer_suite:  {...}
      monitoring:    {...}
      verification:  {...}

  ## Spec Provenance
    spec_provenance:
      resolved_at:      "..."
      resolver_version: "2.0"
      schema_version:   "2.0"
      prd_sha256:       "..."
      llm_endpoint:     "..."

See `skills/vibecoding-state/references/spec-schema.md` for the full
field list and validation rules.
-->

## Hydrated example (Agents Accelerator visible path)

When a workshop runs the Agents Accelerator visible path, prompt 40
(`uc_resources_foundation`) calls `vibecoding-state.hydrate_from_files` to
populate `## Agent`, `## UI`, `## Resources` (as `optional: true` when no
Lakehouse track ran), and `## Spec Provenance` from the four design files
(`docs/agent_spec.yaml`, `docs/agent_tool_plan.yaml`, `docs/ui_design.md`,
`docs/design_prd.md`). The hydrated `## Spec Provenance` block looks like:

```yaml
## Spec Provenance
spec_provenance:
  resolved_at: "2026-04-29T20:00:00Z"
  resolver_version: "3.0"      # set by hydrate_from_files
  schema_version: "2.0"
  prd_sha256: "<computed>"
  llm_endpoint: "n/a"          # hydration does not call an LLM
  hydrated_from_files: true
```

When the Lakehouse track has not run, `## Resources` is the optional stub:

```yaml
## Resources
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

Downstream prompts (KA branch C in prompt 42, tool wiring in prompt 44, MLflow
SDLC in prompts 50–56) treat `optional: true` as "fall back to `docs/*` files;
skip Lakehouse-specific tools".

See [`hydrator-prompt.md`](./hydrator-prompt.md) for the LLM driver prompt that
produces this hydrated state and the post-hydration guards that enforce
`resolver_version: "3.0"` provenance.
