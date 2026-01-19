# Capability Audit Prompt

## Purpose

Before designing any UI, you need to know **exactly what your system can do**. This prompt extracts a complete capability inventory from your codebase/documentation to ground your design in reality.

---

## 📋 The Audit Prompt

**Use this prompt with your codebase or documentation:**

```
You are a technical architect auditing a codebase to extract its capabilities.

=== TASK ===

Analyze the provided codebase/documentation and extract a complete inventory of:
1. What data the system has (tables, metrics, dimensions)
2. What functions/APIs exist (what users can query)
3. What intelligence exists (ML models, agents, predictions)
4. What alerts/notifications exist
5. What actions the system can take (automations, fixes)
6. What dashboards/views are pre-built

=== OUTPUT FORMAT ===

Generate a YAML capability inventory:

```yaml
CAPABILITIES:
  # === DATA LAYER ===
  data_assets:
    tables:
      count: [N]
      by_layer:
        bronze: [N]
        silver: [N]
        gold: [N]
      key_tables:
        - name: "[table_name]"
          purpose: "[what it contains]"
          key_columns: "[important columns]"
    
    metrics:
      count: [N]
      by_domain:
        - domain: "[domain]"
          count: [N]
          examples: "[metric1, metric2]"
      
    dimensions:
      - "[dimension1]"
      - "[dimension2]"
  
  # === FUNCTION LAYER ===
  functions:
    tvfs:
      count: [N]
      by_category:
        - category: "[category]"
          count: [N]
          functions:
            - name: "[function_name]"
              purpose: "[what it does]"
              parameters: "[key params]"
              returns: "[what it returns]"
    
    stored_procedures:
      count: [N]
      list: "[if any]"
    
    api_endpoints:
      count: [N]
      list: "[if any]"
  
  # === INTELLIGENCE LAYER ===
  intelligence:
    ml_models:
      count: [N]
      by_domain:
        - domain: "[domain]"
          models:
            - name: "[model_name]"
              type: "[classification|regression|anomaly|forecasting]"
              input: "[what it takes]"
              output: "[what it predicts]"
              accuracy: "[if known]"
    
    agents:
      exists: [true|false]
      architecture: "[single|multi-agent]"
      capabilities:
        - "[capability 1]"
        - "[capability 2]"
      memory:
        short_term: [true|false]
        long_term: [true|false]
      tools_available:
        - "[tool 1]"
        - "[tool 2]"
      actions_can_take:
        - action: "[action]"
          requires_approval: [true|false]
    
    predictions:
      - name: "[prediction type]"
        source: "[model or rule]"
        refresh: "[frequency]"
  
  # === ALERTING LAYER ===
  alerts:
    count: [N]
    by_domain:
      - domain: "[domain]"
        count: [N]
        examples:
          - name: "[alert_name]"
            condition: "[what triggers it]"
            severity: "[critical|warning|info]"
    
    notification_channels:
      - "[email]"
      - "[slack]"
      - "[pagerduty]"
    
    alert_routing:
      exists: [true|false]
      rules: "[description]"
  
  # === DASHBOARD LAYER ===
  dashboards:
    count: [N]
    list:
      - name: "[dashboard_name]"
        purpose: "[what it shows]"
        key_visualizations: "[chart types]"
    
    visualization_types:
      - "[timeseries]"
      - "[bar chart]"
      - "[heatmap]"
      - "[table]"
  
  # === ACTION LAYER ===
  actions:
    automated:
      - action: "[action name]"
        trigger: "[what triggers it]"
        effect: "[what it does]"
    
    user_initiated:
      - action: "[action name]"
        where: "[where in UI]"
        effect: "[what it does]"
    
    agent_actions:
      - action: "[action name]"
        approval: "[auto|manual]"
        effect: "[what it does]"

# === NOT IMPLEMENTED ===
not_implemented:
  - feature: "[Feature name]"
    reason: "[Why not implemented]"
    planned: [true|false]
```

=== AUDIT SOURCES ===

Look for capabilities in:
1. `/docs/` - Design documents and PRDs
2. `/src/` - Source code (especially Gold layer, functions)
3. `/resources/` - Asset bundle definitions (jobs, pipelines)
4. `/gold_layer_design/` - Table schemas
5. Database catalogs - What's actually deployed
6. ML experiments - What models are trained
7. Alert definitions - What alerts are configured

=== VALIDATION RULES ===

1. ONLY include what EXISTS (deployed, not planned)
2. Count actual items, don't estimate
3. If unsure, mark as "needs verification"
4. Separate "implemented" from "planned"
5. Note any capabilities that are partially implemented

=== COMMON OVERSIGHTS ===

Don't forget to check for:
- [ ] Pre-calculated metrics (not just raw data)
- [ ] Derived dimensions (computed fields)
- [ ] Implicit actions (what happens on data change)
- [ ] Integration capabilities (what other systems connect)
- [ ] Admin functions (user management, permissions)
- [ ] Export/report capabilities
```

---

## 🔍 Quick Audit Commands

**For Databricks projects, run these to count capabilities:**

```bash
# Count Gold tables
ls gold_layer_design/yaml/**/*.yaml | wc -l

# Count TVFs
grep -r "CREATE.*FUNCTION" src/ --include="*.sql" | wc -l

# Count ML models
ls src/ml/models/*.py | wc -l

# Count alerts
grep -r "alert_name:" resources/ --include="*.yaml" | wc -l

# Count dashboards
ls src/dashboards/*.sql | wc -l

# Count custom metrics
grep -r "metric_name:" src/monitoring/*.py | wc -l
```

---

## ✅ Audit Checklist

Before using capabilities in design:

- [ ] Verified table counts against catalog
- [ ] Verified function counts against deployment
- [ ] Verified ML models are actually trained
- [ ] Verified alerts are actually configured
- [ ] Verified dashboards are actually deployed
- [ ] Verified agent capabilities match implementation
- [ ] Marked any planned-but-not-built features

---

## 📊 Output Example

Here's our audit for Databricks Health Monitor:

```yaml
CAPABILITIES:
  data_assets:
    tables:
      count: 41
      by_layer:
        bronze: 12
        silver: 15
        gold: 14
      key_tables:
        - name: "fact_daily_usage"
          purpose: "Daily DBU consumption and cost"
          key_columns: "workspace_id, usage_date, sku_name, dbus, cost"
        - name: "fact_job_run_timeline"
          purpose: "Job execution history"
          key_columns: "run_id, job_id, result_state, duration_seconds"
    
    metrics:
      count: 155
      by_domain:
        - domain: "Cost"
          count: 35
          examples: "total_cost, cost_by_workspace, waste_percentage"
        - domain: "Performance"
          count: 42
          examples: "query_duration_p95, cluster_utilization"
    
    dimensions:
      - "workspace_id"
      - "user_identity"
      - "job_name"
      - "cluster_id"
      - "usage_date"
      - "sku_name"
      - "team_tag"

  functions:
    tvfs:
      count: 62
      by_category:
        - category: "Cost Analysis"
          count: 15
          functions:
            - name: "get_cost_by_workspace"
              purpose: "Cost breakdown by workspace"
              parameters: "start_date, end_date, workspace_filter"
              returns: "workspace, total_cost, dbu_cost, compute_cost"

  intelligence:
    ml_models:
      count: 25
      by_domain:
        - domain: "Cost"
          models:
            - name: "cost_forecaster"
              type: "forecasting"
              input: "30 days historical cost"
              output: "7-day cost prediction"
    
    agents:
      exists: true
      architecture: "single"
      capabilities:
        - "Answer questions about any domain"
        - "Correlate issues across systems"
        - "Recommend optimization actions"
        - "Execute approved fixes"
      memory:
        short_term: true
        long_term: true
      tools_available:
        - "Web Search"
        - "Dashboard Linker"
        - "Alert Trigger"
        - "Runbook RAG"
      actions_can_take:
        - action: "Kill runaway job"
          requires_approval: true
        - action: "Create alert rule"
          requires_approval: true

  alerts:
    count: 56
    by_domain:
      - domain: "Cost"
        count: 12
      - domain: "Performance"
        count: 15

  dashboards:
    count: 12
    list:
      - name: "Cost Overview"
        purpose: "Executive cost summary"

not_implemented:
  - feature: "Dashboard Builder"
    reason: "Using pre-built dashboards"
    planned: false
  - feature: "Custom Alert Builder UI"
    reason: "Alerts created via YAML/API"
    planned: true
```

---

## 🔗 Next Step

After completing the audit, use [01-figma-interface-design-prompt.md](01-figma-interface-design-prompt.md) to generate your Figma design guides.

---

**Version:** 1.0  
**Created:** January 2026

