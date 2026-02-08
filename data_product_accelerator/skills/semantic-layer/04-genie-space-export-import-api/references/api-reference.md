# Genie Space Export/Import API Reference

## API Endpoints

### Official API Documentation

- [Create Space](https://docs.databricks.com/api/workspace/genie/createspace)
- [Update Space](https://docs.databricks.com/api/workspace/genie/updatespace)
- [List Spaces](https://docs.databricks.com/api/workspace/genie/listspaces)
- [Trash Space](https://docs.databricks.com/api/workspace/genie/trashspace)

---

## List All Genie Spaces

```bash
GET /api/2.0/genie/spaces
Authorization: Bearer <your_personal_access_token>
```

**Response:**
```json
{
  "spaces": [
    {
      "space_id": "01ef274d35a310b5bffd01dadcbaf577",
      "title": "Sales Analytics",
      "description": "Natural language sales analysis",
      "warehouse_id": "abc123def456"
    },
    {
      "space_id": "01ef274d35a310b5bffd01dadcbaf588",
      "title": "Cost Intelligence",
      "description": "FinOps and cost analytics",
      "warehouse_id": "abc123def456"
    }
  ]
}
```

**Use Case:** Discover existing spaces, check if space already exists before creating

---

## Export/Get a Genie Space

```bash
GET /api/2.0/genie/spaces/{space_id}?include_serialized_space=true
Authorization: Bearer <your_personal_access_token>
```

**Response:**
```json
{
  "space_id": "01ef274d35a310b5bffd01dadcbaf577",
  "title": "My Space",
  "description": "My Space Description",
  "warehouse_id": "abc123def456",
  "serialized_space": "{\n  \"version\": 1,\n  \"config\": {...}\n}"
}
```

**Use Case:** Export configuration for version control, backup, or migration

---

## Create a New Genie Space

```bash
POST /api/2.0/genie/spaces
Authorization: Bearer <your_personal_access_token>
Content-Type: application/json

{
  "title": "My New Space",
  "description": "Description here",
  "warehouse_id": "abc123def456",
  "parent_path": "/Workspace/Users/user@company.com/Genie Spaces",
  "serialized_space": "{...escaped JSON string...}"
}
```

**Response:**
```json
{
  "space_id": "01ef274d35a310b5bffd01dadcbaf577",
  "title": "My New Space",
  "description": "Description here",
  "warehouse_id": "abc123def456",
  "serialized_space": "{\n  \"version\": 1,\n  \"config\": {...}\n}"
}
```

**Use Case:** Programmatic deployment, CI/CD pipelines, environment promotion

---

## Update an Existing Genie Space

```bash
PATCH /api/2.0/genie/spaces/{space_id}
Authorization: Bearer <your_personal_access_token>
Content-Type: application/json

{
  // All fields optional - only include fields you want to update
  "title": "My Updated Space",
  "description": "Updated description",
  "warehouse_id": "abc123def456",
  "parent_path": "/Workspace/Users/user@company.com/Genie Spaces",
  "serialized_space": "{...updated JSON string...}"
}
```

**Response:**
```json
{
  "space_id": "01ef274d35a310b5bffd01dadcbaf577",
  "title": "My Updated Space",
  "description": "Updated description",
  "warehouse_id": "abc123def456",
  "serialized_space": "{\n  \"version\": 1,\n  \"config\": {...}\n}"
}
```

**Key Points:**
- **PATCH is partial update** - Only include fields you want to change
- **`serialized_space`** - If provided, completely replaces the space configuration
- **`parent_path`** - Optional, allows moving the space to a different folder
- **All fields optional** - Update title only, config only, or any combination

**Use Case:** Incremental updates, configuration changes, adding benchmarks

---

## Delete/Trash a Genie Space

```bash
DELETE /api/2.0/genie/spaces/{space_id}
Authorization: Bearer <your_personal_access_token>
```

**Response:**
```json
{
  "space_id": "01ef274d35a310b5bffd01dadcbaf577"
}
```

**Use Case:** Cleanup, decommissioning, environment teardown

⚠️ **Warning:** This permanently deletes the Genie Space and cannot be undone.

---

## Using Databricks CLI

```bash
# List all spaces
databricks api get /api/2.0/genie/spaces --profile <profile>

# Export/Get space
databricks api get "/api/2.0/genie/spaces/{space_id}?include_serialized_space=true" --profile <profile>

# Create space (POST with JSON body)
databricks api post /api/2.0/genie/spaces --profile <profile> --json '{...}'

# Update space (PATCH with JSON body)
databricks api patch "/api/2.0/genie/spaces/{space_id}" --profile <profile> --json '{...}'

# Delete/Trash space
databricks api delete "/api/2.0/genie/spaces/{space_id}" --profile <profile>
```

---

## API Operations Summary

| Operation | Method | Endpoint | Use Case |
|-----------|--------|----------|----------|
| **List Spaces** | GET | `/api/2.0/genie/spaces` | Discover existing spaces, check before creating |
| **Get Space** | GET | `/api/2.0/genie/spaces/{space_id}` | Export config, backup, version control |
| **Create Space** | POST | `/api/2.0/genie/spaces` | New deployment, CI/CD, environment setup |
| **Update Space** | PATCH | `/api/2.0/genie/spaces/{space_id}` | Modify config, add benchmarks, update metadata |
| **Delete Space** | DELETE | `/api/2.0/genie/spaces/{space_id}` | Cleanup, decommissioning, teardown |

---

## Authentication

All API endpoints require authentication via Bearer token:

```bash
Authorization: Bearer <your_personal_access_token>
```

Generate a personal access token in Databricks:
1. Go to User Settings → Access Tokens
2. Generate New Token
3. Copy token (only shown once)

---

## API Wrapper Structure

The API wraps the `serialized_space` JSON in a top-level structure:

```json
{
  "description": "Natural language description for users",
  "serialized_space": "{...JSON string of GenieSpaceExport...}",
  "space_id": "01f0ad0d629b11879bb8c06e03b919f8",
  "title": "Display Name",
  "warehouse_id": "4b9b953939869799"
}
```

**Note:** `serialized_space` is a JSON string (escaped), not a nested object. When creating/updating, you must `json.dumps()` the GenieSpaceExport object before including it in the payload.
