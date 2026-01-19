# ⚡ Quick Start

Deploy your Databricks App in 4 commands:

```bash
# 1. Clone template
git clone https://github.com/YOUR_ORG/vibe-coding-workshop-template.git my-app && cd my-app

# 2. Setup (configure auth)
./scripts/setup.sh

# 3. Deploy
./scripts/deploy.sh --create

# 4. Open your app URL! 🎉
```

---

## Commands

| Task | Command |
|------|---------|
| **Setup** | `./scripts/setup.sh` |
| **First Deploy** | `./scripts/deploy.sh --create` |
| **Update Deploy** | `./scripts/deploy.sh` |
| **Local Dev** | `./scripts/watch.sh` |
| **Check Status** | `./scripts/app_status.sh` |
| **Format Code** | `./scripts/fix.sh` |

---

## Local URLs

- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/health

---

## Troubleshooting

```bash
# Reconfigure auth
rm .env.local && ./scripts/setup.sh

# Check connection
databricks current-user me

# Check app status
./scripts/app_status.sh --verbose
```

---

**Full docs**: [README.md](README.md)
