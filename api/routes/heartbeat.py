"""
Memory Heartbeat API Routes
============================

Endpoints for managing memory heartbeat and decay.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from core.secondbrain import MemoryHeartbeat
from config.settings import get_vault_path, DEFAULT_TENANT_ID
from core.tenant_identity import TenantIdentityManager
from agents.heartbeat_checker import HouseholdHeartbeatChecker

router = APIRouter(prefix="/heartbeat", tags=["heartbeat"])


def get_memory_base() -> Path:
    """Get memory base path"""
    return get_vault_path(DEFAULT_TENANT_ID)


@router.post("/run")
async def run_heartbeat(
    decay_tacit: bool = True,
    update_recency: bool = True,
    synthesize: bool = True,
    auto_archive: bool = False
):
    """Run memory heartbeat cycle"""
    try:
        memory_base = get_memory_base()
        heartbeat = MemoryHeartbeat(memory_base)

        results = heartbeat.run_heartbeat(
            decay_tacit=decay_tacit,
            update_recency=update_recency,
            synthesize=synthesize,
            auto_archive=auto_archive,
        )

        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hot-entities/{agent_id}")
async def get_hot_entities(agent_id: str):
    """Get hot (recently accessed) entities for an agent"""
    try:
        memory_base = get_memory_base()
        heartbeat = MemoryHeartbeat(memory_base)

        entities = heartbeat.get_hot_entities(agent_id)

        return {
            "agent_id": agent_id,
            "hot_entities": entities,
            "count": len(entities),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stale-entities/{agent_id}")
async def get_stale_entities(agent_id: str, days_threshold: int = 90):
    """Get stale entities for an agent"""
    try:
        memory_base = get_memory_base()
        heartbeat = MemoryHeartbeat(memory_base)

        entities = heartbeat.get_stale_entities(agent_id, days_threshold)

        return {
            "agent_id": agent_id,
            "stale_entities": entities,
            "count": len(entities),
            "days_threshold": days_threshold,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_heartbeat_status():
    """Get heartbeat execution history"""
    try:
        memory_base = get_memory_base()
        heartbeat = MemoryHeartbeat(memory_base)

        log = heartbeat._load_heartbeat_log()

        return {
            "last_run": log.get("last_run"),
            "run_history": log.get("runs", [])[-10:],  # Last 10 runs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/household/run")
async def run_household_heartbeat():
    """Run household heartbeat checks (inbox, calendar, bills, maintenance, security)."""
    try:
        checker = HouseholdHeartbeatChecker(DEFAULT_TENANT_ID)
        result = await checker.run_heartbeat()
        return result.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/household/consolidate")
async def run_household_consolidation():
    """Run memory consolidation for household identity files."""
    try:
        checker = HouseholdHeartbeatChecker(DEFAULT_TENANT_ID)
        return await checker.run_memory_consolidation()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/household/status")
async def get_household_heartbeat_status():
    """Get household heartbeat state and last consolidation timestamp."""
    try:
        manager = TenantIdentityManager(DEFAULT_TENANT_ID)
        identity = manager.load_identity_package()
        return {
            "tenant_id": DEFAULT_TENANT_ID,
            "heartbeat_state": identity.get("heartbeat_state"),
            "last_consolidation": identity.get("heartbeat_state", {}).get("lastConsolidation"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
