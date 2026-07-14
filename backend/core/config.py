from __future__ import annotations

import os
from dataclasses import dataclass


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _csv(name: str, default: str) -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    environment: str = os.getenv("APP_ENV", "development").lower()
    guidance_engine: str = os.getenv("GUIDANCE_ENGINE", os.getenv("BEEEP_GUIDANCE_ENGINE", "rules")).lower()
    cors_allowed_origins: tuple[str, ...] = tuple(
        _csv("CORS_ALLOWED_ORIGINS", "http://localhost:8081,http://localhost:19006")
    )
    max_image_bytes: int = int(os.getenv("MAX_IMAGE_BYTES", str(2 * 1024 * 1024)))
    max_image_edge: int = int(os.getenv("MAX_IMAGE_EDGE", "1600"))
    max_image_pixels: int = int(os.getenv("MAX_IMAGE_PIXELS", "2000000"))
    api_key: str = os.getenv("BEEEP_API_KEY", "")
    vision_timeout_ms: int = int(os.getenv("VISION_TIMEOUT_MS", "1000"))
    guidance_timeout_ms: int = int(os.getenv("GUIDANCE_TIMEOUT_MS", "17000"))
    shuttermuse_service_url: str = os.getenv("SHUTTERMUSE_SERVICE_URL", "http://127.0.0.1:8100").rstrip("/")
    shuttermuse_service_api_key: str = os.getenv("SHUTTERMUSE_SERVICE_API_KEY", "")
    shuttermuse_debug_output: bool = os.getenv("SHUTTERMUSE_DEBUG_OUTPUT", "0") == "1"
    shuttermuse_prompt_mode: str = os.getenv("SHUTTERMUSE_PROMPT_MODE", "official").lower()
    subject_preflight_enabled: bool = _bool("SUBJECT_PREFLIGHT_ENABLED", True)
    subject_preflight_confidence: float = float(os.getenv("SUBJECT_PREFLIGHT_CONFIDENCE", "0.55"))
    subject_preflight_min_area: float = float(os.getenv("SUBJECT_PREFLIGHT_MIN_AREA", "0.03"))
    subject_preflight_timeout_ms: int = int(os.getenv("SUBJECT_PREFLIGHT_TIMEOUT_MS", "800"))
    subject_preflight_blocking: bool = _bool("SUBJECT_PREFLIGHT_BLOCKING", False)
    subject_presence_ttl_ms: int = int(
        os.getenv("SUBJECT_PRESENCE_TTL_MS", os.getenv("SUBJECT_PREFLIGHT_HOLD_MS", "1500"))
    )
    subject_missing_confirm_frames: int = int(
        os.getenv(
            "SUBJECT_MISSING_CONFIRM_FRAMES",
            os.getenv("SUBJECT_PREFLIGHT_CONFIRMATION_FRAMES", "3"),
        )
    )
    subject_pose_min_visible_keypoints: int = int(
        os.getenv("SUBJECT_POSE_MIN_VISIBLE_KEYPOINTS", "4")
    )
    subject_pose_min_visibility: float = float(
        os.getenv("SUBJECT_POSE_MIN_VISIBILITY", "0.35")
    )
    subject_pose_min_area: float = float(os.getenv("SUBJECT_POSE_MIN_AREA", "0.015"))
    subject_preflight_confirmation_frames: int = int(
        os.getenv("SUBJECT_PREFLIGHT_CONFIRMATION_FRAMES", "3")
    )
    subject_preflight_hold_ms: int = int(os.getenv("SUBJECT_PREFLIGHT_HOLD_MS", "1500"))
    subject_preflight_state_ttl_ms: int = int(
        os.getenv("SUBJECT_PREFLIGHT_STATE_TTL_MS", "10000")
    )


settings = Settings()
