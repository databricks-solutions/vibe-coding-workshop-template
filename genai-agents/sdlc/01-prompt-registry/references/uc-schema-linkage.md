# UC Schema Linkage for Prompt Registry

> Deep-dive reference for the `mlflow.promptRegistryLocation` experiment tag,
> the single most-overlooked step when registering prompts under Unity Catalog.

---

## Why the Tag Exists

MLflow Prompt Registry stores prompts as **UC functions** under a
`catalog.schema` namespace. However, the Experiment UI does **not** discover
prompts by scanning every schema the service principal can access. Instead it
relies on an explicit experiment-level tag that tells the UI *where* to look:

```
mlflow.promptRegistryLocation = "<catalog>.<schema>"
```

Without this tag:

- Prompts **are** registered (you can verify via `mlflow.genai.load_prompt`).
- Prompts **do not** appear in the Experiment → Prompts tab.
- Linked Prompts in trace views may show raw function URIs instead of
  friendly version cards.

---

## Full Implementation: Experiment Setup → Tag → Register → Verify

The following end-to-end example mirrors
`register_judge_prompts()` in `evaluation.py` (lines 2229–2233).

### Step 1 — Set the Experiment

```python
import mlflow

experiment_name = "/Shared/genie-optimization/prompts"
mlflow.set_experiment(experiment_name)
```

### Step 2 — Attach the Registry Location Tag

```python
catalog = "main"
schema = "genie_optimization"
uc_schema = f"{catalog}.{schema}"

if uc_schema:
    try:
        mlflow.set_experiment_tags({
            "mlflow.promptRegistryLocation": uc_schema,
        })
    except Exception:
        # Non-fatal: prompts still register, but UI discoverability is lost.
        import logging
        logging.getLogger(__name__).warning(
            "Failed to set experiment prompt registry location to %s",
            uc_schema,
            exc_info=True,
        )
```

**Key points:**

- The value must be exactly `catalog.schema` (two-level). Three-level
  names (with prompt suffix) or one-level names are rejected.
- The tag is **idempotent** — calling `set_experiment_tags` again with the same
  value is a no-op.
- If the experiment does not yet exist, `set_experiment` creates it and the
  subsequent `set_experiment_tags` call adds the tag. Order matters:
  set the experiment *before* setting tags.

### Step 3 — Register a Prompt

```python
import mlflow.genai

prompt_name = f"{uc_schema}.genie_opt_syntax_validity"
version = mlflow.genai.register_prompt(
    name=prompt_name,
    template="Score the SQL syntax: {{ sql_text }}",
    commit_message="Initial syntax judge",
    tags={"domain": "genie_optimization", "type": "judge"},
)
```

### Step 4 — Set an Alias

```python
mlflow.genai.set_prompt_alias(
    name=prompt_name,
    alias="production",
    version=version.version,
)
```

### Step 5 — Verify in the UI

1. Open the MLflow Experiment at the path you used in `set_experiment`.
2. Click the **Prompts** tab.
3. You should see the prompt listed with its latest version and alias.

If it does not appear, see Troubleshooting below.

### Step 6 — Verify Programmatically

```python
loaded = mlflow.genai.load_prompt(f"prompts:/{prompt_name}@production")
assert loaded.template is not None, "Prompt template should not be None"
print(f"Loaded prompt version {loaded.version}: {loaded.template[:80]}...")
```

---

## Troubleshooting: Prompts Not Appearing in UI

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Prompts tab is empty | Missing `mlflow.promptRegistryLocation` tag | Set the tag as shown above |
| Tag is set but still empty | Tag value does not match the catalog.schema used in `register_prompt` | Ensure they are identical (case-sensitive) |
| Tag is set, prompt shows but wrong version | Alias not updated after re-registration | Call `set_prompt_alias` after each `register_prompt` |
| Prompts tab shows prompts from wrong schema | Experiment has a stale tag from a previous run | Update the tag value to the correct schema |
| UI shows "No permission" | Service principal lacks `EXECUTE` on the schema | Grant `EXECUTE` privilege (see Permissions below) |
| Prompt loads fine in code but not in UI | UI caches experiment metadata | Wait ~30s or refresh the experiment page |

### Quick Diagnostic Script

```python
import mlflow

exp = mlflow.get_experiment_by_name("/Shared/genie-optimization/prompts")
if exp is None:
    print("ERROR: Experiment not found")
else:
    tags = exp.tags or {}
    loc = tags.get("mlflow.promptRegistryLocation", "<NOT SET>")
    print(f"Experiment ID: {exp.experiment_id}")
    print(f"promptRegistryLocation: {loc}")
    if loc == "<NOT SET>":
        print("FIX: Call mlflow.set_experiment_tags({'mlflow.promptRegistryLocation': '<catalog>.<schema>'})")
```

---

## Schema Ownership and Permissions

Prompt Registry operations map to UC function privileges:

| Operation | Required privilege | Granted on |
|-----------|-------------------|------------|
| `register_prompt` (first version) | `CREATE FUNCTION` | Schema |
| `register_prompt` (new version) | Owner of the function **or** `MANAGE` | Function or Schema |
| `set_prompt_alias` | Owner of the function **or** `MANAGE` | Function or Schema |
| `load_prompt` | `EXECUTE` | Function or Schema |
| `delete_prompt_alias` | Owner of the function **or** `MANAGE` | Function or Schema |

### Granting Permissions

```sql
-- Grant all required privileges to the app service principal
GRANT CREATE FUNCTION, EXECUTE, MANAGE
  ON SCHEMA main.genie_optimization
  TO `genie-space-optimizer-sp`;

-- Or grant ownership for full control
ALTER SCHEMA main.genie_optimization
  OWNER TO `genie-space-optimizer-sp`;
```

### Common Permission Errors

```
PERMISSION_DENIED: User does not have CREATE FUNCTION on Schema 'main.genie_optimization'
```

This means the service principal running the registration does not have
sufficient privileges. The `_classify_prompt_registration_error()` function
in `evaluation.py` detects this pattern and produces an actionable remediation
string.

```
PERMISSION_DENIED: User does not have permission to update prompt 'main.genie_optimization.genie_opt_syntax_validity'
```

This is an **ownership conflict** — a different principal originally created
the function. See `references/ownership-conflict-handling.md` for the full
fallback strategy.

---

## Multi-Schema Patterns for Different Domains

Large organizations may partition prompts across schemas by domain or team:

```
main.genie_optimization       ← Genie Space optimization judges
main.genie_benchmarks         ← Benchmark scoring prompts
main.customer_support_prompts ← Customer-facing agent prompts
```

### Pattern: One Experiment per Schema

Each schema gets its own experiment with a matching
`promptRegistryLocation` tag:

```python
schemas = {
    "optimization": "main.genie_optimization",
    "benchmarks": "main.genie_benchmarks",
    "support": "main.customer_support_prompts",
}

for domain, uc_schema in schemas.items():
    exp_path = f"/Shared/prompt-registry/{domain}"
    mlflow.set_experiment(exp_path)
    mlflow.set_experiment_tags({
        "mlflow.promptRegistryLocation": uc_schema,
    })
```

### Pattern: Single Experiment, Multiple Schemas

If you prefer a single experiment, note that `promptRegistryLocation` only
accepts **one** value. The UI will only show prompts from that one schema.
Prompts in other schemas still work programmatically but won't appear in
the Prompts tab.

**Recommendation:** Use one experiment per schema for full UI visibility.
This is the pattern used in the Genie Space Optimizer codebase.

### Pattern: Dev / Staging / Prod Schema Separation

```
dev.genie_optimization        ← Development iterations
staging.genie_optimization    ← Pre-production validation
main.genie_optimization       ← Production prompts
```

Each environment uses its own catalog (or schema) and experiment path. The
`uc_schema` parameter in `register_judge_prompts()` controls which target
is used. Deploy scripts pass the appropriate catalog/schema via environment
variables (`GSO_CATALOG`, `GSO_SCHEMA`).

---

## Source References

- `evaluation.py` lines 2229–2233: experiment tag setup in `register_judge_prompts()`
- `evaluation.py` lines 2241–2264: registration loop with `set_prompt_alias`
- `config.py` line 2421–2425: `PROMPT_NAME_TEMPLATE`, `PROMPT_ALIAS`,
  `INSTRUCTION_PROMPT_NAME_TEMPLATE`, `INSTRUCTION_PROMPT_ALIAS`
- `evaluation.py` lines 2002–2057: `_classify_prompt_registration_error()` for
  permission diagnostics

---

## Related References

- [ownership-conflict-handling.md](ownership-conflict-handling.md) — what to do
  when a different principal owns the prompt function.
- [loading-patterns.md](loading-patterns.md) — how `load_prompt()` resolves
  aliases and links to traces.
- [ab-testing.md](ab-testing.md) — champion/challenger alias workflows.
