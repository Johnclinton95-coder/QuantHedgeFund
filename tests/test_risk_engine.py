import pytest
from pathlib import Path
from omega.risk_engine import RiskManager

@pytest.fixture
def risk_mgr(tmp_path):
    # Create a temporary risk limits file
    limits_file = tmp_path / "risk_limits.yaml"
    limits_file.write_text("""
GLOBAL_LIMITS:
  max_total_leverage: 2.0
  max_symbol_exposure_pct: 0.2
ASSET_CLASS_LIMITS:
  EQUITY: {max_total_exposure_pct: 0.5}
  CRYPTO: {max_total_exposure_pct: 0.05}
EXECUTION_AUTHORITY:
  IBKR: [EQUITY]
  NONE: [CRYPTO]
""")
    return RiskManager(limits_path=limits_file)

def test_execution_authority(risk_mgr):
    # Valid: EQUITY is in IBKR authority
    is_valid, reason = risk_mgr.validate_order(
        "AAPL", "EQUITY", "BUY", 10, 200, 100000, [], {"GrossPositionValue": 0}
    )
    assert is_valid
    
    # Invalid: CRYPTO is in NONE authority
    is_valid, reason = risk_mgr.validate_order(
        "BTC/USD", "CRYPTO", "BUY", 1, 40000, 100000, [], {"GrossPositionValue": 0}
    )
    assert not is_valid
    assert "Execution not allowed" in reason

def test_symbol_exposure_limit(risk_mgr):
    # 25% exposure (Limit is 20%)
    is_valid, reason = risk_mgr.validate_order(
        "AAPL", "EQUITY", "BUY", 125, 200, 100000, [], {"GrossPositionValue": 0}
    )
    assert not is_valid
    assert "Symbol exposure" in reason

def test_leverage_limit(risk_mgr):
    # Gross value 220k on 100k portfolio (2.2x leverage, limit 2.0x)
    is_valid, reason = risk_mgr.validate_order(
        "AAPL", "EQUITY", "BUY", 100, 200, 100000, [], {"GrossPositionValue": 200000}
    )
    assert not is_valid
    assert "leverage" in reason

def test_asset_class_limit(risk_mgr):
    # Setup: Already have 40% in other EQUITY symbols
    current_pos = [
        {"symbol": "MSFT", "market_value": 20000}, # 20%
        {"symbol": "GOOGL", "market_value": 20000} # 20%
    ]
    
    # Try to add 20% more in AAPL (Total 60%, Class Limit 50%)
    is_valid, reason = risk_mgr.validate_order(
        "AAPL", "EQUITY", "BUY", 100, 200, 100000, current_pos, {"GrossPositionValue": 40000}
    )
    assert not is_valid
    assert "Asset class EQUITY exposure" in reason
