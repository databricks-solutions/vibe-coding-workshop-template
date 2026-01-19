# 📋 Workshop Prompts

> AI prompts for building features on your Databricks App

This folder contains **reusable prompts** for building data applications with AI-assisted development. Use these with your AI coding assistant (Cursor, GitHub Copilot, etc.) to accelerate development.

---

## 🚀 How to Use These Prompts

### Step 1: Deploy Your App First

Before using these prompts, make sure your Databricks App is deployed:

```bash
# From project root
./scripts/setup.sh
./scripts/deploy.sh --create
```

### Step 2: Choose a Prompt

Pick the prompt that matches what you want to build. Start with the core architecture prompts (01-03) before moving to advanced features.

### Step 3: Use with AI Assistant

Open the prompt file and paste it into your AI assistant, or reference it directly:

```
Using the prompt in context/prompts/01-bronze-layer-prompt.md, 
create a Bronze layer for my booking application with these entities:
- users, properties, bookings, reviews
```

### Step 4: Customize the Output

Review the generated code, customize for your needs, and deploy:

```bash
./scripts/deploy.sh
```

---

## 📁 Prompt Catalog

### Core Architecture

| Prompt | Description | Time |
|--------|-------------|------|
| [01-bronze-layer-prompt.md](./01-bronze-layer-prompt.md) | Raw data ingestion tables | 2-3 hrs |
| [02-silver-layer-prompt.md](./02-silver-layer-prompt.md) | Data quality & validation | 2-4 hrs |
| [03a-gold-layer-design-prompt.md](./03a-gold-layer-design-prompt.md) | Analytics schema design | 2-3 hrs |
| [03b-gold-layer-implementation-prompt.md](./03b-gold-layer-implementation-prompt.md) | Analytics table creation | 3-4 hrs |

### Semantic Layer & BI

| Prompt | Description | Time |
|--------|-------------|------|
| [04-metric-views-prompt.md](./04-metric-views-prompt.md) | Metric definitions for Genie | 2 hrs |
| [09-table-valued-functions-prompt.md](./09-table-valued-functions-prompt.md) | Reusable SQL functions | 2-3 hrs |
| [10-aibi-dashboards-prompt.md](./10-aibi-dashboards-prompt.md) | Lakeview dashboards | 2-4 hrs |

### Observability

| Prompt | Description | Time |
|--------|-------------|------|
| [05-monitoring-prompt.md](./05-monitoring-prompt.md) | Lakehouse Monitoring setup | 2 hrs |
| [07-dqx-integration-prompt.md](./07-dqx-integration-prompt.md) | Advanced data quality | 3-4 hrs |

### Development Tools

| Prompt | Description | Time |
|--------|-------------|------|
| [06-genie-space-prompt.md](./06-genie-space-prompt.md) | Natural language queries | 1-2 hrs |
| [08-exploration-notebook-prompt.md](./08-exploration-notebook-prompt.md) | Ad-hoc data exploration | 1 hr |

### Planning & Advanced

| Prompt | Description | Time |
|--------|-------------|------|
| [11-project-plan-prompt.md](./11-project-plan-prompt.md) | Project planning | 2-4 hrs |
| [12-ml-models-prompt.md](./12-ml-models-prompt.md) | ML pipelines | 6-12 hrs |
| [13-agent-architecture-design-prompt.md](./13-agent-architecture-design-prompt.md) | AI agent design | 2-4 hrs |
| [14-sql-alerts-prompt.md](./14-sql-alerts-prompt.md) | SQL alerting | 1-2 hrs |
| [15-documentation-framework-prompt.md](./15-documentation-framework-prompt.md) | Documentation | 2 hrs |
| [16-capability-audit-prompt.md](./16-capability-audit-prompt.md) | Feature audit | 1-2 hrs |
| [17-figma-interface-design-prompt.md](./17-figma-interface-design-prompt.md) | UI design | 2-3 hrs |

---

## 🎯 Recommended Path

### Quick Start (10-15 hours)
```
01-bronze-layer → 02-silver-layer → 03a-gold-design → 03b-gold-implementation
```

### With Analytics (18-24 hours)
```
Quick Start + 04-metric-views → 05-monitoring → 10-aibi-dashboards
```

### Full Stack (30+ hours)
```
With Analytics + remaining prompts as needed
```

---

## 💡 Tips

1. **Start Small** - Begin with 3-5 tables, not 50
2. **Deploy Often** - Test each component before moving on
3. **Customize** - These are templates; adapt to your needs
4. **Use the Schema** - Reference `context/booking_app_schema.csv` for the sample data model

---

## 📖 Related Documentation

- [Main README](../../README.md) - Project setup and deployment
- [QUICKSTART](../../QUICKSTART.md) - Quick command reference
- [Databricks Apps Docs](https://docs.databricks.com/dev-tools/databricks-apps/)
