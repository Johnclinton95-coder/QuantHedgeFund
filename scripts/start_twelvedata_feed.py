"""
Twelve Data Real-Time Feed
Uses WebSocket to stream real-time price quotes and feed them to the dashboard.
API Key provided by user.
"""
import websocket
import json
import time
import sys
import os
from pathlib import Path
from datetime import datetime

# Add project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from qsconnect.database.duckdb_manager import DuckDBManager
from omega.data.candle_engine import CandleAggregator, Tick, SessionManager

from config.registry import get_registry

from config.registry import get_registry

# API Configuration
API_KEY = os.environ.get("TWELVE_DATA_API_KEY")
if not API_KEY:
    # Fallback to hardcoded for this session if env not loaded yet, 
    # but prefer env in production
    API_KEY = "2b20a28a0c5040f082c35cb6f95a75c2"

REGISTRY = get_registry()
SYMBOLS = [s for s, cfg in REGISTRY.assets.items() if cfg.get("realtime_feed") == "TWELVE_DATA"]

# Force override session check to allow 24/7 processing (Crypto/Forex/Testing)
class PermissiveSession(SessionManager):
    def is_in_session(self, ts, symbol): return True

# Globals
db_path = Path(__file__).parent.parent / "data" / "quant.duckdb"
DB_MGR = DuckDBManager(db_path, read_only=False, auto_close=True)
AGGREGATORS = {}

def on_message(ws, message):
    try:
        data = json.loads(message)
        event = data.get("event")
        
        # Twelve Data 'price' event (Quote)
        if event == "price":
            symbol = data.get("symbol")
            if symbol not in AGGREGATORS:
                return

            price = float(data.get("price", 0))
            raw_ts = data.get("timestamp")
            
            # Robust timestamp handling
            if isinstance(raw_ts, (int, float)):
                exchange_ts = raw_ts
            else:
                exchange_ts = time.time()
                
            tick = Tick(
                symbol=symbol,
                price=price,
                size=0, # Quote-only feed
                exchange_ts=exchange_ts,
                recv_ts=time.time(),
                source="TWELVE_DATA",
                asset_class=REGISTRY.get_asset_class(symbol)
            )
            
            # Process Tick
            AGGREGATORS[symbol].process_tick(tick)
            print(f"Update {symbol}: {price:.2f}")

        elif event == "subscribe-status":
            print(f"📡 Subscription Status: {data.get('status')} for {data.get('success', [])}")
            
        elif event == "heartbeat":
            print(".", end="", flush=True)
            
        elif data.get("status") == "error":
            print(f"\n❌ API Error: {data.get('message')}")
            
    except Exception as e:
        print(f"\nError processing message: {e}")

def on_error(ws, error):
    print(f"\nWS Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("\nWS Connection Closed")

def on_open(ws):
    print("✅ Connected to Twelve Data. Subscribing...")
    
    # Subscribe to price quotes (no interval = ticks/quotes)
    payload = {
        "action": "subscribe",
        "params": {
            "symbols": ",".join(SYMBOLS)
        }
    }
    ws.send(json.dumps(payload))

def main():
    print("🚀 Starting Twelve Data Real-Time Feed...")
    print(f"   Symbols: {SYMBOLS}")
    
    # Initialize Aggregators
    for sym in SYMBOLS:
        AGGREGATORS[sym] = CandleAggregator(
            symbol=sym, 
            session_mgr=PermissiveSession(),
            db_mgr=DB_MGR,
            source="TWELVE_DATA",
            asset_class=REGISTRY.get_asset_class(sym)
        )
    
    # Run WebSocket with reconnection logic
    ws_url = f"wss://ws.twelvedata.com/v1/quotes/price?apikey={API_KEY}"
    
    while True:
        print(f"Connecting to Twelve Data...")
        ws = websocket.WebSocketApp(
            ws_url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        
        try:
            ws.run_forever()
        except KeyboardInterrupt:
            print("\n🛑 Stopped by user.")
            break
        except Exception as e:
            print(f"\n⚠️ WS Crash: {e}")
            
        print("Waiting 5s before reconnecting...")
        time.sleep(5)

if __name__ == "__main__":
    main()
