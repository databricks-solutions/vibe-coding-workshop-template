# Metric View Implementation Workflow

Detailed step-by-step guide for creating metric views from design through deployment.

---

## Step 1: Metric View Design

### Design Checklist

- [ ] **Fact Table:** Which fact table is the primary source?
- [ ] **Dimensions:** Which dimensions to join? (store, product, date)
- [ ] **Measures:** What are the key metrics? (revenue, units, transactions)
- [ ] **User Questions:** What questions will users ask?
- [ ] **Synonyms:** Alternative names for each dimension and measure?

### Example Design

**Business Questions:**
- "What is total revenue by store?"
- "Show me top products by sales"
- "What's the average transaction value?"
- "How many units were sold last month?"

**Metric View Design Sketch:**
```yaml
# Design sketch (not final YAML — no 'name' field in final YAML!)
view_name: sales_performance_metrics  # This becomes the filename
fact_table: fact_sales_daily
dimensions:
  - From fact: store_number, upc_code, transaction_date
  - From dim_store: store_name, city, state
  - From dim_product: brand, category
  - From dim_date: year, quarter, month_name
measures:
  - total_revenue: SUM(net_revenue) — currency USD
  - total_units: SUM(net_units) — number
  - transaction_count: SUM(transaction_count) — number
  - avg_transaction_value: AVG(avg_transaction_value) — currency USD
```

**Use Template:** `references/requirements-template.md` for the full design template.

---

## Step 2: Create Metric View YAML

### YAML File Organization

**Preferred: One file per metric view** (filename = view name)

```
src/semantic/metric_views/
├── sales_performance_metrics.yaml
├── inventory_analytics_metrics.yaml
└── customer_segmentation_metrics.yaml
```

**Alternative: Single file with multiple views** (use `name` field for routing — it gets stripped before sending to Databricks)

### YAML Creation Steps

1. **Set version:** `version: "1.1"` (quoted string, first line)
2. **Write comment:** Use structured format (PURPOSE, BEST FOR, NOT FOR, DIMENSIONS, MEASURES, SOURCE, JOINS, NOTE)
3. **Define source:** Fully qualified fact table path with `${catalog}` and `${gold_schema}` placeholders
4. **Add joins:** For each dimension table:
   - `name`: Join alias (used as column prefix in expressions)
   - `source`: Fully qualified dimension table path
   - `'on'`: Join condition (**quoted key!**). Include `AND {dim}.is_current = true` for SCD2
5. **Define dimensions:** For each dimension column:
   - Correct prefix (`source.` for fact, `{join_name}.` for dimension)
   - Business-friendly comment optimized for Genie
   - Display name for UI
   - 3-5 synonyms (think like a business user asking questions)
6. **Define measures:** For each measure:
   - Correct aggregation (SUM, COUNT, AVG)
   - Proper formatting (currency/number/percentage)
   - Comprehensive comment explaining the calculation
   - 3-5 synonyms

**Reference:** `references/yaml-reference.md` for complete field documentation.
**Reference:** `references/advanced-patterns.md` for a complete worked example.

### ⚠️ CRITICAL: Validate Before Proceeding

Run the validation script to check all column references:

```bash
python scripts/validate_metric_view.py \
  --yaml-file src/semantic/metric_views/sales_performance_metrics.yaml \
  --gold-yaml-dir gold_layer_design/yaml
```

---

## Step 3: Python Creation Script

Use `scripts/create_metric_views.py` as the creation script.

### Per-File Mode (Preferred)

```bash
python scripts/create_metric_views.py \
  --catalog my_catalog \
  --gold_schema my_gold \
  --yaml-dir src/semantic/metric_views/
```

### Multi-File Mode (Alternative)

```bash
python scripts/create_metric_views.py \
  --catalog my_catalog \
  --gold_schema my_gold \
  --yaml-file metric_views.yaml
```

The script handles:
- Loading YAML files and substituting `${catalog}` / `${gold_schema}` placeholders
- Stripping the `name` field (if present) before sending to Databricks
- Using `CREATE VIEW ... WITH METRICS LANGUAGE YAML AS $$...$$` syntax
- Verifying each view is type `METRIC_VIEW` (not just `VIEW`)
- Raising `RuntimeError` if any view fails (job fails, doesn't succeed silently)

---

## Step 4: Asset Bundle Configuration

### Job Template

Use `assets/templates/metric-views-job-template.yml` as the starting point for your Asset Bundle job.

### YAML File Sync (CRITICAL)

Add metric view YAML files to your `databricks.yml` sync section:

```yaml
sync:
  include:
    - "src/semantic/metric_views/**/*.yaml"
```

Without this, the creation script won't find the YAML files when running on Databricks.

### Key Bundle Configuration

- Use `notebook_task` (NOT `python_task`)
- Use `base_parameters` dict (NOT CLI-style `parameters`)
- Include `pyyaml>=6.0` in environment dependencies
- Tags: `layer=semantic`, `job_type=metric_views`

---

## Step 5: Deploy & Test

### Deploy

```bash
databricks bundle deploy -t dev
databricks bundle run metric_views_job -t dev
```

### Verify

See `references/validation-queries.md` for complete verification SQL queries.

**Quick verification:**

```sql
-- Verify type
DESCRIBE EXTENDED {catalog}.{schema}.{view_name};
-- Should show: Type: METRIC_VIEW

-- Test MEASURE() function
SELECT
  store_name,
  MEASURE(`Total Revenue`) as revenue
FROM {catalog}.{schema}.sales_performance_metrics
GROUP BY store_name
ORDER BY revenue DESC
LIMIT 10;
```

### Test with Genie

After deployment, test in Genie Space:
- "Show total revenue by store"
- "What are the top 10 products by sales?"
- "Average transaction value by city"

If Genie doesn't understand a query, check synonyms and measure comments in the YAML.
