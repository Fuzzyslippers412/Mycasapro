"""
Audit logging for sensitive actions.
"""
from __future__ import annotations

from typing import Any, Optional
from datetime import datetime

from sqlalchemy.orm import Session

from database.models import AuditLog


def log_audit(
    db: Session,
    action: str,
    actor_user_id: Optional[int] = None,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    org_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> AuditLog:
    entry = AuditLog(
        actor_user_id=actor_user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        org_id=org_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata_json=metadata or {},
        created_at=datetime.utcnow(),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
