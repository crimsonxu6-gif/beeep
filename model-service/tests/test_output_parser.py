from output_parser import parse_photographer_output


def test_parses_strict_normalized_json() -> None:
    parsed = parse_photographer_output(
        '{"decision":"refine","bbox_norm":[0.1,0.2,0.9,0.8],"confidence":0.84}',
        1000,
        1500,
    )
    assert parsed.status == "success"
    assert parsed.bbox_norm == (0.1, 0.2, 0.9, 0.8)


def test_supports_official_legacy_bbox_output() -> None:
    parsed = parse_photographer_output("(100,120),(900,880)", 1000, 1500)
    assert parsed.status == "success"
    assert parsed.decision == "refine"
    assert parsed.bbox_norm == (0.1, 0.12, 0.9, 0.88)


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
