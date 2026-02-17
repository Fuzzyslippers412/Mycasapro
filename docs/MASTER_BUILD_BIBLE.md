# MyCasa Pro - Master Build Bible

> **Last Updated:** 2026-01-28  
> **Status:** Production-ready development  
> **Purpose:** Complete reference for how this app is built - never forget, never bitch

---

## 🎯 WHAT THIS APP IS

**MyCasa Pro** is an AI-Driven Home Operating System, packaged as an installable Clawdbot skill.

**Core Features:**
- Dashboard with system status
- Inbox aggregation (Gmail + WhatsApp)
- Maintenance task management
- Finance tracking (transactions, budgets, bills)
- Contractor job management
- Project tracking
- Security monitoring
- Full audit logging

**The Manager Chat has FULL CLAWDBOT POWER** - same as terminal.

---

## 🏗️ ARCHITECTURE OVERVIEW

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                 │
│   Next.js 16 + React 19 + Mantine 8 + TypeScript                │
│   Port: 3000                                                     │
│   Location: frontend/                                            │
├─────────────────────────────────────────────────────────────────┤
│                         BACKEND API                              │
│   FastAPI + SQLAlchemy + SQLite                                 │
│   Port: 8000                                                     │
│   Location: backend/api/main.py                                  │
├─────────────────────────────────────────────────────────────────┤
│                       CLAWDBOT RUNNER                            │
│   Subprocess execution of clawdbot CLI                          │
│   Location: backend/core/clawdbot_runner.py                      │
├─────────────────────────────────────────────────────────────────┤
│                         DATABASE                                 │
│   SQLite: data/mycasa_pro.db                                    │
│   Models: backend/storage/models.py                              │
├─────────────────────────────────────────────────────────────────┤
│                        CONNECTORS                                │
│   Gmail (stub) + WhatsApp (wacli)                               │
│   Location: backend/connectors/                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📂 DIRECTORY STRUCTURE

```
mycasa-pro/
├── start.sh                    # Start Streamlit (legacy)
├── start_all.sh                # ✅ START THIS - Backend + Frontend + WhatsApp
├── requirements.txt            # Python dependencies
│
├── backend/                    # ✅ PRIMARY BACKEND
│   ├── api/
│   │   └── main.py             # FastAPI app - ALL endpoints
│   ├── core/
│   │   ├── clawdbot_runner.py  # Execute clawdbot CLI commands
│   │   ├── schemas.py          # Pydantic models
│   │   ├── constants.py        # Budget limits, categories
│   │   └── utils.py            # Helpers
│   ├── storage/
│   │   ├── database.py         # SQLite setup
│   │   ├── models.py           # SQLAlchemy models
│   │   └── repository.py       # Data access layer
│   ├── connectors/
│   │   ├── gmail.py            # Gmail connector (stub)
│   │   └── whatsapp.py         # WhatsApp via wacli
│   └── agents/
│       ├── backup.py           # Backup agent
│       ├── contractor.py       # Contractor agent
│       └── finance.py          # Finance agent
│
├── frontend/                   # ✅ PRIMARY FRONTEND
│   ├── package.json            # npm dependencies
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx      # Root layout + Mantine provider
│   │   │   ├── page.tsx        # Dashboard (/)
│   │   │   ├── inbox/page.tsx  # Inbox
│   │   │   ├── maintenance/page.tsx
│   │   │   ├── finance/page.tsx
│   │   │   ├── contractors/page.tsx
│   │   │   ├── projects/page.tsx
│   │   │   ├── security/page.tsx
│   │   │   ├── logs/page.tsx
│   │   │   └── settings/page.tsx
│   │   ├── components/
│   │   │   ├── layout/Shell.tsx  # App shell with nav
│   │   │   └── widgets/ManagerChat.tsx  # ⭐ MANAGER CHAT
│   │   └── lib/
│   │       ├── api.ts          # API client
│   │       └── hooks.ts        # React hooks
│   └── public/
│       └── favicon.svg
│
├── data/                       # SQLite DB + logs
│   ├── mycasa_pro.db
│   └── logs/
│
├── docs/                       # Documentation
│   ├── MASTER_BUILD_BIBLE.md   # ⭐ THIS FILE
│   ├── ARCHITECTURE.md
│   ├── TERMINAL_TO_WEB_MAPPING.md
│   └── ...
│
├── agents/                     # Legacy agent code (Streamlit version)
│   └── memory/                 # Agent SOUL.md files
│
└── pages/                      # Legacy Streamlit pages
```

---

## 🚀 HOW TO START

### Full Stack (Recommended)
```bash
cd ~/clawd/apps/mycasa-pro
./start_all.sh
```

This starts:
- **Backend API** on http://localhost:8000
- **Frontend UI** on http://localhost:3000  
- **WhatsApp sync** (if wacli available)

### Just Backend
```bash
cd ~/clawd/apps/mycasa-pro
source venv/bin/activate
python -m uvicorn backend.api.main:app --reload --port 8000
```

### Just Frontend
```bash
cd ~/clawd/apps/mycasa-pro/frontend
npm run dev
```

### Legacy Streamlit (Old)
```bash
cd ~/clawd/apps/mycasa-pro
./start.sh
```

---

## 📡 API ENDPOINTS

**Base URL:** http://localhost:8000

### Health & Status
```
GET  /health              - Health check
GET  /status              - Full system status
```

### Intake (First-Run Setup)
```
GET  /intake              - Get intake status
POST /intake              - Complete intake
```

### Tasks
```
GET  /tasks               - List tasks (status, category, limit)
POST /tasks               - Create task
PATCH /tasks/{id}         - Update task
PATCH /tasks/{id}/complete - Complete task
```

### Transactions
```
GET  /transactions        - List transactions
POST /transactions/ingest - Bulk ingest
GET  /transactions/summary - Spending summary
```

### Contractor Jobs
```
GET  /jobs                - List jobs
POST /jobs                - Create job
PATCH /jobs/{id}/schedule - Schedule job
PATCH /jobs/{id}/approve-cost - Approve cost
PATCH /jobs/{id}/complete - Complete job
```

### Inbox
```
GET  /inbox/messages      - Get messages
GET  /inbox/unread-count  - Unread counts
PATCH /inbox/messages/{id}/read - Mark read
POST /inbox/ingest        - Sync inbox
POST /inbox/launch        - Launch sync + report
POST /inbox/stop          - Stop periodic sync
```

### Manager Chat (⭐ FULL CLAWDBOT POWER)
```
GET  /manager/messages    - Get system messages
POST /manager/messages/ack - Acknowledge messages
POST /manager/chat        - Send message (HTTP)
WS   /manager/ws          - WebSocket streaming
GET  /manager/commands    - List available commands
GET  /manager/status      - Execution status
```

### Settings
```
GET  /settings/{manager}  - Get manager settings
PUT  /settings/{manager}  - Update settings
```

### Cost
```
POST /cost                - Record cost
GET  /cost                - Get summary (today, month, all)
GET  /cost/budget         - Budget status
```

### Backup
```
POST /backup/export       - Export backup
POST /backup/restore      - Restore backup
GET  /backup/list         - List backups
```

### Events
```
GET  /events              - List events (audit log)
```

---

## 💾 DATABASE MODELS

**Location:** `backend/storage/models.py`

| Table | Purpose |
|-------|---------|
| `user_settings` | Global user settings |
| `manager_settings` | Per-manager config |
| `budget_policies` | Budget limits (monthly, daily, system) |
| `income_sources` | Income source tracking |
| `transactions` | Financial transactions |
| `tasks` | Task management |
| `contractor_jobs` | Contractor job tracking |
| `events` | Audit log |
| `cost_records` | AI/system cost tracking |
| `inbox_messages` | Aggregated inbox |
| `approvals` | Cost/action approvals |
| `backup_records` | Backup history |

---

## 🧠 MANAGER CHAT - FULL POWER

The Manager Chat widget (`frontend/src/components/widgets/ManagerChat.tsx`) has **FULL CLAWDBOT TERMINAL POWER**.

### How It Works

```
User types message
       │
       ├─ Starts with "/" → Raw CLI command
       │     "/status" → clawdbot status
       │     "/cron list" → clawdbot cron list
       │
       └─ Natural language → Agent execution
             "Check my inbox" → clawdbot agent -m "..."
```

### Backend Flow

```python
# backend/core/clawdbot_runner.py

ClawdbotRunner.run_message(message, context)
    │
    ├─ Builds command: clawdbot agent -m "message" --session-id main
    │
    └─ subprocess.Popen() → streams stdout/stderr → yields events
```

### API Endpoints

```
POST /manager/chat        # HTTP - returns full response
WS   /manager/ws          # WebSocket - streams in real-time
```

### Commands Available

**Natural language:**
- "Check my inbox"
- "What's the weather?"
- "Send WhatsApp to Erika saying hi"
- "Create a task to fix the roof"

**Raw commands (prefix with /):**
- `/status` - System status
- `/sessions` - List sessions
- `/health` - Gateway health
- `/cron list` - List cron jobs
- `/skills list` - List skills
- `/browser tabs` - Browser tabs
- `/message send --to '+1234' --message 'test'`

---

## 🎨 FRONTEND TECH STACK

| Tech | Version | Purpose |
|------|---------|---------|
| Next.js | 16.1.6 | React framework |
| React | 19.2.3 | UI library |
| Mantine | 8.3.13 | Component library |
| TypeScript | 5.x | Type safety |
| Tabler Icons | 3.36.1 | Icons |

### Theme
```typescript
// frontend/src/app/layout.tsx
const theme = createTheme({
  primaryColor: "indigo",
  fontFamily: "Inter, -apple-system, BlinkMacSystemFont, sans-serif",
  defaultRadius: "md",
  // Dark mode colors defined
});
```

### Layout Structure
```
layout.tsx (MantineProvider)
  └── Shell.tsx (AppShell with nav)
        └── page.tsx (Page content)
        └── ManagerChat.tsx (Floating widget)
```

---

## 🐍 BACKEND TECH STACK

| Tech | Version | Purpose |
|------|---------|---------|
| FastAPI | latest | API framework |
| SQLAlchemy | 2.0+ | ORM |
| SQLite | - | Database |
| Pydantic | 2.x | Data validation |
| uvicorn | - | ASGI server |

### Virtual Environment
```bash
# Location
mycasa-pro/venv/

# Activate
source venv/bin/activate

# Install deps
pip install -r requirements.txt
```

### Python Dependencies
```
streamlit>=1.31.0      # Legacy Streamlit UI
pandas>=2.0.0
plotly>=5.18.0
sqlalchemy>=2.0.0
apscheduler>=3.10.0
requests>=2.31.0
python-dateutil>=2.8.0
pyyaml>=6.0
aiohttp>=3.9.0
yfinance>=0.2.36       # Stock data
```

**Backend-specific (in backend/requirements.txt):**
```
fastapi
uvicorn[standard]
pydantic
sqlalchemy
```

---

## 🔄 DATA FLOW

### Inbox Sync Flow
```
User clicks "Launch" in Settings
       │
       ▼
POST /inbox/launch
       │
       ├─ Clear existing messages (fresh start)
       │
       ├─ Gmail: Fetch unread from last 7 days
       │
       ├─ WhatsApp: Fetch from whitelisted contacts
       │
       ├─ Store in inbox_messages table
       │
       └─ Queue report to Manager Chat
```

### Manager Chat Flow
```
User types in ManagerChat
       │
       ├─ WebSocket connected?
       │     │
       │     ├─ Yes → Send via WS → Stream events back
       │     │
       │     └─ No → POST /manager/chat → Get full response
       │
       ▼
ClawdbotRunner executes command
       │
       ├─ Natural language → clawdbot agent -m "..."
       │
       └─ /command → clawdbot <command>
```

### Cost Tracking Flow
```
AI operation runs
       │
       ▼
POST /cost (tokens, model, estimated cost)
       │
       ├─ Store in cost_records
       │
       └─ Check budget warnings → return in response
```

---

## 🔐 BUDGET GUARDRAILS

**Default Limits (from constants.py):**
```python
BUDGET_LIMITS = {
    "monthly_spend": 10000.0,    # $10k/month spending
    "daily_spend": 150.0,        # $150/day spending
    "system_cost": 1000.0,       # $1k/month AI costs
}
```

**Warning Thresholds:**
- 70% - First warning
- 85% - Second warning  
- 100% - Block (if hard cap enabled)

---

## 📝 AGENTS (Legacy)

The `agents/` directory contains agent SOUL.md files:

| Agent | Location | Purpose |
|-------|----------|---------|
| Manager | `agents/memory/manager/SOUL.md` | Orchestrates all |
| Finance | `agents/memory/finance/SOUL.md` | Money management |
| Maintenance | `agents/memory/maintenance/SOUL.md` | Home upkeep |
| Janitor | `agents/memory/janitor/SOUL.md` | Cost aggregation |
| Contractors | `agents/memory/contractors/SOUL.md` | Job coordination |
| Projects | `agents/memory/projects/SOUL.md` | Project tracking |
| Security | `agents/memory/security-manager/SOUL.md` | Security |
| Backup | `agents/memory/backup-recovery/SOUL.md` | Backups |

**Note:** These are persona definitions. The actual execution happens via Clawdbot through the Manager Chat.

---

## 🧪 TESTING

### Test Backend API
```bash
cd ~/clawd/apps/mycasa-pro
source venv/bin/activate
python -c "
from backend.api.main import app
print('Routes:', [r.path for r in app.routes][:10])
"
```

### Test Clawdbot Runner
```bash
cd ~/clawd/apps/mycasa-pro
source venv/bin/activate
python3 << 'EOF'
import asyncio
from backend.core.clawdbot_runner import run_clawdbot_command

async def test():
    result = await run_clawdbot_command("status")
    print(f"Exit code: {result['exit_code']}")
    print(f"Output: {result['stdout'][:200]}")

asyncio.run(test())
EOF
```

### Test Frontend
```bash
cd ~/clawd/apps/mycasa-pro/frontend
npm run build  # Should complete without errors
```

---

## 🐛 TROUBLESHOOTING

### Backend won't start
```bash
# Check if port is in use
lsof -i :8000

# Kill existing process
pkill -f "uvicorn.*backend.api.main"

# Check logs
tail -f /tmp/mycasa-api.log
```

### Frontend won't start
```bash
# Check if port is in use
lsof -i :3000

# Reinstall deps
cd frontend && rm -rf node_modules && npm install

# Check logs
tail -f /tmp/mycasa-frontend.log
```

### Manager Chat not working
1. Check if backend is running: `curl http://localhost:8000/health`
2. Check WebSocket: Browser DevTools → Network → WS
3. Check Clawdbot: `clawdbot status`

### Database issues
```bash
# Reset database
rm data/mycasa_pro.db
python3 seed_data.py
```

---

## 🔗 RELATED FILES

| Purpose | Location |
|---------|----------|
| Architecture overview | `ARCHITECTURE.md` |
| Terminal mapping | `docs/TERMINAL_TO_WEB_MAPPING.md` |
| API spec | `docs/API_ARCHITECTURE.md` |
| UI spec | `docs/UI_BUILD_SPEC.md` |
| Agent coordination | `docs/AGENT_COORDINATION.md` |
| Design decisions | `docs/DESIGN_DECISIONS.md` |
| Skill manifest | `SKILL.md` |
| Runbook | `RUNBOOK.md` |

---

## ✅ QUICK REFERENCE

```bash
# Start everything
cd ~/clawd/apps/mycasa-pro && ./start_all.sh

# URLs
# Frontend: http://localhost:3000
# Backend:  http://localhost:8000
# API Docs: http://localhost:8000/docs

# Stop everything
pkill -f 'uvicorn|next dev|wacli sync'

# Check status
curl http://localhost:8000/health

# View logs
tail -f /tmp/mycasa-api.log
tail -f /tmp/mycasa-frontend.log
```

---

**Remember:** The Manager Chat has FULL CLAWDBOT POWER. Same as terminal. Never forget.

---

## NEW FEATURES (Claude Code Update - 2026-01-28)

### 1. Command Palette (`Cmd+K`)
- **File:** `frontend/src/components/CommandPalette/CommandPalette.tsx`
- Uses `@mantine/spotlight` for spotlight-style search
- Navigation shortcuts to all pages
- Quick actions: backup export, sync inbox, view approvals
- Keyboard-first workflow

### 2. System Monitor (`/system` page)
- **Files:** 
  - Page: `frontend/src/app/system/page.tsx`
  - Component: `frontend/src/components/SystemMonitor/SystemMonitor.tsx`
  - Backend: `backend/api/system_routes.py`
- Features:
  - htop-style process table
  - CPU/Memory usage progress bars
  - Per-agent Start/Stop/Restart buttons
  - Live cost tracking
  - Auto-refresh every 5 seconds

### 3. System Console (Bottom Dock)
- **File:** `frontend/src/components/SystemConsole.tsx`
- Always-visible status bar showing:
  - Active agents count
  - Pending tasks count
  - Today's cost
- Press **`** (backtick) to focus
- Press **Escape** to minimize
- Full Manager Chat power in terminal-style UI
- Replaces floating widget as primary interface

### 4. Approval Queue (`/approvals` page)
- **Files:**
  - Page: `frontend/src/app/approvals/page.tsx`
  - Component: `frontend/src/components/ApprovalQueue/ApprovalQueue.tsx`
  - Backend: `backend/api/approval_routes.py`
- Features:
  - Budget status bar with progress
  - Budget impact preview before approval
  - Red warning if approval exceeds budget
  - Approve/Deny with loading states
  - Expandable details per request

### 5. Launch Screen
- **File:** `frontend/src/components/LaunchScreen.tsx`
- Shows on first page load (uses sessionStorage)
- Checks backend connectivity
- Animated progress bar
- "Continue Anyway" button if backend offline
- Routes to Settings after launch

### 6. Enhanced Log Viewer (`/logs` page)
- **Files:**
  - Page: `frontend/src/app/logs/page.tsx`
  - Component: `frontend/src/components/LogViewer/LogViewer.tsx`
- journalctl-style interface
- Filters: level, agent, search query
- Auto-scroll toggle
- Export to text file
- Permanent logs (cannot clear - audit requirement)

### 7. Custom Logo
- **File:** `frontend/src/components/MyCasaLogo.tsx`
- SVG house icon with indigo-violet gradient
- Used in header and launch screen

### 8. New Backend Routes

**System Control (`/system/...`):**
```
GET  /system/monitor           - htop-style data
POST /agents/{id}/start        - Start agent
POST /agents/{id}/stop         - Stop agent
POST /agents/{id}/restart      - Restart agent
GET  /agents/{id}/status       - Detailed status
```

**Approvals (`/approvals/...`):**
```
GET  /approvals/pending        - Pending approvals
POST /approvals/{id}/approve   - Grant approval
POST /approvals/{id}/deny      - Deny approval
GET  /approvals/history        - Approval history
```

### 9. Shell Updates
- **File:** `frontend/src/components/layout/Shell.tsx`
- Added "System" nav item
- Integrated CommandPalette (Cmd+K)
- Integrated SystemConsole (bottom dock)
- Launch screen gate
- Real notification count from API
- Increased bottom padding for console

### Keyboard Shortcuts
| Shortcut | Action |
|----------|--------|
| `Cmd+K` / `Ctrl+K` | Open Command Palette |
| `` ` `` (backtick) | Focus System Console |
| `Escape` | Close Console/Palette |
