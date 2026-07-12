from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from core.config import settings
from schemas import SubjectPreflightResult


@dataclass
class StreamPresenceState:
    latest_frame_id: int = 0
    last_seen_at_ms: int | None = None
    uncertain_count: int = 0
    missing_count: int = 0
    updated_at_ms: int = 0


class SubjectPresenceGate:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.streams: dict[str, StreamPresenceState] = {}

    def evaluate(
        self,
        stream_id: str,
        frame_id: int,
        result: SubjectPreflightResult,
        now_ms: int | None = None,
    ) -> SubjectPreflightResult:
        now = now_ms if now_ms is not None else int(time.monotonic() * 1000)
        with self.lock:
            self._prune(now)
            state = self.streams.setdefault(stream_id, StreamPresenceState())
            if frame_id < state.latest_frame_id:
                return result.model_copy(
                    update={
                        "state": "uncertain",
                        "detected": False,
                        "allow_shuttermuse": False,
                        "reason": "正在确认人物位置",
                        "reason_code": "confirming_subject",
                    }
                )
            state.latest_frame_id = frame_id
            state.updated_at_ms = now

            if result.state == "detected":
                state.last_seen_at_ms = now
                state.uncertain_count = 0
                state.missing_count = 0
                return result.model_copy(update={"allow_shuttermuse": True})

            recently_seen = (
                state.last_seen_at_ms is not None
                and now - state.last_seen_at_ms <= settings.subject_preflight_hold_ms
            )
            if result.state == "uncertain":
                state.uncertain_count += 1
                state.missing_count = 0
                allow = (
                    recently_seen
                    or state.uncertain_count < settings.subject_preflight_confirmation_frames
                )
                return result.model_copy(update={"allow_shuttermuse": allow})

            state.missing_count += 1
            state.uncertain_count = 0
            allow = (
                recently_seen
                or state.missing_count < settings.subject_preflight_confirmation_frames
            )
            if allow:
                return result.model_copy(
                    update={
                        "state": "uncertain",
                        "allow_shuttermuse": True,
                        "reason": "正在确认人物位置",
                        "reason_code": "recent_subject" if recently_seen else "confirming_subject",
                    }
                )
            return result.model_copy(update={"allow_shuttermuse": False})

    def reset(self, stream_id: str) -> None:
        with self.lock:
            self.streams.pop(stream_id, None)

    def _prune(self, now_ms: int) -> None:
        expired = [
            stream_id
            for stream_id, state in self.streams.items()
            if now_ms - state.updated_at_ms > settings.subject_preflight_state_ttl_ms
        ]
        for stream_id in expired:
            self.streams.pop(stream_id, None)
