"""
JSON Schema definitions for Polymarket BTC 15m skill
All data structures with validation
"""
from typing import Dict, Any, List, Optional, Literal
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum


class CallDirection(str, Enum):
    """Direction call"""
    UP = "UP"
    DOWN = "DOWN"
    NO_TRADE = "NO_TRADE"


class Confidence(str, Enum):
    """Confidence level"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class VolatilityRegime(str, Enum):
    """Volatility classification"""
    LOW = "low"
    MID = "mid"
    HIGH = "high"
    UNKNOWN = "unknown"


class IntentType(str, Enum):
    """Action intent type"""
    TOOL_REQUEST = "TOOL_REQUEST"


class RiskLevel(str, Enum):
    """Risk level"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ==================== MARKET SENSOR ====================

@dataclass
class OrderBookLevel:
    """Single order book level"""
    price_prob: float  # [0, 1]
    size: float

    def to_dict(self) -> Dict[str, Any]:
        return {"price_prob": self.price_prob, "size": self.size}


@dataclass
class Trade:
    """Single trade"""
    side: Literal["buy", "sell", "unknown"]
    price_prob: float  # [0, 1]
    size: float
    time_iso: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MarketSnapshot:
    """Market state extracted from page"""
    captured_at_iso: str
    market_url: str
    market_title: str
    market_id: Optional[str]

    # Outcomes
    up_label: str
    down_label: str
    yes_means_up: bool

    # Prices
    up_prob: Optional[float] = None
    down_prob: Optional[float] = None

    # Spreads
    up_spread: Optional[float] = None
    down_spread: Optional[float] = None
    up_best_bid: Optional[float] = None
    up_best_ask: Optional[float] = None
    down_best_bid: Optional[float] = None
    down_best_ask: Optional[float] = None

    # Liquidity
    volume_24h_usd: Optional[float] = None
    total_volume_usd: Optional[float] = None
    open_interest_usd: Optional[float] = None

    # Time
    time_remaining_seconds: Optional[int] = None

    # Order book snapshot from page
    up_bids: List[OrderBookLevel] = field(default_factory=list)
    up_asks: List[OrderBookLevel] = field(default_factory=list)
    down_bids: List[OrderBookLevel] = field(default_factory=list)
    down_asks: List[OrderBookLevel] = field(default_factory=list)

    # Recent trades from page
    recent_trades: List[Trade] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "captured_at_iso": self.captured_at_iso,
            "market_url": self.market_url,
            "market_title": self.market_title,
            "market_id": self.market_id,
            "outcomes": {
                "up_label": self.up_label,
                "down_label": self.down_label,
                "yes_means_up": self.yes_means_up,
            },
            "prices": {
                "up_prob": self.up_prob,
                "down_prob": self.down_prob,
            },
            "spreads": {
                "up_spread": self.up_spread,
                "down_spread": self.down_spread,
                "up_best_bid": self.up_best_bid,
                "up_best_ask": self.up_best_ask,
                "down_best_bid": self.down_best_bid,
                "down_best_ask": self.down_best_ask,
            },
            "liquidity": {
                "volume_24h_usd": self.volume_24h_usd,
                "total_volume_usd": self.total_volume_usd,
                "open_interest_usd": self.open_interest_usd,
            },
            "time_remaining_seconds": self.time_remaining_seconds,
            "page_orderbook_top": {
                "up_bids": [b.to_dict() for b in self.up_bids],
                "up_asks": [a.to_dict() for a in self.up_asks],
                "down_bids": [b.to_dict() for b in self.down_bids],
                "down_asks": [a.to_dict() for a in self.down_asks],
            },
            "page_recent_trades": [t.to_dict() for t in self.recent_trades],
        }


# ==================== BOOK ANALYZER ====================

@dataclass
class OrderBook:
    """Order book for one side"""
    bids: List[OrderBookLevel]
    asks: List[OrderBookLevel]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bids": [b.to_dict() for b in self.bids],
            "asks": [a.to_dict() for a in self.asks],
        }


@dataclass
class BookSnapshot:
    """Complete order book snapshot"""
    captured_at_iso: str
    up_token_id: Optional[str]
    down_token_id: Optional[str]

    up_book: OrderBook
    down_book: OrderBook

    up_recent_trades: List[Trade]
    down_recent_trades: List[Trade]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "captured_at_iso": self.captured_at_iso,
            "up_token_id": self.up_token_id,
            "down_token_id": self.down_token_id,
            "up_book": self.up_book.to_dict(),
            "down_book": self.down_book.to_dict(),
            "up_recent_trades": [t.to_dict() for t in self.up_recent_trades],
            "down_recent_trades": [t.to_dict() for t in self.down_recent_trades],
        }


# ==================== SIGNAL ENGINE ====================

@dataclass
class Signals:
    """Computed trading signals"""
    decision_ready: bool
    time_remaining_seconds: Optional[int]

    # Spread quality
    spread_ok: bool

    # Order book imbalance
    obi_up: float  # [-1, 1]
    obi_down: float  # [-1, 1]

    # Momentum
    delta_p1: Optional[float]  # 1-minute delta
    delta_p3: Optional[float]  # 3-minute delta

    # Trade flow bias
    tfb_up: float  # [-1, 1]
    tfb_down: float  # [-1, 1]

    # Volatility
    vol_regime: VolatilityRegime

    # Computed edge
    edge_score: float  # [-1, 1] where + means UP
    prob_up: float  # [0, 1]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_ready": self.decision_ready,
            "time_remaining_seconds": self.time_remaining_seconds,
            "spread_ok": self.spread_ok,
            "obi_up": self.obi_up,
            "obi_down": self.obi_down,
            "delta_p1": self.delta_p1,
            "delta_p3": self.delta_p3,
            "tfb_up": self.tfb_up,
            "tfb_down": self.tfb_down,
            "vol_regime": self.vol_regime.value,
            "edge_score": self.edge_score,
            "prob_up": self.prob_up,
        }


# ==================== DECISION ENGINE ====================

@dataclass
class ActionIntent:
    """Proposed action intent"""
    intent_id: str
    intent_type: IntentType
    tool_name: Optional[str]
    tool_operation: Optional[str]
    parameters: Dict[str, Any]
    justification_source: str
    risk_level: RiskLevel

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent_id": self.intent_id,
            "intent_type": self.intent_type.value,
            "tool_name": self.tool_name,
            "tool_operation": self.tool_operation,
            "parameters": self.parameters,
            "justification_source": self.justification_source,
            "risk_level": self.risk_level.value,
        }


@dataclass
class PolymarketDirectionOutput:
    """Final decision output"""
    market_url: str
    timestamp_iso: str
    call: CallDirection
    prob_up: float
    confidence: Confidence
    reasons: List[str]  # Min 6 detailed reasons

    # Key signals (for transparency)
    key_signals: Dict[str, Any]

    # Proposed actions
    action_intents: List[ActionIntent]

    # Betting recommendations
    recommended_bet_usd: float = 0.0
    recommended_bet_pct: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "market_url": self.market_url,
            "timestamp_iso": self.timestamp_iso,
            "call": self.call.value,
            "prob_up": self.prob_up,
            "confidence": self.confidence.value,
            "reasons": self.reasons,
            "key_signals": self.key_signals,
            "action_intents": [intent.to_dict() for intent in self.action_intents],
            "recommended_bet_usd": self.recommended_bet_usd,
            "recommended_bet_pct": self.recommended_bet_pct,
        }


# ==================== RISK GATE ====================

@dataclass
class RiskGateResult:
    """Risk gate approval/denial"""
    approved_intents: List[ActionIntent]
    denied_intents: List[Dict[str, Any]]  # With denial reasons

    def to_dict(self) -> Dict[str, Any]:
        return {
            "approved_intents": [intent.to_dict() for intent in self.approved_intents],
            "denied_intents": self.denied_intents,
        }


# ==================== EXECUTION ENGINE ====================

@dataclass
class ExecutionResult:
    """Result of executing an action intent"""
    intent_id: str
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent_id": self.intent_id,
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
        }
