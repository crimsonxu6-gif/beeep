from __future__ import annotations

from common import EVAL_ROOT, MANIFEST_ROOT, read_jsonl, write_jsonl


def _catalog() -> dict[str, dict]:
    rows = []
    for name in (
        "public_sources.jsonl",
        "ai_sources.jsonl",
        "transformed_sources.jsonl",
    ):
        rows.extend(read_jsonl(MANIFEST_ROOT / name))
    return {row["image_id"]: row for row in rows}


def _base_record(catalog: dict[str, dict], image_id: str) -> dict:
    source = catalog.get(image_id)
    if source is None:
        raise KeyError(f"missing catalog record: {image_id}")
    image_path = EVAL_ROOT / source["image_path"]
    if not image_path.exists():
        raise FileNotFoundError(f"missing image: {image_path}")
    return {
        "image_id": image_id,
        "image_path": source["image_path"],
        "source_kind": source["source_kind"],
        "scenario": source["scenario"],
        "expected_person_present": source["expected_person_present"],
    }


def build_preflight(catalog: dict[str, dict]) -> list[dict]:
    public_ids = [
        "public_front_face",
        "public_side_profile",
        "public_back_view",
        "public_looking_down",
        "public_hat",
        "public_sunglasses",
        "public_group",
        "public_empty_room",
        "public_mask",
        "public_full_body",
    ]
    ai_ids = [
        "ai_side_profile",
        "ai_back_view",
        "ai_looking_down",
        "ai_face_occluded",
        "ai_mask_hat",
        "ai_sunglasses_backlight",
        "ai_distant_tiny",
        "ai_lowlight_blur",
        "ai_group_edge",
        "ai_mannequin_poster",
    ]
    transformed_ids = [
        "tf_dark_front",
        "tf_overexposed_profile",
        "tf_gaussian_mask",
        "tf_motion_group",
        "tf_occluded_sunglasses",
        "tf_shrunk_full_body",
        "tf_mirror_side",
        "tf_dark_empty",
        "tf_blur_empty",
        "tf_mirror_mannequin",
    ]
    return [
        _base_record(catalog, image_id)
        for image_id in public_ids + ai_ids + transformed_ids
    ]


def _composition_record(
    catalog: dict[str, dict],
    eval_id: str,
    image_id: str,
    decision: str,
    bbox: list[float] | None,
    primary: str,
    primary_direction: str | None = None,
    secondary: str | None = None,
    secondary_direction: str | None = None,
) -> dict:
    record = _base_record(catalog, image_id)
    record.update(
        {
            "eval_id": eval_id,
            "target_ratio": "3:4",
            "composition_mode": "auto",
            "model_fixture": {
                "status": "success",
                "decision": decision,
                "bbox_norm": bbox,
                "confidence": 0.84,
            },
            "expected": {
                "primary_action": primary,
                "primary_direction": primary_direction,
                "secondary_action": secondary,
                "secondary_direction": secondary_direction,
                "secondary_helpful": secondary is not None,
            },
        }
    )
    return record


def build_composition(catalog: dict[str, dict]) -> list[dict]:
    spec = [
        (
            "comp_001",
            "public_front_face",
            "keep",
            [0.01, 0.01, 0.99, 0.99],
            "hold",
            None,
            None,
            None,
        ),
        (
            "comp_002",
            "public_side_profile",
            "refine",
            [0.02, 0.10, 0.54, 0.90],
            "move_camera",
            "left",
            "adjust_distance",
            "closer",
        ),
        (
            "comp_003",
            "public_back_view",
            "refine",
            [0.46, 0.10, 0.98, 0.90],
            "move_camera",
            "right",
            "adjust_distance",
            "closer",
        ),
        (
            "comp_004",
            "public_looking_down",
            "refine",
            [0.05, 0.00, 0.95, 0.70],
            "adjust_angle",
            "raise",
            None,
            None,
        ),
        (
            "comp_005",
            "public_hat",
            "refine",
            [0.05, 0.30, 0.95, 1.00],
            "adjust_angle",
            "lower",
            None,
            None,
        ),
        (
            "comp_006",
            "public_sunglasses",
            "refine",
            [0.18, 0.18, 0.82, 0.82],
            "adjust_distance",
            "closer",
            None,
            None,
        ),
        ("comp_007", "public_group", "reject", None, "framing_hint", None, None, None),
        (
            "comp_008",
            "public_empty_room",
            "reject",
            None,
            "framing_hint",
            None,
            None,
            None,
        ),
        (
            "comp_009",
            "public_mask",
            "keep",
            [0.01, 0.01, 0.99, 0.99],
            "hold",
            None,
            None,
            None,
        ),
        (
            "comp_010",
            "public_full_body",
            "refine",
            [0.30, 0.05, 0.94, 0.95],
            "move_camera",
            "right",
            None,
            None,
        ),
        (
            "comp_011",
            "tf_dark_front",
            "refine",
            [0.00, 0.05, 0.60, 0.95],
            "move_camera",
            "left",
            None,
            None,
        ),
        (
            "comp_012",
            "tf_overexposed_profile",
            "refine",
            [0.40, 0.05, 1.00, 0.95],
            "move_camera",
            "right",
            None,
            None,
        ),
        (
            "comp_013",
            "tf_gaussian_mask",
            "refine",
            [0.05, 0.00, 0.95, 0.70],
            "adjust_angle",
            "raise",
            None,
            None,
        ),
        (
            "comp_014",
            "tf_motion_group",
            "refine",
            [0.05, 0.30, 0.95, 1.00],
            "adjust_angle",
            "lower",
            None,
            None,
        ),
        (
            "comp_015",
            "tf_jpeg_hat",
            "refine",
            [0.22, 0.15, 0.78, 0.85],
            "adjust_distance",
            "closer",
            None,
            None,
        ),
        (
            "comp_016",
            "ai_side_profile",
            "refine",
            [0.00, 0.18, 0.48, 0.82],
            "move_camera",
            "left",
            "adjust_distance",
            "closer",
        ),
        (
            "comp_017",
            "ai_group_edge",
            "refine",
            [0.52, 0.18, 1.00, 0.82],
            "move_camera",
            "right",
            "adjust_distance",
            "closer",
        ),
        (
            "comp_018",
            "ai_distant_tiny",
            "refine",
            [0.70, 0.55, 0.97, 0.95],
            "move_camera",
            "right",
            "adjust_distance",
            "closer",
        ),
        (
            "comp_019",
            "ai_mannequin_poster",
            "reject",
            None,
            "framing_hint",
            None,
            None,
            None,
        ),
        (
            "comp_020",
            "ai_lowlight_blur",
            "keep",
            [0.01, 0.01, 0.99, 0.99],
            "hold",
            None,
            None,
            None,
        ),
    ]
    return [_composition_record(catalog, *row) for row in spec]


def build() -> tuple[list[dict], list[dict]]:
    catalog = _catalog()
    preflight = build_preflight(catalog)
    composition = build_composition(catalog)
    write_jsonl(MANIFEST_ROOT / "preflight.jsonl", preflight)
    write_jsonl(MANIFEST_ROOT / "composition.jsonl", composition)
    return preflight, composition


if __name__ == "__main__":
    preflight_rows, composition_rows = build()
    print(f"preflight={len(preflight_rows)} composition={len(composition_rows)}")
