"""add user avatar path

Revision ID: 007
Revises: 006
Create Date: 2026-02-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table_name: str) -> bool:
    inspector = inspect(op.get_bind())
    return table_name in inspector.get_table_names()


def _column_exists(table_name: str, column_name: str) -> bool:
    inspector = inspect(op.get_bind())
    return column_name in {col["name"] for col in inspector.get_columns(table_name)}


def upgrade() -> None:
    if not _table_exists("users"):
        return

    with op.batch_alter_table("users", schema=None) as batch_op:
        if not _column_exists("users", "avatar_path"):
            batch_op.add_column(sa.Column("avatar_path", sa.String(), nullable=True))


def downgrade() -> None:
    if not _table_exists("users"):
        return

    with op.batch_alter_table("users", schema=None) as batch_op:
        if _column_exists("users", "avatar_path"):
            batch_op.drop_column("avatar_path")
