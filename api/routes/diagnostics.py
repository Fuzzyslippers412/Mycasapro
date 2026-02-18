"""
Indicator diagnostics.
Validates indicator sources and freshness.
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from sqlalchemy import func

from database import get_db
from database.models import MaintenanceTask, Bill, InboxMessage, JanitorWizardRun

router = APIRouter(prefix="/diagnostics", tags=["Diagnostics"])


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def _status_from_last_updated(last_updated: Optional[datetime], freshness_s: int) -> str:
    if not last_updated:
        return "missing"
    age = datetime.utcnow() - last_updated
    if age > timedelta(seconds=freshness_s):
        return "stale"
    return "ok"


@router.get("/indicators")
async def indicator_diagnostics() -> Dict[str, Any]:
    """
    Return indicator status with provenance and freshness.
    """
    results: List[Dict[str, Any]] = []
    now = datetime.utcnow()

    # Dashboard: tasks pending
    with get_db() as db:
        task_count = db.query(MaintenanceTask).filter(MaintenanceTask.status == "pending").count()
        task_last = db.query(func.max(MaintenanceTask.updated_at)).scalar()
    results.append({
        "id": "dashboard.tasks.pending_count",
        "label": "Tasks pending",
        "value": task_count,
        "last_updated": task_last.isoformat() if task_last else None,
        "status": _status_from_last_updated(task_last, 86400),
        "source": "maintenance_tasks",
    })

    # Dashboard: unpaid bills total
    with get_db() as db:
        bills = db.query(Bill).filter(Bill.is_paid == False).all()  # noqa: E712
        bill_last = db.query(func.max(Bill.updated_at)).scalar()
    total_bills = sum(b.amount or 0 for b in bills)
    results.append({
        "id": "dashboard.bills.upcoming_total",
        "label": "Upcoming bills total",
        "value": round(total_bills, 2),
        "last_updated": bill_last.isoformat() if bill_last else None,
        "status": _status_from_last_updated(bill_last, 86400),
        "source": "bills",
    })

    # Dashboard: unread messages
    with get_db() as db:
        unread_count = db.query(InboxMessage).filter(InboxMessage.is_read == False).count()  # noqa: E712
        msg_last = db.query(func.max(InboxMessage.updated_at)).scalar()
    results.append({
        "id": "dashboard.messages.unread_total",
        "label": "Messages unread",
        "value": unread_count,
        "last_updated": msg_last.isoformat() if msg_last else None,
        "status": _status_from_last_updated(msg_last, 3600),
        "source": "inbox_messages",
    })
    results.append({
        "id": "inbox.unread.count",
        "label": "Unread count",
        "value": unread_count,
        "last_updated": msg_last.isoformat() if msg_last else None,
        "status": _status_from_last_updated(msg_last, 3600),
        "source": "inbox_messages",
    })
    with get_db() as db:
        inbox_total = db.query(InboxMessage).count()
        inbox_last = db.query(func.max(InboxMessage.updated_at)).scalar()
    results.append({
        "id": "inbox.messages.list",
        "label": "Inbox messages list",
        "value": inbox_total,
        "last_updated": inbox_last.isoformat() if inbox_last else None,
        "status": _status_from_last_updated(inbox_last, 300),
        "source": "inbox_messages",
    })

    # Maintenance tasks list + completed count
    with get_db() as db:
        task_total = db.query(MaintenanceTask).count()
        task_completed = db.query(MaintenanceTask).filter(MaintenanceTask.status == "completed").count()
        task_last_any = db.query(func.max(MaintenanceTask.updated_at)).scalar()
    results.append({
        "id": "maintenance.tasks.list",
        "label": "Maintenance tasks list",
        "value": task_total,
        "last_updated": task_last_any.isoformat() if task_last_any else None,
        "status": _status_from_last_updated(task_last_any, 300),
        "source": "maintenance_tasks",
    })
    results.append({
        "id": "maintenance.tasks.completed",
        "label": "Maintenance tasks completed",
        "value": task_completed,
        "last_updated": task_last_any.isoformat() if task_last_any else None,
        "status": _status_from_last_updated(task_last_any, 300),
        "source": "maintenance_tasks",
    })

    # Dashboard: Janitor last run
    with get_db() as db:
        latest_run = (
            db.query(JanitorWizardRun)
            .order_by(JanitorWizardRun.timestamp.desc())
            .first()
        )
        results.append({
            "id": "dashboard.janitor.last_run",
            "label": "Janitor last run",
            "value": latest_run.timestamp.isoformat() if latest_run else None,
            "last_updated": latest_run.timestamp.isoformat() if latest_run else None,
            "status": "ok" if latest_run else "missing",
            "source": "janitor_wizard_runs",
        })
        results.append({
            "id": "system.janitor.last_run",
            "label": "Janitor last run",
            "value": latest_run.timestamp.isoformat() if latest_run else None,
            "last_updated": latest_run.timestamp.isoformat() if latest_run else None,
            "status": "ok" if latest_run else "missing",
            "source": "janitor_wizard_runs",
        })

    # Quick status derived indicators
    try:
        from api.main import get_manager
        manager = get_manager()
        quick = manager.quick_status()
        facts = quick.get("facts", {}) if isinstance(quick, dict) else {}

        # Heartbeat
        heartbeat = facts.get("heartbeat", {}) if isinstance(facts, dict) else {}
        hb_last = _parse_dt(heartbeat.get("last_run"))
        hb_status = "error" if heartbeat.get("error") else _status_from_last_updated(hb_last, 3600)
        results.append({
            "id": "dashboard.heartbeat.open_findings",
            "label": "Heartbeat findings",
            "value": heartbeat.get("open_findings"),
            "last_updated": heartbeat.get("last_run"),
            "status": hb_status,
            "source": "/status (heartbeat)",
        })

        # Identity
        identity = facts.get("identity", {}) if isinstance(facts, dict) else {}
        results.append({
            "id": "dashboard.identity.ready",
            "label": "Identity readiness",
            "value": identity.get("ready"),
            "last_updated": now.isoformat(),
            "status": "error" if identity.get("error") else "ok",
            "source": "/status (identity)",
        })

        # Agents online count
        agents = facts.get("agents", {}) if isinstance(facts, dict) else {}
        total = len(agents)
        online = len([a for a in agents.values() if a.get("state") in ("running", "online")])
        results.append({
            "id": "dashboard.system.agents_online",
            "label": "Agents online",
            "value": {"online": online, "total": total},
            "last_updated": now.isoformat(),
            "status": "ok",
            "source": "/status (agents)",
        })

        # Recent changes
        recent = facts.get("recent_changes", []) if isinstance(facts, dict) else []
        results.append({
            "id": "dashboard.activity.recent_changes",
            "label": "Recent activity",
            "value": len(recent),
            "last_updated": now.isoformat(),
            "status": "ok" if isinstance(recent, list) else "error",
            "source": "/status (recent_changes)",
        })
    except Exception as exc:
        results.append({
            "id": "dashboard.status.quick",
            "label": "Quick status",
            "value": None,
            "last_updated": None,
            "status": "error",
            "source": "/status",
            "error": str(exc),
        })

    # Portfolio change
    try:
        from api.main import get_manager
        manager = get_manager()
        finance = manager.finance
        if finance:
            summary = finance.get_portfolio_summary()
        else:
            summary = {"error": "finance agent not available"}
        if summary.get("error"):
            results.append({
                "id": "dashboard.portfolio.change_pct",
                "label": "Portfolio change %",
                "value": None,
                "last_updated": summary.get("last_updated"),
                "status": "error",
                "source": "/portfolio",
                "error": summary.get("error"),
            })
        else:
            last = _parse_dt(summary.get("last_updated"))
            results.append({
                "id": "dashboard.portfolio.change_pct",
                "label": "Portfolio change %",
                "value": summary.get("day_change_pct"),
                "last_updated": summary.get("last_updated"),
                "status": _status_from_last_updated(last, 3600),
                "source": "/portfolio",
            })
            results.append({
                "id": "system.portfolio.total_value",
                "label": "Portfolio total value",
                "value": summary.get("total_value"),
                "last_updated": summary.get("last_updated"),
                "status": _status_from_last_updated(last, 3600),
                "source": "/portfolio",
            })
            results.append({
                "id": "system.portfolio.cash",
                "label": "Portfolio cash",
                "value": summary.get("cash"),
                "last_updated": summary.get("last_updated"),
                "status": _status_from_last_updated(last, 3600),
                "source": "/portfolio",
            })
            results.append({
                "id": "system.portfolio.day_change",
                "label": "Portfolio day change",
                "value": summary.get("day_change"),
                "last_updated": summary.get("last_updated"),
                "status": _status_from_last_updated(last, 3600),
                "source": "/portfolio",
            })
    except Exception as exc:
        results.append({
            "id": "dashboard.portfolio.change_pct",
            "label": "Portfolio change %",
            "value": None,
            "last_updated": None,
            "status": "error",
            "source": "/portfolio",
            "error": str(exc),
        })

    # System monitor (best-effort)
    try:
        from core.lifecycle import get_lifecycle_manager
        status = get_lifecycle_manager().get_status()
        metrics = {
            "cpu_usage": status.get("cpu_usage"),
            "memory_usage": status.get("memory_usage"),
            "disk_usage": status.get("disk_usage"),
            "uptime": status.get("uptime"),
        }
        def _metric_status(value: Optional[float]) -> str:
            return "ok" if isinstance(value, (int, float)) else "missing"
        results.append({
            "id": "dashboard.system.health.metrics",
            "label": "System health metrics",
            "value": metrics,
            "last_updated": now.isoformat(),
            "status": "ok" if any(v is not None for v in metrics.values()) else "missing",
            "source": "/system/status",
        })
        results.append({
            "id": "agents.system.monitor",
            "label": "System monitor metrics",
            "value": metrics,
            "last_updated": now.isoformat(),
            "status": "ok" if any(v is not None for v in metrics.values()) else "missing",
            "source": "/system/status",
        })
        results.append({
            "id": "system.monitor.cpu",
            "label": "CPU usage",
            "value": metrics.get("cpu_usage"),
            "last_updated": now.isoformat(),
            "status": _metric_status(metrics.get("cpu_usage")),
            "source": "/system/status",
        })
        results.append({
            "id": "system.monitor.memory",
            "label": "Memory usage",
            "value": metrics.get("memory_usage"),
            "last_updated": now.isoformat(),
            "status": _metric_status(metrics.get("memory_usage")),
            "source": "/system/status",
        })
        results.append({
            "id": "system.monitor.disk",
            "label": "Disk usage",
            "value": metrics.get("disk_usage"),
            "last_updated": now.isoformat(),
            "status": _metric_status(metrics.get("disk_usage")),
            "source": "/system/status",
        })
        results.append({
            "id": "system.monitor.uptime",
            "label": "Uptime",
            "value": metrics.get("uptime"),
            "last_updated": now.isoformat(),
            "status": _metric_status(metrics.get("uptime")),
            "source": "/system/status",
        })
    except Exception as exc:
        results.append({
            "id": "dashboard.system.health.metrics",
            "label": "System health metrics",
            "value": None,
            "last_updated": None,
            "status": "error",
            "source": "/system/status",
            "error": str(exc),
        })

    # Agents/fleet status
    try:
        from core.fleet_manager import get_fleet_manager
        fleet = get_fleet_manager().get_fleet_status()
        results.append({
            "id": "agents.fleet.status",
            "label": "Fleet status",
            "value": {
                "fleet_size": fleet.get("fleet_size"),
                "enabled": fleet.get("enabled_count"),
                "available": fleet.get("available_count"),
            },
            "last_updated": now.isoformat(),
            "status": "ok",
            "source": "/api/fleet/agents",
        })
    except Exception as exc:
        results.append({
            "id": "agents.fleet.status",
            "label": "Fleet status",
            "value": None,
            "last_updated": None,
            "status": "error",
            "source": "/api/fleet/agents",
            "error": str(exc),
        })

    return {
        "timestamp": now.isoformat(),
        "results": results,
    }
