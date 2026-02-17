# MyCasa Pro Refinement Plan

> **Goal:** Harden, standardize, and clean up existing codebase into a stable, maintainable "installable skill."
> **Constraint:** NO NEW FEATURES. Refactor, reorganize, validate, test only.

---

## 1. EXEC SUMMARY (12 bullets)

1. **Repo cleanup:** Rename `pages/` → `legacy/streamlit/`, move root `components/` into `frontend/src/components/` or delete duplicates
2. **API split complete:** `api/main.py` (762 lines) → `api/routes/*.py` + `api/schemas/*.py` + `api/services/*.py`
3. **Typed settings:** `core/settings_typed.py` provides `MyCasaSettings` with per-agent scoping + validation (DONE)
4. **Event bus hardened:** `core/events_v2.py` has correlation IDs, retry, dead-letter queue (DONE)
5. **Idempotent lifecycle:** `core/lifecycle.py` prevents duplicate startups/shutdowns (DONE)
6. **Finance recommendation style:** Add `RecommendationStyle` enum to `FinanceSettings` with validation
7. **DB migrations:** Add Alembic with unique constraints on messages, tasks, transactions
8. **Telemetry integration:** `api/routes/telemetry.py` exposes cost data; Finance reads it to enforce $1000/month cap (DONE)
9. **Frontend status bar:** Global component shows running/stopped + task count + cost (exists in Shell, needs refinement)
10. **Guardrails:** Input validation at API boundary, standardized error payloads with correlation_id
11. **Dev tooling:** Add `Makefile`, `.env.example`, `docker-compose.yml` for dev parity
12. **Test coverage:** Add pytest for backend, validate idempotency + settings + telemetry

---

## 2. PR PLAN (10 PRs)

### PR 1: Repo Hygiene & Directory Cleanup
**Title:** `chore: clean up directory structure and remove ambiguity`

**Files touched:**
- `pages/` → rename to `legacy/streamlit/`
- `components/` → audit and move to `frontend/src/components/shared/` or delete
- `Makefile` (new)
- `.env.example` (new)
- `docker-compose.yml` (new)
- `.gitignore` (update)

**Changes:**
- Rename `pages/` to `legacy/streamlit/` with README explaining it's not primary UI
- Audit root `components/` — if Next-only, move under `frontend/`; if Streamlit-only, move under `legacy/`
- Create `Makefile` with targets: `dev`, `test`, `lint`, `run`, `migrate`
- Create `.env.example` with all required vars documented
- Create minimal `docker-compose.yml` for local dev (postgres optional, backend, frontend)
- Update `.gitignore` for Python/Node artifacts

**Risk:** Low
**Validation:**
```bash
make dev  # Should start backend + frontend
ls legacy/streamlit/  # Should contain old Streamlit pages
ls pages/  # Should not exist
```

---

### PR 2: API Route Split (Part 1 - System & Backup)
**Title:** `refactor(api): split system and backup routes from main.py`

**Files touched:**
- `api/main.py` → remove system/backup routes
- `api/routes/__init__.py`
- `api/routes/system.py` (exists, ensure complete)
- `api/schemas/common.py` (exists, ensure complete)
- `api/schemas/system.py` (new)

**Changes:**
- Ensure all `/system/*` and `/backup/*` routes are in `api/routes/system.py`
- Remove duplicates from `api/main.py`
- Add Pydantic request/response models for every endpoint
- Standardize error payload: `{"error": {"code", "message", "details", "correlation_id"}}`

**Risk:** Medium (route changes)
**Validation:**
```bash
curl -X POST http://localhost:8000/system/startup | jq '.success'  # true
curl -X POST http://localhost:8000/system/startup | jq '.already_running'  # true (idempotent)
curl http://localhost:8000/system/status | jq '.running'  # true
```

---

### PR 3: API Route Split (Part 2 - Tasks, Finance, Inbox)
**Title:** `refactor(api): split tasks, finance, and inbox routes`

**Files touched:**
- `api/main.py` → remove more routes
- `api/routes/tasks.py` (new)
- `api/routes/finance.py` (new)
- `api/routes/inbox.py` (new)
- `api/schemas/tasks.py` (new)
- `api/schemas/finance.py` (new)
- `api/schemas/inbox.py` (new)

**Changes:**
- Move `/tasks/*` to `api/routes/tasks.py`
- Move `/portfolio`, `/bills/*`, `/spend/*` to `api/routes/finance.py`
- Move `/inbox/*` to `api/routes/inbox.py`
- Add Pydantic models for all request/response payloads
- No semantic changes to endpoints

**Risk:** Medium
**Validation:**
```bash
curl http://localhost:8000/tasks | jq '.tasks | length'
curl http://localhost:8000/portfolio | jq '.total_value'
curl http://localhost:8000/inbox/messages | jq '.count'
```

---

### PR 4: Finance Recommendation Style Settings
**Title:** `feat(settings): add finance recommendation style with validation`

**Files touched:**
- `core/settings_typed.py` → add `RecommendationStyle` enum and fields
- `agents/finance.py` → read and use recommendation style
- `api/routes/settings.py` (new) → expose settings endpoints
- `frontend/src/app/settings/page.tsx` → add recommendation style UI

**Changes:**
- Add `RecommendationStyle` enum: `QUICK_FLIP`, `ONE_YEAR_PLAN`, `LONG_TERM_HOLD`, `BALANCED`
- Add to `FinanceSettings`:
  - `recommendation_style: RecommendationStyle`
  - `min_holding_days: int` (derived from style or user-set)
  - `risk_tolerance: Literal["low", "medium", "high"]`
- Add validation: reject contradictory configs (e.g., QUICK_FLIP + risk_tolerance="low")
- Finance agent reads config and adjusts recommendation framing
- Add "not financial advice" disclaimer to all recommendation outputs
- Never recommend actions exceeding user caps

**Risk:** Medium
**Validation:**
```bash
# API validation
curl -X PUT http://localhost:8000/settings/agent/finance \
  -H "Content-Type: application/json" \
  -d '{"recommendation_style": "invalid"}' | jq '.error'  # Should reject

# Valid update
curl -X PUT http://localhost:8000/settings/agent/finance \
  -H "Content-Type: application/json" \
  -d '{"recommendation_style": "LONG_TERM_HOLD"}' | jq '.success'  # true

# Verify persistence
curl http://localhost:8000/settings | jq '.agents.finance.recommendation_style'  # "LONG_TERM_HOLD"
```

---

### PR 5: Alembic Migrations Setup
**Title:** `feat(db): add Alembic migrations with constraints`

**Files touched:**
- `alembic.ini` (new)
- `alembic/` directory (new)
- `alembic/versions/001_initial_schema.py`
- `alembic/versions/002_add_constraints.py`
- `alembic/versions/003_add_telemetry_table.py`
- `database/__init__.py` → update to use migrations
- `Makefile` → add `migrate` target

**Changes:**
- Initialize Alembic with `alembic init alembic`
- Migration 001: baseline existing schema
- Migration 002: add unique constraints
  - `messages`: UNIQUE(provider, external_id, tenant_id)
  - `tasks`: UNIQUE(tenant_id, task_id) or appropriate
  - `transactions`: UNIQUE(tenant_id, external_id) or (tenant_id, date, amount, merchant)
- Migration 003: add `telemetry_events` table
  - id, event_type, source, agent_name, endpoint_name, cost_estimate, duration_ms, tokens_in, tokens_out, status, error, correlation_id, tenant_id, created_at
- Add indexes: messages.ts, tasks.due_date, transactions.ts, telemetry_events.created_at

**Risk:** High (DB changes)
**Validation:**
```bash
make migrate  # Run migrations
alembic current  # Shows current revision
alembic history  # Shows all migrations

# Verify constraints
sqlite3 data/mycasa.db ".schema messages" | grep UNIQUE
```

---

### PR 6: Event Bus Persistence & At-Least-Once Delivery
**Title:** `feat(events): add DB persistence and at-least-once delivery`

**Files touched:**
- `core/events_v2.py` → add DB persistence
- `database/models.py` → add `EventLog` model
- `alembic/versions/004_add_event_log.py`

**Changes:**
- Add `EventLog` model: id, event_id, type, source, tenant_id, correlation_id, payload, status, attempts, created_at, processed_at
- EventBus writes to DB on emit (async, non-blocking)
- On startup, replay unprocessed events (status != 'delivered')
- Mark events as delivered after successful handler execution
- Dead-letter events stay in DB with status='dead_letter' for debugging

**Risk:** Medium
**Validation:**
```bash
# Emit event
curl -X POST http://localhost:8000/telemetry/record \
  -H "Content-Type: application/json" \
  -d '{"category": "ai_api", "source": "test", "operation": "test"}'

# Verify in event log
sqlite3 data/mycasa.db "SELECT COUNT(*) FROM event_log"  # > 0
```

---

### PR 7: Standardize Error Payloads
**Title:** `refactor(api): standardize error responses across all endpoints`

**Files touched:**
- `api/middleware/errors.py` (new)
- `api/main_v2.py` → use error middleware
- All route files → use standard exceptions

**Changes:**
- Create `APIException` class with: code, message, details, status_code
- Create error handler middleware that catches all exceptions
- All errors return: `{"error": {"code": str, "message": str, "details": any, "correlation_id": str}}`
- Map common errors: ValidationError → 400, NotFound → 404, Conflict → 409
- Log all errors with correlation_id for debugging

**Risk:** Low
**Validation:**
```bash
# Invalid request
curl -X POST http://localhost:8000/system/shutdown \
  -H "Content-Type: application/json" \
  -d 'invalid json' | jq '.error.code'  # "VALIDATION_ERROR"

# All errors have correlation_id
curl http://localhost:8000/nonexistent | jq '.error.correlation_id'  # UUID present
```

---

### PR 8: Frontend Status Bar Refinement
**Title:** `refactor(frontend): unify system status display`

**Files touched:**
- `frontend/src/components/layout/Shell.tsx` → refine status badge
- `frontend/src/components/SystemStatusBar.tsx` (new or refactor existing)
- `frontend/src/lib/hooks.ts` → add `useSystemStatus` hook

**Changes:**
- Create `useSystemStatus` hook that polls `/system/status` every 10s
- Status bar shows:
  - Running/Stopped indicator (green/red dot)
  - Active task count
  - Last event timestamp
  - Monthly cost used vs cap ($X / $1000)
- Settings toggle reflects real backend state (no optimistic updates)
- Add loading states during startup/shutdown

**Risk:** Low
**Validation:**
```bash
# Visual check
open http://localhost:3000
# Status bar should show current state
# Toggle system off → bar should update to "Stopped"
# Toggle system on → bar should update to "Running"
```

---

### PR 9: Janitor Telemetry Integration
**Title:** `feat(janitor): integrate telemetry with Finance for cost cap enforcement`

**Files touched:**
- `agents/janitor.py` → write telemetry on every agent operation
- `agents/finance.py` → read telemetry and enforce $1000/month cap
- `api/routes/telemetry.py` → ensure read endpoint works

**Changes:**
- Janitor writes to telemetry table on every AI prompt:
  - agent_name, operation, model, tokens_in, tokens_out, cost_estimate, correlation_id
- Finance agent queries `/telemetry/summary/month` before recommendations
- If monthly cost approaching $1000, Finance warns and reduces AI calls
- Add alert when cost exceeds 80% of cap

**Risk:** Medium
**Validation:**
```bash
# Get monthly cost
curl http://localhost:8000/telemetry/summary/month | jq '.total_cost'

# Verify Finance reads it
# (Manual: trigger Finance recommendation, check it mentions cost awareness if near cap)
```

---

### PR 10: Test Suite & CI Setup
**Title:** `test: add pytest suite and CI workflow`

**Files touched:**
- `tests/` directory (new)
- `tests/conftest.py`
- `tests/test_lifecycle.py`
- `tests/test_settings.py`
- `tests/test_telemetry.py`
- `tests/test_api_system.py`
- `.github/workflows/ci.yml` (new)
- `pyproject.toml` → add test dependencies

**Changes:**
- Add pytest with fixtures for test DB, test client
- Test lifecycle idempotency (startup/startup, shutdown/shutdown)
- Test settings validation (valid/invalid configs)
- Test telemetry recording and retrieval
- Test API endpoints return correct schemas
- Add GitHub Actions CI: lint, typecheck, test

**Risk:** Low
**Validation:**
```bash
make test  # All tests pass
pytest tests/ -v  # Verbose output

# CI check
# Push to branch, verify GitHub Actions passes
```

---

## 3. ARCHITECTURE CONTRACTS

### System Lifecycle Contract
```python
class LifecycleManager:
    """
    INVARIANTS:
    - startup() is idempotent: calling twice returns {already_running: true}
    - shutdown() is idempotent: calling twice returns {already_stopped: true}
    - State transitions: STOPPED → STARTING → RUNNING → STOPPING → STOPPED
    - No state can be skipped
    - On startup: load state → init event bus → init agents → healthcheck → mark RUNNING
    - On shutdown: stop agents → flush queues → persist state → mark STOPPED
    """
    
    def startup(self, force: bool = False) -> StartupResult: ...
    def shutdown(self, create_backup: bool = True) -> ShutdownResult: ...
    def get_status(self) -> SystemStatus: ...
```

### Agent Interface Contract
```python
class BaseAgent(ABC):
    """
    INVARIANTS:
    - Every agent MUST implement all methods
    - configure() MUST be called before start()
    - start() MUST be idempotent (no duplicate subscriptions)
    - stop() MUST cleanup all resources
    - handle() MUST NOT throw; errors go to event bus
    - health() returns current status without side effects
    """
    
    @abstractmethod
    def configure(self, settings: AgentSettings) -> None: ...
    
    @abstractmethod
    def start(self) -> None: ...
    
    @abstractmethod
    def stop(self) -> None: ...
    
    @abstractmethod
    async def handle(self, event: Event) -> None: ...
    
    @abstractmethod
    def health(self) -> AgentHealth: ...
```

### Event Schema Contract
```python
@dataclass
class Event:
    """
    INVARIANTS:
    - event_id is globally unique (UUID)
    - correlation_id links related events (same request chain)
    - causation_id links to the event that caused this one
    - timestamp is server-side, UTC
    - type follows pattern: "{domain}.{action}" (e.g., "task.created")
    - source identifies the emitting component
    - status tracks delivery: pending → processing → delivered | dead_letter
    """
    
    event_id: str          # UUID, required
    type: str              # e.g., "system.started", required
    source: str            # e.g., "agent.finance", required
    tenant_id: str         # default: "default", required
    timestamp: datetime    # UTC, required
    correlation_id: str    # UUID, for tracing, required
    causation_id: str      # UUID, optional (what caused this)
    payload: Dict          # Event-specific data
    status: EventStatus    # pending | processing | delivered | failed | dead_letter
    attempts: int          # Retry count
```

### Settings Scoping Contract
```python
class MyCasaSettings:
    """
    INVARIANTS:
    - Settings are hierarchical: system → agents.{name}
    - All settings have typed defaults
    - Validation runs at API boundary (reject invalid before save)
    - Version field tracks schema migrations
    - updated_at tracks last modification
    - Per-agent settings inherit from AgentSettings base
    """
    
    version: str           # Schema version, e.g., "1.0.0"
    updated_at: datetime   # Last modification time
    system: SystemSettings # Global settings
    agents: AllAgentSettings  # Per-agent settings
    
    # Scoping examples:
    # system.monthly_cost_cap = 1000
    # agents.finance.recommendation_style = "LONG_TERM_HOLD"
    # agents.finance.enabled = true
    # agents.maintenance.auto_schedule_recurring = true
```

---

## 4. ACCEPTANCE CHECKLIST (Runnable Locally)

```bash
#!/bin/bash
# acceptance_test.sh

set -e

echo "=== MyCasa Pro Acceptance Tests ==="

# 1. Backend starts
echo "1. Starting backend..."
cd ~/clawd/apps/mycasa-pro
source .venv/bin/activate
uvicorn api.main_v2:app --port 8000 &
BACKEND_PID=$!
sleep 3

# 2. Health check
echo "2. Health check..."
curl -sf http://localhost:8000/health | jq -e '.status == "ok"'

# 3. Idempotent startup
echo "3. Testing idempotent startup..."
RESULT1=$(curl -sf -X POST http://localhost:8000/system/startup | jq -r '.success')
RESULT2=$(curl -sf -X POST http://localhost:8000/system/startup | jq -r '.already_running')
[ "$RESULT1" = "true" ] && [ "$RESULT2" = "true" ] && echo "✓ Startup idempotent"

# 4. Idempotent shutdown
echo "4. Testing idempotent shutdown..."
RESULT1=$(curl -sf -X POST http://localhost:8000/system/shutdown | jq -r '.success')
RESULT2=$(curl -sf -X POST http://localhost:8000/system/shutdown | jq -r '.already_stopped')
[ "$RESULT1" = "true" ] && [ "$RESULT2" = "true" ] && echo "✓ Shutdown idempotent"

# 5. Settings persistence
echo "5. Testing settings..."
curl -sf http://localhost:8000/system/status | jq -e '.agents_enabled'
echo "✓ Settings retrievable"

# 6. Telemetry endpoint
echo "6. Testing telemetry..."
curl -sf http://localhost:8000/telemetry/cost/today | jq -e '.cost >= 0'
echo "✓ Telemetry returns cost"

# 7. Inbox deduplication (manual check)
echo "7. Inbox messages..."
curl -sf http://localhost:8000/inbox/messages | jq -e '.count >= 0'
echo "✓ Inbox returns messages"

# Cleanup
kill $BACKEND_PID 2>/dev/null || true

echo ""
echo "=== All acceptance tests passed ==="
```

---

## 5. "DO NOT DO" LIST (Anti-Patterns)

| ❌ DO NOT | ✅ DO INSTEAD |
|-----------|---------------|
| Add new pages/features | Refine existing pages only |
| Change endpoint routes | Keep routes, refactor internals |
| Use raw dicts in API responses | Use Pydantic models everywhere |
| Swallow exceptions with bare `except:` | Catch specific exceptions, map to error codes |
| Store secrets in plaintext | Use env vars, never log secrets |
| Fire-and-forget events | Persist events, track delivery status |
| Duplicate startup/shutdown logic | Use single LifecycleManager |
| Optimistic UI updates | Poll backend state, reflect reality |
| Free-form text for settings | Use enums/typed fields with validation |
| Skip migrations | Use Alembic for all schema changes |
| Test manually only | Write automated tests for critical paths |
| Mutable global singletons | Use lifecycle-controlled instances |
| Direct DB calls from frontend | Always go through API |
| TODO comments in critical paths | Return errors with actionable messages |
| Contradictory configs silently accepted | Validate and reject with clear error |

---

## Current Status

**Already Implemented:**
- ✅ `core/settings_typed.py` - Typed settings with validation
- ✅ `core/events_v2.py` - Event bus with correlation IDs, retry, dead-letter
- ✅ `core/lifecycle.py` - Idempotent startup/shutdown
- ✅ `api/routes/system.py` - System routes split out
- ✅ `api/routes/telemetry.py` - Telemetry endpoints
- ✅ `api/schemas/common.py` - Common response schemas
- ✅ `api/main_v2.py` - Slim API entry point

**Next Priority:**
1. PR 1: Repo hygiene (Makefile, directory cleanup)
2. PR 4: Finance recommendation style settings
3. PR 5: Alembic migrations

---

**What else can I tighten up?**
