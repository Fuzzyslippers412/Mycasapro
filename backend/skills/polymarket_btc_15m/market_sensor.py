"""
MARKET_SENSOR Agent
Extracts market state from Polymarket page
"""
from typing import Dict, Any, Optional
from datetime import datetime
import logging

from .schemas import MarketSnapshot, OrderBookLevel, Trade

logger = logging.getLogger(__name__)


class MarketSensor:
    """
    Extracts all visible market state from Polymarket page

    Authority: Can only use browser tools (snapshot, dom_extract)
    Output: MarketSnapshot JSON only
    """

    def __init__(self):
        self.name = "MARKET_SENSOR"

    async def extract_market_snapshot(
        self,
        market_url: str,
        page_data: Optional[Dict[str, Any]] = None
    ) -> MarketSnapshot:
        """
        Extract market snapshot from page data

        Args:
            market_url: Market URL
            page_data: Page DOM/snapshot data (simulated for now)

        Returns:
            MarketSnapshot
        """
        logger.info(f"[{self.name}] Extracting market snapshot from {market_url}")

        # In production, this would use agent_browser.snapshot + dom_extract
        # For now, we'll create a mock extraction that shows the structure

        if page_data is None:
            # Mock data structure - in production this comes from browser tools
            page_data = self._get_mock_page_data(market_url)

        # Extract and normalize all fields
        snapshot = MarketSnapshot(
            captured_at_iso=datetime.utcnow().isoformat(),
            market_url=market_url,
            market_title=page_data.get("title", "Bitcoin Up or Down in 15 minutes"),
            market_id=page_data.get("market_id"),

            # Outcomes
            up_label=page_data.get("up_label", "UP"),
            down_label=page_data.get("down_label", "DOWN"),
            yes_means_up=page_data.get("yes_means_up", True),

            # Prices (normalized to [0,1])
            up_prob=self._normalize_price(page_data.get("up_price")),
            down_prob=self._normalize_price(page_data.get("down_price")),

            # Spreads
            up_spread=page_data.get("up_spread"),
            down_spread=page_data.get("down_spread"),
            up_best_bid=self._normalize_price(page_data.get("up_best_bid")),
            up_best_ask=self._normalize_price(page_data.get("up_best_ask")),
            down_best_bid=self._normalize_price(page_data.get("down_best_bid")),
            down_best_ask=self._normalize_price(page_data.get("down_best_ask")),

            # Liquidity
            volume_24h_usd=page_data.get("volume_24h"),
            total_volume_usd=page_data.get("total_volume"),
            open_interest_usd=page_data.get("open_interest"),

            # Time
            time_remaining_seconds=self._parse_time_remaining(
                page_data.get("time_remaining")
            ),

            # Order book from page
            up_bids=self._parse_order_book_levels(page_data.get("up_bids", [])),
            up_asks=self._parse_order_book_levels(page_data.get("up_asks", [])),
            down_bids=self._parse_order_book_levels(page_data.get("down_bids", [])),
            down_asks=self._parse_order_book_levels(page_data.get("down_asks", [])),

            # Recent trades
            recent_trades=self._parse_trades(page_data.get("recent_trades", [])),
        )

        logger.info(
            f"[{self.name}] Extracted snapshot: "
            f"up_prob={snapshot.up_prob:.3f}, "
            f"time_remaining={snapshot.time_remaining_seconds}s"
        )

        return snapshot

    def _normalize_price(self, price: Optional[Any]) -> Optional[float]:
        """Normalize price to [0, 1] probability"""
        if price is None:
            return None

        try:
            p = float(price)
            # If price is in cents (0-100), convert to probability
            if p > 1.0:
                p = p / 100.0
            return max(0.0, min(1.0, p))
        except (ValueError, TypeError):
            return None

    def _parse_time_remaining(self, time_str: Optional[Any]) -> Optional[int]:
        """Parse time remaining string to seconds"""
        if time_str is None:
            return None

        if isinstance(time_str, int):
            return time_str

        # Parse strings like "14:30" (MM:SS) or "900" (seconds)
        try:
            if ":" in str(time_str):
                parts = str(time_str).split(":")
                minutes = int(parts[0])
                seconds = int(parts[1]) if len(parts) > 1 else 0
                return minutes * 60 + seconds
            return int(time_str)
        except (ValueError, AttributeError):
            return None

    def _parse_order_book_levels(
        self,
        levels: list
    ) -> list[OrderBookLevel]:
        """Parse order book levels"""
        result = []
        for level in levels:
            if isinstance(level, dict):
                price = self._normalize_price(level.get("price"))
                size = level.get("size", 0)
                if price is not None and size > 0:
                    result.append(OrderBookLevel(price_prob=price, size=float(size)))
        return result

    def _parse_trades(self, trades: list) -> list[Trade]:
        """Parse recent trades"""
        result = []
        for trade in trades:
            if isinstance(trade, dict):
                side = trade.get("side", "unknown")
                price = self._normalize_price(trade.get("price"))
                size = trade.get("size", 0)
                time_iso = trade.get("time", datetime.utcnow().isoformat())

                if price is not None and size > 0:
                    result.append(Trade(
                        side=side if side in ["buy", "sell"] else "unknown",
                        price_prob=price,
                        size=float(size),
                        time_iso=time_iso
                    ))
        return result

    def _get_mock_page_data(self, market_url: str) -> Dict[str, Any]:
        """
        Mock page data for testing
        In production, this comes from agent_browser tools
        """
        return {
            "title": "Bitcoin Up or Down in 15 minutes",
            "market_id": "0x1234567890abcdef",
            "up_label": "UP",
            "down_label": "DOWN",
            "yes_means_up": True,
            "up_price": 0.52,  # 52 cents = 52% probability
            "down_price": 0.48,
            "up_best_bid": 0.515,
            "up_best_ask": 0.525,
            "down_best_bid": 0.475,
            "down_best_ask": 0.485,
            "up_spread": 0.01,
            "down_spread": 0.01,
            "volume_24h": 125000.0,
            "total_volume": 450000.0,
            "open_interest": 85000.0,
            "time_remaining": "12:30",  # 12 minutes 30 seconds
            "up_bids": [
                {"price": 0.515, "size": 1500},
                {"price": 0.510, "size": 2200},
                {"price": 0.505, "size": 1800},
            ],
            "up_asks": [
                {"price": 0.525, "size": 1200},
                {"price": 0.530, "size": 2000},
                {"price": 0.535, "size": 1600},
            ],
            "down_bids": [
                {"price": 0.475, "size": 1400},
                {"price": 0.470, "size": 1900},
                {"price": 0.465, "size": 1500},
            ],
            "down_asks": [
                {"price": 0.485, "size": 1300},
                {"price": 0.490, "size": 1700},
                {"price": 0.495, "size": 1400},
            ],
            "recent_trades": [
                {"side": "buy", "price": 0.520, "size": 500, "time": "2026-01-31T13:45:22Z"},
                {"side": "buy", "price": 0.518, "size": 300, "time": "2026-01-31T13:45:15Z"},
                {"side": "sell", "price": 0.516, "size": 200, "time": "2026-01-31T13:45:08Z"},
            ],
        }
