from __future__ import annotations

import argparse
import base64
import sys
import time
from collections import Counter
from pathlib import Path

from PIL import Image

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

from schemas import AnalyzeRequest, ImagePayload  # noqa: E402
from vision.subject_preflight import SubjectPreflight  # noqa: E402
from vision.subject_presence_gate import SubjectPresenceGate  # noqa: E402


def _request(image_path: Path, frame_id: int) -> AnalyzeRequest:
    with Image.open(image_path) as image:
        width, height = image.size
        mime_type = Image.MIME.get(image.format, "image/jpeg")
    return AnalyzeRequest(
        frame_id=frame_id,
        timestamp=int(time.time() * 1000),
        stream_id=f"eval-{image_path.stem}",
        requires_person=True,
        image=ImagePayload(
            base64=base64.b64encode(image_path.read_bytes()).decode("ascii"),
            width=width,
            height=height,
            mime_type=mime_type,
        ),
    )


def evaluate(manifest: Path, *, repeats: int = 3) -> tuple[list[dict], dict]:
    detector = SubjectPreflight()
    gate = SubjectPresenceGate()
    rows = read_jsonl(manifest)
    results = []
    all_latencies: list[int] = []
    confusion = Counter(
        {
            "true_positive": 0,
            "true_negative": 0,
            "false_positive": 0,
            "false_negative": 0,
        }
    )

    for record in rows:
        image_path = EVAL_ROOT / record["image_path"]
        stream_id = f"eval-{record['image_id']}"
        attempts = []
        for frame_id in range(1, repeats + 1):
            request = _request(image_path, frame_id).model_copy(
                update={"stream_id": stream_id}
            )
            started = time.perf_counter()
            raw = detector.analyze(request)
            latency_ms = max(0, round((time.perf_counter() - started) * 1000))
            gated = gate.evaluate(stream_id, frame_id, raw, now_ms=frame_id * 500)
            all_latencies.append(latency_ms)
            attempts.append(
                {
                    "frame_id": frame_id,
                    "preflight_ms": latency_ms,
                    "raw": raw.model_dump(mode="json"),
                    "gated": gated.model_dump(mode="json"),
                }
            )
        gate.reset(stream_id)
        allowed = attempts[-1]["gated"]["allow_shuttermuse"]
        present = record["expected_person_present"]
        key = (
            "true_positive"
            if present and allowed
            else "false_negative"
            if present
            else "false_positive"
            if allowed
            else "true_negative"
        )
        confusion[key] += 1
        results.append(
            {
                **record,
                "prediction": key,
                "blocked_shuttermuse": not allowed,
                "attempts": attempts,
            }
        )

    person_present = confusion["true_positive"] + confusion["false_negative"]
    summary = {
        "evaluation_mode": "local_mediapipe_preflight_with_stateful_gate",
        "total": len(rows),
        "source_counts": dict(Counter(row["source_kind"] for row in rows)),
        "scenario_count": len({row["scenario"] for row in rows}),
        "confusion_matrix": dict(confusion),
        "person_present_block_rate": round(
            confusion["false_negative"] / person_present, 4
        )
        if person_present
        else 0,
        "preflight_p50_ms": percentile(all_latencies, 0.50),
        "preflight_p95_ms": percentile(all_latencies, 0.95),
        "false_negative_ids": [
            row["image_id"] for row in results if row["prediction"] == "false_negative"
        ],
        "false_positive_ids": [
            row["image_id"] for row in results if row["prediction"] == "false_positive"
        ],
    }
    return results, summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Beeep subject preflight over offline images."
    )
    parser.add_argument(
        "--manifest", type=Path, default=MANIFEST_ROOT / "preflight.jsonl"
    )
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    results, summary = evaluate(args.manifest, repeats=args.repeats)
    write_jsonl(REPORT_ROOT / "data" / "preflight_results.jsonl", results)
    write_json(REPORT_ROOT / "preflight_summary.json", summary)
    print(
        f"preflight_total={summary['total']} false_negatives={summary['confusion_matrix']['false_negative']}"
    )


if __name__ == "__main__":
    main()
