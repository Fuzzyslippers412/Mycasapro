"""
Browser-based adapter for Edge Lab using agent-browser CLI.

Enables scraping live market data from websites that don't have public APIs,
using the Clawd Chrome extension relay or headless browser automation.

Integrates with Clawdbot's browser tool and agent-browser CLI.
"""

import json
import subprocess
import logging
import re
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from .base import BaseAdapter, AdapterRegistry, SymbolMetadata, DailyBar

logger = logging.getLogger(__name__)


@dataclass
class BrowserScrapeResult:
    """Result from a browser scrape operation"""
    url: str
    success: bool
    data: Dict[str, Any]
    timestamp: datetime
    source: str
    error: Optional[str] = None


class AgentBrowserClient:
    """
    Client for interacting with agent-browser CLI.
    
    Supports both headless mode and Chrome extension relay mode.
    """
    
    def __init__(
        self,
        session: str = "edgelab",
        headed: bool = False,
        timeout: int = 30000,
        use_chrome_relay: bool = False,
        cdp_port: Optional[int] = None
    ):
        self.session = session
        self.headed = headed
        self.timeout = timeout
        self.use_chrome_relay = use_chrome_relay
        self.cdp_port = cdp_port
    
    def _run_cmd(self, args: List[str], json_output: bool = True) -> Dict[str, Any]:
        """Run agent-browser command and return result"""
        cmd = ["agent-browser", f"--session={self.session}"]
        
        if self.headed:
            cmd.append("--headed")
        
        if json_output:
            cmd.append("--json")
        
        if self.cdp_port:
            cmd.extend([f"--cdp={self.cdp_port}"])
        
        cmd.extend(args)
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout // 1000 + 10
            )
            
            if result.returncode != 0:
                logger.error(f"agent-browser error: {result.stderr}")
                return {"success": False, "error": result.stderr}
            
            if json_output:
                try:
                    return {"success": True, "data": json.loads(result.stdout)}
                except json.JSONDecodeError:
                    return {"success": True, "data": {"raw": result.stdout}}
            
            return {"success": True, "data": {"raw": result.stdout}}
            
        except subprocess.TimeoutExpired:
            logger.error(f"agent-browser timed out after {self.timeout}ms")
            return {"success": False, "error": "timeout"}
        except FileNotFoundError:
            logger.error("agent-browser not found - install with: npm install -g agent-browser")
            return {"success": False, "error": "agent-browser not installed"}
        except Exception as e:
            logger.error(f"agent-browser exception: {e}")
            return {"success": False, "error": str(e)}
    
    def open(self, url: str) -> Dict[str, Any]:
        """Navigate to URL"""
        return self._run_cmd(["open", url])
    
    def snapshot(self, interactive_only: bool = True, compact: bool = True) -> Dict[str, Any]:
        """Get page snapshot with element refs"""
        args = ["snapshot"]
        if interactive_only:
            args.append("-i")
        if compact:
            args.append("-c")
        return self._run_cmd(args)
    
    def get_text(self, ref: str) -> Dict[str, Any]:
        """Get text from element by ref"""
        return self._run_cmd(["get", "text", ref])
    
    def get_html(self, ref: str) -> Dict[str, Any]:
        """Get HTML from element by ref"""
        return self._run_cmd(["get", "html", ref])
    
    def click(self, ref: str) -> Dict[str, Any]:
        """Click element by ref"""
        return self._run_cmd(["click", ref], json_output=False)
    
    def fill(self, ref: str, text: str) -> Dict[str, Any]:
        """Fill input by ref"""
        return self._run_cmd(["fill", ref, text], json_output=False)
    
    def wait(self, selector_or_ms: str) -> Dict[str, Any]:
        """Wait for element or milliseconds"""
        return self._run_cmd(["wait", selector_or_ms], json_output=False)
    
    def eval_js(self, script: str) -> Dict[str, Any]:
        """Execute JavaScript and return result"""
        return self._run_cmd(["eval", script])
    
    def close(self) -> Dict[str, Any]:
        """Close browser"""
        return self._run_cmd(["close"], json_output=False)
    
    def screenshot(self, path: Optional[str] = None, full_page: bool = False) -> Dict[str, Any]:
        """Take screenshot"""
        args = ["screenshot"]
        if path:
            args.append(path)
        if full_page:
            args.append("--full")
        return self._run_cmd(args, json_output=False)


@AdapterRegistry.register
class BrowserAdapter(BaseAdapter):
    """
    Browser-based data adapter using agent-browser.
    
    Scrapes live market data from websites that don't have public APIs.
    Can use Chrome extension relay for sites requiring authentication.
    
    Supports:
    - Live stock prices from finance sites
    - Market sentiment data
    - News headlines and content
    - Any web-based data source
    """
    
    name = "browser"
    
    # Scraping targets with their extraction patterns
    SCRAPE_TARGETS = {
        "yahoo_finance": {
            "url_template": "https://finance.yahoo.com/quote/{symbol}",
            "selectors": {
                "price": "[data-testid='qsp-price']",
                "change": "[data-testid='qsp-price-change']",
                "change_pct": "[data-testid='qsp-price-change-percent']",
                "market_cap": "[data-field='marketCap']",
                "pe_ratio": "[data-field='trailingPE']",
                "volume": "[data-field='regularMarketVolume']"
            }
        },
        "finviz": {
            "url_template": "https://finviz.com/quote.ashx?t={symbol}",
            "selectors": {
                "price": ".quote-price",
                "target_price": "td:contains('Target Price')+td",
                "analyst_rating": "td:contains('Recom')+td"
            }
        },
        "tradingview": {
            "url_template": "https://www.tradingview.com/symbols/{symbol}/",
            "js_extraction": True
        }
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.browser = AgentBrowserClient(
            session=config.get("session", "edgelab") if config else "edgelab",
            headed=config.get("headed", False) if config else False,
            timeout=config.get("timeout", 30000) if config else 30000,
            use_chrome_relay=config.get("use_chrome_relay", False) if config else False,
            cdp_port=config.get("cdp_port") if config else None
        )
        self._initialized = False
    
    def _ensure_initialized(self):
        """Ensure browser is initialized"""
        if not self._initialized:
            self._initialized = True
    
    def scrape_symbol_data(self, symbol: str, source: str = "yahoo_finance") -> BrowserScrapeResult:
        """
        Scrape live data for a symbol from specified source.
        
        Args:
            symbol: Stock/crypto symbol
            source: Data source (yahoo_finance, finviz, tradingview)
        
        Returns:
            BrowserScrapeResult with scraped data
        """
        self._ensure_initialized()
        
        if source not in self.SCRAPE_TARGETS:
            return BrowserScrapeResult(
                url="",
                success=False,
                data={},
                timestamp=datetime.utcnow(),
                source=source,
                error=f"Unknown source: {source}"
            )
        
        target = self.SCRAPE_TARGETS[source]
        url = target["url_template"].format(symbol=symbol)
        
        # Navigate to page
        result = self.browser.open(url)
        if not result.get("success"):
            return BrowserScrapeResult(
                url=url,
                success=False,
                data={},
                timestamp=datetime.utcnow(),
                source=source,
                error=result.get("error", "Failed to open URL")
            )
        
        # Wait for page load
        self.browser.wait("2000")
        
        # Extract data using JavaScript for reliability
        extraction_script = self._build_extraction_script(target)
        extraction_result = self.browser.eval_js(extraction_script)
        
        if not extraction_result.get("success"):
            return BrowserScrapeResult(
                url=url,
                success=False,
                data={},
                timestamp=datetime.utcnow(),
                source=source,
                error=extraction_result.get("error", "Extraction failed")
            )
        
        return BrowserScrapeResult(
            url=url,
            success=True,
            data=extraction_result.get("data", {}),
            timestamp=datetime.utcnow(),
            source=source
        )
    
    def _build_extraction_script(self, target: Dict[str, Any]) -> str:
        """Build JavaScript extraction script for target"""
        selectors = target.get("selectors", {})
        
        # Build extraction object
        extractions = []
        for key, selector in selectors.items():
            extractions.append(
                f'"{key}": document.querySelector(\'{selector}\')?.textContent?.trim() || null'
            )
        
        return f"({{ {', '.join(extractions)} }})"
    
    def scrape_market_overview(self) -> Dict[str, Any]:
        """
        Scrape overall market overview data.
        
        Returns indices, sector performance, market breadth, etc.
        """
        self._ensure_initialized()
        
        # Navigate to market overview
        self.browser.open("https://finance.yahoo.com/markets/")
        self.browser.wait("3000")
        
        script = """
        (() => {
            const indices = [];
            document.querySelectorAll('[data-testid="quote-container"]').forEach(el => {
                const symbol = el.querySelector('[data-testid="symbol"]')?.textContent;
                const price = el.querySelector('[data-testid="price"]')?.textContent;
                const change = el.querySelector('[data-testid="change"]')?.textContent;
                if (symbol) indices.push({ symbol, price, change });
            });
            return { indices, timestamp: new Date().toISOString() };
        })()
        """
        
        result = self.browser.eval_js(script)
        return result.get("data", {})
    
    def scrape_news_headlines(self, symbol: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Scrape news headlines for a symbol or market.
        
        Args:
            symbol: Optional stock symbol (if None, gets market news)
        
        Returns:
            List of headline dictionaries with title, url, source, time
        """
        self._ensure_initialized()
        
        if symbol:
            url = f"https://finance.yahoo.com/quote/{symbol}/news"
        else:
            url = "https://finance.yahoo.com/topic/stock-market-news/"
        
        self.browser.open(url)
        self.browser.wait("2000")
        
        script = """
        (() => {
            const headlines = [];
            document.querySelectorAll('h3 a, [data-testid="story-title"]').forEach(el => {
                const title = el.textContent?.trim();
                const href = el.href || el.closest('a')?.href;
                if (title && href) {
                    headlines.push({ title, url: href });
                }
            });
            return headlines.slice(0, 20);
        })()
        """
        
        result = self.browser.eval_js(script)
        return result.get("data", [])
    
    def fetch_universe(
        self,
        as_of: datetime,
        rules: Dict[str, Any]
    ) -> List[SymbolMetadata]:
        """
        Fetch universe by scraping screener results.
        
        Note: This is slower than API-based adapters but can access
        data not available via APIs.
        """
        self._ensure_initialized()
        
        # Use FinViz screener for universe discovery
        self.browser.open("https://finviz.com/screener.ashx?v=111&f=cap_largeover,sh_avgvol_o400")
        self.browser.wait("3000")
        
        script = """
        (() => {
            const symbols = [];
            document.querySelectorAll('table.screener_table tbody tr').forEach(row => {
                const cells = row.querySelectorAll('td');
                if (cells.length > 1) {
                    const symbol = cells[1]?.textContent?.trim();
                    const company = cells[2]?.textContent?.trim();
                    const sector = cells[3]?.textContent?.trim();
                    const industry = cells[4]?.textContent?.trim();
                    const marketCap = cells[6]?.textContent?.trim();
                    if (symbol) {
                        symbols.push({ symbol, company, sector, industry, marketCap });
                    }
                }
            });
            return symbols;
        })()
        """
        
        result = self.browser.eval_js(script)
        scraped = result.get("data", [])
        
        metadata_list = []
        for item in scraped:
            if isinstance(item, dict) and item.get("symbol"):
                # Parse market cap string
                market_cap = self._parse_market_cap(item.get("marketCap", ""))
                
                metadata_list.append(SymbolMetadata(
                    symbol=item["symbol"],
                    name=item.get("company"),
                    sector=item.get("sector"),
                    industry=item.get("industry"),
                    market_cap=market_cap,
                ))
        
        return metadata_list
    
    def _parse_market_cap(self, cap_str: str) -> Optional[float]:
        """Parse market cap string like '1.5B' to float"""
        if not cap_str:
            return None
        
        cap_str = cap_str.strip().upper()
        multipliers = {'K': 1e3, 'M': 1e6, 'B': 1e9, 'T': 1e12}
        
        for suffix, mult in multipliers.items():
            if cap_str.endswith(suffix):
                try:
                    return float(cap_str[:-1]) * mult
                except ValueError:
                    return None
        
        try:
            return float(cap_str)
        except ValueError:
            return None
    
    def fetch_daily_bars(
        self,
        symbols: List[str],
        start_date: date,
        end_date: date
    ) -> Dict[str, List[DailyBar]]:
        """
        Fetch daily bars by scraping historical data pages.
        
        Note: For historical data, prefer API-based adapters.
        This is primarily useful for live/current data.
        """
        # Browser scraping is better suited for live data
        # For historical bars, fall back to a warning
        logger.warning(
            "BrowserAdapter is optimized for live data. "
            "Consider using YFinanceAdapter for historical bars."
        )
        return {}
    
    def fetch_symbol_metadata(
        self,
        symbols: List[str]
    ) -> Dict[str, SymbolMetadata]:
        """Fetch detailed metadata for symbols by scraping"""
        self._ensure_initialized()
        
        result = {}
        for symbol in symbols:
            scrape_result = self.scrape_symbol_data(symbol, "yahoo_finance")
            
            if scrape_result.success:
                data = scrape_result.data
                result[symbol] = SymbolMetadata(
                    symbol=symbol,
                    name=data.get("name"),
                    market_cap=self._parse_number(data.get("market_cap")),
                )
        
        return result
    
    def _parse_number(self, num_str: str) -> Optional[float]:
        """Parse number string with suffixes"""
        if not num_str:
            return None
        
        # Remove commas and currency symbols
        num_str = re.sub(r'[,$%]', '', str(num_str).strip())
        
        return self._parse_market_cap(num_str)
    
    def get_live_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Get live quote for a symbol.
        
        This is the primary use case for browser adapter -
        getting real-time data that may not be in APIs.
        """
        result = self.scrape_symbol_data(symbol, "yahoo_finance")
        
        if result.success:
            return {
                "symbol": symbol,
                "timestamp": result.timestamp.isoformat(),
                "source": result.source,
                **result.data
            }
        
        return {"symbol": symbol, "error": result.error}
    
    def cleanup(self):
        """Close browser session"""
        try:
            self.browser.close()
        except Exception as e:
            logger.warning(f"Error closing browser: {e}")
