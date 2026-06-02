# Session and Authentication

How user identity flows in AppKit chat applications — all AppKit-native, no Vercel AI SDK.

> **Client note (IDE & Genie Code).** All identity/auth handling here is **server-side code** — OBO header parsing, `.asUser(req)`, and `config.authenticate()` resolve at runtime on the deployed app and behave identically on both clients. There are no client-specific commands in this reference; the local-dev fallback identity (`DEV_USER_EMAIL`) only applies when running outside the Databricks Apps platform.

## User Identity in Databricks Apps

Databricks Apps use On-Behalf-Of (OBO) authentication. When a user accesses the app
through the browser, Databricks injects the following **canonical** headers:

```
x-forwarded-email:                <user email>
x-forwarded-preferred-username:   <preferred username (often equals email)>
x-forwarded-user:                 <stable workspace user id>
x-forwarded-access-token:         <user OBO token, only with user_api_scopes>
```

> `x-forwarded-user-info` is **not** a canonical Databricks Apps header and must
> not be used. Earlier internal patterns assumed a JSON-blob header existed; it
> does not. Always read the four canonical headers above.

### Reading User Info

```typescript
interface DatabricksUserInfo {
  email?: string;              // x-forwarded-email
  preferredUsername?: string;  // x-forwarded-preferred-username
  userId?: string;             // x-forwarded-user (stable workspace user id)
}

function readCanonicalUserHeaders(
  req: import("express").Request,
): DatabricksUserInfo {
  const pick = (h: string | string[] | undefined): string | undefined =>
    typeof h === "string" && h.length > 0 ? h : undefined;
  return {
    email: pick(req.headers["x-forwarded-email"]),
    preferredUsername: pick(req.headers["x-forwarded-preferred-username"]),
    userId: pick(req.headers["x-forwarded-user"]),
  };
}
```

### User ID Strategy

Use a consistent user identifier across all tables. Prefer the email so it
matches MLflow `AssessmentSource.source_id` downstream:

| Environment | User ID Source | Example |
|-------------|---------------|---------|
| Deployed (Databricks Apps) | `x-forwarded-email` (fallback `x-forwarded-user`) | `"alice@example.com"` |
| Local dev | `DEV_USER_EMAIL` env var | `"dev@example.com"` |
| Fallback | Hardcoded string | `"local-dev-user"` |

```typescript
function getCurrentUserId(req: import("express").Request): string {
  const info = readCanonicalUserHeaders(req);
  if (info.email) return info.email;
  if (info.userId) return info.userId;
  return process.env.DEV_USER_EMAIL ?? "local-dev-user";
}
```

## Auth Middleware Layer

Rather than calling `getCurrentUserId(req)` inline in every route handler,
use Express middleware to parse the session once and enforce access control.

### authMiddleware — Parse Session

```typescript
interface AppSession {
  userId: string;
  email: string;
  name?: string;
  authenticated: boolean;
}

declare global {
  namespace Express {
    interface Request {
      session?: AppSession;
    }
  }
}

function authMiddleware(req: import("express").Request, _res: import("express").Response, next: import("express").NextFunction) {
  const info = readCanonicalUserHeaders(req);
  if (info.email || info.userId) {
    const userId = info.email ?? info.userId!;
    req.session = {
      userId,
      email: info.email ?? info.preferredUsername ?? "unknown@local",
      name: info.preferredUsername,
      authenticated: true,
    };
  } else {
    req.session = {
      userId: process.env.DEV_USER_EMAIL ?? "local-dev-user",
      email: process.env.DEV_USER_EMAIL ?? "dev@local",
      authenticated: false,
    };
  }
  next();
}
```

### requireAuth — Reject Unauthenticated Requests

```typescript
function requireAuth(req: import("express").Request, res: import("express").Response, next: import("express").NextFunction) {
  if (!req.session) {
    return res.status(401).json({ error: "Authentication required" });
  }
  next();
}
```

In local development, `authMiddleware` always creates a session (using
`DEV_USER_EMAIL`), so `requireAuth` only rejects when no middleware ran.

### requireChatAccess — Verify Chat Ownership or Visibility

```typescript
function requireChatAccess(req: import("express").Request, res: import("express").Response, next: import("express").NextFunction) {
  const chatId = req.params.chatId;
  if (!chatId) return next();

  AppKit.lakebase.query(
    `SELECT "userId", visibility FROM chat."Chat" WHERE id = $1`,
    [chatId]
  ).then((result) => {
    if (result.rows.length === 0) {
      return res.status(404).json({ error: "Chat not found" });
    }
    const chat = result.rows[0];
    const userId = req.session?.userId;
    if (chat.userId !== userId && chat.visibility !== "public") {
      return res.status(403).json({ error: "Access denied" });
    }
    next();
  }).catch(() => {
    next();
  });
}
```

### Applying Middleware

```typescript
AppKit.server.extend((app) => {
  app.use("/api/chat", authMiddleware, requireAuth);
  app.use("/api/history", authMiddleware, requireAuth);
  app.use("/api/messages", authMiddleware, requireAuth);
  app.use("/api/feedback", authMiddleware, requireAuth);
  app.use("/api/session", authMiddleware);

  // Route handlers now use req.session instead of getCurrentUserId(req)
  app.get("/api/history", async (req, res) => {
    const userId = req.session!.userId;
    // ...
  });
});
```

---

## OBO Token for Agent Calls

**AppKit handles OBO forwarding natively.** Use `.asUser(req)` on any Serving-plugin call
to forward the end user's OBO token transparently — no manual header parsing, no AI SDK
provider factory:

```typescript
// Streaming — what 07-appkit-chat-history's /api/chat route uses
for await (const chunk of AppKit.serving("agent").asUser(req).stream({ messages })) {
  // ...
}

// Invoke — for single-turn calls like title generation
const result = await AppKit.serving("agent").asUser(req).invoke({ messages });
```

Without `.asUser(req)`, calls use the app's Service Principal token. Use SP context
for background tasks (analytics, scheduled jobs) and OBO context (`.asUser(req)`)
for user-facing agent calls so row-level permissions, MLflow experiment ACLs, and
any downstream data access apply as the actual user.

For more on the Serving plugin's OBO pattern, see
[06-appkit-serving-wiring/SKILL.md](../../06-appkit-serving-wiring/SKILL.md).

### When You Need the Raw OBO Token

A few patterns (for example, calling the MLflow Assessments REST API — see
[08-appkit-feedback/references/mlflow-assessments.md](../../08-appkit-feedback/references/mlflow-assessments.md))
require you to attach OAuth headers to a custom `fetch`. Use AppKit's execution
context helper rather than reading `x-forwarded-access-token` directly:

```typescript
import { getExecutionContext } from "@databricks/appkit";

const ctx = getExecutionContext();
const config = ctx.client.config;
await config.ensureResolved();

const headers = new Headers();
await config.authenticate(headers);
// headers now has Authorization: Bearer <token>
```

This pattern is documented in detail in
[06-appkit-serving-wiring/references/custom-proxy-fallback.md](../../06-appkit-serving-wiring/references/custom-proxy-fallback.md).

## Session Endpoint

Provide a `/api/session` endpoint so the frontend knows who is logged in:

```typescript
app.get("/api/session", async (req, res) => {
  res.json({
    user: {
      id: req.session!.userId,
      email: req.session!.email,
      name: req.session?.name,
    },
    authenticated: req.session!.authenticated,
  });
});
```

## Chat Access Control

Each chat has a `userId` and a `visibility` field:

```typescript
// Verify the current user owns the chat before returning/modifying
async function verifyChatOwnership(chatId: string, userId: string): Promise<boolean> {
  const result = await AppKit.lakebase.query(
    `SELECT "userId", visibility FROM chat."Chat" WHERE id = $1`,
    [chatId]
  );
  if (result.rows.length === 0) return false;
  const chat = result.rows[0];
  return chat.userId === userId || chat.visibility === "public";
}
```

### Visibility Rules

| Visibility | Who Can View | Who Can Edit/Delete |
|-----------|-------------|---------------------|
| `private` | Owner only | Owner only |
| `public` | Anyone with the URL | Owner only |

## Local Development

For local development without Databricks Apps OBO:

1. Set `DEV_USER_EMAIL` in `.env`
2. `authMiddleware` falls back to this value when headers are absent
3. All chats created locally will be owned by `DEV_USER_EMAIL`

```env
DEV_USER_EMAIL=yourname@databricks.com
```

Note: with AppKit, local dev typically uses your personal Databricks CLI profile for
auth (see [01-appkit-scaffold](../../01-appkit-scaffold/SKILL.md) and
[05-appkit-lakebase-wiring](../../05-appkit-lakebase-wiring/SKILL.md)). OBO headers
only appear in deployed mode, so `DEV_USER_EMAIL` is what identifies you locally.
