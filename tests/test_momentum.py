"""
Tests for Momentum Factor Calculations

Tests the QSMOM momentum factor features.
"""

import pytest
import pandas as pd
import numpy as np


class TestMomentumFeatures:
    """Test momentum factor calculations."""
    
    def test_add_qsmom_features_creates_column(self, sample_prices_df):
        """Test that add_qsmom_features creates the factor column."""
        from qsresearch.features.momentum import add_qsmom_features
        
        result = add_qsmom_features(
            sample_prices_df,
            fast_period=21,
            slow_period=252,
            signal_period=126
        )
        
        # Check that the expected column exists
        expected_col = "close_qsmom_21_252_126"
        assert expected_col in result.columns
    
    def test_add_qsmom_features_handles_short_data(self):
        """Test that add_qsmom_features handles data shorter than lookback."""
        from qsresearch.features.momentum import add_qsmom_features
        
        # Create data with only 100 rows (less than slow_period=252)
        dates = pd.date_range("2024-01-01", periods=100, freq="D")
        df = pd.DataFrame({
            "symbol": ["AAPL"] * 100,
            "date": dates,
            "open": np.random.uniform(150, 200, 100),
            "high": np.random.uniform(155, 205, 100),
            "low": np.random.uniform(145, 195, 100),
            "close": np.random.uniform(150, 200, 100),
            "volume": np.random.randint(1000000, 10000000, 100),
        })
        
        # Should not raise, but may have NaN values
        result = add_qsmom_features(df, fast_period=21, slow_period=252, signal_period=126)
        
        assert result is not None
        assert len(result) == 100
    
    def test_add_qsmom_features_preserves_original_columns(self, sample_prices_df):
        """Test that original columns are preserved."""
        from qsresearch.features.momentum import add_qsmom_features
        
        original_cols = set(sample_prices_df.columns)
        
        result = add_qsmom_features(
            sample_prices_df,
            fast_period=21,
            slow_period=252,
            signal_period=126
        )
        
        # All original columns should still exist
        for col in original_cols:
            assert col in result.columns
    
    def test_qsmom_values_are_numeric(self, sample_prices_df):
        """Test that QSMOM values are numeric (not inf or complex)."""
        from qsresearch.features.momentum import add_qsmom_features
        
        result = add_qsmom_features(
            sample_prices_df,
            fast_period=21,
            slow_period=252,
            signal_period=126
        )
        
        qsmom_col = "close_qsmom_21_252_126"
        
        # Drop NaN values for this check
        values = result[qsmom_col].dropna()
        
        if len(values) > 0:
            # Should be finite numbers
            assert np.all(np.isfinite(values))
            # Should be real (not complex)
            assert values.dtype in [np.float64, np.float32, np.int64, np.int32]
    
    def test_different_periods_create_different_columns(self, sample_prices_df):
        """Test that different period configurations create unique columns."""
        from qsresearch.features.momentum import add_qsmom_features
        
        result1 = add_qsmom_features(sample_prices_df.copy(), fast_period=21, slow_period=252, signal_period=126)
        result2 = add_qsmom_features(sample_prices_df.copy(), fast_period=42, slow_period=252, signal_period=126)
        
        col1 = "close_qsmom_21_252_126"
        col2 = "close_qsmom_42_252_126"
        
        assert col1 in result1.columns
        assert col2 in result2.columns
        assert col1 != col2


class TestMomentumEdgeCases:
    """Test edge cases for momentum calculations."""
    
    def test_empty_dataframe(self):
        """Test handling of empty DataFrame."""
        from qsresearch.features.momentum import add_qsmom_features
        
        empty_df = pd.DataFrame(columns=["symbol", "date", "close"])
        
        try:
            result = add_qsmom_features(empty_df, fast_period=21, slow_period=252, signal_period=126)
            assert len(result) == 0
        except (ValueError, KeyError):
            # Expected - empty df may raise
            pass
    
    def test_single_symbol_data(self, sample_prices_df):
        """Test with data for a single symbol."""
        from qsresearch.features.momentum import add_qsmom_features
        
        # sample_prices_df already has only AAPL
        result = add_qsmom_features(
            sample_prices_df,
            fast_period=21,
            slow_period=252,
            signal_period=126
        )
        
        assert len(result) == len(sample_prices_df)
        assert result["symbol"].nunique() == 1
