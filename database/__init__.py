"""
MyCasa Pro Database Layer
"""
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import DATABASE_URL, DATA_DIR, DEFAULT_TENANT_ID
from database.models import Base

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)

# Create engine
engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False, "timeout": 30},
)

# Create session factory

# Configure SQLite for concurrency
try:
    from sqlalchemy import text as _sql_text
    with engine.connect() as conn:
        conn.execute(_sql_text("PRAGMA journal_mode=WAL;"))
        conn.execute(_sql_text("PRAGMA synchronous=NORMAL;"))
        conn.execute(_sql_text("PRAGMA busy_timeout=5000;"))
except Exception:
    pass

SessionLocal = sessionmaker(bind=engine)


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)


def _column_names(table: str) -> set[str]:
    inspector = inspect(engine)
    try:
        return {col["name"] for col in inspector.get_columns(table)}
    except Exception:
        return set()


def ensure_schema():
    """Apply minimal, idempotent schema fixes for existing databases."""
    from sqlalchemy import text

    users_columns = _column_names("users")
    if users_columns:
        with engine.begin() as conn:
            if "tenant_id" not in users_columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN tenant_id VARCHAR(36)"))
                conn.execute(
                    text("UPDATE users SET tenant_id = :tenant_id WHERE tenant_id IS NULL"),
                    {"tenant_id": DEFAULT_TENANT_ID},
                )
            if "org_id" not in users_columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN org_id VARCHAR(36)"))
            if "username_normalized" not in users_columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN username_normalized VARCHAR"))
                conn.execute(text("UPDATE users SET username_normalized = lower(username) WHERE username_normalized IS NULL"))
            if "email_normalized" not in users_columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN email_normalized VARCHAR"))
                conn.execute(text("UPDATE users SET email_normalized = lower(email) WHERE email_normalized IS NULL"))
            if "avatar_path" not in users_columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN avatar_path VARCHAR"))
            if "display_name" not in users_columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN display_name VARCHAR(120)"))
            if "status" not in users_columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN status VARCHAR(20)"))
                conn.execute(text("UPDATE users SET status = 'active' WHERE status IS NULL"))
            if "lockout_until" not in users_columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN lockout_until DATETIME"))
            if "deleted_at" not in users_columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN deleted_at DATETIME"))

    event_columns = _column_names("event_log")
    if event_columns and "user_id" not in event_columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE event_log ADD COLUMN user_id INTEGER"))

    session_columns = _column_names("session_tokens")
    if session_columns:
        with engine.begin() as conn:
            if "token_type" not in session_columns:
                conn.execute(text("ALTER TABLE session_tokens ADD COLUMN token_type VARCHAR(20)"))
                conn.execute(text("UPDATE session_tokens SET token_type = 'refresh' WHERE token_type IS NULL"))
            if "session_id" not in session_columns:
                conn.execute(text("ALTER TABLE session_tokens ADD COLUMN session_id VARCHAR(36)"))
            if "revoked_at" not in session_columns:
                conn.execute(text("ALTER TABLE session_tokens ADD COLUMN revoked_at DATETIME"))
            if "ip_address" not in session_columns:
                conn.execute(text("ALTER TABLE session_tokens ADD COLUMN ip_address VARCHAR(64)"))
            if "user_agent" not in session_columns:
                conn.execute(text("ALTER TABLE session_tokens ADD COLUMN user_agent VARCHAR(255)"))
            if "rotation_parent_id" not in session_columns:
                conn.execute(text("ALTER TABLE session_tokens ADD COLUMN rotation_parent_id INTEGER"))

    maintenance_columns = _column_names("maintenance_tasks")
    if maintenance_columns:
        with engine.begin() as conn:
            if "conversation_id" not in maintenance_columns:
                conn.execute(text("ALTER TABLE maintenance_tasks ADD COLUMN conversation_id VARCHAR(36)"))
            if "assigned_to" not in maintenance_columns:
                conn.execute(text("ALTER TABLE maintenance_tasks ADD COLUMN assigned_to VARCHAR(64)"))

    conversation_columns = _column_names("chat_conversations")
    if conversation_columns:
        with engine.begin() as conn:
            if "archived_at" not in conversation_columns:
                conn.execute(text("ALTER TABLE chat_conversations ADD COLUMN archived_at DATETIME"))


def seed_user_management():
    """Seed default org, roles, permissions, and backfill user roles."""
    from datetime import datetime
    from database.models import (
        Org,
        OrgMembership,
        Role,
        Permission,
        RolePermission,
        UserRole,
        UserCredential,
        User,
    )

    with get_db() as db:
        default_org = db.query(Org).filter(Org.is_default == True).first()
        if not default_org:
            default_org = Org(name="Default Household", slug=DEFAULT_TENANT_ID, is_default=True)
            db.add(default_org)
            db.commit()
            db.refresh(default_org)

        permissions = {
            "admin.user.read": "Read users",
            "admin.user.write": "Manage users",
            "admin.role.read": "Read roles",
            "admin.role.write": "Manage roles",
            "admin.audit.read": "Read audit log",
            "admin.db.read": "Read database console",
            "admin.db.write": "Write database console",
        }

        existing_permissions = {p.key: p for p in db.query(Permission).all()}
        for key, desc in permissions.items():
            if key not in existing_permissions:
                db.add(Permission(key=key, description=desc))
        db.commit()

        roles = {
            "SUPER_ADMIN": set(permissions.keys()),
            "ORG_ADMIN": {"admin.user.read", "admin.user.write", "admin.role.read", "admin.audit.read"},
            "SUPPORT_READONLY": {"admin.user.read", "admin.audit.read", "admin.db.read"},
            "MEMBER": set(),
        }

        existing_roles = {r.name: r for r in db.query(Role).all()}
        for name, role_perms in roles.items():
            role = existing_roles.get(name)
            if not role:
                role = Role(name=name, description=name.replace("_", " ").title(), scope="global", is_system=True)
                db.add(role)
                db.commit()
                db.refresh(role)
                existing_roles[name] = role

            current_perm_keys = {
                p.permission.key
                for p in db.query(RolePermission)
                .join(Permission, RolePermission.permission_id == Permission.id)
                .filter(RolePermission.role_id == role.id)
                .all()
            }
            for perm_key in role_perms - current_perm_keys:
                perm = db.query(Permission).filter(Permission.key == perm_key).first()
                if perm:
                    db.add(RolePermission(role_id=role.id, permission_id=perm.id))
        db.commit()

        users = db.query(User).all()
        for user in users:
            if not user.org_id:
                user.org_id = default_org.id
            if not user.status:
                user.status = "active" if user.is_active else "disabled"
            membership = (
                db.query(OrgMembership)
                .filter(OrgMembership.org_id == user.org_id, OrgMembership.user_id == user.id)
                .first()
            )
            if not membership:
                db.add(
                    OrgMembership(
                        org_id=user.org_id,
                        user_id=user.id,
                        status="active",
                        joined_at=user.created_at or datetime.utcnow(),
                    )
                )

            if user.hashed_password:
                credential = db.query(UserCredential).filter(UserCredential.user_id == user.id).first()
                if not credential:
                    db.add(UserCredential(user_id=user.id, password_hash=user.hashed_password))

            role_name = "SUPER_ADMIN" if user.is_admin else "MEMBER"
            role = existing_roles.get(role_name)
            if role:
                existing_user_role = (
                    db.query(UserRole)
                    .filter(
                        UserRole.user_id == user.id,
                        UserRole.role_id == role.id,
                        UserRole.org_id == user.org_id,
                    )
                    .first()
                )
                if not existing_user_role:
                    db.add(UserRole(user_id=user.id, role_id=role.id, org_id=user.org_id))

        db.commit()


@contextmanager
def get_db() -> Session:
    """Context manager for database sessions"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_session() -> Session:
    """Get a database session (remember to close it)"""
    return SessionLocal()


# Initialize on import
init_db()
ensure_schema()
seed_user_management()
