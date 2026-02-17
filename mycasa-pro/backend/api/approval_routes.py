"""
Approval management endpoints
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..core.utils import generate_correlation_id, log_action
from ..storage.database import get_db_session
from ..storage.models import ApprovalDB

router = APIRouter(prefix="/approvals", tags=["Approvals"])


class ApprovalResponse(BaseModel):
    reason: str = ""


def get_db():
    db = get_db_session()
    try:
        yield db
    finally:
        db.close()


@router.get("/pending")
async def get_pending_approvals(
    agent_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all pending approval requests"""
    try:
        query = db.query(ApprovalDB).filter(ApprovalDB.status == "pending")
        
        if agent_id:
            query = query.filter(ApprovalDB.requested_by == agent_id)
        
        approvals = query.order_by(ApprovalDB.created_at.desc()).all()
        
        return {
            "approvals": [
                {
                    "id": str(a.id),
                    "requester_agent": a.requested_by or "unknown",
                    "approver_agent": a.decision_by or "manager",
                    "approval_type": a.approval_type,
                    "amount_usd": a.requested_amount,
                    "description": f"{a.approval_type} approval for {a.entity_type or 'item'} #{a.entity_id or 'N/A'}",
                    "details": {
                        "entity_type": a.entity_type,
                        "entity_id": a.entity_id,
                        "correlation_id": a.correlation_id,
                    },
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                    "status": a.status,
                }
                for a in approvals
            ],
            "count": len(approvals),
        }
    except Exception as e:
        return {
            "approvals": [],
            "count": 0,
            "error": str(e),
        }


@router.post("/{approval_id}/approve")
async def approve_request(
    approval_id: str, 
    response: ApprovalResponse,
    db: Session = Depends(get_db)
):
    """Grant an approval"""
    correlation_id = generate_correlation_id()

    try:
        approval = db.query(ApprovalDB).filter(ApprovalDB.id == int(approval_id)).first()
        
        if not approval:
            raise HTTPException(status_code=404, detail="Approval not found")
        
        if approval.status != "pending":
            raise HTTPException(status_code=400, detail="Approval already processed")
        
        approval.status = "approved"
        approval.decided_at = datetime.utcnow()
        approval.decision_by = "user"
        approval.decision_reason = response.reason or "Approved by user"
        
        db.commit()

        log_action("approval_granted", {
            "approval_id": approval_id,
            "reason": response.reason,
        })

        return {
            "status": "approved",
            "approval_id": approval_id,
            "correlation_id": correlation_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{approval_id}/deny")
async def deny_request(
    approval_id: str, 
    response: ApprovalResponse,
    db: Session = Depends(get_db)
):
    """Deny an approval"""
    correlation_id = generate_correlation_id()

    if not response.reason:
        raise HTTPException(status_code=400, detail="Reason required for denial")

    try:
        approval = db.query(ApprovalDB).filter(ApprovalDB.id == int(approval_id)).first()
        
        if not approval:
            raise HTTPException(status_code=404, detail="Approval not found")
        
        if approval.status != "pending":
            raise HTTPException(status_code=400, detail="Approval already processed")
        
        approval.status = "denied"
        approval.decided_at = datetime.utcnow()
        approval.decision_by = "user"
        approval.decision_reason = response.reason
        
        db.commit()

        log_action("approval_denied", {
            "approval_id": approval_id,
            "reason": response.reason,
        })

        return {
            "status": "denied",
            "approval_id": approval_id,
            "correlation_id": correlation_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_approval_history(
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get approval history (approved/denied)"""
    try:
        approvals = db.query(ApprovalDB).filter(
            ApprovalDB.status.in_(["approved", "denied"])
        ).order_by(ApprovalDB.created_at.desc()).limit(limit).all()

        return {
            "approvals": [
                {
                    "id": str(a.id),
                    "requester_agent": a.requested_by or "unknown",
                    "approver_agent": a.decision_by or "manager",
                    "approval_type": a.approval_type,
                    "amount_usd": a.requested_amount,
                    "description": f"{a.approval_type} approval for {a.entity_type or 'item'} #{a.entity_id or 'N/A'}",
                    "details": {
                        "entity_type": a.entity_type,
                        "entity_id": a.entity_id,
                        "correlation_id": a.correlation_id,
                    },
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                    "decided_at": a.decided_at.isoformat() if a.decided_at else None,
                    "status": a.status,
                    "resolution_reason": a.decision_reason,
                }
                for a in approvals
            ],
            "count": len(approvals),
        }
    except Exception as e:
        return {
            "approvals": [],
            "count": 0,
            "error": str(e),
        }
