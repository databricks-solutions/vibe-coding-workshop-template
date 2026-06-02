---
name: genie-code-environment
description: Session-start behavioral manifest for running this workshop inside Databricks Genie Code. Read FIRST when the client is Genie Code (the coding agent embedded in the Databricks workspace) so you begin knowing how it behaves — surface/page tool-scoping, the three execution paths (runDatabricksCli → SDK → native tools) and the "blocked ≠ impossible, try the next path" discipline, the runDatabricksCli allow-list tiers, bundle-deploy reality (--target dev mandatory, CWD pinned to the page's bundle root, FUSE create-then-validate gap), AppKit/Node reality (apps init --output-dir, no local npm but server-side build, SDK app deploy), agent-skills git-clone install, the Genie-Space deploy tiers, and how to verify a deployed app (3-hop OAuth session). Detection of WHICH client is active lives in vibecoding-state; this skill explains HOW the Genie Code client behaves. Not needed for the IDE+CLI client.
metadata:
  author: prashanth subrahmanyam
  version: "1.0"
  domain: common
  role: shared
  used_by_stages: [all]
  last_verified: "2026-06-02"
  volatility: high
  clients: [genie_code]
  evidence:
    - "retrospectives/genie-code-field-guide.md (narrative)"
    - "probe Ledger P1–P18 (00-overview.md + genie-code-refactor-handoff.md)"
    - "coding_assistant='genie-code' fork lessons (03-prompt-section-chain.md §2a, Buckets A-rationale + C)"
---

# Genie Code Environment — session-start manifest

> **Confidence tags.** `[DOC]` = Databricks documentation; `[TESTED]` = observed directly in a probe
> (probe IDs `P1`–`P18`); `[CONTESTED]` = probes once conflicted — now resolved, see §"Resolved vs.
> open"; `[INFERENCE]` = reasoned, unverified. Every behavioral claim below carries a tag + a citation.

## Why this skill exists

The single highest-leverage fix for working in Genie Code is to **begin each session knowing how it
behaves, instead of re-discovering it live in front of the user** (field guide §6.8 — the meta-fix for
every other gap). This skill is that durable manifest. `skills/vibecoding-state` **detects** which client
is active and writes the capability block; this skill explains **how the Genie Code client behaves** —
detection vs. explanation, no duplication. If `client_context == ide_cli`, you do not need this skill.

## The one operating rule (read this first)

> **Match the surface to the task. If a path is blocked, try the next of the three execution paths. Never
> conclude "impossible" from one path or one page.** Every operation that was hard-blocked on one path in
> the probes had a working alternative on another. [TESTED, recurring P1–P18]

## 1. What Genie Code is, and why the surface matters

Genie Code is Databricks' context-aware AI assistant embedded throughout the workspace — notebooks, SQL
editor, jobs, AI/BI dashboards, the file editor, and bundle folders. It runs on **serverless compute** and
is **pre-authenticated** to the workspace (no `auth login`, no token export). [DOC; TESTED P-runtime]

**The defining fact:** Genie Code **adapts its available tools to the surface (page/asset) you are
currently on.** [DOC] A dashboard page exposes dashboard tools; a notebook page exposes code execution; a
bundle folder exposes bundle operations. This **surface-scoping** is the single most important thing to
understand — the same request can succeed on one page and be "not in the allow-list" on another. The first
move when a capability seems missing is to **navigate to the right surface**, not to conclude it's
impossible. [TESTED P10 — `apps deploy` blocked on a file-editor page]

## 2. The three execution paths

Genie Code can act on Databricks three independent ways, in order of preference:

1. **`runDatabricksCli`** — a pre-authenticated, API-routed CLI path with a per-command **allow-list** and
   safety guardrails. The primary path. [TESTED]
2. **Python SDK** — `from databricks.sdk import WorkspaceClient` via `executeCode`; auto-authenticated;
   full REST surface. This is the **most capable** path: it **bypasses the CLI allow-list** and is the
   reliable way to `w.apps.deploy(...)`, retrieve `w.config.token`, and poll deployment/run state.
   **Caveat:** the SDK has **no bundle-deploy equivalent** — `bundle deploy` is a composite client-side
   operation (read `databricks.yml`, resolve templates, sync files, Terraform state), so it stays on
   `runDatabricksCli`. [TESTED]
3. **Native workspace tools** — `createAsset`, `editAsset`, `openAsset`, `readTable`, `tableSearch`,
   `findReferencesTool`, `checkPermissions`, `renderChart`, `askDataroom`, … operating on governed APIs.
   [TESTED]

A fourth, **raw shell** (`executeCode` language `sh` calling the `databricks` binary), is **blocked by a
trampoline** unless `ENABLE_DATABRICKS_CLI=true` — an escape hatch, not an intended path. [TESTED]
**Discipline:** try path 1 → if blocked, path 2 → if still blocked, path 3.

> Full per-command allow-list tiers and the deploy/CWD/FUSE detail live in
> **[references/allow-list-and-commands.md](references/allow-list-and-commands.md)** — load on demand.

## 3. Bundle deploy reality (the spine, on Genie Code)

The deploy contract is identical to the IDE — `bundle deploy --target dev`, run through
`runDatabricksCli` (see `databricks-asset-bundles` for the canonical contract). The Genie-specific facts:

- **`--target dev` is mandatory** — a *targetless* `bundle deploy` is rejected by a **content safety
  guardrail** ("could affect staging/production"); it is **not** a page block. `--help` / `validate` /
  `summary` are pre-approved from any bundle-context page. [TESTED P4/P5/P6]
- **CWD is pinned to the current page's bundle root** — be **on the page of the bundle you are deploying**.
  There is no `cd`, no `--bundle-root` flag; you can only validate/deploy the bundle tied to the current
  page. [TESTED P2]
- **Edit the *existing* on-page `databricks.yml`.** Files newly written via `createAsset`/the workspace API
  **do not reach the CLI's FUSE mount** in the same session, so "create a new bundle then validate it"
  fails — edit the bundle already on the page. [TESTED P3]
- Use `bundle validate` / `bundle summary` as safe pre-flight (pre-approved, any page). [TESTED P4]

## 4. AppKit / Node reality

- **`apps init` needs `--output-dir`** — it defaults to the workspace root (`/Workspace/<name>`), ignoring
  the page CWD. Pass `--output-dir .` (page folder) or an explicit `/Workspace/Users/<email>/<repo>`.
  [TESTED P14]
- **No local `npm`/`npx`/`corepack`** in the shell (only `node` is present), **but the Apps runtime builds
  server-side**: a SNAPSHOT deploy runs `npm install` + `npm run build` (Vite) from un-built source. A
  Genie-Code participant can edit `client/src/*.tsx` directly and redeploy with **no local Node toolchain**.
  [TESTED P9/P11/P18 — verified: an edited string appeared in the server-built JS bundle]
- **`apps deploy` via `runDatabricksCli` is unreliable** — *page-dependent* (hard-blocked on
  dashboard/file-editor pages, available on an AppKit project page) **and CWD-defeated** (the enhanced
  build flow only fires when CWD = the project root, which never held in probes → it demands `APP_NAME`
  and falls through to the build-skipping API-direct path). The reliable cross-context path is the
  **SDK**: `w.apps.deploy(<name>, AppDeployment(source_code_path=…, mode=SNAPSHOT))` via `executeCode`.
  [TESTED P10/P11]

## 5. Agent-Skills install

`databricks aitools install` (and the legacy `experimental aitools install`) is **hard-blocked** via
`runDatabricksCli` — the whole `aitools` verb family is not allow-listed. [TESTED P12] The working path is
**`git clone` of `databricks/databricks-agent-skills`** (git present, github.com reachable). [TESTED P13]
`npx @databricks/appkit docs` is unavailable (no npm); fetch AppKit docs via `WebFetch` instead. [TESTED P13]

## 6. Genie Spaces

Use the **RULE_8 three tiers** from `databricks-asset-bundles` ("Genie Spaces — three deploy tiers"):
Tier 1 native `genie_spaces` resource (preferred, landing ~this month), Tier 2 provisioning-job (active
fallback, both clients), **Tier 3 `createAsset({assetType:"genie", …})`** — the Genie-Code-only,
last-resort escape hatch that creates a live Space immediately and returns an ID. [TESTED P8] The Space
title always carries the per-user prefix. Point to the spine for the canonical recipe; do not restate it.

## 7. Verifying a deployed app

A deployed App sits behind the Databricks Apps **OAuth gate** — a raw `Authorization: Bearer` token (even
SDK `w.config.token`) is rejected (`/api/health` → 401). [TESTED P16] Two working ways:

1. **Browser** (simplest manual verify) — open `w.apps.get(<name>).url`; the OAuth flow establishes the
   session. Use `apps logs <name>` for backend assertions.
2. **Programmatic** — replay the **3-hop Apps OAuth handshake in one `requests.Session()`** so the CSRF
   cookie persists through the callback (PKCE match), then reuse the session for all `/api/*` calls.
   [TESTED P17] Reusable snippet in
   **[references/app-verification.md](references/app-verification.md)**.

## 8. How a Genie Code session actually operates (operating model)

This is *how* a session runs — distilled from the field forks (someone ran this workshop on Genie Code):

- A **pre-authenticated `WorkspaceClient`** is available via `executeCode` (no auth step). Run Python/SQL on
  **serverless** directly.
- **Read and write *workspace* files**, not `/tmp` — `/tmp` is not durable and is not where artifacts
  belong. Build artifacts **in memory** or write to a project/workspace path.
- The forks evolved a small helper shape — `w`, `read_file`/`write_file`, `run_sql`, `run_job_by_name`.
  These are **session conveniences for inspection and orchestration, NOT artifact-creation channels.**

> **SUPERSEDED — do not resurrect.** The forks also carried ad-hoc SDK-creation primitives
> (`create_job`, `create_pipeline_idempotent`, `make_job_notebook`). Those created un-versioned workspace
> state that diverged from the IDE's bundle output — **that divergence was itself the regression.** They
> are **superseded by the bundle-deploy spine** (`databricks-asset-bundles`): every artifact is a bundle
> resource brought to life by `bundle deploy`, identically on both clients. The only sanctioned in-session
> creation is RULE_8 **Tier 3** Genie-Space `createAsset` (last-resort). [decision #6/#8; M3 §2a Bucket C]

This section is the **canonical home** for the session operating model — the RULE_0 `client_context`
preamble and the PRE-REQUISITES Genie branch point **here** rather than re-inlining it.

## 9. Why the portability rules exist (rationale)

The single-body portability rules (authored elsewhere) exist because of these Genie behaviors — kept here
as the *explanation*, not the rule:

- **No `--var` resolver at the page.** Asset Bundle variables resolve **at deploy time**; you cannot
  "pass a var" interactively. The agnostic body states the concrete-value requirement once.
- **`/tmp` is not durable** and is not the place to write deliverables — write to a workspace/project path.
- **Don't rely on `jq` / raw shell** for control flow — build and inspect artifacts in-memory via the SDK.

## Resolved vs. open

The field guide flagged several items `[CONTESTED]`/`[INCOMPLETE]`. The session-2/3 probes **closed** them
— do not re-import stale doubt:

| Field-guide open item | Status now |
|---|---|
| Does the Apps runtime run `npm run build` server-side from un-built source? `[INCOMPLETE]` | **RESOLVED — yes.** [TESTED P18 / field guide §6.2] |
| Is `bundle deploy` page-context-gated or safety-guardrail-gated? `[CONTESTED]` | **Practical rule settled** (formally still `[CONTESTED]`): `--help`/`validate`/`summary` always run; a real deploy needs an explicit non-prod `--target dev` (targetless → content guardrail). Operate on that rule; don't re-litigate the *why*. [TESTED P4–P6] |
| Is the `runDatabricksCli` CWD the page's bundle root or the workspace home? `[CONTESTED]` | **Page-type-dependent:** = the **bundle root on a bundle page** (proven), = workspace **home on non-bundle pages** (notebook/AppKit). **Be on the bundle's page to deploy it.** [TESTED P2] |
| Is FUSE-invisibility of new files latency or a hard boundary? `[OPEN]` | Unresolved upstream — treat as a boundary in-session: **edit the on-page file.** [TESTED P3] |
| Does any allow-listed path reach the AppKit *enhanced* (`apps deploy`) build in-session? `[OPEN]` | Not demonstrated — use the **SDK SNAPSHOT** path (build still runs server-side). [TESTED P11/P18] |

## Reference files

- **[allow-list-and-commands.md](references/allow-list-and-commands.md)** — the full `runDatabricksCli`
  allow-list tiers (per-command, probe-cited), deploy/CWD/FUSE detail, `apps init --output-dir`,
  `postgres list-*`, the git-clone install path.
- **[app-verification.md](references/app-verification.md)** — the 3-hop OAuth `requests.Session()` snippet
  and the server-side build evidence.

## Related skills

- **`databricks-asset-bundles`** — the canonical deploy contract + Genie-Space tiers (this skill points
  there; it does not restate deploy mechanics).
- **`databricks-expert-agent`** — surface-scoping + path-fallback discipline (cross-references this skill).
- **`skills/vibecoding-state`** — detects the client and writes the capability block; points here for the
  behavioral detail.
