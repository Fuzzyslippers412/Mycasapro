"""
ORCHESTRATOR
Coordinates the sovereign agent pipeline for BTC 15m direction prediction

Pipeline: MARKET_SENSOR → BOOK_ANALYZER → SIGNAL_ENGINE → DECISION_ENGINE → RISK_GATE → EXECUTION_ENGINE

Authority: Orchestration only - delegates to specialist agents
Output: PolymarketDirectionOutput JSON
"""
from typing import Optional, Dict, Any
import logging
from datetime import datetime

from .market_sensor import MarketSensor
from .book_analyzer import BookAnalyzer
from .signal_engine import SignalEngine
from .decision_engine import DecisionEngine
from .risk_gate import RiskGate
from .schemas import PolymarketDirectionOutput, MarketSnapshot

logger = logging.getLogger(__name__)


class PolymarketBTC15mOrchestrator:
    """
    Orchestrates the multi-agent sovereign pipeline

    No direct tool execution - pure coordination
    Follows strict safety protocol with explicit gates
    """

    def __init__(self, bankroll_usd: float = 5000):
        """
        Initialize orchestrator with all specialist agents

        Args:
            bankroll_usd: Available bankroll for risk calculations
        """
        self.name = "ORCHESTRATOR"
        self.bankroll_usd = bankroll_usd

        # Initialize all specialist agents
        self.market_sensor = MarketSensor()
        self.book_analyzer = BookAnalyzer()
        self.signal_engine = SignalEngine()
        self.decision_engine = DecisionEngine()
        self.risk_gate = RiskGate(bankroll_usd=bankroll_usd)

        logger.info(
            f"[{self.name}] Initialized with bankroll=${bankroll_usd:,.2f}"
        )

    async def analyze_market(
        self,
        market_url: Optional[str] = None,
        market_data: Optional[Dict[str, Any]] = None
    ) -> PolymarketDirectionOutput:
        """
        Run full pipeline analysis for BTC 15m direction

        Args:
            market_url: Polymarket URL (for MARKET_SENSOR to scrape)
            market_data: Pre-scraped market data (bypasses MARKET_SENSOR)

        Returns:
            PolymarketDirectionOutput with call, confidence, reasons, intents
        """
        logger.info(f"[{self.name}] Starting pipeline execution")
        start_time = datetime.utcnow()

        try:
            # STAGE 1: MARKET_SENSOR - Extract market state
            logger.info(f"[{self.name}] Stage 1/5: MARKET_SENSOR")

            if market_data:
                # Use pre-provided data (from page scraping tool)
                market_snapshot = MarketSnapshot(**market_data)
            elif market_url:
                # MARKET_SENSOR would scrape the URL
                market_snapshot = await self.market_sensor.sense_market(market_url)
            else:
                raise ValueError("Must provide either market_url or market_data")

            logger.info(
                f"[{self.name}] Market snapshot captured: "
                f"up_spread={market_snapshot.up_spread or 0:.3f}, "
                f"down_spread={market_snapshot.down_spread or 0:.3f}, "
                f"time_remaining={market_snapshot.time_remaining_seconds or 0}s"
            )

            # STAGE 2: BOOK_ANALYZER - Normalize order book
            logger.info(f"[{self.name}] Stage 2/5: BOOK_ANALYZER")
            book_snapshot = await self.book_analyzer.analyze_book(market_snapshot)

            logger.info(
                f"[{self.name}] Book snapshot analyzed: "
                f"up_levels={len(book_snapshot.up_book.bids)}, "
                f"down_levels={len(book_snapshot.down_book.bids)}"
            )

            # STAGE 3: SIGNAL_ENGINE - Compute EDGE_SCORE v1.0
            logger.info(f"[{self.name}] Stage 3/5: SIGNAL_ENGINE")
            signals = await self.signal_engine.compute_signals(
                market_snapshot, book_snapshot
            )

            logger.info(
                f"[{self.name}] Signals computed: "
                f"decision_ready={signals.decision_ready}, "
                f"edge_score={signals.edge_score:.3f}, "
                f"prob_up={signals.prob_up:.3f}"
            )

            # STAGE 4: DECISION_ENGINE - Make call with reasons
            logger.info(f"[{self.name}] Stage 4/5: DECISION_ENGINE")
            decision_output = await self.decision_engine.make_decision(
                market_snapshot, book_snapshot, signals
            )

            logger.info(
                f"[{self.name}] Decision made: "
                f"call={decision_output.call.value}, "
                f"confidence={decision_output.confidence.value}, "
                f"intents={len(decision_output.action_intents)}"
            )

            # STAGE 5: RISK_GATE - Gate action intents
            logger.info(f"[{self.name}] Stage 5/5: RISK_GATE")

            if decision_output.action_intents:
                risk_result = await self.risk_gate.gate_intents(
                    proposed_intents=decision_output.action_intents,
                    signals=signals,
                    call=decision_output.call,
                    confidence=decision_output.confidence
                )

                # Update decision_output with gated intents
                decision_output.action_intents = risk_result.approved_intents

                if risk_result.denied_intents:
                    logger.warning(
                        f"[{self.name}] {len(risk_result.denied_intents)} intents denied by RISK_GATE"
                    )
                    # Add denial reasons to output
                    for denied in risk_result.denied_intents:
                        decision_output.reasons.append(
                            f"⚠️ RISK_GATE denied {denied['tool_name']}: {denied['reason']}"
                        )
            else:
                logger.info(f"[{self.name}] No action intents to gate")

            # PIPELINE COMPLETE
            elapsed_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            logger.info(
                f"[{self.name}] Pipeline complete in {elapsed_ms}ms: "
                f"call={decision_output.call.value}, "
                f"approved_intents={len(decision_output.action_intents)}"
            )

            return decision_output

        except Exception as e:
            logger.error(f"[{self.name}] Pipeline failed: {e}", exc_info=True)
            raise

    async def quick_call(
        self,
        market_data: Dict[str, Any]
    ) -> str:
        """
        Quick direction call for simple queries

        Args:
            market_data: Pre-scraped market data

        Returns:
            Simple string: "UP", "DOWN", or "NO_TRADE"
        """
        result = await self.analyze_market(market_data=market_data)
        return result.call.value

    def get_status(self) -> Dict[str, Any]:
        """
        Get orchestrator status

        Returns:
            Status dictionary with agent health
        """
        return {
            "orchestrator": self.name,
            "bankroll_usd": self.bankroll_usd,
            "agents": {
                "market_sensor": self.market_sensor.name,
                "book_analyzer": self.book_analyzer.name,
                "signal_engine": self.signal_engine.name,
                "decision_engine": self.decision_engine.name,
                "risk_gate": self.risk_gate.name,
            },
            "pipeline": "MARKET_SENSOR → BOOK_ANALYZER → SIGNAL_ENGINE → DECISION_ENGINE → RISK_GATE",
            "status": "ready",
        }
