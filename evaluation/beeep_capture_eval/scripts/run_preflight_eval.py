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

OLD_FALSE_NEGATIVE_IDS = {
    "public_back_view",
    "public_looking_down",
    "public_hat",
    "public_group",
    "ai_back_view",
    "ai_distant_tiny",
    "tf_mirror_side",
}


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


def _recovery_label(raw: dict, gated: dict) -> str:
    if gated["history_used"]:
        return "history"
    if raw["state"] == "confirmed":
        return raw["detection_source"]
    if raw["state"] == "uncertain":
        return "uncertain_fail_open"
    if not gated["blocked_model_call"]:
        return "fail_open"
    return "not_recovered"


def evaluate(manifest: Path, *, repeats: int = 3) -> tuple[list[dict], dict]:
    detector = SubjectPreflight()
    gate = SubjectPresenceGate()
    rows = read_jsonl(manifest)
    results = []
    all_latencies: list[int] = []
    confusion = Counter(
        true_positive=0,
        true_negative=0,
        false_positive=0,
        false_negative=0,
    )
    cascade_confusion = Counter(
        true_positive=0,
        true_negative=0,
        false_positive=0,
        false_negative=0,
    )
    face_only_fn = 0
    cascade_fn = 0
    history_recovered_count = 0
    uncertain_count = 0
    confirmed_missing_count = 0

    for record in rows:
        image_path = EVAL_ROOT / record["image_path"]
        stream_id = f"eval-{record['image_id']}"
        attempts = []
        for frame_id in range(1, repeats + 1):
            request = _request(image_path, frame_id).model_copy(update={"stream_id": stream_id})
            started = time.perf_counter()
            raw = detector.analyze(request)
            latency_ms = max(0, round((time.perf_counter() - started) * 1000))
            gated = gate.evaluate(stream_id, frame_id, raw, now_ms=frame_id * 500)
            raw_data = raw.model_dump(mode="json")
            gated_data = gated.model_dump(mode="json")
            all_latencies.append(latency_ms)
            attempts.append(
                {
                    "frame_id": frame_id,
                    "preflight_ms": latency_ms,
                    "raw_face_result": {
                        "detected": raw.face_detected,
                        "confidence": raw.face_confidence,
                        "confirmed": raw.state == "confirmed"
                        and raw.detection_source == "face",
                    },
                    "raw_pose_result": {
                        "detected": raw.pose_detected,
                        "confidence": raw.pose_confidence,
                        "visible_keypoints": raw.visible_pose_keypoints,
                        "confirmed": raw.state == "confirmed"
                        and raw.detection_source == "pose",
                    },
                    "raw_preflight_state": raw.state,
                    "final_gate_state": gated.state,
                    "detection_source": gated.detection_source,
                    "blocked_model_call": gated.blocked_model_call,
                    "history_used": gated.history_used,
                    "raw": raw_data,
                    "gated": gated_data,
                }
            )
        gate.reset(stream_id)
        final_attempt = attempts[-1]
        raw = final_attempt["raw"]
        gated = final_attempt["gated"]
        blocked = final_attempt["blocked_model_call"]
        present = record["expected_person_present"]
        key = (
            "false_negative"
            if present and blocked
            else "true_positive"
            if present
            else "true_negative"
            if blocked
            else "false_positive"
        )
        confusion[key] += 1
        cascade_missing = raw["state"] == "missing"
        cascade_key = (
            "false_negative"
            if present and cascade_missing
            else "true_positive"
            if present
            else "true_negative"
            if cascade_missing
            else "false_positive"
        )
        cascade_confusion[cascade_key] += 1
        if present and not (
            raw["state"] == "confirmed" and raw["detection_source"] == "face"
        ):
            face_only_fn += 1
        if present and raw["state"] == "missing":
            cascade_fn += 1
        history_recovered_count += int(gated["history_used"])
        uncertain_count += int(gated["state"] == "uncertain")
        confirmed_missing_count += int(gated["state"] == "missing")
        recovery = _recovery_label(raw, gated)
        results.append(
            {
                **record,
                "prediction": key,
                "blocked_shuttermuse": blocked,
                "face_only_false_negative": bool(
                    present
                    and not (
                        raw["state"] == "confirmed"
                        and raw["detection_source"] == "face"
                    )
                ),
                "cascade_false_negative": bool(present and raw["state"] == "missing"),
                "recovery": recovery,
                "attempts": attempts,
            }
        )

    person_present = confusion["true_positive"] + confusion["false_negative"]
    old_fn_recovery = {
        row["image_id"]: row["recovery"]
        for row in results
        if row["image_id"] in OLD_FALSE_NEGATIVE_IDS
    }
    summary = {
        "evaluation_mode": "local_mediapipe_face_pose_cascade_with_fail_open_gate",
        "total": len(rows),
        "source_counts": dict(Counter(row["source_kind"] for row in rows)),
        "scenario_count": len({row["scenario"] for row in rows}),
        "blocking_enabled": gate.blocking_enabled,
        "confusion_matrix": dict(confusion),
        "cascade_confusion_matrix": dict(cascade_confusion),
        "person_present_block_rate": round(confusion["false_negative"] / person_present, 4)
        if person_present
        else 0,
        "face_only_FN": face_only_fn,
        "cascade_FN": cascade_fn,
        "cascade_person_missing_rate": round(cascade_fn / person_present, 4)
        if person_present
        else 0,
        "history_recovered_count": history_recovered_count,
        "uncertain_count": uncertain_count,
        "confirmed_missing_count": confirmed_missing_count,
        "preflight_p50_ms": percentile(all_latencies, 0.50),
        "preflight_p95_ms": percentile(all_latencies, 0.95),
        "false_negative_ids": [
            row["image_id"] for row in results if row["prediction"] == "false_negative"
        ],
        "false_positive_ids": [
            row["image_id"] for row in results if row["prediction"] == "false_positive"
        ],
        "cascade_false_negative_ids": [
            row["image_id"] for row in results if row["cascade_false_negative"]
        ],
        "old_false_negative_recovery": old_fn_recovery,
    }
    return results, summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Beeep subject preflight over offline images."
    )
    parser.add_argument("--manifest", type=Path, default=MANIFEST_ROOT / "preflight.jsonl")
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    results, summary = evaluate(args.manifest, repeats=args.repeats)
    write_jsonl(REPORT_ROOT / "data" / "preflight_results.jsonl", results)
    write_json(REPORT_ROOT / "preflight_summary.json", summary)
    print(
        "preflight_total="
        f"{summary['total']} false_negatives={summary['confusion_matrix']['false_negative']} "
        f"cascade_fn={summary['cascade_FN']} block_rate={summary['person_present_block_rate']}"
    )


if __name__ == "__main__":
    main()
