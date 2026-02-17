# MyCasa Pro - Extensive Codebase Review
**Date:** January 29, 2026  
**Reviewer:** Galidima (AI Assistant)  
**Scope:** Full codebase review with focus on Janitor agent functionality

---

## Executive Summary

MyCasa Pro is a sophisticated AI-driven home operating system with a multi-agent architecture. The codebase demonstrates solid foundations but had gaps in the Janitor agent's integration with CLI and UI. This review documents the existing architecture and the enhancements made to fully integrate the Janitor functionality.

### Changes Made in This Review

1. **API Routes** (`backend/api/routes/janitor.py`) - NEW
   - Full REST API for Janitor operations
   - 12 endpoints for audit, review, cleanup, history, backups, chat, and logs
   
2. **CLI Commands** (`backend/cli/main.py`) - UPDATED
   - Added `mycasa janitor` command group with 8 subcommands
   - status, audit, cleanup, history, backups, logs, review, chat
   
3. **Frontend Page** (`frontend/src/app/janitor/page.tsx`) - NEW
   - Complete UI with 6 tabs: Overview, Audit, Edit History, Backups, Activity Logs, Chat
   - Interactive code review modal
   - Real-time status cards and charts
   
4. **Navigation** (`frontend/src/components/layout/Shell.tsx`) - UPDATED
   - Added Janitor to main navigation

---

## Architecture Overview

### Backend Structure

```
backend/
├── agents/           # AI agent implementations
│   ├── base.py       # BaseAgent class (21KB) - rich activity tracking
│   ├── manager.py    # Galidima - primary orchestrator
│   ├── finance.py    # Mamadou - finance management
│   ├── maintenance.py # Ousmane - home maintenance
│   ├── contractors.py # Contractor management
│   ├── projects.py   # Project tracking
│   ├── security_manager.py # Security agent
│   ├── janitor.py    # Salimata - system health & audits (13KB)
│   ├── coordination.py # Agent coordination system (40KB)
│   └── teams.py      # Team orchestration (25KB)
├── api/
│   ├── main.py       # FastAPI app (116KB) - main API
│   ├── routes/
│   │   ├── chat.py   # Chat API with attachments
│   │   ├── teams.py  # Team management API
│   │   └── janitor.py # NEW: Janitor API routes
│   ├── system_routes.py
│   └── approval_routes.py
├── cli/
│   └── main.py       # Click CLI (15KB) - UPDATED with janitor commands
├── connectors/       # External service integrations
│   ├── gmail.py
│   └── whatsapp.py
├── core/             # Core utilities
│   ├── clawdbot_runner.py # Clawdbot integration
│   ├── schemas.py
│   └── utils.py
└── storage/          # Database layer
    ├── database.py
    ├── models.py
    └── repository.py
```

### Frontend Structure

```
frontend/src/
├── app/
│   ├── page.tsx           # Main dashboard
│   ├── dashboard/         # Customizable dashboard
│   ├── system/           # System management
│   ├── janitor/          # NEW: Janitor page
│   ├── inbox/
│   ├── maintenance/
│   ├── finance/
│   ├── contractors/
│   ├── projects/
│   ├── security/
│   ├── settings/
│   └── logs/
├── components/
│   ├── layout/
│   │   └── Shell.tsx     # Main navigation shell - UPDATED
│   ├── SystemConsole.tsx # Chat interface (40KB)
│   ├── AgentManager/
│   ├── AgentActivityDashboard/
│   ├── LiveSystemDashboard/
│   ├── SchedulerManager/
│   └── ...
```

---

## Agent System Analysis

### BaseAgent (base.py)

**Strengths:**
- Rich activity tracking (files, tools, decisions, questions)
- State persistence to JSON files
- Event subscription/publishing system
- Safe file editing with backups
- HYPERCONTEXT-style activity dashboard support

**Metrics Tracked:**
- Files touched (read/modified)
- Tool usage frequency
- Systems accessed with status
- Decisions made (last 20)
- Open questions (last 10)
- Work threads
- Context usage

### JanitorAgent (janitor.py)

**Responsibilities:**
1. System health audits
2. Code review before edits
3. Safe editing protocol with backups
4. Database cleanup
5. Log rotation
6. Integrity audits

**Audit Checks:**
1. Database connectivity
2. Disk space (warns at <10% free)
3. Agent states (all 5 domain agents)
4. Backup directory health

**Code Review Features:**
- Python syntax validation (compile())
- JSON validation
- Dangerous pattern detection:
  - os.system()
  - eval(), exec()
  - rm -rf
  - DROP TABLE, DELETE FROM
- File size checks (>100KB warning)

### AgentCoordinator (coordination.py - 40KB)

**Key Features:**
- Event-driven communication
- Priority queue (CRITICAL > HIGH > NORMAL > LOW)
- Safe file editing with automatic backups
- Edit history tracking
- Distributed lock management
- Workflow orchestration

**Event Types:**
- TASK_CREATED, TASK_COMPLETED, TASK_FAILED
- ALERT_TRIGGERED, APPROVAL_REQUIRED, APPROVAL_RESOLVED
- BUDGET_WARNING, SPEND_RECORDED
- CONTRACTOR_ASSIGNED, JOB_COMPLETED
- INBOX_MESSAGE, SYSTEM_HEALTH, MAINTENANCE_DUE

### TeamOrchestrator (teams.py - 25KB)

**Team Modes:**
- PARALLEL: All agents work simultaneously
- SEQUENTIAL: Agents work in order
- ADAPTIVE: Dynamic based on complexity
- CONSENSUS: Require agreement

**Preset Teams:**
- home_maintenance_team
- financial_review_team
- emergency_response_team
- project_planning_team
- vendor_negotiation_team
- security_audit_team

---

## API Analysis

### Main API (main.py - 116KB)

The API is comprehensive with endpoints for:
- Health checks and system status
- Task management (CRUD)
- Transaction handling
- Contractor jobs
- Cost tracking and budgets
- Backup/restore
- Inbox sync (Gmail + WhatsApp)
- Portfolio management
- Agent teams
- Chat with attachments

**Background Tasks:**
- Periodic inbox sync (15 min interval, user-enabled)
- Manager message queue

### NEW: Janitor API Routes

```
GET  /api/janitor/status     - Agent status and metrics
GET  /api/janitor/audit      - Run system health audit
POST /api/janitor/review     - Code review for proposed changes
POST /api/janitor/safe-edit  - Edit file with review and backup
POST /api/janitor/cleanup    - Remove old backup files
GET  /api/janitor/history    - Recent file edit history
GET  /api/janitor/logs       - Agent activity logs
GET  /api/janitor/activity   - Rich activity for dashboard
POST /api/janitor/chat       - Chat with Salimata
GET  /api/janitor/backups    - List backup files
DELETE /api/janitor/backups/{filename} - Delete specific backup
POST /api/janitor/restore/{filename}   - Restore from backup
```

---

## CLI Analysis

### Existing Commands

```
mycasa backend [start|stop|status]  # Backend management
mycasa ui [start|stop]              # Frontend management
mycasa intake                       # System setup
mycasa tasks [list|create|complete] # Task management
mycasa transactions [list|summary]  # Transaction tracking
mycasa jobs [list|create]           # Contractor jobs
mycasa cost [summary|budget]        # Cost tracking
mycasa backup [export|restore|list] # Backup management
mycasa events                       # Show recent events
mycasa status                       # Full system status
```

### NEW: Janitor Commands

```
mycasa janitor status    # Show Janitor agent status
mycasa janitor audit     # Run comprehensive system audit
mycasa janitor cleanup   # Clean old backups (--days=7)
mycasa janitor history   # Show edit history (--limit=20)
mycasa janitor backups   # List backup files (--limit=20)
mycasa janitor logs      # Show activity logs (--limit=20)
mycasa janitor review    # Review code change before applying
mycasa janitor chat      # Chat with Salimata
```

---

## Frontend Analysis

### Navigation Structure

Main Shell with sidebar navigation:
1. Dashboard (/)
2. Customize (/dashboard) - NEW badge
3. System (/system)
4. **Janitor (/janitor)** - NEW
5. Inbox (/inbox)
6. Maintenance (/maintenance)
7. Finance (/finance)
8. Contractors (/contractors)
9. Projects (/projects)
10. Security (/security)
11. Logs (/logs)

### System Console (SystemConsole.tsx - 40KB)

**Features:**
- Persistent chat interface at bottom of screen
- Message history with persistence
- Markdown rendering
- Typing indicators
- Expandable/collapsible
- Dark theme integration

### NEW: Janitor Page

**6 Tabs:**

1. **Overview**
   - Status cards (Agent Status, System Health, Findings, Recent Edits)
   - Quick actions (Run Audit, Cleanup, Code Review)
   - Last audit summary with ring progress chart

2. **Audit**
   - Full audit interface
   - Health score with progress bar
   - Findings table with severity badges

3. **Edit History**
   - Table of recent file edits
   - Success/failure status
   - Agent attribution

4. **Backups**
   - List all backup files
   - Size and date info
   - Delete individual backups
   - Bulk cleanup action

5. **Activity Logs**
   - Timeline view of agent activity
   - Status-colored bullets
   - Action details

6. **Chat**
   - Direct conversation with Salimata
   - Supports: "run audit", "cleanup", "show edit history"
   - Chat history persistence

---

## Code Quality Assessment

### Strengths

1. **Well-structured agent hierarchy** - BaseAgent provides excellent foundation
2. **Rich activity tracking** - HYPERCONTEXT-style monitoring
3. **Safe editing system** - Automatic backups, validation, rollback
4. **Event-driven architecture** - Decoupled agent communication
5. **Type safety** - Pydantic models throughout API
6. **Modern frontend** - Mantine UI, good component organization

### Areas for Improvement

1. **Test coverage** - No test files found in review
2. **Error handling** - Some try/except blocks swallow errors
3. **API documentation** - OpenAPI docs exist but could be more detailed
4. **Configuration** - Hardcoded values in some places (API_URL)
5. **State persistence** - In-memory storage for some data

### Security Considerations

1. **CORS** - Currently allows localhost:3000, localhost:8501
2. **Code review** - Good dangerous pattern detection
3. **File access** - Safe edit system prevents arbitrary writes
4. **No auth** - Local-only deployment assumed

---

## Integration Points

### Clawdbot Integration

`core/clawdbot_runner.py` provides:
- Message routing to Clawdbot
- Session management
- Context building with agent soul/memory

### External Connectors

- **Gmail**: OAuth2 authentication, message fetching
- **WhatsApp**: Webhook integration, whitelisted contacts
- **Calendar**: OAuth2 (planned)

---

## Database Schema

SQLite with Alembic migrations:

**Key Tables:**
- inbox_messages
- tasks
- transactions
- contractor_jobs
- cost_records
- portfolio_holdings
- events

---

## Recommendations

### High Priority

1. **Add comprehensive tests** - Unit tests for agents, API integration tests
2. **Implement authentication** - Even for local, add basic auth option
3. **Add database backup automation** - Schedule daily SQLite backups

### Medium Priority

1. **Extract hardcoded config** - Use environment variables consistently
2. **Add API versioning** - Prepare for breaking changes
3. **Implement rate limiting** - Protect against runaway agents

### Low Priority

1. **Add WebSocket for real-time updates** - Currently polling
2. **Implement agent memory search** - Vector embeddings for recall
3. **Add audit trail table** - Persistent record of all changes

---

## Files Changed Summary

| File | Action | Description |
|------|--------|-------------|
| `backend/api/routes/janitor.py` | NEW | 12 API endpoints for Janitor |
| `backend/api/main.py` | UPDATED | Added janitor router |
| `backend/cli/main.py` | UPDATED | 8 new janitor CLI commands |
| `frontend/src/app/janitor/page.tsx` | NEW | Full Janitor UI page |
| `frontend/src/components/layout/Shell.tsx` | UPDATED | Added nav link |

---

## Conclusion

MyCasa Pro has a solid architecture with well-designed agent coordination and rich activity tracking. The Janitor agent (Salimata) is now fully integrated with CLI commands, API routes, and a comprehensive UI page. The system is ready for production use with the caveat that testing and authentication should be added before deployment beyond localhost.

**Total Lines of Code Added:** ~1,500+
**New Files:** 2
**Modified Files:** 3

---

*Review completed by Galidima ✨*
