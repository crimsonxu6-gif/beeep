from __future__ import annotations

import threading
from concurrent.futures import Future
from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

T = TypeVar("T")


class ModelRequestSuperseded(RuntimeError):
    pass


@dataclass
class _Job(Generic[T]):
    operation: Callable[[], T]
    future: Future[T]


class LatestPendingExecutor:
    """One active GPU job and one replaceable not-yet-started job."""

    def __init__(self) -> None:
        self._condition = threading.Condition()
        self._pending: _Job | None = None
        self._active = False
        self._thread = threading.Thread(target=self._run, name="shuttermuse-gpu", daemon=True)
        self._thread.start()

    def submit(self, operation: Callable[[], T]) -> Future[T]:
        future: Future[T] = Future()
        with self._condition:
            if self._pending is not None and not self._pending.future.done():
                self._pending.future.set_exception(
                    ModelRequestSuperseded("MODEL_BUSY: request replaced by a newer frame")
                )
            self._pending = _Job(operation=operation, future=future)
            self._condition.notify()
        return future

    def status(self) -> tuple[bool, int]:
        with self._condition:
            return self._active, int(self._pending is not None)

    def cancel_if_pending(self, future: Future) -> bool:
        with self._condition:
            if self._pending is not None and self._pending.future is future:
                self._pending = None
                future.cancel()
                return True
        return False

    def _run(self) -> None:
        while True:
            with self._condition:
                while self._pending is None:
                    self._condition.wait()
                job = self._pending
                self._pending = None
                self._active = True
            try:
                if not job.future.set_running_or_notify_cancel():
                    continue
                job.future.set_result(job.operation())
            except BaseException as exc:  # noqa: BLE001
                if not job.future.done():
                    job.future.set_exception(exc)
            finally:
                with self._condition:
                    self._active = False
