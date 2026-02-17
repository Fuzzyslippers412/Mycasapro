"""
RBAC helpers for permissions.
"""
from __future__ import annotations

from typing import Iterable, Set

from sqlalchemy.orm import Session

from database.models import Permission, RolePermission, UserRole


def get_user_permissions(db: Session, user_id: int, org_id: str | None = None) -> Set[str]:
    query = (
        db.query(Permission.key)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(UserRole, UserRole.role_id == RolePermission.role_id)
        .filter(UserRole.user_id == user_id)
    )
    if org_id is not None:
        query = query.filter((UserRole.org_id == org_id) | (UserRole.org_id.is_(None)))
    return {row[0] for row in query.all()}


def has_permissions(user_permissions: Iterable[str], required: Iterable[str]) -> bool:
    user_set = set(user_permissions)
    return all(permission in user_set for permission in required)
