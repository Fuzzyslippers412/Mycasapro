"""
Session cleanup routes.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional

from auth.dependencies import require_auth
from core.agent_sessions import clear_sessions

router = APIRouter(prefix="/agents", tags=["Agent Sessions"])


class SessionCleanupRequest(BaseModel):
    prefix: Optional[str] = "mycasa_"
    clear_all: bool = False


@router.post("/sessions/cleanup")
async def cleanup_sessions(
    req: SessionCleanupRequest,
    user: dict = Depends(require_auth),
):
    """Remove session records to avoid context sharing."""
    return clear_sessions(prefix=req.prefix or "mycasa_", clear_all=req.clear_all)
