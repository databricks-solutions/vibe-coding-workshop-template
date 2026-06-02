# Lockfile Hygiene and App Recreation Recovery

Two of the highest-cost failure classes during AppKit deployment are caused by **regenerating `package-lock.json` locally** and by **deleting-and-recreating the app**. Both look harmless, both produce surprising downstream errors, and both are covered by the rules below.

> **Read this when:** preparing to deploy, hitting `ENOTEMPTY` / `Exit handler never called` during platform `npm install`, or when `permission denied for schema` starts appearing after recreating the app.

> **Client note — Genie Code:** Rule 1 (lockfile regeneration) is an **IDE/CLI-only** hazard — Genie Code has no local `npm`, so it never regenerates the lockfile and avoids this class entirely (the build runs server-side). Rule 2 (app-recreation → new SP → Lakebase ownership) applies on **both** clients: avoid deleting/recreating the app regardless of how you deploy.

---

## Rule 1 — Never regenerate `package-lock.json` locally

The Databricks Apps platform runs `npm install` on every deploy inside its own container, using the lockfile you committed. It is optimized for:

1. A lockfile that exists.
2. A lockfile whose registry URLs and resolved versions match what the platform's internal npm cache / registry can serve.

Any local operation that alters registry URLs (switching npm registries, running `npm install` under a different `.npmrc`, deleting the lockfile, or mixing package managers) can break both optimizations simultaneously.

### Failure chain

```
Local: rm -f package-lock.json && npm install @databricks/appkit@latest
  → lockfile regenerated with YOUR registry URLs (e.g., a corporate mirror)
Commit + databricks apps deploy
  → platform runs `npm install` with lockfile
  → platform's internal registry cannot resolve some URLs
  → falls back to full resolution, timeout during tarball extraction
  → ENOTEMPTY: directory not empty, rmdir '.../node_modules/<pkg>'
  → Exit handler never called
  → Deploy fails; subsequent deploys inherit the broken lockfile
```

### Scenario table

| Lockfile state | Platform behavior | Outcome |
|----------------|-------------------|---------|
| Present, matches platform cache | Fast install from cache | Deploy succeeds in seconds |
| Present, mixed / foreign registry URLs | Falls back to full resolve; partial tarballs | `ENOTEMPTY`, `Exit handler never called`, timeout |
| Absent | Full fresh resolve from platform registry | Usually succeeds but slow; may hit timeout on large trees |
| Regenerated locally after switching npm versions or registries | Same as "mixed registries" | Same failure |
| Present but for a different Node/npm major version than platform | Peer-dep warnings; usually OK but flaky | Intermittent fail |

### Pre-deploy check

```bash
# Warn if lockfile was modified locally but not committed
test -f package-lock.json && git diff --quiet -- package-lock.json \
  || echo "WARN: package-lock.json modified locally; review references/lockfile-and-recreation.md before deploy"
```

Add this to your deploy wrapper script (or the CI pre-deploy job) so a regenerated lockfile is surfaced before the platform burns ~3 minutes failing on it.

### Recovery ladder

Apply in order. Escalate only if the previous step fails.

1. **Revert the lockfile.** If `git diff package-lock.json` shows local changes, `git checkout -- package-lock.json` and redeploy.
2. **Delete the lockfile.** If the lockfile is the problem and reverting isn't possible (e.g., after an AppKit upgrade), `rm -f package-lock.json`, commit the deletion, and redeploy. The platform will do a full fresh resolve.
3. **Upgrade in-place with `--package-lock-only`.** If you must refresh dep versions without running a full `npm install` locally, `npm install @databricks/appkit@latest --package-lock-only` keeps the lockfile coherent with your local registry config; then redeploy and see if step 2 is needed.
4. **Last resort: delete and recreate the app.** Only if `Exit handler never called` persists across multiple clean deploys. Read Rule 2 below first — app deletion has Lakebase side effects.

---

## Rule 2 — App deletion orphans Lakebase schema ownership

When you delete an AppKit app and recreate it with the same name, Databricks assigns a **new service principal UUID** to the new app. Any Lakebase schema that was `CREATE`'d by the old SP continues to exist, but its ownership row still points at the old SP — which no longer has access.

### Failure signature

After a clean redeploy of the recreated app:

```
permission denied for schema <schema_name>
  or
relation "<table>" does not exist
```

...even though `psql` as admin shows the schema and tables still present.

### Fix: DROP + recreate as admin so the new SP owns the schema

```sql
-- As a workspace admin, connecting to Lakebase:
DROP SCHEMA IF EXISTS <schema_name> CASCADE;
-- Then let the app's DDL bootstrap re-create the schema under the new SP.
-- Or explicitly:
CREATE SCHEMA <schema_name> AUTHORIZATION "<new-sp-uuid>";
```

The new SP UUID is visible in the Databricks UI under the app's "Access" tab, or via:

```bash
databricks apps get <app-name> -o json | jq -r .service_principal_id
```

### Prevention

- **Prefer redeploying over deleting.** If the only reason to delete is "my deploy is broken," fix the deploy (lockfile recovery ladder above) instead.
- **If you must delete,** pre-capture the Lakebase schema list and DROP + recreate them as admin **before** the new app's first deploy, or hand schema ownership to a neutral admin group that persists across app recreations.
- **Document the app SP UUID** in your deploy notes so a future DROP/CREATE is a one-liner, not a forensic exercise.

---

## Quick Triage Matrix

| Error you see | Rule | First action |
|---------------|------|--------------|
| `ENOTEMPTY: directory not empty, rmdir '.../node_modules/...'` during `Installing packages...` | Rule 1 | Revert or delete `package-lock.json`, redeploy |
| `Exit handler never called` during `Installing packages...` | Rule 1 | Same as above |
| `npm ERR! code ETIMEDOUT` during deploy install | Rule 1 | Delete lockfile, redeploy once; if it recurs, check platform status |
| `permission denied for schema` after app deletion | Rule 2 | DROP + recreate schemas as admin |
| `relation does not exist` after app deletion, visible in `psql` | Rule 2 | Same — new SP cannot see old-SP-owned objects |

---

## Related References

- [03-appkit-deploy/SKILL.md](../SKILL.md) — full deploy flow and the Common Errors table that links back here.
- [05-appkit-lakebase-wiring/SKILL.md](../../05-appkit-lakebase-wiring/SKILL.md) — Lakebase schema bootstrap; relevant if DROP + CREATE is needed.
- [04-appkit-plugin-add/references/plugin-serving.md](../../04-appkit-plugin-add/references/plugin-serving.md) — `databricks.yml` `serving_endpoint` resource schema (the `endpoint_name` vs `name` trap, a sibling failure mode on recreate).
