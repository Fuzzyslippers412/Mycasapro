# MyCasa Pro

> AI-Driven Home Operating System — A Super Skill for Clawdbot

## Overview

MyCasa Pro is a comprehensive home management system that runs as an installable Clawdbot skill. It provides:

- **Finance Manager** — Bills, spending, budgets, portfolio tracking, system cost awareness
- **Maintenance Manager** — Tasks, scheduling, home readings, recurring maintenance
- **Security Manager** — Incident logging, monitoring, alerts
- **Contractors Manager** — Service provider directory, work history
- **Projects Manager** — Home improvement tracking, milestones, budgets

## Quick Start

```bash
# Install the skill
clawdbot skill install mycasa-pro

# Or via ClawdHub
clawdhub install mycasa-pro

# Start the dashboard
clawdbot mycasa start
```

## Requirements

- Clawdbot v1.0+
- Python 3.11+
- 512MB disk space (for SQLite database)

## Installation

MyCasa Pro auto-provisions on first run:

1. Creates data directory
2. Initializes SQLite database
3. Runs migrations
4. Seeds default settings
5. Registers with Clawdbot

## First-Run Wizard

On first launch, complete the setup wizard:

1. **Tenant Setup** — Name your household
2. **Income Source** — Primary funding source (required)
3. **Budgets** — Set spend guardrails (sensible defaults provided)
4. **Connectors** — Enable Gmail, WhatsApp, Calendar (optional)
5. **Notifications** — Alert preferences

## Commands

```bash
# Start dashboard (web UI)
clawdbot mycasa start [--port 8505]

# Show status
clawdbot mycasa status

# Run sync (all connectors)
clawdbot mycasa sync

# Export settings
clawdbot mycasa settings export > settings.json

# Import settings
clawdbot mycasa settings import settings.json

# Run migrations
clawdbot mycasa migrate
```

## Connectors

Enable pluggable connectors for external services:

| Connector | Description | Auth Type |
|-----------|-------------|-----------|
| gmail | Email ingestion | OAuth2 |
| whatsapp | Message sync | QR Link |
| calendar | Event sync | OAuth2 |
| bank_import | Transaction import | CSV/OFX |
| sms | SMS alerts | API Key |

Enable connectors in Settings → Connectors.

## Configuration

### Settings Hierarchy

1. **Defaults** — Shipped with skill
2. **Global** — Infrastructure-wide
3. **Manager** — Per-manager config
4. **Connector** — Per-connector config
5. **Tenant** — Per-tenant overrides

### Key Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `finance.system_cost_budget` | $1,000/mo | MyCasa operational cost cap |
| `finance.monthly_spend_limit` | $10,000/mo | Household spend target |
| `finance.daily_soft_cap` | $150/day | Daily spend visibility threshold |
| `maintenance.task_reminder_days` | 3 | Days before due to remind |

## Multi-Tenant Support

MyCasa Pro supports multi-tenant deployment:

- Strict data isolation per tenant
- Per-tenant encryption keys
- Per-tenant quotas and rate limits
- Per-tenant billing/usage tracking

Enable with: `settings.global.multi_tenant_enabled = true`

## API

REST API available at `/api`:

```
GET  /api/tenant/status
GET  /api/settings
PUT  /api/settings/{scope}/{namespace}
POST /api/settings/export
POST /api/settings/import
GET  /api/connectors
POST /api/connectors/{id}/auth
GET  /api/inbox
GET  /api/usage
```

## Development

```bash
# Clone and install dev dependencies
git clone https://github.com/clawdbot/mycasa-pro
cd mycasa-pro
pip install -e ".[dev]"

# Run tests
pytest

# Run locally
python -m mycasa_pro.app
```

## Versioning

- **Semantic Versioning:** MAJOR.MINOR.PATCH
- **Database Migrations:** Automatic via Alembic
- **Settings Migrations:** Version-aware upgrade scripts

## License

MIT

## Support

- Docs: https://docs.clawd.bot/skills/mycasa-pro
- Issues: https://github.com/clawdbot/mycasa-pro/issues
- Discord: https://discord.gg/clawd
