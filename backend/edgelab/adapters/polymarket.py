"""
Polymarket adapter for Edge Lab.

Fetches prediction market data from Polymarket's APIs:
- Gamma API: Market discovery, metadata, events
- CLOB API: Prices, orderbooks, trading
- Data API: Positions and history

No API key required for read-only market data.
"""

import httpx
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from .base import BaseAdapter, AdapterRegistry, SymbolMetadata, DailyBar

logger = logging.getLogger(__name__)


# Polymarket API endpoints
GAMMA_API_BASE = "https://gamma-api.polymarket.com"
CLOB_API_BASE = "https://clob.polymarket.com"
DATA_API_BASE = "https://data-api.polymarket.com"


@dataclass
class PolymarketEvent:
    """Polymarket event (collection of markets)"""
    id: str
    ticker: str
    slug: str
    title: str
    description: str
    category: str
    active: bool
    closed: bool
    volume: float
    liquidity: float
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    markets: List["PolymarketMarket"] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "ticker": self.ticker,
            "slug": self.slug,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "active": self.active,
            "closed": self.closed,
            "volume": self.volume,
            "liquidity": self.liquidity,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "markets": [m.to_dict() for m in self.markets],
        }


@dataclass
class PolymarketMarket:
    """Individual Polymarket prediction market"""
    id: str
    question: str
    slug: str
    condition_id: str
    outcomes: List[str]
    outcome_prices: List[float]
    volume: float
    liquidity: float
    active: bool
    closed: bool
    category: str
    end_date: Optional[datetime] = None
    clob_token_ids: List[str] = field(default_factory=list)
    best_bid: float = 0.0
    best_ask: float = 1.0
    spread: float = 1.0
    
    @property
    def yes_price(self) -> float:
        """Price for YES outcome (probability)"""
        if self.outcome_prices and len(self.outcome_prices) > 0:
            return self.outcome_prices[0]
        return 0.5
    
    @property
    def no_price(self) -> float:
        """Price for NO outcome"""
        if self.outcome_prices and len(self.outcome_prices) > 1:
            return self.outcome_prices[1]
        return 1.0 - self.yes_price
    
    @property
    def implied_probability(self) -> float:
        """Implied probability from YES price"""
        return self.yes_price
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "question": self.question,
            "slug": self.slug,
            "condition_id": self.condition_id,
            "outcomes": self.outcomes,
            "outcome_prices": self.outcome_prices,
            "yes_price": self.yes_price,
            "no_price": self.no_price,
            "implied_probability": self.implied_probability,
            "volume": self.volume,
            "liquidity": self.liquidity,
            "active": self.active,
            "closed": self.closed,
            "category": self.category,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "clob_token_ids": self.clob_token_ids,
            "best_bid": self.best_bid,
            "best_ask": self.best_ask,
            "spread": self.spread,
        }


class PolymarketClient:
    """
    Client for Polymarket APIs.
    
    Supports:
    - Gamma API for market discovery and metadata
    - CLOB API for live prices and orderbooks
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
    
    # ========== Gamma API Methods ==========
    
    def get_events(
        self,
        active: bool = True,
        closed: bool = False,
        limit: int = 100,
        offset: int = 0,
        category: Optional[str] = None,
        order: str = "volume",
        ascending: bool = False
    ) -> List[PolymarketEvent]:
        """
        Get list of events from Gamma API.
        
        Args:
            active: Include active events
            closed: Include closed events
            limit: Max results
            offset: Pagination offset
            category: Filter by category (Sports, Politics, Crypto, etc.)
            order: Sort field (volume, liquidity, endDate, startDate)
            ascending: Sort direction
        """
        params = {
            "active": str(active).lower(),
            "closed": str(closed).lower(),
            "limit": limit,
            "offset": offset,
            "order": order,
            "ascending": str(ascending).lower(),
        }
        
        if category:
            params["tag"] = category
        
        try:
            resp = self.client.get(f"{GAMMA_API_BASE}/events", params=params)
            resp.raise_for_status()
            data = resp.json()
            
            events = []
            for item in data:
                event = self._parse_event(item)
                if event:
                    events.append(event)
            
            return events
            
        except Exception as e:
            logger.error(f"Error fetching events: {e}")
            return []
    
    def get_event(self, event_id: str) -> Optional[PolymarketEvent]:
        """Get single event by ID"""
        try:
            resp = self.client.get(f"{GAMMA_API_BASE}/events/{event_id}")
            resp.raise_for_status()
            return self._parse_event(resp.json())
        except Exception as e:
            logger.error(f"Error fetching event {event_id}: {e}")
            return None
    
    def get_markets(
        self,
        active: bool = True,
        closed: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[PolymarketMarket]:
        """Get list of markets from Gamma API"""
        params = {
            "active": str(active).lower(),
            "closed": str(closed).lower(),
            "limit": limit,
            "offset": offset,
        }
        
        try:
            resp = self.client.get(f"{GAMMA_API_BASE}/markets", params=params)
            resp.raise_for_status()
            data = resp.json()
            
            markets = []
            for item in data:
                market = self._parse_market(item)
                if market:
                    markets.append(market)
            
            return markets
            
        except Exception as e:
            logger.error(f"Error fetching markets: {e}")
            return []
    
    def search_markets(self, query: str, limit: int = 50) -> List[PolymarketMarket]:
        """Search markets by text query"""
        params = {
            "q": query,
            "limit": limit,
        }
        
        try:
            resp = self.client.get(f"{GAMMA_API_BASE}/markets", params=params)
            resp.raise_for_status()
            data = resp.json()
            
            return [self._parse_market(m) for m in data if m]
            
        except Exception as e:
            logger.error(f"Error searching markets: {e}")
            return []
    
    # ========== CLOB API Methods ==========
    
    def get_price(self, token_id: str) -> Optional[Dict[str, float]]:
        """
        Get current price for a token from CLOB API.
        
        Args:
            token_id: The CLOB token ID (from market.clob_token_ids)
        
        Returns:
            Dict with 'price', 'bid', 'ask' if successful
        """
        try:
            resp = self.client.get(
                f"{CLOB_API_BASE}/price",
                params={"token_id": token_id}
            )
            resp.raise_for_status()
            data = resp.json()
            
            return {
                "price": float(data.get("price", 0)),
                "mid": float(data.get("mid", 0)),
            }
            
        except Exception as e:
            logger.error(f"Error fetching price for {token_id}: {e}")
            return None
    
    def get_midpoint(self, token_id: str) -> Optional[float]:
        """Get midpoint price for a token"""
        try:
            resp = self.client.get(
                f"{CLOB_API_BASE}/midpoint",
                params={"token_id": token_id}
            )
            resp.raise_for_status()
            data = resp.json()
            return float(data.get("mid", 0))
        except Exception as e:
            logger.error(f"Error fetching midpoint for {token_id}: {e}")
            return None
    
    def get_orderbook(self, token_id: str) -> Optional[Dict[str, Any]]:
        """
        Get full orderbook for a token.
        
        Returns:
            Dict with 'bids' and 'asks' arrays
        """
        try:
            resp = self.client.get(
                f"{CLOB_API_BASE}/book",
                params={"token_id": token_id}
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Error fetching orderbook for {token_id}: {e}")
            return None
    
    # ========== Parsing Helpers ==========
    
    def _parse_event(self, data: Dict[str, Any]) -> Optional[PolymarketEvent]:
        """Parse event data from API response"""
        try:
            markets = []
            for m in data.get("markets", []):
                market = self._parse_market(m)
                if market:
                    markets.append(market)
            
            return PolymarketEvent(
                id=str(data.get("id", "")),
                ticker=data.get("ticker", ""),
                slug=data.get("slug", ""),
                title=data.get("title", ""),
                description=data.get("description", ""),
                category=data.get("category", ""),
                active=data.get("active", False),
                closed=data.get("closed", False),
                volume=float(data.get("volume", 0) or 0),
                liquidity=float(data.get("liquidity", 0) or 0),
                start_date=self._parse_date(data.get("startDate")),
                end_date=self._parse_date(data.get("endDate")),
                markets=markets,
            )
        except Exception as e:
            logger.warning(f"Error parsing event: {e}")
            return None
    
    def _parse_market(self, data: Dict[str, Any]) -> Optional[PolymarketMarket]:
        """Parse market data from API response"""
        try:
            # Parse outcomes
            outcomes_raw = data.get("outcomes", "[]")
            if isinstance(outcomes_raw, str):
                import json
                outcomes = json.loads(outcomes_raw)
            else:
                outcomes = outcomes_raw
            
            # Parse outcome prices
            prices_raw = data.get("outcomePrices", "[]")
            if isinstance(prices_raw, str):
                import json
                prices = [float(p) for p in json.loads(prices_raw)]
            else:
                prices = [float(p) for p in (prices_raw or [])]
            
            # Parse CLOB token IDs
            tokens_raw = data.get("clobTokenIds", "[]")
            if isinstance(tokens_raw, str):
                import json
                tokens = json.loads(tokens_raw)
            else:
                tokens = tokens_raw or []
            
            return PolymarketMarket(
                id=str(data.get("id", "")),
                question=data.get("question", ""),
                slug=data.get("slug", ""),
                condition_id=data.get("conditionId", ""),
                outcomes=outcomes,
                outcome_prices=prices,
                volume=float(data.get("volume", 0) or data.get("volumeNum", 0) or 0),
                liquidity=float(data.get("liquidity", 0) or data.get("liquidityNum", 0) or 0),
                active=data.get("active", False),
                closed=data.get("closed", False),
                category=data.get("category", ""),
                end_date=self._parse_date(data.get("endDate")),
                clob_token_ids=tokens,
                best_bid=float(data.get("bestBid", 0) or 0),
                best_ask=float(data.get("bestAsk", 1) or 1),
                spread=float(data.get("spread", 1) or 1),
            )
        except Exception as e:
            logger.warning(f"Error parsing market: {e}")
            return None
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse ISO date string"""
        if not date_str:
            return None
        try:
            # Handle various ISO formats
            if date_str.endswith('Z'):
                date_str = date_str[:-1] + '+00:00'
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except Exception:
            return None


@AdapterRegistry.register
class PolymarketAdapter(BaseAdapter):
    """
    Polymarket prediction market adapter for Edge Lab.
    
    Provides access to prediction market data:
    - Event and market discovery
    - Live prices and probabilities  
    - Orderbook data
    - Volume and liquidity metrics
    
    Useful for:
    - Sentiment indicators (what does the market think?)
    - Event risk hedging
    - Alternative data signals
    """
    
    name = "polymarket"
    
    # Categories available on Polymarket
    CATEGORIES = [
        "Politics",
        "Sports", 
        "Crypto",
        "Pop Culture",
        "Business",
        "Science",
    ]
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.client = PolymarketClient(
            timeout=config.get("timeout", 30) if config else 30
        )
    
    def fetch_universe(
        self,
        as_of: datetime,
        rules: Dict[str, Any]
    ) -> List[SymbolMetadata]:
        """
        Fetch universe of prediction markets.
        
        Note: Returns markets as "symbols" with ticker as the identifier.
        """
        min_volume = rules.get("min_volume", 0)
        min_liquidity = rules.get("min_liquidity", 0)
        categories = rules.get("categories", self.CATEGORIES)
        
        events = self.client.get_events(
            active=True,
            limit=500,
            order="volume",
            ascending=False
        )
        
        result = []
        for event in events:
            # Filter by category
            if event.category not in categories:
                continue
            
            # Filter by volume
            if event.volume < min_volume:
                continue
            
            # Filter by liquidity
            if event.liquidity < min_liquidity:
                continue
            
            result.append(SymbolMetadata(
                symbol=event.ticker,
                name=event.title,
                sector=event.category,
                market_cap=event.volume,  # Use volume as proxy for "market cap"
            ))
        
        return result
    
    def fetch_daily_bars(
        self,
        symbols: List[str],
        start_date: date,
        end_date: date
    ) -> Dict[str, List[DailyBar]]:
        """
        Prediction markets don't have OHLCV bars in the traditional sense.
        This returns empty for now - use get_market_prices for live data.
        """
        logger.info(
            "PolymarketAdapter doesn't support historical bars. "
            "Use get_markets_by_category or get_market_prices for live data."
        )
        return {}
    
    def fetch_symbol_metadata(
        self,
        symbols: List[str]
    ) -> Dict[str, SymbolMetadata]:
        """Fetch metadata for market tickers"""
        result = {}
        
        # Search for each symbol
        for symbol in symbols:
            markets = self.client.search_markets(symbol, limit=1)
            if markets:
                market = markets[0]
                result[symbol] = SymbolMetadata(
                    symbol=market.slug,
                    name=market.question,
                    sector=market.category,
                    market_cap=market.volume,
                )
        
        return result
    
    # ========== Polymarket-specific methods ==========
    
    def get_top_markets(
        self,
        category: Optional[str] = None,
        limit: int = 20
    ) -> List[PolymarketMarket]:
        """
        Get top markets by volume.
        
        Args:
            category: Optional category filter
            limit: Max markets to return
        """
        events = self.client.get_events(
            active=True,
            limit=limit * 2,  # Get extra to filter
            order="volume",
            ascending=False,
            category=category
        )
        
        markets = []
        for event in events:
            markets.extend(event.markets)
            if len(markets) >= limit:
                break
        
        return markets[:limit]
    
    def get_market_price(self, market: PolymarketMarket) -> Dict[str, Any]:
        """
        Get live price data for a market.
        
        Returns yes/no prices, spread, and orderbook summary.
        """
        if not market.clob_token_ids:
            return {
                "market_id": market.id,
                "question": market.question,
                "yes_price": market.yes_price,
                "no_price": market.no_price,
                "source": "gamma"  # From cached Gamma API data
            }
        
        # Get live price from CLOB for YES token
        yes_token = market.clob_token_ids[0] if market.clob_token_ids else None
        
        if yes_token:
            price_data = self.client.get_price(yes_token)
            if price_data:
                return {
                    "market_id": market.id,
                    "question": market.question,
                    "yes_price": price_data.get("price", market.yes_price),
                    "no_price": 1.0 - price_data.get("price", market.yes_price),
                    "mid": price_data.get("mid"),
                    "source": "clob"  # Live CLOB data
                }
        
        return {
            "market_id": market.id,
            "question": market.question,
            "yes_price": market.yes_price,
            "no_price": market.no_price,
            "source": "gamma"
        }
    
    def get_politics_markets(self, limit: int = 20) -> List[PolymarketMarket]:
        """Get top politics prediction markets"""
        return self.get_top_markets(category="Politics", limit=limit)
    
    def get_crypto_markets(self, limit: int = 20) -> List[PolymarketMarket]:
        """Get top crypto prediction markets"""
        return self.get_top_markets(category="Crypto", limit=limit)
    
    def get_sports_markets(self, limit: int = 20) -> List[PolymarketMarket]:
        """Get top sports prediction markets"""
        return self.get_top_markets(category="Sports", limit=limit)
    
    def search_markets(self, query: str, limit: int = 20) -> List[PolymarketMarket]:
        """Search markets by text query"""
        return self.client.search_markets(query, limit=limit)
    
    def get_market_sentiment(self, keywords: List[str]) -> Dict[str, Any]:
        """
        Aggregate sentiment from markets matching keywords.
        
        Useful for getting "wisdom of crowds" on topics like:
        - Company earnings ("AAPL earnings beat")
        - Economic events ("Fed rate cut")
        - Crypto events ("ETH ETF approval")
        
        Returns aggregated probabilities and confidence metrics.
        """
        all_markets = []
        for keyword in keywords:
            markets = self.search_markets(keyword, limit=10)
            all_markets.extend(markets)
        
        if not all_markets:
            return {"keywords": keywords, "markets_found": 0, "sentiment": None}
        
        # Calculate weighted average sentiment
        total_volume = sum(m.volume for m in all_markets)
        if total_volume == 0:
            avg_probability = sum(m.yes_price for m in all_markets) / len(all_markets)
        else:
            avg_probability = sum(
                m.yes_price * m.volume for m in all_markets
            ) / total_volume
        
        return {
            "keywords": keywords,
            "markets_found": len(all_markets),
            "weighted_avg_probability": avg_probability,
            "total_volume": total_volume,
            "markets": [
                {
                    "question": m.question,
                    "yes_price": m.yes_price,
                    "volume": m.volume,
                    "category": m.category,
                }
                for m in sorted(all_markets, key=lambda x: x.volume, reverse=True)[:5]
            ]
        }
    
    def cleanup(self):
        """Close HTTP client"""
        self.client.close()
