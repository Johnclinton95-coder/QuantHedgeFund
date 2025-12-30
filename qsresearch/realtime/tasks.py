"""
TIP-Search Task Definitions.

This module defines the InferenceTask structure used by the real-time scheduler.
"""

from dataclasses import dataclass
from typing import Any, Optional
import numpy as np


@dataclass
class InferenceTask:
    """
    Represents a real-time inference task (e.g., a market data snapshot).
    
    Attributes:
        task_id: Unique identifier for the task
        symbol: Ticker symbol (e.g., "AAPL")
        features: Precomputed feature vector/tensor
        arrival_ns: Arrival timestamp in nanoseconds (monotonic)
        deadline_ns: Absolute deadline timestamp in nanoseconds (monotonic)
        domain: Optional domain label (e.g., 'crypto', 'equities') for analysis
    """
    task_id: str
    symbol: str
    features: Any  # Usually np.ndarray or torch.Tensor
    arrival_ns: int
    deadline_ns: int
    domain: Optional[str] = None
    
    @property
    def latency_budget_ns(self) -> int:
        """Return the total time budget for this task."""
        return self.deadline_ns - self.arrival_ns

    def remaining_time_ns(self, current_time_ns: int) -> int:
        """Return the time remaining until deadline."""
        return self.deadline_ns - current_time_ns
