"""
Mock adapter for testing

Generates deterministic fake data for testing the Edge Lab pipeline.
"""

import random
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional

from .base import BaseAdapter, AdapterRegistry, SymbolMetadata, DailyBar


@AdapterRegistry.register
class MockAdapter(BaseAdapter):
    """
    Mock data adapter for testing.
    
    Generates deterministic data based on symbol hash for reproducibility.
    """
    
    name = "mock"
    
    # Fake universe of stocks
    MOCK_SYMBOLS = [
        ("AAPL", "Apple Inc", "NASDAQ", "Technology", "Consumer Electronics", 3_000_000_000_000),
        ("MSFT", "Microsoft Corp", "NASDAQ", "Technology", "Software", 2_800_000_000_000),
        ("GOOGL", "Alphabet Inc", "NASDAQ", "Technology", "Internet Services", 1_800_000_000_000),
        ("AMZN", "Amazon.com Inc", "NASDAQ", "Consumer Cyclical", "E-Commerce", 1_600_000_000_000),
        ("NVDA", "NVIDIA Corp", "NASDAQ", "Technology", "Semiconductors", 1_200_000_000_000),
        ("META", "Meta Platforms", "NASDAQ", "Technology", "Social Media", 900_000_000_000),
        ("TSLA", "Tesla Inc", "NASDAQ", "Consumer Cyclical", "Auto Manufacturers", 800_000_000_000),
        ("JPM", "JPMorgan Chase", "NYSE", "Financial Services", "Banks", 500_000_000_000),
        ("V", "Visa Inc", "NYSE", "Financial Services", "Payments", 480_000_000_000),
        ("JNJ", "Johnson & Johnson", "NYSE", "Healthcare", "Pharmaceuticals", 450_000_000_000),
        ("WMT", "Walmart Inc", "NYSE", "Consumer Defensive", "Retail", 400_000_000_000),
        ("PG", "Procter & Gamble", "NYSE", "Consumer Defensive", "Household Products", 380_000_000_000),
        ("XOM", "Exxon Mobil", "NYSE", "Energy", "Oil & Gas", 350_000_000_000),
        ("UNH", "UnitedHealth", "NYSE", "Healthcare", "Health Plans", 480_000_000_000),
        ("MA", "Mastercard Inc", "NYSE", "Financial Services", "Payments", 400_000_000_000),
        ("HD", "Home Depot", "NYSE", "Consumer Cyclical", "Home Improvement", 350_000_000_000),
        ("CVX", "Chevron Corp", "NYSE", "Energy", "Oil & Gas", 300_000_000_000),
        ("ABBV", "AbbVie Inc", "NYSE", "Healthcare", "Pharmaceuticals", 290_000_000_000),
        ("CRM", "Salesforce Inc", "NYSE", "Technology", "Software", 250_000_000_000),
        ("KO", "Coca-Cola Co", "NYSE", "Consumer Defensive", "Beverages", 260_000_000_000),
        ("SPY", "SPDR S&P 500 ETF", "NYSE", None, None, None),  # ETF
    ]
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self._seed = config.get("seed", 42) if config else 42
    
    def _get_symbol_seed(self, symbol: str) -> int:
        """Get deterministic seed for symbol"""
        return hash(symbol) + self._seed
    
    def _generate_price(self, symbol: str, base_date: date, days_back: int = 0) -> float:
        """Generate deterministic price for symbol on date"""
        random.seed(self._get_symbol_seed(symbol) + (base_date - timedelta(days=days_back)).toordinal())
        
        # Base price varies by symbol
        base_prices = {
            "AAPL": 180, "MSFT": 400, "GOOGL": 150, "AMZN": 180, "NVDA": 500,
            "META": 400, "TSLA": 250, "JPM": 180, "V": 270, "JNJ": 160,
            "WMT": 170, "PG": 160, "XOM": 110, "UNH": 520, "MA": 450,
            "HD": 350, "CVX": 160, "ABBV": 180, "CRM": 280, "KO": 60,
            "SPY": 500,
        }
        base = base_prices.get(symbol, 100)
        
        # Add some variation based on date
        variation = random.uniform(-0.05, 0.05) * base
        return round(base + variation, 2)
    
    def fetch_universe(
        self,
        as_of: datetime,
        rules: Dict[str, Any]
    ) -> List[SymbolMetadata]:
        """Fetch filtered universe based on rules"""
        result = []
        
        min_price = rules.get("min_price", 0)
        exclude_etfs = rules.get("exclude_etfs", False)
        exchanges = rules.get("exchanges", [])
        
        for symbol, name, exchange, sector, industry, market_cap in self.MOCK_SYMBOLS:
            # Check ETF exclusion
            if exclude_etfs and symbol == "SPY":
                continue
            
            # Check exchange filter
            if exchanges and exchange not in exchanges:
                continue
            
            # Check price
            price = self._generate_price(symbol, as_of.date())
            if price < min_price:
                continue
            
            result.append(SymbolMetadata(
                symbol=symbol,
                name=name,
                exchange=exchange,
                sector=sector,
                industry=industry,
                market_cap=market_cap,
                float_shares=market_cap / price if market_cap else None,
                is_etf=symbol == "SPY",
                is_adr=False,
            ))
        
        return result
    
    def fetch_daily_bars(
        self,
        symbols: List[str],
        start_date: date,
        end_date: date
    ) -> Dict[str, List[DailyBar]]:
        """Fetch daily bars for symbols"""
        result = {}
        
        current = start_date
        while current <= end_date:
            # Skip weekends
            if current.weekday() >= 5:
                current += timedelta(days=1)
                continue
            
            for symbol in symbols:
                if symbol not in result:
                    result[symbol] = []
                
                close = self._generate_price(symbol, current)
                random.seed(self._get_symbol_seed(symbol) + current.toordinal())
                
                # Generate OHLV based on close
                daily_range = close * random.uniform(0.01, 0.03)
                high = close + daily_range * random.uniform(0.3, 0.7)
                low = close - daily_range * random.uniform(0.3, 0.7)
                open_price = low + (high - low) * random.uniform(0.2, 0.8)
                
                # Volume varies by market cap
                base_volume = 10_000_000 + hash(symbol) % 50_000_000
                volume = base_volume * random.uniform(0.5, 2.0)
                
                result[symbol].append(DailyBar(
                    symbol=symbol,
                    date=current,
                    open=round(open_price, 2),
                    high=round(high, 2),
                    low=round(low, 2),
                    close=close,
                    volume=int(volume),
                    vwap=round((high + low + close) / 3, 2),
                ))
            
            current += timedelta(days=1)
        
        return result
    
    def fetch_symbol_metadata(
        self,
        symbols: List[str]
    ) -> Dict[str, SymbolMetadata]:
        """Fetch metadata for specific symbols"""
        result = {}
        
        symbol_data = {s[0]: s for s in self.MOCK_SYMBOLS}
        
        for symbol in symbols:
            if symbol in symbol_data:
                _, name, exchange, sector, industry, market_cap = symbol_data[symbol]
                result[symbol] = SymbolMetadata(
                    symbol=symbol,
                    name=name,
                    exchange=exchange,
                    sector=sector,
                    industry=industry,
                    market_cap=market_cap,
                    is_etf=symbol == "SPY",
                    is_adr=False,
                )
        
        return result
