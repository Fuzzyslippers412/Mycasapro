#!/usr/bin/env python3
"""
BTC ORACLE V2 - Survival Mode
Fixed based on real trading lessons:
1. Price distance to target matters MORE as time runs out
2. Taker flow only matters if price can realistically reach target
3. Momentum confirms or denies the move
4. Clear veto rules when signals conflict
"""

import json
import urllib.request
from datetime import datetime
from typing import Tuple, Dict, Any, Optional

# ==================== CONFIGURATION ====================

class OracleConfig:
    """Tuned from Jan 26-27 and Jan 31 sessions"""
    
    # Taker thresholds
    TAKER_EXTREME_DOWN = 0.30   # Below this = extreme sell pressure
    TAKER_STRONG_DOWN = 0.50    # Below this = strong sell
    TAKER_STRONG_UP = 1.50      # Above this = strong buy
    TAKER_EXTREME_UP = 2.00     # Above this = extreme buy
    
    # Price distance thresholds (as % of price)
    # BTC moves ~0.1-0.3% in 15 mins typically
    PRICE_DIST_EASY = 0.05      # <0.05% = easily reachable
    PRICE_DIST_MODERATE = 0.15  # 0.05-0.15% = moderate challenge
    PRICE_DIST_HARD = 0.25      # 0.15-0.25% = hard but possible
    PRICE_DIST_IMPOSSIBLE = 0.35 # >0.35% = nearly impossible in 15 min
    
    # Time thresholds (seconds remaining)
    TIME_EARLY = 600            # >10 min = early, flow matters most
    TIME_MID = 300              # 5-10 min = mid, balanced
    TIME_LATE = 180             # 3-5 min = late, position matters more
    TIME_CRITICAL = 120         # <2 min = critical, position dominates
    
    # Weight adjustments by time phase
    # [taker_weight, momentum_weight, position_weight]
    WEIGHTS_EARLY = (0.50, 0.25, 0.25)
    WEIGHTS_MID = (0.40, 0.25, 0.35)
    WEIGHTS_LATE = (0.25, 0.25, 0.50)
    WEIGHTS_CRITICAL = (0.15, 0.15, 0.70)
    
    # Edge thresholds
    EDGE_STRONG = 0.40          # Strong conviction
    EDGE_MODERATE = 0.25        # Moderate conviction
    EDGE_WEAK = 0.15            # Weak, probably skip
    
    # Veto rules
    VETO_DIST_PCT = 0.30        # If price >0.30% away with <3 min, veto flow
    VETO_TIME_SEC = 180         # Veto kicks in under 3 minutes


def fetch_json(url: str, timeout: int = 10) -> dict:
    """Fetch JSON from URL"""
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read())


def get_binance_data() -> Dict[str, Any]:
    """Fetch all Binance data in one go"""
    # Recent trades for taker ratio
    trades = fetch_json("https://api.binance.com/api/v3/trades?symbol=BTCUSDT&limit=500")
    
    buy_vol = sum(float(t['qty']) for t in trades if not t['isBuyerMaker'])
    sell_vol = sum(float(t['qty']) for t in trades if t['isBuyerMaker'])
    taker_ratio = buy_vol / sell_vol if sell_vol > 0 else 999
    
    # Orderbook
    book = fetch_json("https://api.binance.com/api/v3/depth?symbol=BTCUSDT&limit=20")
    bid_vol = sum(float(b[1]) for b in book['bids'])
    ask_vol = sum(float(a[1]) for a in book['asks'])
    book_ratio = bid_vol / ask_vol if ask_vol > 0 else 999
    
    # Klines for momentum and current price
    klines = fetch_json("https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1m&limit=10")
    closes = [float(k[4]) for k in klines]
    current_price = closes[-1]
    
    # Momentum calculations
    delta_p1 = (closes[-1] - closes[-2]) / closes[-2] * 100 if len(closes) >= 2 else 0
    delta_p3 = (closes[-1] - closes[-4]) / closes[-4] * 100 if len(closes) >= 4 else 0
    delta_p5 = (closes[-1] - closes[-6]) / closes[-6] * 100 if len(closes) >= 6 else 0
    
    return {
        'current_price': current_price,
        'taker_ratio': taker_ratio,
        'buy_vol': buy_vol,
        'sell_vol': sell_vol,
        'book_ratio': book_ratio,
        'bid_vol': bid_vol,
        'ask_vol': ask_vol,
        'delta_p1': delta_p1,
        'delta_p3': delta_p3,
        'delta_p5': delta_p5,
    }


def calculate_taker_score(taker_ratio: float) -> Tuple[float, str]:
    """
    Calculate taker score from -1 to +1
    Returns (score, description)
    """
    cfg = OracleConfig
    
    if taker_ratio < cfg.TAKER_EXTREME_DOWN:
        return (-1.0, f"EXTREME SELL ({taker_ratio:.2f})")
    elif taker_ratio < cfg.TAKER_STRONG_DOWN:
        return (-0.6, f"STRONG SELL ({taker_ratio:.2f})")
    elif taker_ratio < 0.8:
        return (-0.3, f"MODERATE SELL ({taker_ratio:.2f})")
    elif taker_ratio <= 1.2:
        return (0.0, f"NEUTRAL ({taker_ratio:.2f})")
    elif taker_ratio <= cfg.TAKER_STRONG_UP:
        return (0.3, f"MODERATE BUY ({taker_ratio:.2f})")
    elif taker_ratio <= cfg.TAKER_EXTREME_UP:
        return (0.6, f"STRONG BUY ({taker_ratio:.2f})")
    else:
        return (1.0, f"EXTREME BUY ({taker_ratio:.2f})")


def calculate_momentum_score(delta_p1: float, delta_p3: float, delta_p5: float) -> Tuple[float, str]:
    """
    Calculate momentum score from -1 to +1
    Weight recent moves more heavily
    """
    # Weighted average: 50% p1, 30% p3, 20% p5
    weighted_mom = (0.50 * delta_p1) + (0.30 * delta_p3) + (0.20 * delta_p5)
    
    # Check alignment
    aligned = (delta_p1 > 0 and delta_p3 > 0) or (delta_p1 < 0 and delta_p3 < 0)
    
    if weighted_mom < -0.15:
        score = -1.0
        desc = f"STRONG DOWN ({weighted_mom:+.3f}%)"
    elif weighted_mom < -0.05:
        score = -0.5
        desc = f"MODERATE DOWN ({weighted_mom:+.3f}%)"
    elif weighted_mom < 0.05:
        score = 0.0
        desc = f"NEUTRAL ({weighted_mom:+.3f}%)"
    elif weighted_mom < 0.15:
        score = 0.5
        desc = f"MODERATE UP ({weighted_mom:+.3f}%)"
    else:
        score = 1.0
        desc = f"STRONG UP ({weighted_mom:+.3f}%)"
    
    # Boost if aligned
    if aligned and abs(score) > 0:
        score = score * 1.2
        score = max(-1.0, min(1.0, score))
        desc += " [ALIGNED]"
    
    return (score, desc)


def calculate_position_score(
    current_price: float, 
    target_price: float,
    time_remaining_sec: int
) -> Tuple[float, str, bool]:
    """
    Calculate position score based on price distance to target
    Returns (score, description, veto_flag)
    
    Positive score = price favors UP (current >= target)
    Negative score = price favors DOWN (current < target)
    """
    cfg = OracleConfig
    
    # Calculate distance as percentage
    distance_pct = ((current_price - target_price) / target_price) * 100
    abs_dist = abs(distance_pct)
    
    # Determine difficulty
    if abs_dist < cfg.PRICE_DIST_EASY:
        difficulty = "EASY"
        magnitude = 0.3
    elif abs_dist < cfg.PRICE_DIST_MODERATE:
        difficulty = "MODERATE"
        magnitude = 0.5
    elif abs_dist < cfg.PRICE_DIST_HARD:
        difficulty = "HARD"
        magnitude = 0.7
    elif abs_dist < cfg.PRICE_DIST_IMPOSSIBLE:
        difficulty = "VERY HARD"
        magnitude = 0.9
    else:
        difficulty = "IMPOSSIBLE"
        magnitude = 1.0
    
    # Direction: positive distance = above target (UP winning), negative = below (DOWN winning)
    if distance_pct >= 0:
        score = magnitude
        direction = "ABOVE"
    else:
        score = -magnitude
        direction = "BELOW"
    
    desc = f"{direction} by {abs_dist:.3f}% (${abs(current_price - target_price):.2f}) - {difficulty}"
    
    # VETO CHECK: If too far with too little time, veto opposite signals
    veto = False
    if time_remaining_sec < cfg.VETO_TIME_SEC and abs_dist > cfg.VETO_DIST_PCT:
        veto = True
        desc += " [VETO ACTIVE]"
    
    return (score, desc, veto)


def get_time_weights(time_remaining_sec: int) -> Tuple[float, float, float, str]:
    """
    Get weights based on time remaining
    Returns (taker_w, momentum_w, position_w, phase_name)
    """
    cfg = OracleConfig
    
    if time_remaining_sec > cfg.TIME_EARLY:
        return (*cfg.WEIGHTS_EARLY, "EARLY")
    elif time_remaining_sec > cfg.TIME_MID:
        return (*cfg.WEIGHTS_MID, "MID")
    elif time_remaining_sec > cfg.TIME_LATE:
        return (*cfg.WEIGHTS_LATE, "LATE")
    else:
        return (*cfg.WEIGHTS_CRITICAL, "CRITICAL")


def oracle_analysis(
    target_price: float,
    time_remaining_sec: int,
    up_odds: float,
    down_odds: float,
    binance_data: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Main oracle analysis function
    
    Args:
        target_price: Price to beat from Polymarket
        time_remaining_sec: Seconds until market closes
        up_odds: Current UP price (e.g., 0.38 for 38¢)
        down_odds: Current DOWN price (e.g., 0.62 for 62¢)
        binance_data: Optional pre-fetched data
    
    Returns:
        Complete analysis dict with call, confidence, reasons
    """
    cfg = OracleConfig
    
    # Fetch Binance data if not provided
    if binance_data is None:
        binance_data = get_binance_data()
    
    current_price = binance_data['current_price']
    
    # Calculate component scores
    taker_score, taker_desc = calculate_taker_score(binance_data['taker_ratio'])
    
    mom_score, mom_desc = calculate_momentum_score(
        binance_data['delta_p1'],
        binance_data['delta_p3'],
        binance_data['delta_p5']
    )
    
    pos_score, pos_desc, veto_active = calculate_position_score(
        current_price, target_price, time_remaining_sec
    )
    
    # Get time-adjusted weights
    taker_w, mom_w, pos_w, time_phase = get_time_weights(time_remaining_sec)
    
    # Calculate raw edge
    raw_edge = (taker_w * taker_score) + (mom_w * mom_score) + (pos_w * pos_score)
    
    # Apply veto if active
    final_edge = raw_edge
    veto_applied = False
    
    if veto_active:
        # If position says DOWN (negative) but edge says UP, override to DOWN
        if pos_score < 0 and raw_edge > 0:
            final_edge = pos_score * 0.8  # Force DOWN
            veto_applied = True
        # If position says UP (positive) but edge says DOWN, override to UP
        elif pos_score > 0 and raw_edge < 0:
            final_edge = pos_score * 0.8  # Force UP
            veto_applied = True
    
    # Check for contradictions (reduce confidence)
    contradiction = False
    if (taker_score > 0.3 and mom_score < -0.3) or (taker_score < -0.3 and mom_score > 0.3):
        if not veto_applied:
            final_edge = final_edge * 0.7
        contradiction = True
    
    # Determine call
    if final_edge >= cfg.EDGE_MODERATE:
        call = "UP"
    elif final_edge <= -cfg.EDGE_MODERATE:
        call = "DOWN"
    else:
        call = "NO_TRADE"
    
    # Determine confidence
    abs_edge = abs(final_edge)
    if abs_edge >= cfg.EDGE_STRONG:
        confidence = "HIGH"
    elif abs_edge >= cfg.EDGE_MODERATE:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"
    
    # Bet sizing
    if call == "NO_TRADE":
        bet_size = "$0"
    elif confidence == "HIGH":
        bet_size = "MAX ($40-50)"
    elif confidence == "MEDIUM":
        bet_size = "MEDIUM ($25-35)"
    else:
        bet_size = "SMALL ($15-25)"
    
    # Calculate expected value
    if call == "UP":
        # If we buy UP at up_odds and win, we get (1 - up_odds) profit per dollar
        win_prob = 0.5 + (final_edge * 0.4)  # Convert edge to probability estimate
        ev = (win_prob * (1 - up_odds)) - ((1 - win_prob) * up_odds)
    elif call == "DOWN":
        win_prob = 0.5 + (abs(final_edge) * 0.4)
        ev = (win_prob * (1 - down_odds)) - ((1 - win_prob) * down_odds)
    else:
        ev = 0
        win_prob = 0.5
    
    return {
        'call': call,
        'confidence': confidence,
        'edge': final_edge,
        'bet_size': bet_size,
        'estimated_win_prob': win_prob,
        'expected_value': ev,
        
        'market': {
            'target_price': target_price,
            'current_price': current_price,
            'price_gap': current_price - target_price,
            'price_gap_pct': ((current_price - target_price) / target_price) * 100,
            'time_remaining_sec': time_remaining_sec,
            'time_phase': time_phase,
            'up_odds': up_odds,
            'down_odds': down_odds,
        },
        
        'signals': {
            'taker': {
                'score': taker_score,
                'ratio': binance_data['taker_ratio'],
                'buy_vol': binance_data['buy_vol'],
                'sell_vol': binance_data['sell_vol'],
                'desc': taker_desc,
            },
            'momentum': {
                'score': mom_score,
                'delta_p1': binance_data['delta_p1'],
                'delta_p3': binance_data['delta_p3'],
                'delta_p5': binance_data['delta_p5'],
                'desc': mom_desc,
            },
            'position': {
                'score': pos_score,
                'desc': pos_desc,
                'veto_active': veto_active,
            },
            'book': {
                'ratio': binance_data['book_ratio'],
                'bid_vol': binance_data['bid_vol'],
                'ask_vol': binance_data['ask_vol'],
            },
        },
        
        'weights': {
            'taker': taker_w,
            'momentum': mom_w,
            'position': pos_w,
        },
        
        'flags': {
            'veto_applied': veto_applied,
            'contradiction': contradiction,
        },
        
        'timestamp': datetime.utcnow().isoformat(),
    }


def print_analysis(result: Dict[str, Any]):
    """Pretty print the analysis"""
    m = result['market']
    s = result['signals']
    
    print("=" * 60)
    print("BTC ORACLE V2 - SURVIVAL MODE")
    print("=" * 60)
    
    print(f"\n[MARKET]")
    print(f"  Target Price:    ${m['target_price']:,.2f}")
    print(f"  Current Price:   ${m['current_price']:,.2f}")
    print(f"  Gap:             ${m['price_gap']:+,.2f} ({m['price_gap_pct']:+.3f}%)")
    print(f"  Time Remaining:  {m['time_remaining_sec']}s ({m['time_phase']} phase)")
    print(f"  UP Odds:         {m['up_odds']*100:.0f}¢")
    print(f"  DOWN Odds:       {m['down_odds']*100:.0f}¢")
    
    print(f"\n[SIGNALS]")
    print(f"  Taker:    {s['taker']['score']:+.2f} | {s['taker']['desc']}")
    print(f"            Buy: {s['taker']['buy_vol']:.4f} BTC, Sell: {s['taker']['sell_vol']:.4f} BTC")
    print(f"  Momentum: {s['momentum']['score']:+.2f} | {s['momentum']['desc']}")
    print(f"            ΔP1: {s['momentum']['delta_p1']:+.4f}%, ΔP3: {s['momentum']['delta_p3']:+.4f}%")
    print(f"  Position: {s['position']['score']:+.2f} | {s['position']['desc']}")
    print(f"  Book:     {s['book']['ratio']:.2f} (Bid: {s['book']['bid_vol']:.2f}, Ask: {s['book']['ask_vol']:.2f})")
    
    print(f"\n[WEIGHTS - {m['time_phase']}]")
    w = result['weights']
    print(f"  Taker: {w['taker']*100:.0f}%, Momentum: {w['momentum']*100:.0f}%, Position: {w['position']*100:.0f}%")
    
    print(f"\n[FLAGS]")
    flags = result['flags']
    if flags['veto_applied']:
        print(f"  🚨 VETO APPLIED: Position overrides flow signals")
    if flags['contradiction']:
        print(f"  ⚠️  CONTRADICTION: Taker and Momentum disagree")
    if not flags['veto_applied'] and not flags['contradiction']:
        print(f"  ✅ Signals aligned")
    
    print(f"\n" + "=" * 60)
    print("FINAL CALL")
    print("=" * 60)
    
    call = result['call']
    conf = result['confidence']
    edge = result['edge']
    
    if call == "UP":
        emoji = "🟢"
    elif call == "DOWN":
        emoji = "🔴"
    else:
        emoji = "⚪"
    
    print(f"\n  {emoji} CALL: {call}")
    print(f"  📊 CONFIDENCE: {conf}")
    print(f"  📈 EDGE: {edge:+.3f}")
    print(f"  💰 BET SIZE: {result['bet_size']}")
    print(f"  🎯 Est. Win Prob: {result['estimated_win_prob']*100:.1f}%")
    print(f"  💵 Expected Value: {result['expected_value']:+.3f} per $1")
    
    print(f"\n" + "=" * 60)


def run_oracle(target_price: float, time_remaining_sec: int, up_odds: float, down_odds: float):
    """Convenience function to run and print analysis"""
    result = oracle_analysis(target_price, time_remaining_sec, up_odds, down_odds)
    print_analysis(result)
    return result


if __name__ == "__main__()
    import sys
    
    # Default values for testing
    target = float(sys.argv[1]) if len(sys.argv) > 1 else 78739.52
    time_sec = int(sys.argv[2]) if len(sys.argv) > 2 else 300
    up_price = float(sys.argv[3]) if len(sys.argv) > 3 else 0.50
    down_price = float(sys.argv[4]) if len(sys.argv) > 4 else 0.50
    
    run_oracle(target, time_sec, up_price, down_price)
