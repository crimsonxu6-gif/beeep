from __future__ import annotations

import argparse
import base64
import statistics
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

import httpx
from PIL import Image, ImageDraw, ImageFont

from common import (
    EVAL_ROOT,
    MANIFEST_ROOT,
    PROJECT_ROOT,
    REPORT_ROOT,
    percentile,
    read_jsonl,
    write_json,
    write_jsonl,
)

sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from services.guidance_adapter import GuidanceAdapter  # noqa: E402
from services.shuttermuse_client import ModelCompositionResult  # noqa: E402

OPPOSITES = {
    ("move_camera", "left"): ("move_camera", "right"),
    ("move_camera", "right"): ("move_camera", "left"),
    ("adjust_angle", "raise"): ("adjust_angle", "lower"),
    ("adjust_angle", "lower"): ("adjust_angle", "raise"),
    ("adjust_distance", "closer"): ("adjust_distance", "farther"),
    ("adjust_distance", "farther"): ("adjust_distance", "closer"),
}
REVIEW_BOOLEAN_FIELDS = (
    "composition_improved",
    "subject_preserved",
    "head_cut",
    "body_cut",
    "target_ratio_correct",
    "primary_direction_correct",
    "primary_action_helpful",
    "secondary_action_helpful",
    "instructions_executable_together",
)


def default_review(eval_id: str) -> dict[str, Any]:
    return {
        "eval_id": eval_id,
        "bbox_quality": None,
        **{field: None for field in REVIEW_BOOLEAN_FIELDS},
        "review_notes": "",
    }


def load_reviews(path: Path) -> dict[str, dict[str, Any]]:
    return {
        row["eval_id"]: _normalize_review(row)
        for row in read_jsonl(path)
        if row.get("eval_id")
    }


def _normalize_review(value: dict[str, Any]) -> dict[str, Any]:
    eval_id = str(value.get("eval_id") or "")
    quality = value.get("bbox_quality")
    if quality is not None and (not isinstance(quality, int) or not 1 <= quality <= 5):
        raise ValueError(f"bbox_quality must be an integer from 1 to 5 for {eval_id}")
    review = default_review(eval_id)
    review["bbox_quality"] = quality
    for field in REVIEW_BOOLEAN_FIELDS:
        field_value = value.get(field)
        if field_value is not None and not isinstance(field_value, bool):
            raise ValueError(f"{field} must be true, false, or null for {eval_id}")
        review[field] = field_value
    review["review_notes"] = str(value.get("review_notes") or "")
    return review


def ensure_reviews(records: list[dict], path: Path) -> dict[str, dict[str, Any]]:
    existing = load_reviews(path)
    reviews = {
        record["eval_id"]: {**default_review(record["eval_id"]), **existing.get(record["eval_id"], {})}
        for record in records
    }
    write_jsonl(path, reviews.values())
    return reviews


def _action_key(action: dict | None) -> tuple[str | None, str | None]:
    if not action:
        return None, None
    return action.get("type"), action.get("direction")


def _fixture_output(record: dict, frame_id: int) -> dict:
    fixture = record["model_fixture"]
    model_result = ModelCompositionResult(
        request_id=f"fixture-{record['eval_id']}",
        frame_id=frame_id,
        status=fixture["status"],
        decision=fixture["decision"],
        bbox_norm=fixture["bbox_norm"],
        confidence=fixture["confidence"],
        inference_ms=0,
        prompt_mode="beeep_json",
        coordinate_source="bbox_norm" if fixture["bbox_norm"] else None,
    )
    output = (
        GuidanceAdapter()
        .from_model_composition(model_result, frame_id)
        .model_dump(mode="json", exclude_none=True)
    )
    output["request_id"] = model_result.request_id
    output["frame_id"] = frame_id
    output["status"] = "success"
    output["model_metadata"] = {
        "prompt_mode": model_result.prompt_mode,
        "coordinate_source": model_result.coordinate_source,
        "decision": model_result.decision,
        "bbox_norm": model_result.bbox_norm,
        "confidence": model_result.confidence,
        "inference_ms": model_result.inference_ms,
    }
    output["timing"] = {"preflight_ms": 0, "guidance_ms": 0, "total_ms": 0}
    output["http_status"] = 200
    return output


def _api_output(
    record: dict,
    frame_id: int,
    api_url: str,
    request_timeout_seconds: float = 60,
) -> dict:
    image_path = EVAL_ROOT / record["image_path"]
    with Image.open(image_path) as image:
        width, height = image.size
        mime_type = Image.MIME.get(image.format, "image/jpeg")
    payload = {
        "frame_id": frame_id,
        "timestamp": int(time.time() * 1000),
        "stream_id": f"composition-eval-{record['eval_id']}",
        "mode": "composition",
        "composition_mode": record["composition_mode"],
        "target_ratio": record["target_ratio"],
        "language": "zh-CN",
        "requires_person": True,
        "image": {
            "base64": base64.b64encode(image_path.read_bytes()).decode("ascii"),
            "width": width,
            "height": height,
            "mime_type": mime_type,
        },
    }
    try:
        response = httpx.post(api_url, json=payload, timeout=request_timeout_seconds)
    except httpx.RequestError as exc:
        return {
            "status": "error",
            "frame_id": frame_id,
            "http_status": None,
            "error": {"code": "NETWORK_ERROR", "message": str(exc)},
        }
    try:
        body = response.json()
    except ValueError:
        body = {
            "status": "error",
            "frame_id": frame_id,
            "error": {"code": "INVALID_API_RESPONSE", "message": response.text[:200]},
        }
    body["http_status"] = response.status_code
    if response.status_code >= 400:
        body["status"] = "error"
    return body


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in (Path("C:/Windows/Fonts/msyh.ttc"), Path("C:/Windows/Fonts/arial.ttf")):
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def _valid_bbox(value: Any) -> bool:
    return bool(
        isinstance(value, (list, tuple))
        and len(value) == 4
        and all(isinstance(item, (int, float)) for item in value)
        and 0 <= value[0] < value[2] <= 1
        and 0 <= value[1] < value[3] <= 1
    )


def bbox_pixels(
    bbox: list[float] | tuple[float, float, float, float], width: int, height: int
) -> tuple[float, float, float, float]:
    return bbox[0] * width, bbox[1] * height, bbox[2] * width, bbox[3] * height


def _render(
    record: dict,
    output: dict,
    *,
    mode: str,
    review: dict[str, Any] | None,
) -> str:
    image_path = EVAL_ROOT / record["image_path"]
    with Image.open(image_path) as source:
        original = source.convert("RGB")
    original.thumbnail((680, 680), Image.Resampling.LANCZOS)
    annotated = original.copy()
    draw = ImageDraw.Draw(annotated)
    composition = output.get("composition") or {}
    bbox = composition.get("bbox_norm")
    if _valid_bbox(bbox):
        draw.rounded_rectangle(
            bbox_pixels(bbox, annotated.width, annotated.height),
            radius=12,
            outline=(72, 240, 204),
            width=max(3, annotated.width // 150),
        )

    gap = 18
    footer_height = 170
    canvas = Image.new(
        "RGB",
        (original.width * 2 + gap, original.height + footer_height),
        (19, 24, 25),
    )
    canvas.paste(original, (0, 0))
    canvas.paste(annotated, (original.width + gap, 0))
    canvas_draw = ImageDraw.Draw(canvas)
    label_font = _font(max(16, original.width // 30))
    detail_font = _font(max(14, original.width // 38))
    canvas_draw.text((14, 12), "原始图片", font=label_font, fill=(255, 255, 255))
    canvas_draw.text(
        (original.width + gap + 14, 12),
        "ShutterMuse 推荐框",
        font=label_font,
        fill=(72, 240, 204),
    )
    metadata = output.get("model_metadata") or {}
    actions = output.get("actions") or []
    action_text = " / ".join(action.get("message", "") for action in actions) or "无指令"
    timing = output.get("timing") or {}
    review_score = review.get("bbox_quality") if review else None
    lines = [
        f"decision={metadata.get('decision') or composition.get('decision') or '-'}  coordinate={metadata.get('coordinate_source') or '-'}  confidence={metadata.get('confidence')}",
        f"主/次建议：{action_text}",
        f"preflight/guidance/total={timing.get('preflight_ms', '-')}/{timing.get('guidance_ms', '-')}/{timing.get('total_ms', '-')} ms  review={review_score or '-'}",
        f"error={_error_code(output) or '-'}",
    ]
    y = original.height + 16
    for line in lines:
        canvas_draw.text((16, y), line, font=detail_font, fill=(225, 231, 229))
        y += 34

    folder = "composition_fixture" if mode == "fixture" else "shuttermuse_api"
    destination = REPORT_ROOT / "artifacts" / folder / f"{record['eval_id']}.jpg"
    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(destination, format="JPEG", quality=88)
    return destination.relative_to(REPORT_ROOT).as_posix()


def _error_code(output: dict) -> str | None:
    error = output.get("error")
    if isinstance(error, dict):
        return error.get("code")
    detail = output.get("detail")
    if isinstance(detail, dict):
        nested = detail.get("error") if isinstance(detail.get("error"), dict) else detail
        return nested.get("code")
    return None


def _review_metrics(results: list[dict]) -> dict[str, Any]:
    reviewed = [row for row in results if row["human_review"].get("bbox_quality") is not None]
    scores = [float(row["human_review"]["bbox_quality"]) for row in reviewed]
    metrics: dict[str, Any] = {
        "reviewed_count": len(reviewed),
        "unreviewed_count": len(results) - len(reviewed),
        "bbox_quality_mean": round(statistics.mean(scores), 3) if scores else None,
        "bbox_quality_median": round(statistics.median(scores), 3) if scores else None,
        "bbox_quality_below_3_count": sum(score < 3 for score in scores),
        "bbox_quality_below_3_rate": round(sum(score < 3 for score in scores) / len(scores), 4)
        if scores
        else None,
    }
    for field in REVIEW_BOOLEAN_FIELDS:
        values = [row["human_review"].get(field) for row in reviewed]
        decided = [value for value in values if isinstance(value, bool)]
        metrics[f"{field}_count"] = len(decided)
        metrics[f"{field}_true_count"] = sum(decided)
        metrics[f"{field}_rate"] = round(sum(decided) / len(decided), 4) if decided else None
    return metrics


def evaluate(
    manifest: Path,
    *,
    mode: str,
    api_url: str | None = None,
    reviews_path: Path | None = None,
    render_artifacts: bool = True,
    request_timeout_seconds: float = 60,
) -> tuple[list[dict], dict]:
    rows = read_jsonl(manifest)
    reviews = (
        ensure_reviews(rows, reviews_path or MANIFEST_ROOT / "composition_reviews.jsonl")
        if mode == "api"
        else {record["eval_id"]: default_review(record["eval_id"]) for record in rows}
    )
    results: list[dict] = []
    guidance_latencies: list[int | float] = []
    total_latencies: list[int | float] = []
    bbox_attempts = bbox_success = directional_cases = direction_correct = wrong_direction = 0
    primary_correct = contradictory = secondary_cases = secondary_helpful = 0
    api_success_count = 0
    error_codes: Counter[str] = Counter()
    decisions: Counter[str] = Counter()
    coordinate_sources: Counter[str] = Counter()

    for frame_id, record in enumerate(rows, start=1):
        started = time.perf_counter()
        output = (
            _fixture_output(record, frame_id)
            if mode == "fixture"
            else _api_output(record, frame_id, api_url or "", request_timeout_seconds)
        )
        request_ms = max(0, round((time.perf_counter() - started) * 1000))
        successful = output.get("status") == "success" and int(output.get("http_status") or 200) < 400
        api_success_count += int(successful)
        error_code = _error_code(output)
        if error_code:
            error_codes[error_code] += 1

        timing = output.get("timing") or {}
        guidance_ms = timing.get("guidance_ms")
        total_ms = timing.get("total_ms")
        if isinstance(guidance_ms, (int, float)):
            guidance_latencies.append(guidance_ms)
        if isinstance(total_ms, (int, float)):
            total_latencies.append(total_ms)

        metadata = output.get("model_metadata") or {}
        composition = output.get("composition") or {}
        decision = metadata.get("decision") or composition.get("decision")
        coordinate_source = metadata.get("coordinate_source")
        if decision:
            decisions[str(decision)] += 1
        if coordinate_source:
            coordinate_sources[str(coordinate_source)] += 1

        actions = output.get("actions") or []
        expected = record["expected"]
        actual_primary = _action_key(actions[0] if actions else None)
        expected_primary = (expected["primary_action"], expected["primary_direction"])
        primary_match = successful and actual_primary == expected_primary if mode == "fixture" else None
        primary_correct += int(primary_match or False)
        if mode == "fixture" and expected["primary_direction"] is not None:
            directional_cases += 1
            direction_correct += int(primary_match or False)
            wrong = successful and actual_primary == OPPOSITES.get(expected_primary)
            wrong_direction += int(wrong)
        else:
            wrong = None

        expected_secondary = (expected["secondary_action"], expected["secondary_direction"])
        actual_secondary = _action_key(actions[1] if len(actions) > 1 else None)
        secondary_match = None
        if mode == "fixture" and expected["secondary_helpful"]:
            secondary_cases += 1
            secondary_match = successful and actual_secondary == expected_secondary
            secondary_helpful += int(secondary_match)

        action_keys = {_action_key(action) for action in actions}
        conflict = any(
            key in action_keys and opposite in action_keys for key, opposite in OPPOSITES.items()
        )
        contradictory += int(conflict)

        bbox = metadata.get("bbox_norm") or composition.get("bbox_norm")
        bbox_status = "not_applicable"
        if decision != "reject" and (successful or error_code == "INVALID_MODEL_OUTPUT"):
            bbox_attempts += 1
            bbox_status = "success" if _valid_bbox(bbox) else "invalid"
            bbox_success += int(bbox_status == "success")

        preflight = output.get("subject_preflight") or {}
        primary = actions[0] if actions else {}
        secondary = actions[1] if len(actions) > 1 else {}
        review = reviews[record["eval_id"]]
        result = {
            **record,
            "evaluation_mode": "fixture_adapter" if mode == "fixture" else "live_api",
            "api_success": successful,
            "request_id": output.get("request_id"),
            "frame_id": output.get("frame_id", frame_id),
            "prompt_mode": metadata.get("prompt_mode"),
            "coordinate_source": coordinate_source,
            "raw_model_decision": decision,
            "raw_bbox_norm": metadata.get("bbox_norm") or composition.get("bbox_norm"),
            "model_confidence": (
                metadata.get("confidence")
                if mode == "api"
                else metadata.get("confidence", output.get("confidence"))
            ),
            "bbox_parse_status": bbox_status,
            "preflight_state": preflight.get("state"),
            "preflight_detection_source": preflight.get("detection_source"),
            "preflight_ms": timing.get("preflight_ms"),
            "guidance_ms": guidance_ms,
            "total_ms": total_ms,
            "request_ms": request_ms,
            "primary_action": primary.get("type"),
            "primary_direction": primary.get("direction"),
            "secondary_action": secondary.get("type"),
            "secondary_direction": secondary.get("direction"),
            "error_code": error_code,
            "output": output,
            "human_review": review,
            "checks": {
                "bbox_parse_success": bbox_status == "success" if bbox_status != "not_applicable" else None,
                "fixture_expected_direction_match": (
                    primary_match if mode == "fixture" and expected["primary_direction"] else None
                ),
                "fixture_expected_primary_match": primary_match,
                "fixture_expected_secondary_match": secondary_match,
                "contradictory_actions": conflict,
                "wrong_direction": wrong,
            },
        }
        result["overlay_path"] = (
            _render(record, output, mode=mode, review=review) if render_artifacts else None
        )
        results.append(result)

    total = len(rows)
    invalid_count = error_codes["INVALID_MODEL_OUTPUT"] + sum(
        row["bbox_parse_status"] == "invalid" and row["error_code"] != "INVALID_MODEL_OUTPUT"
        for row in results
    )
    review_metrics = _review_metrics(results)
    summary = {
        "evaluation_mode": "fixture_adapter" if mode == "fixture" else "live_shuttermuse_api",
        "total": total,
        "api_success_count": api_success_count,
        "api_failure_count": total - api_success_count,
        "api_success_rate": round(api_success_count / total, 4) if total else 0,
        "bbox_parse_attempts": bbox_attempts,
        "bbox_parse_success_count": bbox_success,
        "bbox_parse_success": round(bbox_success / bbox_attempts, 4) if bbox_attempts else 0,
        "invalid_output_count": invalid_count,
        "invalid_output_rate": round(invalid_count / total, 4) if total else 0,
        "decision_distribution": dict(decisions),
        "coordinate_source_distribution": dict(coordinate_sources),
        "error_distribution": dict(error_codes),
        "contradictory_actions": contradictory,
        "guidance_p50_ms": percentile(guidance_latencies, 0.50),
        "guidance_p95_ms": percentile(guidance_latencies, 0.95),
        "total_p50_ms": percentile(total_latencies, 0.50),
        "total_p95_ms": percentile(total_latencies, 0.95),
        "review": review_metrics,
    }
    if mode == "fixture":
        summary.update(
            {
                "direction_correct": round(direction_correct / directional_cases, 4)
                if directional_cases
                else 0,
                "primary_action_correct": round(primary_correct / total, 4) if total else 0,
                "secondary_action_helpful": round(secondary_helpful / secondary_cases, 4)
                if secondary_cases
                else None,
                "wrong_direction_count": wrong_direction,
                "wrong_direction_rate": round(wrong_direction / directional_cases, 4)
                if directional_cases
                else 0,
                "wrong_direction_ids": [
                    row["eval_id"] for row in results if row["checks"]["wrong_direction"]
                ],
                "failed_primary_ids": [
                    row["eval_id"]
                    for row in results
                    if not row["checks"]["fixture_expected_primary_match"]
                ],
            }
        )
    else:
        direction_count = review_metrics["primary_direction_correct_count"]
        direction_true = review_metrics["primary_direction_correct_true_count"]
        wrong_direction = direction_count - direction_true
        summary.update(
            {
                "human_primary_direction_correct_rate": review_metrics[
                    "primary_direction_correct_rate"
                ],
                "human_primary_action_helpful_rate": review_metrics[
                    "primary_action_helpful_rate"
                ],
                "human_secondary_action_helpful_rate": review_metrics[
                    "secondary_action_helpful_rate"
                ],
                "wrong_direction_count": wrong_direction,
                "wrong_direction_rate": (
                    round(wrong_direction / direction_count, 4) if direction_count else None
                ),
                "wrong_direction_ids": [
                    row["eval_id"]
                    for row in results
                    if row["human_review"].get("primary_direction_correct") is False
                ],
                "failed_primary_ids": [
                    row["eval_id"]
                    for row in results
                    if row["human_review"].get("primary_action_helpful") is False
                ],
            }
        )
    return results, summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate fixture or live ShutterMuse composition output.")
    parser.add_argument("--manifest", type=Path, default=MANIFEST_ROOT / "composition.jsonl")
    parser.add_argument("--mode", choices=("fixture", "api"), default="fixture")
    parser.add_argument("--api-url")
    parser.add_argument("--request-timeout", type=float, default=60)
    parser.add_argument(
        "--reviews",
        type=Path,
        default=MANIFEST_ROOT / "composition_reviews.jsonl",
    )
    args = parser.parse_args()
    if args.mode == "api" and not args.api_url:
        parser.error("--api-url is required in api mode")
    results, summary = evaluate(
        args.manifest,
        mode=args.mode,
        api_url=args.api_url,
        reviews_path=args.reviews,
        request_timeout_seconds=args.request_timeout,
    )
    if args.mode == "fixture":
        write_jsonl(REPORT_ROOT / "data" / "composition_fixture_results.jsonl", results)
        write_json(REPORT_ROOT / "composition_fixture_summary.json", summary)
        # Keep legacy paths stable for existing tooling.
        write_jsonl(REPORT_ROOT / "data" / "composition_results.jsonl", results)
        write_json(REPORT_ROOT / "composition_summary.json", summary)
    else:
        write_jsonl(REPORT_ROOT / "data" / "composition_api_results.jsonl", results)
        write_json(REPORT_ROOT / "composition_api_summary.json", summary)
    print(
        f"composition_mode={args.mode} total={summary['total']} "
        f"success={summary['api_success_count']} failed={summary['api_failure_count']} "
        f"bbox_parse={summary['bbox_parse_success']}"
    )


if __name__ == "__main__":
    main()
