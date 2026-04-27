# Custom Retriever Schemas

When your agent uses a retriever tool (Vector Search, knowledge base, etc.),
trace it with an MLflow **RETRIEVER span** and declare its output schema so
Databricks can:

1. **Display source document links** in AI Playground automatically.
2. **Run groundedness and relevance judges** in Agent Evaluation.

## When You Need This

| Retriever Type | Schema Required? |
|---|---|
| `databricks_openai.VectorSearchRetrieverTool` | No — AI Bridge tools conform automatically |
| `databricks_langchain.VectorSearchRetrieverTool` | No — AI Bridge tools conform automatically |
| Custom retriever (your own code) | **Yes — call `set_retriever_schema()`** |
| Third-party retriever (LlamaIndex, etc.) | **Yes — call `set_retriever_schema()`** |

**Recommendation:** Prefer the AI Bridge retriever tools from
`databricks_openai` or `databricks_langchain` when possible. They already
conform to the MLflow retriever schema with no additional configuration.
See [Develop a retriever locally using AI Bridge](https://docs.databricks.com/aws/en/generative-ai/agent-framework/unstructured-retrieval-tools#ai-bridge).

## Declaring the Schema

Call `mlflow.models.set_retriever_schema()` at module level in your agent file
(alongside `mlflow.models.set_model()`):

```python
import mlflow

mlflow.models.set_retriever_schema(
    name="docs_vector_search",
    primary_key="document_id",
    text_column="chunk_text",
    doc_uri="doc_uri",
    other_columns=["title"],
)
```

| Parameter | Maps To | Purpose |
|---|---|---|
| `name` | Your RETRIEVER span name | Links the schema to the correct span |
| `primary_key` | Unique ID column | Deduplication across retrieval calls |
| `text_column` | Text content column | Displayed in Playground source panel |
| `doc_uri` | Document URI column | **Critical for evaluation** — ground truth comparison |
| `other_columns` | Additional metadata | Passed through but not used by judges |

## Complete Example

```python
import mlflow
from agents import Agent, function_tool
from databricks.sdk import WorkspaceClient

mlflow.models.set_retriever_schema(
    name="knowledge_base_search",
    primary_key="chunk_id",
    text_column="content",
    doc_uri="source_url",
    other_columns=["title", "last_updated"],
)

@mlflow.trace(name="knowledge_base_search", span_type="RETRIEVER")
def search_knowledge_base(query: str, max_results: int = 5) -> list[dict]:
    """Search the internal knowledge base."""
    w = WorkspaceClient()
    results = w.vector_search_indexes.query_index(
        index_name="prod.docs.knowledge_index",
        columns=["chunk_id", "content", "source_url", "title", "last_updated"],
        query_text=query,
        num_results=max_results,
    )
    return [
        {
            "chunk_id": row[0],
            "content": row[1],
            "source_url": row[2],
            "title": row[3],
            "last_updated": row[4],
        }
        for row in results.result.data_array
    ]

@function_tool
def search_docs(query: str) -> str:
    """Search internal documentation and return relevant content."""
    results = search_knowledge_base(query)
    if not results:
        return "No relevant documents found."
    return "\n\n".join(
        f"[{r['title']}]({r['source_url']})\n{r['content']}"
        for r in results
    )

agent = Agent(
    name="docs-assistant",
    instructions="Answer questions using the knowledge base. Cite sources.",
    model="databricks-claude-sonnet-4-6",
    tools=[search_docs],
)

mlflow.models.set_model(agent)
```

Key points:
- The `@mlflow.trace` span name (`"knowledge_base_search"`) must match the
  `name` in `set_retriever_schema()`.
- The span type must be `"RETRIEVER"` for Databricks to recognize it.
- Column names in the returned dicts must match what you declared in the schema.

## Why `doc_uri` Matters for Evaluation

`doc_uri` is the primary identifier for comparing retrieved documents against
ground truth evaluation sets. When you run Agent Evaluation:

- The **relevance judge** checks whether the retrieved `doc_uri` values match
  the expected source documents.
- The **groundedness judge** verifies that the agent's answer is supported by
  the content of documents at those URIs.

Without `doc_uri`, these judges cannot run, and your evaluation results will
be incomplete.

See [Evaluation sets](https://docs.databricks.com/aws/en/generative-ai/agent-evaluation/evaluation-set)
for how to structure ground truth data.

## DO / DON'T

```python
# ✅ DO: Declare schema at module level, before set_model()
mlflow.models.set_retriever_schema(
    name="my_retriever",
    primary_key="id",
    text_column="text",
    doc_uri="uri",
)
mlflow.models.set_model(agent)

# ❌ DON'T: Declare schema inside predict() — runs per-request, wasteful
class MyAgent(ResponsesAgent):
    def predict(self, request):
        mlflow.models.set_retriever_schema(...)  # Wrong place
```

```python
# ✅ DO: Match span name to schema name
mlflow.models.set_retriever_schema(name="my_search", ...)

@mlflow.trace(name="my_search", span_type="RETRIEVER")  # Names match
def my_search(query): ...

# ❌ DON'T: Use mismatched names
mlflow.models.set_retriever_schema(name="my_search", ...)

@mlflow.trace(name="search_func", span_type="RETRIEVER")  # Mismatch!
def search_func(query): ...
```

```python
# ✅ DO: Use AI Bridge tools when they fit (no schema setup needed)
from databricks_openai import VectorSearchRetrieverTool

vs_tool = VectorSearchRetrieverTool(index_name="prod.docs.knowledge_index")
agent = Agent(tools=[vs_tool], ...)

# ❌ DON'T: Manually wrap AI Bridge tools with set_retriever_schema
# They already handle this internally
```

## References

- [Author an agent — Custom retriever schemas](https://docs.databricks.com/aws/en/generative-ai/agent-framework/author-agent#custom-retriever-schemas)
- [Connect agents to unstructured data](https://docs.databricks.com/aws/en/generative-ai/agent-framework/unstructured-retrieval-tools)
- [MLflow RETRIEVER spans](https://mlflow.org/docs/latest/genai/tracing/concepts/span/#retriever-spans)
- [mlflow.models.set_retriever_schema](https://mlflow.org/docs/latest/api_reference/python_api/mlflow.models.html#mlflow.models.set_retriever_schema)
- [Evaluation sets](https://docs.databricks.com/aws/en/generative-ai/agent-evaluation/evaluation-set)
