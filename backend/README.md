# Beeep FastAPI backend

Run from this directory after installing `requirements.txt`:

```powershell
uvicorn main:app --host 0.0.0.0 --port 8000
```

`POST /v1/analyze` is the only endpoint new mobile clients should use. In `rules`
mode it runs the reusable full MediaPipe processor. In `shuttermuse` mode it first runs
the dedicated face-based `SubjectPreflight`, and calls the GPU service only when a stable
person proxy is detected or `requires_person=false` is sent.

`GUIDANCE_ENGINE=rules` uses deterministic composition, light, distance and pose rules.
`GUIDANCE_ENGINE=shuttermuse` calls the dedicated GPU service at
`SHUTTERMUSE_SERVICE_URL`. The Beeep process does not load model weights and does not
create GPU inference threads.

The model service returns `decision`, strict `bbox_norm`, confidence and model latency.
`GuidanceAdapter` owns the conversion to `move_camera`, `adjust_distance`, `adjust_angle`,
`framing_hint` or `hold`. It scores horizontal, vertical and distance candidates, then
returns the strongest one or two different dimensions. Invalid model geometry is an
explicit `INVALID_MODEL_OUTPUT` state and never creates a composition box.

ShutterMuse failures never fall back to `rules`. API errors preserve the technical code
for logs/debugging while returning deterministic user-facing `message`, `suggestion`,
`retryable` and `severity`. `MODEL_BUSY` and `MODEL_LOADING` are waiting states rather
than severe errors.

Preflight controls:

```env
SUBJECT_PREFLIGHT_ENABLED=1
SUBJECT_PREFLIGHT_CONFIDENCE=0.55
SUBJECT_PREFLIGHT_MIN_AREA=0.03
SUBJECT_PREFLIGHT_TIMEOUT_MS=800
SUBJECT_PREFLIGHT_CONFIRMATION_FRAMES=3
SUBJECT_PREFLIGHT_HOLD_MS=1500
SUBJECT_PREFLIGHT_STATE_TTL_MS=10000
```

Requests default to `requires_person=true`. Future scenery, food or object modes can set
it to false without changing the ShutterMuse service. `/v1/status` includes rolling P50
and P95 preflight/guidance timings for the latest 200 samples, plus detected/uncertain/
missing and blocked outcome counts.

Preflight is intentionally a lightweight face signal rather than full pose estimation.
`SubjectPresenceGate` turns it into a three-state decision per `stream_id`: detected,
uncertain or missing. It permits the first two uncertain/missing frames and retains a
recent detected state for 1.5 seconds before blocking ShutterMuse. A labeled real-device
false-block evaluation is available under `evaluation/preflight_eval`.

All App-facing composition boxes and target pose points use normalized 0-1 coordinates. Pose model output is accepted only when all 17 COCO keypoints and all 17 visibility values are valid; malformed model output is rejected rather than padded.

Deployment notes:

- use explicit `CORS_ALLOWED_ORIGINS` in production;
- use one process worker per MediaPipe detector set;
- Base64 image data is processed in memory and not persisted or logged;
- `BEEEP_API_KEY` enables the reserved API key check for `/v1/*`;
- `SUBJECT_PREFLIGHT_TIMEOUT_MS`, `VISION_TIMEOUT_MS` and `GUIDANCE_TIMEOUT_MS` are independent;
- `/ready` proxies the selected engine's real readiness instead of returning a constant;
- rate limiting should be added at the reverse proxy before public launch.
