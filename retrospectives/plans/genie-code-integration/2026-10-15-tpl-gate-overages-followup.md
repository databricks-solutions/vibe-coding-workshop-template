# tpl-gate-overages-followup — plan r2 SIGNED (2026-10-15; r0 + critic r1 revision + human sign-off D-192)

Repo: **template** (databricks-solutions/vibe-coding-workshop-template). One PR into `feature/genie-code-mcp-integration`.
Commit this plan unchanged at `retrospectives/plans/genie-code-integration/2026-10-15-tpl-gate-overages-followup.md`
(TPL's docs/superpowers/ is git-ignored).

Base: `origin/feature/genie-code-mcp-integration` = `3f6ba0a`. RC #21 merged it to main as `9c0bbe6`;
`git diff 3f6ba0a 9c0bbe6` is empty, so the base tree equals main. Worktree:
`git -C TPL worktree add FORGE/work/tpl-gate-overages-followup -b forge/tpl-gate-overages-followup origin/feature/genie-code-mcp-integration`.
The gate reads the APP seed: use APP `feature/genie-code-mcp-integration` at **2e3397f** (current; #160 merged)
via `git -C APP show 2e3397f:db/lakebase/dml_seed/02_seed_section_input_prompts.sql`. Never check out, pull or
commit in TPL or APP checkouts.

Decisions carried: D-73 (1), D-80, D-156, D-42 (no blanket `--update-baseline`), D-56 (RULE_10 carve-out 2),
D-76 (reworded-lines mechanism), D-190.

## Scope (three items, nothing else)

### Item 1 — pre-existing lock overages (D-73 (1); RC #21 B5)
At 3f6ba0a + APP seed de70b96, `python3 scripts/genie_gate.py --skip-roundtrip` (absolute lock gate) FAILs on four
keys over their lock in `scripts/genie_gate_baseline.json`:

| key | lock → current (B5) | B5 recommendation |
|---|---|---|
| apps_lakebase::GENIE_RESOURCE | 8 → 14 (+6) | text comes from the APP seed; find the rows; re-lock with evidence if sanctioned Genie resource steps, else an APP content task |
| data_product_accelerator::BARE_ARTIFACT_PATH | 8 → 10 (+2) | content fix in TPL: anchor the 2 paths to `<ARTIFACT_ROOT>`; leave the lock |
| skills::APP_DEPLOY | 108 → 114 (+6) | re-lock with evidence if they are the documented SDK SNAPSHOT / CLI guidance (D-44), else content fix |
| skills::INSESSION_CREATE | 14 → 17 (+3) | re-lock with evidence if RULE_8 Tier 3 / RULE_10 carve-out text, else content fix |

Steps:
1. **Measure first (M0)** on the base with APP seed 2e3397f, exactly as B5 did (raw seed extracted into
   `apps_lakebase/prompts/sections`, each ref scored with its own scripts and baseline). Paste the full audit-gate
   output. The APP seed has moved since de70b96 (#135–#160), so numbers may differ: report the current over-lock
   set. Any key over lock that is NOT in the table above → STOP and report (no fix, no re-lock).
2. **Attribute every over-lock line**: for each key, list each counted line beyond the lock with file:line (TPL) or
   seed row id + section_tag + coding_assistant (APP), and the commit that added it (`git log -S` / blame).
3. **Classify each line**: (a) sanctioned guidance (cite the rule: RULE_8 Tier 3, RULE_10 carve-out (1)/(2),
   D-44 client-qualified App deploy, D-156 light path) → candidate for re-lock; (b) a real Genie Code issue in TPL
   text → content fix in this PR; (c) a real issue in APP seed text → do NOT edit APP; list it for a separate APP task.
4. **Content fixes (class b) first.** Expected: the 2 BARE_ARTIFACT_PATH paths anchored to `<ARTIFACT_ROOT>`.
   Each fix must keep the same instruction (D-76 judgment) and remove the counted line, not move it to another key.
5. **Re-lock (class a) only per key, never `--update-baseline` wholesale (D-42).** Edit only the named keys in
   `scripts/genie_gate_baseline.json` (`by_area_class`, plus `by_class` and `total` as the file's own arithmetic
   requires). The PR body has one table row per re-locked key: old lock, new lock, the exact lines absorbed, and
   the rule that sanctions each. **The human signs each re-lock row in plan sign-off (D-42); the implementer
   re-locks only the keys the signed plan names.** Until signed, the plan names none (see Q1).
6. Class c lines: listed in the PR body under "APP follow-up" and queued; the lock for that key is left as is
   unless the human signs a re-lock for it.

### Item 2 — vibecoding-state frontmatter (D-80)
`skills/vibecoding-state/SKILL.md` frontmatter fails `yaml.safe_load` (line 18 col ~1145, unescaped quotes around
"skills/" inside the double-quoted `deploy_note`; came in with 1c8ec7b; identical on main). Fix: re-quote that one
scalar (escape the inner quotes, or switch to a single-quoted / folded block scalar) so the bytes after YAML
parsing are the same string as intended. Acceptance: `yaml.safe_load` parses; the parsed `deploy_note` equals the
intended text (inner quotes preserved); every other frontmatter key's parsed value byte-identical to base; body
below the frontmatter byte-identical. Also check the `compatibility:` line (same style) parses. Check and report
whether any loader in the repo reads this frontmatter (`grep -rn "deploy_note\|safe_load\|frontmatter" scripts/ skills/`),
for severity only.

### Item 3 — D-156 RULE_10 carve-out line (skills/databricks-asset-bundles/SKILL.md)
At `:103-109` RULE_10 names "two carve-outs". Add the third, next to carve-out (1), worded from the D-156 ruling:

> (3) **Genie Code light path (genie-accelerator + Insights), Genie-Code-only:** the AI/BI dashboard via
> `createAsset(assetType:"dashboard")` and its operational add-ons — SQL alerts (`w.alerts.create`) and the
> dashboard schedule/subscription (`w.lakeview.create_schedule` / `create_subscription`) — may be created
> in-session. Each object's id is recorded in `<STATE_FILE>` and a clickable link is printed. Making them
> reproducible belongs to a bundle step (e.g. `gaccel_productionize`), never an ad-hoc import.

and change "There are **two carve-outs**" to "three". Also fix the other places that now say "two"/"one"
sanctioned exception(s) so the template stays consistent: `skills/databricks-asset-bundles/SKILL.md:426`,
`skills/genie-code-environment/SKILL.md:368`, `retrospectives/plans/genie-code-integration/00-overview.md:34-40`
(verify each line at the base; grep for "two carve-outs", "two sanctioned", "one sanctioned", "only exception"
across `skills/` and `retrospectives/plans/genie-code-integration/00-overview.md`, and list every hit with its
classification as #22 did).

**Gate effect — measure on a scratch build first (M1).** The new carve-out text names SDK create calls and
`createAsset`, which the audit likely counts (skills::INSESSION_CREATE or similar). Run
`tools/genie_gate_diff.py` base → scratch head (with the APP seed 2e3397f). If the carve-out (or the count edits)
adds ANY counted line that is not a genuine rewording of a removed line in the same key (D-76 `--reworded`), STOP
and report the keys and lines. No waiver; no scorer change; the human chooses (e.g. extend `RULE_10_SANCTIONED`
in `scripts/audit_genie_compat.py` for the light-path line as #19 did for D-56, re-lock that key, or reword).

## Out of scope
APP edits of any kind; `scripts/audit_genie_compat.py` and `scripts/genie_gate.py` (no scorer change without a
ruling); any key not named; the D-61 raw-seed v1/v2 audit question; the D-65 informational T3.

## Trunk files / charter exception
`scripts/genie_gate_baseline.json` is a TPL trunk file. Exception requested: edit only the keys the signed plan
names (Item 1 step 5), reason D-73 (1) lock overages, reversal = revert this PR (or restore the listed keys' old
values). `scripts/genie_gate.py`: not edited. No other trunk file.

## Acceptance contract (gatekeeper re-derives every item itself)
- A1 M0 output pasted; over-lock set at base + APP 2e3397f listed; any key outside the table → STOP happened.
- A2 Every over-lock line attributed (file:line or row id) and classified a/b/c with the rule cited.
- A3 Content fixes keep the instruction (judged like D-76) and each removes a counted line in its key.
- A4 Only signed keys re-locked; the baseline diff touches only those keys (+ by_class/total arithmetic); each
  re-locked line is listed in the body.
- A5 After the PR, `python3 scripts/genie_gate.py --skip-roundtrip` with APP seed 2e3397f: the four B5 keys no
  longer over lock (by fix or signed re-lock); report the full audit-gate output and exit code. If a class-c key
  remains over lock unsigned, the body says so and the exit is explained, not hidden.
- A6 `tools/genie_gate_diff.py` base → head (APP 2e3397f, with `--reworded` built only from the body): exit 0,
  counted lines and fork findings reported; no added counted line outside the reworded block.
- A7 Item 2: frontmatter parses; parsed values as specified; body bytes unchanged.
- A8 Item 3: carve-out (3) present with every D-156 clause; "three" consistent at every listed site; grep table
  with classification in the body.
- A9 Scope: files changed ⊆ {skills/vibecoding-state/SKILL.md, skills/databricks-asset-bundles/SKILL.md,
  skills/genie-code-environment/SKILL.md, retrospectives/plans/genie-code-integration/00-overview.md, the
  BARE_ARTIFACT_PATH files found in A2, scripts/genie_gate_baseline.json (signed keys only), this plan file}.
  Any other file → explain or STOP.
- A10 TPL test suite (whatever `scripts/` and `tests/` the repo ships; e.g. `python3 -m pytest` if present) green;
  report counts.

## Tampers
- X1 Re-add one fixed BARE_ARTIFACT_PATH bare path → A5 shows the key over lock again.
- X2 Re-lock a key the plan does not name → A4 check fails.
- X3 Reintroduce the unescaped quotes in vibecoding-state → A7 parse fails.
- X4 Drop the `<STATE_FILE>` clause from carve-out (3) → A8 clause check fails.
- X5 List a non-rewording line in the Reworded block → gatekeeper FAILs it on judgment (D-76).

## Questions for the human (sign-off)
- Q1 Which keys may be re-locked? Proposed default: none until M0/A2 attribution is in the PR body; the
  implementer opens the PR with content fixes only and the attribution table, then STOPS; the human signs the
  re-lock rows; a fix-up commit applies only the signed rows. (Alternative: sign now any key whose lines all turn
  out to be class a.)
- Q2 If M1 shows carve-out (3) adds counted lines: stop (default), or pre-authorize extending
  `RULE_10_SANCTIONED` to the light-path line (a scorer change)?

## Revision r1 (critic round 1, D-191)

1. **Item 3 site list — now explicit and grep-complete.** Known sites at 3f6ba0a (lead grep + critic):
   - `skills/databricks-asset-bundles/SKILL.md:103` ("There are **two carve-outs**") — the RULE_10 paragraph itself;
   - `skills/databricks-asset-bundles/SKILL.md:426` ("one of the **two sanctioned exceptions**");
   - `skills/genie-code-environment/SKILL.md:368` (two carve-outs incl. D-56; verify wording);
   - `retrospectives/plans/genie-code-integration/00-overview.md:30`, `:34` ("Two sanctioned exceptions"), `:45`,
     `:153` (RULE_8 row), `:155` (RULE_10 row), and `:59` ("the one exception to the bundle-deploy" — about the App
     deploy verb, D-44; expected KEEP, classify it).
   The implementer must still run, at the base, `git grep -n -i -E` for each of: `two carve-outs`, `two sanctioned`,
   `one sanctioned`, `only exception`, `one exception`, `single exception`, `two exceptions`, `carve-out`,
   `sanctioned exception` across `skills/` and `retrospectives/plans/genie-code-integration/00-overview.md`, and
   put EVERY hit in the PR body table with a classification: "fixed → three" / "keep (other topic: why)". A hit
   counted in the RULE_10 sense and left at two is a FAIL (A8).
2. **Expected gate effect, stated up front (critic (c)).** Carve-out (3) contains `createAsset(` and
   `w.alerts.create` / `w.lakeview.create_*`, which the audit counts as INSESSION_CREATE (`audit_genie_compat.py`
   regex), and `RULE_10_SANCTIONED` (`:125`) sanctions only the D-56 `CREATE SCHEMA/VOLUME IF NOT EXISTS` lines.
   So M1 will almost certainly add counted `skills::INSESSION_CREATE` lines, and under the Q2 default the
   implementer STOPS before committing Item 3. To avoid a wasted round, Q2 now asks the human to choose up front:
   - **Q2-a (lead recommendation):** extend `RULE_10_SANCTIONED` in `scripts/audit_genie_compat.py` with a pattern
     matching ONLY the carve-out (3) sentence(s) in `skills/databricks-asset-bundles/SKILL.md` (and the mirrored
     overview/genie-code-environment lines), the same mechanism #19 used for D-56, with a test/tamper that a
     `w.alerts.create` line elsewhere is still counted. Adds `scripts/audit_genie_compat.py` to the fence.
   - **Q2-b:** word carve-out (3) without literal call tokens (e.g. "the dashboard `createAsset` call and the SQL
     alert / dashboard schedule SDK create calls"), measured by M1 to add 0 counted lines; weaker for learners.
   - **Q2-c:** signed re-lock of `skills::INSESSION_CREATE` by exactly the measured lines.
   - **Q2-d:** stop and report (old default).
3. **B5 numbers will not hold (critic (a)).** At APP 2e3397f the raw seed has more GENIE_RESOURCE matches than at
   de70b96, so `apps_lakebase::GENIE_RESOURCE` will read above 14. That is expected and is exactly what M0 measures;
   the STOP in Item 1 step 1 applies only to keys outside the B5 table, not to higher values of B5 keys.
4. **Baseline arithmetic (critic (e)).** Only `by_area_class` is gating (`cur["by_area_class"] > base_ac`); `total`
   only warns and `by_class` is not used for pass/fail. A re-lock edits the signed `by_area_class` keys and keeps
   `by_class` / `total` arithmetically consistent with them (sum), nothing else. A4 checks the arithmetic.
5. **Item 2 severity (critic (d)).** No script parses the vibecoding-state frontmatter with a YAML loader; only
   agents read it. Severity low; the fix stays in scope (it is a valid-YAML defect any skill loader would hit).

## SIGNED (human, 2026-10-15; D-192) — overrides r0/r1 where they differ

- **Q1 = default NONE.** The implementer opens the PR with the content fixes and the line-by-line
  attribution/classification table, then STOPS. The human signs re-lock rows one by one; a later fix-up commit
  applies only the signed rows. Lines attributed to the APP seed (2e3397f) go to a separate APP task list in the
  PR body, not into this PR.
- **Q2 = (b): wording without the literal call.** Precedent: carve-out (1) already writes "a Genie Space via
  `createAsset`" with no parenthesis; the scorer counts only `createAsset\s*\(` (audit_genie_compat.py:100), so
  that line is uncounted with no sanctioned pattern. Write carve-out (3) the same way. Text (adjust only for fit):
  > (3) the Genie Code light path (genie-accelerator and Insights): the AI/BI dashboard via `createAsset` with
  > `assetType` dashboard, and its operational add-ons (SQL alerts via `w.alerts.create`, the dashboard schedule and
  > subscription via `w.lakeview.create_schedule` / `create_subscription`), Genie-Code-only. Each object's id is
  > recorded in `<STATE_FILE>` and a clickable link is printed; making them reproducible belongs to a bundle step,
  > never to an ad-hoc import (D-156).
  No `scripts/audit_genie_compat.py` change; no `skills::INSESSION_CREATE` re-lock; `audit_genie_compat.py` is
  NOT in the fence. If the measured gate still counts the new line (or any mirrored line), STOP and report the key
  and line; never fall back to (a) or (c) without sign-off.
- "two" → "three" at every counting site in Revision r1 item 1, including `skills/genie-code-environment/SKILL.md:368`;
  `00-overview.md:59` unchanged (RULE_9 App-deploy topic). Mirrored carve-out (3) text at the other counting sites
  must also avoid `createAsset(` (no parenthesis).
- **Tampers:** drop the Q2-a tamper. Add **X-b:** add a parenthesis to the new line (`createAsset(`) → the
  measured INSESSION_CREATE count rises → gate red. Tampers in force: X1–X5 + X-b.
- Frontmatter: as planned (re-quote `deploy_note` only; YAML parses; every other value unchanged).
- **Release:** TPL PR into TPL `feature/genie-code-mcp-integration` from 3f6ba0a; reviewer ACCEPT + gatekeeper
  PASS (after any signed re-lock fix-up); merge only. THEN a small TPL RC, integration → TPL main, one review +
  gate; the human merges it.

## M0 STOP ruling (human, 2026-10-15; D-193) — overrides earlier sections where they differ

M0 (base 3f6ba0a + APP 2e3397f) stopped on two over-lock keys outside the B5 table. Ruling = option 1:
- **APP seed for every measurement: 7e2397a** (current APP integration head). Its seed is byte-identical to 2e3397f
  (`git diff 2e3397f 7e2397a -- db/lakebase/dml_seed` is empty; #160/#161 changed no seed). State that in the PR body.
- **Six keys in the table now:** the four B5 keys plus `apps_lakebase::APP_DEPLOY` (1697 → 1857) and
  `apps_lakebase::LOCAL_AUTH` (76 → 99), each attributed line by line like the others. The Item 1 step 1 STOP now
  applies only to over-lock keys outside these six.
- **Classification for every over-lock line (replaces a/b/c):**
  - **(a) template text** → fix in this PR if in scope (e.g. BARE_ARTIFACT_PATH → `<ARTIFACT_ROOT>`); otherwise list it.
  - **(b) APP-seed text counted twice by the raw-seed + extracted-section measurement (D-61)** → APP follow-up list,
    each with seed row id, version, and whether that version is superseded.
- **No re-locks** unless the human signs individual rows (unchanged).
- Then continue with the content fixes, the vibecoding-state frontmatter, and carve-out (3) as signed (Q2 = (b)).
- **Cross-check APPROVED, fresh folder per measurement:** every measurement runs in a NEW scratch folder under
  `FORGE/work/scratch/<slug>-<sha>/` (e.g. `FORGE/work/scratch/tpl-gate-overages-followup-de70b96/`,
  `…-7e2397a/`). Never delete or reset a folder; create a new one each run. Run the de70b96 measurement this way
  and confirm it reproduces the RC #21 B5 table (head 3f6ba0a column: GENIE_RESOURCE 8 → 14, BARE_ARTIFACT_PATH
  8 → 10, skills::APP_DEPLOY 108 → 114, skills::INSESSION_CREATE 14 → 17, total 3575 → 3446). If it does not
  reproduce, STOP and report; do not proceed on unexplained numbers.
- **Out of scope, record only** in the PR body: absolute-gate failures at base — fork intent-parity on
  `99-activation_reverse_sync`, deploy-fork discipline on `99-gaccel_productionize` (3), state-persistence on 19 forks.
- A1 now reads: M0 at APP 7e2397a pasted (and the de70b96 reproduction pasted); A2 covers all six keys.

## Fix-up r1 — signed re-locks and the final A8 rule (human, 2026-10-15; D-196)

- **R1 SIGNED:** `skills::APP_DEPLOY` lock 108 → 114. Reason: findings-log lines in
  `skills/genie-code-environment/SKILL.md` (:478, :486–490); the regex hits `app.yaml` / `appkit` substrings, not a
  deploy path; the lock in 1d6ee10 was set below the tree count.
- **R2 SIGNED:** `skills::INSESSION_CREATE` lock 14 → 17. Reason: `skills/SKILL.md:34` is a privilege name; :82 and
  :93 are filter literals; false positives; tidy queued as tpl-stray-skill-file.
- **One fix-up commit** on #23: edit `scripts/genie_gate_baseline.json` `by_area_class` for exactly these two keys
  (`by_class` and `total` kept arithmetically consistent: +6 and +3), nothing else; commit this plan file updated
  (byte-identical to the lead copy); in the PR body, mark R1 and R2 "SIGNED (human, D-196)" with the reasons above.
  Trunk exception for `scripts/genie_gate_baseline.json` applies (signed keys only).
- **Final A8 rule:** (i) the Tier-3 `createAsset(` token is byte-identical to base; (ii) any added wording on that row
  has no `createAsset(` (count word and the carve-out (3) mention are allowed); (iii) no counted line is added.
  Retrospectives text is never a gate subject beyond this. Carve-out (3) text itself has no `createAsset(` anywhere.
- **A10:** no-regression (D-195): `scripts/verify_agent_track_flow.py` fails identically at base and head.
- **A5 after the fix-up:** with APP seed 7e2397a, the absolute gate is over lock only on the three apps_lakebase
  (b) keys (GENIE_RESOURCE, APP_DEPLOY, LOCAL_AUTH), which go to genie-gate-absolute-dedupe; exit 1 for those is
  expected and stated.
- Then ONE full re-review + re-gate on the new head; merge only.

## Critic questions
(a) Do the B5 numbers still hold at APP 2e3397f, and does the measuring method (raw seed extract) match how
genie_gate.py actually reads APP content? (b) Are `:426`, `genie-code-environment/SKILL.md:368` and
`00-overview.md:34-40` the only "two/one exception" sites? (c) Which audit class will carve-out (3) hit, given
`RULE_10_SANCTIONED` at `scripts/audit_genie_compat.py:125`? (d) Does anything parse vibecoding-state frontmatter
(Genie Code loader, scripts)? (e) Is `genie_gate_baseline.json`'s `by_class` / `total` derived arithmetic or
independently locked? (f) Can each tamper turn its check red?
