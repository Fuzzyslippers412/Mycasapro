# Indicator Registry

Canonical source of truth for UI indicators. Every indicator below has a real source, freshness rule, and fallback.

Diagnostics endpoint: `GET /api/diagnostics/indicators`

## Dashboard

| ID | Label | UI location | API endpoint | DB/source | Freshness (s) | Validation | Fallback state |
|---|---|---|---|---|---:|---|---|
| dashboard.tasks.pending_count | Tasks pending | Dashboard > Status header + KPI | `GET /api/tasks?status=pending` | `maintenance_tasks.status = 'pending'` | 86400 | Count is integer >= 0 | Show “Tasks unavailable” |
| dashboard.bills.upcoming_total | Upcoming bills total | Dashboard > KPI | `GET /api/bills?include_paid=false` | `bills.is_paid = false` | 86400 | Sum of `amount` numeric >= 0 | Show “Bills unavailable” |
| dashboard.messages.unread_total | Messages unread | Dashboard > Status header + KPI | `GET /api/inbox/unread-count` | `inbox_messages.is_read = false` | 3600 | `total` integer >= 0 | Show “Messages unavailable” |
| dashboard.portfolio.change_pct | Portfolio change % | Dashboard > Status header | `GET /api/portfolio` | Finance agent summary (holdings + yfinance); `last_updated` in response | 3600 | `day_change_pct` numeric or null | Show “Portfolio change unavailable” |
| dashboard.janitor.last_run | Janitor audit summary | Dashboard > Status header | `GET /api/janitor/wizard/history?limit=1` | `janitor_wizard_runs` | 86400 | Latest run exists, `health_score` in [0..100] | Show “Janitor not run” |
| dashboard.heartbeat.open_findings | Heartbeat findings | Dashboard > Status header | `GET /status` | `notifications.category in heartbeat checks` | 3600 | `open_findings` integer >= 0 | Show “Heartbeat not run” |
| dashboard.identity.ready | Identity readiness | Dashboard > Status header | `GET /status` | tenant identity files | 86400 | `ready` boolean | Show “Identity unavailable” |
| dashboard.system.agents_online | Agents online count | Dashboard > KPI + Agents badge | `GET /status` | lifecycle status (normalized) | 300 | `facts.agents` map | Show “Offline / N/A” |
| dashboard.activity.recent_changes | Recent activity feed | Dashboard > Recent Activity | `GET /status` | `agent_logs` (latest) | 300 | Array length >= 0 | Show “No recent activity” |
| dashboard.system.health.metrics | CPU/Memory/Disk/Uptime | Dashboard > System Health card | `GET /api/system/status` | lifecycle status (host metrics if available) | 300 | Each metric numeric or null | Show “Unavailable” per metric |

## System Page

| ID | Label | UI location | API endpoint | DB/source | Freshness (s) | Validation | Fallback state |
|---|---|---|---|---|---:|---|---|
| system.portfolio.total_value | Portfolio total value | System > Portfolio card | `GET /api/portfolio` | Finance agent summary | 3600 | `total_value` numeric >= 0 | Show “Unavailable” |
| system.portfolio.cash | Cash balance | System > Portfolio card | `GET /api/portfolio` | `cash_holdings` table (via finance agent) | 3600 | `cash` numeric >= 0 | Show “Unavailable” |
| system.portfolio.day_change | Portfolio day change | System > Portfolio card | `GET /api/portfolio` | Finance agent summary | 3600 | `day_change` numeric | Show “Unavailable” |
| system.monitor.cpu | CPU usage | System > Live dashboard | `GET /api/system/monitor` | lifecycle monitor | 300 | 0–100 | Show “Unavailable” |
| system.monitor.memory | Memory usage | System > Live dashboard | `GET /api/system/monitor` | lifecycle monitor | 300 | 0–100 | Show “Unavailable” |
| system.monitor.disk | Disk usage | System > Live dashboard | `GET /api/system/monitor` | lifecycle monitor | 300 | 0–100 | Show “Unavailable” |
| system.janitor.last_run | Janitor wizard run | System > Janitor section | `GET /api/janitor/wizard/history?limit=1` | `janitor_wizard_runs` | 86400 | Latest run exists | Show “Unavailable” |

## Inbox

| ID | Label | UI location | API endpoint | DB/source | Freshness (s) | Validation | Fallback state |
|---|---|---|---|---|---:|---|---|
| inbox.messages.list | Messages list | Inbox page | `GET /api/inbox/messages` | `inbox_messages` | 300 | `messages` array | Show “Unable to load messages” |
| inbox.unread.count | Unread count | Inbox header / indicators | `GET /api/inbox/unread-count` | `inbox_messages.is_read = false` | 3600 | `total` integer | Show “Unavailable” |

## Maintenance

| ID | Label | UI location | API endpoint | DB/source | Freshness (s) | Validation | Fallback state |
|---|---|---|---|---|---:|---|---|
| maintenance.tasks.list | Tasks list | Maintenance page | `GET /api/tasks` | `maintenance_tasks` | 300 | `tasks` array | Show “Unable to load tasks” |
| maintenance.tasks.completed | Completed count | Maintenance page | `GET /api/tasks?status=completed` | `maintenance_tasks.status = 'completed'` | 300 | count integer | Show “Unavailable” |

## Agents

| ID | Label | UI location | API endpoint | DB/source | Freshness (s) | Validation | Fallback state |
|---|---|---|---|---|---:|---|---|
| agents.fleet.status | Fleet status | Agent Manager | `GET /api/fleet/agents` | fleet manager | 30 | `agents` array | Show “Backend offline” |
| agents.system.monitor | System monitor | Agent Manager | `GET /api/system/monitor` | lifecycle monitor | 300 | metrics numeric | Show “Unavailable” |
