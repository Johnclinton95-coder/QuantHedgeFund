"""
QS Connect - Cache Manager

Manages parquet file caching for efficient data storage and retrieval.
"""

from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, date
import os

import polars as pl
import pandas as pd
from loguru import logger


class CacheManager:
    """
    Manages parquet file caching for API responses.
    
    Features:
    - Automatic caching of API responses
    - Delta detection for incremental updates
    - Cache invalidation and cleanup
    """
    
    def __init__(self, cache_dir: Path):
        """
        Initialize cache manager.
        
        Args:
            cache_dir: Directory for cached parquet files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        self.fmp_cache_dir = self.cache_dir / "fmp"
        self.fmp_cache_dir.mkdir(exist_ok=True)
        
        logger.info(f"Cache manager initialized: {self.cache_dir}")
    
    def _get_cache_path(self, key: str) -> Path:
        """Get the file path for a cache key."""
        # Sanitize key for filename
        safe_key = key.replace("/", "_").replace(":", "_").replace(" ", "_")
        return self.fmp_cache_dir / f"{safe_key}.parquet"
    
    def get(self, key: str) -> Optional[pl.DataFrame]:
        """
        Get cached data for a key.
        
        Args:
            key: Cache key
            
        Returns:
            Polars DataFrame if cached, None otherwise
        """
        cache_path = self._get_cache_path(key)
        
        if cache_path.exists():
            try:
                df = pl.read_parquet(cache_path)
                logger.debug(f"Cache hit for key: {key}")
                return df
            except Exception as e:
                logger.warning(f"Failed to read cache for key {key}: {e}")
                return None
        
        logger.debug(f"Cache miss for key: {key}")
        return None
    
    def set(self, key: str, data: pl.DataFrame) -> bool:
        """
        Cache data for a key.
        
        Args:
            key: Cache key
            data: Polars DataFrame to cache
            
        Returns:
            True if successful, False otherwise
        """
        cache_path = self._get_cache_path(key)
        
        try:
            data.write_parquet(cache_path)
            logger.info(f"Cached data for key '{key}' to {cache_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to cache data for key {key}: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Check if a cache entry exists."""
        return self._get_cache_path(key).exists()
    
    def delete(self, key: str) -> bool:
        """Delete a cache entry."""
        cache_path = self._get_cache_path(key)
        
        if cache_path.exists():
            cache_path.unlink()
            logger.info(f"Deleted cache for key: {key}")
            return True
        return False
    
    def list_cached_files(self) -> pd.DataFrame:
        """
        List all cached parquet files.
        
        Returns:
            DataFrame with file information
        """
        files = []
        
        for filepath in self.fmp_cache_dir.glob("*.parquet"):
            stat = filepath.stat()
            files.append({
                "filename": filepath.name,
                "path": str(filepath),
                "size_mb": stat.st_size / (1024 * 1024),
                "modified": datetime.fromtimestamp(stat.st_mtime),
                "key": filepath.stem,
            })
        
        return pd.DataFrame(files)
    
    def detect_missing(
        self,
        statement_type: List[str],
        periods: str = "all",
        start_year: int = 2000,
        end_year: Optional[int] = None,
    ) -> List[str]:
        """
        Detect which cache files are missing for incremental download.
        
        Args:
            statement_type: List of statement types
            periods: Period type (annual, quarter, all)
            start_year: Start year
            end_year: End year
            
        Returns:
            List of missing cache keys
        """
        if end_year is None:
            end_year = datetime.now().year
        
        missing = []
        period_list = ["annual", "quarter"] if periods == "all" else [periods]
        
        for stmt in statement_type:
            for period in period_list:
                for year in range(start_year, end_year + 1):
                    key = f"bulk-{stmt}_{year}_{period}-{date.today().isoformat()}"
                    if not self.exists(key):
                        missing.append(key)
        
        return missing
    
    def cleanup_old_cache(self, days: int = 30) -> int:
        """
        Remove cache files older than specified days.
        
        Args:
            days: Age threshold in days
            
        Returns:
            Number of files deleted
        """
        threshold = datetime.now().timestamp() - (days * 24 * 60 * 60)
        deleted = 0
        
        for filepath in self.fmp_cache_dir.glob("*.parquet"):
            if filepath.stat().st_mtime < threshold:
                filepath.unlink()
                deleted += 1
        
        if deleted > 0:
            logger.info(f"Cleaned up {deleted} old cache files")
        
        return deleted
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        files = list(self.fmp_cache_dir.glob("*.parquet"))
        total_size = sum(f.stat().st_size for f in files)
        
        return {
            "num_files": len(files),
            "total_size_mb": total_size / (1024 * 1024),
            "cache_dir": str(self.cache_dir),
        }
