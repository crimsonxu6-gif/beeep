from __future__ import annotations

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


def _with_timeout(callable_, timeout_ms: int, code: str, message: str):
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(callable_)
    try:
        return future.result(timeout=timeout_ms / 1000)
    except FutureTimeoutError as exc:
        future.cancel()
        raise ApiError(504, code, message) from exc
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


@router.post("/analyze", response_model=AnalyzeResponse, response_model_exclude_none=True)
def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    total_started = time.perf_counter()
    try:
        vision_started = time.perf_counter()
        features = _with_timeout(
            lambda: vision_processor.extract_features(request),
            settings.vision_timeout_ms,
            "VISION_TIMEOUT",
            "视觉分析超时",
        )
        vision_ms = int((time.perf_counter() - vision_started) * 1000)

        guidance_started = time.perf_counter()
        output = _with_timeout(
            lambda: guidance_service.analyze(request, features),
            settings.guidance_timeout_ms,
            "GUIDANCE_TIMEOUT",
            "AI 构图超时",
        )
        guidance_ms = int((time.perf_counter() - guidance_started) * 1000)
    except ApiError as exc:
        exc.frame_id = request.frame_id
        raise

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
            total_ms=int((time.perf_counter() - total_started) * 1000),
        ),
    )


@router.get("/status")
def status() -> dict[str, str | bool]:
    return {"status": "ready", "guidance_engine": guidance_service.engine_name}
