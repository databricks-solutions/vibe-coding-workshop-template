# tpl-audit-bare-sh (template; D-42) — ROUND 2 (critic r1 BLOCK folded in: TEXT_EXT; gate design)

Repo: databricks-solutions/vibe-coding-workshop-template, base origin/feature/genie-code-mcp-integration @ a26c6d0f26ed8ad17b9f2826eff3b85bbd31ee0e (created by INIT-TEMPLATE-BRANCH 2026-10-06; = main).
PR plan path: retrospectives/plans/genie-code-integration/2026-10-06-tpl-audit-bare-sh.md. retrospectives/ is git-IGNORED (TPL .gitignore:99), so the implementer must `git add -f` that one file and stage nothing else under retrospectives/.

## Problem (gate-p4-app-family, app #114 @236536b)
scripts/audit_genie_compat.py PATTERNS (~:89-92) match a deploy/setup shell script only as `./scripts/…deploy….sh`, `bash …deploy….sh` (SCRIPT_DEPLOY) or `./scripts/….sh`, `setup-….sh`, `bootstrap….sh` (SETUP_SCRIPT). A bare `./deploy.sh` (or any `./x.sh` outside scripts/) is invisible to the audit, so FORGE/tools/genie_gate_diff.py passes a genie-code fork that tells Genie Code to run a local shell script (RULE_1/RULE_3 violation). Today only the app-side marker lint (APP tests/workshop/test_app_family_genie_forks.py) catches it.
Lines the new rule will newly match (corrected, critic r1 (2)): scan() reads only TEXT_EXT files (audit_genie_compat.py :22 / :71), and TEXT_EXT has no `.sh`, so the 3 usage comments inside skills/*/scripts/*.sh are NOT scanned and stay unmatched (correct: a usage comment inside the script itself isn't an instruction to the agent). TPL contributes 1 line: genai-agents/sdlc/06-deployment-and-automation/references/bundle-configuration.md:97 (`./deploy.sh --var …`). The APP seed (extracted to apps_lakebase/prompts/*.md by genie_gate_diff's measure()) contributes up to 6 lines, all in DEFAULT (IDE-path) bodies. The implementer lists the exact set measured.

## Change
C1 scripts/audit_genie_compat.py (not a TPL trunk file):
  - SCRIPT_DEPLOY: also match a bare `./<path>deploy<…>.sh` in any directory: `(?<![\w/.])\./\S*deploy\S*\.sh`.
  - SETUP_SCRIPT: also match any bare `./<path>.sh` invocation `(?<![\w/.])\./[\w.-][\w./-]*\.sh`, and `\bsh\s+\S+\.sh`.
  - Keep every existing alternative unchanged. A bare `./deploy.sh` counts in BOTH classes, exactly as `./scripts/deploy.sh` already does today (critic r1 (4): consistent, hides nothing). Prose such as "do NOT run project shell scripts (deploy/setup/migrate `.sh` files …)" has no `./` prefix and stays unmatched (critic-verified). `../x.sh` and `foo/./x.sh` are rejected by the lookbehind.
  - TEXT_EXT unchanged (scanning .sh files would flag the scripts' own comments; out of scope).
C2 scripts/genie_gate_baseline.json (TPL TRUNK; charter exception ACCEPTED by critic r1): regenerate with `python scripts/genie_gate.py --update-baseline` after C1. The regenerated file must differ from the old one ONLY in the SETUP_SCRIPT / SCRIPT_DEPLOY entries of the affected areas, plus `total` (and any timestamp/note field); any other changed key is a FAIL. Reversal: revert C1 + C2 together.
C3 the plan file (git add -f), with the before/after audit delta per area::class and the exact list of newly matched lines (file:line).
Not touched: apps_lakebase/prompts/ (git-ignored, the human's local tree: NEVER edited), scripts/genie_gate.py, skills, AGENTS.md.

## Gates (TPL has no test suite). Critic r1 (3): genie_gate_diff.py exits 1 on ANY audit growth, so a rule-tightening PR cannot be green when you compare OLD audit vs NEW audit. Green gates therefore compare like with like (both sides run the new audit); the old-vs-new comparison is a documented EXPECTED-RED evidence check.
G1 (green) `python3 scripts/genie_gate.py --skip-roundtrip` in the PR worktree, with the APP seed extracted the way genie_gate_diff.py's measure() does → PASS against the regenerated baseline.
G2 (green) genie_gate_diff.py --base-ref <PR head> --head-ref <PR head> --base-seed <APP seed @6230f58> --head-seed <APP seed @6230f58> → exit 0, fork findings unchanged (a sanity run that the new audit runs cleanly on today's seed).
G3 (green; the tamper proof and the reason for the task) genie_gate_diff.py --base-ref <PR head> --head-ref <PR head> --base-seed <APP seed @6230f58> --head-seed <that seed with `Run ./deploy.sh before deploying.` added to the fork 1001 body> → exit 1 with a new [audit] SETUP_SCRIPT and/or SCRIPT_DEPLOY finding. The same pair with --base-ref/--head-ref = a26c6d0 (the OLD audit) → exit 0 (shows the gap this closes).
E1 (EXPECTED RED, evidence only) genie_gate_diff.py --base-ref a26c6d0 --head-ref <PR head> --base-seed = --head-seed = APP seed @6230f58 → exit 1, and the ONLY growth is SETUP_SCRIPT / SCRIPT_DEPLOY in the affected areas, equal to the C3 line list; fork findings identical. The gatekeeper verifies this line by line; any other growth or fork-finding change is a FAIL.
G4 (green) no new match on today's APP genie-code fork bodies (901-1002): their per-fork audit hit count is unchanged (list per fork).

## Release
MERGE repo=template, reseed=no; never deployed. After the merge, APP genie gates use --base-ref origin/feature/genie-code-mcp-integration (now valid and stricter); a future APP fork with a bare ./x.sh then fails the APP genie gate too.

## Decision D-42
question: should the Genie compat audit catch a bare ./x.sh? · choice: yes, widen SETUP_SCRIPT/SCRIPT_DEPLOY, regenerate the locked baseline in the same PR; the gates compare new-vs-new, and old-vs-new is expected-red evidence · evidence: audit_genie_compat.py ~:22/:71/:89-92; genie_gate_diff.py :101-105; gate-p4-app-family T2 · reversal: revert both files.

## C3 — measured delta (implementer, 2026-10-06)
Measured in the PR worktree with the APP seed @6230f58 (sha256 99ec684b9a7adb3c9fe50693a2997cde0c2ecacaedcef39b6ce6041364b558fc) extracted the way genie_gate_diff.py measure() does it: `python3 scripts/audit_genie_compat.py` before C1 (a26c6d0) vs after C1, same tree, same seed. No row disappeared; 18 rows were added (9 lines × both classes).

Before → after per area::class:
| area::class | a26c6d0 | PR head | Δ |
|---|---|---|---|
| apps_lakebase::SCRIPT_DEPLOY | 5 | 13 | +8 |
| apps_lakebase::SETUP_SCRIPT | 10 | 18 | +8 |
| genai-agents::SCRIPT_DEPLOY | 0 | 1 | +1 |
| genai-agents::SETUP_SCRIPT | 0 | 1 | +1 |
| total | 3432 | 3450 | +18 |

Lines newly matched (each counted once as SCRIPT_DEPLOY and once as SETUP_SCRIPT):
- apps_lakebase/prompts/02_seed_section_input_prompts.sql:6697
- apps_lakebase/prompts/02_seed_section_input_prompts.sql:6712
- apps_lakebase/prompts/02_seed_section_input_prompts.sql:6846
- apps_lakebase/prompts/02_seed_section_input_prompts.sql:6847
- apps_lakebase/prompts/sections/19-redeploy_test.md:42
- apps_lakebase/prompts/sections/19-redeploy_test.md:57
- apps_lakebase/prompts/sections/19-redeploy_test.md:192
- apps_lakebase/prompts/sections/19-redeploy_test.md:193
- genai-agents/sdlc/06-deployment-and-automation/references/bundle-configuration.md:97

The APP seed contributes 4 distinct lines, all in the DEFAULT redeploy_test body. The audit scans both the seed `.sql` and the extracted `sections/*.md`, so each one counts twice (8 rows per class, not "up to 6"). No genie-code fork line matches.

### C2 — deviation from "regenerate with --update-baseline" (implementer)
A plain `--update-baseline` on this tree + seed changes 14 keys outside SETUP_SCRIPT/SCRIPT_DEPLOY and drops `apps_lakebase::CLIENT_NAV`. The locked baseline (last written 2026-06-05, dd6f667) is stale against both today's tree and today's seed. A full regen would also absorb four untouched-area regressions that are already present at a26c6d0 (apps_lakebase::GENIE_RESOURCE +6, data_product_accelerator::BARE_ARTIFACT_PATH +2, skills::APP_DEPLOY +6, skills::INSESSION_CREATE +3). Under this plan's C2 rule that is a FAIL. So the committed baseline takes ONLY the SETUP_SCRIPT/SCRIPT_DEPLOY entries (by_area_class + by_class) from the `--update-baseline` output, keeps every other key at its locked value, and sets total = 3557 + 18 = 3575 (sum of by_area_class = sum of by_class = total). The regenerated values for the target classes equal old + measured delta exactly.
