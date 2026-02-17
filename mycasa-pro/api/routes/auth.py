from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from pathlib import Path
from uuid import uuid4

from auth.dependencies import require_auth
from auth.schemas import (
    LoginRequest,
    RegisterRequest,
    RefreshRequest,
    LogoutRequest,
    LogoutAllRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    UpdateMeRequest,
    TokenResponse,
    UserResponse,
)
from auth.security import (
    AuthError,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    hash_token,
    generate_token_urlsafe,
    verify_legacy_sha256,
    verify_password,
)
from auth.sessions import create_session, set_session_cookie, clear_session_cookie, get_session_from_request
from auth.settings import (
    LOCKOUT_MAX_ATTEMPTS,
    LOCKOUT_WINDOW_MINUTES,
    LOCKOUT_DURATION_MINUTES,
    PASSWORD_RESET_TOKEN_TTL_MINUTES,
)
from auth.audit import log_audit
from api.middleware.ratelimit import rate_limit
from core.config import get_config
from config.settings import DATA_DIR, DEFAULT_TENANT_ID
from database.connection import get_db
from database.models import (
    User,
    SessionToken,
    UserCredential,
    Org,
    OrgMembership,
    Role,
    UserRole,
    PasswordResetToken,
    LoginAttempt,
)

router = APIRouter(prefix="/auth", tags=["Auth"])

AVATAR_DIR = DATA_DIR / "avatars"
AVATAR_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_AVATAR_TYPES = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
}
MAX_AVATAR_BYTES = 4 * 1024 * 1024


def _user_response(user: User) -> UserResponse:
    avatar_url = "/api/auth/avatar" if getattr(user, "avatar_path", None) else None
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        is_admin=user.is_admin,
        display_name=getattr(user, "display_name", None),
        status=getattr(user, "status", None),
        org_id=getattr(user, "org_id", None),
        tenant_id=getattr(user, "tenant_id", None),
        avatar_url=avatar_url,
    )


def _normalize_username(username: str) -> str:
    return username.strip()


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _request_meta(request: Request) -> tuple[str | None, str | None]:
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return ip_address, user_agent


def _record_login_attempt(
    db: Session,
    identifier: str,
    user_id: int | None,
    success: bool,
    failure_reason: str | None,
    ip_address: str | None,
    user_agent: str | None,
) -> None:
    attempt = LoginAttempt(
        identifier=identifier,
        user_id=user_id,
        success=success,
        failure_reason=failure_reason,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(attempt)
    db.commit()


def _maybe_lockout(db: Session, user: User | None, identifier: str) -> None:
    window_start = datetime.utcnow() - timedelta(minutes=LOCKOUT_WINDOW_MINUTES)
    query = db.query(LoginAttempt).filter(
        LoginAttempt.success == False,  # noqa: E712
        LoginAttempt.created_at >= window_start,
    )
    if user:
        query = query.filter(LoginAttempt.user_id == user.id)
    else:
        query = query.filter(LoginAttempt.identifier == identifier)
    if query.count() >= LOCKOUT_MAX_ATTEMPTS and user:
        user.lockout_until = datetime.utcnow() + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
        db.add(user)
        db.commit()


def _get_default_org(db: Session) -> Org:
    org = db.query(Org).filter(Org.is_default == True).first()  # noqa: E712
    if not org:
        org = Org(name="Default Household", slug=DEFAULT_TENANT_ID, is_default=True)
        db.add(org)
        db.commit()
        db.refresh(org)
    return org


def _ensure_role(db: Session, name: str) -> Role:
    role = db.query(Role).filter(Role.name == name).first()
    if not role:
        role = Role(name=name, description=name.replace("_", " ").title(), scope="global", is_system=True)
        db.add(role)
        db.commit()
        db.refresh(role)
    return role


def _ensure_membership(db: Session, org_id: str, user_id: int) -> None:
    existing = (
        db.query(OrgMembership)
        .filter(OrgMembership.org_id == org_id, OrgMembership.user_id == user_id)
        .first()
    )
    if not existing:
        db.add(OrgMembership(org_id=org_id, user_id=user_id, status="active", joined_at=datetime.utcnow()))
        db.commit()


def _ensure_user_role(db: Session, user_id: int, role_name: str, org_id: str | None) -> None:
    role = _ensure_role(db, role_name)
    existing = (
        db.query(UserRole)
        .filter(UserRole.user_id == user_id, UserRole.role_id == role.id, UserRole.org_id == org_id)
        .first()
    )
    if not existing:
        db.add(UserRole(user_id=user_id, role_id=role.id, org_id=org_id))
        db.commit()


def _ensure_credentials(db: Session, user: User, password_hash: str) -> None:
    credential = db.query(UserCredential).filter(UserCredential.user_id == user.id).first()
    if credential:
        credential.password_hash = password_hash
        credential.last_changed_at = datetime.utcnow()
        credential.requires_reset = False
        db.add(credential)
        db.commit()
        return
    db.add(UserCredential(user_id=user.id, password_hash=password_hash))
    db.commit()


@router.post("/login", response_model=TokenResponse, dependencies=[Depends(rate_limit)])
async def login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    identifier = req.username.strip()
    identifier_normalized = identifier.lower()
    ip_address, user_agent = _request_meta(request)
    now = datetime.utcnow()

    user = (
        db.query(User)
        .filter(
            (User.username_normalized == identifier_normalized)
            | (User.email_normalized == identifier_normalized)
        )
        .first()
    )

    if user and user.lockout_until and user.lockout_until > now:
        _record_login_attempt(db, identifier_normalized, user.id, False, "locked", ip_address, user_agent)
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Account locked. Try again later.")

    if not user or not user.is_active or getattr(user, "status", "active") == "disabled":
        _record_login_attempt(db, identifier_normalized, user.id if user else None, False, "invalid", ip_address, user_agent)
        _maybe_lockout(db, user, identifier_normalized)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    credential = db.query(UserCredential).filter(UserCredential.user_id == user.id).first()
    password_hash = credential.password_hash if credential else user.hashed_password

    if not verify_password(req.password, password_hash):
        if verify_legacy_sha256(req.password, password_hash):
            upgraded_hash = get_password_hash(req.password)
            user.hashed_password = upgraded_hash
            _ensure_credentials(db, user, upgraded_hash)
        else:
            _record_login_attempt(db, identifier_normalized, user.id, False, "invalid", ip_address, user_agent)
            _maybe_lockout(db, user, identifier_normalized)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    elif not credential:
        _ensure_credentials(db, user, password_hash)

    if user.lockout_until:
        user.lockout_until = None
    if not user.status:
        user.status = "active"
    db.add(user)
    db.commit()

    _record_login_attempt(db, identifier_normalized, user.id, True, None, ip_address, user_agent)

    access_token = create_access_token(user)
    refresh_token = create_refresh_token(user)
    refresh_hash = hash_token(refresh_token)
    refresh_expiry = datetime.utcnow() + timedelta(days=get_config().JWT_REFRESH_EXPIRATION)
    refresh_session = SessionToken(
        token_hash=refresh_hash,
        token_type="refresh",
        user_id=user.id,
        expires_at=refresh_expiry,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(refresh_session)
    db.commit()

    raw_session, session = create_session(db, user.id, ip_address, user_agent)
    response = JSONResponse(
        content=TokenResponse(
            token=access_token,
            access_token=access_token,
            refresh_token=refresh_token,
            user=_user_response(user),
        ).dict()
    )
    set_session_cookie(response, raw_session, session.expires_at)
    log_audit(
        db,
        action="auth.login",
        actor_user_id=user.id,
        target_type="user",
        target_id=str(user.id),
        org_id=getattr(user, "org_id", None),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return response


@router.post("/register", response_model=TokenResponse, dependencies=[Depends(rate_limit)])
async def register(req: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    username = _normalize_username(req.username)
    email = _normalize_email(req.email)
    if not username:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Username required")
    if not email:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Email required")

    existing = (
        db.query(User)
        .filter(
            (func.lower(User.username) == username.lower())
            | (func.lower(User.email) == email.lower())
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username or email already exists")

    ip_address, user_agent = _request_meta(request)
    is_first_user = db.query(User).count() == 0
    default_org = _get_default_org(db)
    user = User(
        username=username,
        username_normalized=username.lower(),
        email=email,
        email_normalized=email.lower(),
        hashed_password=get_password_hash(req.password),
        is_admin=is_first_user,
        is_active=True,
        status="active",
        org_id=default_org.id,
    )
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username or email already exists")

    _ensure_credentials(db, user, user.hashed_password)
    _ensure_membership(db, default_org.id, user.id)
    _ensure_user_role(db, user.id, "SUPER_ADMIN" if is_first_user else "MEMBER", default_org.id)

    access_token = create_access_token(user)
    refresh_token = create_refresh_token(user)
    refresh_hash = hash_token(refresh_token)
    refresh_expiry = datetime.utcnow() + timedelta(days=get_config().JWT_REFRESH_EXPIRATION)
    refresh_session = SessionToken(
        token_hash=refresh_hash,
        token_type="refresh",
        user_id=user.id,
        expires_at=refresh_expiry,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(refresh_session)
    db.commit()

    raw_session, session = create_session(db, user.id, ip_address, user_agent)
    response = JSONResponse(
        content=TokenResponse(
            token=access_token,
            access_token=access_token,
            refresh_token=refresh_token,
            user=_user_response(user),
        ).dict()
    )
    set_session_cookie(response, raw_session, session.expires_at)
    log_audit(
        db,
        action="auth.register",
        actor_user_id=user.id,
        target_type="user",
        target_id=str(user.id),
        org_id=default_org.id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return response


@router.post("/refresh", response_model=TokenResponse)
async def refresh(req: RefreshRequest, db: Session = Depends(get_db)):
    try:
        payload = decode_token(req.refresh_token)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=exc.message) from exc

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    token_hash = hash_token(req.refresh_token)
    session = (
        db.query(SessionToken)
        .filter(
            SessionToken.token_hash == token_hash,
            SessionToken.token_type == "refresh",
            SessionToken.revoked_at.is_(None),
        )
        .first()
    )
    if not session or session.expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")

    user = db.query(User).filter(User.id == session.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive or not found")

    session.last_used_at = datetime.utcnow()
    db.add(session)
    db.commit()

    access_token = create_access_token(user)
    return TokenResponse(
        token=access_token,
        access_token=access_token,
        refresh_token=req.refresh_token,
        user=_user_response(user),
    )


@router.post("/logout")
async def logout(
    request: Request,
    user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
    req: LogoutRequest | None = None,
):
    now = datetime.utcnow()
    session = get_session_from_request(request, db) if request else None
    if session and session.user_id == user["id"]:
        session.revoked_at = now
        db.add(session)

    refresh_token = req.refresh_token if req else None
    if refresh_token:
        token_hash = hash_token(refresh_token)
        db.query(SessionToken).filter(
            SessionToken.token_hash == token_hash,
            SessionToken.user_id == user["id"],
            SessionToken.token_type == "refresh",
        ).update({SessionToken.revoked_at: now})

    db.commit()
    response = JSONResponse(content={"success": True})
    clear_session_cookie(response)
    log_audit(
        db,
        action="auth.logout",
        actor_user_id=user["id"],
        target_type="user",
        target_id=str(user["id"]),
        org_id=user.get("org_id"),
    )
    return response


@router.post("/logout-all")
async def logout_all(
    request: Request,
    user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
    req: LogoutAllRequest | None = None,
):
    now = datetime.utcnow()
    db.query(SessionToken).filter(SessionToken.user_id == user["id"]).update({SessionToken.revoked_at: now})
    db.commit()
    response = JSONResponse(content={"success": True})
    clear_session_cookie(response)
    log_audit(
        db,
        action="auth.logout_all",
        actor_user_id=user["id"],
        target_type="user",
        target_id=str(user["id"]),
        org_id=user.get("org_id"),
    )
    return response


@router.get("/me", response_model=UserResponse)
async def get_me(user: dict = Depends(require_auth)):
    return user


@router.patch("/me", response_model=UserResponse)
async def update_me(
    payload: UpdateMeRequest,
    user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
):
    db_user = db.query(User).filter(User.id == user["id"]).first()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if payload.display_name is not None:
        db_user.display_name = payload.display_name.strip() or None
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    log_audit(
        db,
        action="auth.profile.update",
        actor_user_id=db_user.id,
        target_type="user",
        target_id=str(db_user.id),
        org_id=getattr(db_user, "org_id", None),
    )
    return _user_response(db_user)


@router.post("/forgot-password", dependencies=[Depends(rate_limit)])
async def forgot_password(req: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)):
    identifier = _normalize_email(req.email)
    ip_address, user_agent = _request_meta(request)
    user = db.query(User).filter(User.email_normalized == identifier).first()
    raw_token = generate_token_urlsafe()
    if user:
        token_hash = hash_token(raw_token)
        expires_at = datetime.utcnow() + timedelta(minutes=PASSWORD_RESET_TOKEN_TTL_MINUTES)
        db.add(PasswordResetToken(user_id=user.id, token_hash=token_hash, expires_at=expires_at))
        db.commit()
        log_audit(
            db,
            action="auth.forgot_password",
            actor_user_id=user.id,
            target_type="user",
            target_id=str(user.id),
            org_id=getattr(user, "org_id", None),
            ip_address=ip_address,
            user_agent=user_agent,
        )
    return {"success": True, "reset_token": raw_token}


@router.post("/reset-password", dependencies=[Depends(rate_limit)])
async def reset_password(req: ResetPasswordRequest, request: Request, db: Session = Depends(get_db)):
    token_hash = hash_token(req.token)
    reset_token = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used_at.is_(None),
        )
        .first()
    )
    if not reset_token or reset_token.expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")

    user = db.query(User).filter(User.id == reset_token.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    new_hash = get_password_hash(req.new_password)
    user.hashed_password = new_hash
    _ensure_credentials(db, user, new_hash)
    reset_token.used_at = datetime.utcnow()
    db.add(reset_token)
    db.query(SessionToken).filter(SessionToken.user_id == user.id).update(
        {SessionToken.revoked_at: datetime.utcnow()}
    )
    db.commit()

    ip_address, user_agent = _request_meta(request)
    log_audit(
        db,
        action="auth.reset_password",
        actor_user_id=user.id,
        target_type="user",
        target_id=str(user.id),
        org_id=getattr(user, "org_id", None),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return {"success": True}


@router.get("/avatar")
async def get_avatar(user: dict = Depends(require_auth), db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user["id"]).first()
    if not db_user or not db_user.avatar_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avatar not set")
    avatar_path = Path(db_user.avatar_path)
    if not avatar_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avatar file missing")
    media_type = "image/jpeg"
    if avatar_path.suffix.lower() == ".png":
        media_type = "image/png"
    elif avatar_path.suffix.lower() == ".webp":
        media_type = "image/webp"
    return FileResponse(avatar_path, media_type=media_type)


@router.post("/avatar", response_model=UserResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    user: dict = Depends(require_auth),
    db: Session = Depends(get_db),
):
    if file.content_type not in ALLOWED_AVATAR_TYPES:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Unsupported image type")

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")
    if len(contents) > MAX_AVATAR_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Avatar too large")

    ext = ALLOWED_AVATAR_TYPES[file.content_type]
    filename = f"user_{user['id']}_{uuid4().hex}.{ext}"
    avatar_path = AVATAR_DIR / filename
    avatar_path.write_bytes(contents)

    db_user = db.query(User).filter(User.id == user["id"]).first()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Remove old avatar if present
    if db_user.avatar_path:
        try:
            old_path = Path(db_user.avatar_path)
            if old_path.exists():
                old_path.unlink()
        except Exception:
            pass

    db_user.avatar_path = str(avatar_path)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    log_audit(
        db,
        action="auth.avatar.update",
        actor_user_id=db_user.id,
        target_type="user",
        target_id=str(db_user.id),
        org_id=getattr(db_user, "org_id", None),
    )
    return _user_response(db_user)
