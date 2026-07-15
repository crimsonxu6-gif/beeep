import pytest

from output_parser import extract_partial_explicit_bbox, parse_photographer_output


def test_parses_strict_normalized_json() -> None:
    parsed = parse_photographer_output(
        '{"decision":"refine","bbox_norm":[0.1,0.2,0.9,0.8],"confidence":0.84}',
        1000,
        1500,
    )
    assert parsed.status == "success"
    assert parsed.bbox_norm == (0.1, 0.2, 0.9, 0.8)
    assert parsed.coordinate_source == "bbox_norm"


def test_supports_official_norm1000_contract() -> None:
    parsed = parse_photographer_output(
        "(100,120),(900,880)",
        768,
        1024,
        prompt_mode="official",
        official_coordinate_format="norm1000",
    )
    assert parsed.status == "success"
    assert parsed.bbox_norm == (0.1, 0.12, 0.9, 0.88)
    assert parsed.coordinate_source == "official_1000_pairs"


def test_recovers_complete_explicit_field_from_unclosed_json() -> None:
    raw = '{"instance_info":[{"composition_xy":[100,120,900,880],"reason":"unfinished'
    parsed = parse_photographer_output(
        raw,
        768,
        1024,
        prompt_mode="official",
        official_coordinate_format="norm1000",
        reached_max_new_tokens=True,
    )
    assert parsed.status == "success"
    assert parsed.bbox_norm == (0.1, 0.12, 0.9, 0.88)
    assert parsed.coordinate_source == "official_1000_partial_composition_xy"
    assert parsed.partial_structure_used is True
    assert parsed.json_complete is False
    assert parsed.bbox_field_complete is True


@pytest.mark.parametrize(
    "raw",
    [
        '{"composition_xy":[100,120,900',
        '{"composition_xy":[900,120,100,880]',
        '{"reason":"scores 100,120,900,880"',
        '{"composition_xy":[-1,120,900,880]',
    ],
)
def test_partial_extraction_rejects_incomplete_unsafe_or_unrelated_values(raw: str) -> None:
    assert extract_partial_explicit_bbox(raw, "norm1000") is None


def test_supports_official_trained_instance_info_contract() -> None:
    parsed = parse_photographer_output(
        '{"instance_info":[{"task_type":"composition","reason":"主体偏左",'
        '"composition_xy":"(120,80),(880,920)"}]}',
        1080,
        1440,
        prompt_mode="official",
        official_coordinate_format="norm1000",
    )
    assert parsed.status == "success"
    assert parsed.bbox_norm == (0.12, 0.08, 0.88, 0.92)
    assert parsed.coordinate_source == "official_1000_composition_xy"


def test_official_pixel_contract_does_not_guess_from_value_size() -> None:
    parsed = parse_photographer_output(
        "(100,80),(700,950)",
        768,
        1024,
        prompt_mode="official",
        official_coordinate_format="pixels",
    )
    assert parsed.status == "success"
    assert parsed.bbox_norm == (100 / 768, 80 / 1024, 700 / 768, 950 / 1024)
    assert parsed.coordinate_source == "official_pixels_pairs"


def test_explicit_pixel_json_is_parsed_as_pixels() -> None:
    parsed = parse_photographer_output(
        '{"decision":"refine","bbox_pixels":[100,80,700,950]}',
        768,
        1024,
    )
    assert parsed.status == "success"
    assert parsed.bbox_norm == (100 / 768, 80 / 1024, 700 / 768, 950 / 1024)


def test_ambiguous_bbox_field_is_rejected() -> None:
    parsed = parse_photographer_output(
        '{"decision":"refine","bbox":[100,80,700,950]}',
        768,
        1024,
    )
    assert parsed.status == "low_confidence"
    assert parsed.error_code == "INVALID_MODEL_OUTPUT"


def test_near_full_frame_preserves_keep_with_tolerance() -> None:
    parsed = parse_photographer_output(
        '{"decision":"keep","bbox_norm":[0.001,0.0,0.999,1.0]}',
        1000,
        1500,
    )
    assert parsed.status == "success"
    assert parsed.decision == "keep"


def test_invalid_bbox_is_not_clamped_or_fabricated() -> None:
    parsed = parse_photographer_output(
        '{"decision":"refine","bbox_norm":[-0.2,0.1,1.2,0.9]}',
        1000,
        1500,
    )
    assert parsed.status == "low_confidence"
    assert parsed.bbox_norm is None
    assert parsed.error_code == "INVALID_MODEL_OUTPUT"


def test_reject_can_have_no_bbox() -> None:
    parsed = parse_photographer_output(
        '{"decision":"reject","bbox_norm":null,"confidence":0.7}',
        1000,
        1500,
    )
    assert parsed.status == "success"
    assert parsed.decision == "reject"
    assert parsed.bbox_norm is None


def test_supports_official_four_number_list() -> None:
    parsed = parse_photographer_output(
        "[100,120,900,880]",
        1000,
        1000,
        prompt_mode="official",
    )
    assert parsed.status == "success"
    assert parsed.coordinate_source == "official_1000_list"


def test_supports_official_json_bbox() -> None:
    parsed = parse_photographer_output(
        '{"bbox":[100,120,900,880]}',
        1000,
        1000,
        prompt_mode="official",
    )
    assert parsed.status == "success"
    assert parsed.coordinate_source == "official_1000_json_bbox"


def test_supports_official_composition_bbox() -> None:
    parsed = parse_photographer_output(
        '{"composition_bbox":[100,120,900,880]}',
        1000,
        1000,
        prompt_mode="official",
    )
    assert parsed.status == "success"
    assert parsed.coordinate_source == "official_1000_composition_bbox"


def test_supports_official_composition_xy_array() -> None:
    parsed = parse_photographer_output(
        '{"composition_xy":[100,120,900,880]}',
        1000,
        1000,
        prompt_mode="official",
    )
    assert parsed.status == "success"
    assert parsed.coordinate_source == "official_1000_composition_xy"


def test_classifies_placeholder_output() -> None:
    parsed = parse_photographer_output("<bbox>", 1000, 1000, prompt_mode="official")
    assert parsed.parse_failure_type == "PLACEHOLDER_OUTPUT"


def test_classifies_empty_output() -> None:
    parsed = parse_photographer_output("  ", 1000, 1000, prompt_mode="official")
    assert parsed.parse_failure_type == "EMPTY_MODEL_OUTPUT"


def test_classifies_reversed_geometry() -> None:
    parsed = parse_photographer_output(
        "(900,100),(100,800)", 1000, 1000, prompt_mode="official"
    )
    assert parsed.parse_failure_type == "INVALID_BBOX_GEOMETRY"


def test_classifies_truncated_output() -> None:
    parsed = parse_photographer_output(
        '{"instance_info":[{"composition_xy":"(100,100)',
        1000,
        1000,
        prompt_mode="official",
    )
    assert parsed.parse_failure_type == "OUTPUT_TRUNCATED"


def test_does_not_extract_unrelated_numbers_from_long_text() -> None:
    parsed = parse_photographer_output(
        "2026 年有 12 个场景，评分 4 分，版本 3，未提供构图坐标。",
        1000,
        1000,
        prompt_mode="official",
    )
    assert parsed.status == "low_confidence"
    assert parsed.bbox_norm is None
    assert parsed.parse_failure_type == "PARSER_UNSUPPORTED_FORMAT"
