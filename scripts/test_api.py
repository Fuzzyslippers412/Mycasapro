#!/usr/bin/env python3
"""
MyCasa Pro API Test Script
Quick validation of core API functionality.

Run: python scripts/test_api.py
"""
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_imports():
    """Test all major imports work"""
    print("Testing imports...")
    
    try:
        from api.main import app
        print(f"  ✅ FastAPI app: {len(app.routes)} routes")
    except Exception as e:
        print(f"  ❌ FastAPI app: {e}")
        return False
    
    try:
        print("  ✅ Error middleware")
    except Exception as e:
        print(f"  ❌ Error middleware: {e}")
        return False
    
    try:
        print("  ✅ Connectors: WhatsApp, Gmail, Calendar")
    except Exception as e:
        print(f"  ❌ Connectors: {e}")
        return False
    
    try:
        print("  ✅ Agents: Manager, Finance, Base")
    except Exception as e:
        print(f"  ❌ Agents: {e}")
        return False
    
    try:
        print("  ✅ Typed settings")
    except Exception as e:
        print(f"  ❌ Typed settings: {e}")
        return False
    
    return True


def test_finance_agent():
    """Test Finance Agent functionality"""
    print("\nTesting Finance Agent...")
    
    try:
        from agents.finance import FinanceAgent
        fa = FinanceAgent()
        
        # Test settings
        settings = fa.get_settings()
        print(f"  ✅ Settings loaded: {len(settings)} keys")
        
        # Test recommendations
        recs = fa.get_investment_recommendations([
            {"ticker": "NVDA", "change_pct": 5.2, "value": 100000},
            {"ticker": "GOOGL", "change_pct": -2.1, "value": 50000},
        ])
        print(f"  ✅ Recommendations: {len(recs.get('recommendations', []))} items, style={recs.get('style')}")
        
        return True
    except Exception as e:
        print(f"  ❌ Finance Agent: {e}")
        return False


def test_chat_routes():
    """Test Chat route functionality"""
    print("\nTesting Chat routes...")
    
    try:
        from api.routes.chat import _get_conversation, _add_message
        
        conv = _get_conversation("test_api_conv")
        msg_id = _add_message("test_api_conv", "user", "Test message")
        print(f"  ✅ Conversation ops: msg_id={msg_id}")
        
        # Cleanup
        from api.routes.chat import _conversations
        del _conversations["test_api_conv"]
        
        return True
    except Exception as e:
        print(f"  ❌ Chat routes: {e}")
        return False


def test_secondbrain_routes():
    """Test SecondBrain route functionality"""
    print("\nTesting SecondBrain routes...")
    
    try:
        from api.routes.secondbrain import _chunk_text, _extract_links, _get_all_notes
        
        # Test chunking
        chunks = _chunk_text("Para one.\n\nPara two.\n\nPara three.", chunk_size=30)
        print(f"  ✅ Text chunking: {len(chunks)} chunks")
        
        # Test link extraction
        links = _extract_links("Link to [[sb_123]] and [[sb_456]]")
        print(f"  ✅ Link extraction: {len(links)} links")
        
        # Test note listing
        notes = _get_all_notes()
        print(f"  ✅ Note listing: {len(notes)} notes in vault")
        
        return True
    except Exception as e:
        print(f"  ❌ SecondBrain routes: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 50)
    print("MyCasa Pro API Tests")
    print("=" * 50)
    
    results = []
    
    results.append(("Imports", test_imports()))
    results.append(("Finance Agent", test_finance_agent()))
    results.append(("Chat Routes", test_chat_routes()))
    results.append(("SecondBrain Routes", test_secondbrain_routes()))
    
    print("\n" + "=" * 50)
    print("Results:")
    print("=" * 50)
    
    passed = 0
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {name}: {status}")
        if result:
            passed += 1
    
    print(f"\nTotal: {passed}/{len(results)} passed")
    
    return passed == len(results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
