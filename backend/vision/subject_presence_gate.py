from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from core.config import settings
from schemas import SubjectPreflightResult


@dataclass
class StreamPresenceState:
    latest_frame_id: int = 0
    last_confirmed_at_ms: int | None = None
    last_bbox_norm: tuple[float, float, float, float] | None = None
    last_confidence: float = 0
    consecutive_uncertain: int = 0
    consecutive_missing: int = 0
    updated_at_ms: int = 0


class SubjectPresenceGate:
    def __init__(
        self,
        *,
        blocking_enabled: bool | None = None,
        presence_ttl_ms: int | None = None,
        missing_confirm_frames: int | None = None,
        state_ttl_ms: int | None = None,
    ) -> None:
        self.lock = threading.Lock()
        self.streams: dict[str, StreamPresenceState] = {}
        self.blocking_enabled = (
            settings.subject_preflight_blocking
            if blocking_enabled is None
            else blocking_enabled
        )
        self.presence_ttl_ms = presence_ttl_ms or settings.subject_presence_ttl_ms
        self.missing_confirm_frames = max(
            1, missing_confirm_frames or settings.subject_missing_confirm_frames
        )
        self.state_ttl_ms = state_ttl_ms or settings.subject_preflight_state_ttl_ms

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
                return self._finalize(
                    result,
                    state,
                    state_name="uncertain",
                    allow=True,
                    reason_code="confirming_subject",
                )
            state.latest_frame_id = frame_id
            state.updated_at_ms = now

            if result.state == "confirmed":
                state.last_confirmed_at_ms = now
                state.last_bbox_norm = result.bbox_norm
                state.last_confidence = result.confidence
                state.consecutive_uncertain = 0
                state.consecutive_missing = 0
                return self._finalize(result, state, state_name="confirmed", allow=True)

            recent = (
                state.last_confirmed_at_ms is not None
                and now - state.last_confirmed_at_ms <= self.presence_ttl_ms
            )
            if result.state == "uncertain":
                state.consecutive_uncertain += 1
                state.consecutive_missing = 0
                if recent:
                    return self._history_result(result, state, now)
                # Product invariant: uncertain signals always fail open.
                return self._finalize(
                    result,
                    state,
                    state_name="uncertain",
                    allow=True,
                )

            state.consecutive_uncertain = 0
            if recent:
                state.consecutive_missing = 0
                return self._history_result(result, state, now)
            state.consecutive_missing += 1
            if state.consecutive_missing < self.missing_confirm_frames:
                return self._finalize(
                    result,
                    state,
                    state_name="uncertain",
                    allow=True,
                    reason_code="confirming_subject",
                )

            allow = not self.blocking_enabled
            return self._finalize(
                result,
                state,
                state_name="missing",
                allow=allow,
                reason_code="no_subject_signal",
            )

    def reset(self, stream_id: str) -> None:
        with self.lock:
            self.streams.pop(stream_id, None)

    def _history_result(
        self,
        result: SubjectPreflightResult,
        state: StreamPresenceState,
        now_ms: int,
    ) -> SubjectPreflightResult:
        age = now_ms - state.last_confirmed_at_ms if state.last_confirmed_at_ms is not None else None
        return self._finalize(
            result,
            state,
            state_name="confirmed",
            allow=True,
            reason_code="recent_subject",
            extra={
                "detection_source": "history",
                "history_used": True,
                "last_confirmed_age_ms": age,
                "bbox_norm": state.last_bbox_norm,
                "confidence": state.last_confidence,
            },
        )

    def _finalize(
        self,
        result: SubjectPreflightResult,
        state: StreamPresenceState,
        *,
        state_name: str,
        allow: bool,
        reason_code: str | None = None,
        extra: dict[str, object] | None = None,
    ) -> SubjectPreflightResult:
        effective_allow = allow or not self.blocking_enabled
        blocked = self.blocking_enabled and state_name == "missing" and not effective_allow
        update: dict[str, object] = {
            "state": state_name,
            "detected": state_name != "missing",
            "allow_shuttermuse": effective_allow,
            "consecutive_missing": state.consecutive_missing,
            "consecutive_uncertain": state.consecutive_uncertain,
            "blocking_enabled": self.blocking_enabled,
            "blocked_model_call": blocked,
        }
        if reason_code is not None:
            update["reason_code"] = reason_code
        if extra:
            update.update(extra)
        return result.model_copy(update=update)

    def _prune(self, now_ms: int) -> None:
        expired = [
            stream_id
            for stream_id, state in self.streams.items()
            if now_ms - state.updated_at_ms > self.state_ttl_ms
        ]
        for stream_id in expired:
            self.streams.pop(stream_id, None)
