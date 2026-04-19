from __future__ import annotations

"""Quick experiment runner for Snapeats core logic.

This script is *not* a UI. It is a small analytics harness that:
  - generates a synthetic order stream,
  - runs it through FIFO and AdaptiveHybrid schedulers,
  - prints formal metrics so you can demonstrate improvements.

Run from project root:

    python core_demo.py
"""

import copy
import random
from typing import List

from snapeats_core import (
    AdaptiveHybridScheduler,
    AnomalyManager,
    FIFOScheduler,
    KitchenConfig,
    Order,
    RushDetector,
    SlidingWindowETAPredictor,
    run_simulation,
)


def generate_workload(
    num_orders: int = 120,
    mean_interarrival: float = 15.0,
    min_prep: float = 60.0,
    max_prep: float = 300.0,
) -> List[Order]:
    """Generate a synthetic order stream for evaluation.

    - Arrivals follow an exponential inter-arrival distribution
      parameterized by `mean_interarrival`.
    - Prep times are uniform in [min_prep, max_prep].
    - A small fraction of orders is marked as urgent.
    """

    orders: List[Order] = []
    t = 0.0
    urgent_prob = 0.15

    for i in range(1, num_orders + 1):
        # exponential inter-arrival times
        gap = random.expovariate(1.0 / mean_interarrival)
        t += gap
        prep = random.uniform(min_prep, max_prep)
        is_urgent = random.random() < urgent_prob
        priority = 1 if is_urgent else 0
        orders.append(Order(id=i, arrival_time=t, prep_time=prep, priority=priority, is_urgent=is_urgent))

    return orders


def run_experiment() -> None:
    cfg = KitchenConfig(num_slots=3, unavailable_prob=0.05)
    base_orders = generate_workload()

    # FIFO baseline
    fifo_orders = copy.deepcopy(base_orders)
    fifo_scheduler = FIFOScheduler()
    fifo_state, fifo_metrics = run_simulation(
        orders=fifo_orders,
        scheduler=fifo_scheduler,
        config=cfg,
    )

    # Adaptive hybrid
    adaptive_orders = copy.deepcopy(base_orders)
    rush = RushDetector(
        bucket_size=cfg.rush_interval,
        window_size=cfg.rush_window,
        k=cfg.rush_k,
    )
    adaptive_scheduler = AdaptiveHybridScheduler(rush_detector=rush, anomaly_manager=AnomalyManager())
    adaptive_state, adaptive_metrics = run_simulation(
        orders=adaptive_orders,
        scheduler=adaptive_scheduler,
        config=cfg,
    )

    print("=== FIFO baseline ===")
    for k, v in fifo_metrics.items():
        print(f"{k:20s}: {v:8.2f}")

    print("\n=== Adaptive Hybrid ===")
    for k, v in adaptive_metrics.items():
        print(f"{k:20s}: {v:8.2f}")

    print("\nRelative improvement (adaptive vs FIFO, lower is better for times)")
    for key in ["avg_waiting_time", "avg_turnaround_time", "peak_queue_length", "starvation_rate", "failure_rate"]:
        f = fifo_metrics.get(key, 0.0)
        a = adaptive_metrics.get(key, 0.0)
        if f > 0:
            delta = (f - a) / f * 100.0
            print(f"{key:20s}: {delta:8.2f}%")


if __name__ == "__main__":
    run_experiment()
