# Phase 1 inventory — workspace vs local (tracked)
**Workspace root:** `/Workspace/Users/jaiwant.jonathan@databricks.com/v2v-in-geniecode/vibe-coding-workshop-template`
**Local repo:** `v2v-workshop-gc` (this clone)
**Manifests:**
- [workspace-manifest-2026-05-05.tsv](workspace-manifest-2026-05-05.tsv) — `TYPE\tLANG\trelative_path` (881 rows under `WS_ROOT`; line 1 is a `# total_entries=881` comment from the export script — parsers should skip `#` lines)
- [local-manifest-tracked-2026-05-05.txt](local-manifest-tracked-2026-05-05.txt) — `git ls-files` (535 paths)

## Comparison method
Workspace `NOTEBOOK` + `PYTHON` paths without a `.py` suffix are normalized to the same path as git (append `.py`). Other paths compared as-is.

## Counts
| Metric | Count |
|---|---:|
| Workspace file-like objects (FILE + NOTEBOOK) | 584 |
| Unique normalized workspace paths (git-style) | 584 |
| Local tracked paths (`git ls-files`) | 535 |
| **On workspace, not in local tracked** | 98 |
| **In local tracked, not on workspace** | 49 |

## Untracked on this clone (context for “workspace only”)

At export time, `git status --porcelain | grep '^??'` reported **52** untracked paths. Most of the **“On workspace only”** list matches files that **exist on disk locally** but are **not** in `git ls-files` (for example `apps_lakebase/prompts/*.md`, both `gc-prompt-conversion/` trees, `WORKSHOP-FACILITATOR-GUIDE.md`). Treat **“workspace only”** as “not tracked in git,” not necessarily “missing from laptop.”

## Top-level: object counts (workspace file-like)
| Top-level | Workspace FILE+NOTEBOOK count |
|---|---:|
| `data_product_accelerator` | 424 |
| `apps_lakebase` | 74 |
| `gold_layer_design` | 34 |
| `src` | 11 |
| `agentic-framework` | 9 |
| `mcp-appkit-skill` | 6 |
| `presentations` | 6 |
| `scripts` | 4 |
| `docs` | 2 |
| `.assistant_instructions.md` | 1 |
| `.gitignore` | 1 |
| `AGENTS.md` | 1 |
| `CONTRIBUTING.md` | 1 |
| `LICENSE.md` | 1 |
| `PRE-REQUISITES.md` | 1 |
| `QUICKSTART.md` | 1 |
| `README.md` | 1 |
| `SECURITY.md` | 1 |
| `WORKSHOP-FACILITATOR-GUIDE.md` | 1 |
| `databricks.yml` | 1 |
| `env.example` | 1 |
| `pre-req-mcp-setup.md` | 1 |
| `resources` | 1 |

## Top-level: tracked file counts (local git)
| Top-level | Local tracked count |
|---|---:|
| `data_product_accelerator` | 397 |
| `apps_lakebase` | 55 |
| `backup_orig_apps_lakebase` | 26 |
| `docs` | 22 |
| `agentic-framework` | 9 |
| `mcp-appkit-skill` | 6 |
| `presentations` | 6 |
| `scripts` | 4 |
| `.assistant_instructions.md` | 1 |
| `.gitignore` | 1 |
| `AGENTS.md` | 1 |
| `CONTRIBUTING.md` | 1 |
| `LICENSE.md` | 1 |
| `PRE-REQUISITES.md` | 1 |
| `QUICKSTART.md` | 1 |
| `README.md` | 1 |
| `SECURITY.md` | 1 |
| `env.example` | 1 |

## On workspace only (normalized path not in `git ls-files`)
These exist under the Genie workspace path but are not present as tracked paths in this clone. *Untracked* local files are **not** included in the local set — several prompts may exist only on disk or only in workspace.

```
WORKSHOP-FACILITATOR-GUIDE.md
apps_lakebase/gc-prompt-conversion/GENIE-CODE-OVERRIDES.md
apps_lakebase/gc-prompt-conversion/MCP-appkit_tooling.md
apps_lakebase/gc-prompt-conversion/gc-prompt-header.md
apps_lakebase/gc-prompt-conversion/troubleshooting_gc.md
apps_lakebase/gc-prompt-conversion/workshop-variables.md
apps_lakebase/prompts/README.md
apps_lakebase/prompts/cleanup-gc.md
apps_lakebase/prompts/deploy_and_test_gc.md
apps_lakebase/prompts/design_prd.md
apps_lakebase/prompts/generate_prd_gc.md
apps_lakebase/prompts/mcp-setup-gc.md
apps_lakebase/prompts/new_exec_steps.md
apps_lakebase/prompts/one-ui-design-local.md
apps_lakebase/prompts/setup_lakebase_gc.md
apps_lakebase/prompts/ui_design.md
apps_lakebase/prompts/ui_design_build_locally_gc.md
apps_lakebase/prompts/ui_feature_polish_gc.md
apps_lakebase/prompts/wire_ui_to_lakebase_gc.md
apps_lakebase/skills/00-appkit-navigator/scripts/validate-prereqs.sh
apps_lakebase/skills/01-appkit-scaffold/scripts/install-agent-skills.sh
apps_lakebase/skills/03-appkit-deploy/scripts/verify-deploy.sh
apps_lakebase/skills/05-appkit-lakebase-wiring/scripts/test-endpoints.sh
data_product_accelerator/context/booking_app_Schema.csv
data_product_accelerator/gc-prompt-conversion/GENIE-CODE-OVERRIDES.md
data_product_accelerator/gc-prompt-conversion/deploy-assets-cells/README.md
data_product_accelerator/gc-prompt-conversion/deploy-assets-cells/a2_deploy_constants.py
data_product_accelerator/gc-prompt-conversion/deploy-assets-cells/b_step0_discover.py
data_product_accelerator/gc-prompt-conversion/deploy-assets-cells/c_step1_bronze.py
data_product_accelerator/gc-prompt-conversion/deploy-assets-cells/d_step2_dq.py
data_product_accelerator/gc-prompt-conversion/deploy-assets-cells/e_step3_silver_pipeline.py
data_product_accelerator/gc-prompt-conversion/deploy-assets-cells/f_step4_gold_setup.py
data_product_accelerator/gc-prompt-conversion/deploy-assets-cells/g_step5_gold_merge.py
data_product_accelerator/gc-prompt-conversion/deploy-assets-cells/h_verification.py
data_product_accelerator/gc-prompt-conversion/deploy-assets-cells/snippet_failed_task_outputs.py
data_product_accelerator/gc-prompt-conversion/deploy-assets-cells/verification_appendix.sql
data_product_accelerator/gc-prompt-conversion/gc-prompt-header.md
data_product_accelerator/gc-prompt-conversion/lakebase-notebook-connection.md
data_product_accelerator/gc-prompt-conversion/reference_gold_merge_booking_notebook_body.py
data_product_accelerator/gc-prompt-conversion/troubleshooting_gc.md
data_product_accelerator/gc-prompt-conversion/workshop-variables.md
data_product_accelerator/prompts/README.md
data_product_accelerator/prompts/cleanup_workshop_data_gc.md
data_product_accelerator/prompts/clone-from-source-gc.md
data_product_accelerator/prompts/deploy-assets-gc.md
data_product_accelerator/prompts/extract_from_tables_gc.md
data_product_accelerator/prompts/gold-layer-design-gc.md
data_product_accelerator/prompts/gold-layer-pipeline-gc.md
data_product_accelerator/prompts/silver-layer-pipelines-gc.md
data_product_accelerator/scripts/cleanup_workshop_data.py
databricks.yml
gold_layer_design/BUSINESS_ONBOARDING.md
gold_layer_design/COLUMN_LINEAGE.csv
gold_layer_design/COLUMN_LINEAGE.md
gold_layer_design/DESIGN_DECISIONS.md
gold_layer_design/DESIGN_GAP_ANALYSIS.md
gold_layer_design/DESIGN_SUMMARY.md
gold_layer_design/ERD.md
gold_layer_design/README.md
gold_layer_design/SOURCE_TABLE_MAPPING.csv
gold_layer_design/VALIDATION_SUMMARY.md
gold_layer_design/docs/BUSINESS_ONBOARDING_GUIDE.md
gold_layer_design/erd_master.md
gold_layer_design/lineage/column_lineage.csv
gold_layer_design/lineage/column_lineage.md
gold_layer_design/schemas/dim_coupons.yaml
gold_layer_design/schemas/dim_date.yaml
gold_layer_design/schemas/dim_guests.yaml
gold_layer_design/schemas/dim_listings.yaml
gold_layer_design/schemas/dim_location.yaml
gold_layer_design/schemas/fact_bookings.yaml
gold_layer_design/schemas/fact_reviews.yaml
gold_layer_design/source_table_mapping.csv
gold_layer_design/yaml/booking/dim_coupon.yaml
gold_layer_design/yaml/booking/dim_date.yaml
gold_layer_design/yaml/booking/dim_listing.yaml
gold_layer_design/yaml/booking/fact_booking.yaml
gold_layer_design/yaml/booking/fact_review.yaml
gold_layer_design/yaml/bookings/dim_listing.yaml
gold_layer_design/yaml/bookings/fact_booking.yaml
gold_layer_design/yaml/bookings/fact_review.yaml
gold_layer_design/yaml/hospitality/dim_guest.yaml
gold_layer_design/yaml/hospitality/dim_listing.yaml
gold_layer_design/yaml/hospitality/fact_booking.yaml
gold_layer_design/yaml/hospitality/fact_review.yaml
pre-req-mcp-setup.md
resources/bronze_clone_job.yml
src/bronze_clone_from_source.py
src/jaiwant_j_booking_app_bronze/clone_from_source.py
src/jaiwant_j_booking_app_gold/gold_add_fk.py
src/jaiwant_j_booking_app_gold/gold_merge.py
src/jaiwant_j_booking_app_gold/gold_setup.py
src/jaiwant_j_booking_app_gold/gold_setup_tables.py
src/jaiwant_j_booking_app_silver/dq_rules_loader.py
src/jaiwant_j_booking_app_silver/dq_setup.py
src/jaiwant_j_booking_app_silver/setup_dq_rules_table.py
src/jaiwant_j_booking_app_silver/silver_pipeline.py
src/jaiwant_j_booking_app_silver/silver_sdp_pipeline.py
```

## In local git only (not found as FILE/NOTEBOOK on workspace)
Tracked in this repo but no matching workspace object after notebook normalization. Includes deleted-in-workspace trees still in git index, or never-imported paths.

```
apps_lakebase/skills/00-appkit-navigator/scripts/validate-prereqs.py
apps_lakebase/skills/03-appkit-deploy/scripts/validate-app.py
apps_lakebase/skills/Instructions.md
backup_orig_apps_lakebase/Instructions_CLI.md
backup_orig_apps_lakebase/app_deploy_notebook.py
backup_orig_apps_lakebase/apps_deploy.md
backup_orig_apps_lakebase/deploy_app_gc_runner.py
backup_orig_apps_lakebase/helper_deploy.py
backup_orig_apps_lakebase/skills/00-appkit-navigator/SKILL.md
backup_orig_apps_lakebase/skills/00-appkit-navigator/scripts/validate-prereqs.sh
backup_orig_apps_lakebase/skills/01-appkit-scaffold/SKILL.md
backup_orig_apps_lakebase/skills/01-appkit-scaffold/references/appkit-project-structure.md
backup_orig_apps_lakebase/skills/01-appkit-scaffold/scripts/install-agent-skills.sh
backup_orig_apps_lakebase/skills/02-appkit-build/SKILL.md
backup_orig_apps_lakebase/skills/02-appkit-build/references/design-quality.md
backup_orig_apps_lakebase/skills/02-appkit-build/references/llm-guardrails.md
backup_orig_apps_lakebase/skills/03-appkit-deploy/SKILL.md
backup_orig_apps_lakebase/skills/03-appkit-deploy/references/app-management.md
backup_orig_apps_lakebase/skills/03-appkit-deploy/scripts/verify-deploy.sh
backup_orig_apps_lakebase/skills/04-appkit-plugin-add/SKILL.md
backup_orig_apps_lakebase/skills/04-appkit-plugin-add/references/plugin-analytics.md
backup_orig_apps_lakebase/skills/04-appkit-plugin-add/references/plugin-files.md
backup_orig_apps_lakebase/skills/04-appkit-plugin-add/references/plugin-genie.md
backup_orig_apps_lakebase/skills/04-appkit-plugin-add/references/plugin-lakebase.md
backup_orig_apps_lakebase/skills/05-appkit-lakebase-wiring/SKILL.md
backup_orig_apps_lakebase/skills/05-appkit-lakebase-wiring/references/database-design-guide.md
backup_orig_apps_lakebase/skills/05-appkit-lakebase-wiring/references/frontend-patterns.md
backup_orig_apps_lakebase/skills/05-appkit-lakebase-wiring/references/multi-table-example.md
backup_orig_apps_lakebase/skills/05-appkit-lakebase-wiring/scripts/test-endpoints.sh
docs/MCP-appkit_tooling.md
docs/deploy_and_test.md
docs/deploy_and_test_gc.md
docs/gc-prompt-conversion.md
docs/generate_prd.md
docs/generate_prd_gc.md
docs/mcp-setup-gc.md
docs/new_exec_steps.md
docs/references/database-design-guide.md
docs/references/frontend-patterns.md
docs/references/llm-guardrails.md
docs/references/multi-table-example.md
docs/setup_lakebase.md
docs/setup_lakebase_gc.md
docs/summary_exec.md
docs/ui_design_build_locally.md
docs/ui_design_build_locally_gc.md
docs/ui_feature_polish_gc.md
docs/wire_ui_to_lakebase.md
docs/wire_ui_to_lakebase_gc.md
```
