# Deploy assets — Genie Code cell bodies

These **`.py`** files are the **exact code** for [`../../prompts/deploy-assets-gc.md`](../../prompts/deploy-assets-gc.md). In Genie Code, open each file (or `@`-reference it) and paste the contents into a **Python** cell **in order**.

| Order | File | Role |
|-------|------|------|
| — | (not here) | **A1:** run [`../workshop-variables.md`](../workshop-variables.md) |
| A2 | `a2_deploy_constants.py` | Catalog + schema constants |
| B | `b_step0_discover.py` | List jobs / Silver pipeline (cold start gate) |
| C | `c_step1_bronze.py` | Bronze clone job |
| D | `d_step2_dq.py` | Silver DQ setup job |
| E | `e_step3_silver_pipeline.py` | Silver pipeline full refresh |
| F | `f_step4_gold_setup.py` | Gold setup job |
| G | `g_step5_gold_merge.py` | Gold merge job |
| H | `h_verification.py` | Row counts + constraint checklist |
| (as needed) | `snippet_failed_task_outputs.py` | Debug after a failed `run_job_by_name` |

`verification_appendix.sql` is optional manual SQL (small).
