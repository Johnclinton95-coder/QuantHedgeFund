"""
Quant Hedge Fund - Constants and Enums

Shared constants and enumeration types used throughout the system.
"""

from enum import Enum, auto


class DataSource(str, Enum):
    """Supported data sources for market data."""
    FMP = "fmp"  # Financial Modeling Prep
    DATALINK = "datalink"
    YAHOO = "yahoo"


class AssetType(str, Enum):
    """Types of tradeable assets."""
    STOCK = "stock"
    ETF = "etf"
    OPTION = "option"
    FUTURE = "future"
    FOREX = "forex"
    CRYPTO = "crypto"


class Exchange(str, Enum):
    """Supported exchanges."""
    NYSE = "NYSE"
    NASDAQ = "NASDAQ"
    AMEX = "AMEX"
    ARCA = "ARCA"


class OrderType(str, Enum):
    """Order types for trade execution."""
    MARKET = "MKT"
    LIMIT = "LMT"
    STOP = "STP"
    STOP_LIMIT = "STP_LMT"
    TRAILING_STOP = "TRAIL"
    MOC = "MOC"  # Market on Close
    LOC = "LOC"  # Limit on Close


class OrderSide(str, Enum):
    """Order side/direction."""
    BUY = "BUY"
    SELL = "SELL"


class PortfolioStrategy(str, Enum):
    """Portfolio construction strategies."""
    EQUAL_WEIGHT = "equal_weight"
    RISK_PARITY = "risk_parity"
    MIN_VARIANCE = "min_variance"
    MAX_SHARPE = "max_sharpe"
    LONG_SHORT = "long_short"


class FactorType(str, Enum):
    """Factor types for quantitative strategies."""
    MOMENTUM = "momentum"
    VALUE = "value"
    QUALITY = "quality"
    SIZE = "size"
    VOLATILITY = "volatility"
    GROWTH = "growth"


class StatementType(str, Enum):
    """Financial statement types."""
    INCOME = "income-statement"
    BALANCE_SHEET = "balance-sheet-statement"
    CASH_FLOW = "cash-flow-statement"
    RATIOS = "ratios"
    METRICS = "key-metrics"


class Period(str, Enum):
    """Data period frequencies."""
    ANNUAL = "annual"
    QUARTERLY = "quarter"
    DAILY = "daily"


# ===================
# Default Parameters
# ===================

# Screener defaults
DEFAULT_MIN_AVG_VOLUME = 100_000
DEFAULT_MIN_AVG_PRICE = 4.0
DEFAULT_MIN_LAST_PRICE = 5.0
DEFAULT_MAX_VOLATILITY = 0.25
DEFAULT_MAX_PERCENT_CHANGE = 0.35
DEFAULT_LOOKBACK_DAYS = 730  # 2 years

# Backtest defaults
DEFAULT_CAPITAL_BASE = 1_000_000
DEFAULT_START_DATE = "2015-01-01"
DEFAULT_NUM_LONG_POSITIONS = 20
DEFAULT_LONG_THRESHOLD = 1.0

# Momentum factor defaults
DEFAULT_MOMENTUM_FAST = 21
DEFAULT_MOMENTUM_SLOW = 252
DEFAULT_MOMENTUM_SIGNAL = 126

# Risk parameters
DEFAULT_MAX_POSITION_SIZE = 0.10  # 10% max per position
DEFAULT_MAX_SECTOR_EXPOSURE = 0.30  # 30% max per sector
DEFAULT_STOP_LOSS_PCT = 0.15  # 15% stop loss

# API rate limits
FMP_RATE_LIMIT_PER_MINUTE = 2900
