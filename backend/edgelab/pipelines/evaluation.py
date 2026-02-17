"""
Evaluation Pipeline for Edge Lab

Walk-forward evaluation of predictions.
Computes metrics like hit rate, average return, rank correlation.
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import logging
import math

from sqlalchemy.orm import Session
from sqlalchemy import func

from ..db.models import (
    PredictionRun, Prediction, EvaluationRun,
    Snapshot, SnapshotBarDaily
)
from ..utils.hashing import compute_evaluation_hash

logger = logging.getLogger(__name__)


@dataclass
class EvaluationMetrics:
    """Evaluation metrics for a prediction run"""
    hit_rate: float  # % of positive predictions that were correct
    avg_realized_return: float  # Average return of top N predictions
    avg_predicted_return: Optional[float]  # Average predicted return
    rank_correlation: float  # Spearman correlation between score and realized
    top_n_return: float  # Return of top N stocks
    bottom_n_return: float  # Return of bottom N stocks
    benchmark_return: float  # SPY return over horizon
    calibration_bins: Optional[Dict[str, float]]  # Calibration for p_beat_spy
    total_evaluated: int
    top_n: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "hit_rate": self.hit_rate,
            "avg_realized_return": self.avg_realized_return,
            "avg_predicted_return": self.avg_predicted_return,
            "rank_correlation": self.rank_correlation,
            "top_n_return": self.top_n_return,
            "bottom_n_return": self.bottom_n_return,
            "benchmark_return": self.benchmark_return,
            "calibration_bins": self.calibration_bins,
            "total_evaluated": self.total_evaluated,
            "top_n": self.top_n,
        }


class EvaluationPipeline:
    """
    Pipeline for evaluating predictions.
    
    Uses walk-forward methodology to ensure point-in-time correctness.
    """
    
    def __init__(self, session: Session):
        self.session = session
    
    def run(
        self,
        prediction_run_id: str,
        evaluated_at: Optional[datetime] = None,
        top_n: int = 20
    ) -> Tuple[EvaluationRun, EvaluationMetrics, List[str]]:
        """
        Evaluate a prediction run.
        
        Returns: (evaluation_run, metrics, warnings)
        """
        warnings = []
        evaluated_at = evaluated_at or datetime.now()
        
        # Get prediction run
        pred_run = self.session.query(PredictionRun).filter(
            PredictionRun.prediction_run_id == prediction_run_id
        ).first()
        
        if not pred_run:
            raise ValueError(f"Prediction run not found: {prediction_run_id}")
        
        # Compute evaluation hash
        eval_hash = compute_evaluation_hash(prediction_run_id, evaluated_at)
        
        # Check for existing evaluation
        existing = self.session.query(EvaluationRun).filter(
            EvaluationRun.run_hash == eval_hash
        ).first()
        
        if existing and existing.status == "succeeded":
            warnings.append("Evaluation already exists")
            metrics = EvaluationMetrics(**existing.metrics)
            return existing, metrics, warnings
        
        # Create evaluation run
        eval_run = EvaluationRun(
            evaluation_run_id=uuid.uuid4(),
            prediction_run_id=prediction_run_id,
            evaluated_at=evaluated_at,
            status="started",
            run_hash=eval_hash,
        )
        self.session.add(eval_run)
        self.session.flush()
        
        try:
            # Get predictions
            predictions = self.session.query(Prediction).filter(
                Prediction.prediction_run_id == prediction_run_id
            ).order_by(Prediction.score.desc()).all()
            
            if not predictions:
                raise ValueError("No predictions found")
            
            # Get snapshot info
            snapshot = self.session.query(Snapshot).filter(
                Snapshot.snapshot_id == pred_run.snapshot_id
            ).first()
            
            # Calculate evaluation period
            horizon_days = pred_run.horizon_trading_days
            eval_start = snapshot.as_of.date()
            eval_end = eval_start + timedelta(days=horizon_days * 2)  # Buffer for weekends
            
            # Get realized returns
            realized = self._get_realized_returns(
                snapshot.snapshot_id,
                [p.symbol for p in predictions],
                eval_start,
                eval_end,
                horizon_days
            )
            
            if not realized:
                warnings.append("Could not compute realized returns - insufficient data")
                eval_run.status = "failed"
                eval_run.error = "Insufficient data for evaluation"
                eval_run.metrics = {}
                self.session.flush()
                return eval_run, None, warnings
            
            # Compute metrics
            metrics = self._compute_metrics(predictions, realized, top_n)
            
            # Store results
            eval_run.status = "succeeded"
            eval_run.metrics = metrics.to_dict()
            self.session.flush()
            
            logger.info(f"Evaluation complete: hit_rate={metrics.hit_rate:.2%}")
            
            return eval_run, metrics, warnings
            
        except Exception as e:
            eval_run.status = "failed"
            eval_run.error = str(e)
            self.session.flush()
            raise
    
    def _get_realized_returns(
        self,
        snapshot_id: str,
        symbols: List[str],
        start_date,
        end_date,
        horizon_days: int
    ) -> Dict[str, float]:
        """
        Get realized returns for symbols over the horizon.
        
        Uses data from the snapshot for point-in-time correctness.
        """
        realized = {}
        
        for symbol in symbols:
            # Get bars for this symbol
            bars = self.session.query(SnapshotBarDaily).filter(
                SnapshotBarDaily.snapshot_id == snapshot_id,
                SnapshotBarDaily.symbol == symbol,
                SnapshotBarDaily.date >= start_date,
                SnapshotBarDaily.date <= end_date
            ).order_by(SnapshotBarDaily.date).all()
            
            if len(bars) < horizon_days + 1:
                continue
            
            # Start price is the first bar after prediction
            start_price = float(bars[0].c)
            
            # End price is horizon_days trading days later
            end_idx = min(horizon_days, len(bars) - 1)
            end_price = float(bars[end_idx].c)
            
            if start_price > 0:
                realized[symbol] = (end_price / start_price) - 1
        
        return realized
    
    def _compute_metrics(
        self,
        predictions: List[Prediction],
        realized: Dict[str, float],
        top_n: int
    ) -> EvaluationMetrics:
        """Compute evaluation metrics"""
        
        # Filter to predictions with realized returns
        valid = [p for p in predictions if p.symbol in realized]
        
        if not valid:
            return EvaluationMetrics(
                hit_rate=0,
                avg_realized_return=0,
                avg_predicted_return=None,
                rank_correlation=0,
                top_n_return=0,
                bottom_n_return=0,
                benchmark_return=0,
                calibration_bins=None,
                total_evaluated=0,
                top_n=top_n,
            )
        
        # Separate top and bottom N
        top_preds = valid[:top_n]
        bottom_preds = valid[-top_n:] if len(valid) > top_n else []
        
        # Compute hit rate (positive score -> positive return)
        hits = sum(
            1 for p in valid
            if (p.score > 0 and realized[p.symbol] > 0) or
               (p.score <= 0 and realized[p.symbol] <= 0)
        )
        hit_rate = hits / len(valid)
        
        # Average returns
        top_returns = [realized[p.symbol] for p in top_preds]
        bottom_returns = [realized[p.symbol] for p in bottom_preds] if bottom_preds else [0]
        all_returns = [realized[p.symbol] for p in valid]
        
        avg_realized = sum(all_returns) / len(all_returns)
        top_n_return = sum(top_returns) / len(top_returns) if top_returns else 0
        bottom_n_return = sum(bottom_returns) / len(bottom_returns) if bottom_returns else 0
        
        # Predicted return average
        exp_returns = [float(p.exp_return) for p in valid if p.exp_return is not None]
        avg_predicted = sum(exp_returns) / len(exp_returns) if exp_returns else None
        
        # Rank correlation (Spearman)
        rank_corr = self._spearman_correlation(
            [float(p.score) for p in valid],
            [realized[p.symbol] for p in valid]
        )
        
        # Benchmark return (SPY)
        benchmark_return = realized.get("SPY", 0)
        
        # Calibration for p_beat_spy
        calibration = self._compute_calibration(valid, realized, benchmark_return)
        
        return EvaluationMetrics(
            hit_rate=hit_rate,
            avg_realized_return=avg_realized,
            avg_predicted_return=avg_predicted,
            rank_correlation=rank_corr,
            top_n_return=top_n_return,
            bottom_n_return=bottom_n_return,
            benchmark_return=benchmark_return,
            calibration_bins=calibration,
            total_evaluated=len(valid),
            top_n=top_n,
        )
    
    def _spearman_correlation(
        self,
        x: List[float],
        y: List[float]
    ) -> float:
        """Compute Spearman rank correlation"""
        if len(x) != len(y) or len(x) < 2:
            return 0
        
        n = len(x)
        
        # Rank the values
        x_ranked = self._rank(x)
        y_ranked = self._rank(y)
        
        # Compute correlation on ranks
        d_squared = sum((x_ranked[i] - y_ranked[i]) ** 2 for i in range(n))
        
        return 1 - (6 * d_squared) / (n * (n ** 2 - 1))
    
    def _rank(self, values: List[float]) -> List[float]:
        """Compute ranks (average rank for ties)"""
        indexed = [(v, i) for i, v in enumerate(values)]
        sorted_indexed = sorted(indexed, key=lambda x: x[0])
        
        ranks = [0.0] * len(values)
        i = 0
        while i < len(sorted_indexed):
            j = i
            while j < len(sorted_indexed) and sorted_indexed[j][0] == sorted_indexed[i][0]:
                j += 1
            avg_rank = (i + j - 1) / 2 + 1
            for k in range(i, j):
                ranks[sorted_indexed[k][1]] = avg_rank
            i = j
        
        return ranks
    
    def _compute_calibration(
        self,
        predictions: List[Prediction],
        realized: Dict[str, float],
        benchmark_return: float
    ) -> Optional[Dict[str, float]]:
        """Compute calibration bins for p_beat_spy"""
        
        preds_with_prob = [
            (p, realized[p.symbol])
            for p in predictions
            if p.p_beat_spy is not None
        ]
        
        if not preds_with_prob:
            return None
        
        # Create bins: 0-0.2, 0.2-0.4, 0.4-0.6, 0.6-0.8, 0.8-1.0
        bins = {
            "0.0-0.2": {"count": 0, "beat": 0},
            "0.2-0.4": {"count": 0, "beat": 0},
            "0.4-0.6": {"count": 0, "beat": 0},
            "0.6-0.8": {"count": 0, "beat": 0},
            "0.8-1.0": {"count": 0, "beat": 0},
        }
        
        for p, ret in preds_with_prob:
            prob = float(p.p_beat_spy)
            beat = 1 if ret > benchmark_return else 0
            
            if prob < 0.2:
                bins["0.0-0.2"]["count"] += 1
                bins["0.0-0.2"]["beat"] += beat
            elif prob < 0.4:
                bins["0.2-0.4"]["count"] += 1
                bins["0.2-0.4"]["beat"] += beat
            elif prob < 0.6:
                bins["0.4-0.6"]["count"] += 1
                bins["0.4-0.6"]["beat"] += beat
            elif prob < 0.8:
                bins["0.6-0.8"]["count"] += 1
                bins["0.6-0.8"]["beat"] += beat
            else:
                bins["0.8-1.0"]["count"] += 1
                bins["0.8-1.0"]["beat"] += beat
        
        # Convert to actual rates
        calibration = {}
        for bin_name, data in bins.items():
            if data["count"] > 0:
                calibration[bin_name] = data["beat"] / data["count"]
            else:
                calibration[bin_name] = None
        
        return calibration
