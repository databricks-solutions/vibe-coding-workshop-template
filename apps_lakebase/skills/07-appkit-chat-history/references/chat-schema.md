# Chat Schema Design

Database schema for chat persistence in Lakebase, modeled on
[e2e-chatbot-app-next's Drizzle schema](https://github.com/databricks/app-templates/blob/main/e2e-chatbot-app-next/packages/db/src/schema.ts).

> **Client note (IDE & Genie Code).** This is design reference. The schema-creation statements shown here run **server-side on app startup** under the app's Service Principal (the inline-DDL approach in the SKILL Step 1) — there is no client-side schema step on either client, and the behaviour is identical whether deployed from an IDE or Genie Code. The Drizzle migration path below is an IDE/local convenience; on Genie Code there is no local Node toolchain, so prefer the inline-DDL approach (which is the default anyway).

## ER Diagram

```
┌────────────────┐
│     User       │
├────────────────┤
│ id   TEXT PK   │──┐
│ email VARCHAR  │  │
└────────────────┘  │
                    │ 1:N
┌────────────────┐  │
│     Chat       │◄─┘
├────────────────┤
│ id     UUID PK │──┬──────────────┐
│ createdAt TS   │  │              │
│ title  TEXT    │  │ 1:N          │ 1:N
│ userId TEXT FK │  │              │
│ visibility     │  ▼              ▼
│ lastContext    │  ┌──────────┐  ┌──────────┐
└────────────────┘  │ Message  │  │   Vote   │
                    ├──────────┤  ├──────────┤
                    │ id    PK │──│messageId │
                    │ chatId FK│  │ chatId   │
                    │ role     │  │ isUpvoted│
                    │ parts    │  └──────────┘
                    │ attach.  │
                    │ traceId  │
                    │ createdAt│
                    └──────────┘
```

## Tables

### chat.User

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `TEXT` | `PRIMARY KEY NOT NULL` | Databricks user ID from OBO header |
| `email` | `VARCHAR(64)` | `NOT NULL` | User email from OBO header |

### chat.Chat

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `UUID` | `PRIMARY KEY DEFAULT gen_random_uuid()` | Conversation ID (generated client-side or server-side) |
| `createdAt` | `TIMESTAMP` | `NOT NULL DEFAULT CURRENT_TIMESTAMP` | Conversation start time |
| `title` | `TEXT` | `NOT NULL DEFAULT 'New chat'` | Auto-generated from first user message |
| `userId` | `TEXT` | `NOT NULL` | FK to User.id |
| `visibility` | `VARCHAR(10)` | `NOT NULL DEFAULT 'private'` | `'private'` or `'public'` |
| `lastContext` | `JSONB` | nullable | Last conversation context (for continuations) |

### chat.Message

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `UUID` | `PRIMARY KEY DEFAULT gen_random_uuid()` | Message ID |
| `chatId` | `UUID` | `NOT NULL FK → Chat.id CASCADE` | Which conversation this belongs to |
| `role` | `VARCHAR(20)` | `NOT NULL` | `'user'`, `'assistant'`, `'tool'`, `'system'` |
| `parts` | `JSON` | `NOT NULL DEFAULT '[]'` | Message content — array of `{type: "text", text: "..."}` objects |
| `attachments` | `JSON` | `NOT NULL DEFAULT '[]'` | File attachments |
| `createdAt` | `TIMESTAMP` | `NOT NULL DEFAULT CURRENT_TIMESTAMP` | Message timestamp |
| `traceId` | `TEXT` | nullable | MLflow trace ID (only on assistant messages) |

### chat.Vote

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `chatId` | `UUID` | `NOT NULL FK → Chat.id CASCADE` | Conversation context |
| `messageId` | `UUID` | `NOT NULL FK → Message.id CASCADE` | Which message was voted on |
| `isUpvoted` | `BOOLEAN` | `NOT NULL` | `true` = thumbs up, `false` = thumbs down |

**Composite PK:** `(chatId, messageId)` — one vote per message per chat.

## Indexes

```sql
CREATE INDEX idx_chat_user ON chat."Chat" ("userId", "createdAt" DESC);
CREATE INDEX idx_message_chat ON chat."Message" ("chatId", "createdAt" ASC);
```

## Design Decisions

### Why `parts` Array Instead of `content` String

Messages store structured `parts` arrays rather than raw `content` strings. This supports
multi-modal messages (text + images + tool results) in a single message record.

```json
[
  { "type": "text", "text": "Here is the analysis..." },
  { "type": "tool-invocation", "toolCallId": "abc", "toolName": "query_orders", "args": {}, "result": "..." }
]
```

When you're persisting text-only responses accumulated via the dual-format `extractDelta`
helper (see [06-appkit-serving-wiring/references/sse-format-patterns.md](../../06-appkit-serving-wiring/references/sse-format-patterns.md)),
a single `{ type: "text", text: accumulatedText }` part is all you need.

### Why JSONB for lastContext

Stores the last conversation context (system prompt, agent state, or token usage)
as flexible JSON. Useful for continuations where the frontend sends the context back.

### Why CASCADE Deletes

Deleting a Chat removes all its Messages and Votes automatically.
This simplifies the delete endpoint — no manual fan-out of delete statements.

### Schema Name: chat

Using a dedicated `chat` schema keeps chat tables isolated from other app data.
If you're using Lakebase for other features (e.g., an `app` schema for application data),
the chat schema doesn't conflict.

## Schema Management Approaches

### Inline DDL (Current Approach)

`CREATE TABLE IF NOT EXISTS` statements run at startup. Simple, no dependencies,
works for initial schema creation.

```typescript
await AppKit.lakebase.query(`CREATE TABLE IF NOT EXISTS chat."Chat" (...)`);
```

**Pros:** Zero dependencies, easy to understand, runs on every startup idempotently.

**Cons:** No migration history. Adding a column requires a manual `ALTER TABLE`
and you must remember to run it. No type-safe query building.

### Drizzle ORM (Template Approach)

The e2e-chatbot-app-next template uses [Drizzle ORM](https://orm.drizzle.team/)
with `drizzle-kit` for schema definition and migrations.

```bash
npm install drizzle-orm drizzle-kit
```

Schema is defined in TypeScript:

```typescript
import { pgTable, text, uuid, timestamp, boolean, json, pgSchema } from "drizzle-orm/pg-core";

export const chatSchema = pgSchema("chat");

export const chat = chatSchema.table("Chat", {
  id: uuid("id").primaryKey().defaultRandom(),
  createdAt: timestamp("createdAt").notNull().defaultNow(),
  title: text("title").notNull().default("New chat"),
  userId: text("userId").notNull(),
  visibility: text("visibility", { enum: ["public", "private"] }).notNull().default("private"),
});
```

Migrations are generated and applied:

```bash
npx drizzle-kit generate   # generates SQL migration files
npx drizzle-kit migrate    # applies pending migrations
```

**Pros:** Migration history, TypeScript-typed schema, type-safe query builder,
automatic diff detection, rollback support.

**Cons:** Adds `drizzle-orm` + `drizzle-kit` dependencies. More setup. Overkill
for a simple 4-table schema that rarely changes.

### Recommendation

| Context | Approach |
|---------|----------|
| Workshop / prototype | Inline DDL — fast, no setup |
| Production app with evolving schema | Drizzle ORM — proper migrations |
| Adding 1-2 columns post-launch | `ALTER TABLE` (inline DDL still works) |
| Team of multiple developers | Drizzle ORM — migration files are reviewable in PRs |

Start with inline DDL for the workshop. Adopt Drizzle when the schema needs
to evolve across multiple deployments or when type-safe query building becomes
valuable.

## Migration Notes (Inline DDL)

If you need to add columns later, use `ALTER TABLE`:

```sql
ALTER TABLE chat."Message" ADD COLUMN IF NOT EXISTS "usage" JSONB;
ALTER TABLE chat."Chat" ADD COLUMN IF NOT EXISTS "model" TEXT;
```

Lakebase supports standard PostgreSQL DDL — no special migration tool needed.
