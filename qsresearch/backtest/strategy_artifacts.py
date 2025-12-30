"""
QS Research - Strategy Manifest Generator

Creates strategy manifest JSON files for MLflow artifact storage.
Based on the Quant Science production artifact structure.
"""

from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime
import json

import pandas as pd
from loguru import logger


def generate_strategy_manifest(
    config: Dict[str, Any],
    performance: pd.DataFrame,
    metrics: Dict[str, float],
    output_dir: Path,
) -> Path:
    """
    Generate a strategy manifest JSON file.
    
    The manifest contains all configuration and metadata needed
    to reproduce and deploy the strategy.
    
    Args:
        config: Strategy configuration dictionary
        performance: Performance DataFrame
        metrics: Performance metrics dictionary
        output_dir: Directory to save manifest
        
    Returns:
        Path to the saved manifest file
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Build manifest
    manifest = {
        "generated_at": datetime.now().isoformat(),
        "version": "1.0",
        
        # Strategy configuration
        "strategy": {
            "name": config.get("experiment_name", "Unknown"),
            "run_name": config.get("run_name", ""),
            "bundle_name": config.get("bundle_name", ""),
            "start_date": config.get("start_date", ""),
            "end_date": config.get("end_date", ""),
            "capital_base": config.get("capital_base", 1_000_000),
        },
        
        # Preprocessing steps
        "preprocessing": config.get("preprocessing", []),
        
        # Factor configuration
        "factors": config.get("factors", []),
        
        # Algorithm configuration
        "algorithm": config.get("algorithm", {}),
        
        # Portfolio construction
        "portfolio_strategy": config.get("portfolio_strategy", {}),
        
        # Risk settings
        "risk": {
            "stop_loss_enabled": config.get("stop_loss_enabled", False),
            "stop_loss_pct": config.get("stop_loss_pct", 0.15),
        },
        
        # Key metrics summary
        "metrics_summary": {
            "total_return": metrics.get("portfolio_total_return", 0),
            "cagr": metrics.get("portfolio_cagr", 0),
            "sharpe_ratio": metrics.get("portfolio_daily_sharpe", 0),
            "sortino_ratio": metrics.get("portfolio_daily_sortino", 0),
            "max_drawdown": metrics.get("portfolio_max_drawdown", 0),
            "calmar_ratio": metrics.get("portfolio_calmar", 0),
            "win_rate": metrics.get("portfolio_win_rate", 0),
        },
    }
    
    # Save manifest
    manifest_path = output_dir / "strategy_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2, default=str)
    
    logger.info(f"Strategy manifest saved to {manifest_path}")
    
    return manifest_path


def generate_weights_csv(
    weights: pd.DataFrame,
    output_dir: Path,
) -> Path:
    """
    Generate latest weights CSV file.
    
    Args:
        weights: DataFrame with symbol and weight columns
        output_dir: Directory to save CSV
        
    Returns:
        Path to the saved CSV file
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    weights_path = output_dir / "weights_latest.csv"
    weights.to_csv(weights_path, index=False)
    
    logger.info(f"Weights CSV saved to {weights_path}")
    
    return weights_path


def generate_rankings_csv(
    rankings: pd.DataFrame,
    output_dir: Path,
) -> Path:
    """
    Generate latest rankings CSV file.
    
    Args:
        rankings: DataFrame with symbol, factor_value, rank columns
        output_dir: Directory to save CSV
        
    Returns:
        Path to the saved CSV file
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    rankings_path = output_dir / "rankings_latest.csv"
    rankings.to_csv(rankings_path, index=False)
    
    logger.info(f"Rankings CSV saved to {rankings_path}")
    
    return rankings_path


def generate_serving_config(
    config: Dict[str, Any],
    output_dir: Path,
) -> Path:
    """
    Generate serving configuration for model deployment.
    
    Args:
        config: Strategy configuration
        output_dir: Directory to save config
        
    Returns:
        Path to the saved config file
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    serving_config = {
        "model_name": config.get("experiment_name", "production"),
        "version": "latest",
        "capital_base": config.get("capital_base", 1_000_000),
        "bundle_name": config.get("bundle_name", "historical_prices_fmp"),
        "rebalance_frequency": "daily",
        "algorithm": config.get("algorithm", {}),
        "portfolio_strategy": config.get("portfolio_strategy", {}),
    }
    
    config_path = output_dir / "serving_config.json"
    with open(config_path, "w") as f:
        json.dump(serving_config, f, indent=2)
    
    logger.info(f"Serving config saved to {config_path}")
    
    return config_path


def generate_all_strategy_artifacts(
    config: Dict[str, Any],
    performance: pd.DataFrame,
    metrics: Dict[str, float],
    weights: Optional[pd.DataFrame] = None,
    rankings: Optional[pd.DataFrame] = None,
    output_dir: Optional[Path] = None,
) -> Dict[str, Path]:
    """
    Generate all strategy artifacts for MLflow logging.
    
    Args:
        config: Strategy configuration
        performance: Performance DataFrame
        metrics: Metrics dictionary
        weights: Optional weights DataFrame
        rankings: Optional rankings DataFrame
        output_dir: Output directory
        
    Returns:
        Dictionary of artifact names to file paths
    """
    if output_dir is None:
        from config.settings import get_settings
        output_dir = get_settings().dashboard_data_dir / "strategy_assets"
    
    output_dir = Path(output_dir)
    artifacts = {}
    
    # Generate manifest
    artifacts["manifest"] = generate_strategy_manifest(config, performance, metrics, output_dir)
    
    # Generate serving config
    artifacts["serving_config"] = generate_serving_config(config, output_dir)
    
    # Generate weights CSV
    if weights is not None:
        artifacts["weights"] = generate_weights_csv(weights, output_dir)
    
    # Generate rankings CSV
    if rankings is not None:
        artifacts["rankings"] = generate_rankings_csv(rankings, output_dir)
    
    logger.info(f"Generated {len(artifacts)} strategy artifacts")
    
    return artifacts
