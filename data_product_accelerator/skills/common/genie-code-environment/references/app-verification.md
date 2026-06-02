# Genie Code — verifying a deployed App

Loaded on demand from [`../SKILL.md`](../SKILL.md) §7. Tags as in the SKILL.

## The problem

A deployed Databricks App sits behind the **Apps OAuth gate**. A raw `Authorization: Bearer` header — even
the SDK's `w.config.token` — is **rejected** by AppKit's middleware: a live ACTIVE app returns `/api/health`
→ **401** and `/` → **302** (OAuth redirect). `databricks auth token` is also hard-blocked via
`runDatabricksCli`. [TESTED P16]

## Two working verification paths

**1. Browser (simplest manual verify).** Open the app URL (`w.apps.get(<name>).url`) — the Databricks Apps
OAuth flow establishes the session automatically. Use `apps logs <name>` for backend/build assertions
(look for `Installing packages…` / `Building app…` to confirm the server-side build ran). [TESTED P11/P18]

**2. Programmatic (for automated `/api/*` E2E).** Replay the 3-hop Apps OAuth handshake in **one**
`requests.Session()` so the CSRF cookie persists through the callback (PKCE/CSRF match — a fresh session
per hop returns 403). Run via `executeCode`; no PAT needed. [TESTED P17]

```python
import requests
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
app_url = w.apps.get("<app-name>").url

s = requests.Session()
r1 = s.get(app_url, allow_redirects=False)                       # hop 1: __Host-databricksapps_csrf cookie
r2 = s.get(r1.headers["location"],                               # hop 2: Databricks OIDC authorize
           headers={"Authorization": f"Bearer {w.config.token}"},
           allow_redirects=False)
s.get(r2.headers["location"])                                    # hop 3: /.auth/callback -> session cookie
# s is now authenticated — reuse for all /api/* calls:
print(s.get(f"{app_url}/api/health").status_code)
```

The single `Session` **must** carry the CSRF cookie across all 3 hops or hop 3 returns 403. Note: some
apps serve the SPA as a catch-all (no dedicated `/api/health`) — test **app-specific** routes.

## Server-side build evidence (Gap 4 closed)

A SNAPSHOT deploy of un-built source (no local `npm`, no `dist/`) produced these deploy status messages:
baseline `Installing packages…` → `npm run start`; after editing `client/src/App.tsx`, `Downloading source
code…` → **`Building app…`** → started. The edited string was live in the **server-built** JS bundle
(`/assets/index-*.js`), old string gone — confirming the Apps runtime runs the full `npm install` +
`npm run build` (Vite) pipeline server-side. **No local Node toolchain is required from Genie Code.**
[TESTED P18]
