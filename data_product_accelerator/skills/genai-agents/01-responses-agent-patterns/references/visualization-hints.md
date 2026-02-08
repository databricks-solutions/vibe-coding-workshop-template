# Visualization Hints (AI/BI Integration)

## Generating Visualization Metadata

Include visualization hints in `ResponsesAgentResponse.custom_outputs` to help AI/BI dashboards render appropriate charts.

```python
def generate_visualization_hints(domain: str, data: dict) -> dict:
    """
    Generate visualization hints for AI/BI dashboards.
    
    Returns metadata about chart type, axes, and formatting.
    """
    hints = {
        "visualization_type": None,
        "x_axis": None,
        "y_axis": None,
        "color_by": None,
        "sort_by": None,
        "format": {}
    }
    
    # Domain-specific hints
    if domain == "cost":
        if "time_series" in data:
            hints["visualization_type"] = "line_chart"
            hints["x_axis"] = "date"
            hints["y_axis"] = "cost_usd"
            hints["format"]["y_axis"] = {"type": "currency", "currency": "USD"}
        
        elif "top_n" in data:
            hints["visualization_type"] = "bar_chart"
            hints["x_axis"] = "job_name"
            hints["y_axis"] = "cost_usd"
            hints["sort_by"] = {"field": "cost_usd", "order": "desc"}
            hints["format"]["y_axis"] = {"type": "currency", "currency": "USD"}
    
    elif domain == "reliability":
        hints["visualization_type"] = "table"
        hints["columns"] = ["job_name", "failure_count", "last_failure_time"]
        hints["format"]["failure_count"] = {"type": "number"}
        hints["format"]["last_failure_time"] = {"type": "datetime"}
    
    return hints
```

## Including Hints in ResponsesAgentResponse

```python
# In agent predict() method
response_text, visualization_hints = process_query(query)

return ResponsesAgentResponse(
    output=[self.create_text_output_item(text=response_text, id=str(uuid.uuid4()))],
    custom_outputs={
        "visualization_hints": visualization_hints,  # For AI/BI dashboards
        "domain": domain,
    }
)
```

## Hint Schema

| Field | Type | Description |
|---|---|---|
| `visualization_type` | string | `line_chart`, `bar_chart`, `table`, `pie_chart` |
| `x_axis` | string | Column name for x-axis |
| `y_axis` | string | Column name for y-axis |
| `color_by` | string | Column name for color grouping |
| `sort_by` | dict | `{"field": str, "order": "asc"/"desc"}` |
| `columns` | list | Column names for table visualization |
| `format` | dict | Per-field formatting (currency, number, datetime) |
