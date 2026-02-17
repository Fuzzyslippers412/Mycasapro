#!/usr/bin/env python3
"""
BTC ORACLE V3 - Asian Math Edition
Fixes:
1. Chainlink price (what Polymarket uses, not Binance)
2. Dynamic time-decay with exponential urgency
3. Order book microstructure (0.1% depth)
4. ETH-BTC correlation for confluence
5. Whale detection (large trades >5 BTC)
6. Signal-strength based weighting
"""

import json
import urllib.request
from datetime import datetime
from typing import Tuple, Dict, Any, Optional
import requests

# ==================== CONFIGURATION ====================

class OracleConfig:
    """Tuned for 15-min BTC markets"""
    
    # Taker thresholds
    TAKER_EXTREME_DOWN = 0.30
    TAKER_STRONG_DOWN = 0.50
    TAKER_STRONG_UP = 1.50
    TAKER_EXTREME_UP = 2.00
    TAKER_WHALE = 5.00  # 5x+ = whale buying
    
    # Price distance (BTC moves 0.1-0.3% in 15 min)
    PRICE_DIST_EASY = 0.05
    PRICE_DIST_MODERATE = 0.15
    PRICE_DIST_HARD = 0.25
    PRICE_DIST_IMPOSSIBLE = 0.35
    
    # Time weights - exponential decay
    # At 10 min: 50% position, 50% flow
    # At 5 min: 70% position, 30% flow
    # At 2 min: 90% position, 10% flow
    
    # Whale detection
    WHALE_THRESHOLD_BTC = 5.0  # Trade size in BTC
    WHALE_WINDOW_SEC = 60  # Lookback window


def fetch_json(url: str, timeout: int = 10) -> dict:
    """Fetch JSON from URL"""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception as e:
        return {}


def get_chainlink_price() -> float:
    """Get BTC price from Chainlink/Kraken (what Polymarket uses)"""
    try:
        # Kraken is closest proxy to Chainlink
        r = requests.get('https://api.kraken.com/0/public/Ticker?pair=XBTUSD', timeout=10)
        data = r.json()
        return float(data['result']['XXBTZUSD']['c'][0])
    except:
        # Fallback to Binance
        ticker = fetch_json("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT")
        return float(ticker.get('price', 0))


def get_eth_price() -> float:
    """Get ETH price for correlation check"""
    try:
        r = requests.get('https://api.kraken.com/0/public/Ticker?pair=ETHUSD', timeout=10)
        data = r.json()
        return float(data['result']['XETHZUSD']['c'][0])
    except:
        ticker = fetch_json("https://api.binance.com/api/v3/ticker/price?symbol=ETHUSDT")
        return float(ticker.get('price', 0))


def get_binance_microstructure() -> Dict[str, Any]:
    """Get detailed Binance microstructure data"""
    # Recent trades for taker ratio + whale detection
    trades = fetch_json("https://api.binance.com/api/v3/trades?symbol=BTCUSDT&limit=1000")
    
    buy_vol = 0.0
    sell_vol = 0.0
    whale_buy = 0.0
    whale_sell = 0.0
    
    for t in trades:
        qty = float(t['qty'])
        if not t['isBuyerMaker']:
            buy_vol += qty
            if qty >= OracleConfig.WHALE_THRESHOLD_BTC:
                whale_buy += qty
        else:
            sell_vol += qty
            if qty >= OracleConfig.WHALE_THRESHOLD_BTC:
                whale_sell += qty
    
    taker_ratio = buy_vol / sell_vol if sell_vol > 0 else 999
    whale_ratio = whale_buy / whale_sell if whale_sell > 0 else (999 if whale_buy > 0 else 1)
    
    # Orderbook depth within 0.1% of mid
    book = fetch_json("https://api.binance.com/api/v3/depth?symbol=BTCUSDT&limit=100")
    
    # Get mid price
    best_bid = float(book['bids'][0][0])
    best_ask = float(book['asks'][0][0])
    mid = (best_bid + best_ask) / 2
    
    # Calculate depth within 0.1%
    threshold = mid * 0.001  # 0.1%
    
    bid_depth = 0.0
    for price, qty in book['bids']:
        p, q = float(price), float(qty)
        if mid - p <= threshold:
            bid_depth += q
        else:
            break
    
    ask_depth = 0.0
    for price, qty in book['asks']:
        p, q = float(price), float(qty)
        if p - mid <= threshold:
            ask_depth += q
        else:
            break
    
    micro_imbalance = bid_depth / ask_depth if ask_depth > 0 else 999
    
    # Klines for momentum
    klines = fetch_json("https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1m&limit=10")
    closes = [float(k[4]) for k in klines]
    
    delta_p1 = (closes[-1] - closes[-2]) / closes[-2] * 100 if len(closes) >= 2 else 0
    delta_p3 = (closes[-1] - closes[-4]) / closes[-4] * 100 if len(closes) >= 4 else 0
    delta_p5 = (closes[-1] - closes[-6]) / closes[-6] * 100 if len(closes) >= 6 else 0
    
    # Volatility (ATR-like)
    highs = [float(k[2]) for k in klines[-5:]]
    lows = [float(k[3]) for k in klines[-5:]]
    ranges = [h - l for h, l in zip(highs, lows)]
    avg_range = sum(ranges) / len(ranges) if ranges else 0
    volatility = (avg_range / closes[-1]) * 100 if closes[-1] else 0
    
    return {
        'binance_price': closes[-1],
        'taker_ratio': taker_ratio,
        'whale_ratio': whale_ratio,
        'whale_buy': whale_buy,
        'whale_sell': whale_sell,
        'micro_imbalance': micro_imbalance,
        'bid_depth_01pct': bid_depth,
        'ask_depth_01pct': ask_depth,
        'delta_p1': delta_p1,
        'delta_p3': delta_p3,
        'delta_p5': delta_p5,
        'volatility_5min': volatility,
        'buy_vol': buy_vol,
        'sell_vol': sell_vol,
    }


def calculate_dynamic_weights(time_remaining_sec: int, signal_strength: float) -> Tuple[float, float, float]:
    """
    Dynamic weights based on:
    1. Time decay (exponential)
    2. Signal strength (stronger signal = more weight)
    
    signal_strength: 0-1, how extreme the taker ratio is
    """
    # Time factor: 0-1 where 0 = market close, 1 = market open
    total_time = 900  # 15 min
    time_factor = time_remaining_sec / total_time
    
    # Position weight increases as time runs out
    # Exponential curve: at 50% time, position is 70% weight
    position_weight = 1 - (time_factor ** 1.5) * 0.5  # 0.5 to 1.0
    position_weight = min(0.85, max(0.35, position_weight))  # Cap at 35-85%
    
    # Remaining weight split between taker and momentum
    remaining = 1 - position_weight
    
    # Stronger taker signal = more weight to taker
    taker_weight = remaining * (0.5 + signal_strength * 0.3)  # 50-80% of remaining
    mom_weight = remaining - taker_weight
    
    return (taker_weight, mom_weight, position_weight)


def calculate_taker_score(taker_ratio: float, whale_ratio: float) -> Tuple[float, float]:
    """
    Combined taker + whale score
    Returns (score, description)
    """
    cfg = OracleConfig
    
    # Base taker score
    if taker_ratio < cfg.TAKER_EXTREME_DOWN:
        base_score = -1.0
        desc = f"EXTREME SELL ({taker_ratio:.2f})"
    elif taker_ratio < cfg.TAKER_STRONG_DOWN:
        base_score = -0.6
        desc = f"STRONG SELL ({taker_ratio:.2f})"
    elif taker_ratio < 0.8:
        base_score = -0.3
        desc = f"MODERATE SELL ({taker_ratio:.2f})"
    elif taker_ratio <= 1.2:
        base_score = 0.0
        desc = f"NEUTRAL ({taker_ratio:.2f})"
    elif taker_ratio <= cfg.TAKER_STRONG_UP:
        base_score = 0.3
        desc = f"MODERATE BUY ({taker_ratio:.2f})"
    elif taker_ratio <= cfg.TAKER_EXTREME_UP:
        base_score = 0.6
        desc = f"STRONG BUY ({taker_ratio:.2f})"
    else:
        base_score = 1.0
        desc = f"EXTREME BUY ({taker_ratio:.2f})"
    
    # Whale amplification
    if whale_ratio > 3.0 and base_score > 0:
        base_score = min(1.0, base_score * 1.3)
        desc += " + WHALE BUY"
    elif whale_ratio < 0.33 and base_score < 0:
        base_score = max(-1.0, base_score * 1.3)
        desc += " + WHALE SELL"
    
    # Calculate signal strength for weighting
    signal_strength = min(1.0, abs(taker_ratio - 1) / 4.0)  # 0-1
    
    return (base_score, signal_strength, desc)


def calculate_momentum_score(delta_p1: float, delta_p3: float, delta_p5: float, 
                             volatility: float) -> Tuple[float, str]:
    """Momentum with volatility adjustment"""
    # Weighted: 50% p1, 30% p3, 20% p5
    weighted = (0.50 * delta_p1) + (0.30 * delta_p3) + (0.20 * delta_p5)
    
    # Normalize by volatility (z-score like)
    if volatility > 0:
        normalized = weighted / (volatility + 0.02)  # +0.02 to avoid div by zero
    else:
        normalized = weighted * 10  # Assume low vol
    
    # Check alignment
    aligned = (delta_p1 > 0 and delta_p3 > 0) or (delta_p1 < 0 and delta_p3 < 0)
    
    if normalized < -1.0:
        score = -1.0
        desc = f"STRONG DOWN (z={normalized:.2f})"
    elif normalized < -0.3:
        score = -0.5
        desc = f"MODERATE DOWN (z={normalized:.2f})"
    elif normalized < 0.3:
        score = 0.0
        desc = f"NEUTRAL (z={normalized:.2f})"
    elif normalized < 1.0:
        score = 0.5
        desc = f"MODERATE UP (z={normalized:.2f})"
    else:
        score = 1.0
        desc = f"STRONG UP (z={normalized:.2f})"
    
    if aligned and abs(score) > 0:
        score *= 1.15
        score = max(-1.0, min(1.0, score))
        desc += " [ALIGNED]"
    
    return (score, desc)


def check_eth_confluence(eth_delta_p3: float, btc_delta_p3: float) -> Tuple[float, str]:
    """Check if ETH confirms BTC move"""
    same_direction = (eth_delta_p3 > 0 and btc_delta_p3 > 0) or (eth_delta_p3 < 0 and btc_delta_p3 < 0)
    
    if same_direction and abs(eth_delta_p3) > 0.05:
        # ETH confirms
        boost = 0.1 if btc_delta_p3 > 0 else -0.1
        return (boost, f"ETH confirms ({eth_delta_p3:+.3f}%)")
    elif not same_direction and abs(eth_delta_p3) > 0.1:
        # ETH diverges
        boost = -0.15 if btc_delta_p3 > 0 else 0.15
        return (boost, f"ETH DIVERGES ({eth_delta_p3:+.3f}%)")
    else:
        return (0.0, "ETH neutral")


def calculate_position_score(current_price: float, target_price: float, 
                             time_remaining_sec: int, volatility: float) -> Tuple[float, str, bool]:
    """
    Position score with time and volatility adjustment
    """
    cfg = OracleConfig
    distance_pct = ((current_price - target_price) / target_price) * 100
    abs_dist = abs(distance_pct)
    
    # Time-adjusted difficulty: less time = harder to overcome distance
    time_factor = max(0.3, time_remaining_sec / 900)  # 0.3 to 1.0
    
    # Volatility-adjusted: high vol = easier to overcome distance
    vol_factor = min(2.0, max(0.5, volatility / 0.1))  # 0.5 to 2.0
    
    adjusted_dist = abs_dist / (time_factor * vol_factor)
    
    if adjusted_dist < cfg.PRICE_DIST_EASY:
        difficulty = "EASY"
        magnitude = 0.3
    elif adjusted_dist < cfg.PRICE_DIST_MODERATE:
        difficulty = "MODERATE"
        magnitude = 0.5
    elif adjusted_dist < cfg.PRICE_DIST_HARD:
        difficulty = "HARD"
        magnitude = 0.7
    elif adjusted_dist < cfg.PRICE_DIST_IMPOSSIBLE:
        difficulty = "VERY HARD"
        magnitude = 0.9
    else:
        difficulty = "IMPOSSIBLE"
        magnitude = 1.0
    
    score = magnitude if distance_pct >= 0 else -magnitude
    direction = "ABOVE" if distance_pct >= 0 else "BELOW"
    
    desc = f"{direction} by {abs_dist:.3f}% → adj {adjusted_dist:.3f}% | {difficulty}"
    
    # Veto if impossible with little time
    veto = (time_remaining_sec < 120 and abs_dist > 0.30)
    
    return (score, desc, veto)


def oracle_analysis_v3(target_price: float, time_remaining_sec: int, 
                       up_odds: float, down_odds: float) -> Dict[str, Any]:
    """Main oracle analysis - V3"""
    cfg = OracleConfig
    
    # Fetch data
    chainlink_price = get_chainlink_price()
    binance_data = get_binance_microstructure()
    
    # Get ETH for confluence
    eth_klines = fetch_json("https://api.binance.com/api/v3/klines?symbol=ETHUSDT&interval=1m&limit=5")
    eth_closes = [float(k[4]) for k in eth_klines] if eth_klines else [0, 0, 0, 0]
    eth_delta_p3 = (eth_closes[-1] - eth_closes[-4]) / eth_closes[-4] * 100 if len(eth_closes) >= 4 else 0
    
    # Calculate components
    taker_score, signal_strength, taker_desc = calculate_taker_score(
        binance_data['taker_ratio'], 
        binance_data['whale_ratio']
    )
    
    mom_score, mom_desc = calculate_momentum_score(
        binance_data['delta_p1'],
        binance_data['delta_p3'],
        binance_data['delta_p5'],
        binance_data['volatility_5min']
    )
    
    pos_score, pos_desc, veto = calculate_position_score(
        chainlink_price, target_price, time_remaining_sec, binance_data['volatility_5min']
    )
    
    # ETH confluence
    eth_boost, eth_desc = check_eth_confluence(eth_delta_p3, binance_data['delta_p3'])
    
    # Dynamic weights
    taker_w, mom_w, pos_w = calculate_dynamic_weights(time_remaining_sec, signal_strength)
    
    # Composite edge
    raw_edge = (taker_w * taker_score) + (mom_w * mom_score) + (pos_w * pos_score) + eth_boost
    
    # Confidence adjustment
    confidence_penalty = 0.0
    
    # Reduce confidence if microstructure contradicts
    micro_contra = (taker_score > 0.3 and binance_data['micro_imbalance'] < 0.5) or \
                   (taker_score < -0.3 and binance_data['micro_imbalance'] > 2.0)
    if micro_contra:
        confidence_penalty += 0.15
    
    # Reduce confidence if price divergence
    price_diverge = abs(chainlink_price - binance_data['binance_price']) / chainlink_price * 100
    if price_diverge > 0.15:  # >0.15% divergence
        confidence_penalty += 0.1
    
    final_edge = raw_edge * (1 - confidence_penalty)
    
    # Veto override
    if veto and abs(pos_score) > 0.7:
        final_edge = pos_score * 0.9
    
    # Call
    EDGE_THRESHOLD = 0.20
    if final_edge >= EDGE_THRESHOLD:
        call = "UP"
    elif final_edge <= -EDGE_THRESHOLD:
        call = "DOWN"
    else:
        call = "NO_TRADE"
    
    # Confidence
    abs_edge = abs(final_edge)
    if abs_edge >= 0.50:
        confidence = "HIGH"
    elif abs_edge >= 0.30:
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
        bet_size = "SMALL ($10-20)"
    
    # EV
    if call == "UP":
        win_prob = min(0.85, max(0.35, 0.5 + final_edge * 0.5))
        ev = (win_prob * (1 - up_odds)) - ((1 - win_prob) * up_odds)
    elif call == "DOWN":
        win_prob = min(0.85, max(0.35, 0.5 + abs(final_edge) * 0.5))
        ev = (win_prob * (1 - down_odds)) - ((1 - win_prob) * down_odds)
    else:
        win_prob = 0.5
        ev = 0
    
    return {
        'call': call,
        'confidence': confidence,
        'edge': final_edge,
        'bet_size': bet_size,
        'estimated_win_prob': win_prob,
        'expected_value': ev,
        
        'prices': {
            'chainlink': chainlink_price,
            'binance': binance_data['binance_price'],
            'divergence_pct': price_diverge if 'price_diverge' in locals() else 0,
        },
        
        'market': {
            'target_price': target_price,
            'current_price': chainlink_price,
            'price_gap': chainlink_price - target_price,
            'price_gap_pct': ((chainlink_price - target_price) / target_price) * 100,
            'time_remaining_sec': time_remaining_sec,
            'up_odds': up_odds,
            'down_odds': down_odds,
        },
        
        'signals': {
            'taker': {
                'score': taker_score,
                'ratio': binance_data['taker_ratio'],
                'whale_ratio': binance_data['whale_ratio'],
                'desc': taker_desc,
            },
            'momentum': {
                'score': mom_score,
                'delta_p1': binance_data['delta_p1'],
                'delta_p3': binance_data['delta_p3'],
                'volatility': binance_data['volatility_5min'],
                'desc': mom_desc,
            },
            'position': {
                'score': pos_score,
                'desc': pos_desc,
                'veto': veto,
            },
            'microstructure': {
                'imbalance': binance_data['micro_imbalance'],
                'bid_depth': binance_data['bid_depth_01pct'],
                'ask_depth': binance_data['ask_depth_01pct'],
            },
            'eth_confluence': {
                'boost': eth_boost,
                'eth_delta_p3': eth_delta_p3,
                'desc': eth_desc,
            },
        },
        
        'weights': {
            'taker': taker_w,
            'momentum': mom_w,
            'position': pos_w,
        },
        
        'timestamp': datetime.utcnow().isoformat(),
    }


def print_analysis_v3(result: Dict[str, Any]):
    """Pretty print V3 analysis"""
    m = result['market']
    s = result['signals']
    p = result['prices']
    
    print("=" * 65)
    print("BTC ORACLE V3 - ASIAN MATH EDITION")
    print("=" * 65)
    
    print(f"\n[PRICE SOURCES]")
    print(f"  Chainlink (Polymarket): ${p['chainlink']:,.2f}")
    print(f"  Binance:                ${p['binance']:,.2f}")
    print(f"  Divergence:             {p['divergence_pct']:.3f}%")
    
    print(f"\n[MARKET]")
    print(f"  Target:    ${m['target_price']:,.2f}")
    print(f"  Current:   ${m['current_price']:,.2f}")
    print(f"  Gap:       ${m['price_gap']:+,.2f} ({m['price_gap_pct']:+.3f}%)")
    print(f"  Time Left: {m['time_remaining_sec']}s")
    print(f"  UP: {m['up_odds']*100:.0f}¢ | DOWN: {m['down_odds']*100:.0f}¢")
    
    print(f"\n[SIGNALS]")
    print(f"  Taker:    {s['taker']['score']:+.2f} | {s['taker']['desc']}")
    print(f"  Momentum: {s['momentum']['score']:+.2f} | {s['momentum']['desc']}")
    print(f"            vol={s['momentum']['volatility']:.3f}%")
    print(f"  Position: {s['position']['score']:+.2f} | {s['position']['desc']}")
    print(f"  Micro:    imb={s['microstructure']['imbalance']:.2f}")
    print(f"  ETH:      {s['eth_confluence']['boost']:+.2f} | {s['eth_confluence']['desc']}")
    
    print(f"\n[WEIGHTS]")
    w = result['weights']
    print(f"  Taker: {w['taker']*100:.0f}% | Mom: {w['momentum']*100:.0f}% | Pos: {w['position']*100:.0f}%")
    
    print(f"\n" + "=" * 65)
    print("FINAL CALL")
    print("=" * 65)
    
    call = result['call']
    emoji = "🟢" if call == "UP" else ("🔴" if call == "DOWN" else "⚪")
    
    print(f"\n  {emoji} {call}")
    print(f"  Confidence: {result['confidence']}")
    print(f"  EDGE: {result['edge']:+.3f}")
    print(f"  Bet: {result['bet_size']}")
    print(f"  Win Prob: {result['estimated_win_prob']*100:.1f}%")
    print(f"  EV: {result['expected_value']:+.3f}")
    print(f"\n" + "=" * 65)


def run_oracle_v3(target_price: float, time_remaining_sec: int, up_odds: float, down_odds: float):
    """Convenience function"""
    result = oracle_analysis_v3(target_price, time_remaining_sec, up_odds, down_odds)
    print_analysis_v3(result)
    return result


if __name__ == "__main__":
    import sys
    target = float(sys.argv[1]) if len(sys.argv) > 1 else 78739.52
    time_sec = int(sys.argv[2]) if len(sys.argv) > 2 else 300
    up_price = float(sys.argv[3]) if len(sys.argv) > 3 else 0.50
    down_price = float(sys.argv[4]) if len(sys.argv) > 4 else 0.50
    
    run_oracle_v3(target, time_sec, up_price, down_price)
