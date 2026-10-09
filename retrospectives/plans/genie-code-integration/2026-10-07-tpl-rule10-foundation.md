# tpl-rule10-foundation: RULE_10 second carve-out for idempotent foundation provisioning (D-56)

repo=template · base origin/feature/genie-code-mcp-integration @775bebc · plan path in PR: retrospectives/plans/genie-code-integration/2026-10-07-tpl-rule10-foundation.md (force-add; retrospectives/ is git-ignored, as #18)
Trunk files touched: NONE (scripts/genie_gate.py and scripts/genie_gate_baseline.json stay byte-identical).

## Human ruling (verbatim intent)
RULE_10 gets a second carve-out for idempotent foundation provisioning: CREATE ... IF NOT EXISTS of the participant's own prefixed schema/volume, both clients, nothing else. Amend RULE_10 (decision table and overview summary) and record these INSESSION_CREATE findings as sanctioned so the gate no longer counts them as growth.

## Evidence (lead, read-only @775bebc + the human's disk copy of 00-overview)
- 00-overview.md is untracked (`.gitignore:99 retrospectives`; never in any commit). RULE_10 row :149 says "Sole carve-out: the RULE_8 Tier 3 Genie-Space createAsset". Locked decision 1 (:40-43) says "No in-session artifact creation (RULE_10) — sole carve-out: RULE_8 Tier 3".
- Learner-facing tracked copy: skills/databricks-asset-bundles/SKILL.md:97-103 "### No in-session artifact creation (RULE_10)" … "The **sole carve-out** is a Genie Space via `createAsset` (RULE_8 Tier 3)".
- scripts/audit_genie_compat.py:98-102 INSESSION_CREATE = `databricks (jobs|pipelines|schemas|volumes) create | createAsset( | .(jobs|pipelines|schemas|volumes|genie).create( | CREATE (SCHEMA|VOLUME|TABLE)\b` (case-insensitive), one row per matching line.
- FORGE/tools/genie_gate_diff.py compare(): any area::class count that is higher at head, including a key that is new at head, is growth. So a sanctioned line must leave the counted rows; re-classing it under a new class name would itself read as growth.
- genai-agents/foundation/00-uc-resources-foundation/SKILL.md: clients [ide_cli, genie_code]; schemas `${user_schema_prefix}_agent` / `_ops`; idempotency contract :60-61 `CREATE SCHEMA IF NOT EXISTS`, `CREATE VOLUME IF NOT EXISTS`. APP default row 200 names `{lakehouse_default_catalog}.{db_schema}_agent` / `_ops`.

## Changes
S1 scripts/audit_genie_compat.py (not trunk): add `RULE_10_SANCTIONED`, a short list of compiled regexes, and in scan(), when a line matches INSESSION_CREATE AND a sanctioned regex, do NOT append an INSESSION_CREATE row; append it instead to a module-level `SANCTIONED` list (file, line, rule="RULE_10_foundation_carveout", text), which main() prints as its own section ("sanctioned in-session creation, not counted") and writes to the CSV with class `SANCTIONED_RULE_10` ONLY IF genie_gate.current_counts() is proven not to count it (it counts every non-READ_ERROR row returned by scan(), so the simplest correct form is: scan() never returns sanctioned rows; a separate `scan_sanctioned()` returns them). Other patterns on the same line are still evaluated and counted as before.
  The sanctioned regex is NARROW. A line is sanctioned only if ALL hold:
  (a) it contains `CREATE\s+(SCHEMA|VOLUME)\s+IF\s+NOT\s+EXISTS\s+` immediately followed by an identifier (optionally back-quoted) whose SCHEMA segment begins with a per-user prefix token from an explicit allowlist (measured from the tree and the APP seed: expected `{db_schema}`, `${user_schema_prefix}`, `{user_schema_prefix}`; list each token with where it is used; no wildcard);
  (b) the line contains no other INSESSION_CREATE trigger (no `CREATE TABLE`, no `createAsset(`, no `.create(`, no `databricks … create`);
  (c) it is case-insensitive like the base pattern.
  Not sanctioned (stays counted): CREATE TABLE …; CREATE SCHEMA/VOLUME without IF NOT EXISTS; an identifier whose schema segment is not a prefix token (e.g. `main.shared`, `{catalog}.{schema}`); any SDK `*.create(` call including `w.volumes.create(`; prose that names the statement without an identifier right after it.
S2 00-overview.md (force-add the human's disk copy, then edit only these two places): RULE_10 decision-table row: "Sole carve-out" → "Two carve-outs: (1) RULE_8 Tier 3 … (unchanged text); (2) idempotent foundation provisioning: `CREATE SCHEMA IF NOT EXISTS` / `CREATE VOLUME IF NOT EXISTS` of the participant's own prefixed schema/volume (`{user_schema_prefix}_…`), on both clients, nothing else (no tables, jobs, pipelines, SDK create calls or unprefixed names); the audit lists these as sanctioned and does not count them (scripts/audit_genie_compat.py RULE_10_SANCTIONED)." Locked decision 1 summary: same two carve-outs in one sentence. No other edit to the file (the diff vs the disk copy is exactly these two hunks; say so in the PR body with the disk copy's sha256).
S3 skills/databricks-asset-bundles/SKILL.md RULE_10 section (:97-103): "sole carve-out" → the two carve-outs, same wording as S2; nothing else in the file.
S4 Plan file at the plan path above (force-add).
S5 (round 2, critic r1 findings 1-2) genai-agents/foundation/00-uc-resources-foundation/SKILL.md: bring the skill's own provisioning code inside the carve-out, with no behaviour change other than the API used. (i) The schema DDL line (~:148 `f"CREATE SCHEMA IF NOT EXISTS {uc_catalog}.{schema} "`) names the prefixed schema explicitly, e.g. `f"CREATE SCHEMA IF NOT EXISTS {uc_catalog}.{user_schema_prefix}_{suffix}"` for suffix in (agent, ops), so the prefix token is on the line. (ii) The volume step (~:154-:180, `w.volumes.create(` + `except AlreadyExists`) becomes `CREATE VOLUME IF NOT EXISTS {uc_catalog}.{user_schema_prefix}_{suffix}.{volume}` run through the same `w.statement_execution` path as the schemas (a managed volume, as today); drop the now-unused AlreadyExists import only if nothing else uses it. (iii) Prose that describes the mechanism (deploy_note :14 "created via SDK/DDL", :60-61 "AlreadyExists is treated as success", the flow diagram if it names the SDK call) says DDL `IF NOT EXISTS`. Nothing else in the skill (inputs, outputs, captured map, gates) changes. `{schema}` is NOT added to the prefix allowlist: a bare `{schema}` is not provably the participant's prefix, and the ruling admits prefixed names only.

## Acceptance
A1 genie_gate_diff (template mode) exits 0: `python3 FORGE/tools/genie_gate_diff.py --base-ref origin/feature/genie-code-mcp-integration --head-ref <head commit> --base-seed <APP origin/feature/genie-code-mcp-integration seed copy> --work FORGE/work/tpl-rule10-foundation-genie`; no key grows; the PR lists every key whose count FELL, with the delta and every newly sanctioned line (file:line:text). Expected: only *::INSESSION_CREATE keys fall, and only by lines of the S1 shape.
A2 `python3 scripts/genie_gate.py` at head: no regression vs the unchanged baseline (counts only fall).
A3 A probe file outside the repo (FORGE/work/tpl-rule10-foundation-probe/…, never committed) run through scan() shows: `CREATE SCHEMA IF NOT EXISTS {lakehouse_default_catalog}.{db_schema}_agent` → sanctioned; `CREATE VOLUME IF NOT EXISTS {lakehouse_default_catalog}.{db_schema}_agent.ka_source` → sanctioned; each "not sanctioned" form in S1 → counted INSESSION_CREATE.
A4 genie_gate.py and genie_gate_baseline.json byte-identical to base; apps_lakebase/prompts/ untouched; only the 5 files of S1-S5 in the diff.
A5 (round 2, critic r1 finding 3) 00-overview.md vs the human's disk copy: the PR body records the disk copy's sha256 at copy time; `diff -U0 <disk copy> <head file> | grep -c '^@@'` = 2 exactly (the RULE_10 row and Locked decision 1), and each hunk touches only those lines.
A6 (round 2) After S5, 00-uc-resources-foundation/SKILL.md has 0 counted INSESSION_CREATE rows from its provisioning code (every remaining counted row in that file is listed in the PR with a reason, e.g. a prose line naming the statement with no identifier, or the "delegate to F0" warning :39-40), and 0 `.volumes.create(`.

## Tampers (expected red; restore each)
X1 widen the sanctioned regex to accept a bare `CREATE SCHEMA IF NOT EXISTS {catalog}.{schema}` (drop the prefix allowlist) → A3 red (an unprefixed form is sanctioned).
X2 allow `CREATE TABLE IF NOT EXISTS {…}.{db_schema}_x.t` in the sanctioned regex → A3 red.
X3 make scan() return sanctioned rows under a new class → genie_gate_diff exits 1 (a new key at head = growth).
X4 drop the IF NOT EXISTS requirement → A3 red.
X5 edit a third place in 00-overview.md → A5 red (`grep -c '^@@'` = 3).
X6 (round 2) restore `w.volumes.create(` in the foundation skill's volume step → A6 red, and that line is counted INSESSION_CREATE (A3-style scan).

## Release
MERGE repo=template reseed=no. No deploy. Exercised by the next app task (p4-agents-a-1009), whose genie gate runs against this merge.

## Reverse
Revert the PR (counts return to the 775bebc numbers; RULE_10 back to one carve-out).
