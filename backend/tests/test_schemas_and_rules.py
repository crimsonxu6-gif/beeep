from __future__ import annotations

import pytest
from pydantic import ValidationError

from model.shuttermuse import ShutterMuseGuidanceEngine
from schemas import (
    AnalyzeRequest,
    FaceFeatures,
    GuidanceOutput,
    ImagePayload,
    ImageSize,
    PersonDetection,
    SceneFeatures,
    VisionFeatures,
)
from services.guidance_adapter import GuidanceAdapter
from services.service_factory import create_guidance_service


def features(center_x: float) -> VisionFeatures:
    return VisionFeatures(
        frameId=1,
        imageSize=ImageSize(width=1000, height=1000),
        people=[PersonDetection(id="p", bbox=(center_x - 0.1, 0.25, 0.2, 0.5), score=0.9)],
        face=FaceFeatures(position="center", size="medium"),
        scene=SceneFeatures(brightness="normal", clutter="low"),
        preprocessingLatencyMs=1,
    )


def request(mode: str = "auto") -> AnalyzeRequest:
    return AnalyzeRequest(
        frame_id=1,
        timestamp=1,
        composition_mode=mode,
        image=ImagePayload(base64="eA==", width=10, height=10, mime_type="image/jpeg"),
    )


@pytest.mark.parametrize(("mode", "center_x"), [("thirds_left", 0.33), ("thirds_right", 0.67)])
def test_thirds_modes_do_not_force_center(mode: str, center_x: float) -> None:
    output = ShutterMuseGuidanceEngine().infer(features(center_x), mode)
    assert output.actions[0].type == "hold"


def test_center_mode_guides_subject_from_left_third() -> None:
    output = ShutterMuseGuidanceEngine().infer(features(0.33), "center")
    assert output.actions[0].type == "move_camera"


def test_guidance_schema_rejects_invalid_direction() -> None:
    with pytest.raises(ValidationError):
        GuidanceOutput.model_validate(
            {
                "frameId": 1,
                "priority": "composition",
                "problem": {"type": "position", "description": "bad"},
                "actions": [{"type": "move_camera", "direction": "center", "message": "保持"}],
                "message": "保持",
                "reason": "test",
                "summary": "test",
                "confidence": 0.8,
            }
        )


def test_pose_adapter_rejects_incomplete_output() -> None:
    with pytest.raises(ValueError, match="17"):
        GuidanceAdapter().parse_pose([{"name": "nose", "x": 0.5, "y": 0.2}] * 16, [1] * 16)


def test_service_factory_switches_engines() -> None:
    assert create_guidance_service("rules").engine_name == "rules"
    assert create_guidance_service("shuttermuse").engine_name == "shuttermuse"
