"""
FastAPI dependencies for authentication and authorization.
"""
from __future__ import annotations

from typing import Any, Dict, Optional
from datetime import datetime

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import User
from auth.sessions import get_session_from_request
from auth.permissions import get_user_permissions
from core.config import get_config
from auth.personal_mode import ensure_personal_user


def _get_bearer_token(request: Request) -> Optional[str]:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1].strip()
    return None


def _serialize_user(user: User) -> Dict[str, Any]:
    avatar_url = "/api/auth/avatar" if getattr(user, "avatar_path", None) else None
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_admin": user.is_admin,
        "is_active": user.is_active,
        "display_name": getattr(user, "display_name", None),
        "status": getattr(user, "status", None),
        "org_id": getattr(user, "org_id", None),
        "tenant_id": getattr(user, "tenant_id", None),
        "avatar_url": avatar_url,
    }


async def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> Optional[Dict[str, Any]]:
    """Return the current user dict if authenticated, else None."""
    if getattr(request.state, "user", None) is not None:
        return request.state.user

    # Prefer session cookie if present
    session = get_session_from_request(request, db)
    if session:
        if session.revoked_at or session.expires_at < datetime.utcnow():
            return None
        user = db.query(User).filter(User.id == session.user_id).first()
        if not user or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive or not found")
        if getattr(user, "status", "active") == "disabled":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")
        session.last_used_at = datetime.utcnow()
        db.add(session)
        db.commit()
        user_dict = _serialize_user(user)
        request.state.user = user_dict
        request.state.session = session
        return user_dict

    token_payload = getattr(request.state, "token_payload", None)
    if token_payload is None:
        auth_error = getattr(request.state, "auth_error", None)
        if auth_error and not get_config().PERSONAL_MODE:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=auth_error)
        if get_config().PERSONAL_MODE:
            user = ensure_personal_user(db)
            user_dict = _serialize_user(user)
            request.state.user = user_dict
            return user_dict
        return None
    if token_payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token")

    user_id = token_payload.get("sub")
    if not user_id:
        return None

    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token")

    user = db.query(User).filter(User.id == user_id_int).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive or not found")

    user_dict = _serialize_user(user)
    request.state.user = user_dict
    return user_dict


async def require_auth(user: Optional[Dict[str, Any]] = Depends(get_current_user)) -> Dict[str, Any]:
    """Require an authenticated user."""
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return user


async def require_admin(user: Dict[str, Any] = Depends(require_auth)) -> Dict[str, Any]:
    """Require an admin user."""
    if not user.get("is_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


def require_permission(permission: str):
    """Require a specific permission."""

    async def _dependency(
        user: Dict[str, Any] = Depends(require_auth),
        db: Session = Depends(get_db),
    ) -> Dict[str, Any]:
        if user.get("is_admin"):
            return user
        perms = get_user_permissions(db, user_id=user["id"], org_id=user.get("org_id"))
        if permission not in perms:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission required")
        return user

    return _dependency
