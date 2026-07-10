from __future__ import annotations

from typing import Protocol

from schemas import AnalyzeRequest, GuidanceOutput, VisionFeatures


class PhotographyGuidanceService(Protocol):
    engine_name: str

    def analyze(self, request: AnalyzeRequest, vision_features: VisionFeatures) -> GuidanceOutput: ...

    def readiness(self) -> dict[str, object]: ...
