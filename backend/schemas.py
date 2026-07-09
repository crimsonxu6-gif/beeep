from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ActionStrength = Literal["low", "medium", "high"]
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


class MoveCameraAction(BaseModel):
    type: Literal["move_camera"]
    direction: MoveDirection
    strength: ActionStrength


class AdjustPoseAction(BaseModel):
    type: Literal["adjust_pose"]
    instruction: str
    strength: ActionStrength | None = None


class FramingHintAction(BaseModel):
    type: Literal["framing_hint"]
    instruction: str
    direction: MoveDirection | None = None
    strength: ActionStrength | None = None


GuidanceAction = MoveCameraAction | AdjustPoseAction | FramingHintAction


class GuidanceOutput(BaseModel):
    frameId: int | None = None
    actions: list[GuidanceAction]
    summary: str
    confidence: float
