from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError

from fastapi import APIRouter

from core.config import settings
from core.errors import ApiError
from core.request_context import get_request_id
from schemas import AnalyzeRequest, AnalyzeResponse, GuidanceTiming
from services.service_factory import create_guidance_service
from vision.mediapipe_processor import MediaPipeVisionProcessor

router = APIRouter(prefix="/v1")
vision_processor = MediaPipeVisionProcessor()
guidance_service = create_guidance_service()
vision_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="mediapipe")
logger = logging.getLogger("beeep.analyze")


def _run_vision_with_timeout(callable_, timeout_ms: int):
    future = vision_executor.submit(callable_)
    try:
        return future.result(timeout=timeout_ms / 1000)
    except FutureTimeoutError as exc:
        future.cancel()
        raise ApiError(504, "VISION_TIMEOUT", "视觉分析超时") from exc


@router.post("/analyze", response_model=AnalyzeResponse, response_model_exclude_none=True)
def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    total_started = time.perf_counter()
    try:
        vision_started = time.perf_counter()
        features = _run_vision_with_timeout(
            lambda: vision_processor.extract_features(request),
            settings.vision_timeout_ms,
        )
        vision_ms = int((time.perf_counter() - vision_started) * 1000)

        guidance_started = time.perf_counter()
        output = guidance_service.analyze(request, features)
        guidance_ms = int((time.perf_counter() - guidance_started) * 1000)
    except ApiError as exc:
        exc.frame_id = request.frame_id
        raise

    total_ms = int((time.perf_counter() - total_started) * 1000)
    if settings.shuttermuse_debug_output and guidance_service.engine_name == "shuttermuse":
        action = output.actions[0] if output.actions else None
        logger.info(
            "analyze_complete request_id=%s frame_id=%s target_ratio=%s composition_mode=%s "
            "bbox_norm=%s decision=%s action=%s message=%s vision_ms=%s guidance_ms=%s total_ms=%s",
            get_request_id(),
            request.frame_id,
            request.target_ratio,
            request.composition_mode,
            output.composition.bbox_norm if output.composition else None,
            output.composition.decision if output.composition else None,
            action.type if action else None,
            action.message if action else None,
            vision_ms,
            guidance_ms,
            total_ms,
        )
    return AnalyzeResponse(
        request_id=get_request_id(),
        frame_id=request.frame_id,
        guidance_engine=guidance_service.engine_name,
        priority=output.priority,
        problem=output.problem,
        actions=output.actions,
        message=output.message,
        reason=output.reason,
        summary=output.summary,
        confidence=output.confidence,
        composition=output.composition,
        pose=output.pose,
        vision_features=features,
        timing=GuidanceTiming(
            vision_ms=vision_ms,
            guidance_ms=guidance_ms,
            total_ms=total_ms,
        ),
    )


@router.get("/status")
def status() -> dict[str, object]:
    return guidance_service.readiness()
