"""
Session helpers for DB-backed, cookie-authenticated sessions.
"""
from __future__ import annotations

from datetime import datetime, timedelta
import secrets
import uuid
from typing import Optional

from fastapi import Request, Response
from sqlalchemy.orm import Session

from auth.security import hash_token
from auth.settings import SESSION_COOKIE_NAME, SESSION_TTL_DAYS, SESSION_COOKIE_SAMESITE, SESSION_COOKIE_SECURE
from database.models import SessionToken


def _expires_at(ttl_days: int | None = None) -> datetime:
    return datetime.utcnow() + timedelta(days=ttl_days or SESSION_TTL_DAYS)


def create_session(
    db: Session,
    user_id: int,
    ip_address: str | None = None,
    user_agent: str | None = None,
    ttl_days: Optional[int] = None,
) -> tuple[str, SessionToken]:
    raw_token = secrets.token_urlsafe(48)
    token_hash = hash_token(raw_token)
    session = SessionToken(
        token_hash=token_hash,
        token_type="session",
        session_id=str(uuid.uuid4()),
        user_id=user_id,
        expires_at=_expires_at(ttl_days),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return raw_token, session


def set_session_cookie(response: Response, raw_token: str, expires_at: datetime) -> None:
    max_age = max(0, int((expires_at - datetime.utcnow()).total_seconds()))
    response.set_cookie(
        SESSION_COOKIE_NAME,
        raw_token,
        httponly=True,
        secure=SESSION_COOKIE_SECURE,
        samesite=SESSION_COOKIE_SAMESITE,
        max_age=max_age,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")


def get_session_from_request(request: Request, db: Session) -> Optional[SessionToken]:
    raw_token = request.cookies.get(SESSION_COOKIE_NAME)
    if not raw_token:
        return None
    token_hash = hash_token(raw_token)
    session = (
        db.query(SessionToken)
        .filter(SessionToken.token_hash == token_hash, SessionToken.token_type == "session")
        .first()
    )
    return session
