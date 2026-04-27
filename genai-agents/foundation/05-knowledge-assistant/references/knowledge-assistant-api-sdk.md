# Knowledge Assistant — API and SDK Reference

Progressive-load this file when implementing F5 lifecycle steps. Content is
grounded in the public [Knowledge Assistants REST API](https://docs.databricks.com/api/workspace/knowledgeassistants)
and the Databricks SDK for Python.

> **Beta.** Exact field names, request shapes, and pagination semantics may
> evolve. When in doubt, consult the REST reference and the SDK's
> `databricks.sdk.service.knowledgeassistants` module docstrings.

---

## Operation Map

| Lifecycle Step | REST | Python SDK (`WorkspaceClient().knowledge_assistants`) |
|---|---|---|
| Create KA | `POST /api/2.0/knowledge-assistants` | `create_knowledge_assistant(knowledge_assistant=...)` |
| Get KA | `GET /api/2.0/{name}` | `get_knowledge_assistant(name=...)` |
| List KAs | `GET /api/2.0/knowledge-assistants` | `list_knowledge_assistants()` |
| Update KA | `PATCH /api/2.0/{name}` | `update_knowledge_assistant(name=..., update_mask=...)` |
| Delete KA | `DELETE /api/2.0/{name}` | `delete_knowledge_assistant(name=...)` |
| Add source | `POST /api/2.0/{parent}/knowledge-sources` | `create_knowledge_source(parent=..., knowledge_source=...)` |
| Get source | `GET /api/2.0/{name}` | `get_knowledge_source(name=...)` |
| List sources | `GET /api/2.0/{parent}/knowledge-sources` | `list_knowledge_sources(parent=...)` |
| Update source | `PATCH /api/2.0/{name}` | `update_knowledge_source(name=..., update_mask=...)` |
| Delete source | `DELETE /api/2.0/{name}` | `delete_knowledge_source(name=...)` |
| Sync sources | `POST /api/2.0/{name}:syncKnowledgeSources` | `sync_knowledge_sources(name=...)` |

Resource names follow:

- KA: `knowledge-assistants/<id>`
- Source: `knowledge-assistants/<id>/knowledge-sources/<source_id>`

---

## Create KA — Full Example

```python
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.knowledgeassistants import KnowledgeAssistant

w = WorkspaceClient()

ka = w.knowledge_assistants.create_knowledge_assistant(
    knowledge_assistant=KnowledgeAssistant(
        display_name="loyalty-policy-assistant",
        description="Loyalty program Q&A with citations.",
        instructions=(
            "You are a loyalty policy assistant. "
            "Always cite the specific document and section. "
            "If information is not in the documents, say so explicitly."
        ),
    )
)
```

---

## Attach Source — UC Files

```python
from databricks.sdk.service.knowledgeassistants import KnowledgeSource, FilesSpec

source = w.knowledge_assistants.create_knowledge_source(
    parent=ka.name,
    knowledge_source=KnowledgeSource(
        display_name="loyalty-docs",
        description="Program rules, tier benefits, FAQ.",
        source_type="files",
        files=FilesSpec(path="/Volumes/main/skyloyalty/loyalty_docs"),
    ),
)
```

Allowed file types: `.txt`, `.pdf`, `.md`, `.ppt`/`.pptx`, `.doc`/`.docx`.
Files > 50 MB, filenames starting with `_` or `.`, and UC tables are skipped.

## Attach Source — Vector Search Index

```python
from databricks.sdk.service.knowledgeassistants import KnowledgeSource, IndexSpec

source = w.knowledge_assistants.create_knowledge_source(
    parent=ka.name,
    knowledge_source=KnowledgeSource(
        display_name="loyalty-docs-index",
        description="Pre-indexed loyalty docs (GTE embeddings).",
        source_type="index",
        index=IndexSpec(
            index_name="main.skyloyalty.loyalty_docs_index",
            text_col="content",
            doc_uri_col="doc_uri",
        ),
    ),
)
```

The index **must** use `databricks-gte-large-en` as its embedding model, and
the embedding endpoint **must** have AI Guardrails and rate limits disabled.

---

## Sync + Poll Readiness

```python
import time

w.knowledge_assistants.sync_knowledge_sources(name=ka.name)

def wait_for_ready(name: str, timeout_s: int = 3600, interval_s: int = 30):
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        current = w.knowledge_assistants.get_knowledge_assistant(name=name)
        status = (
            getattr(current, "endpoint_status", None)
            or getattr(current, "state", None)
            or ""
        )
        if str(status).upper() in {"ONLINE", "READY"}:
            return current
        time.sleep(interval_s)
    raise TimeoutError(f"KA {name} not ready within {timeout_s}s")

ready = wait_for_ready(ka.name)
```

Budget up to a few hours the first time for large corpora. Subsequent syncs
are incremental.

---

## Capture Endpoint Name and Knowledge Assistant ID

```python
# ka.name is "knowledge-assistants/<id>" — the trailing segment is the id.
knowledge_assistant_id = ka.name.split("/")[-1]

# Prefer SDK-surfaced values where available:
refreshed = w.knowledge_assistants.get_knowledge_assistant(name=ka.name)
knowledge_assistant_id = (
    getattr(refreshed, "knowledge_assistant_id", None) or knowledge_assistant_id
)
ka_endpoint_name = (
    getattr(refreshed, "endpoint_name", None) or f"ka-{knowledge_assistant_id}"
)
print(ka_endpoint_name, knowledge_assistant_id)
```

Persist both in `config.yml`:

```yaml
ka_endpoint_name: "ka-<captured id>"      # Track A / AppKit handle
knowledge_assistant_id: "<captured id>"   # Track B Hosted Tools handle
```

- Track A 03 (`tools-and-mcp`) reads `ka_endpoint_name` and calls the KA
  Model Serving endpoint as a function tool.
- Track B 02 (`hosted-tools`) reads `knowledge_assistant_id` to build the
  `knowledge_assistant` hosted tool entry.

---

## Update and Delete

```python
w.knowledge_assistants.update_knowledge_assistant(
    name=ka.name,
    knowledge_assistant=KnowledgeAssistant(
        description="Loyalty Q&A — updated quarterly.",
        instructions="Always cite the exact section heading.",
    ),
    update_mask="description,instructions",
)

w.knowledge_assistants.delete_knowledge_source(name=source.name)

w.knowledge_assistants.delete_knowledge_assistant(name=ka.name)
```

**Constraint:** you cannot delete the last remaining source. Delete the KA if
you want to tear everything down.

---

## REST Equivalents

```bash
DATABRICKS_HOST="https://<workspace>.cloud.databricks.com"
TOKEN="$(databricks auth token --profile <profile> | jq -r .access_token)"

curl -s -X POST "$DATABRICKS_HOST/api/2.0/knowledge-assistants" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "loyalty-policy-assistant",
    "description": "Loyalty Q&A",
    "instructions": "Always cite the document and section."
  }'

curl -s -X POST "$DATABRICKS_HOST/api/2.0/knowledge-assistants/<id>/knowledge-sources" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "loyalty-docs",
    "source_type": "files",
    "files": { "path": "/Volumes/main/skyloyalty/loyalty_docs" }
  }'

curl -s -X POST \
  "$DATABRICKS_HOST/api/2.0/knowledge-assistants/<id>:syncKnowledgeSources" \
  -H "Authorization: Bearer $TOKEN"

curl -s "$DATABRICKS_HOST/api/2.0/knowledge-assistants/<id>" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Authorization Model

| Action | Required Role |
|---|---|
| Create/Delete KA | Workspace user with serverless + KA preview enabled |
| Sync sources | **Creator of the KA** only |
| Add/Update/Delete source | **Creator of the KA** only |
| Grant access to endpoint | Workspace admin or resource manager |
| Call endpoint | Principals with `CAN_QUERY` on the serving endpoint |

For a shared agent, create the KA under a **service principal** so support
teams can rotate without re-creating.

---

## See Also

- [`knowledge-assistant-operations.md`](knowledge-assistant-operations.md) — quality improvement, guidelines, labeled data, migration.
- Main skill: [`../SKILL.md`](../SKILL.md).
