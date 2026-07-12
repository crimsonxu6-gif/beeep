from __future__ import annotations

import threading

import cv2

from core.config import settings
from schemas import SubjectPreflightResult, VisionFeatureRequest
from vision.mediapipe_processor import (
    _clamp,
    _decode_base64_image,
    _face_box_from_detection,
    mp,
)


class SubjectPreflight:
    """Lightweight person preflight for ShutterMuse; intentionally face-only."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.face_detector = None
        if mp is not None:
            self.face_detector = mp.solutions.face_detection.FaceDetection(
                model_selection=0,
                min_detection_confidence=min(0.5, settings.subject_preflight_confidence),
            )

    def analyze(self, request: VisionFeatureRequest) -> SubjectPreflightResult:
        bgr = _decode_base64_image(request.image.base64, request.image.mime_type)
        if self.face_detector is None:
            raise RuntimeError("mediapipe face detector is unavailable")

        height, width = bgr.shape[:2]
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        with self.lock:
            result = self.face_detector.process(rgb)
        detections = result.detections or []
        if not detections:
            return SubjectPreflightResult(
                detected=False,
                confidence=0,
                face_detected=False,
                reason="暂时没有找到人物",
            )

        detection = max(detections, key=lambda item: float(item.score[0]) if item.score else 0)
        face = _face_box_from_detection(detection, width, height)
        person_width = min(float(width), face.width * 2.2)
        person_height = min(float(height), face.height * 3.4)
        left = _clamp(face.x + face.width / 2 - person_width / 2, 0, width - person_width)
        top = _clamp(face.y - face.height * 0.2, 0, height - person_height)
        bbox = (
            left / width,
            top / height,
            (left + person_width) / width,
            (top + person_height) / height,
        )
        area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
        detected = (
            face.score >= settings.subject_preflight_confidence
            and area >= settings.subject_preflight_min_area
        )
        reason = None
        if face.score < settings.subject_preflight_confidence:
            reason = "人物还不够清晰"
        elif area < settings.subject_preflight_min_area:
            reason = "人物在画面中太小"

        return SubjectPreflightResult(
            detected=detected,
            confidence=face.score,
            bbox_norm=bbox,
            face_detected=True,
            reason=reason,
        )
