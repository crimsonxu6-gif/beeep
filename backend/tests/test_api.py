from __future__ import annotations

import base64
from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from main import app
from vision.mediapipe_processor import _pose_people

client = TestClient(app)


def base_request() -> dict:
    return {
        "frame_id": 7,
        "timestamp": 1,
        "mode": "composition",
        "composition_mode": "auto",
        "target_ratio": "3:4",
        "language": "zh-CN",
        "image": {"base64": "not-base64", "width": 10, "height": 10, "mime_type": "image/jpeg"},
    }


def test_invalid_base64_returns_400_with_request_id() -> None:
    response = client.post("/v1/analyze", json=base_request())
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_BASE64"
    assert response.json()["request_id"].startswith("req_")


def test_invalid_mime_returns_400() -> None:
    payload = base_request()
    payload["image"]["mime_type"] = "image/gif"
    response = client.post("/v1/analyze", json=payload)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_MIME"


def test_missing_image_returns_422() -> None:
    payload = base_request()
    del payload["image"]
    assert client.post("/v1/analyze", json=payload).status_code == 422


def test_oversized_request_is_rejected() -> None:
    response = client.post(
        "/v1/analyze", content=b"x" * (2 * 1024 * 1024 + 1), headers={"content-type": "application/json"}
    )
    assert response.status_code == 413


def test_health_returns_request_id() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers["x-request-id"].startswith("req_")


def test_readiness_reflects_selected_rule_engine() -> None:
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["guidance_engine"] == "rules"
    assert response.json()["status"] == "ready"


def test_mediapipe_no_pose_result_is_safe() -> None:
    assert _pose_people(object(), 100, 100, None) == []


def encoded_image(width: int, height: int) -> str:
    buffer = BytesIO()
    Image.new("RGB", (width, height), "white").save(buffer, format="JPEG", quality=60)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def test_analyze_success_has_strict_response() -> None:
    payload = base_request()
    payload["image"] = {"base64": encoded_image(64, 64), "width": 64, "height": 64, "mime_type": "image/jpeg"}
    response = client.post("/v1/analyze", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["frame_id"] == 7
    assert body["guidance_engine"] == "rules"
    assert body["timing"]["total_ms"] >= 0
    assert body["composition"]["bbox_norm"]


def test_actual_pixel_limit_is_enforced() -> None:
    payload = base_request()
    payload["image"] = {
        "base64": encoded_image(1500, 1500),
        "width": 1500,
        "height": 1500,
        "mime_type": "image/jpeg",
    }
    response = client.post("/v1/analyze", json=payload)
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "IMAGE_DIMENSIONS_TOO_LARGE"
