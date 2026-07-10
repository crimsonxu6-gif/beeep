from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ParsedComposition:
    status: str
    decision: str | None
    bbox_norm: tuple[float, float, float, float] | None
    confidence: float | None
    error_code: str | None = None


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
    if isinstance(value, str):
        return _legacy_bbox(value)
    return None


def _legacy_bbox(raw: str) -> list[float] | None:
    number = r"[-+]?\d*\.?\d+"
    paired = re.search(
        rf"\(\s*({number})\s*,\s*({number})\s*\)\s*,\s*"
        rf"\(\s*({number})\s*,\s*({number})\s*\)",
        raw,
    )
    if paired:
        return [float(value) for value in paired.groups()]
    bracketed = re.search(
        rf"\[\s*({number})\s*,\s*({number})\s*,\s*({number})\s*,\s*({number})\s*\]",
        raw,
    )
    return [float(value) for value in bracketed.groups()] if bracketed else None


def _normalize_bbox(
    values: list[float] | None,
    image_width: int,
    image_height: int,
    source_is_normalized: bool,
) -> tuple[float, float, float, float] | None:
    if not values or len(values) != 4 or image_width <= 0 or image_height <= 0:
        return None
    if source_is_normalized:
        normalized = values
    else:
        maximum = max(abs(value) for value in values)
        if maximum <= 1.0:
            normalized = values
        elif maximum <= 1000.0:
            normalized = [values[0] / 1000, values[1] / 1000, values[2] / 1000, values[3] / 1000]
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


def parse_photographer_output(raw: str, image_width: int, image_height: int) -> ParsedComposition:
    obj = _first_object(raw)
    decision: str | None = None
    confidence: float | None = None
    values: list[float] | None = None
    normalized_source = False

    if obj is not None:
        raw_decision = obj.get("decision")
        if raw_decision in {"keep", "refine", "reject"}:
            decision = str(raw_decision)
        if isinstance(obj.get("confidence"), (int, float)):
            confidence = float(obj["confidence"])
            if not 0 <= confidence <= 1:
                return ParsedComposition("low_confidence", None, None, None, "INVALID_MODEL_OUTPUT")
        if "bbox_norm" in obj:
            normalized_source = True
            values = _bbox_values(obj.get("bbox_norm"))
        else:
            candidate = obj
            instances = obj.get("instance_info")
            if isinstance(instances, list) and instances and isinstance(instances[0], dict):
                candidate = instances[0]
            for key in ("bbox", "composition_xy", "composition_bbox"):
                if key in candidate:
                    values = _bbox_values(candidate[key])
                    break

    if values is None:
        values = _legacy_bbox(raw)
    bbox = _normalize_bbox(values, image_width, image_height, normalized_source)

    if decision == "reject" and bbox is None:
        return ParsedComposition("success", "reject", None, confidence)
    if bbox is None:
        return ParsedComposition("low_confidence", None, None, confidence, "INVALID_MODEL_OUTPUT")
    if decision is None:
        area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
        decision = "keep" if area >= 0.90 else "refine"
    if decision == "keep" and bbox != (0.0, 0.0, 1.0, 1.0):
        decision = "refine"
    return ParsedComposition("success", decision, bbox, confidence)
