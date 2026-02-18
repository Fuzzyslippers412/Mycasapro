"""
System Facts Cache
------------------
Local-only, auditable system facts used for grounding agent responses.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Optional
import json

from config.settings import DATA_DIR

SYSTEM_FACTS_TTL = timedelta(seconds=20)

SYSTEM_FACTS_RULES = """
System Facts Rules:
- Use ONLY the provided System Facts for any status, counts, or health statements.
- If a value is missing, respond with "unavailable" and suggest a next step.
- Never invent numbers, times, or success states.
- Claims about actions must include a real ID from the database.
- Only mention LLM provider details if the user explicitly asks.
""".strip()

SYSTEM_GLOSSARY = """
Glossary:
- Task: a row in maintenance_tasks.
- Reminder: a notification entry linked to a task or bill.
- Message: a row in inbox_messages (email/whatsapp).
- Backup: a recorded backup entry in data/backups.
""".strip()

_cache_lock = Lock()
_cache_data: Optional[Dict[str, Any]] = None
_cache_ts: Optional[datetime] = None


def _facts_path() -> Path:
    return DATA_DIR / "system_facts.json"


def _build_system_facts() -> Dict[str, Any]:
    now = datetime.utcnow()
    facts: Dict[str, Any] = {
        "generated_at": now.isoformat(),
        "sources": {},
    }

    try:
        from database import get_db
        from database.models import MaintenanceTask, Notification, AgentLog
        with get_db() as db:
            pending_tasks = (
                db.query(MaintenanceTask)
                .filter(MaintenanceTask.status.in_(["pending", "in_progress"]))
                .count()
            )
            upcoming = (
                db.query(MaintenanceTask)
                .filter(MaintenanceTask.status == "pending", MaintenanceTask.scheduled_date != None)  # noqa: E711
                .order_by(MaintenanceTask.scheduled_date.asc())
                .limit(3)
                .all()
            )
            alerts = (
                db.query(Notification)
                .filter(Notification.is_read == False, Notification.priority.in_(["high", "critical"]))  # noqa: E712
                .order_by(Notification.created_at.desc())
                .limit(5)
                .all()
            )
            recent = (
                db.query(AgentLog)
                .order_by(AgentLog.created_at.desc())
                .limit(5)
                .all()
            )
        facts["status"] = {
            "timestamp": now.isoformat(),
            "facts": {
                "tasks": {
                    "pending": pending_tasks,
                    "upcoming": [
                        {"title": t.title, "date": t.scheduled_date.isoformat() if t.scheduled_date else None}
                        for t in upcoming
                    ],
                },
                "alerts": [
                    {"title": a.title, "priority": a.priority, "category": a.category}
                    for a in alerts
                ],
                "recent_changes": [
                    {
                        "agent": r.agent,
                        "action": r.action,
                        "status": r.status,
                        "time": r.created_at.isoformat(),
                    }
                    for r in recent
                ],
            },
        }
        facts["sources"]["status"] = "database"
    except Exception as exc:
        facts["status_error"] = str(exc)
        facts["sources"]["status"] = "database:error"

    try:
        from core.settings_typed import get_settings_store
        system = get_settings_store().get().system
        facts["llm"] = {
            "provider": system.llm_provider,
            "auth_type": system.llm_auth_type,
            "base_url": system.llm_base_url,
            "model": system.llm_model,
            "oauth_connected": bool(system.llm_oauth_connected),
            "api_key_set": bool(system.llm_api_key_set),
        }
        facts["sources"]["llm"] = "settings.system"
    except Exception as exc:
        facts["llm_error"] = str(exc)
        facts["sources"]["llm"] = "settings.system:error"

    try:
        from core.lifecycle import get_lifecycle_manager
        lifecycle = get_lifecycle_manager().get_status()
        facts["lifecycle"] = {
            "state": lifecycle.get("state"),
            "running": lifecycle.get("running"),
            "started_at": lifecycle.get("started_at"),
            "uptime_s": lifecycle.get("uptime_seconds"),
            "agents": lifecycle.get("agents", {}),
            "agents_enabled": lifecycle.get("agents_enabled", {}),
        }
        facts["sources"]["lifecycle"] = "lifecycle.get_status"
    except Exception as exc:
        facts["lifecycle_error"] = str(exc)
        facts["sources"]["lifecycle"] = "lifecycle.get_status:error"

    try:
        from core.tenant_identity import TenantIdentityManager
        from agents.heartbeat_checker import HouseholdHeartbeatChecker, CheckType
        from core.config import get_config
        from database import get_db
        from database.models import Notification
        tenant_id = get_config().TENANT_ID
        identity_manager = TenantIdentityManager(tenant_id)
        identity_manager.ensure_identity_structure()
        facts["identity"] = identity_manager.get_identity_status()
        checker = HouseholdHeartbeatChecker(tenant_id)
        state = checker._load_state()
        last_checks = state.get("lastChecks", {})
        last_run = max(last_checks.values()) if last_checks else None
        next_due = checker._calculate_next_check_time().isoformat()
        categories = [c.value for c in CheckType]
        with get_db() as db:
            open_findings = (
                db.query(Notification)
                .filter(Notification.category.in_(categories))
                .filter(Notification.is_read == False)  # noqa: E712
                .count()
            )
        facts["heartbeat"] = {
            "last_run": last_run,
            "next_due": next_due,
            "open_findings": open_findings,
            "last_consolidation": state.get("lastConsolidation"),
        }
        facts["sources"]["identity"] = "tenant_identity"
        facts["sources"]["heartbeat"] = "heartbeat_checker"
    except Exception as exc:
        facts["identity_error"] = str(exc)
        facts["heartbeat_error"] = str(exc)

    return facts


def get_system_facts(force: bool = False) -> Dict[str, Any]:
    global _cache_data, _cache_ts
    now = datetime.utcnow()
    with _cache_lock:
        if not force and _cache_data and _cache_ts and now - _cache_ts < SYSTEM_FACTS_TTL:
            return _cache_data
        facts = _build_system_facts()
        _cache_data = facts
        _cache_ts = now
        _persist_facts(facts)
        return facts


def _persist_facts(facts: Dict[str, Any]) -> None:
    path = _facts_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(facts, indent=2))
    except Exception:
        pass


def format_system_facts_for_prompt(facts: Dict[str, Any]) -> str:
    try:
        status = facts.get("status", {}) if isinstance(facts, dict) else {}
        status_facts = status.get("facts", {}) if isinstance(status, dict) else {}
        tasks = status_facts.get("tasks", {}) if isinstance(status_facts, dict) else {}
        alerts = status_facts.get("alerts", []) if isinstance(status_facts, dict) else []
        recent = status_facts.get("recent_changes", []) if isinstance(status_facts, dict) else []
        lifecycle = facts.get("lifecycle", {}) if isinstance(facts, dict) else {}
        agents_enabled = lifecycle.get("agents_enabled", {}) if isinstance(lifecycle, dict) else {}
        agents = lifecycle.get("agents", {}) if isinstance(lifecycle, dict) else {}
        agent_states = {}
        if isinstance(agents, dict):
            for agent_id, info in agents.items():
                if isinstance(info, dict):
                    agent_states[agent_id] = {
                        "running": info.get("running"),
                        "enabled": info.get("enabled"),
                        "state": info.get("state"),
                    }
        summary = {
            "generated_at": facts.get("generated_at"),
            "lifecycle": {
                "state": lifecycle.get("state"),
                "running": lifecycle.get("running"),
                "agents_enabled": len(agents_enabled),
                "agents_running": len([a for a in agents.values() if a.get("running")]) if isinstance(agents, dict) else 0,
                "agents": agent_states,
            },
            "tasks": {
                "pending": tasks.get("pending"),
                "upcoming": tasks.get("upcoming")[:3] if isinstance(tasks.get("upcoming"), list) else [],
            },
            "alerts_count": len(alerts) if isinstance(alerts, list) else 0,
            "recent_changes_count": len(recent) if isinstance(recent, list) else 0,
            "identity": facts.get("identity"),
            "heartbeat": facts.get("heartbeat"),
            "llm": facts.get("llm"),
        }
        return json.dumps(summary, indent=2)
    except Exception:
        return str(facts)
