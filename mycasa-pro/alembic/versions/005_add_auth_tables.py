"""add auth tables

Revision ID: 005
Revises: 004
Create Date: 2026-02-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table_name: str) -> bool:
    inspector = inspect(op.get_bind())
    return table_name in inspector.get_table_names()


def _index_exists(table_name: str, index_name: str) -> bool:
    inspector = inspect(op.get_bind())
    return index_name in {idx["name"] for idx in inspector.get_indexes(table_name)}


def upgrade() -> None:
    if not _table_exists("users"):
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tenant_id", sa.String(36), nullable=False),
            sa.Column("username", sa.String(), nullable=False),
            sa.Column("email", sa.String(), nullable=False),
            sa.Column("hashed_password", sa.String(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.UniqueConstraint("username", name="uq_users_username"),
            sa.UniqueConstraint("email", name="uq_users_email"),
        )
        op.create_index("ix_users_username", "users", ["username"])
        op.create_index("ix_users_email", "users", ["email"])
        op.create_index("ix_users_tenant_id", "users", ["tenant_id"])
    else:
        if not _index_exists("users", "ix_users_username"):
            op.create_index("ix_users_username", "users", ["username"])
        if not _index_exists("users", "ix_users_email"):
            op.create_index("ix_users_email", "users", ["email"])
        if not _index_exists("users", "ix_users_tenant_id"):
            op.create_index("ix_users_tenant_id", "users", ["tenant_id"])

    if not _table_exists("session_tokens"):
        op.create_table(
            "session_tokens",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("token_hash", sa.String(), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("last_used_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.UniqueConstraint("token_hash", name="uq_session_tokens_token_hash"),
        )
        op.create_index("ix_session_tokens_user_id", "session_tokens", ["user_id"])
        op.create_index("ix_session_tokens_expires_at", "session_tokens", ["expires_at"])
        op.create_index("ix_session_tokens_token_hash", "session_tokens", ["token_hash"])
    else:
        if not _index_exists("session_tokens", "ix_session_tokens_user_id"):
            op.create_index("ix_session_tokens_user_id", "session_tokens", ["user_id"])
        if not _index_exists("session_tokens", "ix_session_tokens_expires_at"):
            op.create_index("ix_session_tokens_expires_at", "session_tokens", ["expires_at"])
        if not _index_exists("session_tokens", "ix_session_tokens_token_hash"):
            op.create_index("ix_session_tokens_token_hash", "session_tokens", ["token_hash"])


def downgrade() -> None:
    if _table_exists("session_tokens"):
        if _index_exists("session_tokens", "ix_session_tokens_token_hash"):
            op.drop_index("ix_session_tokens_token_hash", table_name="session_tokens")
        if _index_exists("session_tokens", "ix_session_tokens_expires_at"):
            op.drop_index("ix_session_tokens_expires_at", table_name="session_tokens")
        if _index_exists("session_tokens", "ix_session_tokens_user_id"):
            op.drop_index("ix_session_tokens_user_id", table_name="session_tokens")
        op.drop_table("session_tokens")

    if _table_exists("users"):
        if _index_exists("users", "ix_users_tenant_id"):
            op.drop_index("ix_users_tenant_id", table_name="users")
        if _index_exists("users", "ix_users_email"):
            op.drop_index("ix_users_email", table_name="users")
        if _index_exists("users", "ix_users_username"):
            op.drop_index("ix_users_username", table_name="users")
        op.drop_table("users")
