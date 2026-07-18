from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image

EVAL_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = EVAL_ROOT / "manifests" / "real_device_image_set_2026-07-18.json"
MATRIX_PATH = EVAL_ROOT / "manifests" / "real_device_test_matrix.jsonl"
ASSET_ROOT = EVAL_ROOT / "assets" / "real_device_test_set" / "2026-07-18"
REPORT_ROOT = EVAL_ROOT / "reports"
ROUND1_REPORT = REPORT_ROOT / "real_device_redmi9a_2026-07-18.json"
ROUND2_REPORT = REPORT_ROOT / "real_device_redmi9a_2026-07-18_round2.json"

EXPECTED_IMAGE_MAPPING = {
    "normal_light_center": ("01_normal_light_center.png", "normal_light"),
    "low_light_indoor": ("02_low_light_indoor.png", "low_light"),
    "strong_backlight": ("03_strong_backlight.png", "strong_backlight"),
    "walking_motion_blur": ("04_walking_motion_blur.png", "walking_motion_blur"),
    "distant_small_person": ("05_distant_small_person.png", "distant_small_person"),
    "multiple_people_right_edge": (
        "06_multiple_people_right_edge.png",
        "multiple_people_at_edge",
    ),
    "subject_top_left": ("07_subject_top_left.png", "subject_top_left"),
    "subject_top_right": ("08_subject_top_right.png", "subject_top_right"),
    "subject_bottom_left": ("09_subject_bottom_left.png", "subject_bottom_left"),
    "subject_bottom_right": ("10_subject_bottom_right.png", "subject_bottom_right"),
}


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _matrix() -> list[dict]:
    return [json.loads(line) for line in MATRIX_PATH.read_text(encoding="utf-8").splitlines()]


def _walk_keys(value: object):
    if isinstance(value, dict):
        for key, nested in value.items():
            yield key
            yield from _walk_keys(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _walk_keys(nested)


def test_controlled_gallery_manifest_matches_original_files() -> None:
    manifest = _json(MANIFEST_PATH)
    images = manifest["images"]
    assert manifest["source_kind"] == "ai_generated"
    assert manifest["purpose"] == "real_device_controlled_test"
    assert manifest["original_preserved"] is True
    assert len(images) == 10
    assert len({image["id"] for image in images}) == 10

    for image in images:
        assert EXPECTED_IMAGE_MAPPING[image["id"]] == (
            image["filename"],
            image["scenario"],
        )
        assert image["source_kind"] == "ai_generated"
        assert image["purpose"] == "real_device_controlled_test"
        assert image["original_preserved"] is True
        assert len(image["sha256"]) == 64
        path = ASSET_ROOT / image["filename"]
        raw = path.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == image["sha256"]
        assert len(raw) == image["bytes"]
        with Image.open(path) as opened:
            assert opened.size == (image["width"], image["height"])
            assert opened.format == image["format"]


def test_real_device_reports_use_unambiguous_commit_and_timing_fields() -> None:
    paths = [ROUND1_REPORT]
    if ROUND2_REPORT.exists():
        paths.append(ROUND2_REPORT)
    for path in paths:
        report = _json(path)
        assert len(report["tested_commit_sha"]) == 40
        assert len(report["report_generated_from_sha"]) == 40
        assert report["report_commit_sha"] is None or len(report["report_commit_sha"]) == 40
        keys = set(_walk_keys(report))
        assert "commit" not in keys
        assert "request_body_bytes" not in keys
        assert "client_p50_ms" not in keys
        assert "client_p95_ms" not in keys


def test_matrix_evidence_cannot_overstate_physical_or_human_validation() -> None:
    rows = {row["case_id"]: row for row in _matrix()}
    assert len(rows) == 22

    for case_id in ("device_11", "device_12", "device_13", "device_14", "device_16", "device_17"):
        row = rows[case_id]
        result = row.get("result") or {}
        if result.get("evidence_type") == "gallery_controlled_image":
            assert row["status"] != "passed"

    for case_id in ("device_03", "device_04"):
        row = rows[case_id]
        result = row.get("result") or {}
        if row["status"] == "passed":
            assert result.get("evidence_type") == "physical_rotation"
            assert result.get("human_verified") is True

    mirror = rows["device_05"]
    if mirror["status"] == "passed":
        assert mirror["result"]["human_verified"] is True

    for case_id in ("device_07", "device_08", "device_09", "device_10"):
        row = rows[case_id]
        if row["status"] == "passed":
            assert row["result"]["human_verified"] is True
            assert len(row["result"]["bbox_norm"]) == 4
            assert len(row["result"]["transformed_bbox_px"]) == 4


def test_rules_report_never_claims_shuttermuse_was_run() -> None:
    if not ROUND2_REPORT.exists():
        return
    report = _json(ROUND2_REPORT)
    if report["app"]["guidance_engine"] == "rules":
        assert report["shuttermuse_model_path"]["status"] == "not_run"
        assert report["shuttermuse_model_path"]["reason"]


def test_second_round_report_is_a_distinct_file() -> None:
    assert ROUND1_REPORT.name != ROUND2_REPORT.name
    if ROUND2_REPORT.exists():
        assert _json(ROUND1_REPORT)["report_type"] != _json(ROUND2_REPORT)["report_type"]
