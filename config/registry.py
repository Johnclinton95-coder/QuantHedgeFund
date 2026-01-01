import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from loguru import logger

class AssetRegistry:
    """Helper to load and query the config/assets.yaml file."""
    
    def __init__(self, config_path: Optional[Path] = None):
        if config_path is None:
            config_path = Path(__file__).parent / "assets.yaml"
        
        self.config_path = config_path
        self.assets: Dict[str, Any] = {}
        self.load()

    def load(self):
        """Load assets from YAML."""
        try:
            with open(self.config_path, 'r') as f:
                data = yaml.safe_load(f)
                self.assets = data.get("ASSETS", {})
                logger.info(f"Loaded {len(self.assets)} symbols from Asset Registry")
        except Exception as e:
            logger.error(f"Failed to load Asset Registry from {self.config_path}: {e}")
            self.assets = {}

    def get_asset(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Retrieve config for a specific symbol."""
        return self.assets.get(symbol)

    def is_tradable(self, symbol: str) -> bool:
        """Check if execution is allowed for this symbol."""
        asset = self.get_asset(symbol)
        if not asset:
            return False
        return asset.get("execution") == "IBKR"

    def get_feed_source(self, symbol: str) -> str:
        """Get the primary real-time feed source."""
        asset = self.get_asset(symbol)
        return asset.get("realtime_feed", "UNKNOWN") if asset else "UNKNOWN"

    def get_asset_class(self, symbol: str) -> str:
        """Get the asset class (EQUITY, FX, etc)."""
        asset = self.get_asset(symbol)
        return asset.get("asset_class", "UNKNOWN") if asset else "UNKNOWN"

# Singleton instance
_registry = None

def get_registry() -> AssetRegistry:
    global _registry
    if _registry is None:
        _registry = AssetRegistry()
    return _registry
