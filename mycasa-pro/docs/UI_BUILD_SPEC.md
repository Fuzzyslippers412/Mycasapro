# MYCASA PRO — UI / FRONTEND BUILD SPEC (ROBO-FORM)

## FRONTEND FOUNDATION

- Use https://github.com/homarr-labs/homarr as the UI skeleton / reference
- Treat Homarr as a dashboard framework, NOT a finished product
- Reuse patterns: grid layout, widget registry, real-time updates, auth patterns
- Respect Apache-2.0 license (NOTICE + attribution if code reused)

## GOAL

Build MyCasa Pro as a local-first, real-time **system control console**, not a static dashboard.

---

## INFORMATION ARCHITECTURE (PAGES)

Left Navigation:
1. Dashboard
2. Inbox (Approvals + Messages)
3. Maintenance
4. Finance
5. Contractors
6. Projects
7. Security
8. Logs
9. Settings

**Dashboard is overview-only. No deep work lives there.**

---

## DASHBOARD REQUIREMENTS

Dashboard must ALWAYS answer:
- What is happening now
- Which agents are active
- What tasks/events are live
- What changed recently
- What needs approval

### Required widgets:
- System Status (click → Full System Report)
- Alerts / Incidents
- Security Posture
- Agent Status (lazy-loaded)
- Task Queue (cross-domain)
- Live Events (real-time stream)
- System Cost (monthly burn vs cap)
- Recent Activity

### Dashboard behavior:
- Widgets load independently
- Top row loads first, then middle, then bottom
- No blocking aggregate calls
- CRITICAL status must be clickable and explain WHY

---

## INBOX (CORE CONTROL CENTER)

Inbox = single triage surface

### Sections (tabs or filters):
- Approvals
- Messages (Gmail + WhatsApp)
- System / Agent Events

### Messages:
- unified message list
- source badge (Gmail / WhatsApp)
- sender, timestamp
- linked domain (or UNKNOWN)
- suggested actions (approve / reply / assign)
- NO auto-replies

### Mail Skill Agent:
- ingestion + normalization only
- no decisions, no replies
- routes everything to Manager
- Inbox updates in real time

---

## AGENT VISIBILITY

Agent Status must show:
- state: idle | running | blocked | disabled
- last heartbeat
- current task
- elapsed time
- error count
- permissions summary

### Agent cards:
- expandable inline
- no page navigation required

`NOT_LOADED` → "Idle — Load details"

---

## TASK + EVENT FLOW

Every action emits events:
- agent_started
- agent_completed
- task_started
- task_completed
- prompt_executed
- cost_recorded
- incident_created

### Live Events panel:
- real-time stream
- source agent
- duration
- outcome

**No invisible background work.**

---

## COST & TELEMETRY

### Janitor tracks:
- token usage
- prompt cost (exact or estimated)
- cost per agent
- daily / weekly / monthly totals

### Finance Manager:
- enforces $1,000/month system cost cap
- forecasts burn
- surfaces overruns

### UI:
- System Cost widget always visible
- % of budget used
- top cost drivers

---

## FINANCE UI BEHAVIOR

- Portfolio is summary-first
- Expand rows for details (no page jump)
- Show concentration + volatility flags
- "Opportunities Detected" counter
- Spend tracking UI:
  - quick-add spend
  - daily / weekly summaries
  - guardrails: $10k/month, $350/day

Payment rails are distinct from spend categories.

---

## RESPONSIVENESS

### Desktop:
- 3-column dashboard grid
- inline expansions

### Tablet:
- 2-column grid
- right rail collapses to drawer

### Mobile:
- single-column
- bottom nav or hamburger (pick one)
- swipe gestures for tasks
- full-screen drawers
- no horizontal scroll

---

## INTERACTION DESIGN (NON-NEGOTIABLE)

- Every click has visible feedback
- Hover previews reveal context
- Animations indicate state change (120–200ms)
- Tasks resolve with motion
- Approvals feel deliberate and satisfying
- No silent actions
- No dead UI

**UI should feel like a flowing control system, not an admin panel.**

---

## SETTINGS ARCHITECTURE

```
Settings
├── Global
├── Finance Manager
├── Maintenance Agent
├── Contractors Agent
├── Projects Agent
├── Security Manager
├── Backup & Recovery Agent
```

Each agent owns its own settings.
Settings must be exportable/importable (JSON).

---

## PRODUCT DIRECTION

MyCasa Pro must be built as a reusable, installable **Clawdbot Super Skill**, not a one-off app.

### Requirements:
- single install
- multi-tenant ready
- pluggable connectors
- first-run wizard
- sane defaults
- versioned personas
- upgrade-safe migrations

---

## REFERENCE IMPLEMENTATION

**Homarr**: https://github.com/homarr-labs/homarr

Key patterns to adopt:
- Widget registry system
- Grid layout with drag-drop
- Real-time WebSocket updates
- Settings per widget
- Board/workspace concept
- Docker-native deployment

**License**: Apache-2.0 (attribution required if code reused)
