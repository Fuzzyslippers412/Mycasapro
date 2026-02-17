"""
MyCasa Pro - Scheduler API Routes
=================================

Manage scheduled agent runs.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

# Import scheduler
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agents.scheduler import (
    get_scheduler,
    ScheduleFrequency,
    JOB_TEMPLATES,
)

router = APIRouter(prefix="/scheduler", tags=["Scheduler"])


class CreateJobRequest(BaseModel):
    name: str = Field(..., description="Job name")
    agent: str = Field(..., description="Agent to run (finance, maintenance, security, etc.)")
    task: str = Field(..., description="Task/prompt for the agent")
    frequency: str = Field(..., description="Run frequency: once, hourly, daily, weekly, monthly")
    description: str = Field(default="", description="Job description")
    hour: int = Field(default=9, ge=0, le=23, description="Hour of day (0-23)")
    minute: int = Field(default=0, ge=0, le=59, description="Minute of hour (0-59)")
    day_of_week: int = Field(default=0, ge=0, le=6, description="Day of week (0=Monday)")
    day_of_month: int = Field(default=1, ge=1, le=28, description="Day of month (1-28)")
    config: Dict[str, Any] = Field(default_factory=dict, description="Additional config")


class UpdateJobRequest(BaseModel):
    name: Optional[str] = None
    task: Optional[str] = None
    frequency: Optional[str] = None
    description: Optional[str] = None
    hour: Optional[int] = None
    minute: Optional[int] = None
    day_of_week: Optional[int] = None
    day_of_month: Optional[int] = None
    enabled: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None


@router.get("/status")
async def get_scheduler_status() -> Dict[str, Any]:
    """Get scheduler status"""
    scheduler = get_scheduler()
    return scheduler.get_status()


@router.get("/jobs")
async def list_jobs(
    include_disabled: bool = Query(default=False, description="Include disabled jobs"),
) -> Dict[str, Any]:
    """List all scheduled jobs"""
    scheduler = get_scheduler()
    jobs = scheduler.list_jobs(include_disabled=include_disabled)
    
    return {
        "jobs": [job.to_dict() for job in jobs],
        "total": len(jobs),
    }


@router.get("/jobs/{job_id}")
async def get_job(job_id: str) -> Dict[str, Any]:
    """Get a specific job"""
    scheduler = get_scheduler()
    job = scheduler.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    
    return job.to_dict()


@router.post("/jobs")
async def create_job(request: CreateJobRequest) -> Dict[str, Any]:
    """Create a new scheduled job"""
    scheduler = get_scheduler()
    
    try:
        frequency = ScheduleFrequency(request.frequency)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid frequency: {request.frequency}. Must be one of: once, hourly, daily, weekly, monthly"
        )
    
    job = scheduler.create_job(
        name=request.name,
        agent=request.agent,
        task=request.task,
        frequency=frequency,
        description=request.description,
        hour=request.hour,
        minute=request.minute,
        day_of_week=request.day_of_week,
        day_of_month=request.day_of_month,
        config=request.config,
    )
    
    return {
        "success": True,
        "job": job.to_dict(),
    }


@router.put("/jobs/{job_id}")
async def update_job(job_id: str, request: UpdateJobRequest) -> Dict[str, Any]:
    """Update a scheduled job"""
    scheduler = get_scheduler()
    
    updates = {}
    if request.name is not None:
        updates["name"] = request.name
    if request.task is not None:
        updates["task"] = request.task
    if request.frequency is not None:
        try:
            updates["frequency"] = ScheduleFrequency(request.frequency)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid frequency: {request.frequency}")
    if request.description is not None:
        updates["description"] = request.description
    if request.hour is not None:
        updates["hour"] = request.hour
    if request.minute is not None:
        updates["minute"] = request.minute
    if request.day_of_week is not None:
        updates["day_of_week"] = request.day_of_week
    if request.day_of_month is not None:
        updates["day_of_month"] = request.day_of_month
    if request.enabled is not None:
        updates["enabled"] = request.enabled
    if request.config is not None:
        updates["config"] = request.config
    
    job = scheduler.update_job(job_id, **updates)
    
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    
    return {
        "success": True,
        "job": job.to_dict(),
    }


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str) -> Dict[str, Any]:
    """Delete a scheduled job"""
    scheduler = get_scheduler()
    
    if not scheduler.delete_job(job_id):
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    
    return {
        "success": True,
        "deleted": job_id,
    }


@router.post("/jobs/{job_id}/run")
async def run_job_now(job_id: str) -> Dict[str, Any]:
    """Run a job immediately (manual trigger)"""
    scheduler = get_scheduler()
    job = scheduler.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    
    run = await scheduler.run_job(job)
    
    return {
        "success": True,
        "run": run.to_dict(),
    }


@router.post("/jobs/{job_id}/enable")
async def enable_job(job_id: str) -> Dict[str, Any]:
    """Enable a disabled job"""
    scheduler = get_scheduler()
    job = scheduler.update_job(job_id, enabled=True)
    
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    
    return {
        "success": True,
        "job": job.to_dict(),
    }


@router.post("/jobs/{job_id}/disable")
async def disable_job(job_id: str) -> Dict[str, Any]:
    """Disable a job"""
    scheduler = get_scheduler()
    job = scheduler.update_job(job_id, enabled=False)
    
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    
    return {
        "success": True,
        "job": job.to_dict(),
    }


@router.get("/history")
async def get_run_history(
    job_id: Optional[str] = Query(default=None, description="Filter by job ID"),
    limit: int = Query(default=50, ge=1, le=500, description="Number of runs to return"),
) -> Dict[str, Any]:
    """Get job run history"""
    scheduler = get_scheduler()
    history = scheduler.get_history(job_id=job_id, limit=limit)
    
    return {
        "runs": history,
        "total": len(history),
    }


@router.get("/templates")
async def list_templates() -> Dict[str, Any]:
    """List available job templates"""
    templates = []
    for template_id, template in JOB_TEMPLATES.items():
        templates.append({
            "id": template_id,
            **template,
            "frequency": template["frequency"].value if isinstance(template["frequency"], ScheduleFrequency) else template["frequency"],
        })
    
    return {
        "templates": templates,
        "total": len(templates),
    }


@router.post("/templates/{template_id}/create")
async def create_from_template(template_id: str) -> Dict[str, Any]:
    """Create a job from a template"""
    if template_id not in JOB_TEMPLATES:
        raise HTTPException(status_code=404, detail=f"Template not found: {template_id}")
    
    template = JOB_TEMPLATES[template_id]
    scheduler = get_scheduler()
    
    job = scheduler.create_job(
        name=template["name"],
        agent=template["agent"],
        task=template["task"],
        frequency=template["frequency"],
        description=template.get("description", ""),
        hour=template.get("hour", 9),
        minute=template.get("minute", 0),
        day_of_week=template.get("day_of_week", 0),
        day_of_month=template.get("day_of_month", 1),
    )
    
    return {
        "success": True,
        "job": job.to_dict(),
        "template": template_id,
    }


@router.post("/start")
async def start_scheduler() -> Dict[str, Any]:
    """Start the scheduler"""
    scheduler = get_scheduler()
    scheduler.start()
    return {"success": True, "status": "started"}


@router.post("/stop")
async def stop_scheduler() -> Dict[str, Any]:
    """Stop the scheduler"""
    scheduler = get_scheduler()
    scheduler.stop()
    return {"success": True, "status": "stopped"}
