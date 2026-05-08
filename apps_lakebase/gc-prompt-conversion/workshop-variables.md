# Workshop Variables — apps_lakebase Standard Setup

**Read this BEFORE following any prompt in `apps_lakebase/prompts/`.** Defines `APP_*`, `REPO_ROOT`, `APP_BASE`, `write_file()`, and **`validate_and_deploy()`** (SDK preflight + Apps deploy). Scaffold from `apps_lakebase/skills/*/SKILL.md` + `write_file()`; Lakebase from `w.postgres` / `w.database` / `w.apps` per each `*_gc.md` prompt and **`GENIE-CODE-OVERRIDES.md`**.

> **Companion:** Read `@apps_lakebase/gc-prompt-conversion/gc-prompt-header.md` first for environment constraints and error-handling protocol.

---

## Three-Cell Bootstrap

Every prompt must run these three cells (in separate cells) before doing anything else:

```python
# Cell 1 — install packages (own cell, run first)
%pip install databricks-sdk --upgrade -q
```

```python
# Cell 2 — restart the kernel (recommended after SDK upgrade)
dbutils.library.restartPython()
```

```python
# Cell 3 — re-derive variables AND helpers AFTER restart (Python state was wiped)
# Paste the entire block below into Cell 3.

import base64
import time

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.workspace import ImportFormat
from databricks.sdk.service.apps import App, AppDeployment

w = WorkspaceClient()

email = spark.sql("SELECT current_user()").collect()[0][0]
prefix = email.split("@")[0].replace(".", "-")
parts = prefix.split("-")
APP_NAME = f"{parts[0]}-{parts[-1][0]}-booking-app"[:26]
DB_SCHEMA = APP_NAME.replace("-", "_")
REPO_ROOT = f"/Workspace/Users/{email}/v2v-in-geniecode/vibe-coding-workshop-template"
APP_BASE = f"{REPO_ROOT}/apps_lakebase/{APP_NAME}"


def write_file(path, content):
    """Write a plain text file (TypeScript, JSON, YAML, markdown) to the workspace.
    Creates parent dirs automatically. Encodes content to base64 for the SDK."""
    parent = "/".join(path.split("/")[:-1])
    w.workspace.mkdirs(parent)
    w.workspace.import_(
        path=path,
        content=base64.b64encode(content.encode()).decode(),
        format=ImportFormat.AUTO,
        overwrite=True,
    )
    print(f"\u2713 Wrote {path.split('/')[-1]}")


def sdk_preflight_app_folder(app_base):
    """Lightweight required-file checks before deploy. Returns list of error strings."""
    errs = []
    required = [
        f"{app_base}/app.yaml",
        f"{app_base}/package.json",
        f"{app_base}/app.ts",
        f"{app_base}/client/index.html",
        f"{app_base}/server/server.ts",
    ]
    for p in required:
        try:
            w.workspace.get_status(p)
        except Exception as e:
            errs.append(f"missing or unreadable: {p} ({e})")
    return errs


def ensure_app_active(app_name, max_wait_minutes=10):
    """Start the app if STOPPED, poll compute_status until ACTIVE.

    Uses .state.name (returns "ACTIVE") — NEVER str(state) (returns
    "ComputeState.ACTIVE") which never matches and infinite-loops.

    Returns the final compute state string.

    Replaces the ~12-line ensure-active block duplicated in
    `one-ui-design-local.md` and `deploy_and_test_gc.md`.
    """
    app = w.apps.get(app_name)
    compute = app.compute_status.state.name if app.compute_status and app.compute_status.state else "UNKNOWN"
    if compute == "ACTIVE":
        return compute

    print(f"App compute is {compute}, starting...")
    w.apps.start(app_name)
    iters = max(1, int((max_wait_minutes * 60) / 15))
    for i in range(iters):
        time.sleep(15)
        app = w.apps.get(app_name)
        compute = app.compute_status.state.name if app.compute_status and app.compute_status.state else "UNKNOWN"
        print(f"  [{i:2d}] {compute}")
        if compute == "ACTIVE":
            return compute
        if compute in ("STOPPED", "ERROR"):
            w.apps.start(app_name)
    return compute


def validate_and_deploy(app_name, app_base, description="StayFindr -- AppKit booking app"):
    """End-to-end deploy contract for AppKit apps via Workspace Apps API (SDK).

    Steps:
      1. sdk_preflight_app_folder(app_base) — required paths exist
      2. w.apps.get(app_name) or w.apps.create_and_wait(...) if missing
      3. ensure_app_active(app_name)
      4. w.apps.deploy_and_wait(app_name=..., app_deployment=AppDeployment(source_code_path=app_base))
      5. Return (deployment, app_url)

    Collapses the validate+create+activate+deploy block in
    `one-ui-design-local.md` and `deploy_and_test_gc.md` into a single call.

    REQUIRES: `w` in scope (paste Cell 3 after pip + restart).
    """
    print(f"Preflight {app_name} (SDK file checks)...")
    bad = sdk_preflight_app_folder(app_base)
    if bad:
        raise RuntimeError("sdk_preflight failed:\n  " + "\n  ".join(bad))
    print("Preflight OK")

    try:
        app = w.apps.get(app_name)
        print(f"App exists: {app_name}")
    except Exception:
        print(f"Creating app {app_name}...")
        w.apps.create_and_wait(
            app=App(name=app_name, description=description, default_source_code_path=app_base)
        )
        print(f"\u2713 App created")

    ensure_app_active(app_name)

    print(f"Deploying {app_name}...")
    deployment = w.apps.deploy_and_wait(
        app_name=app_name,
        app_deployment=AppDeployment(source_code_path=app_base),
    )
    state = deployment.status.state.name if deployment.status and deployment.status.state else "UNKNOWN"
    app_url = w.apps.get(app_name).url
    print(f"\u2713 Deploy: {deployment.deployment_id} -- {state}")
    print(f"  URL: {app_url}")
    return deployment, app_url


def verify_postgres_resource(app_name):
    """Print pass/fail for postgres-type resource binding.

    AppKit's lakebase() plugin REQUIRES a postgres-type AppResource.
    A database-type binding causes ConfigurationError at startup -- the
    most common Lakebase wiring failure in the workshop.

    Returns True if a postgres resource is bound, False otherwise.

    Replaces the 10-15 line verification block duplicated in
    `setup_lakebase_gc.md` Step 5 and `deploy_and_test_gc.md` Step 3 + 6b.
    """
    app = w.apps.get(name=app_name)
    has_postgres = False
    for r in (app.resources or []):
        if r.postgres:
            print(f"  \u2713 Resource '{r.name}' \u2192 postgres type, branch={r.postgres.branch}, db={r.postgres.database}")
            has_postgres = True
        elif r.database:
            print(f"  \u2717 Resource '{r.name}' \u2192 database type -- WRONG. AppKit needs postgres type.")
            print(f"    Fix: re-run setup_lakebase_gc.md Step 2c to rebind as AppResourcePostgres")
    if not has_postgres:
        print("  \u2717 No postgres resource found -- app will crash with ConfigurationError. Run setup_lakebase_gc.md Step 2.")
    return has_postgres


print(f"APP_NAME:  {APP_NAME}")
print(f"DB_SCHEMA: {DB_SCHEMA}")
print(f"REPO_ROOT: {REPO_ROOT}")
print(f"APP_BASE:  {APP_BASE}")
```

---

## Helper Quick Reference

| Helper | Purpose | Notes |
|--------|---------|-------|
| `write_file(path, content)` | Write workspace file (.ts, .json, .yaml, .md) | Replaces shell `echo`/`import`; use for all scaffolding |
| `sdk_preflight_app_folder(app_base)` | Verify required app files exist before deploy | Same intent as manual `app.yaml` / tree validation |
| `ensure_app_active(app_name)` | Start app if STOPPED, poll compute until ACTIVE (uses `.state.name`) | Collapses duplicated activate+polling snippets |
| `validate_and_deploy(app_name, app_base)` | Preflight + create-if-missing + ensure ACTIVE + `deploy_and_wait` + URL | **Only** supported deploy path in Genie prompts |
| `verify_postgres_resource(app_name)` | Check resource binding is `postgres`-type (not `database`) | Collapses duplicated resource-inspection snippets |

---

## AppKit Constraints Cheat-Sheet (for `validate_and_deploy` users)

| Rule | Why |
|------|-----|
| Use `.state.name` for compute polling, NEVER `str(state)` | `str(state)` returns `"ComputeState.ACTIVE"`, breaks `== "ACTIVE"` checks |
| Wrap `source_code_path` in `AppDeployment(source_code_path=...)` | `deploy_and_wait()` rejects it as a top-level kwarg |
| `app.yaml` env: `LAKEBASE_ENDPOINT` with `valueFrom: postgres` (NOT `valueFrom: database`) | `lakebase()` plugin requires postgres-type resource binding |
| `app.ts` plugin order: `lakebase()` BEFORE `server()` | `appkit.lakebase` must exist when routes register |
| `app.ts` (Lakebase wired): **`await createApp({... onPluginsReady ...})`** | Without `await`, `tsx` can finish before routes bind — `/api/health` 404 or perpetual **Mock Data**. Do **not** use bare `createApp({...})`. Do **not** use `.then()` chains for this workshop |
| `package.json` build script: `"(npm run typegen || true) && vite build"` | `appkit build` does not exist; typegen failures must not block vite |
| `app.yaml` command: `["./node_modules/.bin/tsx", "app.ts"]` (NOT `npx`) | `npx` not on PATH at runtime |
