# ShutterMuse GPU Model Service

This service owns the released ShutterMuse model and photographer-side inference only.
Beeep FastAPI remains responsible for MediaPipe, normalized product actions, frame
freshness and mobile API behavior.

The official merged checkpoint is `ShutterMuse/ShutterMuse` (Qwen3-VL, about 9B BF16
parameters). A base model plus LoRA is also accepted for compatibility. No retraining is
part of this MVP.

## Start

```bash
cd model-service
python -m venv .venv
.venv/bin/pip install -r requirements.txt
export SHUTTERMUSE_REPO_PATH=/models/ShutterMuse
export SHUTTERMUSE_MODEL_PATH=ShutterMuse/ShutterMuse
export SHUTTERMUSE_DEVICE=cuda
.venv/bin/uvicorn app:app --host 0.0.0.0 --port 8100
```

For an 8 GB research GPU, install `requirements-4bit.txt` and set
`SHUTTERMUSE_LOAD_IN_4BIT=1`. This may make validation possible,
but it changes the runtime precision from the released BF16 configuration and must be
evaluated separately. Full BF16 deployment should use a GPU with sufficient VRAM.

On startup the service validates the repository, model/LoRA paths and CUDA, loads the
model and processor once, then runs a parse-checked warmup using the configured image or
the official repository test image. `/ready` returns 503 while loading or after failure.

The executor permits one active GPU inference and one replaceable pending inference.
A newer pending frame supersedes the previous not-yet-started frame. A timed-out active
GPU generation is not falsely reported as cancelled; it continues alone while queue size
remains bounded.

Expected model text is strict JSON:

```json
{"decision":"refine","bbox_norm":[0.08,0.11,0.91,0.94],"confidence":0.84}
```

The parser also accepts the released task's legacy `(x1,y1),(x2,y2)` text internally.
Only a validated 0-1 `bbox_norm` leaves this service. Invalid or reversed coordinates
return `status=low_confidence` and `error_code=INVALID_MODEL_OUTPUT`.

Readiness while loading:

```json
{"status":"loading","model_loaded":false,"warmup_completed":false,"device":"cuda"}
```

Readiness after successful warmup includes `model_loaded`, `processor_loaded`,
`warmup_completed`, `load_count`, `inference_count`, executor state and device. Failures
return HTTP 503 with a specific code such as `MODEL_NOT_FOUND`, `LORA_NOT_FOUND`,
`CUDA_UNAVAILABLE`, `CUDA_OUT_OF_MEMORY`, `DEPENDENCY_MISSING`, `MODEL_LOAD_FAILED` or
`WARMUP_PARSE_FAILED`.

Set `SHUTTERMUSE_DEBUG_OUTPUT=1` only in development to log request/frame metadata,
raw model text, normalized bbox, decision and latency. Image Base64 is never logged.

The upstream repository currently says `TODO` for its license. Do not commercialize,
redistribute weights or sell this model service until code and model licenses are explicit.
