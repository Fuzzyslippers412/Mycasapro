"""
Memory Heartbeat API Routes
============================

Endpoints for managing memory heartbeat and decay.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from pathlib import Path

from core.secondbrain import MemoryHeartbeat

router = APIRouter(prefix="/heartbeat", tags=["heartbeat"])


def get_memory_base() -> Path:
    """Get memory base path"""
    return Path.home() / "clawd" / "apps" / "mycasa-pro" / "memory"


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
