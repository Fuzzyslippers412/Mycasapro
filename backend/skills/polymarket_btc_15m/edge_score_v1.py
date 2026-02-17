"""
EDGE_SCORE v1.0 Implementation
Exact copy-paste enforceable specification with locked constraints
"""
from typing import Optional, Tuple
import math


# ==================== CONFIG (canonical constants) ====================

class EdgeConfig:
    """EDGE_CONFIG_V1 - DO NOT MODIFY"""

    # Decision window (default)
    TIME_WINDOW_ENTRY_MIN_SEC = 240      # 4 minutes
    TIME_WINDOW_ENTRY_MAX_SEC = 900      # 15 minutes

    # Spread thresholds (probability units; 0.01 = 1 cent)
    SPREAD_OK_MAX = 0.03
    SPREAD_SOFT_MAX = 0.06

    # OBI thresholds
    OBI_STRONG = 0.25
    OBI_EXTREME = 0.40

    # Momentum thresholds (prob units)
    DELTA_P_SMALL = 0.01
    DELTA_P_STRONG = 0.03

    # Trade flow thresholds
    TFB_STRONG = 0.20

    # Weighting (must sum to 1.0 before penalties)
    W_OBI = 0.45
    W_MOM = 0.30
    W_TFB = 0.15
    W_TIME = 0.10

    # Regime multipliers applied to the momentum term
    MOM_MULT_LOW_VOL = 0.70
    MOM_MULT_MID_VOL = 1.00
    MOM_MULT_HIGH_VOL = 1.15
    MOM_MULT_UNKNOWN = 0.85

    # Penalties (subtractive from |edge|)
    PENALTY_SPREAD_SOFT = 0.10
    PENALTY_SPREAD_HARD = 0.25
    PENALTY_LOW_LIQUIDITY = 0.10
    PENALTY_MISSING_MOM = 0.12
    PENALTY_CONTRADICTION = 0.18

    # Calibration to probability
    PROB_CENTER = 0.50
    PROB_SLOPE = 0.45
    PROB_MIN = 0.05
    PROB_MAX = 0.95

    # Gating / no-trade conditions (hard)
    HARD_DENY_IF_SPREAD_GT = 0.06
    HARD_DENY_IF_TIME_LT_SEC = 120
    HARD_DENY_IF_TIME_GT_SEC = 1200


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp value to range"""
    return max(min_val, min(max_val, value))


def sign(value: float) -> int:
    """Return sign of value"""
    if value > 0:
        return 1
    elif value < 0:
        return -1
    return 0


class EdgeScoreV1:
    """
    Deterministic edge score computation
    Follows EDGE_SCORE v1.0 specification exactly
    """

    @staticmethod
    def compute(
        # Time
        t_sec: Optional[int],

        # Spreads
        up_spread: Optional[float],
        down_spread: Optional[float],
        up_best_bid: Optional[float],
        up_best_ask: Optional[float],
        down_best_bid: Optional[float],
        down_best_ask: Optional[float],

        # Order book imbalance
        obi_up: float,
        obi_down: float,

        # Momentum
        delta_p1_up: Optional[float],
        delta_p3_up: Optional[float],

        # Trade flow
        tfb_up: float,
        tfb_down: float,

        # Volatility
        vol_regime: str,  # "low" | "mid" | "high" | "unknown"

        # Liquidity (optional)
        volume_24h_usd: Optional[float] = None,
        open_interest_usd: Optional[float] = None,
    ) -> Tuple[bool, float, float, dict]:
        """
        Compute edge score with full reasoning

        Returns:
            (decision_ready, edge_score, prob_up, debug_info)
        """
        cfg = EdgeConfig
        debug = {}

        # ========== HARD GATING ==========

        # Check spreads
        if up_spread is None or down_spread is None:
            return (False, 0.0, 0.50, {"gate": "spread_missing"})

        spread_worst = max(up_spread, down_spread)
        debug["spread_worst"] = spread_worst

        if spread_worst > cfg.HARD_DENY_IF_SPREAD_GT:
            return (False, 0.0, 0.50, {"gate": f"spread_worst={spread_worst:.4f} > {cfg.HARD_DENY_IF_SPREAD_GT}"})

        # Check time
        if t_sec is None:
            return (False, 0.0, 0.50, {"gate": "time_missing"})

        if t_sec < cfg.HARD_DENY_IF_TIME_LT_SEC:
            return (False, 0.0, 0.50, {"gate": f"time={t_sec}s < {cfg.HARD_DENY_IF_TIME_LT_SEC}s"})

        if t_sec > cfg.HARD_DENY_IF_TIME_GT_SEC:
            return (False, 0.0, 0.50, {"gate": f"time={t_sec}s > {cfg.HARD_DENY_IF_TIME_GT_SEC}s"})

        # ========== COMPONENT COMPUTATION ==========

        # 1) Book pressure
        book_pressure = clamp(obi_up - obi_down, -1, 1)
        debug["book_pressure"] = book_pressure

        # 2) Momentum
        missing_momentum = False
        momentum_alignment = False
        mom = 0.0

        if delta_p1_up is not None and delta_p3_up is not None:
            mom_raw = clamp(
                (0.65 * delta_p1_up) + (0.35 * delta_p3_up),
                -0.10, +0.10
            )
            mom = clamp(mom_raw / 0.05, -1, +1)

            # Check alignment
            if sign(delta_p1_up) == sign(delta_p3_up) and abs(delta_p1_up) >= cfg.DELTA_P_SMALL:
                momentum_alignment = True
        else:
            missing_momentum = True

        debug["mom"] = mom
        debug["missing_momentum"] = missing_momentum
        debug["momentum_alignment"] = momentum_alignment

        # 3) Trade flow
        flow_pressure = clamp(tfb_up - tfb_down, -1, +1)
        debug["flow_pressure"] = flow_pressure

        # 4) Time term
        time_term = 0.0
        if cfg.TIME_WINDOW_ENTRY_MIN_SEC <= t_sec <= cfg.TIME_WINDOW_ENTRY_MAX_SEC:
            x = (t_sec - cfg.TIME_WINDOW_ENTRY_MIN_SEC) / (cfg.TIME_WINDOW_ENTRY_MAX_SEC - cfg.TIME_WINDOW_ENTRY_MIN_SEC)
            time_term = clamp((0.6 * x) - 0.3, -1, +1)
        debug["time_term"] = time_term

        # 5) Volatility multiplier
        mom_mult_map = {
            "low": cfg.MOM_MULT_LOW_VOL,
            "mid": cfg.MOM_MULT_MID_VOL,
            "high": cfg.MOM_MULT_HIGH_VOL,
            "unknown": cfg.MOM_MULT_UNKNOWN,
        }
        mom_mult = mom_mult_map.get(vol_regime, cfg.MOM_MULT_UNKNOWN)
        debug["mom_mult"] = mom_mult

        # ========== WEIGHTED BASE SCORE ==========

        obi_comp = book_pressure
        mom_comp = mom * mom_mult
        tfb_comp = flow_pressure
        time_comp = time_term

        base = clamp(
            (cfg.W_OBI * obi_comp) +
            (cfg.W_MOM * mom_comp) +
            (cfg.W_TFB * tfb_comp) +
            (cfg.W_TIME * time_comp),
            -1, +1
        )

        debug["base"] = base
        debug["obi_comp"] = obi_comp
        debug["mom_comp"] = mom_comp
        debug["tfb_comp"] = tfb_comp
        debug["time_comp"] = time_comp

        # ========== PENALTIES ==========

        penalty = 0.0

        # 3a) Spread penalty
        if spread_worst <= cfg.SPREAD_OK_MAX:
            spread_penalty = 0.0
        elif spread_worst <= cfg.SPREAD_SOFT_MAX:
            spread_penalty = cfg.PENALTY_SPREAD_SOFT
        else:
            spread_penalty = cfg.PENALTY_SPREAD_HARD

        penalty += spread_penalty
        debug["spread_penalty"] = spread_penalty

        # 3b) Missing momentum penalty
        if missing_momentum:
            penalty += cfg.PENALTY_MISSING_MOM
            debug["missing_mom_penalty"] = cfg.PENALTY_MISSING_MOM

        # 3c) Liquidity penalty
        low_liquidity = False
        if open_interest_usd is not None and open_interest_usd < 25000:
            low_liquidity = True
        elif volume_24h_usd is not None and volume_24h_usd < 20000:
            low_liquidity = True

        if low_liquidity:
            penalty += cfg.PENALTY_LOW_LIQUIDITY
            debug["liquidity_penalty"] = cfg.PENALTY_LOW_LIQUIDITY

        # 3d) Contradiction penalty
        contradiction = (
            abs(obi_comp) >= cfg.OBI_STRONG and
            not missing_momentum and
            sign(obi_comp) != sign(mom)
        )

        if contradiction:
            penalty += cfg.PENALTY_CONTRADICTION
            debug["contradiction_penalty"] = cfg.PENALTY_CONTRADICTION

        debug["total_penalty"] = penalty

        # ========== APPLY PENALTY ==========

        mag = max(0, abs(base) - penalty)
        edge_score = sign(base) * mag
        edge_score = clamp(edge_score, -1, +1)

        debug["edge_score"] = edge_score

        # ========== PROBABILITY CALIBRATION ==========

        prob_up = clamp(
            cfg.PROB_CENTER + (cfg.PROB_SLOPE * edge_score),
            cfg.PROB_MIN,
            cfg.PROB_MAX
        )

        debug["prob_up"] = prob_up

        return (True, edge_score, prob_up, debug)


# ==================== DECISION THRESHOLDS ====================

def get_call_from_edge(edge_score: float, decision_ready: bool) -> str:
    """
    Map edge score to call direction
    CALL_RULES_V1
    """
    if not decision_ready:
        return "NO_TRADE"

    if edge_score >= 0.25:
        return "UP"
    elif edge_score <= -0.25:
        return "DOWN"
    else:
        return "NO_TRADE"


def get_confidence_from_signals(
    edge_score: float,
    obi_comp: float,
    missing_momentum: bool,
    momentum_alignment: bool,
    vol_regime: str,
    spread_worst: float
) -> str:
    """
    Grade confidence level
    CONFIDENCE_V1
    """
    cfg = EdgeConfig

    # HIGH
    if (
        abs(edge_score) >= 0.45 and
        abs(obi_comp) >= cfg.OBI_STRONG and
        not missing_momentum and
        momentum_alignment and
        vol_regime in ["mid", "high"] and
        spread_worst <= cfg.SPREAD_OK_MAX
    ):
        return "HIGH"

    # MEDIUM
    if (
        abs(edge_score) >= 0.30 and
        abs(obi_comp) >= 0.18 and
        spread_worst <= cfg.SPREAD_OK_MAX
    ):
        return "MEDIUM"

    return "LOW"
