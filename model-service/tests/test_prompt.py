from prompt import (
    OFFICIAL_PREFILL,
    build_beeep_json_photographer_prompt,
    build_official_photographer_prompt,
    build_photographer_prompt,
)


def test_official_prompt_uses_only_released_coordinate_contract() -> None:
    prompt = build_official_photographer_prompt("3:4")
    assert "请找出图片中构图最好的区域" in prompt
    assert "(x1,y1),(x2,y2)" in prompt
    assert "bbox_norm" not in prompt
    assert "JSON" not in prompt


def test_beeep_json_prompt_uses_only_normalized_json_contract() -> None:
    prompt = build_beeep_json_photographer_prompt("3:4", "thirds_right")
    assert "右侧三分线" in prompt
    assert "bbox_norm" in prompt
    assert "不要输出 Markdown" in prompt
    assert "(x1,y1),(x2,y2)" not in prompt


def test_dispatches_prompt_mode() -> None:
    assert "bounding box" in build_photographer_prompt("official", "3:4", "auto")
    assert "严格 JSON" in build_photographer_prompt("beeep_json", "3:4", "auto")
    assert "composition_xy" in build_photographer_prompt(
        "official_bbox_first", "3:4", "auto"
    )
    assert build_photographer_prompt("official_prefill", "3:4", "auto") == (
        build_photographer_prompt("official", "3:4", "auto")
    )
    assert OFFICIAL_PREFILL.startswith('{"instance_info"')
