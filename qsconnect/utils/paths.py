"""
QS Connect - Path Utilities

Utility functions for path management.
"""

from pathlib import Path

from config.settings import get_settings


def qsconnect_root() -> Path:
    """Get the QS Connect root path (cache directory)."""
    return get_settings().cache_dir


def get_cache_path() -> Path:
    """Get the cache directory path."""
    return get_settings().cache_dir


def get_db_path() -> Path:
    """Get the database file path."""
    return get_settings().duckdb_path


def get_bundle_path() -> Path:
    """Get the Zipline bundle directory path."""
    return Path.home() / ".zipline" / "custom_bundles"
