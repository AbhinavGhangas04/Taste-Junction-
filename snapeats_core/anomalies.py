from __future__ import annotations

import random
from typing import Iterable

from .domain import KitchenState, Order, OrderStatus


class AnomalyManager:
    """Detect and model delayed orders, overload, and item unavailability.

    This is intentionally lightweight. In a real deployment, this class
    would integrate with monitoring/telemetry and inventory systems.
    """

    def __init__(self, unavailable_prob: float | None = None) -> None:
        self.unavailable_prob = unavailable_prob

    # --- Item unavailability -------------------------------------------------

    def maybe_mark_unavailable(self, order: Order, state: KitchenState) -> bool:
        """Randomly fail an order due to item unavailability (simulation only).

        Returns True if the order was marked FAILED and should not be
        scheduled.
        """

        p = self.unavailable_prob
        if p is None:
            p = state.config.unavailable_prob
        if p <= 0.0:
            return False

        if random.random() < p:
            order.status = OrderStatus.FAILED
            order.failure_reason = "UNAVAILABLE"
            state.failed_orders.append(order)
            return True
        return False

    # --- Delayed orders / overload ------------------------------------------

    def detect_delays(self, state: KitchenState) -> None:
        """Mark orders as delayed if they exceed delay_factor * prep_time.

        This method does not reschedule by itself; it only annotates
        orders. Schedulers (especially the adaptive one) can use this
        information to boost priority of delayed jobs.
        """

        now = state.current_time
        factor = state.config.delay_factor
        for o in state.running_orders.values():
            if o.start_time is None or o.is_delayed:
                continue
            if now - o.start_time > factor * o.prep_time:
                o.is_delayed = True

    def is_overloaded(self, recent_queue_lengths: Iterable[int], threshold: float = 0.8) -> bool:
        """Detect overload based on high average utilization.

        The caller supplies a sliding-window of recent queue lengths
        (including running + waiting). If the average normalized by the
        number of slots exceeds `threshold`, we say the kitchen is
        overloaded.
        """

        recent = list(recent_queue_lengths)
        if not recent:
            return False
        avg_q = sum(recent) / len(recent)
        # The caller is expected to normalize externally if desired.
        return avg_q >= threshold
