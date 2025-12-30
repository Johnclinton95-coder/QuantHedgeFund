"""
QS Research - Technical Indicators with pandas-ta

Calculate technical indicators for signal generation.
Replaces the i*_tk functionality mentioned in the videos.
"""

from typing import Optional, List
import pandas as pd
from loguru import logger

try:
    import pandas_ta as ta
    PANDAS_TA_AVAILABLE = True
except ImportError:
    PANDAS_TA_AVAILABLE = False
    logger.warning("pandas-ta not installed. Technical indicators unavailable.")


def add_technical_indicators(
    df: pd.DataFrame,
    symbol_column: str = "symbol",
    open_column: str = "open",
    high_column: str = "high",
    low_column: str = "low",
    close_column: str = "close",
    volume_column: str = "volume",
    indicators: Optional[List[str]] = None,
) -> pd.DataFrame:
    """
    Add technical indicators to price DataFrame.
    
    Args:
        df: Price DataFrame
        symbol_column: Symbol column name
        open_column: Open price column
        high_column: High price column
        low_column: Low price column
        close_column: Close price column
        volume_column: Volume column
        indicators: List of indicator names to calculate
        
    Returns:
        DataFrame with added indicator columns
    """
    if not PANDAS_TA_AVAILABLE:
        logger.warning("pandas-ta not available, skipping technical indicators")
        return df
    
    if indicators is None:
        indicators = ["sma_20", "sma_50", "sma_200", "ema_21", "rsi_14", "macd", "bbands"]
    
    df = df.copy()
    result_dfs = []
    
    for symbol in df[symbol_column].unique():
        symbol_df = df[df[symbol_column] == symbol].copy()
        
        close = symbol_df[close_column]
        high = symbol_df[high_column]
        low = symbol_df[low_column]
        volume = symbol_df[volume_column]
        
        # Simple Moving Averages
        if "sma_20" in indicators:
            symbol_df["sma_20"] = ta.sma(close, length=20)
        if "sma_50" in indicators:
            symbol_df["sma_50"] = ta.sma(close, length=50)
        if "sma_200" in indicators:
            symbol_df["sma_200"] = ta.sma(close, length=200)
        
        # Exponential Moving Averages
        if "ema_21" in indicators:
            symbol_df["ema_21"] = ta.ema(close, length=21)
        if "ema_50" in indicators:
            symbol_df["ema_50"] = ta.ema(close, length=50)
        
        # RSI
        if "rsi_14" in indicators:
            symbol_df["rsi_14"] = ta.rsi(close, length=14)
        
        # MACD
        if "macd" in indicators:
            macd = ta.macd(close)
            if macd is not None:
                symbol_df = pd.concat([symbol_df, macd], axis=1)
        
        # Bollinger Bands
        if "bbands" in indicators:
            bbands = ta.bbands(close, length=20, std=2)
            if bbands is not None:
                symbol_df = pd.concat([symbol_df, bbands], axis=1)
        
        # ATR (Average True Range)
        if "atr" in indicators:
            symbol_df["atr_14"] = ta.atr(high, low, close, length=14)
        
        # Volume indicators
        if "obv" in indicators:
            symbol_df["obv"] = ta.obv(close, volume)
        
        if "vwap" in indicators:
            symbol_df["vwap"] = ta.vwap(high, low, close, volume)
        
        result_dfs.append(symbol_df)
    
    result = pd.concat(result_dfs, ignore_index=True)
    logger.info(f"Added technical indicators for {len(df[symbol_column].unique())} symbols")
    
    return result


def add_trend_signals(
    df: pd.DataFrame,
    close_column: str = "close",
) -> pd.DataFrame:
    """
    Add trend-following signals based on moving average crossovers.
    
    Args:
        df: DataFrame with price and indicator data
        close_column: Close price column name
        
    Returns:
        DataFrame with added signal columns
    """
    df = df.copy()
    
    # Golden Cross / Death Cross (50/200 SMA)
    if "sma_50" in df.columns and "sma_200" in df.columns:
        df["golden_cross"] = (df["sma_50"] > df["sma_200"]).astype(int)
        df["death_cross"] = (df["sma_50"] < df["sma_200"]).astype(int)
    
    # Price vs SMA signals
    if "sma_200" in df.columns:
        df["above_sma200"] = (df[close_column] > df["sma_200"]).astype(int)
    
    # RSI signals
    if "rsi_14" in df.columns:
        df["rsi_oversold"] = (df["rsi_14"] < 30).astype(int)
        df["rsi_overbought"] = (df["rsi_14"] > 70).astype(int)
    
    # Bollinger Band signals
    if "BBL_20_2.0" in df.columns and "BBU_20_2.0" in df.columns:
        df["bb_lower_touch"] = (df[close_column] <= df["BBL_20_2.0"]).astype(int)
        df["bb_upper_touch"] = (df[close_column] >= df["BBU_20_2.0"]).astype(int)
    
    return df
