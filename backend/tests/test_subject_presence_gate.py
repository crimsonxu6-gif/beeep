from schemas import SubjectPreflightResult
from vision.subject_presence_gate import SubjectPresenceGate


def result(state: str, reason_code: str) -> SubjectPreflightResult:
    return SubjectPreflightResult(
        state=state,
        detected=state == "detected",
        allow_shuttermuse=state == "detected",
        confidence=0.9 if state == "detected" else 0,
        face_detected=state != "missing",
        reason_code=reason_code,
    )


def test_missing_requires_three_consecutive_frames() -> None:
    gate = SubjectPresenceGate()
    first = gate.evaluate("stream", 1, result("missing", "no_face"), now_ms=100)
    second = gate.evaluate("stream", 2, result("missing", "no_face"), now_ms=200)
    third = gate.evaluate("stream", 3, result("missing", "no_face"), now_ms=300)
    assert first.state == "uncertain" and first.allow_shuttermuse
    assert second.state == "uncertain" and second.allow_shuttermuse
    assert third.state == "missing" and not third.allow_shuttermuse


def test_recent_detection_survives_temporary_face_loss() -> None:
    gate = SubjectPresenceGate()
    gate.evaluate("stream", 1, result("detected", "face_confirmed"), now_ms=100)
    temporary = gate.evaluate("stream", 2, result("missing", "no_face"), now_ms=1000)
    assert temporary.state == "uncertain"
    assert temporary.reason_code == "recent_subject"
    assert temporary.allow_shuttermuse


def test_uncertain_is_blocked_only_after_confirmation_window() -> None:
    gate = SubjectPresenceGate()
    raw = result("uncertain", "face_low_confidence")
    assert gate.evaluate("stream", 1, raw, now_ms=100).allow_shuttermuse
    assert gate.evaluate("stream", 2, raw, now_ms=200).allow_shuttermuse
    assert not gate.evaluate("stream", 3, raw, now_ms=300).allow_shuttermuse
