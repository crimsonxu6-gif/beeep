from __future__ import annotations

import logging
from concurrent.futures import TimeoutError as FutureTimeoutError
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse

from config import settings
from engine import ModelServiceError, ShutterMuseEngine
from executor import LatestPendingExecutor, ModelRequestSuperseded
from schemas import PhotographerRequest, PhotographerResponse, ReadinessResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

engine = ShutterMuseEngine(settings)
executor = LatestPendingExecutor()


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.autoload:
        engine.mark_loading()
        executor.submit(engine.initialize)
    yield


app = FastAPI(title="ShutterMuse GPU Model Service", version="0.1.0", lifespan=lifespan)


def verify_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if settings.api_key and x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "Invalid API key"})


@app.post(
    "/v1/photographer/analyze",
    response_model=PhotographerResponse,
    response_model_exclude_none=True,
    dependencies=[],
)
def photographer_analyze(request: PhotographerRequest, x_api_key: str | None = Header(default=None)):
    verify_api_key(x_api_key)
    if engine.state != "ready":
        raise HTTPException(
            status_code=503,
            detail={
                "request_id": request.request_id,
                "frame_id": request.frame_id,
                "code": engine.error_code or "MODEL_NOT_READY",
                "message": "ShutterMuse is not ready",
            },
        )
    future = executor.submit(lambda: engine.infer(request))
    try:
        result = future.result(timeout=settings.inference_timeout_ms / 1000)
    except ModelRequestSuperseded as exc:
        raise HTTPException(
            status_code=429,
            detail={
                "request_id": request.request_id,
                "frame_id": request.frame_id,
                "code": "MODEL_BUSY",
                "message": "AI 正在处理",
            },
        ) from exc
    except FutureTimeoutError as exc:
        executor.cancel_if_pending(future)
        raise HTTPException(
            status_code=504,
            detail={
                "request_id": request.request_id,
                "frame_id": request.frame_id,
                "code": "MODEL_TIMEOUT",
                "message": "ShutterMuse inference timed out",
            },
        ) from exc
    except ModelServiceError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "request_id": request.request_id,
                "frame_id": request.frame_id,
                "code": exc.code,
                "message": str(exc),
            },
        ) from exc
    return PhotographerResponse(
        request_id=request.request_id,
        frame_id=request.frame_id,
        status=result.parsed.status,
        decision=result.parsed.decision,
        bbox_norm=result.parsed.bbox_norm,
        confidence=result.parsed.confidence,
        error_code=result.parsed.error_code,
        inference_ms=result.inference_ms,
        prompt_mode=request.prompt_mode,
        coordinate_source=result.parsed.coordinate_source,
        raw_output=(
            result.generation.raw_output[: min(settings.raw_output_max_chars, 4000)]
            if settings.eval_capture_raw_output
            else None
        ),
        raw_output_length=(
            len(result.generation.raw_output) if settings.eval_capture_raw_output else None
        ),
        generated_token_count=result.generation.generated_token_count,
        reached_max_new_tokens=result.generation.reached_max_new_tokens,
        stopped_by_structure=result.generation.stopped_by_structure,
        parse_failure_type=result.parsed.parse_failure_type,
        parser_comparison=result.parser_comparison,
        generation_config=engine.generation_config(),
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready", response_model=ReadinessResponse)
def readiness():
    active, pending = executor.status()
    result = ReadinessResponse(**engine.readiness(active, pending))
    if result.status != "ready":
        return JSONResponse(status_code=503, content=result.model_dump(exclude_none=True))
    return result
