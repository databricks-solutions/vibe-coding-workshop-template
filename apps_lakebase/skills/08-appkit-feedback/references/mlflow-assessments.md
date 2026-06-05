# MLflow Assessments API

Reference for logging user feedback as MLflow assessments using AppKit-native
authentication.

> **Client note (IDE & Genie Code).** The assessment POST/PATCH calls are **server-side code** authenticated from the app's execution context (`config.authenticate()`), so they run identically on both clients — there is no `--profile` or client-specific routing here. Any `curl` example is an illustration of the REST shape; exercise the live route on the **deployed** app, not localhost, when working in Genie Code.

## Overview

MLflow Assessments link user judgments to specific agent traces. When a user clicks
thumbs up/down, the feedback is logged against the trace that produced the response,
creating a ground-truth dataset for model evaluation.

## API Endpoints

### Create — POST

```
POST {DATABRICKS_HOST}/api/3.0/mlflow/traces/{trace_id}/assessments
```

### Update — PATCH

```
PATCH {DATABRICKS_HOST}/api/3.0/mlflow/traces/{trace_id}/assessments/{assessment_id}
```

### List — GET

```
GET {DATABRICKS_HOST}/api/3.0/mlflow/traces/{trace_id}/assessments
```

### Request Headers

```
Authorization: Bearer <token>
Content-Type: application/json
```

The `Authorization` header is populated by AppKit's execution-context helper — see
[Authentication Strategy](#authentication-strategy) below. **Never set it from
`process.env.DATABRICKS_TOKEN` or `x-forwarded-access-token`.**

### Request Body (POST — Create)

```json
{
  "assessment_name": "user_feedback",
  "source": {
    "source_type": "HUMAN",
    "source_id": "<user-id-or-email>"
  },
  "feedback": {
    "value": true
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `assessment_name` | `string` | Assessment name — use `"user_feedback"` for consistency |
| `source.source_type` | `string` | `"HUMAN"` for user feedback, `"LLM_JUDGE"` for automated eval |
| `source.source_id` | `string` | Identifier of the assessor (user ID or email from `req.session`) |
| `feedback.value` | `boolean` | `true` for thumbs up, `false` for thumbs down |

### Request Body (PATCH — Update Existing)

```json
{
  "feedback": {
    "value": false
  }
}
```

Use PATCH when a user changes their vote. Store the `assessment_id` from the POST
response to deduplicate — avoid creating multiple assessments for the same message.

### Response

```json
{
  "assessment": {
    "assessment_id": "abc123",
    "trace_id": "trace-xyz",
    "assessment_name": "user_feedback",
    "source": { "source_type": "HUMAN", "source_id": "user@example.com" },
    "feedback": { "value": true },
    "timestamp": 1700000000000
  }
}
```

## Authentication Strategy

**AppKit-native.** The execution context resolves the correct authentication
(PAT, OAuth M2M, or OAuth U2M) based on the deployed environment, and attaches
`Authorization: Bearer <token>` to any `Headers` object you give it. This is
the same pattern documented in
[06-appkit-serving-wiring/references/custom-proxy-fallback.md](../../06-appkit-serving-wiring/references/custom-proxy-fallback.md)
for custom serving proxies.

```typescript
import { getExecutionContext } from "@databricks/appkit";

async function mlflowRequest(
  path: string,
  init: { method: "POST" | "PATCH" | "GET"; body?: unknown },
): Promise<Response> {
  const ctx = getExecutionContext();
  const config = ctx.client.config;
  await config.ensureResolved();

  const host = (config.host ?? "").replace(/\/$/, "");
  if (!host) throw new Error("Databricks host not resolved from execution context");

  const headers = new Headers();
  await config.authenticate(headers);     // populates Authorization: Bearer <token>
  headers.set("Content-Type", "application/json");
  headers.set("Accept", "application/json");

  return fetch(`${host}${path}`, {
    method: init.method,
    headers,
    body: init.body ? JSON.stringify(init.body) : undefined,
  });
}
```

Why this is better than header forwarding:

- **Works in all environments.** Locally it uses your CLI profile. Deployed it uses
  the Service Principal OAuth flow. You don't have to branch on `process.env.DATABRICKS_HOST`.
- **No secret in env.** There's no `DATABRICKS_TOKEN` to rotate or leak into logs.
- **Right identity.** The Service Principal that owns the app is the one writing
  assessments, which lets you grant MLflow experiment permissions to exactly one
  identity rather than to every end user.

### Service Principal vs. User OBO for MLflow

The Service Principal pattern (what `getExecutionContext()` returns by default in
`server.extend()` handlers) is almost always correct for MLflow assessments:

| Use case | Identity | Reason |
|----------|----------|--------|
| Logging user_feedback from thumbs up/down | **Service Principal** | Simplest permissions model; record who clicked via `source.source_id` |
| User-attributed MLflow audit log required | User OBO | Each user must have `CAN_EDIT` on the experiment |
| Automated LLM judge scoring | **Service Principal** | No user in the loop |

For user OBO calls, the MLflow write goes out as the actual user rather than the SP.
See [06-appkit-serving-wiring/SKILL.md](../../06-appkit-serving-wiring/SKILL.md) for
how `.asUser(req)` forwards OBO — note that the Serving plugin's helper is not
directly usable for MLflow REST calls, so you'd need to parse the OBO token from the
context and issue the fetch yourself. Default to SP unless you have a compliance
requirement.

## Workspace URL Discovery

`config.host` (from `getExecutionContext().client.config`) always resolves to the
correct workspace URL:

- **Deployed:** the host of the Databricks Apps workspace
- **Local dev:** the host from your CLI profile (`DATABRICKS_CONFIG_PROFILE` env var
  or `~/.databrickscfg` default profile)

No need to read `process.env.DATABRICKS_HOST` or `DATABRICKS_WORKSPACE_URL` directly.

## Error Handling

Common error responses from the MLflow API:

| Status | Meaning | Action |
|--------|---------|--------|
| `200` | Assessment created/updated | Success |
| `400` | Invalid request body | Check `assessment_name` and `feedback.value` types |
| `401` | Token expired or invalid | Verify `config.authenticate` is attaching a token (it will throw if not) |
| `403` | SP lacks `CAN_EDIT` on the MLflow experiment | Grant permission in the experiment permissions UI |
| `404` | Trace ID not found | Trace may not have been logged yet; retry or skip |
| `500` | MLflow internal error | Log warning, still save vote to Lakebase |

Always save the vote to Lakebase regardless of MLflow API status.

**Surface errors to the client.** The feedback endpoint should return `mlflowError`
in the response body when the MLflow call fails, so the frontend can display a
warning. The vote is still saved to Lakebase — only the MLflow linkage failed.

```typescript
res.json({
  success: true,
  mlflowStatus,
  ...(mlflowError && { mlflowError }),
  isUpvoted,
});
```

## Multiple Assessments Per Trace

You can log multiple assessments against the same trace:

- `user_feedback` — thumbs up/down from the end user
- `correctness` — automated evaluation from an LLM judge
- `relevance` — domain-specific scoring

Each assessment has its own `source` and `name`, so they don't conflict.

## Viewing Assessments

### In the MLflow UI

1. Navigate to the experiment in your Databricks workspace
2. Click on the trace (by trace ID)
3. Assessments appear in the "Assessments" tab of the trace detail view

### Via API

```
GET {DATABRICKS_HOST}/api/3.0/mlflow/traces/{trace_id}/assessments
```

Returns all assessments for a given trace. Use the same `mlflowRequest` helper shown
above with `method: "GET"`.

## Best Practices

1. **Always save to Lakebase first** — MLflow is a secondary log, not the primary store
2. **Don't block on MLflow** — if latency is a concern, move the fetch to a background
   job; but a single MLflow POST is usually fast enough to await inline
3. **Use consistent naming** — `user_feedback` as the assessment name across all chat apps
4. **Log the assessor** — `source.source_id` should be the user's email or ID (from `req.session.userId`) for auditability
5. **Handle missing traceId** — some endpoints don't include trace info; skip MLflow silently
   with `mlflowStatus: "no_trace_id"`
6. **Never set `Authorization` manually** — always go through `config.authenticate(headers)`
