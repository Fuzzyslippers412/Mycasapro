from fastapi import APIRouter
from database import get_db
from database.models import EventLog
from datetime import datetime

router = APIRouter(prefix="/audit", tags=["Audit"])

@router.get("/events")
async def list_events(limit: int = 50):
    with get_db() as db:
        rows = db.query(EventLog).order_by(EventLog.created_at.desc()).limit(limit).all()
        return {
            "events": [
                {
                    "id": r.id,
                    "event_id": r.event_id,
                    "event_type": r.event_type,
                    "source": r.source,
                    "payload": r.payload,
                    "status": r.status,
                    "attempts": r.attempts,
                    "last_error": r.last_error,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                } for r in rows
            ]
        }
