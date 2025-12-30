"""
Workflow - Data Ingestion DAG

Luigi task definitions for downloading market and fundamental data.
This module contains the core data pipeline tasks.
"""

import os
import logging
from pathlib import Path
from datetime import date

import luigi
from dotenv import load_dotenv

from qsconnect import Client
from qsconnect.utils.paths import qsconnect_root as qsconnect_root_path

load_dotenv()

logger = logging.getLogger(__name__)


# =============================================================================
# 1. Download Prices Task
# =============================================================================

class DownloadPricesFMP(luigi.Task):
    """
    Task to download historical price data from FMP API.
    
    This task:
    1. Connects to the FMP API
    2. Downloads bulk historical prices
    3. Caches the data as parquet files
    4. Stores in DuckDB database
    """
    
    start_date = luigi.DateParameter()
    run_date = luigi.DateParameter()
    
    # Luigi retry settings
    retry_count = 3
    retry_delay = 60
    
    # Resource management (prevent concurrent DuckDB writes)
    resources = {"duckdb_write": 1}
    
    def output(self):
        """Define task completion marker file."""
        qs_root = Path(qsconnect_root_path())
        path = qs_root / "cache" / "fmp" / f"prices_fmp_{self.run_date:%Y-%m-%d}.done"
        return luigi.LocalTarget(str(path))
    
    def run(self):
        """Execute the price download task."""
        tmp_done = self.output().path + ".partial"
        Path(tmp_done).parent.mkdir(parents=True, exist_ok=True)
        
        try:
            logger.info(f"Fetching price data for {self.run_date}")
            
            # Connect to QS Connect client
            client = Client()
            
            # Get stock list
            stock_list = client.stock_list("stock")
            
            # Filter to US exchanges (NYSE, NASDAQ)
            stock_list = stock_list[
                stock_list["exchangeShortName"].isin(["NYSE", "NASDAQ"])
            ]
            
            # Filter minimum price
            if "price" in stock_list.columns:
                stock_list = stock_list[stock_list["price"] >= 5.0]
            
            symbols = stock_list["symbol"].tolist()
            
            # Add benchmark ETFs
            benchmarks = ["SPY", "QQQ", "IWM"]
            symbols = list(set(symbols + benchmarks))
            
            logger.info(f"Downloading prices for {len(symbols)} symbols")
            
            # Download bulk historical prices
            prices = client.bulk_historical_prices(
                start_date=self.start_date,
                end_date=self.run_date,
                symbols=symbols,
            )
            
            logger.info(f"Downloaded {len(prices)} price records")
            
            # Mark success
            Path(tmp_done).touch()
            os.rename(tmp_done, self.output().path)
            
            logger.info("Price download completed successfully")
            
            client.close()
            
        except Exception as e:
            logger.error(f"Price download failed: {e}")
            if os.path.exists(tmp_done):
                os.remove(tmp_done)
            raise


# =============================================================================
# 2. Download Fundamentals Task
# =============================================================================

class DownloadFundamentalsFMP(luigi.Task):
    """
    Task to download fundamental data from FMP API.
    
    Downloads:
    - Income statements
    - Balance sheets
    - Cash flow statements
    - Financial ratios
    """
    
    start_date = luigi.DateParameter()
    run_date = luigi.DateParameter()
    api_buffer_seconds = luigi.IntParameter(default=10)
    
    retry_count = 3
    retry_delay = 60
    resources = {"duckdb_write": 1}
    
    def requires(self):
        """This task depends on price data being downloaded first."""
        return DownloadPricesFMP(
            start_date=self.start_date,
            run_date=self.run_date,
        )
    
    def output(self):
        """Define task completion marker file."""
        qs_root = Path(qsconnect_root_path())
        path = qs_root / "cache" / "fmp" / f"fundamentals_fmp_{self.run_date:%Y-%m-%d}.done"
        return luigi.LocalTarget(str(path))
    
    def run(self):
        """Execute the fundamentals download task."""
        tmp_done = self.output().path + ".partial"
        Path(tmp_done).parent.mkdir(parents=True, exist_ok=True)
        
        try:
            logger.info(f"Fetching fundamental data for {self.run_date}")
            
            client = Client()
            
            # Statement types to download
            statement_types = [
                "income-statement",
                "balance-sheet-statement",
                "cash-flow-statement",
                "ratios",
            ]
            
            # Download fundamentals
            client.fetch_bulk_financial_statements(
                statement_type=statement_types,
                periods="all",
                start_year=self.start_date.year,
                end_year=self.run_date.year,
                api_buffer_seconds=self.api_buffer_seconds,
            )
            
            # Mark success
            Path(tmp_done).touch()
            os.rename(tmp_done, self.output().path)
            
            logger.info("Fundamentals download completed successfully")
            
            client.close()
            
        except Exception as e:
            logger.error(f"Fundamentals download failed: {e}")
            if os.path.exists(tmp_done):
                os.remove(tmp_done)
            raise


# =============================================================================
# 3. Build Zipline Bundle Task
# =============================================================================

class BuildZiplineBundle(luigi.Task):
    """
    Task to build Zipline-compatible data bundle.
    
    Converts the DuckDB data into Zipline format for backtesting.
    """
    
    start_date = luigi.DateParameter()
    run_date = luigi.DateParameter()
    bundle_name = luigi.Parameter(default="historical_prices_fmp")
    
    retry_count = 1
    retry_delay = 300
    resources = {"duckdb_write": 1, "zipline_ingest": 1}
    
    def requires(self):
        """Depends on both price and fundamental data."""
        return DownloadFundamentalsFMP(
            start_date=self.start_date,
            run_date=self.run_date,
        )
    
    def output(self):
        """Define task completion marker file."""
        qs_root = Path(qsconnect_root_path())
        path = qs_root / "cache" / "bundles" / f"{self.bundle_name}_{self.run_date:%Y-%m-%d}.done"
        return luigi.LocalTarget(str(path))
    
    def run(self):
        """Execute the bundle building task."""
        tmp_done = self.output().path + ".partial"
        Path(tmp_done).parent.mkdir(parents=True, exist_ok=True)
        
        try:
            logger.info(f"Building Zipline bundle: {self.bundle_name}")
            
            client = Client()
            
            # Build the bundle
            client.build_zipline_bundle(
                bundle_name=self.bundle_name,
                start_date=self.start_date,
                end_date=self.run_date,
            )
            
            # Register and ingest
            client.register_bundle(self.bundle_name)
            client.ingest_bundle(self.bundle_name)
            
            # Mark success
            Path(tmp_done).touch()
            os.rename(tmp_done, self.output().path)
            
            logger.info(f"Bundle '{self.bundle_name}' built and ingested successfully")
            
            client.close()
            
        except Exception as e:
            logger.error(f"Bundle building failed: {e}")
            if os.path.exists(tmp_done):
                os.remove(tmp_done)
            raise


# =============================================================================
# 4. Run Backtest Task
# =============================================================================

class RunBacktest(luigi.Task):
    """
    Task to run the backtesting strategy.
    
    Executes the configured strategy and logs results to MLflow.
    """
    
    start_date = luigi.DateParameter()
    run_date = luigi.DateParameter()
    
    retry_count = 1
    retry_delay = 300
    
    def requires(self):
        """Depends on the Zipline bundle being built."""
        return BuildZiplineBundle(
            start_date=self.start_date,
            run_date=self.run_date,
        )
    
    def output(self):
        """Define task output - the backtest results pickle file."""
        qs_root = Path(qsconnect_root_path())
        path = qs_root / "outputs" / "backtests" / f"backtest_{self.run_date:%Y-%m-%d}.done"
        return luigi.LocalTarget(str(path))
    
    def run(self):
        """Execute the backtest."""
        tmp_done = self.output().path + ".partial"
        Path(tmp_done).parent.mkdir(parents=True, exist_ok=True)
        
        try:
            logger.info(f"Running backtest for {self.run_date}")
            
            from qsresearch.backtest.run_backtest import run_backtest
            from qsresearch.strategies.factor.config import MOMENTUM_FACTOR_CONFIG
            
            # Run the backtest
            results = run_backtest(
                config=MOMENTUM_FACTOR_CONFIG,
                log_to_mlflow=True,
            )
            
            # Mark success
            Path(tmp_done).touch()
            os.rename(tmp_done, self.output().path)
            
            logger.info("Backtest completed successfully")
            
        except Exception as e:
            logger.error(f"Backtest failed: {e}")
            if os.path.exists(tmp_done):
                os.remove(tmp_done)
            raise


# =============================================================================
# 5. Execute Trades Task
# =============================================================================

class ExecuteTrades(luigi.Task):
    """
    Task to execute trades based on backtest results.
    
    Uses Omega to send orders to Interactive Brokers.
    """
    
    start_date = luigi.DateParameter()
    run_date = luigi.DateParameter()
    paper_trading = luigi.BoolParameter(default=True)
    
    def requires(self):
        """Depends on backtest being complete."""
        return RunBacktest(
            start_date=self.start_date,
            run_date=self.run_date,
        )
    
    def output(self):
        """Define task completion marker."""
        qs_root = Path(qsconnect_root_path())
        path = qs_root / "outputs" / "trades" / f"trades_{self.run_date:%Y-%m-%d}.done"
        return luigi.LocalTarget(str(path))
    
    def run(self):
        """Execute the trades."""
        tmp_done = self.output().path + ".partial"
        Path(tmp_done).parent.mkdir(parents=True, exist_ok=True)
        
        try:
            logger.info(f"Executing trades for {self.run_date}")
            
            # Import Omega trading app
            from omega.trading_app import TradingApp
            from omega.utils.omega_trades_converter import omega_trades_from_zipline
            
            # Load backtest results
            import pickle
            qs_root = Path(qsconnect_root_path())
            backtest_path = qs_root / "outputs" / "backtests" / f"backtest_{self.run_date:%Y-%m-%d}.pkl"
            
            with open(backtest_path, "rb") as f:
                backtest_results = pickle.load(f)
            
            # Initialize trading app
            app = TradingApp(paper_trading=self.paper_trading)
            
            # Get current positions
            current_positions = app.get_positions()
            
            # Get target positions from backtest
            target_positions = backtest_results.get("positions", [])
            
            # Convert to Omega orders
            orders = omega_trades_from_zipline(
                current_positions=current_positions,
                target_positions=target_positions,
            )
            
            # Execute orders
            for order in orders:
                app.submit_order(order)
            
            # Mark success
            Path(tmp_done).touch()
            os.rename(tmp_done, self.output().path)
            
            logger.info(f"Executed {len(orders)} trades successfully")
            
            app.disconnect()
            
        except Exception as e:
            logger.error(f"Trade execution failed: {e}")
            if os.path.exists(tmp_done):
                os.remove(tmp_done)
            raise


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    # Run the full pipeline
    luigi.run([
        "ExecuteTrades",
        "--start-date", "2000-01-01",
        "--run-date", date.today().isoformat(),
        "--local-scheduler",
    ])
