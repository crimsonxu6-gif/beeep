from __future__ import annotations

from fastapi import HTTPException

from core.config import settings
from services.base import PhotographyGuidanceService
from services.rule_guidance_service import RuleGuidanceService
from services.shuttermuse_service import ShutterMuseGuidanceService


def create_guidance_service(mode: str | None = None) -> PhotographyGuidanceService:
    selected = (mode or settings.guidance_engine).lower()
    if selected in {"rule", "rules", "mock"}:
        return RuleGuidanceService()
    if selected in {"shuttermuse", "real"}:
        return ShutterMuseGuidanceService()
    raise HTTPException(status_code=500, detail=f"Unsupported GUIDANCE_ENGINE: {selected}")
