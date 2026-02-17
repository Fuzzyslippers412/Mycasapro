"""
Fleet Management API Routes.

Provides endpoints for managing the agent fleet including:
- Fleet status and metrics
- Individual agent control
- Cost tracking
- Performance monitoring
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from datetime import datetime

router = APIRouter(prefix="/fleet", tags=["Fleet Management"])


class AgentConfigUpdate(BaseModel):
    """Request to update agent configuration."""
    enabled: Optional[bool] = None
    max_concurrent_requests: Optional[int] = None
    timeout_seconds: Optional[int] = None
    default_model: Optional[str] = None
    max_tier: Optional[str] = None
    context_strategy: Optional[str] = None
    cost_limit_daily_usd: Optional[float] = None
    cost_limit_monthly_usd: Optional[float] = None
    priority: Optional[int] = None


class RouteRequest(BaseModel):
    """Request to analyze routing for a message."""
    message: str
    agent_id: Optional[str] = None


@router.get("/status")
async def get_fleet_status():
    """
    Get comprehensive fleet status.

    Returns status of all agents including:
    - Current state (idle, running, busy, error)
    - Request counts and success rates
    - Cost tracking
    - Performance metrics
    """
    from core.fleet_manager import get_fleet_manager

    fleet = get_fleet_manager()
    return fleet.get_fleet_status()


@router.get("/agents")
async def list_agents():
    """List all agents in the fleet."""
    from core.fleet_manager import get_fleet_manager

    fleet = get_fleet_manager()
    status = fleet.get_fleet_status()
    return {
        "agents": [
            {"id": agent_id, **data}
            for agent_id, data in status["agents"].items()
        ],
        "count": len(status["agents"]),
    }


@router.get("/agents/{agent_id}")
async def get_agent_status(agent_id: str):
    """Get status for a specific agent."""
    from core.fleet_manager import get_fleet_manager

    fleet = get_fleet_manager()
    status = fleet.get_agent_status(agent_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    return status


@router.patch("/agents/{agent_id}")
async def update_agent_config(agent_id: str, config: AgentConfigUpdate):
    """Update agent configuration."""
    from core.fleet_manager import get_fleet_manager

    fleet = get_fleet_manager()
    agent = fleet.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")

    updates = config.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")

    success = fleet.update_agent_config(agent_id, **updates)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update config")

    return {
        "success": True,
        "agent_id": agent_id,
        "updates": updates,
    }


@router.post("/agents/{agent_id}/enable")
async def enable_agent(agent_id: str):
    """Enable an agent."""
    from core.fleet_manager import get_fleet_manager

    fleet = get_fleet_manager()
    if not fleet.get_agent(agent_id):
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")

    success = fleet.enable_agent(agent_id)
    return {"success": success, "agent_id": agent_id, "enabled": True}


@router.post("/agents/{agent_id}/disable")
async def disable_agent(agent_id: str):
    """Disable an agent."""
    from core.fleet_manager import get_fleet_manager

    fleet = get_fleet_manager()
    if not fleet.get_agent(agent_id):
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")

    success = fleet.disable_agent(agent_id)
    return {"success": success, "agent_id": agent_id, "enabled": False}


@router.post("/agents/{agent_id}/reset-metrics")
async def reset_agent_metrics(agent_id: str):
    """Reset metrics for a specific agent."""
    from core.fleet_manager import get_fleet_manager

    fleet = get_fleet_manager()
    if not fleet.get_agent(agent_id):
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")

    fleet.reset_metrics(agent_id)
    return {"success": True, "agent_id": agent_id, "message": "Metrics reset"}


@router.get("/metrics")
async def get_fleet_metrics():
    """Get detailed metrics for the entire fleet."""
    from core.fleet_manager import get_fleet_manager

    fleet = get_fleet_manager()
    return fleet.export_metrics()


@router.post("/metrics/reset")
async def reset_all_metrics():
    """Reset metrics for all agents."""
    from core.fleet_manager import get_fleet_manager

    fleet = get_fleet_manager()
    fleet.reset_metrics()
    return {"success": True, "message": "All metrics reset"}


@router.post("/route/analyze")
async def analyze_routing(request: RouteRequest):
    """
    Analyze how a message would be routed.

    Returns the scoring result including:
    - Complexity score
    - Recommended tier
    - Recommended model
    - Factor breakdown
    """
    from core.request_scorer import get_request_scorer

    scorer = get_request_scorer()
    result = scorer.score(request.message, request.agent_id)

    return {
        "message_preview": request.message[:100] + ("..." if len(request.message) > 100 else ""),
        "agent_id": request.agent_id,
        "routing": {
            "score": result.score,
            "tier": result.tier.value,
            "confidence": result.confidence,
            "recommended_model": result.recommended_model,
            "factors": result.factors,
        },
    }


@router.post("/route/select-agent")
async def select_agent_for_task(
    task_type: str = "general",
    required_tier: str = "medium",
    preferred_agent: Optional[str] = None,
):
    """Select the best available agent for a task."""
    from core.fleet_manager import get_fleet_manager

    fleet = get_fleet_manager()
    agent_id = fleet.select_agent_for_task(
        task_type=task_type,
        required_tier=required_tier,
        preferred_agent=preferred_agent,
    )

    if not agent_id:
        return {
            "success": False,
            "message": "No suitable agent available",
            "available_agents": list(fleet.get_available_agents().keys()),
        }

    return {
        "success": True,
        "selected_agent": agent_id,
        "task_type": task_type,
        "required_tier": required_tier,
    }


@router.get("/costs")
async def get_cost_summary():
    """Get cost summary across all agents."""
    from core.fleet_manager import get_fleet_manager

    fleet = get_fleet_manager()
    status = fleet.get_fleet_status()

    costs_by_agent = {}
    costs_by_tier = {"simple": 0, "medium": 0, "complex": 0, "reasoning": 0}

    for agent_id, agent_status in status["agents"].items():
        metrics = agent_status["metrics"]
        costs_by_agent[agent_id] = {
            "name": agent_status["name"],
            "cost_usd": metrics["total_cost_usd"],
            "requests": metrics["total_requests"],
            "within_budget": agent_status["within_budget"],
            "daily_limit": agent_status["cost_limit_daily"],
        }

        # Aggregate by tier (approximate cost allocation)
        for tier, count in metrics["requests_by_tier"].items():
            if tier in costs_by_tier:
                # Rough cost per tier
                tier_costs = {"simple": 0.0003, "medium": 0.003, "complex": 0.006, "reasoning": 0.015}
                costs_by_tier[tier] += count * tier_costs.get(tier, 0.003)

    return {
        "total_cost_usd": round(status["total_cost_usd"], 4),
        "costs_by_agent": costs_by_agent,
        "costs_by_tier": {k: round(v, 4) for k, v in costs_by_tier.items()},
        "total_requests": status["total_requests"],
    }


@router.get("/health")
async def fleet_health_check():
    """Check overall fleet health."""
    from core.fleet_manager import get_fleet_manager

    fleet = get_fleet_manager()
    status = fleet.get_fleet_status()

    # Calculate health indicators
    total_agents = status["fleet_size"]
    available = status["available_count"]
    enabled = status["enabled_count"]

    issues = []

    # Check for agents with high error rates
    for agent_id, agent_status in status["agents"].items():
        if agent_status["metrics"]["total_requests"] > 10:
            success_rate = agent_status["metrics"]["success_rate"]
            if success_rate < 0.9:
                issues.append(f"{agent_id}: Low success rate ({success_rate:.1%})")

        if not agent_status["within_budget"]:
            issues.append(f"{agent_id}: Over budget")

        if agent_status["state"] == "error":
            issues.append(f"{agent_id}: In error state")

    health_score = 1.0
    if issues:
        health_score -= 0.1 * len(issues)
    if available == 0:
        health_score -= 0.5

    return {
        "healthy": health_score >= 0.7,
        "health_score": round(max(0, health_score), 2),
        "total_agents": total_agents,
        "enabled_agents": enabled,
        "available_agents": available,
        "agents_by_state": status["agents_by_state"],
        "issues": issues,
    }


@router.get("/tiers")
async def get_tier_info():
    """Get information about model tiers."""
    return {
        "tiers": [
            {
                "id": "simple",
                "name": "Simple",
                "model": "claude-haiku-4-5",
                "cost_per_1m_tokens": 0.80,
                "description": "Fast, cheap - for lookups, status checks, simple Q&A",
                "use_cases": ["Status queries", "Simple lookups", "Quick checks"],
            },
            {
                "id": "medium",
                "name": "Medium",
                "model": "claude-3-5-sonnet",
                "cost_per_1m_tokens": 3.00,
                "description": "Balanced - for summaries, standard tasks",
                "use_cases": ["Summaries", "CRUD operations", "Standard tasks"],
            },
            {
                "id": "complex",
                "name": "Complex",
                "model": "claude-sonnet-4",
                "cost_per_1m_tokens": 3.00,
                "description": "Capable - for code, analysis, multi-step reasoning",
                "use_cases": ["Code generation", "Analysis", "Planning"],
            },
            {
                "id": "reasoning",
                "name": "Reasoning",
                "model": "claude-opus-4-5",
                "cost_per_1m_tokens": 15.00,
                "description": "Most powerful - for strategic decisions, complex analysis",
                "use_cases": ["Strategic planning", "Complex reasoning", "Critical decisions"],
            },
        ],
    }
