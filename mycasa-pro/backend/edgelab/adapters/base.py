"""
Base adapter interface for Edge Lab data sources

All adapters must implement this interface to ensure consistent
data ingestion across different sources (Polygon, Alpaca, IEX, Yahoo, etc.)
"""

from abc import ABC, abstractmethod
from datetime import datetime, date
from typing import Dict, List, Any, Optional, Type
from dataclasses import dataclass


@dataclass
class SymbolMetadata:
    """Symbol metadata from adapter"""
    symbol: str
    name: Optional[str] = None
    exchange: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap: Optional[float] = None
    float_shares: Optional[float] = None
    is_etf: Optional[bool] = None
    is_adr: Optional[bool] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "exchange": self.exchange,
            "sector": self.sector,
            "industry": self.industry,
            "market_cap": self.market_cap,
            "float_shares": self.float_shares,
            "is_etf": self.is_etf,
            "is_adr": self.is_adr,
        }


@dataclass
class DailyBar:
    """Daily OHLCV bar from adapter"""
    symbol: str
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: float
    vwap: Optional[float] = None
    
    @property
    def dollar_volume(self) -> float:
        return self.close * self.volume
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "date": self.date.isoformat(),
            "o": self.open,
            "h": self.high,
            "l": self.low,
            "c": self.close,
            "v": self.volume,
            "vw": self.vwap,
            "dollar_vol": self.dollar_volume,
        }


class BaseAdapter(ABC):
    """
    Base class for all data adapters.
    
    Adapters are responsible for:
    1. Fetching universe of symbols based on policy rules
    2. Fetching daily bars for symbols
    3. Fetching symbol metadata
    """
    
    name: str = "base"
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
    
    @abstractmethod
    def fetch_universe(
        self,
        as_of: datetime,
        rules: Dict[str, Any]
    ) -> List[SymbolMetadata]:
        """
        Fetch list of symbols matching universe rules.
        
        Args:
            as_of: Point-in-time for universe snapshot
            rules: Universe policy rules (min_price, min_dollar_vol, etc.)
            
        Returns:
            List of SymbolMetadata for matching symbols
        """
        pass
    
    @abstractmethod
    def fetch_daily_bars(
        self,
        symbols: List[str],
        start_date: date,
        end_date: date
    ) -> Dict[str, List[DailyBar]]:
        """
        Fetch daily OHLCV bars for symbols.
        
        Args:
            symbols: List of symbols to fetch
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            
        Returns:
            Dict mapping symbol to list of DailyBar
        """
        pass
    
    @abstractmethod
    def fetch_symbol_metadata(
        self,
        symbols: List[str]
    ) -> Dict[str, SymbolMetadata]:
        """
        Fetch detailed metadata for symbols.
        
        Args:
            symbols: List of symbols
            
        Returns:
            Dict mapping symbol to SymbolMetadata
        """
        pass
    
    def validate_bars(self, bars: List[DailyBar]) -> List[str]:
        """
        Validate bar data quality.
        
        Returns list of warning messages.
        """
        warnings = []
        
        if not bars:
            warnings.append("No bars returned")
            return warnings
        
        # Check for missing data
        for bar in bars:
            if bar.volume <= 0:
                warnings.append(f"{bar.symbol} {bar.date}: zero volume")
            if bar.close <= 0:
                warnings.append(f"{bar.symbol} {bar.date}: zero/negative close")
            if bar.high < bar.low:
                warnings.append(f"{bar.symbol} {bar.date}: high < low")
            if bar.close > bar.high or bar.close < bar.low:
                warnings.append(f"{bar.symbol} {bar.date}: close outside range")
        
        return warnings


class AdapterRegistry:
    """Registry of available data adapters"""
    
    _adapters: Dict[str, Type[BaseAdapter]] = {}
    
    @classmethod
    def register(cls, adapter_class: Type[BaseAdapter]):
        """Register an adapter class"""
        cls._adapters[adapter_class.name] = adapter_class
        return adapter_class
    
    @classmethod
    def get(cls, name: str, config: Optional[Dict[str, Any]] = None) -> BaseAdapter:
        """Get adapter instance by name"""
        if name not in cls._adapters:
            raise ValueError(f"Unknown adapter: {name}. Available: {list(cls._adapters.keys())}")
        return cls._adapters[name](config)
    
    @classmethod
    def list_adapters(cls) -> List[str]:
        """List available adapter names"""
        return list(cls._adapters.keys())
