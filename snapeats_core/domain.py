from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional


class OrderStatus(Enum):
    """Lifecycle of an order inside the kitchen model."""

    WAITING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()


@dataclass
class Order:
    """Canteen order as seen by the scheduler.

    This is intentionally minimal and independent of any database model.
    The service/UI layer is expected to map persistent rows into this
    in-memory representation before passing it to the core.
    """

    id: int
    arrival_time: float  # seconds since simulation/start of day
    prep_time: float  # estimated preparation time in seconds
    priority: int = 0  # higher = more important
    is_urgent: bool = False

    # Runtime fields, filled by the core logic
    status: OrderStatus = OrderStatus.WAITING
    predicted_eta: Optional[float] = None
    start_time: Optional[float] = None
    completion_time: Optional[float] = None
    failure_reason: Optional[str] = None
    is_delayed: bool = False

    def waiting_time(self) -> Optional[float]:
        """Time spent waiting in queue before preparation started."""

        if self.start_time is None:
            return None
        return self.start_time - self.arrival_time

    def turnaround_time(self) -> Optional[float]:
        """End-to-end time inside the system (arrival -> completion)."""

        if self.completion_time is None:
            return None
        return self.completion_time - self.arrival_time


@dataclass
class KitchenConfig:
    """Configuration knobs for the simulated kitchen/queueing system."""

    num_slots: int = 3  # number of parallel preparation slots
    delay_factor: float = 1.5  # when actual > delay_factor * prep_time => delayed
    starvation_sla: float = 600.0  # seconds; above this counted as starvation
    rush_interval: float = 60.0  # seconds per arrival-rate bucket
    rush_window: int = 10  # how many recent buckets to use for mu/sigma
    rush_k: float = 1.5  # rush if current >= mu + k * sigma
    unavailable_prob: float = 0.0  # probability an item is unavailable (simulation)


@dataclass
class KitchenState:
    """Mutable snapshot of the kitchen at a given simulated time."""

    config: KitchenConfig
    current_time: float = 0.0
    running_orders: Dict[int, Order] = field(default_factory=dict)
    waiting_orders: List[Order] = field(default_factory=list)
    completed_orders: List[Order] = field(default_factory=list)
    failed_orders: List[Order] = field(default_factory=list)
    peak_queue_length: int = 0

    def update_peak_queue(self) -> None:
        q_len = len(self.waiting_orders)
        if q_len > self.peak_queue_length:
            self.peak_queue_length = q_len

    @property
    def free_slots(self) -> int:
        """Number of free preparation slots at this instant."""

        return max(self.config.num_slots - len(self.running_orders), 0)
