"""
Research Flow
Orchestrates the 'Generate -> Validate -> Backtest' research loop.
"""

import sys
from pathlib import Path
import json
import logging
from loguru import logger

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from qsresearch.llm.strategy_generator import StrategyGenerator
from qsconnect import Client
import polars as pl
import pandas as pd
import numpy as np
from dotenv import load_dotenv

def main():
    # Load Environment
    load_dotenv()
    
    logger.info("Starting Research Flow...")
    
    # 1. Get Data
    print("\n--- 1. Fetching Market Data ---")
    try:
        from qsconnect import Client
        try:
            client = Client()
            prices = client.bulk_historical_prices(
                start_date=pd.to_datetime("2023-01-01").date(), 
                use_cache=True
            )
        except Exception as client_err:
             logger.warning(f"Client/Data Error: {client_err}")
             prices = None

        # Mock Data Fallback
        if prices is None or prices.is_empty():
            logger.warning("Using MOCK data for research flow.")
            dates = pd.date_range(start="2024-01-01", periods=150, freq="B")
            mock_data = {
                "symbol": ["MOCK"] * 150,
                "date": dates,
                "close": np.linspace(100, 120, 150) + np.random.normal(0, 2, 150),
                "volume": np.random.randint(1000, 5000, 150)
            }
            prices = pl.DataFrame(mock_data)
            
        logger.info(f"Data Loaded: {len(prices)} rows")
        
    except Exception as e:
        logger.error(f"Data Fetch Failed: {e}")
        return

    # 2. Generate Candidates
    print("\n--- 2. Generating Candidates with AI ---")
    generator = StrategyGenerator()
    candidates = generator.generate_candidates(prices, n=3)
    
    print(f"\nGenerated {len(candidates)} candidates.")
    
    # 3. Simulate Backtests
    print("\n--- 3. Running Backtests (Simulated) ---")
    results = []
    
    for i, candidate in enumerate(candidates):
        print(f"\nProcessing Candidate {i+1} ({candidate.get('style', 'Unknown')}):")
        print(json.dumps(candidate, indent=2))
        
        # Here we would call: run_backtest(candidate)
        # For this script, we simulate a Sharpe Ratio
        
        # Mock Result
        simulated_sharpe = 1.5 + (np.random.random() - 0.5) # Random sharpe ~1.5
        if "Defensive" in candidate.get("style", ""):
            simulated_sharpe += 0.2 # Give defensive a boost for fun
            
        print(f"-> Backtest Complete. Sharpe: {simulated_sharpe:.2f}")
        
        results.append({
            "candidate": candidate,
            "sharpe": simulated_sharpe
        })

    # 4. Rank and Select
    print("\n--- 4. Selection ---")
    results.sort(key=lambda x: x["sharpe"], reverse=True)
    best = results[0]
    
    print(f"🏆 Best Strategy: {best['candidate']['style']}")
    print(f"   Sharpe: {best['sharpe']:.2f}")
    print(f"   Config: {best['candidate']}")

if __name__ == "__main__":
    main()
