# Prompt Loading Patterns

> Complete reference for `mlflow.genai.load_prompt()`, trace linking,
> caching strategies, error handling, and template variable injection.

---

## Basic Loading with Aliases

The canonical load URI follows the pattern `prompts:/<name>@<alias>`:

```python
import mlflow.genai

prompt = mlflow.genai.load_prompt("prompts:/main.genie_optimization.genie_opt_syntax_validity@production")

print(f"Version: {prompt.version}")
print(f"Template: {prompt.template}")
```

### URI Format

```
prompts:/<catalog>.<schema>.<prompt_name>@<alias>
prompts:/<catalog>.<schema>.<prompt_name>/<version_number>
```

| Form | Example | Use case |
|------|---------|----------|
| By alias | `prompts:/main.genie_opt.judge@production` | Production code — follows alias pointer |
| By version | `prompts:/main.genie_opt.judge/3` | Debugging — pin to exact version |

**Always prefer alias-based loading in production.** Version-pinned URIs
require code changes to update; aliases are mutable pointers that can be
rotated without redeployment.

---

## Trace Linking via `_link_prompt_to_trace()`

When `load_prompt()` is called **inside an active MLflow trace**, MLflow
automatically associates the loaded prompt version with that trace. This
creates a "Linked Prompts" entry visible in the trace UI.

### Production Implementation

From `evaluation.py` lines 306–321:

```python
import mlflow

from genie_space_optimizer.common.config import PROMPT_ALIAS


def _link_prompt_to_trace(prompt_name: str) -> None:
    """Load a registered prompt inside the current trace to link it.

    MLflow automatically associates ``load_prompt()`` calls with the
    active trace, making the prompt version visible in the Linked Prompts
    tab of the trace UI.  Failures are silently ignored so scoring continues.
    """
    if not prompt_name:
        return
    try:
        mlflow.genai.load_prompt(f"prompts:/{prompt_name}@{PROMPT_ALIAS}")
    except Exception:
        try:
            mlflow.genai.load_prompt(f"prompts:/{prompt_name}@latest")
        except Exception:
            logger.debug(
                "Could not load prompt '%s' for trace linking", prompt_name
            )
```

### How It Works

1. Caller starts a trace (via `@mlflow.trace` or `mlflow.start_span()`).
2. Inside the trace, `load_prompt()` is called.
3. MLflow records the prompt name, version, and alias in the trace metadata.
4. In the trace UI, the "Linked Prompts" tab shows which prompt version
   was active for each trace.

### When to Use

- **Scoring functions** — call `_link_prompt_to_trace(prompt_name)` at the
  start of each judge so the trace shows which prompt drove the score.
- **Agent calls** — call inside the agent's main span so instruction
  prompt versions are visible.
- **Load-for-side-effects** — you do not need to use the returned template.
  The act of loading is sufficient to create the link.

### When NOT to Use

- Outside a trace context — `load_prompt()` still works but no linking occurs.
- In tight loops with thousands of iterations — each call is a network
  round-trip. See Caching below.

---

## Caching Considerations for High-Throughput Serving

`mlflow.genai.load_prompt()` makes a **network call** to the MLflow tracking
server on every invocation. For high-throughput applications, this adds
latency and load.

### Strategy 1 — Module-Level Cache

Load prompts once at module import time. Suitable when alias changes are
infrequent and a process restart is acceptable to pick up new versions:

```python
import mlflow.genai

_PROMPT_CACHE: dict[str, str] = {}


def get_prompt_template(prompt_name: str, alias: str = "production") -> str:
    cache_key = f"{prompt_name}@{alias}"
    if cache_key not in _PROMPT_CACHE:
        loaded = mlflow.genai.load_prompt(f"prompts:/{prompt_name}@{alias}")
        _PROMPT_CACHE[cache_key] = loaded.template
    return _PROMPT_CACHE[cache_key]
```

### Strategy 2 — TTL-Based Cache

Use a TTL so prompts refresh periodically without restart:

```python
import time
import mlflow.genai

_PROMPT_TTL_CACHE: dict[str, tuple[str, float]] = {}
CACHE_TTL_SECONDS = 300  # 5 minutes


def get_prompt_template_ttl(
    prompt_name: str, alias: str = "production"
) -> str:
    cache_key = f"{prompt_name}@{alias}"
    now = time.monotonic()
    if cache_key in _PROMPT_TTL_CACHE:
        template, expires_at = _PROMPT_TTL_CACHE[cache_key]
        if now < expires_at:
            return template
    loaded = mlflow.genai.load_prompt(f"prompts:/{prompt_name}@{alias}")
    _PROMPT_TTL_CACHE[cache_key] = (loaded.template, now + CACHE_TTL_SECONDS)
    return loaded.template
```

### Strategy 3 — Load Once per Evaluation Batch

The Genie Space Optimizer uses this approach: prompts are loaded and linked
at the start of each scoring call (one per judge per question), which is
acceptable because batch sizes are modest (tens to hundreds of questions).

For serving endpoints processing thousands of requests per second, prefer
Strategy 2.

### Trace Linking with Caching

If you cache templates but still want trace linking, separate the concerns:

```python
def score_with_prompt(prompt_name: str, input_data: dict) -> dict:
    template = get_prompt_template_ttl(prompt_name)  # cached, fast

    _link_prompt_to_trace(prompt_name)  # uncached, creates trace link

    rendered = render_template(template, **input_data)
    return call_llm(rendered)
```

The trace-linking call is lightweight (it only needs to resolve the alias)
and happens once per trace, not once per cached lookup.

---

## Error Handling for Missing Prompts / Aliases

### Prompt Does Not Exist

```python
try:
    prompt = mlflow.genai.load_prompt("prompts:/main.genie_opt.nonexistent@production")
except mlflow.exceptions.MlflowException as e:
    if "RESOURCE_DOES_NOT_EXIST" in str(e):
        print("Prompt not found — has it been registered?")
    else:
        raise
```

### Alias Does Not Exist

```python
try:
    prompt = mlflow.genai.load_prompt("prompts:/main.genie_opt.judge@staging")
except mlflow.exceptions.MlflowException as e:
    if "not found" in str(e).lower():
        print("Alias 'staging' not set — falling back to 'latest'")
        prompt = mlflow.genai.load_prompt("prompts:/main.genie_opt.judge@latest")
    else:
        raise
```

### Cascading Fallback (Production Pattern)

The `_link_prompt_to_trace()` function demonstrates the canonical fallback:

1. Try `@production` (the standard alias).
2. If that fails, try `@latest` (auto-created by MLflow).
3. If both fail, log and continue — never crash the scoring pipeline.

This pattern ensures graceful degradation when prompts have not yet been
registered or when aliases have been deleted.

---

## Template Variable Injection After Loading

`load_prompt()` returns a `Prompt` object whose `.template` field contains
raw `{{ variable }}` placeholders. You must render them before sending to
the LLM.

### Using MLflow's Built-In Rendering

```python
prompt = mlflow.genai.load_prompt(f"prompts:/{prompt_name}@production")

rendered = prompt.format(
    sql_text="SELECT * FROM orders WHERE status = 'active'",
    context="E-commerce order tracking",
)
print(rendered)
```

### Manual Rendering (Jinja2-Compatible)

If you need custom rendering logic (e.g., conditional sections):

```python
from jinja2 import Template

prompt = mlflow.genai.load_prompt(f"prompts:/{prompt_name}@production")
jinja_template = Template(prompt.template)
rendered = jinja_template.render(
    sql_text="SELECT * FROM orders",
    context="E-commerce",
)
```

### Variable Discovery

Inspect which variables a template expects:

```python
import re

prompt = mlflow.genai.load_prompt(f"prompts:/{prompt_name}@production")
variables = re.findall(r"\{\{\s*(\w+)\s*\}\}", prompt.template)
print(f"Template variables: {variables}")
```

---

## Loading by Version Number

For debugging or reproducing historical results, load a specific version:

```python
prompt_v2 = mlflow.genai.load_prompt(f"prompts:/{prompt_name}/2")
print(f"Version 2 template: {prompt_v2.template[:100]}...")
```

This is useful when:

- Investigating a regression: compare the template text across versions.
- Auditing: prove which template was active during a past evaluation run.
- Testing: validate a specific version before promoting it via alias.

---

## Source References

- `evaluation.py` lines 306–321: `_link_prompt_to_trace()` implementation
  with `@production` → `@latest` fallback.
- `evaluation.py` lines 324–335: `_call_llm_for_scoring()` which calls
  `_link_prompt_to_trace()` before each LLM invocation.
- `config.py` line 2422: `PROMPT_ALIAS = "production"` — the default alias.
- `config.py` line 2425: `INSTRUCTION_PROMPT_ALIAS = "latest"` — instruction
  prompts use `latest` by default.

## Related References

- [uc-schema-linkage.md](uc-schema-linkage.md) — the experiment tag that
  enables UI discovery.
- [ab-testing.md](ab-testing.md) — using aliases for champion/challenger
  experiments.
- [ownership-conflict-handling.md](ownership-conflict-handling.md) — when
  `load_prompt()` fails due to permission issues.
