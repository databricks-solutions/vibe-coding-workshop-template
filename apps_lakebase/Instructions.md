# AppKit + Lakebase workshop (Genie Code overview)

Orientation for **Genie Code** — runnable steps are in [`prompts/`](prompts/) (`*_gc.md`); skills under [`skills/`](skills/) are the **CLI/local** reference.

## Run the workshop (Genie)

1. [PRE-REQUISITES.md](../PRE-REQUISITES.md) — workspace / UC / compute.
2. [`prompts/README.md`](prompts/README.md) — prompt order (start with `generate_prd_gc.md` → `one-ui-design-local.md` → …).
3. [`gc-prompt-conversion/workshop-variables.md`](gc-prompt-conversion/workshop-variables.md) — Cell 1–3 (`w`, `write_file`, **`validate_and_deploy`**).
4. [`gc-prompt-conversion/GENIE-CODE-OVERRIDES.md`](gc-prompt-conversion/GENIE-CODE-OVERRIDES.md) — when a skill mentions CLI/npm/shell.
5. [`gc-prompt-conversion/troubleshooting_gc.md`](gc-prompt-conversion/troubleshooting_gc.md) — on any error.

**Lifecycle:** PRD → scaffold/UI + mock deploy → Lakebase setup → wire backend → deploy + E2E.

**Optional:** `apps_lakebase/<APP_NAME>/.vibecoding-state.md` between steps if your team uses it.

## CLI / local IDE (not Genie)

Use [QUICKSTART.md](../QUICKSTART.md) Path A and skills under [`skills/`](skills/) (run CLI/npm steps on your machine per each `SKILL.md`).

---

*Trimmed May 2026 for Genie-first maintenance. Original extended workshop narrative lives in git history; runnable Genie content is `prompts/` + `gc-prompt-conversion/`.*

**Created by:** Prashanth Subrahmanyam (original workshop).
