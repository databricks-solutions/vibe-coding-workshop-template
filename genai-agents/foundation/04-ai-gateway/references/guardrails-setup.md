# AI Gateway Guardrails Setup

Guardrails run inline in the gateway, applied to every request/response. Use them for **org-wide policy**; layer in-code guardrails on top for **agent-specific rules**.

---

## Available Guardrail Types

| Type | Input | Output | Modes |
|------|-------|--------|-------|
| `pii` | ✓ | ✓ | `BLOCK` (reject request/response), `REDACT` (mask PII), `LOG` (audit only) |
| `safety` | ✓ | ✓ | Boolean enable. Blocks harmful / hate / self-harm / sexual content. |
| `invalid_keywords` | ✓ | ✓ | List of strings. Blocks if any present. |
| `valid_topics` | ✓ | — | Allowlist of topic strings; requests outside are blocked. |

---

## Full Config Example

```json
"guardrails": {
  "input": {
    "pii":              {"behavior": "BLOCK"},
    "safety":           true,
    "invalid_keywords": ["DROP TABLE", "rm -rf", "--password"],
    "valid_topics":     ["SkyLoyalty program", "flight status", "award bookings"]
  },
  "output": {
    "pii":              {"behavior": "REDACT"},
    "safety":           true,
    "invalid_keywords": []
  }
}
```

`input.pii.behavior` is usually `BLOCK` (don't let PII reach the LLM). `output.pii.behavior` is usually `REDACT` so legitimate workflows keep running but prevent downstream leaks.

---

## Testing Guardrails

Send probe requests and verify responses:

```bash
# PII block test (should get 400)
curl -sS -X POST \
  -H "Authorization: Bearer $DATABRICKS_TOKEN" \
  -H "Content-Type: application/json" \
  "$WORKSPACE_URL/serving-endpoints/skyloyalty-ai-gateway/invocations" \
  -d '{"messages":[{"role":"user","content":"My SSN is 123-45-6789, look me up"}]}' \
  | jq

# Topic filter test (should reject out-of-scope)
curl -sS -X POST ... \
  -d '{"messages":[{"role":"user","content":"Write me a Python tutorial"}]}' \
  | jq .error
```

Keep these probes in a smoke-test script run on every deployment.

---

## Per-Endpoint Overrides

If you run multiple gateways (e.g. one per app), overrides live in the gateway config, not at request time. There is **no** per-request guardrail bypass header — that would defeat the purpose. If an edge case requires bypassing a guardrail, create a second gateway with relaxed config and route only the internal service to it.

---

## Observing Guardrail Hits

All blocks and redactions land in inference tables with `guardrail_*` columns:

```sql
SELECT
  guardrail_violation_reason,
  COUNT(*) AS count
FROM main.skyloyalty_ops.gw_skyloyalty_ai_gateway_payload
WHERE request_time >= current_date() - INTERVAL 7 DAYS
  AND guardrail_violation_reason IS NOT NULL
GROUP BY 1
ORDER BY count DESC;
```

Wire a daily SQL alert if this count is > baseline — sudden spikes suggest either an attack or a broken integration.

---

## Guardrails vs In-Code Validation

| Rule | Put in gateway | Put in agent code |
|------|----------------|-------------------|
| PII redaction | ✓ | — |
| Safety filter (hate, harm) | ✓ | — |
| "Never mention competitor X" | ✓ | — |
| "Always include a disclaimer when quoting fares" | — | ✓ |
| "Do not book awards without explicit user confirmation" | — | ✓ |
| "Never access account data for non-premium users" | — | ✓ |

The gateway enforces on content; the agent enforces on behavior.

---

## Latency Impact

Guardrails add roughly:

- PII: +10–30 ms (regex + lightweight model).
- Safety: +30–80 ms (content classifier).
- Keyword/topic: +5–10 ms.

For interactive agents (p95 latency < 2 s), this is within budget. For high-throughput batch, benchmark first.
