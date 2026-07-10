from __future__ import annotations

import threading

import pytest

from executor import LatestPendingExecutor, ModelRequestSuperseded


def test_only_latest_not_started_job_is_retained() -> None:
    executor = LatestPendingExecutor()
    started = threading.Event()
    release = threading.Event()

    def first() -> int:
        started.set()
        release.wait(timeout=2)
        return 1

    active = executor.submit(first)
    assert started.wait(timeout=1)
    replaced = executor.submit(lambda: 2)
    latest = executor.submit(lambda: 3)
    with pytest.raises(ModelRequestSuperseded):
        replaced.result(timeout=1)
    release.set()
    assert active.result(timeout=1) == 1
    assert latest.result(timeout=1) == 3
