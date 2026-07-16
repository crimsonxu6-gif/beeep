from __future__ import annotations

from io import BytesIO
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from api import debug_analyze
from main import app as production_shaped_app


def _jpeg() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (64, 64), "white").save(buffer, format="JPEG")
    return buffer.getvalue()


def _client(monkeypatch, delay_ms: int = 1) -> TestClient:
    monkeypatch.setattr(
        debug_analyze,
        "settings",
        SimpleNamespace(
            environment="development",
            debug_analyze_endpoint_enabled=True,
            debug_analyze_delay_ms=delay_ms,
        ),
    )
    test_app = FastAPI()
    test_app.include_router(debug_analyze.router)
    return TestClient(test_app)


def _post(client: TestClient, scenario: str):
    return client.post(
        f"/v1/debug/analyze-response?scenario={scenario}",
        data={"frame_id": "91"},
        files={"image": ("analysis.jpg", _jpeg(), "image/jpeg")},
    )


def test_debug_endpoint_is_not_mounted_by_default() -> None:
    response = TestClient(production_shaped_app).post("/v1/debug/analyze-response")
    assert response.status_code == 404


def test_debug_endpoint_cannot_be_enabled_in_production() -> None:
    assert debug_analyze.debug_endpoint_enabled("development", True) is True
    assert debug_analyze.debug_endpoint_enabled("production", True) is False
    assert debug_analyze.debug_endpoint_enabled("development", False) is False


def test_debug_endpoint_returns_real_success_and_delayed_success(monkeypatch) -> None:
    client = _client(monkeypatch)
    for scenario in ("success", "delayed_success"):
        response = _post(client, scenario)
        assert response.status_code == 200
        assert response.json()["frame_id"] == 91
        assert response.json()["composition"]["bbox_norm"] == [0.15, 0.1, 0.8, 0.9]


def test_debug_endpoint_returns_requested_http_statuses(monkeypatch) -> None:
    client = _client(monkeypatch)
    for status_code in (500, 502, 503, 504):
        response = _post(client, f"http_{status_code}")
        assert response.status_code == status_code
        assert response.json()["error"]["code"] == f"HTTP_{status_code}"


def test_debug_endpoint_returns_invalid_json_and_missing_bbox(monkeypatch) -> None:
    client = _client(monkeypatch)
    invalid = _post(client, "invalid_json")
    assert invalid.status_code == 200
    assert invalid.text == "{invalid-json"

    missing_bbox = _post(client, "missing_bbox")
    assert missing_bbox.status_code == 200
    assert "composition" not in missing_bbox.json()


def test_debug_endpoint_returns_bbox_safety_error(monkeypatch) -> None:
    response = _post(_client(monkeypatch), "bbox_safety_rejected")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "BBOX_SAFETY_REJECTED"
