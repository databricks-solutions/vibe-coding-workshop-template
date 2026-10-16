# genie-gate-absolute-dedupe — plan r0.1 (2026-10-16; critic ACCEPT r1 + X5)

repo=template · base origin/feature/genie-code-mcp-integration (759a14e; == 3f6ba0a + #23 + #24)
PR plan path: retrospectives/plans/genie-code-integration/2026-10-16-genie-gate-absolute-dedupe.md
Status: PLAN ONLY. Build only after the human signs (D-205). No lock change in this task without a signed row.

## Problem (evidence)
- The absolute audit gate (`scripts/genie_gate.py` `check_audit` → `current_counts`, :66-88) runs
  `audit_genie_compat.scan()` over the whole template tree (`ROOTS=["."]`, `TEXT_EXT` includes `.sql` and `.md`,
  audit_genie_compat.py:41-58). App seed text reaches it only through whatever happens to sit in the
  git-ignored `apps_lakebase/prompts/` tree: the raw seed `02_seed_section_input_prompts.sql` (every version),
  `sections/*.md` extracted from it, and generated `NN-*.md` / `NN-*.sql`.
- So one seed row is counted up to three times (raw `.sql` + section file + generated files), and superseded
  versions are counted next to their replacement. That is the D-61 double count behind the three
  `apps_lakebase::` overages left after #23 (APP_DEPLOY 1697 → 1783/1857, GENIE_RESOURCE 8 → 22,
  LOCAL_AUTH 76 → 94/99; the two numbers differ by whether superseded rows were in the tree).
- The result depends on the operator's local, untracked tree: in `--app-repo` mode (#24) the sections live in a temp
  dir outside REPO_ROOT, so the absolute audit sees NO app seed text at all.
- The per-PR diff gate (`FORGE/tools/genie_gate_diff.py` `served_seed`, :75-104) already drops superseded and
  inactive rows (highest active version per (section_tag, coding_assistant), as routes.py serves). It still
  counts the served raw seed AND the sections, but symmetrically on base and head, so its deltas are right.

## Change (one rule: each served seed row counted once, from its section file)
In `scripts/genie_gate.py` only (template trunk file; charter exception named here: reason = the absolute
measurement is wrong by construction; reversal = revert the PR):
1. `current_counts()` excludes from the scan every file under `apps_lakebase/prompts/` (raw seed, NN-* generated
   files, local sections). The template's own text elsewhere in `apps_lakebase/` is still scanned unchanged.
2. It then adds the app seed exactly once: the section files extracted from the SERVED seed (same reduction as
   `served_seed`: drop `is_active = false` and versions below the highest active version per
   (section_tag, coding_assistant); ties all kept), each flagged line attributed to area `apps_lakebase`.
   Source of the seed: `--app-repo PATH` / `APP_REPO` (temp dir, as #24) or, if absent, the local
   `apps_lakebase/prompts/02_seed_section_input_prompts.sql` reduced the same way. If neither exists, the
   absolute audit prints that app seed text was NOT measured and the exact `--app-repo` command (no silent zero).
3. The served-seed reduction is implemented in genie_gate.py itself (the template cannot import FORGE). It must
   give the same dropped-row list as `genie_gate_diff.served_seed` on the same seed (test + proof below).
4. Note (critic e): `current_counts()` is also what `--update-baseline` writes (genie_gate.py:795, check_audit :114).
   After this PR an `--update-baseline` run would write the deduped counts. Intended; the PR body says so, and
   nobody runs `--update-baseline` in this task (re-locks only per signed row).
5. Implementation detail (critic c): the served-seed reduction uses the copied tooling's `_seed_parser`
   (`find_blocks` → input_id/section_tag; `extract_sql_strings` → coding_assistant/version/is_active), imported
   from the temp prompts dir, as genie_gate_diff.py:86-94 does.
6. Unchanged: the scorer (`audit_genie_compat.py`), PATTERNS, RULE_10_SANCTIONED, the baseline file, every fork
   check, the round-trip report, local-mode behaviour of all non-audit checks, `--update-baseline` semantics.

## Measurement (the deliverable the human asked for)
Each run in a NEW folder `FORGE/work/scratch/genie-gate-absolute-dedupe-<label>/` (never delete or reset a folder;
D-193). App seed = app `7e2397a` (byte-identical to the current app head 5457216 for db/; state it).
- M1 BEFORE at template 3f6ba0a, measured the way #23 measured (raw seed + sections in the worktree tree).
- M2 BEFORE at template 759a14e (current head), same way.
- M3 AFTER at the PR head: new rule.
For each: total, every by_area_class count, and, per key, lock → count → over/under.
Report table "locks over after dedupe" and "locks now slack by > 10%" (a lock far above its count hides
regressions). Propose re-lock rows for BOTH directions, each marked AWAITING HUMAN SIGNATURE; apply none.

## Acceptance
- A1 scope: only `scripts/genie_gate.py` + the plan file. The template has no pytest suite, so each check below is
  a runnable command with its output pasted in the PR body.
- A2 served-seed reduction equals genie_gate_diff.served_seed's dropped list on seed 7e2397a (paste both).
- A3 each served row counted once: for 5 sampled rows, the count of a flagged line equals its occurrences in that
  row's section file (not ×2/×3).
- A4 `--app-repo` and local mode give identical audit counts from the same seed.
- A5 no app seed → explicit "not measured" message, gate does not report a pass based on zero app lines.
- A6 fork-check output and round-trip report byte-identical to base (diff of outputs pasted).
- A7 genie_gate_diff.py (forge tool) on base 759a14e vs PR head, app seed 7e2397a both sides: exit 0, fork
  findings unchanged (the diff gate is independent of this change; proves no prompt text moved).
- A8 baseline JSON byte-identical to base.
- A9 no writes under TPL or APP; temp dirs removed; worktrees removed (D-199).

## Tampers
- X1 re-include `apps_lakebase/prompts/*.sql` in the scan → A3 red (counts double).
- X2 skip the superseded-row reduction → A2 red (dropped list differs; superseded row 942 etc. counted).
- X3 make "no app seed" count as zero silently → A5 red.
- X4 attribute section lines to `(root)` instead of `apps_lakebase` → A4/area table red.
- X5 (critic) edit any value in `scripts/genie_gate_baseline.json` → A8 red.

## Out of scope (record only)
- genie_gate_diff.py's symmetric raw+section double count (forge tool; human's). If wanted, a Part-B-style diff:
  add `"02_seed_section_input_prompts.sql"` handling so only sections are audited. Listed, not applied.
- Absolute-gate fork failures at base (activation_reverse_sync parity, gaccel_productionize deploy-fork,
  state persistence) and prompt-tooling-roundtrip-fix.

## Questions for sign-off
- Q1 count from section files (proposed) or from the served raw seed? Sections = what the fork checks read and
  what a learner's prompt body is; raw seed lines include SQL quoting (`''`) that can change a line's text.
- Q2 slack locks: propose tightening locks that end far above the new count, or leave tightening for later?

## SIGNED (human, 2026-10-16, D-208) — r1; these rulings override anything above
- Q1: count from the SECTION FILES of the served rows only (newest active version per (section_tag,
  coding_assistant); ties all kept), PLUS `user_trigger_prompt` of the same served rows, read from the seed with the
  copied tooling's `_seed_parser`. Reason: the extractor never writes user_trigger_prompt into sections (118 of the
  143 round-trip hunks), so a sections-only count would silently stop auditing learner-facing trigger text.
  Trigger lines are scanned with the same scorer (audit_genie_compat PATTERNS / RULE_10_SANCTIONED) and attributed to
  area `apps_lakebase`.
- Build report MUST show:
  - per area::class: lines from section bodies vs lines from triggers (two columns + total);
  - served-row count == number of section files produced, including the 12 Insights rows (301–304, 320, 321,
    1301–1304, 1320, 1321); if they differ, STOP and report the missing/extra rows.
- Q2: YES, proposals only. List every lock whose new count is ≥ 5 lines AND ≥ 10% below the lock as a
  "tighten <key> <lock> → <N>" row, AWAITING HUMAN SIGNATURE, next to the "over lock" rows. No lock changed in this PR.
- No app seed available: the `apps_lakebase::` area prints `SKIP` with the exact `--app-repo` command
  (`python3 scripts/genie_gate.py --app-repo /path/to/vibe-coding-workshop-app`) and counts nothing for app seed text;
  the audit must never PASS silently on a zero app count (tamper X3 covers it). The template's own non-prompts
  `apps_lakebase/` files are still scanned as today.
- `--update-baseline` is never run in this task. Tampers X1–X5 as written, plus:
  - X6 drop the trigger read → body/trigger table shows 0 trigger lines and the trigger acceptance check (A10) red.
  - X7 count superseded triggers too → A2/A10 red.
- New acceptance A10: for 3 sampled served rows with a non-empty user_trigger_prompt containing a flagged line,
  the flagged line is counted once (and not at all for a superseded version of the same prompt).
- prompt-tooling-roundtrip-fix (later) would let this drop the separate trigger read; note only.
