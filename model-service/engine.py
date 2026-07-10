from __future__ import annotations

import base64
import logging
import re
import threading
import time
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps

from config import ModelSettings
from output_parser import ParsedComposition, parse_photographer_output
from prompt import build_beeep_photographer_prompt
from schemas import PhotographerRequest

logger = logging.getLogger("shuttermuse")


class ModelServiceError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class ShutterMuseEngine:
    def __init__(self, settings: ModelSettings) -> None:
        self.settings = settings
        self.model: Any | None = None
        self.processor: Any | None = None
        self.state = "unconfigured"
        self.error_code: str | None = None
        self.error_message: str | None = None
        self.warmup_completed = False
        self.load_count = 0
        self.inference_count = 0
        self._state_lock = threading.Lock()

    def mark_loading(self) -> None:
        with self._state_lock:
            self.state = "loading"
            self.error_code = None
            self.error_message = None

    def initialize(self) -> None:
        self.mark_loading()
        try:
            self._validate_configuration()
            self._load_once()
            self._warmup()
            with self._state_lock:
                self.state = "ready"
            logger.info("Inference ready")
        except ModelServiceError as exc:
            self._record_failure(exc.code, str(exc))
            raise
        except Exception as exc:  # noqa: BLE001
            code = self._classify_exception(exc, "MODEL_LOAD_FAILED")
            self._record_failure(code, str(exc))
            raise ModelServiceError(code, str(exc)) from exc

    def infer(self, request: PhotographerRequest) -> tuple[ParsedComposition, str, int]:
        if self.state != "ready" or self.model is None or self.processor is None:
            raise ModelServiceError("MODEL_NOT_READY", "ShutterMuse model is not ready")
        image = self._decode_image(request.image_base64)
        prompt = build_beeep_photographer_prompt(
            request.target_ratio,
            request.composition_mode,
            request.mode,
            request.language,
        )
        started = time.perf_counter()
        try:
            raw = self._generate(image, prompt)
        except Exception as exc:  # noqa: BLE001
            code = self._classify_exception(exc, "INFERENCE_FAILED")
            raise ModelServiceError(code, str(exc)) from exc
        inference_ms = int((time.perf_counter() - started) * 1000)
        parsed = parse_photographer_output(raw, image.width, image.height)
        self.inference_count += 1
        if self.settings.debug_output:
            logger.info(
                "inference_debug request_id=%s frame_id=%s target_ratio=%s composition_mode=%s "
                "raw_output=%r parsed_bbox=%s decision=%s confidence=%s inference_ms=%s",
                request.request_id,
                request.frame_id,
                request.target_ratio,
                request.composition_mode,
                raw[:2000],
                parsed.bbox_norm,
                parsed.decision,
                parsed.confidence,
                inference_ms,
            )
        if parsed.status != "success":
            logger.warning(
                "Output parsing failed request_id=%s frame_id=%s error_code=%s",
                request.request_id,
                request.frame_id,
                parsed.error_code,
            )
        return parsed, raw, inference_ms

    def readiness(self, executor_active: bool, executor_pending: int) -> dict[str, Any]:
        return {
            "status": self.state,
            "guidance_engine": "shuttermuse",
            "model_loaded": self.model is not None,
            "processor_loaded": self.processor is not None,
            "warmup_completed": self.warmup_completed,
            "device": self.settings.device,
            "model_name": self.settings.model_path or "ShutterMuse/ShutterMuse",
            "load_count": self.load_count,
            "inference_count": self.inference_count,
            "executor_active": executor_active,
            "executor_pending": executor_pending,
            "error_code": self.error_code,
            "error_message": self.error_message,
        }

    def _validate_configuration(self) -> None:
        if not self.settings.repo_path:
            raise ModelServiceError("REPOSITORY_NOT_CONFIGURED", "SHUTTERMUSE_REPO_PATH is required")
        repository = self.settings.repository()
        inference_script = repository / "evaluation" / "photographer-side" / "infer_single_qwen_lora.py"
        if not repository.is_dir() or not inference_script.is_file():
            raise ModelServiceError("REPOSITORY_NOT_FOUND", f"Invalid ShutterMuse repository: {repository}")
        logger.info("ShutterMuse repository loaded path=%s", repository)

        if not self.settings.model_path:
            raise ModelServiceError("MODEL_NOT_CONFIGURED", "SHUTTERMUSE_MODEL_PATH is required")
        if self._looks_like_local_path(self.settings.model_path):
            model_path = Path(self.settings.model_path)
            if not model_path.is_dir() or not (model_path / "config.json").is_file():
                raise ModelServiceError("MODEL_NOT_FOUND", f"Invalid model path: {model_path}")
        else:
            try:
                from huggingface_hub import model_info

                model_info(self.settings.model_path)
            except ImportError as exc:
                raise ModelServiceError("DEPENDENCY_MISSING", "huggingface_hub is not installed") from exc
            except Exception as exc:  # noqa: BLE001
                raise ModelServiceError(
                    "MODEL_NOT_FOUND",
                    f"Model repository is not accessible: {self.settings.model_path}",
                ) from exc
            logger.info("Model repository verified source=%s", self.settings.model_path)
        if self.settings.lora_path and not Path(self.settings.lora_path).exists():
            raise ModelServiceError("LORA_NOT_FOUND", f"LoRA path does not exist: {self.settings.lora_path}")

        try:
            import torch
        except ImportError as exc:
            raise ModelServiceError("DEPENDENCY_MISSING", "PyTorch is not installed") from exc
        if self.settings.device.startswith("cuda") and not torch.cuda.is_available():
            raise ModelServiceError("CUDA_UNAVAILABLE", "CUDA is not available")
        if self.settings.device.startswith("cuda"):
            logger.info("CUDA available device=%s", torch.cuda.get_device_name(0))

    def _load_once(self) -> None:
        if self.model is not None and self.processor is not None:
            return
        try:
            import torch
            from transformers import AutoProcessor, Qwen3VLForConditionalGeneration

            model_kwargs: dict[str, Any] = {
                "torch_dtype": "auto",
                "device_map": self.settings.device_map,
                "trust_remote_code": self.settings.trust_remote_code,
            }
            if self.settings.load_in_4bit:
                from transformers import BitsAndBytesConfig

                model_kwargs["quantization_config"] = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.bfloat16,
                    bnb_4bit_quant_type="nf4",
                )
            logger.info("Base model loading source=%s", self.settings.model_path)
            model = Qwen3VLForConditionalGeneration.from_pretrained(
                self.settings.model_path,
                **model_kwargs,
            )
            logger.info("Base model loaded")
            if self.settings.lora_path:
                from peft import PeftModel

                model = PeftModel.from_pretrained(model, self.settings.lora_path)
                logger.info("LoRA loaded path=%s", self.settings.lora_path)
                if self.settings.merge_lora:
                    model = model.merge_and_unload()
                    logger.info("LoRA merged")
            else:
                logger.info("LoRA not configured; using merged checkpoint")
            processor = AutoProcessor.from_pretrained(
                self.settings.model_path,
                trust_remote_code=self.settings.trust_remote_code,
            )
            logger.info("Processor loaded")
            model.eval()
            self.model = model
            self.processor = processor
            self.load_count += 1
            logger.info(
                "Model dispatched device_map=%s requested_device=%s",
                self.settings.device_map,
                self.settings.device,
            )
        except ImportError as exc:
            raise ModelServiceError("DEPENDENCY_MISSING", str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            code = self._classify_exception(exc, "MODEL_LOAD_FAILED")
            raise ModelServiceError(code, str(exc)) from exc

    def _warmup(self) -> None:
        logger.info("Warmup started")
        image_path = self._warmup_image_path()
        try:
            with Image.open(image_path) as raw_image:
                image = ImageOps.exif_transpose(raw_image).convert("RGB")
            prompt = build_beeep_photographer_prompt("3:4", "auto")
            raw = self._generate(image, prompt)
            parsed = parse_photographer_output(raw, image.width, image.height)
            if parsed.status != "success":
                raise ModelServiceError("WARMUP_PARSE_FAILED", "Warmup output could not be parsed")
            self.warmup_completed = True
            logger.info("Warmup completed decision=%s bbox_norm=%s", parsed.decision, parsed.bbox_norm)
        except ModelServiceError:
            raise
        except Exception as exc:  # noqa: BLE001
            code = self._classify_exception(exc, "WARMUP_FAILED")
            raise ModelServiceError(code, str(exc)) from exc

    def _generate(self, image: Image.Image, prompt: str) -> str:
        import torch
        from qwen_vl_utils import process_vision_info

        image_for_model = self._resize_for_inference(image)
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image_for_model},
                    {"type": "text", "text": prompt},
                ],
            }
        ]
        try:
            text = self.processor.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=False,
            )
        except TypeError:
            text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        image_inputs, video_inputs = process_vision_info(messages)
        inputs = self.processor(
            text=[text],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt",
        ).to(self.settings.device)
        with torch.inference_mode():
            generated = self.model.generate(**inputs, max_new_tokens=self.settings.max_new_tokens)
        trimmed = [
            output[len(input_ids) :] for input_ids, output in zip(inputs.input_ids, generated, strict=True)
        ]
        return self.processor.batch_decode(
            trimmed,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )[0]

    def _warmup_image_path(self) -> Path:
        if self.settings.warmup_image:
            path = Path(self.settings.warmup_image)
        else:
            path = self.settings.repository() / "test" / "401128801616615964.webp"
        if not path.is_file():
            raise ModelServiceError("WARMUP_IMAGE_NOT_FOUND", f"Warmup image not found: {path}")
        return path

    @staticmethod
    def _resize_for_inference(image: Image.Image, min_side: int = 1024) -> Image.Image:
        width, height = image.size
        short_edge = min(width, height)
        if short_edge <= min_side:
            return image
        scale = min_side / short_edge
        return image.resize((int(width * scale), int(height * scale)), Image.Resampling.LANCZOS)

    @staticmethod
    def _decode_image(value: str) -> Image.Image:
        raw = value.split(",", 1)[1] if "," in value and "base64" in value[:48] else value
        try:
            payload = base64.b64decode(raw, validate=True)
            with Image.open(BytesIO(payload)) as image:
                return ImageOps.exif_transpose(image).convert("RGB")
        except Exception as exc:  # noqa: BLE001
            raise ModelServiceError("INVALID_IMAGE", "Image could not be decoded") from exc

    @staticmethod
    def _looks_like_local_path(value: str) -> bool:
        return (
            Path(value).is_absolute()
            or value.startswith(("./", "../"))
            or bool(re.match(r"^[A-Za-z]:", value))
        )

    @staticmethod
    def _classify_exception(exc: Exception, fallback: str) -> str:
        text = str(exc).lower()
        if "out of memory" in text or "cuda error: out of memory" in text:
            return "CUDA_OUT_OF_MEMORY"
        if isinstance(exc, ModuleNotFoundError) or "no module named" in text:
            return "DEPENDENCY_MISSING"
        if "cuda" in text and "not available" in text:
            return "CUDA_UNAVAILABLE"
        return fallback

    def _record_failure(self, code: str, message: str) -> None:
        with self._state_lock:
            self.state = "error"
            self.error_code = code
            self.error_message = message[:500]
        logger.exception("ShutterMuse startup failed code=%s message=%s", code, message)
