# MyCasa Pro API Architecture

**Last Updated:** 2026-01-28
**Author:** Galidima

This document captures the complete API architecture so future sessions don't need to reverse-engineer it.

---

## Stack

| Layer | Technology |
|-------|------------|
| **Backend** | FastAPI (Python 3.14) |
| **Database** | SQLite + SQLAlchemy ORM |
| **Frontend** | Next.js 15 + Mantine 7 |
| **Port** | Backend: 8000, Frontend: 3000 |

---

## Directory Structure

```
mycasa-pro/
├── backend/
│   ├── api/
│   │   └── main.py          # FastAPI app, all endpoints
│   ├── connectors/
│   │   ├── __init__.py      # Exports gmail_connector, whatsapp_connector
│   │   ├── gmail.py         # GmailConnector (uses gog CLI)
│   │   └── whatsapp.py      # WhatsAppConnector (uses wacli CLI)
│   ├── core/
│   │   ├── schemas.py       # Pydantic models
│   │   └── utils.py         # Helpers (generate_correlation_id, log_action)
│   └── storage/
│       ├── database.py      # get_db_session, init_db
│       ├── models.py        # SQLAlchemy models
│       └── repository.py    # Repository class (CRUD operations)
├── frontend/
│   └── src/
│       ├── app/             # Next.js pages
│       ├── components/      # React components
│       └── lib/
│           ├── api.ts       # API client functions
│           └── hooks.ts     # React hooks for data fetching
├── agents/                  # Agent implementations
├── data/
│   └── mycasa.db           # SQLite database
└── docs/                   # Documentation (this file)
```

---

## Global State (main.py)

```python
# Defined at module level in backend/api/main.py

START_TIME = time.time()                    # For uptime calculation
_sync_task: asyncio.Task | None = None      # Background sync task
_sync_enabled: bool = False                 # Inbox sync on/off (default: OFF)
SYNC_INTERVAL_SECONDS = 15 * 60             # 15 minutes

# Manager chat message queue
_manager_messages: list = []                # Pending messages for UI
_message_id_counter: int = 0                # Auto-increment ID
```

---

## Key Functions

### queue_manager_message(text: str)
Queues a message to appear in the Manager Chat UI.
```python
def queue_manager_message(text: str):
    global _manager_messages, _message_id_counter
    _message_id_counter += 1
    _manager_messages.append({
        "id": f"mgr_{_message_id_counter}",
        "text": text,
        "timestamp": datetime.utcnow().isoformat()
    })
```

### _run_inbox_sync()
Fetches messages from Gmail and WhatsApp, stores in database.
```python
async def _run_inbox_sync():
    # Gmail: last 7 days, unread only, max 30
    gmail_result = gmail_connector.fetch_messages(days_back=7, max_results=30, unread_only=True)
    
    # WhatsApp: whitelisted contacts only, max 20
    whatsapp_result = whatsapp_connector.fetch_messages(limit=20)
    
    # Deduplicate by external_id, store new messages
    # Returns: {"gmail": count, "whatsapp": count, "new": count}
```

### _periodic_sync()
Background task that runs sync every 15 minutes (only when enabled).
```python
async def _periodic_sync():
    while True:
        if _sync_enabled:
            await _run_inbox_sync()
        await asyncio.sleep(SYNC_INTERVAL_SECONDS)
```

### _generate_launch_report(sync_result, cleared)
Creates the Manager report shown after launch.
```python
def _generate_launch_report(sync_result: dict, cleared: int) -> dict:
    # Returns: {
    #   "text": "📬 **Inbox Launch Report**\n...",
    #   "gmail_count": int,
    #   "whatsapp_count": int,
    #   "new_count": int,
    #   "cleared": int,
    #   "timestamp": str
    # }
```

---

## API Endpoints

### Health & Status

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check with connector status |
| `/status` | GET | Dashboard status (tasks, events, cost) |

### Inbox Sync Control

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/inbox/sync-status` | GET | Returns `{enabled, sync_task_running, sync_interval_seconds, uptime_seconds}` |
| `/inbox/launch` | POST | **FRESH START**: Clears all messages, fetches new, enables periodic sync, queues Manager report |
| `/inbox/stop` | POST | Disables periodic sync |
| `/inbox/sync` | POST | One-time sync (doesn't enable periodic) |

### Inbox Messages

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/inbox/messages` | GET | List messages. Params: `source`, `unread_only`, `limit` |
| `/inbox/unread-count` | GET | Unread counts by source |
| `/inbox/messages/{id}/read` | PATCH | Mark message as read |
| `/inbox/ingest` | POST | Legacy sync endpoint (use `/inbox/sync` instead) |

### Manager Chat

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/manager/messages` | GET | Get pending Manager messages for chat UI |
| `/manager/messages/ack` | POST | Clear message queue (called after UI displays them) |
| `/manager/chat` | POST | Send message to Manager (future: routes to Clawdbot) |

### Contacts

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/contacts/whitelist` | GET | WhatsApp whitelisted contacts |
| `/contacts/whitelist` | POST | Add to whitelist. Params: `phone`, `name` |
| `/contacts/whitelist/{phone}` | DELETE | Remove from whitelist |

### Tasks

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/tasks` | POST | Create task |
| `/tasks` | GET | List tasks. Params: `status`, `category`, `limit` |
| `/tasks/{id}` | PATCH | Update task |
| `/tasks/{id}/complete` | POST | Mark complete |

### Finance

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/transactions/ingest` | POST | Ingest transactions |
| `/transactions` | GET | List transactions |
| `/spend/summary` | GET | Spending summary |
| `/cost` | POST | Record system cost |
| `/cost/summary` | GET | Cost summary by period |
| `/budgets` | GET | Budget status |

### Contractors

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/contractors/jobs` | POST | Create contractor job |
| `/contractors/jobs` | GET | List jobs |
| `/contractors/jobs/{id}/schedule` | POST | Schedule job |
| `/contractors/jobs/{id}/approve-cost` | POST | Approve job cost |
| `/contractors/jobs/{id}/complete` | POST | Mark complete |

### Backup

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/backup/export` | POST | Create backup |
| `/backup/restore` | POST | Restore from backup |
| `/backup/list` | GET | List available backups |

### Intake

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/intake` | GET | Get intake/setup status |
| `/intake` | POST | Complete initial setup |

---

## Database Models (SQLAlchemy)

### InboxMessageDB
```python
class InboxMessageDB(Base):
    __tablename__ = "inbox_messages"
    
    id: int (PK)
    external_id: str (unique)      # Gmail ID or WhatsApp msg ID
    source: str                     # "gmail" or "whatsapp"
    sender_name: str
    sender_id: str                  # Email or phone
    subject: str | None
    body: str
    timestamp: datetime
    is_read: bool = False
    domain: str | None              # Extracted from email
    linked_task_id: int | None      # FK to tasks
```

### Other Models
- `MaintenanceTask`
- `Contractor`
- `ContractorJob`
- `Project`
- `ProjectMilestone`
- `Bill`
- `Transaction`
- `Budget`
- `FinanceManagerSettings`
- `IncomeSource`
- `SystemCostEntry`
- `Notification`
- `AgentLog`
- `ScheduledJob`

---

## Connectors

### GmailConnector
```python
class GmailConnector:
    def fetch_messages(self, days_back=7, max_results=20, unread_only=True) -> List[dict]:
        # Uses: gog gmail search 'newer_than:{days}d is:unread' --max {max} --json
        # Returns normalized message dicts
    
    def get_status(self) -> ConnectorStatus:
        # Returns: CONNECTED, DISCONNECTED, or ERROR
```

### WhatsAppConnector
```python
class WhatsAppConnector:
    def fetch_messages(self, limit=20) -> List[dict]:
        # Uses: wacli messages list "{contact}" --limit {limit} --json
        # Only fetches from allowlisted contacts in settings
        # Returns normalized message dicts
 
    def get_allowlist(self):
        # Loaded from settings.agents.mail.whatsapp_allowlist/whatsapp_contacts
```

---

## Frontend Hooks (lib/hooks.ts)

```typescript
// Fetch inbox messages
export function useInboxMessages(params?: { source?: string; limit?: number }) {
    // GET /inbox/messages
}

// Fetch unread counts
export function useUnreadCount() {
    // GET /inbox/unread-count
}
```

---

## Frontend API Client (lib/api.ts)

```typescript
export async function syncInbox() {
    // POST /inbox/sync
}

export async function markMessageRead(id: number) {
    // PATCH /inbox/messages/{id}/read
}

export async function launchInbox() {
    // POST /inbox/launch
}

export async function stopInbox() {
    // POST /inbox/stop
}
```

---

## Startup Flow

1. `lifespan()` runs on FastAPI startup
2. `init_db()` creates tables if needed
3. `_sync_task = asyncio.create_task(_periodic_sync())` starts background task
4. Background task waits for `_sync_enabled = True` before syncing
5. User clicks "Launch" → `POST /inbox/launch`:
   - Clears existing messages
   - Fetches fresh from Gmail + WhatsApp
   - Sets `_sync_enabled = True`
   - Queues Manager report
   - Returns report to frontend

---

## Key Behaviors

### Inbox Sync is OPT-IN
- Default: `_sync_enabled = False`
- User must click "Launch Inbox Sync" in Settings or Inbox page
- Launch clears old messages and fetches fresh

### Manager Chat
- Messages queued via `queue_manager_message()`
- Frontend polls `/manager/messages` every 10 seconds
- After displaying, frontend calls `/manager/messages/ack` to clear queue
- Messages persist in localStorage on frontend

### Deduplication
- Messages deduplicated by `external_id`
- If message already exists in DB, it's skipped

---

## CLI Dependencies

| CLI | Purpose | Install |
|-----|---------|---------|
| `gog` | Gmail access | `brew install gog` or npm |
| `wacli` | WhatsApp access | Custom CLI, needs `wacli sync --follow` running |

---

## Environment

- **Database path:** `data/mycasa.db`
- **Logs:** `/tmp/mycasa-api.log`, `/tmp/mycasa-frontend.log`
- **Virtual env:** `venv/` in project root

---

## Start Commands

```bash
# Full stack
cd /path/to/mycasa-pro && ./start_all.sh

# Backend only
cd /path/to/mycasa-pro && source venv/bin/activate
python -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000 --reload

# Frontend only
cd /path/to/mycasa-pro/frontend && npm run dev
```

---

*This document should be updated whenever the API changes.*
