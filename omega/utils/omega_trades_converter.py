"""
Omega - Zipline Trade Converter

Converts Zipline backtest orders to Omega trade format.
"""

from typing import List, Dict, Any
from loguru import logger


def omega_trades_from_zipline(
    current_positions: List[Dict[str, Any]],
    target_positions: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Convert Zipline backtest positions to Omega orders.
    
    Compares current positions with target positions and generates
    the orders needed to rebalance the portfolio.
    
    Args:
        current_positions: List of current position dicts
            Each should have: symbol, quantity
        target_positions: List of target position dicts
            Each should have: symbol, weight
            
    Returns:
        List of order dictionaries for Omega
    """
    orders = []
    
    # Create lookup for current positions
    current_map = {p["symbol"]: p for p in current_positions}
    target_map = {p["symbol"]: p for p in target_positions}
    
    # Find positions to liquidate (in current but not in target)
    for symbol in current_map:
        if symbol not in target_map:
            orders.append({
                "symbol": symbol,
                "side": "SELL",
                "quantity": current_map[symbol]["quantity"],
                "order_type": "MKT",
                "action": "LIQUIDATE",
            })
            logger.info(f"Liquidating position: {symbol}")
    
    # Find positions to adjust or open
    for symbol, target in target_map.items():
        target_weight = target.get("weight", 0)
        
        if target_weight > 0:
            orders.append({
                "symbol": symbol,
                "side": "BUY",
                "target_percent": target_weight,
                "order_type": "MKT",
                "action": "REBALANCE",
            })
    
    logger.info(f"Generated {len(orders)} orders from Zipline positions")
    
    return orders


def extract_orders_from_performance(
    performance_df,
    date_column: str = "date",
) -> List[Dict[str, Any]]:
    """
    Extract orders from Zipline performance DataFrame.
    
    The Zipline performance output contains an 'orders' column
    with the trades executed each day.
    
    Args:
        performance_df: Zipline performance DataFrame
        date_column: Name of date column
        
    Returns:
        List of order dictionaries
    """
    if "orders" not in performance_df.columns:
        logger.warning("No 'orders' column in performance DataFrame")
        return []
    
    # Get the most recent day's orders
    latest_row = performance_df.iloc[-1]
    orders_list = latest_row.get("orders", [])
    
    if not orders_list:
        logger.info("No orders for the latest trading day")
        return []
    
    orders = []
    for order in orders_list:
        orders.append({
            "symbol": order.get("sid", {}).get("symbol", ""),
            "quantity": order.get("amount", 0),
            "side": "BUY" if order.get("amount", 0) > 0 else "SELL",
            "order_type": "MKT",
            "filled": order.get("filled", 0),
            "commission": order.get("commission", 0),
        })
    
    logger.info(f"Extracted {len(orders)} orders from performance")
    
    return orders
