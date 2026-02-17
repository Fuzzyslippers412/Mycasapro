#!/usr/bin/env python3
"""
Test script for agent chat with LLM integration.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from agents.security_manager import SecurityManagerAgent
from agents.finance import FinanceAgent
from agents.maintenance import MaintenanceAgent


async def test_agent_chat():
    """Test that agents respond intelligently via LLM"""

    print("🧪 Testing Agent Chat with LLM Integration\n")
    print("=" * 60)

    # Test Security Manager
    print("\n1️⃣ Testing Security Manager Agent...")
    security = SecurityManagerAgent()
    try:
        response = await security.chat("What are the top 3 security threats I should be monitoring for my home network?")
        print(f"✓ Response length: {len(response)} chars")
        print(f"Response preview: {response[:200]}...")

        if "LLM unavailable" in response or "LLM not configured" in response:
            print("⚠️  LLM not available - need to set ANTHROPIC_API_KEY")
        elif len(response) > 100 and "received your message" not in response.lower():
            print("✓ Agent responded intelligently!")
        else:
            print("⚠️  Response seems like fallback")
    except Exception as e:
        print(f"✗ Error: {e}")

    # Test Finance Agent
    print("\n2️⃣ Testing Finance Agent...")
    finance = FinanceAgent()
    try:
        response = await finance.chat("What's your investment philosophy and how would you analyze a stock?")
        print(f"✓ Response length: {len(response)} chars")
        print(f"Response preview: {response[:200]}...")

        if "LLM unavailable" in response or "LLM not configured" in response:
            print("⚠️  LLM not available - need to set ANTHROPIC_API_KEY")
        elif len(response) > 100:
            print("✓ Agent responded intelligently!")
    except Exception as e:
        print(f"✗ Error: {e}")

    # Test Maintenance Agent
    print("\n3️⃣ Testing Maintenance Agent...")
    maintenance = MaintenanceAgent()
    try:
        response = await maintenance.chat("What's your approach to preventive maintenance?")
        print(f"✓ Response length: {len(response)} chars")
        print(f"Response preview: {response[:200]}...")

        if "LLM unavailable" in response or "LLM not configured" in response:
            print("⚠️  LLM not available - need to set ANTHROPIC_API_KEY")
        elif len(response) > 100:
            print("✓ Agent responded intelligently!")
    except Exception as e:
        print(f"✗ Error: {e}")

    print("\n" + "=" * 60)
    print("\n📋 Summary:")
    print("If you see 'LLM not configured' messages:")
    print("  1. Set your API key in ~/clawd/apps/mycasa-pro/.env")
    print("  2. Format: ANTHROPIC_API_KEY=sk-ant-...")
    print("  3. Install: pip install anthropic python-dotenv")
    print("\nIf agents respond intelligently: ✓ Fix successful!")


if __name__ == "__main__":
    asyncio.run(test_agent_chat())
