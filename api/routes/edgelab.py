"""
Edge Lab API Routes

FastAPI endpoints for the Edge Lab financial prediction system.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID
import logging

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel

from backend.edgelab.db.session import get_session
from backend.edgelab.db.models import (
    Snapshot, PredictionRun, Prediction, EvaluationRun, Source, UniversePolicy
)
from backend.edgelab.adapters import AdapterRegistry
from backend.edgelab.pipelines import SnapshotPipeline, FeatureEngine, PredictionPipeline, EvaluationPipeline
from backend.edgelab.config import get_config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/edgelab", tags=["edgelab"])


# ============ Request/Response Models ============

class DailyScanRequest(BaseModel):
    as_of: datetime
    policy: str = "US_LIQUID_V1"
    adapter: Optional[str] = None
    history_days: int = 252


class WeeklyPredictRequest(BaseModel):
    as_of: datetime
    policy: str = "US_LIQUID_V1"
    horizon: int = 5
    adapter: Optional[str] = None


class EvaluateRequest(BaseModel):
    prediction_run_id: UUID
    top_n: int = 20


class PredictionResult(BaseModel):
    symbol: str
    score: float
    confidence: float
    risk_flags: List[str]
    p_beat_spy: Optional[float] = None
    exp_return: Optional[float] = None
    exp_vol: Optional[float] = None
    top_features: Optional[List[Dict[str, Any]]] = None


class ScanResponse(BaseModel):
    ok: bool
    ids: Dict[str, str]
    warnings: List[str]
    audit: Dict[str, Any]
    predictions: List[PredictionResult]


class EvaluationResponse(BaseModel):
    ok: bool
    evaluation_run_id: str
    prediction_run_id: str
    metrics: Dict[str, Any]
    warnings: List[str]


class AuditResponse(BaseModel):
    snapshot_id: str
    snapshot_hash: str
    as_of: datetime
    policy: Dict[str, Any]
    sources: List[str]
    symbols_count: int
    bars_count: int
    created_at: datetime


# ============ Helper Functions ============

def _run_scan_pipeline(
    as_of: datetime,
    policy: str,
    adapter_name: str,
    history_days: int,
    task: str,
    horizon: int = 5,
) -> ScanResponse:
    """Run the full scan pipeline and return results"""
    
    config = get_config()
    adapter_name = adapter_name or config.default_adapter
    
    with get_session() as session:
        try:
            # Get adapter
            data_adapter = AdapterRegistry.get(adapter_name)
            
            # Run snapshot pipeline
            snapshot_pipeline = SnapshotPipeline(session, data_adapter)
            snapshot, snap_warnings = snapshot_pipeline.run(
                as_of=as_of,
                policy_name=policy,
                history_days=history_days
            )
            
            # Run feature engine
            feature_engine = FeatureEngine(session)
            feature_set_id, feature_count = feature_engine.run(snapshot.snapshot_id)
            
            # Run prediction
            pred_pipeline = PredictionPipeline(session)
            pred_run, predictions, pred_warnings = pred_pipeline.run(
                snapshot_id=snapshot.snapshot_id,
                feature_set_id=feature_set_id,
                task=task,
                horizon=horizon
            )
            
            session.commit()
            
            return ScanResponse(
                ok=True,
                ids={
                    "snapshot_id": str(snapshot.snapshot_id),
                    "prediction_run_id": str(pred_run.prediction_run_id),
                },
                warnings=snap_warnings + pred_warnings,
                audit={
                    "as_of": as_of.isoformat(),
                    "snapshot_hash": snapshot.snapshot_hash,
                    "policy": policy,
                    "adapter": adapter_name,
                },
                predictions=[
                    PredictionResult(
                        symbol=p.symbol,
                        score=float(p.score),
                        confidence=float(p.confidence),
                        risk_flags=p.risk_flags or [],
                        p_beat_spy=float(p.p_beat_spy) if p.p_beat_spy else None,
                        exp_return=float(p.exp_return) if p.exp_return else None,
                        exp_vol=float(p.exp_vol) if p.exp_vol else None,
                        top_features=p.top_features,
                    )
                    for p in predictions[:20]
                ],
            )
            
        except Exception as e:
            session.rollback()
            logger.error(f"Pipeline error: {e}")
            raise HTTPException(status_code=500, detail=str(e))


# ============ API Endpoints ============

@router.get("/status")
async def get_status():
    """Get Edge Lab system status"""
    config = get_config()
    adapters = AdapterRegistry.list_adapters()
    
    with get_session() as session:
        # Count records
        snapshot_count = session.query(Snapshot).count()
        prediction_count = session.query(PredictionRun).count()
        
        # Get latest snapshot
        latest = session.query(Snapshot).order_by(Snapshot.created_at.desc()).first()
        
    return {
        "status": "operational",
        "adapters": adapters,
        "default_adapter": config.default_adapter,
        "database": {
            "snapshots": snapshot_count,
            "prediction_runs": prediction_count,
        },
        "latest_snapshot": {
            "id": str(latest.snapshot_id) if latest else None,
            "as_of": latest.as_of.isoformat() if latest else None,
            "hash": latest.snapshot_hash[:16] if latest else None,
        } if latest else None,
    }


@router.post("/daily_scan", response_model=ScanResponse)
async def daily_scan(request: DailyScanRequest):
    """
    Run daily scan pipeline.
    
    Creates snapshot, computes features, and generates daily scan predictions.
    """
    return _run_scan_pipeline(
        as_of=request.as_of,
        policy=request.policy,
        adapter_name=request.adapter,
        history_days=request.history_days,
        task="daily_scan",
        horizon=1,
    )


@router.post("/weekly_predict", response_model=ScanResponse)
async def weekly_predict(request: WeeklyPredictRequest):
    """
    Run weekly prediction pipeline.
    
    Creates snapshot, computes features, and generates weekly predictions.
    """
    return _run_scan_pipeline(
        as_of=request.as_of,
        policy=request.policy,
        adapter_name=request.adapter,
        history_days=252,
        task="weekly_predict",
        horizon=request.horizon,
    )


@router.post("/evaluate", response_model=EvaluationResponse)
async def evaluate(request: EvaluateRequest):
    """
    Evaluate a prediction run.
    
    Computes metrics like hit rate, average return, and calibration.
    """
    with get_session() as session:
        try:
            eval_pipeline = EvaluationPipeline(session)
            eval_run, metrics, warnings = eval_pipeline.run(
                prediction_run_id=request.prediction_run_id,
                top_n=request.top_n
            )
            
            session.commit()
            
            if metrics:
                return EvaluationResponse(
                    ok=True,
                    evaluation_run_id=str(eval_run.evaluation_run_id),
                    prediction_run_id=str(request.prediction_run_id),
                    metrics=metrics.to_dict() if hasattr(metrics, 'to_dict') else metrics,
                    warnings=warnings,
                )
            else:
                raise HTTPException(
                    status_code=400, 
                    detail="Evaluation failed - insufficient data"
                )
                
        except Exception as e:
            session.rollback()
            logger.error(f"Evaluation error: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/watchlist/{prediction_run_id}")
async def get_watchlist(
    prediction_run_id: UUID,
    limit: int = Query(20, ge=1, le=100),
):
    """Get predictions for a specific run"""
    with get_session() as session:
        pred_run = session.query(PredictionRun).filter(
            PredictionRun.prediction_run_id == prediction_run_id
        ).first()
        
        if not pred_run:
            raise HTTPException(status_code=404, detail="Prediction run not found")
        
        predictions = session.query(Prediction).filter(
            Prediction.prediction_run_id == prediction_run_id
        ).order_by(Prediction.score.desc()).limit(limit).all()
        
        return {
            "prediction_run_id": str(prediction_run_id),
            "task": pred_run.task,
            "horizon": pred_run.horizon_trading_days,
            "created_at": pred_run.created_at.isoformat(),
            "candidates": [
                {
                    "rank": i,
                    "symbol": p.symbol,
                    "score": float(p.score),
                    "confidence": float(p.confidence),
                    "risk_flags": p.risk_flags or [],
                    "p_beat_spy": float(p.p_beat_spy) if p.p_beat_spy else None,
                    "exp_return": float(p.exp_return) if p.exp_return else None,
                }
                for i, p in enumerate(predictions, 1)
            ],
        }


@router.get("/audit/{snapshot_id}", response_model=AuditResponse)
async def get_audit(snapshot_id: UUID):
    """Get audit trail for a snapshot"""
    with get_session() as session:
        snapshot = session.query(Snapshot).filter(
            Snapshot.snapshot_id == snapshot_id
        ).first()
        
        if not snapshot:
            raise HTTPException(status_code=404, detail="Snapshot not found")
        
        # Get source info
        ingest = snapshot.ingest_run
        source = ingest.source if ingest else None
        
        # Count data
        symbols_count = len(snapshot.symbols)
        bars_count = len(snapshot.bars)
        
        # Get policy
        policy = snapshot.universe_policy
        policy_info = {
            "name": policy.name,
            "version": policy.version,
            "rules": policy.rules,
            "hash": policy.policy_hash[:16],
        } if policy else {}
        
        return AuditResponse(
            snapshot_id=str(snapshot.snapshot_id),
            snapshot_hash=snapshot.snapshot_hash,
            as_of=snapshot.as_of,
            policy=policy_info,
            sources=[source.name] if source else [],
            symbols_count=symbols_count,
            bars_count=bars_count,
            created_at=snapshot.created_at,
        )


@router.get("/snapshots")
async def list_snapshots(
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
):
    """List recent snapshots"""
    with get_session() as session:
        total = session.query(Snapshot).count()
        snapshots = session.query(Snapshot).order_by(
            Snapshot.created_at.desc()
        ).offset(offset).limit(limit).all()
        
        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "snapshots": [
                {
                    "id": str(s.snapshot_id),
                    "as_of": s.as_of.isoformat(),
                    "hash": s.snapshot_hash[:16],
                    "stats": s.stats,
                    "created_at": s.created_at.isoformat(),
                }
                for s in snapshots
            ],
        }


@router.get("/prediction_runs")
async def list_prediction_runs(
    limit: int = Query(10, ge=1, le=50),
    task: Optional[str] = None,
):
    """List recent prediction runs"""
    with get_session() as session:
        query = session.query(PredictionRun)
        
        if task:
            query = query.filter(PredictionRun.task == task)
        
        runs = query.order_by(PredictionRun.created_at.desc()).limit(limit).all()
        
        return {
            "runs": [
                {
                    "id": str(r.prediction_run_id),
                    "snapshot_id": str(r.snapshot_id),
                    "task": r.task,
                    "horizon": r.horizon_trading_days,
                    "status": r.status,
                    "created_at": r.created_at.isoformat(),
                }
                for r in runs
            ],
        }


@router.get("/adapters")
async def list_adapters():
    """List available data adapters"""
    return {
        "adapters": AdapterRegistry.list_adapters(),
        "default": get_config().default_adapter,
    }


# ════════════════════════════════════════════════════════════════════════════
# POLYMARKET BROWSER RELAY ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════

@router.get("/browser/polymarket-cached")
async def get_cached_polymarket_data():
    """
    Get the most recently cached Polymarket data from Galidima.
    """
    import json
    from pathlib import Path
    
    cache_file = Path.home() / "clawd" / "apps" / "mycasa-pro" / "data" / "polymarket_latest.json"
    
    try:
        if cache_file.exists():
            with open(cache_file) as f:
                data = json.load(f)
            return {"success": True, "data": data, "source": "cache"}
        else:
            return {"success": False, "error": "No cached data", "code": "NO_CACHE"}
    except Exception as e:
        return {"success": False, "error": str(e), "code": "READ_ERROR"}


# ════════════════════════════════════════════════════════════════════════════
# PREDICTION TRACKING
# ════════════════════════════════════════════════════════════════════════════

@router.get("/predictions/history")
async def get_prediction_history():
    """Get prediction history and accuracy stats."""
    import json
    from pathlib import Path
    
    history_file = Path.home() / "clawd" / "apps" / "mycasa-pro" / "data" / "prediction_history.json"
    
    try:
        if history_file.exists():
            with open(history_file) as f:
                return {"success": True, "data": json.load(f)}
        else:
            return {"success": True, "data": {"predictions": [], "stats": {"total": 0, "correct": 0, "accuracy_pct": None}}}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/predictions/record")
async def record_prediction(
    market_id: str,
    market_title: str,
    call: str,  # UP, DOWN, NO_TRADE
    confidence: str,  # HIGH, MEDIUM, LOW
    edge_score: float,
    btc_price_at_call: float,
    up_odds: float,
    down_odds: float,
    time_to_resolution_sec: int
):
    """Record a new prediction."""
    import json
    from pathlib import Path
    from datetime import datetime
    
    history_file = Path.home() / "clawd" / "apps" / "mycasa-pro" / "data" / "prediction_history.json"
    
    try:
        if history_file.exists():
            with open(history_file) as f:
                data = json.load(f)
        else:
            data = {"predictions": [], "stats": {"total": 0, "correct": 0, "incorrect": 0, "pending": 0, "accuracy_pct": None, "streak": 0, "best_streak": 0}}
        
        prediction = {
            "id": f"pred_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            "market_id": market_id,
            "market_title": market_title,
            "call": call,
            "confidence": confidence,
            "edge_score": edge_score,
            "btc_price_at_call": btc_price_at_call,
            "up_odds": up_odds,
            "down_odds": down_odds,
            "time_to_resolution_sec": time_to_resolution_sec,
            "timestamp": datetime.utcnow().isoformat(),
            "outcome": None,  # Will be filled when resolved
            "correct": None,
            "resolved_at": None
        }
        
        data["predictions"].insert(0, prediction)
        data["stats"]["total"] += 1
        data["stats"]["pending"] += 1
        data["last_updated"] = datetime.utcnow().isoformat()
        
        with open(history_file, "w") as f:
            json.dump(data, f, indent=2)
        
        return {"success": True, "prediction_id": prediction["id"]}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/predictions/resolve")
async def resolve_prediction(
    prediction_id: str,
    outcome: str  # UP or DOWN (actual result)
):
    """Resolve a prediction and update accuracy stats."""
    import json
    from pathlib import Path
    from datetime import datetime
    
    history_file = Path.home() / "clawd" / "apps" / "mycasa-pro" / "data" / "prediction_history.json"
    
    try:
        with open(history_file) as f:
            data = json.load(f)
        
        # Find and update the prediction
        for pred in data["predictions"]:
            if pred["id"] == prediction_id and pred["outcome"] is None:
                pred["outcome"] = outcome
                pred["resolved_at"] = datetime.utcnow().isoformat()
                
                # Check if correct (NO_TRADE predictions are not scored)
                if pred["call"] in ["UP", "DOWN"]:
                    pred["correct"] = pred["call"] == outcome
                    
                    data["stats"]["pending"] -= 1
                    if pred["correct"]:
                        data["stats"]["correct"] += 1
                        data["stats"]["streak"] += 1
                        data["stats"]["best_streak"] = max(data["stats"]["streak"], data["stats"]["best_streak"])
                    else:
                        data["stats"]["incorrect"] += 1
                        data["stats"]["streak"] = 0
                    
                    # Recalculate accuracy
                    scored = data["stats"]["correct"] + data["stats"]["incorrect"]
                    if scored > 0:
                        data["stats"]["accuracy_pct"] = round((data["stats"]["correct"] / scored) * 100, 1)
                else:
                    # NO_TRADE - just mark as resolved
                    data["stats"]["pending"] -= 1
                
                break
        
        data["last_updated"] = datetime.utcnow().isoformat()
        
        with open(history_file, "w") as f:
            json.dump(data, f, indent=2)
        
        return {"success": True, "stats": data["stats"]}
    except Exception as e:
        return {"success": False, "error": str(e)}
