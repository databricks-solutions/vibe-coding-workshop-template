# Synthetic Eval Dataset Generation From Traces

This reference covers the full workflow to turn production traces into a **starter evaluation dataset** — the fastest path from "I have an agent running" to "I have a real benchmark I can gate releases on." It complements `references/benchmark-generation.md` (which focuses on LLM-generated questions + SQL validation).

---

## When to Use

- You have a deployed agent (or a dev agent hitting a realistic dataset) producing MLflow traces in UC.
- You do **not** yet have a labeled eval dataset, or your current one doesn't reflect real usage.
- You need to bootstrap an evaluation set with realistic inputs in < 1 hour.

Do **not** use when:

- Your agent is pre-launch and has no traces. Author SME-curated rows first.
- Your agent never handles varied intents (e.g. a single-purpose classifier). Curate instead.

---

## End-to-End Recipe

### Step 1 — Sample recent traces

Pull the last N days of production traces (or dev traces if pre-launch). Filter out ones that obviously errored.

```python
import mlflow
import pandas as pd

traces = mlflow.search_traces(
    experiment_names=["/Shared/skyloyalty/agent"],
    filter_string="trace.timestamp > 7 days ago AND trace.status = 'OK'",
    max_results=500,
    return_type="pandas",  # returns DataFrame
)

print(f"Fetched {len(traces)} successful traces")
```

### Step 2 — Extract user inputs and outputs

Each trace has `request` and `response` columns, plus rich OTEL spans. Normalize to a flat dict per row.

```python
def trace_to_eval_row(trace_row) -> dict | None:
    req = trace_row["request"]  # Usually a dict-like {"messages": [...]}
    resp = trace_row["response"]
    if not req or not resp:
        return None

    user_turns = [m for m in (req.get("messages") or []) if m.get("role") == "user"]
    if not user_turns:
        return None

    return {
        "inputs":  {"question": user_turns[-1]["content"]},
        "outputs": {"answer":   resp.get("content") or resp.get("answer") or ""},
        "trace_id": trace_row["request_id"],
        "timestamp": trace_row["timestamp"],
    }

rows = [r for r in (trace_to_eval_row(t) for _, t in traces.iterrows()) if r]
print(f"Extracted {len(rows)} candidate rows")
```

### Step 3 — Cluster by intent (optional, for coverage)

Clustering ensures your starter set spans the major intents, not just the top-1 FAQ. Embed each question and group with KMeans / HDBSCAN.

```python
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.cluster import KMeans

model = SentenceTransformer("all-MiniLM-L6-v2")
vecs  = model.encode([r["inputs"]["question"] for r in rows])
k     = min(20, max(5, len(rows) // 25))
km    = KMeans(n_clusters=k, random_state=0).fit(vecs)
for r, label in zip(rows, km.labels_):
    r["cluster"] = int(label)
```

Pick 3–5 examples per cluster for the starter set. Archive the rest.

### Step 4 — Harvest expectations from SME-labeled traces

If subject-matter experts have already labeled some traces (via MLflow labeling sessions — see [04-evaluation-runs](../../04-evaluation-runs/SKILL.md)), pull those labels as `expectations`.

```python
from databricks.sdk import WorkspaceClient

w = WorkspaceClient()
# query *_otel_annotations for human feedback
labels_df = w.sql.query("""
  SELECT request_id, assessment_name, value, rationale
  FROM main.skyloyalty_ops.skyloyalty_agent_otel_annotations
  WHERE assessment_source = 'HUMAN'
""")

labels_by_trace: dict[str, dict] = {}
for row in labels_df:
    labels_by_trace.setdefault(row["request_id"], {})[row["assessment_name"]] = {
        "value": row["value"], "rationale": row["rationale"]
    }

for r in rows:
    expectations = {}
    labels = labels_by_trace.get(r["trace_id"], {})
    if "is_correct" in labels:
        expectations["is_correct"] = labels["is_correct"]["value"]
    if "expected_answer" in labels:
        expectations["expected_answer"] = labels["expected_answer"]["value"]
    if expectations:
        r["expectations"] = expectations
```

Rows without expectations are still useful — scorers that don't need ground truth (e.g. `RelevanceToQuery`, guideline judges) can score them.

### Step 5 — LLM paraphrase expansion (optional, for robustness)

To test the agent's robustness to phrasing variants, paraphrase each question 2–3 times.

```python
from openai import OpenAI

client = OpenAI(base_url=os.environ["LLM_GATEWAY_BASE_URL"], api_key=os.environ["DATABRICKS_TOKEN"])

def paraphrase(question: str, n: int = 2) -> list[str]:
    resp = client.chat.completions.create(
        model="claude-sonnet-46",
        temperature=0.7,
        messages=[
            {"role": "system", "content": (
                "Rewrite the user question {n} times, keeping intent identical. "
                "Preserve named entities. Return one paraphrase per line."
            ).format(n=n)},
            {"role": "user", "content": question},
        ],
    )
    return [l.strip() for l in resp.choices[0].message.content.splitlines() if l.strip()][:n]

expanded_rows = []
for r in rows:
    expanded_rows.append(r)
    for para in paraphrase(r["inputs"]["question"]):
        expanded_rows.append({
            **r,
            "inputs": {"question": para},
            "provenance": "synthetic_paraphrase",
            "source_trace_id": r["trace_id"],
        })
```

Always mark paraphrased rows `provenance="synthetic_paraphrase"` so gating logic can weight them differently.

### Step 6 — Validate

Run every row through the standard validation (schema, tool arg types, no PII in expectations).

```python
from mlflow.genai.eval import validate_dataset_rows  # hypothetical; use your existing validator

errors = validate_dataset_rows(expanded_rows)
if errors:
    print(f"{len(errors)} rows rejected; see errors[:5]: {errors[:5]}")
clean_rows = [r for r, e in zip(expanded_rows, errors) if not e]
```

### Step 7 — Merge into UC dataset

```python
import mlflow.genai.datasets as mlfds

ds = mlfds.get_or_create_dataset(
    "main.skyloyalty.skyloyalty_agent_benchmarks",
    schema={"inputs": "MAP<STRING,STRING>",
            "outputs": "MAP<STRING,STRING>",
            "expectations": "MAP<STRING,STRING>",
            "provenance": "STRING",
            "source_trace_id": "STRING"},
)
ds.merge_records(clean_rows, primary_keys=["trace_id"])  # or your dedupe key
```

---

## Review Gate Before Use

Synthetic + production-derived datasets **must** be reviewed by a subject-matter expert before gating releases on them. Recommended:

1. Sample 20 rows.
2. SME reviews each: is the question realistic? is the expectation correct?
3. Flag bad rows for removal; if > 20% are bad, review the generation pipeline before merging.
4. Add a `dataset_version` tag when SME sign-off completes so you can track what was gated on.

Skipping this step ships a lazy ceiling — the agent only beats its own historical outputs.

---

## Keeping the Dataset Fresh

Run the recipe on a weekly or biweekly schedule. Always:

- Dedupe on `trace_id` so re-runs are idempotent.
- Cap the dataset size (e.g. 500 rows) — remove oldest or lowest-variance rows when at cap.
- Track per-cluster coverage so new intents automatically enter the set.
- Preserve a **frozen gold subset** that never changes — regression gates key off this subset so the bar cannot silently move.
