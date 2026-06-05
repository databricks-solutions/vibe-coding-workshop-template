# Genie Plugin

**Upstream docs (always check for latest):** https://databricks.github.io/appkit/docs/plugins/genie
Also consult the live AppKit docs: `npx @databricks/appkit docs "genie"`
The information below may be outdated. Prefer upstream when available.

> **Client routing:** commands below are for the **IDE/CLI** path. On **Genie Code**: add packages to `package.json` instead of `npm install` (platform installs server-side on deploy); run `databricks …` via `runDatabricksCli` and **omit `--profile`**; `npx … docs` → WebFetch the docs site. See the routing table in [`../SKILL.md`](../SKILL.md) and `skills/genie-code-environment`.

Integrates Databricks AI/BI Genie spaces for natural language data queries via a conversational interface.

**Capabilities:** Named space aliases for multiple Genie spaces, SSE streaming with status updates, conversation history replay, query result attachment fetching, on-behalf-of user execution.

## Adding to an Existing AppKit Project

### 1. Register the Plugin

In `server/server.ts`:

```typescript
import { createApp, genie, server } from "@databricks/appkit";

await createApp({
  plugins: [
    server(),
    genie(),
  ],
});
```

### 2. Environment Variables

Add to `.env`:

```env
DATABRICKS_GENIE_SPACE_ID=<your-genie-space-id>
```

Add to `app.yaml`:

```yaml
env:
  - name: DATABRICKS_GENIE_SPACE_ID
    description: "Default Genie Space ID"
    value: "<your-genie-space-id>"
```

**Finding your Space ID:** Open your Genie space in Databricks, go to the **About** tab, and copy the Space ID.

### 3. Configuration Options

```typescript
genie({
  spaces: {
    sales: "01ABCDEF12345678",      // alias → Space ID
    support: "01GHIJKL87654321",
  },
  timeout: 120000,  // polling timeout in ms (default: 120000; 0 = indefinite)
});
```

If `spaces` is omitted, the plugin reads `DATABRICKS_GENIE_SPACE_ID` from the environment and registers it as `default`.

### 4. Frontend — GenieChat Component

Full-featured chat interface with streaming, history, and reconnection:

```tsx
import { GenieChat } from "@databricks/appkit-ui/react";

function GeniePage() {
  return (
    <div style={{ height: 600 }}>
      <GenieChat alias="sales" />
    </div>
  );
}
```

The `alias` prop must match a key in the `spaces` configuration.

### 5. Frontend — Custom Chat with useGenieChat Hook

```tsx
import { useGenieChat } from "@databricks/appkit-ui/react";

function CustomChat() {
  const { messages, status, sendMessage, reset } = useGenieChat({
    alias: "sales",
  });

  return (
    <>
      {messages.map((msg) => (
        <div key={msg.id}>{msg.content}</div>
      ))}
      <button onClick={() => sendMessage("Show top customers")}>Ask</button>
      <button onClick={reset}>New conversation</button>
    </>
  );
}
```

## HTTP Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/genie/:alias/messages` | Send message (SSE stream) |
| GET | `/api/genie/:alias/conversations/:conversationId` | Replay history (SSE stream) |

### SSE Event Types

| Event | Description |
|-------|-------------|
| `message_start` | Conversation and message IDs assigned |
| `status` | Processing updates (ASKING_AI, EXECUTING_QUERY) |
| `message_result` | Final message with text and query attachments |
| `query_result` | Tabular data for a query attachment |
| `error` | Error details |

## Programmatic Access (Server-Side)

```typescript
const AppKit = await createApp({
  plugins: [server(), genie({ spaces: { demo: "space-id" } })],
});

for await (const event of AppKit.genie.sendMessage("demo", "Show revenue by region")) {
  console.log(event.type, event);
}

const history = await AppKit.genie.getConversation("demo", "conversation-id");
```

## Combining with Other Plugins

```typescript
import { createApp, server, analytics, genie } from "@databricks/appkit";

await createApp({
  plugins: [server(), analytics(), genie()],
});
```
