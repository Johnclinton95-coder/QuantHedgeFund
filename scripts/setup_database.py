"""
Setup Database Script

Initialize the DuckDB database and required directories.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import get_settings
from config.logging_config import setup_logging
from qsconnect.database.duckdb_manager import DuckDBManager
from loguru import logger


def main():
    """Initialize the database and directories."""
    
    settings = get_settings()
    setup_logging(settings.log_level, settings.log_dir)
    
    logger.info("=" * 60)
    logger.info("QS Hedge Fund - Database Setup")
    logger.info("=" * 60)
    
    # Ensure directories exist
    settings.ensure_directories()
    logger.info(f"Created directories:")
    logger.info(f"  - Cache: {settings.cache_dir}")
    logger.info(f"  - Data: {settings.duckdb_path.parent}")
    logger.info(f"  - Logs: {settings.log_dir}")
    
    # Initialize database
    logger.info(f"Initializing DuckDB: {settings.duckdb_path}")
    
    db_manager = DuckDBManager(settings.duckdb_path)
    
    # Get database info
    info = db_manager.get_date_range()
    
    logger.info("Database initialized successfully!")
    logger.info(f"  - Symbols: {info['num_symbols']}")
    logger.info(f"  - Records: {info['num_records']}")
    
    if info['min_date']:
        logger.info(f"  - Date range: {info['min_date']} to {info['max_date']}")
    
    db_manager.close()
    
    logger.info("=" * 60)
    logger.info("Setup complete!")
    logger.info("=" * 60)
    
    print("\n✅ Database setup complete!")
    print(f"   Database: {settings.duckdb_path}")
    print("\nNext steps:")
    print("  1. Add your FMP API key to .env")
    print("  2. Run: python scripts/download_initial_data.py")


if __name__ == "__main__":
    main()
