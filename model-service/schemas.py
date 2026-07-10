from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PhotographerRequest(StrictModel):
    request_id: str = Field(min_length=1, max_length=80)
    frame_id: int = Field(ge=1)
    image_base64: str = Field(min_length=1, max_length=3_000_000)
    mime_type: Literal["image/jpeg", "image/webp", "image/png"]
    target_ratio: Literal["1:1", "3:4", "4:3", "9:16", "16:9"]
    composition_mode: Literal[
        "auto", "center", "thirds_left", "thirds_right", "portrait_closeup", "full_body"
    ]
    mode: Literal["composition"] = "composition"
    language: Literal["zh-CN"] = "zh-CN"


class PhotographerResponse(StrictModel):
    request_id: str
    frame_id: int
    status: Literal["success", "low_confidence"]
    decision: Literal["keep", "refine", "reject"] | None = None
    bbox_norm: tuple[float, float, float, float] | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    error_code: str | None = None
    inference_ms: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_bbox(self):
        if self.bbox_norm is None:
            return self
        x1, y1, x2, y2 = self.bbox_norm
        if not (0 <= x1 < x2 <= 1 and 0 <= y1 < y2 <= 1):
            raise ValueError("bbox_norm is not a valid normalized box")
        return self


class ReadinessResponse(StrictModel):
    status: Literal["unconfigured", "loading", "ready", "error"]
    guidance_engine: Literal["shuttermuse"] = "shuttermuse"
    model_loaded: bool
    processor_loaded: bool
    warmup_completed: bool
    device: str
    model_name: str
    load_count: int
    inference_count: int
    executor_active: bool
    executor_pending: int
    error_code: str | None = None
    error_message: str | None = None
