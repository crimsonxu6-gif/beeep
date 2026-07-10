from __future__ import annotations

from core.config import settings
from schemas import AnalyzeRequest, GuidanceOutput, GuidanceRequest, VisionFeatures
from services.service_factory import create_guidance_service


class GuidanceEngineService:
    """Compatibility wrapper for the legacy /guidance endpoint."""

    def __init__(self) -> None:
        self.engine = create_guidance_service(settings.guidance_engine)

    def infer(self, request: GuidanceRequest, features: VisionFeatures) -> GuidanceOutput:
        analyze_request = AnalyzeRequest(
            frame_id=request.frame_id,
            timestamp=request.timestamp,
            image=request.image,
            mode="composition",
            composition_mode="auto",
            target_ratio="3:4",
            language="zh-CN",
        )
        return self.engine.analyze(analyze_request, features)

    def status(self) -> dict[str, object]:
        return self.engine.readiness()
