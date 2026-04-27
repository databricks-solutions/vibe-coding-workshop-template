# Knowledge Assistant — Day-2 Operations

Progressive-load this file once the KA is live and you need to improve
quality, migrate across workspaces, or hand off ownership.

---

## Quality Improvement Loop

KA quality improves through three mechanisms, in order of cost:

1. **Instructions** — the system prompt you passed at creation. Tweak first.
2. **Guidelines** — reusable answer-style rules (tone, required disclaimers,
   "always cite section").
3. **Labeled examples** — gold question/answer pairs that pin behavior on
   edge cases.

Avoid changing the source corpus as a first-line quality fix; it causes
re-ingest churn and rarely fixes answer-style problems.

---

## Editing Instructions

```python
from databricks.sdk.service.knowledgeassistants import KnowledgeAssistant

w.knowledge_assistants.update_knowledge_assistant(
    name=ka.name,
    knowledge_assistant=KnowledgeAssistant(
        instructions=(
            "Always cite the document title and section heading. "
            "Prefer quoting the source verbatim for policy text. "
            "Never speculate about unreleased features."
        ),
    ),
    update_mask="instructions",
)
```

Instruction changes take effect on the next request — no re-sync required.

---

## Guidelines and Labeled Examples

Databricks stores guidelines and labeled examples in a UC table that backs
the KA. Access them through the Agents UI or the REST import/export
endpoints.

**Export** (for versioning in git):

```bash
curl -s -X POST \
  "$DATABRICKS_HOST/api/2.0/knowledge-assistants/<id>:exportLabeledData" \
  -H "Authorization: Bearer $TOKEN" \
  -o ka-labeled-data.json
```

**Import** (after editing in a PR):

```bash
curl -s -X POST \
  "$DATABRICKS_HOST/api/2.0/knowledge-assistants/<id>:importLabeledData" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  --data @ka-labeled-data.json
```

Exact endpoint names may differ per release; check the
[Knowledge Assistants REST API](https://docs.databricks.com/api/workspace/knowledgeassistants)
for the current spelling. The Agents UI is the authoritative source when in
doubt.

---

## Ownership Handoff

Only the **creator** of the KA can sync and manage sources. To hand off:

1. Create the KA under a **service principal** (preferred) or a shared
   support account.
2. Grant the operating team `CAN_MANAGE` on the KA endpoint.
3. Store the service principal's credentials in a Databricks secret scope.
4. Gate all sync invocations through a scheduled Databricks Job running as
   that principal.

Retrofitting ownership later requires re-creating the KA, so do this step
before onboarding a second team.

---

## Scheduled Sync

Register a Databricks Job that runs `sync_knowledge_sources(name=...)` on a
schedule (daily for slowly changing corpora, hourly for runbooks that must
track git). The job:

- Calls `sync_knowledge_sources`.
- Polls `get_knowledge_assistant` until ready or a configurable timeout.
- Emits an MLflow trace to the experiment recorded in F2 so sync drift shows
  up in the same observability view as agent traces.

Tag the job with the KA id so you can correlate sync history with B3 traces.

---

## Migration Across Workspaces

KA is workspace-scoped. To move between workspaces:

1. **Recreate source** — copy files into a UC Volume in the destination, or
   recreate the VS index with `databricks-gte-large-en`.
2. **Recreate KA** — run F5a/F5b in the destination.
3. **Copy labeled data** — export from source, import into destination.
4. **Re-sync** — poll readiness.
5. **Update config** — swap `knowledge_assistant_id` in `config.yml` for the
   destination id.

Keep the KA display name identical across workspaces so logs and dashboards
stay comparable.

---

## Observability

- **Endpoint traces** — KA is a model-serving endpoint; standard Inference
  Tables apply.
- **Agent traces** — when consumed via the Track B `knowledge_assistant`
  hosted tool, the Supervisor API trace captures tool inputs/outputs including
  the KA call. When consumed via Track A as a function tool, the agent's own
  MLflow trace captures the call.
- **Sync history** — track via the scheduled-job MLflow traces above.

Route KA endpoint Inference Tables into the same UC schema as your agent's
UC OTEL tables (see F2) for unified querying.

---

## Troubleshooting

| Symptom | Likely Cause | Action |
|---|---|---|
| `404` on source creation | KA id mismatch | Pass the full `knowledge-assistants/<id>` |
| Sync succeeds but answers are stale | File skipped at ingest | Check filename (`_`/`.` prefix) and size (>50 MB) |
| Index source rejected | Embedding model not supported | Rebuild index with `databricks-gte-large-en` |
| Index source rejected | AI Guardrails/rate limits on embedding endpoint | Disable on the embedding endpoint |
| Endpoint never goes READY | Insufficient serverless budget | Increase usage policy budget |
| Cannot sync as a teammate | Non-creator | Run under creator/service principal |

---

## See Also

- [`knowledge-assistant-api-sdk.md`](knowledge-assistant-api-sdk.md) — create/attach/sync API surface.
- Main skill: [`../SKILL.md`](../SKILL.md).
