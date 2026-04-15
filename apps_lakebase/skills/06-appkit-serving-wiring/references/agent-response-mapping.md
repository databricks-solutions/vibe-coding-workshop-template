# Agent Response Mapping Patterns

Patterns for extracting structured data from agent responses and rendering them as UI components (cards, tables, charts) instead of raw text. Use these when the agent returns more than plain conversation — e.g., tool call results, structured JSON, or tabular data embedded in its output.

---

## When to Use

- Agent endpoint returns structured output (JSON schema defined in Model Serving config)
- Agent uses tools that produce tabular or object data (SQL results, API responses, search results)
- You want to render agent results as cards, tables, or charts rather than a text stream
- You need a server-side proxy route that post-processes agent output before sending to the frontend

If the agent only returns conversational text, skip this reference — `useServingStream` with the chat patterns in `chat-ui-patterns.md` is sufficient.

---

## Pattern 1: Structured Output Schema

If the agent endpoint defines an output schema via Model Serving configuration, `useServingInvoke` returns typed data that maps directly to React components:

```tsx
import { useServingInvoke } from "@databricks/appkit-ui/react";

interface SearchResult {
  id: string;
  title: string;
  description: string;
  score: number;
}

interface AgentResponse {
  results: SearchResult[];
  summary: string;
}

function StructuredResults() {
  const { invoke, data, loading } = useServingInvoke(
    { messages: [{ role: "user", content: query }] },
    { alias: "agent" },
  );

  const typed = data as AgentResponse | undefined;

  return (
    <>
      {typed?.summary && <p>{typed.summary}</p>}
      {typed?.results.map((r) => (
        <ResultCard key={r.id} result={r} />
      ))}
    </>
  );
}
```

When the endpoint has an OpenAPI schema, AppKit's type generation provides compile-time types automatically — `data` will already be typed and the cast is unnecessary. When the schema is unavailable, `data` is `unknown` and the cast gives you the shape you expect. Do NOT pass a generic type parameter to `useServingInvoke<T>()` — the hook's signature derives types from the auto-generated endpoint schema, not from a manual generic.

---

## Pattern 2: Tool Results Extraction (Server-Side Proxy)

When an agent uses tools (e.g., SQL queries, API calls) and returns tool results alongside text, extract and transform the structured portion server-side before sending to the frontend.

This pattern generalizes the approach from `agentic-framework/agents/agent-ui-wiring-prompt.md`, where a booking agent's Genie SQL results were mapped to `Listing` objects.

### Define a response contract

```typescript
interface SearchResult {
  id: string;
  title: string;
  description: string;
  metadata: Record<string, string | number>;
}

interface AgentSearchResponse {
  query: string;
  summary: string;
  results: SearchResult[];
  total: number;
  source: "agent" | "fallback";
}
```

### Build a mapper function

Extract tool results from the agent's response and map rows to typed objects:

```typescript
function extractResults(agentResponse: any): SearchResult[] {
  const toolCalls = agentResponse.choices?.[0]?.message?.tool_calls ?? [];

  for (const call of toolCalls) {
    if (call.function?.name !== "target_tool_name") continue;

    let parsed: any;
    try {
      parsed = JSON.parse(call.function.arguments ?? "{}");
    } catch {
      continue;
    }

    const rows = parsed.rows ?? parsed.results ?? parsed.data ?? [];
    return rows.map((row: any) => ({
      id: String(row.id ?? row.item_id ?? ""),
      title: row.title ?? row.name ?? "Untitled",
      description: row.description ?? row.summary ?? "",
      metadata: Object.fromEntries(
        Object.entries(row).filter(
          ([k]) => !["id", "item_id", "title", "name", "description", "summary"].includes(k)
        )
      ),
    }));
  }

  return [];
}
```

### Wire the server-side proxy route

```typescript
AppKit.server.extend((app) => {
  app.post("/api/agent-search", async (req, res) => {
    try {
      const agentResponse = await AppKit.serving("agent")
        .asUser(req)
        .invoke({ messages: req.body.messages });

      const results = extractResults(agentResponse);
      const summary =
        agentResponse.choices?.[0]?.message?.content ?? "";

      res.json({
        query: req.body.messages.slice(-1)[0]?.content ?? "",
        summary,
        results,
        total: results.length,
        source: "agent",
      });
    } catch (err) {
      console.warn(`[Serving] /api/agent-search fallback: ${err}`);
      res.json({ query: "", summary: "", results: [], total: 0, source: "fallback" });
    }
  });
});
```

> **Note:** When using `server.extend()`, pass `autoStart: false` to the `server()` plugin and call `AppKit.server.start()` manually after all routes are registered. This is the same pattern used in `05-appkit-lakebase-wiring`.

### Consume from the frontend

```tsx
async function searchAgent(query: string): Promise<AgentSearchResponse> {
  const res = await fetch("/api/agent-search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      messages: [{ role: "user", content: query }],
    }),
  });
  return res.json();
}
```

---

## Pattern 3: Text Parsing (Last Resort)

When the agent returns unstructured text with embedded data, extract it via regex or a follow-up LLM call. This is fragile and should only be used when Patterns 1 and 2 are not viable.

```typescript
function extractJsonFromText(text: string): any[] {
  const jsonBlockRegex = /```json\s*([\s\S]*?)```/g;
  const results: any[] = [];

  let match;
  while ((match = jsonBlockRegex.exec(text)) !== null) {
    try {
      const parsed = JSON.parse(match[1]);
      results.push(...(Array.isArray(parsed) ? parsed : [parsed]));
    } catch {
      continue;
    }
  }

  return results;
}
```

Prefer configuring the agent to use structured output or tool calls over parsing free text.

---

## Choosing a Pattern

| Signal | Use Pattern |
|--------|-------------|
| Endpoint has an OpenAPI output schema | Pattern 1 (Structured Output) |
| Agent uses tools that return JSON/tabular data | Pattern 2 (Tool Results Extraction) |
| Agent returns only free text with embedded data | Pattern 3 (Text Parsing) |
| Agent returns only conversational text | Skip this reference entirely |
