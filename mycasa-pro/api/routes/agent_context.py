from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from auth.dependencies import require_auth
from core.agent_profiles import (
    list_agent_profiles,
    get_or_create_agent_profile,
    normalize_budgets,
    update_agent_profile_context,
)
from database.connection import get_db
from database.models import AgentProfile, LLMRun


router = APIRouter(prefix="/agents", tags=["agents-context"])


class ContextUpdateRequest(BaseModel):
    context_window_tokens: Optional[int] = Field(default=None, ge=8192, le=1_000_000)
    reserved_output_tokens: Optional[int] = Field(default=None, ge=0, le=1_000_000)
    budgets_json: Optional[Dict[str, int]] = None


class SimulateContextRequest(BaseModel):
    context_window_tokens: Optional[int] = None
    reserved_output_tokens: Optional[int] = None
    budgets_json: Optional[Dict[str, int]] = None
    component_tokens: Optional[Dict[str, int]] = None
    history_token_counts: Optional[List[int]] = None
    retrieval_token_counts: Optional[List[int]] = None
    tool_result_token_counts: Optional[List[int]] = None
    retrieval_header_tokens: Optional[int] = None
    tool_header_tokens: Optional[int] = None
    user_tokens: Optional[int] = None


def _get_profile(db: Session, identifier: str) -> AgentProfile:
    profile = db.query(AgentProfile).filter(AgentProfile.id == identifier).first()
    if profile:
        return profile
    profile = db.query(AgentProfile).filter(AgentProfile.name == identifier).first()
    if profile:
        return profile
    raise HTTPException(status_code=404, detail="Agent not found")


def _run_summary(profile: AgentProfile, run: Optional[LLMRun]) -> Dict[str, Any]:
    if not run:
        return {
            "status": "never",
            "headroom": profile.context_window_tokens - profile.reserved_output_tokens,
        }

    input_tokens = run.input_tokens_measured or run.input_tokens_estimated
    output_tokens = run.output_tokens_measured or run.output_tokens_estimated
    headroom = profile.context_window_tokens - (input_tokens + profile.reserved_output_tokens)
    if headroom < 0:
        headroom = 0

    return {
        "id": run.id,
        "status": run.status,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "headroom": headroom,
        "component_tokens": run.component_tokens_json,
        "included_summary": run.included_summary_json,
        "trimming_applied": run.trimming_applied_json,
        "error": run.error_json,
    }


@router.get("")
async def list_agents(db: Session = Depends(get_db), _: dict = Depends(require_auth)):
    profiles = list_agent_profiles(db)
    payload = []
    for profile in profiles:
        last_run = (
            db.query(LLMRun)
            .filter(LLMRun.agent_id == profile.id)
            .order_by(LLMRun.started_at.desc())
            .first()
        )
        payload.append(
            {
                "id": profile.id,
                "name": profile.name,
                "model": profile.model,
                "provider": profile.provider,
                "context_window_tokens": profile.context_window_tokens,
                "reserved_output_tokens": profile.reserved_output_tokens,
                "budgets": normalize_budgets(profile.budgets_json or {}),
                "last_run": _run_summary(profile, last_run),
            }
        )
    return {"agents": payload}


@router.get("/{agent_identifier}/context")
async def get_agent_context(
    agent_identifier: str,
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    _: dict = Depends(require_auth),
):
    profile = _get_profile(db, agent_identifier)
    runs = (
        db.query(LLMRun)
        .filter(LLMRun.agent_id == profile.id)
        .order_by(LLMRun.started_at.desc())
        .limit(limit)
        .all()
    )
    last_run = runs[0] if runs else None

    return {
        "agent": {
            "id": profile.id,
            "name": profile.name,
            "model": profile.model,
            "provider": profile.provider,
        },
        "budgets": normalize_budgets(profile.budgets_json or {}),
        "context_window_tokens": profile.context_window_tokens,
        "reserved_output_tokens": profile.reserved_output_tokens,
        "last_run": _run_summary(profile, last_run),
        "runs": [_run_summary(profile, run) for run in runs],
    }


@router.patch("/{agent_identifier}/context")
async def update_agent_context(
    agent_identifier: str,
    req: ContextUpdateRequest,
    db: Session = Depends(get_db),
    _: dict = Depends(require_auth),
):
    profile = _get_profile(db, agent_identifier)
    context_window = req.context_window_tokens or profile.context_window_tokens
    reserved_output = req.reserved_output_tokens if req.reserved_output_tokens is not None else profile.reserved_output_tokens

    if reserved_output >= context_window:
        raise HTTPException(status_code=400, detail="reserved_output_tokens must be less than context_window_tokens")

    updated = update_agent_profile_context(
        db,
        profile,
        context_window_tokens=req.context_window_tokens,
        reserved_output_tokens=req.reserved_output_tokens,
        budgets_json=req.budgets_json,
    )
    return {
        "id": updated.id,
        "name": updated.name,
        "model": updated.model,
        "provider": updated.provider,
        "context_window_tokens": updated.context_window_tokens,
        "reserved_output_tokens": updated.reserved_output_tokens,
        "budgets": normalize_budgets(updated.budgets_json or {}),
    }


@router.get("/{agent_identifier}/runs")
async def get_agent_runs(
    agent_identifier: str,
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    _: dict = Depends(require_auth),
):
    profile = _get_profile(db, agent_identifier)
    runs = (
        db.query(LLMRun)
        .filter(LLMRun.agent_id == profile.id)
        .order_by(LLMRun.started_at.desc())
        .limit(limit)
        .all()
    )
    return {"agent_id": profile.id, "runs": [_run_summary(profile, run) for run in runs]}


@router.post("/{agent_identifier}/simulate-context")
async def simulate_context(
    agent_identifier: str,
    req: SimulateContextRequest,
    db: Session = Depends(get_db),
    _: dict = Depends(require_auth),
):
    profile = _get_profile(db, agent_identifier)
    budgets = normalize_budgets(req.budgets_json or profile.budgets_json or {})
    context_window = req.context_window_tokens or profile.context_window_tokens
    reserved_output = req.reserved_output_tokens if req.reserved_output_tokens is not None else profile.reserved_output_tokens

    if reserved_output >= context_window:
        raise HTTPException(status_code=400, detail="reserved_output_tokens must be less than context_window_tokens")

    # Use last run tokens if caller didn't provide components
    last_run = (
        db.query(LLMRun)
        .filter(LLMRun.agent_id == profile.id)
        .order_by(LLMRun.started_at.desc())
        .first()
    )

    component_tokens = req.component_tokens or (last_run.component_tokens_json if last_run else {}) or {}
    included = last_run.included_summary_json if last_run else {}

    history_counts = req.history_token_counts or included.get("history", {}).get("token_counts", []) or []
    retrieval_counts = req.retrieval_token_counts or included.get("retrieval", {}).get("token_counts", []) or []
    tool_counts = req.tool_result_token_counts or included.get("tool_results", {}).get("token_counts", []) or []
    retrieval_header = req.retrieval_header_tokens if req.retrieval_header_tokens is not None else included.get("retrieval", {}).get("header_tokens", 0) or 0
    tool_header = req.tool_header_tokens if req.tool_header_tokens is not None else included.get("tool_results", {}).get("header_tokens", 0) or 0
    user_tokens = req.user_tokens if req.user_tokens is not None else included.get("user_message", {}).get("tokens", component_tokens.get("other", 0)) or 0

    system_tokens = component_tokens.get("system", 0)
    developer_tokens = component_tokens.get("developer", 0)
    memory_tokens = component_tokens.get("memory", 0)

    trimming_applied: List[Dict[str, Any]] = []

    if system_tokens + developer_tokens > budgets["system"]:
        return {
            "status": "blocked",
            "error": "System+developer prompt exceeds system budget",
            "trimming_applied": [],
        }

    max_input_tokens = context_window - reserved_output - budgets["safety_margin"]
    if max_input_tokens <= 0:
        return {
            "status": "blocked",
            "error": "Context window too small after safety margin and reserved output tokens",
            "trimming_applied": [],
        }

    history_tokens = sum(history_counts) + (2 if history_counts else 0)
    if history_tokens > budgets["history"]:
        before_tokens = history_tokens
        dropped = 0
        while history_counts and history_tokens > budgets["history"]:
            history_tokens -= history_counts.pop(0)
            dropped += 1
        trimming_applied.append(
            {
                "action": "drop_history_before",
                "before_tokens": before_tokens,
                "after_tokens": history_tokens,
                "dropped_messages": dropped,
            }
        )

    retrieval_tokens = sum(retrieval_counts) + (retrieval_header if retrieval_counts else 0)
    if retrieval_tokens > budgets["retrieval"]:
        before_tokens = retrieval_tokens
        dropped = 0
        while len(retrieval_counts) > 1 and retrieval_tokens > budgets["retrieval"]:
            retrieval_tokens -= retrieval_counts.pop()
            dropped += 1
        if retrieval_counts and retrieval_tokens > budgets["retrieval"]:
            retrieval_tokens = budgets["retrieval"]
        trimming_applied.append(
            {
                "action": "reduce_retrieval",
                "before_tokens": before_tokens,
                "after_tokens": retrieval_tokens,
                "dropped_docs": dropped,
            }
        )

    tool_tokens = sum(tool_counts) + (tool_header if tool_counts else 0)
    if tool_tokens > budgets["tool_results"]:
        before_tokens = tool_tokens
        tool_tokens = budgets["tool_results"]
        trimming_applied.append(
            {
                "action": "truncate_tool_outputs",
                "before_tokens": before_tokens,
                "after_tokens": tool_tokens,
            }
        )

    if memory_tokens > budgets["memory"]:
        before_tokens = memory_tokens
        memory_tokens = budgets["memory"]
        trimming_applied.append(
            {
                "action": "summarize_memory",
                "before_tokens": before_tokens,
                "after_tokens": memory_tokens,
            }
        )

    total_input = system_tokens + developer_tokens + memory_tokens + history_tokens + retrieval_tokens + tool_tokens + user_tokens

    if total_input > max_input_tokens:
        return {
            "status": "blocked",
            "error": "Context still exceeds window after trimming",
            "trimming_applied": trimming_applied,
        }

    headroom = context_window - (total_input + reserved_output)
    if headroom < 0:
        headroom = 0

    return {
        "status": "trimmed" if trimming_applied else "ok",
        "headroom": headroom,
        "context_window_tokens": context_window,
        "reserved_output_tokens": reserved_output,
        "component_tokens": {
            "system": system_tokens,
            "developer": developer_tokens,
            "memory": memory_tokens,
            "history": history_tokens,
            "retrieval": retrieval_tokens,
            "tool_results": tool_tokens,
            "other": user_tokens,
        },
        "trimming_applied": trimming_applied,
    }
