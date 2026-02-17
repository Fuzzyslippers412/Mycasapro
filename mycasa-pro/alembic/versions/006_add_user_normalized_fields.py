"""add normalized user fields

Revision ID: 006
Revises: 005
Create Date: 2026-02-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text


# revision identifiers, used by Alembic.
revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table_name: str) -> bool:
    inspector = inspect(op.get_bind())
    return table_name in inspector.get_table_names()


def _column_exists(table_name: str, column_name: str) -> bool:
    inspector = inspect(op.get_bind())
    return column_name in {col["name"] for col in inspector.get_columns(table_name)}


def _index_exists(table_name: str, index_name: str) -> bool:
    inspector = inspect(op.get_bind())
    return index_name in {idx["name"] for idx in inspector.get_indexes(table_name)}


def upgrade() -> None:
    if not _table_exists("users"):
        return

    with op.batch_alter_table("users", schema=None) as batch_op:
        if not _column_exists("users", "username_normalized"):
            batch_op.add_column(sa.Column("username_normalized", sa.String(), nullable=True))
        if not _column_exists("users", "email_normalized"):
            batch_op.add_column(sa.Column("email_normalized", sa.String(), nullable=True))

    op.execute(text("UPDATE users SET username_normalized = lower(username) WHERE username_normalized IS NULL"))
    op.execute(text("UPDATE users SET email_normalized = lower(email) WHERE email_normalized IS NULL"))

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.alter_column("username_normalized", nullable=False)
        batch_op.alter_column("email_normalized", nullable=False)

    if not _index_exists("users", "ix_users_username_normalized"):
        op.create_index("ix_users_username_normalized", "users", ["username_normalized"], unique=True)
    if not _index_exists("users", "ix_users_email_normalized"):
        op.create_index("ix_users_email_normalized", "users", ["email_normalized"], unique=True)


def downgrade() -> None:
    if not _table_exists("users"):
        return

    if _index_exists("users", "ix_users_username_normalized"):
        op.drop_index("ix_users_username_normalized", table_name="users")
    if _index_exists("users", "ix_users_email_normalized"):
        op.drop_index("ix_users_email_normalized", table_name="users")

    with op.batch_alter_table("users", schema=None) as batch_op:
        if _column_exists("users", "username_normalized"):
            batch_op.drop_column("username_normalized")
        if _column_exists("users", "email_normalized"):
            batch_op.drop_column("email_normalized")
