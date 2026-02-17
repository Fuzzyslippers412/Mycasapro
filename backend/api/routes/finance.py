"""
Finance API Routes
Endpoints for Finance agent (Mamadou) including Polymarket BTC 15m skill
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/finance", tags=["finance"])


class PolymarketAnalysisRequest(BaseModel):
    """Request for Polymarket BTC 15m direction analysis"""
    market_data: Optional[Dict[str, Any]] = None
    market_url: Optional[str] = None
    bankroll_usd: float = 5000


class PolymarketQuickCallRequest(BaseModel):
    """Request for quick UP/DOWN/NO_TRADE call"""
    market_data: Dict[str, Any]
    bankroll_usd: float = 5000


@router.post("/polymarket/analyze")
async def analyze_polymarket_direction(request: PolymarketAnalysisRequest) -> Dict[str, Any]:
    """
    Analyze Polymarket BTC 15m direction

    Returns detailed PolymarketDirectionOutput with:
    - call (UP/DOWN/NO_TRADE)
    - confidence (HIGH/MEDIUM/LOW)
    - probability up
    - 6+ detailed reasons
    - key signals
    - action intents
    """
    try:
        from agents.finance import FinanceAgent

        agent = FinanceAgent()

        result = await agent.analyze_polymarket_direction(
            market_data=request.market_data,
            market_url=request.market_url
        )

        if "error" in result:
            raise HTTPException(status_code=500, detail=result["message"])

        logger.info(f"Polymarket analysis complete: {result.get('call', 'UNKNOWN')}")

        return result

    except Exception as e:
        logger.error(f"Polymarket analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/polymarket/quick-call")
async def quick_polymarket_call(request: PolymarketQuickCallRequest) -> Dict[str, str]:
    """
    Quick UP/DOWN/NO_TRADE call without detailed analysis

    Returns simple string call
    """
    try:
        from agents.finance import FinanceAgent

        agent = FinanceAgent()

        call = await agent.quick_polymarket_call(
            market_data=request.market_data
        )

        logger.info(f"Quick call complete: {call}")

        return {"call": call}

    except Exception as e:
        logger.error(f"Quick call failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/polymarket/status")
async def get_polymarket_skill_status() -> Dict[str, Any]:
    """
    Check if Polymarket BTC 15m skill is available

    Returns skill status and metadata
    """
    try:
        from agents.finance import POLYMARKET_SKILL_AVAILABLE

        if POLYMARKET_SKILL_AVAILABLE:
            from skills.polymarket_btc_15m.skill_interface import get_skill_status
            status = get_skill_status()
            return {
                "available": True,
                **status
            }
        else:
            return {
                "available": False,
                "message": "Skill not installed or import failed"
            }

    except Exception as e:
        logger.error(f"Status check failed: {e}", exc_info=True)
        return {
            "available": False,
            "error": str(e)
        }
