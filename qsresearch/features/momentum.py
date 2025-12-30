"""
QS Research - Momentum Factor

Calculates momentum factors for quantitative strategies.
Based on the classic momentum anomaly with configurable lookback periods.
"""

from typing import Optional
import pandas as pd
import polars as pl
from loguru import logger

try:
    import pandas_ta as ta
except ImportError:
    ta = None
    logger.warning("pandas_ta not installed. Some features may be unavailable.")


def add_qsmom_features(
    df: pd.DataFrame,
    fast_period: int = 21,
    slow_period: int = 252,
    signal_period: int = 126,
    symbol_column: str = "symbol",
    date_column: str = "date",
    close_column: str = "close",
) -> pd.DataFrame:
    """
    Add QS Momentum features to a price DataFrame.
    
    The QS Momentum factor is calculated as:
    QSMOM = ROC(slow) - ROC(fast) - ROC(signal)
    
    This captures momentum while accounting for short-term mean reversion.
    
    Args:
        df: DataFrame with price data
        fast_period: Short-term momentum period (default: 21 days / 1 month)
        slow_period: Long-term momentum period (default: 252 days / 1 year)
        signal_period: Signal smoothing period (default: 126 days / 6 months)
        symbol_column: Name of symbol column
        date_column: Name of date column
        close_column: Name of close price column
        
    Returns:
        DataFrame with added momentum features
    """
    logger.info(f"Calculating QSMOM features ({fast_period}/{slow_period}/{signal_period})")
    
    # Sort by symbol and date
    df = df.sort_values([symbol_column, date_column]).copy()
    
    # Calculate momentum for each symbol
    momentum_dfs = []
    
    for symbol in df[symbol_column].unique():
        symbol_df = df[df[symbol_column] == symbol].copy()
        
        if len(symbol_df) < slow_period:
            continue
        
        close = symbol_df[close_column]
        
        # Calculate Rate of Change (ROC) for different periods
        symbol_df["roc_fast"] = close.pct_change(periods=fast_period) * 100
        symbol_df["roc_slow"] = close.pct_change(periods=slow_period) * 100
        symbol_df["roc_signal"] = close.pct_change(periods=signal_period) * 100
        
        # Calculate momentum factor
        # Higher values = stronger momentum
        symbol_df[f"close_qsmom_{fast_period}_{slow_period}_{signal_period}"] = (
            symbol_df["roc_slow"] - symbol_df["roc_fast"]
        )
        
        # Add rolling momentum rank (percentile within lookback)
        symbol_df["momentum_zscore"] = (
            (symbol_df["roc_slow"] - symbol_df["roc_slow"].rolling(slow_period).mean())
            / symbol_df["roc_slow"].rolling(slow_period).std()
        )
        
        # Add volatility-adjusted momentum
        volatility = close.pct_change().rolling(fast_period).std() * (252 ** 0.5)
        symbol_df["momentum_sharpe"] = symbol_df["roc_slow"] / (volatility * 100 + 1e-6)
        
        momentum_dfs.append(symbol_df)
    
    if not momentum_dfs:
        logger.warning("No symbols had enough data for momentum calculation")
        return df
    
    result = pd.concat(momentum_dfs, ignore_index=True)
    
    # Add cross-sectional rank
    result["momentum_rank"] = result.groupby(date_column)[
        f"close_qsmom_{fast_period}_{slow_period}_{signal_period}"
    ].rank(pct=True)
    
    logger.info(f"Added momentum features for {len(momentum_dfs)} symbols")
    
    return result


def add_roc_features(
    df: pd.DataFrame,
    periods: list = [5, 10, 21, 63, 126, 252],
    symbol_column: str = "symbol",
    close_column: str = "close",
) -> pd.DataFrame:
    """
    Add Rate of Change features for multiple periods.
    
    Args:
        df: DataFrame with price data
        periods: List of lookback periods
        symbol_column: Name of symbol column
        close_column: Name of close price column
        
    Returns:
        DataFrame with ROC features
    """
    df = df.copy()
    
    for symbol in df[symbol_column].unique():
        mask = df[symbol_column] == symbol
        close = df.loc[mask, close_column]
        
        for period in periods:
            df.loc[mask, f"roc_{period}"] = close.pct_change(periods=period) * 100
    
    return df


def add_relative_strength(
    df: pd.DataFrame,
    benchmark_returns: pd.Series,
    period: int = 252,
    symbol_column: str = "symbol",
    date_column: str = "date",
    close_column: str = "close",
) -> pd.DataFrame:
    """
    Add relative strength vs benchmark.
    
    Args:
        df: DataFrame with price data
        benchmark_returns: Series of benchmark daily returns
        period: Lookback period for relative strength
        symbol_column: Name of symbol column
        date_column: Name of date column
        close_column: Name of close price column
        
    Returns:
        DataFrame with relative strength features
    """
    df = df.copy()
    
    # Calculate cumulative benchmark return
    benchmark_cum = (1 + benchmark_returns).rolling(period).apply(
        lambda x: x.prod() - 1, raw=True
    )
    
    for symbol in df[symbol_column].unique():
        mask = df[symbol_column] == symbol
        close = df.loc[mask, close_column]
        
        # Stock cumulative return
        stock_return = close.pct_change(periods=period)
        
        # Relative strength
        df.loc[mask, "relative_strength"] = stock_return - benchmark_cum.reindex(
            df.loc[mask, date_column]
        ).values
    
    return df
