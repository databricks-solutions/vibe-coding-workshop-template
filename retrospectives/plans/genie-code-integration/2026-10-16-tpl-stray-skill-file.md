# tpl-stray-skill-file — plan r0.1 (2026-10-16; critic ACCEPT r1 + X5/X6, M3 site named)

repo=template · base origin/feature/genie-code-mcp-integration (759a14e)
PR plan path: retrospectives/plans/genie-code-integration/2026-10-16-tpl-stray-skill-file.md
Status: PLAN ONLY. Build only after the human signs (D-206).

## Facts (at 759a14e)
- `skills/SKILL.md` (345 lines) is a Lakebase Change Data Feed doc ("Lakebase CDF — Sync Postgres to Unity
  Catalog"), added in 17363b4 (2026-06-30, "Add files via upload"), its only commit. No YAML frontmatter
  (no `name`/`description`). Every sibling skill (`databricks-asset-bundles`, `databricks-expert-agent`,
  `genie-code-environment`, `vibecoding-state`) is a folder with `SKILL.md` + frontmatter.
- No file in the template or app references `skills/SKILL.md` by path (the only hit is the #23 plan's R2 note).
  The app seed's 61 `readSkillFile("skills/vibe-coding-workshop/skills/...")` calls name only the four folder
  skills.
- It is NOT a duplicate: no other template file covers Lakebase CDF (`wal2delta`, `_pg_change_type`,
  `lb_<table>_history`). Its content is what the `sync_from_lakebase` Genie Code fork (app input_id 931, CDF
  branch gated by `{enable_lakebase_cdf}`, state-template.md:175) inlines at seed lines ~19318-19356.
- Genie Code auto-loads every `SKILL.md` under the `.assistant/skills` copy (AGENTS.md:228). A frontmatter-less
  SKILL.md at the skills root is therefore discovered with no name/description to route on.
- Its 3 `skills::INSESSION_CREATE` hits (:34 privilege name `CREATE TABLE`, :82 and :93 event-trigger filter
  literals) are false positives (R2, signed lock 17).

## Proposal (recommended: M — move, not remove)
M1. `git mv skills/SKILL.md skills/lakebase-cdf/SKILL.md` (history kept).
M2. Prepend frontmatter in the sibling style:
    ```
    ---
    name: lakebase-cdf
    description: Lakebase Change Data Feed (CDF) — stream INSERT/UPDATE/DELETE from Lakebase Postgres via the WAL
      (wal2delta) into Unity Catalog lb_<table>_history Delta tables. Use for the sync_from_lakebase step when
      enable_lakebase_cdf is true: prerequisites (Postgres 17 autoscaling, non-default-storage catalog, REPLICA
      IDENTITY FULL), schema-level enablement, verifying STREAMING in wal2delta.tables, consuming _pg_* columns,
      disabling, and the clone fallback.
    metadata:
      author: prashanth subrahmanyam
    ---
    ```
    Body byte-identical to today (proof: `git diff -M` shows 100% rename similarity apart from the frontmatter;
    `tail -n 345` equals the old file).
M3. Add `lakebase-cdf` to the root-skills list at AGENTS.md:234 (`| skills/ | Controller + cross-cutting: ... |`,
    critic-confirmed). Implementer also greps README / other lists and reports any further site.
M4. No app change in this PR. Queued app follow-up (not built): the 931 CDF branch could `readSkillFile` the new
    path instead of inlining, a seed change for a later signed task.

Alternative R (remove): rejected unless the human prefers it — the doc is unique, matches a live fork, and is
needed if `enable_lakebase_cdf=true`. Removal would drop `skills::INSESSION_CREATE` to 14 (slack lock).

## Gate effect (expected, measured before commit)
- The three flagged lines keep their exact text and key (`skills::INSESSION_CREATE`): area is the top folder
  `skills`, unchanged by the move. Diff gate: exit 0, counted lines unchanged, 0 added (the frontmatter adds no
  flagged line; if it does, STOP and report key + line — no reworded block, no waiver).
- Absolute gate: unchanged per key.

## Acceptance
- A1 scope: the rename, the frontmatter, the plan, and (only if found) the M3 list row.
- A2 frontmatter parses as YAML with `name` == folder name; `description` ≤ 1024 chars.
- A3 body byte-identical to `origin/...:skills/SKILL.md`.
- A4 no file left at `skills/SKILL.md`; grep for `skills/SKILL.md` finds only retrospectives/plans text.
- A5 diff gate (FORGE genie_gate_diff, app seed 7e2397a) exit 0; counted lines and fork findings unchanged.
- A6 absolute gate per-key counts identical to base.
- A7 `verify_agent_track_flow.py`: same result as base (known pre-existing failure).

## Tampers
- X1 drop `name:` from the frontmatter → A2 red.
- X2 change one body byte → A3 red.
- X3 leave a copy at `skills/SKILL.md` → A4 red.
- X4 add `createAsset(` to the description → A5 red (+1 counted line).
- X5 (critic) omit the AGENTS.md:234 row addition → A1/M3 red.
- X6 (critic) remove `CREATE TABLE` from the moved file's privilege table (old :34, now ~:43) → A6 red (count 17 → 16) and A3 red.

## Question for sign-off
- Q1 M (move + frontmatter, recommended) or R (remove)?
- Q2 folder name `lakebase-cdf`, or another?
- Ships with the next small template RC.

## SIGNED (human, 2026-10-16, D-209) — r1
- Q1 MOVE: `git mv skills/SKILL.md skills/lakebase-cdf/SKILL.md`, body byte-identical, frontmatter in the house style
  (`name`, `description`, `metadata.author`).
- Q2 folder `lakebase-cdf`. The description must say WHEN to load it: Lakebase change data feed into Unity Catalog
  (wal2delta, `lb_<table>_history` tables), i.e. the `sync_from_lakebase` step with `enable_lakebase_cdf=true`.
  (The M2 draft already does; keep that clause explicit and first-sentence-adjacent.)
- AGENTS.md:234 row as in r0.1; tampers X1–X6 as written.
- Release: review + gate, merge only into TPL integration; then the next small template RC for the human's merge.
