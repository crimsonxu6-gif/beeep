from __future__ import annotations

import base64
import threading
import time
from dataclasses import dataclass

import cv2
import numpy as np
from fastapi import HTTPException

from core.config import settings
from core.errors import ApiError
from schemas import (
    FaceFeatures,
    ImageSize,
    PersonDetection,
    PoseKeypoint,
    SceneFeatures,
    VisionFeatureRequest,
    VisionFeatures,
)

try:
    import mediapipe as mp
except ImportError:  # pragma: no cover - runtime dependency check
    mp = None


@dataclass
class FaceBox:
    x: float
    y: float
    width: float
    height: float
    score: float


POSE_KEYPOINTS = {
    "nose": 0,
    "left_shoulder": 11,
    "right_shoulder": 12,
    "left_elbow": 13,
    "right_elbow": 14,
    "left_wrist": 15,
    "right_wrist": 16,
    "left_hip": 23,
    "right_hip": 24,
}


def _decode_base64_image(value: str | None, mime_type: str) -> np.ndarray:
    if mime_type not in {"image/jpeg", "image/webp", "image/png"}:
        raise ApiError(400, "INVALID_MIME", "不支持的图片格式")
    if not value:
        raise ApiError(400, "IMAGE_REQUIRED", "缺少图片")

    raw = value.split(",", 1)[1] if "," in value and "base64" in value[:40] else value
    try:
        image_bytes = base64.b64decode(raw, validate=True)
    except Exception as exc:  # noqa: BLE001
        raise ApiError(400, "INVALID_BASE64", "图片数据无效") from exc

    if len(image_bytes) > settings.max_image_bytes:
        raise ApiError(413, "IMAGE_TOO_LARGE", "图片超过 2 MB")

    encoded = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    if image is None:
        raise ApiError(400, "INVALID_IMAGE", "图片无法解码")

    height, width = image.shape[:2]
    if max(width, height) > settings.max_image_edge or width * height > settings.max_image_pixels:
        raise ApiError(413, "IMAGE_DIMENSIONS_TOO_LARGE", "图片尺寸过大")

    return image


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _classify_face_position(center_x: float, width: int) -> str:
    ratio = center_x / width if width else 0.5
    if ratio < 0.42:
        return "left"
    if ratio > 0.58:
        return "right"
    return "center"


def _classify_face_size(face_height: float, height: int) -> str:
    ratio = face_height / height if height else 0
    if ratio < 0.18:
        return "small"
    if ratio > 0.42:
        return "large"
    return "medium"


def _scene_brightness(gray: np.ndarray, face: FaceBox | None) -> str:
    mean = float(gray.mean())
    if mean < 65:
        return "low_light"
    if mean > 210:
        return "overexposed"

    if face:
        x1 = int(_clamp(face.x, 0, gray.shape[1] - 1))
        y1 = int(_clamp(face.y, 0, gray.shape[0] - 1))
        x2 = int(_clamp(face.x + face.width, x1 + 1, gray.shape[1]))
        y2 = int(_clamp(face.y + face.height, y1 + 1, gray.shape[0]))
        face_mean = float(gray[y1:y2, x1:x2].mean()) if x2 > x1 and y2 > y1 else mean
        if mean > 120 and face_mean < mean * 0.68:
            return "backlight"

    return "normal"


def _scene_clutter(gray: np.ndarray) -> str:
    edges = cv2.Canny(gray, 80, 160)
    density = float(np.count_nonzero(edges)) / float(edges.size)
    if density > 0.12:
        return "high"
    if density > 0.06:
        return "medium"
    return "low"


def _face_box_from_detection(detection: object, width: int, height: int) -> FaceBox:
    location = detection.location_data.relative_bounding_box
    x = _clamp(location.xmin * width, 0, width)
    y = _clamp(location.ymin * height, 0, height)
    box_width = _clamp(location.width * width, 0, width - x)
    box_height = _clamp(location.height * height, 0, height - y)
    score = float(detection.score[0]) if detection.score else 0
    return FaceBox(x=x, y=y, width=box_width, height=box_height, score=score)


def _pose_people(pose_result: object, width: int, height: int, face: FaceBox | None) -> list[PersonDetection]:
    landmarks = getattr(pose_result, "pose_landmarks", None)
    if not landmarks:
        if not face:
            return []

        person_width = min(width, face.width * 2.2)
        person_height = min(height, face.height * 3.4)
        left = _clamp(face.x + face.width / 2 - person_width / 2, 0, width - person_width)
        top = _clamp(face.y - face.height * 0.2, 0, height - person_height)
        return [
            PersonDetection(
                id="primary",
                bbox=(left / width, top / height, person_width / width, person_height / height),
                keypoints=[],
                score=face.score,
            )
        ]

    visible = [landmark for landmark in landmarks.landmark if getattr(landmark, "visibility", 1.0) >= 0.4]
    if not visible:
        return []

    xs = [float(landmark.x) * width for landmark in visible]
    ys = [float(landmark.y) * height for landmark in visible]
    left = _clamp(min(xs), 0, width)
    top = _clamp(min(ys), 0, height)
    right = _clamp(max(xs), left, width)
    bottom = _clamp(max(ys), top, height)

    keypoints: list[PoseKeypoint] = []
    for name, index in POSE_KEYPOINTS.items():
        landmark = landmarks.landmark[index]
        keypoints.append(
            PoseKeypoint(
                name=name,
                x=_clamp(float(landmark.x), 0, 1),
                y=_clamp(float(landmark.y), 0, 1),
                score=float(getattr(landmark, "visibility", 1.0)),
            )
        )

    score = sum(float(getattr(landmark, "visibility", 1.0)) for landmark in visible) / len(visible)
    return [
        PersonDetection(
            id="primary",
            bbox=(
                left / width,
                top / height,
                max(1.0, right - left) / width,
                max(1.0, bottom - top) / height,
            ),
            keypoints=keypoints,
            score=score,
        )
    ]


class MediaPipeVisionProcessor:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.face_detector = None
        self.pose_detector = None
        if mp is not None:
            self.face_detector = mp.solutions.face_detection.FaceDetection(
                model_selection=0, min_detection_confidence=0.5
            )
            self.pose_detector = mp.solutions.pose.Pose(
                static_image_mode=True,
                model_complexity=0,
                enable_segmentation=False,
                min_detection_confidence=0.5,
            )

    def extract_features(self, request: VisionFeatureRequest) -> VisionFeatures:
        started_at = time.perf_counter()
        bgr = _decode_base64_image(request.image.base64, request.image.mime_type)
        if mp is None:
            raise HTTPException(
                status_code=503,
                detail="mediapipe is not installed. Run `pip install -r backend/requirements.txt`.",
            )
        height, width = bgr.shape[:2]
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

        face_box: FaceBox | None = None
        with self.lock:
            face_result = self.face_detector.process(rgb)
            detections = face_result.detections or []
            if detections:
                face_box = _face_box_from_detection(detections[0], width, height)
            pose_result = self.pose_detector.process(rgb)

        people = _pose_people(pose_result, width, height, face_box)
        if face_box:
            face = FaceFeatures(
                position=_classify_face_position(face_box.x + face_box.width / 2, width),
                size=_classify_face_size(face_box.height, height),
            )
        else:
            face = FaceFeatures(position="unknown", size="unknown")

        return VisionFeatures(
            frameId=request.frame_id,
            imageSize=ImageSize(width=width, height=height),
            people=people,
            face=face,
            scene=SceneFeatures(
                brightness=_scene_brightness(gray, face_box),
                clutter=_scene_clutter(gray),
            ),
            preprocessingLatencyMs=int((time.perf_counter() - started_at) * 1000),
        )
