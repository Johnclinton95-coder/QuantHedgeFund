import pytest
from omega.data.candle_engine import Tick, CandleAggregator, SessionManager, Candle
from datetime import datetime
import time

class MockSessionManager(SessionManager):
    def is_in_session(self, ts: float, symbol: str) -> bool:
        return True # Always in session for tests

@pytest.fixture
def aggregator():
    return CandleAggregator(
        symbol="AAPL",
        interval_sec=60,
        session_mgr=MockSessionManager()
    )

def test_late_tick_rejection(aggregator):
    """Verify that ticks older than the last finalized bar are rejected."""
    # Bar 1: 10:00:00 (approx)
    aggregator.process_tick(Tick("AAPL", 150.0, 100, 1000.0, time.time()))
    # Bar 2 triggered by tick at 10:01:40 (1060)
    aggregator.process_tick(Tick("AAPL", 151.0, 100, 1060.0, time.time()))
    
    assert aggregator.last_finalized_ts == 1020.0
    
    # Try to process a late tick from the first bar (at 10:00:10)
    aggregator.process_tick(Tick("AAPL", 152.0, 100, 1010.0, time.time()))
    
    # If the late tick was accepted, volume would be 200. Since it should be rejected, it's 100.
    assert aggregator.current_candle.volume == 100

def test_multi_bar_gap_handling(aggregator):
    """Verify that a large jump in tick time finalizes and maintains continuity."""
    # Bar 1: 10:00:00
    aggregator.process_tick(Tick("AAPL", 100.0, 10, 1000.0, time.time()))
    
    # Jump to 10:05:00 (1300 / 60 = 21.6 -> bucket 1260)
    aggregator.process_tick(Tick("AAPL", 105.0, 10, 1300.0, time.time()))
    
    assert aggregator.last_finalized_ts == 1020.0
    assert aggregator.current_candle.start_ts == 1260.0

def test_trade_only_guard(aggregator):
    """Verify that zero-size ticks (quotes) are ignored."""
    aggregator.process_tick(Tick("AAPL", 100.0, 0, 1000.0, time.time()))
    assert aggregator.current_candle is None

def test_timestamp_quantization(aggregator):
    """Verify that slightly different timestamps in the same sub-second bucket don't jitter."""
    aggregator.process_tick(Tick("AAPL", 100.0, 10, 1000.0001, time.time()))
    aggregator.process_tick(Tick("AAPL", 100.1, 10, 1000.0002, time.time()))
    
    assert aggregator.current_candle.volume == 20
    assert aggregator.current_candle.close == 100.1
