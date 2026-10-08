# tpl-rule9-wording: RULE_9 says SDK SNAPSHOT first, CLI where the page allows (D-44)

repo=template · base origin/feature/genie-code-mcp-integration (edb07a9 or later) · wording only · plan path in PR: retrospectives/plans/genie-code-integration/2026-10-08-tpl-rule9-wording.md
Files (exactly): retrospectives/plans/genie-code-integration/00-overview.md (already tracked on the integration branch since template #19, so no force-add is needed; confirm with `git ls-files` in the worktree) and the plan file. Trunk files scripts/genie_gate.py and scripts/genie_gate_baseline.json are NOT touched; scripts/audit_genie_compat.py is not touched.

## Evidence (lead, read-only at origin/feature/genie-code-mcp-integration)
- D-44 (protocol 1, shipped code decides): on Genie Code the SDK `w.apps.deploy(<name>, AppDeployment(source_code_path=…, mode=AppDeploymentMode.SNAPSHOT))` via `executeCode` is canonical; the CLI `apps deploy` via `runDatabricksCli` is an acceptable equivalent only where the page allows it. Shipped forks 912, 929 and 930 in the APP seed do SDK first; P10 (00-overview :193: CLI not reliable, CWD pinned, page-gated) and P11 (:194: SDK works from any context) agree.
- 00-overview :150 (the RULE_9 row of the decision table) reads the other way: "Genie Code = `apps deploy` via `runDatabricksCli` **when the page allows it** … with the **sanctioned fallback** being the SDK `w.apps.deploy(…SNAPSHOT)` via `executeCode` (P11)".
- 00-overview :54-55 (overview item 4): "deploys via `apps deploy` through `runDatabricksCli` — the one exception to the bundle-deploy spine (RULE_9)".
- Checked and left unchanged (not RULE_9 wording, a capability record): skills/vibecoding-state/references/state-template.md:119, :134 (`app_deploy = { verb: "apps deploy", gated: true }`); scripts/audit_genie_compat.py:104 (the audit hint string; a tooling message, not learner text, and out of this wording scope).

## Changes
S1 00-overview :150, Genie Code clause only: "Genie Code = the SDK `w.apps.deploy(<name>, AppDeployment(source_code_path=…, mode=SNAPSHOT))` via `executeCode` (canonical: works from any context, P11), or `apps deploy` via `runDatabricksCli` **where the page allows it** (it is **page-gated**, hard-blocked on file-editor / standalone Apps pages, and its enhanced build needs CWD = the app root, P10)." The IDE clause, the RULE_9 key, the `APP_DEPLOY` audit area and the "No local npm step scripted … (Gap 4 resolved, P11)" sentence stay byte-identical.
S2 00-overview :54-55 item 4: "deploys via the SDK `w.apps.deploy(…SNAPSHOT)` in `executeCode` on Genie Code (or `apps deploy` through `runDatabricksCli` where the page allows) and via the CLI in the IDE — the one exception to the bundle-deploy spine (RULE_9)." Keep "(validated)" and the rest of the item.
S3 Nothing else in the file changes. The diff is exactly those two passages.

## Green gates
`python3 FORGE/tools/genie_gate_diff.py --base-ref origin/feature/genie-code-mcp-integration --head-ref <commit> --base-seed <APP seed copy from APP origin/feature/genie-code-mcp-integration> --work FORGE/work/tpl-rule9-wording-genie` exits 0 with no new findings (00-overview is not an audited surface; expect no movement).

## Tampers
X1 revert S1 only (restore "sanctioned fallback being the SDK") → the reviewer's text check fails: the RULE_9 row must name the SDK SNAPSHOT as canonical and the CLI as page-allowed.
X2 change the RULE_9 key or the `APP_DEPLOY` area in the row → `git diff --word-diff` shows a change outside the Genie Code clause → fence fails.
X3 touch any other line of 00-overview → the diff has more than the two passages → fence fails.

## Live checks
None (template merge, never deployed; it is exercised by the human smoke).

## Release
MERGE repo=template, reseed=no.

## Reverse
Revert the PR (the RULE_9 row says CLI first again). If a live smoke proves the CLI reliable, reorder all three forks with it (D-44 reversal).
