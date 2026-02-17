# MyCasa Pro - Full Codebase Audit
**Date:** 2026-01-30
**Auditor:** Galidima (Janitor Mode)
**Scope:** Complete codebase review - no vibe coding allowed

---

## Summary Statistics

| Category | Files | Lines of Code |
|----------|-------|---------------|
| Agents | 16 | ~11,528 |
| API Routes | 20 | ~6,094 |
| Core Modules | 12 | ~3,500 |
| Edge Lab | 20 | ~4,500 |
| Frontend Pages | 11 | ~5,500 |
| Frontend Components | 27 | ~7,500 |
| **TOTAL** | **106** | **~38,622** |

---

## ✅ FULLY COMPLETE (Production Ready)

### Agents (9/9 working)

| Agent | Lines | Status | Methods |
|-------|-------|--------|---------|
| Manager | 1,267 | ✅ | 59 - Orchestration, delegation, status |
| Finance | 1,626 | ✅ | 67 - Portfolio, budgets, recommendations |
| Maintenance | 540 | ✅ | 44 - Task management |
| Security | 695 | ✅ | 45 - Incident tracking |
| Janitor | 1,365 | ✅ | 51 - System maintenance, audits |
| Contractors | 1,015 | ✅ | 48 - Provider management |
| Projects | 572 | ✅ | 46 - Project tracking |
| AgentScheduler | 517 | ✅ | Scheduled agent runs |
| TeamRouter | 428 | ✅ | Multi-agent coordination |

### Edge Lab (Financial Prediction System)

| Component | Status | Notes |
|-----------|--------|-------|
| Database (12 tables) | ✅ | PostgreSQL edgelab schema |
| MockAdapter | ✅ | Testing with 20 stocks |
| YFinanceAdapter | ✅ | Real data (slow but works) |
| SnapshotPipeline | ✅ | Point-in-time data capture |
| FeatureEngine | ✅ | 12 CORE_V1 features |
| PredictionPipeline | ✅ | Risk flags + scoring |
| EvaluationPipeline | ✅ | Walk-forward backtesting |
| CLI | ✅ | daily-scan, weekly-predict, evaluate |
| REST API | ✅ | 9 endpoints |

### Connectors (3/3 working)

| Connector | Status | Notes |
|-----------|--------|-------|
| Gmail | ✅ | OAuth2, read/search/send |
| Calendar | ✅ | OAuth2, events CRUD |
| WhatsApp | ✅ | QR auth, send/receive |

### API Routes (20 modules)

All routes load and are registered with FastAPI:
- secondbrain, settings, messaging, chat, system, system_live
- connectors, finance, inbox, tasks, telemetry, agent_activity
- scheduler, google, clawdbot_import, reminders, memory, agent_chat
- **edgelab** (NEW)

### Frontend Pages (11 pages)

| Page | Status | Notes |
|------|--------|-------|
| Dashboard | ✅ | System overview |
| Finance | ✅ | Portfolio UI |
| Maintenance | ✅ | Task management |
| Contractors | ✅ | Provider directory |
| Projects | ✅ | Project tracking |
| Security | ✅ | Incident UI |
| Inbox | ✅ | Unified messages |
| Settings | ✅ | Full config |
| System | ✅ | Live status + scheduler |
| Logs | ✅ | Log viewer |
| Approvals | ✅ | Approval queue |

### Frontend Components (27 components)

Major components working:
- Shell (navigation)
- MemoryGraph (force graph visualization)
- SchedulerManager (job scheduling)
- LiveSystemDashboard (real-time metrics)
- ConnectorMarketplace (integration browser)
- SetupWizard (6-step onboarding)
- SystemMonitor (agent activity)
- AgentActivityDashboard (HYPERCONTEXT-style)
- ApprovalQueue (approval UI)
- ManagerChat (chat widget)
- CommandPalette (quick actions)
- LogViewer (log display)
- SystemStatusBar (status bar)

---

## ⚠️ PARTIAL (Needs Completion)

### 1. Bank Connector
**Current State:** Not implemented
**Needed:** CSV/OFX import for transaction history
**Priority:** HIGH
**Files to create:**
- `connectors/bank/__init__.py`
- `connectors/bank/csv_parser.py`
- `connectors/bank/ofx_parser.py`
- `api/routes/bank.py`

### 2. Scheduler Notifications
**Current State:** Jobs run but no alerts
**Needed:** WhatsApp/email notification on job completion/failure
**Priority:** HIGH
**Files to modify:**
- `agents/scheduler.py` - Add notification hooks
- `api/routes/scheduler.py` - Add notification config

### 3. Semantic Search for SecondBrain
**Current State:** Text search only
**Needed:** Embeddings + vector similarity search
**Priority:** MEDIUM
**Files to create/modify:**
- `core/secondbrain/embeddings.py`
- `core/secondbrain/skill.py` - Add semantic_search method

### 4. Test Suite
**Current State:** Basic import tests only
**Needed:** Comprehensive pytest suite
**Priority:** HIGH
**Files to create:**
- `tests/test_agents.py`
- `tests/test_pipelines.py`
- `tests/test_api.py`
- `tests/test_edgelab.py`

### 5. Edge Lab yfinance Performance
**Current State:** Slow (60+ API calls for universe)
**Needed:** Caching layer, batch optimization
**Priority:** LOW
**Files to modify:**
- `backend/edgelab/adapters/yfinance.py`
- Add Redis/sqlite cache

---

## ❌ NOT IMPLEMENTED (Missing)

### 1. Home Assistant Integration
**Purpose:** Smart home control
**Effort:** HIGH
**Files needed:**
- `connectors/homeassistant/__init__.py`
- `connectors/homeassistant/client.py`
- Frontend controls

### 2. Ring Doorbell Integration
**Purpose:** Security camera access
**Effort:** MEDIUM
**Files needed:**
- `connectors/ring/__init__.py`
- `connectors/ring/client.py`

### 3. Bill Tracking & Reminders
**Purpose:** Track bills, due dates, auto-pay status
**Effort:** MEDIUM
**Files needed:**
- `agents/bills.py`
- `api/routes/bills.py`
- Frontend page

### 4. Voice Interface
**Purpose:** Voice commands via Siri/Alexa
**Effort:** HIGH
**Files needed:** External integration

### 5. Mobile App
**Purpose:** iOS/Android companion
**Effort:** VERY HIGH
**Files needed:** Separate repo

---

## 🔧 Tech Debt & Issues

### 1. Missing `agents/coordination.py`
Referenced in CHANGELOG but file doesn't exist. The `TeamRouter` in `teams.py` appears to handle coordination instead.

### 2. Class Name Mismatches
- `scheduler.py` has `AgentScheduler` not `SchedulerAgent`
- `teams.py` has `TeamRouter` not `TeamCoordinator`
- `secondbrain/skill.py` has `SecondBrain` not `SecondBrainSkill`

### 3. Port Conflicts on Start
- Backend tries port 8000 (often in use)
- Frontend tries port 3000 (often in use)
- `start.sh` needs `lsof` which isn't installed

### 4. Frontend Lock File Issues
- Multiple `package-lock.json` files detected
- Next.js warns about workspace root inference

---

## 📋 Recommended Build Order

### Phase 1: Critical (This Week)
1. ✅ Edge Lab - DONE
2. Bank Connector (CSV/OFX import)
3. Scheduler Notifications
4. Test Suite foundation

### Phase 2: Important (Next Week)
5. Semantic Search for SecondBrain
6. Bill Tracking agent
7. Fix tech debt items

### Phase 3: Nice to Have (Future)
8. Home Assistant integration
9. Ring Doorbell integration
10. Performance optimization

---

## Quick Commands

```bash
# Start backend
cd ~/clawd/apps/mycasa-pro
source .venv/bin/activate
uvicorn api.main:app --reload --port 8000

# Start frontend
cd frontend && npm run dev

# Run Edge Lab
python -m backend.edgelab.cli daily-scan --as-of "2026-01-29T21:00:00Z" --adapter mock

# Verify build
python scripts/verify_build.py
```

---

**Report generated:** 2026-01-30 05:45 PST
**Next audit:** Scheduled after Phase 1 completion
