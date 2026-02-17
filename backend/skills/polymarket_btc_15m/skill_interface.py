"""
Skill Interface for Finance Agent (Mamadou)
Simple entry point for "up or down?" queries
"""
from typing import Dict, Any, Optional
import logging

from .orchestrator import PolymarketBTC15mOrchestrator
from .schemas import PolymarketDirectionOutput

logger = logging.getLogger(__name__)


# Singleton instance for efficiency
_orchestrator: Optional[PolymarketBTC15mOrchestrator] = None


def get_orchestrator(bankroll_usd: float = 5000) -> PolymarketBTC15mOrchestrator:
    """
    Get singleton orchestrator instance

    Args:
        bankroll_usd: Available bankroll for risk calculations

    Returns:
        PolymarketBTC15mOrchestrator instance
    """
    global _orchestrator

    if _orchestrator is None:
        _orchestrator = PolymarketBTC15mOrchestrator(bankroll_usd=bankroll_usd)
        logger.info(f"Initialized Polymarket BTC 15m orchestrator with ${bankroll_usd:,.2f} bankroll")

    return _orchestrator


async def analyze_btc_15m_direction(
    market_url: Optional[str] = None,
    market_data: Optional[Dict[str, Any]] = None,
    bankroll_usd: float = 5000
) -> PolymarketDirectionOutput:
    """
    Main entry point for BTC 15m direction analysis

    This is what the Finance agent (Mamadou) calls when asked "up or down?"

    Args:
        market_url: Polymarket market URL (for scraping)
        market_data: Pre-scraped market data (bypasses scraping)
        bankroll_usd: Available bankroll for risk calculations

    Returns:
        PolymarketDirectionOutput with call, confidence, reasons, and intents

    Raises:
        ValueError: If neither market_url nor market_data provided

    Example:
        >>> # From Finance agent (Mamadou)
        >>> result = await analyze_btc_15m_direction(
        ...     market_data=scraped_market_data,
        ...     bankroll_usd=5000
        ... )
        >>> print(f"CALL: {result.call.value}")
        >>> print(f"CONFIDENCE: {result.confidence.value}")
        >>> for reason in result.reasons:
        ...     print(f"  {reason}")
    """
    orchestrator = get_orchestrator(bankroll_usd=bankroll_usd)

    try:
        result = await orchestrator.analyze_market(
            market_url=market_url,
            market_data=market_data
        )

        logger.info(
            f"BTC 15m direction analysis complete: "
            f"call={result.call.value}, "
            f"confidence={result.confidence.value}, "
            f"prob_up={result.prob_up:.1%}"
        )

        return result

    except Exception as e:
        logger.error(f"BTC 15m direction analysis failed: {e}", exc_info=True)
        raise


async def quick_call(
    market_data: Dict[str, Any],
    bankroll_usd: float = 5000
) -> str:
    """
    Quick direction call returning just "UP", "DOWN", or "NO_TRADE"

    Args:
        market_data: Pre-scraped market data
        bankroll_usd: Available bankroll

    Returns:
        Simple string: "UP", "DOWN", or "NO_TRADE"

    Example:
        >>> call = await quick_call(market_data)
        >>> print(call)  # "UP"
    """
    orchestrator = get_orchestrator(bankroll_usd=bankroll_usd)
    return await orchestrator.quick_call(market_data)


def get_skill_status() -> Dict[str, Any]:
    """
    Get skill status and health check

    Returns:
        Status dictionary with pipeline health

    Example:
        >>> status = get_skill_status()
        >>> print(status["status"])  # "ready"
    """
    if _orchestrator is None:
        return {
            "status": "not_initialized",
            "message": "Call analyze_btc_15m_direction() to initialize",
        }

    return _orchestrator.get_status()


# Convenience alias for the Finance agent
polymarket_btc_15m = analyze_btc_15m_direction
