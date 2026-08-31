# Databricks Agent Skills Lineage Map

Maps every skill in this repository to its upstream source(s) in [`databricks/databricks-agent-skills`](https://github.com/databricks/databricks-agent-skills). This is the **single authoritative upstream registry** for freshness audits and upstream sync checks.

> **Consolidation note (2026-08-30):** the former `databricks-solutions/ai-dev-kit` registry was retired as a separate upstream. Its `databricks-skills/<slug>` skills now live in this registry under `skills/<slug>` (with a few renames — see the migration table below), so every local `upstream_sources` entry points here.

**Upstream repo:** `databricks/databricks-agent-skills` (branch: `main`)
**Manifest URL:** `https://raw.githubusercontent.com/databricks/databricks-agent-skills/main/manifest.json`
**Raw skill URL pattern:** `https://raw.githubusercontent.com/databricks/databricks-agent-skills/main/skills/<slug>/SKILL.md`
**Manifest snapshot:** `2026-08-30` (32 skills)
**Last full sync:** 2026-08-30 (commit `ca92a6c`)

---

## Manifest Snapshot (2026-08-30)

The upstream `manifest.json` advertises the following skills (all under `repo_dir: skills/` unless noted). This is the authoritative list; new slugs added to the manifest after this date should be picked up at the next sync.

| Slug | Version | Slug | Version |
|---|---|---|---|
| `databricks-agent-bricks` | 0.1.0 | `databricks-lakebase` | 0.1.0 |
| `databricks-ai-functions` | 0.2.0 | `databricks-lakeflow-connect` | 0.1.0 |
| `databricks-ai-runtime` (experimental) | 0.1.0 | `databricks-metric-views` | 0.1.0 |
| `databricks-aibi-dashboards` | 0.2.1 | `databricks-ml-training` | 0.1.0 |
| `databricks-app-design` | 0.1.0 | `databricks-mlflow-evaluation` | 0.1.0 |
| `databricks-apps` | 0.1.3 | `databricks-model-serving` | 0.4.0 |
| `databricks-apps-python` | 0.1.0 | `databricks-pipelines` | 0.3.0 |
| `databricks-core` | 0.1.0 | `databricks-python-sdk` | 0.1.0 |
| `databricks-dabs` | 0.0.1 | `databricks-serverless-migration` | 0.1.0 |
| `databricks-data-discovery` | 0.1.0 | `databricks-spark-structured-streaming` | 0.1.0 |
| `databricks-dbsql` | 0.1.0 | `databricks-synthetic-data-gen` | 0.1.0 |
| `databricks-docs` | 0.1.0 | `databricks-unity-catalog` | 0.3.0 |
| `databricks-execution-compute` | 0.1.0 | `databricks-unstructured-pdf-generation` | 0.1.0 |
| `databricks-genie-agents` | 0.1.0 | `databricks-vector-search` | 0.1.0 |
| `databricks-iceberg` | 0.1.0 | `databricks-zerobus-ingest` | 0.1.0 |
| `databricks-jobs` | 0.2.0 | `spark-python-data-source` (experimental) | 0.1.0 |

---

## Slug Migration (ai-dev-kit → databricks-agent-skills)

Slug renames applied when the `databricks-solutions/ai-dev-kit` `databricks-skills/` slugs were folded into this registry's `skills/`:

| Former ai-dev-kit slug | New databricks-agent-skills slug |
|---|---|
| `databricks-genie` | `databricks-genie-agents` |
| `databricks-asset-bundles` | `databricks-dabs` |
| `databricks-synthetic-data-generation` | `databricks-synthetic-data-gen` |
| `databricks-spark-declarative-pipelines` | `databricks-pipelines` |
| `databricks-config` | `databricks-core` |
| `databricks-lakebase-provisioned` / `databricks-lakebase-autoscale` | `databricks-lakebase` |
| `databricks-app-apx` | `databricks-apps` |
| `databricks-app-python` | `databricks-apps-python` |
| _(all others)_ | _same name_ |

---

## Relationship Types

| Type | Meaning | Sync Priority |
|---|---|---|
| `derived` | Local skill content directly draws from upstream source | High — upstream changes likely require updates |
| `extended` | Local skill extends the upstream pattern with project-specific additions | Medium — check upstream for new base patterns |
| `reference` | Local skill points at upstream as authoritative back-up; content is original | Low — verify API/pattern accuracy only |

Per the audit policy, `extended`/`derived` skills get a structured `metadata.upstream_sources` entry (scanner-tracked). Purely informational pointers use a `## See Also` footer (not tracked).

---

## Direct Mappings (extended / derived)

These skills carry a structured `upstream_sources` entry. The scanner audits them for sync drift.

| Local Skill | Upstream Slug(s) | Relationship | Raw URL for Audit |
|---|---|---|---|
| `apps_lakebase/skills/04-appkit-plugin-add` | `databricks-apps` | extended | [Fetch](https://raw.githubusercontent.com/databricks/databricks-agent-skills/main/skills/databricks-apps/SKILL.md) |
| `apps_lakebase/skills/05-appkit-lakebase-wiring` | `databricks-lakebase`, `databricks-apps` | extended | [Lakebase](https://raw.githubusercontent.com/databricks/databricks-agent-skills/main/skills/databricks-lakebase/SKILL.md), [Apps](https://raw.githubusercontent.com/databricks/databricks-agent-skills/main/skills/databricks-apps/SKILL.md) |
| `apps_lakebase/skills/06-appkit-serving-wiring` | `databricks-model-serving`, `databricks-apps` | extended | [Serving](https://raw.githubusercontent.com/databricks/databricks-agent-skills/main/skills/databricks-model-serving/SKILL.md), [Apps](https://raw.githubusercontent.com/databricks/databricks-agent-skills/main/skills/databricks-apps/SKILL.md) |
| `apps_lakebase/skills/06d-appkit-agent-app-proxy` | `databricks-model-serving`, `databricks-apps` | extended | [Serving](https://raw.githubusercontent.com/databricks/databricks-agent-skills/main/skills/databricks-model-serving/SKILL.md), [Apps](https://raw.githubusercontent.com/databricks/databricks-agent-skills/main/skills/databricks-apps/SKILL.md) |
| `apps_lakebase/skills/07-appkit-chat-history` | `databricks-lakebase`, `databricks-apps` | extended | [Lakebase](https://raw.githubusercontent.com/databricks/databricks-agent-skills/main/skills/databricks-lakebase/SKILL.md), [Apps](https://raw.githubusercontent.com/databricks/databricks-agent-skills/main/skills/databricks-apps/SKILL.md) |
| `apps_lakebase/skills/08-appkit-feedback` | `databricks-apps` | extended | [Fetch](https://raw.githubusercontent.com/databricks/databricks-agent-skills/main/skills/databricks-apps/SKILL.md) |
| `skills/databricks-asset-bundles` | `databricks-dabs` | extended | [Fetch](https://raw.githubusercontent.com/databricks/databricks-agent-skills/main/skills/databricks-dabs/SKILL.md) |
| `data_product_accelerator/skills/common/unity-catalog-constraints` | `databricks-unity-catalog` | derived | [Fetch](https://raw.githubusercontent.com/databricks/databricks-agent-skills/main/skills/databricks-unity-catalog/SKILL.md) |
| `data_product_accelerator/skills/common/schema-management-patterns` | `databricks-unity-catalog` | derived | [Fetch](https://raw.githubusercontent.com/databricks/databricks-agent-skills/main/skills/databricks-unity-catalog/SKILL.md) |
| `data_product_accelerator/skills/common/databricks-table-properties` | `databricks-unity-catalog` | derived | [Fetch](https://raw.githubusercontent.com/databricks/databricks-agent-skills/main/skills/databricks-unity-catalog/SKILL.md) |
| `data_product_accelerator/skills/common/databricks-autonomous-operations` | `databricks-python-sdk`, `databricks-jobs` | extended | [SDK](https://raw.githubusercontent.com/databricks/databricks-agent-skills/main/skills/databricks-python-sdk/SKILL.md), [Jobs](https://raw.githubusercontent.com/databricks/databricks-agent-skills/main/skills/databricks-jobs/SKILL.md) |
| `data_product_accelerator/skills/silver/00-silver-layer-setup` | `databricks-pipelines` | extended | [Fetch](https://raw.githubusercontent.com/databricks/databricks-agent-skills/main/skills/databricks-pipelines/SKILL.md) |
| `data_product_accelerator/skills/silver/01-dlt-expectations-patterns` | `databricks-pipelines` | extended | [Fetch](https://raw.githubusercontent.com/databricks/databricks-agent-skills/main/skills/databricks-pipelines/SKILL.md) |
| `data_product_accelerator/skills/semantic-layer/01-metric-views-patterns` | `databricks-metric-views` | extended | [Fetch](https://raw.githubusercontent.com/databricks/databricks-agent-skills/main/skills/databricks-metric-views/SKILL.md) |
| `data_product_accelerator/skills/semantic-layer/03-genie-space-patterns` | `databricks-genie-agents` | extended | [Fetch](https://raw.githubusercontent.com/databricks/databricks-agent-skills/main/skills/databricks-genie-agents/SKILL.md) |
| `data_product_accelerator/skills/semantic-layer/04-genie-space-export-import-api` | `databricks-genie-agents` | extended | [Fetch](https://raw.githubusercontent.com/databricks/databricks-agent-skills/main/skills/databricks-genie-agents/SKILL.md) |
| `data_product_accelerator/skills/bronze/01-faker-data-generation` | `databricks-synthetic-data-gen` | extended | [Fetch](https://raw.githubusercontent.com/databricks/databricks-agent-skills/main/skills/databricks-synthetic-data-gen/SKILL.md) |
| `data_product_accelerator/skills/ml/00-ml-pipeline-setup` | `databricks-model-serving`, `databricks-vector-search` | extended | [Serving](https://raw.githubusercontent.com/databricks/databricks-agent-skills/main/skills/databricks-model-serving/SKILL.md), [Vector](https://raw.githubusercontent.com/databricks/databricks-agent-skills/main/skills/databricks-vector-search/SKILL.md) |
| `data_product_accelerator/skills/monitoring/02-databricks-aibi-dashboards` | `databricks-aibi-dashboards` | extended | [Fetch](https://raw.githubusercontent.com/databricks/databricks-agent-skills/main/skills/databricks-aibi-dashboards/SKILL.md) |
| `genai-agents/sdlc/02-evaluation-datasets` | `databricks-mlflow-evaluation` | extended | [Fetch](https://raw.githubusercontent.com/databricks/databricks-agent-skills/main/skills/databricks-mlflow-evaluation/SKILL.md) |
| `genai-agents/sdlc/03-scorers-and-judges` | `databricks-mlflow-evaluation` | extended | [Fetch](https://raw.githubusercontent.com/databricks/databricks-agent-skills/main/skills/databricks-mlflow-evaluation/SKILL.md) |
| `genai-agents/sdlc/04-evaluation-runs` | `databricks-mlflow-evaluation` | extended | [Fetch](https://raw.githubusercontent.com/databricks/databricks-agent-skills/main/skills/databricks-mlflow-evaluation/SKILL.md) |
| `genai-agents/sdlc/07-production-monitoring` | `databricks-mlflow-evaluation` | extended | [Fetch](https://raw.githubusercontent.com/databricks/databricks-agent-skills/main/skills/databricks-mlflow-evaluation/SKILL.md) |
| `genai-agents/sdlc/08-prompt-optimization` | `databricks-mlflow-evaluation` | extended | [Fetch](https://raw.githubusercontent.com/databricks/databricks-agent-skills/main/skills/databricks-mlflow-evaluation/SKILL.md) |

---

## Reference-Only Mappings (scanner-tracked, low priority)

These skills carry an `upstream_sources` entry with `relationship: reference` — content is original, but the upstream is a back-up authority for API/pattern accuracy.

| Local Skill | Upstream Slug | Relationship | Raw URL for Audit |
|---|---|---|---|
| `genai-agents/sdlc/01-prompt-registry` | `databricks-mlflow-evaluation` | reference | [Fetch](https://raw.githubusercontent.com/databricks/databricks-agent-skills/main/skills/databricks-mlflow-evaluation/SKILL.md) |
| `genai-agents/sdlc/04c-end-user-feedback` | `databricks-mlflow-evaluation` | reference | [Fetch](https://raw.githubusercontent.com/databricks/databricks-agent-skills/main/skills/databricks-mlflow-evaluation/SKILL.md) |
| `genai-agents/sdlc/05-logged-model-and-uc-registration` | `databricks-mlflow-evaluation` | reference | [Fetch](https://raw.githubusercontent.com/databricks/databricks-agent-skills/main/skills/databricks-mlflow-evaluation/SKILL.md) |
| `genai-agents/sdlc/06-deployment-and-automation` | `databricks-mlflow-evaluation` | reference | [Fetch](https://raw.githubusercontent.com/databricks/databricks-agent-skills/main/skills/databricks-mlflow-evaluation/SKILL.md) |
| `data_product_accelerator/skills/common/databricks-python-imports` | `databricks-core` | reference | [Fetch](https://raw.githubusercontent.com/databricks/databricks-agent-skills/main/skills/databricks-core/SKILL.md) |

---

## See Also Footer (not scanner-tracked)

These skills point at a canonical upstream skill for human readers but keep original content; they are **not** in `upstream_sources`.

| Local Skill | Upstream Slug | Notes |
|---|---|---|
| `apps_lakebase/skills/00-appkit-navigator` | `databricks-apps` | Navigator-only; routing logic, no platform code |
| `apps_lakebase/skills/01-appkit-scaffold` | `databricks-apps` | Wraps `databricks` CLI scaffold; canonical patterns live upstream |
| `apps_lakebase/skills/02-appkit-build` | `databricks-apps` | Project-specific UI/PRD workflow on top of canonical Apps patterns |
| `apps_lakebase/skills/03-appkit-deploy` | `databricks-apps` | Deploy + diagnose workflow on top of upstream deploy guidance |
| `genai-agents/foundation/05-knowledge-assistant` | `databricks-agent-bricks` | KA lifecycle / Supervisor patterns; references `references/1-knowledge-assistants.md` |

---

## Separate Upstream — Databricks Python SDK (not databricks-agent-skills)

These skills track the Databricks Python SDK (`databricks/databricks-sdk-py`) as their source of truth for API method signatures and dataclass definitions. They are original content but must stay in sync with SDK changes. This is a **distinct** upstream from the skill registry and is intentionally retained.

**Upstream repo:** `databricks/databricks-sdk-py` (branch: `main`) — **SDK Docs:** `https://databricks-sdk-py.readthedocs.io/en/latest/`

| Local Skill | SDK Path(s) | Relationship | Docs URL for Audit |
|---|---|---|---|
| `monitoring/01-lakehouse-monitoring-comprehensive` | `databricks/sdk/service/dataquality.py` | reference | [API](https://databricks-sdk-py.readthedocs.io/en/latest/workspace/dataquality/data_quality.html), [Dataclasses](https://databricks-sdk-py.readthedocs.io/en/latest/dbdataclasses/dataquality.html) |
| `monitoring/04-anomaly-detection` | `databricks/sdk/service/dataquality.py` | reference | [API](https://databricks-sdk-py.readthedocs.io/en/latest/workspace/dataquality/data_quality.html), [Dataclasses](https://databricks-sdk-py.readthedocs.io/en/latest/dbdataclasses/dataquality.html) |

**Key verification points for SDK lineage:**
- `DataQualityAPI` method signatures (especially asymmetry: `create_monitor(monitor)` vs `update_monitor(object_type, object_id, monitor, update_mask)`)
- Dataclass field names and types (`Monitor`, `DataProfilingConfig`, `AnomalyDetectionConfig`, etc.)
- Enum values (`DataProfilingCustomMetricType`, `AggregationGranularity`, `RefreshState`)
- Methods marked `(Unimplemented)` in the SDK (`list_monitor`, `delete_refresh`, `update_refresh`)

---

## Cross-References Inside Skills (no formal mapping)

Several `genai-agents/` skills point at upstream slugs as informational pointers (tool-wiring guidance, debugging entry points). These appear inline as prose links rather than `upstream_sources` entries because the local skills implement different content (course / GenAI workflow, not platform reference). Examples:

- `genai-agents/foundation/03-tools-and-data-access` → `databricks-agent-bricks`, `databricks-model-serving`.
- `genai-agents/foundation/05-knowledge-assistant` → `databricks-agent-bricks`.
- `genai-agents/sdlc/01-prompt-registry` → `databricks-agent-bricks`, `databricks-genie-agents` for orchestration guidance.

---

## Gaps Worth Tracking (no local equivalent yet)

These upstream slugs do not have a local skill yet. Candidates for future skill creation:

| Upstream Slug | Why it might be useful here |
|---|---|
| `databricks-serverless-migration` | No accelerator skill covers serverless migration end-to-end. |
| `databricks-iceberg` | Iceberg interop patterns could extend bronze / gold. |
| `databricks-lakeflow-connect` | Managed ingestion connectors could extend bronze. |
| `databricks-dbsql` | DBSQL advanced (scripting, stored procs, AI functions) — broadly useful. |
| `databricks-ml-training` | Serverless GPU training could complement `ml/00-ml-pipeline-setup`. |

---

## Upstream Drift Checks

Run the upstream-source audit (per `skill-freshness-audit/SKILL.md`) and use the raw URL pattern at the top of this document to fetch each upstream skill. Compare the manifest snapshot here against the live `manifest.json`; bump the snapshot date and `last_synced` / `sync_commit` after re-syncing.

```bash
# Quick check: what does the live upstream manifest advertise now?
curl -sSL https://raw.githubusercontent.com/databricks/databricks-agent-skills/main/manifest.json | python3 -m json.tool | head -60

# Current upstream HEAD (for sync_commit)
git ls-remote https://github.com/databricks/databricks-agent-skills.git HEAD
```

If a slug's upstream `version` (in the manifest) or content is newer than any local `last_synced` referencing it, flag it during the audit and re-sync.
