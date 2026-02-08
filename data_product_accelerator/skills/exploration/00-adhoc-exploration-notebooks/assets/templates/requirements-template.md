# Exploration Notebook Requirements Template

Fill in this template before generating exploration notebooks. The agent will use these values to configure the notebooks with correct catalog, schema, and table references.

---

## Catalog Configuration

| Setting | Value |
|---------|-------|
| **Catalog** | _________________ (e.g., `my_catalog`) |
| **Bronze Schema** | _________________ (e.g., `my_project_bronze`) |
| **Silver Schema** | _________________ (e.g., `my_project_silver`) |
| **Gold Schema** | _________________ (e.g., `my_project_gold`) |

## Environment Configuration

| Setting | Dev Value | Prod Value |
|---------|-----------|------------|
| **Catalog** | `dev_catalog` | `prod_catalog` |
| **Schema Prefix** | `dev_{username}_{project}` | `{project}` |
| **Databricks Profile** | `dev` | `prod` |

### Dev Environment (with user prefix)

```python
catalog = "dev_catalog"
bronze_schema = f"dev_{username}_{project}_bronze"
silver_schema = f"dev_{username}_{project}_silver"
gold_schema = f"dev_{username}_{project}_gold"
```

### Production Environment

```python
catalog = "prod_catalog"
bronze_schema = f"{project}_bronze"
silver_schema = f"{project}_silver"
gold_schema = f"{project}_gold"
```

## Tables to Explore

List 5–10 key tables you want to explore across layers:

| # | Layer | Table Name | Purpose |
|---|-------|-----------|---------|
| 1 | Bronze | _________________ | _________________ |
| 2 | Bronze | _________________ | _________________ |
| 3 | Silver | _________________ | _________________ |
| 4 | Silver | _________________ | _________________ |
| 5 | Gold | _________________ | _________________ |
| 6 | Gold | _________________ | _________________ |
| 7 | Gold | _________________ | _________________ |

## Data Quality Focus Areas

Which columns or tables need special attention?

| Table | Column(s) | Concern |
|-------|----------|---------|
| _________________ | _________________ | Nulls / Duplicates / Range / Format |
| _________________ | _________________ | Nulls / Duplicates / Range / Format |

## Cross-Layer Comparisons

Which Bronze → Silver → Gold flows do you want to validate?

| Bronze Table | Silver Table | Gold Table | Key Column(s) |
|-------------|-------------|-----------|---------------|
| _________________ | _________________ | _________________ | _________________ |
| _________________ | _________________ | _________________ | _________________ |

## Metric Views & Monitoring (Optional)

| Metric View / Monitor Table | Purpose |
|----------------------------|---------|
| _________________ | _________________ |
| _________________ | _________________ |
