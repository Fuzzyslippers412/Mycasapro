"""Create edgelab schema and all tables

Revision ID: 001
Revises: 
Create Date: 2025-01-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "edgelab"


def upgrade() -> None:
    # Create schema
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")
    
    # 1. source table
    op.create_table(
        "source",
        sa.Column("source_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False, unique=True),
        sa.Column("base_url", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        schema=SCHEMA,
    )
    
    # 2. universe_policy table
    op.create_table(
        "universe_policy",
        sa.Column("universe_policy_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("rules", postgresql.JSONB(), nullable=False),
        sa.Column("policy_hash", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("name", "version", name="uq_universe_policy_name_version"),
        schema=SCHEMA,
    )
    
    # 3. ingest_run table
    op.create_table(
        "ingest_run",
        sa.Column("ingest_run_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("as_of", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.source.source_id"), nullable=False),
        sa.Column("params", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("snapshot_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("run_hash", sa.Text(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('started', 'succeeded', 'failed')", name="ck_ingest_run_status"),
        schema=SCHEMA,
    )
    
    # 4. snapshot table
    op.create_table(
        "snapshot",
        sa.Column("snapshot_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ingest_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.ingest_run.ingest_run_id"), nullable=False),
        sa.Column("as_of", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("universe_policy_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.universe_policy.universe_policy_id"), nullable=False),
        sa.Column("snapshot_hash", sa.Text(), nullable=False),
        sa.Column("stats", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("as_of", "universe_policy_id", name="uq_snapshot_as_of_policy"),
        schema=SCHEMA,
    )
    
    # 5. snapshot_symbol table
    op.create_table(
        "snapshot_symbol",
        sa.Column("snapshot_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.snapshot.snapshot_id"), primary_key=True),
        sa.Column("symbol", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("exchange", sa.Text(), nullable=True),
        sa.Column("sector", sa.Text(), nullable=True),
        sa.Column("industry", sa.Text(), nullable=True),
        sa.Column("market_cap", sa.Numeric(), nullable=True),
        sa.Column("float_shares", sa.Numeric(), nullable=True),
        sa.Column("is_etf", sa.Boolean(), nullable=True),
        sa.Column("is_adr", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        schema=SCHEMA,
    )
    
    # 6. snapshot_bar_daily table
    op.create_table(
        "snapshot_bar_daily",
        sa.Column("snapshot_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.snapshot.snapshot_id"), primary_key=True),
        sa.Column("symbol", sa.Text(), primary_key=True),
        sa.Column("date", sa.Date(), primary_key=True),
        sa.Column("o", sa.Numeric(), nullable=False),
        sa.Column("h", sa.Numeric(), nullable=False),
        sa.Column("l", sa.Numeric(), nullable=False),
        sa.Column("c", sa.Numeric(), nullable=False),
        sa.Column("v", sa.Numeric(), nullable=False),
        sa.Column("vw", sa.Numeric(), nullable=True),
        sa.Column("dollar_vol", sa.Numeric(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        schema=SCHEMA,
    )
    
    # 7. feature_set table
    op.create_table(
        "feature_set",
        sa.Column("feature_set_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("definition", postgresql.JSONB(), nullable=False),
        sa.Column("feature_set_hash", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("name", "version", name="uq_feature_set_name_version"),
        schema=SCHEMA,
    )
    
    # 8. features table
    op.create_table(
        "features",
        sa.Column("snapshot_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.snapshot.snapshot_id"), primary_key=True),
        sa.Column("feature_set_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.feature_set.feature_set_id"), primary_key=True),
        sa.Column("symbol", sa.Text(), primary_key=True),
        sa.Column("features", postgresql.JSONB(), nullable=False),
        sa.Column("feature_hash", sa.Text(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        schema=SCHEMA,
    )
    
    # 9. model table
    op.create_table(
        "model",
        sa.Column("model_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("model_type", sa.Text(), nullable=False),
        sa.Column("train_window", postgresql.JSONB(), nullable=False),
        sa.Column("config", postgresql.JSONB(), nullable=False),
        sa.Column("model_hash", sa.Text(), nullable=False),
        sa.Column("artifact_path", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("name", "version", name="uq_model_name_version"),
        schema=SCHEMA,
    )
    
    # 10. prediction_run table
    op.create_table(
        "prediction_run",
        sa.Column("prediction_run_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("snapshot_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.snapshot.snapshot_id"), nullable=False),
        sa.Column("feature_set_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.feature_set.feature_set_id"), nullable=False),
        sa.Column("model_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.model.model_id"), nullable=False),
        sa.Column("horizon_trading_days", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("task", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("params", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("run_hash", sa.Text(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("task IN ('weekly_predict', 'daily_scan')", name="ck_prediction_run_task"),
        sa.CheckConstraint("status IN ('started', 'succeeded', 'failed')", name="ck_prediction_run_status"),
        sa.UniqueConstraint("run_hash", name="uq_prediction_run_hash"),
        schema=SCHEMA,
    )
    
    # 11. prediction table
    op.create_table(
        "prediction",
        sa.Column("prediction_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.prediction_run.prediction_run_id"), primary_key=True),
        sa.Column("symbol", sa.Text(), primary_key=True),
        sa.Column("score", sa.Numeric(), nullable=False),
        sa.Column("p_beat_spy", sa.Numeric(), nullable=True),
        sa.Column("exp_return", sa.Numeric(), nullable=True),
        sa.Column("exp_vol", sa.Numeric(), nullable=True),
        sa.Column("confidence", sa.Numeric(), nullable=False),
        sa.Column("risk_flags", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("top_features", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        schema=SCHEMA,
    )
    
    # 12. evaluation_run table
    op.create_table(
        "evaluation_run",
        sa.Column("evaluation_run_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("prediction_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey(f"{SCHEMA}.prediction_run.prediction_run_id"), nullable=False),
        sa.Column("evaluated_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("metrics", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("run_hash", sa.Text(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('started', 'succeeded', 'failed')", name="ck_evaluation_run_status"),
        schema=SCHEMA,
    )


def downgrade() -> None:
    # Drop tables in reverse order (respecting foreign keys)
    op.drop_table("evaluation_run", schema=SCHEMA)
    op.drop_table("prediction", schema=SCHEMA)
    op.drop_table("prediction_run", schema=SCHEMA)
    op.drop_table("model", schema=SCHEMA)
    op.drop_table("features", schema=SCHEMA)
    op.drop_table("feature_set", schema=SCHEMA)
    op.drop_table("snapshot_bar_daily", schema=SCHEMA)
    op.drop_table("snapshot_symbol", schema=SCHEMA)
    op.drop_table("snapshot", schema=SCHEMA)
    op.drop_table("ingest_run", schema=SCHEMA)
    op.drop_table("universe_policy", schema=SCHEMA)
    op.drop_table("source", schema=SCHEMA)
    
    # Drop schema
    op.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
