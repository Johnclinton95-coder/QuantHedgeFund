"""
QS Research - Backtest Runner

Main backtesting execution engine with MLflow integration.
"""

from typing import Dict, Any, Optional, Callable
from pathlib import Path
from datetime import datetime
import pickle

import pandas as pd
from loguru import logger

try:
    import mlflow
    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False
    logger.warning("MLflow not installed. Experiment tracking disabled.")

from config.settings import get_settings
from qsresearch.portfolio_analysis.performance_metrics import calculate_all_metrics


def run_backtest(
    config: Dict[str, Any],
    output_dir: Optional[Path] = None,
    log_to_mlflow: bool = True,
) -> Dict[str, Any]:
    """
    Run a backtest with the given configuration.
    
    This is the main entry point for running backtests. It:
    1. Loads and preprocesses data
    2. Calculates factors/features
    3. Runs the backtesting engine
    4. Calculates performance metrics
    5. Logs results to MLflow
    
    Args:
        config: Backtest configuration dictionary containing:
            - bundle_name: Zipline bundle name
            - start_date: Backtest start date
            - end_date: Backtest end date
            - capital_base: Starting capital
            - preprocessing: List of preprocessing steps
            - algorithm: Algorithm function and params
            - portfolio_strategy: Portfolio construction config
        output_dir: Directory to save results
        log_to_mlflow: Whether to log to MLflow
        
    Returns:
        Dictionary with backtest results and metrics
    """
    settings = get_settings()
    
    if output_dir is None:
        output_dir = settings.dashboard_data_dir / "backtests"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("Starting backtest run")
    logger.info(f"Config: {config.get('experiment_name', 'unnamed')}")
    
    # Extract config values
    bundle_name = config.get("bundle_name", "historical_prices_fmp")
    start_date = config.get("start_date", "2015-01-01")
    end_date = config.get("end_date", datetime.now().strftime("%Y-%m-%d"))
    capital_base = config.get("capital_base", 1_000_000)
    
    # MLflow setup
    if log_to_mlflow and MLFLOW_AVAILABLE:
        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        
        experiment_name = config.get("experiment_name", settings.mlflow_experiment_name)
        mlflow.set_experiment(experiment_name)
        
        run_name = config.get("run_name", f"backtest_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}")
        mlflow.start_run(run_name=run_name)
        
        # Log parameters
        _log_params_to_mlflow(config)
    
    try:
        # Step 1: Load data
        logger.info("Loading price data...")
        price_data = _load_price_data(bundle_name, start_date, end_date)
        
        # Step 2: Apply preprocessing
        logger.info("Applying preprocessing steps...")
        processed_data = _apply_preprocessing(price_data, config.get("preprocessing", []))
        
        # Step 3: Calculate factors
        logger.info("Calculating factors...")
        factor_data = _apply_factors(processed_data, config.get("factors", []))
        
        # Step 4: Run algorithm
        logger.info("Running backtest algorithm...")
        algorithm_config = config.get("algorithm", {})
        performance = _run_algorithm(
            factor_data,
            algorithm_config,
            start_date,
            end_date,
            capital_base,
        )
        
        # Step 5: Calculate metrics
        logger.info("Calculating performance metrics...")
        metrics = calculate_all_metrics(performance)
        
        # Step 6: Save results
        results = {
            "performance": performance,
            "metrics": metrics,
            "config": config,
            "run_date": datetime.now().isoformat(),
        }
        
        # Save pickle file
        output_path = output_dir / f"performance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"
        with open(output_path, "wb") as f:
            pickle.dump(results, f)
        logger.info(f"Results saved to {output_path}")
        
        # Log to MLflow
        if log_to_mlflow and MLFLOW_AVAILABLE:
            # Log metrics
            for name, value in metrics.items():
                if isinstance(value, (int, float)):
                    mlflow.log_metric(name, value)
            
            # Log artifacts
            mlflow.log_artifact(str(output_path))
        
        logger.info("Backtest completed successfully")
        return results
        
    except Exception as e:
        logger.error(f"Backtest failed: {e}")
        raise
    
    finally:
        if log_to_mlflow and MLFLOW_AVAILABLE:
            mlflow.end_run()


def _load_price_data(
    bundle_name: str,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """Load price data from bundle or database."""
    from qsconnect import Client
    
    client = Client()
    db_manager = client._db_manager
    
    prices = db_manager.get_prices(
        start_date=start_date,
        end_date=end_date,
    )
    
    return prices.to_pandas()


def _apply_preprocessing(
    df: pd.DataFrame,
    preprocessing_config: list,
) -> pd.DataFrame:
    """Apply preprocessing steps from config."""
    from qsresearch.preprocessors import preprocess_price_data, universe_screener
    
    PREPROCESSING_FUNCS = {
        "price_preprocessor": preprocess_price_data,
        "universe_screener": universe_screener,
    }
    
    for step in preprocessing_config:
        func_name = step.get("func")
        params = step.get("params", {})
        
        if func_name in PREPROCESSING_FUNCS:
            func = PREPROCESSING_FUNCS[func_name]
            df = func(df, **params)
            logger.info(f"Applied preprocessing: {func_name}")
    
    return df


def _apply_factors(
    df: pd.DataFrame,
    factors_config: list,
) -> pd.DataFrame:
    """Apply factor calculations from config."""
    from qsresearch.features import FactorEngine
    
    engine = FactorEngine()
    
    for factor_spec in factors_config:
        name = factor_spec.get("name")
        params = factor_spec.get("params", {})
        
        if name:
            df = engine.calculate_factor(df, name, **params)
    
    return df


def _run_algorithm(
    df: pd.DataFrame,
    algorithm_config: Dict[str, Any],
    start_date: str,
    end_date: str,
    capital_base: float,
) -> pd.DataFrame:
    """
    Run the trading algorithm.
    
    This is a simplified version. For production, integrate with Zipline Reloaded.
    """
    from qsresearch.strategies.factor.algorithms import use_factor_as_signal
    
    algorithm_func = algorithm_config.get("callable", "use_factor_as_signal")
    params = algorithm_config.get("params", {})
    
    # Generate signals
    signals = use_factor_as_signal(df, **params)
    
    # Simulate portfolio performance
    performance = _simulate_portfolio(signals, df, capital_base, start_date, end_date)
    
    return performance


def _simulate_portfolio(
    signals: pd.DataFrame,
    prices: pd.DataFrame,
    capital_base: float,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """Simple portfolio simulation based on signals."""
    # This is a simplified simulation
    # For production, use Zipline Reloaded
    
    dates = pd.date_range(start=start_date, end=end_date, freq="B")
    
    portfolio_value = [capital_base]
    returns_list = []
    
    for i in range(1, len(dates)):
        # Simplified: assume 10% of signal translates to return
        daily_return = 0.0005  # Placeholder
        new_value = portfolio_value[-1] * (1 + daily_return)
        portfolio_value.append(new_value)
        returns_list.append(daily_return)
    
    performance = pd.DataFrame({
        "date": dates[:len(portfolio_value)],
        "portfolio_value": portfolio_value,
        "returns": [0] + returns_list,
    })
    
    return performance


def _log_params_to_mlflow(config: Dict[str, Any]) -> None:
    """Log configuration parameters to MLflow."""
    def flatten_dict(d: Dict, parent_key: str = "") -> Dict[str, Any]:
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}.{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(flatten_dict(v, new_key).items())
            else:
                items.append((new_key, str(v)[:250]))  # MLflow param limit
        return dict(items)
    
    flat_config = flatten_dict(config)
    
    for key, value in flat_config.items():
        try:
            mlflow.log_param(key, value)
        except Exception as e:
            logger.warning(f"Failed to log param {key}: {e}")
