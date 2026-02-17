"""
Security utilities for authentication (password hashing + JWT).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import secrets
from typing import Any, Dict, Optional

import bcrypt
import jwt

from core.config import get_config


ALGORITHM = "HS256"


@dataclass
class AuthError(Exception):
    """Authentication error with a safe message for clients."""
    message: str


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def verify_legacy_sha256(password: str, hashed_password: str) -> bool:
    """Verify a legacy SHA256 hash (for migration)."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest() == hashed_password


def _base_token_payload(user: Any) -> Dict[str, Any]:
    tenant_id = getattr(user, "tenant_id", None)
    if tenant_id is None and isinstance(user, dict):
        tenant_id = user.get("tenant_id")
    if tenant_id is None:
        tenant_id = get_config().TENANT_ID
    return {
        "sub": str(getattr(user, "id", user.get("id") if isinstance(user, dict) else "")),
        "username": getattr(user, "username", user.get("username") if isinstance(user, dict) else ""),
        "is_admin": bool(getattr(user, "is_admin", user.get("is_admin") if isinstance(user, dict) else False)),
        "tenant_id": tenant_id,
    }


def create_access_token(user: Any, expires_minutes: Optional[int] = None) -> str:
    """Create a signed JWT access token."""
    config = get_config()
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes or config.JWT_EXPIRATION)
    payload = {
        **_base_token_payload(user),
        "type": "access",
        "iat": datetime.utcnow(),
        "exp": expire,
    }
    return jwt.encode(payload, config.SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user: Any, expires_days: Optional[int] = None) -> str:
    """Create a signed JWT refresh token."""
    config = get_config()
    expire = datetime.utcnow() + timedelta(days=expires_days or config.JWT_REFRESH_EXPIRATION)
    payload = {
        **_base_token_payload(user),
        "type": "refresh",
        "iat": datetime.utcnow(),
        "exp": expire,
    }
    return jwt.encode(payload, config.SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT token."""
    config = get_config()
    try:
        return jwt.decode(token, config.SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise AuthError("Token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise AuthError("Invalid token") from exc


def hash_token(token: str) -> str:
    """Create a stable hash for storing refresh tokens."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_token_urlsafe(length: int = 48) -> str:
    """Generate a random URL-safe token."""
    return secrets.token_urlsafe(length)
