"""
MyCasa Pro API - System Routes
System lifecycle, health, backup, and monitoring endpoints.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from typing import Optional, Tuple
from urllib.parse import urlparse

from api.schemas.common import (
    APIError, HealthResponse, SystemStatusResponse,
    StartupRequest, StartupResponse, ShutdownRequest,
    ShutdownResponse, BackupInfo,
    BackupListResponse, BackupCreateResponse, BackupRestoreResponse,
)
from core.lifecycle import get_lifecycle_manager
from core.config import get_config
from core.events_v2 import get_event_bus
from core.settings_typed import get_settings_store
from config.settings import DATABASE_URL
from core.tenant_identity import TenantIdentityManager
from agents.heartbeat_checker import HouseholdHeartbeatChecker, CheckType


# Agent ID aliases between settings/lifecycle and fleet manager
AGENT_SETTINGS_ALIASES = {
    "security-manager": "security",
    "backup-recovery": "backup",
    "mail-skill": "mail",
}

AGENT_FLEET_ALIASES = {
    "security": "security-manager",
    "backup": "backup-recovery",
    "mail": "mail-skill",
}


def _resolve_agent_ids(agent_id: str) -> Tuple[str, str]:
    """Resolve agent IDs for settings/lifecycle vs fleet manager."""
    key = (agent_id or "").strip().lower()
    settings_id = AGENT_SETTINGS_ALIASES.get(key, key)
    fleet_id = AGENT_FLEET_ALIASES.get(key, key)
    return settings_id, fleet_id


router = APIRouter(prefix="/system", tags=["System"])


# ============ STATUS ============

@router.get("/status", response_model=SystemStatusResponse)
async def get_system_status():
    """Get current system status"""
    lifecycle = get_lifecycle_manager()
    status = lifecycle.get_status()
    personal_mode = get_config().PERSONAL_MODE
    status["personal_mode"] = personal_mode
    status["auth_mode"] = "personal" if personal_mode else "account"
    # Attach identity + heartbeat summary
    try:
        identity_manager = TenantIdentityManager(get_config().TENANT_ID)
        identity_manager.ensure_identity_structure()
        status["identity"] = identity_manager.get_identity_status()
    except Exception as exc:
        status["identity"] = {"ready": False, "error": str(exc)}

    try:
        checker = HouseholdHeartbeatChecker(get_config().TENANT_ID)
        state = checker._load_state()
        last_checks = state.get("lastChecks", {})
        last_run = max(last_checks.values()) if last_checks else None
        next_due = checker._calculate_next_check_time().isoformat()
        categories = [c.value for c in CheckType]
        from database import get_db
        from database.models import Notification
        with get_db() as db:
            open_findings = (
                db.query(Notification)
                .filter(Notification.category.in_(categories))
                .filter(Notification.is_read == False)  # noqa: E712
                .count()
            )
        status["heartbeat"] = {
            "last_run": last_run,
            "next_due": next_due,
            "open_findings": open_findings,
            "last_consolidation": state.get("lastConsolidation"),
        }
    except Exception as exc:
        status["heartbeat"] = {"error": str(exc)}
    return status


@router.get("/facts")
async def get_system_facts():
    """Get cached system facts for grounded responses."""
    from core.system_facts import get_system_facts as _get_facts
    return _get_facts()


@router.get("/monitor")
async def get_system_monitor():
    """Get system monitoring data for dashboard"""
    lifecycle = get_lifecycle_manager()
    settings = get_settings_store().get()
    event_bus = get_event_bus()
    
    status = lifecycle.get_status()
    agents_enabled = status.get("agents_enabled", {})
    agents_data = status.get("agents", {})

    # Determine running from lifecycle state if possible
    running = status.get("state") == "running" or status.get("running", False)

    # Fleet status (for richer agent metrics)
    fleet_agents = {}
    try:
        from core.fleet_manager import get_fleet_manager
        fleet_status = get_fleet_manager().get_fleet_status()
        fleet_agents = fleet_status.get("agents", {})
    except Exception:
        fleet_agents = {}

    fleet_to_settings = {
        "security-manager": "security",
        "backup-recovery": "backup",
        "mail-skill": "mail",
    }

    # Build process list for dashboard
    processes = []
    agent_ids = set(agents_enabled.keys()) | set(agents_data.keys())
    for fleet_id in fleet_agents.keys():
        agent_ids.add(fleet_to_settings.get(fleet_id, fleet_id))

    for agent_id in sorted(agent_ids):
        agent_info = agents_data.get(agent_id, {})
        enabled = agents_enabled.get(agent_id, False)
        fleet_id = AGENT_FLEET_ALIASES.get(agent_id, agent_id)
        fleet = fleet_agents.get(fleet_id)

        if fleet:
            fleet_state = fleet.get("state")
            if fleet_state in {"running", "busy", "starting"}:
                state = "running"
            elif fleet_state == "error":
                state = "error"
            elif fleet.get("enabled", enabled):
                state = "idle"
            else:
                state = "stopped"
            pending_tasks = fleet.get("current_requests", 0)
            error_count = 1 if fleet.get("last_error") else 0
        else:
            is_running = agent_info.get("running", False)
            state = "running" if is_running else ("idle" if enabled else "stopped")
            pending_tasks = agent_info.get("pending_tasks", 0)
            error_count = agent_info.get("errors", 0)

        processes.append({
            "id": agent_id,
            "name": agent_info.get("name", fleet.get("name") if fleet else None) or agent_id.title() + " Agent",
            "state": state,
            "uptime": agent_info.get("uptime", 0),
            "memory_mb": 0,
            "cpu_percent": 0,
            "pending_tasks": pending_tasks,
            "error_count": error_count,
            "last_heartbeat": agent_info.get("last_heartbeat"),
            "last_error": fleet.get("last_error") if fleet else None,
        })

    # Count enabled and running agents based on actual statuses
    enabled_count = sum(1 for v in agents_enabled.values() if v)
    running_count = sum(1 for a in processes if a.get("state") == "running")

    # Get database info
    db_status = "unknown"
    db_type = "unknown"
    db_url_display = "unknown"
    db_size_formatted = "—"

    try:
        parsed = urlparse(DATABASE_URL)
        db_type = parsed.scheme or "unknown"
        if db_type.startswith("sqlite"):
            from pathlib import Path
            db_path = Path(parsed.path)
            if db_path.exists():
                db_size = db_path.stat().st_size
                db_size_formatted = (
                    f"{db_size / 1024:.1f} KB"
                    if db_size < 1024 * 1024
                    else f"{db_size / 1024 / 1024:.1f} MB"
                )
            db_url_display = "local"
        else:
            host = parsed.hostname or "localhost"
            port = f":{parsed.port}" if parsed.port else ""
            user = parsed.username or ""
            db_name = parsed.path.lstrip("/")
            db_url_display = f"{db_type}://{user + '@' if user else ''}{host}{port}/{db_name}"

        from database import get_db
        from sqlalchemy import text as _sql_text
        with get_db() as db:
            db.execute(_sql_text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"

    # Get latest backup
    backup_dir = Path(__file__).parent.parent.parent / "data" / "backups"
    backups = sorted(backup_dir.glob("backup_*")) if backup_dir.exists() else []
    last_backup = backups[-1].name.replace("backup_", "") if backups else None
    
    return {
        "running": running,
        "database": {
            "type": db_type,
            "url": db_url_display,
            "status": db_status,
            "size_formatted": db_size_formatted,
            "last_backup": last_backup,
        },
        "agents_enabled": agents_enabled,
        "last_activity": status.get("started_at") or status.get("stopped_at"),
        "resources": {
            "agents_active": running_count,
            "agents_total": enabled_count,
        },
        "processes": processes,
    }


# ============ LIFECYCLE ============

@router.post("/startup", response_model=StartupResponse)
async def system_startup(
    request: StartupRequest = None,
    background_tasks: BackgroundTasks = None
):
    """
    Start the system (idempotent).
    
    - Restores previous state
    - Initializes event bus
    - Starts enabled agents
    """
    lifecycle = get_lifecycle_manager()
    force = request.force if request else False
    result = lifecycle.startup(force=force)
    
    return StartupResponse(
        success=result.get("success", False),
        already_running=result.get("already_running", False),
        agents_started=result.get("agents_started", []),
        restored_from=result.get("restored_from"),
        data=result.get("state"),
        error=APIError(
            error_code="STARTUP_FAILED",
            message=result.get("error", "Unknown error"),
        ) if not result.get("success") else None,
    )


@router.post("/shutdown", response_model=ShutdownResponse)
async def system_shutdown(
    request: ShutdownRequest = None,
    background_tasks: BackgroundTasks = None
):
    """
    Stop the system (idempotent).
    
    - Saves current state
    - Creates backup (optional)
    - Stops all agents
    """
    lifecycle = get_lifecycle_manager()
    
    save_settings = {}
    if request:
        if request.agents_enabled:
            save_settings["agents_enabled"] = request.agents_enabled
        if request.settings:
            save_settings.update(request.settings)
    
    result = lifecycle.shutdown(
        create_backup=request.create_backup if request else True,
        save_settings=save_settings if save_settings else None,
    )
    
    return ShutdownResponse(
        success=result.get("success", False),
        already_stopped=result.get("already_stopped", False),
        backup=result.get("backup"),
        data=result.get("state"),
        error=APIError(
            error_code="SHUTDOWN_FAILED",
            message=result.get("error", "Unknown error"),
        ) if not result.get("success") else None,
    )


# ============ AGENT CONTROL ============

@router.post("/agents/{agent_id}/start")
async def start_agent(agent_id: str):
    """Start a single agent (keeps it enabled)."""
    settings_id, fleet_id = _resolve_agent_ids(agent_id)
    lifecycle = get_lifecycle_manager()

    # Ensure system is running
    status = lifecycle.get_status()
    if status.get("state") != "running":
        startup = lifecycle.startup(force=False)
        if not startup.get("success"):
            raise HTTPException(status_code=500, detail=startup.get("error", "Startup failed"))

    result = lifecycle.set_agent_running(settings_id, True)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Agent not found"))

    # Sync fleet manager enabled state
    try:
        from core.fleet_manager import get_fleet_manager
        fleet = get_fleet_manager()
        fleet.enable_agent(fleet_id)
    except Exception:
        pass

    return {
        "success": True,
        "agent_id": agent_id,
        "settings_id": settings_id,
        "fleet_id": fleet_id,
        "state": result.get("state"),
    }


@router.post("/agents/{agent_id}/stop")
async def stop_agent(agent_id: str):
    """Stop a single agent without disabling it."""
    settings_id, fleet_id = _resolve_agent_ids(agent_id)
    lifecycle = get_lifecycle_manager()

    result = lifecycle.set_agent_running(settings_id, False)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Agent not found"))

    # Sync fleet manager enabled state (idle if enabled)
    try:
        from core.fleet_manager import get_fleet_manager
        fleet = get_fleet_manager()
        if result.get("enabled"):
            fleet.enable_agent(fleet_id)
        else:
            fleet.disable_agent(fleet_id)
    except Exception:
        pass

    return {
        "success": True,
        "agent_id": agent_id,
        "settings_id": settings_id,
        "fleet_id": fleet_id,
        "state": result.get("state"),
    }


# ============ HEALTH ============

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    lifecycle = get_lifecycle_manager()
    status = lifecycle.get_status()
    
    return HealthResponse(
        status="ok",
        system_running=status.get("running", False),
        database="ok",
        event_bus="ok",
    )


# ============ EVENTS ============

@router.get("/events")
async def get_event_log(
    limit: int = 100,
    event_type: Optional[str] = None,
):
    """Get recent events from the event bus"""
    event_bus = get_event_bus()
    return {
        "events": event_bus.get_event_log(limit=limit, event_type=event_type),
        "total": len(event_bus._event_log),
    }


@router.get("/events/dead-letter")
async def get_dead_letter(limit: int = 50):
    """Get events in dead-letter queue"""
    event_bus = get_event_bus()
    return {
        "events": event_bus.get_dead_letter(limit=limit),
        "total": len(event_bus._dead_letter),
    }


@router.get("/events/trace/{correlation_id}")
async def trace_events(correlation_id: str):
    """Trace all events with a correlation ID"""
    event_bus = get_event_bus()
    return {
        "correlation_id": correlation_id,
        "events": event_bus.get_events_by_correlation(correlation_id),
    }


# ============ BACKUP ============

backup_router = APIRouter(prefix="/backup", tags=["Backup"])


@backup_router.post("/export", response_model=BackupCreateResponse)
async def export_backup():
    """Create a backup of the database and state"""
    lifecycle = get_lifecycle_manager()
    result = lifecycle.create_backup()
    
    return BackupCreateResponse(
        success=result.get("success", False),
        timestamp=result.get("timestamp", ""),
        backup_path=result.get("backup_path", ""),
        files=result.get("files", []),
        error=APIError(
            error_code="BACKUP_FAILED",
            message=result.get("error", "Unknown error"),
        ) if not result.get("success") else None,
    )


@backup_router.get("/list", response_model=BackupListResponse)
async def list_backups():
    """List all available backups"""
    lifecycle = get_lifecycle_manager()
    backups = lifecycle.list_backups()
    
    return BackupListResponse(
        success=True,
        backups=[BackupInfo(**b) for b in backups],
    )


@backup_router.post("/restore/{backup_name}", response_model=BackupRestoreResponse)
async def restore_backup(backup_name: str):
    """Restore from a specific backup"""
    lifecycle = get_lifecycle_manager()
    result = lifecycle.restore_backup(backup_name)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "RESTORE_FAILED",
                "message": result.get("error", "Unknown error"),
            }
        )
    
    return BackupRestoreResponse(
        success=True,
        backup_name=backup_name,
        restored_files=result.get("restored_files", []),
    )


# Include backup routes
router.include_router(backup_router)
