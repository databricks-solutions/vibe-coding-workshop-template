> **Header:** `@data_product_accelerator/gc-prompt-conversion/gc-prompt-header.md` — read FIRST.  
> **CLI / bundle context:** `@data_product_accelerator/skills/gold/00-gold-layer-design/SKILL.md` — Genie follows the same stages via SDK/read paths in this prompt.

---

**Bootstrap:** Paste **`@data_product_accelerator/gc-prompt-conversion/workshop-variables.md`** so **`w`** and **`REPO_ROOT`** exist.

**Input:** **`data_product_accelerator/context/booking_app_Schema.csv`** on the workspace (**FILE** — no `open()`).

```python
import base64, csv, io
p = f"{REPO_ROOT}/data_product_accelerator/context/booking_app_Schema.csv"
raw = w.workspace.export(path=p).content
rows = list(csv.DictReader(io.StringIO(base64.b64decode(raw).decode())))
```

**Task:** Execute **`@data_product_accelerator/skills/gold/00-gold-layer-design/SKILL.md`** exactly as the original prompt describes (parse → dimensional model → DESIGN_DECISIONS → ERDs → YAML → lineage → business doc → source mapping → validation). The orchestrator loads workers; **`AGENTS.md`** layout rules apply (artifacts under repo **`gold_layer_design/`**, not **`data_product_accelerator/`**).

**Done when:** SKILL acceptance criteria satisfied.
