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

> **Record the load (G3 manifest-load gate).** The moment you have read this manifest in the current
> thread, set `environment_capabilities.genie_code_manifest_loaded: true` in the live state file. This skill
> is the **owner** of the `genie_code_manifest_loaded` preflight check (`skills/vibecoding-state`
> § *Preflight Check Registry*): on Genie Code, the first deploy / client-divergent prompt's `enter`
> **halts** until this flag is `true`, so the deploy machinery (allow-list tiers, CWD pin, FUSE gap, App
> scaffold/deploy, OAuth-session verify) is in context before you act. The check is **inert on `ide_cli`**.

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
- **How to GET on the bundle page: open the bundle editor.** As soon as a folder contains a `databricks.yml`,
  the Databricks workspace file browser shows an **"Open in bundle editor"** affordance for that folder (and an
  "Open in editor" button at the top of the folder view). Click it to enter the **Bundle UI**, whose page CWD
  IS that bundle root — this is the reliable way to satisfy the CWD pin above, and Genie Code operates more
  predictably (deploy/run pre-approved) from inside the bundle editor than from a generic file page. So the
  canonical sequence is: write `databricks.yml` under `dp_bundle_root` → open that folder's **bundle editor** →
  run `bundle validate`/`deploy`/`run` there. A `databricks.yml not found` error means you are NOT on the
  bundle page — open the bundle editor for the `dp_bundle_root` folder; never fall back to direct SQL. [TESTED — user-observed]
- **Surface a clickable bundle-editor link — don't make the operator hunt for the icon.** With the
  pre-authenticated `WorkspaceClient` (`w`): `host = w.config.host`; `o = w.get_workspace_id()`;
  `file_id = w.workspace.get_status("<dp_bundle_root>/databricks.yml").object_id`;
  `folder_id = w.workspace.get_status("<dp_bundle_root>").object_id`. Then the **bundle-editor URL** is
  `{host}/editor/files/{file_id}?o={o}&contextId=folder%3A{folder_id}` (the plain folder is
  `{host}/browse/folders/{folder_id}?o={o}`). Print the bundle-editor link and tell the operator to open it
  *before* deploy. [TESTED — user-observed]
- **🛑 Blocked `bundle` command ⇒ navigate, don't improvise. If still blocked, STOP.** `bundle deploy`/`run`
  are page-context-gated: BLOCKED on a generic file/notebook page, but they work normally from the bundle
  editor — CONFIRMED in the field, the *same* `bundle deploy` that returned "blocked by safety guardrails" from
  a file page returned "Deployment complete!" and `bundle run … SUCCESS` once the operator opened the bundle
  editor. So a "blocked" / `databricks.yml not found` message is a **wrong-page signal, not a dead end**: open
  the bundle-editor link and retry. Only if it still fails *from the bundle editor* do you STOP and report the
  blocker. Do **NOT** fall back to the Jobs/Pipelines REST API (`jobs/create`, `/api/2.0/pipelines`), the SDK,
  or direct SQL to "get the tables created" — that silently defeats version control and `bundle destroy`
  cleanup and is the exact regression this spine prevents. The REST/SDK route is an **escape hatch available
  only on explicit operator authorization.** [TESTED — user-observed]
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
- **Anchor every relative artifact path to `artifact_root`, never the page CWD or your home dir.**
  `artifact_root` is the workshop clone / git-folder root that `skills/vibecoding-state` captures into the
  `## Environment Capabilities` block (= the local repo root on `ide_cli`; the cloned-repo path under
  `/Workspace/Users/<email>/.assistant/skills/<repo>` on `genie_code`). A bare `docs/design_prd.md` is
  unsafe here because Genie Code's CWD is **page-type-dependent** (the bundle root on a bundle page, the
  workspace home otherwise — see §"Resolved vs. open"), so the same relative path resolves to different
  places.   Write deliverables to `<ARTIFACT_ROOT>/<relpath>` (e.g. `<ARTIFACT_ROOT>/docs/design_prd.md`),
  filling `<ARTIFACT_ROOT>` from the captured `artifact_root`. `/tmp` remains forbidden. [TESTED P2]
- **The data-product bundle anchors to `dp_bundle_root`, a dedicated subdir — not the bare clone root.**
  `skills/vibecoding-state` captures `dp_bundle_root = <artifact_root>/<use_case_slug>_dab` (e.g.
  `…/vibe-coding-workshop/booking_app_dab`). The whole DP pipeline (bronze→silver→gold→semantic) writes its
  `databricks.yml` / `src/` / `resources/` UNDER `<DP_BUNDLE_ROOT>`. Writing them at the clone root is the
  observed "one level too high" bug (generated artifacts mixed into the framework clone). Because `bundle
  deploy`'s CWD is pinned to the current page's bundle root, `<DP_BUNDLE_ROOT>` is ALSO the page you deploy
  from: be on that folder's page, then run `bundle validate`/`deploy`/`run`. A `databricks.yml not found`
  error means you are on the wrong page — navigate to `<DP_BUNDLE_ROOT>`; never fall back to direct SQL.
- **Load every workshop skill by its clone-rooted `readSkillFile` path, never a bare repo-relative path or
  `@`-mention.** Genie Code loads skills through `readSkillFile`, which has **no repo-root-relative
  resolution**: a file under `.assistant/skills/` is loadable only as `skills/{path-after-.assistant/skills/}`.
  Because this repo is cloned to `.assistant/skills/<clone-folder>/`, a repo-relative skill path `X/Y/SKILL.md`
  must be loaded as `readSkillFile("<skill_ref_root>/X/Y/SKILL.md")` where `skill_ref_root` is captured by
  `skills/vibecoding-state` (= `"skills/" + basename(artifact_root)`, default `skills/vibe-coding-workshop`;
  **empty on `ide_cli`**, where `@`-mentions resolve from the workspace root). Nesting depth is irrelevant —
  e.g. `data_product_accelerator/skills/bronze/00-bronze-layer-setup/SKILL.md` loads as
  `skills/vibe-coding-workshop/data_product_accelerator/skills/bronze/00-bronze-layer-setup/SKILL.md`. A bare
  `@data_product_accelerator/…` sends Genie Code on a goose chase. **`AGENTS.md` does not help here** — it is
  read once at the clone root and does **not** propagate across Agent threads, so each prompt must name the
  skill by its `skill_ref_root`-prefixed path (the `genie-code` prompt forks do exactly this). [TESTED — user-observed]
- The forks evolved a small helper shape — `w`, `read_file`/`write_file`, `run_sql`, `run_job_by_name`.
  These are **session conveniences for inspection and orchestration, NOT artifact-creation channels.**

> **SUPERSEDED — do not resurrect.** The forks also carried ad-hoc SDK-creation primitives
> (`create_job`, `create_pipeline_idempotent`, `make_job_notebook`). Those created un-versioned workspace
> state that diverged from the IDE's bundle output — **that divergence was itself the regression.** They
> are **superseded by the bundle-deploy spine** (`databricks-asset-bundles`): every artifact is a bundle
> resource brought to life by `bundle deploy`, identically on both clients. The only sanctioned in-session
> creation is RULE_8 **Tier 3** Genie-Space `createAsset` (last-resort). [decision #6/#8; M3 §2a Bucket C]
>
> **This explicitly includes data-product table DDL.** Creating Bronze/Silver/Gold schemas and tables —
> `CREATE SCHEMA`, `CREATE TABLE`, `DEEP CLONE`, `ALTER TABLE … SET TBLPROPERTIES`, `CLUSTER BY`, and the
> data load — directly via `executeCode`/`spark.sql` is the SAME regression: it produces live tables with
> no versioned bundle behind them. Those statements are the **body of a bundle job notebook**, executed by
> `bundle run`, not run by hand. The frictionless `executeCode` path is the trap (it "works" and the tables
> appear, so the gate passes) — but it bypasses the spine. If `bundle deploy` is blocked, FIX the page
> context (open the `dp_bundle_root` **bundle editor**, §"bundle-deploy reality"); do **not** fall back to
> direct SQL, the Jobs/Pipelines REST API (`jobs/create`, `/api/2.0/pipelines`), or the SDK — those are an
> escape hatch only on explicit operator authorization, and the field-confirmed fix is the bundle editor, not
> the API. Read-only inspection (`SHOW TABLES`, `DESCRIBE`, `SELECT COUNT(*)`) via `executeCode` is fine.

This section is the **canonical home** for the session operating model — the RULE_0 `client_context`
preamble and the PRE-REQUISITES Genie branch point **here** rather than re-inlining it.

## 9. Why the portability rules exist (rationale)

The single-body portability rules (authored elsewhere) exist because of these Genie behaviors — kept here
as the *explanation*, not the rule:

- **No `--var` resolver at the page.** Asset Bundle variables resolve **at deploy time**; you cannot
  "pass a var" interactively. The agnostic body states the concrete-value requirement once.
- **`/tmp` is not durable** and is not the place to write deliverables — write to a workspace/project path.
- **CWD is page-type-dependent**, so a bare relative path (`docs/design_prd.md`) is unstable across pages.
  The `artifact_root` rule above exists for this reason: resolve relative artifacts against the captured
  clone root, not the page CWD. The agnostic body keeps a single anchored form (`<ARTIFACT_ROOT>/…`).
- **No repo-root-relative skill resolution and no cross-thread `AGENTS.md`.** `readSkillFile` only resolves
  `skills/{path-after-.assistant/skills/}`, and `AGENTS.md` is read once at the clone root without propagating
  to later Agent threads. The `skill_ref_root` rule above exists for this reason: prompts (and the
  `genie-code` forks) name each skill by its `skill_ref_root`-prefixed path so it loads regardless of thread.
- **Don't rely on `jq` / raw shell** for control flow — build and inspect artifacts in-memory via the SDK.

## 10. Session ergonomics — parallel skill reads, file-write tiers, and `executeCode` timeouts

Three behaviors that materially change session speed and reliability. All [TESTED — user-observed,
Gold-design run].

- **Read every skill a phase needs in ONE batched turn.** `readSkillFile` calls run **in parallel** —
  issuing all of a phase's skill reads in a single turn returned every file successfully, whereas
  serializing them costs one full turn each. When a step's Step-1 list (or an orchestrator's "Mandatory
  Skill Dependencies") names several skills with **no inter-dependency**, load them together, not one per
  turn. [TESTED]
- **File writes — two paths, choose by situation (there is NO single-call, compute-free file-creation
  tool):**
  - **`executeCode` with `open(path,"w").write(...)`** — one call; creates and writes any workspace file
    directly; but **needs warm serverless compute** (see cold-start below). Best for creating **many** files
    or **large** content — once compute is warm.
  - **`createAsset` → `readFile` → `workspaceUpdateFile`** — a **compute-free** trio (no cold-start risk),
    but with two field-proven constraints: `workspaceUpdateFile` **cannot create a new file** (the file must
    already exist) **and requires the file to have been read in the current thread first**. So:
    `createAsset` (with `assetType: file`) makes the empty file → `readFile` satisfies the read-first guard →
    `workspaceUpdateFile` populates it. Three calls, zero compute. Best for **updating a single
    already-read file**, or writing a few files **before** compute is warm. [TESTED]
- **`executeCode` cold start & timeout — never starve the first call.** The **first** `executeCode` in a
  session pays a **serverless cold start of ~3–5 minutes** before any code runs; subsequent calls are warm
  (~0 s). `timeoutMinutes` **defaults to 15** (minimum 5). **Never set `timeoutMinutes` below 15** — the
  only thing a smaller budget buys is a cold-start timeout and a wasted retry (the retry then "succeeds"
  only because the failed first attempt warmed the compute). For **heavy phases** (e.g. Gold design — CSV
  parsing, per-table YAML generation, cross-table validation) set it **higher (≥ 20)**, and/or send a
  trivial `print("ready")` **warm-up** call first so the cold start is paid once, up front. [TESTED — two
  5-min timeouts on cold first calls; identical code on warm compute ran instantly]

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
