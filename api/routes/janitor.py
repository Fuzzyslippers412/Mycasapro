"""
MyCasa Pro API - Janitor Routes
System health, audits, cost tracking, and incident management.
"""
import asyncio
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import sys
from pathlib import Path
import shutil

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from agents.janitor import JanitorAgent

router = APIRouter(prefix="/janitor", tags=["Janitor"])

# Singleton janitor instance
_janitor: Optional[JanitorAgent] = None

def get_janitor() -> JanitorAgent:
    global _janitor
    if _janitor is None:
        _janitor = JanitorAgent()
    return _janitor


class PreflightRequest(BaseModel):
    api_base: Optional[str] = None
    skip_oauth: bool = True
    open_browser: bool = False
    allow_destructive: bool = False
    isolated: bool = True


class AuditResult(BaseModel):
    timestamp: str
    status: str
    health_score: int
    checks_passed: int
    checks_total: int
    findings: List[Dict[str, Any]]


class CodeReviewRequest(BaseModel):
    file_path: str
    new_content: str


class CodeReviewResult(BaseModel):
    approved: bool
    concerns: List[Dict[str, Any]]
    blocker_count: int
    warning_count: int
    reviewed_at: str
    reviewed_by: str


class CleanupResult(BaseModel):
    deleted: int
    kept: int
    errors: List[str]


class EditHistoryItem(BaseModel):
    timestamp: str
    file: str
    agent: str
    success: bool
    reason: Optional[str] = None


class WizardFixRequest(BaseModel):
    action: str
    params: Optional[Dict[str, Any]] = None


@router.get("/status")
async def get_janitor_status():
    """Get current janitor status and health overview"""
    janitor = get_janitor()
    status = janitor.get_status()
    metrics = status.get("metrics", {}) if isinstance(status, dict) else {}
    last_audit = getattr(janitor, "_last_audit_result", None) or {}
    findings_count = len(last_audit.get("findings", []) or [])
    health = status.get("health") if isinstance(status, dict) else None
    system_health = "healthy" if health == "healthy" else "needs_attention" if health in {"warning", "degraded", "critical"} else "unknown"

    return {
        "agent": {
            "id": "janitor",
            "name": "Salimata",
            "emoji": "✨",
            "status": status.get("status", "active") if isinstance(status, dict) else "active",
            "description": "System health, audits, and safe edits",
        },
        "metrics": {
            "last_audit": metrics.get("last_audit"),
            "findings_count": findings_count,
            "recent_edits": len(janitor.get_edit_history(50)),
            "system_health": system_health,
            "last_preflight": metrics.get("last_preflight"),
            "last_preflight_status": metrics.get("last_preflight_status"),
        },
        "uptime_seconds": status.get("uptime_seconds", 0) if isinstance(status, dict) else 0,
    }


@router.get("/health")
async def get_health_report(format: str = "json"):
    """Get system health report"""
    janitor = get_janitor()
    
    if format == "text":
        return {"report": janitor.get_health_report(format="text")}
    
    return janitor.get_full_report()


@router.get("/costs")
async def get_cost_summary(period: str = "month"):
    """Get cost summary for the specified period"""
    janitor = get_janitor()
    return janitor.get_cost_summary(period=period)


@router.get("/alerts")
async def get_alerts():
    """Get current system alerts"""
    janitor = get_janitor()
    return {"alerts": janitor.check_alerts()}


@router.get("/incidents")
async def get_incidents(status: Optional[str] = None, limit: int = 50):
    """Get incident history"""
    janitor = get_janitor()
    incidents = list(janitor._incidents.values())
    
    if status:
        incidents = [i for i in incidents if i.get("status") == status]
    
    # Sort by timestamp descending
    incidents.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    return {
        "incidents": incidents[:limit],
        "total": len(janitor._incidents),
    }


@router.post("/incidents")
async def create_incident(
    severity: str,
    category: str,
    title: str,
    details: str,
    source: str = "api"
):
    """Create a new incident"""
    janitor = get_janitor()
    
    result = janitor.create_incident(
        severity=severity,
        category=category,
        title=title,
        details=details,
        source=source
    )
    
    return {"success": True, "incident_id": result}


@router.post("/run-audit")
async def run_audit():
    """Run a full system audit"""
    janitor = get_janitor()
    
    # Run actual audit
    audit = janitor.run_audit()
    
    # Get full report
    report = janitor.get_full_report()
    
    # Get health report text
    health_text = janitor.get_health_report(format="text")
    
    # Get alerts
    alerts = janitor.check_alerts()
    
    # Get cost summary
    costs = janitor.get_cost_summary(period="month")
    
    return {
        "success": True,
        "timestamp": datetime.now().isoformat(),
        "audit": audit,
        "report": report,
        "health_text": health_text,
        "alerts": alerts,
        "costs": costs,
    }


@router.get("/audit", response_model=AuditResult)
async def run_audit_summary():
    """Run a full system audit and return summary used by UI."""
    janitor = get_janitor()
    result = janitor.run_audit()
    return AuditResult(
        timestamp=result.get("timestamp") or result.get("audit_time") or datetime.now().isoformat(),
        status=result.get("status", "ok"),
        health_score=result.get("health_score", 100),
        checks_passed=result.get("checks_passed", 0),
        checks_total=result.get("checks_total", 0),
        findings=result.get("findings", []),
    )


@router.post("/cleanup", response_model=CleanupResult)
async def cleanup_backups(days_to_keep: int = Query(default=7, ge=1, le=90)):
    """Delete backups older than the specified number of days."""
    from core.lifecycle import get_lifecycle_manager

    lifecycle = get_lifecycle_manager()
    cutoff = datetime.now() - timedelta(days=days_to_keep)
    deleted = 0
    kept = 0
    errors: List[str] = []

    for backup_dir in lifecycle.backup_dir.iterdir():
        if not (backup_dir.is_dir() and backup_dir.name.startswith("backup_")):
            continue
        timestamp = backup_dir.name.replace("backup_", "")
        try:
            backup_time = datetime.strptime(timestamp, "%Y%m%d_%H%M%S")
        except Exception:
            kept += 1
            continue
        if backup_time < cutoff:
            try:
                shutil.rmtree(backup_dir)
                deleted += 1
            except Exception as e:
                errors.append(f"{backup_dir.name}: {e}")
        else:
            kept += 1

    return CleanupResult(deleted=deleted, kept=kept, errors=errors)


@router.get("/history")
async def get_edit_history(limit: int = Query(default=20, ge=1, le=100)):
    """Return recent Janitor edit history."""
    janitor = get_janitor()
    history = janitor.get_edit_history(limit)
    return {
        "edits": [
            EditHistoryItem(
                timestamp=edit.get("timestamp", ""),
                file=edit.get("file", "unknown"),
                agent=edit.get("agent", "unknown"),
                success=bool(edit.get("success", False)),
                reason=edit.get("reason"),
            ).model_dump()
            for edit in history
        ],
        "total": len(history),
    }


@router.get("/logs")
async def get_janitor_logs(limit: int = Query(default=50, ge=1, le=200)):
    janitor = get_janitor()
    logs = janitor.get_recent_logs(limit)
    return {
        "logs": [
            {
                "timestamp": log.get("created_at"),
                "action": log.get("action"),
                "details": log.get("details"),
                "status": log.get("status"),
                "agent_id": janitor.name,
            }
            for log in logs
        ],
        "count": len(logs),
    }


@router.get("/backups")
async def list_backups(limit: int = Query(default=50, ge=1, le=200)):
    """List current backups from lifecycle manager."""
    from core.lifecycle import get_lifecycle_manager

    lifecycle = get_lifecycle_manager()
    backups = lifecycle.list_backups()[:limit]
    return {
        "backups": [
            {
                "filename": backup.get("name"),
                "size_bytes": backup.get("size_bytes", 0),
                "modified": backup.get("timestamp"),
                "path": backup.get("path"),
            }
            for backup in backups
        ],
        "count": len(backups),
    }


@router.delete("/backups/{filename}")
async def delete_backup(filename: str):
    """Delete a specific backup directory."""
    from core.lifecycle import get_lifecycle_manager

    lifecycle = get_lifecycle_manager()
    backup_dir = lifecycle.backup_dir / filename
    if not (backup_dir.exists() and backup_dir.is_dir() and backup_dir.name.startswith("backup_")):
        raise HTTPException(status_code=404, detail="Backup not found")
    try:
        shutil.rmtree(backup_dir)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"deleted": True, "filename": filename}


@router.post("/review", response_model=CodeReviewResult)
async def review_code_change(request: CodeReviewRequest):
    janitor = get_janitor()
    result = janitor.review_code_change(request.file_path, request.new_content)
    return CodeReviewResult(
        approved=result["approved"],
        concerns=result.get("concerns", []),
        blocker_count=result.get("blocker_count", 0),
        warning_count=result.get("warning_count", 0),
        reviewed_at=result.get("reviewed_at", datetime.now().isoformat()),
        reviewed_by=result.get("reviewed_by", "janitor"),
    )


@router.post("/chat")
async def chat_with_janitor(message: str):
    janitor = get_janitor()
    response = await janitor.chat(message)
    return {
        "response": response,
        "agent": {
            "id": "janitor",
            "name": "Salimata",
            "emoji": "✨",
        },
    }


@router.get("/preflight-info")
async def get_preflight_info():
    """Expose preflight command and script location."""
    janitor = get_janitor()
    return janitor.get_preflight_info()


@router.post("/run-preflight")
async def run_preflight(req: PreflightRequest):
    """Run the preflight script via Janitor."""
    janitor = get_janitor()
    result = await asyncio.to_thread(
        janitor.run_preflight,
        api_base=req.api_base,
        skip_oauth=req.skip_oauth,
        open_browser=req.open_browser,
        allow_destructive=req.allow_destructive,
        isolated=req.isolated,
    )
    if not result.get("success"):
        raise HTTPException(status_code=500, detail="Preflight failed")
    return result


@router.post("/wizard")
async def run_audit_wizard():
    """Run the Janitor audit wizard and persist results."""
    janitor = get_janitor()
    return janitor.run_audit_wizard()


@router.get("/wizard/history")
async def get_wizard_history(limit: int = 10):
    """Return recent audit wizard runs."""
    janitor = get_janitor()
    return {"runs": janitor.get_wizard_history(limit)}


@router.post("/wizard/fix")
async def apply_wizard_fix(request: WizardFixRequest):
    """Apply a wizard recommendation fix."""
    janitor = get_janitor()
    result = await janitor.apply_fix(request.action, request.params or {})
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error") or "Fix failed")
    return result
