from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from typing import Callable, TypeVar

from fastapi import APIRouter

from core.config import settings
from core.errors import ApiError
from core.request_context import get_request_id
from core.timing_metrics import PreflightMetrics, TimingMetrics
from schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    GuidanceOutput,
    GuidanceTiming,
    SubjectPreflightResult,
    VisionFeatures,
)
from services.guidance_adapter import GuidanceAdapter
from services.service_factory import create_guidance_service
from vision.mediapipe_processor import MediaPipeVisionProcessor
from vision.subject_preflight import SubjectPreflight
from vision.subject_presence_gate import SubjectPresenceGate

router = APIRouter(prefix="/v1")
guidance_service = create_guidance_service()
vision_processor = (
    MediaPipeVisionProcessor() if guidance_service.engine_name != "shuttermuse" else None
)
subject_preflight = SubjectPreflight() if guidance_service.engine_name == "shuttermuse" else None
subject_presence_gate = SubjectPresenceGate()
guidance_adapter = GuidanceAdapter()
vision_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="mediapipe")
logger = logging.getLogger("beeep.analyze")
timing_metrics = TimingMetrics()
preflight_metrics = PreflightMetrics()
T = TypeVar("T")


def _run_with_timeout(callable_: Callable[[], T], timeout_ms: int, code: str, message: str) -> T:
    future = vision_executor.submit(callable_)
    try:
        return future.result(timeout=timeout_ms / 1000)
    except FutureTimeoutError as exc:
        future.cancel()
        raise ApiError(504, code, message) from exc


def _run_subject_preflight(request: AnalyzeRequest) -> SubjectPreflightResult:
    try:
        if subject_preflight is None:
            raise RuntimeError("subject preflight is not initialized")
        return _run_with_timeout(
            lambda: subject_preflight.analyze(request),
            settings.subject_preflight_timeout_ms,
            "PREFLIGHT_FAILED",
            "Subject preflight timed out",
        )
    except ApiError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise ApiError(503, "PREFLIGHT_FAILED", "Subject preflight failed") from exc


def _response(
    request: AnalyzeRequest,
    output: GuidanceOutput,
    *,
    features: VisionFeatures | None,
    preflight: SubjectPreflightResult | None,
    preflight_ms: int | None,
    vision_ms: int,
    guidance_ms: int,
    total_ms: int,
) -> AnalyzeResponse:
    return AnalyzeResponse(
        request_id=get_request_id(),
        frame_id=request.frame_id,
        guidance_engine=guidance_service.engine_name,
        priority=output.priority,
        problem=output.problem,
        actions=output.actions,
        message=output.actions[0].message if output.actions else output.message,
        reason=output.reason,
        summary=output.summary,
        confidence=output.confidence,
        composition=output.composition,
        pose=output.pose,
        model_metadata=output.model_metadata,
        vision_features=features,
        subject_preflight=preflight,
        timing=GuidanceTiming(
            preflight_ms=preflight_ms,
            vision_ms=vision_ms,
            guidance_ms=guidance_ms,
            total_ms=total_ms,
        ),
    )


@router.post("/analyze", response_model=AnalyzeResponse, response_model_exclude_none=True)
def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    total_started = time.perf_counter()
    features: VisionFeatures | None = None
    preflight: SubjectPreflightResult | None = None
    raw_preflight: SubjectPreflightResult | None = None
    preflight_ms: int | None = None
    vision_ms = 0
    guidance_started: float | None = None

    try:
        if guidance_service.engine_name == "shuttermuse":
            if request.requires_person and settings.subject_preflight_enabled:
                preflight_started = time.perf_counter()
                raw_preflight = _run_subject_preflight(request)
                preflight = subject_presence_gate.evaluate(
                    request.stream_id,
                    request.frame_id,
                    raw_preflight,
                )
                preflight_ms = int((time.perf_counter() - preflight_started) * 1000)
                blocked = preflight.blocked_model_call
                preflight_metrics.record(
                    preflight.state,
                    preflight.reason_code,
                    blocked,
                    detection_source=preflight.detection_source,
                    history_used=preflight.history_used,
                )
                if settings.shuttermuse_debug_output:
                    logger.info(
                        "preflight_complete request_id=%s frame_id=%s raw_state=%s "
                        "final_state=%s source=%s blocked=%s history_used=%s preflight_ms=%s",
                        get_request_id(),
                        request.frame_id,
                        raw_preflight.state,
                        preflight.state,
                        preflight.detection_source,
                        blocked,
                        preflight.history_used,
                        preflight_ms,
                    )
                if blocked:
                    output = guidance_adapter.from_subject_preflight(preflight, request.frame_id)
                    total_ms = int((time.perf_counter() - total_started) * 1000)
                    timing_metrics.record(preflight_ms=preflight_ms, guidance_ms=None)
                    return _response(
                        request,
                        output,
                        features=None,
                        preflight=preflight,
                        preflight_ms=preflight_ms,
                        vision_ms=0,
                        guidance_ms=0,
                        total_ms=total_ms,
                    )
        else:
            if vision_processor is None:
                raise ApiError(503, "VISION_UNAVAILABLE", "Vision processor is unavailable")
            vision_started = time.perf_counter()
            features = _run_with_timeout(
                lambda: vision_processor.extract_features(request),
                settings.vision_timeout_ms,
                "VISION_TIMEOUT",
                "Vision analysis timed out",
            )
            vision_ms = int((time.perf_counter() - vision_started) * 1000)

        guidance_started = time.perf_counter()
        output = guidance_service.analyze(request, features)
        guidance_ms = int((time.perf_counter() - guidance_started) * 1000)
    except ApiError as exc:
        exc.frame_id = request.frame_id
        guidance_ms = (
            int((time.perf_counter() - guidance_started) * 1000)
            if guidance_started is not None
            else None
        )
        total_ms = int((time.perf_counter() - total_started) * 1000)
        error_timing: dict[str, int] = {
            "vision_ms": vision_ms,
            "total_ms": total_ms,
        }
        if preflight_ms is not None:
            error_timing["preflight_ms"] = preflight_ms
        if guidance_ms is not None:
            error_timing["guidance_ms"] = guidance_ms
        exc.context = {
            **exc.context,
            "subject_preflight": (
                preflight.model_dump(mode="json", exclude_none=True) if preflight else None
            ),
            "timing": error_timing,
        }
        timing_metrics.record(preflight_ms=preflight_ms, guidance_ms=guidance_ms)
        raise

    total_ms = int((time.perf_counter() - total_started) * 1000)
    timing_metrics.record(preflight_ms=preflight_ms, guidance_ms=guidance_ms)
    if settings.shuttermuse_debug_output and guidance_service.engine_name == "shuttermuse":
        action_messages = [action.message for action in output.actions]
        logger.info(
            "analyze_complete request_id=%s frame_id=%s target_ratio=%s composition_mode=%s "
            "preflight=%s source=%s blocked=%s bbox_norm=%s decision=%s actions=%s "
            "preflight_ms=%s guidance_ms=%s total_ms=%s",
            get_request_id(),
            request.frame_id,
            request.target_ratio,
            request.composition_mode,
            preflight.state if preflight else None,
            preflight.detection_source if preflight else None,
            preflight.blocked_model_call if preflight else None,
            output.composition.bbox_norm if output.composition else None,
            output.composition.decision if output.composition else None,
            action_messages,
            preflight_ms,
            guidance_ms,
            total_ms,
        )
    return _response(
        request,
        output,
        features=features,
        preflight=preflight,
        preflight_ms=preflight_ms,
        vision_ms=vision_ms,
        guidance_ms=guidance_ms,
        total_ms=total_ms,
    )


@router.get("/status")
def status() -> dict[str, object]:
    return {
        **guidance_service.readiness(),
        "timing_percentiles": timing_metrics.snapshot(),
        "preflight_outcomes": preflight_metrics.snapshot(),
    }
