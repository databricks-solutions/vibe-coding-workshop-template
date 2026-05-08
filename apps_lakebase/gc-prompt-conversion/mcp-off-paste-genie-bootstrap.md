# Genie Code — Paste scaffold (supplement)

**Canonical bootstrap:** Paste **Cell 1–3** from [`workshop-variables.md`](workshop-variables.md). That defines `w`, `APP_*`, `write_file`, `sdk_preflight_app_folder`, `ensure_app_active`, **`validate_and_deploy()`** (SDK preflight + `create_and_wait` + `deploy_and_wait`), and `verify_postgres_resource`. **This file does not replace `workshop-variables.md`** — it only documents the **paste-a-tree** pattern for bulk `write_file` loops.

---

## When to use the `FILES` dict pattern

Use a Python dict of **relative path → full file body** when bulk-writing many files (e.g. after reading `apps_lakebase/skills/01-appkit-scaffold/SKILL.md` and synthesizing the tree, or pasting JSON exported elsewhere with the same `files[]` / `path` / `contents` shape).

```python
w.workspace.mkdirs(APP_BASE)

FILES = {
    # "package.json": '''{ ... }''',
    # "app.yaml": '''...''',
    # "app.ts": '''...''',
    # "client/index.html": '''...''',
    # ... server/, client/src/, etc.
}

for rel, body in FILES.items():
    write_file(f"{APP_BASE}/{rel}", body)
```

Then:

```python
bad = sdk_preflight_app_folder(APP_BASE)
assert not bad, bad
deployment, app_url = validate_and_deploy(APP_NAME, APP_BASE)
```

---

## JSON shape (optional)

If you have a single JSON string (historically similar to old MCP scaffold output):

```python
import json

raw = """{ "files": [ {"path": "package.json", "contents": "..."}, ... ] }"""
data = json.loads(raw)
w.workspace.mkdirs(APP_BASE)
for f in data["files"]:
    write_file(f"{APP_BASE}/{f['path']}", f["contents"])
```

---

## Permissions

The **app’s service principal** must read `APP_BASE` during deploy-time build. See `.assistant_instructions.md` Deploy Rules and [`troubleshooting_gc.md`](troubleshooting_gc.md).

---

## Lakebase / plugins

No MCP tools — follow [`GENIE-CODE-OVERRIDES.md`](GENIE-CODE-OVERRIDES.md) and the numbered prompts (`setup_lakebase_gc.md`, …) using **`w.database`**, **`w.postgres`**, **`w.apps`**, and `write_file()` only.
