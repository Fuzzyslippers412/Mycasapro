"""
Janitor API Routes
System health, audits, and maintenance operations via Salimata (Janitor Agent)
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

router = APIRouter(prefix="/api/janitor", tags=["janitor"])


# ==================== MODELS ====================

class AuditResult(BaseModel):
    timestamp: str
    status: str
    health_score: int
    checks_passed: int
    checks_total: int
    findings: List[Dict[str, Any]]


class CodeReviewRequest(BaseModel):
    file_path: str = Field(..., description="Path to the file being changed")
    new_content: str = Field(..., description="Proposed new content")


class CodeReviewResult(BaseModel):
    approved: bool
    concerns: List[Dict[str, Any]]
    blocker_count: int
    warning_count: int
    reviewed_at: str
    reviewed_by: str


class SafeEditRequest(BaseModel):
    file_path: str = Field(..., description="Path to file to edit")
    new_content: str = Field(..., description="New file content")
    reason: str = Field(..., description="Reason for the edit")
    requesting_agent: str = Field(default="api", description="Who is requesting")


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
    action: str = Field(..., description="Fix action identifier")
    params: Dict[str, Any] = Field(default_factory=dict)


# ==================== HELPER ====================

_janitor_instance: Optional["JanitorAgent"] = None

def get_janitor():
    """Get or create the Janitor agent instance (singleton)"""
    global _janitor_instance
    from ...agents import JanitorAgent
    if _janitor_instance is None:
        _janitor_instance = JanitorAgent()
    return _janitor_instance


# ==================== ENDPOINTS ====================

@router.get("/status")
async def get_janitor_status():
    """
    Get Janitor agent status and metrics.
    Returns current state, last audit results, and activity summary.
    """
    janitor = get_janitor()
    status = janitor.get_status()
    
    return {
        "agent": {
            "id": status["agent_id"],
            "name": status["name"],
            "emoji": status["emoji"],
            "status": status["status"],
            "description": status["description"],
        },
        "metrics": status.get("metrics", {}),
        "uptime_seconds": status.get("uptime_seconds", 0),
    }


@router.get("/audit", response_model=AuditResult)
async def run_system_audit():
    """
    Run a comprehensive system health audit.
    
    Checks:
    - Database connectivity
    - Disk space
    - Agent health
    - Backup directory status
    
    Returns a health score and list of findings.
    """
    janitor = get_janitor()
    result = janitor.run_audit()
    
    return AuditResult(
        timestamp=result["timestamp"],
        status=result["status"],
        health_score=result["health_score"],
        checks_passed=result["checks_passed"],
        checks_total=result["checks_total"],
        findings=result["findings"],
    )


@router.post("/review", response_model=CodeReviewResult)
async def review_code_change(request: CodeReviewRequest):
    """
    Review a proposed code change before applying it.
    
    Performs:
    - Syntax validation (Python, JSON)
    - Dangerous pattern detection (eval, exec, rm -rf, etc.)
    - Size checks
    
    Returns approval status and any concerns.
    """
    janitor = get_janitor()
    result = janitor.review_code_change(request.file_path, request.new_content)
    
    return CodeReviewResult(
        approved=result["approved"],
        concerns=result["concerns"],
        blocker_count=result["blocker_count"],
        warning_count=result["warning_count"],
        reviewed_at=result["reviewed_at"],
        reviewed_by=result["reviewed_by"],
    )


@router.post("/safe-edit")
async def safe_edit_file(request: SafeEditRequest):
    """
    Perform a safe file edit with code review and backup.
    
    Process:
    1. Review the proposed change for issues
    2. Create a backup of the original file
    3. Apply the change with validation
    4. Rollback on failure
    
    This is the recommended method for all code changes.
    """
    janitor = get_janitor()
    result = janitor.safe_edit_with_review(
        file_path=request.file_path,
        new_content=request.new_content,
        reason=request.reason,
        requesting_agent=request.requesting_agent,
    )
    
    if not result["success"]:
        raise HTTPException(
            status_code=400,
            detail={
                "error": result.get("error", "Edit failed"),
                "stage": result.get("stage"),
                "review": result.get("review"),
            }
        )
    
    return {
        "success": True,
        "stage": result["stage"],
        "review": result["review"],
        "edit": result.get("edit"),
    }


@router.post("/cleanup", response_model=CleanupResult)
async def cleanup_old_backups(days_to_keep: int = Query(default=7, ge=1, le=90)):
    """
    Clean up old backup files.
    
    Removes backup files older than the specified number of days.
    Default: 7 days.
    """
    janitor = get_janitor()
    result = janitor.cleanup_old_backups(days_to_keep)
    
    return CleanupResult(
        deleted=result["deleted"],
        kept=result["kept"],
        errors=result["errors"],
    )


@router.get("/history")
async def get_edit_history(limit: int = Query(default=20, ge=1, le=100)):
    """
    Get recent file edit history from the coordinator.
    
    Shows the last N edits made through the safe edit system.
    """
    from ...agents.coordination import get_coordinator
    
    coordinator = get_coordinator()
    history = coordinator.get_edit_history(limit)
    
    return {
        "edits": [
            EditHistoryItem(
                timestamp=edit.get("timestamp", ""),
                file=edit.get("file", "unknown"),
                agent=edit.get("agent", "unknown"),
                success=edit.get("success", False),
                reason=edit.get("reason"),
            ).model_dump()
            for edit in history
        ],
        "total": len(history),
    }


@router.get("/logs")
async def get_janitor_logs(limit: int = Query(default=50, ge=1, le=200)):
    """
    Get recent Janitor activity logs.
    """
    janitor = get_janitor()
    logs = janitor.get_recent_logs(limit)
    
    return {
        "logs": logs,
        "agent": "janitor",
        "count": len(logs),
    }


@router.get("/activity")
async def get_janitor_activity():
    """
    Get rich activity data for HYPERCONTEXT-style dashboard.
    
    Returns files touched, tools used, decisions made, heat map, and context usage.
    """
    janitor = get_janitor()
    activity = janitor.get_rich_activity()
    
    return activity


@router.post("/chat")
async def chat_with_janitor(message: str):
    """
    Chat with Salimata (Janitor Agent).
    
    Supports commands like:
    - "run audit" / "health check"
    - "cleanup" / "clean backups"
    - "edit history" / "recent edits"
    """
    janitor = get_janitor()
    response = await janitor.chat(message)
    
    return {
        "response": response,
        "agent": {
            "id": "janitor",
            "name": "Salimata",
            "emoji": "✨",
        }
    }


@router.post("/wizard")
async def run_audit_wizard():
    """
    Run the full audit wizard and return recommendations.
    """
    janitor = get_janitor()
    return janitor.run_audit_wizard()


@router.get("/wizard/history")
async def get_wizard_history(limit: int = Query(default=10, ge=1, le=50)):
    """
    Return recent audit wizard runs.
    """
    janitor = get_janitor()
    return {"runs": janitor.get_wizard_history(limit)}


@router.post("/wizard/fix")
async def apply_wizard_fix(request: WizardFixRequest):
    """
    Apply a wizard-recommended fix action.
    """
    janitor = get_janitor()
    result = await janitor.apply_fix(request.action, request.params)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Fix failed"))
    return result


@router.get("/connectors")
async def check_connectors():
    """
    Check Gmail and WhatsApp connector status.
    
    Shows whether each connector is:
    - connected (real data flowing)
    - stub (using demo data - CLI not configured)
    - disconnected (CLI installed but not authenticated)
    - error (something wrong)
    """
    janitor = get_janitor()
    result = janitor.check_connectors()
    return result


@router.get("/backups")
async def list_backups(limit: int = Query(default=50, ge=1, le=200)):
    """
    List current backup files.
    """
    from ...agents.coordination import get_coordinator
    from pathlib import Path
    import os
    
    coordinator = get_coordinator()
    
    backups = []
    if coordinator.backup_dir.exists():
        for backup_file in sorted(
            coordinator.backup_dir.glob("*.backup.*"),
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )[:limit]:
            stat = backup_file.stat()
            backups.append({
                "filename": backup_file.name,
                "size_bytes": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "path": str(backup_file),
            })
    
    return {
        "backups": backups,
        "count": len(backups),
        "backup_dir": str(coordinator.backup_dir),
    }


@router.delete("/backups/{filename}")
async def delete_specific_backup(filename: str):
    """
    Delete a specific backup file.
    """
    from ...agents.coordination import get_coordinator
    import os
    
    coordinator = get_coordinator()
    backup_path = coordinator.backup_dir / filename
    
    if not backup_path.exists():
        raise HTTPException(status_code=404, detail="Backup not found")
    
    if not backup_path.name.startswith(".") or ".backup." not in backup_path.name:
        raise HTTPException(status_code=400, detail="Invalid backup file")
    
    try:
        os.remove(backup_path)
        return {"deleted": True, "filename": filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete: {str(e)}")


@router.post("/restore/{filename}")
async def restore_from_backup(filename: str):
    """
    Restore a file from backup.
    
    Extracts the original filename from the backup and restores it.
    """
    from ...agents.coordination import get_coordinator
    import shutil
    
    coordinator = get_coordinator()
    backup_path = coordinator.backup_dir / filename
    
    if not backup_path.exists():
        raise HTTPException(status_code=404, detail="Backup not found")
    
    # Parse original path from backup filename
    # Format: .original_filename.backup.TIMESTAMP
    try:
        parts = filename.split(".backup.")
        if len(parts) != 2:
            raise ValueError("Invalid format")
        
        original_name = parts[0].lstrip(".")
        
        # The backup stores the full path somehow - read the metadata if present
        # For now, we'll just inform the user about the backup
        return {
            "info": "Backup found",
            "backup_file": filename,
            "parsed_name": original_name,
            "note": "Manual restoration required - copy backup to original location",
            "backup_path": str(backup_path),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse backup: {str(e)}")
