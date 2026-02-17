"""
DECISION_ENGINE Agent
Makes UP/DOWN/NO_TRADE call with detailed reasons
"""
from typing import List
from datetime import datetime
import logging

from .schemas import (
    PolymarketDirectionOutput, CallDirection, Confidence,
    ActionIntent, IntentType, RiskLevel,
    MarketSnapshot, BookSnapshot, Signals
)

logger = logging.getLogger(__name__)


class DecisionEngine:
    """
    Makes directional calls with detailed reasoning

    Authority: No tools - pure decision logic
    Output: PolymarketDirectionOutput JSON only
    """

    def __init__(self):
        self.name = "DECISION_ENGINE"

    async def make_decision(
        self,
        market_snapshot: MarketSnapshot,
        book_snapshot: BookSnapshot,
        signals: Signals
    ) -> PolymarketDirectionOutput:
        """
        Make UP/DOWN/NO_TRADE call

        Args:
            market_snapshot: Market data
            book_snapshot: Order book data
            signals: Computed signals

        Returns:
            PolymarketDirectionOutput with call, reasons, and intents
        """
        logger.info(f"[{self.name}] Making decision")

        # Apply decision rules
        call, reasons = self._determine_call(signals)

        # Grade confidence
        confidence = self._grade_confidence(signals, call)

        # Generate action intents (if tradeable)
        action_intents = self._generate_action_intents(
            call, confidence, signals, market_snapshot
        )

        # Calculate recommended bet size
        bankroll_usd = 5000  # Default bankroll
        recommended_bet_pct, recommended_bet_usd = self._calculate_bet_size(
            call, confidence, signals, bankroll_usd
        )

        # Build output
        output = PolymarketDirectionOutput(
            market_url=market_snapshot.market_url,
            timestamp_iso=datetime.utcnow().isoformat(),
            call=call,
            prob_up=signals.prob_up,
            confidence=confidence,
            reasons=reasons,
            key_signals={
                "time_remaining_seconds": signals.time_remaining_seconds,
                "obi_up": signals.obi_up,
                "obi_down": signals.obi_down,
                "delta_p1": signals.delta_p1,
                "delta_p3": signals.delta_p3,
                "spread_ok": signals.spread_ok,
                "vol_regime": signals.vol_regime.value,
                "edge_score": signals.edge_score,
            },
            action_intents=action_intents,
            recommended_bet_usd=recommended_bet_usd,
            recommended_bet_pct=recommended_bet_pct,
        )

        logger.info(
            f"[{self.name}] Decision: call={call.value}, "
            f"confidence={confidence.value}, "
            f"intents={len(action_intents)}"
        )

        return output

    def _determine_call(self, signals: Signals) -> tuple[CallDirection, List[str]]:
        """
        Determine call direction with detailed reasons
        Returns: (call, reasons list with min 6 items)
        """
        reasons = []

        # Rule 1: Insufficient data
        if not signals.decision_ready:
            return CallDirection.NO_TRADE, [
                "❌ INSUFFICIENT DATA: Critical market data unavailable",
                f"• Spread quality: {signals.spread_ok}",
                f"• Time remaining: {signals.time_remaining_seconds}s",
                f"• Order book imbalance UP: {signals.obi_up:.3f}",
                f"• Order book imbalance DOWN: {signals.obi_down:.3f}",
                "• Cannot make reliable decision without complete data",
            ]

        # Rule 2: Spread quality
        if not signals.spread_ok:
            return CallDirection.NO_TRADE, [
                "❌ SPREAD TOO WIDE: Market spread exceeds 3% threshold",
                f"• Spread check failed: {signals.spread_ok}",
                f"• Edge score: {signals.edge_score:.3f}",
                "• Wide spreads indicate poor liquidity",
                "• Risk of significant slippage",
                "• Waiting for tighter spreads",
            ]

        # Rule 3: Timing window
        time_ok, time_reason = self._check_timing(signals.time_remaining_seconds)
        if not time_ok and abs(signals.edge_score) < 0.75:
            return CallDirection.NO_TRADE, [
                f"❌ TIMING: {time_reason}",
                f"• Time remaining: {signals.time_remaining_seconds}s",
                f"• Edge score: {signals.edge_score:.3f} (below 0.75 threshold for off-window)",
                "• Optimal window: 240-900 seconds (4-15 minutes)",
                "• Insufficient edge to justify early/late entry",
                "• Waiting for optimal timing window",
            ]

        # Rule 4: Edge threshold
        if abs(signals.edge_score) < 0.25:
            return CallDirection.NO_TRADE, [
                "❌ NO EDGE: Edge score below 0.25 threshold",
                f"• Edge score: {signals.edge_score:.3f}",
                f"• OBI UP: {signals.obi_up:.3f}, OBI DOWN: {signals.obi_down:.3f}",
                f"• TFB UP: {signals.tfb_up:.3f}, TFB DOWN: {signals.tfb_down:.3f}",
                f"• Volatility regime: {signals.vol_regime.value}",
                "• Market signals too weak for confident directional call",
            ]

        # Determine direction
        if signals.edge_score >= 0.25:
            # Call UP
            reasons = [
                f"✅ BULLISH SIGNAL: Edge score {signals.edge_score:.3f} indicates UP",
                f"• Probability UP: {signals.prob_up:.1%}",
                f"• OBI UP: {signals.obi_up:.3f} (positive = buy pressure)",
                f"• OBI DOWN: {signals.obi_down:.3f}",
                f"• Trade flow bias UP: {signals.tfb_up:.3f}",
                f"• Volatility regime: {signals.vol_regime.value}",
            ]

            # Add momentum if available
            if signals.delta_p1 is not None:
                reasons.append(f"• 1-min momentum: {signals.delta_p1:+.3f}")
            if signals.delta_p3 is not None:
                reasons.append(f"• 3-min momentum: {signals.delta_p3:+.3f}")

            # Add timing
            reasons.append(f"• Time remaining: {signals.time_remaining_seconds}s")

            # Ensure min 6 reasons
            while len(reasons) < 6:
                reasons.append(f"• Spread quality: {signals.spread_ok}")

            return CallDirection.UP, reasons

        elif signals.edge_score <= -0.25:
            # Call DOWN
            reasons = [
                f"✅ BEARISH SIGNAL: Edge score {signals.edge_score:.3f} indicates DOWN",
                f"• Probability DOWN: {(1 - signals.prob_up):.1%}",
                f"• OBI DOWN: {signals.obi_down:.3f} (positive = buy pressure for DOWN)",
                f"• OBI UP: {signals.obi_up:.3f}",
                f"• Trade flow bias DOWN: {signals.tfb_down:.3f}",
                f"• Volatility regime: {signals.vol_regime.value}",
            ]

            # Add momentum if available
            if signals.delta_p1 is not None:
                reasons.append(f"• 1-min momentum: {signals.delta_p1:+.3f}")
            if signals.delta_p3 is not None:
                reasons.append(f"• 3-min momentum: {signals.delta_p3:+.3f}")

            # Add timing
            reasons.append(f"• Time remaining: {signals.time_remaining_seconds}s")

            # Ensure min 6 reasons
            while len(reasons) < 6:
                reasons.append(f"• Spread quality: {signals.spread_ok}")

            return CallDirection.DOWN, reasons

        # Shouldn't reach here, but safety fallback
        return CallDirection.NO_TRADE, [
            "❌ INDETERMINATE: Edge score in dead zone",
            f"• Edge score: {signals.edge_score:.3f}",
            "• No clear directional signal",
            "• Waiting for stronger conviction",
            "• Market appears range-bound",
            "• Preserving capital",
        ]

    def _check_timing(self, time_remaining: int | None) -> tuple[bool, str]:
        """Check if timing is in optimal window"""
        if time_remaining is None:
            return False, "Unknown time remaining"

        if time_remaining < 240:  # Less than 4 minutes
            return False, f"Too late (< 4m remaining)"
        if time_remaining > 900:  # More than 15 minutes
            return False, f"Too early (> 15m remaining)"

        return True, "Optimal timing window"

    def _grade_confidence(self, signals: Signals, call: CallDirection) -> Confidence:
        """
        Grade confidence level

        HIGH requires:
        - Strong OBI alignment (>=0.25)
        - Momentum alignment (both deltas same sign as call)
        - Mid/High volatility regime

        MEDIUM: 2 out of 3 above
        LOW: Otherwise
        """
        if call == CallDirection.NO_TRADE:
            return Confidence.LOW

        criteria_met = 0

        # Criterion 1: Strong OBI
        if call == CallDirection.UP:
            if signals.obi_up >= 0.25:
                criteria_met += 1
        else:  # DOWN
            if signals.obi_down >= 0.25:
                criteria_met += 1

        # Criterion 2: Momentum alignment
        if signals.delta_p1 is not None and signals.delta_p3 is not None:
            if call == CallDirection.UP:
                if signals.delta_p1 > 0 and signals.delta_p3 > 0:
                    criteria_met += 1
            else:  # DOWN
                if signals.delta_p1 < 0 and signals.delta_p3 < 0:
                    criteria_met += 1

        # Criterion 3: Volatility regime
        if signals.vol_regime in ["mid", "high"]:
            criteria_met += 1

        if criteria_met >= 3:
            return Confidence.HIGH
        elif criteria_met >= 2:
            return Confidence.MEDIUM
        else:
            return Confidence.LOW

    def _generate_action_intents(
        self,
        call: CallDirection,
        confidence: Confidence,
        signals: Signals,
        market: MarketSnapshot
    ) -> List[ActionIntent]:
        """
        Generate action intents for execution
        Only propose intents if call is tradeable and confidence >= MEDIUM
        """
        intents = []

        # Only generate intents for actual calls with sufficient confidence
        if call == CallDirection.NO_TRADE:
            return intents

        if confidence == Confidence.LOW:
            return intents

        # Intent 1: Confirm orderbook before trade
        intents.append(ActionIntent(
            intent_id="confirm_book_1",
            intent_type=IntentType.TOOL_REQUEST,
            tool_name="polymarket_clob.orderbook",
            tool_operation="GET",
            parameters={
                "token_id": "UP_TOKEN" if call == CallDirection.UP else "DOWN_TOKEN",
                "depth": 10,
            },
            justification_source="trusted_user_request",
            risk_level=RiskLevel.LOW,
        ))

        # Intent 2: Place limit order (if user confirms)
        side = "buy" if call == CallDirection.UP else "buy"  # Buying the outcome token
        limit_price = market.up_best_ask if call == CallDirection.UP else market.down_best_ask

        if limit_price is not None:
            intents.append(ActionIntent(
                intent_id="place_entry_order_1",
                intent_type=IntentType.TOOL_REQUEST,
                tool_name="polymarket_clob.place_order",
                tool_operation="LIMIT",
                parameters={
                    "token_id": "UP_TOKEN" if call == CallDirection.UP else "DOWN_TOKEN",
                    "side": side,
                    "limit_price_prob": round(limit_price, 3),
                    "max_cost_usd": 250,  # Max $250 position
                    "time_in_force": "IOC",  # Immediate or cancel
                },
                justification_source="trusted_user_request",
                risk_level=RiskLevel.HIGH,
            ))

        return intents

    def _calculate_bet_size(
        self,
        call: CallDirection,
        confidence: Confidence,
        signals: Signals,
        bankroll_usd: float
    ) -> tuple[float, float]:
        """
        Calculate recommended bet size based on confidence and edge

        Returns: (bet_pct, bet_usd)
        """
        if call == CallDirection.NO_TRADE:
            return (0.0, 0.0)

        # Base bet sizes by confidence
        if confidence == Confidence.HIGH:
            base_pct = 0.05  # 5% for high confidence
        elif confidence == Confidence.MEDIUM:
            base_pct = 0.03  # 3% for medium confidence
        else:
            base_pct = 0.01  # 1% for low confidence

        # Adjust by edge score (0.6-1.0 range)
        edge_multiplier = min(abs(signals.edge_score), 1.0)
        adjusted_pct = base_pct * edge_multiplier

        # Cap at 5% (MAX_POSITION_PCT from risk_gate)
        final_pct = min(adjusted_pct, 0.05)
        final_usd = bankroll_usd * final_pct

        return (round(final_pct * 100, 1), round(final_usd, 2))
