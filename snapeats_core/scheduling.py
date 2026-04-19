from __future__ import annotations

import heapq
import logging
from abc import ABC, abstractmethod
from collections import deque
from typing import Deque, List

from .anomalies import AnomalyManager
from .domain import KitchenState, Order
from .rush_detection import RushDetector

logger = logging.getLogger(__name__)


class BaseScheduler(ABC):
    """Abstract base class for all queue scheduling policies."""

    name: str = "base"

    @abstractmethod
    def enqueue(self, order: Order, state: KitchenState) -> None:  # pragma: no cover - interface
        ...

    @abstractmethod
    def pop_next(self, state: KitchenState, k: int) -> List[Order]:  # pragma: no cover - interface
        ...

    def on_order_completed(self, order: Order, state: KitchenState) -> None:
        """Hook for derived classes; called whenever an order completes."""

        # default: nothing
        return None


class FIFOScheduler(BaseScheduler):
    """First-In-First-Out baseline scheduler (for comparison)."""

    name = "fifo"

    def __init__(self) -> None:
        self._queue: Deque[Order] = deque()

    def enqueue(self, order: Order, state: KitchenState) -> None:
        self._queue.append(order)
        state.waiting_orders.append(order)
        state.update_peak_queue()

    def pop_next(self, state: KitchenState, k: int) -> List[Order]:
        selected: List[Order] = []
        while k > 0 and self._queue:
            o = self._queue.popleft()
            selected.append(o)
            # keep state.waiting_orders in sync
            if o in state.waiting_orders:
                state.waiting_orders.remove(o)
            k -= 1
        return selected


class SJFScheduler(BaseScheduler):
    """Shortest-Job-First scheduler based on prep_time.

    This is non-preemptive SJF; once a job starts, it runs to
    completion. Queue discipline only affects which order starts next.
    """

    name = "sjf"

    def __init__(self) -> None:
        self._heap: List[tuple[float, float, int, Order]] = []

    def enqueue(self, order: Order, state: KitchenState) -> None:
        heapq.heappush(self._heap, (order.prep_time, order.arrival_time, order.id, order))
        state.waiting_orders.append(order)
        state.update_peak_queue()

    def pop_next(self, state: KitchenState, k: int) -> List[Order]:
        selected: List[Order] = []
        while k > 0 and self._heap:
            _, _, _, o = heapq.heappop(self._heap)
            selected.append(o)
            if o in state.waiting_orders:
                state.waiting_orders.remove(o)
            k -= 1
        return selected


class PriorityScheduler(BaseScheduler):
    """Priority queue scheduler.

    Higher `order.priority` means more important; ties broken by
    arrival_time. This can be used both for urgent orders and for
    delayed ones whose priority has been boosted by the service layer.
    """

    name = "priority"

    def __init__(self) -> None:
        self._heap: List[tuple[int, float, int, Order]] = []

    def enqueue(self, order: Order, state: KitchenState) -> None:
        # negative priority so that larger priority is popped first
        heapq.heappush(self._heap, (-order.priority, order.arrival_time, order.id, order))
        state.waiting_orders.append(order)
        state.update_peak_queue()

    def pop_next(self, state: KitchenState, k: int) -> List[Order]:
        selected: List[Order] = []
        while k > 0 and self._heap:
            _, _, _, o = heapq.heappop(self._heap)
            selected.append(o)
            if o in state.waiting_orders:
                state.waiting_orders.remove(o)
            k -= 1
        return selected


class AdaptiveHybridScheduler(BaseScheduler):
    """Runtime-adaptive hybrid scheduler.

    Decision logic (simplified but explainable):
    - If there are any delayed or urgent orders waiting: PRIORITY mode.
    - Else if RushDetector reports a rush: SJF mode.
    - Else: FIFO mode for fairness.

    All decisions are logged so they can be visualized in the UI.
    """

    name = "adaptive_hybrid"

    def __init__(
        self,
        rush_detector: RushDetector,
        anomaly_manager: AnomalyManager | None = None,
    ) -> None:
        self.rush_detector = rush_detector
        self.anomaly_manager = anomaly_manager or AnomalyManager()
        # We reuse simple policy-specific views via sorting of the shared
        # state.waiting_orders; no duplicated queues are kept here.

    def enqueue(self, order: Order, state: KitchenState) -> None:
        state.waiting_orders.append(order)
        state.update_peak_queue()

    def _choose_mode(self, state: KitchenState) -> str:
        has_urgent_or_delayed = any(o.is_urgent or o.is_delayed for o in state.waiting_orders)
        if has_urgent_or_delayed:
            return "PRIORITY"
        if self.rush_detector.is_rush():
            return "SJF"
        return "FIFO"

    def pop_next(self, state: KitchenState, k: int) -> List[Order]:
        if not state.waiting_orders or k <= 0:
            return []

        mode = self._choose_mode(state)
        logger.info("AdaptiveHybridScheduler mode=%s queue_len=%d", mode, len(state.waiting_orders))

        # Materialize a local copy of waiting orders to sort and select
        candidates = list(state.waiting_orders)
        now = state.current_time

        if mode == "PRIORITY":
            # Urgent + delayed first, then by priority, then FIFO among equals
            candidates.sort(
                key=lambda o: (
                    not (o.is_urgent or o.is_delayed),  # False < True
                    -o.priority,
                    o.arrival_time,
                )
            )
        elif mode == "SJF":
            candidates.sort(key=lambda o: (o.prep_time, o.arrival_time))
        else:  # FIFO
            candidates.sort(key=lambda o: o.arrival_time)

        selected = []
        for o in candidates:
            if k <= 0:
                break
            if o not in state.waiting_orders:
                continue
            state.waiting_orders.remove(o)
            selected.append(o)
            k -= 1

        return selected
