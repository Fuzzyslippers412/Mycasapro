"""
Prediction Pipeline for Edge Lab

Generates predictions using features and models.
All predictions are linked to snapshots via hashes.
"""

import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import logging

from sqlalchemy.orm import Session

from ..db.models import (
    Snapshot, Features, FeatureSet, Model, PredictionRun, Prediction
)
from ..utils.hashing import compute_prediction_run_hash, compute_model_hash
from ..config import get_config

logger = logging.getLogger(__name__)


@dataclass
class PredictionResult:
    """Individual prediction result"""
    symbol: str
    score: float
    p_beat_spy: Optional[float]
    exp_return: Optional[float]
    exp_vol: Optional[float]
    confidence: float
    risk_flags: List[str]
    top_features: List[Dict[str, Any]]


class BaseModel:
    """Base class for prediction models"""
    
    name: str = "base"
    version: int = 1
    model_type: str = "base"
    
    def predict(
        self,
        features: Dict[str, Dict[str, Any]],
        spy_features: Optional[Dict[str, Any]] = None
    ) -> List[PredictionResult]:
        raise NotImplementedError


class RuleScoreModel(BaseModel):
    """
    Rule-based scoring model (baseline).
    
    Combines momentum, mean reversion, volatility, and liquidity signals.
    """
    
    name = "BASELINE_V1"
    version = 1
    model_type = "rule_score"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or get_config().model.config
        self.risk_config = get_config().risk_flags
    
    def predict(
        self,
        features: Dict[str, Dict[str, Any]],
        spy_features: Optional[Dict[str, Any]] = None
    ) -> List[PredictionResult]:
        results = []
        
        for symbol, feat in features.items():
            if symbol == "SPY":
                continue  # Skip benchmark
            
            # Compute score components
            momentum_score = self._momentum_score(feat)
            mean_rev_score = self._mean_reversion_score(feat)
            vol_penalty = self._volatility_penalty(feat)
            liquidity_score = self._liquidity_score(feat)
            
            # Weighted combination
            weights = self.config
            score = (
                momentum_score * weights.get("momentum_weight", 0.3) +
                mean_rev_score * weights.get("mean_reversion_weight", 0.2) -
                vol_penalty * weights.get("volatility_penalty", 0.2) +
                liquidity_score * weights.get("liquidity_weight", 0.3)
            )
            
            # Compute expected return (simplified)
            exp_return = feat.get("ret_20d")
            exp_vol = feat.get("vol_20d")
            
            # Compute p_beat_spy if SPY features available
            p_beat_spy = None
            if spy_features and exp_return is not None:
                spy_ret = spy_features.get("ret_20d")
                if spy_ret is not None:
                    # Simple comparison (could be more sophisticated)
                    p_beat_spy = 0.5 + (exp_return - spy_ret) * 2
                    p_beat_spy = max(0, min(1, p_beat_spy))
            
            # Risk flags
            risk_flags = self._compute_risk_flags(feat)
            
            # Confidence based on data quality
            confidence = self._compute_confidence(feat, risk_flags)
            
            # Top contributing features
            top_features = [
                {"name": "momentum", "value": momentum_score},
                {"name": "mean_reversion", "value": mean_rev_score},
                {"name": "volatility", "value": -vol_penalty},
                {"name": "liquidity", "value": liquidity_score},
            ]
            
            results.append(PredictionResult(
                symbol=symbol,
                score=score,
                p_beat_spy=p_beat_spy,
                exp_return=exp_return,
                exp_vol=exp_vol,
                confidence=confidence,
                risk_flags=risk_flags,
                top_features=top_features,
            ))
        
        # Sort by score descending
        results.sort(key=lambda x: x.score, reverse=True)
        
        return results
    
    def _momentum_score(self, feat: Dict[str, Any]) -> float:
        """Score based on momentum signals"""
        ret_5d = feat.get("ret_5d") or 0
        ret_20d = feat.get("ret_20d") or 0
        trend = feat.get("trend_slope_20") or 0
        
        # Normalize and combine
        return (ret_5d * 0.3 + ret_20d * 0.3 + trend * 100 * 0.4)
    
    def _mean_reversion_score(self, feat: Dict[str, Any]) -> float:
        """Score based on mean reversion signals"""
        dist_sma_20 = feat.get("dist_sma_20") or 0
        dist_sma_50 = feat.get("dist_sma_50") or 0
        
        # Oversold = positive score (mean reversion opportunity)
        return -dist_sma_20 * 0.6 - dist_sma_50 * 0.4
    
    def _volatility_penalty(self, feat: Dict[str, Any]) -> float:
        """Penalty for high volatility"""
        vol = feat.get("vol_20d") or 0
        atr = feat.get("atr_14_pct") or 0
        
        # Higher vol = higher penalty
        return (vol * 0.6 + atr * 0.4) * 10
    
    def _liquidity_score(self, feat: Dict[str, Any]) -> float:
        """Score based on liquidity"""
        dollar_vol = feat.get("dollar_vol_20d") or 0
        rel_vol = feat.get("rel_vol_20d") or 1
        
        # Higher liquidity = better
        liq_score = min(1, dollar_vol / 100_000_000)  # Normalize to 100M
        vol_score = min(1, rel_vol / 2)  # Relative volume boost
        
        return liq_score * 0.7 + vol_score * 0.3
    
    def _compute_risk_flags(self, feat: Dict[str, Any]) -> List[str]:
        """Compute risk flags based on features"""
        flags = []
        
        dollar_vol = feat.get("dollar_vol_20d") or 0
        if dollar_vol < self.risk_config.low_liquidity_threshold:
            flags.append("LOW_LIQUIDITY")
        
        gap_pct = feat.get("gap_pct") or 0
        if abs(gap_pct) > self.risk_config.huge_gap_threshold:
            flags.append("HUGE_GAP")
        
        ret_1d = feat.get("ret_1d") or 0
        if abs(ret_1d) > self.risk_config.extreme_1d_move_threshold:
            flags.append("EXTREME_1D_MOVE")
        
        # Check for missing features
        required = ["ret_1d", "ret_5d", "ret_20d", "vol_20d"]
        if any(feat.get(f) is None for f in required):
            flags.append("DATA_MISSING")
        
        return flags
    
    def _compute_confidence(
        self,
        feat: Dict[str, Any],
        risk_flags: List[str]
    ) -> float:
        """Compute confidence score (0-1)"""
        confidence = 1.0
        
        # Reduce confidence for risk flags
        confidence -= len(risk_flags) * 0.1
        
        # Reduce for missing features
        missing = sum(1 for v in feat.values() if v is None)
        confidence -= missing * 0.05
        
        return max(0.1, min(1.0, confidence))


class PredictionPipeline:
    """
    Pipeline for generating predictions.
    """
    
    def __init__(self, session: Session):
        self.session = session
        self.config = get_config()
    
    def get_or_create_model(
        self,
        name: str = "BASELINE_V1",
        version: int = 1
    ) -> Model:
        """Get or create model record"""
        model = self.session.query(Model).filter(
            Model.name == name,
            Model.version == version
        ).first()
        
        if model:
            return model
        
        # Create default baseline model
        model_config = self.config.model.config
        model = Model(
            model_id=uuid.uuid4(),
            name=name,
            version=version,
            model_type="rule_score",
            train_window=self.config.model.train_window,
            config=model_config,
            model_hash=compute_model_hash(model_config),
            is_active=True,
        )
        self.session.add(model)
        self.session.flush()
        
        return model
    
    def run(
        self,
        snapshot_id: str,
        feature_set_id: str,
        task: str = "weekly_predict",
        horizon: int = 5,
        model_name: str = "BASELINE_V1",
        model_version: int = 1
    ) -> Tuple[PredictionRun, List[Prediction], List[str]]:
        """
        Run prediction pipeline.
        
        Returns: (prediction_run, predictions, warnings)
        """
        warnings = []
        
        # Get snapshot
        snapshot = self.session.query(Snapshot).filter(
            Snapshot.snapshot_id == snapshot_id
        ).first()
        
        if not snapshot:
            raise ValueError(f"Snapshot not found: {snapshot_id}")
        
        # Get model
        model = self.get_or_create_model(model_name, model_version)
        
        # Compute run hash
        run_hash = compute_prediction_run_hash(
            snapshot_hash=snapshot.snapshot_hash,
            model_hash=model.model_hash,
            params={"task": task, "horizon": horizon},
        )
        
        # Check for existing run
        existing = self.session.query(PredictionRun).filter(
            PredictionRun.run_hash == run_hash
        ).first()
        
        if existing:
            warnings.append("Prediction run already exists, returning existing")
            predictions = self.session.query(Prediction).filter(
                Prediction.prediction_run_id == existing.prediction_run_id
            ).all()
            return existing, predictions, warnings
        
        # Create prediction run
        prediction_run = PredictionRun(
            prediction_run_id=uuid.uuid4(),
            snapshot_id=snapshot_id,
            feature_set_id=feature_set_id,
            model_id=model.model_id,
            horizon_trading_days=horizon,
            task=task,
            status="started",
            params={"task": task, "horizon": horizon},
            run_hash=run_hash,
        )
        self.session.add(prediction_run)
        self.session.flush()
        
        try:
            # Load features
            features_rows = self.session.query(Features).filter(
                Features.snapshot_id == snapshot_id,
                Features.feature_set_id == feature_set_id
            ).all()
            
            if not features_rows:
                raise ValueError("No features found for snapshot")
            
            features_dict = {f.symbol: f.features for f in features_rows}
            
            # Get SPY features for benchmark comparison
            spy_features = features_dict.get("SPY")
            
            # Run model
            model_impl = RuleScoreModel()
            results = model_impl.predict(features_dict, spy_features)
            
            # Store predictions
            predictions = []
            for result in results:
                pred = Prediction(
                    prediction_run_id=prediction_run.prediction_run_id,
                    symbol=result.symbol,
                    score=result.score,
                    p_beat_spy=result.p_beat_spy,
                    exp_return=result.exp_return,
                    exp_vol=result.exp_vol,
                    confidence=result.confidence,
                    risk_flags=result.risk_flags,
                    top_features=result.top_features,
                )
                self.session.add(pred)
                predictions.append(pred)
            
            prediction_run.status = "succeeded"
            self.session.flush()
            
            logger.info(f"Created {len(predictions)} predictions")
            
            return prediction_run, predictions, warnings
            
        except Exception as e:
            prediction_run.status = "failed"
            prediction_run.error = str(e)
            self.session.flush()
            raise
