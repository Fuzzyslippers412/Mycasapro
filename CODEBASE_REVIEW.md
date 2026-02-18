# MyCasa Pro - Codebase Review
*Generated: 2026-01-30*

## Summary

| Metric | Count |
|--------|-------|
| Python files | 155 |
| TSX files | 44 |
| TS files | 8 |
| Database tables | 23 |
| API routes | 21 |
| Agent classes | 15 |

## Architecture

```
MyCasa Pro
├── api/                    # FastAPI backend
│   ├── routes/             # 21 route modules
│   ├── schemas/            # Pydantic models
│   └── middleware/         # Error handlers
├── agents/                 # Agent implementations
│   ├── manager.py          # Main orchestrator (48KB)
│   ├── finance.py          # Finance agent (71KB)
│   ├── janitor.py          # System health (59KB)
│   ├── janitor_debugger.py # HTML report gen (85KB)
│   ├── maintenance.py      # Tasks/repairs
│   ├── contractors.py      # Service providers
│   ├── projects.py         # Home improvements
│   ├── security_manager.py # Security monitoring
│   └── base.py             # Base agent class
├── core/                   # Core systems
│   ├── lifecycle.py        # System start/stop
│   ├── events_v2.py        # Event bus
│   ├── shared_context.py   # Clawdbot sync
│   └── llm.py              # Venice AI integration
├── database/               # SQLAlchemy models
│   └── models.py           # 23 tables
├── frontend/               # Next.js 16 + Mantine
│   └── src/app/            # 11 pages
├── backend/edgelab/        # Financial prediction system
│   ├── adapters/           # Data sources (yfinance)
│   ├── pipelines/          # Analysis pipelines
│   └── db/                 # Postgres models (not SQLite compatible)
└── config/                 # Settings & portfolio config
```

## Working Features ✅

### Backend
- **Health endpoint**: `/health` - 200 OK
- **System monitor**: `/system/monitor` - Shows 8/9 agents
- **Chat with LLM**: `/api/chat/send` - Venice AI with 6 agent personas
- **Tasks API**: `/api/tasks` - CRUD operations
- **Janitor**: `/api/janitor/status` - Health monitoring
- **Finance**: `/api/finance/portfolio` - Portfolio tracking (empty until user adds holdings)
- **Settings**: `/api/settings/*` - System configuration
- **Connectors**: Gmail OAuth2, WhatsApp (via wacli)

### Frontend
- **Dashboard**: Main overview with stats
- **Customizable Dashboard**: `/dashboard` - Drag-and-drop widgets (NEW)
- **System page**: Agent status, controls
- **Settings**: Multi-tab configuration
- **Finance**: Portfolio view
- **Inbox**: Message management
- **Contractors**: Service provider directory
- **Maintenance**: Task management

### Agents with LLM Personas
1. **Galidima** (Manager) - Wise, uses West African proverbs
2. **Mamadou** (Finance) - Precise with numbers
3. **Ousmane** (Maintenance) - Practical, hands-on
4. **Aïcha** (Security) - Vigilant, calm
5. **Malik** (Contractors) - Personable
6. **Zainab** (Projects) - Organized, enthusiastic

## Partial/Not Working ⚠️

### EdgeLab (Financial Prediction)
- **Issue**: Uses PostgreSQL-specific features (schemas, UUID, JSONB)
- **Status**: Not working with SQLite
- **Workaround**: Simplified analysis methods added to Finance agent using yfinance directly

### SecondBrain
- **Status**: Routes exist but vault not initialized
- **Endpoint**: `/api/secondbrain/status` returns 404

### Connectors
- **Gmail**: OAuth2 configured but needs user auth
- **WhatsApp**: Depends on wacli external tool

## Database Schema (23 tables)

| Table | Purpose |
|-------|---------|
| Contractor | Service provider info |
| MaintenanceTask | Home maintenance tasks |
| Project | Home improvement projects |
| ProjectMilestone | Project milestones |
| ContractorJob | Jobs assigned to contractors |
| HomeReading | Sensor readings (water, HVAC) |
| Bill | Bills and payments |
| Transaction | Financial transactions |
| Budget | Budget allocations |
| SpendEntry | Spending tracking |
| SpendingBaseline | Baseline spend data |
| FinanceManagerSettings | Finance config |
| IncomeSource | Income sources |
| SystemCostEntry | API cost tracking |
| SpendGuardrailAlert | Spend alerts |
| InboxMessage | Messages |
| AgentLog | Agent activity logs |
| ScheduledJob | Cron-like jobs |
| Notification | User notifications |
| PortfolioHolding | Stock holdings |
| CashHolding | Cash positions |
| TelemetryEvent | Usage telemetry |
| EventLog | System events |

## Janitor Debugger

The Janitor has a comprehensive debugger that:
- Scans Python syntax
- Checks imports
- Validates API routes
- Checks database integrity
- Verifies spec compliance
- **Generates interactive HTML reports** ✅

Latest audit: 65 findings (0 critical, 4 high)

## File Sizes (Largest)

| File | Size | Purpose |
|------|------|---------|
| janitor_debugger.py | 85KB | HTML report generator |
| finance.py | 71KB | Finance agent |
| janitor.py | 59KB | Janitor agent |
| manager.py | 48KB | Manager orchestrator |
| settings/page.tsx | 41KB | Settings UI |
| contractors.py | 41KB | Contractors agent |
| system/page.tsx | 33KB | System UI |
| coordinator.py | 35KB | Agent coordination |
| chat.py | 30KB | Chat API routes |

## What's Needed

1. **EdgeLab**: Convert to SQLite or keep as separate Postgres service
2. **SecondBrain**: Initialize vault and connect
3. **Gmail**: Complete OAuth flow
4. **Portfolio**: User needs to add holdings via Finance agent
5. **Testing**: No test coverage currently

## Running the App

```bash
# Backend
cd /path/to/mycasa-pro
source .venv/bin/activate
export VENICE_API_KEY=...
uvicorn api.main:app --port 8000

# Frontend
cd frontend
npm run dev
```

URLs:
- Backend: http://localhost:8000
- Frontend: http://localhost:3000
- Customizable Dashboard: http://localhost:3000/dashboard
