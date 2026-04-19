from __future__ import annotations

from statistics import mean
from typing import Dict, Iterable

from .domain import KitchenState, Order


def _safe_mean(values: Iterable[float]) -> float:
    vals = list(values)
    return mean(vals) if vals else 0.0


def compute_metrics(state: KitchenState) -> Dict[str, float]:
    """Compute formal metrics for a finished simulation run.

    Metrics:
      - avg_waiting_time
      - avg_turnaround_time
      - peak_queue_length
      - throughput
      - starvation_rate
      - failure_rate
    """

    completed: Iterable[Order] = state.completed_orders
    failed: Iterable[Order] = state.failed_orders

    waiting_times = [o.waiting_time() for o in completed if o.waiting_time() is not None]
    turnaround_times = [
        o.turnaround_time() for o in completed if o.turnaround_time() is not None
    ]

    avg_waiting_time = _safe_mean(waiting_times)
    avg_turnaround_time = _safe_mean(turnaround_times)

    total_time = state.current_time if state.current_time > 0 else 1.0
    throughput = len(state.completed_orders) / total_time

    sla = state.config.starvation_sla
    starved = [wt for wt in waiting_times if wt > sla]
    starvation_rate = len(starved) / len(waiting_times) if waiting_times else 0.0

    total_orders = len(state.completed_orders) + len(state.failed_orders)
    failure_rate = len(state.failed_orders) / total_orders if total_orders else 0.0

    return {
        "avg_waiting_time": avg_waiting_time,
        "avg_turnaround_time": avg_turnaround_time,
        "peak_queue_length": state.peak_queue_length,
        "throughput": throughput,
        "starvation_rate": starvation_rate,
        "failure_rate": failure_rate,
    }
