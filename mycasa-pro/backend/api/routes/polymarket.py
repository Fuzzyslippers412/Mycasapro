"""
Polymarket API Routes
Handles trade tracking, CSV uploads, and analysis
"""
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/polymarket", tags=["polymarket"])


class TradeStatsResponse(BaseModel):
    """Trade statistics response"""
    stats: Dict[str, Any]
    recommendations: Dict[str, Any]


@router.post("/upload-csv")
async def upload_trade_history(file: UploadFile = File(...)) -> TradeStatsResponse:
    """
    Upload Polymarket CSV export and get trade statistics

    Expected CSV format:
    "marketName","action","usdcAmount","tokenAmount","tokenName","timestamp","hash"
    """
    try:
        from skills.polymarket_btc_15m.trade_tracker import TradeTracker

        # Read CSV content
        content = await file.read()
        csv_text = content.decode('utf-8')

        # Parse and analyze
        tracker = TradeTracker()
        trades = tracker.parse_csv(csv_text)

        if not trades:
            raise HTTPException(status_code=400, detail="No valid trades found in CSV")

        stats = tracker.calculate_stats(trades)
        recommendations = tracker.generate_recommendations(stats)

        logger.info(f"Analyzed {len(trades)} trades - Win rate: {stats.win_rate:.1f}%")

        return TradeStatsResponse(
            stats=stats.model_dump(),
            recommendations=recommendations
        )

    except Exception as e:
        logger.error(f"CSV upload failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
