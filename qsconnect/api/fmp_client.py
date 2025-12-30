"""
QS Connect - Financial Modeling Prep (FMP) API Client

Client for interacting with the FMP API for market and fundamental data.
https://financialmodelingprep.com/developer/docs
"""

from datetime import date
from typing import Optional, List, Dict, Any
import time

import pandas as pd
import polars as pl
from loguru import logger
from tqdm import tqdm

from qsconnect.api.base_client import BaseAPIClient
from config.constants import FMP_RATE_LIMIT_PER_MINUTE, StatementType


class FMPClient(BaseAPIClient):
    """
    Client for Financial Modeling Prep API.
    
    Provides access to:
    - Stock lists and company profiles
    - Historical price data
    - Financial statements (income, balance sheet, cash flow)
    - Financial ratios and metrics
    """
    
    BASE_URL = "https://financialmodelingprep.com/api/v3"
    
    def __init__(self, api_key: str):
        """
        Initialize FMP client.
        
        Args:
            api_key: FMP API key
        """
        super().__init__(
            base_url=self.BASE_URL,
            api_key=api_key,
            rate_limit_per_minute=FMP_RATE_LIMIT_PER_MINUTE,
        )
        logger.info("FMP client initialized")
    
    # =====================
    # Stock Lists
    # =====================
    
    def get_stock_list(self) -> pd.DataFrame:
        """
        Get complete list of available stocks.
        
        Returns:
            DataFrame with columns: symbol, name, price, exchange, exchangeShortName, type
        """
        data = self._make_request("stock/list")
        if data:
            return pd.DataFrame(data)
        return pd.DataFrame()
    
    def get_etf_list(self) -> pd.DataFrame:
        """Get list of available ETFs."""
        data = self._make_request("etf/list")
        if data:
            return pd.DataFrame(data)
        return pd.DataFrame()
    
    def get_tradeable_symbols(self) -> pd.DataFrame:
        """Get list of all tradeable symbols."""
        data = self._make_request("available-traded/list")
        if data:
            return pd.DataFrame(data)
        return pd.DataFrame()
    
    # =====================
    # Company Profiles
    # =====================
    
    def get_company_profile(self, symbol: str) -> Dict[str, Any]:
        """Get company profile for a symbol."""
        data = self._make_request(f"profile/{symbol}")
        if data and len(data) > 0:
            return data[0]
        return {}
    
    def get_company_profiles_batch(self, symbols: List[str]) -> pd.DataFrame:
        """Get company profiles for multiple symbols (batch of up to 50)."""
        symbols_str = ",".join(symbols[:50])
        data = self._make_request(f"profile/{symbols_str}")
        if data:
            return pd.DataFrame(data)
        return pd.DataFrame()
    
    # =====================
    # Historical Prices
    # =====================
    
    def get_historical_prices(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> pd.DataFrame:
        """
        Get historical daily prices for a symbol.
        
        Args:
            symbol: Stock symbol
            start_date: Start date for data
            end_date: End date for data
            
        Returns:
            DataFrame with OHLCV data
        """
        params = {}
        if start_date:
            params["from"] = start_date.isoformat()
        if end_date:
            params["to"] = end_date.isoformat()
        
        data = self._make_request(f"historical-price-full/{symbol}", params=params)
        
        if data and "historical" in data:
            df = pd.DataFrame(data["historical"])
            df["symbol"] = symbol
            return df
        return pd.DataFrame()
    
    def get_bulk_historical_prices(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        symbols: Optional[List[str]] = None,
    ) -> pl.DataFrame:
        """
        Get bulk historical prices for multiple symbols.
        
        This method fetches data in batches to handle large numbers of symbols.
        
        Args:
            start_date: Start date for data
            end_date: End date for data
            symbols: Optional list of specific symbols
            
        Returns:
            Polars DataFrame with all price data
        """
        if symbols is None:
            # Get all symbols from stock list
            stock_list = self.get_stock_list()
            symbols = stock_list["symbol"].tolist()
        
        logger.info(f"Fetching bulk prices for {len(symbols)} symbols")
        
        all_data = []
        
        # Process in batches of 5 symbols per request
        batch_size = 5
        for i in tqdm(range(0, len(symbols), batch_size), desc="Downloading prices"):
            batch = symbols[i : i + batch_size]
            symbols_str = ",".join(batch)
            
            params = {}
            if start_date:
                params["from"] = start_date.isoformat()
            if end_date:
                params["to"] = end_date.isoformat()
            
            data = self._make_request(
                f"historical-price-full/{symbols_str}",
                params=params,
            )
            
            if data:
                if isinstance(data, dict) and "historicalStockList" in data:
                    for item in data["historicalStockList"]:
                        if "historical" in item:
                            df = pd.DataFrame(item["historical"])
                            df["symbol"] = item["symbol"]
                            all_data.append(df)
                elif isinstance(data, dict) and "historical" in data:
                    df = pd.DataFrame(data["historical"])
                    df["symbol"] = data.get("symbol", batch[0])
                    all_data.append(df)
        
        if all_data:
            combined = pd.concat(all_data, ignore_index=True)
            logger.info(f"Downloaded {len(combined)} price records")
            return pl.from_pandas(combined)
        
        return pl.DataFrame()
    
    # =====================
    # Financial Statements
    # =====================
    
    def get_income_statement(
        self,
        symbol: str,
        period: str = "annual",
        limit: int = 100,
    ) -> pd.DataFrame:
        """Get income statements for a symbol."""
        params = {"period": period, "limit": limit}
        data = self._make_request(f"income-statement/{symbol}", params=params)
        if data:
            return pd.DataFrame(data)
        return pd.DataFrame()
    
    def get_balance_sheet(
        self,
        symbol: str,
        period: str = "annual",
        limit: int = 100,
    ) -> pd.DataFrame:
        """Get balance sheet statements for a symbol."""
        params = {"period": period, "limit": limit}
        data = self._make_request(f"balance-sheet-statement/{symbol}", params=params)
        if data:
            return pd.DataFrame(data)
        return pd.DataFrame()
    
    def get_cash_flow_statement(
        self,
        symbol: str,
        period: str = "annual",
        limit: int = 100,
    ) -> pd.DataFrame:
        """Get cash flow statements for a symbol."""
        params = {"period": period, "limit": limit}
        data = self._make_request(f"cash-flow-statement/{symbol}", params=params)
        if data:
            return pd.DataFrame(data)
        return pd.DataFrame()
    
    def get_financial_ratios(
        self,
        symbol: str,
        period: str = "annual",
        limit: int = 100,
    ) -> pd.DataFrame:
        """Get financial ratios for a symbol."""
        params = {"period": period, "limit": limit}
        data = self._make_request(f"ratios/{symbol}", params=params)
        if data:
            return pd.DataFrame(data)
        return pd.DataFrame()
    
    def get_key_metrics(
        self,
        symbol: str,
        period: str = "annual",
        limit: int = 100,
    ) -> pd.DataFrame:
        """Get key metrics for a symbol."""
        params = {"period": period, "limit": limit}
        data = self._make_request(f"key-metrics/{symbol}", params=params)
        if data:
            return pd.DataFrame(data)
        return pd.DataFrame()
    
    # =====================
    # Bulk Financial Data
    # =====================
    
    def get_bulk_financial_statements(
        self,
        statement_type: str,
        periods: str = "all",
        start_year: int = 2000,
        end_year: int = 2025,
        api_buffer_seconds: int = 10,
    ) -> pl.DataFrame:
        """
        Get bulk financial statements for all companies.
        
        Uses the bulk endpoints to efficiently download large amounts of data.
        
        Args:
            statement_type: Type of statement (income-statement, balance-sheet, etc.)
            periods: 'annual', 'quarter', or 'all'
            start_year: Start year
            end_year: End year
            api_buffer_seconds: Delay between API calls
            
        Returns:
            Polars DataFrame with all financial data
        """
        all_data = []
        
        period_list = ["annual", "quarter"] if periods == "all" else [periods]
        
        for period in period_list:
            logger.info(f"Fetching {period} data for {statement_type} statements...")
            
            for year in tqdm(
                range(start_year, end_year + 1),
                desc=f"{period.capitalize()} Progress ({statement_type})"
            ):
                cache_key = f"bulk-{statement_type}_{year}_{period}"
                
                # Use bulk endpoint
                endpoint = f"income-statement-bulk"
                if statement_type == "balance-sheet-statement":
                    endpoint = "balance-sheet-statement-bulk"
                elif statement_type == "cash-flow-statement":
                    endpoint = "cash-flow-statement-bulk"
                elif statement_type == "ratios":
                    endpoint = "ratios-bulk"
                
                params = {"year": year, "period": period}
                data = self._make_request(endpoint, params=params)
                
                if data:
                    df = pd.DataFrame(data)
                    df["_year"] = year
                    df["_period"] = period
                    all_data.append(df)
                    logger.info(f"Cached data for key '{cache_key}'")
                
                # Buffer to avoid rate limiting
                time.sleep(api_buffer_seconds / 10)
        
        if all_data:
            combined = pd.concat(all_data, ignore_index=True)
            logger.info(f"Downloaded {len(combined)} {statement_type} records")
            return pl.from_pandas(combined)
        
        return pl.DataFrame()
