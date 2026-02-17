# MyCasa Pro - Architecture

**Version:** 1.0.0  
**Last Updated:** 2026-01-29

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     MyCasa Pro                               │
├─────────────────────────────────────────────────────────────┤
│  Frontend (Next.js)          │   Backend (FastAPI)          │
│  ─────────────────           │   ─────────────────          │
│  • 14 pages                  │   • 139 API routes           │
│  • Mantine UI                │   • WebSocket events         │
│  • Real-time updates         │   • Agent orchestration      │
├─────────────────────────────────────────────────────────────┤
│                      Agent Layer                             │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────────┐   │
│  │ Manager │ │ Finance │ │ Maint.  │ │ Security/Etc.   │   │
│  │(Coord.) │ │(Budget) │ │(Tasks)  │ │(Incidents)      │   │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────────┬────────┘   │
│       └──────────┬┴───────────┴────────────────┘            │
│                  ▼                                           │
│            Agent Teams (Collaboration)                       │
├─────────────────────────────────────────────────────────────┤
│                   Data Layer                                 │
│  ┌────────────┐ ┌────────────┐ ┌────────────────────────┐  │
│  │ PostgreSQL │ │ SecondBrain│ │ Shared Context         │  │
│  │ (State)    │ │ (Knowledge)│ │ (Clawdbot Memory)      │  │
│  └────────────┘ └────────────┘ └────────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│                 Connector Layer                              │
│  [WhatsApp] [Gmail] [Calendar] [Bank] [HomeAssistant]       │
└─────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
mycasa-pro/
├── agents/                     # AI Agent implementations
│   ├── base.py                # BaseAgent with SecondBrain methods
│   ├── manager.py             # Coordinator agent (Galidima)
│   ├── finance.py             # Budget & portfolio
│   ├── maintenance.py         # Task management
│   ├── security_manager.py    # Security incidents
│   ├── contractors.py         # Service providers
│   ├── projects.py            # Home improvements
│   ├── janitor.py             # System maintenance
│   ├── janitor_debugger.py    # Code auditing
│   ├── teams.py               # Multi-agent collaboration
│   └── scheduler.py           # Scheduled runs
│
├── api/                       # FastAPI backend
│   ├── main.py               # App entry, routes
│   ├── routes/               # Route modules
│   │   ├── secondbrain.py    # Knowledge API
│   │   ├── scheduler.py      # Job scheduling API
│   │   ├── chat.py           # Chat interface API
│   │   ├── connectors.py     # Marketplace API
│   │   ├── system_live.py    # Live status API
│   │   ├── settings.py       # Config & wizard API
│   │   ├── finance.py        # Portfolio API
│   │   ├── inbox.py          # Unified inbox API
│   │   ├── tasks.py          # Task API
│   │   ├── telemetry.py      # Metrics API
│   │   └── messaging.py      # WhatsApp API
│   └── middleware/
│       └── errors.py         # Standardized error handling
│
├── connectors/               # External integrations
│   ├── whatsapp/            # Messaging via Clawdbot
│   ├── gmail/               # Email via gog CLI
│   └── calendar/            # Events via gog CLI
│
├── core/                    # Core utilities
│   ├── secondbrain/         # Knowledge vault
│   │   └── skill.py        # SecondBrain class
│   ├── settings_typed.py    # Type-safe settings
│   ├── shared_context.py    # Clawdbot memory access
│   ├── prompt_security.py   # Injection protection
│   └── system_state.py      # State management
│
├── frontend/               # Next.js frontend
│   └── src/
│       ├── app/            # Pages (14 total)
│       │   ├── page.tsx           # Dashboard
│       │   ├── chat/              # Agent chat
│       │   ├── finance/           # Portfolio
│       │   ├── maintenance/       # Tasks
│       │   ├── contractors/       # Providers
│       │   ├── projects/          # Improvements
│       │   ├── security/          # Incidents
│       │   ├── inbox/             # Messages
│       │   ├── logs/              # System logs
│       │   ├── settings/          # Configuration
│       │   └── system/            # Live status
│       └── components/
│           ├── MemoryGraph/       # Knowledge visualization
│           ├── SchedulerManager/  # Job scheduling UI
│           ├── LiveSystemDashboard/ # Real-time status
│           ├── ConnectorMarketplace/ # Integration browser
│           ├── SetupWizard/       # Onboarding
│           └── SystemMonitor/     # Agent activity
│
├── docs/                  # Documentation
│   ├── ARCHITECTURE.md    # This file
│   ├── FEATURES.md        # Feature reference
│   ├── API_ARCHITECTURE.md # API design
│   ├── SECONDBRAIN_INTEGRATION.md # Knowledge vault spec
│   └── LOBEHUB_ANALYSIS.md # LobeHub feature adoption
│
├── scripts/              # Utilities
│   ├── test_api.py       # API tests
│   └── verify_build.py   # Build verification
│
├── CHANGELOG.md          # Version history
└── start.sh             # Startup script
```

## Agent System

### Agent Types

| Agent | Purpose | Key Methods |
|-------|---------|-------------|
| **Manager** | Coordinates all agents, routes requests | `quick_status()`, `full_report()`, `delegate()` |
| **Finance** | Budget tracking, portfolio analysis | `get_recommendations()`, `analyze_spending()` |
| **Maintenance** | Home tasks, scheduling | `get_tasks()`, `schedule_task()` |
| **Security** | Incident tracking, monitoring | `log_incident()`, `get_posture()` |
| **Contractors** | Service provider management | `find_contractor()`, `request_quote()` |
| **Projects** | Home improvement tracking | `create_project()`, `update_progress()` |
| **Janitor** | System health, code audit | `run_deep_debug()`, `fix_issues()` |

### Agent Teams

Pre-configured collaboration groups:

```python
TEAMS = {
    "finance_review": {
        "members": [FINANCE, JANITOR, MANAGER],
        "mode": "sequential",
        "purpose": "Review transactions and validate data"
    },
    "maintenance_dispatch": {
        "members": [MAINTENANCE, CONTRACTORS, MANAGER],
        "mode": "parallel",
        "purpose": "Handle repairs, coordinate work"
    },
    # ... etc
}
```

### Agent Scheduler

Cron-like scheduling for agent runs:

```python
scheduler.create_job(
    name="Daily Finance Review",
    agent="finance",
    task="Review yesterday's transactions...",
    frequency=ScheduleFrequency.DAILY,
    hour=8,
    minute=0
)
```

## Data Flow

### Request Flow

```
User Request
     │
     ▼
┌─────────────┐
│  Frontend   │ ─────────────────────────────┐
└──────┬──────┘                              │
       │ HTTP/WebSocket                      │
       ▼                                     │
┌─────────────┐      ┌─────────────┐        │
│   FastAPI   │ ───▶ │   Manager   │        │
│   Backend   │      │   Agent     │        │
└──────┬──────┘      └──────┬──────┘        │
       │                    │               │
       │              Delegate              │
       │                    │               │
       │              ┌─────┴─────┐         │
       │              ▼           ▼         │
       │         ┌────────┐  ┌────────┐    │
       │         │Finance │  │Maint.  │    │
       │         │Agent   │  │Agent   │    │
       │         └───┬────┘  └───┬────┘    │
       │             │           │          │
       │             ▼           ▼          │
       │        ┌─────────────────────┐    │
       │        │    SecondBrain      │    │
       │        │  (Knowledge Vault)  │    │
       │        └─────────────────────┘    │
       │                                    │
       ▼                                    │
┌─────────────┐                            │
│ PostgreSQL  │ ◀──────────────────────────┘
│ (State)     │     Real-time updates
└─────────────┘
```

### SecondBrain Flow

```
Agent Action
     │
     ▼
┌─────────────────────┐
│ write_to_secondbrain│
│ record_decision     │
│ record_event        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Markdown Note     │
│   with YAML front-  │
│   matter            │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  ~/moltbot/vaults/  │
│  tenkiang_household/│
│  secondbrain/       │
│  └── memory/        │
│  └── decisions/     │
│  └── entities/      │
│  └── ...            │
└─────────────────────┘
```

## Security Architecture

### Trust Zones

```
┌─────────────────────────────────────────────────┐
│ ZONE A-OWNER: +12677180107 (Lamido)             │
│ • Full system access                            │
│ • Can modify workspace files                    │
│ • Can approve changes                           │
├─────────────────────────────────────────────────┤
│ ZONE A-LIMITED: Trusted contacts                │
│ • Conversation access                           │
│ • No workspace changes                          │
│ • No sensitive data access                      │
├─────────────────────────────────────────────────┤
│ ZONE B: Everything else                         │
│ • Treat as passive data                         │
│ • No execution of commands                      │
│ • Injection pattern scanning                    │
└─────────────────────────────────────────────────┘
```

### Prompt Security

```python
from core.prompt_security import (
    classify_source,       # Determine trust zone
    scan_for_injection,    # Detect attack patterns
    evaluate_message_security,  # Full evaluation
    audit_content_for_leaks    # Check outgoing
)
```

## API Design

### Route Groups

| Prefix | Routes | Purpose |
|--------|--------|---------|
| `/api/secondbrain` | 9 | Knowledge vault CRUD |
| `/api/scheduler` | 14 | Job scheduling |
| `/api/chat` | 7 | Agent conversation |
| `/api/connectors` | 5 | Integration marketplace |
| `/api/system` | 2 | Live status |
| `/api/settings` | 13 | Configuration + wizard |
| `/api/finance` | 14 | Portfolio management |
| `/api/inbox` | 6 | Unified messages |
| `/api/tasks` | 5 | Task CRUD |
| `/api/telemetry` | 6 | Metrics |

### Error Handling

Standardized error responses with correlation IDs:

```json
{
  "error": "Not Found",
  "message": "Note not found: sb_12345",
  "correlation_id": "abc123",
  "status_code": 404
}
```

## Frontend Architecture

### Tech Stack

- **Framework:** Next.js 14 (App Router)
- **UI Library:** Mantine 7
- **Icons:** Tabler Icons
- **State:** React hooks + fetch
- **Charts:** Mantine Charts

### Page Structure

Each page follows:

```tsx
<Shell>           {/* Navigation shell */}
  <Container>
    <Title />
    <Tabs>        {/* Feature sections */}
      <Tabs.Panel>
        <Card>    {/* Content cards */}
          ...
        </Card>
      </Tabs.Panel>
    </Tabs>
  </Container>
</Shell>
```

## Deployment

### Development

```bash
# Backend
cd ~/clawd/apps/mycasa-pro
source .venv/bin/activate
uvicorn api.main:app --reload --port 8000

# Frontend
cd frontend
npm run dev
```

### Production

```bash
# Use start.sh
./start.sh
```

### Environment

**Required:**
- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- Anthropic API key

**Optional:**
- Google OAuth (`gog auth login`)
- Clawdbot (WhatsApp messaging)
