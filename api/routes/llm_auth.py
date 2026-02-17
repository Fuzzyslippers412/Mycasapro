"""
LLM Auth Routes - Qwen OAuth Device Flow
"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth.dependencies import require_auth
from database.connection import get_db
from database.models import OAuthDeviceSession
from core.qwen_oauth import (
    request_device_authorization,
    poll_device_token,
    build_oauth_settings,
    QWEN_OAUTH_SCOPE,
)

router = APIRouter(prefix="/llm", tags=["LLM"])


class QwenOAuthStartResponse(BaseModel):
    session_id: str
    user_code: str
    verification_uri: str
    verification_uri_complete: Optional[str] = None
    expires_at: str
    interval_seconds: int


class QwenOAuthPollRequest(BaseModel):
    session_id: str


class QwenOAuthPollResponse(BaseModel):
    status: str  # pending|success|error|expired
    message: Optional[str] = None
    interval_seconds: Optional[int] = None
    expires_at: Optional[int] = None
    resource_url: Optional[str] = None


@router.post("/qwen/oauth/start", response_model=QwenOAuthStartResponse)
async def start_qwen_oauth(
    user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
):
    # Supersede any existing pending sessions for this user/provider
    db.query(OAuthDeviceSession).filter(
        OAuthDeviceSession.user_id == user["id"],
        OAuthDeviceSession.provider == "qwen",
        OAuthDeviceSession.status == "pending",
    ).update({"status": "superseded"})

    try:
        payload = await request_device_authorization()
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "QWEN_OAUTH_START_FAILED",
                "message": str(exc),
            },
        )
    expires_in = int(payload.get("expires_in") or 600)
    interval = int(payload.get("interval") or 5)
    expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

    session = OAuthDeviceSession(
        user_id=user["id"],
        provider="qwen",
        device_code=payload["device_code"],
        user_code=payload["user_code"],
        verification_uri=payload["verification_uri"],
        verification_uri_complete=payload.get("verification_uri_complete"),
        code_verifier=payload["code_verifier"],
        code_challenge=payload["code_challenge"],
        code_challenge_method="S256",
        scope=QWEN_OAUTH_SCOPE,
        interval_seconds=interval,
        expires_at=expires_at,
        status="pending",
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return QwenOAuthStartResponse(
        session_id=session.id,
        user_code=session.user_code,
        verification_uri=session.verification_uri,
        verification_uri_complete=session.verification_uri_complete,
        expires_at=session.expires_at.isoformat(),
        interval_seconds=session.interval_seconds,
    )


@router.post("/qwen/oauth/poll", response_model=QwenOAuthPollResponse)
async def poll_qwen_oauth(
    request: QwenOAuthPollRequest,
    user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
):
    session = (
        db.query(OAuthDeviceSession)
        .filter(
            OAuthDeviceSession.id == request.session_id,
            OAuthDeviceSession.user_id == user["id"],
            OAuthDeviceSession.provider == "qwen",
        )
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="OAuth session not found")

    if session.expires_at < datetime.utcnow():
        session.status = "expired"
        db.add(session)
        db.commit()
        return QwenOAuthPollResponse(status="expired", message="Device code expired.")

    result = await poll_device_token(session.device_code, session.code_verifier)
    if result.get("status") == "pending":
        interval = session.interval_seconds
        if result.get("slow_down"):
            interval = min(interval + 5, 30)
            session.interval_seconds = interval
            db.add(session)
            db.commit()
        return QwenOAuthPollResponse(status="pending", interval_seconds=interval)

    if result.get("status") == "error":
        session.status = "error"
        session.error = result.get("error_description") or result.get("error") or "OAuth error"
        db.add(session)
        db.commit()
        return QwenOAuthPollResponse(status="error", message=session.error)

    token_data = result.get("token") or {}
    oauth_settings = build_oauth_settings(token_data)

    from core.settings_typed import get_settings_store
    from core.llm_client import reset_llm_client

    store = get_settings_store()
    settings = store.get()
    settings.system.llm_auth_type = "qwen-oauth"
    settings.system.llm_provider = "openai-compatible"
    settings.system.llm_base_url = oauth_settings.get("resource_url")
    current_model = getattr(settings.system, "llm_model", None) or ""
    if current_model.strip() in {"", "qwen2.5-72b-instruct", "qwen2.5-72b", "qwen-plus"}:
        settings.system.llm_model = "qwen3-coder-next"
    settings.system.llm_oauth = oauth_settings
    store.save(settings)
    reset_llm_client()

    session.status = "approved"
    session.error = None
    db.add(session)
    db.commit()

    return QwenOAuthPollResponse(
        status="success",
        expires_at=oauth_settings.get("expiry_date"),
        resource_url=oauth_settings.get("resource_url"),
    )


@router.delete("/qwen/oauth")
async def disconnect_qwen_oauth(
    user: dict = Depends(require_auth),
):
    from core.settings_typed import get_settings_store
    from core.llm_client import reset_llm_client

    store = get_settings_store()
    settings = store.get()
    settings.system.llm_auth_type = "api_key"
    settings.system.llm_oauth = None
    store.save(settings)
    reset_llm_client()

    return {"success": True}
