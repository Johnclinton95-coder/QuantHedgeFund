"""
QS Research - Forward Returns

Calculate forward returns for target variable creation in ML strategies.
"""

from typing import List
import pandas as pd
from loguru import logger


def add_forward_returns(
    df: pd.DataFrame,
    forward_periods: List[int] = [1, 5, 10, 21],
    symbol_column: str = "symbol",
    date_column: str = "date",
    close_column: str = "close",
    engine: str = "polars",
) -> pd.DataFrame:
    """
    Add forward return columns for ML target creation.
    
    Args:
        df: DataFrame with price data
        forward_periods: List of forward periods (in trading days)
        symbol_column: Name of symbol column
        date_column: Name of date column
        close_column: Name of close price column
        engine: Processing engine ('polars' or 'pandas')
        
    Returns:
        DataFrame with forward return columns added
    """
    df = df.sort_values([symbol_column, date_column]).copy()
    
    for period in forward_periods:
        col_name = f"forward_return_{period}d"
        
        # Calculate forward return per symbol
        df[col_name] = df.groupby(symbol_column)[close_column].transform(
            lambda x: x.shift(-period) / x - 1
        )
        
        logger.debug(f"Added forward return column: {col_name}")
    
    logger.info(f"Added {len(forward_periods)} forward return columns")
    return df


def add_forward_return_quintiles(
    df: pd.DataFrame,
    forward_column: str = "forward_return_21d",
    date_column: str = "date",
    output_column: str = "return_quintile",
) -> pd.DataFrame:
    """
    Add quintile labels for forward returns (for classification).
    
    Args:
        df: DataFrame with forward returns
        forward_column: Forward return column to quintile
        date_column: Date column for cross-sectional ranking
        output_column: Name of output quintile column
        
    Returns:
        DataFrame with quintile labels (1-5)
    """
    df = df.copy()
    
    # Calculate quintiles cross-sectionally (within each date)
    df[output_column] = df.groupby(date_column)[forward_column].transform(
        lambda x: pd.qcut(x, 5, labels=[1, 2, 3, 4, 5], duplicates="drop")
    )
    
    return df
