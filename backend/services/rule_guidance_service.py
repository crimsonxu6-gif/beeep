from __future__ import annotations

from model.shuttermuse import ShutterMuseGuidanceEngine
from schemas import AnalyzeRequest, GuidanceOutput, VisionFeatures
from services.guidance_adapter import GuidanceAdapter


class RuleGuidanceService:
    engine_name = "rules"

    def __init__(self) -> None:
        self.engine = ShutterMuseGuidanceEngine()
        self.adapter = GuidanceAdapter()

    def analyze(self, request: AnalyzeRequest, vision_features: VisionFeatures) -> GuidanceOutput:
        output = self.engine.infer(vision_features, request.composition_mode)
        return self.adapter.adapt(output, request, vision_features)
