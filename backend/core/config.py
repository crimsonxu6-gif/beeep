from __future__ import annotations

import os
from dataclasses import dataclass


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


settings = Settings()
