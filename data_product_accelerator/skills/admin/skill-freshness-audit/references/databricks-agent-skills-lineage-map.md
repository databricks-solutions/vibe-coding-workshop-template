# Databricks Agent Skills Lineage Map

Maps every skill in this repository to its upstream source(s) in [`databricks/databricks-agent-skills`](https://github.com/databricks/databricks-agent-skills). Use this map during freshness audits and upstream sync checks for canonical Databricks-platform skills.

**Upstream repo:** `databricks/databricks-agent-skills` (branch: `main`)
**Manifest URL:** `https://raw.githubusercontent.com/databricks/databricks-agent-skills/main/manifest.json`
**Raw skill URL pattern:** `https://raw.githubusercontent.com/databricks/databricks-agent-skills/main/skills/<slug>/SKILL.md`
**Manifest version:** `2`
**Manifest snapshot:** `manifest-v2-2026-04-22` (`updated_at: 2026-04-22T15:52:03Z`)
**Last full sync:** 2026-04-27

---

## Why two upstream registries?

This repo recognizes two authoritative upstream registries:

| Registry | Coverage | Lineage Map |
|---|---|---|
| `databricks-solutions/ai-dev-kit` | Accelerator-style skills (silver, gold, ml, semantic-layer, monitoring, common) | [ai-dev-kit-lineage-map.md](ai-dev-kit-lineage-map.md) |
| `databricks/databricks-agent-skills` | Canonical Databricks-platform skills (apps, lakebase, model-serving, pipelines, dabs, jobs, core, serverless-migration) | this file |

A single skill may have lineage to **either** registry — or, in a few cases, **both** (for example, an apps skill whose patterns are derived from the platform-canonical AI-Dev-Kit version *and* extend the published `databricks-apps` skill).

---

## Manifest Snapshot (2026-04-22)

The upstream `manifest.json` advertises the following skills. This is the authoritative list; new slugs added to the manifest after this date should be picked up at the next sync.

| Slug | Version | Updated | Notes |
|---|---|---|---|
| `databricks-apps` | 0.1.1 | 2026-04-14 | AppKit + Databricks Apps platform |
| `databricks-core` | 0.1.0 | 2026-04-14 | CLI, auth, data exploration |
| `databricks-dabs` | 0.0.0 | 2026-04-14 | Declarative Automation Bundles |
| `databricks-jobs` | 0.1.0 | 2026-04-14 | Jobs orchestration |
| `databricks-lakebase` | 0.1.0 | 2026-04-15 | Lakebase Postgres |
| `databricks-model-serving` | 0.1.0 | 2026-04-14 | Model Serving endpoints |
| `databricks-pipelines` | 0.1.0 | 2026-04-14 | DLT / Spark Declarative Pipelines |
| `databricks-serverless-migration` | 0.1.0 | 2026-04-22 | Classic → serverless migration |

---

## Relationship Types

| Type | Meaning | Sync Priority |
|---|---|---|
| `derived` | Local skill content directly draws from upstream source | High — upstream changes likely require updates |
| `extended` | Local skill extends the upstream pattern with project-specific additions | Medium — check upstream for new base patterns |
| `reference` | Local skill points at upstream as authoritative back-up; content is original | Low — `## See Also` footer only, not tracked by scanner |

Per the audit policy, `extended`/`derived` skills get a structured `metadata.upstream_sources` entry (scanner-tracked). `reference` skills get a `## See Also` footer (not tracked) so they are not added to `upstream_sources`.

---

## Direct Mappings (extended / derived)

These skills have a structured `upstream_sources` entry pointing at `databricks/databricks-agent-skills`. The scanner audits them for sync drift.

| Local Skill | Upstream Slug(s) | Relationship | Raw URL for Audit |
|---|---|---|---|
| `apps_lakebase/skills/04-appkit-plugin-add` | `databricks-apps` | extended | [Fetch](https://raw.githubusercontent.com/databricks/databricks-agent-skills/main/skills/databricks-apps/SKILL.md) |
| `apps_lakebase/skills/05-appkit-lakebase-wiring` | `databricks-lakebase`, `databricks-apps` | extended | [Lakebase](https://raw.githubusercontent.com/databricks/databricks-agent-skills/main/skills/databricks-lakebase/SKILL.md), [Apps](https://raw.githubusercontent.com/databricks/databricks-agent-skills/main/skills/databricks-apps/SKILL.md) |
| `apps_lakebase/skills/06-appkit-serving-wiring` | `databricks-model-serving`, `databricks-apps` | extended | [Serving](https://raw.githubusercontent.com/databricks/databricks-agent-skills/main/skills/databricks-model-serving/SKILL.md), [Apps](https://raw.githubusercontent.com/databricks/databricks-agent-skills/main/skills/databricks-apps/SKILL.md) |
| `apps_lakebase/skills/06d-appkit-agent-app-proxy` | `databricks-model-serving`, `databricks-apps` | extended | [Serving](https://raw.githubusercontent.com/databricks/databricks-agent-skills/main/skills/databricks-model-serving/SKILL.md), [Apps](https://raw.githubusercontent.com/databricks/databricks-agent-skills/main/skills/databricks-apps/SKILL.md) |
| `apps_lakebase/skills/07-appkit-chat-history` | `databricks-lakebase`, `databricks-apps` | extended | [Lakebase](https://raw.githubusercontent.com/databricks/databricks-agent-skills/main/skills/databricks-lakebase/SKILL.md), [Apps](https://raw.githubusercontent.com/databricks/databricks-agent-skills/main/skills/databricks-apps/SKILL.md) |
| `apps_lakebase/skills/08-appkit-feedback` | `databricks-apps` | extended | [Fetch](https://raw.githubusercontent.com/databricks/databricks-agent-skills/main/skills/databricks-apps/SKILL.md) |
| `skills/databricks-asset-bundles` | `databricks-dabs` | extended | [Fetch](https://raw.githubusercontent.com/databricks/databricks-agent-skills/main/skills/databricks-dabs/SKILL.md) |

---

## Reference-Only Mappings (See Also footer)

These skills carry a `## See Also` footer pointing at the canonical upstream skill but their content is original / accelerator-specific. They are **not** added to `upstream_sources` and are **not** tracked by the scanner — the footer is purely a back-up reference for human readers.

| Local Skill | Upstream Slug(s) | Notes |
|---|---|---|
| `apps_lakebase/skills/00-appkit-navigator` | `databricks-apps` | Navigator-only; routing logic, no platform code |
| `apps_lakebase/skills/01-appkit-scaffold` | `databricks-apps` | Wraps `databricks` CLI scaffold; canonical patterns live upstream |
| `apps_lakebase/skills/02-appkit-build` | `databricks-apps` | Project-specific UI/PRD workflow on top of canonical Apps patterns |
| `apps_lakebase/skills/03-appkit-deploy` | `databricks-apps` | Deploy + diagnose workflow on top of upstream deploy guidance |
| `data_product_accelerator/skills/common/databricks-autonomous-operations` | `databricks-core` | CLI / SDK reference |
| `data_product_accelerator/skills/silver/00-silver-layer-setup` | `databricks-pipelines` | Already extends ai-dev-kit; add upstream-skills as second reference |
| `data_product_accelerator/skills/silver/01-dlt-expectations-patterns` | `databricks-pipelines` | Project-specific expectation patterns |
| `data_product_accelerator/skills/ml/00-ml-pipeline-setup` | `databricks-model-serving` | Already extends ai-dev-kit; upstream-skills as second reference |

---

## Cross-References Inside Skills (no formal mapping)

Several `genai-agents/` skills point at upstream `databricks/databricks-agent-skills` slugs as informational pointers (e.g. tool wiring guidance, debugging entry points). These appear inline as prose links rather than `upstream_sources` entries because the local skills implement different content (course / GenAI workflow, not platform reference). Examples:

- `genai-agents/foundation/03-tools-and-data-access` → references upstream `databricks-agent-bricks` (n/a in this manifest), `databricks-model-serving`.
- `genai-agents/foundation/05-knowledge-assistant` → references upstream `databricks-agent-bricks` (n/a).
- `genai-agents/foundation/02-experiment-tracing-and-uc-storage/references/prod-tracing-deployment.md` → references upstream `databricks-model-serving`.
- `genai-agents/sdlc/01-prompt-registry` → references upstream `databricks-agent-bricks` (n/a) and `databricks-genie` (n/a) for orchestration guidance.

Note: `databricks-agent-bricks` and `databricks-genie` are mentioned in some local skills but are **not** in the current `manifest.json`. Treat those references as project-internal pointers until the upstream registry adds those slugs.

---

## Gaps Worth Tracking (no local equivalent yet)

These upstream slugs do not have a local skill yet. Candidates for future skill creation:

| Upstream Slug | Why it might be useful here |
|---|---|
| `databricks-jobs` | Currently subsumed inside `common/databricks-autonomous-operations`. Could stand alone if Jobs-specific guidance grows. |
| `databricks-serverless-migration` | No accelerator skill covers serverless migration end-to-end. Worth adopting verbatim if the topic comes up. |

---

## Upstream Drift Checks

Run the upstream-source audit (per `skill-freshness-audit/SKILL.md`) and use the raw URL pattern at the top of this document to fetch each upstream skill. Compare the `Manifest snapshot` here against the live `manifest.json`; bump the snapshot tag and `last_synced` after re-syncing.

```bash
# Quick check: what changed in the upstream manifest since 2026-04-22?
curl -sSL https://raw.githubusercontent.com/databricks/databricks-agent-skills/main/manifest.json | python -m json.tool | head -50
```

If a slug's `updated_at` is newer than any local `last_synced` referencing it, the scanner should flag it (or, until that scanner check ships, do it manually as part of the audit).
