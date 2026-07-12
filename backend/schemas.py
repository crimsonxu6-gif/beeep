from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

StrictModelConfig = ConfigDict(extra="forbid", populate_by_name=True)
ActionStrength = Literal["low", "medium", "high"]
GuidancePriority = Literal[
    "subject", "lighting", "composition", "pose", "camera", "distance", "angle", "hold"
]
CompositionMode = Literal["auto", "center", "thirds_left", "thirds_right", "portrait_closeup", "full_body"]
FacePosition = Literal["left", "center", "right", "unknown"]
FaceSize = Literal["small", "medium", "large", "unknown"]
SceneBrightness = Literal["normal", "low_light", "backlight", "overexposed"]
SceneClutter = Literal["low", "medium", "high"]


class StrictModel(BaseModel):
    model_config = StrictModelConfig


class ImagePayload(StrictModel):
    base64: str | None = None
    uri: str | None = None
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    mime_type: str = Field(default="image/jpeg", max_length=32)


class VisionFeatureRequest(StrictModel):
    frame_id: int = Field(ge=1)
    timestamp: int = Field(ge=0)
    image: ImagePayload


class AnalyzeRequest(VisionFeatureRequest):
    mode: Literal["composition", "portrait", "general"] = "composition"
    composition_mode: CompositionMode = "auto"
    target_ratio: Literal["1:1", "3:4", "4:3", "9:16", "16:9"] = "3:4"
    language: Literal["zh-CN"] = "zh-CN"
    requires_person: bool = True
    stream_id: str = Field(default="legacy", min_length=1, max_length=64)


class ImageSize(StrictModel):
    width: int
    height: int


class PoseKeypoint(StrictModel):
    name: str
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    score: float | None = Field(default=None, ge=0, le=1)


class PersonDetection(StrictModel):
    id: str
    bbox: tuple[float, float, float, float]
    keypoints: list[PoseKeypoint] = Field(default_factory=list)
    score: float = Field(ge=0, le=1)


class FaceFeatures(StrictModel):
    position: FacePosition
    size: FaceSize


class SceneFeatures(StrictModel):
    brightness: SceneBrightness
    clutter: SceneClutter


class VisionFeatures(StrictModel):
    frameId: int
    imageSize: ImageSize
    people: list[PersonDetection] = Field(default_factory=list)
    face: FaceFeatures
    scene: SceneFeatures
    preprocessingLatencyMs: int = Field(ge=0)


class GuidanceRequest(VisionFeatureRequest):
    vision_features: VisionFeatures | None = None


class GuidanceProblem(StrictModel):
    type: str = Field(max_length=40)
    description: str = Field(max_length=48)


class GuidanceActionBase(StrictModel):
    message: str = Field(max_length=16)
    confidence: float | None = Field(default=None, ge=0, le=1)
    strength: ActionStrength | None = None


class MoveCameraAction(GuidanceActionBase):
    type: Literal["move_camera"]
    direction: Literal["left", "right", "up", "down"]


class AdjustDistanceAction(GuidanceActionBase):
    type: Literal["adjust_distance"]
    direction: Literal["closer", "farther"]


class AdjustAngleAction(GuidanceActionBase):
    type: Literal["adjust_angle"]
    direction: Literal["lower", "raise", "tilt_left", "tilt_right", "straighten"]


class AdjustPoseAction(GuidanceActionBase):
    type: Literal["adjust_pose"]


class FramingHintAction(GuidanceActionBase):
    type: Literal["framing_hint"]


class LightingHintAction(GuidanceActionBase):
    type: Literal["lighting_hint"]


class HoldAction(GuidanceActionBase):
    type: Literal["hold"]


GuidanceAction = Annotated[
    MoveCameraAction
    | AdjustDistanceAction
    | AdjustAngleAction
    | AdjustPoseAction
    | FramingHintAction
    | LightingHintAction
    | HoldAction,
    Field(discriminator="type"),
]


class CompositionRecommendation(StrictModel):
    decision: Literal["keep", "refine", "reject"]
    bbox_norm: tuple[float, float, float, float]

    @model_validator(mode="after")
    def validate_bbox(self):
        x1, y1, x2, y2 = self.bbox_norm
        if not (0 <= x1 < x2 <= 1 and 0 <= y1 < y2 <= 1):
            raise ValueError("bbox_norm must satisfy 0 <= x1 < x2 <= 1 and 0 <= y1 < y2 <= 1")
        return self


class TargetPoseKeypoint(StrictModel):
    name: str
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    visibility: float = Field(ge=0, le=1)


class PoseRecommendation(StrictModel):
    keypoints: list[TargetPoseKeypoint] = Field(min_length=17, max_length=17)
    keypoint_count: Literal[17]


class GuidanceTiming(StrictModel):
    preflight_ms: int | None = Field(default=None, ge=0)
    vision_ms: int = Field(ge=0)
    guidance_ms: int = Field(ge=0)
    total_ms: int = Field(ge=0)


class GuidanceOutput(StrictModel):
    frameId: int | None = None
    priority: GuidancePriority
    problem: GuidanceProblem
    actions: list[GuidanceAction] = Field(max_length=2)
    message: str = Field(max_length=16)
    reason: str = Field(max_length=80)
    summary: str = Field(max_length=32)
    confidence: float = Field(ge=0, le=1)
    composition: CompositionRecommendation | None = None
    pose: PoseRecommendation | None = None


class SubjectPreflightResult(StrictModel):
    state: Literal["detected", "uncertain", "missing"]
    detected: bool
    allow_shuttermuse: bool
    confidence: float = Field(ge=0, le=1)
    bbox_norm: tuple[float, float, float, float] | None = None
    face_detected: bool
    reason: str | None = Field(default=None, max_length=48)
    reason_code: Literal[
        "face_confirmed",
        "face_low_confidence",
        "subject_too_small",
        "no_face",
        "recent_subject",
        "confirming_subject",
    ]

    @model_validator(mode="after")
    def validate_bbox(self):
        if self.bbox_norm is None:
            return self
        x1, y1, x2, y2 = self.bbox_norm
        if not (0 <= x1 < x2 <= 1 and 0 <= y1 < y2 <= 1):
            raise ValueError("bbox_norm must be normalized xyxy coordinates")
        return self


class AnalyzeResponse(StrictModel):
    request_id: str
    frame_id: int
    status: Literal["success"] = "success"
    guidance_engine: str
    priority: GuidancePriority
    problem: GuidanceProblem
    actions: list[GuidanceAction] = Field(max_length=2)
    message: str = Field(max_length=16)
    reason: str = Field(max_length=80)
    summary: str = Field(max_length=32)
    confidence: float = Field(ge=0, le=1)
    composition: CompositionRecommendation | None = None
    pose: PoseRecommendation | None = None
    vision_features: VisionFeatures | None = None
    subject_preflight: SubjectPreflightResult | None = None
    timing: GuidanceTiming
