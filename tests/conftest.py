"""
Pytest Configuration and Shared Fixtures

Provides common fixtures for QuantHedgeFund tests.
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime
import pandas as pd
import polars as pl
import numpy as np


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_prices_df():
    """Create sample price data for testing."""
    dates = pd.date_range("2024-01-01", periods=300, freq="D")
    
    data = {
        "symbol": ["AAPL"] * 300,
        "date": dates,
        "open": np.random.uniform(150, 200, 300),
        "high": np.random.uniform(155, 205, 300),
        "low": np.random.uniform(145, 195, 300),
        "close": np.random.uniform(150, 200, 300),
        "volume": np.random.randint(1000000, 10000000, 300),
    }
    
    df = pd.DataFrame(data)
    # Ensure high >= low
    df["high"] = df[["high", "open", "close"]].max(axis=1) + 1
    df["low"] = df[["low", "open", "close"]].min(axis=1) - 1
    
    return df


@pytest.fixture
def sample_prices_polars(sample_prices_df):
    """Create sample price data as Polars DataFrame."""
    return pl.from_pandas(sample_prices_df)


@pytest.fixture
def mock_state_file(temp_dir):
    """Create a mock system state file path."""
    return temp_dir / "system_state.json"


@pytest.fixture
def sample_symbols():
    """List of sample stock symbols for testing."""
    return ["AAPL", "MSFT", "GOOGL", "AMZN", "META"]
