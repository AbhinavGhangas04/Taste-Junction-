from __future__ import annotations

import copy
import random

import streamlit as st

from snapeats_core import (
    AdaptiveHybridScheduler,
    AnomalyManager,
    FIFOScheduler,
    KitchenConfig,
    Order,
    RushDetector,
    run_simulation,
)


def set_page_style() -> None:
    """Global visual style for the Streamlit dashboard (cinematic restaurant look)."""

    st.set_page_config(page_title="Snapeats", layout="wide")
    st.markdown(
        """
        <style>
        /* full page background similar to high-end restaurant landing pages */
        .stApp {
            background:
              radial-gradient(circle at top left, rgba(255,255,255,0.08), transparent 55%),
              linear-gradient(135deg, rgba(3,7,18,0.96), rgba(15,23,42,0.98)),
              url('https://images.pexels.com/photos/958545/pexels-photo-958545.jpeg')
              center/cover no-repeat fixed;
            color: #f5f5f5;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }

.hero-container {
            text-align: left;
            padding: 40px 40px 10px 40px;
        }

        .hero-title {
            font-size: 56px;
            font-weight: 900;
            letter-spacing: 8px;
            text-transform: uppercase;
            text-shadow: 0 12px 40px rgba(0,0,0,0.9);
        }

        .hero-tagline {
            font-size: 16px;
            letter-spacing: 3px;
            text-transform: uppercase;
            opacity: 0.9;
        }

        .hero-badge {
            display:inline-block;
            padding:4px 10px;
            border-radius:999px;
            font-size:11px;
            letter-spacing:2px;
            text-transform:uppercase;
            background:rgba(255,255,255,0.08);
            border:1px solid rgba(255,255,255,0.25);
            margin-bottom:10px;
        }

        .metric-card {
            background: rgba(0,0,0,0.55);
            padding: 14px 16px;
            border-radius: 10px;
            border: 1px solid rgba(255,255,255,0.08);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def generate_workload(num_orders: int = 200) -> list[Order]:
    """Generate a synthetic order workload for demonstration.

    This is not production logic – it is purely to showcase the
    difference between FIFO and the adaptive scheduler in the UI.
    """

    orders: list[Order] = []
    t = 0.0
    urgent_prob = 0.15
    mean_interarrival = 12.0

    for i in range(1, num_orders + 1):
        gap = random.expovariate(1.0 / mean_interarrival)
        t += gap
        prep = random.uniform(60.0, 300.0)
        is_urgent = random.random() < urgent_prob
        priority = 1 if is_urgent else 0
        orders.append(
            Order(
                id=i,
                arrival_time=t,
                prep_time=prep,
                priority=priority,
                is_urgent=is_urgent,
            )
        )

    return orders


def main() -> None:
    set_page_style()

    # --- HERO SECTION -------------------------------------------------------
    st.markdown(
        """
        <div class="hero-container">
          <div class="hero-badge">Adaptive Canteen Queue Intelligence</div>
          <div class="hero-title">SNAPEATS</div>
          <div class="hero-tagline">Real-time load balancing for high-density college canteens</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.write("\n")
        st.markdown("#### Live Demo: Compare FIFO vs Adaptive Hybrid Scheduler")
        st.caption(
            "This UI is just a visualization shell – the core logic is a reusable "
            "Python engine implementing your M.Tech contributions."
        )

        num_orders = st.slider("Number of synthetic orders", 50, 400, 200, step=50)
        slots = st.slider("Kitchen parallel slots", 1, 6, 3)

        if st.button("Run simulation"):
            cfg = KitchenConfig(num_slots=slots, unavailable_prob=0.05)
            base_orders = generate_workload(num_orders=num_orders)

            # FIFO baseline
            fifo_state, fifo_metrics = run_simulation(
                orders=copy.deepcopy(base_orders),
                scheduler=FIFOScheduler(),
                config=cfg,
            )

            # Adaptive hybrid
            rush = RushDetector(
                bucket_size=cfg.rush_interval,
                window_size=cfg.rush_window,
                k=cfg.rush_k,
            )
            adaptive_state, adaptive_metrics = run_simulation(
                orders=copy.deepcopy(base_orders),
                scheduler=AdaptiveHybridScheduler(rush_detector=rush, anomaly_manager=AnomalyManager()),
                config=cfg,
            )

            st.write("### Metrics")
            st.write("FIFO baseline")
            st.json(fifo_metrics)

            st.write("Adaptive Hybrid")
            st.json(adaptive_metrics)

            st.write("### Relative improvement (Adaptive vs FIFO)")
            rows = []
            for key in [
                "avg_waiting_time",
                "avg_turnaround_time",
                "peak_queue_length",
                "starvation_rate",
                "failure_rate",
            ]:
                f = fifo_metrics.get(key, 0.0)
                a = adaptive_metrics.get(key, 0.0)
                if f > 0:
                    delta = (f - a) / f * 100.0
                else:
                    delta = 0.0
                rows.append({"metric": key, "improvement_%": round(delta, 2)})

            st.dataframe(rows, use_container_width=True)

    with col_right:
        st.markdown("### Who are you?")
        st.markdown(
            "- **Student view**: order placement and ETA tracking (to be wired to core).\n"
            "- **Cafeteria staff view**: dashboard of queues, rush periods, and anomalies.\n\n"
            "This Streamlit app can sit alongside your Flask+SocketIO UI as a research "
            "dashboard for viva/thesis demos.",
        )


if __name__ == "__main__":  # pragma: no cover
    main()
