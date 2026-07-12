from __future__ import annotations

from typing import Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from core.config import settings
from core.errors import ApiError
from core.request_context import get_request_id
from schemas import AnalyzeRequest


class ModelCompositionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str
    frame_id: int
    status: Literal["success", "low_confidence"]
    decision: Literal["keep", "refine", "reject"] | None = None
    bbox_norm: tuple[float, float, float, float] | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    error_code: str | None = None
    inference_ms: int = Field(ge=0)
    prompt_mode: Literal["official", "beeep_json"]
    coordinate_source: Literal[
        "bbox_norm", "bbox_1000", "bbox_pixels", "official_1000", "official_pixels"
    ] | None = None

    @model_validator(mode="after")
    def validate_bbox(self):
        if self.bbox_norm is None:
            return self
        x1, y1, x2, y2 = self.bbox_norm
        if not (0 <= x1 < x2 <= 1 and 0 <= y1 < y2 <= 1):
            raise ValueError("bbox_norm is not a valid normalized box")
        return self


class ShutterMuseModelClient:
    def __init__(self) -> None:
        self.base_url = settings.shuttermuse_service_url
        self.timeout = settings.guidance_timeout_ms / 1000
        headers = (
            {"X-API-Key": settings.shuttermuse_service_api_key}
            if settings.shuttermuse_service_api_key
            else {}
        )
        self.http = httpx.Client(base_url=self.base_url, headers=headers, timeout=self.timeout)

    def infer(self, request: AnalyzeRequest) -> ModelCompositionResult:
        if not request.image.base64:
            raise ApiError(400, "IMAGE_REQUIRED", "缺少图片", request.frame_id)
        payload = {
            "request_id": get_request_id(),
            "frame_id": request.frame_id,
            "image_base64": request.image.base64,
            "mime_type": request.image.mime_type,
            "target_ratio": request.target_ratio,
            "composition_mode": request.composition_mode,
            "mode": "composition",
            "language": request.language,
            "prompt_mode": settings.shuttermuse_prompt_mode,
        }
        try:
            response = self.http.post(
                "/v1/photographer/analyze",
                json=payload,
            )
        except httpx.TimeoutException as exc:
            raise ApiError(504, "MODEL_TIMEOUT", "ShutterMuse inference timed out", request.frame_id) from exc
        except httpx.HTTPError as exc:
            raise ApiError(
                503,
                "MODEL_SERVICE_UNAVAILABLE",
                "ShutterMuse model service is unavailable",
                request.frame_id,
            ) from exc

        if response.status_code >= 400:
            defaults = {
                429: "MODEL_BUSY",
                503: "MODEL_LOADING",
                504: "MODEL_TIMEOUT",
            }
            code = defaults.get(response.status_code, "MODEL_SERVICE_FAILED")
            try:
                detail = response.json().get("detail", {})
                code = detail.get("code", code)
            except ValueError:
                pass
            if code == "MODEL_NOT_READY":
                code = "MODEL_LOADING"
            raise ApiError(
                response.status_code,
                code,
                "ShutterMuse model service rejected the request",
                request.frame_id,
            )
        try:
            return ModelCompositionResult.model_validate(response.json())
        except (ValueError, ValidationError) as exc:
            raise ApiError(
                502,
                "INVALID_MODEL_OUTPUT",
                "Invalid ShutterMuse output",
                request.frame_id,
            ) from exc

    def readiness(self) -> dict[str, object]:
        try:
            response = self.http.get("/ready", timeout=2.0)
            payload = response.json()
            if response.status_code >= 400 and isinstance(payload.get("detail"), dict):
                return payload["detail"]
            return payload
        except (httpx.HTTPError, ValueError):
            return {
                "status": "error",
                "guidance_engine": "shuttermuse",
                "model_loaded": False,
                "warmup_completed": False,
                "error_code": "MODEL_SERVICE_UNAVAILABLE",
            }
