"""
Snapshot Pipeline for Edge Lab

Creates point-in-time snapshots of market data.
All data is stored with hashes for auditability.
"""

import uuid
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional, Tuple
import logging

from sqlalchemy.orm import Session

from ..db.models import (
    Source, UniversePolicy, IngestRun, Snapshot,
    SnapshotSymbol, SnapshotBarDaily
)
from ..adapters import AdapterRegistry, BaseAdapter
from ..utils.hashing import (
    compute_run_hash, compute_snapshot_hash, compute_policy_hash,
    compute_symbol_hash, compute_bars_hash
)
from ..config import get_config

logger = logging.getLogger(__name__)


class SnapshotPipeline:
    """
    Pipeline for creating market data snapshots.
    
    Steps:
    1. Resolve universe policy
    2. Fetch data via adapters
    3. Create snapshot with hashes
    4. Store in database
    """
    
    def __init__(self, session: Session, adapter: Optional[BaseAdapter] = None):
        self.session = session
        self.config = get_config()
        self.adapter = adapter or AdapterRegistry.get(self.config.default_adapter)
    
    def get_or_create_source(self, name: str) -> Source:
        """Get or create data source"""
        source = self.session.query(Source).filter(
            Source.name == name
        ).first()
        
        if source:
            return source
        
        source = Source(
            source_id=uuid.uuid4(),
            name=name,
            base_url=None,
            notes=f"Auto-created for {name} adapter",
        )
        self.session.add(source)
        self.session.flush()
        
        return source
    
    def get_or_create_universe_policy(
        self,
        name: str = "US_LIQUID_V1",
        version: int = 1,
        rules: Optional[Dict[str, Any]] = None
    ) -> UniversePolicy:
        """Get or create universe policy"""
        policy = self.session.query(UniversePolicy).filter(
            UniversePolicy.name == name,
            UniversePolicy.version == version
        ).first()
        
        if policy:
            return policy
        
        # Use provided rules or default from config
        if rules is None:
            rules = self.config.universe_policy.rules
        
        policy = UniversePolicy(
            universe_policy_id=uuid.uuid4(),
            name=name,
            version=version,
            rules=rules,
            policy_hash=compute_policy_hash(rules),
            is_active=True,
        )
        self.session.add(policy)
        self.session.flush()
        
        return policy
    
    def create_ingest_run(
        self,
        as_of: datetime,
        source: Source,
        policy: UniversePolicy,
        params: Dict[str, Any]
    ) -> IngestRun:
        """Create a new ingest run record"""
        run_hash = compute_run_hash(
            as_of=as_of,
            source_id=source.source_id,
            params=params,
            universe_policy_version=policy.version,
        )
        
        ingest_run = IngestRun(
            ingest_run_id=uuid.uuid4(),
            as_of=as_of,
            status="started",
            source_id=source.source_id,
            params=params,
            run_hash=run_hash,
        )
        self.session.add(ingest_run)
        self.session.flush()
        
        return ingest_run
    
    def run(
        self,
        as_of: datetime,
        policy_name: str = "US_LIQUID_V1",
        policy_version: int = 1,
        history_days: Optional[int] = None
    ) -> Tuple[Snapshot, List[str]]:
        """
        Run the snapshot pipeline.
        
        Returns: (snapshot, warnings)
        """
        warnings = []
        
        # Get source and policy
        source = self.get_or_create_source(self.adapter.name)
        policy = self.get_or_create_universe_policy(policy_name, policy_version)
        
        # Create ingest run
        params = {
            "history_days": history_days or self.config.preferred_history_days,
            "policy_name": policy_name,
        }
        ingest_run = self.create_ingest_run(as_of, source, policy, params)
        
        try:
            # Fetch universe
            logger.info(f"Fetching universe with policy {policy_name}")
            symbols_meta = self.adapter.fetch_universe(as_of, policy.rules)
            
            if not symbols_meta:
                raise ValueError("No symbols returned from adapter")
            
            symbols = [s.symbol for s in symbols_meta]
            logger.info(f"Found {len(symbols)} symbols")
            
            # Calculate date range for bars
            history_days = history_days or self.config.preferred_history_days
            end_date = as_of.date()
            start_date = end_date - timedelta(days=int(history_days * 1.5))  # Extra buffer for weekends
            
            # Fetch bars
            logger.info(f"Fetching bars from {start_date} to {end_date}")
            bars_data = self.adapter.fetch_daily_bars(symbols, start_date, end_date)
            
            # Validate bars
            for symbol, bars in bars_data.items():
                bar_warnings = self.adapter.validate_bars(bars)
                warnings.extend(bar_warnings)
            
            # Compute hashes for each symbol
            symbol_hashes = {}
            bar_hashes = {}
            
            for meta in symbols_meta:
                symbol_hashes[meta.symbol] = compute_symbol_hash(meta.to_dict())
            
            for symbol, bars in bars_data.items():
                bar_hashes[symbol] = compute_bars_hash([b.to_dict() for b in bars])
            
            # Compute snapshot hash
            snapshot_hash = compute_snapshot_hash(symbols, symbol_hashes, bar_hashes)
            
            # Check if snapshot already exists
            existing = self.session.query(Snapshot).filter(
                Snapshot.as_of == as_of,
                Snapshot.universe_policy_id == policy.universe_policy_id
            ).first()
            
            if existing:
                warnings.append(f"Snapshot already exists for {as_of}, returning existing")
                ingest_run.status = "succeeded"
                ingest_run.snapshot_id = existing.snapshot_id
                self.session.flush()
                return existing, warnings
            
            # Create snapshot
            snapshot = Snapshot(
                snapshot_id=uuid.uuid4(),
                ingest_run_id=ingest_run.ingest_run_id,
                as_of=as_of,
                universe_policy_id=policy.universe_policy_id,
                snapshot_hash=snapshot_hash,
                stats={
                    "symbol_count": len(symbols),
                    "total_bars": sum(len(bars) for bars in bars_data.values()),
                    "date_range": {
                        "start": start_date.isoformat(),
                        "end": end_date.isoformat(),
                    },
                },
            )
            self.session.add(snapshot)
            self.session.flush()
            
            # Store symbol metadata
            for meta in symbols_meta:
                symbol_row = SnapshotSymbol(
                    snapshot_id=snapshot.snapshot_id,
                    symbol=meta.symbol,
                    name=meta.name,
                    exchange=meta.exchange,
                    sector=meta.sector,
                    industry=meta.industry,
                    market_cap=meta.market_cap,
                    float_shares=meta.float_shares,
                    is_etf=meta.is_etf,
                    is_adr=meta.is_adr,
                )
                self.session.add(symbol_row)
            
            # Store bars
            for symbol, bars in bars_data.items():
                for bar in bars:
                    bar_row = SnapshotBarDaily(
                        snapshot_id=snapshot.snapshot_id,
                        symbol=bar.symbol,
                        date=bar.date,
                        o=bar.open,
                        h=bar.high,
                        l=bar.low,
                        c=bar.close,
                        v=bar.volume,
                        vw=bar.vwap,
                        dollar_vol=bar.dollar_volume,
                    )
                    self.session.add(bar_row)
            
            # Update ingest run
            ingest_run.status = "succeeded"
            ingest_run.snapshot_id = snapshot.snapshot_id
            self.session.flush()
            
            logger.info(f"Created snapshot {snapshot.snapshot_id} with {len(symbols)} symbols")
            
            return snapshot, warnings
            
        except Exception as e:
            ingest_run.status = "failed"
            ingest_run.error = str(e)
            self.session.flush()
            raise
