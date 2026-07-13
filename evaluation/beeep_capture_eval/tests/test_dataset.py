from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

EVAL_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = EVAL_ROOT.parents[1]
sys.path.insert(0, str(EVAL_ROOT / "scripts"))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from common import MANIFEST_ROOT, read_jsonl  # noqa: E402
from services.guidance_adapter import GuidanceAdapter  # noqa: E402
from services.shuttermuse_client import ModelCompositionResult  # noqa: E402


def test_preflight_manifest_has_required_mix_and_scenarios() -> None:
    rows = read_jsonl(MANIFEST_ROOT / "preflight.jsonl")
    assert len(rows) == 30
    assert Counter(row["source_kind"] for row in rows) == {
        "public_real": 10,
        "ai_generated": 10,
        "transformed": 10,
    }
    scenarios = {row["scenario"] for row in rows}
    required_fragments = {
        "front_face",
        "side_profile",
        "back_view",
        "looking_down",
        "face_occluded",
        "mask",
        "hat",
        "sunglasses",
        "full_body",
        "multiple_people",
        "person_very_small",
    }
    assert required_fragments <= scenarios
    assert sum(not row["expected_person_present"] for row in rows) >= 5


def test_public_manifest_has_explicit_allowed_license_metadata() -> None:
    rows = read_jsonl(MANIFEST_ROOT / "public_sources.jsonl")
    assert len(rows) == 10
    for row in rows:
        assert row["source_url"].startswith("https://commons.wikimedia.org/wiki/File:")
        assert row["author"]
        assert row["downloaded_at"]
        assert row["license"].startswith(("CC0", "CC BY", "Public domain", "PDM"))


def test_composition_manifest_exercises_expected_adapter_actions() -> None:
    rows = read_jsonl(MANIFEST_ROOT / "composition.jsonl")
    assert len(rows) == 20
    assert Counter(row["source_kind"] for row in rows) == {
        "public_real": 10,
        "transformed": 5,
        "ai_generated": 5,
    }
    adapter = GuidanceAdapter()
    for frame_id, row in enumerate(rows, start=1):
        fixture = row["model_fixture"]
        result = ModelCompositionResult(
            request_id=row["eval_id"],
            frame_id=frame_id,
            status=fixture["status"],
            decision=fixture["decision"],
            bbox_norm=fixture["bbox_norm"],
            confidence=fixture["confidence"],
            inference_ms=0,
            prompt_mode="beeep_json",
            coordinate_source="bbox_norm" if fixture["bbox_norm"] else None,
        )
        output = adapter.from_model_composition(result, frame_id)
        expected = row["expected"]
        assert output.actions[0].type == expected["primary_action"]
        assert (
            getattr(output.actions[0], "direction", None)
            == expected["primary_direction"]
        )
        if expected["secondary_helpful"]:
            assert len(output.actions) == 2
            assert output.actions[1].type == expected["secondary_action"]
            assert (
                getattr(output.actions[1], "direction", None)
                == expected["secondary_direction"]
            )
        else:
            assert len(output.actions) == 1


def test_manifests_are_valid_jsonl() -> None:
    for path in MANIFEST_ROOT.glob("*.jsonl"):
        for line in path.read_text(encoding="utf-8").splitlines():
            assert isinstance(json.loads(line), dict)
