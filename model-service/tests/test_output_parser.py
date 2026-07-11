from output_parser import parse_photographer_output


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
    assert parsed.coordinate_source == "official_1000"


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
    assert parsed.coordinate_source == "official_1000"


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
    assert parsed.coordinate_source == "official_pixels"


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
