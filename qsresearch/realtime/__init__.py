"""
QS Research Real-Time Module.

Implements the TIP-Search framework for deadline-aware inference scheduling.
"""

from qsresearch.realtime.tasks import InferenceTask
from qsresearch.realtime.models import ModelWrapper
from qsresearch.realtime.scheduler import TIPSearchScheduler

__all__ = ["InferenceTask", "ModelWrapper", "TIPSearchScheduler"]
