---
name: 08b-prompt-handauthoring
description: >
  Default reusable MLflow workshop path for instruction-shaped prompt iteration.
  Hand-authored prompt revisions guided by failing-scorer rationales from the
  first scored eval, with full-dataset re-eval and alias-gated promotion. Use
  when Step 4 evaluation reveals specific prompt-related failure modes
  (guideline misses, missing structure, wrong tone) AND failure_shape is
  `instruction` AND there are no L1 scorer failures. Cheaper, more transparent,
  and lower-risk than automated optimization. SDLC Step 8b — runs AFTER Step 4.
  Do NOT use for L1 scorer failures (route to architecture review) or when the
  quality gap is tool/retrieval-shaped.
license: Apache-2.0
compatibility: "Requires Databricks workspace with MLflow >= 3.10.1 and Unity Catalog Prompt Registry. No GEPA / `optimize_prompts` dependency."
clients: [ide_cli, genie_code]
bundle_resource: none
deploy_verb: none
deploy_note: "Hand-authored prompt revisions re-registered + alias-gated in the UC Prompt Registry via the MLflow SDK; full-dataset re-eval on serverless. No bundle resource. Identical on both clients. See `skills/genie-code-environment`."
coverage: full
metadata:
  last_verified: "2026-04-15"
  volatility: medium
  upstream_sources: []
  author: "prashanth-subrahmanyam"
  version: "1.0.0"
  domain: "genai-agents"
  pipeline_position: "S8b"
  consumes: "registered_prompts, evaluation_dataset, scorers, predict_fn, agent_spec, llm_role_endpoints"
  produces: "prompt_iteration_ran, prompt_handauthoring_iterations, prompt_handauthoring_template_diff_summaries"
  grounded_in: "https://docs.databricks.com/aws/en/mlflow3/genai/prompt-version-mgmt/prompt-registry, https://docs.databricks.com/aws/en/mlflow3/genai/eval-monitor/evaluate-app, docs/retrospective/three-gap-followup.md"
---

# Hand-Authored Prompt Iteration (Default MLflow Workshop Path)

This is the **default** path for instruction-shaped prompt iteration in the reusable MLflow workshop. It produces hand-authored prompt revisions guided by failing-scorer rationales from the first scored eval, then validates them against the **full** evaluation dataset before promotion. It is intentionally cheap, transparent, and easy to roll back.

> **GEPA / automated optimization is NOT in the default flow.** If the prompt explicitly declares `prompt_iteration_strategy: gepa`, route to [08-prompt-optimization](../08-prompt-optimization/SKILL.md) instead. That skill owns the Databricks Agent Skills `databricks-mlflow-evaluation` upstream lineage for `optimize_prompts()` / GEPA guidance and is maintained as the optional advanced path.

---

## Do I Need This Skill?

Use 08b only when **all** of the following are true. Otherwise go back to the listed SDLC step.

| Check | If false → go to |
|-------|------------------|
| Prompt is registered in UC Prompt Registry with an alias (e.g. `@production`). | [01-prompt-registry](../01-prompt-registry/SKILL.md) |
| Evaluation dataset with ≥ 20 rows and expected facts/ids exists. | [02-evaluation-datasets](../02-evaluation-datasets/SKILL.md) |
| Scorers produce a numeric or boolean signal per row, with rationales. | [03-scorers-and-judges](../03-scorers-and-judges/SKILL.md) |
| First scored eval (`first_scored_eval` role) ran and recorded `failing_scorers_if_regressed`. | [04-evaluation-runs](../04-evaluation-runs/SKILL.md) |
| `failure_shape == "instruction"` (guidelines missed, wrong format, wrong tone), not a tool/retrieval gap. | Debug: [tracks/A-custom-agent-apps/08-debugging](../../tracks/A-custom-agent-apps/08-debugging/SKILL.md) |
| No L1 scorer failures (safety, PII, structural-output L1) in the failing set. | Architecture review — see "Refusal Conditions" below |

---

## Refusal Conditions

Refuse to run and surface a typed remediation hint when:

1. **`target_scorers` is empty.** There is nothing to iterate against. The first scored eval did not record any failing scorers, so a prompt change cannot be validated. Route the operator back to Step 4 (re-run eval) or to architecture review if the eval itself is misconfigured.
2. **`target_scorers` contains an L1 scorer failure.** L1 scorers (safety, PII, hard structural contracts) are not safe to iterate against with a prompt rewrite — a passing prompt that papers over an L1 failure can mask a regression. Route to architecture review (e.g., re-design the agent's tool contract, add input/output guardrails, change retrieval) rather than re-authoring the system prompt.
3. **`reflection_lm_large_context_probe` preflight fails.** The role-bound reflection model cannot summarize a representative diff payload. Without a working diff-summary path, hand-authoring becomes opaque and template diff summaries cannot be captured. Route the operator to bind a larger-context model to the `reflection_lm` role.

---

## Skill Parameters

| Param | Required | Description |
|-------|----------|-------------|
| `agent_spec_ref` | yes | Pointer to the live `AgentSpec` (e.g. `state://AgentSpec`). Used to resolve scorer names to definitions and read `governance.scorer_suite.l1_scorers`. |
| `prompt_ref` | yes | UC prompt URI to iterate on. Format: `prompts:/{uc_catalog}.{uc_agent_schema}.{prompt_name}@{alias}`. The schema field is `uc_agent_schema`, not `use_case_slug`. |
| `target_scorers` | yes | List of scorer names to improve. Read from the `failing_scorers_if_regressed` entry of the `first_scored_eval` step's `## Captured Resource IDs`. Must be non-empty. |
| `rerun_prompt_role` | yes | Role identifier of the eval prompt to re-run after each iteration (default: `"first_scored_eval"`). |
| `write_alias` | yes | Alias to write the candidate to (default: `"@staging"`). Never write directly to `@production`. |
| `promote_if` | yes | Promotion condition. Must be `"all_target_scorers_meet_or_beat_baseline_on_full_dataset"`. Holdout-based promotion is not supported in 08b. |
| `promote_from` | yes | Source alias to promote from (default: `"@staging"`). |
| `promote_to` | yes | Destination alias (default: `"@production"`). |
| `reflection_lm_role` | yes | Role identifier (default: `"reflection_lm"`) used to look up the reflection model in `state://llm_role_endpoints`. Used only for diff-summary generation, never for autonomous prompt rewriting. |
| `preflight_checks` | yes | Must include `"reflection_lm_large_context_probe"`. The skill aborts if any preflight fails. |
| `capture_into_state` | yes | Must include `"prompt_iteration_ran"`, `"prompt_handauthoring_iterations"`, `"prompt_handauthoring_template_diff_summaries"`. |

---

## The Hand-Authored Loop

This skill is **not** an autonomous optimizer. It runs a structured loop where every prompt change is authored by the operator (with LLM assistance for diff summaries) and validated against the full eval dataset. There is no inner search, no candidate scoring, and no reward signal feeding back into the LLM.

```
┌──────────────────────────────────────────────────────────────────┐
│ 1. Read failing_scorers_if_regressed from first_scored_eval      │
│ 2. Refuse if target_scorers empty OR has L1 failures             │
│ 3. Preflight: reflection_lm_large_context_probe                  │
│ 4. For each iteration (cap at 3 by default):                     │
│    a. Operator authors candidate prompt revision                 │
│    b. LLM-assisted diff summary (reflection_lm role)             │
│    c. Run full-dataset re-eval (NOT a holdout)                   │
│    d. Compare every target scorer mean to baseline               │
│    e. Capture template_diff_summary into state                   │
│ 5. Promote @staging → @production iff all target scorer means    │
│    meet or beat baseline; else leave @staging in place           │
└──────────────────────────────────────────────────────────────────┘
```

### Step 1 — Read failing scorers

Pull `failing_scorers_if_regressed` from the live state file's `first_scored_eval` `## Captured Resource IDs` block. This list is the input to `target_scorers`. Resolve each scorer name to its full definition via `agent_spec.governance.scorer_suite[*]`.

### Step 2 — Refuse on empty or L1 failures

Apply the refusal conditions above. Empty `target_scorers` and L1-classified failures are both routed out of this skill; do not proceed.

### Step 3 — Reflection LM preflight

Read `llm_role_endpoints[reflection_lm_role].endpoint` from state. Run the `reflection_lm_large_context_probe` preflight (synthetic 80k- and 150k-character probe payloads). Abort with a typed remediation hint if either probe fails — diff summaries cannot be captured against a too-small-context model, and silent truncation would corrupt the iteration record.

### Step 4 — Author candidate prompt revisions

For each iteration:

1. The operator hand-authors a candidate revision to the prompt body. The reflection LM is used **only** to produce a structured diff summary (what guidelines were added, what tone constraints were tightened, what examples were inserted). It is not used to autonomously generate or score candidate prompts.
2. Register the candidate as a new prompt version under the same UC `name`.
3. Set the `write_alias` (e.g. `@staging`) to the new version.
4. Run the eval prompt identified by `rerun_prompt_role` against the **full evaluation dataset** — not a holdout, not a sample. Holdout splits are explicitly out of scope: the dataset is the canonical contract and we re-evaluate the entire thing each iteration.
5. Capture an iteration record: candidate version number, target-scorer means before/after, and the LLM-generated `template_diff_summary` string.

Default iteration cap is 3. After 3 iterations without all target scorer means meeting or beating baseline, exit with `iteration_did_not_beat_baseline` and leave `@production` untouched.

### Step 5 — Promote (or don't)

Promote `@staging → @production` **only if every target scorer mean meets or beats the baseline mean on the full-dataset re-eval**. A single regressed target scorer mean blocks promotion. Partial wins are not promoted; the operator can choose to keep `@staging` for further iteration or revert.

When promotion is skipped, capture the reason and the per-scorer means in the iteration record so the next operator can pick up where this one left off.

---

## State Capture Contract

Capture the following into `## Captured Resource IDs` of the calling prompt's state section:

| Field | Type | Description |
|-------|------|-------------|
| `prompt_iteration_ran` | bool | `true` if at least one iteration ran (regardless of promotion outcome). |
| `prompt_handauthoring_iterations` | list of dicts | One entry per iteration: `{version, target_scorer_means_before, target_scorer_means_after, promoted}`. |
| `prompt_handauthoring_template_diff_summaries` | list of strings | Reflection-LM-generated structured diff summaries, one per iteration. |

The state-file capture is the durable record of what was hand-authored and why. Do not collapse iterations into a single summary.

---

## No External Model Fallback

This skill **never falls back to Anthropic, OpenAI, or any BYO external model**. The `reflection_lm` role is bound to a workspace-resident endpoint (typically `databricks-claude-sonnet-4-6` or equivalent) via `llm_role_endpoints` in state. If that endpoint is unavailable or the preflight fails, the skill aborts — it does not silently retry against an external provider. Workspace policy and data residency requirements forbid the fallback path.

---

## Validation Checklist

- [ ] First scored eval has run and recorded `failing_scorers_if_regressed` and `failure_shape`.
- [ ] `failure_shape == "instruction"` and there are no L1 scorer failures in `target_scorers`.
- [ ] `prompt_ref` resolves via `prompts:/{uc_catalog}.{uc_agent_schema}.<name>@<alias>` (note: `uc_agent_schema`, not `use_case_slug`).
- [ ] `reflection_lm_large_context_probe` preflight passed (80k + 150k payloads).
- [ ] Re-eval ran on the full dataset, not a holdout split.
- [ ] Each iteration's `template_diff_summary` was captured into state.
- [ ] Promotion happened **only** when every target scorer mean met or beat baseline.
- [ ] `prompt_iteration_ran`, `prompt_handauthoring_iterations`, and `prompt_handauthoring_template_diff_summaries` are present in `## Captured Resource IDs`.
- [ ] No call was made to `mlflow.genai.optimize_prompts()` or `GepaPromptOptimizer`.
- [ ] No call was made to an external (non-Databricks-workspace) model serving endpoint.

---

## Do's and Don'ts

|  | Do | Don't |
|---|---|---|
| **When** | Run only after `first_scored_eval` shows a specific scorer below threshold AND `failure_shape == instruction`. | Use as the first pass to "make the agent good." |
| **Target scorers** | Read `target_scorers` from `failing_scorers_if_regressed`; refuse if empty or contains L1 failures. | Iterate against an arbitrary scorer subset chosen by the operator. |
| **Re-eval split** | Re-evaluate against the **full** dataset every iteration. | Use a held-out split — promotion is gated on full-dataset means. |
| **Reflection LM** | Use only for diff summaries; resolve via `llm_role_endpoints[reflection_lm].endpoint`. | Use the reflection LM to autonomously rewrite the prompt. |
| **Promotion** | Promote `@staging → @production` only if every target scorer mean meets or beats baseline. | Promote on a single-scorer win; promote on a partial improvement. |
| **External fallback** | Stay inside the workspace's bound endpoints. | Fall back to Anthropic / OpenAI / any BYO external model. |
| **Iteration cap** | Cap at 3 iterations by default; surface "did not beat baseline" exit on cap. | Loop indefinitely or exceed the cap silently. |

---

## Related Skills

- [08-prompt-optimization](../08-prompt-optimization/SKILL.md) — optional/advanced GEPA path, only when the prompt declares `prompt_iteration_strategy: gepa`.
- [01-prompt-registry](../01-prompt-registry/SKILL.md) — prompt registration prerequisite.
- [03-scorers-and-judges](../03-scorers-and-judges/SKILL.md) — scorer suite (including L1 classification).
- [04-evaluation-runs](../04-evaluation-runs/SKILL.md) — first scored eval and re-eval mechanics.

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-04-26 | Initial skill: default MLflow workshop path for instruction-shaped prompt iteration. Hand-authored loop, full-dataset re-eval, refusal on empty `target_scorers` or L1 failures, `reflection_lm_large_context_probe` preflight, no external-model fallback. |
