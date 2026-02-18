# Indicators

User‑facing summary of indicators. Each entry references a registry ID in `INDICATOR_REGISTRY.md`.
Diagnostics: `GET /api/diagnostics/indicators`.

## Dashboard

- **Tasks pending** (`dashboard.tasks.pending_count`)
  - Source: Maintenance tasks
  - Shown in: Status header + Open Tasks KPI
  - Unavailable means: backend/tasks API not reachable

- **Messages unread** (`dashboard.messages.unread_total`)
  - Source: Inbox unread count
  - Shown in: Status header + Unread Messages KPI
  - Unavailable means: inbox service not reachable

- **Portfolio change** (`dashboard.portfolio.change_pct`)
  - Source: Portfolio summary
  - Shown in: Status header
  - Unavailable means: portfolio summary unavailable or missing data

- **Janitor audit** (`dashboard.janitor.last_run`)
  - Source: Janitor wizard runs
  - Shown in: Status header
  - Unavailable means: no audit has run or janitor service is down

- **Heartbeat findings** (`dashboard.heartbeat.open_findings`)
  - Source: Heartbeat notifications
  - Shown in: Status header
  - Unavailable means: heartbeat state missing

- **Identity readiness** (`dashboard.identity.ready`)
  - Source: Tenant identity status
  - Shown in: Status header
  - Unavailable means: identity files missing or error

- **Upcoming bills total** (`dashboard.bills.upcoming_total`)
  - Source: Bills list (unpaid)
  - Shown in: Upcoming Bills KPI
  - Unavailable means: bills API not reachable

- **System health (agents online)** (`dashboard.system.agents_online`)
  - Source: Quick status agent list
  - Shown in: System Health KPI + Agents badge
  - Unavailable means: status endpoint not reachable

- **Recent activity** (`dashboard.activity.recent_changes`)
  - Source: Agent logs (recent)
  - Shown in: Recent Activity
  - Unavailable means: status endpoint not reachable

- **System health metrics** (`dashboard.system.health.metrics`)
  - Source: System status
  - Shown in: System Health card
  - Unavailable means: lifecycle monitor not reporting

## System Page

- **Portfolio total/cash/day change** (`system.portfolio.*`)
  - Source: Portfolio summary
  - Unavailable means: finance agent unavailable or summary error

- **System monitor metrics** (`system.monitor.*`)
  - Source: system monitor
  - Unavailable means: lifecycle monitor not reporting

- **Janitor last run** (`system.janitor.last_run`)
  - Source: janitor wizard history

## Inbox

- **Messages list** (`inbox.messages.list`)
  - Source: inbox messages

- **Unread count** (`inbox.unread.count`)
  - Source: unread count endpoint

## Maintenance

- **Tasks list** (`maintenance.tasks.list`)
  - Source: maintenance tasks

- **Completed count** (`maintenance.tasks.completed`)
  - Source: maintenance tasks (status completed)

## Agents

- **Fleet status** (`agents.fleet.status`)
  - Source: fleet manager

- **System monitor** (`agents.system.monitor`)
  - Source: lifecycle monitor
