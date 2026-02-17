"""
MyCasa Pro API - Janitor Routes
System health, audits, cost tracking, and incident management.
"""
import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
import sys
from pathlib import Path

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


class WizardFixRequest(BaseModel):
    action: str
    params: Optional[Dict[str, Any]] = None


@router.get("/status")
async def get_janitor_status():
    """Get current janitor status and health overview"""
    janitor = get_janitor()
    return janitor.get_status()


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
