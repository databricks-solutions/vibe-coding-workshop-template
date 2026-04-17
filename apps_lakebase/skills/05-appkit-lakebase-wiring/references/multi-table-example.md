# Multi-Table Example: Products with Reviews and Tags

A worked example showing DDL ordering, FK-aware seeding, application-side joins in routes, mapper assembly, and mock fallback — for a schema with 3 related tables.

---

## Schema

```
products (parent)
  ├── product_reviews (1:N — one product has many reviews)
  └── product_tags (1:N — one product has many tags)
```

---

## DDL (parent tables first)

Create parent tables before child tables so FK references resolve:

```typescript
const DB_SCHEMA = process.env.DB_SCHEMA || "app";

await AppKit.lakebase.query(`CREATE SCHEMA IF NOT EXISTS ${DB_SCHEMA}`);

// Parent table
await AppKit.lakebase.query(`
  CREATE TABLE IF NOT EXISTS ${DB_SCHEMA}.products (
    id bigint generated always as identity primary key,
    name text not null,
    price numeric(10,2) not null,
    category text not null,
    created_at timestamptz default now()
  )
`);

// Child table 1
await AppKit.lakebase.query(`
  CREATE TABLE IF NOT EXISTS ${DB_SCHEMA}.product_reviews (
    id bigint generated always as identity primary key,
    product_id bigint not null references ${DB_SCHEMA}.products(id),
    reviewer_name text not null,
    rating int not null check (rating between 1 and 5),
    review_text text,
    created_at timestamptz default now()
  )
`);

// Child table 2
await AppKit.lakebase.query(`
  CREATE TABLE IF NOT EXISTS ${DB_SCHEMA}.product_tags (
    id bigint generated always as identity primary key,
    product_id bigint not null references ${DB_SCHEMA}.products(id),
    tag text not null
  )
`);

// Always index FK columns
await AppKit.lakebase.query(`
  CREATE INDEX IF NOT EXISTS idx_product_reviews_product_id
  ON ${DB_SCHEMA}.product_reviews (product_id)
`);
await AppKit.lakebase.query(`
  CREATE INDEX IF NOT EXISTS idx_product_tags_product_id
  ON ${DB_SCHEMA}.product_tags (product_id)
`);
```

---

## Seed Data (count-check on parent only)

Check the parent table count once. Insert parent rows first, then child rows — all inside the same `if` block so they seed atomically:

```typescript
const seedCheck = await AppKit.lakebase.query(
  `SELECT count(*) AS cnt FROM ${DB_SCHEMA}.products`
);

if (parseInt(seedCheck.rows[0].cnt) === 0) {
  // Parent rows first
  await AppKit.lakebase.query(`
    INSERT INTO ${DB_SCHEMA}.products (name, price, category) VALUES
      ('Wireless Headphones', 79.99, 'Electronics'),
      ('Ergonomic Chair', 349.00, 'Furniture'),
      ('Running Shoes', 129.95, 'Footwear')
  `);

  // Child rows reference parent IDs (1, 2, 3 from identity sequence)
  await AppKit.lakebase.query(`
    INSERT INTO ${DB_SCHEMA}.product_reviews (product_id, reviewer_name, rating, review_text) VALUES
      (1, 'Alice', 5, 'Great sound quality'),
      (1, 'Bob', 4, 'Comfortable for long sessions'),
      (2, 'Carol', 5, 'Best chair I''ve owned'),
      (3, 'Dave', 3, 'Runs a bit narrow')
  `);

  await AppKit.lakebase.query(`
    INSERT INTO ${DB_SCHEMA}.product_tags (product_id, tag) VALUES
      (1, 'bluetooth'), (1, 'noise-cancelling'), (1, 'wireless'),
      (2, 'ergonomic'), (2, 'adjustable'),
      (3, 'running'), (3, 'athletic')
  `);

  console.log("[Lakebase] Seed data inserted (3 products + reviews + tags)");
}
```

Key details:
- Count-check on `products` only — if it's empty, all child tables are too
- Apostrophes escaped with double single quotes: `'Best chair I''ve owned'`
- Child inserts reference parent IDs by position in the identity sequence (1, 2, 3)

---

## Mock Data (server/mock-data.ts)

Define mock fallback data in camelCase, matching the shape mappers would produce from DB rows. Import this in routes for catch-block fallbacks:

```typescript
export interface Product {
  id: number;
  name: string;
  price: number;
  category: string;
  reviews: ProductReview[];
  tags: string[];
}

export interface ProductReview {
  id: number;
  reviewerName: string;
  rating: number;
  reviewText: string;
}

export const MOCK_PRODUCTS: Product[] = [
  {
    id: 1,
    name: "Wireless Headphones",
    price: 79.99,
    category: "Electronics",
    reviews: [
      { id: 1, reviewerName: "Alice", rating: 5, reviewText: "Great sound quality" },
      { id: 2, reviewerName: "Bob", rating: 4, reviewText: "Comfortable for long sessions" },
    ],
    tags: ["bluetooth", "noise-cancelling", "wireless"],
  },
  {
    id: 2,
    name: "Ergonomic Chair",
    price: 349.0,
    category: "Furniture",
    reviews: [
      { id: 3, reviewerName: "Carol", rating: 5, reviewText: "Best chair I've owned" },
    ],
    tags: ["ergonomic", "adjustable"],
  },
  {
    id: 3,
    name: "Running Shoes",
    price: 129.95,
    category: "Footwear",
    reviews: [
      { id: 4, reviewerName: "Dave", rating: 3, reviewText: "Runs a bit narrow" },
    ],
    tags: ["running", "athletic"],
  },
];
```

---

## Mapper Functions

Mappers translate DB rows (snake_case, string decimals) to the camelCase shapes the frontend expects:

```typescript
function mapProduct(row: any): Omit<Product, "reviews" | "tags"> {
  return {
    id: row.id,
    name: row.name,
    price: Number(row.price),
    category: row.category,
  };
}

function mapReview(row: any): ProductReview {
  return {
    id: row.id,
    reviewerName: row.reviewer_name,
    rating: row.rating,
    reviewText: row.review_text ?? "",
  };
}
```

---

## Route: Application-Side Join (List Endpoint)

Fetch parent rows, then batch-load children for all returned IDs. Assemble nested objects in code:

```typescript
import { MOCK_PRODUCTS } from "./mock-data.js";

app.get("/api/products", async (req, res) => {
  try {
    // 1. Fetch parent rows
    const productResult = await AppKit.lakebase.query(
      `SELECT * FROM ${DB_SCHEMA}.products ORDER BY id`
    );
    const products = productResult.rows.map(mapProduct);
    const ids = products.map((p) => p.id);

    // 2. Batch-fetch children (one query per child table, NOT one per product)
    const reviewResult = await AppKit.lakebase.query(
      `SELECT * FROM ${DB_SCHEMA}.product_reviews WHERE product_id = ANY($1) ORDER BY created_at`,
      [ids]
    );
    const tagResult = await AppKit.lakebase.query(
      `SELECT * FROM ${DB_SCHEMA}.product_tags WHERE product_id = ANY($1)`,
      [ids]
    );

    // 3. Group children by parent ID
    const reviewsByProduct = new Map<number, ProductReview[]>();
    for (const row of reviewResult.rows) {
      const list = reviewsByProduct.get(row.product_id) ?? [];
      list.push(mapReview(row));
      reviewsByProduct.set(row.product_id, list);
    }

    const tagsByProduct = new Map<number, string[]>();
    for (const row of tagResult.rows) {
      const list = tagsByProduct.get(row.product_id) ?? [];
      list.push(row.tag);
      tagsByProduct.set(row.product_id, list);
    }

    // 4. Assemble nested response
    const data: Product[] = products.map((p) => ({
      ...p,
      reviews: reviewsByProduct.get(p.id) ?? [],
      tags: tagsByProduct.get(p.id) ?? [],
    }));

    res.json({ data, source: "live" });
  } catch (err) {
    console.warn(`[Lakebase] /api/products fallback: ${err}`);
    res.json({ data: MOCK_PRODUCTS, source: "mock" });
  }
});
```

This approach uses 3 queries total regardless of how many products exist (1 parent + 2 child queries), avoiding the N+1 problem. For <50 rows this is simpler than SQL JOINs with manual de-duplication.

---

## Route: Detail Endpoint

For a single-item endpoint, separate queries are fine:

```typescript
app.get("/api/products/:id", async (req, res) => {
  try {
    const productResult = await AppKit.lakebase.query(
      `SELECT * FROM ${DB_SCHEMA}.products WHERE id = $1`, [req.params.id]
    );
    if (productResult.rows.length === 0) {
      return res.status(404).json({ data: [], source: "live" });
    }

    const product = mapProduct(productResult.rows[0]);

    const reviewResult = await AppKit.lakebase.query(
      `SELECT * FROM ${DB_SCHEMA}.product_reviews WHERE product_id = $1 ORDER BY created_at`,
      [req.params.id]
    );
    const tagResult = await AppKit.lakebase.query(
      `SELECT * FROM ${DB_SCHEMA}.product_tags WHERE product_id = $1`,
      [req.params.id]
    );

    const data: Product = {
      ...product,
      reviews: reviewResult.rows.map(mapReview),
      tags: tagResult.rows.map((r: any) => r.tag),
    };

    res.json({ data: [data], source: "live" });
  } catch (err) {
    const mock = MOCK_PRODUCTS.find((p) => p.id === Number(req.params.id));
    res.json({ data: mock ? [mock] : [], source: "mock" });
  }
});
```

---

## Cross-Entity Enrichment

**When to use:** Any page that previously did `OTHER_ARRAY.find(x => x.id === item.foreignKeyId)` to display fields from a related entity (e.g., showing a property name on a booking detail page, or a customer name on an order lookup page).

**Pattern:** Use a LEFT JOIN in the lookup query to include related entity fields in a single round-trip:

```typescript
app.get("/api/orders/:id", async (req, res) => {
  try {
    const result = await AppKit.lakebase.query(
      `SELECT o.*, p.name AS product_name, p.image_url AS product_image
       FROM ${DB_SCHEMA}.orders o
       LEFT JOIN ${DB_SCHEMA}.products p ON p.id = o.product_id
       WHERE o.id = $1`,
      [req.params.id]
    );
    if (result.rows.length === 0) {
      return res.status(404).json({ data: [], source: "live" });
    }
    res.json({ data: [mapOrderWithProduct(result.rows[0])], source: "live" });
  } catch (err) {
    const mock = MOCK_ORDERS.find((o) => o.id === Number(req.params.id));
    res.json({ data: mock ? [mock] : [], source: "mock" });
  }
});
```

**Anti-pattern:** Returning only the foreign key (`product_id`) and expecting the frontend to make a second API call. When the original static code used `PRODUCTS.find()` inline, the replacement must provide that data server-side — otherwise UI elements (images, names, descriptions) silently disappear.

**Rule of thumb:** If the old code used `PARENT_ARRAY.find(x => x.id === item.fkId)` to display any field, the new SQL query must LEFT JOIN that parent table and include those fields.

---

## JOIN'd Column Handling in Mappers

When a query JOINs two tables, the result row contains columns from both. Map them cleanly with a wrapper mapper rather than re-finding the related entity:

**Good — wrapper mapper:**

```typescript
function mapOrderWithProduct(row: any): OrderWithProduct {
  return {
    ...mapOrder(row),
    productName: row.product_name,
    productImage: row.product_image,
  };
}
```

**Bad — O(n²) re-find inside `.map()`:**

```typescript
const orders = orderRows.map((o) => ({
  ...mapOrder(o),
  product: productRows.find((p) => p.id === o.product_id),
}));
```

The re-find pattern is O(n²) and breaks when the products list is incomplete or paginated. The wrapper mapper approach uses data already present in the JOIN'd row, which is O(1) per row.
