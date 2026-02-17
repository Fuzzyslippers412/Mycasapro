"""
Example Usage of Polymarket BTC 15m Direction Skill
For Finance Agent (Mamadou) integration
"""
import asyncio
from skill_interface import analyze_btc_15m_direction, quick_call


async def example_full_analysis():
    """
    Example: Full analysis with detailed output
    """
    # Mock market data (in production, this comes from page scraping tool)
    market_data = {
        "captured_at_iso": "2025-01-31T13:00:00Z",
        "market_url": "https://polymarket.com/event/btc-15m",
        "market_title": "Will BTC be above $105,000 at 1:15 PM EST?",
        "market_id": "btc-15m-example",
        "up_label": "Yes",
        "down_label": "No",
        "yes_means_up": True,
        "up_prob": 0.52,
        "down_prob": 0.48,
        "up_spread": 0.02,  # 2% spread
        "down_spread": 0.025,  # 2.5% spread
        "up_best_bid": 0.51,
        "up_best_ask": 0.53,
        "down_best_bid": 0.47,
        "down_best_ask": 0.495,
        "volume_24h_usd": 150000,
        "total_volume_usd": 500000,
        "open_interest_usd": 75000,
        "time_remaining_seconds": 600,  # 10 minutes
        "up_bids": [
            {"price_prob": 0.51, "size": 1000},
            {"price_prob": 0.50, "size": 1500},
            {"price_prob": 0.49, "size": 2000},
        ],
        "up_asks": [
            {"price_prob": 0.53, "size": 800},
            {"price_prob": 0.54, "size": 1200},
            {"price_prob": 0.55, "size": 1800},
        ],
        "down_bids": [
            {"price_prob": 0.47, "size": 1200},
            {"price_prob": 0.46, "size": 1600},
            {"price_prob": 0.45, "size": 2200},
        ],
        "down_asks": [
            {"price_prob": 0.495, "size": 900},
            {"price_prob": 0.505, "size": 1300},
            {"price_prob": 0.515, "size": 1900},
        ],
        "recent_trades": [
            {"side": "buy", "price_prob": 0.52, "size": 500, "time_iso": "2025-01-31T12:59:30Z"},
            {"side": "buy", "price_prob": 0.51, "size": 300, "time_iso": "2025-01-31T12:59:00Z"},
            {"side": "sell", "price_prob": 0.48, "size": 200, "time_iso": "2025-01-31T12:58:30Z"},
        ],
    }

    # Run full analysis
    result = await analyze_btc_15m_direction(
        market_data=market_data,
        bankroll_usd=5000
    )

    # Display results
    print("\n" + "="*60)
    print("POLYMARKET BTC 15M DIRECTION ANALYSIS")
    print("="*60)
    print(f"\nMARKET: {result.market_url}")
    print(f"TIMESTAMP: {result.timestamp_iso}")
    print(f"\nCALL: {result.call.value}")
    print(f"CONFIDENCE: {result.confidence.value}")
    print(f"PROBABILITY UP: {result.prob_up:.1%}")
    print(f"\nREASONS:")
    for i, reason in enumerate(result.reasons, 1):
        print(f"  {i}. {reason}")

    print(f"\nKEY SIGNALS:")
    for key, value in result.key_signals.items():
        print(f"  {key}: {value}")

    print(f"\nACTION INTENTS: {len(result.action_intents)}")
    for intent in result.action_intents:
        print(f"  - {intent.intent_id}: {intent.tool_name}")

    print("\n" + "="*60)

    return result


async def example_quick_call():
    """
    Example: Quick call for simple "up or down?" query
    """
    market_data = {
        "captured_at_iso": "2025-01-31T13:00:00Z",
        "market_url": "https://polymarket.com/event/btc-15m",
        "market_title": "Will BTC be above $105,000 at 1:15 PM EST?",
        "market_id": "btc-15m-example",
        "up_label": "Yes",
        "down_label": "No",
        "yes_means_up": True,
        "up_prob": 0.52,
        "down_prob": 0.48,
        "up_spread": 0.02,
        "down_spread": 0.025,
        "up_best_bid": 0.51,
        "up_best_ask": 0.53,
        "down_best_bid": 0.47,
        "down_best_ask": 0.495,
        "volume_24h_usd": 150000,
        "total_volume_usd": 500000,
        "open_interest_usd": 75000,
        "time_remaining_seconds": 600,
        "up_bids": [],
        "up_asks": [],
        "down_bids": [],
        "down_asks": [],
        "recent_trades": [],
    }

    # Get quick call
    call = await quick_call(market_data)
    print(f"\nQuick Call: {call}")

    return call


if __name__ == "__main__()
    # Run examples
    asyncio.run(example_full_analysis())
    asyncio.run(example_quick_call())
