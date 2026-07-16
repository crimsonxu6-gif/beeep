# Beeep FastAPI backend

Run from this directory after installing `requirements.txt`:

```powershell
uvicorn main:app --host 0.0.0.0 --port 8000
```

`POST /v1/analyze` is the only endpoint new mobile clients should use. In `rules`
mode it runs the reusable full MediaPipe processor. In `shuttermuse` mode it runs a
face-first, pose-fallback `SubjectPreflight`. Uncertain detections fail open, while only
confirmed multi-frame absence can block the GPU service when blocking is explicitly enabled.
The endpoint accepts the legacy JSON Base64 body and the preferred multipart upload. Multipart
metadata explicitly carries camera facing, mirror state, device orientation, preview/image size,
and client capture timestamps; the backend converts the image in memory for the existing model
service contract.

`GUIDANCE_ENGINE=rules` uses deterministic composition, light, distance and pose rules.
`GUIDANCE_ENGINE=shuttermuse` calls the dedicated GPU service at
`SHUTTERMUSE_SERVICE_URL`. The Beeep process does not load model weights and does not
create GPU inference threads.

The model service returns `decision`, strict `bbox_norm`, confidence and model latency.
`GuidanceAdapter` owns the conversion to `move_camera`, `adjust_distance`, `adjust_angle`,
`framing_hint` or `hold`. It scores horizontal, vertical and distance candidates, then
returns the strongest one or two different dimensions. Invalid model geometry is an
explicit `INVALID_MODEL_OUTPUT` state and never creates a composition box.
Legal model boxes pass a separate safety validator before display. Target-ratio mismatch, very
small crops, insufficient subject preservation, head-cut risk, and full-body loss reject the box
without repairing it. The raw box and rejection reasons remain in `model_metadata` for evaluation.

ShutterMuse failures never fall back to `rules`. API errors preserve the technical code
for logs/debugging while returning deterministic user-facing `message`, `suggestion`,
`retryable` and `severity`. `MODEL_BUSY` and `MODEL_LOADING` are waiting states rather
than severe errors.

For Android Emulator HTTP error validation, development/test environments can explicitly set
`DEBUG_ANALYZE_ENDPOINT_ENABLED=1` and call `POST /v1/debug/analyze-response`. The hidden endpoint
returns real HTTP 500/502/503/504 responses, invalid JSON, missing-bbox success responses, delayed
success, or bbox safety errors without touching `/v1/analyze`. It is not registered when
`APP_ENV=production`, even if the flag is set.

Preflight controls:

```env
SUBJECT_PREFLIGHT_ENABLED=1
SUBJECT_PREFLIGHT_CONFIDENCE=0.55
SUBJECT_PREFLIGHT_MIN_AREA=0.03
SUBJECT_PREFLIGHT_TIMEOUT_MS=800
SUBJECT_PREFLIGHT_BLOCKING=0
SUBJECT_PRESENCE_TTL_MS=1500
SUBJECT_MISSING_CONFIRM_FRAMES=3
SUBJECT_POSE_MIN_VISIBLE_KEYPOINTS=4
SUBJECT_POSE_MIN_VISIBILITY=0.35
SUBJECT_POSE_MIN_AREA=0.015
BBOX_SAFETY_MIN_AREA=0.12
BBOX_SAFETY_RATIO_TOLERANCE=0.20
SUBJECT_PREFLIGHT_CONFIRMATION_FRAMES=3
SUBJECT_PREFLIGHT_HOLD_MS=1500
SUBJECT_PREFLIGHT_STATE_TTL_MS=10000
```

Requests default to `requires_person=true`. Future scenery, food or object modes can set
it to false without changing the ShutterMuse service. `/v1/status` includes rolling P50
and P95 preflight/guidance timings for the latest 200 samples, plus confirmed/uncertain/
missing and blocked outcome counts.

Preflight uses a cascade: a confirmed face skips Pose, while failed or weak face detection
runs MediaPipe Pose with lightweight thresholds. `SubjectPresenceGate` produces
`confirmed`, `uncertain`, or `missing`, retains a confirmed subject for 1.5 seconds, and
requires three consecutive missing frames before confirming absence. `uncertain` always
allows ShutterMuse. `SUBJECT_PREFLIGHT_BLOCKING=0` is the default fail-open rollout mode;
with blocking enabled, only confirmed `missing` blocks a model call. The legacy
`SUBJECT_PREFLIGHT_CONFIRMATION_FRAMES` and `SUBJECT_PREFLIGHT_HOLD_MS` variables remain
as fallbacks for existing deployments.

All App-facing composition boxes and target pose points use normalized 0-1 coordinates. Pose model output is accepted only when all 17 COCO keypoints and all 17 visibility values are valid; malformed model output is rejected rather than padded.

Deployment notes:

- use explicit `CORS_ALLOWED_ORIGINS` in production;
- use one process worker per MediaPipe detector set;
- multipart and Base64 image data are processed in memory and not persisted or logged;
- `BEEEP_API_KEY` enables the reserved API key check for `/v1/*`;
- `SUBJECT_PREFLIGHT_TIMEOUT_MS`, `VISION_TIMEOUT_MS` and `GUIDANCE_TIMEOUT_MS` are independent;
- `/ready` proxies the selected engine's real readiness instead of returning a constant;
- rate limiting should be added at the reverse proxy before public launch.
