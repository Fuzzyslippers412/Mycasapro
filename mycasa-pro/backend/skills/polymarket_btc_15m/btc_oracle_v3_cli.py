#!/usr/bin/env python3
"""
BTC Oracle V3 CLI - Quick prediction tool
Usage: python btc_oracle_v3_cli.py [target_price] [minutes]
"""
import sys
import argparse
sys.path.insert(0, '/Users/chefmbororo/clawd/apps/mycasa-pro/backend')
from skills.polymarket_btc_15m.btc_oracle_v3 import run_oracle_v3, get_chainlink_price
from datetime import datetime

def main():
    parser = argparse.ArgumentParser(description='BTC Oracle V3 - 15min Up/Down Prediction')
    parser.add_argument('--price', type=float, help='Target price to beat')
    parser.add_argument('--minutes', type=int, default=15, help='Time window in minutes (default: 15)')
    parser.add_argument('--up', type=float, default=0.50, help='Up odds (default: 0.50)')
    parser.add_argument('--down', type=float, default=0.50, help='Down odds (default: 0.50)')
    
    args = parser.parse_args()
    
    # If no price given, use current BTC price
    if not args.price:
        args.price = get_chainlink_price()
        print(f"Using current BTC price: ${args.price:,.2f}")
    
    time_sec = args.minutes * 60
    
    print("="*70)
    print(f"BTC ORACLE V3 - {args.minutes}-min Prediction")
    print(f"Target: ${args.price:,.2f} | Time: {args.minutes}min")
    print(f"Market Odds - UP: {args.up:.1%} | DOWN: {args.down:.1%}")
    print("="*70)
    print()
    
    result = run_oracle_v3(
        target_price=args.price,
        time_remaining_sec=time_sec,
        up_odds=args.up,
        down_odds=args.down
    )
    
    # Clean output
    print("🎯 PREDICTION:", result['call'].upper())
    print("📊 Confidence:", result['confidence'])
    print("💰 Bet Size:", result['bet_size'])
    print("🎲 Win Probability: {:.1f}%".format(result['estimated_win_prob']*100))
    print("📈 Expected Value: +{:.3f}".format(result['expected_value']))

if __name__ == '__main__()
    main()
