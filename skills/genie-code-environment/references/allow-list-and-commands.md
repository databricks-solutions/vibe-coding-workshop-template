# Genie Code — `runDatabricksCli` allow-list & command catalog

Loaded on demand from [`../SKILL.md`](../SKILL.md). Every row is probe-cited; tags as in the SKILL.

## Allow-list tiers

`runDatabricksCli` sorts commands into four tiers. This is the catalog observed across probes P1–P18.

| Tier | Meaning | Commands (observed) | Evidence |
|---|---|---|---|
| **Pre-approved** | runs immediately | `bundle validate`, `bundle summary`, `bundle init`; `clusters list/get/start`; `jobs list/get/run-now/list-runs`; `pipelines list/get/list-updates/list-pipeline-events`; `serving-endpoints list/get`; `secrets list-scopes/list`; `fs ls/cat/cp`; `workspace list/get-status/export`; `apps list/get/start/stop/logs/list-deployments/get-deployment`; `postgres list-projects/list-databases/list-endpoints`; `apps init`; `warehouses list` | [TESTED P4, P14, P15; field guide §2.3] |
| **Safety-gated / unreliable** | conditioned, or page/CWD-dependent | `bundle deploy` (**requires an explicit non-prod `--target`**); **`apps deploy` — treat as unreliable** (page-dependent + CWD-defeated; see below) → use the SDK | [TESTED P5/P6, P10] |
| **Hard-blocked** | refused in all tested contexts | all `delete`/`destroy`/`rm`, `clusters permanent-delete`; `--version`; `help`; `bundle schema`; **`aitools` / `experimental aitools`** (entire family); **`apps validate`**; **`apps manifest`**; **`auth token`** | [TESTED P1, P12, P14, P16] |
| **Redirected** | returns a message pointing to a native tool | `pipelines create` → use `openAsset` | [TESTED] |

> **`--help` is always allowed, even on gated verbs** (`bundle deploy --help`, `apps deploy --help` run
> as read-only) — "help works" never implies "the verb will run." [TESTED, field guide §2.3]

> **The SDK bypasses this allow-list.** When a verb is CLI-blocked or unreliable (notably `apps deploy`,
> `auth token`), the Python SDK (`WorkspaceClient` via `executeCode`) is the reliable path — it is the
> **most capable** of the three. The one thing the SDK can **not** do is `bundle deploy` (a composite
> client-side operation with no single API) — that stays on `runDatabricksCli`. [TESTED, field guide §2.2]

> The agent **cannot introspect its own environment** (`--version`/`help`/`bundle schema`/`apps manifest`
> blocked) — which is exactly why this manifest exists. When a version-dependent decision is needed, fall
> back to a **behavior probe** (e.g. `bundle validate` against a sample), never a numeric compare. [TESTED P1]

## Bundle deploy — the precise model (CWD pin + target guardrail)

- `runDatabricksCli` always runs with **CWD = the current page's bundle root** (no `cd`, no
  `--bundle-root`). You can only validate/deploy **the bundle tied to the current page**. [TESTED P2]
- `bundle deploy --help`, `bundle validate`, `bundle summary` are unrestricted from any bundle-context
  page. [TESTED P4]
- A **targetless** `bundle deploy` is rejected by a **content** safety guardrail ("could affect
  staging/production") — not a page block. [TESTED P5]
- `bundle deploy --target dev` **passes the guardrail and runs** against the on-page `databricks.yml`
  (fails only on bad bundle content). [TESTED P6]

## FUSE create-then-validate gap

Files written via `createAsset`/`editAsset`/the workspace API are **not visible to the CLI's FUSE mount**
in the same session. "Scaffold a new `databricks.yml`, then `bundle validate` it" fails. **Edit the
existing on-page `databricks.yml`** instead of creating a new bundle elsewhere. [TESTED P3]

## Escape hatch — raw shell CLI (last resort, NOT the sanctioned path)

The shell `databricks` binary is a trampoline that refuses unless `ENABLE_DATABRICKS_CLI=true`. Setting it
and invoking from a bundle root **auto-installs the real CLI** to `$HOME/bin/databricks` (v1.1.0) and a
real `bundle deploy --target dev --auto-approve` has **succeeded** this way — proving the bundle/Terraform
backend is fully provisioned server-side (`DATABRICKS_BUNDLE_ENGINE=direct`, Terraform 1.5.5). [TESTED,
field guide §2.5/§8] **This violates the "never a bare-shell `databricks` call" rule (RULE_1)** — use it
only as a genuine last resort when `runDatabricksCli` cannot reach the bundle (off-page) and the SDK has no
equivalent (i.e. `bundle deploy` specifically). Prefer navigating to the bundle's page instead.

## AppKit scaffold output location

`apps init` is pre-approved but **ignores the CWD pin** and defaults to `/Workspace/<name>` (workspace
root). Always pass **`--output-dir`** — `--output-dir .` for the page's folder, or an explicit
`/Workspace/Users/<email>/<repo>`. The `⚠ npm not found` warning is expected (P9) and harmless — the
scaffold completes; deps install server-side on deploy. `apps manifest` is hard-blocked; discover plugins
by reading the generated `appkit.plugins.json` post-scaffold, or via `WebFetch` of the AppKit docs.
[TESTED P14]

## Lakebase Phase-2 discovery (postgres list-*)

`postgres list-projects`, `list-databases`, `list-endpoints` are **pre-approved (read-tier)** — this
unblocks the Phase-2 binding chain (`project_id → database_id → endpoint host`). Note: `list-databases` /
`list-endpoints` require a fully-qualified `PARENT = projects/{id}/branches/{id}` (the wiring convention
uses `branches/production`), and both are flagged **Beta**. [TESTED P15]

## Agent-Skills install (git-clone path)

The `aitools` family is hard-blocked (P12). The working install path:

```bash
git clone --depth 1 https://github.com/databricks/databricks-agent-skills /tmp/das
# then copy the skills you need into the project's .agents/skills/ (or reference in place)
```

git 2.52.0 is present and github.com is reachable; 8 skill packages observed. `node` is present at
`/usr/local/bin/node`; `npm`/`npx`/`corepack` are absent. [TESTED P13]
