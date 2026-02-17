"""
MyCasa Pro - Live System Status API
Real-time status of all system components.

This provides the comprehensive view Lamido wants:
- Agents and their states
- SecondBrain vault stats
- Connectors (WhatsApp, Gmail, etc.)
- Chat sessions
- Shared context
- Memory/files
- Scheduled jobs
"""
from fastapi import APIRouter
from typing import Dict, Any
from datetime import datetime

from config.settings import VAULT_PATH, DEFAULT_TENANT_ID
from core.tenant_identity import TenantIdentityManager
from agents.heartbeat_checker import HouseholdHeartbeatChecker, CheckType

router = APIRouter(prefix="/system", tags=["System Live"])

# Map lifecycle/settings IDs to fleet IDs where they differ
AGENT_FLEET_ALIASES = {
    "security": "security-manager",
    "backup": "backup-recovery",
    "mail": "mail-skill",
}


@router.get("/live")
async def get_live_status() -> Dict[str, Any]:
    """
    Get comprehensive live status of all system components.
    This is the main endpoint for the System tab.
    """
    return {
        "timestamp": datetime.now().isoformat(),
        "agents": await _get_agent_status(),
        "secondbrain": await _get_secondbrain_status(),
        "connectors": await _get_connector_status(),
        "chat": await _get_chat_status(),
        "shared_context": await _get_shared_context_status(),
        "memory": await _get_memory_status(),
        "scheduled_jobs": await _get_scheduled_jobs(),
        "household_heartbeat": await _get_household_heartbeat_status(),
    }


async def _get_agent_status() -> Dict[str, Any]:
    """Get status of all agents - synced with actual running instances"""
    try:
        # Get real agent status from lifecycle manager
        from core.lifecycle import get_lifecycle_manager
        from core.settings_typed import get_settings_store
        lifecycle = get_lifecycle_manager()
        system_status = lifecycle.get_status()

        agents_data = system_status.get("agents", {})
        # Source of truth for enabled flags
        agents_enabled = get_settings_store().get().get_enabled_agents()

        # Fleet status for richer runtime state
        fleet_agents = {}
        try:
            from core.fleet_manager import get_fleet_manager
            fleet_status = get_fleet_manager().get_fleet_status()
            fleet_agents = fleet_status.get("agents", {})
        except Exception:
            fleet_agents = {}

        # All configured agents in the system
        all_agent_ids = [
            "manager", "finance", "maintenance", "contractors",
            "projects", "janitor", "security", "mail", "backup"
        ]

        agents = {}
        for agent_id in all_agent_ids:
            agent_info = agents_data.get(agent_id, {})
            is_enabled = agents_enabled.get(agent_id, False)
            is_running = agent_info.get("running", False)
            fleet_id = AGENT_FLEET_ALIASES.get(agent_id, agent_id)
            fleet = fleet_agents.get(fleet_id)

            # Determine accurate status
            if fleet:
                fleet_state = fleet.get("state")
                if fleet_state in {"running", "busy", "starting"}:
                    status = "active"
                elif fleet_state == "error":
                    status = "error"
                elif is_enabled:
                    status = "available"
                else:
                    status = "offline"
            else:
                if is_running:
                    status = "active"
                elif is_enabled:
                    status = "available"
                else:
                    status = "offline"

            agents[agent_id] = {
                "status": status,
                "loaded": is_running,
                "health": "healthy" if status == "active" else "unknown",
                "pending_tasks": (
                    fleet.get("current_requests", 0) if fleet else agent_info.get("pending_tasks", 0)
                ),
                "errors": (
                    1 if fleet and fleet.get("last_error") else agent_info.get("errors", 0)
                ),
                "uptime": agent_info.get("uptime", 0),
            }

        # Count accurate stats
        active = sum(1 for a in agents.values() if a.get("status") == "active")
        available = sum(1 for a in agents.values() if a.get("status") == "available")
        offline = sum(1 for a in agents.values() if a.get("status") == "offline")

        # Detect system running state from lifecycle
        running = system_status.get("state") == "running" or system_status.get("running", False)

        return {
            "agents": agents,
            "stats": {
                "total": len(agents),
                "active": active,
                "available": available,
                "offline": offline,
                "running": running,
            }
        }
    except Exception as e:
        # Fallback to basic status if lifecycle manager fails
        print(f"[system_live] Error getting agent status: {e}")
        return {
            "agents": {
                "manager": {"status": "unknown", "loaded": False, "health": "unknown"},
                "finance": {"status": "unknown", "loaded": False, "health": "unknown"},
                "maintenance": {"status": "unknown", "loaded": False, "health": "unknown"},
                "contractors": {"status": "unknown", "loaded": False, "health": "unknown"},
                "projects": {"status": "unknown", "loaded": False, "health": "unknown"},
                "janitor": {"status": "unknown", "loaded": False, "health": "unknown"},
                "security": {"status": "unknown", "loaded": False, "health": "unknown"},
                "mail": {"status": "unknown", "loaded": False, "health": "unknown"},
                "backup": {"status": "unknown", "loaded": False, "health": "unknown"},
            },
            "stats": {
                "total": 9,
                "active": 0,
                "available": 0,
                "offline": 9,
            }
        }


async def _get_secondbrain_status() -> Dict[str, Any]:
    """Get SecondBrain vault status"""
    vault_path = VAULT_PATH
    
    if not vault_path.exists():
        return {"status": "not_found", "path": str(vault_path)}
    
    # Count notes per folder
    folders = {}
    total_notes = 0
    
    for folder in vault_path.iterdir():
        if folder.is_dir():
            notes = list(folder.glob("sb_*.md"))
            count = len(notes)
            folders[folder.name] = count
            total_notes += count
    
    # Get recent notes
    recent_notes = []
    all_notes = list(vault_path.glob("**/sb_*.md"))
    all_notes.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    for note in all_notes[:5]:
        recent_notes.append({
            "id": note.stem,
            "folder": note.parent.name,
            "modified": datetime.fromtimestamp(note.stat().st_mtime).isoformat(),
        })
    
    return {
        "status": "healthy",
        "path": str(vault_path),
        "stats": {
            "total_notes": total_notes,
            "folders": folders,
        },
        "recent_notes": recent_notes,
    }


async def _get_connector_status() -> Dict[str, Any]:
    """Get status of all connectors"""
    connectors = {}

    def _label(status) -> str:
        try:
            from connectors.base import ConnectorStatus
            if status == ConnectorStatus.HEALTHY:
                return "healthy"
            if status == ConnectorStatus.DEGRADED:
                return "degraded"
            if status in {ConnectorStatus.FAILED, ConnectorStatus.RATE_LIMITED}:
                return "error"
            if status == ConnectorStatus.DISABLED:
                return "disabled"
            if status == ConnectorStatus.AUTHENTICATING:
                return "authenticating"
        except Exception:
            pass
        return "unknown"
    
    # WhatsApp connector
    try:
        from connectors.whatsapp import WhatsAppConnector
        wa = WhatsAppConnector()
        contacts = wa.get_all_contacts()
        connectors["whatsapp"] = {
            "status": "healthy",
            "contacts_loaded": len(contacts),
            "contacts": [c["name"] for c in contacts[:5]],
        }
    except Exception as e:
        connectors["whatsapp"] = {"status": "error", "error": str(e)}
    
    # Gmail connector (check if configured)
    try:
        from connectors.gmail.connector import GmailConnector
        gmail = GmailConnector()
        gmail_status = await gmail.health_check(DEFAULT_TENANT_ID)
        connectors["gmail"] = {
            "status": _label(gmail_status),
            "note": "gog CLI required" if not getattr(gmail, "_gog_available", True) else None,
        }
    except Exception as e:
        connectors["gmail"] = {"status": "error", "error": str(e)}
    
    # Calendar connector
    try:
        from connectors.calendar.connector import CalendarConnector
        calendar = CalendarConnector()
        calendar_status = await calendar.health_check(DEFAULT_TENANT_ID)
        connectors["calendar"] = {
            "status": _label(calendar_status),
            "note": "gog CLI required" if not getattr(calendar, "_gog_available", True) else None,
        }
    except Exception as e:
        connectors["calendar"] = {"status": "error", "error": str(e)}
    
    return {
        "connectors": connectors,
        "stats": {
            "total": len(connectors),
            "healthy": sum(1 for c in connectors.values() if c.get("status") == "healthy"),
        }
    }


async def _get_chat_status() -> Dict[str, Any]:
    """Get chat session status"""
    try:
        from database import get_db
        from database.models import ChatConversation, ChatMessage
        from datetime import timedelta

        with get_db() as db:
            conversations = (
                db.query(ChatConversation)
                .order_by(ChatConversation.updated_at.desc())
                .limit(20)
                .all()
            )
            sessions = []
            for conv in conversations:
                last_msg = (
                    db.query(ChatMessage)
                    .filter(ChatMessage.conversation_id == conv.id)
                    .order_by(ChatMessage.created_at.desc())
                    .first()
                )
                count = (
                    db.query(ChatMessage)
                    .filter(ChatMessage.conversation_id == conv.id)
                    .count()
                )
                sessions.append({
                    "id": conv.id,
                    "message_count": count,
                    "last_activity": last_msg.created_at.isoformat() if last_msg else None,
                })

            total_messages = db.query(ChatMessage).count()
            recent_cutoff = datetime.now() - timedelta(hours=12)
            active_sessions = sum(
                1 for session in sessions
                if session.get("last_activity") and datetime.fromisoformat(session["last_activity"]) > recent_cutoff
            )

        return {
            "active_sessions": active_sessions,
            "sessions": sessions,
            "total_messages": total_messages,
        }
    except Exception as e:
        return {"active_sessions": 0, "sessions": [], "total_messages": 0, "error": str(e)}


async def _get_shared_context_status() -> Dict[str, Any]:
    """Get shared context status"""
    try:
        from core.shared_context import get_shared_context
        ctx = get_shared_context()
        
        user = ctx.get_user_profile()
        memory = ctx.get_long_term_memory()
        contacts = ctx.get_contacts()
        recent = ctx.get_recent_memory(days=3)
        
        return {
            "status": "healthy",
            "sources": {
                "user_profile": len(user) > 0,
                "user_profile_chars": len(user),
                "long_term_memory": len(memory) > 0,
                "memory_chars": len(memory),
                "contacts": len(contacts),
                "recent_memory_days": len(recent),
            }
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def _get_memory_status() -> Dict[str, Any]:
    """Get memory file status"""
    manager = TenantIdentityManager(DEFAULT_TENANT_ID)
    manager.ensure_identity_structure()
    tenant_dir = manager.tenant_dir
    memory_dir = tenant_dir / "memory"

    files = {}
    for filename in manager.REQUIRED_FILES + manager.OPTIONAL_FILES:
        files[filename] = (tenant_dir / filename).exists()

    daily_files = list(memory_dir.glob("*.md")) if memory_dir.exists() else []
    today = datetime.now().strftime("%Y-%m-%d")
    today_file = memory_dir / f"{today}.md"
    today_chars = 0
    if today_file.exists():
        try:
            today_chars = len(today_file.read_text())
        except Exception:
            today_chars = 0

    return {
        "workspace": str(tenant_dir),
        "core_files": files,
        "daily_memory": {
            "total_files": len(daily_files),
            "today_exists": today_file.exists(),
            "today_chars": today_chars,
        }
    }


async def _get_scheduled_jobs() -> Dict[str, Any]:
    """Get scheduled job status"""
    try:
        from agents.scheduler import get_scheduler, ScheduleFrequency

        scheduler = get_scheduler()
        jobs = []

        def _describe(job) -> str:
            freq = job.frequency
            if freq == ScheduleFrequency.HOURLY:
                return f"Hourly @ :{job.minute:02d}"
            if freq == ScheduleFrequency.DAILY:
                return f"Daily @ {job.hour:02d}:{job.minute:02d}"
            if freq == ScheduleFrequency.WEEKLY:
                return f"Weekly (day {job.day_of_week}) @ {job.hour:02d}:{job.minute:02d}"
            if freq == ScheduleFrequency.MONTHLY:
                return f"Monthly (day {job.day_of_month}) @ {job.hour:02d}:{job.minute:02d}"
            return "Once"

        for job in scheduler.list_jobs(include_disabled=False):
            jobs.append({
                "id": job.id,
                "name": job.name,
                "schedule": _describe(job),
                "last_run": job.last_run.isoformat() if job.last_run else None,
                "next_run": job.next_run.isoformat() if job.next_run else None,
            })

        return {
            "active_jobs": len(jobs),
            "jobs": jobs,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def _get_household_heartbeat_status() -> Dict[str, Any]:
    """Get household heartbeat status and findings summary."""
    try:
        checker = HouseholdHeartbeatChecker(DEFAULT_TENANT_ID)
        state = checker._load_state()
        last_checks = state.get("lastChecks", {})
        last_run = None
        if last_checks:
            last_run = max(last_checks.values())

        next_due = checker._calculate_next_check_time().isoformat()

        from database import get_db
        from database.models import Notification
        categories = [c.value for c in CheckType]
        with get_db() as db:
            open_findings = (
                db.query(Notification)
                .filter(Notification.category.in_(categories))
                .filter(Notification.is_read == False)  # noqa: E712
                .count()
            )

        return {
            "last_run": last_run,
            "next_due": next_due,
            "open_findings": open_findings,
            "last_consolidation": state.get("lastConsolidation"),
        }
    except Exception as e:
        return {"error": str(e)}


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Quick health check for all components"""
    checks = {}
    
    # Database
    try:
        from database import get_db
        with get_db() as db:
            db.execute("SELECT 1")
        checks["database"] = "healthy"
    except Exception as e:
        checks["database"] = f"error: {e}"
    
    # SecondBrain
    vault = VAULT_PATH
    checks["secondbrain_vault"] = "healthy" if vault.exists() else "not_found"
    
    # Shared context
    try:
        from core.shared_context import get_shared_context
        ctx = get_shared_context()
        ctx.get_contacts()
        checks["shared_context"] = "healthy"
    except Exception as e:
        checks["shared_context"] = f"error: {e}"
    
    # WhatsApp connector
    try:
        from connectors.whatsapp import WhatsAppConnector
        wa = WhatsAppConnector()
        wa.get_all_contacts()
        checks["whatsapp_connector"] = "healthy"
    except Exception as e:
        checks["whatsapp_connector"] = f"error: {e}"
    
    all_healthy = all(v == "healthy" for v in checks.values())
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "checks": checks,
        "timestamp": datetime.now().isoformat(),
    }
