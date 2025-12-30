"""
Omega - Trading Application

Main trading application for executing trades via Interactive Brokers.
"""

from typing import Optional, List, Dict, Any
from loguru import logger

from config.settings import get_settings


class TradingApp:
    """
    Main trading application for Omega.
    
    Provides interface to Interactive Brokers for:
    - Account management
    - Position tracking
    - Order execution
    - Market data retrieval
    
    Example:
        >>> from omega import TradingApp
        >>> app = TradingApp()
        >>> positions = app.get_positions()
        >>> app.order_target_percent("AAPL", 0.05)
    """
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        client_id: Optional[int] = None,
        paper_trading: bool = True,
    ):
        """
        Initialize the trading application.
        
        Args:
            host: IB Gateway host (default from settings)
            port: IB Gateway port (default from settings)
            client_id: Client ID for connection
            paper_trading: Whether to use paper trading mode
        """
        settings = get_settings()
        
        self.host = host or settings.ib_host
        self.port = port or settings.ib_port
        self.client_id = client_id or settings.ib_client_id
        self.paper_trading = paper_trading
        
        self._connected = False
        self._ib = None
        
        logger.info(
            f"TradingApp initialized: {self.host}:{self.port} "
            f"(paper={self.paper_trading})"
        )
    
    # =====================
    # Connection Management
    # =====================
    
    def connect(self) -> bool:
        """
        Connect to Interactive Brokers.
        
        Returns:
            True if connection successful
        """
        try:
            from ib_insync import IB
            
            self._ib = IB()
            self._ib.connect(
                host=self.host,
                port=self.port,
                clientId=self.client_id,
            )
            
            self._connected = True
            logger.info("Connected to Interactive Brokers")
            return True
            
        except ImportError:
            logger.error("ib_insync not installed. Run: pip install ib_insync")
            return False
            
        except Exception as e:
            logger.error(f"Failed to connect to IB: {e}")
            return False
    
    def disconnect(self) -> None:
        """Disconnect from Interactive Brokers."""
        if self._ib and self._connected:
            self._ib.disconnect()
            self._connected = False
            logger.info("Disconnected from Interactive Brokers")
    
    def is_connected(self) -> bool:
        """Check if connected to IB."""
        return self._connected and self._ib and self._ib.isConnected()
    
    # =====================
    # Account Information
    # =====================
    
    def get_account_info(self) -> Dict[str, Any]:
        """
        Get account information.
        
        Returns:
            Dictionary with account values
        """
        if not self.is_connected():
            self.connect()
        
        account_values = self._ib.accountValues()
        
        info = {}
        for av in account_values:
            if av.tag in ["NetLiquidation", "TotalCashValue", "BuyingPower", "GrossPositionValue"]:
                info[av.tag] = float(av.value)
        
        return info
    
    def get_portfolio_value(self) -> float:
        """Get total portfolio value."""
        info = self.get_account_info()
        return info.get("NetLiquidation", 0.0)
    
    # =====================
    # Position Management
    # =====================
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """
        Get current positions.
        
        Returns:
            List of position dictionaries
        """
        if not self.is_connected():
            self.connect()
        
        positions = []
        
        for pos in self._ib.positions():
            positions.append({
                "symbol": pos.contract.symbol,
                "quantity": pos.position,
                "avg_cost": pos.avgCost,
                "market_value": pos.position * pos.avgCost,
                "contract": pos.contract,
            })
        
        return positions
    
    def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get position for a specific symbol."""
        positions = self.get_positions()
        for pos in positions:
            if pos["symbol"] == symbol:
                return pos
        return None
    
    # =====================
    # Order Execution
    # =====================
    
    def create_contract(self, symbol: str, sec_type: str = "STK", exchange: str = "SMART") -> Any:
        """
        Create an IB contract object.
        
        Args:
            symbol: Stock symbol
            sec_type: Security type (STK, OPT, FUT, etc.)
            exchange: Exchange name
            
        Returns:
            IB Contract object
        """
        from ib_insync import Stock
        
        return Stock(symbol, exchange, "USD")
    
    def order_target_percent(
        self,
        symbol: str,
        target_percent: float,
        order_type: str = "MKT",
    ) -> Optional[Any]:
        """
        Place order to reach target portfolio percentage.
        
        This is the primary method for portfolio rebalancing.
        
        Args:
            symbol: Stock symbol
            target_percent: Target allocation (0.0 to 1.0)
            order_type: Order type (MKT, LMT)
            
        Returns:
            Order trade object
        """
        if not self.is_connected():
            self.connect()
        
        from ib_insync import MarketOrder, LimitOrder
        
        # Get portfolio value
        portfolio_value = self.get_portfolio_value()
        target_value = portfolio_value * target_percent
        
        # Get current position
        current_pos = self.get_position(symbol)
        current_value = current_pos["market_value"] if current_pos else 0.0
        
        # Calculate difference
        diff_value = target_value - current_value
        
        # Skip if difference is too small
        if abs(diff_value) < 100:  # $100 threshold
            logger.info(f"Skipping {symbol}: difference too small (${diff_value:.2f})")
            return None
        
        # Get current price for share calculation
        contract = self.create_contract(symbol)
        ticker = self._ib.reqMktData(contract)
        self._ib.sleep(1)  # Wait for price
        
        if ticker.marketPrice():
            current_price = ticker.marketPrice()
        else:
            logger.warning(f"Could not get price for {symbol}")
            return None
        
        # Calculate shares
        shares = int(diff_value / current_price)
        
        if shares == 0:
            logger.info(f"Skipping {symbol}: calculated 0 shares")
            return None
        
        # Determine order action
        action = "BUY" if shares > 0 else "SELL"
        shares = abs(shares)
        
        # Create order
        if order_type.upper() == "MKT":
            order = MarketOrder(action, shares)
        else:
            order = LimitOrder(action, shares, current_price)
        
        # Submit order
        trade = self._ib.placeOrder(contract, order)
        
        logger.info(f"Placed {action} order for {shares} shares of {symbol}")
        
        return trade
    
    def liquidate_position(self, symbol: str) -> Optional[Any]:
        """
        Liquidate entire position in a symbol.
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Order trade object
        """
        return self.order_target_percent(symbol, 0.0)
    
    def submit_order(self, order: Dict[str, Any]) -> Optional[Any]:
        """
        Submit a pre-built order dictionary.
        
        Args:
            order: Order specification dict
            
        Returns:
            Order trade object
        """
        symbol = order.get("symbol")
        quantity = order.get("quantity", 0)
        side = order.get("side", "BUY")
        order_type = order.get("order_type", "MKT")
        
        if not symbol or quantity == 0:
            return None
        
        if not self.is_connected():
            self.connect()
        
        from ib_insync import MarketOrder, LimitOrder
        
        contract = self.create_contract(symbol)
        
        if order_type.upper() == "MKT":
            ib_order = MarketOrder(side, abs(quantity))
        else:
            price = order.get("limit_price", 0)
            ib_order = LimitOrder(side, abs(quantity), price)
        
        trade = self._ib.placeOrder(contract, ib_order)
        
        logger.info(f"Submitted order: {side} {quantity} {symbol}")
        
        return trade
    
    # =====================
    # Order Management
    # =====================
    
    def get_open_orders(self) -> List[Dict[str, Any]]:
        """Get list of open orders."""
        if not self.is_connected():
            self.connect()
        
        orders = []
        for trade in self._ib.openTrades():
            orders.append({
                "symbol": trade.contract.symbol,
                "action": trade.order.action,
                "quantity": trade.order.totalQuantity,
                "order_type": trade.order.orderType,
                "status": trade.orderStatus.status,
            })
        
        return orders
    
    def cancel_all_orders(self) -> int:
        """
        Cancel all open orders.
        
        Returns:
            Number of orders cancelled
        """
        if not self.is_connected():
            self.connect()
        
        open_trades = self._ib.openTrades()
        
        for trade in open_trades:
            self._ib.cancelOrder(trade.order)
        
        logger.info(f"Cancelled {len(open_trades)} orders")
        return len(open_trades)
    
    # =====================
    # Market Data
    # =====================
    
    def get_quote(self, symbol: str) -> Dict[str, float]:
        """
        Get current quote for a symbol.
        
        Returns:
            Dictionary with bid, ask, last, volume
        """
        if not self.is_connected():
            self.connect()
        
        contract = self.create_contract(symbol)
        ticker = self._ib.reqMktData(contract)
        self._ib.sleep(1)
        
        return {
            "bid": ticker.bid or 0.0,
            "ask": ticker.ask or 0.0,
            "last": ticker.last or 0.0,
            "volume": ticker.volume or 0,
        }
