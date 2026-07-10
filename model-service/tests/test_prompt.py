from prompt import build_beeep_photographer_prompt


def test_prompt_preserves_official_task_and_adds_beeep_context() -> None:
    prompt = build_beeep_photographer_prompt("3:4", "thirds_right")
    assert "请找出图片中构图最好的区域" in prompt
    assert "3:4" in prompt
    assert "右侧三分线" in prompt
    assert "bbox_norm" in prompt
    assert "composition" in prompt
    assert "zh-CN" in prompt
    assert "不要输出 Markdown" in prompt
