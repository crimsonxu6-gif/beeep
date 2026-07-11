from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass
from typing import Any, Literal

CoordinateSource = Literal["bbox_norm", "bbox_1000", "bbox_pixels", "official_1000", "official_pixels"]


@dataclass(frozen=True)
class ParsedComposition:
    status: str
    decision: str | None
    bbox_norm: tuple[float, float, float, float] | None
    confidence: float | None
    error_code: str | None = None
    coordinate_source: CoordinateSource | None = None


def _first_object(raw: str) -> dict[str, Any] | None:
    text = raw.strip()
    for loader in (json.loads, ast.literal_eval):
        try:
            value = loader(text)
            if isinstance(value, dict):
                return value
        except Exception:
            pass
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    for index in range(start, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                block = text[start : index + 1]
                for loader in (json.loads, ast.literal_eval):
                    try:
                        value = loader(block)
                        if isinstance(value, dict):
                            return value
                    except Exception:
                        pass
                return None
    return None


def _bbox_values(value: Any) -> list[float] | None:
    if isinstance(value, (list, tuple)) and len(value) == 4:
        try:
            return [float(item) for item in value]
        except (TypeError, ValueError):
            return None
    return None


def _official_bbox(raw: str) -> list[float] | None:
    number = r"[-+]?\d*\.?\d+"
    paired = re.search(
        rf"\(\s*({number})\s*,\s*({number})\s*\)\s*,\s*"
        rf"\(\s*({number})\s*,\s*({number})\s*\)",
        raw,
    )
    return [float(value) for value in paired.groups()] if paired else None


def _normalize_bbox(
    values: list[float] | None,
    image_width: int,
    image_height: int,
    source: CoordinateSource,
) -> tuple[float, float, float, float] | None:
    if not values or len(values) != 4 or image_width <= 0 or image_height <= 0:
        return None
    if source == "bbox_norm":
        normalized = values
    elif source in {"bbox_1000", "official_1000"}:
        normalized = [value / 1000 for value in values]
    else:
        normalized = [
            values[0] / image_width,
            values[1] / image_height,
            values[2] / image_width,
            values[3] / image_height,
        ]
    x1, y1, x2, y2 = normalized
    if not (0 <= x1 < x2 <= 1 and 0 <= y1 < y2 <= 1):
        return None
    return x1, y1, x2, y2


def _is_full_frame(bbox: tuple[float, float, float, float]) -> bool:
    x1, y1, x2, y2 = bbox
    return x1 <= 0.02 and y1 <= 0.02 and x2 >= 0.98 and y2 >= 0.98


def parse_photographer_output(
    raw: str,
    image_width: int,
    image_height: int,
    *,
    prompt_mode: Literal["official", "beeep_json"] = "beeep_json",
    official_coordinate_format: Literal["norm1000", "pixels"] = "norm1000",
) -> ParsedComposition:
    obj = _first_object(raw)
    decision: str | None = None
    confidence: float | None = None
    values: list[float] | None = None
    source: CoordinateSource | None = None

    if obj is not None:
        raw_decision = obj.get("decision")
        if raw_decision in {"keep", "refine", "reject"}:
            decision = str(raw_decision)
        if isinstance(obj.get("confidence"), (int, float)):
            confidence = float(obj["confidence"])
            if not 0 <= confidence <= 1:
                return ParsedComposition("low_confidence", None, None, None, "INVALID_MODEL_OUTPUT")
        for field, coordinate_source in (
            ("bbox_norm", "bbox_norm"),
            ("bbox_1000", "bbox_1000"),
            ("bbox_pixels", "bbox_pixels"),
        ):
            if field in obj:
                values = _bbox_values(obj[field])
                source = coordinate_source
                break
        if values is None and prompt_mode == "official":
            instances = obj.get("instance_info")
            if isinstance(instances, list) and instances and isinstance(instances[0], dict):
                composition_xy = instances[0].get("composition_xy")
                if isinstance(composition_xy, str):
                    values = _official_bbox(composition_xy)
                    source = (
                        "official_1000"
                        if official_coordinate_format == "norm1000"
                        else "official_pixels"
                    )

    if values is None and prompt_mode == "official":
        values = _official_bbox(raw)
        source = "official_1000" if official_coordinate_format == "norm1000" else "official_pixels"

    if decision == "reject" and values is None:
        return ParsedComposition("success", "reject", None, confidence)
    if values is None or source is None:
        return ParsedComposition("low_confidence", None, None, confidence, "INVALID_MODEL_OUTPUT")

    bbox = _normalize_bbox(values, image_width, image_height, source)
    if bbox is None:
        return ParsedComposition("low_confidence", None, None, confidence, "INVALID_MODEL_OUTPUT", source)

    if decision is None:
        decision = "keep" if _is_full_frame(bbox) else "refine"
    elif decision == "keep" and not _is_full_frame(bbox):
        decision = "refine"
    return ParsedComposition("success", decision, bbox, confidence, coordinate_source=source)
