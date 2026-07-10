from __future__ import annotations

import os

from fastapi import HTTPException

from schemas import GuidanceOutput, GuidanceRequest, VisionFeatures

from .shuttermuse import ShutterMuseGuidanceEngine
from .shuttermuse_adapter import RealShutterMuseAdapter


class GuidanceEngineService:
    def __init__(self) -> None:
        self.mode = (
            os.getenv("GUIDANCE_ENGINE", os.getenv("BEEEP_GUIDANCE_ENGINE", "rule")).strip().lower() or "rule"
        )
        self.rule_engine = ShutterMuseGuidanceEngine()
        self.real_shuttermuse: RealShutterMuseAdapter | None = None

    def infer(self, request: GuidanceRequest, features: VisionFeatures) -> GuidanceOutput:
        if self.mode in {"rule", "mock"}:
            return self.rule_engine.infer(features)

        if self.mode in {"shuttermuse", "real"}:
            return self._real_engine().infer(request, features)

        raise HTTPException(
            status_code=500,
            detail=f"Unsupported BEEEP_GUIDANCE_ENGINE mode: {self.mode}",
        )

    def status(self) -> dict[str, str | bool]:
        return {
            "mode": self.mode,
            "usesRealShutterMuse": self.mode in {"shuttermuse", "real"},
            "modelLoaded": self.real_shuttermuse is not None,
        }

    def _real_engine(self) -> RealShutterMuseAdapter:
        if self.real_shuttermuse is None:
            self.real_shuttermuse = RealShutterMuseAdapter.from_env()
        return self.real_shuttermuse
