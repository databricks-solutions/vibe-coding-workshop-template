# Remote push plan — `jai-gc-update`

**Target branch:** [`databricks-solutions/vibe-coding-workshop-template`](https://github.com/databricks-solutions/vibe-coding-workshop-template) → **`jai-gc-update`**  
**Updated:** When you are ready to open a PR or push from your clone (`v2v-workshop-gc`).

**Local repo (May 2026):** `backup_orig_apps_lakebase/`, `backup_orig_data_product_accelerator/`, `apps_lakebase/backup_skills/`, and empty `lakehouse_doc/` were **removed** from this clone. AppKit Genie UI flow is **`one-ui-design-local.md` only** (split `ui_design_build_locally_gc` / `ui_feature_polish_gc` deleted). `apps_lakebase/prompts/` is **tracked in git** (`.gitignore` entry removed). Reference material for `npx @databricks/appkit docs` maps to **`apps_lakebase/skills/*/references/`** via `GENIE-CODE-OVERRIDES.md`. Repo-root **`scripts/`** (Genie Code agent simulator notebooks: `_agent`, `_config`, `_tools`, `run_prompt`) was **removed** from this clone and from the Genie workspace mirror — not required by `*_gc.md` prompts; do not re-add unless you revive that facilitator flow.

## Policy (current)

- **Include** both `**/prompts/` trees (`apps_lakebase/prompts/`, `data_product_accelerator/prompts/`) — Genie workshop prompts are part of the deliverable.
- **Include** both `**/gc-prompt-conversion/` trees.
- **Include** `mcp-appkit-skill/` as a **new top-level folder** on the remote (not on `jai-gc-update` today).
- **Backup trees** above are **not in this repo anymore**; do not reintroduce them unless you intentionally vendor CLI duplicates again.
- **`agentic-framework/`** — content on `jai-gc-update` is **byte-identical** to your clone (same 9 files / same git blob SHAs). **No push required** unless you edit it later.

## Folders / paths to land on remote (checklist)

Use this as a PR file list or `rsync`/import manifest.

| Area | Path | Notes |
|------|------|--------|
| MCP app | `mcp-appkit-skill/` | Entire directory (new on remote). |
| AppKit Genie | `apps_lakebase/gc-prompt-conversion/` | All files. |
| AppKit Genie | `apps_lakebase/prompts/` | All `*.md` (tracked; include on remote). |
| AppKit | _(removed)_ `apps_lakebase/orig_prompts/` | Dropped from this repo; CLI uses `apps_lakebase/skills/` only. |
| AppKit | `apps_lakebase/skills/` | Skill updates (e.g. navigator); also the canonical path for `appkit docs` reference files in Genie overrides. |
| AppKit | `apps_lakebase/Instructions.md` | Minimal Genie overview. |
| AppKit sample | `apps_lakebase/jaiwant-j-booking-app/` | If you keep the sample in-repo. |
| DPA Genie | `data_product_accelerator/gc-prompt-conversion/` | Includes `deploy-assets-cells/`. |
| DPA Genie | `data_product_accelerator/prompts/` | All `*_gc.md`, `README.md`, etc. |
| DPA | _(removed)_ `data_product_accelerator/orig_prompts/` | Dropped; use `data_product_accelerator/skills/` + `prompts/*_gc.md`. |
| DPA | `data_product_accelerator/scripts/` | e.g. `cleanup_workshop_data.py`. |
| DPA | `data_product_accelerator/AGENTS.md` | If changed. |
| Root | `AGENTS.md`, `README.md`, `QUICKSTART.md`, `PRE-REQUISITES.md`, `WORKSHOP-FACILITATOR-GUIDE.md`, `pre-req-mcp-setup.md`, `presentations/workshop.marp.md`, … | As needed for your PR. |
| Root | _(removed)_ `scripts/` | Dropped (May 2026): simulator notebooks were not on `jai-gc-update` and are not referenced by GC prompts. Workspace copy deleted too. |

## Suggested git workflow

```bash
git remote add upstream https://github.com/databricks-solutions/vibe-coding-workshop-template.git   # if not set
git fetch upstream jai-gc-update
git checkout -b pr/jai-gc-update-sync upstream/jai-gc-update
# cherry-pick or copy changes; commit
git push origin pr/jai-gc-update-sync
# open PR → jai-gc-update on GitHub
```

## `gc-prompt-conversion` audit (unused files)

### `apps_lakebase/gc-prompt-conversion/` (5 files)

| File | Used by |
|------|---------|
| `gc-prompt-header.md` | `workshop-variables.md`, `apps_lakebase/prompts/*`, `Instructions.md` |
| `workshop-variables.md` | All AppKit GC prompts, `GENIE-CODE-OVERRIDES.md` |
| `GENIE-CODE-OVERRIDES.md` | Header, prompts, `MCP-appkit_tooling.md` |
| `troubleshooting_gc.md` | Header, prompts, `MCP-appkit_tooling.md` |
| `MCP-appkit_tooling.md` | `mcp-setup-gc.md`, overrides |

**Verdict:** No orphan files; all five are referenced by AppKit Genie prompts and each other.

### `data_product_accelerator/gc-prompt-conversion/` (17 files: 10 under `deploy-assets-cells/` + 7 top-level)

| Path | Used by |
|------|---------|
| `gc-prompt-header.md` | All DPA `*_gc.md` prompts, `workshop-variables` |
| `workshop-variables.md` | All DPA prompts, `lakebase-notebook-connection.md`, troubleshooting |
| `GENIE-CODE-OVERRIDES.md` | Header, prompts, troubleshooting |
| `troubleshooting_gc.md` | Header, prompts, gold pipeline, clone, silver, deploy |
| `lakebase-notebook-connection.md` | extract, clone, troubleshooting, header, overrides |
| `reference_gold_merge_booking_notebook_body.py` | `gold-layer-pipeline-gc.md`, header, troubleshooting, overrides |
| `deploy-assets-cells/README.md` | `deploy-assets-gc.md`, `prompts/README.md` |
| `deploy-assets-cells/*.py`, `verification_appendix.sql` | `deploy-assets-gc.md` (each cell named) |

**Verdict:** No unused files under this folder relative to DPA GC prompts and shared headers/overrides/troubleshooting.

## After push

- Refresh Databricks **Repos** / re-import workspace paths that mirror GitHub.
- Re-run a smoke Genie path: `prompts/README.md` order for each track.
