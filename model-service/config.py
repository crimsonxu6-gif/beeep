from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class ModelSettings:
    repo_path: str = os.getenv("SHUTTERMUSE_REPO_PATH", "").strip()
    model_path: str = os.getenv("SHUTTERMUSE_MODEL_PATH", "ShutterMuse/ShutterMuse").strip()
    lora_path: str = os.getenv("SHUTTERMUSE_LORA_PATH", "").strip()
    device: str = os.getenv("SHUTTERMUSE_DEVICE", "cuda").strip()
    device_map: str = os.getenv("SHUTTERMUSE_DEVICE_MAP", "auto").strip()
    warmup_image: str = os.getenv("SHUTTERMUSE_WARMUP_IMAGE", "").strip()
    prompt_mode: str = os.getenv("SHUTTERMUSE_PROMPT_MODE", "official").strip().lower()
    official_coordinate_format: str = os.getenv(
        "SHUTTERMUSE_OFFICIAL_COORDINATES", "norm1000"
    ).strip().lower()
    max_new_tokens: int = int(os.getenv("SHUTTERMUSE_MAX_NEW_TOKENS", "96"))
    input_short_edge: int = int(os.getenv("SHUTTERMUSE_INPUT_SHORT_EDGE", "1024"))
    generation_max_time_ms: int = int(os.getenv("SHUTTERMUSE_GENERATION_MAX_TIME_MS", "14000"))
    inference_timeout_ms: int = int(os.getenv("SHUTTERMUSE_INFERENCE_TIMEOUT_MS", "15000"))
    trust_remote_code: bool = _bool("SHUTTERMUSE_TRUST_REMOTE_CODE", False)
    merge_lora: bool = _bool("SHUTTERMUSE_MERGE_LORA", True)
    load_in_4bit: bool = _bool("SHUTTERMUSE_LOAD_IN_4BIT", False)
    cpu_offload: bool = _bool("SHUTTERMUSE_CPU_OFFLOAD", False)
    gpu_max_memory: str = os.getenv("SHUTTERMUSE_GPU_MAX_MEMORY", "7GiB").strip()
    cpu_max_memory: str = os.getenv("SHUTTERMUSE_CPU_MAX_MEMORY", "8GiB").strip()
    offload_folder: str = os.getenv("SHUTTERMUSE_OFFLOAD_FOLDER", "").strip()
    debug_output: bool = _bool("SHUTTERMUSE_DEBUG_OUTPUT", False)
    autoload: bool = _bool("SHUTTERMUSE_AUTOLOAD", True)
    api_key: str = os.getenv("SHUTTERMUSE_SERVICE_API_KEY", "")

    def repository(self) -> Path:
        return Path(self.repo_path)

    def resolved_offload_folder(self) -> Path:
        if self.offload_folder:
            return Path(self.offload_folder)
        return self.repository().parent / "shuttermuse-offload"


settings = ModelSettings()
