from __future__ import annotations

from typing import Dict, Any, Optional, List
import os

from sqlalchemy.orm import Session

from core.fleet_manager import FleetManager
from core.llm_client import get_llm_client
from database.models import AgentProfile


DEFAULT_CONTEXT_WINDOW_TOKENS = int(os.getenv("LLM_CONTEXT_WINDOW_TOKENS", "32768"))
DEFAULT_RESERVED_OUTPUT_TOKENS = int(os.getenv("LLM_RESERVED_OUTPUT_TOKENS", "2048"))

LEGACY_DEFAULT_BUDGETS: Dict[str, int] = {
    "system": 2048,
    "memory": 4096,
    "history": 8192,
    "retrieval": 4096,
    "tool_results": 2048,
    "safety_margin": 512,
}

DEFAULT_BUDGETS: Dict[str, int] = {
    "system": 4096,
    "memory": 4096,
    "history": 8192,
    "retrieval": 4096,
    "tool_results": 2048,
    "safety_margin": 512,
}


def get_known_agent_ids() -> List[str]:
    return sorted(FleetManager.DEFAULT_AGENTS.keys())


def _is_legacy_defaults(source: Dict[str, Any]) -> bool:
    try:
        for key, value in LEGACY_DEFAULT_BUDGETS.items():
            if int(source.get(key, -1)) != value:
                return False
        return True
    except (TypeError, ValueError):
        return False


def normalize_budgets(budgets: Optional[Dict[str, Any]]) -> Dict[str, int]:
    normalized: Dict[str, int] = {}
    source = budgets or {}
    if source and _is_legacy_defaults(source):
        source = {}
    for key, default_value in DEFAULT_BUDGETS.items():
        raw = source.get(key, default_value)
        try:
            value = int(raw)
        except (TypeError, ValueError):
            value = default_value
        if value < 0:
            value = 0
        normalized[key] = value
    return normalized


def get_or_create_agent_profile(
    db: Session,
    name: str,
    model: Optional[str] = None,
    provider: Optional[str] = None,
) -> AgentProfile:
    existing = db.query(AgentProfile).filter(AgentProfile.name == name).first()
    if existing:
        # Ensure required keys exist
        budgets = normalize_budgets(existing.budgets_json or {})
        if budgets != (existing.budgets_json or {}):
            existing.budgets_json = budgets
            db.add(existing)
            db.commit()
            db.refresh(existing)
        return existing

    llm = get_llm_client()
    base_provider = provider or llm.provider or "openai-compatible"
    base_model = model or llm.model or "unknown"

    # If FleetManager has a default model for this agent, prefer it.
    config = FleetManager.DEFAULT_AGENTS.get(name)
    if config and config.default_model:
        base_model = config.default_model

    profile = AgentProfile(
        name=name,
        model=base_model,
        provider=base_provider,
        context_window_tokens=DEFAULT_CONTEXT_WINDOW_TOKENS,
        reserved_output_tokens=DEFAULT_RESERVED_OUTPUT_TOKENS,
        budgets_json=normalize_budgets({}),
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def list_agent_profiles(db: Session) -> List[AgentProfile]:
    profiles = db.query(AgentProfile).all()
    existing_names = {p.name for p in profiles}
    for agent_id in get_known_agent_ids():
        if agent_id not in existing_names:
            profiles.append(get_or_create_agent_profile(db, agent_id))
    return profiles


def update_agent_profile_context(
    db: Session,
    profile: AgentProfile,
    context_window_tokens: Optional[int] = None,
    reserved_output_tokens: Optional[int] = None,
    budgets_json: Optional[Dict[str, Any]] = None,
) -> AgentProfile:
    if context_window_tokens is not None:
        profile.context_window_tokens = int(context_window_tokens)
    if reserved_output_tokens is not None:
        profile.reserved_output_tokens = int(reserved_output_tokens)
    if budgets_json is not None:
        profile.budgets_json = normalize_budgets(budgets_json)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile
