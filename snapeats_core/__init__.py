"""Core scheduling, ETA, rush detection and analytics for Snapeats.

This package is intentionally UI-agnostic so it can be reused from
Flask/SocketIO handlers, offline simulators, or unit tests.
"""

from .domain import Order, KitchenConfig, KitchenState, OrderStatus
from .scheduling import (
    BaseScheduler,
    FIFOScheduler,
    SJFScheduler,
    PriorityScheduler,
    AdaptiveHybridScheduler,
)
from .eta import SlidingWindowETAPredictor
from .rush_detection import RushDetector
from .anomalies import AnomalyManager
from .metrics import compute_metrics
from .simulation import run_simulation
