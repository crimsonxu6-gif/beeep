from __future__ import annotations

import math
import threading
from collections import Counter, deque


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


class PreflightMetrics:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.states: Counter[str] = Counter()
        self.reasons: Counter[str] = Counter()
        self.sources: Counter[str] = Counter()
        self.passed = 0
        self.blocked = 0
        self.history_recovered = 0

    def record(
        self,
        result_state: str,
        reason_code: str,
        blocked: bool,
        *,
        detection_source: str = "none",
        history_used: bool = False,
    ) -> None:
        with self.lock:
            self.states[result_state] += 1
            self.reasons[reason_code] += 1
            self.sources[detection_source] += 1
            if history_used:
                self.history_recovered += 1
            if blocked:
                self.blocked += 1
            else:
                self.passed += 1

    def snapshot(self) -> dict[str, object]:
        with self.lock:
            total = self.passed + self.blocked
            return {
                "total": total,
                "passed": self.passed,
                "blocked": self.blocked,
                "block_rate": round(self.blocked / total, 4) if total else 0,
                "states": dict(self.states),
                "reasons": dict(self.reasons),
                "sources": dict(self.sources),
                "history_recovered": self.history_recovered,
            }
