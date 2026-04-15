# Chat UI Patterns for Serving Plugin

Reusable React patterns for building agent chat interfaces with AppKit's Serving plugin. The Serving plugin provides `useServingStream` and `useServingInvoke` hooks but no pre-built chat component (unlike Genie's `GenieChat`). These patterns fill that gap.

---

## Message State Management

`useServingStream` is stateless — it doesn't track conversation history across calls. The app must manage messages in `useState` and pass the full array on each request:

```tsx
import { useState, useRef, useEffect } from "react";
import { useServingStream } from "@databricks/appkit-ui/react";

interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp: number;
}

function AgentChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  const { stream, chunks, streaming, error, reset } = useServingStream(
    {
      messages: [
        ...messages.map((m) => ({ role: m.role, content: m.content })),
        { role: "user" as const, content: input },
      ],
    },
    {
      alias: "agent",
      onComplete: (finalChunks) => {
        const assistantText = finalChunks
          .map((c: any) => c.choices?.[0]?.delta?.content ?? "")
          .join("");
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: assistantText, timestamp: Date.now() },
        ]);
        reset();
      },
    },
  );

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || streaming) return;
    setMessages((prev) => [
      ...prev,
      { role: "user", content: input.trim(), timestamp: Date.now() },
    ]);
    stream();
    setInput("");
  }

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, chunks]);

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, i) => (
          <MessageBubble key={i} message={msg} />
        ))}
        {streaming && <StreamingIndicator chunks={chunks} />}
        <div ref={bottomRef} />
      </div>
      <form onSubmit={handleSubmit} className="border-t p-4 flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask your agent..."
          disabled={streaming}
          className="flex-1 border rounded-lg px-3 py-2 text-sm disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={streaming || !input.trim()}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm disabled:opacity-50"
        >
          {streaming ? "Thinking..." : "Send"}
        </button>
      </form>
      {error && (
        <div className="px-4 pb-2 text-red-600 text-sm">Error: {error}</div>
      )}
    </div>
  );
}
```

### Key implementation details

- **Full history on every call:** The `messages` array passed to `useServingStream` must include the entire conversation history so the agent has context. The hook doesn't persist state between calls.
- **Append on complete:** Add the assistant message to state inside `onComplete`, not during streaming. This prevents partial messages from polluting the history.
- **Reset after complete:** Call `reset()` after capturing the response to clear the hook's internal chunks for the next turn.

> **Request body timing:** The first argument to `useServingStream` is the request body sent when `stream()` is called. Verify that the hook re-reads this argument at call time (not at mount time). If the messages array appears stale (always sends the initial empty array), the hook may be capturing the value at mount. In that case, use a `useRef` to hold the current messages and build the request from the ref:
>
> ```tsx
> const messagesRef = useRef(messages);
> messagesRef.current = messages;
>
> const { stream, ... } = useServingStream(
>   { messages: [...messagesRef.current, { role: "user", content: input }] },
>   { alias: "agent", ... },
> );
> ```
>
> Test multi-turn early: send two messages in sequence and confirm the second request includes the first exchange in its payload.

---

## Streaming Indicator

Show progressive output while the agent is responding:

```tsx
function StreamingIndicator({ chunks }: { chunks: any[] }) {
  const partialText = chunks
    .map((c: any) => c.choices?.[0]?.delta?.content ?? "")
    .join("");

  if (!partialText) {
    return (
      <div className="flex items-center gap-2 text-gray-500 text-sm">
        <span className="animate-pulse">Agent is thinking...</span>
      </div>
    );
  }

  return (
    <div className="bg-gray-50 rounded-lg p-3 text-sm whitespace-pre-wrap">
      {partialText}
      <span className="animate-pulse">|</span>
    </div>
  );
}
```

### Chunk format considerations

The structure of streaming chunks depends on the agent endpoint's response format. Common patterns:

- **OpenAI-compatible:** `chunk.choices[0].delta.content` — standard for Databricks agent endpoints
- **Raw text:** `chunk` may be a string directly
- **Unknown schema:** When the endpoint has no OpenAPI streaming spec, chunks are typed as `unknown` — cast or stringify them

Always check the actual chunk shape from your endpoint before building the UI. Log the first chunk to stderr during development.

---

## Message Bubble Component

```tsx
function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] rounded-lg px-4 py-2 text-sm ${
          isUser
            ? "bg-blue-600 text-white"
            : "bg-gray-100 text-gray-900"
        }`}
      >
        <div className="whitespace-pre-wrap">{message.content}</div>
      </div>
    </div>
  );
}
```

---

## Error Handling and Retry

```tsx
function ErrorBanner({
  error,
  onRetry,
}: {
  error: string;
  onRetry: () => void;
}) {
  return (
    <div className="flex items-center gap-2 bg-red-50 text-red-700 rounded-lg p-3 text-sm">
      <span className="flex-1">{error}</span>
      <button
        onClick={onRetry}
        className="px-3 py-1 bg-red-100 rounded text-xs hover:bg-red-200"
      >
        Retry
      </button>
    </div>
  );
}
```

Common error scenarios:
- **Timeout (120s default):** Agent didn't respond in time. Increase `timeout` in `serving()` config or simplify the prompt.
- **403 Forbidden:** User lacks `CAN_QUERY` permission on the endpoint. Verify the app resource binding.
- **Endpoint not ready:** The serving endpoint is starting up or scaling. Retry after a short delay.

---

## Multi-Turn Conversation Considerations

- **Token limits:** Long conversations accumulate tokens. If the agent starts returning errors or truncated responses, implement a sliding window that keeps the last N messages.
- **System messages:** Prepend a system message at the start of the `messages` array if the agent expects one. Keep it outside of `useState` if it's static.
- **Clear conversation:** Provide a "New chat" button that calls `setMessages([])` and `reset()`.

---

## autoStart Usage

Both `useServingStream` and `useServingInvoke` accept `autoStart: true` to fire automatically on mount:

```tsx
const { data } = useServingInvoke(
  { messages: [{ role: "user", content: "What can you help with?" }] },
  { alias: "agent", autoStart: true },
);
```

- **Use `autoStart: true`** for single-shot demo pages, welcome messages, or pre-populated queries
- **Omit `autoStart`** (default: `false`) for interactive chat where the user initiates each message
