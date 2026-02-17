"""
Clawdbot Gateway Client

Calls Clawdbot's browser tool via HTTP API to use the Chrome extension relay.
This enables MyCasa Pro to grab data from attached browser tabs.
"""

import httpx
import logging
import re
import os
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


def get_clawdbot_config() -> Dict[str, Any]:
    """Load Clawdbot gateway config from ~/.clawdbot/clawdbot.json"""
    config_path = Path.home() / ".clawdbot" / "clawdbot.json"
    try:
        if config_path.exists():
            with open(config_path) as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Could not load clawdbot config: {e}")
    return {}


def get_gateway_url() -> str:
    """Get the Clawdbot gateway URL from config"""
    config = get_clawdbot_config()
    port = config.get("port", 18789)
    return f"http://localhost:{port}"


def get_gateway_token() -> Optional[str]:
    """Get the Clawdbot gateway auth token from config"""
    config = get_clawdbot_config()
    auth = config.get("auth", {})
    return auth.get("token")


@dataclass
class PolymarketBTC15mData:
    """Parsed data from a Polymarket BTC 15-minute market"""
    market_title: str
    market_url: str
    btc_price: float
    price_to_beat: Optional[float]
    up_price: float  # e.g., 0.53 = 53¢
    down_price: float  # e.g., 0.49 = 49¢
    time_remaining_minutes: Optional[int]
    time_remaining_seconds: Optional[int]
    volume: Optional[float]
    # User position if any
    user_position_side: Optional[str]  # "Up" or "Down"
    user_position_qty: Optional[int]
    user_position_avg: Optional[float]
    user_position_value: Optional[float]
    user_position_pnl: Optional[float]
    # Raw snapshot for debugging
    raw_snapshot: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "market_title": self.market_title,
            "market_url": self.market_url,
            "btc_price": self.btc_price,
            "price_to_beat": self.price_to_beat,
            "up_prob": self.up_price,
            "down_prob": self.down_price,
            "up_price_cents": int(self.up_price * 100),
            "down_price_cents": int(self.down_price * 100),
            "time_remaining_minutes": self.time_remaining_minutes,
            "time_remaining_seconds": self.time_remaining_seconds,
            "volume": self.volume,
            "user_position": {
                "side": self.user_position_side,
                "qty": self.user_position_qty,
                "avg_price": self.user_position_avg,
                "value": self.user_position_value,
                "pnl": self.user_position_pnl,
            } if self.user_position_side else None,
        }


class ClawdbotBrowserClient:
    """
    Client for calling Clawdbot's browser tool via HTTP API.
    
    Uses the Chrome extension relay (profile="chrome") to access
    the user's attached browser tabs.
    """
    
    def __init__(self, gateway_url: Optional[str] = None, token: Optional[str] = None, timeout: int = 30):
        self.gateway_url = (gateway_url or get_gateway_url()).rstrip("/")
        self.token = token or get_gateway_token()
        self.timeout = timeout
        self._client = None
    
    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            headers = {}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"
            self._client = httpx.Client(timeout=self.timeout, headers=headers)
        return self._client
    
    def close(self):
        if self._client:
            self._client.close()
            self._client = None
    
    def browser_snapshot(self, profile: str = "chrome", compact: bool = True) -> Dict[str, Any]:
        """
        Get a snapshot of the currently attached browser tab.
        
        Args:
            profile: "chrome" for Chrome extension relay, "clawd" for isolated browser
            compact: Whether to return compact snapshot
        
        Returns:
            Snapshot data with element refs and text content
        """
        try:
            # Call Clawdbot's tool API
            resp = self.client.post(
                f"{self.gateway_url}/api/tools/browser",
                json={
                    "action": "snapshot",
                    "profile": profile,
                    "compact": compact,
                },
                timeout=self.timeout
            )
            
            if resp.status_code == 200:
                return {"success": True, "data": resp.json()}
            else:
                error_text = resp.text
                logger.error(f"Browser snapshot failed: {resp.status_code} - {error_text}")
                return {"success": False, "error": error_text}
                
        except httpx.ConnectError:
            logger.error(f"Cannot connect to Clawdbot gateway at {self.gateway_url}")
            return {"success": False, "error": f"Cannot connect to Clawdbot gateway at {self.gateway_url}. Is Clawdbot running?"}
        except Exception as e:
            logger.error(f"Browser snapshot error: {e}")
            return {"success": False, "error": str(e)}
    
    def browser_navigate(self, url: str, profile: str = "chrome") -> Dict[str, Any]:
        """Navigate to a URL in the attached browser tab."""
        try:
            resp = self.client.post(
                f"{self.gateway_url}/api/tools/browser",
                json={
                    "action": "navigate",
                    "profile": profile,
                    "targetUrl": url,
                },
                timeout=self.timeout
            )
            
            if resp.status_code == 200:
                return {"success": True, "data": resp.json()}
            else:
                return {"success": False, "error": resp.text}
                
        except Exception as e:
            logger.error(f"Browser navigate error: {e}")
            return {"success": False, "error": str(e)}
    
    def get_page_url(self, profile: str = "chrome") -> Optional[str]:
        """Get the current URL of the attached tab."""
        try:
            resp = self.client.post(
                f"{self.gateway_url}/api/tools/browser",
                json={
                    "action": "tabs",
                    "profile": profile,
                },
                timeout=self.timeout
            )
            
            if resp.status_code == 200:
                data = resp.json()
                # Extract URL from tabs response
                if isinstance(data, list) and len(data) > 0:
                    return data[0].get("url")
                return None
            else:
                return None
                
        except Exception as e:
            logger.error(f"Get page URL error: {e}")
            return None


def parse_polymarket_btc_snapshot(snapshot_text: str) -> Optional[PolymarketBTC15mData]:
    """
    Parse a Polymarket BTC Up/Down market snapshot into structured data.
    
    Extracts:
    - Market title and time window
    - Current BTC price
    - Up/Down odds
    - Countdown timer
    - User position if any
    """
    try:
        # Extract market title
        title_match = re.search(r'heading "([^"]*Bitcoin[^"]*)"', snapshot_text)
        market_title = title_match.group(1) if title_match else "Bitcoin Up or Down"
        
        # Extract time window from title (e.g., "January 31, 8:30-8:45PM ET")
        time_match = re.search(r'paragraph[^:]*:\s*([A-Z][a-z]+ \d+,\s*[\d:]+[AP]M[-–][\d:]+[AP]M\s*ET)', snapshot_text)
        if time_match:
            market_title = f"Bitcoin Up or Down - {time_match.group(1)}"
        
        # Extract BTC price - look for the animated price display
        # Pattern: "7" "8" "," "7" "0" "7" . "5" "8" 
        price_digits = []
        # Find the "current price" section and extract digits
        current_price_section = re.search(r'current price.*?(\d[\d,\.]*)', snapshot_text, re.DOTALL)
        if current_price_section:
            price_str = current_price_section.group(1).replace(",", "")
            try:
                btc_price = float(price_str)
            except:
                btc_price = 0.0
        else:
            # Alternative: look for $ followed by digits in the price section
            price_match = re.search(r'\$\s*([\d,]+\.?\d*)', snapshot_text)
            if price_match:
                btc_price = float(price_match.group(1).replace(",", ""))
            else:
                # Try extracting from the digit sequence in generic refs
                digit_pattern = re.findall(r'generic \[ref=e\d+\]: "(\d)"', snapshot_text)
                if len(digit_pattern) >= 5:
                    # First 5+ digits are likely the BTC price
                    price_str = "".join(digit_pattern[:5])
                    if len(digit_pattern) > 6:
                        price_str = "".join(digit_pattern[:6])
                    btc_price = float(price_str)
                else:
                    btc_price = 0.0
        
        # Extract Up/Down prices from the radio buttons
        # Pattern: radio "Up 53¢" or "Down 49¢"
        up_match = re.search(r'Up["\s]*(\d+)¢', snapshot_text)
        down_match = re.search(r'Down["\s]*(\d+)¢', snapshot_text)
        
        up_price = float(up_match.group(1)) / 100 if up_match else 0.5
        down_price = float(down_match.group(1)) / 100 if down_match else 0.5
        
        # Also try paragraph format: "Up" then "53¢"
        if not up_match:
            up_para = re.search(r'paragraph: Up.*?paragraph: (\d+)¢', snapshot_text, re.DOTALL)
            if up_para:
                up_price = float(up_para.group(1)) / 100
        
        if not down_match:
            down_para = re.search(r'paragraph: Down.*?paragraph: (\d+)¢', snapshot_text, re.DOTALL)
            if down_para:
                down_price = float(down_para.group(1)) / 100
        
        # Extract countdown - look for MINS and SECS sections
        mins_match = re.search(r'MINS.*?(\d+)', snapshot_text)
        secs_match = re.search(r'SECS.*?(\d+)', snapshot_text)
        
        # Also try to find digit pairs near MINS/SECS
        time_remaining_minutes = None
        time_remaining_seconds = None
        
        # Look for the timer pattern with digit refs
        timer_section = re.search(r'generic \[ref=e145\].*?MINS.*?SECS', snapshot_text, re.DOTALL)
        if timer_section:
            timer_text = timer_section.group(0)
            # Extract minutes digits (2 digits before MINS)
            min_digits = re.findall(r'"(\d)"', timer_text.split('MINS')[0])
            if len(min_digits) >= 2:
                time_remaining_minutes = int(min_digits[-2] + min_digits[-1])
            # Extract seconds digits (2 digits before SECS)
            sec_part = timer_text.split('MINS')[-1] if 'MINS' in timer_text else timer_text
            sec_digits = re.findall(r'"(\d)"', sec_part.split('SECS')[0])
            if len(sec_digits) >= 2:
                time_remaining_seconds = int(sec_digits[-2] + sec_digits[-1])
        
        # Extract volume
        vol_match = re.search(r'\$?([\d,]+)\s*Vol', snapshot_text)
        volume = float(vol_match.group(1).replace(",", "")) if vol_match else None
        
        # Extract user position
        user_position_side = None
        user_position_qty = None
        user_position_avg = None
        user_position_value = None
        user_position_pnl = None
        
        # Look for position table: OUTCOME, QTY, AVG, VALUE, RETURN
        position_match = re.search(
            r'generic \[ref=e286\]: (Up|Down).*?'
            r'generic \[ref=e287\]: "(\d+)".*?'
            r'generic \[ref=e288\]: (\d+)¢.*?'
            r'generic \[ref=e291\]: \$([\d.]+).*?'
            r'button "([+-]?\$[\d.]+)"',
            snapshot_text, re.DOTALL
        )
        
        if position_match:
            user_position_side = position_match.group(1)
            user_position_qty = int(position_match.group(2))
            user_position_avg = float(position_match.group(3)) / 100
            user_position_value = float(position_match.group(4))
            pnl_str = position_match.group(5).replace("$", "").replace("+", "")
            user_position_pnl = float(pnl_str)
        
        # Extract price to beat if shown
        price_to_beat = None
        ptb_match = re.search(r'price to beat.*?\$([\d,]+\.?\d*)', snapshot_text, re.IGNORECASE)
        if ptb_match:
            price_to_beat = float(ptb_match.group(1).replace(",", ""))
        
        # Get URL from the links
        url_match = re.search(r'/url: (https?://polymarket\.com/event/[^\s\n]+)', snapshot_text)
        market_url = url_match.group(1) if url_match else ""
        if not market_url:
            url_match = re.search(r'/url: (/event/btc-updown[^\s\n]+)', snapshot_text)
            market_url = f"https://polymarket.com{url_match.group(1)}" if url_match else ""
        
        return PolymarketBTC15mData(
            market_title=market_title,
            market_url=market_url,
            btc_price=btc_price,
            price_to_beat=price_to_beat,
            up_price=up_price,
            down_price=down_price,
            time_remaining_minutes=time_remaining_minutes,
            time_remaining_seconds=time_remaining_seconds,
            volume=volume,
            user_position_side=user_position_side,
            user_position_qty=user_position_qty,
            user_position_avg=user_position_avg,
            user_position_value=user_position_value,
            user_position_pnl=user_position_pnl,
            raw_snapshot=snapshot_text[:2000] if len(snapshot_text) > 2000 else snapshot_text,
        )
        
    except Exception as e:
        logger.error(f"Failed to parse Polymarket snapshot: {e}")
        return None


async def fetch_polymarket_from_browser() -> Dict[str, Any]:
    """
    Fetch Polymarket BTC 15m data from the attached Chrome tab.
    
    Returns structured market data ready for EDGE_SCORE analysis.
    """
    client = ClawdbotBrowserClient()
    
    try:
        # Get browser snapshot
        result = client.browser_snapshot(profile="chrome")
        
        if not result.get("success"):
            error = result.get("error", "Unknown error")
            if "no tab is connected" in error.lower():
                return {
                    "success": False,
                    "error": "No browser tab attached. Click the Clawdbot Browser Relay extension icon on your Polymarket tab.",
                    "code": "NO_TAB"
                }
            return {"success": False, "error": error}
        
        # Get the snapshot text
        snapshot_data = result.get("data", {})
        
        # The snapshot might be a string directly or nested
        if isinstance(snapshot_data, str):
            snapshot_text = snapshot_data
        elif isinstance(snapshot_data, dict):
            snapshot_text = snapshot_data.get("snapshot", str(snapshot_data))
        else:
            snapshot_text = str(snapshot_data)
        
        # Check if this is a Polymarket page
        if "polymarket" not in snapshot_text.lower() and "btc" not in snapshot_text.lower():
            return {
                "success": False,
                "error": "The attached tab doesn't appear to be a Polymarket BTC market. Navigate to a BTC Up/Down market first.",
                "code": "WRONG_PAGE"
            }
        
        # Parse the snapshot
        market_data = parse_polymarket_btc_snapshot(snapshot_text)
        
        if not market_data:
            return {
                "success": False,
                "error": "Could not parse market data from page. Make sure you're on a BTC 15-minute Up/Down market.",
                "code": "PARSE_ERROR",
                "raw_preview": snapshot_text[:500]
            }
        
        return {
            "success": True,
            "data": market_data.to_dict(),
            "source": "chrome_relay"
        }
        
    finally:
        client.close()
