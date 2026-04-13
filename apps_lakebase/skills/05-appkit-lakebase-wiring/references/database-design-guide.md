# Database Design Guide for AppKit + Lakebase

A concise reference for designing PostgreSQL schemas in AppKit applications. Combines relational design methodology with PostgreSQL-specific conventions.

---

## Part A: Design Methodology

### The Design Process

1. **Determine purpose** — what data does the app need? Read the PRD.
2. **Identify entities** — each major noun (user, order, listing, booking) becomes a table.
3. **Define columns** — each property of an entity becomes a column. Break compound fields into atomic parts (e.g., separate `first_name` and `last_name`, not a single `name`).
4. **Choose primary keys** — every table needs a unique identifier. Prefer `bigint generated always as identity`.
5. **Establish relationships** — identify how tables relate (1:N, M:N). Add foreign keys.
6. **Normalize** — apply normalization rules to eliminate redundancy.
7. **Refine** — create sample data, test queries, adjust.

### Normalization Rules

**First Normal Form (1NF):** Every cell contains a single value, never a list.

```sql
-- Bad: list in a column
CREATE TABLE listings (id bigint, amenities text); -- 'wifi,pool,gym'

-- Good: separate table for multi-valued attributes
CREATE TABLE listing_amenities (
  listing_id bigint references listings(id),
  amenity text not null
);
```

**Second Normal Form (2NF):** Every non-key column depends on the *entire* primary key, not just part of it. Applies to composite keys.

```sql
-- Bad: product_name depends only on product_id, not the full (order_id, product_id) key
CREATE TABLE order_items (
  order_id bigint, product_id bigint, product_name text, quantity int
);

-- Good: product_name belongs in the products table
CREATE TABLE order_items (
  order_id bigint references orders(id),
  product_id bigint references products(id),
  quantity int not null
);
```

**Third Normal Form (3NF):** Non-key columns must not depend on other non-key columns.

```sql
-- Bad: discount depends on price, not on the primary key
CREATE TABLE products (id bigint, name text, price numeric, discount numeric);

-- Good: if discount is derived from price, compute it at query time or store in a separate table keyed by price tier
```

### Relationship Patterns

**One-to-Many (1:N):** Add a foreign key on the "many" side.

```sql
-- One customer has many orders
CREATE TABLE orders (
  id bigint generated always as identity primary key,
  customer_id bigint not null references customers(id),
  total numeric(10,2) not null
);
CREATE INDEX idx_orders_customer_id ON orders (customer_id);
```

**Many-to-Many (M:N):** Use a junction table.

```sql
-- A booking can have many add-ons; an add-on can appear in many bookings
CREATE TABLE booking_addons (
  booking_id bigint references bookings(id),
  addon_id bigint references addons(id),
  primary key (booking_id, addon_id)
);
```

### Anti-Patterns to Avoid

- **Storing calculated data** — compute totals and aggregates at query time, not in columns
- **Repeating groups** — columns like `phone1`, `phone2`, `phone3` indicate a missing child table
- **Composite strings** — storing comma-separated values instead of a proper relationship table
- **One table for everything** — if a row contains facts about multiple subjects, split into separate tables

---

## Part B: PostgreSQL Conventions

### Data Types

| Use Case | Type | Why |
|----------|------|-----|
| Auto-increment ID | `bigint generated always as identity` | SQL-standard, 9 quintillion max (not `serial`, which is legacy) |
| Text fields | `text` | Same performance as `varchar(n)` with no artificial limit |
| Constrained text | `text` + `CHECK` constraint | `CHECK (status IN ('a','b','c'))` enforces allowed values |
| Money / prices | `numeric(10,2)` | Exact decimal (not `float` which has rounding errors) |
| Timestamps | `timestamptz default now()` | Always timezone-aware (not `timestamp`) |
| Calendar dates | `date` | Date without time |
| Yes/no flags | `boolean default false` | 1 byte (not `varchar(5)` storing `'true'`/`'false'`) |
| Foreign keys | `bigint references parent_table(id)` | Match the parent PK type |

### Primary Key Strategy

- **Single database (most AppKit apps):** `bigint generated always as identity` — sequential, 8 bytes, SQL-standard
- **`serial`/`SERIAL`** works but is legacy — prefer `identity` for new tables
- **Avoid random UUID (v4)** as PK on large tables — causes index fragmentation due to random insertion order

### Frontend ID Format Alignment

If the frontend uses formatted string IDs (e.g., `"lst-001"`, `"bk-2024-001"`):

- **Option A (recommended for existing apps):** Use `text` primary keys storing the formatted ID directly. Simpler — no conversion layer needed in routes or mappers.
- **Option B:** Use `bigint identity` PKs and convert in mapper functions:
  ```typescript
  function formatId(prefix: string, id: number): string {
    return `${prefix}-${String(id).padStart(3, '0')}`;
  }
  ```
  The API returns formatted IDs; the database stores integers. Requires a parse step on incoming requests too (e.g., `"lst-001"` → `1`).

**Choose Option A** if the frontend already uses formatted IDs in URL params, component keys, and cross-page navigation. Changing to numeric IDs would require updating every `useParams()` call and route definition. Choose Option B only for new apps where you control the ID format from the start.

### Indexing

- **Always index foreign key columns** — without an index, JOINs and cascading deletes cause full table scans
- **Index columns used in WHERE clauses** — any column frequently filtered or sorted
- **Use partial indexes** for queries that consistently filter on the same condition:

```sql
CREATE INDEX idx_orders_pending ON orders (created_at)
  WHERE status = 'pending';
```

### Idempotent Schema Changes

- `CREATE TABLE IF NOT EXISTS` — safe for DDL on every startup
- `CREATE INDEX IF NOT EXISTS` — safe for index creation
- **Constraints:** PostgreSQL has no `ADD CONSTRAINT IF NOT EXISTS`. Use `DO $$` blocks:

```sql
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'orders_status_check'
  ) THEN
    ALTER TABLE orders ADD CONSTRAINT orders_status_check
      CHECK (status IN ('pending', 'confirmed', 'cancelled'));
  END IF;
END $$;
```

### Naming Conventions

- `snake_case` for all PostgreSQL objects: tables, columns, indexes, constraints
- Table names: plural (`orders`, `bookings`, `customers`)
- Foreign key columns: `{referenced_table_singular}_id` (e.g., `customer_id`, `listing_id`)
- Indexes: `idx_{table}_{column}` (e.g., `idx_orders_customer_id`)
- Constraints: `{table}_{column}_{type}` (e.g., `orders_status_check`, `bookings_listing_id_fkey`)

### Seed Data Gotchas

- **Escape apostrophes** with double single quotes: `'chef''s kitchen'` (not backslash)
- **Avoid semicolons inside string values** — the SQL parser may interpret them as statement terminators. Use pipe (`|`) or comma as delimiters instead
- **FK reference counts must match parent rows** — if you insert 10 hosts, `listings.host_id` values must be 1-10, not 1-12. Count your parent rows before writing child inserts
- **Avoid ARRAY types** (`TEXT[]`, `INT[]`) — Lakebase's `AppKit.lakebase.query()` parser may not handle PostgreSQL ARRAY syntax correctly. Store multi-valued data in a child table (1NF) or as delimited TEXT with application-side splitting
