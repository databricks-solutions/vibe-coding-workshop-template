# AppKit + Lakebase workshop (Genie Code overview)

This document is **orientation only** for **Databricks Genie Code**. It does **not** replace executable prompts or skills under [`skills/`](skills/).

**First read:** [`gc-prompt-conversion/GENIE-CODE-OVERRIDES.md`](gc-prompt-conversion/GENIE-CODE-OVERRIDES.md) — maps CLI / `npm` / localhost patterns in skills to **Databricks SDK** patterns that work in notebooks.

## Run the workshop (Genie)

1. **Workspace prep:** [PRE-REQUISITES.md](../PRE-REQUISITES.md) (foundation).
2. **Prompt order and `@` links:** [`prompts/README.md`](prompts/README.md) — canonical sequence (recommended UI: `one-ui-design-local.md`).
3. **Variables + helpers** (`APP_NAME`, `REPO_ROOT`, `validate_and_deploy`, etc.): [`gc-prompt-conversion/workshop-variables.md`](gc-prompt-conversion/workshop-variables.md).
4. **CLI → notebook mapping:** [`gc-prompt-conversion/GENIE-CODE-OVERRIDES.md`](gc-prompt-conversion/GENIE-CODE-OVERRIDES.md) — standard track is SDK-only (**MCP out of scope**).
5. **Errors:** [`gc-prompt-conversion/troubleshooting_gc.md`](gc-prompt-conversion/troubleshooting_gc.md).

**Legacy facilitator-only (do not prepend to Genie context):** [pre-req-mcp-setup.md](../pre-req-mcp-setup.md), [`prompts/mcp-setup-gc.md`](prompts/mcp-setup-gc.md), [`gc-prompt-conversion/MCP-appkit_tooling.md`](gc-prompt-conversion/MCP-appkit_tooling.md).

**Lifecycle (summary):** PRD → scaffold/UI + mock deploy → Setup Lakebase → Wire Lakebase → Deploy + E2E. **Executable** steps live only in [`prompts/`](prompts/) (`*_gc.md`).

**Optional:** `apps_lakebase/<APP_NAME>/.vibecoding-state.md` — append `APP_NAME`, URLs, and fixes between prompts if your team uses it.

## CLI / local IDE (not Genie)

Use [QUICKSTART.md](../QUICKSTART.md) Path A and skills under [`skills/`](skills/) (run CLI/npm steps on your machine per each `SKILL.md`).

---

*Trimmed May 2026 for Genie-first maintenance. Original extended workshop narrative lives in git history; runnable Genie content is `prompts/` + `gc-prompt-conversion/`.*

**Created by:** Prashanth Subrahmanyam (original workshop).
