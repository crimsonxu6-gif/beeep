# AI Photo Coach

Mobile AI photography assistant prototype based on the ShutterMuse-style guidance architecture.

## Architecture

```text
Camera Input
  -> Frame Sampler (2-5 FPS)
  -> Vision Preprocessing Layer
  -> AI Guidance Engine (ShutterMuse HTTP API or local mock)
  -> Strict JSON Parser + Retry
  -> Stability Filter (debounce + consistency + smoothing)
  -> UI Overlay (direction arrows + short action message)
```

## Run

```bash
npm install
npm start
```

Open the project in an Expo development build or a simulator. Without backend URLs, the app falls back to local mock vision/guidance so the prototype remains runnable.

## FastAPI + MediaPipe backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

Set these for a phone on the same Wi-Fi, replacing the IP with your computer LAN IP:

```bash
EXPO_PUBLIC_MEDIAPIPE_VISION_API_URL=http://192.168.0.106:8000/vision/features
EXPO_PUBLIC_SHUTTERMUSE_API_URL=http://192.168.0.106:8000/guidance
```

If `EXPO_PUBLIC_MEDIAPIPE_VISION_API_URL` is omitted and `EXPO_PUBLIC_SHUTTERMUSE_API_URL`
ends with `/guidance`, the app derives `/vision/features` automatically.

The backend exposes:

- `POST /vision/features`: MediaPipe face detection, person bbox, pose keypoints, scene features.
- `POST /guidance`: strict `GuidanceOutput` JSON for `move_camera`, `adjust_pose`, `framing_hint`, `lighting_hint`, and `hold`.

## Development build

Expo Go version mismatches can be avoided with an EAS development build:

```bash
npm install
eas login
eas init
npm run build:ios:dev
```

For iPhone installation, EAS will ask for Apple credentials and device/profile setup during the iOS build. The project uses `expo-dev-client`, so after the build is installed you can connect it to the local Metro server with `npx expo start --dev-client`.

Android test APK:

```bash
npm run build:android:dev
```

## ShutterMuse API contract

Set `EXPO_PUBLIC_SHUTTERMUSE_API_URL` to a service that accepts:

```json
{
  "frame_id": 123,
  "timestamp": 123456,
  "image": {
    "base64": "...",
    "width": 1080,
    "height": 1920,
    "mime_type": "image/jpeg"
  },
  "vision_features": {},
  "prompt": "strict JSON prompt",
  "schema": {}
}
```

The service must return strict JSON:

```json
{
  "priority": "composition",
  "problem": {
    "type": "subject_position",
    "description": "主体偏右"
  },
  "actions": [
    {
      "type": "move_camera",
      "direction": "left",
      "message": "往左一点",
      "confidence": 0.85
    }
  ],
  "message": "往左一点",
  "reason": "主体中心位于画面右侧",
  "summary": "主体偏右",
  "confidence": 0.85
}
```

Rules:

- Return at most 2 actions.
- `message` must be Chinese, immediately actionable, and no more than 10 characters.
- `problem` and `reason` are for developer debugging; the user only sees `message`.
- Prefer one strongest action over a list of comments.
- If the frame is good, return `{ "type": "hold", "message": "保持角度" }`.
- Additional action types include `lighting_hint`, `adjust_distance`, `adjust_angle`, and `hold`.

Optional batch endpoint: set `EXPO_PUBLIC_SHUTTERMUSE_BATCH_API_URL`; it receives `{ "requests": [...] }` and returns an array of guidance objects.

## Real ShutterMuse backend mode

The mobile app does not embed ShutterMuse. Keep ShutterMuse behind the FastAPI
backend and switch the backend mode when model weights are available:

```bash
BEEEP_GUIDANCE_ENGINE=shuttermuse
SHUTTERMUSE_REPO_PATH=D:\models\ShutterMuse
SHUTTERMUSE_MODEL_PATH=D:\models\Qwen3-VL-8B-Instruct
SHUTTERMUSE_LORA_PATH=D:\models\ShutterMuse-LoRA
SHUTTERMUSE_DEVICE=cuda
```

Default mode remains `BEEEP_GUIDANCE_ENGINE=rule`, so local mobile previews keep
working without GPU dependencies. Check the active backend mode with
`GET /guidance/status`.

## Modules

- `src/camera`: 2-5 FPS frame sampling, no per-frame LLM calls.
- `src/vision`: MediaPipe backend adapter with mock fallback for face/person/pose/scene features.
- `src/ai_engine`: prompt manager, HTTP client, batch interface, strict JSON parser, mock engine.
- `src/stability`: multi-frame consistency, confidence threshold, debounce, bbox smoothing.
- `src/ui`: camera overlay arrows and <=10 character action message.

## Developer debug panel

Set `EXPO_PUBLIC_DEBUG_PANEL=1` to overlay developer diagnostics in the camera:

- latency and processing state
- summarized MediaPipe vision features
- current action, priority, problem, and reason

## UI direction

- Minimal, tool-like mobile interface with iOS-native spacing and system typography.
- Main screens: home dashboard, live camera workspace, composition coach, and profile/services.
- Camera workspace keeps guidance controls close to the shutter: gallery, capture, composition mode, and pose recommendation.
- Visual style avoids decorative assets; UI uses soft geometric surfaces, compact controls, and concise action text.

## Production integration notes

- `MediaPipeVisionPreprocessor` calls the backend vision API and falls back to local mock features when no endpoint is configured.
- Put the real ShutterMuse model behind `POST /guidance`; avoid embedding the model directly in the mobile app.
- Keep `EXPO_PUBLIC_SAMPLE_FPS` between `2` and `5`.
- Keep `EXPO_PUBLIC_AI_TIMEOUT_MS` near the target update budget; default is `280ms`.
