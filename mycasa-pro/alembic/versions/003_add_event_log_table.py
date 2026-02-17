"""add event log table for event bus persistence

Revision ID: 003
Revises: 002
Create Date: 2026-01-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create event_log table for event bus persistence and at-least-once delivery"""
    
    op.create_table(
        'event_log',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('event_id', sa.String(36), nullable=False, unique=True),  # UUID
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('source', sa.String(50), nullable=False),
        sa.Column('tenant_id', sa.String(36), default='default'),
        sa.Column('correlation_id', sa.String(36)),
        sa.Column('causation_id', sa.String(36)),
        
        # Payload
        sa.Column('payload', sa.Text()),  # JSON
        
        # Delivery tracking
        sa.Column('status', sa.String(20), default='pending'),  # pending, processing, delivered, failed, dead_letter
        sa.Column('attempts', sa.Integer(), default=0),
        sa.Column('max_attempts', sa.Integer(), default=3),
        sa.Column('last_error', sa.Text()),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('processed_at', sa.DateTime()),
    )
    
    # Indexes for event bus operations
    op.create_index('ix_event_log_status', 'event_log', ['status'])
    op.create_index('ix_event_log_created_at', 'event_log', ['created_at'])
    op.create_index('ix_event_log_correlation_id', 'event_log', ['correlation_id'])
    op.create_index('ix_event_log_event_type', 'event_log', ['event_type'])
    
    # Composite index for replay queries (unprocessed events)
    op.create_index('ix_event_log_replay', 'event_log', ['status', 'created_at'])


def downgrade() -> None:
    """Drop event_log table"""
    op.drop_index('ix_event_log_replay')
    op.drop_index('ix_event_log_event_type')
    op.drop_index('ix_event_log_correlation_id')
    op.drop_index('ix_event_log_created_at')
    op.drop_index('ix_event_log_status')
    op.drop_table('event_log')
