"""
Strategy Generator & Regime Analyzer
Calculates market signals and prompts the LLM for strategy adjustments.
"""

from typing import Dict, Any, List
import pandas as pd
import numpy as np
import polars as pl
import json
from loguru import logger

from qsresearch.llm.client import GroqClient

class StrategyGenerator:
    """Regime-aware strategy generator using LLM."""
    
    def __init__(self):
        self.llm_client = GroqClient()
    
    def analyze_market_regime(self, prices: pl.DataFrame) -> Dict[str, Any]:
        """
        Calculate simple market regime metrics from price history.
        
        Args:
            prices: Polars DataFrame with symbol, date, close
            
        Returns:
            Dictionary of regime metrics (volatility, trend, etc.)
        """
        # Convert to pandas for easier time-series calc (or use polars)
        # For simplicity, let's analyze SPY or the aggregate market
        
        # 1. Calculate Market Index (Equal Weight of all provided symbols for proxy)
        # Ideally we'd use SPY, but let's assume 'prices' has many stocks
        
        # Filter to last 6 months (approx 126 trading days)
        df = prices.to_pandas()
        df['date'] = pd.to_datetime(df['date'])
        
        # Simple Proxy: Average daily return of all stocks
        daily_returns = df.pivot(index='date', columns='symbol', values='close').pct_change().mean(axis=1)
        
        # Metrics
        recent_returns = daily_returns.tail(126) # 6 months
        
        volatility = recent_returns.std() * np.sqrt(252)
        total_return = (1 + recent_returns).prod() - 1
        
        # Trend: Simple SMA comparison (last price vs 200 SMA of index)
        # Create a synthetic index price series
        index_price = (1 + daily_returns).cumprod()
        current_price = index_price.iloc[-1]
        sma_200 = index_price.tail(200).mean() if len(index_price) >= 200 else index_price.mean()
        
        trend_strength = (current_price / sma_200) - 1
        
        # Regime Classification
        if total_return > 0.05 and volatility < 0.15:
            regime = "Bull Steady"
        elif total_return > 0.05 and volatility >= 0.15:
            regime = "Bull Volatile"
        elif total_return < -0.05:
            regime = "Bear"
        else:
            regime = "Sideways"
            
        metrics = {
            "regime_label": regime,
            "annualized_volatility": round(float(volatility), 4),
            "6m_return": round(float(total_return), 4),
            "trend_strength_vs_sma200": round(float(trend_strength), 4),
            "data_points": len(recent_returns)
        }
        
        logger.info(f"Market Regime Analysis: {metrics}")
        return metrics

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and sanitize strategy configuration.
        
        Rules:
        - top_n: 5 to 50
        - factor_weights: Sum to 1.0 (approx)
        - momentum_window: 5 to 504
        """
        try:
            # 1. Validate top_n
            top_n = config.get("top_n", 20)
            if not isinstance(top_n, int):
                top_n = 20
            config["top_n"] = max(5, min(50, top_n))
            
            # 2. Validate weights
            weights = config.get("factor_weights", {})
            if not weights:
                weights = {"momentum": 1.0, "value": 0.0, "quality": 0.0}
            
            # Normalize weights to sum to 1.0
            total_weight = sum(weights.values())
            if total_weight <= 0:
                 weights = {"momentum": 1.0, "value": 0.0, "quality": 0.0}
            elif abs(total_weight - 1.0) > 0.01:
                # Renormalize
                weights = {k: round(v / total_weight, 2) for k, v in weights.items()}
                # Fix rounding error on last item
                diff = 1.0 - sum(weights.values())
                if diff != 0:
                     last_key = list(weights.keys())[-1]
                     weights[last_key] += diff
            config["factor_weights"] = weights
            
            # 3. Validate momentum window
            window = config.get("momentum_window", [21, 252])
            if isinstance(window, list) and len(window) == 2:
                config["momentum_window"] = [
                    max(5, min(504, w)) for w in window
                ]
                # Ensure fast < slow
                if config["momentum_window"][0] >= config["momentum_window"][1]:
                    config["momentum_window"].sort()
            else:
                 config["momentum_window"] = [21, 252]
                 
            return config
            
        except Exception as e:
            logger.error(f"Config validation failed: {e}. Using default.")
            return self._get_default_config()

    def generate_candidates(self, prices: pl.DataFrame, n: int = 3) -> List[Dict[str, Any]]:
        """
        Generate N distinct strategy candidates for the current regime.
        Logs to MLflow if available.
        """
        if not self.llm_client.client:
            logger.warning("LLM Client not available.")
            return [self._get_default_config()] * n
            
        regime = self.analyze_market_regime(prices)
        candidates = []
        
        # MLflow Logging Setup
        try:
            import mlflow
            mlflow_active = True
            mlflow.set_experiment("LLM_Strategy_Generator")
        except ImportError:
            mlflow_active = False
            logger.warning("MLflow not found. Skipping experiment tracking.")

        for i in range(n):
            try:
                # Add diversity instruction
                diversity_prompt = ""
                if i == 0:
                    diversity_prompt = "Propose a 'Balanced' approach."
                elif i == 1:
                    diversity_prompt = "Propose an 'Aggressive' approach (higher risk/return)."
                else:
                    diversity_prompt = "Propose a 'Defensive' approach (lower volatility)."

                logger.info(f"Generating candidate {i+1}/{n}: {diversity_prompt}")
                
                # We reuse the client but inject the diversity nuance
                # NOTE: For a real impl, we'd update the client method or prompt construction
                # Here we just append it to a custom regime dict strictly for prompting context
                regime_context = regime.copy()
                regime_context["requested_style"] = diversity_prompt
                
                llm_response = self.llm_client.generate_strategy_params(regime_context)
                raw_config = llm_response.get("config", self._get_default_config())
                reasoning = llm_response.get("reasoning", "No reasoning provided")
                
                # VALIDATE
                valid_config = self.validate_config(raw_config)
                valid_config["candidate_id"] = f"candidate_{i+1}"
                valid_config["style"] = diversity_prompt
                valid_config["reasoning"] = reasoning
                
                candidates.append(valid_config)
                
                # MLflow Log
                if mlflow_active:
                    with mlflow.start_run(run_name=f"Generate_{regime['regime_label']}_{i}"):
                        mlflow.log_params(regime)
                        mlflow.log_param("style", diversity_prompt)
                        mlflow.log_text(reasoning, "reasoning.txt")
                        mlflow.log_dict(valid_config, "config.json")
                        
            except Exception as e:
                logger.error(f"Candidate generation {i} failed: {e}")
                candidates.append(self._get_default_config())

        return candidates

    def generate_strategy(self, prices: pl.DataFrame) -> Dict[str, Any]:
        """Original single-strategy method (backward compatibility)"""
        candidates = self.generate_candidates(prices, n=1)
        return candidates[0] if candidates else self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Safe fallback strategy configuration."""
        return {
            "top_n": 20,
            "momentum_window": [21, 252],
            "rebalance_frequency": "month_end",
            "factor_weights": {"momentum": 1.0, "value": 0.0, "quality": 0.0}
        }

if __name__ == "__main__":
    # Test Run
    import sys
    from pathlib import Path
    
    # Add parent to path to allow imports
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    
    from qsconnect import Client
    
    # Create the generator
    generator = StrategyGenerator()
    
    print("Fetching sample data...")
    from dotenv import load_dotenv
    load_dotenv() # Explicitly load .env
    
    # Check if GROQ_API_KEY is loaded
    import os
    if not os.getenv("GROQ_API_KEY"):
         print("WARNING: GROQ_API_KEY not found in env even after load_dotenv()")
         
    try:
        from qsconnect import Client
        try:
            client = Client()
            # Fetch a small sample or rely on cache
            prices = client.bulk_historical_prices(
                start_date=pd.to_datetime("2023-01-01").date(), 
                use_cache=True
            )
        except Exception as client_err:
             print(f"Client/Data Error: {client_err}")
             prices = None

        # MOCK DATA IF NONE FOUND (For testing without API key)
        if prices is None or prices.is_empty():
            print("No real data found/accessible. Using MOCK data for verification.")
            dates = pd.date_range(start="2024-01-01", periods=150, freq="B")
            mock_data = {
                "symbol": ["MOCK"] * 150,
                "date": dates,
                "close": np.linspace(100, 120, 150) + np.random.normal(0, 2, 150),
                "volume": np.random.randint(1000, 5000, 150)
            }
            prices = pl.DataFrame(mock_data)
        
        print(f"Data ready: {len(prices)} rows")
        
        # Re-init generator to pick up env vars if they were just loaded
        generator = StrategyGenerator()
        config = generator.generate_strategy(prices)
        
        print("\nGenerated Strategy Config:")
        print(json.dumps(config, indent=2))
            
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
