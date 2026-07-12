from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request
from fastapi.responses import JSONResponse

from core.request_context import get_request_id


@dataclass(frozen=True)
class UserError:
    message: str
    suggestion: str
    retryable: bool
    severity: str = "error"


ERROR_PRESENTATIONS: dict[str, UserError] = {
    "MODEL_LOADING": UserError("AI 正在准备", "稍等一会再试", True, "waiting"),
    "MODEL_NOT_READY": UserError("AI 正在准备", "稍等一会再试", True, "waiting"),
    "MODEL_BUSY": UserError("AI 正在分析上一张画面", "保持一下，很快就好", True, "waiting"),
    "MODEL_TIMEOUT": UserError("这次分析花得有点久", "保持画面稳定，再试一次", True),
    "GUIDANCE_TIMEOUT": UserError("这次分析花得有点久", "保持画面稳定，再试一次", True),
    "NETWORK_ERROR": UserError("网络连接不太稳定", "检查网络后再试", True),
    "MODEL_SERVICE_UNAVAILABLE": UserError("AI 暂时无法使用", "可以稍后再来试试", True),
    "MODEL_SERVICE_FAILED": UserError("AI 暂时无法使用", "可以稍后再来试试", True),
    "INVALID_MODEL_OUTPUT": UserError("这次没看懂画面", "稍微换个角度再试", True),
    "CUDA_OUT_OF_MEMORY": UserError("AI 暂时无法完成分析", "可以稍后再试", True),
    "MODEL_INTERNAL_ERROR": UserError("AI 暂时无法完成分析", "可以稍后再试", True),
    "INFERENCE_FAILED": UserError("AI 暂时无法完成分析", "可以稍后再试", True),
    "PREFLIGHT_FAILED": UserError("人物识别暂时不可用", "保持画面稳定，再试一次", True),
}


class ApiError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        frame_id: int | None = None,
        *,
        suggestion: str | None = None,
        retryable: bool | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.frame_id = frame_id
        self.suggestion = suggestion
        self.retryable = retryable


def present_error(exc: ApiError) -> UserError:
    mapped = ERROR_PRESENTATIONS.get(exc.code)
    if mapped is not None:
        return mapped
    return UserError(
        message=exc.message,
        suggestion=exc.suggestion or "请稍后重试",
        retryable=exc.retryable if exc.retryable is not None else exc.status_code >= 500,
    )


async def api_error_handler(_: Request, exc: ApiError) -> JSONResponse:
    error = present_error(exc)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "request_id": get_request_id(),
            "frame_id": exc.frame_id,
            "status": "error",
            "error": {
                "code": exc.code,
                "message": error.message,
                "suggestion": error.suggestion,
                "retryable": error.retryable,
                "severity": error.severity,
            },
        },
    )
