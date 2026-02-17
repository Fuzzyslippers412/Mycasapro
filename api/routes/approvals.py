from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

router = APIRouter(prefix="/approvals", tags=["Approvals"])

# Minimal in-memory approvals for now
_APPROVALS = []

class ApprovalRequest(BaseModel):
    action: str
    payload: dict
    requested_by: str = "system"

@router.post("/request")
async def request_approval(req: ApprovalRequest):
    item = {
        "id": len(_APPROVALS) + 1,
        "action": req.action,
        "payload": req.payload,
        "requested_by": req.requested_by,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
    }
    _APPROVALS.append(item)
    return {"success": True, "approval": item}

@router.get("")
async def list_approvals():
    return {"items": _APPROVALS}
