from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
REPORT_PATH = ROOT / "evaluation" / "beeep_capture_eval" / "reports" / "simulator_latest.json"
MANIFEST_PATH = ROOT / "assets" / "analysis-fixtures" / "manifest.json"


def test_simulator_report_has_traceable_full_commit_fields() -> None:
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    assert len(report["base_commit"]) == 40
    assert len(report["implementation_commit_sha"]) == 40
    assert report["tested_commit_sha"] is None or len(report["tested_commit_sha"]) == 40
    assert len(report["report_generated_from_sha"]) == 40


def test_fixture_manifest_uses_actual_file_dimensions_and_bytes() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    by_id = {item["id"]: item for item in manifest}
    assert by_id["landscape_group"]["width"] == 1280
    assert by_id["landscape_group"]["height"] == 960
    assert by_id["large_portrait"]["width"] == 3024
    assert by_id["large_portrait"]["height"] == 4032

    for item in manifest:
        path = MANIFEST_PATH.parent / item["file"]
        with Image.open(path) as image:
            assert image.size == (item["width"], item["height"])
        assert path.stat().st_size == item["bytes"]
