"""
TIP-Search Simulation Script.

This script demonstrates the TIP-Search scheduler in action by simulating a stream 
of market tasks with varying deadlines and observing model selection behavior.
"""

import time
import random
import numpy as np
import pandas as pd
from loguru import logger
from typing import List

import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from qsresearch.realtime import InferenceTask, ModelWrapper, TIPSearchScheduler

# Mock Models
class MockPredictor:
    def __init__(self, name):
        self.name = name
        
    def predict(self, features):
        return random.random()

def run_simulation():
    # 1. Setup Model Pool
    # Profile: (Name, Latency_ms, Accuracy)
    # Fast: 1ms, 60% acc
    # Medium: 5ms, 75% acc
    # Slow: 15ms, 85% acc
    
    models = [
        ModelWrapper("Fast-CNN", MockPredictor("fast"), p99_latency_ns=1_000_000, base_accuracy=0.60),
        ModelWrapper("Medium-LSTM", MockPredictor("med"), p99_latency_ns=5_000_000, base_accuracy=0.75),
        ModelWrapper("Slow-Transformer", MockPredictor("slow"), p99_latency_ns=15_000_000, base_accuracy=0.85),
    ]
    
    scheduler = TIPSearchScheduler(models)
    
    logger.info("Initialized TIP-Search Scheduler with models:")
    for m in models:
        logger.info(f" - {m.name}: {m.p99_latency_ns/1e6}ms latency, {m.base_accuracy:.1%} accuracy")
        
    # 2. Simulate Task Stream
    n_tasks = 20
    results = []
    
    logger.info(f"\nStarting simulation of {n_tasks} tasks...")
    print(f"{'Task ID':<10} | {'Budget (ms)':<12} | {'Selected Model':<20} | {'Exp. Acc':<10} | {'Status'}")
    print("-" * 75)
    
    for i in range(n_tasks):
        # Generate random deadline budget between 2ms and 20ms
        budget_ms = random.uniform(2, 25) 
        budget_ns = int(budget_ms * 1_000_000)
        
        arrival_time = time.monotonic_ns()
        deadline = arrival_time + budget_ns
        
        task = InferenceTask(
            task_id=f"T-{i:03d}",
            symbol="AAPL",
            features=np.random.rand(10, 10),
            arrival_ns=arrival_time,
            deadline_ns=deadline
        )
        
        # Schedule
        selected_model = scheduler.schedule(task)
        
        # Record result
        if selected_model:
            status = "✅ Scheduled"
            model_name = selected_model.name
            acc = selected_model.base_accuracy
        else:
            status = "❌ VIOLATION"
            model_name = "None"
            acc = 0.0
            
        results.append({
            "budget_ms": budget_ms,
            "model": model_name,
            "success": selected_model is not None
        })
        
        print(f"{task.task_id:<10} | {budget_ms:<12.1f} | {model_name:<20} | {acc:<10.2f} | {status}")
        
        # Simulate processing time slightly
        time.sleep(0.01)

    # 3. Analyze Results
    df = pd.DataFrame(results)
    success_rate = df["success"].mean()
    
    print("\nSimulation Summary")
    print("==================")
    print(f"Total Tasks: {n_tasks}")
    print(f"Success Rate: {success_rate:.1%}")
    print("\nModel Selection Distribution:")
    print(df["model"].value_counts())
    
    # Validation logic
    # Tighter budgets should favor Fast/Medium models
    # Looser budgets should favor Slow models
    
    low_budget = df[df["budget_ms"] < 6]
    high_budget = df[df["budget_ms"] > 16]
    
    print("\nValidation Checks:")
    if not low_budget.empty:
        fast_usage = (low_budget["model"] == "Fast-CNN").mean()
        print(f"- Low budget (<6ms) used Fast-CNN: {fast_usage:.1%} (Expected ~100%)")
        
    if not high_budget.empty:
        slow_usage = (high_budget["model"] == "Slow-Transformer").mean()
        print(f"- High budget (>16ms) used Slow-Transformer: {slow_usage:.1%} (Expected ~100%)")

if __name__ == "__main__":
    run_simulation()
