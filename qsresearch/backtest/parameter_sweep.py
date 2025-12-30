"""
QS Research - Parameter Sweep Engine

Run iterative parameter sweeps to find optimal strategy configurations.
Based on the Quant Science production sweep methodology.
"""

from typing import Dict, List, Any, Optional
from datetime import date
from pathlib import Path
import itertools
import json

import pandas as pd
from loguru import logger

try:
    import mlflow
    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False

from config.settings import get_settings
from qsresearch.backtest.run_backtest import run_backtest


def run_iterative_sweep(
    sweep_config: Dict[str, Any],
    run_date: Optional[date] = None,
    experiment_name: str = "Momentum_Factor_Iterative_Sweep",
    max_combinations: int = 100,
    log_to_mlflow: bool = True,
) -> List[Dict[str, Any]]:
    """
    Run an iterative parameter sweep.
    
    This tests multiple combinations of strategy parameters to find
    the optimal configuration. Results are logged to MLflow.
    
    Args:
        sweep_config: Configuration for the sweep containing:
            - base_config: Base strategy configuration name
            - param_grid: Dict of parameter names to lists of values
            - rounds: Number of sweep rounds
        run_date: Date for the sweep
        experiment_name: MLflow experiment name
        max_combinations: Maximum number of combinations to test
        log_to_mlflow: Whether to log to MLflow
        
    Returns:
        List of result dictionaries for each combination
    """
    if run_date is None:
        run_date = date.today()
    
    settings = get_settings()
    
    logger.info(f"Starting iterative parameter sweep for {run_date}")
    
    # Get base configuration
    from qsresearch.strategies.factor.config import MOMENTUM_FACTOR_CONFIG
    base_config = MOMENTUM_FACTOR_CONFIG.copy()
    
    # Extract parameter grid
    param_grid = sweep_config.get("param_grid", {
        "fast_period": [21, 42, 63],
        "slow_period": [126, 252, 504],
        "top_n": [10, 20, 30],
    })
    
    # Generate combinations
    param_names = list(param_grid.keys())
    param_values = list(param_grid.values())
    combinations = list(itertools.product(*param_values))
    
    # Limit combinations
    if len(combinations) > max_combinations:
        logger.warning(f"Limiting from {len(combinations)} to {max_combinations} combinations")
        combinations = combinations[:max_combinations]
    
    logger.info(f"Testing {len(combinations)} parameter combinations")
    
    # Setup MLflow
    if log_to_mlflow and MLFLOW_AVAILABLE:
        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        mlflow.set_experiment(experiment_name)
    
    results = []
    
    for i, combo in enumerate(combinations):
        params = dict(zip(param_names, combo))
        
        # Build run name
        param_str = "_".join([f"{k[:3]}{v}" for k, v in params.items()])
        run_name = f"IterSweep/qsbacktest_{param_str}"
        
        logger.info(f"[{i+1}/{len(combinations)}] Testing: {params}")
        
        # Build config for this combination
        test_config = base_config.copy()
        test_config["run_name"] = run_name
        test_config["end_date"] = run_date.isoformat()
        
        # Apply parameter overrides
        if "fast_period" in params or "slow_period" in params:
            # Update momentum factor params
            for factor in test_config.get("factors", []):
                if factor.get("name") == "momentum_factor":
                    if "fast_period" in params:
                        factor["params"]["fast_period"] = params["fast_period"]
                    if "slow_period" in params:
                        factor["params"]["slow_period"] = params["slow_period"]
        
        if "top_n" in params:
            # Update algorithm params
            if "algorithm" in test_config:
                test_config["algorithm"]["params"]["top_n"] = params["top_n"]
        
        try:
            # Run backtest
            backtest_results = run_backtest(
                test_config,
                log_to_mlflow=log_to_mlflow,
            )
            
            metrics = backtest_results.get("metrics", {})
            
            result = {
                "params": params,
                "run_name": run_name,
                "total_return": metrics.get("portfolio_total_return", 0),
                "sharpe_ratio": metrics.get("portfolio_daily_sharpe", 0),
                "max_drawdown": metrics.get("portfolio_max_drawdown", 0),
                "calmar_ratio": metrics.get("portfolio_calmar", 0),
                "win_rate": metrics.get("portfolio_win_rate", 0),
                "success": True,
            }
            
            logger.info(f"  → Sharpe: {result['sharpe_ratio']:.4f}, Return: {result['total_return']:.2%}")
            
        except Exception as e:
            logger.error(f"  → Failed: {e}")
            result = {
                "params": params,
                "run_name": run_name,
                "success": False,
                "error": str(e),
            }
        
        results.append(result)
    
    # Save sweep results
    output_dir = settings.dashboard_data_dir / "sweeps"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = output_dir / f"sweep_{run_date.isoformat()}.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    # Find best result
    successful = [r for r in results if r.get("success", False)]
    if successful:
        best = max(successful, key=lambda x: x.get("sharpe_ratio", 0))
        logger.info(f"Best combination: {best['params']} with Sharpe {best['sharpe_ratio']:.4f}")
    
    logger.info(f"Sweep complete. Results saved to {output_path}")
    
    return results


def generate_sweep_report(results: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Generate a summary report from sweep results.
    
    Args:
        results: List of sweep result dictionaries
        
    Returns:
        DataFrame with sweep summary
    """
    rows = []
    
    for r in results:
        if r.get("success", False):
            row = {
                "run_name": r.get("run_name", ""),
                **r.get("params", {}),
                "total_return": r.get("total_return", 0),
                "sharpe_ratio": r.get("sharpe_ratio", 0),
                "max_drawdown": r.get("max_drawdown", 0),
                "calmar_ratio": r.get("calmar_ratio", 0),
            }
            rows.append(row)
    
    df = pd.DataFrame(rows)
    
    # Sort by Sharpe ratio
    df = df.sort_values("sharpe_ratio", ascending=False)
    
    return df
