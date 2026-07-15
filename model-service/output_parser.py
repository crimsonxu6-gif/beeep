from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass
from typing import Any, Literal

ParseFailureType = Literal[
    "MODEL_NO_COORDINATES",
    "PARSER_UNSUPPORTED_FORMAT",
    "INVALID_BBOX_GEOMETRY",
    "OUTPUT_TRUNCATED",
    "INVALID_COORDINATE_RANGE",
    "PLACEHOLDER_OUTPUT",
    "EMPTY_MODEL_OUTPUT",
    "UNKNOWN_PARSE_FAILURE",
]

CoordinateSource = Literal[
    "bbox_norm",
    "bbox_1000",
    "bbox_pixels",
    "official_1000_pairs",
    "official_pixels_pairs",
    "official_1000_list",
    "official_pixels_list",
    "official_1000_json_bbox",
    "official_pixels_json_bbox",
    "official_1000_composition_bbox",
    "official_pixels_composition_bbox",
    "official_1000_composition_xy",
    "official_pixels_composition_xy",
    "official_1000_partial_bbox",
    "official_pixels_partial_bbox",
    "official_1000_partial_composition_bbox",
    "official_pixels_partial_composition_bbox",
    "official_1000_partial_composition_xy",
    "official_pixels_partial_composition_xy",
]

NUMBER = r"[-+]?\d*\.?\d+"
PAIR_PATTERN = re.compile(
    rf"\(\s*({NUMBER})\s*,\s*({NUMBER})\s*\)\s*,\s*"
    rf"\(\s*({NUMBER})\s*,\s*({NUMBER})\s*\)"
)
LIST_PATTERN = re.compile(
    rf"^\s*\[\s*({NUMBER})\s*,\s*({NUMBER})\s*,\s*"
    rf"({NUMBER})\s*,\s*({NUMBER})\s*\]\s*$"
)
PLACEHOLDER_PATTERN = re.compile(
    r"<\s*bbox\s*>|\[\s*x1\s*,\s*y1\s*,\s*x2\s*,\s*y2\s*\]|"
    r"\(\s*x1\s*,\s*y1\s*\)\s*,\s*\(\s*x2\s*,\s*y2\s*\)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ParsedComposition:
    status: str
    decision: str | None
    bbox_norm: tuple[float, float, float, float] | None
    confidence: float | None
    error_code: str | None = None
    coordinate_source: CoordinateSource | None = None
    parse_failure_type: ParseFailureType | None = None
    partial_structure_used: bool = False
    json_complete: bool = False
    bbox_field_complete: bool = False


@dataclass(frozen=True)
class PartialBBoxResult:
    values: list[float]
    coordinate_source: CoordinateSource
    field_name: Literal["bbox", "composition_bbox", "composition_xy"]
    json_complete: bool
    bbox_field_complete: bool = True


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
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
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
        pair = PAIR_PATTERN.search(value)
        if pair:
            return [float(item) for item in pair.groups()]
        listed = LIST_PATTERN.match(value)
        if listed:
            return [float(item) for item in listed.groups()]
    return None


def _official_source(
    coordinate_format: Literal["norm1000", "pixels"],
    shape: str,
) -> CoordinateSource:
    prefix = "official_1000" if coordinate_format == "norm1000" else "official_pixels"
    return f"{prefix}_{shape}"  # type: ignore[return-value]


def _partial_official_source(
    coordinate_format: Literal["norm1000", "pixels"],
    field_name: str,
) -> CoordinateSource:
    prefix = "official_1000" if coordinate_format == "norm1000" else "official_pixels"
    return f"{prefix}_partial_{field_name}"  # type: ignore[return-value]


def _json_is_complete(raw: str) -> bool:
    text = raw.strip()
    start = text.find("{")
    if start < 0:
        return False
    try:
        _, end = json.JSONDecoder().raw_decode(text[start:])
    except json.JSONDecodeError:
        return False
    return not text[start + end :].strip()


def extract_partial_explicit_bbox(
    raw_output: str,
    official_coordinate_format: Literal["norm1000", "pixels"],
    image_width: int | None = None,
    image_height: int | None = None,
) -> PartialBBoxResult | None:
    """Recover only a complete, explicitly named bbox field from partial JSON.

    The extraction is deliberately narrow: it never scans arbitrary prose for
    four numbers and never repairs geometry or coordinate ranges.
    """
    for field_name in ("bbox", "composition_bbox", "composition_xy"):
        field = re.escape(field_name)
        patterns = (
            re.compile(
                rf'["\']{field}["\']\s*:\s*\[\s*({NUMBER})\s*,\s*({NUMBER})\s*,\s*'
                rf'({NUMBER})\s*,\s*({NUMBER})\s*\]',
                re.IGNORECASE,
            ),
            re.compile(
                rf'["\']{field}["\']\s*:\s*["\']\s*'
                rf'\(\s*({NUMBER})\s*,\s*({NUMBER})\s*\)\s*,\s*'
                rf'\(\s*({NUMBER})\s*,\s*({NUMBER})\s*\)\s*["\']',
                re.IGNORECASE,
            ),
        )
        for pattern in patterns:
            match = pattern.search(raw_output)
            if match is None:
                continue
            values = [float(value) for value in match.groups()]
            source = _partial_official_source(official_coordinate_format, field_name)
            # Validate using the declared coordinate system without mutating it.
            x1, y1, x2, y2 = values
            limit = 1000.0 if official_coordinate_format == "norm1000" else None
            if x2 <= x1 or y2 <= y1:
                return None
            if limit is not None and not all(0 <= value <= limit for value in values):
                return None
            if official_coordinate_format == "pixels":
                if image_width is None or image_height is None:
                    return None
                if not (
                    0 <= x1 <= image_width
                    and 0 <= x2 <= image_width
                    and 0 <= y1 <= image_height
                    and 0 <= y2 <= image_height
                ):
                    return None
            return PartialBBoxResult(
                values=values,
                coordinate_source=source,
                field_name=field_name,  # type: ignore[arg-type]
                json_complete=_json_is_complete(raw_output),
            )
    return None


def _explicit_bbox_from_object(
    obj: dict[str, Any],
    *,
    prompt_mode: Literal["official", "beeep_json"],
    official_coordinate_format: Literal["norm1000", "pixels"],
) -> tuple[list[float] | None, CoordinateSource | None]:
    for field, source in (
        ("bbox_norm", "bbox_norm"),
        ("bbox_1000", "bbox_1000"),
        ("bbox_pixels", "bbox_pixels"),
    ):
        if field in obj:
            return _bbox_values(obj[field]), source  # type: ignore[return-value]

    if prompt_mode != "official":
        return None, None

    container = obj
    instances = obj.get("instance_info")
    if isinstance(instances, list) and instances and isinstance(instances[0], dict):
        container = instances[0]

    for field in ("bbox", "composition_bbox", "composition_xy"):
        if field not in container:
            continue
        value = container[field]
        values = _bbox_values(value)
        if values is None:
            return None, None
        shape = "json_bbox" if field == "bbox" else field
        return values, _official_source(official_coordinate_format, shape)
    return None, None


def _normalize_bbox(
    values: list[float],
    image_width: int,
    image_height: int,
    source: CoordinateSource,
) -> tuple[tuple[float, float, float, float] | None, ParseFailureType | None]:
    if len(values) != 4 or image_width <= 0 or image_height <= 0:
        return None, "UNKNOWN_PARSE_FAILURE"
    x1, y1, x2, y2 = values
    if x2 <= x1 or y2 <= y1:
        return None, "INVALID_BBOX_GEOMETRY"

    if source == "bbox_norm":
        limits = (1.0, 1.0)
        normalized = values
    elif source == "bbox_pixels" or source.startswith("official_pixels"):
        limits = (float(image_width), float(image_height))
        normalized = [x1 / image_width, y1 / image_height, x2 / image_width, y2 / image_height]
    else:
        limits = (1000.0, 1000.0)
        normalized = [value / 1000 for value in values]

    max_x, max_y = limits
    if not (0 <= x1 <= max_x and 0 <= x2 <= max_x and 0 <= y1 <= max_y and 0 <= y2 <= max_y):
        return None, "INVALID_COORDINATE_RANGE"
    return (normalized[0], normalized[1], normalized[2], normalized[3]), None


def _is_full_frame(bbox: tuple[float, float, float, float]) -> bool:
    x1, y1, x2, y2 = bbox
    return x1 <= 0.02 and y1 <= 0.02 and x2 >= 0.98 and y2 >= 0.98


def _looks_truncated(raw: str, reached_max_new_tokens: bool) -> bool:
    if reached_max_new_tokens:
        return True
    text = raw.strip()
    if text.startswith("{") and _first_object(text) is None:
        return True
    if text.startswith("[") and text.count("[") > text.count("]"):
        return True
    return text.endswith(("(", "[", "{", ",", ":"))


def _failure_type(raw: str, reached_max_new_tokens: bool) -> ParseFailureType:
    text = raw.strip()
    if not text:
        return "EMPTY_MODEL_OUTPUT"
    if PLACEHOLDER_PATTERN.search(text):
        return "PLACEHOLDER_OUTPUT"
    if _looks_truncated(text, reached_max_new_tokens):
        return "OUTPUT_TRUNCATED"
    if len(re.findall(NUMBER, text)) >= 4:
        return "PARSER_UNSUPPORTED_FORMAT"
    return "MODEL_NO_COORDINATES"


def parse_photographer_output(
    raw: str,
    image_width: int,
    image_height: int,
    *,
    prompt_mode: Literal[
        "official", "official_bbox_first", "official_prefill", "beeep_json"
    ] = "beeep_json",
    official_coordinate_format: Literal["norm1000", "pixels"] = "norm1000",
    reached_max_new_tokens: bool = False,
) -> ParsedComposition:
    obj = _first_object(raw)
    decision: str | None = None
    confidence: float | None = None
    values: list[float] | None = None
    source: CoordinateSource | None = None
    partial_structure_used = False
    bbox_field_complete = False
    json_complete = _json_is_complete(raw)

    if obj is not None:
        raw_decision = obj.get("decision")
        if raw_decision in {"keep", "refine", "reject"}:
            decision = str(raw_decision)
        if isinstance(obj.get("confidence"), (int, float)):
            confidence = float(obj["confidence"])
            if not 0 <= confidence <= 1:
                return ParsedComposition(
                    "low_confidence",
                    None,
                    None,
                    None,
                    "INVALID_MODEL_OUTPUT",
                    parse_failure_type="INVALID_COORDINATE_RANGE",
                )
        values, source = _explicit_bbox_from_object(
            obj,
            prompt_mode="official" if prompt_mode.startswith("official") else "beeep_json",
            official_coordinate_format=official_coordinate_format,
        )

    if values is None and prompt_mode.startswith("official") and not json_complete:
        partial = extract_partial_explicit_bbox(
            raw,
            official_coordinate_format,
            image_width,
            image_height,
        )
        if partial is not None:
            values = partial.values
            source = partial.coordinate_source
            partial_structure_used = True
            bbox_field_complete = partial.bbox_field_complete
            json_complete = partial.json_complete

    if values is None and prompt_mode.startswith("official"):
        pair = PAIR_PATTERN.search(raw)
        if pair:
            values = [float(value) for value in pair.groups()]
            source = _official_source(official_coordinate_format, "pairs")
        else:
            listed = LIST_PATTERN.match(raw.strip())
            if listed:
                values = [float(value) for value in listed.groups()]
                source = _official_source(official_coordinate_format, "list")

    if decision == "reject" and values is None:
        return ParsedComposition(
            "success", "reject", None, confidence, json_complete=json_complete
        )
    if values is None or source is None:
        failure = _failure_type(raw, reached_max_new_tokens)
        return ParsedComposition(
            "low_confidence",
            None,
            None,
            confidence,
            "INVALID_MODEL_OUTPUT",
            parse_failure_type=failure,
            json_complete=json_complete,
        )

    bbox, normalization_error = _normalize_bbox(values, image_width, image_height, source)
    if bbox is None:
        return ParsedComposition(
            "low_confidence",
            None,
            None,
            confidence,
            "INVALID_MODEL_OUTPUT",
            source,
            normalization_error or "UNKNOWN_PARSE_FAILURE",
            partial_structure_used,
            json_complete,
            bbox_field_complete,
        )

    if decision is None:
        decision = "keep" if _is_full_frame(bbox) else "refine"
    elif decision == "keep" and not _is_full_frame(bbox):
        decision = "refine"
    return ParsedComposition(
        "success",
        decision,
        bbox,
        confidence,
        coordinate_source=source,
        partial_structure_used=partial_structure_used,
        json_complete=json_complete,
        bbox_field_complete=bbox_field_complete,
    )
