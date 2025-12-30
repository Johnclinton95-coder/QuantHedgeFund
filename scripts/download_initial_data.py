"""
Download Initial Data Script

Downloads initial market and fundamental data.
"""

import sys
from pathlib import Path
from datetime import date

# Add parent directory to path  
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import get_settings
from config.logging_config import setup_logging
from qsconnect import Client
from loguru import logger


def main():
    """Download initial data."""
    
    settings = get_settings()
    setup_logging(settings.log_level, settings.log_dir)
    
    logger.info("=" * 60)
    logger.info("QS Hedge Fund - Initial Data Download")
    logger.info("=" * 60)
    
    # Check API key
    if not settings.fmp_api_key:
        logger.error("FMP API key not set! Add FMP_API_KEY to your .env file")
        print("\n❌ Error: FMP API key not configured")
        print("   Add FMP_API_KEY=your_key to .env file")
        return
    
    # Initialize client
    client = Client()
    
    # Download stock list
    logger.info("Downloading stock list...")
    stock_list = client.stock_list("stock")
    logger.info(f"Found {len(stock_list)} stocks")
    
    # Download historical prices
    logger.info("Downloading historical prices...")
    logger.info("This may take several minutes depending on your API tier...")
    
    try:
        prices = client.bulk_historical_prices(
            start_date=date(2015, 1, 1),
            end_date=date.today(),
        )
        logger.info(f"Downloaded {len(prices)} price records")
    except Exception as e:
        logger.error(f"Error downloading prices: {e}")
        logger.info("You may need to upgrade your FMP API plan for bulk data")
    
    # Download fundamental data (optional, takes longer)
    download_fundamentals = input("\nDownload fundamental data too? (y/n): ").lower() == 'y'
    
    if download_fundamentals:
        logger.info("Downloading fundamental data...")
        logger.info("This will take 15-30 minutes...")
        
        try:
            client.fetch_bulk_financial_statements(
                statement_type=[
                    "income-statement",
                    "balance-sheet-statement",
                    "cash-flow-statement",
                    "ratios",
                ],
                periods="all",
                start_year=2015,
                end_year=date.today().year,
                api_buffer_seconds=10,
            )
        except Exception as e:
            logger.error(f"Error downloading fundamentals: {e}")
    
    # Build Zipline bundle
    build_bundle = input("\nBuild Zipline bundle? (y/n): ").lower() == 'y'
    
    if build_bundle:
        logger.info("Building Zipline bundle...")
        try:
            client.build_zipline_bundle("historical_prices_fmp")
            logger.info("Bundle built successfully!")
        except Exception as e:
            logger.error(f"Error building bundle: {e}")
    
    client.close()
    
    logger.info("=" * 60)
    logger.info("Data download complete!")
    logger.info("=" * 60)
    
    print("\n✅ Data download complete!")
    print("\nNext steps:")
    print("  1. Run backtests: python -m qsresearch.backtest.run_backtest")
    print("  2. Launch dashboard: streamlit run dashboard/app.py")
    print("  3. Start MLflow: mlflow server --port 5050")


if __name__ == "__main__":
    main()
