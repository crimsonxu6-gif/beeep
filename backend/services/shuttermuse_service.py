from __future__ import annotations

from model.shuttermuse_adapter import RealShutterMuseAdapter
from schemas import AnalyzeRequest, GuidanceOutput, VisionFeatures
from services.guidance_adapter import GuidanceAdapter


class ShutterMuseGuidanceService:
    engine_name = "shuttermuse"

    def __init__(self) -> None:
        self.adapter: RealShutterMuseAdapter | None = None
        self.guidance_adapter = GuidanceAdapter()

    def analyze(self, request: AnalyzeRequest, vision_features: VisionFeatures) -> GuidanceOutput:
        if self.adapter is None:
            self.adapter = RealShutterMuseAdapter.from_env()
        output = self.adapter.infer(request, vision_features)
        return self.guidance_adapter.adapt(output, request, vision_features)

    @property
    def model_loaded(self) -> bool:
        return self.adapter is not None
