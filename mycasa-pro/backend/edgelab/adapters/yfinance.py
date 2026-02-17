"""
Yahoo Finance adapter for Edge Lab

Uses yfinance library to fetch real market data.
Free tier, no API key required.
"""

from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional
import logging

from .base import BaseAdapter, AdapterRegistry, SymbolMetadata, DailyBar

logger = logging.getLogger(__name__)


@AdapterRegistry.register
class YFinanceAdapter(BaseAdapter):
    """
    Yahoo Finance data adapter.
    
    Fetches real market data using the yfinance library.
    Note: Has rate limits and may be slower than paid APIs.
    """
    
    name = "yfinance"
    
    # Default US liquid universe (can be overridden)
    DEFAULT_UNIVERSE = [
        # Mega caps
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B",
        "JPM", "V", "JNJ", "WMT", "PG", "XOM", "UNH", "MA", "HD", "CVX",
        "ABBV", "CRM", "KO", "PEP", "MRK", "COST", "TMO", "AVGO", "CSCO",
        "ACN", "MCD", "ABT", "NKE", "DHR", "TXN", "NEE", "PM", "UNP",
        # Large caps
        "AMD", "INTC", "QCOM", "AMAT", "ADI", "LRCX", "MU", "KLAC",
        "NFLX", "ADBE", "PYPL", "SQ", "SHOP", "NOW", "INTU", "SNOW",
        "GS", "MS", "BAC", "C", "WFC", "AXP", "BLK", "SCHW", "CME",
        "LLY", "PFE", "BMY", "GILD", "AMGN", "VRTX", "REGN", "MRNA",
        # SPY for benchmark
        "SPY",
    ]
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._yf = None
    
    @property
    def yf(self):
        """Lazy load yfinance"""
        if self._yf is None:
            try:
                import yfinance as yf
                self._yf = yf
            except ImportError:
                raise ImportError(
                    "yfinance not installed. Run: pip install yfinance"
                )
        return self._yf
    
    def fetch_universe(
        self,
        as_of: datetime,
        rules: Dict[str, Any]
    ) -> List[SymbolMetadata]:
        """
        Fetch universe based on rules.
        
        Note: yfinance doesn't have a screener API, so we filter
        from a predefined list of liquid US stocks.
        """
        min_price = rules.get("min_price", 0)
        exclude_etfs = rules.get("exclude_etfs", False)
        exchanges = rules.get("exchanges", [])
        min_dollar_vol = rules.get("min_avg_dollar_vol_20d", 0)
        
        # Get universe to check
        universe = self.config.get("universe", self.DEFAULT_UNIVERSE)
        
        result = []
        
        # Batch download tickers
        try:
            tickers = self.yf.Tickers(" ".join(universe))
            
            for symbol in universe:
                try:
                    ticker = tickers.tickers.get(symbol)
                    if not ticker:
                        continue
                    
                    info = ticker.info
                    
                    # Check ETF exclusion
                    quote_type = info.get("quoteType", "")
                    is_etf = quote_type == "ETF"
                    if exclude_etfs and is_etf:
                        continue
                    
                    # Check exchange
                    exchange = info.get("exchange", "")
                    if exchanges:
                        # Map Yahoo exchanges to standard names
                        exchange_map = {
                            "NMS": "NASDAQ", "NGM": "NASDAQ", "NCM": "NASDAQ",
                            "NYQ": "NYSE", "NYS": "NYSE",
                        }
                        mapped_exchange = exchange_map.get(exchange, exchange)
                        if mapped_exchange not in exchanges:
                            continue
                    
                    # Check price
                    current_price = info.get("regularMarketPrice") or info.get("previousClose", 0)
                    if current_price < min_price:
                        continue
                    
                    # Check dollar volume
                    avg_vol = info.get("averageVolume", 0) or 0
                    dollar_vol = avg_vol * current_price
                    if dollar_vol < min_dollar_vol:
                        continue
                    
                    result.append(SymbolMetadata(
                        symbol=symbol,
                        name=info.get("longName") or info.get("shortName"),
                        exchange=exchange,
                        sector=info.get("sector"),
                        industry=info.get("industry"),
                        market_cap=info.get("marketCap"),
                        float_shares=info.get("floatShares"),
                        is_etf=is_etf,
                        is_adr=info.get("quoteType") == "ADR",
                    ))
                    
                except Exception as e:
                    logger.warning(f"Error fetching {symbol}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error fetching universe: {e}")
            raise
        
        return result
    
    def fetch_daily_bars(
        self,
        symbols: List[str],
        start_date: date,
        end_date: date
    ) -> Dict[str, List[DailyBar]]:
        """Fetch daily bars using yfinance"""
        result = {}
        
        # Convert dates to strings for yfinance
        start_str = start_date.isoformat()
        end_str = (end_date + timedelta(days=1)).isoformat()  # yfinance end is exclusive
        
        try:
            # Download all at once for efficiency
            data = self.yf.download(
                symbols,
                start=start_str,
                end=end_str,
                group_by="ticker",
                auto_adjust=True,
                threads=True,
            )
            
            if len(symbols) == 1:
                # Single symbol has different structure
                symbol = symbols[0]
                result[symbol] = []
                for idx, row in data.iterrows():
                    if not row.isna().all():
                        result[symbol].append(DailyBar(
                            symbol=symbol,
                            date=idx.date(),
                            open=float(row["Open"]),
                            high=float(row["High"]),
                            low=float(row["Low"]),
                            close=float(row["Close"]),
                            volume=float(row["Volume"]),
                            vwap=None,  # yfinance doesn't provide VWAP
                        ))
            else:
                # Multiple symbols
                for symbol in symbols:
                    result[symbol] = []
                    if symbol in data.columns.get_level_values(0):
                        symbol_data = data[symbol]
                        for idx, row in symbol_data.iterrows():
                            if not row.isna().all():
                                result[symbol].append(DailyBar(
                                    symbol=symbol,
                                    date=idx.date(),
                                    open=float(row["Open"]),
                                    high=float(row["High"]),
                                    low=float(row["Low"]),
                                    close=float(row["Close"]),
                                    volume=float(row["Volume"]),
                                    vwap=None,
                                ))
                    
        except Exception as e:
            logger.error(f"Error fetching bars: {e}")
            raise
        
        return result
    
    def fetch_symbol_metadata(
        self,
        symbols: List[str]
    ) -> Dict[str, SymbolMetadata]:
        """Fetch detailed metadata for symbols"""
        result = {}
        
        try:
            tickers = self.yf.Tickers(" ".join(symbols))
            
            for symbol in symbols:
                try:
                    ticker = tickers.tickers.get(symbol)
                    if not ticker:
                        continue
                    
                    info = ticker.info
                    
                    result[symbol] = SymbolMetadata(
                        symbol=symbol,
                        name=info.get("longName") or info.get("shortName"),
                        exchange=info.get("exchange"),
                        sector=info.get("sector"),
                        industry=info.get("industry"),
                        market_cap=info.get("marketCap"),
                        float_shares=info.get("floatShares"),
                        is_etf=info.get("quoteType") == "ETF",
                        is_adr=info.get("quoteType") == "ADR",
                    )
                    
                except Exception as e:
                    logger.warning(f"Error fetching metadata for {symbol}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error fetching metadata: {e}")
            raise
        
        return result
