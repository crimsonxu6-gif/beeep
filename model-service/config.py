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
    max_new_tokens: int = int(os.getenv("SHUTTERMUSE_MAX_NEW_TOKENS", "256"))
    inference_timeout_ms: int = int(os.getenv("SHUTTERMUSE_INFERENCE_TIMEOUT_MS", "30000"))
    trust_remote_code: bool = _bool("SHUTTERMUSE_TRUST_REMOTE_CODE", False)
    merge_lora: bool = _bool("SHUTTERMUSE_MERGE_LORA", True)
    load_in_4bit: bool = _bool("SHUTTERMUSE_LOAD_IN_4BIT", False)
    debug_output: bool = _bool("SHUTTERMUSE_DEBUG_OUTPUT", False)
    autoload: bool = _bool("SHUTTERMUSE_AUTOLOAD", True)
    api_key: str = os.getenv("SHUTTERMUSE_SERVICE_API_KEY", "")

    def repository(self) -> Path:
        return Path(self.repo_path)


settings = ModelSettings()
