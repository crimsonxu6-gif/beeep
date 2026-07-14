from __future__ import annotations

import logging

from core.config import settings
from core.errors import ApiError
from core.request_context import get_request_id
from schemas import AnalyzeRequest, GuidanceOutput, ModelEvaluationMetadata, VisionFeatures
from services.guidance_adapter import GuidanceAdapter
from services.shuttermuse_client import ShutterMuseModelClient

logger = logging.getLogger("beeep.shuttermuse")


class ShutterMuseGuidanceService:
    engine_name = "shuttermuse"

    def __init__(self) -> None:
        self.client = ShutterMuseModelClient()
        self.guidance_adapter = GuidanceAdapter()

    def analyze(self, request: AnalyzeRequest, vision_features: VisionFeatures | None) -> GuidanceOutput:
        model_result = self.client.infer(request)
        metadata = ModelEvaluationMetadata(
            prompt_mode=model_result.prompt_mode,
            coordinate_source=model_result.coordinate_source,
            decision=model_result.decision,
            bbox_norm=model_result.bbox_norm,
            confidence=model_result.confidence,
            inference_ms=model_result.inference_ms,
            raw_output=model_result.raw_output,
            raw_output_length=model_result.raw_output_length,
            generated_token_count=model_result.generated_token_count,
            reached_max_new_tokens=model_result.reached_max_new_tokens,
            stopped_by_structure=model_result.stopped_by_structure,
            parse_failure_type=model_result.parse_failure_type,
            parser_comparison=model_result.parser_comparison,
            generation_config=model_result.generation_config,
        )
        if model_result.status != "success":
            error = ApiError(
                502,
                model_result.error_code or "INVALID_MODEL_OUTPUT",
                "ShutterMuse returned a low-confidence result",
                request.frame_id,
            )
            error.context["model_metadata"] = metadata.model_dump(
                mode="json", exclude_none=True
            )
            raise error
        output = self.guidance_adapter.from_model_composition(
            model_result,
            frame_id=request.frame_id,
        )
        output = output.model_copy(
            update={
                "model_metadata": metadata
            }
        )
        if settings.shuttermuse_debug_output:
            action = output.actions[0] if output.actions else None
            logger.info(
                "guidance_debug request_id=%s frame_id=%s target_ratio=%s composition_mode=%s "
                "bbox_norm=%s decision=%s action=%s message=%s model_ms=%s",
                get_request_id(),
                request.frame_id,
                request.target_ratio,
                request.composition_mode,
                model_result.bbox_norm,
                model_result.decision,
                action.type if action else None,
                action.message if action else None,
                model_result.inference_ms,
            )
        return output

    def readiness(self) -> dict[str, object]:
        return self.client.readiness()
