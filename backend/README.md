# Beeep FastAPI Guidance Backend

This backend keeps ShutterMuse-style guidance out of the mobile app. It uses
MediaPipe for the first production-oriented vision pass and returns strict
`GuidanceOutput` JSON.

## Run

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

For Android dev-client testing on the same Wi-Fi, set these in the Expo env
using your computer LAN IP:

```bash
EXPO_PUBLIC_MEDIAPIPE_VISION_API_URL=http://192.168.0.106:8000/vision/features
EXPO_PUBLIC_SHUTTERMUSE_API_URL=http://192.168.0.106:8000/guidance
```

## Endpoints

- `POST /vision/features`: `image + frame_id -> VisionFeatures`
- `POST /guidance`: `image + optional vision_features -> GuidanceOutput`

`/guidance` computes MediaPipe features internally when `vision_features` is not
provided. The rule-based `ShutterMuseGuidanceEngine` is intentionally isolated
in `backend/model/shuttermuse.py` so it can later be replaced by the real
ShutterMuse service/model without changing the mobile app contract.
