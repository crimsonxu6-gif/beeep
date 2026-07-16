from __future__ import annotations

import asyncio
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse, Response
from starlette.datastructures import UploadFile

from core.config import settings
from core.request_context import get_request_id

DebugScenario = Literal[
    "success",
    "delayed_success",
    "http_500",
    "http_502",
    "http_503",
    "http_504",
    "invalid_json",
    "missing_bbox",
    "bbox_safety_rejected",
    "invalid_model_output",
]

router = APIRouter(prefix="/v1/debug", tags=["development"], include_in_schema=False)


def debug_endpoint_enabled(environment: str, configured: bool) -> bool:
    return configured and environment != "production"


def _ensure_enabled() -> None:
    if not debug_endpoint_enabled(
        settings.environment,
        settings.debug_analyze_endpoint_enabled,
    ):
        raise HTTPException(status_code=404, detail="Not found")


async def _request_metadata(request: Request) -> tuple[int, int]:
    content_type = request.headers.get("content-type", "").lower()
    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        upload = form.get("image")
        if not isinstance(upload, UploadFile):
            raise HTTPException(status_code=422, detail="image is required")
        image_bytes = await upload.read()
        return int(str(form.get("frame_id") or 0)), len(image_bytes)

    payload = await request.json()
    frame_id = int(payload.get("frame_id", 0))
    base64_value = payload.get("image", {}).get("base64", "")
    return frame_id, len(base64_value)


def _success(frame_id: int, include_bbox: bool = True) -> dict[str, object]:
    result: dict[str, object] = {
        "request_id": get_request_id(),
        "frame_id": frame_id,
        "status": "success",
        "guidance_engine": "debug_fixture",
        "priority": "composition",
        "problem": {"type": "subject_position", "description": "主体稍微偏右"},
        "actions": [
            {
                "type": "move_camera",
                "direction": "left",
                "message": "镜头稍微往左移",
                "confidence": 0.86,
            }
        ],
        "message": "镜头稍微往左移",
        "reason": "开发环境固定 HTTP 响应",
        "summary": "开发环境构图响应",
        "confidence": 0.86,
        "timing": {"vision_ms": 0, "guidance_ms": 0, "total_ms": 0},
    }
    if include_bbox:
        result["composition"] = {
            "decision": "refine",
            "bbox_norm": [0.15, 0.1, 0.8, 0.9],
        }
    return result


@router.post("/analyze-response")
async def analyze_response(
    request: Request,
    scenario: DebugScenario = Query(default="success"),
):
    _ensure_enabled()
    frame_id, _image_bytes = await _request_metadata(request)

    if scenario == "delayed_success":
        await asyncio.sleep(max(0, settings.debug_analyze_delay_ms) / 1000)
        return _success(frame_id)
    if scenario == "invalid_json":
        return Response(content="{invalid-json", status_code=200, media_type="application/json")
    if scenario == "missing_bbox":
        return _success(frame_id, include_bbox=False)
    if scenario == "invalid_model_output":
        return JSONResponse(status_code=200, content={"frame_id": frame_id, "status": "success"})
    if scenario == "bbox_safety_rejected":
        return JSONResponse(
            status_code=422,
            content={
                "request_id": get_request_id(),
                "frame_id": frame_id,
                "status": "error",
                "error": {
                    "code": "BBOX_SAFETY_REJECTED",
                    "message": "这次推荐框不够稳定",
                    "suggestion": "稍微换个角度再分析",
                    "retryable": True,
                },
            },
        )
    if scenario.startswith("http_"):
        status_code = int(scenario.removeprefix("http_"))
        return JSONResponse(
            status_code=status_code,
            content={
                "request_id": get_request_id(),
                "frame_id": frame_id,
                "status": "error",
                "error": {
                    "code": f"HTTP_{status_code}",
                    "message": "AI 暂时无法使用",
                    "suggestion": "可以稍后再试",
                    "retryable": True,
                },
            },
        )
    return _success(frame_id)
