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
.venv/bin/python -m pip install -r requirements.txt
export SHUTTERMUSE_REPO_PATH=/models/ShutterMuse
export SHUTTERMUSE_MODEL_PATH=ShutterMuse/ShutterMuse
export SHUTTERMUSE_DEVICE=cuda
.venv/bin/python -m uvicorn app:app --host 0.0.0.0 --port 8100
```

PowerShell uses the same interpreter explicitly:

```powershell
cd D:\beeep\model-service
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-4bit.txt
# Windows CUDA 12.8: replace PyPI CPU wheels with matching CUDA builds.
python -m pip install --force-reinstall -r requirements-cuda128.txt
python -m uvicorn app:app --host 0.0.0.0 --port 8100
```

For an 8 GB research GPU, install `requirements-4bit.txt` and set
`SHUTTERMUSE_LOAD_IN_4BIT=1`. If the quantized checkpoint does not fit entirely in
available VRAM, also set `SHUTTERMUSE_CPU_OFFLOAD=1`,
`SHUTTERMUSE_GPU_MAX_MEMORY=7GiB` and `SHUTTERMUSE_CPU_MAX_MEMORY=8GiB`. Offloaded
state defaults to a sibling `shuttermuse-offload` directory next to the repository.
For a local smoke test, `SHUTTERMUSE_INPUT_SHORT_EDGE=512` reduces vision prefill cost;
use the default 1024 and the released precision for quality evaluation.
This may make validation possible,
but it changes the runtime precision from the released BF16 configuration and must be
evaluated separately. Full BF16 deployment should use a GPU with sufficient VRAM.

On the tested 8 GB Windows laptop, the official prompt needed 128 generated tokens to
finish its verbose `instance_info` JSON; 64 tokens stopped inside `reason`. CPU offload
also makes generation far slower than the production timeout budget. For a conservative
engineering smoke test only, use a 384-512 input short edge and temporarily increase the
generation/model-service deadlines. Do not use those local latency numbers as a product
benchmark.

On startup the service validates the repository, model/LoRA paths and CUDA, loads the
model and processor once, then runs a parse-checked warmup using the configured image or
the official repository test image. `/ready` returns 503 while loading or after failure.

The executor permits one active GPU inference and one replaceable pending inference.
A newer pending frame supersedes the previous not-yet-started frame. A timed-out active
GPU generation is not falsely reported as cancelled; it continues alone while queue size
remains bounded.

Two prompt modes are available and can be evaluated against the same images. They are
never combined in a single prompt:

- `SHUTTERMUSE_PROMPT_MODE=official` preserves the released photographer-side wording
  and `(x1,y1),(x2,y2)` output. Set `SHUTTERMUSE_OFFICIAL_COORDINATES=norm1000` (the
  default) or `pixels` according to the upstream contract being evaluated.
- `SHUTTERMUSE_PROMPT_MODE=beeep_json` requests only strict normalized JSON:

```json
{"decision":"refine","bbox_norm":[0.08,0.11,0.91,0.94],"confidence":0.84}
```

The parser never guesses a coordinate system from numeric size. JSON must use one of
`bbox_norm`, `bbox_1000` or `bbox_pixels`; official text uses the explicitly configured
official coordinate format. Only a validated 0-1 `bbox_norm` leaves this service.
Invalid, reversed or ambiguous coordinates return `status=low_confidence` and
`error_code=INVALID_MODEL_OUTPUT`. A two-percent edge tolerance treats an almost-full
box as `keep`.

The initial validation budgets are ordered so model generation stops before each outer
HTTP layer: generation 14 s, model-service wait 15 s, Beeep backend wait 17 s and mobile
wait 19 s. `SHUTTERMUSE_MAX_NEW_TOKENS` defaults to 96. Transformers `max_time` is passed
into generation; an HTTP timeout alone cannot stop an already-running GPU call.

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
