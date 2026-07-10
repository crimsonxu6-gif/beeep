# Beeep FastAPI backend

Run from this directory after installing `requirements.txt`:

```powershell
uvicorn main:app --host 0.0.0.0 --port 8000
```

`POST /v1/analyze` is the only endpoint new mobile clients should use. It decodes one compressed frame, runs the reusable MediaPipe processor, invokes the selected photography guidance service and returns normalized geometry with per-stage timing.

`GUIDANCE_ENGINE=rules` uses deterministic composition, light, distance and pose rules. `GUIDANCE_ENGINE=shuttermuse` lazily loads the external ShutterMuse photographer-side model through `services/shuttermuse_service.py`. The released repository and model paths must be provided through the `SHUTTERMUSE_*` environment variables.

All App-facing composition boxes and target pose points use normalized 0-1 coordinates. Pose model output is accepted only when all 17 COCO keypoints and all 17 visibility values are valid; malformed model output is rejected rather than padded.

Deployment notes:

- use explicit `CORS_ALLOWED_ORIGINS` in production;
- use one process worker per MediaPipe detector set;
- Base64 image data is processed in memory and not persisted or logged;
- `BEEEP_API_KEY` enables the reserved API key check for `/v1/*`;
- `VISION_TIMEOUT_MS` and `GUIDANCE_TIMEOUT_MS` are independent;
- rate limiting should be added at the reverse proxy before public launch.
