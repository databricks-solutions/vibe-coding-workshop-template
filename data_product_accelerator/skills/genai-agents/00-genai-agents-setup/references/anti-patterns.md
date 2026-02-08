# Consolidated Anti-Patterns

## 1. Manual Signatures → Breaks AI Playground

```python
# ❌ NEVER: Manual signature breaks auto-inference
mlflow.pyfunc.log_model(
    python_model=agent,
    signature=my_custom_signature,  # ❌ Breaks AI Playground!
)

# ✅ ALWAYS: Let MLflow infer signature from ResponsesAgent
mlflow.pyfunc.log_model(
    python_model=agent,
    # NO signature parameter!
)
```

**Why:** ResponsesAgent has automatic signature inference. Manual signatures override this and break AI Playground compatibility.

## 2. LLM Fallback for Data Queries → Hallucination

```python
# ❌ DANGEROUS: LLM generates FAKE DATA
try:
    result = genie.query(question)
except Exception:
    # ❌ FATAL: LLM fallback = hallucinated data
    result = llm.invoke(f"Answer: {question}")

# ✅ CORRECT: Return explicit error
try:
    result = genie.query(question)
except Exception as e:
    result = f"""## Genie Query Failed
**Error:** {str(e)}
I was unable to retrieve real data.
**Note:** I will NOT generate fake data."""
```

**Production Learning (Jan 7, 2026):** Agent showed "Job Failures Analysis" with completely fabricated job names. User couldn't tell the data was fake.

## 3. OBO in Non-Serving Contexts → Permission Errors

```python
# ❌ WRONG: Always use OBO
client = WorkspaceClient(credentials_strategy=ModelServingUserCredentials())

# ✅ CORRECT: Context detection
is_model_serving = (
    os.environ.get("IS_IN_DB_MODEL_SERVING_ENV") == "true" or
    os.environ.get("DATABRICKS_SERVING_ENDPOINT") is not None or
    os.environ.get("MLFLOW_DEPLOYMENT_FLAVOR_NAME") == "databricks"
)
if is_model_serving:
    client = WorkspaceClient(credentials_strategy=ModelServingUserCredentials())
else:
    client = WorkspaceClient()  # Default auth for notebooks/evaluation
```

**Production Learning (Jan 27, 2026):** Evaluation jobs failed because OBO was attempted outside Model Serving.

## 4. Missing _extract_response_text() → Scores = 0.0

```python
# ❌ WRONG: Direct access fails with serialized format
@scorer
def broken(inputs, outputs):
    text = outputs.get("response", "")  # ❌ Key doesn't exist!
    return Score(value=0.0)

# ✅ CORRECT: Use universal extraction helper
@scorer
def working(inputs, outputs):
    text = _extract_response_text(outputs)  # ✅ Handles all formats
    return Score(value=calculate_score(text))
```

**Impact:** 9+ custom scorers returned 0.0 for ALL responses. Took 5+ iterations to discover.

## 5. langchain_databricks in Scorers → Serverless Failures

```python
# ❌ WRONG: Package install issues on serverless
from langchain_databricks import ChatDatabricks
llm = ChatDatabricks(endpoint="...")

# ✅ CORRECT: Databricks SDK - reliable everywhere
from databricks.sdk import WorkspaceClient
w = WorkspaceClient()
response = w.serving_endpoints.query(name="endpoint", messages=[...])
```

## 6. Too Many Guidelines → Low Scores

```python
# ❌ WRONG: 8 sections = score 0.20
guidelines = ["Section 1...", "Section 2...", ..., "Section 8..."]

# ✅ CORRECT: 4-6 focused sections = score 0.50+
guidelines = [
    "Data Accuracy: MUST include specific numbers with time context",
    "No Fabrication: MUST NEVER fabricate numbers",
    "Actionability: MUST provide specific recommendations",
    "Professional Tone: MUST use proper formatting",
]
```

## 7. Missing Metric Aliases → Silent Threshold Bypass

```python
# ❌ WRONG: Only checks one metric name
passed = metrics.get("relevance/mean", 0) >= 0.4
# Problem: MLflow 3.1 uses "relevance_to_query/mean"

# ✅ CORRECT: Check both names
METRIC_ALIASES = {"relevance/mean": ["relevance_to_query/mean"]}
passed = check_thresholds(metrics, thresholds)  # Handles aliases
```

## 8. Immutable Scorer Pattern Violation

```python
# ❌ WRONG: Object not updated
safety = Safety().register(name="safety")
safety.start(sampling_config=...)  # ❌ Not assigned!

# ✅ CORRECT: Assign result
safety = Safety().register(name="safety")
safety = safety.start(sampling_config=...)  # ✅ Assigned!
```

## 9. Genie API-Only Updates → Lost on Redeployment

```python
# ❌ WRONG: Only API update
subprocess.run(["databricks", "api", "patch", ...])
# Change lost when config redeployed from repository!

# ✅ CORRECT: Dual persistence
subprocess.run(["databricks", "api", "patch", ...])  # Immediate
with open("src/genie/config.json", "w") as f:         # Persistent
    json.dump(templated_config, f, indent=2)
```

## 10. External Imports in Scorers → Serialization Fails

```python
# ❌ WRONG: Import at module level
import external_library
@scorer
def bad(outputs):
    return external_library.process(outputs)

# ✅ CORRECT: Import inside function
@scorer
def good(outputs):
    import json  # Inline import
    return len(json.dumps(outputs))
```

## 11. Assuming Memory Tables Exist

```python
# ❌ WRONG: Crashes if tables not created
memory = ShortTermMemory()
with memory.get_checkpointer() as cp:
    graph = workflow.compile(checkpointer=cp)

# ✅ CORRECT: Graceful fallback
try:
    memory = ShortTermMemory()
    with memory.get_checkpointer() as cp:
        graph = workflow.compile(checkpointer=cp)
except Exception:
    graph = workflow.compile()  # Stateless fallback
```

## 12. Hardcoded Prompts in Agent Code

```python
# ❌ WRONG: No versioning, no A/B testing
PROMPT = "You are a helpful assistant..."

# ✅ CORRECT: Load from registry
prompt = load_prompt(spark, catalog, schema, "orchestrator")
```

## 13. Forgetting to Return thread_id

```python
# ❌ WRONG: Client can't continue conversation
return ResponsesAgentResponse(output=[...])

# ✅ CORRECT: Return thread_id for conversation tracking
return ResponsesAgentResponse(
    output=[...],
    custom_outputs={"thread_id": thread_id}
)
```

## 14. Sequential Domain Queries

```python
# ❌ WRONG: Slow sequential execution
for domain in domains:
    result = query_genie(domain, query)

# ✅ CORRECT: Parallel execution
from concurrent.futures import ThreadPoolExecutor, as_completed
with ThreadPoolExecutor() as executor:
    futures = {executor.submit(query_genie, d, query): d for d in domains}
    results = {domains[f]: f.result() for f in as_completed(futures)}
```
