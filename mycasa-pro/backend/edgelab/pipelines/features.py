"""
Feature Engine for Edge Lab

DETERMINISTIC feature computation from snapshot data.
All features are pure functions of snapshot_id - no external data calls.
"""

import math
import uuid
from datetime import date
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import logging

from sqlalchemy.orm import Session

from ..db.models import (
    Snapshot, SnapshotBarDaily, FeatureSet, Features
)
from ..utils.hashing import compute_feature_hash, compute_feature_set_hash
from ..config import get_config, FeatureSetConfig

logger = logging.getLogger(__name__)


@dataclass
class BarData:
    """Simple bar data for computation"""
    date: date
    o: float
    h: float
    l: float
    c: float
    v: float
    vw: Optional[float] = None
    dollar_vol: Optional[float] = None


class FeatureEngine:
    """
    Deterministic feature computation engine.
    
    CRITICAL: Features are computed ONLY from data in the snapshot.
    No external API calls are made during feature computation.
    """
    
    def __init__(self, session: Session):
        self.session = session
        self.config = get_config()
    
    def get_or_create_feature_set(
        self,
        name: str = "CORE_V1",
        version: int = 1
    ) -> FeatureSet:
        """Get or create a feature set definition"""
        existing = self.session.query(FeatureSet).filter(
            FeatureSet.name == name,
            FeatureSet.version == version
        ).first()
        
        if existing:
            return existing
        
        # Create from config
        fs_config = self.config.feature_set
        definition = {
            "features": fs_config.features,
            "windows": fs_config.windows,
        }
        
        feature_set = FeatureSet(
            feature_set_id=uuid.uuid4(),
            name=name,
            version=version,
            definition=definition,
            feature_set_hash=compute_feature_set_hash(definition),
            is_active=True,
        )
        
        self.session.add(feature_set)
        self.session.flush()
        
        return feature_set
    
    def compute_features(
        self,
        snapshot_id: str,
        feature_set_id: str
    ) -> Dict[str, Dict[str, Any]]:
        """
        Compute features for all symbols in a snapshot.
        
        This is a PURE FUNCTION of snapshot data.
        Returns: {symbol: {feature_name: value}}
        """
        # Get snapshot
        snapshot = self.session.query(Snapshot).filter(
            Snapshot.snapshot_id == snapshot_id
        ).first()
        
        if not snapshot:
            raise ValueError(f"Snapshot not found: {snapshot_id}")
        
        # Get feature set definition
        feature_set = self.session.query(FeatureSet).filter(
            FeatureSet.feature_set_id == feature_set_id
        ).first()
        
        if not feature_set:
            raise ValueError(f"Feature set not found: {feature_set_id}")
        
        definition = feature_set.definition
        feature_names = definition.get("features", [])
        
        # Get all bars for this snapshot, organized by symbol
        bars_query = self.session.query(SnapshotBarDaily).filter(
            SnapshotBarDaily.snapshot_id == snapshot_id
        ).order_by(SnapshotBarDaily.symbol, SnapshotBarDaily.date)
        
        # Group bars by symbol
        symbol_bars: Dict[str, List[BarData]] = {}
        for bar in bars_query:
            if bar.symbol not in symbol_bars:
                symbol_bars[bar.symbol] = []
            symbol_bars[bar.symbol].append(BarData(
                date=bar.date,
                o=float(bar.o),
                h=float(bar.h),
                l=float(bar.l),
                c=float(bar.c),
                v=float(bar.v),
                vw=float(bar.vw) if bar.vw else None,
                dollar_vol=float(bar.dollar_vol) if bar.dollar_vol else None,
            ))
        
        # Compute features for each symbol
        result = {}
        for symbol, bars in symbol_bars.items():
            # Sort by date (oldest first)
            bars = sorted(bars, key=lambda x: x.date)
            
            if len(bars) < 2:
                logger.warning(f"Insufficient data for {symbol}: {len(bars)} bars")
                continue
            
            features = self._compute_symbol_features(bars, feature_names)
            if features:
                result[symbol] = features
        
        return result
    
    def _compute_symbol_features(
        self,
        bars: List[BarData],
        feature_names: List[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Compute all features for a single symbol.
        
        DETERMINISTIC: Same bars always produce same features.
        """
        if len(bars) < 2:
            return None
        
        # Pre-compute commonly needed values
        closes = [b.c for b in bars]
        volumes = [b.v for b in bars]
        highs = [b.h for b in bars]
        lows = [b.l for b in bars]
        opens = [b.o for b in bars]
        
        # Most recent bar is last in list
        latest_close = closes[-1]
        latest_volume = volumes[-1]
        latest_open = opens[-1]
        prev_close = closes[-2] if len(closes) > 1 else latest_close
        
        features = {}
        
        for name in feature_names:
            try:
                value = self._compute_single_feature(
                    name, closes, volumes, highs, lows, opens,
                    latest_close, latest_volume, latest_open, prev_close
                )
                features[name] = value
            except Exception as e:
                logger.warning(f"Error computing {name}: {e}")
                features[name] = None
        
        return features
    
    def _compute_single_feature(
        self,
        name: str,
        closes: List[float],
        volumes: List[float],
        highs: List[float],
        lows: List[float],
        opens: List[float],
        latest_close: float,
        latest_volume: float,
        latest_open: float,
        prev_close: float
    ) -> Optional[float]:
        """Compute a single feature value"""
        
        if name == "ret_1d":
            if prev_close > 0:
                return (latest_close / prev_close) - 1
            return None
        
        elif name == "ret_5d":
            if len(closes) > 5 and closes[-6] > 0:
                return (latest_close / closes[-6]) - 1
            return None
        
        elif name == "ret_20d":
            if len(closes) > 20 and closes[-21] > 0:
                return (latest_close / closes[-21]) - 1
            return None
        
        elif name == "ret_60d":
            if len(closes) > 60 and closes[-61] > 0:
                return (latest_close / closes[-61]) - 1
            return None
        
        elif name == "vol_20d":
            if len(closes) > 20:
                returns = [(closes[i] / closes[i-1]) - 1 for i in range(-20, 0)]
                return self._std(returns)
            return None
        
        elif name == "atr_14_pct":
            if len(closes) > 14:
                atr = self._compute_atr(highs[-15:], lows[-15:], closes[-15:], 14)
                if atr and latest_close > 0:
                    return atr / latest_close
            return None
        
        elif name == "gap_pct":
            if prev_close > 0:
                return (latest_open / prev_close) - 1
            return None
        
        elif name == "rel_vol_20d":
            if len(volumes) > 20:
                avg_vol = self._mean(volumes[-21:-1])
                if avg_vol and avg_vol > 0:
                    return latest_volume / avg_vol
            return None
        
        elif name == "dollar_vol_20d":
            if len(closes) > 20 and len(volumes) > 20:
                dollar_vols = [closes[i] * volumes[i] for i in range(-20, 0)]
                return self._mean(dollar_vols)
            return None
        
        elif name == "dist_sma_20":
            if len(closes) > 20:
                sma = self._mean(closes[-20:])
                if sma and sma > 0:
                    return (latest_close - sma) / sma
            return None
        
        elif name == "dist_sma_50":
            if len(closes) > 50:
                sma = self._mean(closes[-50:])
                if sma and sma > 0:
                    return (latest_close - sma) / sma
            return None
        
        elif name == "trend_slope_20":
            if len(closes) > 20:
                log_closes = [math.log(c) if c > 0 else 0 for c in closes[-20:]]
                return self._linear_regression_slope(log_closes)
            return None
        
        return None
    
    @staticmethod
    def _mean(values: List[float]) -> Optional[float]:
        """Compute mean of values"""
        if not values:
            return None
        return sum(values) / len(values)
    
    @staticmethod
    def _std(values: List[float]) -> Optional[float]:
        """Compute standard deviation of values"""
        if len(values) < 2:
            return None
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return math.sqrt(variance)
    
    @staticmethod
    def _compute_atr(
        highs: List[float],
        lows: List[float],
        closes: List[float],
        period: int
    ) -> Optional[float]:
        """Compute Average True Range"""
        if len(highs) < period + 1:
            return None
        
        true_ranges = []
        for i in range(1, len(highs)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            )
            true_ranges.append(tr)
        
        if len(true_ranges) < period:
            return None
        
        return sum(true_ranges[-period:]) / period
    
    @staticmethod
    def _linear_regression_slope(values: List[float]) -> Optional[float]:
        """Compute slope of linear regression"""
        n = len(values)
        if n < 2:
            return None
        
        x_sum = sum(range(n))
        y_sum = sum(values)
        xy_sum = sum(i * v for i, v in enumerate(values))
        x2_sum = sum(i * i for i in range(n))
        
        denominator = n * x2_sum - x_sum * x_sum
        if denominator == 0:
            return None
        
        slope = (n * xy_sum - x_sum * y_sum) / denominator
        return slope
    
    def save_features(
        self,
        snapshot_id: str,
        feature_set_id: str,
        features_data: Dict[str, Dict[str, Any]]
    ) -> int:
        """
        Save computed features to database.
        
        Returns number of features saved.
        """
        count = 0
        
        for symbol, feature_values in features_data.items():
            # Compute feature hash for auditability
            feature_hash = compute_feature_hash(feature_values)
            
            # Check if already exists
            existing = self.session.query(Features).filter(
                Features.snapshot_id == snapshot_id,
                Features.feature_set_id == feature_set_id,
                Features.symbol == symbol
            ).first()
            
            if existing:
                # Update if hash changed
                if existing.feature_hash != feature_hash:
                    existing.features = feature_values
                    existing.feature_hash = feature_hash
            else:
                # Create new
                feature_row = Features(
                    snapshot_id=snapshot_id,
                    feature_set_id=feature_set_id,
                    symbol=symbol,
                    features=feature_values,
                    feature_hash=feature_hash,
                )
                self.session.add(feature_row)
                count += 1
        
        self.session.flush()
        return count
    
    def run(
        self,
        snapshot_id: str,
        feature_set_name: str = "CORE_V1",
        feature_set_version: int = 1
    ) -> Tuple[str, int]:
        """
        Run feature computation pipeline.
        
        Returns: (feature_set_id, num_features_computed)
        """
        # Get or create feature set
        feature_set = self.get_or_create_feature_set(
            feature_set_name,
            feature_set_version
        )
        
        # Compute features
        features_data = self.compute_features(snapshot_id, feature_set.feature_set_id)
        
        # Save features
        count = self.save_features(
            snapshot_id,
            feature_set.feature_set_id,
            features_data
        )
        
        logger.info(f"Computed {count} feature rows for snapshot {snapshot_id}")
        
        return feature_set.feature_set_id, count
