# MyCasa Pro - Design Decisions & Architecture Log

> This document tracks all major design decisions, improvements, and learnings so future sessions don't have to reverse-engineer the app.

## Architecture Overview

```
mycasa-pro/
├── frontend/          # Next.js 15 + Mantine 7 (port 3000)
├── backend/           # FastAPI (port 8000)
├── streamlit/         # Legacy Streamlit UI (port 8501, deprecated)
├── agents/            # Autonomous agent definitions
├── connectors/        # Gmail, WhatsApp integrations
├── core/              # Event bus, shared utilities
├── database/          # SQLite + SQLAlchemy ORM
└── data/              # SQLite DB files, message cache
```

### Running the App

```bash
# Full stack (recommended)
cd /path/to/mycasa-pro && ./start_all.sh

# Frontend only (port 3000)
cd frontend && npm run dev

# Backend API only (port 8000)
cd backend && python -m uvicorn api.main:app --reload
```

---

## Design System

### Color Scheme Support

The app uses Mantine's built-in color scheme system with `defaultColorScheme="auto"` to follow system preferences.

**Key lesson learned (2026-01-28):**
- Never hardcode `var(--mantine-color-dark-X)` for backgrounds
- Always use computed color scheme for conditional styling
- Example pattern:

```tsx
const computedColorScheme = useComputedColorScheme("light");
const bgColor = computedColorScheme === "dark" 
  ? "var(--mantine-color-dark-6)" 
  : "var(--mantine-color-gray-1)";
```

### Theme Configuration (layout.tsx)

```tsx
const theme = createTheme({
  primaryColor: "indigo",
  fontFamily: "Inter, -apple-system, BlinkMacSystemFont, sans-serif",
  defaultRadius: "md",
  colors: {
    dark: [
      "#C9C9C9", "#B8B8B8", "#828282", "#696969",
      "#424242", "#3B3B3B", "#2E2E2E", "#242424",
      "#1F1F1F", "#141414",
    ],
  },
});
```

### Color Tokens for Light Mode

| Use Case | Dark Mode | Light Mode |
|----------|-----------|------------|
| Unread message bg | `dark-6` | `indigo-0` or `gray-1` |
| Hover bg | `dark-5` | `gray-1` |
| Selected bg | `blue-light` | `blue-light` (works both) |
| Card bg | automatic | automatic |

---

## Inbox Page

### Message Sources
- **WhatsApp**: Via wacli sync (manual trigger)
- **Gmail**: Via gog CLI (your@gmail.com)

### Message Status Styling (Fixed 2026-01-28)

```tsx
// In MessageItem component
const computedColorScheme = useComputedColorScheme("light");
const unreadBg = computedColorScheme === "dark" 
  ? "var(--mantine-color-dark-6)" 
  : "var(--mantine-color-indigo-0)";

// Apply to Paper background
background: isSelected 
  ? "var(--mantine-color-blue-light)" 
  : !message.is_read ? unreadBg : "transparent"
```

### Sync Behavior
- Sync button triggers `POST /inbox/sync`
- Backend runs `gog gmail search` and `wacli messages` 
- Messages stored in SQLite `inbox_messages` table
- WhatsApp sync requires wacli to be authenticated

---

## Pages

| Route | Purpose | Status |
|-------|---------|--------|
| `/` | Dashboard - stats, alerts, activity | ✅ Working |
| `/inbox` | Unified inbox (WhatsApp + Gmail) | ✅ Fixed light mode |
| `/maintenance` | Tasks, scheduling, home readings | ✅ Working |
| `/finance` | Bills, portfolio, transactions | ✅ Working |
| `/contractors` | Service provider directory | ✅ Working |
| `/projects` | Renovation tracking | ✅ Working |
| `/settings` | Agent status, jobs, notifications | ✅ Working |
| `/security` | Placeholder | 🚧 Stub |
| `/logs` | System logs viewer | ✅ Working |

---

## Backend API

### Key Endpoints

```
GET  /status               - Health check
GET  /inbox/messages       - List messages (filter: source, is_read, limit)
GET  /inbox/unread         - Unread counts by source
POST /inbox/sync           - Trigger sync from sources
PUT  /inbox/messages/{id}/read  - Mark message as read
```

### Database Schema (SQLAlchemy)

```python
class InboxMessage(Base):
    id: int
    source: str  # "whatsapp" | "gmail"
    sender: str
    sender_id: str | None
    subject: str | None
    body: str
    timestamp: datetime
    is_read: bool
    domain: str | None  # extracted from email
```

---

## Agents (Autonomous)

Three-agent architecture managed by supervisor:

1. **Finance Agent** - Bills, transactions, portfolio
2. **Maintenance Agent** - Tasks, contractors, home readings
3. **Supervisor Agent** - Orchestration, routing, priorities

Agents communicate via event bus (`core/events.py`).

---

## Known Issues & TODOs

### High Priority
- [ ] WhatsApp message body often missing (needs full sync)
- [ ] Portfolio real-time updates not working

### Medium Priority
- [ ] Search in inbox not implemented
- [ ] Archive/delete actions not wired up
- [ ] Events tab empty (needs calendar integration)

### Low Priority
- [ ] Security page needs content
- [ ] Mobile responsiveness could be better

---

## Changelog

### 2026-01-28
- Fixed light mode colors in inbox (unread messages had dark background)
- Added `useComputedColorScheme` hook for color-scheme-aware styling
- Created this documentation file
- **Added auto-sync on startup** — Backend now automatically syncs Gmail + WhatsApp when it starts
- **Added periodic background sync** — Runs every 15 minutes automatically
- **Added mail-skill to Manager agent registry** — Manager can now access mail ingestion agent
- **New endpoints:**
  - `GET /inbox/sync-status` — Check if background sync is running
  - `POST /inbox/sync` — Manually trigger a sync

---

## Auto-Sync Architecture (Added 2026-01-28)

The backend now runs inbox sync automatically:

1. **On startup**: 5 seconds after API starts, initial sync runs
2. **Periodic**: Every 15 minutes (configurable via `SYNC_INTERVAL_SECONDS`)
3. **Manual**: `POST /inbox/sync` or "Sync" button in UI

### Implementation

```python
# In backend/api/main.py

async def _periodic_sync():
    # Initial sync after 5 seconds
    await asyncio.sleep(5)
    await _run_inbox_sync()
    
    # Then every 15 minutes
    while True:
        await asyncio.sleep(SYNC_INTERVAL_SECONDS)
        await _run_inbox_sync()

# Started in lifespan
_sync_task = asyncio.create_task(_periodic_sync())
```

### Sync Sources

| Source | What's Fetched | Filter |
|--------|---------------|--------|
| Gmail | Last 7 days | Unread only |
| WhatsApp | Last 20 messages | Whitelisted contacts only |

---

## Files Modified Today

1. `frontend/src/app/inbox/page.tsx` - Added color scheme support
2. `docs/DESIGN_DECISIONS.md` - This file (new + updated)
3. `backend/api/main.py` - Added auto-sync on startup + periodic sync
4. `agents/manager.py` - Added mail-skill to agent registry

---

*Last updated: 2026-01-28*

---

## Related Documentation

- **API_ARCHITECTURE.md** — Complete API reference (endpoints, functions, models)
- **AGENT_COORDINATION.md** — Agent coordination matrix and flows
- **AGENT_AUDIT.md** — Agent audit results and fixes

