"""
TIP-Search Model Wrapper.

This module defines the wrapper class for models to be used with the TIP-Search scheduler.
It encapsulates the model prediction logic along with its latency profile and accuracy estimator.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Protocol
import time
from loguru import logger
from qsresearch.realtime.tasks import InferenceTask


class ModelInterface(Protocol):
    """Protocol that any model must follow."""
    def predict(self, input_data: Any) -> Any:
        ...


class ModelWrapper:
    """
    Wraps a predictive model with metadata required for TIP-Search scheduling.
    
    Attributes:
        name: Human-readable model name
        model: The actual model instance (sklearn, torch, etc.)
        p99_latency_ns: Profiled 99th percentile inference latency in nanoseconds
        base_accuracy: Baseline accuracy/score (0.0 to 1.0)
    """
    
    def __init__(
        self, 
        name: str, 
        model: Any, 
        p99_latency_ns: int, 
        base_accuracy: float = 0.5
    ):
        self.name = name
        self.model = model
        self.p99_latency_ns = p99_latency_ns
        self.base_accuracy = base_accuracy
        
    def predict(self, task: InferenceTask) -> Any:
        """
        Execute inference on the task.
        
        Args:
            task: The inference task containing features
            
        Returns:
            Model prediction
        """
        # In a real low-latency system, we might want to measure actual runtime here
        return self.model.predict(task.features)
        
    def estimated_accuracy(self, task: InferenceTask) -> float:
        """
        Estimate the accuracy of this model for the specific task.
        
        In the basic TIP-Search implementation, this returns the static base accuracy.
        Advanced implementations could use a secondary lightweight model to estimate 
        confidence based on input features or domain.
        
        Args:
            task: The inference task
            
        Returns:
            Estimated accuracy score (higher is better)
        """
        # TODO: Implement dynamic accuracy estimation based on task.domain or features
        return self.base_accuracy
        
    def check_deadline(self, task: InferenceTask) -> bool:
        """
        Check if the model can process the task within the deadline.
        
        Uses the profiled P99 latency to be conservative/robust.
        
        Args:
            task: The inference task
            
        Returns:
            True if expected completion time <= deadline
        """
        # We use current time to account for scheduling overhead already spent
        current_time = time.monotonic_ns()
        expected_completion_time = current_time + self.p99_latency_ns
        return expected_completion_time <= task.deadline_ns
