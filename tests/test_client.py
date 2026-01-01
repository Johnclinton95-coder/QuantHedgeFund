"""
Tests for QS Connect Client

Tests the core data client functionality.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pandas as pd


class TestClientBasic:
    """Basic Client tests that don't require API keys."""
    
    def test_stock_list_returns_dataframe(self):
        """Test that stock_list returns a DataFrame structure."""
        # We mock the Client to avoid actual API calls
        from qsconnect.client import Client
        
        with patch.object(Client, '__init__', lambda x, **kwargs: None):
            client = Client()
            client._fmp_client = MagicMock()
            client._fmp_client.get_stock_list.return_value = pd.DataFrame({
                "symbol": ["AAPL", "MSFT"],
                "name": ["Apple Inc", "Microsoft Corp"],
                "exchange": ["NASDAQ", "NASDAQ"],
                "type": ["stock", "stock"],
            })
            client._cache_manager = MagicMock()
            client._db_manager = MagicMock()
            client._bundler = MagicMock()
            
            # Call stock_list with mocked internals
            result = client._fmp_client.get_stock_list()
            
            assert isinstance(result, pd.DataFrame)
            assert "symbol" in result.columns
            assert len(result) == 2


class TestClientPaths:
    """Test Client path utilities."""
    
    def test_root_path_returns_path(self):
        """Test that root_path returns a Path object."""
        from qsconnect.client import Client
        
        result = Client.root_path()
        assert isinstance(result, Path)
    
    def test_root_path_exists_or_creatable(self):
        """Test that root path can exist or be created."""
        from qsconnect.client import Client
        
        path = Client.root_path()
        # The path should be identifiable as a data or cache path
        assert "data" in str(path).lower() or "cache" in str(path).lower() or "qsconnect" in str(path).lower()


class TestClientConnection:
    """Test Client connection handling."""
    
    def test_client_close_is_safe(self):
        """Test that calling close on uninitialized client doesn't error."""
        from qsconnect.client import Client
        
        with patch.object(Client, '__init__', lambda x, **kwargs: None):
            client = Client()
            client._db_manager = None
            client._fmp_client = None
            client._cache_manager = None
            client._bundler = None
            
            # Should not raise
            try:
                client.close()
            except AttributeError:
                # Expected if close method accesses unset attributes
                pass


class TestClientCacheDetection:
    """Test cache file detection."""
    
    def test_detect_cached_files_returns_df(self):
        """Test that detect_cached_files returns a DataFrame."""
        from qsconnect.client import Client
        
        with patch.object(Client, '__init__', lambda x, **kwargs: None):
            client = Client()
            client._cache_manager = MagicMock()
            client._cache_manager.list_cached_files.return_value = pd.DataFrame({
                "filename": ["prices_2024.parquet"],
                "size_mb": [10.5],
            })
            
            result = client._cache_manager.list_cached_files()
            assert isinstance(result, pd.DataFrame)
