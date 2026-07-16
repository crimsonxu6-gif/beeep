from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.analyze import guidance_service
from api.analyze import router as analyze_router
from api.debug_analyze import router as debug_analyze_router
from api.guidance import router as guidance_router
from core.config import settings
from core.errors import ApiError, api_error_handler
from core.request_context import new_request_id, request_id_var

app = FastAPI(title="Beeep Guidance Backend", version="0.2.0")
origins = list(settings.cors_allowed_origins)
if settings.environment == "production" and "*" in origins:
    raise RuntimeError("CORS_ALLOWED_ORIGINS cannot contain '*' in production")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key", "X-Request-ID"],
)
app.add_exception_handler(ApiError, api_error_handler)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or new_request_id()
    token = request_id_var.set(request_id)
    try:
        content_length = int(request.headers.get("content-length", "0") or 0)
        if content_length > settings.max_image_bytes:
            return JSONResponse(
                status_code=413,
                content={
                    "request_id": request_id,
                    "frame_id": None,
                    "status": "error",
                    "error": {"code": "REQUEST_TOO_LARGE", "message": "请求体超过 2 MB"},
                },
            )
        if settings.api_key and request.url.path.startswith("/v1/"):
            if request.headers.get("X-API-Key") != settings.api_key:
                return JSONResponse(
                    status_code=401,
                    content={
                        "request_id": request_id,
                        "status": "error",
                        "error": {"code": "UNAUTHORIZED", "message": "无效的 API Key"},
                    },
                )
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        request_id_var.reset(token)


app.include_router(analyze_router)
app.include_router(guidance_router)
if settings.environment != "production" and settings.debug_analyze_endpoint_enabled:
    app.include_router(debug_analyze_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def readiness():
    state = guidance_service.readiness()
    status_code = 200 if state.get("status") == "ready" else 503
    return JSONResponse(status_code=status_code, content=state)
