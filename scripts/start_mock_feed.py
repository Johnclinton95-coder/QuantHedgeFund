"""
Start Mock Live Feed
Feeds simulated ticks to the real-time database for testing the dashboard.
Use this if you don't have active Interactive Brokers market data subscriptions.
"""
import sys
import os
import time
import random
from pathlib import Path
from datetime import datetime

# Add project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from qsconnect.database.duckdb_manager import DuckDBManager
from omega.data.candle_engine import CandleAggregator, Tick, SessionManager
from config.registry import get_registry

# Force override session check to allow 24/7 testing
class MockSession(SessionManager):
    def is_in_session(self, ts, symbol): return True

def main():
    print("🚀 Starting MOCK Data Feed (Simulated Exchange)...")
    print("   Target DB: data/quant.duckdb")
    
    # Connect to PROD database (same as Dashboard)
    db_mgr = DuckDBManager(db_path="data/quant.duckdb", auto_close=True)
    
    registry = get_registry()
    # Mock ALL Equities found in registry
    symbols = [s for s, cfg in registry.assets.items() if cfg.get("asset_class") == "EQUITY"]
    aggs = {}
    
    # Initialize aggregators
    for sym in symbols:
        # Create table if not exists (handled by candle engine logic or first insert)
        aggs[sym] = CandleAggregator(
            symbol=sym, 
            session_mgr=MockSession(),
            db_mgr=db_mgr,
            source="MOCK_IBKR",
            asset_class=registry.get_asset_class(sym)
        )
        print(f"   Initialized {sym} aggregator")
        
    # Initial prices (Randomized around a base for simulation)
    prices = {s: random.uniform(50.0, 500.0) for s in symbols}
    
    print("\n✅ Simulation Running. Press Ctrl+C to stop.\n")
    
    try:
        while True:
            # Re-enable persistent connection for the batch
            db_mgr.auto_close = False 
            
            for sym in symbols:
                # Random walk simulation
                prices[sym] += (random.random() - 0.5) * 0.5 # +/- $0.25 move
                
                now = time.time()
                tick = Tick(
                    symbol=sym,
                    price=round(prices[sym], 2),
                    size=random.randint(10, 500),
                    exchange_ts=now,
                    recv_ts=now,
                    source="MOCK_IBKR",
                    asset_class=registry.get_asset_class(sym)
                )
                aggs[sym].process_tick(tick)
            
            # Release lock after batch
            db_mgr.close()
            
            # Show heartbeat
            print(".", end="", flush=True)
            time.sleep(2.0) # Lower frequency to reduce collision surface area
            
    except KeyboardInterrupt:
        print("\n🛑 Stopped Mock Feed.")
    finally:
        db_mgr.close()

if __name__ == "__main__":
    main()
