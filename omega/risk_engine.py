import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from loguru import logger
from datetime import datetime

class RiskManager:
    """
    Centralized Risk Engine for QuantHedgeFund.
    Enforces portfolio-wide constraints and execution safety.
    """
    
    def __init__(self, limits_path: Optional[Path] = None):
        if limits_path is None:
            limits_path = Path(__file__).parent.parent / "config" / "risk_limits.yaml"
        
        self.limits_path = limits_path
        self.limits: Dict[str, Any] = {}
        self.load_limits()

    def load_limits(self):
        """Load risk limits from YAML."""
        try:
            with open(self.limits_path, 'r') as f:
                self.limits = yaml.safe_load(f)
                logger.info("Risk Manager initialized with centralized limits")
        except Exception as e:
            logger.error(f"Failed to load risk limits from {self.limits_path}: {e}")
            self.limits = {}

    def validate_order(
        self, 
        symbol: str, 
        asset_class: str,
        side: str, 
        quantity: float, 
        price: float, 
        portfolio_value: float,
        current_positions: List[Dict[str, Any]],
        account_info: Dict[str, Any]
    ) -> (bool, str):
        """
        Comprehensive pre-trade check.
        
        Returns:
            (is_valid, reason)
        """
        if not self.limits:
            return False, "Risk limits not loaded"

        order_value = abs(quantity * price)
        
        # 1. Execution Authority Check
        authority = self.limits.get("EXECUTION_AUTHORITY", {})
        allowed_classes = []
        for broker, classes in authority.items():
            if broker != "NONE":
                allowed_classes.extend(classes)
        
        if asset_class not in allowed_classes:
            return False, f"Execution not allowed for asset class: {asset_class}"

        # 2. Daily Loss Limit (Placeholder for real PnL tracking)
        # In production, this would query the DB for today's realized/unrealized PnL
        daily_loss_limit = self.limits.get("GLOBAL_LIMITS", {}).get("daily_loss_limit_usd", 0)
        # current_drawdown = ... (query DB)
        # if current_drawdown > daily_loss_limit: return False, "Daily loss limit exceeded"

        # 3. Individual Symbol Exposure
        symbol_limit_pct = self.limits.get("GLOBAL_LIMITS", {}).get("max_symbol_exposure_pct", 0.1)
        
        # Calculate existing position value for this symbol
        existing_value = 0.0
        for pos in current_positions:
            if pos["symbol"] == symbol:
                existing_value = pos["market_value"]
        
        new_symbol_value = abs(existing_value + (order_value if side == "BUY" else -order_value))
        symbol_exposure = new_symbol_value / portfolio_value
        
        if symbol_exposure > symbol_limit_pct:
            return False, f"Symbol exposure {symbol_exposure:.1%} exceeds limit {symbol_limit_pct:.1%}"

        # 4. Asset Class Exposure Check
        ac_limits = self.limits.get("ASSET_CLASS_LIMITS", {}).get(asset_class, {})
        ac_limit_pct = ac_limits.get("max_total_exposure_pct", 1.0)
        
        ac_total_value = order_value
        for pos in current_positions:
            # Note: positions would need to be tagged with asset_class in a real system
            # or looked up from the registry. Assuming for now we can filter by symbol prefix or registry
            from config.registry import get_registry
            reg = get_registry()
            if reg.get_asset_class(pos["symbol"]) == asset_class:
                ac_total_value += abs(pos["market_value"])
        
        ac_exposure = ac_total_value / portfolio_value
        if ac_exposure > ac_limit_pct:
            return False, f"Asset class {asset_class} exposure {ac_exposure:.1%} exceeds limit {ac_limit_pct:.1%}"

        # 5. Leverage Check
        max_leverage = self.limits.get("GLOBAL_LIMITS", {}).get("max_total_leverage", 2.0)
        gross_value = account_info.get("GrossPositionValue", 0.0) + order_value
        leverage = gross_value / portfolio_value
        
        if leverage > max_leverage:
            return False, f"Portfolio leverage {leverage:.2f} exceeds limit {max_leverage}"

        return True, "Risk validation passed"

    def get_volatility_adjusted_size(self, portfolio_value: float, price: float, atr: float, risk_per_trade_pct: float = 0.01) -> int:
        """
        Calculates position size based on ATR (Average True Range).
        Risk 1% of equity per 'N' (ATR unit).
        """
        if atr <= 0:
            return 0
        
        risk_amount = portfolio_value * risk_per_trade_pct
        shares = int(risk_amount / (atr * price)) # Simplistic sizing logic
        return shares
