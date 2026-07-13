from schemas import SubjectPreflightResult
from vision.subject_presence_gate import SubjectPresenceGate


def result(state: str, reason_code: str, *, source: str = "none") -> SubjectPreflightResult:
    return SubjectPreflightResult(
        state=state,
        detected=state != "missing",
        allow_shuttermuse=state != "missing",
        confidence=0.9 if state == "confirmed" else 0.3 if state == "uncertain" else 0,
        bbox_norm=(0.2, 0.1, 0.8, 0.95) if state != "missing" else None,
        face_detected=source == "face",
        pose_detected=source == "pose",
        detection_source=source,
        reason_code=reason_code,
    )


def test_default_fail_open_never_blocks_confirmed_missing() -> None:
    gate = SubjectPresenceGate(blocking_enabled=False, missing_confirm_frames=3)
    raw = result("missing", "no_subject_signal")
    first = gate.evaluate("stream", 1, raw, now_ms=100)
    second = gate.evaluate("stream", 2, raw, now_ms=200)
    third = gate.evaluate("stream", 3, raw, now_ms=300)
    assert first.state == "uncertain" and first.allow_shuttermuse
    assert second.state == "uncertain" and second.allow_shuttermuse
    assert third.state == "missing" and third.allow_shuttermuse
    assert not third.blocked_model_call


def test_blocking_requires_threshold_and_expired_history() -> None:
    gate = SubjectPresenceGate(
        blocking_enabled=True,
        presence_ttl_ms=1500,
        missing_confirm_frames=3,
    )
    gate.evaluate(
        "stream", 1, result("confirmed", "face_confirmed", source="face"), now_ms=0
    )
    raw = result("missing", "no_subject_signal")
    first = gate.evaluate("stream", 2, raw, now_ms=500)
    second = gate.evaluate("stream", 3, raw, now_ms=1000)
    third = gate.evaluate("stream", 4, raw, now_ms=1600)
    assert first.detection_source == "history" and first.allow_shuttermuse
    assert second.detection_source == "history" and second.allow_shuttermuse
    assert third.state == "missing" and not third.allow_shuttermuse
    assert third.blocked_model_call


def test_recent_confirmation_recovers_uncertain_with_history() -> None:
    gate = SubjectPresenceGate(blocking_enabled=True, presence_ttl_ms=1500)
    gate.evaluate(
        "stream", 1, result("confirmed", "face_confirmed", source="face"), now_ms=100
    )
    temporary = gate.evaluate(
        "stream", 2, result("uncertain", "pose_partial", source="pose"), now_ms=1000
    )
    assert temporary.state == "confirmed"
    assert temporary.detection_source == "history"
    assert temporary.history_used
    assert temporary.last_confirmed_age_ms == 900
    assert temporary.allow_shuttermuse


def test_uncertain_never_blocks_shuttermuse() -> None:
    gate = SubjectPresenceGate(blocking_enabled=True)
    raw = result("uncertain", "pose_partial", source="pose")
    for frame_id in range(1, 10):
        evaluated = gate.evaluate("stream", frame_id, raw, now_ms=frame_id * 500)
        assert evaluated.state == "uncertain"
        assert evaluated.allow_shuttermuse
        assert not evaluated.blocked_model_call


def test_stale_frame_is_fail_open() -> None:
    gate = SubjectPresenceGate(blocking_enabled=True)
    gate.evaluate("stream", 2, result("missing", "no_subject_signal"), now_ms=200)
    stale = gate.evaluate("stream", 1, result("missing", "no_subject_signal"), now_ms=300)
    assert stale.state == "uncertain"
    assert stale.allow_shuttermuse
    assert not stale.blocked_model_call
