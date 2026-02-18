# MyCasa Pro - Feature Documentation

**Last Updated:** 2026-01-29
**Version:** 1.0.0

## Overview

MyCasa Pro is an AI-driven home operating system with 8 specialized agents, a SecondBrain knowledge vault, and comprehensive home management capabilities.

---

## Core Features

### 1. Agent System

#### Manager Agent (Galidima)
The central orchestrator that routes tasks to specialists.

**Capabilities:**
- Natural language command processing
- Agent delegation and coordination
- Status reporting (quick and full)
- WhatsApp messaging integration
- Shared context with main Clawdbot instance

**API Endpoints:**
- `GET /status` - Quick status
- `GET /status/full` - Full system report
- `POST /api/chat/send` - Chat with manager

#### Agent Teams
Pre-configured agent groups for complex tasks.

**Teams:**
| Team | Members | Purpose |
|------|---------|---------|
| finance_review | Finance + Janitor | Review transactions, validate data |
| maintenance_dispatch | Maintenance + Contractors | Handle repairs, coordinate work |
| security_response | Security + Manager | Respond to security events |
| project_planning | Projects + Finance | Plan and budget projects |
| daily_operations | All specialists | Daily household operations |

**Collaboration Modes:**
- `parallel` - All agents work simultaneously
- `sequential` - Agents work in order
- `consensus` - Agents must agree on response

**Location:** `agents/teams.py`

---

### 2. SecondBrain Integration

Obsidian-compatible knowledge vault at `$MYCASA_DATA_DIR/vaults/tenkiang_household/secondbrain/`

#### Vault Structure
```
secondbrain/
├── inbox/          # Unprocessed notes
├── memory/         # Event logs, daily notes
├── decisions/      # Decision records
├── entities/       # People, places, things
├── finance/        # Financial data
├── maintenance/    # Maintenance records
├── contractors/    # Contractor info
├── projects/       # Project tracking
├── logs/           # System logs
└── documents/      # Uploaded documents
```

#### Note Format
```yaml
---
id: sb_20260129123456_abc123
type: decision
title: Example Note
created_at: 2026-01-29T12:34:56
agent: manager
tags: [example, documentation]
---

Note content here...
```

#### API Endpoints
- `GET /api/secondbrain/notes` - List notes (filter by folder/type)
- `GET /api/secondbrain/notes/{id}` - Get specific note
- `POST /api/secondbrain/notes` - Create note
- `POST /api/secondbrain/upload` - Upload document (PDF/DOCX/TXT/MD)
- `GET /api/secondbrain/graph` - Knowledge graph for visualization
- `GET /api/secondbrain/graph/{id}` - Note connections
- `GET /api/secondbrain/stats` - Vault statistics
- `GET /api/secondbrain/search?q=` - Text search

**Location:** `core/secondbrain/skill.py`, `api/routes/secondbrain.py`

---

### 3. Agent Scheduler

Schedule agents to run automatically.

#### Frequencies
- `once` - Run once at specified time
- `hourly` - Every hour at specified minute
- `daily` - Daily at specified time
- `weekly` - Weekly on specified day/time
- `monthly` - Monthly on specified day/time

#### Job Templates
| Template | Agent | Schedule | Purpose |
|----------|-------|----------|---------|
| daily_finance_review | finance | 8:00 AM daily | Review transactions |
| weekly_maintenance_check | maintenance | Monday 9:00 AM | Check tasks |
| daily_security_audit | security | 7:30 AM daily | Audit events |
| monthly_portfolio_review | finance | 1st of month 10:00 AM | Portfolio analysis |
| weekly_contractor_followup | contractors | Friday 10:00 AM | Check pending work |

#### API Endpoints
- `GET /api/scheduler/status` - Scheduler status
- `GET /api/scheduler/jobs` - List jobs
- `POST /api/scheduler/jobs` - Create job
- `PUT /api/scheduler/jobs/{id}` - Update job
- `DELETE /api/scheduler/jobs/{id}` - Delete job
- `POST /api/scheduler/jobs/{id}/run` - Run immediately
- `POST /api/scheduler/jobs/{id}/enable` - Enable job
- `POST /api/scheduler/jobs/{id}/disable` - Disable job
- `GET /api/scheduler/history` - Run history
- `GET /api/scheduler/templates` - Job templates
- `POST /api/scheduler/templates/{id}/create` - Create from template

**Location:** `agents/scheduler.py`, `api/routes/scheduler.py`

---

### 4. Chat Interface

Real-time chat with the Manager agent.

#### Features
- Persistent conversation history
- Quick action badges for common commands
- Reasoning display (shows why agent made decisions)
- Auto-scroll, loading states
- WhatsApp message sending from chat

#### Commands
| Command | Action |
|---------|--------|
| "What's going on?" | Quick status |
| "Full report" | Detailed system report |
| "Send WhatsApp to [name]..." | Send message |
| "List contacts" | Show contact directory |
| "Show pending tasks" | List tasks |
| "Help" | Command reference |

#### Reasoning Display
Each response includes a collapsible "How I decided this" section showing:
- Message received
- Context loaded
- Intent detected
- Action taken
- Result generated

**Location:** `api/routes/chat.py`, `frontend/src/app/chat/page.tsx`

---

### 5. Connector System

Standardized integrations with external services.

#### Available Connectors
| Connector | Category | Status |
|-----------|----------|--------|
| WhatsApp | messaging | ✅ Connected |
| Gmail | email | 🔧 Installed |
| Google Calendar | calendar | 🔧 Installed |
| Bank Import | finance | ❌ Not installed |
| Apple Notes | messaging | ✅ Connected |
| Home Assistant | smart_home | ❌ Not installed |
| Ring Doorbell | security | ❌ Not installed |

#### Connector Marketplace
Browse, configure, and test connectors from the UI.

**API Endpoints:**
- `GET /api/connectors/marketplace` - List all connectors
- `GET /api/connectors/marketplace/{id}` - Get connector details
- `POST /api/connectors/marketplace/{id}/configure` - Configure
- `POST /api/connectors/marketplace/{id}/test` - Test connection
- `GET /api/connectors/health` - Health check all

**Location:** `connectors/`, `api/routes/connectors.py`

---

### 6. Memory Graph Visualization

Interactive force-directed graph of SecondBrain knowledge.

#### Features
- Force-directed layout using react-force-graph-2d
- Color-coded nodes by type
- Click to view note details
- Zoom, pan, fit-to-view controls
- Filter by type, folder, or search
- Toggle between graph and list view
- Legend showing node type colors

#### Node Colors
| Type | Color |
|------|-------|
| decision | Blue |
| event | Green |
| entity | Yellow |
| policy | Purple |
| task | Orange |
| message | Teal |
| telemetry | Gray |
| document | Pink |

**Location:** `frontend/src/components/MemoryGraph/`

---

### 7. Live System Dashboard

Real-time overview of all systems.

#### Sections
- Agents (active, available, loaded)
- SecondBrain (note count by folder)
- Connectors (health status)
- Chat sessions (count, messages)
- Shared context (sources, chars)
- Memory files (core files, daily memory)
- Scheduled jobs

**Location:** `api/routes/system_live.py`, `frontend/src/components/LiveSystemDashboard/`

---

### 8. Setup Wizard

6-step onboarding flow for new users.

#### Steps
1. **Welcome** - Tenant name, locale
2. **Income Source** - Primary income, frequency
3. **Budgets** - Monthly budget categories
4. **Connectors** - Enable integrations
5. **Notifications** - Alert preferences
6. **Complete** - Summary and launch

**Location:** `api/routes/settings.py`, `frontend/src/components/SetupWizard/`

---

### 9. Portfolio Management

Track investment holdings.

#### Features
- Add/edit/delete holdings
- Real-time price lookup
- Asset type categorization
- Cash reserve tracking
- Portfolio value breakdown
- Allocation percentages

**API Endpoints:**
- `GET /portfolio` - Get portfolio
- `POST /portfolio/holdings` - Add/update holding
- `DELETE /portfolio/holdings/{ticker}` - Remove holding
- `PUT /portfolio/cash` - Update cash
- `DELETE /portfolio/clear` - Clear all

**Location:** `api/main.py` (inline routes)

---

### 10. Security Features

#### Prompt Security
- Source classification (Owner/Trusted/Untrusted)
- Injection pattern detection
- Content leak auditing
- Action gating by trust level

#### Janitor Debugger
- Code audit (104+ files)
- Import validation
- Spec compliance checks
- Enum type handling
- Frontend/backend sync

**Location:** `core/prompt_security.py`, `agents/janitor_debugger.py`

---

## Frontend Pages

| Page | Path | Description |
|------|------|-------------|
| Dashboard | `/` | System overview |
| Chat | `/chat` | Talk to Manager |
| Finance | `/finance` | Portfolio, budgets |
| Maintenance | `/maintenance` | Tasks, scheduling |
| Contractors | `/contractors` | Service providers |
| Projects | `/projects` | Home improvements |
| Security | `/security` | Incidents, monitoring |
| Inbox | `/inbox` | Unified messages |
| Logs | `/logs` | System logs |
| Settings | `/settings` | Configuration |
| System | `/system` | Live status, scheduler |

---

## API Route Count

**Total: 139 routes**

| Category | Routes |
|----------|--------|
| SecondBrain | 7 |
| Settings | 12 |
| Messaging | 5 |
| Chat | 4 |
| System Live | 2 |
| Connectors | 5 |
| Finance | 8 |
| Inbox | 6 |
| Tasks | 5 |
| Telemetry | 6 |
| Scheduler | 14 |
| Core (status, portfolio, etc.) | 65 |

---

## Quick Start

```bash
# Backend
cd /path/to/mycasa-pro
source .venv/bin/activate
uvicorn api.main:app --reload --port 8000

# Frontend
cd frontend
npm run dev
```

**URLs:**
- Backend: http://localhost:8000
- Frontend: http://localhost:3000
- API Docs: http://localhost:8000/docs

---

## Environment Requirements

**Minimum:**
- Python 3.11+
- Node.js 18+
- Anthropic API key

**Full Features:**
- Google OAuth via `gog auth login`
- WhatsApp via Clawdbot gateway
- pdfplumber, python-docx for document upload
