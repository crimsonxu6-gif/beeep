# Beeep AI Photo Coach

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
mode a lightweight MediaPipe face preflight first checks that a person is present; the
full pose/scene processor remains exclusive to rules mode. Beeep scores the model's
normalized crop into one or two deterministic actions. Invalid boxes and model failures
return explicit status messages and never produce a fabricated crop or silent rules fallback.

The lightweight face signal is stateful rather than a one-frame hard gate. Per-camera
`stream_id` state distinguishes detected, uncertain and missing, tolerates two transient
frames and retains recent subject presence briefly. Use `evaluation/preflight_eval` to
measure labeled false-block rate on real-device scenarios.

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
- `EXPO_PUBLIC_SAMPLE_FPS`: clamped to `0.5-1` while sampling uses `takePictureAsync`.
- `EXPO_PUBLIC_VISION_TIMEOUT_MS` / `EXPO_PUBLIC_GUIDANCE_TIMEOUT_MS`: separate status budgets.

Long term, replace `takePictureAsync` sampling with CameraX `ImageAnalysis`, AVFoundation or a native frame processor. The pipeline API can remain unchanged.

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
- Subject-side ShutterMuse inference still needs to be connected to the strict COCO-17 adapter.
- The upstream repository currently has no finalized code/model license. Commercial use remains blocked pending explicit terms.
- MediaPipe currently runs on the backend; a later mobile-native visual layer will reduce latency and traffic.
- Gallery images currently enter preview; offline gallery scoring is not part of this MVP.
