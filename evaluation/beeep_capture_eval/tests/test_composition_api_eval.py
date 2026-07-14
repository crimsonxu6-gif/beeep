from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

EVAL_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = EVAL_ROOT.parents[1]
sys.path.insert(0, str(EVAL_ROOT / "scripts"))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

import render_report  # noqa: E402
import run_composition_eval as composition_eval  # noqa: E402
from common import read_jsonl, write_json, write_jsonl  # noqa: E402


def record(image_path: Path, eval_id: str = "api_001") -> dict:
    return {
        "eval_id": eval_id,
        "image_id": eval_id,
        "image_path": str(image_path),
        "scenario": "front_face",
        "source_kind": "public_real",
        "expected_person_present": True,
        "composition_mode": "auto",
        "target_ratio": "3:4",
        "model_fixture": {
            "status": "success",
            "decision": "refine",
            "bbox_norm": [0.1, 0.1, 0.8, 0.9],
            "confidence": 0.8,
        },
        "expected": {
            "primary_action": "move_camera",
            "primary_direction": "left",
            "secondary_action": None,
            "secondary_direction": None,
            "secondary_helpful": False,
        },
    }


def api_success(frame_id: int = 1) -> dict:
    return {
        "status": "success",
        "http_status": 200,
        "request_id": "req_live",
        "frame_id": frame_id,
        "confidence": 0.84,
        "actions": [
            {
                "type": "move_camera",
                "direction": "left",
                "message": "镜头稍微往左移",
            }
        ],
        "composition": {"decision": "refine", "bbox_norm": [0.1, 0.1, 0.8, 0.9]},
        "model_metadata": {
            "prompt_mode": "official",
            "coordinate_source": "official_1000",
            "decision": "refine",
            "bbox_norm": [0.1, 0.1, 0.8, 0.9],
            "confidence": 0.84,
            "inference_ms": 900,
        },
        "subject_preflight": {
            "state": "confirmed",
            "detection_source": "face",
        },
        "timing": {"preflight_ms": 18, "guidance_ms": 900, "total_ms": 930},
    }


def build_manifest(tmp_path: Path, count: int = 1) -> Path:
    image_path = tmp_path / "source.jpg"
    Image.new("RGB", (100, 200), "white").save(image_path)
    manifest = tmp_path / "composition.jsonl"
    write_jsonl(manifest, [record(image_path, f"api_{index:03d}") for index in range(count)])
    return manifest


def test_api_mode_records_raw_model_fields_and_can_be_saved(
    tmp_path: Path, monkeypatch
) -> None:
    manifest = build_manifest(tmp_path)
    monkeypatch.setattr(composition_eval, "_api_output", lambda *_args: api_success())
    results, summary = composition_eval.evaluate(
        manifest,
        mode="api",
        api_url="http://test/v1/analyze",
        reviews_path=tmp_path / "reviews.jsonl",
        render_artifacts=False,
    )
    output_path = tmp_path / "results.jsonl"
    write_jsonl(output_path, results)
    saved = read_jsonl(output_path)[0]
    assert summary["api_success_count"] == 1
    assert saved["request_id"] == "req_live"
    assert saved["prompt_mode"] == "official"
    assert saved["coordinate_source"] == "official_1000"
    assert saved["raw_model_decision"] == "refine"
    assert saved["raw_bbox_norm"] == [0.1, 0.1, 0.8, 0.9]
    assert saved["preflight_detection_source"] == "face"
    assert saved["checks"]["fixture_expected_primary_match"] is None
    assert summary["human_primary_direction_correct_rate"] is None
    assert summary["wrong_direction_rate"] is None


def test_api_quality_metrics_only_use_human_review(tmp_path: Path, monkeypatch) -> None:
    manifest = build_manifest(tmp_path)
    reviews_path = tmp_path / "reviews.jsonl"
    write_jsonl(
        reviews_path,
        [
            {
                **composition_eval.default_review("api_000"),
                "bbox_quality": 2,
                "primary_direction_correct": False,
                "primary_action_helpful": False,
            }
        ],
    )
    monkeypatch.setattr(composition_eval, "_api_output", lambda *_args: api_success())
    results, summary = composition_eval.evaluate(
        manifest,
        mode="api",
        api_url="http://test/v1/analyze",
        reviews_path=reviews_path,
        render_artifacts=False,
    )
    assert results[0]["checks"]["fixture_expected_direction_match"] is None
    assert summary["human_primary_direction_correct_rate"] == 0
    assert summary["human_primary_action_helpful_rate"] == 0
    assert summary["wrong_direction_count"] == 1
    assert summary["wrong_direction_rate"] == 1


def test_api_error_is_recorded_without_aborting_batch(tmp_path: Path, monkeypatch) -> None:
    manifest = build_manifest(tmp_path, count=2)
    responses = iter(
        [
            api_success(),
            {
                "status": "error",
                "http_status": 503,
                "frame_id": 2,
                "error": {"code": "MODEL_BUSY", "message": "busy"},
            },
        ]
    )
    monkeypatch.setattr(composition_eval, "_api_output", lambda *_args: next(responses))
    results, summary = composition_eval.evaluate(
        manifest,
        mode="api",
        api_url="http://test/v1/analyze",
        reviews_path=tmp_path / "reviews.jsonl",
        render_artifacts=False,
    )
    assert len(results) == 2
    assert summary["api_success_count"] == 1
    assert summary["api_failure_count"] == 1
    assert summary["error_distribution"] == {"MODEL_BUSY": 1}


def test_invalid_model_output_is_counted(tmp_path: Path, monkeypatch) -> None:
    manifest = build_manifest(tmp_path)
    monkeypatch.setattr(
        composition_eval,
        "_api_output",
        lambda *_args: {
            "status": "error",
            "http_status": 502,
            "frame_id": 1,
            "error": {"code": "INVALID_MODEL_OUTPUT", "message": "invalid"},
        },
    )
    results, summary = composition_eval.evaluate(
        manifest,
        mode="api",
        api_url="http://test/v1/analyze",
        reviews_path=tmp_path / "reviews.jsonl",
        render_artifacts=False,
    )
    assert results[0]["bbox_parse_status"] == "invalid"
    assert summary["invalid_output_count"] == 1
    assert summary["invalid_output_rate"] == 1


def test_normalized_bbox_maps_to_visual_pixels() -> None:
    assert composition_eval.bbox_pixels((0.1, 0.2, 0.8, 0.9), 1000, 500) == (
        100,
        100,
        800,
        450,
    )


def test_human_review_fields_round_trip(tmp_path: Path) -> None:
    reviews_path = tmp_path / "reviews.jsonl"
    rows = [record(Path("unused.jpg"))]
    composition_eval.ensure_reviews(rows, reviews_path)
    review = read_jsonl(reviews_path)[0]
    review.update(
        {
            "bbox_quality": 4,
            "composition_improved": True,
            "subject_preserved": True,
            "review_notes": "good crop",
        }
    )
    write_jsonl(reviews_path, [review])
    loaded = composition_eval.ensure_reviews(rows, reviews_path)["api_001"]
    assert loaded["bbox_quality"] == 4
    assert loaded["composition_improved"] is True
    assert loaded["review_notes"] == "good crop"


def test_report_separates_fixture_and_live_api(tmp_path: Path, monkeypatch) -> None:
    manifest_root = tmp_path / "manifests"
    report_root = tmp_path / "reports"
    manifest_root.mkdir()
    write_jsonl(manifest_root / "preflight.jsonl", [])
    write_jsonl(manifest_root / "composition.jsonl", [record(Path("unused.jpg"))])
    for name in ("public_sources", "ai_sources", "transformed_sources"):
        write_jsonl(manifest_root / f"{name}.jsonl", [])
    write_json(report_root / "preflight_summary.json", {"confusion_matrix": {}})
    write_json(
        report_root / "composition_fixture_summary.json",
        {"total": 1, "bbox_parse_success": 1, "direction_correct": 1},
    )
    write_json(
        report_root / "composition_api_summary.json",
        {
            "total": 1,
            "api_success_count": 1,
            "api_success_rate": 1,
            "review": {"reviewed_count": 0, "unreviewed_count": 1},
        },
    )
    write_jsonl(report_root / "data" / "composition_fixture_results.jsonl", [])
    write_jsonl(report_root / "data" / "composition_api_results.jsonl", [])
    monkeypatch.setattr(render_report, "MANIFEST_ROOT", manifest_root)
    monkeypatch.setattr(render_report, "REPORT_ROOT", report_root)
    render_report.render()
    markdown = (report_root / "latest.md").read_text(encoding="utf-8")
    assert "## 2. GuidanceAdapter Fixture" in markdown
    assert "## 3. ShutterMuse API" in markdown
    assert "Fixture output is not evidence" in markdown
