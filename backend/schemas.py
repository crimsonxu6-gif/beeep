from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ActionStrength = Literal["low", "medium", "high"]
GuidancePriority = Literal["subject", "lighting", "composition", "pose", "camera", "distance", "angle", "hold"]
MoveDirection = Literal["left", "right", "up", "down", "forward", "back", "hold"]
FacePosition = Literal["left", "center", "right", "unknown"]
FaceSize = Literal["small", "medium", "large", "unknown"]
SceneBrightness = Literal["normal", "low_light", "backlight", "overexposed"]
SceneClutter = Literal["low", "medium", "high"]


class ImagePayload(BaseModel):
    base64: str | None = None
    uri: str | None = None
    width: int
    height: int
    mime_type: str = Field(default="image/jpeg", alias="mime_type")


class VisionFeatureRequest(BaseModel):
    frame_id: int = Field(alias="frame_id")
    timestamp: int
    image: ImagePayload


class ImageSize(BaseModel):
    width: int
    height: int


class PoseKeypoint(BaseModel):
    name: str
    x: float
    y: float
    score: float | None = None


class PersonDetection(BaseModel):
    id: str
    bbox: tuple[float, float, float, float]
    keypoints: list[PoseKeypoint] = Field(default_factory=list)
    score: float


class FaceFeatures(BaseModel):
    position: FacePosition
    size: FaceSize


class SceneFeatures(BaseModel):
    brightness: SceneBrightness
    clutter: SceneClutter


class VisionFeatures(BaseModel):
    frameId: int
    imageSize: ImageSize
    people: list[PersonDetection] = Field(default_factory=list)
    face: FaceFeatures
    scene: SceneFeatures
    preprocessingLatencyMs: int


class GuidanceRequest(VisionFeatureRequest):
    vision_features: VisionFeatures | None = Field(default=None, alias="vision_features")


class GuidanceProblem(BaseModel):
    type: str = Field(max_length=40)
    description: str = Field(max_length=48)


class GuidanceActionBase(BaseModel):
    message: str = Field(max_length=10)
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


GuidanceAction = (
    MoveCameraAction
    | AdjustDistanceAction
    | AdjustAngleAction
    | AdjustPoseAction
    | FramingHintAction
    | LightingHintAction
    | HoldAction
)


class GuidanceOutput(BaseModel):
    frameId: int | None = None
    priority: GuidancePriority
    problem: GuidanceProblem
    actions: list[GuidanceAction] = Field(max_length=2)
    message: str = Field(max_length=10)
    reason: str = Field(max_length=80)
    summary: str = Field(max_length=32)
    confidence: float = Field(ge=0, le=1)
