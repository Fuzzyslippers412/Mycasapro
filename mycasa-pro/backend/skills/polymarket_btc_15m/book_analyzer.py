"""
BOOK_ANALYZER Agent
Retrieves and normalizes order book + recent trades
"""
from typing import Optional
from datetime import datetime
import logging

from .schemas import BookSnapshot, OrderBook, OrderBookLevel, MarketSnapshot

logger = logging.getLogger(__name__)


class BookAnalyzer:
    """
    Retrieves order book and recent trades

    Authority: May request CLOB endpoints if granted by orchestrator
    Output: BookSnapshot JSON only
    """

    def __init__(self):
        self.name = "BOOK_ANALYZER"

    async def analyze_book(
        self,
        market_snapshot: MarketSnapshot
    ) -> BookSnapshot:
        """
        Analyze order book from market snapshot

        Args:
            market_snapshot: Market data from MARKET_SENSOR

        Returns:
            BookSnapshot with normalized book data
        """
        logger.info(f"[{self.name}] Analyzing order book")

        # Use page-visible order book data (prioritize what's on page)
        # In production, could also fetch from polymarket_clob if needed

        # Convert raw arrays [[price, size], ...] to OrderBookLevel objects
        def convert_to_levels(raw_levels):
            """Convert [[price, size], ...] arrays to OrderBookLevel objects"""
            levels = []
            for level in raw_levels:
                if isinstance(level, list) and len(level) >= 2:
                    levels.append(OrderBookLevel(
                        price_prob=float(level[0]),
                        size=float(level[1])
                    ))
            return levels

        snapshot = BookSnapshot(
            captured_at_iso=datetime.utcnow().isoformat(),
            up_token_id=None,  # Would extract from market_id if available
            down_token_id=None,

            up_book=OrderBook(
                bids=convert_to_levels(market_snapshot.up_bids[:10]),  # Top 10 levels
                asks=convert_to_levels(market_snapshot.up_asks[:10]),
            ),
            down_book=OrderBook(
                bids=convert_to_levels(market_snapshot.down_bids[:10]),
                asks=convert_to_levels(market_snapshot.down_asks[:10]),
            ),

            # Partition trades by outcome
            up_recent_trades=self._filter_trades_by_outcome(
                market_snapshot.recent_trades, "up", market_snapshot.yes_means_up
            ),
            down_recent_trades=self._filter_trades_by_outcome(
                market_snapshot.recent_trades, "down", market_snapshot.yes_means_up
            ),
        )

        logger.info(
            f"[{self.name}] Book snapshot: "
            f"up_bids={len(snapshot.up_book.bids)}, "
            f"up_asks={len(snapshot.up_book.asks)}, "
            f"up_trades={len(snapshot.up_recent_trades)}"
        )

        return snapshot

    def _filter_trades_by_outcome(self, trades, outcome, yes_means_up):
        """
        Filter trades by outcome
        For BTC markets, "buy" typically means buying UP outcome
        """
        # Simple heuristic: buy side = UP, sell side = DOWN
        if outcome == "up":
            return [t for t in trades if t.side == "buy"]
        else:
            return [t for t in trades if t.side == "sell"]
