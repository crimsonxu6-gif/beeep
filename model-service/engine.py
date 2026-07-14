from __future__ import annotations

import base64
import importlib.util
import json
import logging
import re
import threading
import time
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps

from config import ModelSettings
from output_parser import ParsedComposition, parse_photographer_output
from prompt import build_photographer_prompt
from schemas import PhotographerRequest

logger = logging.getLogger("shuttermuse")


@dataclass(frozen=True)
class GenerationResult:
    raw_output: str
    generated_token_count: int
    reached_max_new_tokens: bool
    stopped_by_structure: bool


@dataclass(frozen=True)
class InferenceResult:
    parsed: ParsedComposition
    generation: GenerationResult
    inference_ms: int
    parser_comparison: str


def _complete_json_object(text: str) -> bool:
    start = text.find("{")
    if start < 0:
        return False
    try:
        _, end = json.JSONDecoder().raw_decode(text[start:])
    except json.JSONDecodeError:
        return False
    return not text[start + end :].strip()


def is_structured_output_complete(text: str, prompt_mode: str) -> bool:
    if prompt_mode == "beeep_json":
        return _complete_json_object(text)
    # Released checkpoints occasionally answer the official prompt with their
    # training JSON envelope. Either complete representation is safe to stop on.
    has_coordinate_pairs = bool(
        re.search(
            r"\(\s*[-+]?\d*\.?\d+\s*,\s*[-+]?\d*\.?\d+\s*\)\s*,\s*"
            r"\(\s*[-+]?\d*\.?\d+\s*,\s*[-+]?\d*\.?\d+\s*\)",
            text,
        )
    )
    return has_coordinate_pairs or _complete_json_object(text)


class StructuredOutputStoppingCriteria:
    def __init__(self, processor: Any, input_length: int, prompt_mode: str) -> None:
        self.processor = processor
        self.input_length = input_length
        self.prompt_mode = prompt_mode
        self.triggered = False

    def __call__(self, input_ids: Any, _scores: Any, **_kwargs: Any) -> bool:
        generated = input_ids[0][self.input_length :]
        if hasattr(self.processor, "decode"):
            text = self.processor.decode(generated, skip_special_tokens=True)
        else:
            text = self.processor.batch_decode([generated], skip_special_tokens=True)[0]
        self.triggered = is_structured_output_complete(text, self.prompt_mode)
        return self.triggered


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
        self._official_parser: Any | None = None

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

    def infer(self, request: PhotographerRequest) -> InferenceResult:
        if self.state != "ready" or self.model is None or self.processor is None:
            raise ModelServiceError("MODEL_NOT_READY", "ShutterMuse model is not ready")
        image = self._decode_image(request.image_base64)
        prompt = build_photographer_prompt(
            request.prompt_mode,
            request.target_ratio,
            request.composition_mode,
            request.mode,
            request.language,
        )
        started = time.perf_counter()
        try:
            generation = self._generate(image, prompt, request.prompt_mode)
        except Exception as exc:  # noqa: BLE001
            code = self._classify_exception(exc, "INFERENCE_FAILED")
            raise ModelServiceError(code, str(exc)) from exc
        inference_ms = int((time.perf_counter() - started) * 1000)
        parsed = parse_photographer_output(
            generation.raw_output,
            image.width,
            image.height,
            prompt_mode=request.prompt_mode,
            official_coordinate_format=self.settings.official_coordinate_format,
            reached_max_new_tokens=generation.reached_max_new_tokens,
        )
        parser_comparison = self._compare_with_official_parser(
            generation.raw_output,
            image.width,
            image.height,
            parsed.status == "success",
        )
        self.inference_count += 1
        if self.settings.debug_output:
            logger.info(
                "inference_debug request_id=%s frame_id=%s prompt_mode=%s target_ratio=%s "
                "composition_mode=%s raw_output=%r parsed_bbox=%s coordinate_source=%s "
                "decision=%s confidence=%s inference_ms=%s",
                request.request_id,
                request.frame_id,
                request.prompt_mode,
                request.target_ratio,
                request.composition_mode,
                generation.raw_output[:2000],
                parsed.bbox_norm,
                parsed.coordinate_source,
                parsed.decision,
                parsed.confidence,
                inference_ms,
            )
        if parsed.status != "success":
            logger.warning(
                "Output parsing failed request_id=%s frame_id=%s error_code=%s failure_type=%s",
                request.request_id,
                request.frame_id,
                parsed.error_code,
                parsed.parse_failure_type,
            )
        return InferenceResult(parsed, generation, inference_ms, parser_comparison)

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
            "prompt_mode": self.settings.prompt_mode,
            "official_coordinate_format": self.settings.official_coordinate_format,
            "attention_implementation": self.settings.attention_implementation,
            "input_short_edge": self.settings.input_short_edge,
            "generation_config": self.generation_config(),
            "error_code": self.error_code,
            "error_message": self.error_message,
        }

    def _validate_configuration(self) -> None:
        if self.settings.prompt_mode not in {"official", "beeep_json"}:
            raise ModelServiceError(
                "INVALID_CONFIGURATION",
                "SHUTTERMUSE_PROMPT_MODE must be official or beeep_json",
            )
        if self.settings.official_coordinate_format not in {"norm1000", "pixels"}:
            raise ModelServiceError(
                "INVALID_CONFIGURATION",
                "SHUTTERMUSE_OFFICIAL_COORDINATES must be norm1000 or pixels",
            )
        if self.settings.attention_implementation not in {
            "default",
            "sdpa",
            "flash_attention_2",
        }:
            raise ModelServiceError(
                "INVALID_CONFIGURATION",
                "SHUTTERMUSE_ATTENTION_IMPLEMENTATION must be default, sdpa, or flash_attention_2",
            )
        if not 1 <= self.settings.max_new_tokens <= 512:
            raise ModelServiceError(
                "INVALID_CONFIGURATION",
                "SHUTTERMUSE_MAX_NEW_TOKENS must be between 1 and 512",
            )
        if not 1 <= self.settings.raw_output_max_chars <= 20_000:
            raise ModelServiceError(
                "INVALID_CONFIGURATION",
                "SHUTTERMUSE_RAW_OUTPUT_MAX_CHARS must be between 1 and 20000",
            )
        if self.settings.generation_max_time_ms >= self.settings.inference_timeout_ms:
            raise ModelServiceError(
                "INVALID_CONFIGURATION",
                "Generation deadline must be shorter than model-service inference timeout",
            )
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
                **self._attention_model_kwargs(),
            }
            if self.settings.load_in_4bit:
                from transformers import BitsAndBytesConfig

                model_kwargs["quantization_config"] = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.bfloat16,
                    bnb_4bit_quant_type="nf4",
                    llm_int8_enable_fp32_cpu_offload=self.settings.cpu_offload,
                )
                if self.settings.cpu_offload:
                    offload_folder = self.settings.resolved_offload_folder()
                    offload_folder.mkdir(parents=True, exist_ok=True)
                    model_kwargs["max_memory"] = {
                        0: self.settings.gpu_max_memory,
                        "cpu": self.settings.cpu_max_memory,
                    }
                    model_kwargs["offload_folder"] = str(offload_folder)
                    model_kwargs["offload_state_dict"] = True
                    logger.info(
                        "4-bit CPU offload enabled gpu_max_memory=%s cpu_max_memory=%s folder=%s",
                        self.settings.gpu_max_memory,
                        self.settings.cpu_max_memory,
                        offload_folder,
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
            prompt = build_photographer_prompt(
                self.settings.prompt_mode,
                "3:4",
                "auto",
            )
            generation = self._generate(image, prompt, self.settings.prompt_mode)
            if self.settings.debug_output:
                logger.info("warmup_raw_output=%r", generation.raw_output[:2000])
            parsed = parse_photographer_output(
                generation.raw_output,
                image.width,
                image.height,
                prompt_mode=self.settings.prompt_mode,
                official_coordinate_format=self.settings.official_coordinate_format,
                reached_max_new_tokens=generation.reached_max_new_tokens,
            )
            if parsed.status != "success":
                raise ModelServiceError("WARMUP_PARSE_FAILED", "Warmup output could not be parsed")
            self.warmup_completed = True
            logger.info("Warmup completed decision=%s bbox_norm=%s", parsed.decision, parsed.bbox_norm)
        except ModelServiceError:
            raise
        except Exception as exc:  # noqa: BLE001
            code = self._classify_exception(exc, "WARMUP_FAILED")
            raise ModelServiceError(code, str(exc)) from exc

    def _generate(self, image: Image.Image, prompt: str, prompt_mode: str) -> GenerationResult:
        import torch
        from qwen_vl_utils import process_vision_info

        image_for_model = self._resize_for_inference(image, self.settings.input_short_edge)
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
        input_length = int(inputs.input_ids.shape[-1])
        stopping_criteria = StructuredOutputStoppingCriteria(
            self.processor,
            input_length,
            prompt_mode,
        )
        with torch.inference_mode():
            generated = self.model.generate(
                **inputs,
                max_new_tokens=self.settings.max_new_tokens,
                max_time=self.settings.generation_max_time_ms / 1000,
                do_sample=False,
                num_beams=1,
                stopping_criteria=[stopping_criteria],
            )
        trimmed = [
            output[len(input_ids) :] for input_ids, output in zip(inputs.input_ids, generated, strict=True)
        ]
        raw_output = self.processor.batch_decode(
            trimmed,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )[0]
        token_count = int(trimmed[0].shape[-1])
        return GenerationResult(
            raw_output=raw_output,
            generated_token_count=token_count,
            reached_max_new_tokens=token_count >= self.settings.max_new_tokens,
            stopped_by_structure=stopping_criteria.triggered,
        )

    def generation_config(self) -> dict[str, Any]:
        return {
            "do_sample": False,
            "num_beams": 1,
            "max_new_tokens": self.settings.max_new_tokens,
            "attention_implementation": self.settings.attention_implementation,
        }

    def _attention_model_kwargs(self) -> dict[str, str]:
        if self.settings.attention_implementation == "default":
            return {}
        return {"attn_implementation": self.settings.attention_implementation}

    def _compare_with_official_parser(
        self,
        raw: str,
        image_width: int,
        image_height: int,
        beeep_success: bool,
    ) -> str:
        try:
            if self._official_parser is None:
                path = self.settings.repository() / "evaluation" / "photographer-side" / "utils.py"
                spec = importlib.util.spec_from_file_location("shuttermuse_official_utils", path)
                if spec is None or spec.loader is None:
                    return "official_unavailable"
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                self._official_parser = module.parse_qwen_bbox
            official_success = self._official_parser(raw, image_width, image_height) is not None
        except Exception:  # noqa: BLE001
            logger.warning("Official parser comparison unavailable", exc_info=True)
            return "official_unavailable"
        if beeep_success and official_success:
            return "both_success"
        if beeep_success:
            return "beeep_only_success"
        if official_success:
            return "official_only_success"
        return "both_failed"

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
