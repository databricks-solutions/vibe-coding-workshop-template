# Retrospective Template — Generalized Workshop

This template lives inside the `vibecoding-state` skill so it travels with the runtime contract to any project that adopts the Instructions.md workshop.

Use it **once per prompt** executed during the workshop (count depends on pathway + track recorded in the live state file — `<app_root>/.vibecoding-state.md` for Pathways A/B/C, `<agent_app_root>/.vibecoding-state.md` for the Track A agent app on Pathways C/D, `<dp_bundle_root>/.vibecoding-state.md` for a pure data-product / lakehouse run). Run retrospectives **async after the full workshop completes** — do not interleave them with active prompts.

Paste the block below into a fresh Agent thread, replacing `<N>` and `<title>` with the prompt/module identifier and title you are reviewing. Point the agent at the state file, the retrospective file, and [`Instructions.md`](../../../Instructions.md) so it has the full context.

The output format is fixed so individual retros can be aggregated by the rollup prompt into a prioritized edit backlog.

---

## Handoff invariant (every summary, context-compaction, or thread handoff MUST record this)

The live `.vibecoding-state.md` file — NOT the chat summary — is the state store. Whenever a run is summarized, compacted, or handed to a fresh thread, the handoff MUST carry these five fields verbatim so the next thread can re-open the durable state instead of trusting prose:

| Field | Source |
|---|---|
| `state_file_path` | the canonical live file for this track: `<dp_bundle_root>/.vibecoding-state.md` (data-product), `<app_root>/.vibecoding-state.md` (apps), or `<agent_app_root>/.vibecoding-state.md` (agents) — never the temporary `example/…` path |
| `last_completed_prompt` | the `prompt_id` of the most recent `exit` that was confirmed by re-read |
| `last_gate` | the exact Gate string that `exit` recorded |
| `environment_capabilities` | the `## Environment Capabilities` block (incl. `lakehouse_default_catalog`, `client_context`) |
| `state file updated: yes/no` | whether the last step's `exit` actually appended to the live file and the write was verified by re-read |

If `state file updated: no`, the next thread MUST treat the run as **unverified** and re-run the last `exit` before advancing. A handoff that omits these fields is non-conformant.

---

## Per-Prompt Retrospective Prompt (copy this block)

> **Retrospective for Prompt `<N>` — `<title>`** (use case: `<use_case_slug>`)
>
> You are reviewing a single completed step of the `<use_case_slug>` workshop run. Your job is to identify concrete, actionable improvements to the walkthrough prompt, the referenced skills, the state-file schema, and the pathway/track applicability logic. Be critical. Do not sugarcoat. Do not propose improvements unless they are specific enough to act on.
>
> **Inputs available to you:**
> - The walkthrough prompt text at `Instructions.md`, Prompt `<N>`.
> - The state file at `<app_root>/.vibecoding-state.md` (Pathways A/B/C) or `<agent_app_root>/.vibecoding-state.md` (Track A agent app, Pathways C/D) — specifically the `## Prompt <N>` section plus any prior sections it depended on.
> - The `Workshop Choices` and `Pathway Applicability Matrix` in the same state file — these tell you whether this prompt should have executed at all for the chosen pathway/track.
> - The agent transcript for this step if provided; otherwise reconstruct from the state file's "Resolved issues / workarounds" and "Verification" notes.
>
> **Produce a Markdown block with exactly the headings shown below.** Append it as a new `## Prompt <N> — <title>` section in `example/<use_case_slug>/retrospective.md`. Do not add or rename headings. If a section has no findings, write `none`.
>
> ```markdown
> ## Prompt <N> — <title>
>
> **Reviewed:** <ISO timestamp>
> **Pathway:** <A | B | C | D>
> **Track (if applicable):** <A | B | C | n/a>
> **Outcome:** success | partial | failed | skipped-correctly | skipped-incorrectly
> **Duration (minutes):** <n>
> **Friction score (1–5, 5 = painful):** <n>
>
> ### Skills
> - **Invoked as required:** <list of skill paths>
> - **Should have been invoked but weren't:** <list, or "none">
> - **Invoked unnecessarily:** <list, or "none">
> - **Skill-level issues found:** <skill path → specific issue + proposed fix>
>
> ### State file hygiene
> - **Values read from state:** <keys>
> - **Values written to state:** <keys>
> - **Values the prompt had to guess (not in state, not derivable):** <list>
> - **Disambiguation questions asked of user:** <count; ideal = 0>
> - **State schema gaps (fields that should exist but don't):** <list>
>
> ### Prompt quality
> - **Ambiguous wording (quote phrase → why ambiguous):** <list>
> - **Missing context the prompt assumed:** <list>
> - **Redundant steps already handled by a prior prompt:** <list>
> - **Commands that failed on first try:** <list with error snippet>
> - **Recovery steps taken:** <list>
>
> ### Pathway / track applicability issues
> - **Did the prompt execute when it shouldn't have for this pathway/track?** yes | no
> - **Did the prompt skip something the chosen pathway/track needs?** yes | no
> - **If yes to either, the matrix/guard fix needed:** <specific field or check to add in Pathway Applicability Matrix or prompt preamble>
>
> ### Gate integrity
> - **Gate written in state file:** <exact string>
> - **Was the gate respected? (did we advance only after local test / verification passed?):** yes | no
> - **If no, what let us advance prematurely:** <explanation>
>
> ### Handoff to next prompt
> - **Values the next prompt needs:** <list>
> - **All present in state file?** yes | no
> - **If no, which are missing and how should they be captured:** <list>
> - **state_file_path:** <canonical live file path for this track>
> - **last_completed_prompt / last_gate:** <prompt_id> / <gate string>
> - **state file updated (exit appended + verified by re-read)?** yes | no
>
> ### Top 3 concrete improvements
> 1. <proposed new wording or structural change — be specific>
> 2. <...>
> 3. <...>
>
> ### Classification of improvements
> - **Fix in Instructions.md:** <bullet numbers from "Top 3" above>
> - **Fix in a skill file:** <skill path → bullet numbers>
> - **Fix in state-file schema / Pathway Applicability Matrix:** <bullet numbers>
> ```
>
> After appending the block to `example/<use_case_slug>/retrospective.md`, print back to the chat **only** the Friction score, Outcome, Pathway/track applicability verdict, and the Top 3 improvements. Do not summarize anything else.

---

## Session Rollup Prompt (run once, after all per-prompt retros are in `retrospective.md`)

> Read `example/<use_case_slug>/retrospective.md`. Produce a prioritized edit backlog grouped by fix destination. Write it to `example/<use_case_slug>/retrospective-rollup.md`.
>
> Structure:
>
> 1. **Instructions.md edits** — ranked by (friction score × frequency across prompts). For each item include: prompt number(s), the exact current wording (quoted), proposed new wording, and one-line rationale.
> 2. **Skill edits** — grouped by skill path. For each skill list the prompts that surfaced the issue, a one-line description, and the proposed change.
> 3. **State-file schema edits** — new fields to add, fields to rename, fields to remove, each with a one-line rationale.
> 4. **Pathway Applicability Matrix edits** — cells that were wrong for this run (prompt ran when it shouldn't, or was skipped when it shouldn't), each with a one-line rationale.
> 5. **Top disambiguation gaps** — any values that multiple prompts had to guess or ask the user for. These are the highest-leverage state-schema fixes.
> 6. **Gate violations** — any step where the gate was not respected. List per prompt with the specific premature-advance trigger.
> 7. **Spec drift (hard fail, must be section 7; HALT the rollup if any entry here is non-empty — do not proceed to sections 1–6 until drift is resolved):**
>    Run this check **before** any other section. The live state file conforms to schema v2.0 (see [`references/spec-schema.md`](spec-schema.md)). The producer (`resolve_spec`) emits six YAML blocks under `## Variant`, `## Resources`, `## UI`, `## Agent`, `## Governance`, `## Spec Provenance`. Every consumer skill declares which of those fields it reads via a machine-parseable `fields_read:` list in its frontmatter (dotted-path strings — see `skills/vibecoding-state/SKILL.md` § *Field Consumer Contract*). Do:
>    a. **PRD drift.** Compute `sha256` of the file at `## Workshop Choices → prd_path`; compare with `## Spec Provenance → prd_sha256`. Mismatch → list the old and new hashes. HALT.
>    b. **Schema version drift.** Read `## Spec Provenance → schema_version`. If ≠ `"2.0"`, emit: `"State file schema_version=<X> ≠ 2.0 — run scripts/migrate-spec-v1-to-v2.py before re-running rollup."` HALT.
>    c. **Producer / consumer contract drift.** Enumerate every dotted-path leaf under the four content sections (`resources`, `ui`, `agent`, `governance`) in the live state file — call this set `produced`. For every consumer skill in the repo (find them with `rg -l '^fields_read:' genai-agents/ apps_lakebase/skills/`), parse its frontmatter `fields_read:` list (expand wildcards like `ui.*` and `agent.tools[].*` to all matching leaves in the state file). Union these into `consumed`. Report:
>       - `produced − consumed` → fields emitted by the resolver that no skill declares reading. Each one is either a stale resolver output or a missing consumer declaration. HALT.
>       - `consumed − produced` → fields a skill declares reading that the resolver never emits. Each one is either a schema drift or a typo in the consumer skill. HALT.
>    d. **Unused resolved fields (non-blocking).** Optional pass: if a field in `produced ∩ consumed` was declared in `fields_read:` but the consumer skill never actually referenced it in any executed prompt this session, flag it as `info:` — not a halt, just a note in section 2 (Skill edits) of the backlog.
>    e. **Hardcoded leaks (non-blocking).** Grep every walkthrough + skill file the session touched for hardcoded strings that also appear in the state file (table names, persona names, tool names). Any hit = prose that should be replaced with a `fields_read:`-declared dotted-path reference. Flag in section 1 or 2 of the backlog.
>    Only if (a), (b), and (c) all pass does the rollup proceed to sections 1–6.
>
> Keep it terse. This is an edit backlog, not a narrative. Preserve priority ordering — the first item in each section is the one to fix next.

---

## Metrics to Watch Across the Retros

As the workshop matures, these should trend toward the target:

| Metric | Target | Why |
|---|---|---|
| Disambiguation questions asked per prompt | 0 | Every needed value should live in the state file or be auto-derivable. |
| Values guessed per prompt | 0 | Same as above — state file is authoritative. |
| Gate violations | 0 | Advancing past a failed build is the single highest-risk failure mode. |
| Pathway/track applicability errors | 0 | A prompt that runs for the wrong pathway (or skips the right one) is a matrix bug. |
| Median friction score | ≤ 2 | Higher means prompts are either ambiguous or missing context. |
| Skills invoked unnecessarily | 0 | Signals the prompt is over-scoped. |
| Skills that should have been invoked but weren't | 0 | Signals the prompt under-specifies required context. |
