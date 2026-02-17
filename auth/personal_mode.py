"""
Personal (no-login) mode support.
Creates and returns a single local user record for local-first use.
"""
from __future__ import annotations

from datetime import datetime
import os
import secrets
from typing import Optional

from sqlalchemy.orm import Session

from auth.security import get_password_hash
from config.settings import DEFAULT_TENANT_ID
from database.models import User, UserCredential, Org, OrgMembership, Role, UserRole


PERSONAL_USERNAME = os.getenv("MYCASA_PERSONAL_USERNAME", "local")
PERSONAL_EMAIL = os.getenv("MYCASA_PERSONAL_EMAIL", "local@mycasa.local")


def _ensure_default_org(db: Session) -> Org:
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
        if credential.password_hash != password_hash:
            credential.password_hash = password_hash
            credential.last_changed_at = datetime.utcnow()
            credential.requires_reset = False
        db.add(credential)
        db.commit()
        return
    db.add(UserCredential(user_id=user.id, password_hash=password_hash))
    db.commit()


def ensure_personal_user(db: Session, display_name: Optional[str] = None) -> User:
    """
    Ensure a local personal-mode user exists and return it.
    """
    username_norm = PERSONAL_USERNAME.strip().lower()
    email_norm = PERSONAL_EMAIL.strip().lower()
    user = (
        db.query(User)
        .filter((User.username_normalized == username_norm) | (User.email_normalized == email_norm))
        .first()
    )

    org = _ensure_default_org(db)

    if not user:
        password_hash = get_password_hash(secrets.token_urlsafe(32))
        user = User(
            username=PERSONAL_USERNAME,
            email=PERSONAL_EMAIL,
            hashed_password=password_hash,
            display_name=display_name.strip() if display_name else None,
            is_active=True,
            is_admin=True,
            status="active",
            tenant_id=DEFAULT_TENANT_ID,
            org_id=org.id,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        _ensure_credentials(db, user, password_hash)
    else:
        if display_name is not None:
            updated_name = display_name.strip() or None
            if user.display_name != updated_name:
                user.display_name = updated_name
                db.add(user)
                db.commit()

    if not user.org_id:
        user.org_id = org.id
        db.add(user)
        db.commit()

    _ensure_membership(db, user.org_id, user.id)
    _ensure_user_role(db, user.id, "SUPER_ADMIN", user.org_id)

    return user
