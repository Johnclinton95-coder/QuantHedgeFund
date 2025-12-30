"""
QS Connect - Main Client

The Client class is the primary interface for all data operations.
It provides methods to download, cache, and manage market and fundamental data.
"""

import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, date

import pandas as pd
import polars as pl
from loguru import logger

from config.settings import get_settings
from config.constants import (
    AssetType,
    Exchange,
    StatementType,
    Period,
    FMP_RATE_LIMIT_PER_MINUTE,
)
from qsconnect.api.fmp_client import FMPClient
from qsconnect.database.duckdb_manager import DuckDBManager
from qsconnect.cache.cache_manager import CacheManager
from qsconnect.bundle.zipline_bundler import ZiplineBundler


class Client:
    """
    Main QS Connect client for data operations.
    
    Example:
        >>> from qsconnect import Client
        >>> client = Client()
        >>> prices = client.bulk_historical_prices()
        >>> client.build_zipline_bundle("historical_prices_fmp")
    """
    
    def __init__(
        self,
        fmp_api_key: Optional[str] = None,
        datalink_api_key: Optional[str] = None,
        duckdb_path: Optional[Path] = None,
        cache_dir: Optional[Path] = None,
    ):
        """
        Initialize the QS Connect client.
        
        Args:
            fmp_api_key: FMP API key (defaults to environment variable)
            datalink_api_key: Datalink API key (defaults to environment variable)
            duckdb_path: Path to DuckDB database file
            cache_dir: Directory for parquet file cache
        """
        settings = get_settings()
        
        # API Keys
        self._fmp_api_key = fmp_api_key or settings.fmp_api_key
        self._datalink_api_key = datalink_api_key or settings.datalink_api_key
        
        # Paths
        self._duckdb_path = duckdb_path or settings.duckdb_path
        self._cache_dir = cache_dir or settings.cache_dir
        
        # Validate API keys
        if not self._fmp_api_key:
            logger.warning("FMP API key not set. Some features will be unavailable.")
        
        # Initialize sub-clients
        self._fmp_client = FMPClient(api_key=self._fmp_api_key)
        self._db_manager = DuckDBManager(db_path=self._duckdb_path)
        self._cache_manager = CacheManager(cache_dir=self._cache_dir)
        self._bundler = ZiplineBundler(db_manager=self._db_manager)
        
        logger.info(f"QS Connect client initialized. Cache: {self._cache_dir}")
    
    # =====================
    # Stock Universe
    # =====================
    
    def stock_list(
        self,
        asset_type: str = "stock",
        exchanges: Optional[List[str]] = None,
        min_price: float = 5.0,
    ) -> pd.DataFrame:
        """
        Get filtered list of tradeable symbols.
        
        Args:
            asset_type: Filter by asset type ('stock', 'etf', etc.)
            exchanges: List of exchanges to include (defaults to NYSE, NASDAQ)
            min_price: Minimum price filter
            
        Returns:
            DataFrame with symbol, name, exchange, type columns
        """
        if exchanges is None:
            exchanges = [Exchange.NYSE.value, Exchange.NASDAQ.value]
        
        logger.info(f"Fetching stock list for {asset_type} from {exchanges}")
        
        stock_list = self._fmp_client.get_stock_list()
        
        # Filter by asset type
        if asset_type:
            stock_list = stock_list[stock_list["type"] == asset_type]
        
        # Filter by exchange
        stock_list = stock_list[stock_list["exchangeShortName"].isin(exchanges)]
        
        # Filter by price
        if min_price > 0 and "price" in stock_list.columns:
            stock_list = stock_list[stock_list["price"] >= min_price]
        
        logger.info(f"Filtered to {len(stock_list)} symbols")
        return stock_list
    
    # =====================
    # Price Data
    # =====================
    
    def bulk_historical_prices(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        symbols: Optional[List[str]] = None,
        use_cache: bool = True,
    ) -> pl.DataFrame:
        """
        Download bulk historical price data for all symbols.
        
        Args:
            start_date: Start date for historical data
            end_date: End date for historical data
            symbols: Optional list of specific symbols
            use_cache: Whether to use cached data
            
        Returns:
            Polars DataFrame with OHLCV data
        """
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = date(2000, 1, 1)
        
        cache_key = f"bulk_prices_{start_date}_{end_date}"
        
        # Check cache
        if use_cache:
            cached = self._cache_manager.get(cache_key)
            if cached is not None:
                logger.info(f"Loaded {len(cached)} rows from cache")
                return cached
        
        logger.info(f"Fetching bulk historical prices from {start_date} to {end_date}")
        
        # Get data from FMP
        prices = self._fmp_client.get_bulk_historical_prices(
            start_date=start_date,
            end_date=end_date,
            symbols=symbols,
        )
        
        # Cache the result
        if use_cache and prices is not None:
            self._cache_manager.set(cache_key, prices)
        
        # Store in database
        self._db_manager.upsert_prices(prices)
        
        return prices
    
    # =====================
    # Fundamental Data
    # =====================
    
    def fetch_bulk_financial_statements(
        self,
        statement_type: List[str],
        periods: str = "all",
        start_year: int = 2000,
        end_year: Optional[int] = None,
        api_buffer_seconds: int = 10,
    ) -> Dict[str, pl.DataFrame]:
        """
        Download bulk financial statement data.
        
        Args:
            statement_type: List of statement types (income-statement, balance-sheet, etc.)
            periods: 'annual', 'quarter', or 'all'
            start_year: Start year for data
            end_year: End year for data
            api_buffer_seconds: Delay between API calls
            
        Returns:
            Dictionary of DataFrames by statement type
        """
        if end_year is None:
            end_year = datetime.now().year
        
        results = {}
        
        for stmt_type in statement_type:
            logger.info(f"Fetching {stmt_type} statements from {start_year} to {end_year}")
            
            data = self._fmp_client.get_bulk_financial_statements(
                statement_type=stmt_type,
                periods=periods,
                start_year=start_year,
                end_year=end_year,
                api_buffer_seconds=api_buffer_seconds,
            )
            
            if data is not None:
                # Cache and store
                cache_key = f"bulk_{stmt_type}_{start_year}_{end_year}"
                self._cache_manager.set(cache_key, data)
                self._db_manager.upsert_fundamentals(stmt_type, data)
                results[stmt_type] = data
        
        return results
    
    # =====================
    # Cache Management
    # =====================
    
    def detect_cached_files(self) -> pd.DataFrame:
        """Get a list of all cached parquet files."""
        return self._cache_manager.list_cached_files()
    
    def detect_missing_cached_files(
        self,
        statement_type: List[str],
        periods: str = "all",
        start_year: int = 2000,
        end_year: Optional[int] = None,
    ) -> List[str]:
        """Detect which files are missing from cache for incremental download."""
        return self._cache_manager.detect_missing(
            statement_type=statement_type,
            periods=periods,
            start_year=start_year,
            end_year=end_year,
        )
    
    # =====================
    # Database Operations
    # =====================
    
    def connect_db(self):
        """Establish connection to DuckDB database."""
        return self._db_manager.connect()
    
    def query(self, sql: str) -> pl.DataFrame:
        """Execute a SQL query against the database."""
        return self._db_manager.query(sql)
    
    # =====================
    # Zipline Bundle
    # =====================
    
    def build_zipline_bundle(
        self,
        bundle_name: str = "historical_prices_fmp",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> None:
        """
        Build a Zipline-compatible data bundle.
        
        Args:
            bundle_name: Name for the bundle
            start_date: Start date for bundle data
            end_date: End date for bundle data
        """
        logger.info(f"Building Zipline bundle: {bundle_name}")
        self._bundler.build_bundle(
            bundle_name=bundle_name,
            start_date=start_date,
            end_date=end_date,
        )
    
    def register_bundle(self, bundle_name: str) -> None:
        """Register a bundle with Zipline."""
        self._bundler.register_bundle(bundle_name)
    
    def ingest_bundle(self, bundle_name: str) -> None:
        """Ingest a registered bundle into Zipline."""
        self._bundler.ingest_bundle(bundle_name)
    
    # =====================
    # Utilities
    # =====================
    
    @staticmethod
    def root_path() -> Path:
        """Get the QS Connect root cache path."""
        return get_settings().cache_dir
    
    def close(self) -> None:
        """Close all connections."""
        self._db_manager.close()
        logger.info("QS Connect client closed")
