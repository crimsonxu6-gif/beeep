from __future__ import annotations

import base64
import importlib.util
import os
import sys
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from types import ModuleType
from typing import Any

from fastapi import HTTPException

from schemas import (
    AdjustAngleAction,
    AdjustDistanceAction,
    CompositionRecommendation,
    FramingHintAction,
    GuidanceAction,
    GuidanceOutput,
    GuidanceProblem,
    GuidanceRequest,
    HoldAction,
    MoveCameraAction,
    VisionFeatures,
)

try:
    from PIL import Image, ImageOps
except ImportError:  # pragma: no cover - optional runtime dependency
    Image = None
    ImageOps = None


@dataclass(frozen=True)
class RealShutterMuseConfig:
    repo_path: Path
    model_path: str
    lora_path: str = ""
    device: str = "cuda"
    trust_remote_code: bool = False
    merge_lora: bool = True
    max_new_tokens: int = 512

    @classmethod
    def from_env(cls) -> "RealShutterMuseConfig":
        repo_path = os.getenv("SHUTTERMUSE_REPO_PATH", "").strip()
        model_path = os.getenv("SHUTTERMUSE_MODEL_PATH", "").strip()
        if not repo_path:
            raise HTTPException(
                status_code=503,
                detail="SHUTTERMUSE_REPO_PATH is required when BEEEP_GUIDANCE_ENGINE=shuttermuse.",
            )
        if not model_path:
            raise HTTPException(
                status_code=503,
                detail="SHUTTERMUSE_MODEL_PATH is required when BEEEP_GUIDANCE_ENGINE=shuttermuse.",
            )

        return cls(
            repo_path=Path(repo_path),
            model_path=model_path,
            lora_path=os.getenv("SHUTTERMUSE_LORA_PATH", "").strip(),
            device=os.getenv("SHUTTERMUSE_DEVICE", "cuda").strip() or "cuda",
            trust_remote_code=_env_bool("SHUTTERMUSE_TRUST_REMOTE_CODE", default=False),
            merge_lora=_env_bool("SHUTTERMUSE_MERGE_LORA", default=True),
            max_new_tokens=_env_int("SHUTTERMUSE_MAX_NEW_TOKENS", default=512),
        )


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _problem(problem_type: str, description: str) -> GuidanceProblem:
    return GuidanceProblem(type=problem_type, description=description)


def _decode_image(request: GuidanceRequest) -> Any:
    if Image is None or ImageOps is None:
        raise HTTPException(status_code=503, detail="Pillow is required for ShutterMuse image decoding.")
    if not request.image.base64:
        raise HTTPException(status_code=400, detail="image.base64 is required for ShutterMuse inference.")

    raw = request.image.base64
    if "," in raw and "base64" in raw[:48]:
        raw = raw.split(",", 1)[1]

    try:
        image_bytes = base64.b64decode(raw, validate=False)
        with Image.open(BytesIO(image_bytes)) as image_raw:
            return ImageOps.exif_transpose(image_raw).convert("RGB")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="image.base64 could not be decoded as an image.") from exc


def _module_path(repo_path: Path) -> Path:
    return repo_path / "evaluation" / "photographer-side" / "infer_single_qwen_lora.py"


def _load_shuttermuse_module(repo_path: Path) -> ModuleType:
    script_path = _module_path(repo_path)
    if not script_path.exists():
        raise HTTPException(
            status_code=503,
            detail=f"ShutterMuse inference script not found: {script_path}",
        )

    # ShutterMuse imports sibling helpers with bare `from utils import ...`.
    helper_dir = str(script_path.parent)
    if helper_dir not in sys.path:
        sys.path.insert(0, helper_dir)

    spec = importlib.util.spec_from_file_location("beeep_shuttermuse_single", script_path)
    if spec is None or spec.loader is None:
        raise HTTPException(status_code=503, detail="Could not load ShutterMuse inference module.")

    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"ShutterMuse dependencies are not installed: {exc}",
        ) from exc
    return module


def _bbox_to_guidance(
    bbox: list[float] | None,
    image_width: int,
    image_height: int,
    features: VisionFeatures,
) -> GuidanceOutput:
    if not bbox:
        return GuidanceOutput(
            frameId=features.frameId,
            priority="composition",
            problem=_problem("composition_unknown", "构图建议不稳定"),
            actions=[FramingHintAction(type="framing_hint", message="重新取景", confidence=0.62)],
            message="重新取景",
            reason="ShutterMuse 没有返回可解析构图框",
            summary="构图建议不稳定",
            confidence=0.62,
        )

    x1, y1, x2, y2 = bbox
    bbox_norm = (
        max(0.0, min(1.0, x1 / max(image_width, 1))),
        max(0.0, min(1.0, y1 / max(image_height, 1))),
        max(0.0, min(1.0, x2 / max(image_width, 1))),
        max(0.0, min(1.0, y2 / max(image_height, 1))),
    )
    box_width = max(1.0, x2 - x1)
    box_height = max(1.0, y2 - y1)
    center_x = (x1 + x2) / 2 / max(image_width, 1)
    center_y = (y1 + y2) / 2 / max(image_height, 1)
    area_ratio = (box_width * box_height) / max(image_width * image_height, 1)
    actions: list[GuidanceAction] = []

    if center_x < 0.43:
        actions.append(
            MoveCameraAction(type="move_camera", direction="left", message="往左一点", confidence=0.82)
        )
        priority = "composition"
        problem = _problem("crop_left", "最佳区域偏左")
        reason = "ShutterMuse 推荐保留画面左侧区域"
        summary = "最佳区域偏左"
    elif center_x > 0.57:
        actions.append(
            MoveCameraAction(type="move_camera", direction="right", message="往右一点", confidence=0.82)
        )
        priority = "composition"
        problem = _problem("crop_right", "最佳区域偏右")
        reason = "ShutterMuse 推荐保留画面右侧区域"
        summary = "最佳区域偏右"
    elif center_y < 0.36:
        actions.append(
            AdjustAngleAction(type="adjust_angle", direction="raise", message="手机高一点", confidence=0.76)
        )
        priority = "angle"
        problem = _problem("crop_top", "最佳区域偏上")
        reason = "ShutterMuse 推荐保留画面上方区域"
        summary = "最佳区域偏上"
    elif center_y > 0.64:
        actions.append(
            AdjustAngleAction(type="adjust_angle", direction="lower", message="手机低一点", confidence=0.76)
        )
        priority = "angle"
        problem = _problem("crop_bottom", "最佳区域偏下")
        reason = "ShutterMuse 推荐保留画面下方区域"
        summary = "最佳区域偏下"
    elif area_ratio < 0.62:
        actions.append(
            AdjustDistanceAction(
                type="adjust_distance", direction="closer", message="靠近一点", confidence=0.76
            )
        )
        priority = "distance"
        problem = _problem("crop_tighter", "主体占比偏小")
        reason = "ShutterMuse 推荐裁掉较多边缘区域"
        summary = "主体占比偏小"
    elif area_ratio > 0.9:
        actions.append(HoldAction(type="hold", message="保持角度", confidence=0.84))
        priority = "hold"
        problem = _problem("none", "画面稳定")
        reason = "ShutterMuse 推荐区域接近当前完整画面"
        summary = "画面稳定"
    else:
        actions.append(FramingHintAction(type="framing_hint", message="微调构图", confidence=0.7))
        priority = "composition"
        problem = _problem("crop_refine", "构图可微调")
        reason = "ShutterMuse 推荐构图框与当前画面有轻微差异"
        summary = "构图可微调"

    return GuidanceOutput(
        frameId=features.frameId,
        priority=priority,
        problem=problem,
        actions=actions[:2],
        message=actions[0].message,
        reason=reason,
        summary=summary,
        confidence=max(action.confidence or 0.7 for action in actions[:2]),
        composition=CompositionRecommendation(
            decision="keep" if area_ratio > 0.9 else "refine",
            bbox_norm=bbox_norm,
        ),
    )


class RealShutterMuseAdapter:
    def __init__(self, config: RealShutterMuseConfig) -> None:
        self.config = config
        self._module: ModuleType | None = None
        self._model: Any | None = None
        self._processor: Any | None = None

    @classmethod
    def from_env(cls) -> "RealShutterMuseAdapter":
        return cls(RealShutterMuseConfig.from_env())

    def infer(self, request: GuidanceRequest, features: VisionFeatures) -> GuidanceOutput:
        image = _decode_image(request)
        module = self._ensure_module()
        model, processor = self._ensure_model(module)

        instruction = module.build_photographer_prompt(image)
        output_text = module.run_inference(
            model=model,
            processor=processor,
            image=image,
            instruction=instruction,
            max_new_tokens=self.config.max_new_tokens,
            device=self.config.device,
            side="photographer",
        )
        image_width, image_height = image.size
        pred_bbox = module.parse_qwen_bbox(output_text, image_width, image_height)
        return _bbox_to_guidance(pred_bbox, image_width, image_height, features)

    def _ensure_module(self) -> ModuleType:
        if self._module is None:
            self._module = _load_shuttermuse_module(self.config.repo_path)
        return self._module

    def _ensure_model(self, module: ModuleType) -> tuple[Any, Any]:
        if self._model is None or self._processor is None:
            try:
                self._model, self._processor = module.load_qwen_model(
                    self.config.model_path,
                    self.config.lora_path,
                    self.config.trust_remote_code,
                    merge_lora=self.config.merge_lora,
                )
            except ImportError as exc:
                raise HTTPException(
                    status_code=503,
                    detail=f"ShutterMuse dependencies are not installed: {exc}",
                ) from exc
            except Exception as exc:  # noqa: BLE001
                raise HTTPException(
                    status_code=503, detail=f"ShutterMuse model failed to load: {exc}"
                ) from exc
        return self._model, self._processor
