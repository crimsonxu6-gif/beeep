from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient

from core.errors import ApiError
from main import app
from schemas import SubjectPreflightResult
from services.guidance_adapter import GuidanceAdapter
from services.shuttermuse_client import ModelCompositionResult
from vision.subject_presence_gate import SubjectPresenceGate

analyze_module = importlib.import_module("api.analyze")
client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_presence_gate(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(analyze_module, "subject_presence_gate", SubjectPresenceGate())


def request_payload() -> dict[str, object]:
    return {
        "frame_id": 12,
        "timestamp": 100,
        "mode": "composition",
        "composition_mode": "auto",
        "target_ratio": "3:4",
        "language": "zh-CN",
        "requires_person": True,
        "stream_id": "test-stream",
        "image": {
            "base64": "unused-by-fakes",
            "width": 100,
            "height": 100,
            "mime_type": "image/jpeg",
        },
    }


class FakePreflight:
    def __init__(self, result: SubjectPreflightResult | Exception) -> None:
        self.result = result

    def analyze(self, _request):
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class FakeShutterMuseService:
    engine_name = "shuttermuse"

    def __init__(self, error: ApiError | None = None) -> None:
        self.calls = 0
        self.error = error

    def analyze(self, request, _features):
        self.calls += 1
        if self.error:
            raise self.error
        result = ModelCompositionResult(
            request_id="req_model",
            frame_id=request.frame_id,
            status="success",
            decision="refine",
            bbox_norm=(0.05, 0.2, 0.55, 0.8),
            confidence=0.84,
            inference_ms=200,
            prompt_mode="official",
        )
        return GuidanceAdapter().from_model_composition(result, request.frame_id)

    def readiness(self):
        return {"status": "ready", "guidance_engine": "shuttermuse"}


def detected_subject() -> SubjectPreflightResult:
    return SubjectPreflightResult(
        state="confirmed",
        detected=True,
        allow_shuttermuse=True,
        confidence=0.9,
        bbox_norm=(0.2, 0.1, 0.8, 0.95),
        face_detected=True,
        detection_source="face",
        face_confidence=0.9,
        reason_code="face_confirmed",
    )


def test_detected_subject_calls_shuttermuse(monkeypatch: pytest.MonkeyPatch) -> None:
    service = FakeShutterMuseService()
    monkeypatch.setattr(analyze_module, "guidance_service", service)
    monkeypatch.setattr(analyze_module, "subject_preflight", FakePreflight(detected_subject()))
    response = client.post("/v1/analyze", json=request_payload())
    assert response.status_code == 200
    assert service.calls == 1
    assert response.json()["subject_preflight"]["detected"] is True
    assert response.json()["timing"]["preflight_ms"] >= 0


def test_missing_subject_skips_shuttermuse(monkeypatch: pytest.MonkeyPatch) -> None:
    service = FakeShutterMuseService()
    monkeypatch.setattr(analyze_module, "guidance_service", service)
    monkeypatch.setattr(
        analyze_module,
        "subject_presence_gate",
        SubjectPresenceGate(blocking_enabled=True, missing_confirm_frames=3),
    )
    monkeypatch.setattr(
        analyze_module,
        "subject_preflight",
        FakePreflight(
            SubjectPreflightResult(
                state="missing",
                detected=False,
                allow_shuttermuse=False,
                confidence=0,
                face_detected=False,
                reason="暂时没有找到人物",
                reason_code="no_subject_signal",
            )
        ),
    )
    client.post("/v1/analyze", json=request_payload())
    client.post("/v1/analyze", json={**request_payload(), "frame_id": 13})
    response = client.post("/v1/analyze", json={**request_payload(), "frame_id": 14})
    assert response.status_code == 200
    assert service.calls == 2
    body = response.json()
    assert body["problem"]["type"] == "subject_missing"
    assert body["actions"][0]["message"] == "把人物放进画面再试试"
    assert body.get("composition") is None


def test_default_fail_open_missing_still_calls_shuttermuse(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = FakeShutterMuseService()
    monkeypatch.setattr(analyze_module, "guidance_service", service)
    monkeypatch.setattr(
        analyze_module,
        "subject_preflight",
        FakePreflight(
            SubjectPreflightResult(
                state="missing",
                detected=False,
                allow_shuttermuse=False,
                confidence=0,
                face_detected=False,
                reason_code="no_subject_signal",
            )
        ),
    )
    response = client.post("/v1/analyze", json=request_payload())
    assert response.status_code == 200
    assert service.calls == 1
    assert response.json()["subject_preflight"]["blocked_model_call"] is False


def test_non_person_mode_skips_preflight_and_calls_shuttermuse(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = FakeShutterMuseService()
    monkeypatch.setattr(analyze_module, "guidance_service", service)
    monkeypatch.setattr(analyze_module, "subject_preflight", FakePreflight(RuntimeError("must not run")))
    payload = request_payload()
    payload["requires_person"] = False
    response = client.post("/v1/analyze", json=payload)
    assert response.status_code == 200
    assert service.calls == 1
    assert "subject_preflight" not in response.json()


def test_preflight_failure_is_not_subject_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    service = FakeShutterMuseService()
    monkeypatch.setattr(analyze_module, "guidance_service", service)
    monkeypatch.setattr(analyze_module, "subject_preflight", FakePreflight(RuntimeError("boom")))
    response = client.post("/v1/analyze", json=request_payload())
    assert response.status_code == 503
    assert service.calls == 0
    assert response.json()["error"]["code"] == "PREFLIGHT_FAILED"


@pytest.mark.parametrize(
    ("code", "message", "suggestion"),
    [
        ("MODEL_TIMEOUT", "这次分析花得有点久", "保持画面稳定，再试一次"),
        ("MODEL_SERVICE_UNAVAILABLE", "AI 暂时无法使用", "可以稍后再来试试"),
    ],
)
def test_model_errors_are_structured_without_rule_fallback(
    monkeypatch: pytest.MonkeyPatch,
    code: str,
    message: str,
    suggestion: str,
) -> None:
    service = FakeShutterMuseService(ApiError(503, code, "technical detail"))
    monkeypatch.setattr(analyze_module, "guidance_service", service)
    monkeypatch.setattr(analyze_module, "subject_preflight", FakePreflight(detected_subject()))
    response = client.post("/v1/analyze", json=request_payload())
    assert response.status_code == 503
    body = response.json()
    assert "actions" not in body
    assert body["error"]["code"] == code
    assert body["error"]["message"] == message
    assert body["error"]["suggestion"] == suggestion
    assert body["error"]["retryable"] is True
    assert body["subject_preflight"]["state"] == "confirmed"
    assert body["subject_preflight"]["detection_source"] == "face"
    assert body["timing"]["preflight_ms"] >= 0
    assert body["timing"]["guidance_ms"] >= 0
    assert body["timing"]["total_ms"] >= body["timing"]["guidance_ms"]
