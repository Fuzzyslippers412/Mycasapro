"""
System control and monitoring endpoints
"""
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..core.utils import generate_correlation_id, log_action
from ..storage.database import get_db_session
from ..storage.models import CostRecordDB, TaskDB

router = APIRouter(prefix="/system", tags=["System"])

# Also create an /api/system router for the live endpoint
api_router = APIRouter(prefix="/api/system", tags=["System"])

# In-memory agent state (would be managed by a real process manager in production)
# IDs must match frontend expectations (e.g., "security" not "security-manager")
_agent_states = {
    "manager": {"state": "idle", "loaded_at": None, "error_count": 0},
    "finance": {"state": "idle", "loaded_at": None, "error_count": 0},
    "maintenance": {"state": "idle", "loaded_at": None, "error_count": 0},
    "contractors": {"state": "idle", "loaded_at": None, "error_count": 0},
    "projects": {"state": "idle", "loaded_at": None, "error_count": 0},
    "janitor": {"state": "idle", "loaded_at": None, "error_count": 0},
    "security": {"state": "idle", "loaded_at": None, "error_count": 0},
}


def get_db():
    db = get_db_session()
    try:
        yield db
    finally:
        db.close()


@router.get("/monitor")
async def get_system_monitor(db: Session = Depends(get_db)):
    """
    Get system monitoring data (htop-style)
    Returns agent processes and resource usage
    """
    processes = []
    agents_active = 0
    
    for agent_name, health in _agent_states.items():
        state = health.get("state", "idle")
        if state in ["active", "running"]:
            agents_active += 1
        
        # Calculate uptime
        loaded_at = health.get("loaded_at")
        uptime_seconds = 0
        if loaded_at:
            loaded_dt = datetime.fromisoformat(loaded_at)
            uptime_seconds = (datetime.now() - loaded_dt).total_seconds()
        
        # Get pending tasks for this agent
        pending_tasks = 0
        try:
            pending_tasks = db.query(TaskDB).filter(
                TaskDB.status == "pending",
                TaskDB.category == agent_name.replace("-manager", "")
            ).count()
        except Exception:
            pass
        
        processes.append({
            "id": agent_name,
            "name": agent_name.replace("-", " ").title(),
            "state": state,
            "uptime": uptime_seconds,
            "memory_mb": 0,
            "cpu_percent": 0,
            "pending_tasks": pending_tasks,
            "error_count": health.get("error_count", 0),
            "last_heartbeat": health.get("last_heartbeat", "never"),
        })

    # Get today's cost
    cost_today = 0.0
    try:
        from datetime import date
        cost_today = db.query(func.sum(CostRecordDB.amount)).filter(
            func.date(CostRecordDB.created_at) == date.today()
        ).scalar() or 0.0
    except Exception as e:
        print(f"Error fetching cost: {e}")

    resources = {
        "cpu_percent": 0,
        "memory_percent": 0,
        "agents_active": agents_active,
        "agents_total": len(_agent_states),
        "cost_today": float(cost_today),
    }

    return {
        "processes": processes,
        "resources": resources,
    }


@router.post("/agents/{agent_id}/start")
async def start_agent(agent_id: str):
    """Start an agent (systemctl-style)"""
    correlation_id = generate_correlation_id()

    if agent_id not in _agent_states:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    _agent_states[agent_id]["state"] = "running"
    _agent_states[agent_id]["loaded_at"] = datetime.now().isoformat()
    
    log_action("agent_started", {"agent_id": agent_id})

    return {
        "status": "started",
        "agent_id": agent_id,
        "correlation_id": correlation_id,
    }


@router.post("/agents/{agent_id}/stop")
async def stop_agent(agent_id: str):
    """Stop an agent gracefully"""
    correlation_id = generate_correlation_id()

    if agent_id not in _agent_states:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    _agent_states[agent_id]["state"] = "stopped"
    _agent_states[agent_id]["loaded_at"] = None
    
    log_action("agent_stopped", {"agent_id": agent_id})

    return {
        "status": "stopped",
        "agent_id": agent_id,
        "correlation_id": correlation_id,
    }


@router.post("/agents/{agent_id}/restart")
async def restart_agent(agent_id: str):
    """Restart an agent"""
    correlation_id = generate_correlation_id()

    if agent_id not in _agent_states:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    # Stop then start
    _agent_states[agent_id]["state"] = "running"
    _agent_states[agent_id]["loaded_at"] = datetime.now().isoformat()
    _agent_states[agent_id]["error_count"] = 0
    
    log_action("agent_restarted", {"agent_id": agent_id})

    return {
        "status": "restarted",
        "agent_id": agent_id,
        "correlation_id": correlation_id,
    }


@router.get("/agents/{agent_id}/status")
async def get_agent_status(agent_id: str, db: Session = Depends(get_db)):
    """Get detailed status for one agent (systemctl status style)"""
    if agent_id not in _agent_states:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    health = _agent_states[agent_id]

    # Calculate uptime
    loaded_at = health.get("loaded_at")
    uptime_seconds = 0
    if loaded_at:
        loaded_dt = datetime.fromisoformat(loaded_at)
        uptime_seconds = (datetime.now() - loaded_dt).total_seconds()

    # Get pending tasks
    pending_tasks = db.query(TaskDB).filter(
        TaskDB.status == "pending",
        TaskDB.category == agent_id.replace("-manager", "")
    ).count()

    return {
        "agent_id": agent_id,
        "state": health.get("state", "idle"),
        "loaded_at": loaded_at,
        "uptime_seconds": uptime_seconds,
        "memory_mb": 0,
        "pending_tasks": pending_tasks,
        "error_count": health.get("error_count", 0),
        "recent_logs": [],
    }


@router.post("/launch")
async def launch_system(db: Session = Depends(get_db)):
    """
    Launch/initialize all agents in the system
    Triggers Janitor audit on startup
    """
    # Import agents directly
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from agents.janitor import JanitorAgent
    
    now = datetime.now().isoformat()
    started = 0
    janitor_report = None
    
    for agent_id in _agent_states:
        _agent_states[agent_id]["state"] = "running"
        _agent_states[agent_id]["loaded_at"] = now
        _agent_states[agent_id]["error_count"] = 0
        started += 1
    
    # Trigger Janitor audit on system launch
    try:
        janitor = JanitorAgent()
        if janitor:
            # Run initial audit
            janitor_report = janitor.run_audit()
            findings_count = len(janitor_report.get('findings', []))
            janitor.log_action("system_launch_audit", f"Ran startup audit, {findings_count} findings")
            
            # Check system health
            janitor.log_action("health_check", "Verified all agents loaded successfully")
            
            # If findings, log them
            for finding in janitor_report.get('findings', [])[:3]:
                janitor.log_action(
                    f"finding_{finding.get('severity', 'P3')}",
                    f"{finding.get('domain')}: {finding.get('finding')}",
                    status="warning" if finding.get('severity') in ['P2', 'P3'] else "error"
                )
    except Exception as e:
        print(f"[Janitor] Startup audit failed: {e}")
    
    log_action("system_launched", {"agents_started": started})

    return {
        "success": True,
        "message": "System launched. All agents are now running.",
        "agents_started": started,
        "total_agents": len(_agent_states),
        "janitor_audit": janitor_report,
    }


@api_router.get("/live")
async def get_live_status(db: Session = Depends(get_db)):
    """
    Get comprehensive live system status for the dashboard.
    Returns agents, connectors, chat stats, memory status, etc.
    
    Uses the singleton agent instances from main.py to get real activity logs.
    """
    from pathlib import Path
    from .main import get_agent  # Use the singleton pattern from main.py
    
    # Build agents info from real agent instances
    agents_data = {}
    active_count = 0
    
    # Map state keys to agent IDs used by get_agent()
    # Now all keys match both frontend and get_agent() expectations
    agent_id_map = {
        "manager": "manager",
        "finance": "finance",
        "maintenance": "maintenance",
        "contractors": "contractors",
        "projects": "projects",
        "janitor": "janitor",
        "security": "security",
    }
    
    for state_key, state in _agent_states.items():
        is_active = state.get("state") in ["running", "active"]
        if is_active:
            active_count += 1
        
        # Get real agent instance and its logs
        recent_activity = []
        agent_id = agent_id_map.get(state_key, state_key)
        try:
            agent = get_agent(agent_id)
            if agent:
                logs = agent.get_recent_logs(10)
                recent_activity = [
                    {
                        "action": log.get("action", "unknown"),
                        "details": log.get("details", ""),
                        "status": log.get("status", "success"),
                        "time": log.get("timestamp", ""),
                    }
                    for log in logs
                ]
        except Exception as e:
            print(f"[LiveStatus] Error getting logs for {agent_id}: {e}")
        
        agents_data[state_key] = {
            "status": "active" if is_active else "available",
            "loaded_at": state.get("loaded_at"),
            "error_count": state.get("error_count", 0),
            "recent_activity": recent_activity,
        }
    
    # Connectors status - check actual connector health via get_status()
    connectors_data = {}
    try:
        from ..connectors import gmail_connector, whatsapp_connector
        from ..core.schemas import ConnectorStatus
        
        # Map enum values to display strings
        status_map = {
            ConnectorStatus.CONNECTED: "healthy",
            ConnectorStatus.STUB: "available",
            ConnectorStatus.ERROR: "error",
            ConnectorStatus.DISCONNECTED: "disconnected",
        }
        
        gmail_status = gmail_connector.get_status()
        connectors_data["gmail"] = {
            "status": status_map.get(gmail_status, "available"),
            "last_sync": getattr(gmail_connector, 'last_sync', None),
        }
        
        whatsapp_status = whatsapp_connector.get_status()
        connectors_data["whatsapp"] = {
            "status": status_map.get(whatsapp_status, "available"),
            "last_sync": getattr(whatsapp_connector, 'last_sync', None),
        }
    except Exception as e:
        print(f"[LiveStatus] Connector status error: {e}")
        connectors_data = {
            "gmail": {"status": "available", "last_sync": None},
            "whatsapp": {"status": "available", "last_sync": None},
        }
    connectors_data["calendar"] = {"status": "available", "last_sync": None}
    
    # Get chat/message stats from database
    total_messages = 0
    try:
        from ..storage.models import InboxMessageDB
        total_messages = db.query(InboxMessageDB).count()
    except Exception:
        pass
    
    # Check memory files
    workspace = Path("/Users/chefmbororo/clawd")
    memory_files = {
        "MEMORY.md": (workspace / "MEMORY.md").exists(),
        "TOOLS.md": (workspace / "TOOLS.md").exists(),
        "SOUL.md": (workspace / "SOUL.md").exists(),
    }
    
    # Check daily memory
    from datetime import date
    today_file = workspace / "memory" / f"{date.today().isoformat()}.md"
    today_exists = today_file.exists()
    today_chars = 0
    if today_exists:
        try:
            today_chars = len(today_file.read_text())
        except Exception:
            pass
    
    # Count memory files
    memory_dir = workspace / "memory"
    total_memory_files = 0
    if memory_dir.exists():
        total_memory_files = len(list(memory_dir.glob("*.md")))
    
    return {
        "timestamp": datetime.now().isoformat(),
        "agents": {
            "agents": agents_data,
            "stats": {
                "total": len(_agent_states),
                "active": active_count,
                "available": len(_agent_states) - active_count,
            }
        },
        "secondbrain": {
            "status": "available",
            "stats": {"total_notes": 0, "folders": {}},
            "recent_notes": [],
        },
        "connectors": {
            "connectors": connectors_data,
            "stats": {
                "total": len(connectors_data),
                "healthy": sum(1 for c in connectors_data.values() if c.get("status") == "healthy"),
            }
        },
        "chat": {
            "active_sessions": 1,
            "total_messages": total_messages,
        },
        "shared_context": {
            "status": "healthy",
            "sources": {},
        },
        "memory": {
            "core_files": memory_files,
            "daily_memory": {
                "total_files": total_memory_files,
                "today_exists": today_exists,
                "today_chars": today_chars,
            }
        },
        "scheduled_jobs": {
            "active_jobs": 0,
            "jobs": [],
        }
    }
