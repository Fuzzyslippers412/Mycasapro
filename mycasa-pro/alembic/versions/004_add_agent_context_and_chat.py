"""add agent context budgets and chat persistence

Revision ID: 004
Revises: 003
Create Date: 2026-02-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Agent profiles
    op.create_table(
        "agent_profiles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("context_window_tokens", sa.Integer(), nullable=False),
        sa.Column("reserved_output_tokens", sa.Integer(), nullable=False, server_default="2048"),
        sa.Column("budgets_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_agent_profiles_name", "agent_profiles", ["name"])

    # LLM runs
    op.create_table(
        "llm_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("agent_id", sa.String(36), sa.ForeignKey("agent_profiles.id"), nullable=False),
        sa.Column("request_id", sa.String(64)),
        sa.Column("started_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime()),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("input_tokens_measured", sa.Integer()),
        sa.Column("output_tokens_measured", sa.Integer()),
        sa.Column("input_tokens_estimated", sa.Integer(), nullable=False),
        sa.Column("output_tokens_estimated", sa.Integer(), nullable=False),
        sa.Column("component_tokens_json", sa.JSON(), nullable=False),
        sa.Column("included_summary_json", sa.JSON(), nullable=False),
        sa.Column("trimming_applied_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("error_json", sa.JSON()),
    )
    op.create_index("ix_llm_runs_agent_id", "llm_runs", ["agent_id"])
    op.create_index("ix_llm_runs_request_id", "llm_runs", ["request_id"])
    op.create_index("ix_llm_runs_started_at", "llm_runs", ["started_at"])

    # Agent context snapshots
    op.create_table(
        "agent_context_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("agent_id", sa.String(36), sa.ForeignKey("agent_profiles.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("snapshot_json", sa.JSON()),
    )
    op.create_index("ix_agent_context_snapshots_agent_id", "agent_context_snapshots", ["agent_id"])
    op.create_index("ix_agent_context_snapshots_created_at", "agent_context_snapshots", ["created_at"])

    # Chat persistence
    op.create_table(
        "chat_conversations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("agent_name", sa.String(100), nullable=False),
        sa.Column("title", sa.String(200)),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_chat_conversations_user_id", "chat_conversations", ["user_id"])
    op.create_index("ix_chat_conversations_agent_name", "chat_conversations", ["agent_name"])

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("conversation_id", sa.String(36), sa.ForeignKey("chat_conversations.id"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_chat_messages_conversation_id", "chat_messages", ["conversation_id"])
    op.create_index("ix_chat_messages_created_at", "chat_messages", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_chat_messages_created_at")
    op.drop_index("ix_chat_messages_conversation_id")
    op.drop_table("chat_messages")

    op.drop_index("ix_chat_conversations_agent_name")
    op.drop_index("ix_chat_conversations_user_id")
    op.drop_table("chat_conversations")

    op.drop_index("ix_agent_context_snapshots_created_at")
    op.drop_index("ix_agent_context_snapshots_agent_id")
    op.drop_table("agent_context_snapshots")

    op.drop_index("ix_llm_runs_started_at")
    op.drop_index("ix_llm_runs_request_id")
    op.drop_index("ix_llm_runs_agent_id")
    op.drop_table("llm_runs")

    op.drop_index("ix_agent_profiles_name")
    op.drop_table("agent_profiles")
