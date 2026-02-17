"""Data adapters for Edge Lab"""

from .base import BaseAdapter, AdapterRegistry, SymbolMetadata, DailyBar
from .mock import MockAdapter
from .yfinance import YFinanceAdapter
from .browser import BrowserAdapter, AgentBrowserClient, BrowserScrapeResult
from .polymarket import (
    PolymarketAdapter,
    PolymarketClient,
    PolymarketEvent,
    PolymarketMarket,
)
from .binance import (
    BinanceAdapter,
    BinanceClient,
    BinanceTicker,
    BinanceKline,
)

__all__ = [
    # Base
    "BaseAdapter",
    "AdapterRegistry",
    "SymbolMetadata",
    "DailyBar",
    # Adapters
    "MockAdapter",
    "YFinanceAdapter",
    "BrowserAdapter",
    "PolymarketAdapter",
    "BinanceAdapter",
    # Browser utilities
    "AgentBrowserClient",
    "BrowserScrapeResult",
    # Polymarket types
    "PolymarketClient",
    "PolymarketEvent",
    "PolymarketMarket",
    # Binance types
    "BinanceClient",
    "BinanceTicker",
    "BinanceKline",
]
