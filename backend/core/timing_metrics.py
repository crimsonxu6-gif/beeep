from __future__ import annotations

import math
import threading
from collections import deque


def _percentile(values: deque[int], percentile: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(percentile * len(ordered)) - 1))
    return ordered[index]


class TimingMetrics:
    def __init__(self, capacity: int = 200) -> None:
        self.lock = threading.Lock()
        self.preflight = deque[int](maxlen=capacity)
        self.guidance = deque[int](maxlen=capacity)

    def record(self, *, preflight_ms: int | None, guidance_ms: int | None) -> None:
        with self.lock:
            if preflight_ms is not None:
                self.preflight.append(preflight_ms)
            if guidance_ms is not None:
                self.guidance.append(guidance_ms)

    def snapshot(self) -> dict[str, int | None]:
        with self.lock:
            return {
                "preflight_p50_ms": _percentile(self.preflight, 0.50),
                "preflight_p95_ms": _percentile(self.preflight, 0.95),
                "guidance_p50_ms": _percentile(self.guidance, 0.50),
                "guidance_p95_ms": _percentile(self.guidance, 0.95),
                "sample_count": max(len(self.preflight), len(self.guidance)),
            }
