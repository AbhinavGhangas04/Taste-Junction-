from __future__ import annotations

import logging
from math import inf
from typing import Iterable, List, Tuple

from .anomalies import AnomalyManager
from .domain import KitchenConfig, KitchenState, Order, OrderStatus
from .eta import SlidingWindowETAPredictor
from .metrics import compute_metrics
from .rush_detection import RushDetector
from .scheduling import BaseScheduler

logger = logging.getLogger(__name__)


def run_simulation(
    orders: Iterable[Order],
    scheduler: BaseScheduler,
    config: KitchenConfig | None = None,
    eta_model: SlidingWindowETAPredictor | None = None,
    rush_detector: RushDetector | None = None,
    anomaly_manager: AnomalyManager | None = None,
) -> Tuple[KitchenState, dict]:
    """Run a discrete-event simulation for a single scheduler.

    The same engine can be reused for FIFO / SJF / Priority / Adaptive
    schedulers. This function returns the final KitchenState plus a
    metrics dictionary suitable for comparison and plotting.
    """

    cfg = config or KitchenConfig()
    state = KitchenState(config=cfg)

    eta_model = eta_model or SlidingWindowETAPredictor()
    rush_detector = rush_detector or RushDetector(
        bucket_size=cfg.rush_interval,
        window_size=cfg.rush_window,
        k=cfg.rush_k,
    )
    anomaly_manager = anomaly_manager or AnomalyManager()

    # Sort arrivals by arrival_time
    arrivals: List[Order] = sorted(list(orders), key=lambda o: o.arrival_time)
    i = 0
    n = len(arrivals)

    # For overload detection we keep a short history of total system size
    recent_sizes: List[int] = []
    recent_window = max(10, cfg.rush_window)

    # Main event loop
    while i < n or state.running_orders or state.waiting_orders:
        # If nothing is happening yet, fast-forward to next arrival
        if not state.running_orders and not state.waiting_orders and i < n:
            state.current_time = max(state.current_time, arrivals[i].arrival_time)

        # 1) Process all arrivals up to current_time
        while i < n and arrivals[i].arrival_time <= state.current_time:
            order = arrivals[i]
            i += 1
            rush_detector.on_arrival(order.arrival_time)

            if anomaly_manager.maybe_mark_unavailable(order, state):
                logger.info(
                    "order %s failed=UNAVAILABLE at t=%.1f", order.id, state.current_time
                )
                continue

            scheduler.enqueue(order, state)

        # update rush and delay markers
        anomaly_manager.detect_delays(state)

        # 2) Start new orders if there are free slots
        free_slots = state.free_slots
        if free_slots > 0 and state.waiting_orders:
            to_start = scheduler.pop_next(state, free_slots)
            for o in to_start:
                o.status = OrderStatus.RUNNING
                o.start_time = state.current_time
                # assign deterministic completion time (prep_time only)
                o.completion_time = state.current_time + o.prep_time
                eta_model.predict(o, state)
                state.running_orders[o.id] = o
                logger.info(
                    "start order %s at t=%.1f prep=%.1f eta=%.1f", 
                    o.id,
                    state.current_time,
                    o.prep_time,
                    o.predicted_eta or -1,
                )

        # 3) Decide next event time: next completion vs next arrival
        if state.running_orders:
            next_completion = min(o.completion_time for o in state.running_orders.values() if o.completion_time is not None)  # type: ignore[arg-type]
        else:
            next_completion = inf

        next_arrival = arrivals[i].arrival_time if i < n else inf

        if next_arrival == inf and next_completion == inf:
            break  # no more events

        next_time = min(next_arrival, next_completion)
        if next_time <= state.current_time:
            # avoid infinite loops with degenerate data
            next_time = state.current_time + 1e-6

        state.current_time = next_time

        # track recent sizes for overload heuristics
        total_size = len(state.waiting_orders) + len(state.running_orders)
        recent_sizes.append(total_size)
        if len(recent_sizes) > recent_window:
            recent_sizes.pop(0)

        # 4) Complete any orders finishing at this time
        completed_ids = [
            oid
            for oid, o in list(state.running_orders.items())
            if o.completion_time is not None and abs(o.completion_time - state.current_time) < 1e-6
        ]
        for oid in completed_ids:
            o = state.running_orders.pop(oid)
            o.status = OrderStatus.COMPLETED
            eta_model.update(o)
            state.completed_orders.append(o)
            scheduler.on_order_completed(o, state)
            logger.info("complete order %s at t=%.1f", o.id, state.current_time)

    metrics = compute_metrics(state)
    return state, metrics
