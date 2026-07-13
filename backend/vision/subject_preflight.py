from __future__ import annotations

import threading
from dataclasses import dataclass

import cv2
import numpy as np

from core.config import settings
from schemas import SubjectPreflightResult, VisionFeatureRequest
from vision.mediapipe_processor import (
    _clamp,
    _decode_base64_image,
    _face_box_from_detection,
    mp,
)


@dataclass(frozen=True)
class PreflightSignal:
    found: bool
    confirmed: bool
    confidence: float = 0
    bbox_norm: tuple[float, float, float, float] | None = None
    visible_keypoints: int = 0
    reason_code: str = "no_subject_signal"


class SubjectPreflight:
    """Face-first, lightweight pose-fallback subject detector for ShutterMuse."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.face_detector = None
        self.pose_detector = None
        if mp is not None:
            self.face_detector = mp.solutions.face_detection.FaceDetection(
                model_selection=0,
                min_detection_confidence=min(0.5, settings.subject_preflight_confidence),
            )
            self.pose_detector = mp.solutions.pose.Pose(
                static_image_mode=True,
                model_complexity=0,
                enable_segmentation=False,
                min_detection_confidence=settings.subject_pose_min_visibility,
            )

    def analyze(self, request: VisionFeatureRequest) -> SubjectPreflightResult:
        bgr = _decode_base64_image(request.image.base64, request.image.mime_type)
        if self.face_detector is None or self.pose_detector is None:
            raise RuntimeError("mediapipe subject detectors are unavailable")

        height, width = bgr.shape[:2]
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        face = self._detect_face(rgb, width, height)
        if face.confirmed:
            return self._result(
                state="confirmed",
                source="face",
                face=face,
                pose=None,
                reason_code="face_confirmed",
            )

        pose = self._detect_pose(rgb)
        if pose.confirmed:
            return self._result(
                state="confirmed",
                source="pose",
                face=face,
                pose=pose,
                reason_code="face_missing_pose_detected",
            )
        if pose.found:
            return self._result(
                state="uncertain",
                source="pose",
                face=face,
                pose=pose,
                reason_code="pose_partial",
                reason="partial pose signal",
            )
        if face.found:
            reason_code = face.reason_code
            reason = (
                "subject appears small"
                if reason_code == "subject_too_small"
                else "face confidence is low"
            )
            return self._result(
                state="uncertain",
                source="face",
                face=face,
                pose=pose,
                reason_code=reason_code,
                reason=reason,
            )
        return self._result(
            state="missing",
            source="none",
            face=face,
            pose=pose,
            reason_code="no_subject_signal",
            reason="no face or pose signal",
        )

    def _detect_face(self, rgb: np.ndarray, width: int, height: int) -> PreflightSignal:
        with self.lock:
            result = self.face_detector.process(rgb)
        detections = result.detections or []
        if not detections:
            return PreflightSignal(found=False, confirmed=False, reason_code="no_face")

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
        confirmed = (
            face.score >= settings.subject_preflight_confidence
            and area >= settings.subject_preflight_min_area
        )
        reason_code = (
            "face_low_confidence"
            if face.score < settings.subject_preflight_confidence
            else "subject_too_small"
            if area < settings.subject_preflight_min_area
            else "face_confirmed"
        )
        return PreflightSignal(
            found=True,
            confirmed=confirmed,
            confidence=face.score,
            bbox_norm=bbox,
            reason_code=reason_code,
        )

    def _detect_pose(self, rgb: np.ndarray) -> PreflightSignal:
        with self.lock:
            result = self.pose_detector.process(rgb)
        landmarks = getattr(result, "pose_landmarks", None)
        if not landmarks:
            return PreflightSignal(found=False, confirmed=False)

        visible = [
            landmark
            for landmark in landmarks.landmark
            if float(getattr(landmark, "visibility", 0))
            >= settings.subject_pose_min_visibility
        ]
        if not visible:
            return PreflightSignal(found=False, confirmed=False)

        xs = [_clamp(float(landmark.x), 0, 1) for landmark in visible]
        ys = [_clamp(float(landmark.y), 0, 1) for landmark in visible]
        x1, y1, x2, y2 = min(xs), min(ys), max(xs), max(ys)
        bbox = (x1, y1, x2, y2) if x1 < x2 and y1 < y2 else None
        area = (x2 - x1) * (y2 - y1) if bbox else 0
        confidence = sum(
            float(getattr(landmark, "visibility", 0)) for landmark in visible
        ) / len(visible)
        confirmed = (
            len(visible) >= settings.subject_pose_min_visible_keypoints
            and area >= settings.subject_pose_min_area
        )
        return PreflightSignal(
            found=True,
            confirmed=confirmed,
            confidence=confidence,
            bbox_norm=bbox,
            visible_keypoints=len(visible),
            reason_code="face_missing_pose_detected" if confirmed else "pose_partial",
        )

    @staticmethod
    def _result(
        *,
        state: str,
        source: str,
        face: PreflightSignal,
        pose: PreflightSignal | None,
        reason_code: str,
        reason: str | None = None,
    ) -> SubjectPreflightResult:
        active = pose if source == "pose" and pose is not None else face
        return SubjectPreflightResult(
            state=state,
            detected=state != "missing",
            allow_shuttermuse=state != "missing",
            confidence=active.confidence,
            bbox_norm=active.bbox_norm,
            face_detected=face.found,
            pose_detected=bool(pose and pose.found),
            detection_source=source,
            face_confidence=face.confidence,
            pose_confidence=pose.confidence if pose else 0,
            visible_pose_keypoints=pose.visible_keypoints if pose else 0,
            reason=reason,
            reason_code=reason_code,
        )
