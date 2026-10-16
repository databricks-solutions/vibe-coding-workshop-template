# prompt-tooling-tracked — plan r1 SIGNED (2026-10-15; r0 + critic r1 ACCEPT + human sign-off D-196)

One plan, three parts, in order: **A** (APP PR, merge only) → **B** (forge tool change, applied by the HUMAN) →
**C** (TPL PR, merge only; ships in the next small TPL RC). Plan → critic → human sign-off before any build.
Commit this plan unchanged in each PR: APP `docs/superpowers/plans/2026-10-15-prompt-tooling-tracked.md`;
TPL `retrospectives/plans/genie-code-integration/2026-10-15-prompt-tooling-tracked.md`. Decisions: D-61, D-76,
D-146, D-169, D-194.

## Problem (human, D-194)
The prompt tooling exists only as git-ignored files in the human's TPL checkout (`TPL/apps_lakebase/prompts/`,
ignored since 5cebe54; TPL `.gitignore:96`). `tools/genie_gate_diff.py:44` copies it from there
(`TOOLING = TEMPLATE / "apps_lakebase" / "prompts"`), so the gate isn't reproducible elsewhere. Its `sections/`
and seed snapshots are stale (26 Sep). Its write-back scripts would overwrite the APP seed with 26-Sep text. TPL's
`scripts/genie_gate.py` SKIPs its fork checks in a clean clone (`:138`, `:178-181`, `:253-256`, `:333-336`).
Backup: `~/Backups/template-apps_lakebase-prompts-2026-10-15.tgz`. **TPL/apps_lakebase/prompts is read-only for
every role: never write there** (run Python with `PYTHONDONTWRITEBYTECODE=1` when importing from it, so no
`__pycache__` is written).

## Source inventory (lead, read-only, 2026-10-15)
`TPL/apps_lakebase/prompts/`: `_seed_parser.py`, `extract_contract_baseline.py`, `extract_sql_blocks.py`,
`extract_to_markdown.py`, `gen_fork_contract_baseline.py`, `generate_standalone_md.py`, `lint_section_prompts.py`,
`replace_inserts.py`, `splice_genie_to_app_seed.py`, `sync_markdown_to_seed.py`; `_templates/`
(`contract_baseline.json`, `fork_template.md`, `section_template.md`, `style_guide.md`); `tests/`
(`test_lint_section_prompts.py`, `fixtures/lint/`); plus untracked outputs NOT to copy: `sections/` (136),
`02_seed_section_input_prompts.sql`, `seed.sql`, `NN-*.md`/`NN-*.sql` (00-…05-), `__pycache__/`.
Write sites (lead grep `write_text`): seed writers `replace_inserts.py:157`, `splice_genie_to_app_seed.py:189`,
`sync_markdown_to_seed.py:375`; non-seed writers `extract_to_markdown.py:140,:176` (sections),
`extract_sql_blocks.py:47`, `generate_standalone_md.py:146` (generated md/sql),
`extract_contract_baseline.py:149` and `gen_fork_contract_baseline.py:183` (write `_templates/contract_baseline.json`).
Path defaults are `Path(__file__).parent`-relative (`extract_to_markdown.py:100`, `replace_inserts.py:105`,
`splice_genie_to_app_seed.py:103`, `sync_markdown_to_seed.py:279`, `_seed_parser.py:233`, …).

## Part A — APP PR into `feature/genie-code-mcp-integration`
Worktree from APP integration head (7e2397a or later at dispatch).
1. Add `scripts/prompt_tooling/` with every `*.py` above and `_templates/` copied byte-for-byte from TPL. The PR body
   lists each file's sha256 at source and destination (identical except files changed in steps 3–4, which show the
   diff). **Q1:** also copy `tests/` (`test_lint_section_prompts.py` + `fixtures/`)? Lead recommends YES: genie_gate_diff
   copies the whole tooling dir into the TPL worktree today, so `tests/` is part of what the audit scans (equivalence),
   and it tests the lint script.
2. Do NOT add `sections/`, seed snapshots (`02_seed_section_input_prompts.sql`, `seed.sql`), generated `NN-*.md` /
   `NN-*.sql`, or `__pycache__/`. Add `.gitignore` entries for `scripts/prompt_tooling/sections/`, the seed snapshot
   names and `NN-*` outputs under `scripts/prompt_tooling/`, so running the tooling in place leaves `git status` clean.
3. **Guard every seed write-back path** (`replace_inserts.py`, `splice_genie_to_app_seed.py`, `sync_markdown_to_seed.py`,
   and any other script the implementer finds that writes a seed file): the CLI entry point refuses by default
   (non-zero exit, no write) with: "Seed edits go through builders (e.g. scripts/insights_prompts/build_rows.py) and
   reviewed PRs. Re-run with --i-know-this-overwrites-the-seed to bypass." The flag name is the only bypass (no env var).
   Library functions (`parse_markdown`, `_seed_parser.*`, other parsers) stay importable and byte-unchanged.
   Non-seed writers (sections, generated md/sql, `_templates/contract_baseline.json`): unguarded, but must only write
   under `scripts/prompt_tooling/` or an explicit `--out`; list them in the README.
4. **Default paths:** keep `Path(__file__).parent`-relative defaults working exactly as today (so a copy of the folder
   placed elsewhere — genie_gate_diff's mode — behaves byte-identically). Only where a script cannot find its seed in
   its own folder, fall back to the APP seed `../../db/lakebase/dml_seed/02_seed_section_input_prompts.sql`, read-only.
   List every changed default. Prefer adding `--seed PATH` / `--out PATH` options over changing defaults.
5. `scripts/prompt_tooling/README.md`: purpose, the source-of-truth rule (APP seed only), how to regenerate sections,
   the guarded scripts and their flag, the backup location. **Note for Part B:** genie_gate_diff copies the folder into
   the TPL worktree's `apps_lakebase/prompts/`, where the audit scans `.md` files; the README must therefore be
   excluded by Part B's ignore patterns (see Part B) or it changes audit counts.
6. Tests in `tests/workshop/test_prompt_tooling.py` (canonical suite): extracting sections from the current APP seed
   into a temp dir works (count of INSERT blocks = count of sections); `parse_markdown` round-trips a generated
   section; each guarded script refuses without the flag (exit ≠ 0, seed file bytes unchanged) and writes only to a
   temp copy with the flag; nothing is written under TPL (assert TPL tooling dir mtime/listing unchanged, or never
   referenced: grep the folder for the TPL path → 0 hits).
7. **Equivalence proof:** run `tools/genie_gate_diff.py` on one pair — `--base-ref 3f6ba0a --base-seed <APP de70b96 seed>
   --head-seed <APP 7e2397a seed>` — twice, each in a NEW scratch folder under `FORGE/work/scratch/` (never delete or
   reset): (i) as shipped (TOOLING = TPL), (ii) with TOOLING pointed at the PR worktree's `scripts/prompt_tooling`
   WITHOUT editing the forge tool: `PYTHONDONTWRITEBYTECODE=1 python3 -c` importing `tools/genie_gate_diff.py`,
   setting `ggd.TOOLING`, and calling its `main` with the same arguments (critic: confirm `main` accepts argv, else
   name the exact invocation). Paste both outputs.
   **Q2 (expected difference):** the TPL folder also holds generated `NN-*.md` files that genie_gate_diff copies in
   today (its ignore patterns skip only `sections`, `__pycache__`, `*.sql`), and the audit counts them. The PR folder
   has none, so the absolute "counted audit lines X -> Y" numbers will drop by the same amount on both sides while
   the delta, the fixed/new lines and the fork findings stay identical. Proposed acceptance: identical except those
   absolute counts, with the difference attributed line by line to the `NN-*.md` files (equal on base and head).
   Alternative: human requires byte-identical output → Part B also ignores `NN-*.md`, and (ii) is compared to a run (i)
   with the same ignore. The human picks.

Acceptance A-A: files ⊆ {`scripts/prompt_tooling/**` (no excluded outputs), `.gitignore`,
`tests/workshop/test_prompt_tooling.py`, the plan, `docs/superpowers/decision-log.md` (D-190…D-194)}; sha256 table;
guards proven; canonical suite ≥ 2120 passed / 0 failed + root 10/0 (D-190 floor 2130 combined); equivalence outputs
pasted with Q2 rule applied. No trunk file. Tampers: T-A1 remove one guard → its refusal test red; T-A2 make a parser
change one byte → round-trip test red; T-A3 point a default at TPL → the "no TPL path" test red.

## Part B — forge tool change (applied by the HUMAN; no role edits forge tools)
Exact diff for `tools/genie_gate_diff.py` (after Part A merges and the APP checkout holds `scripts/prompt_tooling`):
```diff
@@ docstring (:7-10)
-`apps_lakebase/prompts/sections/`, which the template git-ignores; the deployed
-prompt bodies are the APP repo's seed. So each side of the diff is a throwaway
-template worktree at a ref, with the local prompt tooling copied in and the
-sections extracted from an app seed.
+`apps_lakebase/prompts/sections/`, which the template git-ignores; the deployed
+prompt bodies are the APP repo's seed. So each side of the diff is a throwaway
+template worktree at a ref, with the APP repo's scripts/prompt_tooling copied in
+and the sections extracted from an app seed.
@@ :43-44
 TEMPLATE = Path("/Users/prashanth.subrahmanyam/Projects/vibe-coding-workshop-template")
-TOOLING = TEMPLATE / "apps_lakebase" / "prompts"
+APP = Path("/Users/prashanth.subrahmanyam/Projects/vibe-coding-workshop-app/vibe-coding-workshop-app")
+TOOLING = APP / "scripts" / "prompt_tooling"
@@ _add_worktree (:69-70)
     shutil.copytree(TOOLING, path / "apps_lakebase" / "prompts", dirs_exist_ok=True,
-                    ignore=shutil.ignore_patterns("sections", "__pycache__", "*.sql"))
+                    ignore=shutil.ignore_patterns("sections", "__pycache__", "*.sql", "README.md"))
@@ main (:212-213)
     if not (TOOLING / "extract_to_markdown.py").is_file():
-        print(f"template prompt tooling not found under {TOOLING}", file=sys.stderr)
+        print(f"app prompt tooling not found under {TOOLING} (needs APP with scripts/prompt_tooling)", file=sys.stderr)
         return 2
```
(+ `"[0-9][0-9]-*.md"` in the ignore patterns if the human picks the Q2 alternative.)
Matching `FORGE/tests/test_genie_gate_diff.py` change:
```diff
@@ :137-138
 needs_tooling = pytest.mark.skipif(not (ggd.TOOLING / "_seed_parser.py").is_file(),
-                                   reason="template prompt tooling not on this machine")
+                                   reason="APP scripts/prompt_tooling not on this machine")
+
+
+def test_tooling_comes_from_the_app_repo_not_the_template():
+    assert ggd.TOOLING == ggd.APP / "scripts" / "prompt_tooling"
+    assert ggd.TEMPLATE not in ggd.TOOLING.parents
```
The human applies it, runs the forge suite, and updates the definition fingerprint if needed. Line numbers verified at
FORGE HEAD on 2026-10-15; the critic re-checks them.

## Part C — TPL PR into TPL `feature/genie-code-mcp-integration` (after B)
Worktree from TPL integration head (3f6ba0a, or tpl-gate-overages-followup's merge if it has merged first; take the
newer). Trunk exception: `scripts/genie_gate.py` (TPL trunk file), reason D-194, reversal = revert this PR.
1. `scripts/genie_gate.py`: when `apps_lakebase/prompts/sections` is absent, accept `--app-repo PATH` (or `APP_REPO`
   env; the flag wins). Then: copy the seed `PATH/db/lakebase/dml_seed/02_seed_section_input_prompts.sql` and the
   tooling `PATH/scripts/prompt_tooling` into a temp dir (`tempfile.mkdtemp`), run its `extract_to_markdown.py`
   there, and run every fork check (`:175-…`, `:251-…`, `:332-…`) against that temp `sections/`, importing
   `parse_markdown` from the temp tooling. Never write into PATH or into the TPL tree; remove the temp dir at exit.
   **Critic:** should the extract use the served-rows reduction like genie_gate_diff (D-61), or the raw seed as the
   local sections tree does today? Proposal: raw seed (matches today's local behaviour, which the proof compares to);
   the dedupe question belongs to the queued genie-gate-absolute-dedupe.
2. With neither present: keep the SKIP, and print the exact command:
   `python3 scripts/genie_gate.py --skip-roundtrip --app-repo /path/to/vibe-coding-workshop-app`.
3. `.gitignore` `apps_lakebase/prompts/` entry unchanged.
4. **Proof:** fork-check output with `--app-repo <APP at A's merge>` equals the output from a local sections tree
   regenerated from the same seed with the same tooling (built in a NEW scratch folder, not in TPL). Paste both.
5. Tests (if TPL has none, a script-level check in the PR body): `--app-repo` with a missing seed → clear error; with
   neither → SKIP + the command line printed; temp dir removed.
Acceptance A-C: files ⊆ {`scripts/genie_gate.py`, the plan}; proof outputs identical; `tools/genie_gate_diff.py`
(after B) base → head exit 0 with no new findings; SKIP message exact. Tampers: T-C1 write the temp dir under TPL →
the "no TPL write" check red; T-C2 drop one fork check from the --app-repo path → proof differs.

## Release
A: reviewer + gatekeeper, merge only. B: the human. C: reviewer + gatekeeper, merge only; then into the next small TPL
RC (integration → TPL main), one review + gate, the human merges. No forge deploys; no merge to main.

## Questions for the human (sign-off)
- Q1 Copy `tests/` too (lead: yes).
- Q2 Equivalence rule: identical except the absolute counts explained by the TPL folder's `NN-*.md` (lead), or
  byte-identical with `NN-*.md` ignored in Part B.

## SIGNED (human, 2026-10-15; D-196; critic r1 ACCEPT) — overrides earlier sections where they differ

- **Q1 YES:** Part A also copies `tests/` (`test_lint_section_prompts.py` + `fixtures/`), byte-for-byte, in the sha256 table.
- **Q2 (extended):** equivalence run (ii) sets `ggd.TOOLING` to the PR's `scripts/prompt_tooling` and runs WITHOUT Part B's
  ignore list (the shipped tool). Invocation (critic (c)): `PYTHONDONTWRITEBYTECODE=1 python3 -c` with
  `sys.path.insert(0, FORGE/tools)`, `import genie_gate_diff as ggd`, `ggd.TOOLING = Path(...)`,
  `sys.argv = ["genie_gate_diff", "--base-ref", "3f6ba0a", "--base-seed", <de70b96 seed>, "--head-seed", <7e2397a seed>, "--work", <new scratch>]`,
  `sys.exit(ggd.main())`. Expected differences vs run (i): the TPL folder's `NN-*.md` lines missing and the
  `scripts/prompt_tooling/README.md` lines added, each attributed line by line and equal on base and head. The change
  ("X -> Y" delta), the fixed/new lines and the fork findings must be identical. Anything else → STOP and report.
- **Part A guard:** `--dry-run` (and any mode that writes nothing) must NOT be refused; only real seed writes need
  `--i-know-this-overwrites-the-seed`. Extra test: `sync_markdown_to_seed.py --dry-run` exits 0 without the flag and the
  seed bytes are unchanged. Tamper **T-A4:** make the guard also refuse `--dry-run` → that test turns red.
- **Part B (human applies; diff updated):** the ignore list becomes
  ```diff
  -                    ignore=shutil.ignore_patterns("sections", "__pycache__", "*.sql"))
  +                    ignore=shutil.ignore_patterns("sections", "__pycache__", "*.sql", "README.md",
  +                                                  "[0-9][0-9]-*.md"))
  ```
  (outputs generated in place must never be audited); the rest of the Part B diff as above.
- **Part C round-trip: YES.** In `--app-repo` mode `check_roundtrip` (TPL `scripts/genie_gate.py:138`) runs
  `sync_markdown_to_seed.py --dry-run` in the temp dir against the temp seed copy; it must report
  "No differences detected". The printed SKIP command drops `--skip-roundtrip`:
  `python3 scripts/genie_gate.py --app-repo /path/to/vibe-coding-workshop-app`. Part C covers all six SKIP branches
  (`:138`, `:178`, `:253`, `:333`, `:405`, `:515`); `check_state_persistence_discipline` keeps reading TPL
  `skills/vibecoding-state/SKILL.md` from the TPL tree.
- **Part C seed:** raw seed, as proposed; dedupe stays with genie-gate-absolute-dedupe.
- **Order:** A (merge only) → lead tells the human → B (human applies + forge suite) → C (merge only) → next small TPL RC.
- Tampers in force: T-A1..T-A4, T-B1 (critic), T-C1, T-C2.

## Part C dispatch notes (2026-10-15; D-197, D-198) — override earlier Part C text where they differ

- Part A merged: APP 5457216 (`scripts/prompt_tooling/` present). Part B applied by the human (forge suite 314/0/0;
  fingerprint unchanged). Part C base: TPL `feature/genie-code-mcp-integration` = eb078a3 (#23 merged).
- **Round trip = report only (D-197).** In `--app-repo` mode `check_roundtrip` runs `sync_markdown_to_seed.py --dry-run`
  in the temp dir against the temp seed copy and prints the difference count split by the three known causes —
  (1) `user_trigger_prompt` not extracted, (2) Insights column layout (rows 1301–1304, 1320, 1321), (3) versions sharing
  one section file — plus an "other" bucket. It NEVER fails on the known causes. If "other" > 0: print a WARN with the
  first hunks; still no failure, and the PR body reports it. Local mode (prompts tree present) keeps today's behaviour
  exactly. Expected on APP 5457216 seed (= 7e2397a seed): 143 differences in total (gatekeeper-reproduced on #162).
- **Proof (step 4)** also shows the round-trip report from both runs (`--app-repo` and the regenerated local tree);
  the counts must be equal.
- Printed SKIP command (neither present): `python3 scripts/genie_gate.py --app-repo /path/to/vibe-coding-workshop-app`
  (no `--skip-roundtrip`).
- Measurements in NEW folders under `FORGE/work/scratch/prompt-tooling-tracked-c-<run>/`; never delete or reset.
- Tampers in force for C: T-C1, T-C2, plus **T-C3:** make the round-trip classifier put one known-cause hunk in
  "other" → the WARN appears and the PR-body check flags it.

## Critic questions
(a) Is the source inventory complete (any other script that writes a seed or reads a hard-coded TPL path)?
(b) Do the `Path(__file__).parent` defaults keep genie_gate_diff's copy-and-run mode byte-identical after step 4?
(c) Does `genie_gate_diff.main` accept an argv list (for the equivalence run (ii)); exact invocation otherwise?
(d) Which audit areas scan the copied tooling dir (README / NN-*.md / tests fixtures), confirming Q2's expectation?
(e) Are the Part B line numbers right at FORGE HEAD?
(f) For Part C, which functions in TPL `scripts/genie_gate.py` hold the SKIP branches, and does any check need more
than `sections/` + `parse_markdown`?
(g) Can each tamper turn its check red?
