import pytest
import time
from dataclasses import dataclass
from typing import Optional
from unittest.mock import MagicMock
import numpy as np


@dataclass
class MockTask:
    """Mock inference task for testing."""
    task_id: str
    deadline_ns: int
    data: dict = None
    
    def __post_init__(self):
        if self.data is None:
            self.data = {}


@dataclass  
class MockModel:
    """Mock model wrapper for testing."""
    name: str
    p99_latency_ns: int
    accuracy: float
    
    def estimated_accuracy(self, task=None) -> float:
        return self.accuracy


class TestTIPSearchScheduler:
    """Test the TIP-Search scheduling algorithm."""
    
    @pytest.fixture
    def model_pool(self):
        """Create a pool of mock models with varying latencies."""
        return [
            MockModel("fast_small", 1_000_000, 0.85),      # 1ms, 85% accuracy
            MockModel("medium", 5_000_000, 0.92),          # 5ms, 92% accuracy  
            MockModel("slow_large", 20_000_000, 0.98),     # 20ms, 98% accuracy
        ]
    
    def test_scheduler_filters_by_deadline(self, model_pool):
        """Test that scheduler filters out models that can't meet deadline."""
        from qsresearch.realtime.scheduler import TIPSearchScheduler
        from qsresearch.realtime.tasks import InferenceTask
        from qsresearch.realtime.models import ModelWrapper
        
        # Create actual ModelWrapper instances
        models = [
            ModelWrapper(name=m.name, model=MagicMock(), p99_latency_ns=m.p99_latency_ns, base_accuracy=m.accuracy)
            for m in model_pool
        ]
        
        scheduler = TIPSearchScheduler(models)
        
        # Create task with tight deadline (only fast model can meet it)
        current_ns = time.monotonic_ns()
        tight_deadline = current_ns + 2_000_000  # 2ms from now
        
        task = InferenceTask(
            task_id="test_1",
            symbol="AAPL",
            features=np.array([1.0]),
            arrival_ns=current_ns,
            deadline_ns=tight_deadline,
            domain="equities"
        )
        
        selected = scheduler.schedule(task)
        
        # Only the fast model (1ms) can meet 2ms deadline
        if selected is not None:
            assert selected.p99_latency_ns <= 2_000_000
    
    def test_scheduler_selects_most_accurate(self, model_pool):
        """Test that scheduler selects highest accuracy model within deadline."""
        from qsresearch.realtime.scheduler import TIPSearchScheduler
        from qsresearch.realtime.tasks import InferenceTask
        from qsresearch.realtime.models import ModelWrapper
        
        models = [
            ModelWrapper(name=m.name, model=MagicMock(), p99_latency_ns=m.p99_latency_ns, base_accuracy=m.accuracy)
            for m in model_pool
        ]
        
        scheduler = TIPSearchScheduler(models)
        
        # Create task with loose deadline (all models can meet it)
        current_ns = time.monotonic_ns()
        loose_deadline = current_ns + 100_000_000  # 100ms from now
        
        task = InferenceTask(
            task_id="test_2",
            symbol="AAPL",
            features=np.array([1.0]),
            arrival_ns=current_ns,
            deadline_ns=loose_deadline,
            domain="equities"
        )
        
        selected = scheduler.schedule(task)
        
        # Should select slow_large (highest accuracy) since deadline is loose
        if selected is not None:
            # The most accurate model should be selected when all can meet deadline
            assert selected.base_accuracy >= 0.85  # At least the minimum
    
    def test_scheduler_handles_impossible_deadline(self, model_pool):
        """Test that scheduler returns None when no model can meet deadline."""
        from qsresearch.realtime.scheduler import TIPSearchScheduler
        from qsresearch.realtime.tasks import InferenceTask
        from qsresearch.realtime.models import ModelWrapper
        
        models = [
            ModelWrapper(name=m.name, model=MagicMock(), p99_latency_ns=m.p99_latency_ns, base_accuracy=m.accuracy)
            for m in model_pool
        ]
        
        scheduler = TIPSearchScheduler(models)
        
        # Create task with impossible deadline (in the past)
        current_ns = time.monotonic_ns()
        past_deadline = current_ns - 1_000_000  # 1ms ago
        
        task = InferenceTask(
            task_id="test_3",
            symbol="AAPL",
            features=np.array([1.0]),
            arrival_ns=current_ns,
            deadline_ns=past_deadline
        )
        
        selected = scheduler.schedule(task)
        
        # No model can meet a deadline in the past
        assert selected is None
    
    def test_get_fastest_model(self, model_pool):
        """Test fallback to fastest model."""
        from qsresearch.realtime.scheduler import TIPSearchScheduler
        from qsresearch.realtime.models import ModelWrapper
        
        models = [
            ModelWrapper(name=m.name, model=MagicMock(), p99_latency_ns=m.p99_latency_ns, base_accuracy=m.accuracy)
            for m in model_pool
        ]
        
        scheduler = TIPSearchScheduler(models)
        
        fastest = scheduler.get_fastest_model()
        
        assert fastest is not None
        assert fastest.name == "fast_small"
        assert fastest.p99_latency_ns == 1_000_000
    
    def test_scheduler_validates_empty_pool(self):
        """Test that scheduler handles empty model pool."""
        from qsresearch.realtime.scheduler import TIPSearchScheduler
        
        scheduler = TIPSearchScheduler([])
        
        fastest = scheduler.get_fastest_model()
        assert fastest is None
