from omega.ai_service import get_market_analyst
import json

def test_ai():
    print("Testing AI Service...")
    analyst = get_market_analyst()
    
    # Check attributes
    print(f"Has generate_market_summary: {hasattr(analyst, 'generate_market_summary')}")
    
    snapshot = {
        "symbol": "BTC/USD",
        "price": 90000,
        "vwap": 89500,
        "volume": 1000,
        "session": "TEST"
    }
    
    print("\nCalling Generate Summary...")
    res = analyst.generate_market_summary("BTC/USD", snapshot)
    print(json.dumps(res, indent=2))

if __name__ == "__main__":
    test_ai()
