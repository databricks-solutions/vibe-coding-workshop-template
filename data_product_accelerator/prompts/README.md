# Data Product Accelerator — Genie Code prompts

These **`*_gc.md`** files run in **Databricks Genie Code** (notebook) with the Databricks Python SDK — no local `databricks bundle` / shell. For CLI / Asset Bundle patterns, use **`data_product_accelerator/skills/common/databricks-asset-bundles/SKILL.md`** and the stage-specific skills referenced in each prompt.

## Once per session (before any prompt below)

1. Read [`@data_product_accelerator/gc-prompt-conversion/gc-prompt-header.md`](../gc-prompt-conversion/gc-prompt-header.md).
2. Paste and run **[`@data_product_accelerator/gc-prompt-conversion/workshop-variables.md`](../gc-prompt-conversion/workshop-variables.md)** so `w`, `REPO_ROOT`, `APP_NAME`, `DB_SCHEMA`, `TARGET_CATALOG`, and helpers exist.

Details: [`GENIE-CODE-OVERRIDES.md`](../gc-prompt-conversion/GENIE-CODE-OVERRIDES.md), [`troubleshooting_gc.md`](../gc-prompt-conversion/troubleshooting_gc.md).

## Recommended pipeline order

| Step | Prompt |
|------|--------|
| 0 (optional reset) | [`cleanup_workshop_data_gc.md`](cleanup_workshop_data_gc.md) — or locally `python3 data_product_accelerator/scripts/cleanup_workshop_data.py --profile … --execute` |
| 1 | [`extract_from_tables_gc.md`](extract_from_tables_gc.md) — schema CSV under `context/` |
| 2 | [`clone-from-source-gc.md`](clone-from-source-gc.md) — Bronze |
| 3 | [`silver-layer-pipelines-gc.md`](silver-layer-pipelines-gc.md) — Silver SDP + DQ |
| 4 | [`gold-layer-design-gc.md`](gold-layer-design-gc.md) — dimensional model + YAML (uses extract CSV; may reference Silver names for lineage if helpful) |
| 5 | [`gold-layer-pipeline-gc.md`](gold-layer-pipeline-gc.md) — Gold DDL + merge jobs |
| 6 | [`deploy-assets-gc.md`](deploy-assets-gc.md) — run jobs + Silver pipeline orchestration; **executable cells** in [`../gc-prompt-conversion/deploy-assets-cells/`](../gc-prompt-conversion/deploy-assets-cells/README.md) |

`REPO_ROOT` must match your workspace checkout (see `workshop-variables.md`).
