"""
Binance adapter for Edge Lab.

Fetches live crypto prices from Binance public API.
No API key required for public market data.
"""

import httpx
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from .base import BaseAdapter, AdapterRegistry, SymbolMetadata, DailyBar

logger = logging.getLogger(__name__)

# Binance API endpoints
BINANCE_API_BASE = "https://api.binance.com"
BINANCE_FAPI_BASE = "https://fapi.binance.com"  # Futures


@dataclass
class BinanceTicker:
    """Binance ticker data"""
    symbol: str
    price: float
    price_change: float
    price_change_pct: float
    high_24h: float
    low_24h: float
    volume_24h: float
    quote_volume_24h: float
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "price": self.price,
            "price_change": self.price_change,
            "price_change_pct": self.price_change_pct,
            "high_24h": self.high_24h,
            "low_24h": self.low_24h,
            "volume_24h": self.volume_24h,
            "quote_volume_24h": self.quote_volume_24h,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class BinanceKline:
    """Binance kline/candlestick data"""
    symbol: str
    open_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    close_time: datetime
    quote_volume: float
    trades: int
    
    def to_daily_bar(self) -> DailyBar:
        return DailyBar(
            symbol=self.symbol,
            date=self.open_time.date(),
            open=self.open,
            high=self.high,
            low=self.low,
            close=self.close,
            volume=self.volume,
        )


class BinanceClient:
    """
    Client for Binance public API.
    
    No authentication required for market data.
    """
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self._client = None
    
    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=self.timeout)
        return self._client
    
    def close(self):
        if self._client:
            self._client.close()
            self._client = None
    
    def get_ticker_24h(self, symbol: str) -> Optional[BinanceTicker]:
        """
        Get 24h ticker for a symbol.
        
        Args:
            symbol: Trading pair (e.g., "BTCUSDT", "ETHUSDT")
        """
        try:
            resp = self.client.get(
                f"{BINANCE_API_BASE}/api/v3/ticker/24hr",
                params={"symbol": symbol.upper()}
            )
            resp.raise_for_status()
            data = resp.json()
            
            return BinanceTicker(
                symbol=data["symbol"],
                price=float(data["lastPrice"]),
                price_change=float(data["priceChange"]),
                price_change_pct=float(data["priceChangePercent"]),
                high_24h=float(data["highPrice"]),
                low_24h=float(data["lowPrice"]),
                volume_24h=float(data["volume"]),
                quote_volume_24h=float(data["quoteVolume"]),
                timestamp=datetime.fromtimestamp(data["closeTime"] / 1000),
            )
        except Exception as e:
            logger.error(f"Error fetching ticker for {symbol}: {e}")
            return None
    
    def get_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol"""
        try:
            resp = self.client.get(
                f"{BINANCE_API_BASE}/api/v3/ticker/price",
                params={"symbol": symbol.upper()}
            )
            resp.raise_for_status()
            return float(resp.json()["price"])
        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {e}")
            return None
    
    def get_all_prices(self) -> Dict[str, float]:
        """Get prices for all symbols"""
        try:
            resp = self.client.get(f"{BINANCE_API_BASE}/api/v3/ticker/price")
            resp.raise_for_status()
            return {item["symbol"]: float(item["price"]) for item in resp.json()}
        except Exception as e:
            logger.error(f"Error fetching all prices: {e}")
            return {}
    
    def get_klines(
        self,
        symbol: str,
        interval: str = "1d",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 500
    ) -> List[BinanceKline]:
        """
        Get klines/candlesticks for a symbol.
        
        Args:
            symbol: Trading pair
            interval: Kline interval (1m, 5m, 15m, 1h, 4h, 1d, 1w, 1M)
            start_time: Start time
            end_time: End time
            limit: Max klines (default 500, max 1000)
        """
        params = {
            "symbol": symbol.upper(),
            "interval": interval,
            "limit": min(limit, 1000),
        }
        
        if start_time:
            params["startTime"] = int(start_time.timestamp() * 1000)
        if end_time:
            params["endTime"] = int(end_time.timestamp() * 1000)
        
        try:
            resp = self.client.get(f"{BINANCE_API_BASE}/api/v3/klines", params=params)
            resp.raise_for_status()
            
            klines = []
            for k in resp.json():
                klines.append(BinanceKline(
                    symbol=symbol.upper(),
                    open_time=datetime.fromtimestamp(k[0] / 1000),
                    open=float(k[1]),
                    high=float(k[2]),
                    low=float(k[3]),
                    close=float(k[4]),
                    volume=float(k[5]),
                    close_time=datetime.fromtimestamp(k[6] / 1000),
                    quote_volume=float(k[7]),
                    trades=int(k[8]),
                ))
            
            return klines
        except Exception as e:
            logger.error(f"Error fetching klines for {symbol}: {e}")
            return []
    
    def get_orderbook(self, symbol: str, limit: int = 20) -> Optional[Dict[str, Any]]:
        """Get orderbook for a symbol"""
        try:
            resp = self.client.get(
                f"{BINANCE_API_BASE}/api/v3/depth",
                params={"symbol": symbol.upper(), "limit": limit}
            )
            resp.raise_for_status()
            data = resp.json()
            
            return {
                "bids": [[float(p), float(q)] for p, q in data["bids"]],
                "asks": [[float(p), float(q)] for p, q in data["asks"]],
                "last_update_id": data["lastUpdateId"],
            }
        except Exception as e:
            logger.error(f"Error fetching orderbook for {symbol}: {e}")
            return None
    
    def get_recent_trades(self, symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent trades for a symbol"""
        try:
            resp = self.client.get(
                f"{BINANCE_API_BASE}/api/v3/trades",
                params={"symbol": symbol.upper(), "limit": limit}
            )
            resp.raise_for_status()
            
            return [
                {
                    "id": t["id"],
                    "price": float(t["price"]),
                    "qty": float(t["qty"]),
                    "time": datetime.fromtimestamp(t["time"] / 1000).isoformat(),
                    "is_buyer_maker": t["isBuyerMaker"],
                }
                for t in resp.json()
            ]
        except Exception as e:
            logger.error(f"Error fetching trades for {symbol}: {e}")
            return []


@AdapterRegistry.register
class BinanceAdapter(BaseAdapter):
    """
    Binance crypto price adapter for Edge Lab.
    
    Provides:
    - Live crypto prices (BTC, ETH, etc.)
    - 24h ticker statistics
    - Historical kline/candlestick data
    - Orderbook depth
    
    No API key required for public data.
    """
    
    name = "binance"
    
    # Common crypto pairs
    DEFAULT_SYMBOLS = [
        "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
        "DOGEUSDT", "ADAUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT",
    ]
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.client = BinanceClient(
            timeout=config.get("timeout", 30) if config else 30
        )
    
    def fetch_universe(
        self,
        as_of: datetime,
        rules: Dict[str, Any]
    ) -> List[SymbolMetadata]:
        """Fetch crypto universe"""
        min_volume = rules.get("min_volume_usdt", 0)
        quote_asset = rules.get("quote_asset", "USDT")
        
        # Get all prices to filter
        prices = self.client.get_all_prices()
        
        result = []
        for symbol, price in prices.items():
            # Filter by quote asset
            if not symbol.endswith(quote_asset):
                continue
            
            base_asset = symbol[:-len(quote_asset)]
            
            # Get 24h ticker for volume
            ticker = self.client.get_ticker_24h(symbol)
            if ticker and ticker.quote_volume_24h >= min_volume:
                result.append(SymbolMetadata(
                    symbol=symbol,
                    name=base_asset,
                    exchange="BINANCE",
                    market_cap=ticker.quote_volume_24h,  # Use 24h volume as proxy
                ))
        
        return result
    
    def fetch_daily_bars(
        self,
        symbols: List[str],
        start_date: date,
        end_date: date
    ) -> Dict[str, List[DailyBar]]:
        """Fetch daily OHLCV bars from Binance"""
        result = {}
        
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())
        
        for symbol in symbols:
            klines = self.client.get_klines(
                symbol=symbol,
                interval="1d",
                start_time=start_dt,
                end_time=end_dt,
                limit=1000
            )
            
            result[symbol] = [k.to_daily_bar() for k in klines]
        
        return result
    
    def fetch_symbol_metadata(
        self,
        symbols: List[str]
    ) -> Dict[str, SymbolMetadata]:
        """Fetch metadata for crypto symbols"""
        result = {}
        
        for symbol in symbols:
            ticker = self.client.get_ticker_24h(symbol)
            if ticker:
                # Extract base asset from pair
                base = symbol.replace("USDT", "").replace("BTC", "").replace("ETH", "")
                result[symbol] = SymbolMetadata(
                    symbol=symbol,
                    name=base,
                    exchange="BINANCE",
                    market_cap=ticker.quote_volume_24h,
                )
        
        return result
    
    # ========== Binance-specific methods ==========
    
    def get_btc_price(self) -> Dict[str, Any]:
        """Get current BTC/USDT price with 24h stats"""
        ticker = self.client.get_ticker_24h("BTCUSDT")
        if ticker:
            return ticker.to_dict()
        return {"error": "Failed to fetch BTC price"}
    
    def get_eth_price(self) -> Dict[str, Any]:
        """Get current ETH/USDT price with 24h stats"""
        ticker = self.client.get_ticker_24h("ETHUSDT")
        if ticker:
            return ticker.to_dict()
        return {"error": "Failed to fetch ETH price"}
    
    def get_crypto_prices(self, symbols: List[str] = None) -> Dict[str, float]:
        """
        Get current prices for multiple crypto pairs.
        
        Args:
            symbols: List of pairs (e.g., ["BTCUSDT", "ETHUSDT"])
                    If None, returns default symbols
        """
        if symbols is None:
            symbols = self.DEFAULT_SYMBOLS
        
        result = {}
        for symbol in symbols:
            price = self.client.get_price(symbol)
            if price is not None:
                result[symbol] = price
        
        return result
    
    def get_btc_klines(
        self,
        interval: str = "15m",
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get BTC/USDT klines for prediction analysis.
        
        Args:
            interval: 1m, 5m, 15m, 1h, 4h, 1d
            limit: Number of klines
        """
        klines = self.client.get_klines("BTCUSDT", interval=interval, limit=limit)
        return [
            {
                "time": k.open_time.isoformat(),
                "open": k.open,
                "high": k.high,
                "low": k.low,
                "close": k.close,
                "volume": k.volume,
            }
            for k in klines
        ]
    
    def get_orderbook_imbalance(self, symbol: str = "BTCUSDT", depth: int = 20) -> Dict[str, Any]:
        """
        Calculate orderbook imbalance for a symbol.
        
        Useful for short-term price prediction.
        """
        book = self.client.get_orderbook(symbol, limit=depth)
        if not book:
            return {"error": "Failed to fetch orderbook"}
        
        bid_volume = sum(qty for _, qty in book["bids"])
        ask_volume = sum(qty for _, qty in book["asks"])
        total_volume = bid_volume + ask_volume
        
        imbalance = (bid_volume - ask_volume) / total_volume if total_volume > 0 else 0
        
        return {
            "symbol": symbol,
            "bid_volume": bid_volume,
            "ask_volume": ask_volume,
            "imbalance": imbalance,  # Positive = more buyers, Negative = more sellers
            "imbalance_pct": imbalance * 100,
            "best_bid": book["bids"][0][0] if book["bids"] else None,
            "best_ask": book["asks"][0][0] if book["asks"] else None,
            "spread": book["asks"][0][0] - book["bids"][0][0] if book["bids"] and book["asks"] else None,
        }
    
    def cleanup(self):
        """Close HTTP client"""
        self.client.close()
