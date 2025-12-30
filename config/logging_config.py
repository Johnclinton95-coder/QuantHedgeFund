"""
Quant Hedge Fund - Logging Configuration

Structured logging setup using loguru for the entire system.
"""

import sys
from pathlib import Path
from loguru import logger


def setup_logging(
    log_level: str = "INFO",
    log_dir: Path = Path("./logs"),
    log_name: str = "quant_hedge_fund"
) -> None:
    """
    Configure structured logging for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_dir: Directory for log files
        log_name: Base name for log files
    """
    # Remove default handler
    logger.remove()
    
    # Console handler with color
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
               "<level>{message}</level>",
        level=log_level,
        colorize=True,
    )
    
    # Create log directory
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # File handler for all logs
    logger.add(
        log_dir / f"{log_name}.log",
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        level="DEBUG",
    )
    
    # Separate file for errors
    logger.add(
        log_dir / f"{log_name}_errors.log",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        level="ERROR",
    )
    
    logger.info(f"Logging initialized at level: {log_level}")


def get_logger(name: str):
    """Get a logger instance bound to a specific module name."""
    return logger.bind(name=name)
