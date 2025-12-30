"""
TIP-Search Scheduler Implementation.

This module implements the Time-Predictable Inference Scheduling (TIP-Search) algorithm
as described in arXiv:2506.08026.
"""

from typing import List, Optional
import time
from loguru import logger

from qsresearch.realtime.tasks import InferenceTask
from qsresearch.realtime.models import ModelWrapper


class TIPSearchScheduler:
    """
    Implements the TIP-Search scheduling policy.
    
    The scheduler filters models based on deadline constraints and selects 
    the one with the highest expected accuracy.
    """
    
    def __init__(self, models: List[ModelWrapper]):
        """
        Initialize the scheduler with a pool of available models.
        
        Args:
            models: List of available ModelWrapper instances
        """
        self.models = models
        self.validate_pool()
        
    def validate_pool(self):
        """Ensure the model pool is valid (e.g., at least one model)."""
        if not self.models:
            logger.warning("TIP-Search Scheduler initialized with empty model pool!")
        
        # Sort models by latency (fastest first) for easier debugging/fallback
        self.models.sort(key=lambda m: m.p99_latency_ns)
        
    def schedule(self, task: InferenceTask) -> Optional[ModelWrapper]:
        """
        Select the best model for the given task.
        
        Algorithm 1 (TIP-Search):
        1. Identify set F(ti) of models where Latency <= Deadline - CurrentTime
        2. If F(ti) is empty, return None (or fallback)
        3. Return model in F(ti) with max estimated accuracy
        
        Args:
            task: The inference task to schedule
            
        Returns:
            Selected ModelWrapper or None if no model can meet deadline
        """
        # Step 1: Filter eligible models
        eligible_models = []
        current_time = time.monotonic_ns()
        
        for model in self.models:
            # Check feasibility: current_time + latency <= deadline
            if current_time + model.p99_latency_ns <= task.deadline_ns:
                eligible_models.append(model)
                
        # Step 2: Handle no solution
        if not eligible_models:
            logger.warning(f"Deadline violation! No model can meet deadline for task {task.task_id}")
            return None
            
        # Step 3: Select expected best model
        # We want the model with the highest estimated accuracy
        selected_model = max(eligible_models, key=lambda m: m.estimated_accuracy(task))
        
        return selected_model

    def get_fastest_model(self) -> Optional[ModelWrapper]:
        """Return the fastest model (fallback)."""
        return self.models[0] if self.models else None
