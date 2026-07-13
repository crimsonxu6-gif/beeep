from __future__ import annotations

import argparse
import base64
import sys
import time
from pathlib import Path

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
    return (
        GuidanceAdapter()
        .from_model_composition(model_result, frame_id)
        .model_dump(mode="json")
    )


def _api_output(record: dict, frame_id: int, api_url: str) -> dict:
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
        "requires_person": False,
        "image": {
            "base64": base64.b64encode(image_path.read_bytes()).decode("ascii"),
            "width": width,
            "height": height,
            "mime_type": mime_type,
        },
    }
    response = httpx.post(api_url, json=payload, timeout=60)
    body = response.json()
    body["http_status"] = response.status_code
    return body


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in (Path("C:/Windows/Fonts/msyh.ttc"), Path("C:/Windows/Fonts/arial.ttf")):
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def _render(record: dict, output: dict) -> str:
    image_path = EVAL_ROOT / record["image_path"]
    with Image.open(image_path) as source:
        image = source.convert("RGB")
    image.thumbnail((900, 900), Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(image)
    composition = output.get("composition")
    if composition and composition.get("bbox_norm"):
        x1, y1, x2, y2 = composition["bbox_norm"]
        draw.rounded_rectangle(
            (x1 * image.width, y1 * image.height, x2 * image.width, y2 * image.height),
            radius=12,
            outline=(72, 240, 204),
            width=max(3, image.width // 180),
        )
    labels = [action.get("message", "") for action in output.get("actions", [])]
    if labels:
        font = _font(max(18, image.width // 28))
        text = "  /  ".join(labels)
        box = draw.textbbox((0, 0), text, font=font)
        width = box[2] - box[0] + 32
        height = box[3] - box[1] + 24
        y = image.height - height - 16
        draw.rounded_rectangle(
            (16, y, min(image.width - 16, 16 + width), y + height),
            radius=12,
            fill=(10, 16, 18, 210),
        )
        draw.text((32, y + 8), text, font=font, fill=(255, 255, 255))
    destination = REPORT_ROOT / "artifacts" / "composition" / f"{record['eval_id']}.jpg"
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, format="JPEG", quality=86)
    return destination.relative_to(REPORT_ROOT).as_posix()


def evaluate(
    manifest: Path, *, mode: str, api_url: str | None = None
) -> tuple[list[dict], dict]:
    rows = read_jsonl(manifest)
    results = []
    latencies: list[int] = []
    bbox_cases = bbox_success = directional_cases = direction_correct = (
        wrong_direction
    ) = 0
    primary_correct = contradictory = secondary_cases = secondary_helpful = 0

    for frame_id, record in enumerate(rows, start=1):
        started = time.perf_counter()
        output = (
            _fixture_output(record, frame_id)
            if mode == "fixture"
            else _api_output(record, frame_id, api_url or "")
        )
        local_ms = max(0, round((time.perf_counter() - started) * 1000))
        latency = output.get("timing", {}).get("guidance_ms", local_ms)
        latencies.append(latency)
        actions = output.get("actions", [])
        expected = record["expected"]
        actual_primary = _action_key(actions[0] if actions else None)
        expected_primary = (expected["primary_action"], expected["primary_direction"])
        primary_match = actual_primary == expected_primary
        primary_correct += int(primary_match)

        if expected["primary_direction"] is not None:
            directional_cases += 1
            direction_correct += int(primary_match)
            wrong = actual_primary == OPPOSITES.get(expected_primary)
            wrong_direction += int(wrong)
        else:
            wrong = False

        expected_secondary = (
            expected["secondary_action"],
            expected["secondary_direction"],
        )
        actual_secondary = _action_key(actions[1] if len(actions) > 1 else None)
        secondary_match = None
        if expected["secondary_helpful"]:
            secondary_cases += 1
            secondary_match = actual_secondary == expected_secondary
            secondary_helpful += int(secondary_match)

        action_keys = {_action_key(action) for action in actions}
        conflict = any(
            key in action_keys and opposite in action_keys
            for key, opposite in OPPOSITES.items()
        )
        contradictory += int(conflict)

        expected_bbox = record["model_fixture"]["bbox_norm"]
        if expected_bbox is not None:
            bbox_cases += 1
            composition = output.get("composition")
            valid_bbox = bool(composition and composition.get("bbox_norm"))
            bbox_success += int(valid_bbox)
        else:
            valid_bbox = None

        results.append(
            {
                **record,
                "evaluation_mode": "fixture_adapter"
                if mode == "fixture"
                else "live_api",
                "output": output,
                "guidance_ms": latency,
                "checks": {
                    "bbox_parse_success": valid_bbox,
                    "direction_correct": primary_match
                    if expected["primary_direction"]
                    else None,
                    "primary_action_correct": primary_match,
                    "secondary_action_helpful": secondary_match,
                    "contradictory_actions": conflict,
                    "wrong_direction": wrong,
                },
                "overlay_path": _render(record, output),
            }
        )

    total = len(rows)
    summary = {
        "evaluation_mode": "fixture_adapter"
        if mode == "fixture"
        else "live_shuttermuse_api",
        "total": total,
        "bbox_parse_success": round(bbox_success / bbox_cases, 4) if bbox_cases else 0,
        "direction_correct": round(direction_correct / directional_cases, 4)
        if directional_cases
        else 0,
        "primary_action_correct": round(primary_correct / total, 4) if total else 0,
        "secondary_action_helpful": round(secondary_helpful / secondary_cases, 4)
        if secondary_cases
        else None,
        "contradictory_actions": contradictory,
        "wrong_direction_rate": round(wrong_direction / directional_cases, 4)
        if directional_cases
        else 0,
        "guidance_p50_ms": percentile(latencies, 0.50),
        "guidance_p95_ms": percentile(latencies, 0.95),
        "wrong_direction_ids": [
            row["eval_id"] for row in results if row["checks"]["wrong_direction"]
        ],
        "failed_primary_ids": [
            row["eval_id"]
            for row in results
            if not row["checks"]["primary_action_correct"]
        ],
    }
    return results, summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate bbox-to-action behavior and overlays."
    )
    parser.add_argument(
        "--manifest", type=Path, default=MANIFEST_ROOT / "composition.jsonl"
    )
    parser.add_argument("--mode", choices=("fixture", "api"), default="fixture")
    parser.add_argument("--api-url")
    args = parser.parse_args()
    if args.mode == "api" and not args.api_url:
        parser.error("--api-url is required in api mode")
    results, summary = evaluate(args.manifest, mode=args.mode, api_url=args.api_url)
    write_jsonl(REPORT_ROOT / "data" / "composition_results.jsonl", results)
    write_json(REPORT_ROOT / "composition_summary.json", summary)
    print(
        f"composition_total={summary['total']} wrong_direction_rate={summary['wrong_direction_rate']}"
    )


if __name__ == "__main__":
    main()
