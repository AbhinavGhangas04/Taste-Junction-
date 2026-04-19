from __future__ import annotations

from collections import deque
from statistics import mean
from typing import Deque, Optional

from .domain import KitchenState, Order


class SlidingWindowETAPredictor:
    """Adaptive ETA predictor with sliding-window bias correction.

    The model is deliberately simple but captures three important aspects:
    - current backlog ahead of the order
    - parallelism (number of preparation slots)
    - systematic bias in previous predictions over a sliding window
    """

    def __init__(self, window_size: int = 50) -> None:
        self.window_size = window_size
        self._errors: Deque[float] = deque(maxlen=window_size)

    @property
    def bias(self) -> float:
        """Current bias estimate (predicted - actual).

        If positive, we have been over-estimating ETAs; if negative,
        we have been under-estimating.
        """

        if not self._errors:
            return 0.0
        return mean(self._errors)

    def predict(self, order: Order, state: KitchenState) -> float:
        """Return an ETA (absolute time) for *completion* of given order.

        Base ETA is derived from remaining work in the system, divided by
        effective parallelism, plus the order's own prep time. Then we
        subtract the learned bias so the model gradually self-corrects.
        """

        now = state.current_time
        # Remaining work in running orders
        remaining_running = 0.0
        for o in state.running_orders.values():
            if o.start_time is None:
                remaining_running += o.prep_time
            else:
                elapsed = max(0.0, now - o.start_time)
                remaining_running += max(0.0, o.prep_time - elapsed)

        # Work ahead in the waiting queue (including this order conceptually)
        work_ahead = sum(o.prep_time for o in state.waiting_orders)
        work_ahead += order.prep_time

        effective_capacity = max(1, state.config.num_slots)
        eta_base = now + (remaining_running + work_ahead) / effective_capacity

        eta_corrected = eta_base - self.bias
        order.predicted_eta = eta_corrected
        return eta_corrected

    def update(self, order: Order) -> None:
        """Update the bias window using the error of a completed order.

        ETA_actual_error = ETA_predicted - ETA_real
        """

        if order.predicted_eta is None or order.completion_time is None:
            return
        error = order.predicted_eta - order.completion_time
        self._errors.append(error)
