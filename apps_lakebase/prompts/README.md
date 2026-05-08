# Genie Code prompts (`apps_lakebase/prompts/`)

Workshop prompts for **Genie Code** (Databricks notebooks + **Databricks SDK** only — no `mcp-appkit-skill`). **Local IDE + CLI:** follow [`apps_lakebase/skills/`](../skills/) (same lifecycle; run shell/CLI on your machine per each `SKILL.md`).

**`REPO_ROOT` / `APP_BASE` / facilitator paths:** Maintain these **only** in [`../gc-prompt-conversion/workshop-variables.md`](../gc-prompt-conversion/workshop-variables.md) (Cell 3 derivation). Do not duplicate or drift copies in other files.

## Standard references (paste once per notebook / link in every prompt)

In Genie Code, use **`@`** paths from the repo root so files resolve reliably:

| Doc | Purpose |
|-----|---------|
| `@apps_lakebase/gc-prompt-conversion/gc-prompt-header.md` | Environment forbid-list, SDK deploy contract |
| `@apps_lakebase/gc-prompt-conversion/workshop-variables.md` | `%pip` / restart / `APP_NAME` / `write_file` / `validate_and_deploy()` |
| `@apps_lakebase/gc-prompt-conversion/GENIE-CODE-OVERRIDES.md` | CLI → SDK; **explicit MCP forbid-list** for Genie |
| `@apps_lakebase/gc-prompt-conversion/troubleshooting_gc.md` | Error catalog |

**Genie agents:** Do **not** open `MCP-appkit_tooling.md` or `mcp-setup-gc.md` as part of setup — both teach MCP `DatabricksMCPClient` / `appkit_*` tools and derail SDK-only flows. Humans use those only when running the legacy facilitator MCP track.

## Recommended workshop order (Genie)

Start here (standard track uses **Databricks SDK only** — no MCP install):

1. `@apps_lakebase/prompts/generate_prd_gc.md`
2. `@apps_lakebase/prompts/one-ui-design-local.md` — single prompt for scaffold + UI + mock deploy
3. `@apps_lakebase/prompts/setup_lakebase_gc.md`
4. `@apps_lakebase/prompts/wire_ui_to_lakebase_gc.md`
5. `@apps_lakebase/prompts/deploy_and_test_gc.md`

## Main sequence (CLI names → Genie)

| Step | Typical CLI / local doc name | This folder (Genie) |
|------|------------------------------|---------------------|
| PRD | product requirements | `generate_prd_gc.md` |
| UI + mock deploy | UI design + mock deploy | **`one-ui-design-local.md`** |
| Setup Lakebase | setup Lakebase | `setup_lakebase_gc.md` |
| Wire Lakebase | wire UI to Lakebase | `wire_ui_to_lakebase_gc.md` |
| Deploy + E2E | deploy and test | `deploy_and_test_gc.md` |

## Supporting files

| File | Note |
|------|------|
| `mcp-setup-gc.md` | **Facilitator / legacy MCP only** — not part of Genie `@` preamble |
| `cleanup-gc.md`, `new_exec_steps.md` | Facilitator / operational |
| `design_prd.md`, `ui_design.md` | Samples / scaffolding (not substitutes for `docs/` in repo root) |

Skills under `apps_lakebase/skills/` are **not** edited for Genie; behavior differences are covered by `GENIE-CODE-OVERRIDES.md` and these prompts.
