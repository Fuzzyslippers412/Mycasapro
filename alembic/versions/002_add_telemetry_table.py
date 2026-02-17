"""add telemetry events table

Revision ID: 002
Revises: 001
Create Date: 2026-01-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create telemetry_events table for cost tracking and observability"""
    
    op.create_table(
        'telemetry_events',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('event_id', sa.String(36), nullable=False, unique=True),  # UUID
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('category', sa.String(30), nullable=False),  # ai_api, connector_sync, agent_task, etc.
        sa.Column('source', sa.String(50), nullable=False),  # agent name or component
        sa.Column('operation', sa.String(100)),  # What was done
        sa.Column('tenant_id', sa.String(36), default='default'),
        
        # AI/LLM specific
        sa.Column('model', sa.String(50)),  # claude-opus-4, gpt-4, etc.
        sa.Column('tokens_in', sa.Integer()),
        sa.Column('tokens_out', sa.Integer()),
        sa.Column('cost_estimate', sa.Float()),  # In dollars
        
        # Performance
        sa.Column('duration_ms', sa.Integer()),
        
        # Status
        sa.Column('status', sa.String(20), default='success'),  # success, error
        sa.Column('error', sa.Text()),
        
        # Tracing
        sa.Column('correlation_id', sa.String(36)),
        sa.Column('endpoint_name', sa.String(100)),
        
        # Metadata
        sa.Column('extra_data', sa.Text()),  # JSON for extra data
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    
    # Indexes for common queries
    op.create_index('ix_telemetry_events_created_at', 'telemetry_events', ['created_at'])
    op.create_index('ix_telemetry_events_source', 'telemetry_events', ['source'])
    op.create_index('ix_telemetry_events_category', 'telemetry_events', ['category'])
    op.create_index('ix_telemetry_events_correlation_id', 'telemetry_events', ['correlation_id'])
    op.create_index('ix_telemetry_events_model', 'telemetry_events', ['model'])


def downgrade() -> None:
    """Drop telemetry_events table"""
    op.drop_index('ix_telemetry_events_model')
    op.drop_index('ix_telemetry_events_correlation_id')
    op.drop_index('ix_telemetry_events_category')
    op.drop_index('ix_telemetry_events_source')
    op.drop_index('ix_telemetry_events_created_at')
    op.drop_table('telemetry_events')
