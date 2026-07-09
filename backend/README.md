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
- `GET /guidance/status`: current guidance engine mode and model load state

Guidance output is product-oriented, not a photo critique:

```json
{
  "priority": "lighting",
  "problem": {
    "type": "backlight",
    "description": "人物逆光"
  },
  "actions": [
    {
      "type": "lighting_hint",
      "message": "转向光源",
      "confidence": 0.86
    }
  ],
  "message": "转向光源",
  "reason": "背景亮度明显高于主体区域",
  "summary": "人物逆光",
  "confidence": 0.86
}
```

Rules:

- Return at most 2 actions.
- `message` is Chinese and no more than 10 characters.
- `problem` and `reason` are for developer debugging.
- Allowed action types: `move_camera`, `adjust_pose`, `framing_hint`, `lighting_hint`, `adjust_distance`, `adjust_angle`, `hold`.

`/guidance` computes MediaPipe features internally when `vision_features` is not
provided. The default rule-based engine is intentionally isolated so the mobile
app contract stays unchanged when the real ShutterMuse model is enabled.

## Guidance engine modes

Default local mode:

```bash
BEEEP_GUIDANCE_ENGINE=rule
```

Real ShutterMuse mode:

```bash
BEEEP_GUIDANCE_ENGINE=shuttermuse
SHUTTERMUSE_REPO_PATH=D:\models\ShutterMuse
SHUTTERMUSE_MODEL_PATH=D:\models\Qwen3-VL-8B-Instruct
SHUTTERMUSE_LORA_PATH=D:\models\ShutterMuse-LoRA
SHUTTERMUSE_DEVICE=cuda
SHUTTERMUSE_TRUST_REMOTE_CODE=0
SHUTTERMUSE_MERGE_LORA=1
SHUTTERMUSE_MAX_NEW_TOKENS=512
```

The adapter loads ShutterMuse lazily on the first `/guidance` request. It reuses
ShutterMuse's photographer-side inference, parses the recommended composition
box, and maps it into Beeep actions such as `move_camera`, `adjust_distance`,
`adjust_angle`, `framing_hint`, or `hold`.

Install the ShutterMuse runtime separately from this lightweight backend:

```bash
git clone https://github.com/lijayuTnT/ShutterMuse.git D:\models\ShutterMuse
cd D:\models\ShutterMuse
pip install -r requirements.txt
```

Then download the released ShutterMuse checkpoint/LoRA and the matching Qwen-VL
base or merged checkpoint, and point the environment variables above to those
paths.
