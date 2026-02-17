"""add constraints and indexes

Revision ID: 001
Revises: 
Create Date: 2026-01-28

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add constraints and indexes for data integrity.
    Using batch mode for SQLite compatibility.
    """
    
    # ============ MESSAGES TABLE ============
    # Add unique constraint for deduplication
    with op.batch_alter_table('messages', schema=None) as batch_op:
        # Dedupe key: provider + external_id
        batch_op.create_index(
            'ix_messages_dedupe',
            ['provider', 'external_id'],
            unique=True
        )
        # Index for timestamp queries (newest first)
        batch_op.create_index(
            'ix_messages_timestamp',
            ['timestamp'],
        )
        # Index for status filtering
        batch_op.create_index(
            'ix_messages_status',
            ['status'],
        )
    
    # ============ MAINTENANCE_TASKS TABLE ============
    with op.batch_alter_table('maintenance_tasks', schema=None) as batch_op:
        # Index for due date queries
        batch_op.create_index(
            'ix_maintenance_tasks_due_date',
            ['due_date'],
        )
        # Index for status filtering
        batch_op.create_index(
            'ix_maintenance_tasks_status',
            ['status'],
        )
        # Index for scheduled date
        batch_op.create_index(
            'ix_maintenance_tasks_scheduled_date',
            ['scheduled_date'],
        )
    
    # ============ TRANSACTIONS TABLE ============
    with op.batch_alter_table('transactions', schema=None) as batch_op:
        # Index for timestamp queries
        batch_op.create_index(
            'ix_transactions_timestamp',
            ['timestamp'],
        )
        # Index for category grouping
        batch_op.create_index(
            'ix_transactions_category',
            ['category'],
        )
    
    # ============ BILLS TABLE ============
    with op.batch_alter_table('bills', schema=None) as batch_op:
        # Index for due date queries
        batch_op.create_index(
            'ix_bills_due_date',
            ['due_date'],
        )
    
    # ============ PROJECTS TABLE ============
    with op.batch_alter_table('projects', schema=None) as batch_op:
        # Index for status filtering
        batch_op.create_index(
            'ix_projects_status',
            ['status'],
        )
    
    # ============ CONTRACTOR_JOBS TABLE ============
    with op.batch_alter_table('contractor_jobs', schema=None) as batch_op:
        # Index for status filtering
        batch_op.create_index(
            'ix_contractor_jobs_status',
            ['status'],
        )


def downgrade() -> None:
    """Remove constraints and indexes"""
    
    with op.batch_alter_table('contractor_jobs', schema=None) as batch_op:
        batch_op.drop_index('ix_contractor_jobs_status')
    
    with op.batch_alter_table('projects', schema=None) as batch_op:
        batch_op.drop_index('ix_projects_status')
    
    with op.batch_alter_table('bills', schema=None) as batch_op:
        batch_op.drop_index('ix_bills_due_date')
    
    with op.batch_alter_table('transactions', schema=None) as batch_op:
        batch_op.drop_index('ix_transactions_category')
        batch_op.drop_index('ix_transactions_timestamp')
    
    with op.batch_alter_table('maintenance_tasks', schema=None) as batch_op:
        batch_op.drop_index('ix_maintenance_tasks_scheduled_date')
        batch_op.drop_index('ix_maintenance_tasks_status')
        batch_op.drop_index('ix_maintenance_tasks_due_date')
    
    with op.batch_alter_table('messages', schema=None) as batch_op:
        batch_op.drop_index('ix_messages_status')
        batch_op.drop_index('ix_messages_timestamp')
        batch_op.drop_index('ix_messages_dedupe')
