import time
import sys
import random
from datetime import datetime
from loguru import logger
from omega.trading_app import TradingApp
from omega.data.candle_engine import Tick

def run_simulation(app):
    """Generates synthetic ticks for offline verification."""
    logger.warning("⚠️  STARTING SIMULATION MODE ⚠️")
    logger.info("Generating synthetic ticks for AMZN to verify Truth Layer...")
    
    symbol = "AMZN"
    price = 185.50
    
    # Manually initialize aggregator if not already done via subscribe
    # Simulation bypasses IBKR subscription, so we init manually
    if symbol not in app.aggregators:
        from omega.data.candle_engine import CandleAggregator
        app.aggregators[symbol] = CandleAggregator(
            symbol=symbol,
            interval_sec=60, # 1 min bars
            event_bus=app.event_bus,
            db_mgr=app._db_manager
        )
    
    agg = app.aggregators[symbol]
    
    try:
        while True:
            # Random Walk
            price += random.choice([-0.05, -0.01, 0.00, 0.01, 0.05])
            size = random.randint(1, 500)
            
            # Create Truth Tick
            tick = Tick(
                symbol=symbol,
                price=price,
                size=float(size),
                exchange_ts=datetime.now().timestamp(),
                recv_ts=datetime.now().timestamp()
            )
            
            # Feed Engine
            agg.process_tick(tick)
            
            # logger.info(f"SIM TICK: {price:.2f}")
            time.sleep(0.5) # 2 ticks per second
            
    except KeyboardInterrupt:
        logger.info("Simulation Stopped.")

def main():
    logger.info("Starting Omega Trading Node...")
    
    # Initialize App
    app = TradingApp()
    
    # Connect to IBKR
    connected = False
    try:
        if app.connect():
            connected = True
        else:
            logger.error("Failed to connect to IB Gateway/TWS!")
    except Exception as e:
        logger.error(f"Connection Error: {e}")

    if not connected:
        logger.info("Running in OFFLINE SIMULATION mode to verify Dashboard integration.")
        run_simulation(app)
        return

    # Subscribe to Truth Layer (Live Mode)
    symbol = "AMZN"
    logger.info(f"Subscribing to Truth Layer for {symbol}...")
    app.subscribe_truth_layer(symbol)
    
    logger.success(f"Trading Node Active. Feeding {symbol} candles to Dashboard.")
    
    # Keep alive
    try:
        while True:
            time.sleep(1)
            # Optional: Print heartbeat or stats
            if app.metrics["last_tick_time"]:
                pass
    except KeyboardInterrupt:
        logger.info("Stopping Trading Node...")
        app.cancel_all_orders()

if __name__ == "__main__":
    main()
