"""
Polymarket URL Scraper
Fetches and extracts market data from Polymarket URLs
Uses CLOB API for real order book data
"""
from typing import Dict, Any, Optional, List
import logging
import re
from datetime import datetime
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Polymarket CLOB API endpoints
CLOB_BASE_URL = "https://clob.polymarket.com"


class PolymarketURLScraper:
    """
    Scrapes Polymarket market pages to extract market data
    """

    def __init__(self):
        self.name = "POLYMARKET_URL_SCRAPER"
        self.timeout = 10.0
        self.clob_timeout = 5.0

    def scrape_market_url(self, market_url: str) -> Dict[str, Any]:
        """
        Scrape market data from Polymarket URL

        Args:
            market_url: Polymarket market URL

        Returns:
            Market data dictionary compatible with MarketSnapshot schema
        """
        logger.info(f"[{self.name}] Scraping market data from {market_url}")

        try:
            # Use synchronous client to avoid async context issues
            with httpx.Client(timeout=self.timeout) as client:
                # Fetch page
                headers = {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                }
                response = client.get(market_url, headers=headers, follow_redirects=True)
                response.raise_for_status()

                # Parse HTML
                soup = BeautifulSoup(response.text, 'html.parser')

                # Extract market data
                market_data = self._extract_market_data(soup, market_url)

                logger.info(
                    f"[{self.name}] Successfully scraped market data: "
                    f"title={market_data.get('market_title', 'Unknown')}"
                )

                return market_data

        except Exception as e:
            logger.error(f"[{self.name}] Failed to scrape URL: {e}", exc_info=True)
            raise ValueError(f"Failed to scrape Polymarket URL: {e}")

    def _extract_market_data(self, soup: BeautifulSoup, market_url: str) -> Dict[str, Any]:
        """
        Extract market data from parsed HTML
        """
        # Extract market title
        title_elem = soup.find('h1')
        market_title = title_elem.get_text(strip=True) if title_elem else "Unknown Market"

        # Extract market ID from URL
        market_id = market_url.split('/')[-1] if '/' in market_url else 'unknown'

        # Try to find JSON data in script tags (Polymarket often embeds data)
        market_data_json = self._extract_json_data(soup)

        if market_data_json:
            # If we found embedded JSON, parse it
            result = self._parse_json_data(market_data_json, market_url, market_title, market_id)
            if result:
                return result

        # Fall back to HTML scraping if JSON parsing failed or returned None
        return self._parse_html_data(soup, market_url, market_title, market_id)

    def _extract_json_data(self, soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """
        Try to extract embedded JSON data from script tags (Next.js __NEXT_DATA__)
        """
        try:
            import json

            # Look for Next.js data
            script_tag = soup.find('script', type='application/json', id='__NEXT_DATA__')
            if script_tag and script_tag.string:
                next_data = json.loads(script_tag.string)

                # Navigate to the event data in React Query cache
                props = next_data.get('props', {})
                page_props = props.get('pageProps', {})
                dehydrated = page_props.get('dehydratedState', {})
                queries = dehydrated.get('queries', [])

                # Find the event query
                for query in queries:
                    query_key = query.get('queryKey', [])
                    # Look for event API query
                    if len(query_key) >= 2 and '/api/event' in str(query_key[0]):
                        state = query.get('state', {})
                        event_data = state.get('data', {})
                        if event_data and 'markets' in event_data:
                            return event_data

            return None
        except Exception as e:
            logger.debug(f"Could not extract Next.js data: {e}")
            return None

    def _parse_json_data(
        self,
        data: Dict[str, Any],
        market_url: str,
        market_title: str,
        market_id: str
    ) -> Dict[str, Any]:
        """
        Parse Polymarket Next.js embedded event data
        Fetches REAL order book data from CLOB API
        """
        # Extract market data from event structure
        markets = data.get('markets', [])

        if not markets:
            # Fallback to HTML parsing if no markets found
            return None

        # Get first market (BTC 15m markets typically have 1 market with 2 outcomes)
        market = markets[0]

        # Extract token IDs for CLOB API
        token_ids = market.get('clobTokenIds', [])

        if not token_ids or len(token_ids) < 2:
            logger.warning("No token IDs found in market data")
            # Fall back to basic parsing without order book
            outcome_prices = market.get('outcomePrices', [])
            yes_price = self._normalize_price(outcome_prices[0]) if len(outcome_prices) > 0 else 0.5
            no_price = self._normalize_price(outcome_prices[1]) if len(outcome_prices) > 1 else 0.5

            return {
                "captured_at_iso": datetime.utcnow().isoformat(),
                "market_url": market_url,
                "market_title": data.get('title', market_title),
                "market_id": data.get('slug', market_id),
                "up_label": "Yes",
                "down_label": "No",
                "yes_means_up": True,
                "up_prob": yes_price,
                "down_prob": no_price,
                "up_spread": 0.01,
                "down_spread": 0.01,
                "up_best_bid": yes_price - 0.005,
                "up_best_ask": yes_price + 0.005,
                "down_best_bid": no_price - 0.005,
                "down_best_ask": no_price + 0.005,
                "volume_24h_usd": float(market.get('volume', 10000)),
                "total_volume_usd": float(market.get('liquidity', 50000)),
                "open_interest_usd": float(market.get('liquidity', 25000)),
                "time_remaining_seconds": 600,
                "up_bids": [],
                "up_asks": [],
                "down_bids": [],
                "down_asks": [],
                "recent_trades": [],
            }

        # === FETCH REAL ORDER BOOK DATA FROM CLOB API ===
        logger.info(f"[{self.name}] Fetching order books from CLOB API")

        up_token_id = token_ids[0]  # YES/UP token
        down_token_id = token_ids[1]  # NO/DOWN token

        up_book = self._fetch_order_book(up_token_id)
        down_book = self._fetch_order_book(down_token_id)

        if not up_book or not down_book:
            logger.warning("Failed to fetch order books from CLOB API, using fallback data")
            # Use fallback data if CLOB API fails
            outcome_prices = market.get('outcomePrices', [])
            yes_price = self._normalize_price(outcome_prices[0]) if len(outcome_prices) > 0 else 0.5
            no_price = self._normalize_price(outcome_prices[1]) if len(outcome_prices) > 1 else 0.5

            return self._build_fallback_data(
                market_url, data.get('title', market_title), data.get('slug', market_id),
                yes_price, no_price, market
            )

        # === EXTRACT REAL ORDER BOOK DATA ===

        # Get bids/asks arrays
        up_bids = up_book.get('bids', [])
        up_asks = up_book.get('asks', [])
        down_bids = down_book.get('bids', [])
        down_asks = down_book.get('asks', [])

        # Get current prices - USE PAGE PRICES (outcomePrices), NOT stale CLOB last_trade_price
        # outcomePrices is ['0.865', '0.135'] for [YES, NO]
        outcome_prices = market.get('outcomePrices', [])
        if outcome_prices and len(outcome_prices) >= 2:
            up_last_price = self._normalize_price(outcome_prices[0])  # YES/UP price
            down_last_price = self._normalize_price(outcome_prices[1])  # NO/DOWN price
            logger.info(f"[{self.name}] Using page prices: UP={up_last_price:.3f}, DOWN={down_last_price:.3f}")
        else:
            # Fallback to CLOB last_trade_price if outcomePrices missing
            up_last_price = float(up_book.get('last_trade_price', 0.5))
            down_last_price = float(down_book.get('last_trade_price', 0.5))
            logger.warning(f"[{self.name}] Using CLOB API prices (may be stale): UP={up_last_price:.3f}, DOWN={down_last_price:.3f}")

        # Polymarket order books are sorted BACKWARDS:
        # - Bids: ascending (0.01, 0.02, ..., 0.15) - BEST bid is LAST
        # - Asks: descending (0.99, 0.98, ...) - BEST ask is LAST
        # We want the highest bid and lowest ask

        def find_best_bid(bids):
            """Find highest bid (last item in ascending-sorted array)"""
            if not bids:
                return None
            # Scan from end to find highest reasonable bid
            for bid in reversed(bids):
                price = float(bid['price'])
                if price > 0.01:  # Skip dust orders
                    return price
            return float(bids[-1]['price']) if bids else None

        def find_best_ask(asks):
            """Find lowest ask (last item in descending-sorted array)"""
            if not asks:
                return None
            # Scan from end to find lowest reasonable ask
            for ask in reversed(asks):
                price = float(ask['price'])
                if price < 0.99:  # Skip dust orders
                    return price
            return float(asks[-1]['price']) if asks else None

        up_best_bid = find_best_bid(up_bids) or (up_last_price - 0.005)
        up_best_ask = find_best_ask(up_asks) or (up_last_price + 0.005)
        down_best_bid = find_best_bid(down_bids) or (down_last_price - 0.005)
        down_best_ask = find_best_ask(down_asks) or (down_last_price + 0.005)

        # Calculate spreads
        up_spread = up_best_ask - up_best_bid if up_best_ask > up_best_bid else 0.005
        down_spread = down_best_ask - down_best_bid if down_best_ask > down_best_bid else 0.005

        # Extract volume
        volume = float(market.get('volume', 0) or market.get('volume24hr', 0) or 10000)

        # Extract time data
        end_date = data.get('endDate')
        time_remaining_seconds = 600  # Default
        if end_date:
            try:
                from dateutil import parser as date_parser
                end_time = date_parser.parse(end_date)
                time_remaining = (end_time - datetime.utcnow()).total_seconds()
                time_remaining_seconds = max(0, int(time_remaining))
            except Exception:
                pass

        logger.info(
            f"[{self.name}] Order book extracted: "
            f"UP bids={len(up_bids)}, asks={len(up_asks)}, "
            f"DOWN bids={len(down_bids)}, asks={len(down_asks)}"
        )

        # Convert bid/ask arrays to the format expected by signal engine
        # Format: [[price, size], [price, size], ...]
        up_bids_formatted = [[float(b['price']), float(b['size'])] for b in up_bids[:50]]
        up_asks_formatted = [[float(a['price']), float(a['size'])] for a in up_asks[:50]]
        down_bids_formatted = [[float(b['price']), float(b['size'])] for b in down_bids[:50]]
        down_asks_formatted = [[float(a['price']), float(a['size'])] for a in down_asks[:50]]

        return {
            "captured_at_iso": datetime.utcnow().isoformat(),
            "market_url": market_url,
            "market_title": data.get('title', market_title),
            "market_id": data.get('slug', market_id),
            "up_label": "Yes",
            "down_label": "No",
            "yes_means_up": True,
            "up_prob": up_last_price,
            "down_prob": down_last_price,
            "up_spread": up_spread,
            "down_spread": down_spread,
            "up_best_bid": up_best_bid,
            "up_best_ask": up_best_ask,
            "down_best_bid": down_best_bid,
            "down_best_ask": down_best_ask,
            "volume_24h_usd": volume,
            "total_volume_usd": float(market.get('liquidity', volume * 5)),
            "open_interest_usd": float(market.get('liquidity', volume * 2.5)),
            "time_remaining_seconds": time_remaining_seconds,
            "up_bids": up_bids_formatted,
            "up_asks": up_asks_formatted,
            "down_bids": down_bids_formatted,
            "down_asks": down_asks_formatted,
            "recent_trades": [],  # TODO: Implement trade history polling
        }

    def _build_fallback_data(
        self,
        market_url: str,
        market_title: str,
        market_id: str,
        yes_price: float,
        no_price: float,
        market: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build fallback data when CLOB API fails"""
        return {
            "captured_at_iso": datetime.utcnow().isoformat(),
            "market_url": market_url,
            "market_title": market_title,
            "market_id": market_id,
            "up_label": "Yes",
            "down_label": "No",
            "yes_means_up": True,
            "up_prob": yes_price,
            "down_prob": no_price,
            "up_spread": 0.01,
            "down_spread": 0.01,
            "up_best_bid": yes_price - 0.005,
            "up_best_ask": yes_price + 0.005,
            "down_best_bid": no_price - 0.005,
            "down_best_ask": no_price + 0.005,
            "volume_24h_usd": float(market.get('volume', 10000)),
            "total_volume_usd": float(market.get('liquidity', 50000)),
            "open_interest_usd": float(market.get('liquidity', 25000)),
            "time_remaining_seconds": 600,
            "up_bids": [],
            "up_asks": [],
            "down_bids": [],
            "down_asks": [],
            "recent_trades": [],
        }

    def _parse_html_data(
        self,
        soup: BeautifulSoup,
        market_url: str,
        market_title: str,
        market_id: str
    ) -> Dict[str, Any]:
        """
        Parse market data from HTML elements (fallback method)
        """
        # Extract prices - look for elements with price/probability
        up_prob = None
        down_prob = None

        # Try to find price elements
        price_elements = soup.find_all(string=re.compile(r'\d+\.?\d*¢'))
        for elem in price_elements:
            # Look for "Yes" and "No" labels
            parent_text = elem.parent.get_text() if elem.parent else ""
            match = re.search(r'(\d+\.?\d*)¢', elem)
            if match:
                price = float(match.group(1)) / 100  # Convert cents to probability
                if 'yes' in parent_text.lower() and up_prob is None:
                    up_prob = price
                elif 'no' in parent_text.lower() and down_prob is None:
                    down_prob = price

        # Calculate complement if one is missing
        if up_prob and not down_prob:
            down_prob = 1 - up_prob
        if down_prob and not up_prob:
            up_prob = 1 - down_prob

        # Extract volume data
        volume_24h = None
        total_volume = None
        open_interest = None

        volume_elements = soup.find_all(string=re.compile(r'\$[\d,]+'))
        for elem in volume_elements:
            parent_text = elem.parent.get_text().lower() if elem.parent else ""
            match = re.search(r'\$([\d,]+)', elem)
            if match:
                value = float(match.group(1).replace(',', ''))
                if '24h' in parent_text or '24 h' in parent_text:
                    volume_24h = value
                elif 'total' in parent_text:
                    total_volume = value
                elif 'open' in parent_text or 'interest' in parent_text:
                    open_interest = value

        # Extract time remaining
        time_remaining_seconds = None
        time_elements = soup.find_all(string=re.compile(r'\d+m|\d+h|\d+d'))
        for elem in time_elements:
            time_str = elem.strip()
            time_remaining_seconds = self._parse_time_string(time_str)
            if time_remaining_seconds:
                break

        # Build market data with ALL required fields
        # Use defaults for missing data so analysis can still run
        up_prob = up_prob or 0.5  # Default 50/50 if not found
        down_prob = down_prob or 0.5

        return {
            "captured_at_iso": datetime.utcnow().isoformat(),
            "market_url": market_url,
            "market_title": market_title,
            "market_id": market_id,
            "up_label": "Yes",
            "down_label": "No",
            "yes_means_up": True,
            "up_prob": up_prob,
            "down_prob": down_prob,
            # Defaults for required fields
            "up_spread": 0.02,  # 2% spread estimate
            "down_spread": 0.025,  # 2.5% spread estimate
            "up_best_bid": up_prob - 0.01,
            "up_best_ask": up_prob + 0.01,
            "down_best_bid": down_prob - 0.0125,
            "down_best_ask": down_prob + 0.0125,
            "volume_24h_usd": volume_24h or 10000.0,  # Default $10k volume
            "total_volume_usd": total_volume or 50000.0,
            "open_interest_usd": open_interest or 25000.0,
            "time_remaining_seconds": time_remaining_seconds or 600,  # Default 10 mins
            "up_bids": [],
            "up_asks": [],
            "down_bids": [],
            "down_asks": [],
            "recent_trades": [],
        }

    def _normalize_price(self, price: Optional[Any]) -> Optional[float]:
        """Normalize price to [0, 1] probability"""
        if price is None:
            return None
        try:
            p = float(price)
            if p > 1.0:
                p = p / 100.0
            return max(0.0, min(1.0, p))
        except (ValueError, TypeError):
            return None

    def _fetch_order_book(self, token_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch order book from Polymarket CLOB API

        Returns dict with bids, asks, last_trade_price, etc.
        """
        try:
            book_url = f"{CLOB_BASE_URL}/book?token_id={token_id}"

            with httpx.Client(timeout=self.clob_timeout) as client:
                headers = {"User-Agent": "Mozilla/5.0"}
                response = client.get(book_url, headers=headers)

                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(f"CLOB API returned {response.status_code} for token {token_id[:8]}...")
                    return None

        except Exception as e:
            logger.warning(f"Failed to fetch order book from CLOB API: {e}")
            return None

    def _calculate_obi(self, bids: List[Dict], asks: List[Dict], depth: int = 10) -> float:
        """
        Calculate Order Book Imbalance from bid/ask levels

        OBI = (bid_volume - ask_volume) / (bid_volume + ask_volume)

        Returns value in [-1, +1] where:
        - Positive = more buy pressure
        - Negative = more sell pressure
        """
        try:
            bid_volume = sum(float(b.get('size', 0)) for b in bids[:depth])
            ask_volume = sum(float(a.get('size', 0)) for a in asks[:depth])

            total = bid_volume + ask_volume
            if total == 0:
                return 0.0

            obi = (bid_volume - ask_volume) / total
            return obi

        except Exception as e:
            logger.warning(f"Failed to calculate OBI: {e}")
            return 0.0

    def _parse_time_string(self, time_str: str) -> Optional[int]:
        """Parse time string like '15m', '1h 30m' to seconds"""
        try:
            seconds = 0
            # Match days, hours, minutes
            days_match = re.search(r'(\d+)d', time_str)
            hours_match = re.search(r'(\d+)h', time_str)
            minutes_match = re.search(r'(\d+)m', time_str)

            if days_match:
                seconds += int(days_match.group(1)) * 86400
            if hours_match:
                seconds += int(hours_match.group(1)) * 3600
            if minutes_match:
                seconds += int(minutes_match.group(1)) * 60

            return seconds if seconds > 0 else None
        except Exception:
            return None
