from __future__ import annotations

import argparse
import statistics
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from common import MANIFEST_ROOT, REPORT_ROOT, percentile, read_jsonl, write_json, write_jsonl
from run_composition_eval import (
    _api_output,
    _error_code,
    _read_readiness,
    _valid_bbox,
    prepare_run_root,
)

SCENARIOS = ("front_face", "side_profile", "back_view", "multiple_people", "empty_room")


def summarize_image(eval_id: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    raw_values = [str(row.get("raw_output") or "") for row in rows]
    raw_counts = Counter(raw_values)
    decisions = Counter(str(row.get("decision") or "none") for row in rows)
    formats = Counter(
        f"{row.get('coordinate_source') or 'none'}:{row.get('parse_failure_type') or 'success'}"
        for row in rows
    )
    bboxes = [row["bbox_norm"] for row in rows if _valid_bbox(row.get("bbox_norm"))]
    bbox_mean = [round(statistics.mean(values), 6) for values in zip(*bboxes, strict=True)] if bboxes else None
    bbox_std = [
        round(statistics.pstdev(values), 6) for values in zip(*bboxes, strict=True)
    ] if bboxes else None
    latencies = [row["inference_ms"] for row in rows if isinstance(row.get("inference_ms"), int)]
    parse_count = len(bboxes)
    exact_count = max(raw_counts.values()) if raw_counts else 0
    failed = parse_count < len(rows) * 0.9 or exact_count < len(rows) * 0.9
    return {
        "eval_id": eval_id,
        "attempts": len(rows),
        "parse_success_count": parse_count,
        "exact_same_raw_output_count": exact_count,
        "unique_raw_output_count": len(raw_counts),
        "decision_distribution": dict(decisions),
        "bbox_mean": bbox_mean,
        "bbox_std": bbox_std,
        "placeholder_output_count": sum(
            row.get("parse_failure_type") == "PLACEHOLDER_OUTPUT" for row in rows
        ),
        "format_distribution": dict(formats),
        "format_change_count": max(0, len(formats) - 1),
        "inference_p50_ms": percentile(latencies, 0.50),
        "inference_p95_ms": percentile(latencies, 0.95),
        "status": "MODEL_REPEATABILITY_FAILED" if failed else "passed",
    }


def evaluate_repeatability(
    records: list[dict[str, Any]],
    *,
    api_url: str,
    repeats: int,
    timeout_seconds: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    attempts: list[dict[str, Any]] = []
    frame_id = 1
    for record in records:
        for repeat_index in range(repeats):
            output = _api_output(record, frame_id, api_url, timeout_seconds)
            metadata = output.get("model_metadata") or {}
            composition = output.get("composition") or {}
            attempts.append(
                {
                    "eval_id": record["eval_id"],
                    "scenario": record["scenario"],
                    "repeat_index": repeat_index + 1,
                    "request_id": output.get("request_id"),
                    "frame_id": output.get("frame_id", frame_id),
                    "status": output.get("status"),
                    "error_code": _error_code(output),
                    "raw_output": metadata.get("raw_output"),
                    "generated_token_count": metadata.get("generated_token_count"),
                    "parse_failure_type": metadata.get("parse_failure_type"),
                    "parser_comparison": metadata.get("parser_comparison"),
                    "coordinate_source": metadata.get("coordinate_source"),
                    "decision": metadata.get("decision") or composition.get("decision"),
                    "bbox_norm": metadata.get("bbox_norm") or composition.get("bbox_norm"),
                    "inference_ms": metadata.get("inference_ms"),
                }
            )
            frame_id += 1

    per_image = [
        summarize_image(
            record["eval_id"],
            [row for row in attempts if row["eval_id"] == record["eval_id"]],
        )
        for record in records
    ]
    summary = {
        "images": len(records),
        "repeats_per_image": repeats,
        "total_requests": len(attempts),
        "failed_image_count": sum(row["status"] == "MODEL_REPEATABILITY_FAILED" for row in per_image),
        "status": (
            "MODEL_REPEATABILITY_FAILED"
            if any(row["status"] == "MODEL_REPEATABILITY_FAILED" for row in per_image)
            else "passed"
        ),
        "per_image": per_image,
    }
    return attempts, summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate deterministic ShutterMuse repeatability.")
    parser.add_argument("--manifest", type=Path, default=MANIFEST_ROOT / "composition.jsonl")
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--repeats", type=int, default=10)
    parser.add_argument("--request-timeout", type=float, default=180)
    args = parser.parse_args()
    selected = [row for row in read_jsonl(args.manifest) if row["scenario"] in SCENARIOS]
    by_scenario = {row["scenario"]: row for row in selected}
    missing = set(SCENARIOS) - set(by_scenario)
    if missing:
        parser.error(f"missing repeatability scenarios: {sorted(missing)}")
    records = [by_scenario[scenario] for scenario in SCENARIOS]
    run_root = prepare_run_root(REPORT_ROOT, args.run_id)
    readiness = _read_readiness(args.api_url, args.request_timeout)
    attempts, summary = evaluate_repeatability(
        records,
        api_url=args.api_url,
        repeats=args.repeats,
        timeout_seconds=args.request_timeout,
    )
    summary["run_id"] = args.run_id
    write_jsonl(run_root / "repeatability_results.jsonl", attempts)
    write_json(run_root / "repeatability_summary.json", summary)
    write_json(
        run_root / "run_config.json",
        {
            "run_id": args.run_id,
            "created_at": datetime.now(UTC).isoformat(),
            "evaluation": "repeatability",
            **readiness,
        },
    )
    print(
        f"repeatability={summary['status']} images={summary['images']} "
        f"requests={summary['total_requests']}"
    )


if __name__ == "__main__":
    main()
