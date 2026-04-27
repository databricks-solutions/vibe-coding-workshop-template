# `predict_fn` Contract for `optimize_prompts`

`mlflow.genai.optimize_prompts()` calls your `predict_fn` hundreds of times with different candidate prompt bodies substituted for the kwargs matching `prompt_uris`. If the function contract is wrong, optimization silently produces noise.

---

## Signature Rules

1. First positional argument is **`inputs: dict`** — one row from `train_data["inputs"]`.
2. Each prompt in `prompt_uris` injects **one kwarg** whose name is the **prompt variable name**, not the full URI.
   - URI `prompts:/main.x.system_instructions@production` → kwarg `system_instructions: str`.
   - URI `prompts:/main.x.planner@production` → kwarg `planner: str`.
3. Return type is a **`dict`**. Keys must cover whatever your scorers read.

```python
def predict_fn(inputs: dict, system_instructions: str) -> dict:
    ...
    return {"answer": ..., "tool_calls": ...}
```

---

## You MUST Inject the Kwarg Into the LLM Call

The most common silent failure: the kwarg is accepted but ignored.

```python
def predict_fn(inputs: dict, system_instructions: str) -> dict:
    # WRONG: re-loads the registered prompt, ignoring the candidate body
    from mlflow.genai import load_prompt
    prompt = load_prompt("prompts:/main.x.system_instructions@production")
    llm_out = call_llm(system=prompt.template, user=inputs["question"])
    return {"answer": llm_out}
```

Scores won't change between candidates because the actual system text never changes.

```python
def predict_fn(inputs: dict, system_instructions: str) -> dict:
    # RIGHT: pass the injected body directly
    llm_out = call_llm(system=system_instructions, user=inputs["question"])
    return {"answer": llm_out}
```

**Sanity check before running optimization:**

```python
result1 = predict_fn({"question": "q"}, system_instructions="body A")
result2 = predict_fn({"question": "q"}, system_instructions="body B")
assert result1 != result2, "predict_fn ignores system_instructions kwarg"
```

---

## Multi-Prompt

Kwargs map 1:1 to `prompt_uris` by **variable name**. Order in `prompt_uris` determines the order of `result.optimized_prompts`, but kwargs must match variable names.

```python
prompt_uris = [
    "prompts:/main.x.planner@production",          # variable name: planner
    "prompts:/main.x.answer_instructions@production",  # variable name: answer_instructions
]

def predict_fn(inputs, planner: str, answer_instructions: str) -> dict:
    plan = call_planner(inputs["question"], planner)
    ans = call_answerer(plan, inputs["question"], answer_instructions)
    return {"answer": ans, "plan": plan}
```

Variable name = the slug after the last `.` in the prompt name (what you registered).

---

## Streaming / Async Agents

The optimizer runs `predict_fn` synchronously. If your production agent streams, use a synchronous wrapper that collects the full response.

```python
def predict_fn(inputs, system_instructions: str) -> dict:
    chunks = []
    for delta in agent.stream(inputs["question"], system=system_instructions):
        chunks.append(delta)
    return {"answer": "".join(chunks)}
```

Do not use `async def predict_fn` — wrap with `asyncio.run(...)` inside a sync function if you must.

---

## Session / Memory State

Optimization is **stateless** between rows. Do not rely on a shared conversation history across `train_data` rows. If your agent requires memory for the question to make sense, flatten the multi-turn context into `inputs["question"]` before calling.

```python
def predict_fn(inputs, system_instructions: str) -> dict:
    # inputs already contains the flattened turn history in inputs["question"]
    ans = call_agent(system_instructions, inputs["question"])
    return {"answer": ans}
```

---

## Scorer-Readable Return Dict

Every scorer you pass to `optimize_prompts(scorers=[...])` reads specific fields from the return dict. Common contracts:

| Scorer | Reads |
|--------|-------|
| `Correctness` | `outputs["answer"]`, `expectations["expected_answer"]` or similar |
| `RelevanceToQuery` | `outputs["answer"]`, `inputs["question"]` |
| `Guidelines` | `outputs["answer"]` |
| Custom `@scorer` | Whatever your function reads |

If in doubt: log the full return dict and the full scorer call signature on one row, verify by hand, then run optimization.

---

## Validating Before Full Run

Run a 3-row micro-optimization first to flush out contract bugs before burning a full budget:

```python
result = mlflow.genai.optimize_prompts(
    predict_fn=predict_fn,
    train_data=train_data[:3],
    prompt_uris=[prompt_uri],
    optimizer=GepaPromptOptimizer(
        reflection_model="databricks:/databricks-claude-sonnet-4-6",
        max_metric_calls=10,   # tiny budget for sanity
    ),
    scorers=[Correctness()],
)
```

If the 3-row run raises, the full run will too.
