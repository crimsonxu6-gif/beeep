# Beeep AI Photo Coach

> Starting a new Codex session? Read [PROJECT_HANDOFF.md](./PROJECT_HANDOFF.md) first. It records
> the current product decisions, verified baseline, environment, remaining risks, and next work in
> one place.

Expo + FastAPI mobile photography assistant. The MVP now implements the complete loop:

```text
Camera preview
  -> 0.5-1 FPS compressed analysis frame
  -> POST /v1/analyze (image uploaded once)
  -> MediaPipe reusable vision processor
  -> rules or ShutterMuse GPU model service
  -> normalized composition / pose adapter
  -> latest-wins + stale frame guard + stability filter
  -> one short overlay action
```

The model runs on the server. The phone owns camera preview, low-rate sampling, overlays, capture, preview and saving.

## Mobile setup

```powershell
cd D:\beeep
npm install
Copy-Item .env.example .env
npx expo start --dev-client
```

Set `EXPO_PUBLIC_ANALYZE_API_URL` to the backend address reachable by the phone. Do not hard-code a LAN IP in source code.

The default route remains the home screen. Open the camera from the home capture button. The camera supports automatic, centered, left-thirds and right-thirds composition modes.

## Backend setup

```powershell
cd D:\beeep
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

Endpoints:

- `POST /v1/analyze`: the production mobile endpoint; performs vision and guidance in one upload.
- `GET /v1/status`: active guidance engine and readiness.
- `GET /health`: liveness.
- `GET /ready`: readiness.
- `/vision/features` and `/guidance`: retained for older clients only.

The server does not persist uploaded analysis images and must not log Base64 data. Image requests are limited by MIME, request size, dimensions and total pixels. For production set explicit `CORS_ALLOWED_ORIGINS`, optionally set `BEEEP_API_KEY`, and run one worker per MediaPipe detector set. Each worker owns one face and pose detector; calls inside a worker are lock-protected.

## Mock policy

Mock output is disabled by default and can never activate in a production JS bundle. It is enabled only when both conditions are true:

```text
__DEV__ === true
EXPO_PUBLIC_ENABLE_MOCK=1
```

Without an API URL or when the API fails, the app shows a short connection/error state instead of fabricated photography advice.

## Guidance engine

Use the built-in deterministic engine during local development:

```env
GUIDANCE_ENGINE=rules
```

The released ShutterMuse checkpoint is already trained. Do not retrain or fine-tune it for
the first product validation. Run the dedicated GPU service after cloning the official
repository:

```powershell
git clone https://github.com/lijayuTnT/ShutterMuse.git D:\models\ShutterMuse
cd D:\beeep\model-service
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-4bit.txt
python -m pip install --force-reinstall -r requirements-cuda128.txt
$env:SHUTTERMUSE_REPO_PATH="D:\models\ShutterMuse"
$env:SHUTTERMUSE_MODEL_PATH="ShutterMuse/ShutterMuse"
$env:SHUTTERMUSE_DEVICE="cuda"
$env:SHUTTERMUSE_LOAD_IN_4BIT="1"
python -m uvicorn app:app --host 0.0.0.0 --port 8100
```

Then start Beeep FastAPI with:

```env
GUIDANCE_ENGINE=shuttermuse
SHUTTERMUSE_SERVICE_URL=http://127.0.0.1:8100
```

The GPU process loads one model and one processor, performs parse-checked warmup before
readiness, and permits one active plus one replaceable pending generation. In ShutterMuse
mode a lightweight MediaPipe cascade checks Face first and runs Pose only when Face is
weak or absent; the full pose/scene processor remains exclusive to rules mode. Beeep scores the model's
normalized crop into one or two deterministic actions. Invalid boxes and model failures
return explicit status messages and never produce a fabricated crop or silent rules fallback.

The subject signal is stateful rather than a one-frame hard gate. Per-camera `stream_id`
state distinguishes confirmed, uncertain and missing, tolerates two transient missing
frames, and retains recent subject presence for 1.5 seconds. Uncertain results always
fail open. Preflight blocking defaults off and can be enabled only after evaluation with
`SUBJECT_PREFLIGHT_BLOCKING=1`. Use `evaluation/beeep_capture_eval` to measure labeled
face-only misses, cascade misses and the effective model block rate.

Live ShutterMuse quality evaluation uses the same 20 composition images but writes separate
API results, bbox overlays, and a persistent human review manifest. The deterministic fixture
report remains separate and must not be interpreted as model quality.

The mobile app defaults to `EXPO_PUBLIC_GUIDANCE_TRIGGER_MODE=manual`: the user taps
"分析构图", one frame is submitted, and the button remains disabled until that request
finishes. `stable_auto` keeps the configuration boundary for a later stability trigger;
`continuous` preserves the previous sampler for development only. During a manual request
the UI shows staged status text after two seconds and may retain an unexpired previous
suggestion at reduced opacity. No failed model request is retried automatically.

Use `GUIDANCE_ENGINE=rules` to run without the GPU service. Use
`GUIDANCE_ENGINE=shuttermuse` only after `http://127.0.0.1:8100/ready` reports ready.

## Capture flow

Analysis frames and final photos use separate controllers:

- analysis: JPEG Base64, quality `0.28`, default `0.75 FPS`;
- final photo: processed image, quality `1.0`, no Base64 upload;
- capturing and photo preview pause automatic analysis;
- preview supports retake, save, return to camera and system gallery selection.

Camera shutter animation, flash and shutter sound are disabled in the app configuration used by these controllers.

## Environment reference

See [.env.example](./.env.example). Important app flags:

- `EXPO_PUBLIC_ANALYZE_API_URL`: unified backend endpoint.
- `EXPO_PUBLIC_ENABLE_MOCK`: development-only explicit mock switch.
- `EXPO_PUBLIC_DEBUG_PANEL`: shows request/frame IDs, stale drops, timing, engine and mode.
- `EXPO_PUBLIC_GUIDANCE_TRIGGER_MODE`: `manual` (default), `stable_auto`, or development-only `continuous`.
- `EXPO_PUBLIC_SAMPLE_FPS`: clamped to `0.5-1` while sampling uses `takePictureAsync`.
- `EXPO_PUBLIC_VISION_TIMEOUT_MS` / `EXPO_PUBLIC_GUIDANCE_TIMEOUT_MS`: separate status budgets.

Long term, replace `takePictureAsync` sampling with CameraX `ImageAnalysis`, AVFoundation or a native frame processor. The pipeline API can remain unchanged.

## Composition analysis pipeline

The mobile client defaults to a deliberate manual analysis flow. An analysis tap captures an
orientation-correct JPEG without Base64, resizes it proportionally to a 768 px short edge,
compresses it at JPEG quality 0.7, and uploads it as multipart form data. The legacy JSON Base64
contract remains available with `EXPO_PUBLIC_ANALYSIS_UPLOAD_MODE=base64_json`.

### Android emulator fixture validation

Development builds can replace camera capture with a bundled or gallery fixture while preserving
the production preprocessing, upload, parser, stability, and overlay pipeline:

```env
EXPO_PUBLIC_ENABLE_ANALYSIS_FIXTURE=1
EXPO_PUBLIC_ANALYSIS_FIXTURE_SOURCE=bundled
EXPO_PUBLIC_ANALYSIS_API_MODE=mock_success
EXPO_PUBLIC_DEBUG_PANEL=1
```

`EXPO_PUBLIC_ANALYSIS_FIXTURE_SOURCE` accepts `bundled` or `gallery`.
`EXPO_PUBLIC_ANALYSIS_API_MODE` accepts `live`, `live_debug`, `mock_success`, `mock_error`, or
`mock_timeout`. `live_debug` calls the development-only backend response endpoint configured by
`EXPO_PUBLIC_ANALYSIS_DEBUG_API_URL`. Fixture, debug, and mock API modes are forced off outside
development. The fixture tool
can simulate front/rear metadata, image mirroring, portrait/landscape metadata, preview ratios,
multipart/Base64 regression, a pre-request delay, and an error before `fetch`. These network
profiles validate UI state only; they do not simulate Android bandwidth or the Android network stack.
Mock modes validate UI state only;
use `live` for backend and ShutterMuse validation.

Because `expo-file-system`, `expo-image-manipulator`, and `expo-asset` are native modules, Expo Go
or Metro hot reload is insufficient after dependency changes. Use the Android development build:

```powershell
npx expo prebuild --clean --platform android
npx expo run:android
```

See `evaluation/beeep_capture_eval/SIMULATOR_TESTING.md`. Simulator reports are explicitly marked
`Simulator validation only` and do not replace the physical-device checklist below.

The model service supports four prompt experiments through `SHUTTERMUSE_PROMPT_MODE`:
`official`, `official_bbox_first`, `official_prefill`, and `beeep_json`. Official-mode parsing may
recover a complete explicitly named `bbox`, `composition_bbox`, or `composition_xy` field from an
otherwise truncated JSON response. It never scans arbitrary prose for coordinates and never swaps,
clamps, or invents bbox values.

Readiness reports `runtime_ready` separately from `quality_ready`. Runtime readiness requires a
loaded model and a warmup generation with at least one token. A failed warmup bbox parse produces a
quality warning but still permits evaluation requests unless
`SHUTTERMUSE_REQUIRE_QUALITY_WARMUP=1`.

Before a model bbox reaches the App, the backend validates target ratio, minimum area, subject
preservation, and head/full-body cut risk. Unsafe boxes remain in evaluation metadata but are not
drawn. Production UI displays only the primary action by default; set
`EXPO_PUBLIC_ENABLE_SECONDARY_GUIDANCE=1` for controlled experiments. The debug panel still lists
all backend actions.

### Minimum real-device verification

Automated tests do not replace camera verification. At minimum, validate one physical Android
phone on Wi-Fi with rear and front portrait capture, landscape rotation, front-preview mirroring,
aspect-fill overlays near all four corners, normal/low/backlight/motion scenes, timeout recovery,
and ten consecutive analyses without duplicate requests, freezes, or crashes. Record capture,
preprocess, payload, network/server, render, and tap-to-overlay timings; do not infer these metrics
from server inference time.

## Checks

```powershell
npm run check
cd backend
..\.venv\Scripts\python.exe -m pytest -q
..\.venv\Scripts\ruff.exe check .
cd ..\model-service
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
```

## Current limitations

- ShutterMuse weights are not included in this repository; use the official merged Hugging Face checkpoint.
- The released model is about 9B BF16 parameters. This workstation completed a 4-bit
  smoke test with CPU offload, but full BF16 quality and latency still require a larger GPU.
  The current 8 GB laptop results are research data, not a real-time or production benchmark.
- Subject-side ShutterMuse inference still needs to be connected to the strict COCO-17 adapter.
- The upstream repository currently has no finalized code/model license. Commercial use remains blocked pending explicit terms.
- MediaPipe currently runs on the backend; a later mobile-native visual layer will reduce latency and traffic.
- Gallery images currently enter preview; offline gallery scoring is not part of this MVP.
