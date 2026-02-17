#!/usr/bin/env python3
"""
Live Scanner - Parses Polymarket page and runs Oracle V2
"""

import re
import sys
import json
from typing import Optional, Dict, Any, Tuple
from datetime import datetime

# Import oracle
from btc_oracle_v2 import oracle_analysis, print_analysis, get_binance_data


def parse_polymarket_snapshot(snapshot_text: str) -> Dict[str, Any]:
    """
    Parse Polymarket browser snapshot to extract market data
    
    Returns dict with:
    - market_title
    - target_price (price to beat)
    - time_remaining_sec (estimated)
    - up_odds
    - down_odds
    """
    result = {
        'market_title': None,
        'target_price': None,
        'time_remaining_sec': None,
        'time_remaining_min': None,
        'up_odds': None,
        'down_odds': None,
        'current_polymarket_price': None,
        'volume': None,
    }
    
    # Extract market title/time window
    # Pattern: "January 31, 9:15-9:30PM ET"
    title_match = re.search(r'paragraph: ((?:January|February|March|April|May|June|July|August|September|October|November|December) \d+,\s*[\d:]+[AP]M[-–][\d:]+[AP]M\s*ET)', snapshot_text)
    if title_match:
        result['market_title'] = f"BTC Up/Down - {title_match.group(1)}"
    
    # Extract price to beat
    # Pattern: "price to beat $78,739.52"
    ptb_match = re.search(r'price to beat \$?([\d,]+\.?\d*)', snapshot_text)
    if ptb_match:
        result['target_price'] = float(ptb_match.group(1).replace(',', ''))
    
    # Extract time remaining from MINS/SECS pattern
    # Look for digit sequences near MINS and SECS
    mins_section = re.search(r'(\d)\s*(\d)\s*MINS', snapshot_text)
    secs_section = re.search(r'(\d)\s*(\d)\s*SECS', snapshot_text)
    
    mins = 0
    secs = 0
    if mins_section:
        mins = int(mins_section.group(1) + mins_section.group(2))
    if secs_section:
        secs = int(secs_section.group(1) + secs_section.group(2))
    
    if mins > 0 or secs > 0:
        result['time_remaining_sec'] = mins * 60 + secs
        result['time_remaining_min'] = mins
    
    # Extract UP/DOWN odds
    # Pattern: radio "Up 38¢" or "Down 63¢"
    up_match = re.search(r'Up\s*(\d+)¢', snapshot_text)
    down_match = re.search(r'Down\s*(\d+)¢', snapshot_text)
    
    if up_match:
        result['up_odds'] = float(up_match.group(1)) / 100
    if down_match:
        result['down_odds'] = float(down_match.group(1)) / 100
    
    # Extract volume
    vol_match = re.search(r'\$([\d.]+)k?\s*Vol', snapshot_text)
    if vol_match:
        vol_str = vol_match.group(1)
        result['volume'] = float(vol_str) * (1000 if 'k' in snapshot_text[vol_match.end()-2:vol_match.end()+2] else 1)
    
    return result


def run_live_analysis(snapshot_text: str) -> Optional[Dict[str, Any]]:
    """
    Run complete analysis from browser snapshot
    """
    # Parse market data
    market = parse_polymarket_snapshot(snapshot_text)
    
    print("=" * 60)
    print("POLYMARKET DATA PARSED")
    print("=" * 60)
    print(f"  Market: {market['market_title']}")
    print(f"  Target Price: ${market['target_price']:,.2f}" if market['target_price'] else "  Target Price: NOT FOUND")
    print(f"  Time Left: {market['time_remaining_min']}m {market['time_remaining_sec'] % 60 if market['time_remaining_sec'] else 0}s")
    print(f"  UP: {market['up_odds']*100:.0f}¢" if market['up_odds'] else "  UP: NOT FOUND")
    print(f"  DOWN: {market['down_odds']*100:.0f}¢" if market['down_odds'] else "  DOWN: NOT FOUND")
    
    # Validate required data
    if not market['target_price']:
        print("\n❌ ERROR: Could not find price to beat")
        return None
    
    if not market['time_remaining_sec']:
        print("\n❌ ERROR: Could not determine time remaining")
        # Default to 5 minutes if can't parse
        market['time_remaining_sec'] = 300
        print("  Using default: 300 seconds")
    
    if not market['up_odds'] or not market['down_odds']:
        print("\n❌ ERROR: Could not find odds")
        return None
    
    print("\n")
    
    # Run oracle analysis
    result = oracle_analysis(
        target_price=market['target_price'],
        time_remaining_sec=market['time_remaining_sec'],
        up_odds=market['up_odds'],
        down_odds=market['down_odds']
    )
    
    print_analysis(result)
    
    return result


def quick_scan():
    """
    Quick scan using current Binance data only
    Requires manual input of Polymarket data
    """
    print("=" * 60)
    print("QUICK SCAN MODE")
    print("=" * 60)
    
    # Get Binance data
    binance = get_binance_data()
    
    print(f"\nBinance BTC: ${binance['current_price']:,.2f}")
    print(f"Taker Ratio: {binance['taker_ratio']:.3f}")
    print(f"Book Ratio: {binance['book_ratio']:.3f}")
    print(f"Momentum 1m: {binance['delta_p1']:+.4f}%")
    print(f"Momentum 3m: {binance['delta_p3']:+.4f}%")
    
    # Quick signal summary
    if binance['taker_ratio'] > 2.0:
        print(f"\n🟢 EXTREME BUY PRESSURE (taker {binance['taker_ratio']:.2f})")
    elif binance['taker_ratio'] > 1.5:
        print(f"\n🟢 Strong buy pressure (taker {binance['taker_ratio']:.2f})")
    elif binance['taker_ratio'] < 0.3:
        print(f"\n🔴 EXTREME SELL PRESSURE (taker {binance['taker_ratio']:.2f})")
    elif binance['taker_ratio'] < 0.5:
        print(f"\n🔴 Strong sell pressure (taker {binance['taker_ratio']:.2f})")
    else:
        print(f"\n⚪ Neutral taker flow ({binance['taker_ratio']:.2f})")
    
    if binance['delta_p3'] > 0.05:
        print(f"🟢 Positive momentum ({binance['delta_p3']:+.3f}%)")
    elif binance['delta_p3'] < -0.05:
        print(f"🔴 Negative momentum ({binance['delta_p3']:+.3f}%)")
    else:
        print(f"⚪ Flat momentum ({binance['delta_p3']:+.3f}%)")
    
    return binance


if __name__ == "__main__()
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        quick_scan()
    else:
        # Read snapshot from stdin or file
        if len(sys.argv) > 1:
            with open(sys.argv[1]) as f:
                snapshot = f.read()
        else:
            print("Usage: python live_scanner.py <snapshot_file>")
            print("       python live_scanner.py --quick")
            sys.exit(1)
        
        run_live_analysis(snapshot)
