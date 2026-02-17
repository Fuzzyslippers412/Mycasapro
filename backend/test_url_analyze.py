#!/usr/bin/env python3
"""
Quick test script for URL analysis
"""
import asyncio
import sys

async def test_url_analysis(url: str):
    """Test the full analysis flow"""
    from agents.finance import FinanceAgent

    print(f"Testing URL: {url}\n")

    agent = FinanceAgent()
    result = await agent.analyze_polymarket_direction(market_url=url)

    if "error" in result:
        print(f"❌ ERROR: {result.get('message', 'Unknown error')}")
        return False

    print("✅ SUCCESS! Analysis complete:\n")
    print(f"Call: {result.get('call')}")
    print(f"Confidence: {result.get('confidence')}")
    print(f"Prob Up: {result.get('prob_up', 0):.1%}")
    print(f"Recommended Bet: ${result.get('recommended_bet_usd', 0):.2f} ({result.get('recommended_bet_pct', 0):.1f}%)")
    print(f"\nReasons:")
    for reason in result.get('reasons', [])[:3]:
        print(f"  • {reason}")

    return True

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "https://polymarket.com/event/btc-updown-15m-1769902200"
    success = asyncio.run(test_url_analysis(url))
    sys.exit(0 if success else 1)
