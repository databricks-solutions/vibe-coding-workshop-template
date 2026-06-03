---
name: vibecoding-state
description: >
  Owns the end-to-end state, gating, pathway-applicability, and retrospective
  contract for the `Instructions.md` / `example/<use_case>/WALKTHROUGH.md`
  vibecoding workshops. Every workshop prompt invokes this skill at the top
  (`enter`) and bottom (`exit`) so the state file is read, gates are enforced,
  non-applicable steps are skipped, and the per-step log is appended — without
  each prompt repeating the contract as prose. Also owns the `bootstrap`
  initializer, the bootstrap → canonical `migrate_canonical` move, and the
  async `retrospective.per_prompt` / `retrospective.rollup` passes. Invoke
  BEFORE acting on any workshop prompt.
license: Apache-2.0
compatibility: "Works with any workshop that follows the vibecoding state schema in references/state-template.md. Pathways A, B, C write the AppKit state to <app_root>/.vibecoding-state.md (= <artifact_root>/<app_name>/.vibecoding-state.md, the top-level app dir); the Track A custom-agent app (Pathways C/D) writes to <agent_app_root>/.vibecoding-state.md (= <artifact_root>/<agent_app_name>/.vibecoding-state.md, the top-level agent app dir)."
clients: [ide_cli, genie_code]
bundle_resource: none
deploy_verb: none
deploy_note: "Runtime state/gating/retrospective contract — not a deployable skill; no bundle resource and no deploy verb. It is the resolver: at `enter` (and, pre-bootstrap, via the lightweight `resolve_root` op) it resolves the active client and writes the `client_context` capability set (`cli_channel`, `bundle_deploy.verb`, `page_context_required`, `state_file_root`, `artifact_root`, `skill_ref_root`, `dp_bundle_root`) that every downstream prompt and skill consumes, so it is client-agnostic by construction. On Genie Code the state file and artifacts live under the cloned repo root (`state_file_root` = `artifact_root` = `{REPO_ROOT}`); relative artifact paths resolve as `<ARTIFACT_ROOT>/<relpath>`, repo-relative skill paths load via `readSkillFile` under `skill_ref_root` (= `skills/<clone-folder>`), the data-product bundle is authored under `dp_bundle_root` (= `<artifact_root>/{user_schema_prefix}_<use_case_slug>_dab`, the `bundle deploy` page-context root), and the AppKit app is authored under `app_root` (= `<artifact_root>/<app_name>`, the top-level app dir — same shape on both clients). See `skills/genie-code-environment` §8 for the resolved per-client deploy verbs, the artifact_root rule, the skill-load rule, and the dp_bundle_root rule."
coverage: full
metadata:
  last_verified: "2026-04-15"
  volatility: low
  upstream_sources: []
  author: "prashanth-subrahmanyam"
  version: "2.0.0"
  domain: "genai-agents"
  role: "runtime-contract"
  operations: "bootstrap, resolve_root, resolve_spec, enter, migrate_canonical, exit, retrospective.per_prompt, retrospective.rollup, state_contract_audit, endpoint_guardrail_audit, llm_role_endpoint_probe, audit_debts, skill_helper_resolution"
  produces: "live_state_file, bootstrap_preflight, state_file_set, canonical_names, state_overrides, deferred_actions, mlflow_eval_known_quality_issues, gate_load_bearing_checks, productized_debts, preflight_check_registry, evaluation_runs_preflight, system_prompt_review, skill_helper_resolutions, resolved_variant, resolved_resources, resolved_ui, resolved_agent, resolved_governance, per_step_log_section, retrospective_entry"
  consumes: "Workshop Choices (PRD), PRD document at prd_path, Pathway Applicability Matrix, prior prompt gate"
  references:
    - "references/state-template.md"
    - "references/retrospective-template.md"
    - "references/spec-schema.md"
    - "references/resolver-prompt.md"
---

# Vibecoding State — Workshop Runtime Contract

This skill is the single source of truth for how every prompt in the repo-root [`Instructions.md`](../../Instructions.md) workshop and its worked instantiations (e.g. [`example/skyloyalty/WALKTHROUGH.md`](../../example/skyloyalty/WALKTHROUGH.md)) interacts with the shared per-user **state file** and the async per-prompt **retrospective file**.

Prompts do **not** re-state the "Vibecoding state contract / Preamble / Postamble / Pathway Applicability guard / Retrospective contract" prose. They invoke this skill with typed parameters and this skill owns the behavior.

---

## When to Use

Invoke this skill — always — when executing any vibecoding workshop prompt. Specifically:

- **Every** prompt in [`Instructions.md`](../../Instructions.md) (Prompt 0.1 through 8.24).
- **Every** prompt in `example/<use_case>/WALKTHROUGH.md` (e.g. SkyLoyalty's 22 prompts).
- **Every** post-workshop per-prompt retro + the single session rollup.

Do not invoke for: one-off terminal commands, ad-hoc debugging, or anything outside the workshop flow.

Candidate future skills that this skill deliberately does **not** absorb (they stay inline in prompts for now): `workspace-preflight` (`databricks compute-policies list`, `databricks current-user me`), `llm-endpoint-health` (`databricks serving-endpoints get <endpoint>`), `bundle-deploy` (`databricks bundle validate/deploy/run`), `derive-app-name` (email + use_case_slug → APP_NAME), `prd-reader`. If you end up duplicating any of those across prompts, extract them next.

---

## Operations

All thirteen operations take a typed parameter bag. The prompt invokes the operation by name (e.g. `vibecoding-state.enter`) and passes only the dynamic values. Everything else (file paths, log schema, gate rules, pathway matrix, resolved spec) is owned by this skill.

### Operation: `bootstrap`

**When:** Once per workshop run, at Prompt 0.1 (`Instructions.md`) or Prompt 1 (`WALKTHROUGH.md`). Only runs if no live state file exists.

**Inputs:**

| Param | Type | Required | Description |
|---|---|---|---|
| `use_case_slug` | string | required | Short hyphenated lowercase slug, ≤ 26 chars. Drives the bootstrap path. |
| `workspace_url` | string | required | The only value the operator provides by hand. Every subsequent prompt reads it from state. |
| `pathway` | `A` \| `B` \| `C` \| `D` | required | |
| `track` | `A` \| `B` \| `C` \| `n/a` | required | `n/a` for pathways A, B. |
| `prd_path` | string | required | e.g. `example/<use_case_slug>/docs/design_prd.md`. |
| `llm_endpoint` | string | required | e.g. `databricks-claude-sonnet-4-6`. |
| `dabs_bundle_path` | string \| `n/a` | required | |

**Behavior:**

0. **Detect environment & write the `## Environment Capabilities` block (RULE_0 / RULE_1 enabling).** Before any other step, resolve the active coding client and write the capability block (schema in [`references/state-template.md`](references/state-template.md) § *Environment Capabilities*) as **section 0** of the state file. This is the block every prompt and the `enter` / `exit` operations read to resolve the deploy verb, CLI channel, and state-file root — so no skill or prompt body assumes a local IDE. Detection signal **[inference — pending the live Genie Code probe]**: if a Databricks-managed CLI channel is present in-session (the `runDatabricksCli` tool / Genie serverless markers), set `client_context: genie_code`, `cli_channel: runDatabricksCli`, `bundle_deploy.page_context_required: true`, and both `state_file_root` and `artifact_root` to the git-folder workspace (clone) path; otherwise set `client_context: ide_cli`, `cli_channel: local_shell`, `bundle_deploy.page_context_required: false`, and both `state_file_root` and `artifact_root` to the local repo path. (`artifact_root` defaults equal to `state_file_root`; it is where relative artifact paths resolve as `<ARTIFACT_ROOT>/<relpath>` — see `skills/genie-code-environment` §8.) **Also set `skill_ref_root`** — the prefix that makes a repo-relative *skill* path loadable: on `genie_code` it is the `readSkillFile` prefix `"skills/" + basename(artifact_root)` (e.g. `skills/vibe-coding-workshop`, because the clone lives under `.assistant/skills/<repo>` and any file there loads as `skills/{path-after-.assistant/skills/}`); on `ide_cli` it is empty (repo-relative skill paths / `@`-mentions resolve as-is). See `skills/genie-code-environment` §8 for how prompts use it. **Also set `dp_bundle_root`** = `<artifact_root>/{user_schema_prefix}_<use_case_slug>_dab` (the `use_case_slug` bootstrap param is available here; `{user_schema_prefix}` is the SAME username-derived prefix used for the `{user_schema_prefix}_bronze`/`_silver`/`_gold` schemas — companion app on `genie_code`, authenticated-user derivation on `ide_cli`, e.g. `prashanth_s`) — the self-contained Databricks Asset Bundle project directory the whole data-product pipeline (bronze→silver→gold→semantic) writes its `databricks.yml` / `src/` / `resources/` into, and the `bundle deploy` page-context root on `genie_code`. The username prefix disambiguates concurrent users in a shared workspace; the bundle `name:` inside `databricks.yml` MUST match this prefixed folder name (`bundle: { name: {user_schema_prefix}_<use_case_slug>_dab }`). It is the same shape on both clients (a dedicated subdir of the repo/clone root, NOT the bare root and NOT inside a read-only framework dir); see `skills/genie-code-environment` §8. **Also set `app_root`** = `<artifact_root>/<app_name>` — the AppKit application track's analog of `dp_bundle_root`: a TOP-LEVEL sibling of `<use_case_slug>_dab` (NOT nested under `apps_lakebase/`) that holds the scaffolded app (`app.yaml` / `databricks.yml` / `server/` / `client/` + `<app_root>/.vibecoding-state.md`) on BOTH clients, so the app's root folder has parity regardless of client. It is the `apps init --output-dir` target on `genie_code`, deploys via `apps deploy` (no `bundle` page-context pin), and is `<pending>` until `APP_NAME` is resolved (Module 1 / prompt 04); `n/a` for Pathway D. **Also set `agent_app_root`** = `<artifact_root>/<agent_app_name>` — the Track A custom-agent track's analog of `app_root`: a TOP-LEVEL sibling of `<app_name>` and `<use_case_slug>_dab` (NOT nested under `apps_lakebase/`) that holds the cloned agent framework (`app.yaml` / `pyproject.toml` / `databricks.yml` / `server/` + `<agent_app_root>/.vibecoding-state.md`) on BOTH clients, so the agent app's root folder has parity regardless of client. On `genie_code` it is the `apps init --output-dir` target and the `uv`/FastAPI server builds server-side via `apps deploy` (`mode=SNAPSHOT`) — there is no local `uv run dev` loop. It is `<pending>` until `AGENT_APP_NAME` is resolved (Track A clone / prompt 43); `n/a` for Pathways A/B. The remaining fields are client-invariant: `bundle_deploy.verb` is always `bundle deploy --target dev`, `app_deploy` is always `{ verb: "apps deploy", gated: true }`, and `destructive_ops` is always `confirm_required`. **Also seed `genie_code_manifest_loaded` (G3):** `n/a` on `ide_cli` (the check is inert there), `false` on `genie_code` — on Genie Code the first deploy/divergent prompt's `enter` halts until the `skills/genie-code-environment` manifest is read in-thread and flips it `true` (see `references/spec-schema.md` § *Genie Code manifest-load gate*). Record the detection signal that fired in a trailing `# detected_via:` comment so a later live probe can confirm or correct it. For *how* the detected `genie_code` client actually behaves — the `runDatabricksCli` allow-list tiers, the bundle-deploy CWD pin and FUSE create-then-validate gap, the App-scaffold output-dir rule, and the deployed-app OAuth session pattern — see the **`genie-code-environment`** skill (this skill *detects* the client; that skill *explains* it).
1. **Workspace URL normalization & placeholder refusal.** Trim any trailing slash from `workspace_url` and normalize the scheme to `https://`. Refuse any literal placeholder — `<your-workspace-url>`, the empty string, or `https://<...>` — by halting with a remediation hint pointing the operator at Workshop Choices. Record the normalized value in `bootstrap_preflight.workspace_url_normalized` and the placeholder check in `workspace_url_was_placeholder`.
2. **Profile selection & host match.** Run `databricks auth profiles` and select the profile whose host equals the normalized workspace host. Store it in `bootstrap_preflight.workspace_profile`. If no profile matches, set `workspace_host_auth_status: wrong_host` and halt; if the matching profile fails `databricks current-user me`, set `unauthenticated` and halt; on success set `authenticated`.
3. **CLI version preflight (client-branched — Gap-1).** **On `ide_cli`:** capture `databricks --version` into `bootstrap_preflight.databricks_cli_version`, compare against `bootstrap_preflight.databricks_cli_min_version` (default `0.295.0`, may be raised by workshop config), and halt with an upgrade hint if the installed version is older. **On `genie_code`:** `databricks --version` is **hard-blocked** (no local CLI binary — the managed `runDatabricksCli` channel does not expose a version string; CONFIRMED P1), so set `bootstrap_preflight.databricks_cli_version: unknown_on_genie_code` and **skip the numeric comparison and the version halt entirely**. Any later decision that would have keyed off the numeric version (the `databricks_cli_min_version` registry check, and `skill_helper_resolution`'s CLI-version gate) falls back to the **behavior probe** — `databricks bundle validate` accepting the field/deploy without stripping — instead of a version number. The managed channel always tracks a current CLI, so the only real risk a version gate guards against (a stale local install) cannot occur on Genie Code.
4. **Apps quota preflight.** Before any `databricks apps create` happens (Pathways A/B/C), run `databricks apps list --output json` and record `current_count`, `max_count`, and `free_slots` in `bootstrap_preflight.apps_quota`. If `free_slots < 1`, halt with a clean-up hint listing the apps the operator can delete.
5. **First state file path.** Write the bootstrap live file to `example/<use_case_slug>/.vibecoding-state.md` (used in this repo's `example/` examples) or `workshops/<use_case_slug>/.vibecoding-state.md` (used by external adopters that follow the `workshops/` convention). Whichever path is chosen, record it verbatim in `bootstrap_preflight.first_state_file_path` so `migrate_canonical` knows exactly which file to move once `$APP_NAME` is resolved. Set `bootstrap_preflight.app_name_known_at_bootstrap = false` — `$APP_NAME` is resolved later by Module 1 / Prompt 2.
6. **Copy the template.** Copy [`references/state-template.md`](references/state-template.md) to `bootstrap_preflight.first_state_file_path`.
7. Replace `<USE_CASE_SLUG>` in the title and both `<ISO timestamp>` placeholders with the current ISO timestamp.
8. Write all `Workshop Choices` from the params above.
9. Run `databricks auth profiles` + `databricks current-user me` to capture `PROFILE`, `Workspace host`, `User email` into `Global Variables`. (`PROFILE` is the same value already stored as `bootstrap_preflight.workspace_profile`.)
10. Run the serverless-only preflight (`databricks compute-policies list`) and set `workspace_serverless_only`.
11. **DAB dev-mode schema-prefix detection.** If `dabs_bundle_path` is a real path (not `n/a`), shell out to `databricks bundle validate --target dev --output json` from that path and inspect every UC schema resource. If any resource has dev-mode prefixing applied (a name shaped like `dev_${user}_<schema>` instead of the unprefixed `<schema>`), set `bootstrap_preflight.bundle_dev_mode_schema_prefix_detected = true`. Every downstream prompt that passes `agent_schema`, `ops_schema`, or `uc_schema` into a job/notebook MUST read the resolved (prefixed) schema name from state — never the unprefixed variable name.
12. **Verify-job summary semantics.** Set `bootstrap_preflight.verify_summary_semantics` from the merged workshop config. Default `pass_field`/`warn_field`/`fail_field` are `"pass"`, `"warn"`, `"fail"` (matching `05_verify_infrastructure.py`'s `notebook.exit` payload). `warning_policy` defaults to `allow_with_notes`; set to `block_if_load_bearing` for use cases whose verify-job emits warnings that must block the gate. When `warning_policy == block_if_load_bearing`, any warning whose name matches an entry in the workshop's `gate_load_bearing_checks[]` list blocks the first verify gate (PASS only when `fail == 0` AND no load-bearing warning is present).
13. **Derive `variant_id`** from `pathway` + `track` using the deterministic derivation table in [`references/resolver-prompt.md`](references/resolver-prompt.md) § *Variant-ID Derivation Table*.
14. **Invoke `resolve_spec`** (see below) to parse the PRD at `prd_path` and populate the six spec sections (`## Variant`, `## Resources`, `## UI`, `## Agent`, `## Governance`, `## Spec Provenance`). This is a hard step: if `resolve_spec` halts, `bootstrap` halts.

**Outputs:** Path of the bootstrap state file (also stored as `bootstrap_preflight.first_state_file_path`), populated with `## Environment Capabilities` (section 0), `## Bootstrap Preflight`, Workshop Choices, Global Variables (partial), and fully resolved Variant / Resources / UI / Agent / Governance / Provenance spec sections (schema v2.0). The workshop continues with this path until `migrate_canonical` runs.

**Errors:** If the bootstrap path already exists, abort — do not overwrite. The operator must remove or migrate the stale file. Any of the four halt rules in `references/spec-schema.md` § Bootstrap Preflight (steps 1–4 above) abort before the template is copied. If `resolve_spec` fails validation twice, abort and surface the validation errors; the operator must fix the PRD before re-running.

**DAB dev-mode schema-prefix rule (consumer-side).** If Databricks Asset Bundle dev mode prefixes UC schema resource names, notebook/job parameters must receive the resolved prefixed schema name, not the unprefixed variable. Bootstrap captures `bundle_dev_mode_schema_prefix_detected`; any prompt that passes `agent_schema`, `ops_schema`, or `uc_schema` to a job reads the resolved value from state.

### Operation: `resolve_root`

**When:** Any prompt that writes an artifact **before `bootstrap` has run** (e.g. the PRD-generation prompt produces `docs/design_prd.md` *before* the PRD exists to bootstrap from). It is the minimal, gate-free way to learn *where relative artifact paths must land* so a bare `docs/…` does not resolve against a page-dependent CWD on Genie Code. Idempotent — safe to call repeatedly; a later `bootstrap` supersedes it as the persistence owner.

**Inputs:** none required. (Optional `state_file_path` — if the caller already knows where a state file lives.)

**Behavior:**

1. **Read-if-present.** If a state file with a `## Environment Capabilities` block (section 0) already exists (the live file, or the bootstrap path `example/<use_case_slug>/.vibecoding-state.md` / `workshops/<use_case_slug>/.vibecoding-state.md`), read `client_context`, `artifact_root`, and `skill_ref_root` from it and return them. Do **not** re-detect or rewrite.
2. **Else detect fresh (bootstrap step-0 detection ONLY).** Run just the client/root detection from `bootstrap` step 0 — no URL/profile/CLI/quota preflights, no template copy, no `resolve_spec`, no gates: if a Databricks-managed CLI channel is present (`runDatabricksCli` / Genie serverless markers) ⇒ `client_context: genie_code`, `artifact_root` = the git-folder workspace (clone) path (e.g. `/Workspace/Users/<email>/.assistant/skills/<repo>`), `skill_ref_root` = `"skills/" + basename(artifact_root)` (e.g. `skills/vibe-coding-workshop`); otherwise ⇒ `client_context: ide_cli`, `artifact_root` = the local repo root, `skill_ref_root` = empty.
3. **Echo, do not persist.** Return `client_context` + `artifact_root` + `skill_ref_root` for the caller to use immediately and to echo the clone-root + skill-load rules to the operator. **No file is written** — `bootstrap` step 0 remains the sole writer of section 0, so there is no "abort if path exists" conflict and no half-initialized state file.

**Outputs:** `{ client_context, artifact_root, skill_ref_root }` (ephemeral). The calling prompt resolves its relative artifact path as `<ARTIFACT_ROOT>/<relpath>`, loads any repo-relative skill path `X/Y/SKILL.md` as `<skill_ref_root>/X/Y/SKILL.md` via `readSkillFile` (§8), and echoes: "artifacts resolve under the workshop clone root (`artifact_root`) and skills load under `skill_ref_root` (= `skills/<clone-folder>` on Genie Code), never the page CWD."

**Errors:** None that halt — `resolve_root` is fail-soft. If detection is ambiguous, default to `ide_cli` / repo-root and note the assumption; the later `bootstrap` step 0 is authoritative.

### Operation: `resolve_spec`

**When:** Called automatically as the final step of `bootstrap`. May also be re-invoked manually if the PRD changes mid-workshop (rare; prefer restarting from bootstrap).

**Inputs:**

| Param | Type | Required | Description |
|---|---|---|---|
| `prd_path` | string | required | Path to the PRD. Read from `Workshop Choices.prd_path` if omitted. |
| `llm_endpoint` | string | required | LLM endpoint used to synthesize the spec. Read from `Workshop Choices.llm_endpoint` if omitted. Must be a Databricks Model Serving endpoint reachable from the workspace. |

**Behavior:**

1. Read the PRD contents from `prd_path` and compute `prd_sha256`.
2. Load the schema from [`references/spec-schema.md`](references/spec-schema.md) and the prompt from [`references/resolver-prompt.md`](references/resolver-prompt.md).
3. Derive `variant_id` deterministically from Workshop Choices (`pathway`, `track`) per the resolver prompt's *Variant-ID Derivation Table*. Inject it into the user prompt.
4. Call `llm_endpoint` with the system + user prompts. Expect a single YAML document with exactly six top-level keys: `variant_id`, `resources`, `ui`, `agent`, `governance`, `spec_provenance`.
5. Run the deterministic guards listed in the resolver prompt's "Post-resolution Guards" section:
   - YAML parses cleanly into a dict with the expected top-level keys.
   - Every validation rule in [`references/spec-schema.md`](references/spec-schema.md) §"Validation Rules" passes.
   - Consumer cross-check: each `agent.tools[].name` of `kind: function` with `language: python` reconciles with the PRD Tools Table.
   - Placeholder guard: no resource-ID-shaped strings leaked through.
   - Variant-ID echo check: emitted `variant_id` equals the one passed in.
   - MCP ref resolution: every `agent.tools[].mcp_server_ref` (kind=mcp) maps to an `agent.mcp_servers[].name`.
6. If any guard fails, retry **once** with the validation errors appended to the user prompt. Second failure halts bootstrap.
7. Split the validated YAML by top-level key and write each block into its matching state-file section (`## Variant`, `## Resources`, `## UI`, `## Agent`, `## Governance`, `## Spec Provenance`), replacing the `<pending>` placeholder body with a fenced ```yaml block containing the resolved content.
8. Stamp `## Spec Provenance` with `resolved_at`, `resolver_version: "2.0"`, `schema_version: "2.0"`, `prd_sha256`, and `llm_endpoint`.

**Outputs:** No return value; mutates the live state file.

**Errors:** Validation failure (after one retry), missing PRD file, unreachable `llm_endpoint`, or any LLM response that is not parseable YAML with the six expected keys — all halt bootstrap.

**Downstream contract:** Every consuming skill declares which fields it reads via a machine-parseable `fields_read:` YAML list in its frontmatter (see § *Field Consumer Contract* below and [`references/spec-schema.md`](references/spec-schema.md) §"Field Consumer Contract"). Prompts in `Instructions.md` and `WALKTHROUGH.md` reference resolved content by dotted path (e.g. `ui.user_journeys`, `agent.tools`, `governance.scorer_suite.guidelines`) instead of inlining domain-specific content. This is what makes the workshops use-case-agnostic.

### Operation: `enter`

**When:** At the **top** of every workshop prompt, before any domain skill or command runs.

**Inputs:**

| Param | Type | Required | Description |
|---|---|---|---|
| `prompt_id` | string | required | e.g. `0.1`, `3.2`, `5.A4`, `7.22.5`, or `20c`. Matches the heading the prompt will log under. |
| `require_prior_gate` | `{prompt_id: string, gate: string}` | optional | Assert the listed prompt's Gate equals the listed string. If it does not match, `enter` stops the workshop and surfaces the mismatch. |

**Behavior:**

1. **Locate the live state file:**
   - **First, resolve `state_file_root`** from the `## Environment Capabilities` block (section 0). Every path below is relative to it — the local repo root for `client_context: ide_cli`, the git-folder workspace path for `genie_code`. On a pre-capability state file (no section 0), default `state_file_root` to the repo root and proceed without assuming a deploy channel.
   - If `$APP_NAME` is known (Pathways A/B/C), use `<app_root>/.vibecoding-state.md` (= `<state_file_root>/<app_name>/.vibecoding-state.md`, the TOP-LEVEL app dir — NOT `apps_lakebase/<app_name>/`).
   - Else if `$AGENT_APP_NAME` is known (Track A agent app, Pathways C/D), use `<agent_app_root>/.vibecoding-state.md` (= `<state_file_root>/<agent_app_name>/.vibecoding-state.md`, the TOP-LEVEL agent app dir — NOT `apps_lakebase/<agent_app_name>/`).
   - **Else if `dp_bundle_root` is resolved (a data-product / lakehouse run with no app or agent app — e.g. the Gold-design→Bronze→Silver→Gold→semantic pipeline), use `<dp_bundle_root>/.vibecoding-state.md`** (= `<state_file_root>/{user_schema_prefix}_<use_case_slug>_dab/.vibecoding-state.md`). This is the **canonical DP-track live file** — the data-product analog of `<app_root>` / `<agent_app_root>`. The FIRST data-product prompt to run (Gold design, step 09 — or Bronze, step 10, if design was skipped) **bootstrap-creates** it from [`references/state-template.md`](references/state-template.md) if absent (a real create, copying the template + filling Workshop Choices from the prior `example/` bootstrap file if present — not just `resolve_root`); every later DP step appends to it. Do NOT leave data-product state in the temporary `example/` bootstrap path — that path carries no durable record and was the root cause of "state survived only in chat summary."
   - Else fall back to the bootstrap path `<state_file_root>/example/<use_case_slug>/.vibecoding-state.md` (pre-bootstrap only — once `dp_bundle_root`/`app_root`/`agent_app_root` is known, migrate/bootstrap-create the canonical file above).
   - If none of these exists yet: for the **`dp_bundle_root`/`app_root`/`agent_app_root` canonical paths, bootstrap-create the file from the template** (this is the first prompt of that track); only stop and tell the operator to run `bootstrap` first if even `use_case_slug`/Workshop Choices are unknown.
2. **Schema v2.0 gate (hard fail).** Parse the `## Spec Provenance` YAML block. If `schema_version != "2.0"`, halt with:

   ```
   State file uses schema v<X> — this repo is strictly v2.0.
   Run: python scripts/migrate-spec-v1-to-v2.py <path-to-state-file>
   Then re-run this prompt.
   ```

   No best-effort reads against older shapes.
3. **Read end-to-end.** Treat `Workshop Choices`, `Global Variables`, and `Captured Resource IDs` as authoritative. **Never ask the operator for a value that already exists in state.**
4. **Multi-file resolution via `state_file_set`.** Parse the `## State File Set` block.
   - If `state_file_set.secondary.path` is `<pending>` or null, treat the located file as the only source — done.
   - If `secondary` is declared and `prompt_id` is in `secondary.required_for_prompts`, read the secondary file too. Halt if it does not exist (remediation: run `bootstrap` for the missing side or correct `secondary.path`).
   - Walk both files following `lookup_order` (e.g. `["primary", "secondary"]`). For each canonical field requested by the prompt, the first hit wins.
   - For any canonical field present in **both** files with different values: halt unless `conflict_policy: primary_wins` is set explicitly. With `primary_wins`, use the primary value and append the conflict to `## State Contract Audit` (`fields_read_but_never_produced` / `captured_fields_with_no_consumer` are unaffected; conflicts get their own audit row).
5. **Apply `canonical_names` aliasing on read.** Parse the `## Canonical Names` block. Whenever the prompt reads an env var, HTTP header, jq path, or state field listed as a legacy/incorrect spelling on the left of a `canonical_names` map, resolve to the canonical name on the right. If the map's value is `null` (e.g. `http_headers.x-forwarded-user-info: null`), the name does not exist; halt and surface a hint pointing at the canonical alternatives. `state_contract_audit` performs the same checks at audit time.
6. **Enforce the prior gate** if `require_prior_gate` is set. On mismatch, halt unless a matching entry exists in `state_overrides[]` (see step 7). Mismatches that are NOT covered by an override stop the workshop.
7. **Apply `state_overrides[]` (fail-closed escape hatch).** Parse `## State Overrides`. An override entry covers a failing gate when ALL of the following hold: `prompt_id` matches the current prompt; `gate_type` matches the failing gate (`require_prior_gate` for step 6, `hard_assert` / `preflight_check` for step 9 below, `pathway_applicability` for step 8); and `expires_at` is in the future relative to the current ISO timestamp. A covered failure is treated as satisfied and the override is logged in the prompt's `Resolved issues / workarounds` Per-Step Log entry. Expired or missing entries DO NOT cover the failure — `enter` halts. Cross-session continuity (e.g. resuming from a previous run's state file) is recorded as a `state_override` whose `reason` cites the earlier run's evidence; it is NOT a prose exception.
8. **Consult the Pathway Applicability Matrix** (below). If the prompt does not apply for this `pathway`/`track` and no `state_override` with `gate_type: pathway_applicability` covers it, synthesize a `## Prompt <prompt_id> — Skipped (N/A for pathway <X>)` section with `Gate: Skipped — N/A for pathway <X>`, append it, and return a `skipped: true` signal so the prompt body short-circuits. With a covering override, proceed (the override `reason` is logged in the prompt's Per-Step Log entry).
9. **Enforce `deferred_actions[]`.** Parse `## Deferred Actions`. Halt if the current prompt's role is in any open `deferred_action`'s `target_prompt_roles[]` and its `divergence_check` evaluates to false (or fails to parse under the divergence-check grammar in `references/spec-schema.md` § *Deferred Actions*). Halt is suppressed only when a `state_override` with `gate_type: hard_assert` (or `preflight_check`) on the current `prompt_id` exists AND its `references[]` contains `"deferred_action:<id>"` matching the action's `id`. If `divergence_check` returns true, flip `status` to `resolved` and proceed. Entries with `status: waived` are skipped without evaluation.
10. **Enforce `mlflow_eval_known_quality_issues[]`.** Parse `## MLflow Eval Known Quality Issues`. If the current prompt's role appears in any open issue's `target_prompt_roles_blocked[]`, halt with a remediation hint citing `id`, `source_prompt_role`, and `error_signature` — unless a `state_override` exists on the current `prompt_id` whose `references[]` contains `"known_issue:<id>"` matching the issue's `id`. The issue's `error_signature` SHOULD be a name from `gate_load_bearing_checks[]` so audits and verify summaries align, but `enter` halts purely on `target_prompt_roles_blocked[]` membership and `status: open` — it does NOT consult `gate_load_bearing_checks[]` directly (that list drives `state_contract_audit` and the verify-job `warning_policy: block_if_load_bearing` rule per § *Gate Load Bearing Checks* in `references/spec-schema.md`).
11. **Enforce `preflight_check_registry`.** Parse `## Preflight Check Registry`. For each registry entry, if the current prompt's role appears in `blocks_prompt_roles[]`, evaluate the matching state field per the *State-field mapping* table in `references/spec-schema.md` § *Preflight Check Registry*. If the pass condition is not met (the field is `<pending>`, missing, or fails the predicate), halt with a remediation hint pointing at `owner`. The halt is suppressed only when a matching `state_override` with `gate_type: preflight_check` exists on the current `prompt_id` whose `affected_state_field` matches the check's state field. For `reflection_lm_large_context_probe`, the check is treated as passing only when a synchronous ≥80000-character probe has been run against the currently bound `llm_role_endpoints.reflection_lm.endpoint` and `endpoint_guardrail_audit[<reflection_lm.endpoint>].long_context_ok == true` AND `accepted_min_context_chars >= 80000` — the generic bootstrap endpoint guardrail pass is NOT sufficient on its own. The owning skill (`instruction_iteration`) MUST invoke the probe synchronously before any 08b diff-summary helper or iteration helper call. For `genie_code_manifest_loaded` (G3, the one **client-conditional** check), evaluate it **only when `environment_capabilities.client_context == 'genie_code'`** — it is inert on `ide_cli` — and on Genie Code halt the deploy roles until `environment_capabilities.genie_code_manifest_loaded == true` (the agent has read `skills/genie-code-environment` in-thread); see `references/spec-schema.md` § *Genie Code manifest-load gate*.
12. **Resolve variables.** Return the subset of state the prompt body needs (it is declared in the prompt's `enter` invocation — e.g. `APP_NAME`, `PROFILE`, `warehouse_id`). **Always also return the environment-capability set** so any deploy/run instruction the prompt emits uses the resolved verb + channel instead of assuming a local IDE: `bundle_deploy.verb` (always `bundle deploy --target dev`), `app_deploy.verb` (`apps deploy`), `cli_channel` (`local_shell` for `ide_cli`, `runDatabricksCli` for `genie_code`), `artifact_root` + `skill_ref_root`, and — for data-product prompts — `dp_bundle_root` (so the bundle is written and deployed under `<artifact_root>/{user_schema_prefix}_<use_case_slug>_dab`, not the bare clone root), and — for AppKit app-track prompts — `app_root` (so the app is scaffolded, wired, and deployed under `<artifact_root>/<app_name>`, the top-level app dir, on both clients), and — for Track A custom-agent prompts — `agent_app_root` (so the agent app is cloned, wired, and deployed under `<artifact_root>/<agent_app_name>`, the top-level agent app dir, on both clients). When `bundle_deploy.page_context_required: true`, also return the page-context note (Genie Code must run the deploy from the `dp_bundle_root` page). The body never hardcodes a bare-shell `databricks` call.

**Outputs:** `{skipped: bool, resolved: {<key>: <value>}, capabilities: {client_context, cli_channel, bundle_deploy, app_deploy, state_file_root}}`.

**Errors:**

- step 6 — prior-gate mismatch with no covering override.
- step 7 — invalid override (expired / missing fields / fails any of the four override-coverage clauses).
- step 8 — pathway-applicability mismatch with no `pathway_applicability` override.
- step 9 — open `deferred_action` whose `divergence_check` evaluates to false (or fails to parse) and no `state_override` references it.
- step 10 — open `mlflow_eval_known_quality_issue` whose `target_prompt_roles_blocked[]` includes the current prompt and no `state_override` references it.
- step 11 — `preflight_check_registry` entry whose `blocks_prompt_roles[]` includes the current prompt's role and whose state-field pass condition is not met (and no `state_override` with `gate_type: preflight_check` covers it). For `reflection_lm_large_context_probe`, the synchronous large-context probe MUST have been run against the currently bound reflection-LM endpoint with `accepted_min_context_chars >= 80000`.
- step 7 corollary — expired `state_overrides[]` entries do NOT cover failures.

Other halt conditions (not numbered above): missing state file, unresolved `<pending>` value the prompt requires, missing required secondary state file when `prompt_id` is in `state_file_set.secondary.required_for_prompts`, conflicting canonical fields across primary/secondary without `conflict_policy: primary_wins`, and read on a header/env-var/jq-path/state-field whose `canonical_names` entry is `null`.

### Operation: `migrate_canonical`

**When:** Exactly once, at the prompt that first resolves `$APP_NAME` (Pathways A/B/C, usually Prompt 1.1 / Prompt 2 of the walkthrough) or `$AGENT_NAME` (Pathway D, usually Prompt 4.0).

**Inputs:**

| Param | Type | Required | Description |
|---|---|---|---|
| `app_name` | string | required for A/B/C | Mutually exclusive with `agent_name`. |
| `agent_name` | string | required for D | Mutually exclusive with `app_name`. |

**Behavior:**

1. Move `example/<use_case_slug>/.vibecoding-state.md` to `<app_root>/.vibecoding-state.md` (= `<artifact_root>/<app_name>/.vibecoding-state.md`, A/B/C) or `<agent_app_root>/.vibecoding-state.md` (= `<artifact_root>/<agent_app_name>/.vibecoding-state.md`, Track A agent app for C/D).
2. Update `Global Variables.APP_NAME` (or `AGENT_NAME`).
3. All subsequent `enter` calls resolve to the canonical path automatically.

**Outputs:** Path of the canonical state file.

**Errors:** If the canonical path already exists, abort — the operator has collided with an earlier run.

### Operation: `exit`

**When:** At the **bottom** of every workshop prompt, after all verification checks have passed.

**Inputs:**

| Param | Type | Required | Description |
|---|---|---|---|
| `prompt_id` | string | required | Must match the `enter` call. |
| `title` | string | required | Human-readable title (e.g. `Deploy to Databricks Apps`). |
| `gate` | string | required | The Gate line. For build/modify prompts this MUST be `Local testing passed`. For infra/deploy/eval prompts it is the prompt's success criterion (e.g. `Deployment RUNNING`, `Eval thresholds met`, `Signoff APPROVED`). For skipped steps: `Skipped — N/A for pathway <X>`. |
| `captured` | `{key: value, ...}` | optional | Newly resolved `Captured Resource IDs` (e.g. `{app_url: "https://..."}`). The skill writes these into the top-of-file list, replacing the matching `<pending>` entries. |
| `skills_invoked` | `[string, ...]` | optional | Paths of domain skills that ran between `enter` and `exit`. Written into the Per-Step Log. |
| `resolved_issues` | `[string, ...]` | optional | One bullet per issue hit and its fix. Defaults to `none`. |
| `verification` | `[string, ...]` | optional | One bullet per objective check that passed. |

**Behavior:**

1. Run the prompt's verification checks (caller supplies `verification` if declared). When a check involves a deploy/run, use the verb + CLI channel resolved by `enter` from `## Environment Capabilities` (never a bare-shell `databricks` call).
2. Append a new `## Prompt <prompt_id> — <title>` section to the live state file (located under `environment_capabilities.state_file_root`, same resolution as `enter` step 1) using the Per-Step Log template in [`references/state-template.md`](references/state-template.md).
3. Update `Captured Resource IDs` at the top — replace `<pending>` entries for every key in `captured`. Mark pathway-irrelevant IDs `<n/a>`.
4. Bump `Last updated` in the header.
5. **Gate rule (hard):** if the prompt is a build/modify prompt, `gate` MUST be `Local testing passed`. If it is anything else, `exit` stops and the next deployment-oriented prompt's `enter` will reject on the prior-gate check.
6. **Verify the write (load-bearing — not advisory):** after appending, **re-read the live state file** and confirm the new `## Prompt <prompt_id>` section, the updated `Captured Resource IDs`, and the bumped `Last updated` are actually present. If the re-read does not show the appended section, the `exit` did NOT persist — retry the write (on Genie Code, fall back to `executeCode` `open(path,"a")` when `workspaceUpdateFile` silently no-ops on an existing file). **The prompt is NOT complete until this re-read confirms the write.** The chat summary is NOT the state store.
7. Print a 3-line summary to chat: what was created, what values were captured, what the next prompt will consume.

**Handoff invariant (every summary / context-compaction / thread handoff):** carry `state_file_path`, `last_completed_prompt`, `last_gate`, `environment_capabilities`, and `state file updated: yes/no` verbatim (see [`references/retrospective-template.md`](references/retrospective-template.md) § *Handoff invariant*). A handoff that omits these is non-conformant; the next thread must re-open the live file rather than trust the prose.

**Outputs:** The new log section's path inside the state file.

**Errors:** Verification check failure, gate-rule violation — halt without marking complete.

### Operation: `retrospective.per_prompt`

**When:** Async, after the whole workshop completes. Run once per executed prompt. **Do not interleave with active prompts.**

**Inputs:**

| Param | Type | Required | Description |
|---|---|---|---|
| `prompt_id` | string | required | The prompt being retro'd. |
| `title` | string | required | Same title logged in the Per-Step Log. |
| `transcript` | string \| `null` | optional | Raw agent transcript. If null, reconstruct from the state file's `Resolved issues` + `Verification` bullets. |

**Behavior:**

1. Load [`references/retrospective-template.md`](references/retrospective-template.md).
2. Fill in the per-prompt block exactly as specified (fixed headings, no additions or renames).
3. Append to `example/<use_case_slug>/retrospective.md`.
4. Print back to chat: Friction score, Outcome, Pathway/track applicability verdict, Top 3 improvements. Nothing else.

**Errors:** If the state file has no matching `## Prompt <prompt_id>` section, halt — there is nothing to retro.

### Operation: `retrospective.rollup`

**When:** After every per-prompt retro is in `retrospective.md`. Run exactly once.

**Inputs:** None.

**Behavior:** Follow the Session Rollup Prompt in [`references/retrospective-template.md`](references/retrospective-template.md). Produce `example/<use_case_slug>/retrospective-rollup.md` with the seven fixed sections (Instructions.md edits, Skill edits, State-file schema edits, Pathway Applicability Matrix edits, Top disambiguation gaps, Gate violations, Spec drift).

Before producing the backlog, run the **Spec Drift** checks from the rollup template in this order:

1. **PRD drift.** Compute `sha256` of the file at `## Workshop Choices → prd_path` and compare with `## Spec Provenance → prd_sha256`. Mismatch → halt with a hard error instructing the operator to re-run `resolve_spec` (or accept drift by updating `prd_sha256` explicitly).
2. **Schema drift.** Read `## Spec Provenance → schema_version`. If it differs from the `Schema Version` in [`references/spec-schema.md`](references/spec-schema.md) (currently `"2.0"`), halt with a hard error: either run the migrator for that schema bump or re-run `resolve_spec` on the current schema.
3. **Producer-consumer contract (fields_read: drift check).** Load every known consumer skill's frontmatter and parse its `fields_read:` YAML list. Parse the live state file's `## Resources`, `## UI`, `## Agent`, `## Governance` YAML blocks and enumerate every dotted-path leaf. Compute `consumed = union(fields_read:)` (expand parent paths like `ui.*` to their leaves). Compute `produced = leaves_of(state file)`. Halt with a hard error if:
   - `produced − consumed ≠ ∅` → resolver emitted a field nothing reads (stale or missing consumer).
   - `consumed − produced ≠ ∅` → consumer declares a read on a field the resolver did not emit (schema drift or typo).

Only if all three pass does the rollup proceed to enumerate the four non-blocking sub-checks (unused resolved fields, hardcoded leaks), merge them into the backlog as section 7 (`Spec drift`), and write the rollup file.

Surface `state_contract_audit.productized_debts_status` in the rollup as a one-line debt-lift summary (e.g. "Productized debts: 5 total / 1 lifted / 0 parse errors").

**Outputs:** Path of the rollup file. On halt, path of a short error report at `example/<use_case_slug>/retrospective-rollup.ERROR.md` explaining which check failed and how to recover.

### Operation: `state_contract_audit`

**When:** Run before `retrospective.rollup`, before any workshop release, and after modifying prompt/skill state fields.

**Inputs:**

| Param | Type | Required | Description |
|---|---|---|---|
| `prompt_registry_ref` | string | required | Path or SQL seed ref containing prompt `captured` fields. |
| `skill_root` | string | optional | Default: `genai-agents`. |
| `state_template_path` | string | optional | Default: `skills/vibecoding-state/references/state-template.md`. |
| `mode` | enum | optional | `warn` for local authoring, `fail` before release. Default: `fail`. |

**Behavior:**

1. Parse every prompt's declared `captured` fields from `docs/02_seed_section_input_prompts.sql`.
2. Parse every skill frontmatter `fields_read:` and `produces:` list.
3. Parse `references/spec-schema.md` and `references/state-template.md`.
4. Emit four lists:
   - `fields_read_but_never_produced`
   - `fields_produced_but_not_in_schema`
   - `schema_fields_missing_from_template`
   - `captured_fields_with_no_consumer`
5. **Canonical-names extension.** Parse the live state file's `## Canonical Names` block and grep prompt sources + skill bodies for legacy/incorrect spellings of env vars, HTTP headers, jq paths, MLflow Prompt Registry URI schemes, and eval-dataset column names. Add any non-canonical reads to `fields_read_but_never_produced` (with the legacy name as the field) so the same fail-list flushes them. Reads on `null`-valued canonical entries (e.g. `x-forwarded-user-info`) are always reported regardless of mode.
6. **Preflight-registry extension.** Parse the live state file's `## Preflight Check Registry` block. For each entry, verify (a) `owner` resolves to either a real skill path under `skill_root` or a known prompt id in the workshop's prompt registry, and (b) every check name referenced from a prompt body or skill `fields_read:` list exists as a key in the registry. Unresolved owners and unknown referenced check names are added to `fields_read_but_never_produced` so the same fail-list flushes them. Until forward-referenced owners (Phase 2.2's `instruction_iteration`, Phase 4.4's `lakebase_memory`, etc.) land, those entries roll up into `fields_read_but_never_produced` rather than halting `mode: fail`. See references/spec-schema.md § Preflight Check Registry "Forward-reference handling" carve-out.
7. In `mode: fail`, halt if any of the first three lists are non-empty (canonical-name and preflight-registry violations roll up into `fields_read_but_never_produced`, so they halt too).
8. Write the audit result to the `## State Contract Audit` section of the state file.

**Outputs:** Mutates state with the audit result and prints a markdown table suitable for `retrospective.rollup`.

### Operation: `endpoint_guardrail_audit`

**When:** During `bootstrap`, before `llm_role_endpoint_probe` selects bindings. May be re-run after the workshop if the operator suspects an endpoint changed (e.g. a new workspace guardrail was attached).

**Inputs:**

| Param | Type | Required | Description |
|---|---|---|---|
| `endpoints` | `[string]` | required | Endpoints to probe. Typically the union of every `llm_role_endpoints.<role>.candidates` list, deduplicated. |
| `profile` | string | optional | Databricks CLI profile. Defaults to `Global Variables.PROFILE`, then `DATABRICKS_CONFIG_PROFILE`. |

**Behavior:**

1. Shell out to [`scripts/probe_endpoints.py`](scripts/probe_endpoints.py) with `--profile <profile>`, `--timeout <seconds>` (default 60), and the endpoint list as positional args. Pass `--skip-long-context` for endpoints that are NOT bound to `reflection_lm` (the long-context probe submits ~80k input characters per endpoint and is only required for the reflection LM). Use `--output <path>` when you want the JSON written to a file rather than captured from stdout — note that the script's stdout is reserved for the JSON result either way; diagnostics, retries, and timeout notices go to stderr.
2. The script returns a JSON object keyed by endpoint name, with the eight `EndpointProbe` fields per entry: `audited_at`, `short_chat_ok`, `long_context_ok`, `sql_quote_ok`, `streaming_arg_accepted`, `input_guardrail_signature`, `output_guardrail_signature`, `accepted_min_context_chars`. Two of these names changed to match what they actually measure: `streaming_arg_accepted` (was `streaming_ok`) records that the endpoint did not reject the SDK's `stream=True` kwarg — NOT that it actually streams chunks (the SDK buffers SSE internally). `accepted_min_context_chars` (was `observed_context_chars`) is the input-length floor the probe successfully submitted (e.g. 80000), or `0` when the long-context probe was skipped, or `-1` when it failed. It is a floor, not an observation of the endpoint's true context window. A real streaming probe is tracked as a TODO in the script.
3. Write the parsed result into the live state file's `## Endpoint Guardrail Audit` block, merging with any existing entries (later runs replace earlier entries for the same endpoint name; entries for endpoints not in `endpoints` are preserved).

**Cost note.** The long-context probe submits ~80k input characters per endpoint. For a candidate set of N endpoints, that is ~80k × N input chars per audit run on top of the three short probes. Pass `--skip-long-context` for any endpoint not bound to `reflection_lm` to keep the audit cheap; the workshop only requires the long-context floor on the reflection LM.

**Timeout note.** `--timeout` (default 60s) wraps each of the four sub-probes per endpoint. On timeout, the response field records the literal string `"timeout"` and the corresponding `*_ok` bool is `False`. Timeouts are NOT retried; non-timeout failures retry once with a 2-second backoff before being recorded.

**Outputs:** No return value; mutates the live state file. The probe JSON is also echoed to stdout (or to `--output PATH` if set) so the operator sees exact platform error strings on failures.

**Errors:** If the probe script exits non-zero or returns invalid JSON, halt and surface stderr. Per-endpoint failures (e.g. one endpoint returns `short_chat_ok: false` or `streaming_arg_accepted: false` with response `"timeout"`) are NOT errors — they are the data the next operation acts on.

### Operation: `llm_role_endpoint_probe`

**When:** During `bootstrap`, immediately after `endpoint_guardrail_audit` populates `## Endpoint Guardrail Audit`. Halts bootstrap if no candidate satisfies a role's selection rule.

**Inputs:** None — reads `## LLM Role Endpoints` and `## Endpoint Guardrail Audit` from the live state file.

**Behavior:**

1. For each role in `llm_role_endpoints`, walk `candidates` in order and apply the role's selection rule (below). The first candidate whose audit row satisfies all required predicates is bound to `endpoint`.
2. Set `selected_after_probe: true` and write a one-line `rationale` describing which probe checks passed (e.g. `"databricks-gpt-5-mini passed short_chat_ok && sql_quote_ok; gpt-5-2 not yet audited"`).
3. If no candidate satisfies a role's rule, halt bootstrap and emit the audit JSON for that role's candidates so the operator can either expand `candidates` or fix the underlying endpoint.

**Selection rules:**

- `agent_chat`: choose the first candidate with `short_chat_ok`. Streaming may be `false`.
- `agent_chat_streaming_smoke`: choose the first candidate with `short_chat_ok && streaming_arg_accepted`. (Rename only — same semantics. The selection rule still binds based on whether the endpoint accepted `stream=True` at the SDK layer, which is all the probe currently measures.)
- `reflection_lm`: choose the first candidate with `short_chat_ok && long_context_ok && sql_quote_ok`.
- `llm_judge_default`: choose the first candidate with `short_chat_ok && sql_quote_ok`.
- `failure_categorizer`: choose the first candidate with `short_chat_ok && sql_quote_ok`.

The default candidate lists in [`references/state-template.md`](references/state-template.md) put GPT first for non-chat roles, with Llama as fallback. If every GPT candidate fails its rule, Llama may bind only if it passes the same rule. If every candidate fails, bootstrap halts with the audit JSON — the operator must fix the endpoint or extend `candidates` and re-run.

**Outputs:** No return value; mutates `## LLM Role Endpoints` with `endpoint`, `selected_after_probe`, and `rationale` for every role.

**Errors:** Any role with no qualifying candidate halts bootstrap.

### Operation: `audit_debts`

**When:** Run before `retrospective.rollup` and after every prompt that introduces or could close a productized debt (typically alongside `state_contract_audit`). May also be re-run on demand if the operator suspects a `remove_when` predicate has flipped.

**Inputs:**

| Param | Type | Required | Description |
|---|---|---|---|
| `mode` | enum | optional | `warn` for local authoring, `fail` before release. Default: `warn`. `fail` halts when any debt with `debt_lifted: true` still has the workaround in place at the next implementation pass. |
| `audited_at` | string | optional | ISO8601 UTC timestamp to stamp on appended `audit_history[]` entries. Defaults to current time. |

**Behavior:**

1. Parse the live state file's canonical `## Productized Debts` H2 section. Treat this section as authoritative — operators MAY add entries but MUST NOT remove the seeds in [`references/state-template.md`](references/state-template.md). Joint reporting with `## State Contract Audit` is required: this operation appends a one-row summary to that section so audit consumers see debt status alongside contract drift.
2. For each entry, evaluate `remove_when` against the parsed live state file using the divergence-check grammar in [`references/spec-schema.md`](references/spec-schema.md) § *Deferred Actions* (extended with `AND` / `OR` connectors and the `[]` empty-array literal — see § *Divergence-check grammar* in that file). Strings that fail to parse are treated as evaluating to false and recorded with `debt_lifted_evaluation: parse_error`.
3. If `remove_when` evaluates true, set `debt_lifted: true` and append a new entry to `audit_history[]` with `audited_at`, `debt_lifted_evaluation: true`, and `evaluator_evidence` (the resolved jq-path or field set the predicate consulted). The next implementation pass that touches `introduced_at_prompt_role`'s downstream prompts MUST remove the workaround; `audit_debts` halts in `mode: fail` if a lifted debt's workaround is still detected on subsequent runs.
4. If `remove_when` evaluates false, leave `debt_lifted: false`, append an `audit_history[]` entry with `debt_lifted_evaluation: false` and an `evaluator_evidence` snippet citing the field(s) that did not satisfy the predicate.
5. "Accepted permanent debt" means **no admin-ticket dependency exists** — the workshop deliberately ships with the workaround and there is no upstream owner to file against. It does **NOT** mean the debt lacks a `remove_when` predicate. Every productized debt MUST carry a `remove_when` string; debts whose closure depends only on internal workshop work use predicates over `mlflow_eval_known_quality_issues[]`, `endpoint_guardrail_audit[...]`, or `agent.*` configuration, not on external tickets.
6. Write the updated `productized_debts[]` list back to the `## Productized Debts` section. Append a one-row summary `productized_debts_status: { total, lifted, parse_errors }` to `## State Contract Audit` for joint reporting.

**Outputs:** No return value; mutates the live state file's `## Productized Debts` section and the `productized_debts_status` summary in `## State Contract Audit`. Prints a markdown table of `(name, debt_lifted, last_evaluation, evaluator_evidence)` suitable for the rollup.

**Errors:** Halts in `mode: fail` if (a) the canonical `## Productized Debts` section is missing, (b) any seed entry has been removed, or (c) any debt is marked `debt_lifted: true` but a subsequent implementation pass has not removed the workaround. Per-debt `parse_error` evaluations are NOT errors — they are recorded in `audit_history[]` and surfaced in the printed table so the operator can fix the predicate.

### Operation: `skill_helper_resolution`

**When:** Invoked by any consuming skill or prompt that needs to resolve a skill-prescribed helper (an import path, a function signature, a bundle-resource schema, an API/CLI field path, or a CLI-version-dependent schema) to the concrete shape available in the current workspace/library/CLI version. Run before the helper is called for the first time; re-run when the predicate-bearing surface (SDK version, CLI version, workspace policy) changes.

This operation is the structural fix for retrospective recurring-issue #11 ("skill helper vs concrete shape"): the skill prescribes a "canonical" surface, the workspace ships a different one, the agent rediscovers the right one, captures it in state, but the skill stays unchanged. Lifting resolution into `vibecoding-state` lets every consuming skill emit `(contract_name, candidates[], min_cli_version, inline_template_fallback)` and inherit the same first-callable-wins probe + capture contract.

**Inputs:**

| Param | Type | Required | Description |
|---|---|---|---|
| `contract_name` | string | required | Stable identifier for the helper contract the consuming skill emits. Examples: `obo_helper`, `predict_fn_signature`, `genie_space_resource_schema`, `apps_get_status_jq_path`, `databricks_apps_resource_app_schema`. |
| `candidates` | `[Candidate]` | required | Ordered list of concrete shapes to probe. The first candidate that satisfies its kind-specific probe wins. Each entry is `{kind: string, value: string, probe: string \| null}`. `kind` MUST be one of the six values listed under *Candidate kinds* below. |
| `min_cli_version` | string \| `null` | optional | Minimum `databricks --version` required for any `cli_version_dependent_schema` or `cli_field_path` candidate to be eligible. Compared lexicographically against `bootstrap_preflight.databricks_cli_version`. Candidates whose kind is CLI-version-sensitive are skipped when the installed CLI is older. Pass `null` (or omit) for contracts that do not depend on CLI version. |
| `inline_template_fallback` | string \| `null` | optional | A concrete in-template path or reference module the consuming skill ships when no SDK candidate resolves (e.g. `agent_server/long_term_memory.py` for the missing `databricks_openai.LongTermMemory` case at Prompt 15). Used only when every entry in `candidates` fails its probe. If both `candidates` exhaust and `inline_template_fallback` is `null`, the operation halts. |

**Candidate kinds.** The `kind` discriminator on each candidate selects the probe shape `vibecoding-state` runs. The six recognized kinds are:

- `import_path` — Python dotted path. Probe: `importlib.util.find_spec(value)` returns non-`None`. Covers Prompts 9 / 13 / 14 / 15 / 20a (skill points at an import that does not resolve).
- `function_signature` — Python callable + signature contract. `value` is `<dotted.module.callable>::<param_list_or_protocol>`. Probe: `inspect.signature` on the resolved callable matches the declared shape. Covers Prompt 16 (skill says `predict_fn(messages: list[dict])`, runner expects `predict_fn(question: str) -> str`).
- `bundle_resource_schema` — Databricks Asset Bundle resource schema. `value` is `<resource_kind>::<required_field_set>`. Probe: `databricks bundle validate --output json` accepts a synthetic bundle that exercises the field set without warnings whose names appear in `gate_load_bearing_checks[]`. Covers Prompt 17 (`genie_space` needs `name` + `space_id`; `apps` resource needs `experiment.id` vs `experiment.experiment_id`).
- `api_field_path` — Databricks REST API JSON field path. `value` is `<endpoint>::<json.field.path>`. Probe: a single read against the endpoint returns a non-null value at that path. Covers `KA serving Responses API: input` vs `Chat Completions: messages`.
- `cli_field_path` — `jq`-style path into Databricks CLI JSON output. `value` is `<cli_command>::<jq_path>`. Probe: running the command and applying the jq path returns a non-null value. Covers `apps get .status.state` vs `.app_status.state` (cross-checks `canonical_names.jq_paths`).
- `cli_version_dependent_schema` — bundle/apps schema field whose acceptance depends on the installed CLI version. `value` is `<resource_kind>::<field_path>::<min_cli_version>`. Probe: installed CLI `>= min_cli_version` AND `databricks bundle validate` accepts the field without stripping. Covers Prompt 18 (v0.297.1 silently strips `AppResourceApp` fields; v0.298.0 forwards them).

**Behavior:**

1. **CLI-version gate (Gap-1 fallback on Genie Code).** If `min_cli_version` is set, halt early when `bootstrap_preflight.databricks_cli_version < min_cli_version` AND no candidate kind in `candidates` is `import_path` or `function_signature` (the two CLI-independent kinds). The remediation hint MUST cite the upgrade path captured by `bootstrap` step 3. **Exception — `databricks_cli_version == unknown_on_genie_code`:** the numeric comparison is undefined (no version string on Genie Code), so **do not halt on the version gate**. Instead, treat every `cli_version_dependent_schema` / `cli_field_path` candidate as *eligible* and let its own probe (`databricks bundle validate` accepting the field without stripping) decide — the behavior probe replaces the numeric gate. The managed channel tracks a current CLI, so a stale-install failure (the only thing the numeric gate guards) cannot occur; if the probe itself rejects the field, the normal candidate walk falls through to the next candidate or `inline_template_fallback`.
2. **Walk `candidates` in order.** For each candidate, run the kind-specific probe described above. The first candidate whose probe succeeds is selected; remaining candidates are not probed. Probes MUST be side-effect free against workspace state (no resource creation; read-only API/CLI calls).
3. **Fallback selection.** If every candidate fails its probe, select `inline_template_fallback` if non-null; otherwise halt. The fallback is recorded with `selected_kind: inline_template_fallback` and `fallback_used: true`.
4. **Capture.** Append (or replace, keyed by `contract_name`) an entry to the live state file's `## Skill Helper Resolutions` section:

   ```yaml
   skill_helper_resolutions:
     - contract_name: <contract_name>
       selected_kind: <one of: import_path | function_signature |
                              bundle_resource_schema | api_field_path |
                              cli_field_path | cli_version_dependent_schema |
                              inline_template_fallback>
       selected_value: <the candidate's `value` string, or the
                       inline_template_fallback string>
       probed_at: <ISO8601 UTC>
       fallback_used: <bool — true when no candidate's probe succeeded>
   ```

5. **Return value.** The operation returns `{selected_kind, selected_value, fallback_used}` to the caller so the consuming skill / prompt can use the resolved shape directly without a second lookup.

**Outputs:** Mutates `## Skill Helper Resolutions` in the live state file and returns the resolved triple to the caller. Stale entries for the same `contract_name` are replaced; the most recent `probed_at` always wins.

**Errors:**

- `min_cli_version` not satisfied AND no CLI-independent candidate present.
- Every candidate's probe failed AND `inline_template_fallback` is `null`.
- A candidate `value` does not parse under its kind's expected `<a>::<b>` shape.
- A `cli_version_dependent_schema` candidate's embedded `min_cli_version` conflicts with the operation-level `min_cli_version`.

**Downstream contract.** Consuming skills that depend on a resolved helper MUST cite the entry by `contract_name` in their `fields_read:` frontmatter via the canonical path `skill_helper_resolutions[contract_name='<name>'].selected_value`. `state_contract_audit` flags any `fields_read:` entry that names a `contract_name` not present in the state file's `## Skill Helper Resolutions` section.

---

## State File Layout

Every live state file has a section-0 capability block plus twenty-two numbered parts (schema v2.0). The full schema is in [`references/state-template.md`](references/state-template.md); the resolved-spec schema is in [`references/spec-schema.md`](references/spec-schema.md).

0. **Environment Capabilities** — written by `bootstrap` step 0 before anything else; read by `enter` / `exit` and every prompt. Resolves the active coding client (`client_context: ide_cli | genie_code`), the `cli_channel` (`local_shell` | `runDatabricksCli`), the client-invariant `bundle_deploy.verb` (`bundle deploy --target dev`) with its `page_context_required` flag, the `app_deploy` verb (gated), `destructive_ops: confirm_required`, and the `state_file_root` under which all state-file paths resolve. This is the RULE_0 (navigation preamble) / RULE_1 (deploy verb) source of truth — the skill/prompt body stays one content set across clients; only the preamble and channel vary.
1. **Workshop Choices** — `use_case_slug`, `prd_path`, `pathway`, `track`, `dabs_bundle_path`, `llm_endpoint`. Set once at `bootstrap`, never changed.
2. **Global Variables** — `APP_NAME`, `AGENT_NAME`, `PROFILE`, `Workspace URL`, `Workspace host`, `User email`, `workspace_serverless_only`, `UC catalog`, `UC schema (app|agent|ops)`.
3. **Captured Resource IDs** — `warehouse_id`, `warehouse_name`, `llm_endpoint_ready`, `bundle_job_id`, `last_successful_run_id`, `last_verify_summary`, `app_url`, `serving_endpoint_name`, `ai_gateway_endpoint`, `mlflow_experiment_path`, `mlflow_feedback_experiment_path`, `lakebase_project`, `lakebase_host`, `doc_qa_backend`, `signoff_decision`, `prompt_iteration_ran`, `capstone_done`, plus list-valued sections for Genie Spaces, Vector Search indexes, Knowledge Assistants, custom `@function_tool` tools, and External MCP connections.
4. **Variant** — `variant_id` (one of `v1-sup-appkit`, `v2-serving-appkit`, `v3-agentapp-only`, `v4-agentapp-plus-appkit`, `v5-integrated-appkit`). Derived at `bootstrap` from `pathway` + `track`. Consumed by variant-specific skills to gate their applicability.
5. **Resources** — resolved from the PRD by `resolve_spec`. Contains a unified `tables[]` list (each with `kind: sql_warehouse | lakebase` discriminator), `knowledge_base_documents`, `genie_spaces`, `vector_search_indexes`, `dabs_bundle`, `sample_data`.
6. **UI** — resolved from the PRD by `resolve_spec`. Contains `description`, `personas`, `pages`, `overview_widgets`, `sql_files`, `user_journeys`.
7. **Agent** — resolved from the PRD by `resolve_spec`. First-class fields: `model`, `auth_mode` (`app` | `user` | `mixed`), `memory` (`none` | `session` | `long_term`). Content fields: `system_prompt`, `tone_persona`, `must_do`, `must_not_do`, `capabilities`, `reviewer_role`. Tool fields: `tools[]` (discriminated union with `kind: hosted | function | mcp`), `mcp_servers[]` (each with a `name` referenced by `kind: mcp` tools), `knowledge_base_backend`, `external_integrations`, `benchmark_seeds`.
8. **Governance** — resolved from the PRD by `resolve_spec`. Contains `scorer_suite`, `monitoring` (per-environment scorer+threshold config), `verification` (smoke + eval gate config).
9. **Spec Provenance** — stamp of when and how sections 4–8 were resolved. Contains `resolved_at`, `resolver_version`, `schema_version` (`"2.0"`), `prd_sha256`, `llm_endpoint`. Consumed by `retrospective.rollup` to detect PRD drift.
10. **Bootstrap Preflight** — written by `bootstrap` before the spec sections. Contains `workspace_url_normalized`, `workspace_url_was_placeholder`, `workspace_profile`, `workspace_host_auth_status`, `databricks_cli_version` + `databricks_cli_min_version`, `apps_quota` (current/max/free), `bundle_dev_mode_schema_prefix_detected`, `first_state_file_path`, `app_name_known_at_bootstrap`, and `verify_summary_semantics` (PASS/WARN/FAIL field names + `warning_policy`). See `references/spec-schema.md` § *Bootstrap Preflight* for normative halt rules.
11. **State File Set** — declares which state file(s) `enter` reads for prompts that span both an AppKit app and a separately authored agent. Contains `primary` and `secondary` (each with `path` + `owner`), `lookup_order`, and `conflict_policy` (`primary_wins` | `fail_on_conflict`). Pathways A, B, and pure-D runs leave `secondary` at `<pending>` — the block is required only when a prompt MUST read both files. See `references/spec-schema.md` § *State File Set*.
12. **Canonical Names** — pinned spellings for state-field aliases, env vars, jq paths, HTTP headers, MLflow Prompt Registry URI scheme + schema field, eval-dataset column names, label-schema namespace prefix, and file paths. The maps' direction is `<legacy_or_incorrect_name>: <canonical_name>`; a `null` value (e.g. `http_headers.x-forwarded-user-info: null`) means the name does not exist and any prompt that reads it is a bug. `enter` aliases reads through this registry; `state_contract_audit` extends its drift checks to flag legacy spellings and `null`-valued reads. See `references/spec-schema.md` § *Canonical Names*.
13. **State Overrides** — `state_overrides[]` is the only mechanism by which `enter` may proceed past a failed gate, prior-gate mismatch, failed `hard_assert`, failed `preflight_check`, or non-applicable pathway. Each entry is bounded by `expires_at`; expired entries are inert. Cross-session continuity is recorded here (with an evidence link), NOT in prose. Defaults to an empty list. See `references/spec-schema.md` § *State Overrides*.
14. **Deferred Actions** — `deferred_actions[]` is the canonical baseline of cross-prompt dependencies the workshop knows about up front (six seeded entries: `f2_grants_complete`, `prompt16_column_grounding`, `registered_prompt_runtime_consumption`, `eval_dataset_expected_response`, `labeling_session_dataset_enrichment`, `full_benchmark_candidate_reeval`). Each entry blocks every prompt role listed in `target_prompt_roles[]` until `divergence_check` evaluates true (or a `state_override` covers it). Workshops MAY add entries; they MUST NOT remove the seeds. See `references/spec-schema.md` § *Deferred Actions*.
15. **MLflow Eval Known Quality Issues** — `mlflow_eval_known_quality_issues[]` records evaluation traces with known unreliability (tool warnings, jq paths returning null, scorer floors not met, synthesized stand-ins). Each open entry blocks every prompt role listed in `target_prompt_roles_blocked[]`. Defaults to an empty list; entries are appended as issues surface. See `references/spec-schema.md` § *MLflow Eval Known Quality Issues*.
16. **Gate Load Bearing Checks** — `gate_load_bearing_checks[]` is the canonical list of verify-job and audit warning names that, when present, MUST block the gate (rather than soft-pass). Backs `bootstrap_preflight.verify_summary_semantics.warning_policy: block_if_load_bearing`. Bootstrap pre-populates the nine canonical names: `tool_warning`, `jq_path_returns_null`, `scorer_below_floor`, `dataset_coverage_below_floor`, `synthesized_stand_in`, `time_to_label_below_floor`, `open_deferred_action`, `open_known_quality_issue`, `bundle_validate_warning_load_bearing`. See `references/spec-schema.md` § *Gate Load Bearing Checks*.
17. **Productized Debts** — `productized_debts[]` records workarounds the workshop deliberately ships with, each carrying a `remove_when` predicate evaluated by `audit_debts`. Each entry has `name`, `introduced_at_prompt_role`, `remove_when`, `debt_lifted`, and an `audit_history[]` of `{audited_at, debt_lifted_evaluation, evaluator_evidence}` entries appended on every audit run. Bootstrap pre-populates five seeds: `workspace_sse_guardrail`, `mlflow_make_judge_aggregations_default`, `predict_fn_input_guardrail_sentinel`, `predict_fn_api_connection_sentinel`, `predict_fn_sql_table_not_found_sentinel`. Workshops MAY append additional debts; they MUST NOT remove the seeds. See `references/spec-schema.md` § *Productized Debts*.
18. **Preflight Check Registry** — `preflight_check_registry` is the canonical map of every named preflight check the workshop knows about. Each entry maps a check name to its `owner` (skill or prompt id) and `blocks_prompt_roles[]` (prompt roles whose `enter` MUST halt while the check has not been recorded as passing). Bootstrap pre-populates nine seeds: `workspace_url_not_placeholder`, `workspace_profile_matches_host`, `databricks_cli_min_version`, `databricks_apps_capacity`, `mlflow_tracing_sql_warehouse_id_present`, `predict_fn_signature_matches_runner`, `reflection_lm_large_context_probe`, `f2_grants_complete`, `lakebase_cold_start_retry_policy_present`. Workshops MAY append additional checks; they MUST NOT remove the seeds. The `reflection_lm_large_context_probe` check requires a synchronous ≥80k-character probe against the bound `llm_role_endpoints.reflection_lm.endpoint` before any 08b diff-summary or iteration helper call — a generic bootstrap audit pass is NOT sufficient. See `references/spec-schema.md` § *Preflight Check Registry*.
19. **Evaluation Runs Preflight** — `evaluation_runs_preflight` is the namespaced state block consumed by `preflight_check_registry.predict_fn_signature_matches_runner`. Owned by SDLC Skill 04 (`genai-agents/sdlc/04-evaluation-runs/SKILL.md`). Defaults at bootstrap: `predict_fn_signature_matches_runner: false`, `last_run_at: <pending>`. The boolean flips `true` once a Skill 04 run completes whose captured `mlflow_eval_predict_fn_signature` matches the runner-expected `(inputs: dict) -> str` or `(inputs: dict) -> dict` shape; a non-matching signature flips it back to `false`. Replaces the ad-hoc top-level `predict_fn_signature_matches_runner_status` enum seeded earlier in Phase 1.7. See `references/spec-schema.md` § *Evaluation Runs Preflight*.
20. **System Prompt Review** — `system_prompt_review` records the structured pre-eval audit of the agent's hand-authored system prompt. Defaults at bootstrap: `complete: false`, `reviewed_at: <pending>`, `reviewed_by: <pending>`, `must_do_worked_examples: []`, `must_not_do_worked_examples: []`. The two example arrays are populated by the prompt that maps to `first_scored_eval` (Prompt 7.20 in `Instructions.md`, Prompt 20d in `example/skyloyalty/WALKTHROUGH.md`, section `mlflow_agent_quality_judges` in `docs/02_seed_section_input_prompts.sql`). `enter` halts the first scored eval prompt unless `system_prompt_review.complete == true` AND `count(system_prompt_review.must_do_worked_examples) >= count(agent.must_do)` AND `count(system_prompt_review.must_not_do_worked_examples) >= count(agent.must_not_do)`. The `count()` builtin is the only divergence-check grammar extension introduced for this gate. See `references/spec-schema.md` § *System Prompt Review* and § *Divergence-check grammar extension: `count()`*.
21. **Skill Helper Resolutions** — `skill_helper_resolutions[]` records the concrete shape selected by `skill_helper_resolution` for every skill-prescribed helper contract the workshop probes. Each entry stamps `contract_name`, `selected_kind` (one of `import_path | function_signature | bundle_resource_schema | api_field_path | cli_field_path | cli_version_dependent_schema | inline_template_fallback`), `selected_value`, `probed_at`, and `fallback_used`. Defaults to an empty list; entries are appended (or replaced by `contract_name`) every time `skill_helper_resolution` runs. Consuming skills cite resolved helpers by canonical path `skill_helper_resolutions[contract_name='<name>'].selected_value`. See `references/spec-schema.md` § *Skill Helper Resolutions*.
22. **Per-Step Log** — one `## Prompt <N>` / `## Module <N>` / `## Phase <N.M>` section per completed prompt. Append-only. Skipped steps still get a section with `Gate: Skipped — N/A for pathway <X>`.

---

## Field Consumer Contract

Schema v2.0 replaces the prose "Field Consumers" table in [`references/spec-schema.md`](references/spec-schema.md) with a **machine-parseable** contract.

**Producer side.** `resolve_spec` emits the six spec sections (`## Variant`, `## Resources`, `## UI`, `## Agent`, `## Governance`, `## Spec Provenance`) as YAML blocks in the live state file. Leaf dotted paths (e.g. `ui.user_journeys`, `agent.model`, `agent.tools[].uc_function_name`, `governance.scorer_suite.guidelines`) are the unit of the contract.

**Consumer side.** Every skill that reads state **MUST** declare a `fields_read:` YAML list in its SKILL.md frontmatter. Example:

```yaml
---
name: appkit-scaffold
description: ...
fields_read:
  - ui.description
  - ui.personas
  - ui.pages
  - resources.tables[].kind
  - resources.tables[].table_name
---
```

- Wildcards are permitted: `ui.*` reads every leaf under `ui`. `agent.tools[].*` reads every sub-field of every tool entry.
- If the skill reads **nothing** from the spec, it MUST declare `fields_read: []` explicitly. Missing frontmatter = consumer-side drift error.

**Audit.** `retrospective.rollup` step 3 (§ *Spec drift* above) loads every known consumer skill's `fields_read:` list, flattens to a set, and compares against the set of leaves actually produced in the state file. Produced-but-never-read → stale resolver output. Read-but-never-produced → schema drift or typo in the consumer. Both halt the rollup.

**In-prose references.** Walkthroughs and `Instructions.md` may cite dotted paths in prose (e.g. "populate system prompt from `agent.system_prompt`"). These are **not** audited — only frontmatter `fields_read:` lists are.

---

## Pathway Applicability Matrix

`enter` consults this matrix to decide whether the current prompt runs or is skipped.

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

The same matrix is mirrored into the live state file at `bootstrap` so every `enter` call has it in context.

---

## Gate Rules

- **Build / modify prompts** (code edits, scaffolding, agent construction) MUST end with `Gate: Local testing passed`. No deployment-oriented prompt runs until this is true.
- **Infra / deploy / eval prompts** have their own success criterion as the gate (`Deployment RUNNING`, `Infrastructure healthy`, `Eval thresholds met`, `Lakebase endpoint active`, `Signoff APPROVED`, etc.).
- **Skipped prompts** record `Gate: Skipped — N/A for pathway <X>` and do not block downstream `require_prior_gate` checks that expect a non-skip gate (the next non-skipped prompt in the chain is what downstream prompts should point at).
- A prompt MUST NOT be marked complete if its verification fails — `exit` will refuse.

---

## Live vs Bootstrap Paths

| Moment | Path |
|--------|------|
| Canonical generalized template (committed, lives in this skill) | [`references/state-template.md`](references/state-template.md) |
| Bootstrap live file (before `$APP_NAME` / `$AGENT_NAME` is known) | `example/<use_case_slug>/.vibecoding-state.md` |
| Canonical live file — Pathways A, B, C | `<app_root>/.vibecoding-state.md` (= `<artifact_root>/<app_name>/.vibecoding-state.md`, the top-level app dir) |
| Canonical live file — Track A agent app (Pathways C / D) | `<agent_app_root>/.vibecoding-state.md` (= `<artifact_root>/<agent_app_name>/.vibecoding-state.md`, the top-level agent app dir) |
| Per-prompt retrospective file (live, gitignored) | `example/<use_case_slug>/retrospective.md` |
| Session rollup file (live, gitignored) | `example/<use_case_slug>/retrospective-rollup.md` |

Live state and retrospective files are gitignored. Only the two files under `references/` are committed.

---

## References

- [`references/state-template.md`](references/state-template.md) — canonical state-file template copied by `bootstrap`.
- [`references/spec-schema.md`](references/spec-schema.md) — schema v2.0 + Field Consumer Contract for Variant / Resources / UI / Agent / Governance / Provenance spec sections. Enforced by `resolve_spec` and audited by `retrospective.rollup`.
- [`references/resolver-prompt.md`](references/resolver-prompt.md) — LLM prompt + deterministic guards used by `resolve_spec`.
- [`references/retrospective-template.md`](references/retrospective-template.md) — per-prompt retro prompt + Session Rollup prompt.
- [`genai-agents/00-course-orchestrator/SKILL.md`](../../genai-agents/00-course-orchestrator/SKILL.md) — declares this skill as a runtime dependency.
- [`Instructions.md`](../../Instructions.md) and [`example/skyloyalty/WALKTHROUGH.md`](../../example/skyloyalty/WALKTHROUGH.md) — every prompt in these files invokes `enter` / `exit` from this skill and reads spec content by dotted path (`ui.*`, `agent.*`, `governance.*`, `resources.*`).
