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
    prompt_mode: Literal[
        "official", "official_bbox_first", "official_prefill", "beeep_json"
    ] = "official"


class GenerationConfigMetadata(StrictModel):
    do_sample: Literal[False] = False
    num_beams: Literal[1] = 1
    max_new_tokens: int = Field(ge=1, le=512)
    attention_implementation: Literal["default", "sdpa", "flash_attention_2"]


class PhotographerResponse(StrictModel):
    request_id: str
    frame_id: int
    status: Literal["success", "low_confidence"]
    decision: Literal["keep", "refine", "reject"] | None = None
    bbox_norm: tuple[float, float, float, float] | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    error_code: str | None = None
    inference_ms: int = Field(ge=0)
    prompt_mode: Literal[
        "official", "official_bbox_first", "official_prefill", "beeep_json"
    ]
    coordinate_source: Literal[
        "bbox_norm",
        "bbox_1000",
        "bbox_pixels",
        "official_1000_pairs",
        "official_pixels_pairs",
        "official_1000_list",
        "official_pixels_list",
        "official_1000_json_bbox",
        "official_pixels_json_bbox",
        "official_1000_composition_bbox",
        "official_pixels_composition_bbox",
        "official_1000_composition_xy",
        "official_pixels_composition_xy",
        "official_1000_partial_bbox",
        "official_pixels_partial_bbox",
        "official_1000_partial_composition_bbox",
        "official_pixels_partial_composition_bbox",
        "official_1000_partial_composition_xy",
        "official_pixels_partial_composition_xy",
    ] | None = None
    raw_output: str | None = Field(default=None, max_length=4000)
    raw_output_length: int | None = Field(default=None, ge=0)
    generated_token_count: int = Field(ge=0)
    reached_max_new_tokens: bool
    stopped_by_structure: bool
    stop_reason: Literal["bbox_field", "json", "coordinate_pairs"] | None = None
    stopped_by_bbox_field: bool = False
    stopped_by_json: bool = False
    stopped_by_coordinate_pairs: bool = False
    partial_structure_used: bool = False
    json_complete: bool = False
    bbox_field_complete: bool = False
    parse_failure_type: str | None = None
    parser_comparison: Literal[
        "both_success",
        "beeep_only_success",
        "official_only_success",
        "both_failed",
        "official_unavailable",
    ]
    generation_config: GenerationConfigMetadata

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
    runtime_ready: bool
    quality_ready: bool
    readiness_warning: str | None = None
    device: str
    model_name: str
    load_count: int
    inference_count: int
    executor_active: bool
    executor_pending: int
    prompt_mode: str
    assistant_prefill: str | None = None
    official_coordinate_format: str
    attention_implementation: str
    input_short_edge: int
    generation_config: GenerationConfigMetadata
    error_code: str | None = None
    error_message: str | None = None
