"""
RISK_GATE Agent
Enforces strict survival rules and position limits
"""
from typing import List, Dict, Any
import logging

from .schemas import (
    RiskGateResult, ActionIntent, Signals,
    CallDirection, Confidence
)

logger = logging.getLogger(__name__)


class RiskGate:
    """
    Enforces bankroll protection rules

    Authority: No tools - pure gating logic
    Output: Approved/denied intents with constraints
    """

    # Risk parameters (5% bankroll hardcoded for production safety)
    MAX_POSITION_PCT = 0.05  # 5% of bankroll per market
    MAX_DAILY_LOSS_PCT = 0.10  # 10% daily loss limit
    ASSUMED_BANKROLL_USD = 5000  # Default if not provided

    def __init__(self, bankroll_usd: float = ASSUMED_BANKROLL_USD):
        self.name = "RISK_GATE"
        self.bankroll_usd = bankroll_usd
        self.daily_loss_usd = 0.0  # Would track in production

    async def gate_intents(
        self,
        proposed_intents: List[ActionIntent],
        signals: Signals,
        call: CallDirection,
        confidence: Confidence
    ) -> RiskGateResult:
        """
        Gate proposed intents with risk rules

        Args:
            proposed_intents: Intents from DECISION_ENGINE
            signals: Computed signals
            call: Direction call
            confidence: Confidence level

        Returns:
            RiskGateResult with approved/denied lists
        """
        logger.info(f"[{self.name}] Gating {len(proposed_intents)} intents")

        approved = []
        denied = []

        for intent in proposed_intents:
            deny_reason = self._check_intent(intent, signals, call, confidence)

            if deny_reason:
                denied.append({
                    "intent_id": intent.intent_id,
                    "tool_name": intent.tool_name,
                    "reason": deny_reason,
                })
                logger.warning(
                    f"[{self.name}] DENIED intent {intent.intent_id}: {deny_reason}"
                )
            else:
                # Approve with constraints
                constrained = self._apply_constraints(intent)
                approved.append(constrained)
                logger.info(f"[{self.name}] APPROVED intent {intent.intent_id}")

        result = RiskGateResult(
            approved_intents=approved,
            denied_intents=denied,
        )

        logger.info(
            f"[{self.name}] Gate result: "
            f"approved={len(approved)}, denied={len(denied)}"
        )

        return result

    def _check_intent(
        self,
        intent: ActionIntent,
        signals: Signals,
        call: CallDirection,
        confidence: Confidence
    ) -> str | None:
        """
        Check if intent should be denied
        Returns denial reason or None if approved
        """
        # Rule 1: Daily loss limit
        max_daily_loss = self.bankroll_usd * self.MAX_DAILY_LOSS_PCT
        if self.daily_loss_usd >= max_daily_loss:
            return f"Daily loss limit reached: ${self.daily_loss_usd:.2f} >= ${max_daily_loss:.2f}"

        # Rule 2: No market orders (only limit orders)
        if intent.tool_name == "polymarket_clob.place_order":
            if intent.parameters.get("order_type") == "MARKET":
                return "Market orders denied - limit orders only"

        # Rule 3: Late entry protection
        if signals.time_remaining_seconds is not None:
            if signals.time_remaining_seconds < 240:  # < 4 minutes
                # Only allow if HIGH confidence and strong edge
                if confidence != Confidence.HIGH or abs(signals.edge_score) < 0.75:
                    return f"Late entry denied: {signals.time_remaining_seconds}s remaining, confidence={confidence.value}"

        # Rule 4: Spread safety
        if not signals.spread_ok:
            return "Spread exceeds safety threshold"

        # Rule 5: Position size limit
        if intent.tool_name == "polymarket_clob.place_order":
            max_cost = intent.parameters.get("max_cost_usd", 0)
            max_position = self.bankroll_usd * self.MAX_POSITION_PCT

            if max_cost > max_position:
                return f"Position size ${max_cost} exceeds {self.MAX_POSITION_PCT*100}% limit (${max_position:.2f})"

        # Rule 6: OBI flip check (requires pre-trade confirmation)
        # In production, would check if OBI flipped between decision and execution
        # For now, we require confirmation fetch intent before place_order

        return None  # Approved

    def _apply_constraints(self, intent: ActionIntent) -> ActionIntent:
        """
        Apply additional constraints to approved intent
        """
        # For place_order intents, enforce strict limits
        if intent.tool_name == "polymarket_clob.place_order":
            params = intent.parameters.copy()

            # Cap position size
            max_position = self.bankroll_usd * self.MAX_POSITION_PCT
            if params.get("max_cost_usd", 0) > max_position:
                params["max_cost_usd"] = max_position

            # Force IOC (immediate or cancel)
            params["time_in_force"] = "IOC"

            # Return constrained intent
            return ActionIntent(
                intent_id=intent.intent_id,
                intent_type=intent.intent_type,
                tool_name=intent.tool_name,
                tool_operation=intent.tool_operation,
                parameters=params,
                justification_source=intent.justification_source,
                risk_level=intent.risk_level,
            )

        return intent
