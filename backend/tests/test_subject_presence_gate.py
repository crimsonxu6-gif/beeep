from schemas import SubjectPreflightResult
from vision.subject_presence_gate import SubjectPresenceGate


def result(
    state: str,
    reason_code: str,
    *,
    source: str = "none",
    bbox: tuple[float, float, float, float] | None = None,
) -> SubjectPreflightResult:
    return SubjectPreflightResult(
        state=state,
        detected=state != "missing",
        allow_shuttermuse=state != "missing",
        confidence=0.9 if state == "confirmed" else 0.3 if state == "uncertain" else 0,
        bbox_norm=bbox or ((0.2, 0.1, 0.8, 0.95) if state != "missing" else None),
        face_detected=source == "face",
        pose_detected=source == "pose",
        detection_source=source,
        reason_code=reason_code,
    )


def confirmed(*, bbox: tuple[float, float, float, float] | None = None):
    return result("confirmed", "face_confirmed", source="face", bbox=bbox)


def missing():
    return result("missing", "no_subject_signal")


def uncertain():
    return result("uncertain", "pose_partial", source="pose")


def test_default_fail_open_never_blocks_confirmed_missing() -> None:
    gate = SubjectPresenceGate(blocking_enabled=False, missing_confirm_frames=3)
    first = gate.evaluate("stream", 1, missing(), now_ms=100)
    second = gate.evaluate("stream", 2, missing(), now_ms=200)
    third = gate.evaluate("stream", 3, missing(), now_ms=300)
    assert first.state == "uncertain" and first.allow_shuttermuse
    assert second.state == "uncertain" and second.allow_shuttermuse
    assert third.state == "missing" and third.allow_shuttermuse
    assert not third.blocked_model_call


def test_sequence_a_short_loss_uses_history_inside_ttl() -> None:
    gate = SubjectPresenceGate(blocking_enabled=True, presence_ttl_ms=1500)
    gate.evaluate("stream", 1, confirmed(), now_ms=0)
    first = gate.evaluate("stream", 2, missing(), now_ms=500)
    second = gate.evaluate("stream", 3, missing(), now_ms=1400)
    for recovered in (first, second):
        assert recovered.state == "confirmed"
        assert recovered.detection_source == "history"
        assert recovered.history_used
        assert recovered.consecutive_missing == 0
        assert recovered.allow_shuttermuse
        assert not recovered.blocked_model_call


def test_sequence_b_ttl_expiry_starts_new_missing_window() -> None:
    gate = SubjectPresenceGate(
        blocking_enabled=True,
        presence_ttl_ms=1500,
        missing_confirm_frames=3,
    )
    gate.evaluate("stream", 1, confirmed(), now_ms=0)
    history = gate.evaluate("stream", 2, missing(), now_ms=500)
    first = gate.evaluate("stream", 3, missing(), now_ms=1600)
    second = gate.evaluate("stream", 4, missing(), now_ms=1700)
    third = gate.evaluate("stream", 5, missing(), now_ms=1800)
    assert history.history_used and history.consecutive_missing == 0
    assert first.state == "uncertain" and first.consecutive_missing == 1
    assert second.state == "uncertain" and second.consecutive_missing == 2
    assert third.state == "missing" and third.consecutive_missing == 3
    assert not third.allow_shuttermuse
    assert third.blocked_model_call


def test_sequence_b_fail_open_still_allows_final_missing() -> None:
    gate = SubjectPresenceGate(
        blocking_enabled=False,
        presence_ttl_ms=1500,
        missing_confirm_frames=3,
    )
    gate.evaluate("stream", 1, confirmed(), now_ms=0)
    gate.evaluate("stream", 2, missing(), now_ms=1600)
    gate.evaluate("stream", 3, missing(), now_ms=1700)
    final = gate.evaluate("stream", 4, missing(), now_ms=1800)
    assert final.state == "missing"
    assert final.allow_shuttermuse
    assert not final.blocked_model_call


def test_sequence_c_confirmed_immediately_resets_missing_state() -> None:
    gate = SubjectPresenceGate(blocking_enabled=True, missing_confirm_frames=3)
    gate.evaluate("stream", 1, missing(), now_ms=100)
    gate.evaluate("stream", 2, missing(), now_ms=200)
    new_bbox = (0.1, 0.05, 0.7, 0.9)
    recovered = gate.evaluate("stream", 3, confirmed(bbox=new_bbox), now_ms=300)
    state = gate.streams["stream"]
    assert recovered.state == "confirmed"
    assert recovered.consecutive_missing == 0
    assert recovered.bbox_norm == new_bbox
    assert state.last_confirmed_at_ms == 300
    assert state.last_bbox_norm == new_bbox


def test_sequence_d_detection_fluctuation_remains_allowed() -> None:
    gate = SubjectPresenceGate(blocking_enabled=True, presence_ttl_ms=1500)
    outputs = [
        gate.evaluate("stream", 1, confirmed(), now_ms=0),
        gate.evaluate("stream", 2, uncertain(), now_ms=400),
        gate.evaluate("stream", 3, missing(), now_ms=800),
        gate.evaluate("stream", 4, confirmed(), now_ms=1000),
    ]
    assert all(output.allow_shuttermuse for output in outputs)
    assert outputs[1].history_used
    assert outputs[2].history_used
    assert outputs[-1].state == "confirmed"


def test_sequence_e_stale_frame_cannot_overwrite_new_confirmation() -> None:
    gate = SubjectPresenceGate(blocking_enabled=True)
    current = gate.evaluate("stream", 5, confirmed(), now_ms=500)
    stale = gate.evaluate("stream", 4, missing(), now_ms=600)
    state = gate.streams["stream"]
    assert current.state == "confirmed"
    assert stale.state == "uncertain" and stale.allow_shuttermuse
    assert state.latest_frame_id == 5
    assert state.last_confirmed_at_ms == 500
    assert state.consecutive_missing == 0


def test_uncertain_never_blocks_shuttermuse() -> None:
    gate = SubjectPresenceGate(blocking_enabled=True)
    for frame_id in range(1, 10):
        evaluated = gate.evaluate("stream", frame_id, uncertain(), now_ms=frame_id * 500)
        assert evaluated.state == "uncertain"
        assert evaluated.allow_shuttermuse
        assert not evaluated.blocked_model_call


def test_stream_states_are_independent() -> None:
    gate = SubjectPresenceGate(blocking_enabled=True, missing_confirm_frames=3)
    gate.evaluate("person", 1, confirmed(), now_ms=0)
    for frame_id in range(1, 4):
        missing_output = gate.evaluate("empty", frame_id, missing(), now_ms=frame_id * 100)
    person_output = gate.evaluate("person", 2, missing(), now_ms=500)
    assert missing_output.blocked_model_call
    assert person_output.history_used
    assert person_output.allow_shuttermuse


def test_expired_stream_state_is_pruned() -> None:
    gate = SubjectPresenceGate(blocking_enabled=False, state_ttl_ms=1000)
    gate.evaluate("old", 1, confirmed(), now_ms=0)
    gate.evaluate("new", 1, missing(), now_ms=1001)
    assert "old" not in gate.streams
    assert "new" in gate.streams
