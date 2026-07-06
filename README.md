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
  -> UI Overlay (arrows + bbox + short instruction)
```

## Run

```bash
npm install
npm start
```

Open the project in Expo Go or a simulator. Without `EXPO_PUBLIC_SHUTTERMUSE_API_URL`, the app uses a local mock guidance engine so the prototype remains runnable.

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
  "actions": [
    {
      "type": "move_camera",
      "direction": "left",
      "strength": "medium"
    }
  ],
  "summary": "subject is off center",
  "confidence": 0.82
}
```

Optional batch endpoint: set `EXPO_PUBLIC_SHUTTERMUSE_BATCH_API_URL`; it receives `{ "requests": [...] }` and returns an array of guidance objects.

## Modules

- `src/camera`: 2-5 FPS frame sampling, no per-frame LLM calls.
- `src/vision`: replaceable preprocessing adapter for face/person/pose/scene features.
- `src/ai_engine`: prompt manager, HTTP client, batch interface, strict JSON parser, mock engine.
- `src/stability`: multi-frame consistency, confidence threshold, debounce, bbox smoothing.
- `src/ui`: camera overlay arrows, person box, and <=10 character instruction text.

## Production integration notes

- Replace `PrototypeVisionPreprocessor` with MediaPipe, MoveNet, or YOLO output adapters.
- Put ShutterMuse behind an HTTP API; avoid embedding the model directly in the mobile app.
- Keep `EXPO_PUBLIC_SAMPLE_FPS` between `2` and `5`.
- Keep `EXPO_PUBLIC_AI_TIMEOUT_MS` near the target update budget; default is `280ms`.
