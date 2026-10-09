# tpl-overview-carveouts (v2, D-71): reconcile template text with D-56 (two RULE_10 carve-outs) and D-44 (SDK SNAPSHOT canonical on Genie Code)

repo=template · base origin/feature/genie-code-mcp-integration (a77f33b) · wording only · plan path in PR: retrospectives/plans/genie-code-integration/2026-10-08-tpl-overview-carveouts.md
Supersedes the D-67 park by human ruling D-71. Trunk files scripts/genie_gate.py and scripts/genie_gate_baseline.json untouched; no scripts/ change at all.
00-overview.md is tracked (blob at a77f33b) though .gitignore:99 matches it: edit it in place, `git add` works for a tracked file (no -f needed; do not add any other ignored file).

## ACCEPTANCE (human, D-71; replaces round-by-round discovery)
The PR body pastes the output of this grep, run on the PR head over learner-facing text (retrospectives/ excluded):
  git grep -n -E "sole carve-out|sanctioned exception|only sanctioned|one exception|explicitly includes data-product|apps deploy" <head> -- . ':!retrospectives/'
and marks EVERY hit `fixed` or `kept — <reason>`. Hits may be grouped by file when one reason covers the group, but each line number appears. Also paste the before-grep at a77f33b (lead count: 3 non-`apps deploy` hits + 114 `apps deploy` hits, case-sensitive). Separately list the 00-overview.md sites (excluded by the grep, but named by D-71).

## Rule for `apps deploy` (D-44 changed only the Genie Code path)
`apps deploy` stays correct for the IDE. Never blanket-replace. A hit is FIXED only if it states, without client qualification, that the App ships via `apps deploy` as the (only/canonical) path on both clients or on Genie Code; the fix makes the sentence client-qualified: "IDE: `apps deploy` (local CLI); Genie Code: SDK `w.apps.deploy(…, mode=SNAPSHOT)` via `executeCode` canonical, `apps deploy` via `runDatabricksCli` only where the page allows (RULE_9)". Machine-read field VALUES (state-template `app_deploy: { verb: "apps deploy", gated: true }`, :134/:143; skills/vibecoding-state/SKILL.md:243 `app_deploy.verb`) are NOT changed (learner state files and prompts read them); an adjacent comment/clause may qualify them.

## Changes (lead pre-classification at a77f33b; the implementer verifies on the head)
FIX — carve-out text:
C1 skills/genie-code-environment/SKILL.md:368-369 "The only sanctioned in-session creation is RULE_8 **Tier 3** Genie-Space `createAsset` (last-resort)" → name both carve-outs: (1) RULE_8 Tier 3 `createAsset` (Genie Code only, last resort); (2) RULE_10 idempotent foundation provisioning: `CREATE SCHEMA IF NOT EXISTS` / `CREATE VOLUME IF NOT EXISTS` of the participant's own prefixed schema/volume, both clients, nothing else (D-56). Keep the bracketed citation.
C2 same file :371-372 "**This explicitly includes data-product table DDL.** Creating Bronze/Silver/Gold schemas and tables — `CREATE SCHEMA`, …" → scope it explicitly to data-product (Bronze/Silver/Gold) schemas and tables, and add one sentence that the D-56 foundation carve-out (the participant's own prefixed foundation schema/volume, IF NOT EXISTS) is separate and is not this regression. The rest of the blockquote byte-identical.
C3 skills/databricks-asset-bundles/SKILL.md:426 "This is the **one sanctioned exception** to the authoring discipline" → "one of the **two sanctioned exceptions** … (the other is RULE_10's idempotent foundation provisioning, D-56)".
C4 data_product_accelerator/skills/common/databricks-autonomous-operations/SKILL.md:580 (`w.schemas.create()` / `CREATE SCHEMA` / `CREATE VOLUME` / `CREATE TABLE` to provision the deliverable): KEEP the NEVER (it is about the deliverable); append a pointer: "(The RULE_10 foundation carve-out, D-56: `CREATE SCHEMA/VOLUME IF NOT EXISTS` of your own prefixed foundation schema/volume, is separate and not a workaround.)"
C5 …/databricks-autonomous-operations/references/sdk-api-reference.md:9-11: schemas/volumes listed as never in-session → add "except the RULE_10 foundation carve-out (D-56)"; and "(App via `apps deploy`)" → client-qualified per the rule above.
FIX — `apps deploy` client qualification:
A1 skills/databricks-asset-bundles/SKILL.md:14 frontmatter `deploy_note` "…; App via apps deploy" → "…; App via apps deploy (IDE) / SDK SNAPSHOT (Genie Code, RULE_9)". Frontmatter stays valid YAML (one quoted string).
A2 same file :91-92: already names the Genie Code SDK path, but leads with "it ships via `apps deploy`" for both → reorder to the client-qualified form (IDE `apps deploy`; Genie Code SDK SNAPSHOT canonical, `apps deploy` where the page allows).
A3 skills/vibecoding-state/references/state-template.md:119-120 "The app deploys via `apps deploy` (RULE_9 exception)" → client-qualified.
A4 same file :127-130 (agent app "builds server-side via `apps deploy` (`mode=SNAPSHOT`)" and "plus `apps deploy` (for the host)") → client-qualified (Genie Code: SDK SNAPSHOT; IDE: `apps deploy`).
A4b (critic r1) same file :151 `agent_app_root` comment "On genie_code it is the apps init --output-dir target and builds the uv/FastAPI server server-side via apps deploy (mode=SNAPSHOT)" → client-qualified like A4 (Genie Code: SDK `w.apps.deploy(…, mode=SNAPSHOT)` via `executeCode`, build runs server-side; IDE: `apps deploy`). Keep it a single YAML comment line; the `agent_app_root:` key/value is unchanged.
A5 skills/vibecoding-state/SKILL.md:82 "deploys via `apps deploy` (no `bundle` page-context pin)" → client-qualified (same sentence shape as A3).
A5b (critic r1) same line :82, SECOND occurrence: "On `genie_code` it is the `apps init --output-dir` target and the `uv`/FastAPI server builds server-side via `apps deploy` (`mode=SNAPSHOT`)" → same fix as A4/A4b (SNAPSHOT is the SDK mode, not a CLI `apps deploy` flag on Genie Code).
RULE (critic r1): a line with several hits is classified PER OCCURRENCE; the body lists each occurrence. Lead check at a77f33b of the lines with ≥2 hits or `apps deploy` + SNAPSHOT on one line: Instructions.md:1349 (K1, IDE), 03-appkit-deploy/SKILL.md:331 (K2: already the Genie Code client note naming the SDK SNAPSHOT fallback), :339 (K3), sdlc/06 references/apps-deployment-patterns.md:23 (K4), vibecoding-state/SKILL.md:82 (A5 + A5b), state-template.md:151 (A4b). Any line whose text says Genie Code uses `apps deploy` with `mode=SNAPSHOT` is FIX, never KEEP.
A6c (critic r2) vibecoding-state/SKILL.md:82 THIRD occurrence: "Client-invariant: … `app_deploy` is always `{ verb: "apps deploy", gated: true }`" → the A6 treatment: the field value stays; the sentence stops calling app_deploy client-invariant (e.g. "`app_deploy` is `{ verb: "apps deploy", gated: true }` (the IDE verb; on genie_code the SDK SNAPSHOT is canonical, RULE_9)"). Lead occurrence count at a77f33b (excl retrospectives/, case-sensitive): 120 occurrences on 114 lines; multi-occurrence lines = Instructions.md:1349 x2 (K1), 03:331 x2 (K2), 03:339 x2 (K3), sdlc/06 patterns:23 x2 (K4), vibecoding-state/SKILL.md:82 x3 (A5, A5b, A6c). The PR body must reach 120/120 at a77f33b-equivalent classification.
A6 state-template.md:134 and :143 and vibecoding-state/SKILL.md:243: field values unchanged; add a short qualifier ("IDE verb; on genie_code the SDK SNAPSHOT is canonical, RULE_9") next to :134 (inside the comment block) and in :243's parenthesis. :134's heading "Client-invariant fields" must not falsely cover app_deploy: either move the qualifier onto that line or note it.
FIX — 00-overview.md (excluded from the grep; D-67/D-71 sites):
O1 :29-30 add ", except for the two sanctioned carve-outs below" after "the workshop **deliberately does not**".
O2 :34-38 blockquote → "> **Two sanctioned exceptions (user-approved):**" with the RULE_8 Tier 3 text byte-identical as (1) and (2) the foundation provisioning text taken from locked decision 1 :44-46.
O3 :42-43 "App via `apps deploy`" → "App via the SDK `w.apps.deploy(…SNAPSHOT)` in `executeCode` on Genie Code, or `apps deploy` where the page allows / in the IDE (RULE_9)".
O4 :151 RULE_8 row "the **one sanctioned exception**" → "one of the **two sanctioned exceptions** … (the other is RULE_10's idempotent foundation provisioning, D-56)". (:57 "the one exception to the bundle-deploy spine (RULE_9)" is the deploy-spine exception, a different thing: keep.) :152 RULE_9 row and :165 field value: keep (#20 already reconciled RULE_9; :165 is the field value).
KEEP (pre-classified; the implementer confirms each line on the head and writes the reason):
K1 IDE commands / IDE-labelled text: every `databricks apps deploy --profile …`, `--skip-build`, `--help`, `--source-code-path` line and IDE tables (QUICKSTART.md, README.md, apps_lakebase/Instructions.md, apps_lakebase/skills/01/03/04/05/06/06d/07 IDE rows and code blocks, references/*) — reason "IDE path; D-44 changed only Genie Code".
K2 already Genie-Code-qualified: 03-appkit-deploy/SKILL.md:17-18, :68, :331; the `03-appkit-deploy deploy-routing contract` rows in 01:63, 04:82, 06:99, 06d:238, 07:101, 08:89; 01:300; genie-code-environment/SKILL.md:66, :160, :167, :449; references/allow-list-and-commands.md:12, :16, :19; databricks-autonomous-operations/SKILL.md:123, :139 — reason "already client-qualified (RULE_9 routing)".
K3 descriptive mentions that are not a deploy instruction (e.g. "apps deployed without it" foundation/02:572, 03:127/:142/:339 build behaviour, plugin-lakebase.md:113, 07:1175) — reason "describes CLI behaviour, not the Genie Code path".
K4 genai-agents Track A / SDLC agent-app deploy (00-course-orchestrator:202, genai-agents/README.md:203, tracks/A-custom-agent-apps/02, 07, 08, sdlc/06 references), agentic-framework/agents/*, presentations/*, genai-agents/workshop-explorer.html — reason "not the RULE_9 workshop App / legacy IDE material; out of D-44's scope". If any of these explicitly tells a Genie Code learner to run `apps deploy` as the only path, list it under "follow-up (not fixed here)" in the body rather than editing it (keeps scope bounded).
Anything on the head-grep that is in none of the above → classify it in the body with a reason; do NOT widen edits beyond C/A/O without listing them as a plan amendment in the PR body.

## Green gates
1. `python3 FORGE/tools/genie_gate_diff.py --base-ref origin/feature/genie-code-mcp-integration --head-ref <commit> --base-seed <APP origin/feature/genie-code-mcp-integration seed copy> --work FORGE/work/tpl-overview-carveouts-genie` exits 0, no audit key growth (forge 15ec49d; fork-check counts are not comparable with older 80→80 numbers). If a key grows from new wording (e.g. a new `CREATE …` or `apps deploy` token), STOP and report; the new wording must not add counted tokens — prefer prose like "the RULE_10 foundation carve-out (D-56)" over pasting DDL.
2. Word-diff fence: only the lines named in C1-C5, A1-A6 (incl. A4b, A5b), O1-O4 change (plus the plan file).
3. YAML frontmatter of every edited SKILL.md still parses (`python3 -c` with yaml.safe_load of the frontmatter, or the repo's own frontmatter check if one exists).

## Tampers (restore each)
X1 revert C1 → text check: genie-code-environment/SKILL.md no longer names the RULE_10 foundation carve-out → red.
X2 revert C2's separation sentence → text check red.
X3 revert O2 (back to "One sanctioned exception") → text check red.
X4 revert A3 → the head-grep classification no longer matches (an unqualified Genie-Code-path `apps deploy` line) → red.
X5 change state-template.md:134's field value to `"SDK SNAPSHOT"` → fence red (field values must not change).
X6 edit a K1 line → fence red.
X7 (critic r1) revert A5b only (keep A5) → the head-grep classification shows an unqualified Genie-Code `apps deploy (mode=SNAPSHOT)` occurrence on :82 → red.
X8 (human D-76) add one line to the PR body's "Reworded audit lines" block that is NOT a rewording of a removed line (e.g. a flagged line the PR did not touch, or a new instruction) → whatever genie_gate_diff's exit code, the gatekeeper's judgment of each "reworded (listed):" line must FAIL it.

## Amendment D-74 / D-76 (human rulings 2026-10-08; forge 3204841)
D-74 option (ii): implemented on this plan as it stands; no third critic round. GATEKEEPER ACCEPTANCE: the gatekeeper runs the D-71 grep itself on the PR head (case-sensitive, retrospectives/ excluded, and `git grep -o` for occurrences) and requires that the PR body classifies EXACTLY those hits: same line numbers, every occurrence on multi-hit lines. Before-count at a77f33b (lead, re-verified this session): 117 lines / 123 occurrences in total = 3 non-`apps deploy` lines + 120 `apps deploy` occurrences on 114 lines. The body must reach N/N for the head's actual count. Any mismatch (a missing, extra or misnumbered hit) FAILs.
D-76 (genie_gate_diff now compares the per-line multiset of (area::class, flagged line text)): a flagged line the PR rewords but keeps flagged prints as `[audit] <key>: +n <text>` and FAILs unless listed. Expected here: the client-qualified `apps deploy` sentences (A1-A6c, C5, O3) and the re-scoped CREATE SCHEMA text (C1, C2, C4, C5). The implementer copies each genuine rewording as `<key> <text>` into a "Reworded audit lines" block in the PR body and re-runs the gate with `--reworded <file of that block>`. Listed lines must be covered by lines the PR removed in the same key, and every listed line must be used. Never list a line to get a new instruction past the gate; prefer prose that adds no counted token. The gatekeeper builds the --reworded file ONLY from the PR body and judges each "reworded (listed):" line: same instruction, re-scoped or client-qualified. A listed line that adds new coupling FAILs whatever the exit code. "fixed:" output is per key (`<key>: N counted line(s) removed`); gate outputs from before 3204841 are not comparable line for line.
Green gate 1 therefore reads: genie_gate_diff exits 0 with `--reworded <block file>` (or without it if nothing is reworded), no unlisted `+n` line, every listed line used.

## Live checks
None (template; never deployed). After merge: TPL RC #21's head moves → re-review + re-gate #21 (D-71).

## Release
MERGE repo=template reseed=no.

## Reverse
Revert the PR.
