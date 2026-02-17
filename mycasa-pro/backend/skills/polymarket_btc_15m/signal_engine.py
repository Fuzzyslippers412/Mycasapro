"""
SIGNAL_ENGINE Agent
Computes trading signals using EDGE_SCORE v1.0

Uses Binance BTC price data for momentum signals.
"""
from typing import Optional
import logging
from datetime import datetime, timedelta

from .schemas import Signals, MarketSnapshot, BookSnapshot, VolatilityRegime
from .edge_score_v1 import EdgeScoreV1

logger = logging.getLogger(__name__)

# Binance client for BTC price data
_binance_client = None

def get_binance_client():
    """Lazy-load Binance adapter for momentum data"""
    global _binance_client
    if _binance_client is None:
        try:
            from backend.edgelab.adapters import BinanceAdapter
            _binance_client = BinanceAdapter()
            logger.info("[SIGNAL_ENGINE] Binance adapter loaded for momentum signals")
        except Exception as e:
            logger.warning(f"[SIGNAL_ENGINE] Could not load Binance adapter: {e}")
    return _binance_client


class SignalEngine:
    """
    Computes trading signals using EDGE_SCORE v1.0 specification

    Authority: No tools - pure computation
    Output: Signals JSON only
    """

    def __init__(self):
        self.name = "SIGNAL_ENGINE"

    async def compute_signals(
        self,
        market_snapshot: MarketSnapshot,
        book_snapshot: BookSnapshot
    ) -> Signals:
        """
        Compute all trading signals using EDGE_SCORE v1.0

        Args:
            market_snapshot: Market data
            book_snapshot: Order book data

        Returns:
            Signals with all computed indicators
        """
        logger.info(f"[{self.name}] Computing signals with EDGE_SCORE v1.0")

        # Compute OBI
        obi_up = self._compute_obi(book_snapshot.up_book)
        obi_down = self._compute_obi(book_snapshot.down_book)

        # Compute TFB
        tfb_up = self._compute_tfb(book_snapshot.up_recent_trades)
        tfb_down = self._compute_tfb(book_snapshot.down_recent_trades)

        # Compute momentum (would be historical in production)
        delta_p1, delta_p3 = self._compute_momentum(book_snapshot)

        # Classify volatility
        vol_regime = self._classify_volatility(market_snapshot)

        # Use EDGE_SCORE v1.0 for deterministic computation
        decision_ready, edge_score, _calculated_prob_up, debug = EdgeScoreV1.compute(
            t_sec=market_snapshot.time_remaining_seconds,
            up_spread=market_snapshot.up_spread,
            down_spread=market_snapshot.down_spread,
            up_best_bid=market_snapshot.up_best_bid,
            up_best_ask=market_snapshot.up_best_ask,
            down_best_bid=market_snapshot.down_best_bid,
            down_best_ask=market_snapshot.down_best_ask,
            obi_up=obi_up,
            obi_down=obi_down,
            delta_p1_up=delta_p1,
            delta_p3_up=delta_p3,
            tfb_up=tfb_up,
            tfb_down=tfb_down,
            vol_regime=vol_regime.value,
            volume_24h_usd=market_snapshot.volume_24h_usd,
            open_interest_usd=market_snapshot.open_interest_usd,
        )

        # CRITICAL FIX: Use ACTUAL market probability, not EDGE_SCORE's calculated probability
        # In prediction markets, the market price IS the probability
        # We're looking for edge in the order book, not trying to predict the price itself
        prob_up = market_snapshot.up_prob if market_snapshot.up_prob is not None else 0.5

        # Spread quality from EDGE_SCORE
        spread_worst = debug.get("spread_worst", 0.0)
        spread_ok = spread_worst <= 0.03

        signals = Signals(
            decision_ready=decision_ready,
            time_remaining_seconds=market_snapshot.time_remaining_seconds,
            spread_ok=spread_ok,
            obi_up=obi_up,
            obi_down=obi_down,
            delta_p1=delta_p1,
            delta_p3=delta_p3,
            tfb_up=tfb_up,
            tfb_down=tfb_down,
            vol_regime=vol_regime,
            edge_score=edge_score,
            prob_up=prob_up,  # Use actual market probability
        )

        logger.info(
            f"[{self.name}] EDGE_SCORE v1.0: "
            f"decision_ready={decision_ready}, "
            f"edge_score={edge_score:.3f}, "
            f"market_prob_up={prob_up:.3f} (actual), "
            f"calculated_prob={_calculated_prob_up:.3f} (ignored)"
        )

        if not decision_ready:
            logger.warning(f"[{self.name}] Hard gate triggered: {debug.get('gate', 'unknown')}")

        return signals

    def _compute_obi(self, book) -> float:
        """
        Compute Order Book Imbalance
        OBI = (bid_volume - ask_volume) / (bid_volume + ask_volume)
        Using top 3 levels as per spec
        """
        bids = book.bids[:3]
        asks = book.asks[:3]

        bid_volume = sum(level.size for level in bids)
        ask_volume = sum(level.size for level in asks)

        total = bid_volume + ask_volume
        if total == 0:
            return 0.0

        obi = (bid_volume - ask_volume) / total
        return max(-1.0, min(1.0, obi))

    def _compute_momentum(self, book: BookSnapshot) -> tuple[Optional[float], Optional[float]]:
        """
        Compute price momentum (deltas) using Binance BTC klines
        
        ΔP1 = (current_price - price_1min_ago) / price_1min_ago
        ΔP3 = (current_price - price_3min_ago) / price_3min_ago
        
        Returns momentum as probability-space deltas (small values like 0.01 = 1%)
        """
        try:
            binance = get_binance_client()
            if binance is None:
                logger.warning("[SIGNAL_ENGINE] No Binance client - momentum unavailable")
                return None, None
            
            # Get recent 1-minute klines (need at least 4 for 3-min lookback)
            klines = binance.client.get_klines("BTCUSDT", interval="1m", limit=5)
            
            if len(klines) < 4:
                logger.warning("[SIGNAL_ENGINE] Insufficient klines for momentum")
                return None, None
            
            # Current price (latest close)
            current_price = klines[-1].close
            
            # Price 1 minute ago
            price_1min = klines[-2].close
            
            # Price 3 minutes ago
            price_3min = klines[-4].close
            
            # Calculate momentum as percentage change
            # Scaled to probability space (0.01 = 1% move)
            delta_p1 = (current_price - price_1min) / price_1min if price_1min > 0 else 0
            delta_p3 = (current_price - price_3min) / price_3min if price_3min > 0 else 0
            
            logger.info(
                f"[SIGNAL_ENGINE] BTC momentum: "
                f"price=${current_price:,.2f}, "
                f"ΔP1={delta_p1*100:.3f}%, "
                f"ΔP3={delta_p3*100:.3f}%"
            )
            
            return delta_p1, delta_p3
            
        except Exception as e:
            logger.error(f"[SIGNAL_ENGINE] Momentum calculation failed: {e}")
            return None, None

    def _compute_tfb(self, trades: list) -> float:
        """
        Compute Trade Flow Bias
        TFB = (buy_volume - sell_volume) / (buy_volume + sell_volume)
        """
        buy_volume = sum(t.size for t in trades if t.side == "buy")
        sell_volume = sum(t.size for t in trades if t.side == "sell")

        total = buy_volume + sell_volume
        if total == 0:
            return 0.0

        tfb = (buy_volume - sell_volume) / total
        return max(-1.0, min(1.0, tfb))

    def _classify_volatility(self, market: MarketSnapshot) -> VolatilityRegime:
        """
        Classify volatility regime using BTC price data from Binance
        
        Uses 15-minute realized volatility (standard deviation of returns)
        """
        try:
            binance = get_binance_client()
            if binance is None:
                # Fallback to spread-based proxy
                return self._classify_volatility_from_spread(market)
            
            # Get recent 1-minute klines for volatility calculation
            klines = binance.client.get_klines("BTCUSDT", interval="1m", limit=15)
            
            if len(klines) < 10:
                return self._classify_volatility_from_spread(market)
            
            # Calculate returns
            closes = [k.close for k in klines]
            returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
            
            # Realized volatility (standard deviation of returns)
            mean_return = sum(returns) / len(returns)
            variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
            vol = variance ** 0.5
            
            # Annualized (multiply by sqrt of periods per year)
            # 1-min bars, ~525600 per year
            annualized_vol = vol * (525600 ** 0.5)
            
            logger.info(f"[SIGNAL_ENGINE] BTC realized vol: {vol*100:.4f}% (1m), annualized: {annualized_vol*100:.1f}%")
            
            # Classify based on annualized vol
            if annualized_vol < 30:  # < 30% annualized = low vol
                return VolatilityRegime.LOW
            elif annualized_vol > 60:  # > 60% annualized = high vol
                return VolatilityRegime.HIGH
            else:
                return VolatilityRegime.MID
                
        except Exception as e:
            logger.warning(f"[SIGNAL_ENGINE] Vol classification failed: {e}")
            return self._classify_volatility_from_spread(market)
    
    def _classify_volatility_from_spread(self, market: MarketSnapshot) -> VolatilityRegime:
        """Fallback: classify volatility from Polymarket spread width"""
        if market.up_spread is None:
            return VolatilityRegime.UNKNOWN

        if market.up_spread < 0.015:
            return VolatilityRegime.LOW
        elif market.up_spread > 0.025:
            return VolatilityRegime.HIGH
        else:
            return VolatilityRegime.MID
