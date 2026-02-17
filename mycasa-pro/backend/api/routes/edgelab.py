"""
EdgeLab API Routes
Data acquisition via browser automation and prediction market APIs

Provides:
- Browser scraping via agent-browser CLI / Clawd Chrome extension
- Polymarket prediction market data and sentiment analysis
- Live quotes and market overview
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/edgelab", tags=["edgelab"])


# ════════════════════════════════════════════════════════════════════════════
# REQUEST/RESPONSE MODELS
# ════════════════════════════════════════════════════════════════════════════

class LiveQuoteRequest(BaseModel):
    """Request for live quote scraping"""
    symbol: str = Field(..., description="Stock/ETF symbol")
    use_chrome_relay: bool = Field(False, description="Use Clawd Chrome extension for authenticated sites")


class LiveQuoteResponse(BaseModel):
    """Live quote response"""
    symbol: str
    price: Optional[str] = None
    change: Optional[str] = None
    change_pct: Optional[str] = None
    volume: Optional[str] = None
    market_cap: Optional[str] = None
    timestamp: Optional[str] = None
    source: Optional[str] = None
    error: Optional[str] = None


class NewsHeadline(BaseModel):
    """News headline"""
    title: str
    url: str


class PolymarketSearchRequest(BaseModel):
    """Request for Polymarket search"""
    query: str = Field(..., description="Search query")
    limit: int = Field(10, ge=1, le=50, description="Max results")


class PolymarketSentimentRequest(BaseModel):
    """Request for sentiment analysis"""
    keywords: List[str] = Field(..., description="Keywords to analyze sentiment for")


class PolymarketMarket(BaseModel):
    """Polymarket market data"""
    id: str
    question: str
    slug: str
    yes_price: float
    no_price: float
    implied_probability: float
    volume: float
    liquidity: float
    category: str
    active: bool
    closed: bool


class PolymarketSentimentResponse(BaseModel):
    """Sentiment analysis response"""
    keywords: List[str]
    markets_found: int
    weighted_avg_probability: Optional[float] = None
    total_volume: Optional[float] = None
    markets: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None


class AdapterStatusResponse(BaseModel):
    """Adapter availability status"""
    edgelab_available: bool
    adapters: List[str]
    browser_adapter: bool
    polymarket_adapter: bool
    yfinance_adapter: bool


# ════════════════════════════════════════════════════════════════════════════
# BROWSER SCRAPING ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════

@router.post("/browser/quote", response_model=LiveQuoteResponse)
async def scrape_live_quote(request: LiveQuoteRequest) -> Dict[str, Any]:
    """
    Scrape live quote for a symbol using browser automation.
    
    Uses agent-browser CLI to scrape Yahoo Finance.
    Can use Clawd Chrome extension for sites requiring authentication.
    """
    try:
        from agents.finance import FinanceAgent
        
        agent = FinanceAgent()
        result = await agent.scrape_live_quote(
            symbol=request.symbol,
            use_chrome_relay=request.use_chrome_relay
        )
        
        logger.info(f"Scraped quote for {request.symbol}")
        return result
        
    except Exception as e:
        logger.error(f"Quote scrape failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/browser/news", response_model=List[NewsHeadline])
async def scrape_news(
    symbol: Optional[str] = Query(None, description="Symbol for news (None = market news)")
) -> List[Dict[str, str]]:
    """
    Scrape market news headlines.
    
    If symbol provided, gets news for that symbol.
    If no symbol, gets general market news.
    """
    try:
        from agents.finance import FinanceAgent
        
        agent = FinanceAgent()
        headlines = await agent.scrape_market_news(symbol=symbol)
        
        logger.info(f"Scraped {len(headlines)} headlines for {symbol or 'market'}")
        return headlines
        
    except Exception as e:
        logger.error(f"News scrape failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/browser/overview")
async def scrape_market_overview() -> Dict[str, Any]:
    """
    Scrape overall market overview.
    
    Returns indices, sector performance, market breadth data.
    """
    try:
        from agents.finance import FinanceAgent
        
        agent = FinanceAgent()
        overview = await agent.scrape_market_overview()
        
        logger.info("Scraped market overview")
        return overview
        
    except Exception as e:
        logger.error(f"Overview scrape failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ════════════════════════════════════════════════════════════════════════════
# POLYMARKET ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════

@router.get("/polymarket/markets")
async def get_polymarket_markets(
    category: Optional[str] = Query(None, description="Category filter (Politics, Crypto, Sports, etc.)"),
    limit: int = Query(10, ge=1, le=50, description="Max markets to return")
) -> List[Dict[str, Any]]:
    """
    Get top prediction markets from Polymarket by volume.
    
    Categories: Politics, Crypto, Sports, Pop Culture, Business, Science
    """
    try:
        from agents.finance import FinanceAgent
        
        agent = FinanceAgent()
        markets = await agent.get_polymarket_top_markets(category=category, limit=limit)
        
        logger.info(f"Fetched {len(markets)} Polymarket markets")
        return markets
        
    except Exception as e:
        logger.error(f"Polymarket fetch failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/polymarket/search")
async def search_polymarket_markets(request: PolymarketSearchRequest) -> List[Dict[str, Any]]:
    """
    Search Polymarket markets by text query.
    
    Useful for finding markets about specific topics.
    """
    try:
        from agents.finance import FinanceAgent
        
        agent = FinanceAgent()
        markets = await agent.search_polymarket(query=request.query, limit=request.limit)
        
        logger.info(f"Searched Polymarket for '{request.query}', found {len(markets)}")
        return markets
        
    except Exception as e:
        logger.error(f"Polymarket search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/polymarket/price/{market_slug}")
async def get_polymarket_price(market_slug: str) -> Dict[str, Any]:
    """
    Get live price for a specific Polymarket market.
    
    Returns yes/no prices, volume, and probability.
    """
    try:
        from agents.finance import FinanceAgent
        
        agent = FinanceAgent()
        price_data = await agent.get_polymarket_price(market_slug)
        
        if "error" in price_data:
            raise HTTPException(status_code=404, detail=price_data["error"])
        
        logger.info(f"Fetched Polymarket price for {market_slug}")
        return price_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Polymarket price fetch failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/polymarket/sentiment", response_model=PolymarketSentimentResponse)
async def analyze_polymarket_sentiment(request: PolymarketSentimentRequest) -> Dict[str, Any]:
    """
    Analyze aggregated sentiment from Polymarket for keywords.
    
    Aggregates probabilities from all matching markets weighted by volume.
    
    Useful for:
    - Company earnings ("AAPL earnings beat")
    - Economic events ("Fed rate cut")
    - Crypto events ("ETH ETF approval")
    """
    try:
        from agents.finance import FinanceAgent
        
        agent = FinanceAgent()
        sentiment = await agent.get_polymarket_sentiment(keywords=request.keywords)
        
        if "error" in sentiment:
            logger.warning(f"Sentiment analysis error: {sentiment['error']}")
        else:
            logger.info(f"Analyzed sentiment for {request.keywords}")
        
        return sentiment
        
    except Exception as e:
        logger.error(f"Sentiment analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ════════════════════════════════════════════════════════════════════════════
# BINANCE ENDPOINTS (Crypto Prices)
# ════════════════════════════════════════════════════════════════════════════

@router.get("/binance/btc")
async def get_btc_price() -> Dict[str, Any]:
    """
    Get current BTC/USDT price with 24h statistics.
    
    Returns price, 24h change, high/low, volume.
    """
    try:
        from ...edgelab.adapters import BinanceAdapter
        
        adapter = BinanceAdapter()
        result = adapter.get_btc_price()
        adapter.cleanup()
        
        logger.info(f"Fetched BTC price: ${result.get('price', 'N/A')}")
        return result
        
    except Exception as e:
        logger.error(f"BTC price fetch failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/binance/eth")
async def get_eth_price() -> Dict[str, Any]:
    """
    Get current ETH/USDT price with 24h statistics.
    """
    try:
        from ...edgelab.adapters import BinanceAdapter
        
        adapter = BinanceAdapter()
        result = adapter.get_eth_price()
        adapter.cleanup()
        
        logger.info(f"Fetched ETH price: ${result.get('price', 'N/A')}")
        return result
        
    except Exception as e:
        logger.error(f"ETH price fetch failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/binance/prices")
async def get_crypto_prices(
    symbols: Optional[str] = Query(None, description="Comma-separated symbols (e.g., BTCUSDT,ETHUSDT)")
) -> Dict[str, float]:
    """
    Get current prices for multiple crypto pairs.
    
    Default: BTC, ETH, BNB, SOL, XRP, DOGE, ADA, AVAX, LINK, DOT
    """
    try:
        from ...edgelab.adapters import BinanceAdapter
        
        adapter = BinanceAdapter()
        
        symbol_list = None
        if symbols:
            symbol_list = [s.strip().upper() for s in symbols.split(",")]
        
        result = adapter.get_crypto_prices(symbol_list)
        adapter.cleanup()
        
        logger.info(f"Fetched {len(result)} crypto prices")
        return result
        
    except Exception as e:
        logger.error(f"Crypto prices fetch failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/binance/klines/{symbol}")
async def get_klines(
    symbol: str,
    interval: str = Query("15m", description="Interval: 1m, 5m, 15m, 1h, 4h, 1d"),
    limit: int = Query(100, ge=1, le=1000, description="Number of klines")
) -> List[Dict[str, Any]]:
    """
    Get klines/candlesticks for a crypto pair.
    
    Useful for technical analysis and price prediction.
    """
    try:
        from ...edgelab.adapters import BinanceAdapter
        
        adapter = BinanceAdapter()
        klines = adapter.client.get_klines(symbol.upper(), interval=interval, limit=limit)
        adapter.cleanup()
        
        result = [
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
        
        logger.info(f"Fetched {len(result)} klines for {symbol}")
        return result
        
    except Exception as e:
        logger.error(f"Klines fetch failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/binance/orderbook/{symbol}")
async def get_orderbook_imbalance(
    symbol: str,
    depth: int = Query(20, ge=5, le=100, description="Orderbook depth")
) -> Dict[str, Any]:
    """
    Get orderbook imbalance for a crypto pair.
    
    Positive imbalance = more buyers (bullish)
    Negative imbalance = more sellers (bearish)
    
    Useful for short-term price prediction.
    """
    try:
        from ...edgelab.adapters import BinanceAdapter
        
        adapter = BinanceAdapter()
        result = adapter.get_orderbook_imbalance(symbol.upper(), depth=depth)
        adapter.cleanup()
        
        logger.info(f"Orderbook imbalance for {symbol}: {result.get('imbalance_pct', 0):.2f}%")
        return result
        
    except Exception as e:
        logger.error(f"Orderbook fetch failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ════════════════════════════════════════════════════════════════════════════
# CLAWDBOT BROWSER RELAY ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════

@router.get("/browser/polymarket-cached")
async def get_cached_polymarket_data() -> Dict[str, Any]:
    """
    Get the most recently cached Polymarket data from Galidima.
    
    This reads from ~/clawd/apps/mycasa-pro/data/polymarket_latest.json
    which is updated by Galidima when user requests browser fetch.
    """
    import json
    from pathlib import Path
    
    cache_file = Path.home() / "clawd" / "apps" / "mycasa-pro" / "data" / "polymarket_latest.json"
    
    try:
        if cache_file.exists():
            with open(cache_file) as f:
                data = json.load(f)
            
            return {
                "success": True,
                "data": data,
                "source": "cache",
                "cache_file": str(cache_file)
            }
        else:
            return {
                "success": False,
                "error": "No cached data. Ask Galidima to fetch from browser first.",
                "code": "NO_CACHE"
            }
    except Exception as e:
        logger.error(f"Error reading cached data: {e}")
        return {
            "success": False,
            "error": str(e),
            "code": "READ_ERROR"
        }


@router.get("/browser/polymarket-snapshot")
async def fetch_polymarket_from_chrome() -> Dict[str, Any]:
    """
    Fetch Polymarket BTC 15m market data from the attached Chrome tab.
    
    Uses Clawdbot's browser relay (Chrome extension) to grab data
    directly from the user's open Polymarket page.
    
    Returns structured market data ready for EDGE_SCORE analysis.
    
    Prerequisites:
    - Clawdbot gateway running
    - Chrome extension installed
    - Polymarket BTC market tab attached (click extension icon)
    """
    try:
        from ...edgelab.clawdbot_client import fetch_polymarket_from_browser
        
        result = await fetch_polymarket_from_browser()
        
        if result.get("success"):
            logger.info(f"Fetched Polymarket data from browser: {result['data'].get('market_title', 'unknown')}")
        else:
            logger.warning(f"Browser fetch failed: {result.get('error')}")
        
        return result
        
    except Exception as e:
        logger.error(f"Polymarket browser fetch failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/browser/polymarket-analyze")
async def analyze_polymarket_from_chrome(bankroll_usd: float = 5000) -> Dict[str, Any]:
    """
    Fetch Polymarket data from Chrome AND run EDGE_SCORE analysis.
    
    One-click: grabs data from attached tab and returns UP/DOWN prediction.
    
    Args:
        bankroll_usd: Bankroll for bet sizing calculation
    
    Returns:
        Analysis result with call, confidence, reasons, and bet sizing
    """
    try:
        from ...edgelab.clawdbot_client import fetch_polymarket_from_browser
        
        # Step 1: Fetch market data from browser
        fetch_result = await fetch_polymarket_from_browser()
        
        if not fetch_result.get("success"):
            return {
                "success": False,
                "step": "fetch",
                "error": fetch_result.get("error"),
                "code": fetch_result.get("code"),
            }
        
        market_data = fetch_result["data"]
        
        # Step 2: Run EDGE_SCORE analysis
        try:
            from agents.finance import FinanceAgent
            agent = FinanceAgent()
            
            # Convert browser data to analysis format
            analysis_input = {
                "captured_at_iso": None,
                "market_url": market_data.get("market_url", ""),
                "market_title": market_data.get("market_title", ""),
                "up_prob": market_data.get("up_prob", 0.5),
                "down_prob": market_data.get("down_prob", 0.5),
                "btc_current_price": market_data.get("btc_price"),
                "price_to_beat": market_data.get("price_to_beat"),
                "time_remaining_seconds": (
                    (market_data.get("time_remaining_minutes") or 0) * 60 +
                    (market_data.get("time_remaining_seconds") or 0)
                ),
                "volume_24h_usd": market_data.get("volume"),
            }
            
            analysis_result = await agent.analyze_polymarket_direction(
                market_data=analysis_input,
                market_url=None
            )
            
            return {
                "success": True,
                "market_data": market_data,
                "analysis": analysis_result,
                "source": "chrome_relay"
            }
            
        except ImportError:
            # Finance agent not available, return raw data
            return {
                "success": True,
                "market_data": market_data,
                "analysis": None,
                "warning": "Finance agent not available for analysis",
                "source": "chrome_relay"
            }
        
    except Exception as e:
        logger.error(f"Polymarket analyze failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ════════════════════════════════════════════════════════════════════════════
# STATUS/UTILITY ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════

@router.get("/status", response_model=AdapterStatusResponse)
async def get_edgelab_status() -> Dict[str, Any]:
    """
    Check EdgeLab adapter availability.
    
    Returns which adapters are available and ready to use.
    """
    try:
        from ...edgelab.adapters import AdapterRegistry
        
        adapters = AdapterRegistry.list_adapters()
        browser_ok = "browser" in adapters
        polymarket_ok = "polymarket" in adapters
        yfinance_ok = "yfinance" in adapters
        binance_ok = "binance" in adapters
        
        return {
            "edgelab_available": True,
            "adapters": adapters,
            "browser_adapter": browser_ok,
            "polymarket_adapter": polymarket_ok,
            "yfinance_adapter": yfinance_ok,
            "binance_adapter": binance_ok,
        }
        
    except Exception as e:
        logger.error(f"Status check failed: {e}", exc_info=True)
        return {
            "edgelab_available": False,
            "adapters": [],
            "browser_adapter": False,
            "polymarket_adapter": False,
            "yfinance_adapter": False,
            "binance_adapter": False,
        }


@router.get("/adapters")
async def list_adapters() -> Dict[str, Any]:
    """
    List all available EdgeLab adapters with their capabilities.
    """
    try:
        from ...edgelab.adapters import AdapterRegistry
        
        adapter_info = {}
        for name in AdapterRegistry.list_adapters():
            adapter_info[name] = {
                "name": name,
                "available": True,
            }
        
        # Add capabilities info
        if "browser" in adapter_info:
            adapter_info["browser"]["capabilities"] = [
                "live_quotes",
                "news_scraping", 
                "market_overview",
                "chrome_relay_support",
            ]
        
        if "polymarket" in adapter_info:
            adapter_info["polymarket"]["capabilities"] = [
                "market_discovery",
                "live_prices",
                "sentiment_analysis",
                "market_search",
            ]
        
        if "yfinance" in adapter_info:
            adapter_info["yfinance"]["capabilities"] = [
                "historical_bars",
                "symbol_metadata",
                "universe_screening",
            ]
        
        if "binance" in adapter_info:
            adapter_info["binance"]["capabilities"] = [
                "live_crypto_prices",
                "btc_eth_ticker",
                "klines_candlesticks",
                "orderbook_imbalance",
                "historical_crypto_data",
            ]
        
        return {"available": True, "adapters": adapter_info}
        
    except Exception as e:
        logger.error(f"Adapter list failed: {e}", exc_info=True)
        return {"available": False, "adapters": {}, "error": str(e)}
