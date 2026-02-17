"""
Edge Lab Database Models - SQLite Compatible

Converted from PostgreSQL to SQLite:
- UUID → String (36 chars)
- JSONB → JSON
- TIMESTAMP → DateTime
- Removed schema references
"""

import uuid
from datetime import datetime, date
from typing import Optional, List, Dict, Any

from sqlalchemy import (
    Column, String, Text, Boolean, Integer, Float, Date, DateTime,
    ForeignKey, UniqueConstraint, Index, JSON
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


def generate_uuid():
    return str(uuid.uuid4())


class Source(Base):
    """Data source registry (yfinance, polygon, etc.)"""
    __tablename__ = "edgelab_source"

    source_id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(Text, nullable=False, unique=True)
    base_url = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    ingest_runs = relationship("IngestRun", back_populates="source")


class UniversePolicy(Base):
    """Universe filter rules (e.g., US_LIQUID_V1)"""
    __tablename__ = "edgelab_universe_policy"

    universe_policy_id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(Text, nullable=False)
    version = Column(Integer, nullable=False)
    rules = Column(JSON, nullable=False)
    policy_hash = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_edgelab_policy_name_version"),
    )

    snapshots = relationship("Snapshot", back_populates="universe_policy")


class IngestRun(Base):
    """Track data ingestion runs"""
    __tablename__ = "edgelab_ingest_run"

    ingest_run_id = Column(String(36), primary_key=True, default=generate_uuid)
    as_of = Column(DateTime, nullable=False)
    status = Column(Text, nullable=False)  # started, succeeded, failed
    source_id = Column(String(36), ForeignKey("edgelab_source.source_id"), nullable=False)
    params = Column(JSON, nullable=False, default=dict)
    error = Column(Text, nullable=True)
    snapshot_id = Column(String(36), nullable=True)
    run_hash = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    source = relationship("Source", back_populates="ingest_runs")
    snapshot = relationship("Snapshot", back_populates="ingest_run", uselist=False)


class Snapshot(Base):
    """Point-in-time data snapshot"""
    __tablename__ = "edgelab_snapshot"

    snapshot_id = Column(String(36), primary_key=True, default=generate_uuid)
    ingest_run_id = Column(String(36), ForeignKey("edgelab_ingest_run.ingest_run_id"), nullable=False)
    as_of = Column(DateTime, nullable=False)
    universe_policy_id = Column(String(36), ForeignKey("edgelab_universe_policy.universe_policy_id"), nullable=False)
    snapshot_hash = Column(Text, nullable=False)
    stats = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("as_of", "universe_policy_id", name="uq_edgelab_snapshot_as_of_policy"),
    )

    ingest_run = relationship("IngestRun", back_populates="snapshot")
    universe_policy = relationship("UniversePolicy", back_populates="snapshots")
    symbols = relationship("SnapshotSymbol", back_populates="snapshot", cascade="all, delete-orphan")
    bars = relationship("SnapshotBarDaily", back_populates="snapshot", cascade="all, delete-orphan")
    features = relationship("Features", back_populates="snapshot", cascade="all, delete-orphan")
    prediction_runs = relationship("PredictionRun", back_populates="snapshot")


class SnapshotSymbol(Base):
    """Symbol metadata within a snapshot"""
    __tablename__ = "edgelab_snapshot_symbol"

    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_id = Column(String(36), ForeignKey("edgelab_snapshot.snapshot_id"), nullable=False)
    symbol = Column(Text, nullable=False)
    name = Column(Text, nullable=True)
    exchange = Column(Text, nullable=True)
    sector = Column(Text, nullable=True)
    industry = Column(Text, nullable=True)
    market_cap = Column(Float, nullable=True)
    float_shares = Column(Float, nullable=True)
    is_etf = Column(Boolean, nullable=True)
    is_adr = Column(Boolean, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("snapshot_id", "symbol", name="uq_edgelab_snapshot_symbol"),
    )

    snapshot = relationship("Snapshot", back_populates="symbols")


class SnapshotBarDaily(Base):
    """Daily OHLCV bars within a snapshot"""
    __tablename__ = "edgelab_snapshot_bar_daily"

    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_id = Column(String(36), ForeignKey("edgelab_snapshot.snapshot_id"), nullable=False)
    symbol = Column(Text, nullable=False)
    bar_date = Column(Date, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    vwap = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("snapshot_id", "symbol", "bar_date", name="uq_edgelab_bar_daily"),
        Index("ix_edgelab_bar_symbol_date", "symbol", "bar_date"),
    )

    snapshot = relationship("Snapshot", back_populates="bars")


class FeatureSet(Base):
    """Feature set configuration"""
    __tablename__ = "edgelab_feature_set"

    feature_set_id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(Text, nullable=False)
    version = Column(Integer, nullable=False)
    config = Column(JSON, nullable=False)
    feature_hash = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_edgelab_feature_set"),
    )


class Model(Base):
    """Prediction model configuration"""
    __tablename__ = "edgelab_model"

    model_id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(Text, nullable=False)
    version = Column(Integer, nullable=False)
    model_type = Column(Text, nullable=False)
    config = Column(JSON, nullable=False)
    model_hash = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_edgelab_model"),
    )


class Features(Base):
    """Computed features for a symbol within a snapshot"""
    __tablename__ = "edgelab_features"

    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_id = Column(String(36), ForeignKey("edgelab_snapshot.snapshot_id"), nullable=False)
    symbol = Column(Text, nullable=False)
    feature_set = Column(Text, nullable=False)  # e.g., CORE_V1
    features = Column(JSON, nullable=False)  # {"ret_1d": 0.02, "vol_20d": 0.15, ...}
    feature_hash = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("snapshot_id", "symbol", "feature_set", name="uq_edgelab_features"),
    )

    snapshot = relationship("Snapshot", back_populates="features")


class PredictionRun(Base):
    """A prediction run against a snapshot"""
    __tablename__ = "edgelab_prediction_run"

    prediction_run_id = Column(String(36), primary_key=True, default=generate_uuid)
    snapshot_id = Column(String(36), ForeignKey("edgelab_snapshot.snapshot_id"), nullable=False)
    model_name = Column(Text, nullable=False)
    model_version = Column(Integer, nullable=False)
    horizon_days = Column(Integer, nullable=False)
    run_config = Column(JSON, nullable=False, default=dict)
    run_hash = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    snapshot = relationship("Snapshot", back_populates="prediction_runs")
    predictions = relationship("Prediction", back_populates="prediction_run", cascade="all, delete-orphan")
    evaluations = relationship("EvaluationRun", back_populates="prediction_run")


class Prediction(Base):
    """Individual stock prediction"""
    __tablename__ = "edgelab_prediction"

    id = Column(Integer, primary_key=True, autoincrement=True)
    prediction_run_id = Column(String(36), ForeignKey("edgelab_prediction_run.prediction_run_id"), nullable=False)
    symbol = Column(Text, nullable=False)
    score = Column(Float, nullable=False)
    confidence = Column(Float, nullable=True)
    risk_flags = Column(JSON, nullable=True)  # ["LOW_LIQUIDITY", "HUGE_GAP", ...]
    feature_contributions = Column(JSON, nullable=True)  # {"ret_5d": 0.3, "vol_20d": -0.1, ...}
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("prediction_run_id", "symbol", name="uq_edgelab_prediction"),
        Index("ix_edgelab_prediction_score", "prediction_run_id", "score"),
    )

    prediction_run = relationship("PredictionRun", back_populates="predictions")


class EvaluationRun(Base):
    """Evaluation of prediction accuracy"""
    __tablename__ = "edgelab_evaluation_run"

    evaluation_run_id = Column(String(36), primary_key=True, default=generate_uuid)
    prediction_run_id = Column(String(36), ForeignKey("edgelab_prediction_run.prediction_run_id"), nullable=False)
    evaluation_date = Column(Date, nullable=False)
    metrics = Column(JSON, nullable=False)  # {"hit_rate": 0.6, "avg_return": 0.02, ...}
    top_n_evaluated = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    prediction_run = relationship("PredictionRun", back_populates="evaluations")
