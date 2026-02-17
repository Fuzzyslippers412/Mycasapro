"""Create indexes for performance

Revision ID: 002
Revises: 001
Create Date: 2025-01-30

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "edgelab"


def upgrade() -> None:
    # Snapshot lookups
    op.create_index("ix_snapshot_as_of", "snapshot", ["as_of"], schema=SCHEMA)
    op.create_index("ix_snapshot_policy", "snapshot", ["universe_policy_id"], schema=SCHEMA)
    
    # Symbol lookups
    op.create_index("ix_snapshot_symbol_symbol", "snapshot_symbol", ["symbol"], schema=SCHEMA)
    
    # Bar lookups (critical for feature computation)
    op.create_index("ix_bar_daily_symbol", "snapshot_bar_daily", ["symbol"], schema=SCHEMA)
    op.create_index("ix_bar_daily_date", "snapshot_bar_daily", ["date"], schema=SCHEMA)
    op.create_index("ix_bar_daily_symbol_date", "snapshot_bar_daily", ["symbol", "date"], schema=SCHEMA)
    
    # Feature lookups
    op.create_index("ix_features_symbol", "features", ["symbol"], schema=SCHEMA)
    
    # Prediction lookups
    op.create_index("ix_prediction_run_snapshot", "prediction_run", ["snapshot_id"], schema=SCHEMA)
    op.create_index("ix_prediction_run_task", "prediction_run", ["task"], schema=SCHEMA)
    op.create_index("ix_prediction_symbol", "prediction", ["symbol"], schema=SCHEMA)
    op.create_index("ix_prediction_score", "prediction", ["score"], schema=SCHEMA)
    
    # Evaluation lookups
    op.create_index("ix_evaluation_run_prediction", "evaluation_run", ["prediction_run_id"], schema=SCHEMA)
    
    # Ingest run lookups
    op.create_index("ix_ingest_run_as_of", "ingest_run", ["as_of"], schema=SCHEMA)
    op.create_index("ix_ingest_run_status", "ingest_run", ["status"], schema=SCHEMA)


def downgrade() -> None:
    # Drop all indexes
    op.drop_index("ix_evaluation_run_prediction", table_name="evaluation_run", schema=SCHEMA)
    op.drop_index("ix_prediction_score", table_name="prediction", schema=SCHEMA)
    op.drop_index("ix_prediction_symbol", table_name="prediction", schema=SCHEMA)
    op.drop_index("ix_prediction_run_task", table_name="prediction_run", schema=SCHEMA)
    op.drop_index("ix_prediction_run_snapshot", table_name="prediction_run", schema=SCHEMA)
    op.drop_index("ix_features_symbol", table_name="features", schema=SCHEMA)
    op.drop_index("ix_bar_daily_symbol_date", table_name="snapshot_bar_daily", schema=SCHEMA)
    op.drop_index("ix_bar_daily_date", table_name="snapshot_bar_daily", schema=SCHEMA)
    op.drop_index("ix_bar_daily_symbol", table_name="snapshot_bar_daily", schema=SCHEMA)
    op.drop_index("ix_snapshot_symbol_symbol", table_name="snapshot_symbol", schema=SCHEMA)
    op.drop_index("ix_snapshot_policy", table_name="snapshot", schema=SCHEMA)
    op.drop_index("ix_snapshot_as_of", table_name="snapshot", schema=SCHEMA)
    op.drop_index("ix_ingest_run_status", table_name="ingest_run", schema=SCHEMA)
    op.drop_index("ix_ingest_run_as_of", table_name="ingest_run", schema=SCHEMA)
