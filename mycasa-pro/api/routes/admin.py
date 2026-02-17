from __future__ import annotations

from datetime import datetime, timedelta
import hashlib
import re
import time
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session
from sqlalchemy.sql import text as sql_text

from auth.dependencies import require_permission
from auth.permissions import get_user_permissions
from auth.schemas import (
    AdminCreateUserRequest,
    AdminUpdateUserRequest,
    AdminUserResponse,
    AdminRoleRequest,
    AdminRolePermissionsRequest,
    AdminDBQueryRequest,
)
from auth.security import get_password_hash, generate_token_urlsafe, hash_token
from auth.audit import log_audit
from auth.settings import ADMIN_DB_WRITE_ENABLED, PASSWORD_RESET_TOKEN_TTL_MINUTES
from database.connection import get_db
from database import engine
from database.models import (
    User,
    Role,
    Permission,
    RolePermission,
    UserRole,
    Org,
    OrgMembership,
    PasswordResetToken,
    AuditLog,
)

router = APIRouter(prefix="/admin", tags=["Admin"])

MAX_DB_ROWS = 200
FORBIDDEN_SQL = {"drop", "alter", "create", "pragma", "vacuum", "attach", "detach", "copy", "pg_sleep"}
WRITE_SQL = {"insert", "update", "delete"}
WRITE_ALLOWLIST = {"feature_flags", "roles", "permissions", "role_permissions", "user_roles", "orgs", "org_memberships"}


def _default_org(db: Session) -> Org:
    org = db.query(Org).filter(Org.is_default == True).first()  # noqa: E712
    if not org:
        org = Org(name="Default Household", slug="default", is_default=True)
        db.add(org)
        db.commit()
        db.refresh(org)
    return org


def _role_by_name(db: Session, name: str) -> Role:
    role = db.query(Role).filter(Role.name == name).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return role


def _user_roles_map(db: Session, user_ids: list[int]) -> dict[int, list[str]]:
    if not user_ids:
        return {}
    rows = (
        db.query(UserRole.user_id, Role.name)
        .join(Role, Role.id == UserRole.role_id)
        .filter(UserRole.user_id.in_(user_ids))
        .all()
    )
    roles_map: dict[int, list[str]] = {}
    for user_id, role_name in rows:
        roles_map.setdefault(user_id, []).append(role_name)
    return roles_map


@router.get("/users")
async def list_users(
    query: str | None = None,
    role: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("admin.user.read")),
):
    page = max(1, page)
    page_size = min(max(1, page_size), 200)
    q = db.query(User)
    if query:
        q = q.filter(or_(User.username.ilike(f"%{query}%"), User.email.ilike(f"%{query}%")))
    if status:
        q = q.filter(User.status == status)
    if role:
        q = q.join(UserRole, UserRole.user_id == User.id).join(Role, Role.id == UserRole.role_id).filter(Role.name == role)

    total = q.count()
    users = q.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    roles_map = _user_roles_map(db, [u.id for u in users])
    return {
        "total": total,
        "users": [
            AdminUserResponse(
                id=u.id,
                username=u.username,
                email=u.email,
                is_admin=u.is_admin,
                display_name=getattr(u, "display_name", None),
                status=getattr(u, "status", None),
                org_id=getattr(u, "org_id", None),
                tenant_id=getattr(u, "tenant_id", None),
                avatar_url="/api/auth/avatar" if getattr(u, "avatar_path", None) else None,
                roles=roles_map.get(u.id, []),
            ).dict()
            for u in users
        ],
    }


@router.post("/users")
async def create_user(
    payload: AdminCreateUserRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(require_permission("admin.user.write")),
):
    if db.query(User).filter(or_(User.username_normalized == payload.username.lower(), User.email_normalized == payload.email.lower())).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username or email already exists")

    org = db.query(Org).filter(Org.id == payload.org_id).first() if payload.org_id else _default_org(db)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Org not found")

    password = payload.password or generate_token_urlsafe(18)
    user = User(
        username=payload.username.strip(),
        username_normalized=payload.username.strip().lower(),
        email=payload.email.strip().lower(),
        email_normalized=payload.email.strip().lower(),
        hashed_password=get_password_hash(password),
        is_admin=(payload.role == "SUPER_ADMIN"),
        is_active=(payload.status != "disabled"),
        status=payload.status or "active",
        org_id=org.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    db.add(OrgMembership(org_id=org.id, user_id=user.id, status="active", joined_at=datetime.utcnow()))
    role_name = payload.role or "MEMBER"
    role = _role_by_name(db, role_name)
    db.add(UserRole(user_id=user.id, role_id=role.id, org_id=org.id))
    db.commit()

    reset_token = None
    if payload.send_invite or payload.password is None:
        raw_token = generate_token_urlsafe()
        token_hash = hash_token(raw_token)
        expires_at = datetime.utcnow() + timedelta(minutes=PASSWORD_RESET_TOKEN_TTL_MINUTES)
        db.add(PasswordResetToken(user_id=user.id, token_hash=token_hash, expires_at=expires_at))
        db.commit()
        reset_token = raw_token

    log_audit(db, action="admin.user.create", actor_user_id=user["id"], target_type="user", target_id=str(user.id), org_id=org.id)
    return {"user_id": user.id, "reset_token": reset_token}


@router.patch("/users/{user_id}")
async def update_user(
    user_id: int,
    payload: AdminUpdateUserRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(require_permission("admin.user.write")),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if payload.status is not None:
        user.status = payload.status
        user.is_active = payload.status != "disabled"

    if payload.org_id:
        org = db.query(Org).filter(Org.id == payload.org_id).first()
        if not org:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Org not found")
        user.org_id = org.id
        existing_membership = (
            db.query(OrgMembership)
            .filter(OrgMembership.org_id == org.id, OrgMembership.user_id == user.id)
            .first()
        )
        if not existing_membership:
            db.add(OrgMembership(org_id=org.id, user_id=user.id, status="active", joined_at=datetime.utcnow()))

    if payload.role:
        role = _role_by_name(db, payload.role)
        db.query(UserRole).filter(UserRole.user_id == user.id, UserRole.org_id == user.org_id).delete()
        db.add(UserRole(user_id=user.id, role_id=role.id, org_id=user.org_id))
        user.is_admin = payload.role == "SUPER_ADMIN"

    db.add(user)
    db.commit()
    log_audit(db, action="admin.user.update", actor_user_id=user["id"], target_type="user", target_id=str(user.id), org_id=user.org_id)
    return {"success": True}


@router.post("/users/{user_id}/reset-password")
async def admin_reset_password(
    user_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(require_permission("admin.user.write")),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    raw_token = generate_token_urlsafe()
    token_hash = hash_token(raw_token)
    expires_at = datetime.utcnow() + timedelta(minutes=PASSWORD_RESET_TOKEN_TTL_MINUTES)
    db.add(PasswordResetToken(user_id=user.id, token_hash=token_hash, expires_at=expires_at))
    db.commit()
    log_audit(db, action="admin.user.reset_password", actor_user_id=user["id"], target_type="user", target_id=str(user.id), org_id=user.org_id)
    return {"reset_token": raw_token}


@router.get("/audit-log")
async def list_audit_log(
    limit: int = 100,
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("admin.audit.read")),
):
    rows = (
        db.query(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .limit(min(max(limit, 1), 500))
        .all()
    )
    return {
        "events": [
            {
                "id": row.id,
                "action": row.action,
                "actor_user_id": row.actor_user_id,
                "target_type": row.target_type,
                "target_id": row.target_id,
                "org_id": row.org_id,
                "metadata": row.metadata_json,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    }


@router.get("/roles")
async def list_roles(
    db: Session = Depends(get_db),
    _: dict = Depends(require_permission("admin.role.read")),
):
    roles = db.query(Role).order_by(Role.name.asc()).all()
    role_ids = [r.id for r in roles]
    permissions = (
        db.query(RolePermission.role_id, Permission.key)
        .join(Permission, Permission.id == RolePermission.permission_id)
        .filter(RolePermission.role_id.in_(role_ids))
        .all()
    )
    perm_map: dict[int, list[str]] = {}
    for role_id, key in permissions:
        perm_map.setdefault(role_id, []).append(key)
    return {
        "roles": [
            {
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "scope": r.scope,
                "permissions": perm_map.get(r.id, []),
            }
            for r in roles
        ]
    }


@router.post("/roles")
async def create_role(
    payload: AdminRoleRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(require_permission("admin.role.write")),
):
    if db.query(Role).filter(Role.name == payload.name).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Role already exists")
    role = Role(name=payload.name, description=payload.description, scope=payload.scope, is_system=False)
    db.add(role)
    db.commit()
    log_audit(db, action="admin.role.create", actor_user_id=user["id"], target_type="role", target_id=str(role.id))
    return {"id": role.id}


@router.patch("/roles/{role_id}")
async def update_role(
    role_id: int,
    payload: AdminRoleRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(require_permission("admin.role.write")),
):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    role.name = payload.name
    role.description = payload.description
    role.scope = payload.scope
    db.add(role)
    db.commit()
    log_audit(db, action="admin.role.update", actor_user_id=user["id"], target_type="role", target_id=str(role.id))
    return {"success": True}


@router.post("/roles/{role_id}/permissions")
async def set_role_permissions(
    role_id: int,
    payload: AdminRolePermissionsRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(require_permission("admin.role.write")),
):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    db.query(RolePermission).filter(RolePermission.role_id == role.id).delete()
    for key in payload.permissions:
        perm = db.query(Permission).filter(Permission.key == key).first()
        if perm:
            db.add(RolePermission(role_id=role.id, permission_id=perm.id))
    db.commit()
    log_audit(db, action="admin.role.permissions", actor_user_id=user["id"], target_type="role", target_id=str(role.id))
    return {"success": True}


def _sanitize_sql(sql: str) -> str:
    stripped = sql.strip()
    if ";" in stripped[:-1]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Multiple statements not allowed")
    stripped = stripped.strip(";")
    return re.sub(r"\s+", " ", stripped)


def _contains_forbidden(sql_lower: str) -> bool:
    return any(keyword in sql_lower for keyword in FORBIDDEN_SQL)


def _is_select(sql_lower: str) -> bool:
    return sql_lower.startswith("select") or sql_lower.startswith("with")


def _extract_tables(sql_lower: str) -> set[str]:
    tokens = re.split(r"\s+", sql_lower)
    tables = set()
    for idx, token in enumerate(tokens):
        if token in {"from", "into", "update"} and idx + 1 < len(tokens):
            table = re.sub(r"[;,]", "", tokens[idx + 1])
            tables.add(table)
    return tables


@router.post("/db/query")
async def db_query(
    payload: AdminDBQueryRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(require_permission("admin.db.read")),
):
    sql = _sanitize_sql(payload.sql)
    sql_lower = sql.lower()
    if _contains_forbidden(sql_lower):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Forbidden SQL")

    if payload.danger_mode:
        if not ADMIN_DB_WRITE_ENABLED:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Danger mode disabled")
        if not user.get("is_admin"):
            perms = get_user_permissions(db, user_id=user["id"], org_id=user.get("org_id"))
            if "admin.db.write" not in perms:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Write access required")
    else:
        if not _is_select(sql_lower):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Read-only console")

    tables = _extract_tables(sql_lower)
    if payload.danger_mode:
        if any(table not in WRITE_ALLOWLIST for table in tables):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Table not allowlisted")
        if not any(word in sql_lower for word in WRITE_SQL):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Write statement required")

    if _is_select(sql_lower) and "limit" not in sql_lower:
        sql = f"{sql} LIMIT {MAX_DB_ROWS}"

    sql_hash = hashlib.sha256(sql.encode("utf-8")).hexdigest()
    started = time.monotonic()
    if engine.dialect.name == "postgresql":
        db.execute(sql_text("SET LOCAL statement_timeout = :timeout"), {"timeout": "3000"})
    try:
        result = db.execute(sql_text(sql))
        rows = []
        columns: list[str] = []
        if result.returns_rows:
            columns = list(result.keys())
            rows = [dict(zip(columns, row)) for row in result.fetchmany(MAX_DB_ROWS)]
        else:
            db.commit()
    except Exception:
        db.rollback()
        log_audit(
            db,
            action="admin.db.query.error",
            actor_user_id=user["id"],
            target_type="db",
            target_id=sql_hash,
            org_id=user.get("org_id"),
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Query failed")
    duration_ms = int((time.monotonic() - started) * 1000)

    log_audit(
        db,
        action="admin.db.query",
        actor_user_id=user["id"],
        target_type="db",
        target_id=sql_hash,
        org_id=user.get("org_id"),
        metadata={"rows": len(rows), "duration_ms": duration_ms, "danger_mode": payload.danger_mode},
    )

    return {"columns": columns, "rows": rows, "duration_ms": duration_ms}
