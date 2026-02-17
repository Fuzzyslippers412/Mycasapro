"""
Team Orchestration API Routes
Manage agent teams and coordinate multi-agent tasks
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

router = APIRouter(prefix="/api/teams", tags=["teams"])


# ==================== MODELS ====================

class TeamInfo(BaseModel):
    id: str
    name: str
    description: str
    members: List[str]
    leader: str
    mode: str
    emoji: str = "👥"


class CreateTeamRequest(BaseModel):
    id: str
    name: str
    description: str
    members: List[str]
    leader: str
    mode: str = "sequential"
    emoji: str = "👥"
    auto_escalate: bool = True
    require_consensus_threshold: float = 0.6


class CreateTaskRequest(BaseModel):
    team_id: str
    description: str
    context: Dict[str, Any] = Field(default_factory=dict)
    mode_override: Optional[str] = None


class WorkflowStepRequest(BaseModel):
    id: str
    agent_id: str
    action: str
    params: Dict[str, Any] = Field(default_factory=dict)
    depends_on: List[str] = Field(default_factory=list)
    timeout_seconds: int = 120


class CreateWorkflowRequest(BaseModel):
    name: str
    description: str
    steps: List[WorkflowStepRequest]
    context: Dict[str, Any] = Field(default_factory=dict)


class PublishEventRequest(BaseModel):
    event_type: str
    payload: Dict[str, Any]
    priority: str = "normal"


class SetContextRequest(BaseModel):
    key: str
    value: Any


# ==================== TEAM ROUTES ====================

@router.get("/")
async def list_teams():
    """List all available teams (preset + custom)"""
    from ...agents import get_orchestrator
    
    orchestrator = get_orchestrator()
    teams = orchestrator.list_teams()
    
    return {
        "teams": [t.to_dict() for t in teams],
        "count": len(teams),
    }


@router.get("/presets")
async def list_preset_teams():
    """List preset team configurations"""
    from ...agents import PRESET_TEAMS
    
    return {
        "presets": [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "members": t.members,
                "leader": t.leader,
                "mode": t.mode.value,
                "emoji": t.emoji,
            }
            for t in PRESET_TEAMS.values()
        ]
    }


@router.get("/{team_id}")
async def get_team(team_id: str):
    """Get a specific team"""
    from ...agents import get_orchestrator
    
    orchestrator = get_orchestrator()
    team = orchestrator.get_team(team_id)
    
    if not team:
        raise HTTPException(status_code=404, detail=f"Team not found: {team_id}")
    
    return {
        "team": team.to_dict(),
        "stats": orchestrator.get_team_stats(team_id),
    }


@router.post("/")
async def create_team(req: CreateTeamRequest):
    """Create a custom team"""
    from ...agents import get_orchestrator, TeamMode
    
    orchestrator = get_orchestrator()
    
    try:
        mode = TeamMode(req.mode)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid mode: {req.mode}")
    
    team = orchestrator.create_custom_team(
        id=req.id,
        name=req.name,
        description=req.description,
        members=req.members,
        leader=req.leader,
        mode=mode,
        emoji=req.emoji,
        auto_escalate=req.auto_escalate,
        require_consensus_threshold=req.require_consensus_threshold,
    )
    
    return {
        "created": True,
        "team": team.to_dict(),
    }


@router.delete("/{team_id}")
async def delete_team(team_id: str):
    """Delete a custom team (cannot delete presets)"""
    from ...agents import get_orchestrator, PRESET_TEAMS
    
    if team_id in PRESET_TEAMS:
        raise HTTPException(status_code=400, detail="Cannot delete preset teams")
    
    orchestrator = get_orchestrator()
    deleted = orchestrator.delete_custom_team(team_id)
    
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Team not found: {team_id}")
    
    return {"deleted": True, "team_id": team_id}


# ==================== TASK ROUTES ====================

@router.post("/tasks")
async def create_and_execute_task(req: CreateTaskRequest, background_tasks: BackgroundTasks):
    """Create and execute a team task"""
    from ...agents import get_orchestrator, TeamMode
    import asyncio
    
    orchestrator = get_orchestrator()
    
    # Validate team exists
    team = orchestrator.get_team(req.team_id)
    if not team:
        raise HTTPException(status_code=404, detail=f"Team not found: {req.team_id}")
    
    # Parse mode override
    mode_override = None
    if req.mode_override:
        try:
            mode_override = TeamMode(req.mode_override)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid mode: {req.mode_override}")
    
    # Create task
    task = orchestrator.create_task(
        team_id=req.team_id,
        description=req.description,
        context=req.context,
        mode_override=mode_override,
    )
    
    # Execute in background
    async def run_task():
        return await orchestrator.execute_task(task)
    
    background_tasks.add_task(asyncio.get_event_loop().create_task, run_task())
    
    return {
        "task_id": task.id,
        "status": "started",
        "team_id": req.team_id,
        "mode": (mode_override or team.mode).value,
        "agents": task.assigned_agents,
    }


@router.get("/tasks")
async def list_active_tasks():
    """List all active team tasks"""
    from ...agents import get_orchestrator
    
    orchestrator = get_orchestrator()
    tasks = orchestrator.get_active_tasks()
    
    return {
        "tasks": [t.to_dict() for t in tasks],
        "count": len(tasks),
    }


@router.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """Get a specific task"""
    from ...agents import get_orchestrator
    
    orchestrator = get_orchestrator()
    task = orchestrator.get_task(task_id)
    
    if not task:
        # Check history
        history = orchestrator.get_task_history(limit=100)
        for h in history:
            if h.get("id") == task_id:
                return {"task": h, "from_history": True}
        
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    
    return {"task": task.to_dict(), "from_history": False}


@router.get("/tasks/history")
async def get_task_history(limit: int = 50):
    """Get team task history"""
    from ...agents import get_orchestrator
    
    orchestrator = get_orchestrator()
    history = orchestrator.get_task_history(limit=limit)
    
    return {
        "history": history,
        "count": len(history),
    }


# ==================== WORKFLOW ROUTES ====================

@router.post("/workflows")
async def create_workflow(req: CreateWorkflowRequest, background_tasks: BackgroundTasks):
    """Create and execute a workflow"""
    from ...agents import get_coordinator
    import asyncio
    
    coordinator = get_coordinator()
    
    # Convert steps
    steps = [
        {
            "id": s.id,
            "agent_id": s.agent_id,
            "action": s.action,
            "params": s.params,
            "depends_on": s.depends_on,
            "timeout_seconds": s.timeout_seconds,
        }
        for s in req.steps
    ]
    
    workflow = coordinator.create_workflow(
        name=req.name,
        description=req.description,
        steps=steps,
        context=req.context,
    )
    
    # Execute in background
    async def run_workflow():
        return await coordinator.execute_workflow(workflow.id)
    
    background_tasks.add_task(asyncio.get_event_loop().create_task, run_workflow())
    
    return {
        "workflow_id": workflow.id,
        "status": "started",
        "steps": len(steps),
    }


@router.get("/workflows")
async def list_workflows():
    """List active workflows"""
    from ...agents import get_coordinator
    
    coordinator = get_coordinator()
    workflows = coordinator.get_active_workflows()
    
    return {
        "workflows": [w.to_dict() for w in workflows],
        "count": len(workflows),
    }


@router.get("/workflows/history")
async def get_workflow_history(limit: int = 50):
    """Get workflow execution history"""
    from ...agents import get_coordinator
    
    coordinator = get_coordinator()
    history = coordinator.get_workflow_history(limit=limit)
    
    return {
        "history": history,
        "count": len(history),
    }


# ==================== EVENT BUS ROUTES ====================

@router.post("/events")
async def publish_event(req: PublishEventRequest):
    """Publish an event to the event bus"""
    from ...agents import get_coordinator, EventType, Priority
    
    coordinator = get_coordinator()
    
    try:
        event_type = EventType(req.event_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid event type: {req.event_type}")
    
    try:
        priority = Priority(req.priority)
    except ValueError:
        priority = Priority.NORMAL
    
    event = coordinator.publish_event(
        event_type=event_type,
        source_agent="api",
        payload=req.payload,
        priority=priority,
    )
    
    return {
        "event_id": event.id,
        "consumed_by": event.consumed_by,
    }


@router.get("/events")
async def get_recent_events(event_type: str = None, limit: int = 50):
    """Get recent events"""
    from ...agents import get_coordinator, EventType
    
    coordinator = get_coordinator()
    
    evt_type = None
    if event_type:
        try:
            evt_type = EventType(event_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid event type: {event_type}")
    
    events = coordinator.get_recent_events(event_type=evt_type, limit=limit)
    
    return {
        "events": [e.to_dict() for e in events],
        "count": len(events),
    }


@router.get("/events/types")
async def list_event_types():
    """List all available event types"""
    from ...agents import EventType
    
    return {
        "event_types": [e.value for e in EventType],
    }


# ==================== SHARED CONTEXT ROUTES ====================

@router.get("/context")
async def get_shared_context():
    """Get all shared context"""
    from ...agents import get_coordinator
    
    coordinator = get_coordinator()
    return {
        "context": coordinator.get_full_context(),
    }


@router.get("/context/{key}")
async def get_context_value(key: str):
    """Get a specific context value"""
    from ...agents import get_coordinator
    
    coordinator = get_coordinator()
    value = coordinator.get_context(key)
    
    if value is None:
        raise HTTPException(status_code=404, detail=f"Context key not found: {key}")
    
    return {"key": key, "value": value}


@router.post("/context")
async def set_context_value(req: SetContextRequest):
    """Set a shared context value"""
    from ...agents import get_coordinator
    
    coordinator = get_coordinator()
    coordinator.set_context(req.key, req.value, source_agent="api")
    
    return {"set": True, "key": req.key}


@router.delete("/context/{key}")
async def clear_context_key(key: str):
    """Clear a specific context key"""
    from ...agents import get_coordinator
    
    coordinator = get_coordinator()
    coordinator.clear_context(key)
    
    return {"cleared": True, "key": key}


# ==================== ROUTING ROUTES ====================

@router.post("/route")
async def route_request(message: str, from_agent: str = "manager"):
    """Route a message to the appropriate agent"""
    from ...agents import get_coordinator
    
    coordinator = get_coordinator()
    
    # Get enhanced routing with team suggestion
    result = coordinator.route_with_team_suggestion(message, from_agent)
    
    return {
        "primary_agent": result["primary_agent"],
        "suggested_team": result["suggested_team"],
        "confidence": result["confidence"],
        "all_scores": result["all_scores"],
    }


# ==================== AGENT STATUS ROUTES ====================

@router.get("/agents")
async def list_agents():
    """List all registered agents with status"""
    from ...agents import get_coordinator
    
    coordinator = get_coordinator()
    agents = coordinator.list_agents()
    
    return {
        "agents": [
            {
                "id": aid,
                "healthy": coordinator.is_agent_healthy(aid),
            }
            for aid in agents
        ],
        "count": len(agents),
    }


@router.get("/agents/{agent_id}/health")
async def get_agent_health(agent_id: str):
    """Get health status of a specific agent"""
    from ...agents import get_coordinator
    
    coordinator = get_coordinator()
    
    if agent_id not in coordinator.list_agents():
        raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
    
    return {
        "agent_id": agent_id,
        "healthy": coordinator.is_agent_healthy(agent_id),
        "circuit_open": agent_id in coordinator._circuit_open,
    }
