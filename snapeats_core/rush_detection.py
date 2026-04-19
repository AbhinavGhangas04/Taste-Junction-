from __future__ import annotations

from collections import deque
from statistics import mean, pstdev
from typing import Deque, Tuple


class RushDetector:
    """Arrival-rate based rush detector using mu + k*sigma rule.

    Time is partitioned into fixed-size buckets (e.g., 60 seconds). For
    each bucket we keep a count of arriving orders. Over a sliding window
    of recent buckets we maintain mean (mu) and population std-dev
    (sigma). The current interval is flagged as *rush* if

        count_t >= mu + k * sigma

    This is simple, explainable, and cheap to compute in real time.
    """

    def __init__(self, bucket_size: float, window_size: int, k: float) -> None:
        self.bucket_size = bucket_size
        self.window_size = window_size
        self.k = k

        self._history: Deque[int] = deque(maxlen=window_size)
        self._current_bucket_index: int | None = None
        self._current_bucket_count: int = 0

    def _bucket_index(self, t: float) -> int:
        return int(t // self.bucket_size)

    def on_arrival(self, t: float) -> None:
        """Record a new order arrival at absolute time t (seconds)."""

        idx = self._bucket_index(t)
        if self._current_bucket_index is None:
            self._current_bucket_index = idx

        if idx != self._current_bucket_index:
            # roll over to a new bucket
            self._history.append(self._current_bucket_count)
            self._current_bucket_index = idx
            self._current_bucket_count = 0

        self._current_bucket_count += 1

    def stats(self) -> Tuple[float, float, int]:
        """Return (mu, sigma, current_count) over the sliding window."""

        if not self._history:
            return (0.0, 0.0, self._current_bucket_count)

        mu = mean(self._history)
        sigma = pstdev(self._history) if len(self._history) > 1 else 0.0
        return (mu, sigma, self._current_bucket_count)

    def is_rush(self) -> bool:
        """Whether the current interval is considered a rush period."""

        mu, sigma, c = self.stats()
        if len(self._history) < max(3, self.window_size // 2):
            # not enough history yet
            return False
        threshold = mu + self.k * sigma
        return c >= threshold
