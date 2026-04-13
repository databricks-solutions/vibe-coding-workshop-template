# Frontend Patterns for Lakebase Wiring

Reusable React hooks, components, and data-handling patterns for AppKit + Lakebase apps.

---

## `useLakebaseData` Hook

Create a reusable hook to avoid duplicating `useState`/`useEffect`/`fetch` boilerplate. The hook accepts `string | null` — pass `null` to skip the fetch (useful when route params haven't resolved yet):

```tsx
import { useState, useEffect } from "react";

function useLakebaseData<T>(endpoint: string | null) {
  const [data, setData] = useState<T[]>([]);
  const [source, setSource] = useState<"live" | "mock" | "loading">("loading");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!endpoint) return;
    setSource("loading");
    fetch(endpoint)
      .then((res) => res.json())
      .then((json) => {
        setData(json.data ?? []);
        setSource(json.source ?? "mock");
      })
      .catch((err) => {
        setError(String(err));
        setSource("mock");
      });
  }, [endpoint]);

  return { data, source, error };
}
```

**List page usage:**

```typescript
const { data: orders, source, error } = useLakebaseData<Order>("/api/orders");
```

**Detail page usage** (conditional fetch based on route param):

```typescript
const { id } = useParams();
const { data, source } = useLakebaseData<Listing>(id ? `/api/listings/${id}` : null);
const listing = data[0]; // detail endpoints return single-item arrays
```

---

## `ConnectionStatus` Component

Show the data source on every page:

```tsx
function ConnectionStatus({
  source,
  context,
}: {
  source: "live" | "mock" | "loading";
  context?: string;
}) {
  if (source === "loading")
    return <span>{context ? `Loading ${context}...` : "Loading..."}</span>;
  if (source === "live")
    return (
      <span className="text-green-600">
        Live Data{context ? ` — ${context}` : ""}
      </span>
    );
  return (
    <span className="text-yellow-600">
      Mock Data{context ? ` — ${context}` : ""}
    </span>
  );
}
```

Place this at the **top of every page** that fetches data. Pass a `context` string describing the data (e.g., `context="orders"`).

---

## Defensive Data Handling

Prevent runtime errors from PostgreSQL type coercion:

- **Initialize arrays with `[]`**, not `undefined`
- **Optional chaining and fallbacks**: `(data ?? []).map(...)`, `data?.length`
- **DECIMAL/NUMERIC → string coercion**: `node-pg` returns `DECIMAL` columns as strings (e.g., `"189.00"`). Always coerce with `Number(row.amount)` before arithmetic — otherwise `a + b` produces string concatenation (`"73" + "51" = "7351"`)
- **DATE → Date object coercion**: `node-pg` returns `DATE` columns as JavaScript `Date` objects. Use `.toISOString().slice(0, 10)` for `YYYY-MM-DD` format
- **snake_case → camelCase mapping**: API routes are the translation layer between PostgreSQL `snake_case` and frontend `camelCase`. Write mapper functions that handle column renaming, DECIMAL→Number, Date→ISO string, and TEXT→`string[]` splitting

Example mapper:

```typescript
function mapOrder(row: any): Order {
  return {
    id: row.id,
    customerName: row.customer_name,
    amount: Number(row.amount),
    status: row.status,
    createdAt: row.created_at instanceof Date
      ? row.created_at.toISOString()
      : String(row.created_at),
  };
}
```

Use mappers in routes: `res.json({ data: result.rows.map(mapOrder), source: "live" });`

---

## TypeScript Interfaces for Chart Compatibility

AppKit chart components expect `Record<string, unknown>[]`. Add an index signature to your interfaces:

```typescript
interface Order {
  [key: string]: unknown;
  id: number;
  customerName: string;
  amount: number;
  status: string;
  createdAt: string;
}
```

Without the `[key: string]: unknown` index signature, TypeScript will reject your interface when passed to AppKit chart `data` props.

---

## Body Parser Alternative (Inline, No Extra Dependency)

If you cannot add `express` as an explicit dependency, use this inline body parser:

```typescript
AppKit.server.extend((app) => {
  app.use((req, _res, next) => {
    if (req.headers["content-type"]?.includes("application/json") && !req.body) {
      let raw = "";
      req.on("data", (chunk) => { raw += chunk; });
      req.on("end", () => {
        try { req.body = JSON.parse(raw); } catch { req.body = {}; }
        next();
      });
    } else { next(); }
  });
  // POST routes ...
});
```

The recommended approach (Option A in the main SKILL.md) is to `npm install express` and use `express.json()` instead.
