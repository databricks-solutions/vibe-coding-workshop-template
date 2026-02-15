Wire the multi-agent system to the existing StayFinder frontend UI.

## Objective

The supervisor agent (built in Part 1) returns plain text responses. The frontend
expects **structured listing objects**. This prompt bridges the gap by modifying
the agent loop return type, creating a data mapper, and updating the API endpoints
so the UI can render agent search results as listing cards.

## Prerequisites

Before starting this wiring:
- [ ] Part 1 complete: supervisor agent is built, tested, and deployed
- [ ] Agent returns coherent text responses when tested via CLI or curl
- [ ] Frontend is built and served (React + Vite, `client/build/` exists)

## The Problem

Currently, both search endpoints return `listings: []` when the agent succeeds:

**`POST /search/natural-language`** (agent path):
```json
{
  "query": "...",
  "extracted_filters": {},
  "filter_chips": [],
  "agent_response": "Here are apartments in Austin...",
  "listings": [],
  "total": 0,
  "source": "agent"
}
```

**`POST /search/agent`** (agent path):
```json
{
  "query": "...",
  "agent_summary": "I found 4 listings near downtown Austin...",
  "resolved_params": {},
  "listings": [],
  "total": 0,
  "source": "agent"
}
```

The frontend `SearchResults.tsx` reads `data.listings` and `data.total` to render
listing cards. With `listings: []` and `total: 0`, it shows **"No stays found"**
even though the agent gave a good text answer.

## Frontend Contract

The frontend expects these exact response shapes. Reference files:
- `src/services/api.ts` — TypeScript interfaces
- `src/components/SearchResults.tsx` — Consumer component

### Listing Object Shape

```typescript
interface Listing {
  id: string;
  title: string;
  description: string;
  property_type: string;
  location: {
    city: string;
    state: string;
    lat: number;
    lng: number;
    neighborhood: string;
  };
  bedrooms: number;
  bathrooms: number;
  max_guests: number;
  amenities: string[];
  house_rules: string;
  photos: string[];
  nightly_rate: number;
  cleaning_fee: number;
  service_fee_pct: number;
  tax_pct: number;
  rating: number;
  review_count: number;
  host_name: string;
  is_available: boolean;
}
```

### Natural Language Search Response

```typescript
{
  query: string;
  extracted_filters: Record<string, string | number>;
  filter_chips: FilterChip[];
  listings: Listing[];   // <-- MUST be populated from agent tool results
  total: number;         // <-- MUST match listings.length
  source: "agent" | "fallback";
}
```

### Agent Search Response

```typescript
{
  query: string;
  agent_summary: string;
  resolved_params: Record<string, string>;
  listings: Listing[];   // <-- MUST be populated from agent tool results
  total: number;         // <-- MUST match listings.length
  source: "agent" | "fallback";
}
```

## Build Steps

Each step produces one change and has one validation gate.

### Step 2.1: Modify Agent Loop Return Type

**File:** `server/agents/agent_loop.py`

**Change:** Update `run_agent_loop()` to return a dict instead of a plain string:

```python
def run_agent_loop(user_message: str) -> dict:
    """Run the agentic tool-calling loop.

    Returns:
        dict with:
          - "text": str — the model's final text response
          - "tool_results": list[dict] — each dict has {"tool": name, "result": json_str}
    """
```

**Implementation details:**
- Accumulate tool results in a list as tools are executed
- On each tool call, append `{"tool": tool_name, "result": tool_result_str}` to the list
- When the loop ends, return `{"text": final_content, "tool_results": accumulated_list}`
- Update the early return paths (errors, no choices, exhausted iterations) to also return dicts

**Gate:**
```bash
APP_MOCK_MODE=true python3 -c "
from server.agents.agent_loop import run_agent_loop
result = run_agent_loop('Find apartments in Austin')
assert isinstance(result, dict), 'Expected dict'
assert 'text' in result, 'Missing text key'
assert 'tool_results' in result, 'Missing tool_results key'
print('PASS:', result.keys())
"
```

---

### Step 2.2: Update _query_agent Helper

**File:** `server/routers/api.py`

**Change:** Update `_query_agent()` to work with the new dict return type:

```python
def _query_agent(user_message: str) -> Optional[dict]:
    try:
        from server.agents.agent_loop import run_agent_loop
        result = run_agent_loop(user_message)
        if result and result.get("text"):
            return result  # Now returns {"text": ..., "tool_results": [...]}
        return None
    except Exception as exc:
        logger.warning("Agent loop failed: %s", exc)
        return None
```

**Gate:** No standalone gate — tested as part of Step 2.4.

---

### Step 2.3: Create Genie-to-Listing Mapper

**File:** `server/routers/api.py` (add a new helper function)

**Task:** Create `_genie_rows_to_listings(tool_results: list) -> list[dict]` that:

1. Finds the first `query_genie` result in `tool_results`
2. Parses its JSON to get `columns` and `rows`
3. Maps each Genie row to the frontend `Listing` format:

```python
def _genie_rows_to_listings(tool_results: list) -> list[dict]:
    """Extract Genie query results and map to frontend Listing objects."""
    for tr in tool_results:
        if tr.get("tool") != "query_genie":
            continue
        try:
            genie_data = json.loads(tr["result"])
        except (json.JSONDecodeError, KeyError):
            continue

        if "error" in genie_data or not genie_data.get("rows"):
            continue

        listings = []
        for row in genie_data["rows"]:
            listings.append({
                "id": row.get("listing_id", row.get("id", "")),
                "title": row.get("title", "Untitled"),
                "description": row.get("description", ""),
                "property_type": row.get("property_type", ""),
                "location": {
                    "city": row.get("city", ""),
                    "state": row.get("state", ""),
                    "lat": float(row.get("latitude", 0) or 0),
                    "lng": float(row.get("longitude", 0) or 0),
                    "neighborhood": row.get("neighborhood", ""),
                },
                "bedrooms": int(row.get("bedrooms", 0) or 0),
                "bathrooms": int(row.get("bathrooms", 0) or 0),
                "max_guests": int(row.get("max_guests", 0) or 0),
                "amenities": [],
                "house_rules": "",
                "photos": [],
                "nightly_rate": float(row.get("nightly_rate", 0) or 0),
                "cleaning_fee": float(row.get("cleaning_fee", 0) or 0),
                "service_fee_pct": 0.12,
                "tax_pct": 0.08,
                "rating": float(row.get("rating", 0) or 0),
                "review_count": int(row.get("review_count", 0) or 0),
                "host_name": row.get("host_name", ""),
                "is_available": True,
            })
        return listings

    return []  # No Genie results found
```

**Gate:**
```bash
python3 -c "
import json
# Simulate the mapper with mock Genie data
mock_tool_results = [{'tool': 'query_genie', 'result': json.dumps({
    'columns': ['listing_id','title','city','state','nightly_rate','bedrooms','bathrooms','rating','review_count'],
    'rows': [{'listing_id':'lst-001','title':'Test Loft','city':'Austin','state':'TX','nightly_rate':'175','bedrooms':'2','bathrooms':'1','rating':'4.9','review_count':'127'}],
    'row_count': 1
})}]
# Paste _genie_rows_to_listings function here or import it
print('PASS: mapper produces listing objects')
"
```

---

### Step 2.4: Update Search Endpoints

**File:** `server/routers/api.py`

**Change:** Update both `natural_language_search()` and `agent_search()` to extract
listings from agent tool results:

**For `natural_language_search()`:**
```python
agent_result = _query_agent(f"Parse this accommodation search query and find matching listings: {request.query}")
if agent_result:
    listings = _genie_rows_to_listings(agent_result.get("tool_results", []))
    return {
        "query": request.query,
        "extracted_filters": {},
        "filter_chips": [],
        "agent_response": agent_result.get("text", ""),
        "listings": listings,
        "total": len(listings),
        "source": "agent",
    }
```

**For `agent_search()`:**
```python
agent_result = _query_agent(request.query)
if agent_result:
    listings = _genie_rows_to_listings(agent_result.get("tool_results", []))
    return {
        "query": request.query,
        "agent_summary": agent_result.get("text", ""),
        "resolved_params": {},
        "listings": listings,
        "total": len(listings),
        "source": "agent",
    }
```

**Gate:**
```bash
# Start the server locally, then:
curl -s -X POST http://localhost:8000/api/search/agent \
  -H "Content-Type: application/json" \
  -d '{"query": "Find apartments in Austin under 200"}' | python3 -c "
import sys, json
data = json.load(sys.stdin)
print('source:', data.get('source'))
print('total:', data.get('total'))
print('listings count:', len(data.get('listings', [])))
assert data.get('source') == 'agent', 'Expected agent source'
assert data.get('total', 0) > 0, 'Expected listings'
print('PASS')
"
```

---

### Step 2.5: Deploy and E2E Test

**Subagent:** databricks-deployer (`agentic-framework/agents/databricks-deployer.md`)

**Task:**
- Redeploy the Databricks App with updated `agent_loop.py` and `api.py`
- Open the app URL in a browser
- Switch to "Agent Search" mode
- Type "Find apartments in Austin under $200/night"
- Verify listing cards are rendered (not just text)

**Gate:** The search results page shows listing cards with photos, titles, and prices — not just an agent text summary.

## Step Dependency Diagram

```
Part 1 Complete (agent tested and deployed)
        │
  Step 2.1: Modify agent loop return type
        │
  Step 2.2: Update _query_agent helper
        │
  Step 2.3: Create Genie-to-Listing mapper
        │
  Step 2.4: Update search endpoints
        │
  Step 2.5: Deploy and E2E test
```

All steps are sequential — each depends on the previous.

## Key Files

| File | Role |
|------|------|
| `server/agents/agent_loop.py` | Agent loop — modified return type (Step 2.1) |
| `server/routers/api.py` | API endpoints — mapper + wiring (Steps 2.2-2.4) |
| `src/services/api.ts` | Frontend TypeScript types (reference only — no changes) |
| `src/components/SearchResults.tsx` | Frontend consumer (reference only — no changes) |
