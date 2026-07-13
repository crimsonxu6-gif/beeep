from __future__ import annotations

import numpy as np
import pytest

from schemas import ImagePayload, VisionFeatureRequest
from vision.subject_preflight import PreflightSignal, SubjectPreflight
from vision.subject_presence_gate import SubjectPresenceGate


def request() -> VisionFeatureRequest:
    return VisionFeatureRequest(
        frame_id=1,
        timestamp=1,
        image=ImagePayload(base64="unused", width=100, height=200, mime_type="image/jpeg"),
    )


@pytest.fixture
def detector(monkeypatch: pytest.MonkeyPatch) -> SubjectPreflight:
    instance = object.__new__(SubjectPreflight)
    instance.face_detector = object()
    instance.pose_detector = object()
    monkeypatch.setattr(
        "vision.subject_preflight._decode_base64_image",
        lambda *_args: np.zeros((200, 100, 3), dtype=np.uint8),
    )
    return instance


def test_confirmed_face_skips_pose(
    detector: SubjectPreflight, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        detector,
        "_detect_face",
        lambda *_args: PreflightSignal(
            found=True,
            confirmed=True,
            confidence=0.9,
            bbox_norm=(0.2, 0.1, 0.8, 0.95),
            reason_code="face_confirmed",
        ),
    )
    monkeypatch.setattr(
        detector,
        "_detect_pose",
        lambda *_args: pytest.fail("Pose must not run after a confirmed face"),
    )
    output = detector.analyze(request())
    assert output.state == "confirmed"
    assert output.detection_source == "face"
    assert output.face_detected
    assert not output.pose_detected


def test_failed_face_runs_pose_and_confirms_subject(
    detector: SubjectPreflight, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        detector,
        "_detect_face",
        lambda *_args: PreflightSignal(found=False, confirmed=False, reason_code="no_face"),
    )
    monkeypatch.setattr(
        detector,
        "_detect_pose",
        lambda *_args: PreflightSignal(
            found=True,
            confirmed=True,
            confidence=0.8,
            bbox_norm=(0.1, 0.05, 0.9, 0.98),
            visible_keypoints=12,
            reason_code="face_missing_pose_detected",
        ),
    )
    output = detector.analyze(request())
    assert output.state == "confirmed"
    assert output.detection_source == "pose"
    assert output.pose_detected
    assert output.visible_pose_keypoints == 12


def test_partial_pose_is_uncertain_and_allowed(
    detector: SubjectPreflight, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        detector,
        "_detect_face",
        lambda *_args: PreflightSignal(found=False, confirmed=False, reason_code="no_face"),
    )
    monkeypatch.setattr(
        detector,
        "_detect_pose",
        lambda *_args: PreflightSignal(
            found=True,
            confirmed=False,
            confidence=0.4,
            bbox_norm=(0.4, 0.2, 0.5, 0.5),
            visible_keypoints=3,
            reason_code="pose_partial",
        ),
    )
    output = detector.analyze(request())
    assert output.state == "uncertain"
    assert output.detected
    assert output.allow_shuttermuse


def test_no_face_or_pose_returns_raw_missing_candidate(
    detector: SubjectPreflight, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing = PreflightSignal(found=False, confirmed=False)
    monkeypatch.setattr(detector, "_detect_face", lambda *_args: missing)
    monkeypatch.setattr(detector, "_detect_pose", lambda *_args: missing)
    output = detector.analyze(request())
    assert output.state == "missing"
    assert not output.detected
    assert not output.allow_shuttermuse
    assert output.reason_code == "no_subject_signal"


def test_back_view_pose_signal_recovers_missing_face(
    detector: SubjectPreflight, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        detector,
        "_detect_face",
        lambda *_args: PreflightSignal(found=False, confirmed=False),
    )
    monkeypatch.setattr(
        detector,
        "_detect_pose",
        lambda *_args: PreflightSignal(
            found=True,
            confirmed=True,
            confidence=0.72,
            bbox_norm=(0.2, 0.08, 0.8, 0.98),
            visible_keypoints=10,
        ),
    )
    output = detector.analyze(request())
    assert output.state == "confirmed"
    assert output.detection_source == "pose"


def test_looking_down_or_tiny_subject_is_uncertain_not_blocked(
    detector: SubjectPreflight, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        detector,
        "_detect_face",
        lambda *_args: PreflightSignal(
            found=True,
            confirmed=False,
            confidence=0.4,
            bbox_norm=(0.45, 0.2, 0.55, 0.35),
            reason_code="subject_too_small",
        ),
    )
    monkeypatch.setattr(
        detector,
        "_detect_pose",
        lambda *_args: PreflightSignal(found=False, confirmed=False),
    )
    raw = detector.analyze(request())
    gated = SubjectPresenceGate(blocking_enabled=True).evaluate(
        "tiny", 1, raw, now_ms=100
    )
    assert raw.state == "uncertain"
    assert gated.allow_shuttermuse
    assert not gated.blocked_model_call
