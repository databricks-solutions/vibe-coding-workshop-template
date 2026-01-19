# Figma Interface Design Prompt

## Purpose

This prompt generates a **complete, production-ready Figma design guide** for any application, grounded in actual capabilities. It produces step-by-step AI-friendly prompts that can be fed directly to Figma AI or any design tool.

---

## 📋 Fill In Your Project Details First

### Section 1: Product Definition

```yaml
PRODUCT:
  name: "[Your Product Name]"
  tagline: "[One-line description]"
  category: "[monitoring|analytics|workflow|collaboration|marketplace|other]"
  
  # Who uses this?
  primary_users:
    - role: "[e.g., Platform Engineer]"
      goal: "[What they're trying to accomplish]"
    - role: "[e.g., FinOps Analyst]"
      goal: "[What they're trying to accomplish]"
  
  # Core user questions (what mental model?)
  user_questions:
    - "[What's broken/wrong?]"
    - "[Why did it happen?]"
    - "[What should I do?]"
    - "[Did it work?]"
  
  # Design inspiration (which apps to mimic?)
  design_inspiration:
    - app: "[e.g., Datadog]"
      patterns: "[What to borrow - e.g., single pane of glass, dense tables]"
    - app: "[e.g., Grafana]"
      patterns: "[What to borrow - e.g., time controls, panel system]"
    - app: "[e.g., Notion]"
      patterns: "[What to borrow - e.g., clean UX, command palette]"
```

### Section 2: Capability Inventory

**Critical: List ONLY features you have actually built. No aspirational features.**

```yaml
CAPABILITIES:
  # Data sources - what data can users see?
  data_assets:
    tables: "[Count] Gold layer tables"
    metrics: "[Count] custom metrics"
    dimensions: "[List key dimensions: workspace, user, date, etc.]"
  
  # Functions - what can users query?
  functions:
    tvfs: "[Count] Table-Valued Functions"
    categories:
      - name: "[Category 1]"
        count: "[N]"
        examples: "[example_function_1, example_function_2]"
      - name: "[Category 2]"
        count: "[N]"
        examples: "[example_function_1, example_function_2]"
  
  # Intelligence - what AI/ML capabilities exist?
  intelligence:
    ml_models:
      count: "[N]"
      domains:
        - name: "[Domain 1]"
          models: "[N]"
          capabilities: "[prediction, anomaly detection, classification]"
        - name: "[Domain 2]"
          models: "[N]"
          capabilities: "[forecasting, clustering]"
    
    agents:
      architecture: "[single unified | multiple specialized]"
      capabilities:
        - "[capability 1]"
        - "[capability 2]"
      memory: "[yes/no - short-term, long-term]"
      actions: "[list actions agent can take]"
  
  # Alerts - what alerting exists?
  alerts:
    count: "[N]"
    domains:
      - "[domain 1]: [N] alerts"
      - "[domain 2]: [N] alerts"
    channels: "[email, slack, pagerduty, webhook]"
  
  # Dashboards - what pre-built views exist?
  dashboards:
    count: "[N]"
    list:
      - "[Dashboard 1]"
      - "[Dashboard 2]"
  
  # Actions - what can the system DO (not just show)?
  actions:
    - action: "[e.g., Kill runaway job]"
      automated: "[yes/no]"
    - action: "[e.g., Apply fix]"
      automated: "[yes/no]"
```

### Section 3: Screen Inventory

**Based on your capabilities, define which screens you need:**

```yaml
SCREENS:
  # Required screens (pick from template)
  core:
    - name: "Executive Overview"
      purpose: "KPIs, health summary, critical alerts"
      required: true
    
    - name: "Explorer/List View"
      purpose: "Browse all items with filters"
      required: true
    
    - name: "Detail/Drilldown"
      purpose: "Deep dive into single item"
      required: true
  
  # Domain-specific screens
  domains:
    - name: "[Domain 1] Page"
      purpose: "[What this shows]"
      key_metrics: "[metric1, metric2, metric3]"
    
    - name: "[Domain 2] Page"
      purpose: "[What this shows]"
      key_metrics: "[metric1, metric2, metric3]"
  
  # Feature screens
  features:
    - name: "Chat/AI Interface"
      include: "[yes/no - only if you have agents]"
    
    - name: "Alert Center"
      include: "[yes/no - only if you have alerts]"
    
    - name: "Settings"
      include: "[yes - always needed]"
  
  # DO NOT include if you don't have the capability
  excluded:
    - name: "[Screen you don't need]"
      reason: "[Not implemented / Not in scope]"
```

---

## 🚀 The Master Prompt

**Copy everything below and fill in the [PLACEHOLDERS] from your sections above:**

---

```
You are a senior product designer creating a complete Figma design system.

=== PRODUCT CONTEXT ===

Product: [PRODUCT.name]
Tagline: [PRODUCT.tagline]

Primary Users:
[For each user in PRODUCT.primary_users:]
- [role]: [goal]

User Mental Model (the questions they ask):
[For each question in PRODUCT.user_questions:]
- [question]

=== DESIGN PHILOSOPHY ===

Create an enterprise-grade interface that rivals [PRODUCT.design_inspiration apps].
Borrow these specific patterns:
[For each app in PRODUCT.design_inspiration:]
- [app]: [patterns]

Visual Style:
- Modern, crisp enterprise SaaS
- Dense but readable (monitoring tool density, not consumer app whitespace)
- Dark mode primary (matches developer tools)
- Clear information hierarchy
- Fast scanning and triage

=== CAPABILITIES TO SURFACE ===

**CRITICAL: Only include features from this list. No aspirational features.**

Data:
- [CAPABILITIES.data_assets.tables]
- [CAPABILITIES.data_assets.metrics]
- Key dimensions: [CAPABILITIES.data_assets.dimensions]

Intelligence:
[If CAPABILITIES.intelligence.ml_models exists:]
- [ml_models.count] ML models for: [list domains and capabilities]
[If CAPABILITIES.intelligence.agents exists:]
- AI Assistant: [architecture], with [capabilities]
- Memory: [memory capabilities]
- Can take actions: [actions list]

Alerts:
[If CAPABILITIES.alerts exists:]
- [alerts.count] alert rules across [domains]
- Notification channels: [channels]

Pre-built Dashboards:
[If CAPABILITIES.dashboards exists:]
- [dashboards.count] dashboards: [list]

=== SCREENS TO DESIGN ===

Design [total count] screens at 1440px width:

[List all screens from SCREENS.core, SCREENS.domains, and SCREENS.features]

1. [Screen Name]
   - Purpose: [purpose]
   - Key content: [what to show]
   - Capabilities used: [which capabilities from above]

2. [Next screen...]

=== FOR EACH SCREEN, PROVIDE ===

1. ASCII WIREFRAME (detailed layout with measurements)
2. COMPONENT LIST (every element on screen)
3. DATA MAPPING (which capabilities power which components)
4. INTERACTIONS (what happens on click/hover)
5. STATES (loading, empty, error, success)

=== DELIVERABLES ===

For the complete design system, create:

1. **Context Setup Prompt** - Initial AI context for design tool
2. **Per-Screen Prompts** - One detailed prompt per screen
3. **Visualization Guide** - All chart types with specs
4. **Component Library** - All UI components with states
5. **Design Tokens** - Colors, typography, spacing

=== CONSTRAINTS ===

1. ONLY surface capabilities that exist (from list above)
2. Every metric/feature must map to a real capability
3. If it's not in the capabilities list, don't show it
4. Design for power users (dense information, keyboard shortcuts)
5. Desktop-first (1440px), responsive notes optional

=== OUTPUT FORMAT ===

Structure output as markdown files:
- 00-getting-started.md (workflow overview)
- 01-context-setup.md (initial prompt)
- 02-[screen-name].md (one per screen)
- ...
- XX-visualizations.md (chart patterns)
- XX-component-library.md (all components)

Each screen file should contain:
1. Overview (what/why)
2. Design Prompt (copy-paste to Figma AI)
3. Key Measurements (px values)
4. Checklist (what to verify)
5. Capability Mapping (which backend features used)
6. Next pointer (sequential workflow)

BEGIN GENERATING THE COMPLETE FIGMA DESIGN GUIDE.
```

---

## 📝 Example: Databricks Health Monitor

Here's how we filled this out for our project:

```yaml
PRODUCT:
  name: "Databricks Health Monitor"
  tagline: "Enterprise observability for your data platform"
  category: "monitoring"
  
  primary_users:
    - role: "Platform Engineer"
      goal: "Keep the platform healthy and performant"
    - role: "FinOps Analyst"
      goal: "Control and optimize cloud costs"
    - role: "Security Admin"
      goal: "Ensure compliance and security"
  
  user_questions:
    - "What's broken or at risk?"
    - "Why did it happen?"
    - "What should I do about it?"
    - "Did my fix work?"
  
  design_inspiration:
    - app: "Datadog"
      patterns: "Single pane of glass, dense signal tables, filter chips"
    - app: "Grafana"
      patterns: "Time controls, variable selectors, panel layouts"
    - app: "New Relic"
      patterns: "AIOps correlation, root cause analysis"
    - app: "Sentry"
      patterns: "Issue-centric triage, context-rich detail pages"

CAPABILITIES:
  data_assets:
    tables: "40+ Gold layer tables"
    metrics: "155+ custom metrics"
    dimensions: "workspace, user, job, cluster, date, SKU, team"
  
  functions:
    tvfs: "60+ Table-Valued Functions"
    categories:
      - name: "Cost Analysis"
        count: 15
        examples: "get_cost_by_workspace, get_cost_anomalies"
      - name: "Job Performance"
        count: 12
        examples: "get_failed_jobs, get_slow_jobs"
      - name: "Security Events"
        count: 10
        examples: "get_security_events, get_access_violations"
  
  intelligence:
    ml_models:
      count: 25
      domains:
        - name: "Cost"
          models: 6
          capabilities: "forecasting, anomaly detection, waste identification"
        - name: "Performance"
          models: 7
          capabilities: "bottleneck prediction, optimization recommendations"
        - name: "Reliability"
          models: 5
          capabilities: "failure prediction, SLA risk scoring"
        - name: "Security"
          models: 4
          capabilities: "threat detection, access anomalies"
        - name: "Quality"
          models: 3
          capabilities: "data drift, freshness prediction"
    
    agents:
      architecture: "single unified"
      capabilities:
        - "Answer questions across all domains"
        - "Correlate issues across systems"
        - "Recommend actions"
        - "Execute fixes with approval"
      memory: "yes - short-term (conversation) + long-term (preferences, past issues)"
      actions:
        - "Kill runaway jobs"
        - "Adjust cluster sizes"
        - "Create alerts"
        - "Generate reports"
  
  alerts:
    count: 56
    domains:
      - "Cost: 12 alerts"
      - "Performance: 15 alerts"
      - "Reliability: 10 alerts"
      - "Security: 12 alerts"
      - "Quality: 7 alerts"
    channels: "email, Slack, PagerDuty"
  
  dashboards:
    count: 12
    list:
      - "Cost Overview"
      - "Job Performance"
      - "Security Audit"
      - "Data Quality"

SCREENS:
  core:
    - name: "Executive Overview"
      purpose: "Platform health at a glance"
      required: true
    - name: "Global Explorer"
      purpose: "Browse all signals with filters"
      required: true
    - name: "Signal Detail"
      purpose: "Deep dive with root cause"
      required: true
  
  domains:
    - name: "Cost Domain"
      purpose: "Cost analytics and optimization"
      key_metrics: "total_cost, cost_trend, waste_identified"
    - name: "Reliability Domain"
      purpose: "Job health and SLA tracking"
      key_metrics: "success_rate, failed_jobs, sla_status"
    - name: "Performance Domain"
      purpose: "System performance metrics"
      key_metrics: "query_duration, cluster_utilization"
    - name: "Security Domain"
      purpose: "Compliance and access"
      key_metrics: "security_events, access_violations"
    - name: "Quality Domain"
      purpose: "Data quality metrics"
      key_metrics: "freshness, completeness, accuracy"
  
  features:
    - name: "Chat Interface"
      include: "yes"
    - name: "Alert Center"
      include: "yes"
    - name: "Settings"
      include: "yes"
  
  excluded:
    - name: "Dashboard Builder"
      reason: "Not implemented - we have pre-built dashboards only"
```

---

## ✅ Pre-Flight Checklist

Before generating, verify:

- [ ] All capabilities are actually implemented (not planned)
- [ ] Screen list matches capability inventory
- [ ] No screen references features that don't exist
- [ ] Design inspiration apps are relevant to your category
- [ ] User questions reflect real user needs

---

## 🎯 Usage

1. **Fill out Sections 1-3** with your project details
2. **Copy the Master Prompt** and fill in placeholders
3. **Feed to Claude/GPT-4** to generate complete Figma guides
4. **Use generated prompts** in Figma AI or similar tools
5. **Iterate** on individual screens as needed

---

## 📚 Related Templates

- [02-capability-audit-prompt.md](02-capability-audit-prompt.md) - Audit your codebase for capabilities
- [03-design-system-prompt.md](03-design-system-prompt.md) - Generate design tokens
- [04-component-library-prompt.md](04-component-library-prompt.md) - Generate component specs

---

**Version:** 1.0  
**Created:** January 2026  
**Based on:** Databricks Health Monitor design process

