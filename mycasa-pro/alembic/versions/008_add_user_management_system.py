"""add user management system

Revision ID: 008
Revises: 007
Create Date: 2026-02-15
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table_name: str) -> bool:
    inspector = inspect(op.get_bind())
    return table_name in inspector.get_table_names()


def _index_exists(table_name: str, index_name: str) -> bool:
    inspector = inspect(op.get_bind())
    return index_name in {idx["name"] for idx in inspector.get_indexes(table_name)}


def _column_exists(table_name: str, column_name: str) -> bool:
    inspector = inspect(op.get_bind())
    return column_name in {col["name"] for col in inspector.get_columns(table_name)}


def upgrade() -> None:
    # ---- Users table extensions ----
    if _table_exists("users"):
        if not _column_exists("users", "org_id"):
            op.add_column("users", sa.Column("org_id", sa.String(36), nullable=True))
        if not _column_exists("users", "display_name"):
            op.add_column("users", sa.Column("display_name", sa.String(120), nullable=True))
        if not _column_exists("users", "status"):
            op.add_column("users", sa.Column("status", sa.String(20), nullable=True))
        if not _column_exists("users", "lockout_until"):
            op.add_column("users", sa.Column("lockout_until", sa.DateTime(), nullable=True))
        if not _column_exists("users", "deleted_at"):
            op.add_column("users", sa.Column("deleted_at", sa.DateTime(), nullable=True))
        if not _index_exists("users", "ix_users_org_id"):
            op.create_index("ix_users_org_id", "users", ["org_id"])

    # ---- Session tokens extensions ----
    if _table_exists("session_tokens"):
        if not _column_exists("session_tokens", "token_type"):
            op.add_column("session_tokens", sa.Column("token_type", sa.String(20), nullable=True))
        if not _column_exists("session_tokens", "session_id"):
            op.add_column("session_tokens", sa.Column("session_id", sa.String(36), nullable=True))
        if not _column_exists("session_tokens", "revoked_at"):
            op.add_column("session_tokens", sa.Column("revoked_at", sa.DateTime(), nullable=True))
        if not _column_exists("session_tokens", "ip_address"):
            op.add_column("session_tokens", sa.Column("ip_address", sa.String(64), nullable=True))
        if not _column_exists("session_tokens", "user_agent"):
            op.add_column("session_tokens", sa.Column("user_agent", sa.String(255), nullable=True))
        if not _column_exists("session_tokens", "rotation_parent_id"):
            op.add_column("session_tokens", sa.Column("rotation_parent_id", sa.Integer(), nullable=True))
        if not _index_exists("session_tokens", "ix_session_tokens_token_type"):
            op.create_index("ix_session_tokens_token_type", "session_tokens", ["token_type"])
        if not _index_exists("session_tokens", "ix_session_tokens_session_id"):
            op.create_index("ix_session_tokens_session_id", "session_tokens", ["session_id"])

    # ---- Orgs ----
    if not _table_exists("orgs"):
        op.create_table(
            "orgs",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("name", sa.String(150), nullable=False),
            sa.Column("slug", sa.String(80), nullable=False),
            sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("slug", name="uq_orgs_slug"),
        )
        op.create_index("ix_orgs_slug", "orgs", ["slug"])

    if not _table_exists("org_memberships"):
        op.create_table(
            "org_memberships",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("org_id", sa.String(36), sa.ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'active'")),
            sa.Column("invited_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("joined_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.UniqueConstraint("org_id", "user_id", name="uq_org_memberships_org_user"),
        )
        op.create_index("ix_org_memberships_org_id", "org_memberships", ["org_id"])
        op.create_index("ix_org_memberships_user_id", "org_memberships", ["user_id"])

    # ---- Roles + Permissions ----
    if not _table_exists("roles"):
        op.create_table(
            "roles",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(50), nullable=False),
            sa.Column("description", sa.String(255), nullable=True),
            sa.Column("scope", sa.String(20), nullable=False, server_default=sa.text("'global'")),
            sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.UniqueConstraint("name", name="uq_roles_name"),
        )
        op.create_index("ix_roles_name", "roles", ["name"])

    if not _table_exists("permissions"):
        op.create_table(
            "permissions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("key", sa.String(100), nullable=False),
            sa.Column("description", sa.String(255), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.UniqueConstraint("key", name="uq_permissions_key"),
        )
        op.create_index("ix_permissions_key", "permissions", ["key"])

    if not _table_exists("role_permissions"):
        op.create_table(
            "role_permissions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False),
            sa.Column("permission_id", sa.Integer(), sa.ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False),
            sa.UniqueConstraint("role_id", "permission_id", name="uq_role_permissions_role_permission"),
        )
        op.create_index("ix_role_permissions_role_id", "role_permissions", ["role_id"])
        op.create_index("ix_role_permissions_permission_id", "role_permissions", ["permission_id"])

    if not _table_exists("user_roles"):
        op.create_table(
            "user_roles",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False),
            sa.Column("org_id", sa.String(36), sa.ForeignKey("orgs.id", ondelete="CASCADE"), nullable=True),
            sa.Column("assigned_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("assigned_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.UniqueConstraint("user_id", "role_id", "org_id", name="uq_user_roles_user_role_org"),
        )
        op.create_index("ix_user_roles_user_id", "user_roles", ["user_id"])
        op.create_index("ix_user_roles_role_id", "user_roles", ["role_id"])
        op.create_index("ix_user_roles_org_id", "user_roles", ["org_id"])

    # ---- Credentials + identities ----
    if not _table_exists("user_credentials"):
        op.create_table(
            "user_credentials",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("password_hash", sa.String(), nullable=False),
            sa.Column("last_changed_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("requires_reset", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.UniqueConstraint("user_id", name="uq_user_credentials_user_id"),
        )
        op.create_index("ix_user_credentials_user_id", "user_credentials", ["user_id"])

    if not _table_exists("auth_identities"):
        op.create_table(
            "auth_identities",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("provider", sa.String(50), nullable=False),
            sa.Column("provider_user_id", sa.String(100), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.UniqueConstraint("provider", "provider_user_id", name="uq_auth_identities_provider_user"),
        )
        op.create_index("ix_auth_identities_user_id", "auth_identities", ["user_id"])

    # ---- Login attempts + audit ----
    if not _table_exists("login_attempts"):
        op.create_table(
            "login_attempts",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("identifier", sa.String(255), nullable=False),
            sa.Column("ip_address", sa.String(64), nullable=True),
            sa.Column("user_agent", sa.String(255), nullable=True),
            sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("failure_reason", sa.String(255), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )
        op.create_index("ix_login_attempts_user_id", "login_attempts", ["user_id"])
        op.create_index("ix_login_attempts_identifier", "login_attempts", ["identifier"])
        op.create_index("ix_login_attempts_created_at", "login_attempts", ["created_at"])

    if not _table_exists("audit_log"):
        op.create_table(
            "audit_log",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("action", sa.String(100), nullable=False),
            sa.Column("target_type", sa.String(80), nullable=True),
            sa.Column("target_id", sa.String(80), nullable=True),
            sa.Column("org_id", sa.String(36), sa.ForeignKey("orgs.id"), nullable=True),
            sa.Column("ip_address", sa.String(64), nullable=True),
            sa.Column("user_agent", sa.String(255), nullable=True),
            sa.Column("metadata", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )
        op.create_index("ix_audit_log_actor_user_id", "audit_log", ["actor_user_id"])
        op.create_index("ix_audit_log_action", "audit_log", ["action"])
        op.create_index("ix_audit_log_created_at", "audit_log", ["created_at"])
        op.create_index("ix_audit_log_org_id", "audit_log", ["org_id"])

    # ---- Password reset ----
    if not _table_exists("password_reset_tokens"):
        op.create_table(
            "password_reset_tokens",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("token_hash", sa.String(), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("used_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.UniqueConstraint("token_hash", name="uq_password_reset_tokens_token_hash"),
        )
        op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])
        op.create_index("ix_password_reset_tokens_token_hash", "password_reset_tokens", ["token_hash"])

    # ---- API keys + feature flags ----
    if not _table_exists("api_keys"):
        op.create_table(
            "api_keys",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("org_id", sa.String(36), sa.ForeignKey("orgs.id", ondelete="SET NULL"), nullable=True),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("key_hash", sa.String(), nullable=False),
            sa.Column("prefix", sa.String(12), nullable=True),
            sa.Column("scopes_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("last_used_at", sa.DateTime(), nullable=True),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("key_hash", name="uq_api_keys_key_hash"),
        )
        op.create_index("ix_api_keys_user_id", "api_keys", ["user_id"])
        op.create_index("ix_api_keys_org_id", "api_keys", ["org_id"])
        op.create_index("ix_api_keys_prefix", "api_keys", ["prefix"])

    if not _table_exists("feature_flags"):
        op.create_table(
            "feature_flags",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("key", sa.String(120), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("rules_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.UniqueConstraint("key", name="uq_feature_flags_key"),
        )
        op.create_index("ix_feature_flags_key", "feature_flags", ["key"])


def downgrade() -> None:
    # Drop new tables (reverse order)
    for table in [
        "feature_flags",
        "api_keys",
        "password_reset_tokens",
        "audit_log",
        "login_attempts",
        "auth_identities",
        "user_credentials",
        "user_roles",
        "role_permissions",
        "permissions",
        "roles",
        "org_memberships",
        "orgs",
    ]:
        if _table_exists(table):
            op.drop_table(table)

    # Drop added columns
    if _table_exists("session_tokens"):
        for col in ["rotation_parent_id", "user_agent", "ip_address", "revoked_at", "session_id", "token_type"]:
            if _column_exists("session_tokens", col):
                op.drop_column("session_tokens", col)

    if _table_exists("users"):
        for col in ["deleted_at", "lockout_until", "status", "display_name", "org_id"]:
            if _column_exists("users", col):
                op.drop_column("users", col)
